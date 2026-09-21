#pragma once
#include "nmea_gga.h"
namespace gnss_receiver {
struct Snapshot {
    gnss::Gga solution;
    uint32_t accepted = 0, rejected = 0, overflow = 0, uart_errors = 0;
    // Tramas RTCM entregadas al receptor por la UART y descartadas antes de salir.
    // Sin estas cifras no se puede distinguir "el caster no manda" de "no llega al GPS".
    uint32_t correction_frames_sent = 0, correction_frames_dropped = 0;
    // Salud del binario nativo Unicore (OBSVMB y efemerides usadas para PPK).
    uint32_t native_valid = 0, native_invalid = 0;
    bool enabled = false, start_failed = false;
};
void begin();
bool enqueueCorrections(const uint8_t* data, size_t length);
Snapshot snapshot();
}
