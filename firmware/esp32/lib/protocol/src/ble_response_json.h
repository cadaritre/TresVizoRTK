#pragma once
#include <ArduinoJson.h>

namespace protocol {
inline void boundBleResponse(JsonDocument& envelope) {
    if (measureJson(envelope) <= 4096) return;
    // Conservar id incluso en el error: las apps correlacionan por el JSON,
    // no por el identificador de las tramas de transporte.
    envelope["status"] = 413;
    envelope["body"].clear();
    envelope["body"]["error"] = "response_too_large";
}
}
