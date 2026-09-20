#pragma once

#include <Arduino.h>
#include <ArduinoJson.h>

namespace instrument {
constexpr const char* kVersion = "0.4.0";
void begin();
void tick();
int changeAccessKey(JsonVariantConst body, JsonDocument& response);
const String& accessKey();
const String& apName();
int request(const String& method, const String& path, JsonVariantConst body, JsonDocument& response);
}
