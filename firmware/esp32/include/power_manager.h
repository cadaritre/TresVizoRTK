#pragma once
#include <ArduinoJson.h>
namespace power_manager {
void begin();
void tick(); // Bajo el mutex del instrumento.
void sampleGauge(); // Exclusivamente desde la tarea dueña de Wire.
void status(JsonObject out);
bool pending();
bool requestShutdown();
}
