#pragma once
#include <cstdint>

// Alarma `receiver_silent` de /api/status (instrument.cpp), sin Arduino para
// probarla en la Mac (test/receiver_silence_test.cpp).
namespace receiver_silence {

// Sin ninguna GGA durante este tiempo, el receptor está mudo. Son cinco épocas
// seguidas a 1 Hz, la tasa más lenta que configuran el panel y las apps: ya no
// es una trama perdida por suma de control. Deja pasar de sobra el hueco de un
// trabajo que quita y repone salidas (el `rover`, entre su UNLOG y su GPGGA),
// que se espera de menos de un segundo; no está medido en el equipo.
constexpr uint64_t kSilentAfterUs = 5000000;

// **Depende de la antigüedad de la última GGA, no del contador acumulado.**
// Hasta 0.7.12 solo saltaba con el contador en cero, es decir, si el receptor
// no había emitido nunca desde el arranque; uno que perdía sus salidas a mitad
// de sesión seguía con el contador alto y la alarma no salía hasta reiniciar.
//
// `ggaAgeUs`: antigüedad de la última GGA aceptada, medida con el reloj
// monotónico del ESP32 desde su llegada. Con `acceptedGga` en cero no se usa.
inline bool silent(bool uartEnabled, uint32_t acceptedGga, uint64_t ggaAgeUs) {
    return uartEnabled && (acceptedGga == 0 || ggaAgeUs > kSilentAfterUs);
}
}
