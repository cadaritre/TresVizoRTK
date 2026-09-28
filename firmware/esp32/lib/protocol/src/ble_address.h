#pragma once
#include <cstddef>
#include <cstdint>

namespace protocol {
// Direccion con la que se anuncia el equipo por BLE, atada a la tabla GATT.
//
// **Por que.** Sin emparejamiento, el telefono guarda la tabla GATT (servicios,
// caracteristicas y sus propiedades) por direccion y no se entera de que cambio:
// el aviso de «servicios cambiados» solo se garantiza a clientes emparejados.
// Medido el 27-09-2026: una Mac que se habia conectado a 0.7.10 seguia viendo con
// 0.7.11 cuatro caracteristicas (sin la de salud) y la de RTCM solo con
// respuesta. Anunciado con otra direccion, la misma Mac vio las cinco al
// instante. Emparejar lo arreglaria, pero en campo cada recarga del firmware o
// borrado de la NVS rompe el emparejamiento y obliga a olvidarlo en los ajustes
// del telefono (decision del propietario, 28-09-2026: direccion por tabla).
//
// **Regla.** Toda modificacion de la tabla GATT (caracteristica anadida o
// quitada, propiedades o descriptores cambiados) sube kGattTableGeneration. El
// equipo pasa a anunciarse con otra direccion, cada telefono lo ve como un
// equipo nuevo y lee la tabla desde cero. El costo: tras una actualizacion que
// cambie la tabla, el equipo se conecta una vez desde «Cerca».
//
// Historial:
//   (publica)  hasta 0.7.11: la direccion Bluetooth publica del chip.
//   1          0.7.12: la tabla de 0.7.11 (cinco caracteristicas; a04c0005 con
//              y sin respuesta; a04c0006 salud).
constexpr uint8_t kGattTableGeneration = 1;

constexpr size_t kBleAddressBytes = 6;

// Direccion aleatoria estatica (Core 5.x, Vol 6, Parte B, 1.3.2.1): los dos bits
// altos del byte mas significativo a 1, y la parte aleatoria ni todo ceros ni
// todo unos. En ESP-IDF el byte 0 de esp_bd_addr_t es el mas significativo.
constexpr uint8_t kStaticRandomMarker = 0xC0;
constexpr uint8_t kStaticRandomPayloadMask = 0x3F;

// La direccion del equipo para una generacion de la tabla.
//
// Los bytes 3-5 son los del chip (la parte propia de cada ESP32), asi que dos
// equipos no chocan aunque tengan generaciones distintas. La generacion va en
// los bytes del fabricante, que son iguales en todos los equipos: 1..63 dan
// direcciones distintas sin tocar lo que distingue a un equipo de otro.
// `chip` es la direccion Bluetooth publica (esp_read_mac con ESP_MAC_BT).
inline void advertisedAddress(const uint8_t chip[kBleAddressBytes], uint8_t generation,
                              uint8_t out[kBleAddressBytes]) {
    for (size_t i = 0; i < kBleAddressBytes; ++i) out[i] = chip[i];
    out[0] = kStaticRandomMarker | ((chip[0] ^ generation) & kStaticRandomPayloadMask);
    // Nunca la parte aleatoria toda a unos o toda a ceros, que el estandar
    // prohibe: con una direccion de chip real no pasa, pero no se supone.
    bool allOnes = (out[0] & kStaticRandomPayloadMask) == kStaticRandomPayloadMask;
    bool allZeros = (out[0] & kStaticRandomPayloadMask) == 0;
    for (size_t i = 1; i < kBleAddressBytes; ++i) {
        allOnes = allOnes && out[i] == 0xFF;
        allZeros = allZeros && out[i] == 0x00;
    }
    if (allOnes || allZeros) out[kBleAddressBytes - 1] ^= 0x01;
}
}  // namespace protocol
