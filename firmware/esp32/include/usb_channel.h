#pragma once
#include <Arduino.h>
#include <cstddef>
#include <cstdint>

// El USB-C del equipo como canal único (docs/radio/USB_LINK.md §3): por el mismo CDC
// llegan las órdenes JSON de siempre (de una computadora) y, si lo conectado es el
// radio LoRa externo, sus tramas del enlace y el RTCM crudo. Una tarea lee el CDC y lo
// separa con radio_usb::Demux; todo lo que sale por el USB pasa por `write`.
namespace usb_channel {
// Arranca la tarea que lee el CDC (Serial ya iniciado). Antes de esto se escribe
// directo: el arranque no tiene con quién competir.
bool begin();
// Escribe entero, de una vez y bajo un cerrojo común: una respuesta JSON, un aviso,
// una trama del enlace o una RTCM nunca sale partida ni mezclada con otra.
bool write(const uint8_t* data, size_t length);
bool writeLine(const String& text);   // añade '\n'
// La orden que llegó por el USB, para el bucle principal: la copia en `out` (con su
// NUL) y devuelve su longitud, o 0 si no hay. Mientras espera, la tarea no lee más (la
// consola va de una en una, como siempre).
size_t takeLine(char* out, size_t capacity);
// Tramas binarias rechazadas en el USB (CRC malo, caducadas o abandonadas).
uint32_t errors();
}
