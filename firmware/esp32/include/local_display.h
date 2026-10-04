#pragma once
#include <ArduinoJson.h>
namespace local_display {
void begin();
void servicesReady();
// No bloquea: confirma que la tarea dueña de I2C apagó la OLED, o vence a 300 ms.
bool prepareRestart();
void status(JsonObject out);
}
