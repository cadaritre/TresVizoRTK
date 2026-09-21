#pragma once

#include <Arduino.h>
#include <ArduinoJson.h>

namespace instrument {
constexpr const char* kVersion = "0.6.0";
void begin();
void tick();
int changeAccessKey(JsonVariantConst body, JsonDocument& response);
const String& accessKey();
// Contraseña de la red Wi-Fi propia. Desde 0.6.0 es distinta de la clave de
// API: unirse al AP ya no entrega el control del instrumento.
const String& apPassword();
const String& apName();
int request(const String& method, const String& path, JsonVariantConst body, JsonDocument& response);
}
