#pragma once

#include <Arduino.h>
#include <ArduinoJson.h>

namespace instrument {
constexpr const char* kVersion = "0.1.0";
void begin();
void tick();
const String& accessKey();
const String& apName();
int request(const String& method, const String& path, JsonVariantConst body, JsonDocument& response);
}
