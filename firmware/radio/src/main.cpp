// Módulo de radio LoRa del MeridianV (docs/radio/RADIO_MODULE.md, docs/radio/USB_LINK.md).
//
// Dos partes en un bucle:
//   - USB-C como anfitrión: el MeridianV (dispositivo CDC) se enchufa al radio y por ese
//     cable van el saludo, el papel, la configuración, el estado y el RTCM crudo. Sin
//     saludo aceptado el radio no transmite nada ni entrega correcciones.
//   - LoRa (SX1262 de la E22-900M30S): en base transmite el RTCM que le da el MeridianV;
//     en rover lo recibe, lo rearma con el parser RTCM3 (CRC-24Q) y le entrega solo
//     tramas válidas.
// La consola de depuración va por UART0 (el USB nativo es el enlace).
#include <Arduino.h>
#include <ArduinoJson.h>
#include <RadioLib.h>
#include <SPI.h>
#include <esp_app_format.h>
#include <esp_image_format.h>
#include <esp_system.h>
#include "radio_air.h"
#include "radio_config.h"
#include "radio_usb.h"
#include "rtcm3.h"
#include "signed_firmware.h"
#include "usb_cdc_host.h"
#include "usb_session.h"

#ifndef RADIO_PIN_VBAT
#define RADIO_PIN_VBAT -1
#endif
#ifndef RADIO_VBAT_DIVIDER
#define RADIO_VBAT_DIVIDER 2.0f
#endif

// Identidad de la imagen en la sección que ESP-IDF deja tras el descriptor de
// aplicación (byte 288: versión; byte 320: placa), igual que el MeridianV. Así el
// cargador por USB (tools/flasher/) sabe que un .bin es del módulo de radio.
static_assert(sizeof(esp_image_header_t) + sizeof(esp_image_segment_header_t) + sizeof(esp_app_desc_t) ==
              signed_firmware::kIdentityImageOffset, "la identidad va justo detras de esp_app_desc_t");
static_assert(signed_firmware::fitsIdentity(RADIO_VERSION), "la versión no cabe en la identidad");
const signed_firmware::BoardFirmwareIdentity kImageIdentity __attribute__((section(".rodata_custom_desc"), used)) =
    {signed_firmware::makeIdentity(RADIO_VERSION), RADIO_HARDWARE_ID};

