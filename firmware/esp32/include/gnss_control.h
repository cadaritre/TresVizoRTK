#pragma once
#include <Arduino.h>
#include <ArduinoJson.h>
namespace gnss_control {
void begin();
// Consume un bloque completo con una sola toma del mutex. Antes se tomaba y
// soltaba el semaforo una vez por byte desde la tarea UART.
void feed(const char* data, size_t length);
void tick(HardwareSerial& uart);
bool busy();
bool roverReady();
// El receptor trabaja como base. Un equipo base no consume correcciones: las
// produce. Sin esta distincion el panel puede decir a la vez que es base y
// que esta recibiendo correcciones, que no tiene sentido.
bool isBase();
const char* heightReference();
int start(JsonVariantConst body, JsonDocument& out);
int applyBase(JsonVariantConst plan, JsonDocument& out);
void status(JsonObject out);
// Ultima configuracion avanzada aplicada y leida del receptor. Refleja lo que
// este firmware envio o leyo, no una lectura continua del UM980.
void profile(JsonObject out);
}
