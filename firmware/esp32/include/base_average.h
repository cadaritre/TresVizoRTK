#pragma once
#include <cmath>
#include <cstdint>

// Reglas del promedio de base que hace el ESP32 (base_survey.cpp), sin Arduino
// para poder probarlas en la Mac (test/base_average_test.cpp).
//
// Qué se decide aquí: si una época entra en la media, si hay que cancelar, y si
// al cumplirse el tiempo la media se puede declarar. Lo que no se decide aquí
// es qué hacer con la coordenada: eso es base_plan.h.
namespace base_average {

// Calidad mínima exigida a cada época. Los códigos son los de GGA.
enum class Quality : uint8_t { Any = 0, Single = 1, Float = 5, Fixed = 4 };

inline bool matches(Quality required, unsigned ggaQuality) {
    switch (required) {
        case Quality::Fixed: return ggaQuality == 4;
        case Quality::Float: return ggaQuality == 5;
        case Quality::Single: return ggaQuality == 1;
        default: return ggaQuality != 0;
    }
}

// Qué hacer con una época GGA nueva.
enum class Epoch : uint8_t {
    Accept,       // entra en la media
    NoPosition,   // sin posición o sin altura: se cancela
    LostQuality,  // con posición, pero por debajo de lo exigido: se cancela
};

// **Una época sin posición es una pérdida de solución**, no una época que se
// salta. Hasta 0.7.12 se saltaba: una GGA de calidad 0 marcaba la época como
// vista y salía antes de comparar la calidad, y al cumplirse el tiempo la base
// se declaraba con las muestras de antes del corte (visto con una sola).
inline Epoch classify(Quality required, unsigned ggaQuality, bool hasPosition,
                      double latitudeDeg, double longitudeDeg, double altitudeMslM) {
    if (!hasPosition || !std::isfinite(latitudeDeg) || !std::isfinite(longitudeDeg) ||
        !std::isfinite(altitudeMslM)) return Epoch::NoPosition;
    if (!matches(required, ggaQuality)) return Epoch::LostQuality;
    return Epoch::Accept;
}

// Sin ninguna GGA durante este tiempo se considera que el receptor dejó de
// entregar posiciones. Tres épocas seguidas a 1 Hz, la tasa más lenta que
// configuran el panel y las apps.
constexpr uint64_t kEpochStaleUs = 3000000;
// Tras arrancar el promedio se espera esto antes de cancelar por silencio: da
// tiempo a que llegue la primera época aunque el arranque coincida con un hueco.
constexpr uint32_t kSilenceGraceMs = 5000;

// Tasa de GGA más lenta que configuran el panel y las apps (1 Hz; ver `rateFor`
// y `kMaxOutputRateHz` en gnss_control.cpp). Las reglas de cierre se calculan
// para ella: lo que se cumple a 1 Hz se cumple de sobra a 2 y a 5 Hz.
constexpr uint32_t kSlowestGgaRateHz = 1;

// Antigüedad máxima de la última época aceptada al cerrar. A 1 Hz, perder una
// época por suma de control (se han visto descartes del 13 % de las GGA) deja
// un hueco de 2 s; se añade medio segundo de holgura de llegada por la UART.
// Si la última muestra buena es más vieja, algo pasó al final del promedio y
// no se vio: la media no describe los últimos segundos.
constexpr uint32_t kMaxLastSampleAgeMs = 2500;

// Una sola época no es un promedio.
constexpr uint32_t kMinSamplesFloor = 2;
// De las épocas que daría la tasa más lenta en el tiempo pedido, al menos una
// de cada dos tiene que haber entrado. Admite perder la mitad por suma de
// control o por huecos cortos; más que eso, el tiempo pedido no está cubierto.
constexpr uint32_t kMinCoverageDivisor = 2;

inline uint32_t minSamples(uint32_t seconds) {
    const uint32_t expected = seconds * kSlowestGgaRateHz;
    const uint32_t half = (expected + kMinCoverageDivisor - 1) / kMinCoverageDivisor;
    return half > kMinSamplesFloor ? half : kMinSamplesFloor;
}

// Qué hacer cuando no hay época nueva: seguir, declarar la media o cancelar.
enum class Close : uint8_t {
    Wait,            // no se ha cumplido el tiempo
    Apply,           // se declara la media
    StaleLastSample, // la última muestra buena es demasiado vieja
    TooFewSamples,   // no hay épocas suficientes para el tiempo pedido
};

// `lastSampleAgeMs` se mide con el reloj monotónico del ESP32 desde la llegada
// de la última época aceptada; sin muestras no significa nada.
inline Close closeVerdict(uint32_t elapsedMs, uint32_t wantedSeconds, uint32_t samples,
                          uint32_t lastSampleAgeMs) {
    if (elapsedMs < wantedSeconds * 1000UL) return Close::Wait;
    if (samples == 0) return Close::TooFewSamples;
    if (lastSampleAgeMs > kMaxLastSampleAgeMs) return Close::StaleLastSample;
    if (samples < minSamples(wantedSeconds)) return Close::TooFewSamples;
    return Close::Apply;
}
}