namespace {
using usb_session::Role;

// --- Tiempos y límites (con su motivo) ---------------------------------------------
// RTCM de la base más viejo que esto ya no le sirve al rover: se tira antes de
// transmitirlo (el receptor admite correcciones de pocos segundos de edad).
constexpr uint32_t kMaxFrameAgeMs = 2000;
constexpr size_t kPendingFrames = 16;
// Corriente máxima del SX1262 para la etapa que excita al amplificador de la E22.
constexpr float kCurrentLimitMilliamps = 140.0f;

radio_config::Settings settings;

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
Role airRole = Role::idle;     // el papel con el que está configurada la radio

void IRAM_ATTR onPacketReceived() { packetArrived = true; }

// --- Enlace USB con el MeridianV ----------------------------------------------------
usb_session::Session session;
radio_usb::Demux demux;
uint32_t usbSession = 0;
String receiverVersion;
uint32_t framesToAir = 0, framesFromAir = 0;

struct PendingFrame { uint32_t arrivedMs; uint16_t length; uint8_t bytes[radio_usb::kMaxRtcmBytes]; };
PendingFrame pending[kPendingFrames];
size_t pendingHead = 0, pendingCount = 0;
uint32_t framesExpired = 0, framesOverflow = 0;

void setLed(bool on) {
    if (RADIO_PIN_LED >= 0) digitalWrite(RADIO_PIN_LED, on ? HIGH : LOW);
}

String radioId() {
    uint8_t mac[6] = {};
    esp_efuse_mac_get_default(mac);
    char text[13];
    snprintf(text, sizeof(text), "%02X%02X%02X%02X%02X%02X", mac[0], mac[1], mac[2], mac[3], mac[4], mac[5]);
    return text;
}

// --- Radio ----------------------------------------------------------------------------
// Deja la radio como pide el papel: rover escuchando, base lista para transmitir e idle
// dormida (3 µA): el radio va con su pila y sin MeridianV no hay nada que hacer.
void applyAirRole() {
    pendingCount = 0;
    packetizer = radio_air::Packetizer();
    packetizer.network = settings.network;
    receiver.reset();
    roverParser.reset();
    if (!loraReady) return;
    lora.standby();
    if (airRole == Role::rover) lora.startReceive();
    else if (airRole == Role::idle) lora.sleep(true);
}

// Frecuencia, potencia y red según los ajustes.
void configureLora() {
    packetizer.network = settings.network;
    receiver.network = settings.network;
    if (!loraReady) return;
    lora.standby();
    lora.setFrequency(radio_air::channelHz(settings.channel) / 1e6f);
    lora.setOutputPower(radio_air::chipDbmFor(settings.powerDbm));
    applyAirRole();
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

const char* airState() {
    if (!loraReady) return "radio_error";
    if (airRole == Role::base) return "transmitting";
    if (airRole == Role::rover) return receiver.accepted ? "receiving" : "listening";
    return "idle";
}

// --- Envío por el USB ---------------------------------------------------------------
bool sendJson(radio_usb::Type type, JsonDocument& doc) {
    char text[radio_usb::kMaxPayloadBytes];
    const size_t n = serializeJson(doc, text, sizeof(text));
    if (!n || n >= sizeof(text)) return false;
    uint8_t wire[radio_usb::kMaxFrameBytes];
    const size_t length = radio_usb::encode(type, reinterpret_cast<const uint8_t*>(text), n, wire, sizeof(wire));
    return length && usb_cdc_host::write(wire, length);
}

void putSettings(JsonDocument& doc) {
    doc["network"] = settings.network;
    doc["channel"] = settings.channel;
    doc["power_dbm"] = settings.powerDbm;
    doc["max_power_dbm"] = radio_config::kMaxOutputDbm;
}

void sendHello() {
    JsonDocument doc;
    doc["protocol"] = radio_usb::kProtocol;
    doc["radio_version"] = static_cast<const char*>(kImageIdentity.firmware.version);
    doc["radio_id"] = radioId();
    doc["hardware"] = static_cast<const char*>(kImageIdentity.hardwareId);
    putSettings(doc);
    doc["channels"] = radio_air::kChannelCount;
    sendJson(radio_usb::Type::hello, doc);
}

// Estado cada segundo: también es el latido del radio para el MeridianV.
void sendStatus() {
    JsonDocument doc;
    doc["role"] = usb_session::roleName(airRole);
    putSettings(doc);
    if (isnan(lastRssiDbm)) doc["rssi_dbm"] = nullptr; else doc["rssi_dbm"] = lastRssiDbm;
    if (isnan(lastSnrDb)) doc["snr_db"] = nullptr; else doc["snr_db"] = lastSnrDb;
    doc["packets_sent"] = packetsSent;
    doc["packets_received"] = receiver.accepted;
    doc["packets_lost"] = receiver.lost;
    doc["packets_foreign"] = receiver.foreign;
    doc["frames_to_air"] = framesToAir;
    doc["frames_from_air"] = framesFromAir;
    doc["frames_expired"] = framesExpired;
    doc["frames_overflow"] = framesOverflow;
    doc["rtcm_rejected"] = roverParser.rejected;
    doc["air"] = airState();
    if (!loraReady) doc["radio_error_code"] = loraError;
    if (RADIO_PIN_VBAT >= 0) doc["battery_mv"] = int(analogReadMilliVolts(RADIO_PIN_VBAT) * RADIO_VBAT_DIVIDER);
    else doc["battery_mv"] = nullptr;
    doc["uptime_s"] = millis() / 1000;
    const usb_cdc_host::Info usb = usb_cdc_host::info();
    doc["usb_rx_dropped"] = usb.rxDropped;
    doc["usb_tx_dropped"] = usb.txDropped;
    sendJson(radio_usb::Type::status, doc);
}

// --- Lo que llega del MeridianV --------------------------------------------------------
void applyConfig(JsonDocument& request) {
    radio_config::Settings next = settings;
    String error;
    bool limited = false;
    JsonDocument ack;
    ack["seq"] = request["seq"];
    if (radio_config::apply(request.as<JsonVariantConst>(), next, error, limited)) {
        settings = next;
        ack["ok"] = true;
        if (!radio_config::save(settings)) ack["saved"] = false;   // vale hasta apagarlo
        if (limited) ack["power_limited"] = true;
        configureLora();
        Serial.printf("Ajustes: red %u, canal %u, %d dBm%s\n", settings.network, settings.channel,
                      settings.powerDbm, limited ? " (recortado al tope legal)" : "");
    } else {
        ack["ok"] = false;
        ack["error"] = "invalid_setting";
        ack["message"] = error;
    }
    putSettings(ack);
    sendJson(radio_usb::Type::config_ack, ack);
}

void handleFrame(uint8_t type, const uint8_t* payload, size_t length) {
    const uint32_t now = millis();
    session.heard(now);
    JsonDocument doc;
    if (deserializeJson(doc, reinterpret_cast<const char*>(payload), length) || !doc.is<JsonObject>()) return;
    switch (static_cast<radio_usb::Type>(type)) {
        case radio_usb::Type::welcome: {
            // Aceptado solo si el receptor habla nuestro protocolo.
            const bool accepted = (doc["accepted"] | false) && (doc["protocol"] | 0) == radio_usb::kProtocol;
            const bool wasLinked = session.linked();
            session.welcome(accepted, now);
            receiverVersion = doc["receiver_version"] | "";
            if (!wasLinked) {
                if (session.linked()) Serial.printf("Enlazado con el MeridianV %s\n", receiverVersion.c_str());
                else Serial.printf("El MeridianV rechazó el enlace: %s\n", static_cast<const char*>(doc["error"] | "?"));
            }
            break;
        }
        case radio_usb::Type::role:
            session.setRole(usb_session::parseRole(doc["role"] | "idle"), now);
            break;
        case radio_usb::Type::config:
            if (session.linked()) applyConfig(doc);
            break;
        default:
            break;   // tipos nuevos que esta versión no conoce: se ignoran
    }
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

struct LinkHandler {
    void onFrame(uint8_t type, const uint8_t* payload, size_t length) { handleFrame(type, payload, length); }
    // RTCM del receptor: solo la base lo transmite.
    void onRtcm(const uint8_t* frame, size_t length) {
        if (session.linked() && airRole == Role::base) queueFrame(frame, length);
    }
    // Respuestas JSON y texto del receptor (arranque, avisos): no son para el radio.
    void onLine(const char*, size_t) {}
    void onLineOverflow() {}
    void onLineTimeout() {}
};
LinkHandler linkHandler;

void serviceUsb() {
    const uint32_t now = millis();
    if (usb_cdc_host::open()) {
        const uint32_t current = usb_cdc_host::session();
        if (current != usbSession) {             // CDC nuevo: de cero
            usbSession = current;
            demux.reset();
            session.attach(now);
            const usb_cdc_host::Info usb = usb_cdc_host::info();
            Serial.printf("USB: CDC %04X:%04X abierto\n", usb.vid, usb.pid);
        }
    } else if (session.state != usb_session::State::detached) {
        session.detach();
        Serial.println("USB: desconectado");
    }
    uint8_t chunk[256];
    for (size_t n; (n = usb_cdc_host::read(chunk, sizeof(chunk))) > 0;) demux.feed(chunk, n, millis(), linkHandler);
    demux.tick(millis(), linkHandler);
    const usb_session::Session::Due due = session.tick(millis());
    if (due.lost) Serial.println("Enlace: sin latido del MeridianV");
    if (due.hello) sendHello();
    if (due.status) sendStatus();
    // El papel manda sobre la radio: cambia con `role`, al caerse el enlace y al desconectar.
    if (session.role != airRole) {
        airRole = session.role;
        applyAirRole();
        Serial.printf("Papel: %s\n", usb_session::roleName(airRole));
    }
}

// --- Aire -------------------------------------------------------------------------------
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
        ++framesToAir;
        packetizer.add(frame.bytes, frame.length, millis(), transmit);
    }
    packetizer.tick(millis(), transmit);
}

void deliver(const uint8_t* frame, size_t length) {
    // Cruda, con su CRC: el MeridianV la vuelve a comprobar en su demultiplexor.
    // Si no cabe en el USB, cuenta en usb_tx_dropped.
    if (session.linked() && airRole == Role::rover && usb_cdc_host::write(frame, length)) ++framesFromAir;
}

// Rover: un paquete llegó; se rearma el RTCM y se entregan las tramas válidas. Con
// reloj (feedAt): una trama a medias sin bytes nuevos durante 1 s se descarta, y una
// completa y buena detrás de una a medias sale en el acto (rtcm3.h).
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
            const uint32_t now = millis();
            for (size_t i = 0; i < chunkLength; ++i) roverParser.feedAt(chunk[i], now, deliver);
        }
    }
    lora.startReceive();
}

