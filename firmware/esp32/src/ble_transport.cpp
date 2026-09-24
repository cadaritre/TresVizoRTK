#include "ble_transport.h"
#include "instrument.h"
#include "gnss_receiver.h"
#include "rtcm3.h"
#include "correction_router.h"
#include "correction_output.h"
#include <BLEDevice.h>
#include <BLEServer.h>
#include <BLE2902.h>
#include <esp_timer.h>
#include <atomic>
#include <Preferences.h>

namespace ble_transport {
namespace {
constexpr char serviceId[] = "a04c0001-8f24-4adb-a350-77ef6339c320";
constexpr char commandId[] = "a04c0002-8f24-4adb-a350-77ef6339c320";
constexpr char responseId[] = "a04c0003-8f24-4adb-a350-77ef6339c320";
constexpr char correctionId[] = "a04c0005-8f24-4adb-a350-77ef6339c320";
constexpr char solutionId[] = "a04c0004-8f24-4adb-a350-77ef6339c320";
constexpr char healthId[] = "a04c0006-8f24-4adb-a350-77ef6339c320";
struct Request { uint32_t generation, arrival; char json[1025]; };
QueueHandle_t requests = nullptr;
Dispatch dispatchRequest;
Authenticate authenticateRequest;
BLECharacteristic *responses = nullptr, *solutions = nullptr, *health = nullptr;
BLEServer* server = nullptr;
std::atomic<bool> connected{false}, authorized{false}, advertise{false};
// Interruptor del transporte. Se persiste: apagar la radio debe seguir apagada
// después de un corte de corriente, no volver sola en la siguiente jornada.
std::atomic<bool> enabled{true};
std::atomic<uint32_t> generation{0}, dropped{0}, correctionAccepted{0}, correctionRejected{0}, correctionDropped{0};
bool ready = false;
Preferences settings;
String pending;
size_t offset = 0;
uint16_t messageId = 0, sampleSequence = 0;
uint32_t lastSend = 0, lastEpoch = UINT32_MAX, lastSample = 0, lastHealth = 0;
uint32_t responseGeneration = 0;

class ConnectionCallbacks : public BLEServerCallbacks {
    void onConnect(BLEServer*, esp_ble_gatts_cb_param_t* parameters) override {
        // Sin emparejamiento: quien se conecta queda autorizado. La única
        // barrera que queda es el alcance de la radio.
        (void)parameters;
        ++generation; connected = true; authorized = true;
    }
    void onDisconnect(BLEServer*) override {
        ++generation; connected = false; authorized = false;
        // Solo volver a anunciarse si el transporte sigue habilitado.
        advertise = enabled.load();
    }
};
class CommandCallbacks : public BLECharacteristicCallbacks {
    char buffer[1025] = {};
    size_t length = 0;
    bool overflow = false;
    uint32_t started = 0, seenGeneration = 0;
    void onWrite(BLECharacteristic* characteristic) override {
        if (!enabled) return;
        const uint32_t currentGeneration = generation.load();
        if (seenGeneration != currentGeneration || (length && millis() - started > 5000)) {
            length = 0; overflow = false; seenGeneration = currentGeneration;
        }
        const std::string data = characteristic->getValue();
        for (const char byte : data) {
            if (!length && !overflow) started = millis();
            if (byte == '\n') {
                if (!overflow && length) {
                    Request request = {};
                    request.generation = currentGeneration; request.arrival = millis();
                    memcpy(request.json, buffer, length);
                    if (xQueueSend(requests, &request, 0) != pdTRUE) ++dropped;
                } else ++dropped;
                length = 0; overflow = false;
            } else if (byte != '\r') {
                if (length < 1024 && !overflow) buffer[length++] = byte;
                else overflow = true;
            }
        }
    }
};
class CorrectionCallbacks : public BLECharacteristicCallbacks {
    gnss::Rtcm3Parser parser;
    uint32_t seenGeneration = 0, lastByte = 0, sourceGeneration = 0;
    void onWrite(BLECharacteristic* characteristic) override {
        // El teléfono actúa de puente: recibe RTCM de un caster por datos
        // móviles y lo escribe aquí cuando el equipo no tiene red propia.
        // Sin emparejamiento, cualquiera dentro del alcance puede escribir:
        // al menos no se admite mientras el equipo trabaja como base, donde
        // recibir correcciones ajenas no tiene ningún sentido legítimo.
        if (!enabled || !authorized || correction_output::active()) return;
        if (seenGeneration != generation.load() || sourceGeneration != correction_router::generation() || millis() - lastByte > 2000) parser.reset();
        sourceGeneration = correction_router::generation();
        seenGeneration = generation.load(); lastByte = millis();
        const auto data = characteristic->getValue();
        for (uint8_t byte : data) parser.feed(byte, [](const uint8_t* frame, size_t length) {
            if (!correction_router::submit(correction_router::Source::Ble, frame, length)) ++correctionDropped;
        });
        correctionAccepted = parser.accepted; correctionRejected = parser.rejected;
    }
};
void put32(uint8_t* p, int32_t value) {
    const uint32_t encoded = static_cast<uint32_t>(value);
    for (int i = 0; i < 4; ++i) p[i] = encoded >> (8*i);
}
}
void begin(Dispatch dispatch, Authenticate authenticate) {
    dispatchRequest = dispatch; authenticateRequest = authenticate;
    requests = xQueueCreate(2, sizeof(Request));
    if (!requests) return;
    if (settings.begin("ble", false)) enabled = settings.getBool("enabled", true);
    // Sin emparejamiento ni PIN, por decisión del propietario: la app de campo
    // debe conectarse de un toque. La contrapartida es real y conviene tenerla
    // presente: cualquier equipo dentro del alcance puede escribir en las
    // características, incluidas las correcciones que van al receptor.
    BLEDevice::init(instrument::apName().c_str());
    server = BLEDevice::createServer();
    server->setCallbacks(new ConnectionCallbacks());
    auto service = server->createService(serviceId);
    auto commands = service->createCharacteristic(commandId, BLECharacteristic::PROPERTY_WRITE);
    commands->setAccessPermissions(ESP_GATT_PERM_WRITE);
    commands->setCallbacks(new CommandCallbacks());
    responses = service->createCharacteristic(responseId, BLECharacteristic::PROPERTY_NOTIFY);
    responses->addDescriptor(new BLE2902());
    solutions = service->createCharacteristic(solutionId, BLECharacteristic::PROPERTY_NOTIFY);
    solutions->addDescriptor(new BLE2902());
    auto corrections = service->createCharacteristic(correctionId, BLECharacteristic::PROPERTY_WRITE);
    corrections->setAccessPermissions(ESP_GATT_PERM_WRITE);
    corrections->setCallbacks(new CorrectionCallbacks());
    // Salud del equipo, aparte de la posición: precisión estimada, antigüedad de
    // las correcciones y presencia de IMU. La app necesita saber con qué calidad
    // está midiendo, no solo dónde. Va en su propia característica para no
    // romper el paquete de 20 bytes que cabe en un MTU ATT sin negociar.
    health = service->createCharacteristic(healthId, BLECharacteristic::PROPERTY_NOTIFY);
    health->addDescriptor(new BLE2902());
    service->start();
    auto advertising = BLEDevice::getAdvertising();
    advertising->addServiceUUID(serviceId);
    advertising->setScanResponse(true);
    if (enabled) BLEDevice::startAdvertising();
    ready = true;
}
void tick() {
    if (!ready) return;
    // Apagado: dejar de anunciarse y soltar a quien esté conectado. La radio BLE
    // del SDK no se desinicializa aquí: hacerlo y rehacerlo fragmenta el heap.
    if (!enabled) {
        if (connected && server) server->disconnect(server->getConnId());
        pending = ""; offset = 0;
        return;
    }
    if (advertise.exchange(false)) BLEDevice::startAdvertising();
    if (!connected) { pending = ""; offset = 0; return; }
    if (responseGeneration != generation.load()) { pending = ""; offset = 0; }
    if (pending.isEmpty()) {
        Request request;
        if (xQueueReceive(requests, &request, 0) == pdTRUE) {
            if (request.generation != generation.load() || millis() - request.arrival > 5000) { ++dropped; return; }
            JsonDocument input, output, body;
            const auto error = deserializeJson(input, request.json, DeserializationOption::NestingLimit(5));
            int code = 400;
            if (error || !input.is<JsonObject>() || !input["id"].is<uint32_t>()) {
                body["error"] = "invalid_request";
            } else {
                output["id"] = input["id"];
                if (!authenticateRequest(input["key"] | "")) {
                    code = 401; body["error"] = "unauthorized";
                } else {
                    authorized = true;
                    const String method = input["method"] | "";
                    const String path = input["path"] | "";
                    // La recuperación/cambio de credenciales permanece exclusivamente por USB.
                    if (path == "/api/recording/read" || path == "/api/access" || (path.startsWith("/api/update/") && method != "GET") || (method != "GET" && method != "POST" && method != "PUT")) {
                        code = 400; body["error"] = "unsupported_operation";
                    } else code = dispatchRequest(method, path, input["body"].as<JsonVariantConst>(), body);
                }
            }
            output["status"] = code; output["body"] = body;
            serializeJson(output, pending);
            if (pending.length() > 4096) pending = "{\"status\":413,\"body\":{\"error\":\"response_too_large\"}}";
            responseGeneration = request.generation; offset = 0; ++messageId;
        }
    }
    // Tramas de 20 bytes: funcionan incluso con MTU ATT de 23.
    if (!pending.isEmpty() && millis() - lastSend >= 5) {
        uint8_t frame[20] = {};
        const size_t count = std::min<size_t>(15, pending.length() - offset);
        frame[0] = messageId; frame[1] = messageId >> 8;
        frame[2] = offset; frame[3] = offset >> 8;
        frame[4] = (offset == 0 ? 1 : 0) | (offset + count == pending.length() ? 2 : 0);
        memcpy(frame + 5, pending.c_str() + offset, count);
        responses->setValue(frame, count + 5); responses->notify();
        offset += count; lastSend = millis();
        if (offset == pending.length()) pending = "";
    }
    if (!authorized || millis() - lastSample < 20) return;
    lastSample = millis();
    const auto snapshot = gnss_receiver::snapshot();
    const auto& s = snapshot.solution;
    if (!snapshot.enabled || !snapshot.accepted || !s.has_utc || esp_timer_get_time() - s.arrival_us > 500000 || s.utc_ms == lastEpoch) return;
    lastEpoch = s.utc_ms;
    uint8_t sample[20] = {};
    ++sampleSequence;
    sample[0] = sampleSequence; sample[1] = sampleSequence >> 8;
    sample[2] = s.quality; sample[3] = s.has_satellites ? s.satellites : 255;
    put32(sample + 4, s.utc_ms);
    put32(sample + 8, s.has_position ? lround(s.latitude_deg * 1e7) : INT32_MIN);
    put32(sample + 12, s.has_position ? lround(s.longitude_deg * 1e7) : INT32_MIN);
    put32(sample + 16, s.has_position && std::isfinite(s.altitude_msl_m) && fabs(s.altitude_msl_m) < 2147483.0 ? lround(s.altitude_msl_m * 1000) : INT32_MIN);
    solutions->setValue(sample, sizeof(sample)); solutions->notify();
    // Salud a 1 Hz: la sigma y la antigüedad de correcciones no cambian a la
    // velocidad de la posición y mandarlas a 10 Hz solo gastaría radio.
    if (millis() - lastHealth < 1000) return;
    lastHealth = millis();
    uint8_t report[20] = {};
    report[0] = 1; // versión del paquete de salud
    // Sigmas en milímetros. 0xFFFF significa "el receptor no la estima".
    const auto sigma = [](double metres) -> uint16_t {
        if (!std::isfinite(metres) || metres < 0 || metres > 65.0) return 0xFFFF;
        return uint16_t(lround(metres * 1000));
    };
    const uint16_t h = snapshot.precision_accepted ? sigma(snapshot.precision.horizontal_sigma_m) : 0xFFFF;
    const uint16_t v = snapshot.precision_accepted ? sigma(snapshot.precision.altitude_sigma_m) : 0xFFFF;
    report[1] = h; report[2] = h >> 8;
    report[3] = v; report[4] = v >> 8;
    const uint32_t age = correction_router::ageMs();
    // 0xFFFF = sin fuente conectada; el resto, segundos desde la última trama.
    const uint16_t ageSeconds = age == UINT32_MAX ? 0xFFFF : uint16_t(std::min<uint32_t>(age / 1000, 65534));
    report[5] = ageSeconds; report[6] = ageSeconds >> 8;
    report[7] = uint8_t(correction_router::sourceCode());
    report[8] = s.quality;
    report[9] = 0; // IMU: sin hardware todavía, reservado para no renumerar después
    health->setValue(report, sizeof(report)); health->notify();
}
void status(JsonObject out) {
    out["state"] = !ready ? "start_failed" : (!enabled ? "disabled" : (connected ? "connected" : "advertising"));
    out["enabled"] = enabled.load();
    // Sin emparejamiento ni PIN por decisión del propietario: cualquier equipo
    // dentro del alcance puede escribir, incluidas las correcciones.
    out["pairing_required"] = false;
    out["protocol_version"] = 2;
    out["dropped_requests"] = dropped.load();
    out["control_available"] = ready;
    out["rtcm_available"] = gnss_receiver::snapshot().enabled;
    out["rtcm_valid_frames"] = correctionAccepted.load();
    out["rtcm_crc_errors"] = correctionRejected.load();
    out["rtcm_dropped_frames"] = correctionDropped.load();
    out["file_download_available"] = false;
    out["telemetry_hardware_validated"] = false;
}
int request(const String& method, JsonVariantConst body, JsonDocument& out) {
    if (method == "GET") { status(out.to<JsonObject>()); return 200; }
    if (method != "POST" || !body.is<JsonObjectConst>() || body.size() != 1) return 400;
    if (!body["enabled"].is<bool>()) return 400;
    const bool next = body["enabled"].as<bool>();
    if (next != enabled) {
        enabled = next;
        if (!settings.putBool("enabled", next)) {
            out["message"] = "No se pudo guardar el ajuste; el cambio se perderá al reiniciar.";
        }
        if (next) advertise = true;
    }
    status(out.to<JsonObject>());
    return 200;
}
}
