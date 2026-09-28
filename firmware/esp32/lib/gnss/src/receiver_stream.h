#pragma once
#include <cstddef>
#include <cstdint>
#include "rtcm3.h"
#include "wire_filter.h"

namespace gnss {
// Reparte los bytes que llegan del UM980 por la UART. Por COM2 salen mezclados
// tres formatos: texto NMEA, binario Unicore (OBSVMB y efemérides para PPK) y,
// cuando el receptor trabaja como base, RTCM3.
//
// **El RTCM se reconstruye con el byte crudo, antes del filtro de binario.**
// Hasta 0.7.12 se reconstruía con lo que `WireFilter` dejaba pasar como texto, y
// el filtro retiene todo 0xAA por si abre una cabecera Unicore (AA 44 B5) y lo
// tira si no la abre. Una trama RTCM se perdía entera en cuanto llevaba un 0xAA
// en la carga o en el CRC: 1 − (255/256)^L, cerca del 45 % de las MSM de 150
// bytes y del 90 % de las de 600. Solo lo sufría lo que produce la base (caster
// local y publicación, `correction_output::publish`); las correcciones que
// entran al rover van por otro camino.
//
// Con el byte crudo, el parser de RTCM ve también el texto y el binario Unicore,
// y no pasa nada: una trama solo sale si cuadra su CRC24Q, y ante una cabecera
// falsa se resincroniza en el siguiente 0xD3 que ya tiene guardado. Lo que sí
// puede pasar es un **retraso**: un 0xD3 dentro del binario Unicore con una
// longitud plausible detrás hace esperar al parser hasta completarla, así que una
// trama real puede salir hasta 1029 bytes después de empezar (≈ 90 ms a 115200
// baudios). No se pierde. El texto que reciben los parsers NMEA es exactamente
// el de antes: el filtro no cambia.
//
// Sin Arduino: se prueba en la PC (test/receiver_stream_test.cpp).
class ReceiverStream {
public:
    WireFilter filter;  // aparta el binario Unicore de los parsers de texto
    Rtcm3Parser rtcm;   // tramas RTCM3 que emite el receptor como base

    template<class RtcmConsumer, class TextConsumer>
    void feed(uint8_t byte, uint32_t nowMs, RtcmConsumer rtcmFrame, TextConsumer text) {
        rtcm.feed(byte, rtcmFrame);
        filter.feed(byte, nowMs, text);
    }
};
}  // namespace gnss
