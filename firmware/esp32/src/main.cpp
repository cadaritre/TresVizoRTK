#include "sd_recorder.h"
#include "ntrip_input.h"
#include "gnss_control.h"
#include "memory_health.h"
#include <Arduino.h>
#include <ArduinoJson.h>
#include <esp_http_server.h>
#include <freertos/semphr.h>
#include "config_rules.h"
#include "instrument.h"
#include "gnss_receiver.h"
#include "ble_transport.h"
#include "firmware_update.h"
#include "web_assets.h"

namespace {
httpd_handle_t server = nullptr;
SemaphoreHandle_t instrumentMutex;
char serialBuffer[config_rules::kMaxRequestBytes + 1];
size_t serialLength = 0;
bool serialOverflow = false;
uint32_t serialStartedAt = 0;

// El instrumento dejó de pedir clave de panel por decisión del propietario:
// es un receptor GNSS de campo y la barrera estorbaba más de lo que protegía.
// La contraseña del Wi-Fi propio es la única puerta que queda. Conviene tenerlo
// presente: la carga de firmware por OTA no lleva firma.
bool authenticated(const char*) { return true; }

int dispatch(const String& method, const String& path, JsonVariantConst body, JsonDocument& response) {
    if (xSemaphoreTake(instrumentMutex, pdMS_TO_TICKS(1000)) != pdTRUE) {
        response["error"] = "busy";
        response["message"] = "El instrumento está ocupado. Intenta de nuevo.";
        return 503;
    }
    const int code = instrument::request(method, path, body, response);
    xSemaphoreGive(instrumentMutex);
    return code;
}

void headers(httpd_req_t* request) {
    httpd_resp_set_hdr(request, "Cache-Control", "no-store");
    httpd_resp_set_hdr(request, "X-Content-Type-Options", "nosniff");
    httpd_resp_set_hdr(request, "Referrer-Policy", "no-referrer");
    httpd_resp_set_hdr(request, "Content-Security-Policy", "default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self'; connect-src 'self'; frame-ancestors 'none'; base-uri 'none'; form-action 'self'");
}

esp_err_t reply(httpd_req_t* request, int code, JsonDocument& response) {
    const char* status = "500 Internal Server Error";
    switch (code) {
        case 200: status = "200 OK"; break;
        case 202: status = "202 Accepted"; break;
        case 400: status = "400 Bad Request"; break;
        case 401: status = "401 Unauthorized"; break;
        case 404: status = "404 Not Found"; break;
        case 409: status = "409 Conflict"; break;
        case 413: status = "413 Payload Too Large"; break;
        case 503: status = "503 Service Unavailable"; break;
    }
    String encoded;
    serializeJson(response, encoded);
    headers(request);
    httpd_resp_set_status(request, status);
    httpd_resp_set_type(request, "application/json; charset=utf-8");
    return httpd_resp_send(request, encoded.c_str(), encoded.length());
}

esp_err_t handleHttp(httpd_req_t* request) {
    JsonDocument response;
    // Comprobar antes de reservar memoria o leer el cuerpo de la solicitud.
    if (request->content_len > config_rules::kMaxRequestBytes) {
        response["error"] = "request_too_large";
        response["message"] = "La solicitud supera 1024 bytes.";
        reply(request, 413, response);
        return ESP_FAIL; // cerrar la conexión con datos sin consumir
    }
    if (request->method == HTTP_GET && request->content_len == 0) {
        for (const auto& asset : web_assets::all) {
            if (strcmp(request->uri, asset.path) != 0) continue;
            headers(request);
            httpd_resp_set_type(request, asset.mime);
            httpd_resp_set_hdr(request, "Content-Encoding", "gzip");
            return httpd_resp_send(request, reinterpret_cast<const char*>(asset.data), asset.size);
        }
    }
    char payload[config_rules::kMaxRequestBytes + 1];
    size_t received = 0;
    const uint32_t receiveStartedAt = millis();
    while (received < request->content_len) {
        if (config_rules::elapsed(millis(), receiveStartedAt, 5000)) return ESP_FAIL;
        const int count = httpd_req_recv(request, payload + received, request->content_len - received);
        if (count <= 0) return ESP_FAIL;
        received += count;
    }
    payload[received] = '\0';
    JsonDocument body;
    if (received && deserializeJson(body, payload, received, DeserializationOption::NestingLimit(4))) {
        response["error"] = "invalid_json";
        response["message"] = "La solicitud JSON está incompleta o no es válida.";
        return reply(request, 400, response);
    }
    const String method = request->method == HTTP_GET ? "GET" : (request->method == HTTP_PUT ? "PUT" : "POST");
    const int code = dispatch(method, request->uri, body.as<JsonVariantConst>(), response);
    return reply(request, code, response);
}

void serialReply(JsonDocument& response) {
    serializeJson(response, Serial);
    Serial.println();
}

void handleSerialLine() {
    JsonDocument input;
    JsonDocument output;
    const auto parsed = deserializeJson(input, serialBuffer, serialLength, DeserializationOption::NestingLimit(5));
    if (parsed || !input.is<JsonObject>()) {
        output["status"] = 400;
        output["body"]["error"] = "invalid_json";
        serialReply(output);
        return;
    }
    if (!input["id"].is<uint32_t>()) {
        output["status"] = 400;
        output["body"]["error"] = "invalid_id";
        serialReply(output);
        return;
    }
    output["id"] = input["id"];
    // Recuperación por acceso físico USB; esta ruta no existe por HTTP.
    if (input["method"] == "GET" && input["path"] == "/api/access") {
        output["status"] = 200;
        output["body"]["ap_ssid"] = instrument::apName();
        // Única credencial del equipo: la del Wi-Fi propio. El panel y la API no
        // piden clave. El PIN de BLE es aparte y lo exige el emparejamiento.
        output["body"]["ap_password"] = instrument::apPassword();
        output["body"]["ble_pairing_pin"] = ble_transport::passkey();
        output["body"]["ap_url"] = "http://192.168.4.1";
        serialReply(output);
        return;
    }
    JsonDocument body;
    output["status"] = dispatch(input["method"] | "", input["path"] | "", input["body"].as<JsonVariantConst>(), body);
    output["body"] = body;
    serialReply(output);
}

void pollSerial() {
    // Cuota por ciclo: una entrada continua no monopoliza el controlador.
    for (size_t count = 0; count < 256 && Serial.available(); ++count) {
        const char c = Serial.read();
        if (!serialLength && !serialOverflow) serialStartedAt = millis();
        if (c == '\n') {
            if (serialOverflow) Serial.println("{\"status\":413,\"body\":{\"error\":\"request_too_large\"}}");
            else if (serialLength) {
                serialBuffer[serialLength] = '\0';
                handleSerialLine();
            }
            serialLength = 0;
            serialOverflow = false;
        } else if (c != '\r') {
            if (serialLength < config_rules::kMaxRequestBytes && !serialOverflow) serialBuffer[serialLength++] = c;
            else serialOverflow = true;
        }
    }
    if ((serialLength || serialOverflow) && config_rules::elapsed(millis(), serialStartedAt, 5000)) {
        serialLength = 0;
        serialOverflow = false;
        Serial.println("{\"status\":408,\"body\":{\"error\":\"request_timeout\"}}");
    }
}
}

