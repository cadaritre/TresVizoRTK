// Módulo de radio LoRa del MeridianV (docs/radio/RADIO_MODULE.md).
//
// Tres partes en un bucle:
//   - Bluetooth: la app le da de alta (red Wi-Fi y contraseña de su MeridianV) y lo
//     configura; se anuncia como «TresVizo Radio XXXX».
//   - Wi-Fi: se une a la red propia del MeridianV y abre TCP a su puerta de enlace
//     (192.168.4.1:2102). Por ahí recibe su papel, el RTCM de la base y la
//     configuración, y manda su estado cada segundo.
//   - LoRa (SX1262 de la E22-900M30S): en base transmite el RTCM; en rover lo recibe,
//     lo rearma con el parser RTCM3 (CRC-24Q) y entrega solo tramas válidas.
#include <Arduino.h>
#include <ArduinoJson.h>
#include <BLE2902.h>
#include <BLEDevice.h>
#include <BLEServer.h>
#include <RadioLib.h>
#include <SPI.h>
#include <WiFi.h>
#include <freertos/semphr.h>
#include <esp_app_format.h>
#include <esp_image_format.h>
#include "radio_air.h"
#include "radio_config.h"
#include "signed_firmware.h"
#include "radio_link.h"
#include "rtcm3.h"

// Identidad de la imagen en la sección que ESP-IDF deja tras el descriptor de
// aplicación (byte 288: versión; byte 320: placa), igual que el MeridianV. Así el
// cargador por USB (tools/flasher/) sabe que un .bin es del módulo de radio.
static_assert(sizeof(esp_image_header_t) + sizeof(esp_image_segment_header_t) + sizeof(esp_app_desc_t) ==
              signed_firmware::kIdentityImageOffset, "la identidad va justo detras de esp_app_desc_t");
static_assert(signed_firmware::fitsIdentity(RADIO_VERSION), "la versión no cabe en la identidad");
const signed_firmware::BoardFirmwareIdentity kImageIdentity __attribute__((section(".rodata_custom_desc"), used)) =
    {signed_firmware::makeIdentity(RADIO_VERSION), RADIO_HARDWARE_ID};

