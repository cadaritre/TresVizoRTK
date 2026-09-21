#pragma once
#include <ArduinoJson.h>
namespace sd_recorder {
void begin();
// Se alimenta por bloques desde la tarea UART: un xStreamBufferSend por byte
// costaba una llamada al kernel por cada byte recibido.
void feed(const uint8_t* data, size_t length);
bool active();
int request(const String& method,const String& path,JsonVariantConst body,JsonDocument& out);
void status(JsonObject out);
}
