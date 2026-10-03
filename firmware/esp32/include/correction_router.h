#pragma once
#include <ArduinoJson.h>
#include <cstddef>
#include <cstdint>
namespace correction_router {
enum class Source : uint8_t { None, Ble, Ntrip, Radio };
bool select(const char* source);
// La fuente que **eligió el usuario**, guardada en NVS para que sobreviva a un
// reinicio. `select` cambia la selección del momento, y la cambian también el
// modo base, una red caída o detener NTRIP; eso no es cambiar de elección.
//
// Hasta 0.7.3 no se guardaba nada: quien elegía BLE y reiniciaba volvía a NTRIP,
// porque la autoconexión del perfil lo seleccionaba al arrancar.
void begin();                      // lee la elección y, si era BLE, la aplica
bool choose(const char* source);   // elección explícita: selecciona y guarda
bool bleChosen();                  // la última elección explícita fue BLE
bool radioChosen();                // la última elección explícita fue el radio
// Un módulo de radio se conectó como rover: si el usuario eligió el radio, o no
// eligió nada y no hay otra fuente activa, se selecciona sin guardarlo como elección.
void adoptRadio();
bool submit(Source source, const uint8_t* frame, size_t length);
void status(JsonObject out);
uint32_t generation();
// Milisegundos desde la última trama aceptada, o UINT32_MAX si no hay fuente
// seleccionada o todavía no ha llegado ninguna. Es el dato que dice si el
// equipo sigue corregido: contar tramas no distingue "van bien" de "se cortó".
uint32_t ageMs();
// Fuente activa como número, para el paquete BLE: 0 ninguna, 1 BLE, 2 NTRIP, 3 radio.
uint8_t sourceCode();
// Tramas rechazadas al entrar (fuente no seleccionada, formato, CRC o sin UART),
// de todas las fuentes. Para el byte 18 del paquete de salud.
uint32_t rejectedFrames();
}
