#include "usb_channel.h"
#include "config_rules.h"
#include "radio_module.h"
#include "radio_usb.h"
#include <atomic>
#include <cstring>
#include <freertos/semphr.h>
#ifdef TRESVIZO_TASK_WDT
#include <esp_task_wdt.h>
#endif

namespace usb_channel {
// La consola de siempre admite 1024 bytes por orden; el demultiplexor, lo mismo.
static_assert(radio_usb::kMaxLineBytes == config_rules::kMaxRequestBytes, "límite de línea distinto de la consola");
namespace {
// Lo que se lee de una vez del CDC (su búfer de entrada es de 2048, main.cpp).
constexpr size_t kReadBytes = 512;
// La tarea duerme poco: el RTCM de una época llega de golpe y no debe esperar.
constexpr TickType_t kPollTicks = pdMS_TO_TICKS(2);

SemaphoreHandle_t writeLock = nullptr;
radio_usb::Demux demux;
// La orden para el bucle. La escribe la tarea solo con `linePending` en false y la lee
// el bucle solo con `linePending` en true.
char line[radio_usb::kMaxLineBytes + 1];
size_t lineLength = 0;
std::atomic<bool> linePending{false};
uint8_t rx[kReadBytes];
size_t rxPosition = 0, rxLength = 0;

bool writeText(const char* text) {
    return write(reinterpret_cast<const uint8_t*>(text), strlen(text));
}

struct Handler {
    void onFrame(uint8_t type, const uint8_t* payload, size_t length) { radio_module::onFrame(type, payload, length); }
    void onRtcm(const uint8_t* frame, size_t length) { radio_module::onRtcm(frame, length); }
    // Con un radio enlazado no hay consola: del otro lado está el radio, que no manda
    // órdenes; una línea sería un trozo roto y no se ejecuta ni se contesta.
    void onLine(const char* text, size_t length) {
        if (radio_module::connected()) return;
        memcpy(line, text, length);
        line[length] = '\0';
        lineLength = length;
        linePending = true;
    }
    void onLineOverflow() {
        if (!radio_module::connected()) writeText("{\"status\":413,\"body\":{\"error\":\"request_too_large\"}}\n");
    }
    void onLineTimeout() {
        if (!radio_module::connected()) writeText("{\"status\":408,\"body\":{\"error\":\"request_timeout\"}}\n");
    }
};
Handler handler;

void task(void*) {
#ifdef TRESVIZO_TASK_WDT
    esp_task_wdt_add(nullptr);
#endif
    for (;;) {
#ifdef TRESVIZO_TASK_WDT
        esp_task_wdt_reset();
#endif
        if (rxPosition == rxLength && !linePending) {
            const int available = Serial.available();
            if (available > 0) {
                rxLength = Serial.read(rx, size_t(available) < kReadBytes ? size_t(available) : kReadBytes);
                rxPosition = 0;
            }
        }
        // Byte a byte para parar en cuanto haya una orden esperando al bucle: lo que
        // venga detrás se queda aquí hasta que la tome.
        const uint32_t now = millis();
        while (rxPosition < rxLength && !linePending) demux.feed(rx + rxPosition++, 1, now, handler);
        demux.tick(millis(), handler);
        radio_module::service(millis());
        vTaskDelay(kPollTicks);
    }
}
}  // namespace

bool begin() {
    writeLock = xSemaphoreCreateMutex();
    // Pila holgada: los JsonDocument del enlace y una trama entera para escribir.
    return writeLock && xTaskCreate(task, "usb_link", 8192, nullptr, 1, nullptr) == pdPASS;
}

bool write(const uint8_t* data, size_t length) {
    if (!length) return true;
    if (!writeLock) return Serial.write(data, length) == length;
    xSemaphoreTake(writeLock, portMAX_DELAY);
    const size_t written = Serial.write(data, length);
    xSemaphoreGive(writeLock);
    return written == length;
}

bool writeLine(const String& text) {
    // Texto y '\n' bajo el mismo cerrojo, sin copiar la respuesta (puede pasar de 5 KB).
    if (writeLock) xSemaphoreTake(writeLock, portMAX_DELAY);
    const bool ok = Serial.write(reinterpret_cast<const uint8_t*>(text.c_str()), text.length()) == text.length() &&
                    Serial.write(uint8_t('\n')) == 1;
    if (writeLock) xSemaphoreGive(writeLock);
    return ok;
}

size_t takeLine(char* out, size_t capacity) {
    if (!linePending.load()) return 0;
    const size_t n = lineLength < capacity ? lineLength : capacity - 1;
    memcpy(out, line, n);
    out[n] = '\0';
    linePending = false;
    return n;
}

uint32_t errors() {
    // Lecturas sueltas de contadores de 32 bits: sin cerrojo, como el resto del estado.
    return demux.counters.crcErrors + demux.counters.expired + demux.counters.abandoned;
}
}  // namespace usb_channel
