#pragma once
#include <ArduinoJson.h>
namespace ntrip_input {
void begin();
bool active();
int request(const String& method,JsonVariantConst body,JsonDocument& out);
// Perfiles guardados en NVS y autoconexión al último elegido. "Ninguno" también
// se guarda: es una decisión del usuario, no la ausencia de una.
int profileRequest(const String& method,JsonVariantConst body,JsonDocument& out);
// Lista de puntos de montaje publicada por el caster. Comparte radio con el
// flujo, así que solo se resuelve con la conexión detenida.
int sourcetableRequest(const String& method,JsonVariantConst body,JsonDocument& out);
void status(JsonObject out);
}
