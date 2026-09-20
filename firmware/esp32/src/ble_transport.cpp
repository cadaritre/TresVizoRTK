#include "ble_transport.h"
#include "instrument.h"
#include "gnss_receiver.h"
#include "rtcm3.h"
#include "correction_router.h"
#include <BLEDevice.h>
#include <BLEServer.h>
#include <BLE2902.h>
#include <BLESecurity.h>
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
struct Request { uint32_t generation, arrival; char json[1025]; };
QueueHandle_t requests = nullptr;
Dispatch dispatchRequest;
Authenticate authenticateRequest;
BLECharacteristic *responses = nullptr, *solutions = nullptr;
BLEServer* server = nullptr;
std::atomic<bool> connected{false}, secure{false}, authorized{false}, advertise{false};
std::atomic<uint32_t> generation{0}, dropped{0}, correctionAccepted{0}, correctionRejected{0}, correctionDropped{0};
std::atomic<uint8_t> lastAuthReason{0},lastAuthMode{0};
bool ready = false;
uint32_t pairingPin = 0;
String pending;
size_t offset = 0;
uint16_t messageId = 0, sampleSequence = 0;
uint32_t lastSend = 0, lastEpoch = UINT32_MAX, lastSample = 0;
uint32_t responseGeneration = 0;

class ConnectionCallbacks : public BLEServerCallbacks {
    void onConnect(BLEServer*, esp_ble_gatts_cb_param_t* parameters) override {
        ++generation; connected = true; secure = false; authorized = false;
        esp_ble_set_encryption(parameters->connect.remote_bda,ESP_BLE_SEC_ENCRYPT_MITM);
    }
    void onDisconnect(BLEServer*) override {
        ++generation; connected = false; secure = false; authorized = false; advertise = true;
    }
};
class SecurityCallbacks : public BLESecurityCallbacks {
    uint32_t onPassKeyRequest() override { return pairingPin; }
    void onPassKeyNotify(uint32_t) override {}
    bool onSecurityRequest() override { return true; }
    bool onConfirmPIN(uint32_t) override { return false; }
    void onAuthenticationComplete(esp_ble_auth_cmpl_t event) override {
        lastAuthReason=event.fail_reason;lastAuthMode=event.auth_mode;
        secure = event.success && (event.auth_mode & ESP_LE_AUTH_REQ_MITM);
        if (!secure && server) server->disconnect(server->getConnId());
    }
};
class CommandCallbacks : public BLECharacteristicCallbacks {
    char buffer[1025] = {};
    size_t length = 0;
    bool overflow = false;
    uint32_t started = 0, seenGeneration = 0;
    void onWrite(BLECharacteristic* characteristic) override {
        if (!secure) return;
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
        if (!secure || !authorized) return;
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
    Preferences pairing;
    if(!pairing.begin("ble_pairing",false))return;
    pairingPin=pairing.getUInt("pin",0);
    if(pairingPin<100000 || pairingPin>999999){
        pairingPin=100000+esp_random()%900000;
        if(pairing.putUInt("pin",pairingPin)!=sizeof(uint32_t)){pairing.end();return;}
    }
    pairing.end();
    BLEDevice::init(instrument::apName().c_str());
    BLEDevice::setEncryptionLevel(ESP_BLE_SEC_ENCRYPT_MITM);
    BLEDevice::setSecurityCallbacks(new SecurityCallbacks());
    auto security = new BLESecurity();
    security->setStaticPIN(pairingPin);
    security->setAuthenticationMode(ESP_LE_AUTH_REQ_SC_MITM_BOND);
    security->setCapability(ESP_IO_CAP_OUT);
    security->setKeySize(16);
    security->setInitEncryptionKey(ESP_BLE_ENC_KEY_MASK | ESP_BLE_ID_KEY_MASK);
    security->setRespEncryptionKey(ESP_BLE_ENC_KEY_MASK | ESP_BLE_ID_KEY_MASK);
    server = BLEDevice::createServer();
    server->setCallbacks(new ConnectionCallbacks());
    auto service = server->createService(serviceId);
    auto commands = service->createCharacteristic(commandId, BLECharacteristic::PROPERTY_WRITE);
    commands->setAccessPermissions(ESP_GATT_PERM_WRITE_ENC_MITM);
    commands->setCallbacks(new CommandCallbacks());
    responses = service->createCharacteristic(responseId, BLECharacteristic::PROPERTY_NOTIFY);
    responses->addDescriptor(new BLE2902());
    solutions = service->createCharacteristic(solutionId, BLECharacteristic::PROPERTY_NOTIFY);
    solutions->addDescriptor(new BLE2902());
    auto corrections = service->createCharacteristic(correctionId, BLECharacteristic::PROPERTY_WRITE);
    corrections->setAccessPermissions(ESP_GATT_PERM_WRITE_ENC_MITM);
    corrections->setCallbacks(new CorrectionCallbacks());
    service->start();
    auto advertising = BLEDevice::getAdvertising();
    advertising->addServiceUUID(serviceId);
    advertising->setScanResponse(true);
    BLEDevice::startAdvertising();
    ready = true;
}
void tick() {
    if (!ready) return;
    if (advertise.exchange(false)) BLEDevice::startAdvertising();
    if (!connected || !secure) { pending = ""; offset = 0; return; }
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
}
void status(JsonObject out) {
    out["state"] = !ready ? "start_failed" : (connected ? (authorized ? "authorized" : "connected") : "advertising");
    out["encrypted_authenticated"] = secure.load();
    out["last_auth_reason"] = lastAuthReason.load();out["last_auth_mode"] = lastAuthMode.load();
    out["protocol_version"] = 1;
    out["dropped_requests"] = dropped.load();
    out["control_available"] = ready;
    out["rtcm_available"] = gnss_receiver::snapshot().enabled;
    out["rtcm_valid_frames"] = correctionAccepted.load();
    out["rtcm_crc_errors"] = correctionRejected.load();
    out["rtcm_dropped_frames"] = correctionDropped.load();
    out["file_download_available"] = false;
    out["telemetry_hardware_validated"] = false;
}
uint32_t passkey() { return pairingPin; }
}
