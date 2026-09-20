#pragma once
#include <Arduino.h>
#include <ArduinoJson.h>
namespace ble_transport {
using Dispatch = int (*)(const String&, const String&, JsonVariantConst, JsonDocument&);
using Authenticate = bool (*)(const char*);
void begin(Dispatch dispatch, Authenticate authenticate);
void tick();
void status(JsonObject out);
uint32_t passkey(); // Solo recuperación física USB; nunca HTTP ni publicidad.
}
