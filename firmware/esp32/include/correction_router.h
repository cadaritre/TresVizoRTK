#pragma once
#include <ArduinoJson.h>
#include <cstddef>
#include <cstdint>
namespace correction_router {
enum class Source : uint8_t { None, Ble, Ntrip, Radio };
bool select(const char* source);
bool submit(Source source, const uint8_t* frame, size_t length);
void status(JsonObject out);
uint32_t generation();
// Milisegundos desde la última trama aceptada, o UINT32_MAX si no hay fuente
// seleccionada o todavía no ha llegado ninguna. Es el dato que dice si el
// equipo sigue corregido: contar tramas no distingue "van bien" de "se cortó".
uint32_t ageMs();
// Fuente activa como número, para el paquete BLE: 0 ninguna, 1 BLE, 2 NTRIP, 3 radio.
uint8_t sourceCode();
}
