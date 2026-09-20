#pragma once
#include <Arduino.h>
#include <ArduinoJson.h>
namespace firmware_update {
int request(const String& method, const String& path, JsonVariantConst body, JsonDocument& response);
void tick(bool servicesReady);
bool busy();
}