void setup() {
    Serial.setRxBufferSize(2048);
    Serial.begin(115200);
    Serial.setTxTimeoutMs(50);
    instrumentMutex = xSemaphoreCreateMutex();
    if (!instrumentMutex) {
        Serial.println("Error: no se pudo crear el bloqueo del instrumento.");
        return;
    }
    memory_health::begin();
    gnss_control::begin();
    instrument::begin();
    sd_recorder::begin();
    gnss_receiver::begin();
    ntrip_input::begin();
    ble_transport::begin(dispatch, authenticated);
    httpd_config_t configuration = HTTPD_DEFAULT_CONFIG();
    configuration.uri_match_fn = httpd_uri_match_wildcard;
    configuration.stack_size = 8192;
    configuration.max_open_sockets = 4;
    configuration.lru_purge_enable = true;
    configuration.recv_wait_timeout = 2;
    configuration.send_wait_timeout = 2;
    if (httpd_start(&server, &configuration) == ESP_OK) {
        for (const httpd_method_t method : {HTTP_GET, HTTP_PUT, HTTP_POST}) {
            httpd_uri_t route = {};
            route.uri = "/*";
            route.method = method;
            route.handler = handleHttp;
            if (httpd_register_uri_handler(server, &route) != ESP_OK) Serial.println("Error al registrar ruta HTTP.");
        }
    } else Serial.println("Error al iniciar el servidor web. Consola USB disponible.");
    Serial.printf("TresVizo RTK %s. Consola JSON USB disponible.\n", instrument::kVersion);
}

void loop() {
    if (instrumentMutex) {
        pollSerial();
        ble_transport::tick();
        if (xSemaphoreTake(instrumentMutex, pdMS_TO_TICKS(10)) == pdTRUE) {
            instrument::tick();
            firmware_update::tick(server != nullptr);
            xSemaphoreGive(instrumentMutex);
        }
    }
    delay(2);
}
