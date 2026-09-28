#pragma once
#include <cstdint>
#include "gnss_receiver.h"
#include "health_packet.h"
#include "health_timing.h"

namespace health_report {

// La parte de la salud que sale del receptor —calidad (byte 8) y precisión
// mostrada y cruda (bytes 1-4 y 12-15)— con su caducidad. Aparte de
// `health_report.h` y sin Arduino para probarla en la PC con la instantánea de
// verdad (test/health_solution_test.cpp).
//
// `nowUs`: esp_timer_get_time() leído **después** de tomar la instantánea.
inline void fillFromReceiver(protocol::HealthInputs& in, const gnss_receiver::Snapshot& snapshot, uint64_t nowUs) {
    const bool solutionFresh = protocol::arrivedWithin(snapshot.accepted, snapshot.solution.arrival_us, nowUs,
                                                       protocol::kHealthSolutionMaxAgeUs);
    // La sigma de GST describe una solución: sin solución vigente no hay
    // precisión que enseñar, igual que en `/api/status`.
    const bool precisionFresh = solutionFresh
        && protocol::arrivedWithin(snapshot.precision_accepted, snapshot.precision.arrival_us, nowUs,
                                   protocol::kHealthPrecisionMaxAgeUs);
    // GGA vencida: calidad 0, «sin solución». Es lo que el byte ya significa y
    // lo que las apps pintan como sin fix; no se inventa un código nuevo.
    in.quality = solutionFresh ? uint8_t(snapshot.solution.quality) : 0;
    in.um980RawHorizontalSigmaMm = protocol::kUnknownMm;
    in.um980RawVerticalSigmaMm = protocol::kUnknownMm;
    if (precisionFresh) {
        const auto& p = snapshot.precision;
        // Cruda del UM980, tal como llega en GST: no se toca.
        in.um980RawHorizontalSigmaMm = protocol::sigmaToMm(
            protocol::um980WorstAxisHorizontalSigmaM(p.latitude_sigma_m, p.longitude_sigma_m, p.horizontal_sigma_m));
        in.um980RawVerticalSigmaMm = protocol::sigmaToMm(p.altitude_sigma_m);
    }
    // Precision que Meridian V enseña (decision de producto): la gobierna la
    // horizontal cruda. Sin estimacion vigente del receptor sale 0xFFFF.
    in.meridianDisplay = protocol::meridianDisplayFromRaw(in.um980RawHorizontalSigmaMm);
}

}  // namespace health_report