// LED: fijo enlazado con el MeridianV; parpadeo saludando; destello corto esperando el
// cable; parpadeo rápido si la radio no arrancó o el MeridianV rechazó el enlace.
void updateLed(uint32_t now) {
    if (!loraReady || session.state == usb_session::State::rejected) setLed((now / 100) % 2);
    else if (session.linked()) setLed(true);
    else if (session.state == usb_session::State::greeting) setLed((now / 250) % 2);
    else setLed(now % 2000 < 80);
}
}  // namespace

void setup() {
    Serial.begin(115200);
    if (RADIO_PIN_LED >= 0) pinMode(RADIO_PIN_LED, OUTPUT);
    settings = radio_config::load();
    startLora();   // queda dormida (idle) hasta que el MeridianV le dé papel
    const bool usbReady = usb_cdc_host::begin();
    Serial.printf("TresVizo Radio %s (%s). LoRa %s, USB anfitrión %s. Red %u, canal %u, %d dBm.\n",
                  RADIO_VERSION, radioId().c_str(), loraReady ? "lista" : "con error",
                  usbReady ? "listo" : "con error", settings.network, settings.channel, settings.powerDbm);
    if (!loraReady) Serial.printf("RadioLib: error %d\n", loraError);
}

void loop() {
    serviceUsb();
    if (airRole == Role::base) serviceBase();
    else if (airRole == Role::rover) serviceRover();
    updateLed(millis());
    delay(1);
}
