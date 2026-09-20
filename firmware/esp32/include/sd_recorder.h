#pragma once
#include <ArduinoJson.h>
namespace sd_recorder {
void begin();void feed(uint8_t byte);bool active();
int request(const String& method,const String& path,JsonVariantConst body,JsonDocument& out);
void status(JsonObject out);
}
