#pragma once
#include <ArduinoJson.h>
#include <cstddef>
#include <cstdint>
namespace correction_router {
enum class Source : uint8_t { None, Ble, Ntrip, Radio };
bool select(const char* source);
bool submit(Source source, const uint8_t* frame, size_t length);
void status(JsonObject out);
uint32_t generation();
}
