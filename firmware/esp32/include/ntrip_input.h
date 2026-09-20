#pragma once
#include <ArduinoJson.h>
namespace ntrip_input {void begin();bool active();int request(const String& method,JsonVariantConst body,JsonDocument& out);void status(JsonObject out);}
