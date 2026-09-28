#pragma once
#include <cstdint>

namespace protocol {
// Ritmo y vigencia del paquete de salud (lib/protocol/src/health_packet.h), el
// mismo por BLE (a04c0006) y por el WebSocket (trama 0x02). Sin Arduino: se
// prueba en la PC (test/health_solution_test.cpp).

// La salud sale a 1 Hz **siempre** que el enlace está arriba, haya solución o
// no: es también el latido. Por eso las apps la toman por fresca en cuanto
// llega, y por eso lo que lleva tiene que caducar aquí, en el equipo.
constexpr uint32_t kHealthPeriodMs = 1000;

// Cuánto vale la última GGA para el byte 8 (calidad) y la última GST para los
// bytes 1-4 y 12-15 (precisión mostrada y cruda). Pasado esto, calidad 0 y
// precisión 0xFFFF: las dos codificaciones que el paquete ya tenía para «no hay
// solución» y «no hay estimación». Hasta 0.7.12 se copiaba lo último recibido
// sin mirar cuándo llegó, y con un receptor que dejaba de hablar la salud seguía
// diciendo FIJO y dando la última precisión, que es la que pintan las apps.
//
// **2 s, no los 500 ms con que se notifica la solución.** La GGA puede ir a
// 1 Hz (`rateFor` en gnss_control.cpp admite 1, 2 y 5 Hz) y la GST va siempre a
// 1 Hz; la salud sale con una fase cualquiera respecto a ellas, así que un
// equipo sano la arma con una GGA de hasta casi 1 s. Con 500 ms, en el banco de
// la auditoría, 49 de 100 paquetes de un equipo sano salían vencidos y la
// precisión habría parpadeado. Dos periodos de la salida más lenta aguantan
// además una sentencia perdida suelta. Es la misma ventana que usa
// `/api/status` para la GST.
constexpr uint64_t kHealthSolutionMaxAgeUs = 2000000;
constexpr uint64_t kHealthPrecisionMaxAgeUs = 2000000;

// ¿Llegó alguna vez y lo último llegó hace `maxAgeUs` o menos?
//
// - `acceptedCount` es el contador de sentencias aceptadas del parser: con 0
//   nunca llegó ninguna y la hora de llegada (0) no significa nada. Al
//   arrancar, `nowUs` es pequeño y sin esta comprobación parecería fresca.
// - Las horas son del reloj monotónico del ESP32 (esp_timer, µs) —el de quien
//   mira—, no la hora UTC de la GGA.
// - `nowUs` debe leerse **después** de tomar la instantánea. Si aun así la
//   llegada es posterior, es de hace nada: antigüedad 0, sin que la resta en
//   uint64 dé la vuelta.
inline bool arrivedWithin(uint32_t acceptedCount, uint64_t arrivalUs, uint64_t nowUs, uint64_t maxAgeUs) {
    if (!acceptedCount) return false;
    const uint64_t ageUs = nowUs > arrivalUs ? nowUs - arrivalUs : 0;
    return ageUs <= maxAgeUs;
}
}  // namespace protocol
