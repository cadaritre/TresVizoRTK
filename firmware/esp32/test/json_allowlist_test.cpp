// g++ -std=c++17 -I lib/protocol/src -I .pio/libdeps/esp32s3_usb/ArduinoJson/src test/json_allowlist_test.cpp
#include "ble_status_keys.h"
#include "json_allowlist.h"
#include <cassert>
#include <cstdio>
#include <fstream>
#include <sstream>
#include <string>

namespace {
// Lo que manda ble_transport.cpp por BLE: la respuesta dentro de su envoltura.
size_t bleBytes(JsonVariantConst body) {
    JsonDocument output;
    output["id"] = 65535;
    output["status"] = 200;
    output["body"] = body;
    std::string text;
    serializeJson(output, text);
    return text.size();
}
}  // namespace

int main() {
    // Recorte básico: claves sueltas, objetos anidados y arreglos.
    {
        const char* const keep[] = {"firmware_version", "solution.fix", "alerts[].code", "subsystems.ble.protocol_version"};
        JsonDocument doc;
        deserializeJson(doc, R"({
            "firmware_version":"0.8.0","board":"Thing Plus",
            "solution":{"fix":4,"hdop":0.7},
            "alerts":[{"code":"a","level":"info","message":"x"},{"code":"b"}],
            "subsystems":{"ble":{"protocol_version":3,"att_mtu":247},"radio":{"state":"not_connected"}}
        })");
        protocol::keepOnly(doc.as<JsonVariant>(), keep, 4);
        std::string text;
        serializeJson(doc, text);
        assert(text == R"({"firmware_version":"0.8.0","solution":{"fix":4},"alerts":[{"code":"a"},{"code":"b"}],"subsystems":{"ble":{"protocol_version":3}}})");
    }
    // Un prefijo de clave no basta: «sol» no conserva «solution».
    {
        const char* const keep[] = {"sol"};
        JsonDocument doc;
        deserializeJson(doc, R"({"solution":{"fix":4},"sol":1})");
        protocol::keepOnly(doc.as<JsonVariant>(), keep, 1);
        std::string text;
        serializeJson(doc, text);
        assert(text == R"({"sol":1})");
    }
    // Más de 64 claves a quitar en un mismo objeto (el recorte va por tandas).
    {
        const char* const keep[] = {"k0"};
        JsonDocument doc;
        for (int i = 0; i < 200; ++i) doc[std::string("k") + std::to_string(i)] = i;
        protocol::keepOnly(doc.as<JsonVariant>(), keep, 1);
        assert(doc.as<JsonObject>().size() == 1 && doc["k0"] == 0);
    }
    // El estado completo del 0.8.0 con el radio (respuestas armadas a partir del código
    // del firmware) no cabe por BLE; recortado al contrato sí, con margen.
    {
        std::ifstream file("../../tools/api_contract/fixtures/device_0.8.0_from_source.json");
        if (!file) {
            std::puts("json_allowlist_test: sin fixture (corre desde firmware/esp32); se omite la prueba de tamaño");
        } else {
            std::stringstream buffer;
            buffer << file.rdbuf();
            JsonDocument fixtures;
            assert(!deserializeJson(fixtures, buffer.str()));
            JsonDocument status;
            status.set(fixtures["GET /api/status"]["body"]);
            const size_t full = bleBytes(status.as<JsonVariantConst>());
            protocol::keepOnly(status.as<JsonVariant>(), protocol::kBleStatusKeys, protocol::kBleStatusKeyCount);
            const size_t trimmed = bleBytes(status.as<JsonVariantConst>());
            std::printf("estado por BLE: completo %zu bytes, recortado al contrato %zu bytes (límite 4096)\n", full, trimmed);
            assert(full > 4096);          // por eso hace falta
            assert(trimmed <= 3800);      // margen para valores más largos que los del fixture
            assert(status["firmware_version"].is<const char*>());
            assert(status["subsystems"]["ble"]["protocol_version"].is<int>());
            assert(status["subsystems"]["radio"].isNull());   // no lo lee ninguna app
        }
    }
    std::puts("json_allowlist_test: OK");
    return 0;
}
