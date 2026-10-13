#include "radio_module.h"
#include "board_profile.h"
#include "correction_router.h"
#include "gnss_control.h"
#include "instrument.h"
#include "power_manager.h"
#include "radio_air.h"
#include "radio_usb.h"
#include "radio_usb_receiver.h"
#include "usb_channel.h"
#include <atomic>
#include <cstring>

namespace radio_module {
namespace {
// Tramas RTCM de la base esperando a salir hacia el radio; una época MSM4 son
// 5–8 tramas. Si el radio va lento se tiran las nuevas (es estado: la siguiente
// época las repone), nunca se bloquea a quien las produce.
constexpr UBaseType_t kQueueFrames = 8;

struct Frame { uint16_t length; uint8_t bytes[radio_usb::kMaxRtcmBytes]; };
using radio_usb::LinkRole;

QueueHandle_t outgoing = nullptr;
SemaphoreHandle_t lock = nullptr;
// Solo la tarea del canal USB: el saludo, el papel y el latido.
radio_usb::ReceiverSession session;
// Lo que leen las demás tareas (HTTP, BLE, la salida de correcciones).
std::atomic<bool> ready{false}, linked{false}, configPending{false};
std::atomic<LinkRole> toldRole{LinkRole::idle};
std::atomic<uint32_t> framesToRadio{0}, framesFromRadio{0}, framesRejected{0}, framesDropped{0},
    connections{0}, refused{0};
std::atomic<uint32_t> lastStatusAt{0};
std::atomic<int> protocol{0};

// Lo que dijo el radio (saludo, estado y respuesta a la configuración). Bajo `lock`.
String radioVersion, radioId, radioHardware, airState;
int network = -1, channel = -1, powerDbm = INT32_MIN, maxPowerDbm = INT32_MIN, batteryMv = INT32_MIN;
float rssiDbm = NAN, snrDb = NAN;
uint32_t packetsSent = 0, packetsReceived = 0, packetsLost = 0, packetsForeign = 0;
// La última configuración pedida por /api/radio y lo que contestó el radio.
String pendingConfig;
uint32_t configSeq = 0;
const char* configState = nullptr;   // pending, applied, rejected, not_confirmed
String configError;
int powerLimited = -1;               // -1 sin respuesta todavía

LinkRole wantedRole() {
    if (gnss_control::isBase()) return LinkRole::base;
    if (gnss_control::isRover()) return LinkRole::rover;
    return LinkRole::idle;
}

bool sendJson(radio_usb::Type type, JsonDocument& doc) {
    char text[radio_usb::kMaxPayloadBytes];
    const size_t n = serializeJson(doc, text, sizeof(text));
    if (!n || n >= sizeof(text)) return false;
    uint8_t wire[radio_usb::kMaxFrameBytes];
    const size_t length = radio_usb::encode(type, reinterpret_cast<const uint8_t*>(text), n, wire, sizeof(wire));
    return length && usb_channel::write(wire, length);
}

// Ajustes que el radio manda en `hello`, `status` y `config_ack`. Bajo `lock`.
void rememberSettings(JsonDocument& doc) {
    if (doc["network"].is<int>()) network = doc["network"];
    if (doc["channel"].is<int>()) channel = doc["channel"];
    if (doc["power_dbm"].is<int>()) powerDbm = doc["power_dbm"];
    if (doc["max_power_dbm"].is<int>()) maxPowerDbm = doc["max_power_dbm"];
}

void forget() {
    xSemaphoreTake(lock, portMAX_DELAY);
    radioVersion = radioId = radioHardware = airState = "";
    network = channel = -1; powerDbm = maxPowerDbm = batteryMv = INT32_MIN; rssiDbm = snrDb = NAN;
    packetsSent = packetsReceived = packetsLost = packetsForeign = 0;
    // Una orden sin respuesta cuando se fue el radio no se sabe si se aplicó.
    if (configState && !strcmp(configState, "pending")) configState = "not_confirmed";
    xSemaphoreGive(lock);
    configPending = false;
    protocol = 0;
}

void onHello(JsonDocument& doc, uint32_t now) {
    const int agreed = session.hello(doc["protocol"] | 0, now);
    JsonDocument reply;
    reply["protocol"] = agreed ? agreed : radio_usb::kProtocol;
    reply["accepted"] = agreed > 0;
    if (agreed) {
        reply["receiver_version"] = instrument::kVersion;
        reply["hardware_id"] = board_profile::kHardwareId;
        xSemaphoreTake(lock, portMAX_DELAY);
        radioVersion = doc["radio_version"] | "";
        radioId = doc["radio_id"] | "";
        radioHardware = doc["hardware"] | "";
        rememberSettings(doc);
        xSemaphoreGive(lock);
        protocol = agreed;
        lastStatusAt = now;
        ++connections;
    } else {
        reply["error"] = "unsupported_protocol";
        reply["message"] = "El radio no habla ninguna versión del enlace que entienda este firmware.";
        ++refused;
        forget();
    }
    linked = session.linked;
    toldRole = session.role();
    sendJson(radio_usb::Type::welcome, reply);
}

void onStatus(JsonDocument& doc, uint32_t now) {
    lastStatusAt = now;
    xSemaphoreTake(lock, portMAX_DELAY);
    rememberSettings(doc);
    rssiDbm = doc["rssi_dbm"].is<float>() ? doc["rssi_dbm"].as<float>() : NAN;
    snrDb = doc["snr_db"].is<float>() ? doc["snr_db"].as<float>() : NAN;
    packetsSent = doc["packets_sent"] | 0u;
    packetsReceived = doc["packets_received"] | 0u;
    packetsLost = doc["packets_lost"] | 0u;
    packetsForeign = doc["packets_foreign"] | 0u;
    airState = doc["air"] | "";
    batteryMv = doc["battery_mv"].is<int>() ? doc["battery_mv"].as<int>() : INT32_MIN;
    xSemaphoreGive(lock);
}

void onConfigAck(JsonDocument& doc) {
    xSemaphoreTake(lock, portMAX_DELAY);
    // Solo cuenta la respuesta a la última orden: una vieja no la confirma.
    if (doc["seq"].is<uint32_t>() && doc["seq"].as<uint32_t>() == configSeq) {
        const bool ok = doc["ok"] | false;
        configState = ok ? "applied" : "rejected";
        configError = ok ? "" : String(doc["message"] | (doc["error"] | "invalid_setting"));
        powerLimited = (doc["power_limited"] | false) ? 1 : 0;
    }
    rememberSettings(doc);
    xSemaphoreGive(lock);
}
}  // namespace

void begin() {
    lock = xSemaphoreCreateMutex();
    outgoing = xQueueCreate(kQueueFrames, sizeof(Frame));
    // El trabajo lo hace la tarea del canal USB (usb_channel::begin), que llama a
    // onFrame, onRtcm y service.
    ready = lock && outgoing;
}

void onFrame(uint8_t type, const uint8_t* payload, size_t length) {
    if (!ready) return;
    const uint32_t now = millis();
    JsonDocument doc;
    if (deserializeJson(doc, reinterpret_cast<const char*>(payload), length) || !doc.is<JsonObject>()) return;
    if (type == uint8_t(radio_usb::Type::hello)) { onHello(doc, now); return; }
    if (!session.linked) return;   // sin saludo aceptado no se escucha nada más
    session.heard(now);
    if (type == uint8_t(radio_usb::Type::status)) onStatus(doc, now);
    else if (type == uint8_t(radio_usb::Type::config_ack)) onConfigAck(doc);
    // Tipos nuevos que esta versión no conoce: cuentan como latido y se ignoran.
}

void onRtcm(const uint8_t* frame, size_t length) {
    if (!ready || !session.linked) return;   // RTCM de algo que no es un radio enlazado
    if (session.role() == LinkRole::rover &&
        correction_router::submit(correction_router::Source::Radio, frame, length))
        ++framesFromRadio;
    else ++framesRejected;
}

void service(uint32_t now) {
    if (!ready) return;
    const radio_usb::ReceiverSession::Due due = session.tick(wantedRole(), now);
    if (due.lost) forget();
    if (due.role) {
        JsonDocument doc;
        doc["role"] = radio_usb::linkRoleName(session.role());
        sendJson(radio_usb::Type::role, doc);
        // En rover, si nadie eligió otra cosa, la radio se usa sola.
        if (due.changed && session.role() == LinkRole::rover) correction_router::adoptRadio();
    }
    linked = session.linked;
    toldRole = session.role();
    if (session.linked && configPending.exchange(false)) {
        xSemaphoreTake(lock, portMAX_DELAY);
        const String text = pendingConfig;
        xSemaphoreGive(lock);
        uint8_t wire[radio_usb::kMaxFrameBytes];
        const size_t n = radio_usb::encode(radio_usb::Type::config, reinterpret_cast<const uint8_t*>(text.c_str()),
                                           text.length(), wire, sizeof(wire));
        if (n) usb_channel::write(wire, n);
    }
    // Base: lo que produjo el receptor sale hacia el radio, crudo. Sin radio en base,
    // la cola se vacía para no entregar RTCM viejo al reconectar.
    Frame frame;
    while (xQueueReceive(outgoing, &frame, 0) == pdTRUE) {
        if (session.role() != LinkRole::base) continue;
        if (usb_channel::write(frame.bytes, frame.length)) ++framesToRadio;
        else ++framesDropped;
    }
    // Energía (USB_LINK.md §9.2): con el radio enlazado, la v0.3 no toma corriente de VBUS.
    power_manager::blockUsbInput(session.linked);
}

void publish(const uint8_t* frame, size_t length) {
    if (!ready || !linked || toldRole != LinkRole::base || !length || length > radio_usb::kMaxRtcmBytes) return;
    Frame item; item.length = uint16_t(length);
    memcpy(item.bytes, frame, length);
    if (xQueueSend(outgoing, &item, 0) != pdTRUE) ++framesDropped;
}

bool connected() { return linked.load(); }

void status(JsonObject out) {
    const bool on = linked.load();
    out["state"] = !ready ? "start_failed" : on ? "connected" : "not_connected";
    // Aditivo (enlace por USB-C, USB_LINK.md): por dónde va el radio. Hasta 0.9.0 era
    // el Wi-Fi propio (TCP 2102); `port` queda en 0 porque ya no se escucha ningún puerto.
    out["link"] = "usb";
    out["port"] = 0;
    // Aditivo (0.9.0, receiver-identity.md): el radio del MeridianV es el aparato
    // aparte, no uno integrado. Las apps lo usan junto con capabilities.lora_radio.
    out["integrated"] = false;
    out["role"] = on ? radio_usb::linkRoleName(toldRole.load()) : nullptr;
    out["frames_to_radio"] = framesToRadio.load();
    out["frames_from_radio"] = framesFromRadio.load();
    out["frames_rejected"] = framesRejected.load();
    out["frames_dropped"] = framesDropped.load();
    out["connections"] = connections.load();
    out["refused_connections"] = refused.load();
    out["usb_errors"] = usb_channel::errors();
    // Regla de energía: -1 = esta placa no puede (Thing Plus) → null.
    const int hiz = power_manager::usbInputBlocked(), vbus = power_manager::usbPowerPresent();
    if (hiz < 0) out["charger_hiz"] = nullptr; else out["charger_hiz"] = hiz == 1;
    if (vbus < 0) out["vbus_present"] = nullptr; else out["vbus_present"] = vbus == 1;
    xSemaphoreTake(lock, portMAX_DELAY);
    // La última orden de /api/radio: pending hasta que el radio la confirma con su `seq`.
    if (configSeq) out["config_seq"] = configSeq; else out["config_seq"] = nullptr;
    out["config_state"] = configState;
    if (configError.length()) out["config_error"] = configError.c_str(); else out["config_error"] = nullptr;
    if (powerLimited < 0) out["power_limited"] = nullptr; else out["power_limited"] = powerLimited == 1;
    xSemaphoreGive(lock);
    if (!on) return;
    out["protocol"] = protocol.load();
    const uint32_t age = millis() - lastStatusAt.load();
    out["last_status_age_ms"] = age;
    xSemaphoreTake(lock, portMAX_DELAY);
    // Desconocido es null, nunca 0 (un RSSI de 0 dBm sería un disparate creíble).
    out["radio_version"] = radioVersion.length() ? radioVersion.c_str() : nullptr;
    out["radio_id"] = radioId.length() ? radioId.c_str() : nullptr;
    out["hardware"] = radioHardware.length() ? radioHardware.c_str() : nullptr;
    if (network >= 0) out["network"] = network; else out["network"] = nullptr;
    if (channel >= 0) {
        out["channel"] = channel;
        out["frequency_hz"] = radio_air::channelHz(uint8_t(channel));
    } else { out["channel"] = nullptr; out["frequency_hz"] = nullptr; }
    if (powerDbm != INT32_MIN) out["power_dbm"] = powerDbm; else out["power_dbm"] = nullptr;
    if (maxPowerDbm != INT32_MIN) out["max_power_dbm"] = maxPowerDbm; else out["max_power_dbm"] = nullptr;
    if (isnan(rssiDbm)) out["rssi_dbm"] = nullptr; else out["rssi_dbm"] = rssiDbm;
    if (isnan(snrDb)) out["snr_db"] = nullptr; else out["snr_db"] = snrDb;
    out["packets_sent"] = packetsSent;
    out["packets_received"] = packetsReceived;
    out["packets_lost"] = packetsLost;
    out["packets_foreign"] = packetsForeign;
    out["air"] = airState.length() ? airState.c_str() : nullptr;
    if (batteryMv != INT32_MIN) out["battery_mv"] = batteryMv; else out["battery_mv"] = nullptr;
    xSemaphoreGive(lock);
}

int request(const String& method, JsonVariantConst body, JsonDocument& out) {
    if (method == "GET") { status(out.to<JsonObject>()); return 200; }
    if (method != "POST" || !body.is<JsonObjectConst>() || body.size() == 0) return 400;
    JsonDocument config;
    for (JsonPairConst field : body.as<JsonObjectConst>()) {
        const char* key = field.key().c_str();
        if (!strcmp(key, "network") && field.value().is<int>() && field.value().as<int>() >= 0 &&
            field.value().as<int>() <= 255) config["network"] = field.value().as<int>();
        else if (!strcmp(key, "channel") && field.value().is<int>() && field.value().as<int>() >= 0 &&
                 field.value().as<int>() < radio_air::kChannelCount) config["channel"] = field.value().as<int>();
        // Hasta 30 (lo que da la E22): el radio aplica como mucho su tope legal (27 dBm,
        // IFT-008-2015) y lo dice en `power_limited`. Rechazar 28–30 aquí rompería a
        // una app que los mande.
        else if (!strcmp(key, "power_dbm") && field.value().is<int>() && field.value().as<int>() >= 0 &&
                 field.value().as<int>() <= radio_air::kMaxOutputDbm) config["power_dbm"] = field.value().as<int>();
        else {
            out["error"] = "invalid_setting";
            out["message"] = "Solo se cambian network (0–255), channel (0–12) y power_dbm (0–30; el radio aplica hasta 27).";
            return 400;
        }
    }
    if (!linked) {
        out["error"] = "radio_not_connected";
        out["message"] = "No hay ningún radio conectado al USB-C del equipo.";
        return 409;
    }
    xSemaphoreTake(lock, portMAX_DELAY);
    config["seq"] = ++configSeq;
    pendingConfig = "";
    serializeJson(config, pendingConfig);
    configState = "pending";
    configError = "";
    powerLimited = -1;
    xSemaphoreGive(lock);
    configPending = true;
    // Aceptada no es confirmada: el radio contesta con su `seq` y se ve en el GET
    // siguiente (`config_state`: applied o rejected).
    status(out.to<JsonObject>());
    return 202;
}
}  // namespace radio_module
