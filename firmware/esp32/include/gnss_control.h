#pragma once
#include <Arduino.h>
#include <ArduinoJson.h>
namespace gnss_control {
void begin();
void feed(char byte);
void tick(HardwareSerial& uart);
bool busy();
bool roverReady();
const char* heightReference();
int start(JsonVariantConst body, JsonDocument& out);
int applyBase(JsonVariantConst plan, JsonDocument& out);
void status(JsonObject out);
}
