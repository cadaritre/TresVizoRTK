#pragma once
#include <algorithm>
#include <cstdint>
#include "ble_transport.h"
#include "correction_router.h"
#include "gnss_receiver.h"
#include "gnss_sky.h"
#include "gnss_visible.h"
#include "health_packet.h"

// El paquete de salud que mandan el Bluetooth y el WebSocket, armado en un
// solo sitio para que los dos no puedan dar cifras distintas. La codificacion
// y la regla de precision mostrada estan en `lib/protocol/src/health_packet.h`.
namespace health_report {

inline void build(uint8_t report[20], const gnss_receiver::Snapshot& snapshot) {
    protocol::HealthInputs in;
    if (snapshot.precision_accepted) {
        const auto& p = snapshot.precision;
        // Cruda del UM980, tal como llega en GST: no se toca.
        in.um980RawHorizontalSigmaMm = protocol::sigmaToMm(
            protocol::um980WorstAxisHorizontalSigmaM(p.latitude_sigma_m, p.longitude_sigma_m, p.horizontal_sigma_m));
        in.um980RawVerticalSigmaMm = protocol::sigmaToMm(p.altitude_sigma_m);
    }
    // Precision que Meridian V enseña (decision de producto): la gobierna la
    // horizontal cruda. Sin estimacion del receptor sale 0xFFFF.
    in.meridianDisplay = protocol::meridianDisplayFromRaw(in.um980RawHorizontalSigmaMm);
    const uint32_t age = correction_router::ageMs();
    in.correctionAgeSeconds = age == UINT32_MAX ? protocol::kUnknownMm
                                                : uint16_t(std::min<uint32_t>(age / 1000, 65534));
    in.source = uint8_t(correction_router::sourceCode());
    in.quality = uint8_t(snapshot.solution.quality);
    // Satelites **rastreados** (GSV). 255 = sin GSV reciente.
    unsigned tracked = 0;
    in.tracked = gnss_sky::tracked(tracked) ? uint8_t(std::min(tracked, 254u)) : 255;
    // Satelites **visibles** (geometria sobre la mascara). 255 = no se sabe.
    unsigned visible = 0;
    in.visible = gnss_visible::visible(visible) ? uint8_t(std::min(visible, 254u)) : 255;
    // Contadores de RTCM (desde 0.7.11): lo que el equipo tiró camino del UM980
    // y lo que llegó corrupto. Sin UART configurada no hay cola y no se mandan.
    if (snapshot.correction_queue_capacity_bytes) {
        in.hasRtcmCounters = true;
        in.rtcmFramesDiscarded = uint8_t(snapshot.correction_frames_dropped);
        in.rtcmFramesRejected = uint8_t(correction_router::rejectedFrames() + ble_transport::rtcmParserRejected());
        in.rtcmQueuePercent = protocol::queuePercent(snapshot.correction_queue_bytes, snapshot.correction_queue_capacity_bytes);
    }
    protocol::encodeHealth(report, in);
}

}  // namespace health_report
