#pragma once
#include "nmea_gga.h"
namespace gnss_receiver {
struct Snapshot {
    gnss::Gga solution;
    uint32_t accepted = 0, rejected = 0, overflow = 0, uart_errors = 0;
    uint32_t correction_frames_sent = 0, correction_frames_dropped = 0;
    bool enabled = false, start_failed = false;
};
void begin();
bool enqueueCorrections(const uint8_t* data, size_t length);
Snapshot snapshot();
}
