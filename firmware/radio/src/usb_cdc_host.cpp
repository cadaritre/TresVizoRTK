#include "usb_cdc_host.h"
#include <Arduino.h>
#include <algorithm>
#include <atomic>
#include <cstring>
#include <esp_intr_alloc.h>
#include <freertos/FreeRTOS.h>
#include <freertos/semphr.h>
#include <freertos/stream_buffer.h>
#include <freertos/task.h>
#include "usb/usb_host.h"

namespace usb_cdc_host {
namespace {
// --- Tamaños (con su motivo) --------------------------------------------------------
// IN: múltiplo del paquete de 64 B de full speed. La transferencia acaba con el primer
// paquete corto, así que lo que escribe el receptor llega enseguida, no al llenarla.
constexpr size_t kInBytes = 512;
// OUT: una trama del enlace (1033 B) o una RTCM (1029 B) caben en una transferencia.
constexpr size_t kOutBytes = 1088;
// Holgura entre el USB y el bucle principal (que se queda ~100 ms en cada paquete que
// transmite): más de un segundo del RTCM más gordo que cabe por el aire.
constexpr size_t kRxBytes = 4096;
constexpr size_t kTxBytes = 4096;
constexpr size_t kControlBytes = sizeof(usb_setup_packet_t) + 7;
constexpr uint8_t kClassComm = 0x02, kSubclassAcm = 0x02, kClassData = 0x0a;
constexpr uint8_t kSetLineCoding = 0x20, kSetControlLineState = 0x22;
// DTR = RTS = 0. En el USB-Serial/JTAG del ESP32-S3, RTS reinicia el chip (es lo que usa
// esptool para reiniciarlo) y DTR prepara el modo de descarga. El MeridianV se usa así
// desde siempre (monitor_dtr = monitor_rts = 0 en firmware/esp32/platformio.ini).
constexpr uint16_t kLineState = 0;
// 115200 8N1. El USB-Serial/JTAG no usa la velocidad; un CDC con UART detrás, sí.
constexpr uint8_t kLineCoding[7] = {0x00, 0xc2, 0x01, 0x00, 0, 0, 8};
// Errores seguidos de una transferencia antes de dar el dispositivo por perdido.
constexpr uint32_t kMaxConsecutiveErrors = 8;
// Si al cerrar algo no vuelve en este tiempo, se cierra igual.
constexpr uint32_t kCloseTimeoutMs = 2000;

enum class Phase : uint8_t { idle, lineCoding, lineState, ready, closing };

// Todo esto lo toca solo la tarea `usb_cdc` (los callbacks corren dentro de
// usb_host_client_handle_events, en esa misma tarea), salvo lo atómico y el anillo de
// salida, que va con su cerrojo.
usb_host_client_handle_t client = nullptr;
usb_device_handle_t device = nullptr;
usb_transfer_t* inTransfer = nullptr;
usb_transfer_t* outTransfer = nullptr;
usb_transfer_t* controlTransfer = nullptr;
uint8_t inEndpoint = 0, outEndpoint = 0, commInterface = 0, dataInterface = 0;
uint16_t inPacket = 64;
bool haveComm = false;
bool inBusy = false, outBusy = false, controlBusy = false;
uint32_t consecutiveErrors = 0, closingSince = 0;
bool openPending = false, gonePending = false;
uint8_t pendingAddress = 0;

std::atomic<Phase> phase{Phase::idle};
std::atomic<bool> installed{false};
std::atomic<uint32_t> sessions{0}, refused{0}, rxDropped{0}, txDropped{0}, transferErrors{0};
std::atomic<uint16_t> lastVid{0}, lastPid{0};

StreamBufferHandle_t rx = nullptr;
SemaphoreHandle_t txLock = nullptr;
SemaphoreHandle_t installedSignal = nullptr;
uint8_t txRing[kTxBytes];
size_t txHead = 0, txCount = 0;

void onIn(usb_transfer_t* transfer);
void onOut(usb_transfer_t* transfer);
void onControl(usb_transfer_t* transfer);

void onClientEvent(const usb_host_client_event_msg_t* event, void*) {
    if (event->event == USB_HOST_CLIENT_EVENT_NEW_DEV) {
        pendingAddress = event->new_dev.address;
        openPending = true;
    } else if (event->event == USB_HOST_CLIENT_EVENT_DEV_GONE && device && event->dev_gone.dev_hdl == device) {
        gonePending = true;
    }
}

void beginClose() {
    if (!device || phase == Phase::closing) return;
    phase = Phase::closing;
    closingSince = millis();
    // Lo que esté en vuelo vuelve cancelado por su callback.
    for (const uint8_t endpoint : {inEndpoint, outEndpoint}) {
        usb_host_endpoint_halt(device, endpoint);
        usb_host_endpoint_flush(device, endpoint);
    }
}

void finishClose() {
    for (const uint8_t endpoint : {inEndpoint, outEndpoint}) usb_host_endpoint_clear(device, endpoint);
    usb_host_interface_release(client, device, dataInterface);
    usb_host_device_close(client, device);
    device = nullptr;
    inBusy = outBusy = controlBusy = false;
    phase = Phase::idle;
}

void transferFailed() {
    ++transferErrors;
    if (++consecutiveErrors > kMaxConsecutiveErrors) beginClose();
}

void submitIn() {
    inTransfer->device_handle = device;
    inTransfer->bEndpointAddress = inEndpoint;
    inTransfer->num_bytes = int(kInBytes - kInBytes % inPacket);
    inTransfer->callback = onIn;
    inBusy = true;
    if (usb_host_transfer_submit(inTransfer) != ESP_OK) { inBusy = false; ++transferErrors; beginClose(); }
}

void pumpOut() {
    if (outBusy || phase != Phase::ready) return;
    size_t n = 0;
    xSemaphoreTake(txLock, portMAX_DELAY);
    while (n < kOutBytes && txCount) {
        const size_t run = std::min(std::min(txCount, kTxBytes - txHead), kOutBytes - n);
        std::memcpy(outTransfer->data_buffer + n, txRing + txHead, run);
        n += run;
        txHead = (txHead + run) % kTxBytes;
        txCount -= run;
    }
    xSemaphoreGive(txLock);
    if (!n) return;
    outTransfer->device_handle = device;
    outTransfer->bEndpointAddress = outEndpoint;
    outTransfer->num_bytes = int(n);
    outTransfer->callback = onOut;
    outBusy = true;
    if (usb_host_transfer_submit(outTransfer) != ESP_OK) { outBusy = false; transferFailed(); }
}

void startReady() {
    xSemaphoreTake(txLock, portMAX_DELAY);
    txHead = txCount = 0;
    xSemaphoreGive(txLock);
    xStreamBufferReset(rx);   // nadie espera en él: el bucle lee sin bloquear
    consecutiveErrors = 0;
    phase = Phase::ready;
    ++sessions;
    submitIn();
}

void submitControl(uint8_t request, uint16_t value, const uint8_t* data, uint16_t length) {
    auto* setup = reinterpret_cast<usb_setup_packet_t*>(controlTransfer->data_buffer);
    setup->bmRequestType = USB_BM_REQUEST_TYPE_DIR_OUT | USB_BM_REQUEST_TYPE_TYPE_CLASS | USB_BM_REQUEST_TYPE_RECIP_INTERFACE;
    setup->bRequest = request;
    setup->wValue = value;
    setup->wIndex = commInterface;
    setup->wLength = length;
    if (length) std::memcpy(controlTransfer->data_buffer + sizeof(usb_setup_packet_t), data, length);
    controlTransfer->num_bytes = int(sizeof(usb_setup_packet_t) + length);
    controlTransfer->device_handle = device;
    controlTransfer->bEndpointAddress = 0;
    controlTransfer->callback = onControl;
    controlBusy = true;
    if (usb_host_transfer_submit_control(client, controlTransfer) != ESP_OK) {
        controlBusy = false; ++transferErrors; beginClose();
    }
}

void onControl(usb_transfer_t* transfer) {
    controlBusy = false;
    if (phase == Phase::closing) return;
    const usb_transfer_status_t status = transfer->status;
    if (status == USB_TRANSFER_STATUS_NO_DEVICE || status == USB_TRANSFER_STATUS_CANCELED) return;   // DEV_GONE llega aparte
    // Los dos pedidos son opcionales en CDC: si el dispositivo no los atiende, se sigue.
    if (status != USB_TRANSFER_STATUS_COMPLETED) ++transferErrors;
    if (phase == Phase::lineCoding) {
        phase = Phase::lineState;
        submitControl(kSetControlLineState, kLineState, nullptr, 0);
    } else if (phase == Phase::lineState) {
        startReady();
    }
}

void onIn(usb_transfer_t* transfer) {
    inBusy = false;
    if (phase != Phase::ready) return;
    const usb_transfer_status_t status = transfer->status;
    if (status == USB_TRANSFER_STATUS_NO_DEVICE || status == USB_TRANSFER_STATUS_CANCELED) return;
    if (status == USB_TRANSFER_STATUS_COMPLETED) {
        consecutiveErrors = 0;
        const size_t n = size_t(transfer->actual_num_bytes);
        if (n) {
            const size_t kept = xStreamBufferSend(rx, transfer->data_buffer, n, 0);
            if (kept < n) rxDropped += uint32_t(n - kept);   // el demultiplexor se resincroniza
        }
    } else transferFailed();
    if (phase == Phase::ready) submitIn();
}

void onOut(usb_transfer_t* transfer) {
    outBusy = false;
    const usb_transfer_status_t status = transfer->status;
    if (status == USB_TRANSFER_STATUS_COMPLETED) consecutiveErrors = 0;
    else if (status != USB_TRANSFER_STATUS_NO_DEVICE && status != USB_TRANSFER_STATUS_CANCELED) transferFailed();
    pumpOut();
}

// Busca una interfaz de datos CDC (clase 0x0A) con un bulk IN y un bulk OUT, y la de
// comunicaciones ACM (para DTR/RTS y la velocidad), si la hay.
bool findCdc(const usb_config_desc_t* config) {
    haveComm = false;
    bool haveData = false;
    int offset = 0;
    const auto* desc = reinterpret_cast<const usb_standard_desc_t*>(config);
    while ((desc = usb_parse_next_descriptor_of_type(desc, config->wTotalLength, USB_B_DESCRIPTOR_TYPE_INTERFACE, &offset))) {
        const auto* intf = reinterpret_cast<const usb_intf_desc_t*>(desc);
        if (intf->bAlternateSetting != 0) continue;
        if (!haveComm && intf->bInterfaceClass == kClassComm && intf->bInterfaceSubClass == kSubclassAcm) {
            haveComm = true;
            commInterface = intf->bInterfaceNumber;
        }
        if (haveData || intf->bInterfaceClass != kClassData) continue;
        uint8_t in = 0, out = 0;
        uint16_t inSize = 0;
        for (int i = 0; i < intf->bNumEndpoints; ++i) {
            int endpointOffset = offset;
            const usb_ep_desc_t* ep = usb_parse_endpoint_descriptor_by_index(intf, i, config->wTotalLength, &endpointOffset);
            if (!ep || USB_EP_DESC_GET_XFERTYPE(ep) != USB_TRANSFER_TYPE_BULK) continue;
            if (USB_EP_DESC_GET_EP_DIR(ep)) { in = ep->bEndpointAddress; inSize = USB_EP_DESC_GET_MPS(ep); }
            else out = ep->bEndpointAddress;
        }
        if (in && out && inSize) {
            haveData = true;
            dataInterface = intf->bInterfaceNumber;
            inEndpoint = in;
            outEndpoint = out;
            inPacket = inSize;
        }
    }
    return haveData;
}

void openDevice(uint8_t address) {
    if (usb_host_device_open(client, address, &device) != ESP_OK) { device = nullptr; return; }
    const usb_device_desc_t* deviceDesc = nullptr;
    if (usb_host_get_device_descriptor(device, &deviceDesc) == ESP_OK && deviceDesc) {
        lastVid = deviceDesc->idVendor;
        lastPid = deviceDesc->idProduct;
    }
    const usb_config_desc_t* config = nullptr;
    if (usb_host_get_active_config_descriptor(device, &config) != ESP_OK || !config || !findCdc(config) ||
        usb_host_interface_claim(client, device, dataInterface, 0) != ESP_OK) {
        // No es un CDC (teclado, memoria...): se suelta y se espera a otro.
        ++refused;
        usb_host_device_close(client, device);
        device = nullptr;
        return;
    }
    consecutiveErrors = 0;
    if (haveComm) {
        phase = Phase::lineCoding;
        submitControl(kSetLineCoding, 0, kLineCoding, sizeof(kLineCoding));
    } else {
        startReady();
    }
}

void libraryTask(void*) {
    usb_host_config_t config = {};
    config.skip_phy_setup = false;      // PHY interno en modo anfitrión (GPIO19/20)
    config.intr_flags = ESP_INTR_FLAG_LEVEL1;
    installed = usb_host_install(&config) == ESP_OK;
    xSemaphoreGive(installedSignal);
    if (!installed) { vTaskDelete(nullptr); return; }
    for (;;) {
        uint32_t flags = 0;
        usb_host_lib_handle_events(portMAX_DELAY, &flags);
        if (flags & USB_HOST_LIB_EVENT_FLAGS_NO_CLIENTS) usb_host_device_free_all();
    }
}

void clientTask(void*) {
    usb_host_client_config_t config = {};
    config.is_synchronous = false;
    config.max_num_event_msg = 5;
    config.async.client_event_callback = onClientEvent;
    config.async.callback_arg = nullptr;
    if (usb_host_client_register(&config, &client) != ESP_OK ||
        usb_host_transfer_alloc(kInBytes, 0, &inTransfer) != ESP_OK ||
        usb_host_transfer_alloc(kOutBytes, 0, &outTransfer) != ESP_OK ||
        usb_host_transfer_alloc(kControlBytes, 0, &controlTransfer) != ESP_OK) {
        installed = false;
        vTaskDelete(nullptr);
        return;
    }
    for (;;) {
        usb_host_client_handle_events(client, pdMS_TO_TICKS(10));
        if (gonePending) { gonePending = false; beginClose(); }
        if (phase == Phase::closing &&
            ((!inBusy && !outBusy && !controlBusy) || millis() - closingSince > kCloseTimeoutMs))
            finishClose();
        if (openPending && phase == Phase::idle && !device) { openPending = false; openDevice(pendingAddress); }
        pumpOut();
    }
}
}  // namespace

bool begin() {
    rx = xStreamBufferCreate(kRxBytes, 1);
    txLock = xSemaphoreCreateMutex();
    installedSignal = xSemaphoreCreateBinary();
    if (!rx || !txLock || !installedSignal) return false;
    // Las dos tareas del USB en el núcleo 0; el bucle de Arduino (LoRa) va en el 1.
    if (xTaskCreatePinnedToCore(libraryTask, "usb_lib", 4096, nullptr, 3, nullptr, 0) != pdPASS) return false;
    if (xSemaphoreTake(installedSignal, pdMS_TO_TICKS(2000)) != pdTRUE || !installed) return false;
    return xTaskCreatePinnedToCore(clientTask, "usb_cdc", 4096, nullptr, 2, nullptr, 0) == pdPASS;
}

uint32_t session() { return sessions.load(); }
bool open() { return phase.load() == Phase::ready; }

size_t read(uint8_t* out, size_t capacity) {
    return rx ? xStreamBufferReceive(rx, out, capacity, 0) : 0;
}

bool write(const uint8_t* data, size_t length) {
    if (!length) return true;
    if (phase.load() != Phase::ready || length > kTxBytes || !txLock) { ++txDropped; return false; }
    xSemaphoreTake(txLock, portMAX_DELAY);
    const bool fits = kTxBytes - txCount >= length;
    if (fits) {
        size_t tail = (txHead + txCount) % kTxBytes;
        for (size_t done = 0; done < length;) {
            const size_t run = std::min(length - done, kTxBytes - tail);
            std::memcpy(txRing + tail, data + done, run);
            done += run;
            tail = (tail + run) % kTxBytes;
        }
        txCount += length;
    }
    xSemaphoreGive(txLock);
    if (!fits) { ++txDropped; return false; }
    usb_host_client_unblock(client);   // que la tarea del USB lo mande ya
    return true;
}

Info info() {
    Info out;
    out.installed = installed.load();
    out.open = open();
    out.vid = lastVid.load();
    out.pid = lastPid.load();
    out.sessions = sessions.load();
    out.refused = refused.load();
    out.rxDropped = rxDropped.load();
    out.txDropped = txDropped.load();
    out.transferErrors = transferErrors.load();
    return out;
}
}  // namespace usb_cdc_host
