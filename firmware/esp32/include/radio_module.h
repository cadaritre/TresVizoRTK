#pragma once
#include <Arduino.h>
#include <ArduinoJson.h>
#include <cstddef>
#include <cstdint>

// El módulo de radio LoRa externo (docs/radio/RADIO_MODULE.md): un aparato aparte, con
// su propia pila, que se conecta al USB-C del equipo y es su anfitrión USB. Habla por
// el mismo CDC que la consola (docs/radio/USB_LINK.md): saludo, papel, estado,
// configuración y RTCM crudo. Si el receptor está en base, se le manda el RTCM que
// produce; si está en rover, lo que llega por el aire entra al router como fuente `radio`.
namespace radio_module {
void begin();
// Una trama RTCM completa que produjo el receptor (la llama la salida de
// correcciones). No bloquea: si no hay radio, o el radio no transmite, no hace nada.
void publish(const uint8_t* frame, size_t length);
// Hay un radio enlazado (saludo aceptado y latido en los últimos 3.5 s).
bool connected();
void status(JsonObject out);
// `/api/radio`: GET estado; POST {network?, channel?, power_dbm?} se reenvía al radio.
int request(const String& method, JsonVariantConst body, JsonDocument& out);

// Desde la tarea del canal USB (usb_channel.cpp): lo que llega y la vuelta periódica.
void onFrame(uint8_t type, const uint8_t* payload, size_t length);
void onRtcm(const uint8_t* frame, size_t length);
void service(uint32_t nowMs);
}
