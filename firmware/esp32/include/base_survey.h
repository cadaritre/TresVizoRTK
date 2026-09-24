#pragma once
#include <ArduinoJson.h>

// Promedio de coordenadas hecho en el ESP32, no en el receptor. El UM980 sabe
// promediar solo ("MODE BASE ... TIME"), pero no distingue con qué calidad de
// solución lo hace ni avisa si esa calidad se pierde a mitad. Promediar cien
// épocas autónomas da una coordenada muy repetible y igual de equivocada.
namespace base_survey {
void begin();
// Consume una época nueva si cumple la calidad exigida; la llama el bucle.
void tick();
bool active();
// start: segundos y calidad mínima. cancel: aborta. GET: estado y progreso.
int request(const String& method, JsonVariantConst body, JsonDocument& out);
void status(JsonObject out);
}
