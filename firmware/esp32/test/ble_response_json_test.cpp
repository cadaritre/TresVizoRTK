#include "ble_response_json.h"
#include <cassert>
#include <string>
#include <cstdio>

int main() {
    JsonDocument envelope;
    envelope["id"] = UINT32_MAX;
    envelope["status"] = 200;
    envelope["body"]["text"] = "";
    const size_t overhead = measureJson(envelope);
    envelope["body"]["text"] = std::string(4096 - overhead, 'x');
    assert(measureJson(envelope) == 4096);
    protocol::boundBleResponse(envelope);
    assert(envelope["status"] == 200);
    envelope["body"]["text"] = std::string(4097 - overhead, 'x');
    protocol::boundBleResponse(envelope);
    assert(envelope["id"].as<uint32_t>() == UINT32_MAX);
    assert(envelope["status"] == 413);
    assert(envelope["body"]["error"] == "response_too_large");
    assert(envelope["body"].size() == 1 && measureJson(envelope) < 100);
    // El límite se mide en bytes JSON, incluidos escapes, no caracteres.
    envelope["body"]["text"] = std::string(2100, '\n');
    protocol::boundBleResponse(envelope);
    assert(envelope["id"].as<uint32_t>() == UINT32_MAX);
    assert(envelope["body"].size() == 1);
    puts("ble_response_json: OK");
}
