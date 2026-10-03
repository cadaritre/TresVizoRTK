#include "radio_module.h"
#include "correction_router.h"
#include "gnss_control.h"
#include "radio_air.h"
#include "radio_link.h"
#include <WiFi.h>
#include <atomic>
#include <cstring>

namespace radio_module {
namespace {
// Sin estado del radio en este tiempo, la conexión se da por muerta: el radio
// manda el suyo cada segundo y se vuelve a conectar solo.
constexpr uint32_t kSilenceTimeoutMs = 5000;
// La tarea duerme poco: el RTCM de una época llega de golpe y no debe esperar.
constexpr TickType_t kPollTicks = pdMS_TO_TICKS(5);
// Tramas RTCM de la base esperando a salir hacia el radio; una época MSM4 son
// 5–8 tramas. Si el radio va lento se tiran las nuevas (es estado: la siguiente
// época las repone), nunca se bloquea a quien las produce.
constexpr UBaseType_t kQueueFrames = 8;
constexpr size_t kMaxRtcmBytes = 1029;

struct Frame { uint16_t length; uint8_t bytes[kMaxRtcmBytes]; };

enum class Role : uint8_t { idle, base, rover };
const char* roleName(Role role) {
    return role == Role::base ? "base" : role == Role::rover ? "rover" : "idle";
}

QueueHandle_t outgoing = nullptr;
SemaphoreHandle_t lock = nullptr;
std::atomic<bool> ready{false}, linked{false}, configPending{false};
std::atomic<Role> sentRole{Role::idle};
std::atomic<uint32_t> framesToRadio{0}, framesFromRadio{0}, framesRejected{0}, framesDropped{0},
    connections{0}, refused{0};
std::atomic<uint32_t> lastStatusAt{0};

// Lo que dijo el radio (hola y estado). Bajo `lock`: son cadenas.
String radioVersion, radioId, radioHardware, airState;
int network = -1, channel = -1, powerDbm = INT32_MIN;
float rssiDbm = NAN, snrDb = NAN;
uint32_t packetsSent = 0, packetsReceived = 0, packetsLost = 0, packetsForeign = 0;
// Lo que pidió el usuario por /api/radio, para mandarlo en la próxima pasada.
String pendingConfig;

Role wantedRole() {
    if (gnss_control::isBase()) return Role::base;
    if (gnss_control::isRover()) return Role::rover;
    return Role::idle;
}

// Solo desde la red propia del equipo (192.168.4.x): nunca desde la red externa a
// la que esté unido, donde cualquiera podría inyectar correcciones.
bool fromOwnNetwork(WiFiClient& client) {
    const IPAddress peer = client.remoteIP(), own = WiFi.softAPIP();
    return peer[0] == own[0] && peer[1] == own[1] && peer[2] == own[2];
}

bool sendFrame(WiFiClient& client, radio_link::Type type, const uint8_t* payload, size_t length) {
    uint8_t wire[radio_link::kHeaderBytes + radio_link::kMaxPayloadBytes];
    const size_t n = radio_link::encode(type, payload, length, wire, sizeof(wire));
    return n && client.write(wire, n) == n;
}

bool sendJson(WiFiClient& client, radio_link::Type type, JsonDocument& doc) {
    char text[radio_link::kMaxPayloadBytes];
    const size_t n = serializeJson(doc, text, sizeof(text));
    return n && n < sizeof(text) && sendFrame(client, type, reinterpret_cast<const uint8_t*>(text), n);
}

void remember(radio_link::Type type, const uint8_t* payload, size_t length) {
    JsonDocument doc;
    if (deserializeJson(doc, reinterpret_cast<const char*>(payload), length)) return;
    xSemaphoreTake(lock, portMAX_DELAY);
    if (type == radio_link::Type::hello) {
        radioVersion = doc["radio_version"] | "";
        radioId = doc["radio_id"] | "";
        radioHardware = doc["hardware"] | "";
    }
    if (doc["network"].is<int>()) network = doc["network"];
    if (doc["channel"].is<int>()) channel = doc["channel"];
    if (doc["power_dbm"].is<int>()) powerDbm = doc["power_dbm"];
    if (type == radio_link::Type::status) {
        rssiDbm = doc["rssi_dbm"].is<float>() ? doc["rssi_dbm"].as<float>() : NAN;
        snrDb = doc["snr_db"].is<float>() ? doc["snr_db"].as<float>() : NAN;
        packetsSent = doc["packets_sent"] | 0u;
        packetsReceived = doc["packets_received"] | 0u;
        packetsLost = doc["packets_lost"] | 0u;
        packetsForeign = doc["packets_foreign"] | 0u;
        airState = doc["air"] | "";
    }
    xSemaphoreGive(lock);
}

void forget() {
    xSemaphoreTake(lock, portMAX_DELAY);
    radioVersion = radioId = radioHardware = airState = "";
    network = channel = -1; powerDbm = INT32_MIN; rssiDbm = snrDb = NAN;
    packetsSent = packetsReceived = packetsLost = packetsForeign = 0;
    xSemaphoreGive(lock);
}

void close(WiFiClient& client) {
    client.stop();
    linked = false;
    sentRole = Role::idle;
    forget();
    // La fuente sigue elegida (vuelve sola al reconectar); solo deja de llegar.
}

void worker(void*) {
    WiFiServer server(radio_link::kPort);
    server.begin();
    server.setNoDelay(true);
    WiFiClient client;
    radio_link::Decoder decoder;
    uint8_t buffer[512];
    for (;;) {
        // Aceptar: un radio a la vez. Otro que llegue mientras hay uno vivo se rechaza.
        WiFiClient incoming = server.available();
        if (incoming) {
            if (!fromOwnNetwork(incoming) || (linked && client.connected())) {
                incoming.stop(); ++refused;
            } else {
                client = incoming;
                client.setNoDelay(true);
                decoder.reset();
                linked = true; ++connections;
                lastStatusAt = millis();
                sentRole = Role::idle;
                configPending = false;
            }
        }
        if (linked && !client.connected()) close(client);

        if (linked) {
            // Leer y despachar lo que mande el radio.
            while (client.available() > 0) {
                const int n = client.read(buffer, sizeof(buffer));
                if (n <= 0) break;
                decoder.feed(buffer, size_t(n), [&](radio_link::Type type, const uint8_t* payload, size_t length) {
                    switch (type) {
                        case radio_link::Type::hello:
                            remember(type, payload, length);
                            sentRole = Role::idle;   // que se le diga su papel otra vez
                            break;
                        case radio_link::Type::status:
                            remember(type, payload, length);
                            lastStatusAt = millis();
                            break;
                        case radio_link::Type::rtcm:
                            if (sentRole == Role::rover &&
                                correction_router::submit(correction_router::Source::Radio, payload, length))
                                ++framesFromRadio;
                            else ++framesRejected;
                            break;
                        default: break;   // el radio no manda papel ni configuración
                    }
                });
                if (decoder.broken) break;
            }
            if (decoder.broken || millis() - lastStatusAt.load() > kSilenceTimeoutMs) close(client);
        }

        if (linked) {
            // El papel sigue al modo del receptor; se manda al conectar y al cambiar.
            const Role role = wantedRole();
            if (role != sentRole.load()) {
                JsonDocument doc; doc["role"] = roleName(role);
                if (sendJson(client, radio_link::Type::role, doc)) {
                    sentRole = role;
                    // En rover, si nadie eligió otra cosa, la radio se usa sola.
                    if (role == Role::rover) correction_router::adoptRadio();
                } else close(client);
            }
        }
        if (linked && configPending.exchange(false)) {
            xSemaphoreTake(lock, portMAX_DELAY);
            const String text = pendingConfig;
            xSemaphoreGive(lock);
            if (!sendFrame(client, radio_link::Type::config, reinterpret_cast<const uint8_t*>(text.c_str()), text.length()))
                close(client);
        }

        // Base: lo que produjo el receptor sale hacia el radio. Sin radio que
        // transmita, la cola se vacía para no entregar RTCM viejo al reconectar.
        Frame frame;
        while (xQueueReceive(outgoing, &frame, 0) == pdTRUE) {
            if (!linked || sentRole != Role::base) continue;
            if (sendFrame(client, radio_link::Type::rtcm, frame.bytes, frame.length)) ++framesToRadio;
            else { close(client); break; }
        }
        vTaskDelay(kPollTicks);
    }
}
}  // namespace

void begin() {
    lock = xSemaphoreCreateMutex();
    outgoing = xQueueCreate(kQueueFrames, sizeof(Frame));
    // Pila holgada: dos JsonDocument y un búfer de trama del enlace.
    ready = lock && outgoing && xTaskCreate(worker, "radio_link", 8192, nullptr, 1, nullptr) == pdPASS;
}

void publish(const uint8_t* frame, size_t length) {
    if (!ready || !linked || sentRole != Role::base || !length || length > kMaxRtcmBytes) return;
    Frame item; item.length = uint16_t(length);
    memcpy(item.bytes, frame, length);
    if (xQueueSend(outgoing, &item, 0) != pdTRUE) ++framesDropped;
}

bool connected() { return linked.load(); }

void status(JsonObject out) {
    out["state"] = !ready ? "start_failed" : linked ? "connected" : "not_connected";
    out["port"] = radio_link::kPort;
    out["role"] = linked ? roleName(sentRole.load()) : nullptr;
    out["frames_to_radio"] = framesToRadio.load();
    out["frames_from_radio"] = framesFromRadio.load();
    out["frames_rejected"] = framesRejected.load();
    out["frames_dropped"] = framesDropped.load();
    out["connections"] = connections.load();
    out["refused_connections"] = refused.load();
    if (!linked) return;
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
    if (isnan(rssiDbm)) out["rssi_dbm"] = nullptr; else out["rssi_dbm"] = rssiDbm;
    if (isnan(snrDb)) out["snr_db"] = nullptr; else out["snr_db"] = snrDb;
    out["packets_sent"] = packetsSent;
    out["packets_received"] = packetsReceived;
    out["packets_lost"] = packetsLost;
    out["packets_foreign"] = packetsForeign;
    out["air"] = airState.length() ? airState.c_str() : nullptr;
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
        else if (!strcmp(key, "power_dbm") && field.value().is<int>() && field.value().as<int>() >= 0 &&
                 field.value().as<int>() <= radio_air::kMaxOutputDbm) config["power_dbm"] = field.value().as<int>();
        else {
            out["error"] = "invalid_setting";
            out["message"] = "Solo se cambian network (0–255), channel (0–12) y power_dbm (0–30).";
            return 400;
        }
    }
    if (!linked) {
        out["error"] = "radio_not_connected";
        out["message"] = "No hay ningún radio conectado a la red del equipo.";
        return 409;
    }
    String text; serializeJson(config, text);
    xSemaphoreTake(lock, portMAX_DELAY);
    pendingConfig = text;
    xSemaphoreGive(lock);
    configPending = true;
    // El radio contesta con su estado: el cambio se ve en el siguiente GET.
    status(out.to<JsonObject>());
    return 202;
}
}  // namespace radio_module
