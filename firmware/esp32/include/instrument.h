#pragma once

#include <Arduino.h>
#include <ArduinoJson.h>

namespace instrument {
constexpr const char* kVersion = "0.7.0";
void begin();
void tick();
// Contraseña de la red Wi-Fi propia. Es la única credencial del equipo: el
// panel y la API no piden clave. Sale de fábrica con un valor conocido y
// tecleable, y se cambia desde Configuración.
const String& apPassword();
const String& apName();
// ¿Hay una red externa configurada? NTRIP por Wi-Fi no puede salir sin ella.
// Se consulta desde la tarea NTRIP, así que no expone la cadena del SSID.
bool stationConfigured();
int request(const String& method, const String& path, JsonVariantConst body, JsonDocument& response);
}
