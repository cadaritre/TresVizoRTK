#pragma once
#include <ArduinoJson.h>
namespace local_display {
void begin();
void status(JsonObject out);
}
