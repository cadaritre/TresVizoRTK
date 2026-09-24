#pragma once
#include <Arduino.h>
#include <ArduinoJson.h>
namespace ble_transport {
using Dispatch = int (*)(const String&, const String&, JsonVariantConst, JsonDocument&);
using Authenticate = bool (*)(const char*);
void begin(Dispatch dispatch, Authenticate authenticate);
void tick();
void status(JsonObject out);
// Encendido/apagado del transporte, persistido en NVS. El emparejamiento y el
// PIN se retiraron por decisión del propietario: la app de campo se conecta sin
// pasos previos y la única barrera es el alcance de la radio.
int request(const String& method, JsonVariantConst body, JsonDocument& out);
}
