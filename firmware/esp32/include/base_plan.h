#pragma once
#include <cmath>
namespace base_plan {
// Altura del case entre el punto medido y la base del receptor. Todavía no se
// ha medido la carcasa: hasta entonces es una constante declarada, no un dato
// verificado. **Es la única del firmware**: la usan el plan de coordenada
// conocida (instrument.cpp) y el promedio (base_survey.cpp). Cambiarla aquí la
// cambia en todo el firmware.
constexpr double kCaseOffsetM = 0.10;
// La altura que se recibe es siempre la del punto en el suelo: desde 0.6.2 no
// se pregunta a que punto corresponde, asi que la antena siempre se suma.
inline bool known(double lat, double lon, double height, double antenna, double& arp) {
    if (!std::isfinite(lat) || !std::isfinite(lon) || !std::isfinite(height) || !std::isfinite(antenna) ||
        lat < -90 || lat > 90 || lon < -180 || lon > 180 || antenna < 0 || antenna > 100) return false;
    arp = height + antenna;
    return height >= -30000 && height <= 30000 && arp >= -30000 && arp <= 30000;
}
inline bool average(unsigned seconds, double reuse) {
    return seconds >= 1 && seconds <= 3600 && std::isfinite(reuse) && reuse >= 0 && reuse <= 10;
}

// --- Promedio hecho por el ESP32 (base_survey.cpp) --------------------------

// Altura elipsoidal de la antena en una época GGA: la altura sobre el geoide
// más la ondulación que informa el propio receptor. Con `CONFIG UNDULATION
// 0.0000` la ondulación llega en 0 y la altura ya es elipsoidal; con AUTO, la
// suma deshace el geoide interno del receptor. Sin ondulación informada se toma
// 0 y el estado del promedio lo advierte (`geoid_separation_known`).
inline double ggaEllipsoidHeightM(double altitudeMslM, double geoidSeparationM) {
    return altitudeMslM + (std::isfinite(geoidSeparationM) ? geoidSeparationM : 0);
}

// Alturas elipsoidales que salen de un promedio.
struct SurveyHeights {
    // La que se declara en `MODE BASE`: la media **tal cual**.
    double declaredEllipsoidHeightM;
    // Cota de la marca en el suelo. Solo informativa: no se envía al receptor.
    double markEllipsoidHeightM;
};

// **La media de las GGA ya es la posición de la antena.** El receptor tiene
// `CONFIG ANTENNADELTAHEN 0 0 0` (receiver_baseline.h): no desplaza nada, así
// que lo que entrega es la antena, no la marca. Por eso se declara tal cual.
//
// Hasta 0.7.12 se le sumaban además la altura de antena del operador y el case,
// y la base quedaba alta justo en esa cantidad (con un jalón de 1.8 m, 1.90 m).
// La altura de antena solo sirve ahora para **informar** la cota de la marca:
// media − antena − case.
inline SurveyHeights surveyHeights(double meanAntennaEllipsoidHeightM, double antennaVerticalM) {
    return {meanAntennaEllipsoidHeightM, meanAntennaEllipsoidHeightM - antennaVerticalM - kCaseOffsetM};
}
}
