#pragma once
#include <cstdint>
#include "ble_frames.h"

namespace protocol {
inline bool telemetryFresh(uint64_t now, uint64_t built, uint64_t arrival, bool solution) {
    return now >= built && now - built <= kSolutionMaxAgeUs &&
           (!solution || (now >= arrival && now - arrival <= kSolutionMaxAgeUs));
}
}
