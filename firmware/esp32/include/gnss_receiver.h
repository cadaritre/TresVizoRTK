#pragma once
#include "nmea_gga.h"
#include "nmea_gst.h"
namespace gnss_receiver {
struct Snapshot {
    gnss::Gga solution;
    // Estimación de error del propio receptor (GST). Es su desviación típica
    // declarada, no una exactitud comprobada contra una referencia externa.
    gnss::Gst precision;
    uint32_t precision_accepted = 0;
    uint32_t accepted = 0, rejected = 0, overflow = 0, uart_errors = 0;
    // Tramas RTCM entregadas al receptor por la UART y descartadas antes de salir.
    // Sin estas cifras no se puede distinguir "el caster no manda" de "no llega al GPS".
    uint32_t correction_frames_sent = 0, correction_frames_dropped = 0;
    // Desde 0.7.11, el detalle: bytes RTCM escritos a la UART, tramas desalojadas
    // por falta de sitio (las más viejas) y caducadas (más de 2 s o de otra
    // generación de fuente), y la ocupación de la cola en bytes. `dropped` es la
    // suma de las dos, como antes. Con estas cifras cuadran recibido, encolado,
    // escrito y descartado.
    uint64_t correction_bytes_written = 0;
    uint32_t correction_frames_evicted = 0, correction_frames_expired = 0;
    uint32_t correction_queue_bytes = 0, correction_queue_high_water_bytes = 0, correction_queue_capacity_bytes = 0;
    // Salud del binario nativo Unicore (OBSVMB y efemerides usadas para PPK).
    uint32_t native_valid = 0, native_invalid = 0;
    bool enabled = false, start_failed = false;
};
void begin();
bool enqueueCorrections(const uint8_t* data, size_t length);
Snapshot snapshot();
}
