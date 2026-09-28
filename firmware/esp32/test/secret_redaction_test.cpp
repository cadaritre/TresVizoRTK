// Recorte de credenciales en las respuestas BLE (lib/protocol/src/secret_redaction.h).
//
// Necesita ArduinoJson, que PlatformIO deja en .pio/libdeps tras un `pio run`:
//   g++ -std=c++17 -Wall -Wextra -I lib/gnss/src -I lib/protocol/src -I include \
//       -I .pio/libdeps/esp32s3_usb/ArduinoJson/src test/secret_redaction_test.cpp
#include "secret_redaction.h"
#include <cassert>
#include <cstdio>
#include <string>

using protocol::isSecretKeyName;
using protocol::stripSecrets;

static std::string redacted(const char* json) {
    JsonDocument document;
    const DeserializationError error = deserializeJson(document, json);
    assert(!error);
    (void)error;
    stripSecrets(document.as<JsonVariant>());
    std::string out;
    serializeJson(document, out);
    return out;
}

int main() {
    // Nombres: las credenciales en claro, si o si.
    // `has_password` tambien: lo que lo salva es que su valor es booleano.
    for (const char* name : {"ap_password", "password", "wifi_password", "pass", "cpass", "psk", "secret",
                             "ntrip_password", "caster_pass", "wifi_psk", "api_secret", "has_password"})
        assert(isSecretKeyName(name));
    // Y lo que no lo es, aunque se parezca.
    for (const char* name : {"ap_password_saved", "wifi_password_saved", "credentials_persisted",
                             "passive", "password_hint_count", "ap_ssid", "session", "key", "", "compass"})
        assert(!isSecretKeyName(name));
    assert(!isSecretKeyName(nullptr));

    // GET /api/config tal como lo da el firmware (instrument.cpp, config()).
    const std::string config = redacted(
        R"({"schema_version":1,"revision":7,"device_name":"MeridianV","refresh_ms":2000,)"
        R"("wifi_ssid":"iPhone de Chuck","wifi_password_saved":true,)"
        R"("networks":[{"ssid":"iPhone de Chuck","has_password":true,"ip":"","gateway":"","mask":""}],)"
        R"("networks_max":5,"station_paused":false,"preferred_ssid":"","ap_ssid":"MeridianV",)"
        R"("ap_password":"TresVIzoRTK","persistence_ready":true,"stored_config_valid":true})");
    assert(config.find("ap_password\"") == std::string::npos);
    assert(config.find("TresVIzoRTK") == std::string::npos);
    // Lo demas, intacto y en su orden.
    assert(config ==
           R"({"schema_version":1,"revision":7,"device_name":"MeridianV","refresh_ms":2000,)"
           R"("wifi_ssid":"iPhone de Chuck","wifi_password_saved":true,)"
           R"("networks":[{"ssid":"iPhone de Chuck","has_password":true,"ip":"","gateway":"","mask":""}],)"
           R"("networks_max":5,"station_paused":false,"preferred_ssid":"","ap_ssid":"MeridianV",)"
           R"("persistence_ready":true,"stored_config_valid":true})");

    // Respuesta de guardado: el booleano se queda, la cadena se va.
    assert(redacted(R"({"saved":true,"ap_password_saved":true,"ap_password":"otra-clave-1"})") ==
           R"({"saved":true,"ap_password_saved":true})");

    // A cualquier profundidad, dentro de objetos y de arreglos, y varias
    // seguidas en el mismo objeto (quitar una no debe saltarse la siguiente).
    assert(redacted(R"({"a":{"b":[{"password":"x","pass":"y","ok":1},{"c":{"wifi_psk":"z"}}]},"secret":null})") ==
           R"({"a":{"b":[{"ok":1},{"c":{}}]}})");

    // Un secreto numerico o anidado tambien se va; solo el booleano se queda.
    assert(redacted(R"({"has_password":false,"pin_secret":1234,"ntrip_password":{"v":"x"}})") ==
           R"({"has_password":false})");

    // Nada que quitar: sin cambios. Raiz que no es objeto: sin cambios.
    assert(redacted(R"({"state":"idle","received_bytes":0})") == R"({"state":"idle","received_bytes":0})");
    assert(redacted(R"([1,"password",{"x":true}])") == R"([1,"password",{"x":true}])");
    assert(redacted(R"("password")") == R"("password")");

    // Mas hondo que el limite: el subarbol se borra, no sale sin revisar.
    std::string deep;
    for (size_t i = 0; i < protocol::kMaxRedactionDepth + 2; ++i) deep += R"({"n":)";
    deep += R"({"password":"x"})";
    for (size_t i = 0; i < protocol::kMaxRedactionDepth + 2; ++i) deep += "}";
    {
        JsonDocument document;
        const DeserializationError error =
            deserializeJson(document, deep, DeserializationOption::NestingLimit(64));
        assert(!error);
        (void)error;
        stripSecrets(document.as<JsonVariant>());
        std::string out;
        serializeJson(document, out);
        assert(out.find("password") == std::string::npos);
    }

    std::puts("secret_redaction: OK");
    return 0;
}
