#pragma once
#include <algorithm>
#include <cstddef>
#include <cstdint>
#include <cstring>

namespace protocol {
// Tramas de respuesta por BLE (caracteristica a04c0003).
//
// Cada notificacion lleva una cabecera de cinco bytes -identificador de
// mensaje, desplazamiento y banderas- y un trozo del JSON. Cuanto JSON cabe
// depende del MTU ATT negociado con el telefono: sin negociar son 23 bytes y
// quedan 15 de JSON; con 247 quedan 239. Una respuesta de 2 kB pasa de 134
// tramas a 9 (hueco G5).
//
// La app reensambla por desplazamiento, no por tamano de trama, asi que los dos
// tamanos conviven: un cliente que no negocia sigue recibiendo tramas de 20.
//
// Sin Arduino a proposito: se prueba con g++ en test/ble_frames_test.cpp.
constexpr size_t kResponseHeaderBytes = 5;
constexpr size_t kAttHeaderBytes = 3;
// El MTU ATT minimo que exige el estandar, y el que rige hasta que se negocia.
constexpr uint16_t kMinimumAttMtu = 23;
// El MTU que ofrece el equipo. 247 deja notificaciones de 244 bytes, que con
// extension de longitud de datos caben en un solo paquete del enlace
// (251 - 4 de L2CAP - 3 de ATT). Mas grande solo partiria cada notificacion en
// varios paquetes, sin ganar caudal.
constexpr uint16_t kPreferredAttMtu = 247;
constexpr size_t kMaxNotificationBytes = kPreferredAttMtu - kAttHeaderBytes;
constexpr size_t kMaxResponsePayloadBytes = kMaxNotificationBytes - kResponseHeaderBytes;

// Bytes de JSON por trama con el MTU negociado. Nunca menos que sin negociar
// ni mas de lo que ofrece el equipo. C++11: el firmware compila con gnu++11.
constexpr size_t responsePayloadBytes(uint16_t negotiatedMtu) {
    return (negotiatedMtu < kMinimumAttMtu ? kMinimumAttMtu
            : negotiatedMtu > kPreferredAttMtu ? kPreferredAttMtu : negotiatedMtu)
           - kAttHeaderBytes - kResponseHeaderBytes;
}

// Escribe en `frame` la trama del mensaje que empieza en `offset` y devuelve
// su longitud. `frame` tiene que tener sitio para kMaxNotificationBytes.
// Los desplazamientos van en 16 bits: el mensaje no pasa de 4096 bytes.
inline size_t encodeResponseFrame(uint8_t* frame, uint16_t messageId, size_t offset,
                                  const char* json, size_t total, size_t payloadBytes) {
    const size_t count = offset < total ? std::min(payloadBytes, total - offset) : 0;
    frame[0] = uint8_t(messageId); frame[1] = uint8_t(messageId >> 8);
    frame[2] = uint8_t(offset); frame[3] = uint8_t(offset >> 8);
    frame[4] = uint8_t((offset == 0 ? 1 : 0) | (offset + count == total ? 2 : 0));
    if (count) std::memcpy(frame + kResponseHeaderBytes, json + offset, count);
    return kResponseHeaderBytes + count;
}
}
