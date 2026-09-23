#pragma once
#include <ArduinoJson.h>
#include <cstddef>
#include <cstdint>

// Salida de correcciones: lo que el equipo distribuye cuando trabaja como base.
// Dos destinos sobre el mismo flujo RTCM que emite el receptor por la UART:
//   - publicación hacia un caster externo (el equipo es cliente "source")
//   - caster propio en la red del equipo (el equipo atiende a los rovers)
// Son independientes y pueden estar activos a la vez.
namespace correction_output {
void begin();
// Entrega una trama RTCM completa recibida DEL receptor. La llama la tarea de
// adquisición; no bloquea y descarta si el destino va lento.
void publish(const uint8_t* frame, size_t length);
// ¿Hay algún destino activo? Otras operaciones lo consultan antes de tocar el
// receptor, igual que se hace con la entrada NTRIP.
bool active();
void status(JsonObject out);
int serverRequest(const String& method, JsonVariantConst body, JsonDocument& out);
int casterRequest(const String& method, JsonVariantConst body, JsonDocument& out);
}
