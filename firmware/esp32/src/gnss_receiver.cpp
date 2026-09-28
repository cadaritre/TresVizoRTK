#include <Arduino.h>
#include <esp_timer.h>
#include "gnss_receiver.h"
#include "correction_router.h"
#include "gnss_control.h"
#include "gnss_sky.h"
#include "sd_recorder.h"
#include "receiver_stream.h"
#include "correction_output.h"
#include "rtcm_queue.h"
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
// Correcciones camino del UM980: cola **por bytes** (lib/protocol/src/rtcm_queue.h).
// Hasta 0.7.10 eran cuatro tramas y una época MSM de cuatro constelaciones son
// de 6 a 10: la UART a 115200 (≈11.5 kB/s) no alcanzaba a vaciarlas cuando
// llegaban de golpe y se tiraban tramas en cada época. 8 KiB caben una época
// completa del peor caso (MSM7, cuatro constelaciones, 1005/1033/1230, unos
// 6 kB) mientras la anterior aún sale, y equivalen a unos 0.7 s de UART: más
// no sirve, porque lo que espere más de kCorrectionMaxAgeMs se tira igual.
constexpr size_t kCorrectionQueueBytes = 8192;
// Una corrección que esperó más que esto ya no ayuda al receptor: el UM980
// trabaja con la época más reciente y las viejas solo le quitan UART.
constexpr uint32_t kCorrectionMaxAgeMs = 2000;
protocol::RtcmFrameQueue<kCorrectionQueueBytes> corrections;
// Productores: el Bluetooth (tarea de Bluedroid) y NTRIP; consumidor: gnss_rx.
portMUX_TYPE correctionsLock = portMUX_INITIALIZER_UNLOCKED;
struct Outbound { uint16_t length; uint8_t bytes[protocol::RtcmFrameQueue<kCorrectionQueueBytes>::kMaxFrameBytes]; };

// Fuera de la pila de la tarea: la trama son 1029 bytes.
Outbound outbound = {};
constexpr size_t kBlock = 512;
uint8_t rawBlock[kBlock];
char textBlock[kBlock];

void acquire(void*) {
    gnss::GgaParser parser;
    gnss::GstParser precisionParser;
    // Los satelites uno a uno. GSV trae donde esta cada uno y con cuanta senal;
    // GSA, cuales entraron en la solucion y los tres DOP. Ninguna de las dos
    // cosas esta en GGA, que solo dice cuantos se usaron.
    gnss::GsvParser skyParser;
    gnss::GsaParser usedParser;
    // Texto NMEA, binario Unicore y, como base, RTCM, por la misma UART. El
    // RTCM se reconstruye con el byte crudo para publicarlo o servirlo; el
    // texto, sin el binario (lib/gnss/src/receiver_stream.h).
    gnss::ReceiverStream stream;
    gnss::Gga solution;
    gnss::Gst precision;
    gnss::GsvMessage sky;
    gnss::Gsa used;
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
                stream.feed(rawBlock[i], now, [](const uint8_t* p, size_t size) {
                    correction_output::publish(p, size);
                }, [&](char character) {
                    parser.feed(character, arrival, solution);
                    precisionParser.feed(character, arrival, precision);
                    // El cielo se guarda en su propio modulo: la instantanea de
                    // aqui se copia en media docena de sitios que no lo usan.
                    if (skyParser.feed(character, arrival, sky)) gnss_sky::feed(sky, now);
                    if (usedParser.feed(character, arrival, used)) gnss_sky::feed(used, now);
                    textBlock[textLength++] = character;
                });
            }
            if (textLength) gnss_control::feed(textBlock, textLength);
        }
        if (!outbound.length) gnss_control::tick(uart);
        // Las órdenes de configuración al UM980 van por la misma UART: mientras
        // haya una en curso no se empieza otra trama, para no intercalar bytes.
        if (!gnss_control::busy() && !outbound.length) {
            // La caducidad y la generación se miran **al sacar**, antes del
            // primer byte. Una trama empezada se termina siempre: dejarla a
            // medias en la UART le costaría al UM980 también la siguiente.
            portENTER_CRITICAL(&correctionsLock);
            outbound.length = uint16_t(corrections.pop(outbound.bytes, millis(), kCorrectionMaxAgeMs, correction_router::generation()));
            portEXIT_CRITICAL(&correctionsLock);
            sent = 0;
        }
        if (outbound.length) {
            const size_t remaining = outbound.length - sent;
            const size_t available = uart.availableForWrite();
            const size_t count = std::min<size_t>(128, std::min(remaining, available));
            if (count) sent += uart.write(outbound.bytes + sent, count);
            if (sent == outbound.length) {
                portENTER_CRITICAL(&lock);
                ++state.correction_frames_sent;
                state.correction_bytes_written += outbound.length;
                portEXIT_CRITICAL(&lock);
                outbound.length = 0;
            }
        }
        portENTER_CRITICAL(&lock);
        state.solution = solution;
        state.precision = precision;
        state.precision_accepted = precisionParser.accepted;
        state.accepted = parser.accepted;
        state.rejected = parser.rejected;
        state.overflow = parser.overflow;
        state.native_valid = stream.filter.native_valid;
        state.native_invalid = stream.filter.native_invalid;
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
    //
    // **8 KiB de pila, no 4.** Con 4 KiB el camino más hondo dejaba unos 600
    // bytes antes de contar interrupciones: `acquire` ocupa 2112, su lambda 192
    // y `correction_output::publish` 1072 (medido con -fstack-usage). El
    // 26-09-2026, al activar GSV y GSA por COM2, el equipo empezó a reiniciarse
    // por panic cada pocos minutos con la pila corrupta. El mínimo de pila libre
    // de esta tarea se publica en `/api/status` → `memory.stack_free_min_bytes`.
    const bool started = uart && xTaskCreate(acquire, "gnss_rx", 8192, nullptr, 2, nullptr) == pdPASS;
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
    // Siempre entra: si no cabe, la cola desaloja las tramas más viejas y lo
    // cuenta (`correction_frames_evicted`). La nueva vale más que la atrasada.
    size_t evicted = 0;
    portENTER_CRITICAL(&correctionsLock);
    const bool queued = corrections.push(data, length, millis(), correction_router::generation(), evicted);
    portEXIT_CRITICAL(&correctionsLock);
    return queued;
#else
    (void)data; (void)length;
#endif
    return false;
}
Snapshot snapshot() {
    portENTER_CRITICAL(&lock);
    Snapshot copy = state;
    portEXIT_CRITICAL(&lock);
#ifdef TRESVIZO_GNSS_CONFIGURED
    portENTER_CRITICAL(&correctionsLock);
    const auto counters = corrections.counters();
    copy.correction_queue_bytes = corrections.usedBytes();
    copy.correction_queue_high_water_bytes = corrections.highWaterBytes();
    portEXIT_CRITICAL(&correctionsLock);
    copy.correction_queue_capacity_bytes = kCorrectionQueueBytes;
    copy.correction_frames_evicted = counters.framesEvicted;
    copy.correction_frames_expired = counters.framesExpired + counters.framesTooLarge;
    // El total de siempre: todo lo que entró a la cola y no llegó al UM980.
    copy.correction_frames_dropped = copy.correction_frames_evicted + copy.correction_frames_expired;
#endif
    return copy;
}
}
