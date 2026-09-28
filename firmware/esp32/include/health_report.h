#pragma once
#include <algorithm>
#include <cstdint>
#include "ble_transport.h"
#include "correction_router.h"
#include "gnss_receiver.h"
#include "gnss_sky.h"
#include "gnss_visible.h"
#include "health_packet.h"
#include "health_solution.h"

// El paquete de salud que mandan el Bluetooth y el WebSocket, armado en un
// solo sitio para que los dos no puedan dar cifras distintas. La codificacion
// y la regla de precision mostrada estan en `lib/protocol/src/health_packet.h`;
// la caducidad de la calidad y la precision, en `health_solution.h` y
// `lib/protocol/src/health_timing.h`.
namespace health_report {

// `nowUs`: esp_timer_get_time() leído **después** de tomar `snapshot`, para que
// una GGA llegada entre las dos lecturas no quede «en el futuro».
inline void build(uint8_t report[20], const gnss_receiver::Snapshot& snapshot, uint64_t nowUs) {
    protocol::HealthInputs in;
    // Calidad y precision, solo si la GGA y la GST siguen vigentes (2 s).
    fillFromReceiver(in, snapshot, nowUs);
    const uint32_t age = correction_router::ageMs();
    in.correctionAgeSeconds = age == UINT32_MAX ? protocol::kUnknownMm
                                                : uint16_t(std::min<uint32_t>(age / 1000, 65534));
    in.source = uint8_t(correction_router::sourceCode());
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
