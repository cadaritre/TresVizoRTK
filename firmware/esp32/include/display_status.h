#pragma once
#include "gnss_receiver.h"
#include "health_timing.h"
#include <cstdio>
#include <cstring>

// Texto de campo sin Arduino/I2C, para probar pérdidas de GNSS y correcciones.
namespace display_status {
struct Lines {
    const char* fix;
    char satellites[22], corrections[22], storage[22];
};
inline Lines build(const gnss_receiver::Snapshot& gnss, uint64_t nowUs,
                   uint8_t source, uint32_t correctionAgeMs, const char* sdState) {
    Lines result{};
    const bool fresh = gnss.enabled && protocol::arrivedWithin(
        gnss.accepted, gnss.solution.arrival_us, nowUs, protocol::kHealthSolutionMaxAgeUs);
    if (!gnss.enabled || !gnss.accepted) result.fix = "ESPERA";
    else if (!fresh) result.fix = "ANTIGUO";
    else if (!gnss.solution.has_position) result.fix = "SIN FIX";
    else switch (gnss.solution.quality) {
        case 1: result.fix = "SINGLE"; break;
        case 2: result.fix = "DGPS"; break;
        case 4: result.fix = "FIX"; break;
        case 5: result.fix = "FLOAT"; break;
        case 6: result.fix = "ESTIMADO"; break;
        default: result.fix = "SIN FIX"; break;
    }
    if (fresh && gnss.solution.has_satellites)
        std::snprintf(result.satellites,sizeof(result.satellites),"SAT %u",gnss.solution.satellites);
    else std::snprintf(result.satellites,sizeof(result.satellites),"SAT --");
    const char* sourceName = source == 1 ? "BLE" : source == 2 ? "NTRIP" : source == 3 ? "RADIO" : "--";
    if (!source || correctionAgeMs == UINT32_MAX)
        std::snprintf(result.corrections,sizeof(result.corrections),"RTCM %s --",sourceName);
    else if (correctionAgeMs >= 100000)
        std::snprintf(result.corrections,sizeof(result.corrections),"RTCM %s >99s",sourceName);
    else std::snprintf(result.corrections,sizeof(result.corrections),"RTCM %s %lu.%lus",sourceName,
                       (unsigned long)(correctionAgeMs / 1000),(unsigned long)((correctionAgeMs % 1000) / 100));
    const char* state = !std::strcmp(sdState,"recording") ? "GRABANDO"
        : !std::strcmp(sdState,"closing") ? "CERRANDO"
        : !std::strcmp(sdState,"busy") ? "OCUPADA"
        : (!std::strcmp(sdState,"idle") || !std::strcmp(sdState,"closed")) ? "LISTA"
        : !std::strcmp(sdState,"card_missing") ? "NO DISP." : "REVISAR";
    std::snprintf(result.storage,sizeof(result.storage),"MEM INT. %s",state);
    return result;
}
}