namespace {
// --- Tiempos y límites (con su motivo) ---------------------------------------------
// El MeridianV corta la conexión si pasan 5 s sin estado; uno por segundo deja margen.
constexpr uint32_t kStatusPeriodMs = 1000;
// Reintento de Wi-Fi y TCP: rápido para que al encender el MeridianV se enganche
// enseguida, sin saturar al equipo si todavía no ha levantado su red.
constexpr uint32_t kReconnectMs = 2000;
// RTCM de la base más viejo que esto ya no le sirve al rover: se tira antes de
// transmitirlo (el receptor admite correcciones de pocos segundos de edad).
constexpr uint32_t kMaxFrameAgeMs = 2000;
constexpr size_t kPendingFrames = 16;
// Corriente máxima del SX1262 para la etapa que excita al amplificador de la E22.
constexpr float kCurrentLimitMilliamps = 140.0f;
constexpr uint16_t kBleMtu = 247;

// UUID del servicio de configuración del radio (docs/radio/RADIO_MODULE.md).
const char* kServiceUuid = "c04c0001-8f24-4adb-a350-77ef6339c320";
const char* kConfigUuid = "c04c0002-8f24-4adb-a350-77ef6339c320";
const char* kStatusUuid = "c04c0003-8f24-4adb-a350-77ef6339c320";

enum class Role : uint8_t { idle, base, rover };
const char* roleName(Role role) { return role == Role::base ? "base" : role == Role::rover ? "rover" : "idle"; }

radio_config::Settings settings;
Role role = Role::idle;

// --- LoRa -------------------------------------------------------------------------
SPIClass loraSpi(FSPI);
SX1262 lora = new Module(RADIO_PIN_NSS, RADIO_PIN_DIO1, RADIO_PIN_NRST, RADIO_PIN_BUSY, loraSpi);
bool loraReady = false;
int loraError = 0;
volatile bool packetArrived = false;
radio_air::Packetizer packetizer;
radio_air::Receiver receiver;
gnss::Rtcm3Parser roverParser;
uint32_t packetsSent = 0;
float lastRssiDbm = NAN, lastSnrDb = NAN;

void IRAM_ATTR onPacketReceived() { packetArrived = true; }

// --- Enlace con el MeridianV -------------------------------------------------------
WiFiClient meridianLink;
radio_link::Decoder decoder;
uint32_t lastWifiAttempt = 0, lastLinkAttempt = 0, lastStatus = 0;
bool helloSent = false;

struct PendingFrame { uint32_t arrivedMs; uint16_t length; uint8_t bytes[1029]; };
PendingFrame pending[kPendingFrames];
size_t pendingHead = 0, pendingCount = 0;
uint32_t framesExpired = 0, framesOverflow = 0;

// --- Bluetooth ---------------------------------------------------------------------
BLECharacteristic* statusCharacteristic = nullptr;
SemaphoreHandle_t bleLock = nullptr;
String bleRequest;          // lo último que escribió la app, para aplicarlo en el bucle
bool bleRequestPending = false;
String lastError;
bool bleClient = false;

void setLed(bool on) {
    if (RADIO_PIN_LED >= 0) digitalWrite(RADIO_PIN_LED, on ? HIGH : LOW);
}

// Frecuencia, potencia y red según los ajustes; el papel decide si se escucha.
void configureLora() {
    if (!loraReady) return;
    lora.standby();
    lora.setFrequency(radio_air::channelHz(settings.channel) / 1e6f);
    lora.setOutputPower(radio_air::chipDbmFor(settings.powerDbm));
    packetizer.network = settings.network;
    receiver.network = settings.network;
    receiver.reset();
    roverParser.reset();
    if (role == Role::rover) lora.startReceive();
}

void startLora() {
    loraSpi.begin(RADIO_PIN_SCK, RADIO_PIN_MISO, RADIO_PIN_MOSI, RADIO_PIN_NSS);
    loraError = lora.begin(radio_air::channelHz(settings.channel) / 1e6f, radio_air::kBandwidthHz / 1e3f,
                           radio_air::kSpreadingFactor, radio_air::kCodingRateDenominator,
                           RADIOLIB_SX126X_SYNC_WORD_PRIVATE, radio_air::chipDbmFor(settings.powerDbm),
                           radio_air::kPreambleSymbols, RADIO_TCXO_VOLTS);
    if (loraError != RADIOLIB_ERR_NONE) return;
    // La E22 no usa DIO2 para la antena: dos pines del ESP32 conmutan emisión y recepción.
    lora.setRfSwitchPins(RADIO_PIN_RXEN, RADIO_PIN_TXEN);
    lora.setCurrentLimit(kCurrentLimitMilliamps);
    lora.setCRC(2);
    lora.setPacketReceivedAction(onPacketReceived);
    loraReady = true;
    configureLora();
}

bool sendToMeridian(radio_link::Type type, const uint8_t* payload, size_t length) {
    if (!meridianLink.connected()) return false;
    uint8_t wire[radio_link::kHeaderBytes + radio_link::kMaxPayloadBytes];
    const size_t n = radio_link::encode(type, payload, length, wire, sizeof(wire));
    return n && meridianLink.write(wire, n) == n;
}

bool sendJson(radio_link::Type type, JsonDocument& doc) {
    char text[512];
    const size_t n = serializeJson(doc, text, sizeof(text));
    return n && n < sizeof(text) && sendToMeridian(type, reinterpret_cast<const uint8_t*>(text), n);
}

String radioId() {
    uint8_t mac[6];
    WiFi.macAddress(mac);
    char text[18];
    snprintf(text, sizeof(text), "%02X%02X%02X%02X%02X%02X", mac[0], mac[1], mac[2], mac[3], mac[4], mac[5]);
    return text;
}

const char* airState() {
    if (!loraReady) return "radio_error";
    if (role == Role::base) return "transmitting";
    if (role == Role::rover) return receiver.accepted ? "receiving" : "listening";
    return "idle";
}

// El mismo estado para el MeridianV y para la app. La contraseña nunca sale.
void fillStatus(JsonDocument& doc, bool forApp) {
    doc["radio_version"] = static_cast<const char*>(kImageIdentity.firmware.version);
    doc["role"] = roleName(role);
    doc["network"] = settings.network;
    doc["channel"] = settings.channel;
    doc["power_dbm"] = settings.powerDbm;
    if (isnan(lastRssiDbm)) doc["rssi_dbm"] = nullptr; else doc["rssi_dbm"] = lastRssiDbm;
    if (isnan(lastSnrDb)) doc["snr_db"] = nullptr; else doc["snr_db"] = lastSnrDb;
    doc["packets_sent"] = packetsSent;
    doc["packets_received"] = receiver.accepted;
    doc["packets_lost"] = receiver.lost;
    doc["packets_foreign"] = receiver.foreign;
    doc["frames_expired"] = framesExpired;
    doc["air"] = airState();
    if (forApp) {
        doc["wifi_ssid"] = settings.wifiSsid;
        doc["wifi"] = WiFi.status() == WL_CONNECTED ? "connected" : "connecting";
        doc["meridian"] = meridianLink.connected() ? "connected" : "not_connected";
        if (!loraReady) doc["radio_error_code"] = loraError;
        if (lastError.length()) doc["error"] = lastError;
    }
}

void sendHello() {
    JsonDocument doc;
    doc["radio_version"] = static_cast<const char*>(kImageIdentity.firmware.version);
    doc["radio_id"] = radioId();
    doc["hardware"] = static_cast<const char*>(kImageIdentity.hardwareId);
    doc["network"] = settings.network;
    doc["channel"] = settings.channel;
    doc["power_dbm"] = settings.powerDbm;
    helloSent = sendJson(radio_link::Type::hello, doc);
}

void setRole(Role next) {
    if (next == role) return;
    role = next;
    pendingCount = 0;
    if (!loraReady) return;
    lora.standby();
    receiver.reset();
    roverParser.reset();
    if (role == Role::rover) lora.startReceive();
}

void queueFrame(const uint8_t* frame, size_t length) {
    if (length > sizeof(pending[0].bytes)) return;
    if (pendingCount == kPendingFrames) {        // lleno: se pierde la más vieja
        pendingHead = (pendingHead + 1) % kPendingFrames; --pendingCount; ++framesOverflow;
    }
    PendingFrame& slot = pending[(pendingHead + pendingCount) % kPendingFrames];
    slot.arrivedMs = millis(); slot.length = uint16_t(length);
    memcpy(slot.bytes, frame, length);
    ++pendingCount;
}

void transmit(const uint8_t* packet, size_t length) {
    if (!loraReady) return;
    if (lora.transmit(packet, length) == RADIOLIB_ERR_NONE) ++packetsSent;
}

// Base: lo que espera sale por el aire, salvo lo que ya caducó.
void serviceBase() {
    while (pendingCount) {
        PendingFrame& frame = pending[pendingHead];
        pendingHead = (pendingHead + 1) % kPendingFrames; --pendingCount;
        if (millis() - frame.arrivedMs > kMaxFrameAgeMs) { ++framesExpired; continue; }
        packetizer.add(frame.bytes, frame.length, millis(), transmit);
    }
    packetizer.tick(millis(), transmit);
}

// Rover: un paquete llegó; se rearma el RTCM y se entregan las tramas válidas.
void serviceRover() {
    if (!packetArrived) return;
    packetArrived = false;
    uint8_t packet[radio_air::kMaxPacketBytes];
    const size_t length = lora.getPacketLength();
    const int state = length <= sizeof(packet) ? lora.readData(packet, length) : RADIOLIB_ERR_PACKET_TOO_LONG;
    if (state == RADIOLIB_ERR_NONE) {
        lastRssiDbm = lora.getRSSI();
        lastSnrDb = lora.getSNR();
        size_t chunkLength = 0; bool gap = false;
        const uint8_t* chunk = receiver.accept(packet, length, chunkLength, gap);
        if (chunk) {
            if (gap) roverParser.reset();
            for (size_t i = 0; i < chunkLength; ++i)
                roverParser.feed(chunk[i], [](const uint8_t* frame, size_t frameLength) {
                    sendToMeridian(radio_link::Type::rtcm, frame, frameLength);
                });
        }
    }
    lora.startReceive();
}

void handleLinkFrame(radio_link::Type type, const uint8_t* payload, size_t length) {
    if (type == radio_link::Type::rtcm) {
        if (role == Role::base) queueFrame(payload, length);
        return;
    }
    JsonDocument doc;
    if (deserializeJson(doc, reinterpret_cast<const char*>(payload), length)) return;
    if (type == radio_link::Type::role) {
        const String name = doc["role"] | "idle";
        setRole(name == "base" ? Role::base : name == "rover" ? Role::rover : Role::idle);
    } else if (type == radio_link::Type::config) {
        radio_config::Settings next = settings;
        String error;
        // El MeridianV no toca el Wi-Fi del radio: eso solo por Bluetooth.
        if (radio_config::apply(doc.as<JsonVariantConst>(), next, error, false)) {
            settings = next;
            radio_config::save(settings);
            configureLora();
        } else lastError = error;
    }
}

void serviceLink() {
    const uint32_t now = millis();
    if (WiFi.status() != WL_CONNECTED) {
        if (meridianLink.connected()) meridianLink.stop();
        setRole(Role::idle);
        if (now - lastWifiAttempt > kReconnectMs * 5) {
            lastWifiAttempt = now;
            WiFi.disconnect();
            WiFi.begin(settings.wifiSsid.c_str(), settings.wifiPassword.c_str());
        }
        return;
    }
    if (!meridianLink.connected()) {
        setRole(Role::idle);
        helloSent = false;
        if (now - lastLinkAttempt < kReconnectMs) return;
        lastLinkAttempt = now;
        // El MeridianV es la puerta de enlace de su propia red.
        if (!meridianLink.connect(WiFi.gatewayIP(), radio_link::kPort, kReconnectMs)) return;
        meridianLink.setNoDelay(true);
        decoder.reset();
        sendHello();
        lastStatus = 0;
    }
    uint8_t buffer[512];
    while (meridianLink.available() > 0) {
        const int n = meridianLink.read(buffer, sizeof(buffer));
        if (n <= 0) break;
        decoder.feed(buffer, size_t(n), handleLinkFrame);
        if (decoder.broken) { meridianLink.stop(); return; }
    }
    if (now - lastStatus >= kStatusPeriodMs) {
        lastStatus = now;
        JsonDocument doc;
        fillStatus(doc, false);
        if (!sendJson(radio_link::Type::status, doc)) meridianLink.stop();
    }
}

// --- Bluetooth: alta y configuración desde la app ----------------------------------
class ConfigCallbacks : public BLECharacteristicCallbacks {
    void onWrite(BLECharacteristic* characteristic) override {
        const std::string value = characteristic->getValue();
        xSemaphoreTake(bleLock, portMAX_DELAY);
        bleRequest = String(value.c_str());
        bleRequestPending = true;
        xSemaphoreGive(bleLock);
    }
};

class ServerCallbacks : public BLEServerCallbacks {
    void onConnect(BLEServer*) override { bleClient = true; }
    void onDisconnect(BLEServer*) override { bleClient = false; BLEDevice::startAdvertising(); }
};

void startBluetooth() {
    bleLock = xSemaphoreCreateMutex();
    uint8_t mac[6];
    WiFi.macAddress(mac);
    char name[32];
    snprintf(name, sizeof(name), "TresVizo Radio %02X%02X", mac[4], mac[5]);
    BLEDevice::init(name);
    BLEDevice::setMTU(kBleMtu);
    BLEServer* server = BLEDevice::createServer();
    server->setCallbacks(new ServerCallbacks());
    BLEService* service = server->createService(kServiceUuid);
    BLECharacteristic* config = service->createCharacteristic(kConfigUuid, BLECharacteristic::PROPERTY_WRITE);
    config->setCallbacks(new ConfigCallbacks());
    statusCharacteristic = service->createCharacteristic(
        kStatusUuid, BLECharacteristic::PROPERTY_READ | BLECharacteristic::PROPERTY_NOTIFY);
    statusCharacteristic->addDescriptor(new BLE2902());
    service->start();
    BLEAdvertising* advertising = BLEDevice::getAdvertising();
    advertising->addServiceUUID(kServiceUuid);
    advertising->setScanResponse(true);
    BLEDevice::startAdvertising();
}

void serviceBluetooth() {
    String request;
    xSemaphoreTake(bleLock, portMAX_DELAY);
    if (bleRequestPending) { request = bleRequest; bleRequestPending = false; }
    xSemaphoreGive(bleLock);
    if (request.length()) {
        JsonDocument doc;
        radio_config::Settings next = settings;
        String error;
        if (deserializeJson(doc, request)) lastError = "JSON no válido.";
        else if (!radio_config::apply(doc.as<JsonVariantConst>(), next, error, true)) lastError = error;
        else {
            const bool wifiChanged = next.wifiSsid != settings.wifiSsid || next.wifiPassword != settings.wifiPassword;
            settings = next;
            lastError = radio_config::save(settings) ? "" : "No se pudo guardar el ajuste.";
            configureLora();
            if (wifiChanged) { meridianLink.stop(); WiFi.disconnect(); lastWifiAttempt = 0; }
        }
    }
    static uint32_t lastNotify = 0;
    if (millis() - lastNotify >= kStatusPeriodMs) {
        lastNotify = millis();
        JsonDocument doc;
        fillStatus(doc, true);
        String text;
        serializeJson(doc, text);
        statusCharacteristic->setValue(text.c_str());
        if (bleClient) statusCharacteristic->notify();
    }
}
}  // namespace

void setup() {
    Serial.begin(115200);
    if (RADIO_PIN_LED >= 0) pinMode(RADIO_PIN_LED, OUTPUT);
    settings = radio_config::load();
    WiFi.mode(WIFI_STA);
    WiFi.setAutoReconnect(true);
    startBluetooth();
    startLora();
    WiFi.begin(settings.wifiSsid.c_str(), settings.wifiPassword.c_str());
    lastWifiAttempt = millis();
}

void loop() {
    serviceBluetooth();
    serviceLink();
    if (role == Role::base) serviceBase();
    else if (role == Role::rover) serviceRover();
    // LED: fijo enlazado con el MeridianV; parpadeo lento buscándolo.
    setLed(meridianLink.connected() || (millis() / 500) % 2);
    delay(1);
}
