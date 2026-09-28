// Reglas del promedio de base del ESP32 (include/base_average.h).
#include "base_average.h"
#include <cassert>
#include <limits>

int main() {
    using namespace base_average;
    const double nan = std::numeric_limits<double>::quiet_NaN();
    const double lat = 19.4326077, lon = -99.1332080;

    // Calidad exigida.
    assert(matches(Quality::Fixed, 4) && !matches(Quality::Fixed, 5) && !matches(Quality::Fixed, 0));
    assert(matches(Quality::Float, 5) && !matches(Quality::Float, 4));
    assert(matches(Quality::Single, 1) && !matches(Quality::Single, 2));
    assert(matches(Quality::Any, 1) && matches(Quality::Any, 4) && !matches(Quality::Any, 0));

    // F03: una época sin posición o sin altura cancela, con motivo propio,
    // exija lo que se exija. Antes se saltaba y el promedio seguía.
    assert(classify(Quality::Fixed, 0, false, nan, nan, nan) == Epoch::NoPosition);
    assert(classify(Quality::Any, 0, false, nan, nan, nan) == Epoch::NoPosition);
    assert(classify(Quality::Fixed, 4, true, lat, lon, nan) == Epoch::NoPosition);
    assert(classify(Quality::Fixed, 4, true, nan, lon, 100.0) == Epoch::NoPosition);
    assert(classify(Quality::Fixed, 4, false, lat, lon, 100.0) == Epoch::NoPosition);
    // FIX → FLOAT sigue cancelando por calidad.
    assert(classify(Quality::Fixed, 5, true, lat, lon, 100.3) == Epoch::LostQuality);
    // Calidad 0 con posición (por si el receptor repite la última): también cancela.
    assert(classify(Quality::Any, 0, true, lat, lon, 100.0) == Epoch::LostQuality);
    // Época buena.
    assert(classify(Quality::Fixed, 4, true, lat, lon, 100.0) == Epoch::Accept);
    assert(classify(Quality::Any, 2, true, lat, lon, 100.0) == Epoch::Accept);

    // Mínimo de épocas: la mitad de las de 1 Hz, nunca menos de dos.
    assert(minSamples(2) == kMinSamplesFloor);
    assert(minSamples(3) == 2);
    assert(minSamples(10) == 5);
    assert(minSamples(11) == 6);
    assert(minSamples(60) == 30);
    assert(minSamples(900) == 450);

    // Cierre.
    assert(closeVerdict(1999, 2, 10, 0) == Close::Wait);
    // Sano: tiempo cumplido, muestra reciente, épocas de sobra.
    assert(closeVerdict(2000, 2, 10, 200) == Close::Apply);
    assert(closeVerdict(60000, 60, 300, 200) == Close::Apply);
    // A 1 Hz con una época perdida por suma de control sigue aplicando.
    assert(closeVerdict(60000, 60, 59, 2000) == Close::Apply);
    // La última muestra buena es vieja: cancela aunque haya muchas.
    assert(closeVerdict(2000, 2, 10, kMaxLastSampleAgeMs + 1) == Close::StaleLastSample);
    assert(closeVerdict(2000, 2, 10, kMaxLastSampleAgeMs) == Close::Apply);
    // El caso de la auditoría: una sola muestra.
    assert(closeVerdict(2000, 2, 1, 1000) == Close::TooFewSamples);
    assert(closeVerdict(2000, 2, 0, UINT32_MAX) == Close::TooFewSamples);
    assert(closeVerdict(10000, 10, 4, 1600) == Close::TooFewSamples);
    assert(closeVerdict(10000, 10, 5, 1600) == Close::Apply);

    // Los plazos de silencio son coherentes entre sí: la muestra vieja al
    // cerrar salta antes que el silencio total.
    assert(uint64_t(kMaxLastSampleAgeMs) * 1000 < kEpochStaleUs);
    return 0;
}
