#pragma once
#include <Arduino.h>
#include <ArduinoJson.h>
#include <cstddef>
#include <cstdint>

// El módulo de radio LoRa externo (docs/radio/RADIO_MODULE.md): un aparato aparte
// con su propio ESP32 que se une a la red Wi-Fi del equipo y abre TCP al puerto
// radio_link::kPort. Si el receptor está en base, se le manda el RTCM que produce;
// si está en rover, lo que llega por el aire entra al router como fuente `radio`.
namespace radio_module {
void begin();
// Una trama RTCM completa que produjo el receptor (la llama la salida de
// correcciones). No bloquea: si no hay radio, o el radio no transmite, no hace nada.
void publish(const uint8_t* frame, size_t length);
bool connected();
void status(JsonObject out);
// `/api/radio`: GET estado; POST {network?, channel?, power_dbm?} se reenvía al radio.
int request(const String& method, JsonVariantConst body, JsonDocument& out);
}
