#pragma once
#include <cmath>
namespace base_plan {
// Altura del case entre el punto medido y la base del receptor. Todavía no se
// ha medido la carcasa: hasta entonces es una constante declarada, no un dato
// verificado. Cambiarla aquí la cambia en todo el firmware.
constexpr double kCaseOffsetM = 0.10;
inline bool known(double lat, double lon, double height, double antenna, bool marker, double& arp) {
    if (!std::isfinite(lat) || !std::isfinite(lon) || !std::isfinite(height) || !std::isfinite(antenna) ||
        lat < -90 || lat > 90 || lon < -180 || lon > 180 || antenna < 0 || antenna > 100) return false;
    arp = height + (marker ? antenna : 0);
    return height >= -30000 && height <= 30000 && arp >= -30000 && arp <= 30000;
}
inline bool average(unsigned seconds, double reuse) {
    return seconds >= 1 && seconds <= 3600 && std::isfinite(reuse) && reuse >= 0 && reuse <= 10;
}
}
