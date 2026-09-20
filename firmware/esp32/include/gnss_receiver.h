#pragma once
#include "nmea_gga.h"
namespace gnss_receiver {
struct Snapshot {
    gnss::Gga solution;
    uint32_t accepted = 0, rejected = 0, overflow = 0, uart_errors = 0;
    bool enabled = false, start_failed = false;
};
void begin();
Snapshot snapshot();
}
