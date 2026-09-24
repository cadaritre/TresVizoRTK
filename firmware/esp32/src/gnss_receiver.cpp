#include <Arduino.h>
#include <esp_timer.h>
#include "gnss_receiver.h"
#include "correction_router.h"
#include "gnss_control.h"
#include "sd_recorder.h"
#include "wire_filter.h"
#include "rtcm3.h"
#include "correction_output.h"
#ifdef TRESVIZO_TASK_WDT
#include <esp_task_wdt.h>
#endif

#if defined(TRESVIZO_GNSS_RX) || defined(TRESVIZO_GNSS_TX) || defined(TRESVIZO_GNSS_BAUD)
#if !defined(TRESVIZO_GNSS_RX) || !defined(TRESVIZO_GNSS_TX) || !defined(TRESVIZO_GNSS_BAUD)
#error "Configure RX, TX y BAUD juntos, solo tras verificar el cableado."
#endif
#define TRESVIZO_GNSS_CONFIGURED
#endif

namespace gnss_receiver {
namespace {
portMUX_TYPE lock = portMUX_INITIALIZER_UNLOCKED;
Snapshot state;
#ifdef TRESVIZO_GNSS_CONFIGURED
HardwareSerial uart(2);
struct Correction { uint32_t arrival, generation; uint16_t length; uint8_t bytes[1029]; };
QueueHandle_t corrections = nullptr;

// Fuera de la pila de la tarea: la trama son 1029 bytes y "gnss_rx" tiene 4 KiB.
Correction outbound = {};
constexpr size_t kBlock = 512;
uint8_t rawBlock[kBlock];
char textBlock[kBlock];

void acquire(void*) {
    gnss::GgaParser parser;
    gnss::GstParser precisionParser;
    gnss::WireFilter filter;
    // El receptor emite RTCM por la misma UART cuando trabaja como base. Se
    // reconstruyen las tramas aquí para poder publicarlas o servirlas.
    gnss::Rtcm3Parser outgoing;
    gnss::Gga solution;
    gnss::Gst precision;
    size_t sent = 0;
#ifdef TRESVIZO_TASK_WDT
    // Desactivado por defecto: cambia el comportamiento ante un bloqueo a reinicio
    // y todavia no se ha ensayado en campo. Habilitar con -DTRESVIZO_TASK_WDT.
    esp_task_wdt_add(nullptr);
#endif
    for (;;) {
#ifdef TRESVIZO_TASK_WDT
        esp_task_wdt_reset();
#endif
        // Se lee por bloques y se entrega por bloques: antes cada byte costaba un
        // xStreamBufferSend y una toma de semaforo desde esta misma tarea.
        for (size_t budget = 0; budget < 4096 && uart.available(); budget += kBlock) {
            const size_t wanted = uart.available() < int(kBlock) ? size_t(uart.available()) : kBlock;
            const size_t got = uart.read(rawBlock, wanted);
            if (!got) break;
            sd_recorder::feed(rawBlock, got);
            // Una marca por bloque leido del driver, no una por byte: el instante
            // sigue siendo de llegada al ESP32, no de medicion del receptor.
            const uint64_t arrival = esp_timer_get_time();
            const uint32_t now = millis();
            size_t textLength = 0;
            for (size_t i = 0; i < got; ++i) {
                filter.feed(rawBlock[i], now, [&](char character) {
                    parser.feed(character, arrival, solution);
                    precisionParser.feed(character, arrival, precision);
                    outgoing.feed(uint8_t(character), [](const uint8_t* p, size_t size) {
                        correction_output::publish(p, size);
                    });
                    textBlock[textLength++] = character;
                });
            }
            if (textLength) gnss_control::feed(textBlock, textLength);
        }
        if (!outbound.length) gnss_control::tick(uart);
        if (!gnss_control::busy() && !outbound.length && xQueueReceive(corrections, &outbound, 0) == pdTRUE) sent = 0;
        if (outbound.length) {
            if (millis() - outbound.arrival > 2000 || outbound.generation != correction_router::generation()) {
                portENTER_CRITICAL(&lock); ++state.correction_frames_dropped; portEXIT_CRITICAL(&lock);
                outbound.length = 0;
            } else {
                const size_t remaining = outbound.length - sent;
                const size_t available = uart.availableForWrite();
                const size_t count = std::min<size_t>(128, std::min(remaining, available));
                if (count) sent += uart.write(outbound.bytes + sent, count);
                if (sent == outbound.length) {
                    portENTER_CRITICAL(&lock); ++state.correction_frames_sent; portEXIT_CRITICAL(&lock);
                    outbound.length = 0;
                }
            }
        }
        portENTER_CRITICAL(&lock);
        state.solution = solution;
        state.precision = precision;
        state.precision_accepted = precisionParser.accepted;
        state.accepted = parser.accepted;
        state.rejected = parser.rejected;
        state.overflow = parser.overflow;
        state.native_valid = filter.native_valid;
        state.native_invalid = filter.native_invalid;
        portEXIT_CRITICAL(&lock);
        vTaskDelay(1);
    }
}
#endif
}
void begin() {
#ifdef TRESVIZO_GNSS_CONFIGURED
    if (uart.setRxBufferSize(8192) != 8192) {
        portENTER_CRITICAL(&lock);
        state.start_failed = true;
        portEXIT_CRITICAL(&lock);
        return;
    }
    uart.onReceiveError([](hardwareSerial_error_t error) {
        if (error == UART_NO_ERROR) return;
        portENTER_CRITICAL(&lock);
        ++state.uart_errors;
        portEXIT_CRITICAL(&lock);
    });
    corrections = xQueueCreate(4, sizeof(Correction));
    if (!corrections) {
        portENTER_CRITICAL(&lock);
        state.start_failed = true;
        portEXIT_CRITICAL(&lock);
        return;
    }
    uart.begin(TRESVIZO_GNSS_BAUD, SERIAL_8N1, TRESVIZO_GNSS_RX, TRESVIZO_GNSS_TX);
    // La tarea UART no depende del temporizador HTTP ni del mutex de configuración.
    const bool started = uart && xTaskCreate(acquire, "gnss_rx", 4096, nullptr, 2, nullptr) == pdPASS;
    portENTER_CRITICAL(&lock);
    state.enabled = started;
    state.start_failed = !started;
    portEXIT_CRITICAL(&lock);
    if (!started) uart.end();
#endif
}
bool enqueueCorrections(const uint8_t* data, size_t length) {
#ifdef TRESVIZO_GNSS_CONFIGURED
    if (length > 1029 || length < 6 || !snapshot().enabled) return false;
    Correction frame = {}; frame.arrival = millis(); frame.generation = correction_router::generation(); frame.length = length;
    memcpy(frame.bytes, data, length);
    if (xQueueSend(corrections, &frame, 0) == pdTRUE) return true;
    portENTER_CRITICAL(&lock); ++state.correction_frames_dropped; portEXIT_CRITICAL(&lock);
#else
    (void)data; (void)length;
#endif
    return false;
}
Snapshot snapshot() {
    portENTER_CRITICAL(&lock);
    Snapshot copy = state;
    portEXIT_CRITICAL(&lock);
    return copy;
}
}
