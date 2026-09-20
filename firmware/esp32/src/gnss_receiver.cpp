#include <Arduino.h>
#include <esp_timer.h>
#include "gnss_receiver.h"

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
void acquire(void*) {
    gnss::GgaParser parser;
    gnss::Gga solution;
    for (;;) {
        // Un bloque acotado permite atender otras tareas con entrada continua.
        for (size_t budget = 0; budget < 4096 && uart.available(); ++budget) {
            parser.feed(static_cast<char>(uart.read()), esp_timer_get_time(), solution);
        }
        portENTER_CRITICAL(&lock);
        state.solution = solution;
        state.accepted = parser.accepted;
        state.rejected = parser.rejected;
        state.overflow = parser.overflow;
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
Snapshot snapshot() {
    portENTER_CRITICAL(&lock);
    Snapshot copy = state;
    portEXIT_CRITICAL(&lock);
    return copy;
}
}
