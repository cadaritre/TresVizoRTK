#include "sd_recorder.h"
#include "ntrip_input.h"
#include "gnss_control.h"
#include "memory_health.h"
#include "instrument.h"
#include "gnss_receiver.h"
#include "ble_transport.h"
#include "firmware_update.h"
#include "correction_router.h"
#include "correction_output.h"
#include "config_rules.h"
#include "base_plan.h"
#include "base_survey.h"

#include <Preferences.h>
#include <WiFi.h>
#include <ESPmDNS.h>
#include <atomic>
#include <esp_system.h>
#include <esp_timer.h>

namespace instrument {
namespace {
Preferences preferences;
// El equipo se llama MeridianV y el nombre no se edita: la red que emite debe
// ser reconocible en campo sin consultar a nadie. 3Vizo es la marca del panel.
constexpr const char* kDeviceName = "MeridianV";
String deviceName = kDeviceName;
String stationSsid;
String stationPassword;
String apKey;
String networkName;

// Contraseña de fábrica del Wi-Fi propio. Deliberadamente fija y tecleable: la
// aleatoria de 0.6.0 era imposible de escribir en un teléfono a media jornada.
// Va escrita en el repositorio, así que no protege de nadie que lo lea; el
// propietario la cambia desde Configuración cuando quiera otra.
constexpr const char* kDefaultApPassword = "TresVIzoRTK";
uint32_t refreshMs = 2000;
uint32_t revision = 0;
bool storageReady = false;
bool configValid = true;
bool apReady = false;
bool pendingNetwork = false;
uint32_t networkChangedAt = 0;
uint32_t lastConnectionAttempt = 0;
bool pendingRestart = false;
uint32_t restartRequestedAt = 0;
// Espejo atómico de la existencia de redes guardadas: la tarea NTRIP lo lee
// sin tomar el mutex del instrumento, y leer los String directamente sería una
// carrera con saveConfig.
std::atomic<bool> stationPresent{false};

// Tope deliberado de redes guardadas. La partición NVS son 20 KB y ahí conviven
// además la clave del panel, la contraseña del AP y el PIN de emparejamiento.
// Cada entrada ronda los 125 bytes entre SSID, contraseña y envoltura JSON.
constexpr size_t kMaxNetworks = 5;
struct SavedNetwork {
    String ssid;
    String password;
    // Dirección fija opcional, por red y no global: con varias redes guardadas
    // en subredes distintas, una sola IP fija sería correcta en una y estaría
    // equivocada en el resto. Vacío significa DHCP.
    String ip;
    String gateway;
    String mask;
};
SavedNetwork networks[kMaxNetworks];
size_t networkCount = 0;

// El escaneo es asíncrono porque uno bloqueante detendría el servidor HTTP
// varios segundos. Aun así la radio recorre los canales y el AP propio se
// interrumpe mientras tanto: quien mire el panel desde la red del equipo verá
// un corte. No es un fallo del panel.
enum class ScanState : uint8_t { idle, running, ready, failed };
ScanState scanState = ScanState::idle;
uint32_t scanStartedAt = 0;
uint32_t scanFinishedAt = 0;
int scanFound = 0;
bool joinRequested = false;

void error(JsonDocument& response, const char* code, const char* message) {
    response["error"] = code;
    response["message"] = message;
}

void config(JsonDocument& response) {
    response["schema_version"] = 1;
    response["revision"] = revision;
    response["device_name"] = deviceName;
    response["refresh_ms"] = refreshMs;
    response["wifi_ssid"] = stationSsid;
    response["wifi_password_saved"] = !stationPassword.isEmpty();
    // Las contraseñas guardadas no salen nunca del equipo: solo el nombre y si
    // hay credencial almacenada.
    JsonArray saved = response["networks"].to<JsonArray>();
    for (size_t i = 0; i < networkCount; ++i) {
        JsonObject item = saved.add<JsonObject>();
        item["ssid"] = networks[i].ssid;
        item["has_password"] = !networks[i].password.isEmpty();
        item["ip"] = networks[i].ip;
        item["gateway"] = networks[i].gateway;
        item["mask"] = networks[i].mask;
    }
    response["networks_max"] = kMaxNetworks;
    response["ap_ssid"] = networkName;
    // El panel no pide clave, así que ocultar la del AP aquí no protegería nada
    // y en cambio impediría leerla para unir un teléfono.
    response["ap_password"] = apKey;
    response["persistence_ready"] = storageReady;
    response["stored_config_valid"] = configValid;
}

int findNetwork(const String& ssid) {
    for (size_t i = 0; i < networkCount; ++i) {
        if (networks[i].ssid == ssid) return static_cast<int>(i);
    }
    return -1;
}

void startScan() {
    WiFi.scanDelete();
    scanFound = 0;
    scanStartedAt = millis();
    scanState = WiFi.scanNetworks(true, false) == WIFI_SCAN_RUNNING
        ? ScanState::running : ScanState::failed;
    if (scanState == ScanState::failed) scanFinishedAt = scanStartedAt;
}

void connectTo(const SavedNetwork& network) {
    WiFi.disconnect(false, false);
    lastConnectionAttempt = millis();
    stationSsid = network.ssid;
    stationPassword = network.password;
    IPAddress ip, gateway, mask;
    // Si la red trae dirección fija se aplica; si no, se devuelve el interfaz a
    // DHCP explícitamente, porque una configuración estática anterior seguiría
    // vigente y dejaría el equipo inalcanzable en la red siguiente.
    if (!network.ip.isEmpty() && ip.fromString(network.ip) &&
        gateway.fromString(network.gateway) && mask.fromString(network.mask)) {
        // El gateway hace también de DNS: en una red de obra no hay otro.
        WiFi.config(ip, gateway, mask, gateway);
    } else {
        WiFi.config(INADDR_NONE, INADDR_NONE, INADDR_NONE);
    }
    WiFi.begin(network.ssid.c_str(), network.password.c_str());
}

// Elige, entre las redes guardadas que el escaneo vio de verdad, la de mejor
// señal. No intenta una red que no esté a la vista: esperar el tiempo de espera
// de asociación sobre una red ausente retrasa la que sí está.
bool joinBestVisible() {
    int best = -1;
    int32_t bestRssi = 0;
    for (int i = 0; i < scanFound; ++i) {
        const int index = findNetwork(WiFi.SSID(i));
        if (index < 0) continue;
        const int32_t rssi = WiFi.RSSI(i);
        if (best < 0 || rssi > bestRssi) {
            best = index;
            bestRssi = rssi;
        }
    }
    if (best < 0) return false;
    connectTo(networks[best]);
    return true;
}

// Persiste el registro completo. Recibe la lista candidata en vez de leer la
// activa para no publicar ajustes que no llegaron a escribirse.
bool persistConfig(uint32_t nextRevision, const String& name, uint32_t refresh,
                   const SavedNetwork* list, size_t count) {
    if (!storageReady) return false;
    JsonDocument record;
    record["schema_version"] = 2;
    record["revision"] = nextRevision;
    record["device_name"] = name;
    record["refresh_ms"] = refresh;
    JsonArray saved = record["networks"].to<JsonArray>();
    for (size_t i = 0; i < count; ++i) {
        JsonObject item = saved.add<JsonObject>();
        item["ssid"] = list[i].ssid;
        item["password"] = list[i].password;
        if (!list[i].ip.isEmpty()) {
            item["ip"] = list[i].ip;
            item["gateway"] = list[i].gateway;
            item["mask"] = list[i].mask;
        }
    }
    String encoded;
    serializeJson(record, encoded);
    // Una única entrada NVS: no publicar ajustes parcialmente persistidos.
    return preferences.putString("config", encoded) == encoded.length();
}

void adoptNetworks(const SavedNetwork* list, size_t count) {
    for (size_t i = 0; i < kMaxNetworks; ++i) {
        networks[i].ssid = i < count ? list[i].ssid : String();
        networks[i].password = i < count ? list[i].password : String();
        networks[i].ip = i < count ? list[i].ip : String();
        networks[i].gateway = i < count ? list[i].gateway : String();
        networks[i].mask = i < count ? list[i].mask : String();
    }
    networkCount = count;
    stationPresent = count > 0;
    // Si la red a la que se está enlazado ya no figura en la lista, soltarla y
    // volver a buscar. Seguir asociado a una red que el usuario acaba de borrar
    // contradice lo que muestra el panel.
    if (!count || (!stationSsid.isEmpty() && findNetwork(stationSsid) < 0)) {
        WiFi.disconnect(false, false);
        stationSsid = "";
        stationPassword = "";
        joinRequested = count > 0;
    }
}

bool validString(JsonVariantConst field, bool (*rule)(const char*)) {
    if (!field.is<const char*>()) return false;
    const JsonString value = field.as<JsonString>();
    return value.size() == strlen(value.c_str()) && rule(value.c_str());
}

int saveConfig(JsonVariantConst body, JsonDocument& response) {
    if (!body.is<JsonObjectConst>()) {
        error(response, "invalid_request", "Se esperaba un objeto de configuración.");
        return 400;
    }
    for (JsonPairConst pair : body.as<JsonObjectConst>()) {
        if (pair.value().isNull()) {
            error(response, "invalid_setting", "Los ajustes no pueden tener valores nulos.");
            return 400;
        }
        const String name = pair.key().c_str();
        if (name != "revision" && name != "device_name" && name != "refresh_ms" &&
            name != "wifi_ssid" && name != "wifi_password" && name != "forget_wifi" &&
            name != "ap_password") {
            error(response, "unknown_setting", "La solicitud contiene un ajuste no admitido.");
            return 400;
        }
    }
    if (!body["revision"].is<uint32_t>() || body["revision"].as<uint32_t>() != revision) {
        error(response, "revision_conflict", "Los ajustes cambiaron. Vuelve a cargarlos antes de guardar.");
        return 409;
    }
    String nextName = deviceName;
    String requestedSsid;
    String requestedPassword;
    bool hasSsid = false;
    uint32_t nextRefresh = refreshMs;
    // El nombre del equipo es fijo. Se sigue admitiendo el campo para no romper
    // clientes antiguos, pero se ignora: cambiarlo renombraría la red del
    // instrumento y dejaría de ser reconocible en campo.
    if (!body["device_name"].isNull() && !validString(body["device_name"], config_rules::deviceName)) {
        error(response, "invalid_name", "Usa entre 1 y 32 letras sin acentos, números, espacios, guiones o guiones bajos.");
        return 400;
    }
    if (!body["refresh_ms"].isNull()) {
        if (!body["refresh_ms"].is<uint32_t>() || !config_rules::refresh(body["refresh_ms"].as<uint32_t>())) {
            error(response, "invalid_refresh", "El intervalo debe ser 1000, 2000 o 5000 ms.");
            return 400;
        }
        nextRefresh = body["refresh_ms"].as<uint32_t>();
    }
    String nextApKey = apKey;
    if (!body["ap_password"].isNull()) {
        if (!validString(body["ap_password"], config_rules::password)) {
            error(response, "invalid_ap_password", "La contraseña del Wi-Fi del equipo debe tener entre 8 y 63 caracteres ASCII imprimibles.");
            return 400;
        }
        nextApKey = body["ap_password"].as<const char*>();
    }
    if (!body["forget_wifi"].isNull() && !body["forget_wifi"].is<bool>()) {
        error(response, "invalid_wifi", "La opción de olvidar red debe ser booleana.");
        return 400;
    }
    if (!body["wifi_ssid"].isNull()) {
        if (!validString(body["wifi_ssid"], config_rules::ssid)) {
            error(response, "invalid_ssid", "El nombre de red no puede superar 32 bytes ni contener controles.");
            return 400;
        }
        requestedSsid = body["wifi_ssid"].as<const char*>();
        hasSsid = !requestedSsid.isEmpty();
    }
    if (!body["wifi_password"].isNull()) {
        if (!body["wifi_password"].is<const char*>()) {
            error(response, "invalid_password", "La contraseña debe ser texto.");
            return 400;
        }
        JsonString value = body["wifi_password"].as<JsonString>();
        if (value.size() != strlen(value.c_str()) ||
            (value.size() && !config_rules::password(value.c_str()))) {
            error(response, "invalid_password", "Usa entre 8 y 63 caracteres ASCII imprimibles.");
            return 400;
        }
        if (value.size()) requestedPassword = value.c_str();
    }
    if (!storageReady) {
        error(response, "storage_unavailable", "No se pudo abrir el almacenamiento interno de ajustes.");
        return 503;
    }
    // La lista candidata se arma aparte y solo se adopta si el registro llegó a
    // escribirse. Así un fallo de NVS deja intacta la configuración activa.
    SavedNetwork candidate[kMaxNetworks];
    size_t candidateCount = networkCount;
    for (size_t i = 0; i < networkCount; ++i) candidate[i] = networks[i];
    bool networksChanged = false;
    if (body["forget_wifi"] == true) {
        networksChanged = candidateCount > 0;
        candidateCount = 0;
    } else if (hasSsid) {
        const int existing = findNetwork(requestedSsid);
        String password = requestedPassword;
        if (password.isEmpty()) {
            if (existing < 0) {
                error(response, "password_required", "Introduce la contraseña de la red seleccionada. Solo se admiten redes protegidas.");
                return 400;
            }
            password = candidate[existing].password;
        }
        if (existing >= 0) {
            networksChanged = candidate[existing].password != password;
            candidate[existing].password = password;
        } else if (candidateCount == kMaxNetworks) {
            error(response, "networks_full", "Se alcanzó el máximo de redes guardadas de este equipo. Olvida una antes de añadir otra.");
            return 409;
        } else {
            candidate[candidateCount].ssid = requestedSsid;
            candidate[candidateCount].password = password;
            ++candidateCount;
            networksChanged = true;
        }
    }
    const bool changed = nextName != deviceName || nextRefresh != refreshMs ||
        networksChanged || nextApKey != apKey || !configValid;
    if (!changed) {
        config(response);
        response["saved"] = true;
        response["changed"] = false;
        return 200;
    }
    if (!persistConfig(revision + 1, nextName, nextRefresh, candidate, candidateCount)) {
        error(response, "save_failed", "No se pudieron guardar los ajustes. La configuración activa se conserva.");
        return 503;
    }
    if (networksChanged) {
        pendingNetwork = true;
        networkChangedAt = millis();
    }
    deviceName = nextName;
    refreshMs = nextRefresh;
    adoptNetworks(candidate, candidateCount);
    ++revision;
    configValid = true;
    // La contraseña del AP vive en su propia entrada NVS, no en el registro de
    // ajustes: se escribe aparte y se informa si esa parte no llegó a guardarse.
    bool apSaved = true;
    if (nextApKey != apKey) {
        apSaved = preferences.putString("ap_password", nextApKey) == nextApKey.length() &&
            preferences.putBool("ap_custom", true) != 0;
        if (apSaved) {
            apKey = nextApKey;
            // Reaplicar el AP corta a quien estuviera conectado a la red del equipo.
            apReady = WiFi.softAP(networkName.c_str(), apKey.c_str(), 1, false, 4);
        }
    }
    config(response);
    response["saved"] = true;
    response["changed"] = true;
    response["ap_password_saved"] = apSaved;
    if (!apSaved) {
        response["message"] = "Los ajustes se guardaron, pero la contraseña del Wi-Fi del equipo no. Sigue activa la anterior.";
    }
    return 200;
}

// Tope de redes informadas por escaneo. Un entorno urbano devuelve decenas y la
// respuesta se arma entera en memoria antes de enviarse.
constexpr int kMaxScanReported = 20;

int wifiNetworks(const String& method, JsonVariantConst body, JsonDocument& response) {
    if (method == "GET") {
        config(response);
        return 200;
    }
    if (!body.is<JsonObjectConst>()) {
        error(response, "invalid_request", "Se esperaba un objeto con la red.");
        return 400;
    }
    for (JsonPairConst pair : body.as<JsonObjectConst>()) {
        const String name = pair.key().c_str();
        if (name != "ssid" && name != "password" && name != "forget" &&
            name != "ip" && name != "gateway" && name != "mask") {
            error(response, "unknown_setting", "La solicitud contiene un campo no admitido.");
            return 400;
        }
    }
    if (!storageReady) {
        error(response, "storage_unavailable", "No se pudo abrir el almacenamiento interno de ajustes.");
        return 503;
    }
    SavedNetwork candidate[kMaxNetworks];
    size_t count = networkCount;
    for (size_t i = 0; i < networkCount; ++i) candidate[i] = networks[i];
    if (!body["forget"].isNull()) {
        if (!validString(body["forget"], config_rules::ssid)) {
            error(response, "invalid_ssid", "El nombre de red no puede superar 32 bytes ni contener controles.");
            return 400;
        }
        const int index = findNetwork(body["forget"].as<const char*>());
        if (index < 0) {
            error(response, "not_found", "Esa red no está guardada.");
            return 404;
        }
        for (size_t i = static_cast<size_t>(index); i + 1 < count; ++i) candidate[i] = candidate[i + 1];
        --count;
        candidate[count].ssid = "";
        candidate[count].password = "";
    } else {
        if (!validString(body["ssid"], config_rules::ssid)) {
            error(response, "invalid_ssid", "El nombre de red no puede superar 32 bytes ni contener controles.");
            return 400;
        }
        const String ssid = body["ssid"].as<const char*>();
        if (ssid.isEmpty()) {
            error(response, "invalid_ssid", "Indica el nombre de la red.");
            return 400;
        }
        const int index = findNetwork(ssid);
        String password;
        if (!body["password"].isNull()) {
            if (!validString(body["password"], config_rules::password)) {
                error(response, "invalid_password", "Usa entre 8 y 63 caracteres ASCII imprimibles.");
                return 400;
            }
            password = body["password"].as<const char*>();
        }
        if (password.isEmpty()) {
            if (index < 0) {
                error(response, "password_required", "Introduce la contraseña de la red. Solo se admiten redes protegidas.");
                return 400;
            }
            password = candidate[index].password;
        }
        // Dirección fija opcional. Las tres van juntas o ninguna: una IP sin
        // máscara ni puerta de enlace deja el equipo incomunicado.
        String fixedIp, fixedGateway, fixedMask;
        // Mencionar los campos vacíos es la forma de volver a dirección
        // automática: exigir que fueran válidos impediría desactivarla.
        const bool mentionsAddress = !body["ip"].isNull() || !body["gateway"].isNull() || !body["mask"].isNull();
        const char* rawIp = body["ip"].is<const char*>() ? body["ip"].as<const char*>() : "";
        const char* rawGateway = body["gateway"].is<const char*>() ? body["gateway"].as<const char*>() : "";
        const char* rawMask = body["mask"].is<const char*>() ? body["mask"].as<const char*>() : "";
        const bool wantsFixed = *rawIp || *rawGateway || *rawMask;
        if (wantsFixed) {
            IPAddress probe;
            if (!probe.fromString(rawIp) || !probe.fromString(rawGateway) || !probe.fromString(rawMask)) {
                error(response, "invalid_address", "Para una dirección fija hacen falta IP, puerta de enlace y máscara, las tres válidas. Déjalas vacías para volver a dirección automática.");
                return 400;
            }
            fixedIp = rawIp;
            fixedGateway = rawGateway;
            fixedMask = rawMask;
        }
        if (index >= 0) {
            candidate[index].password = password;
            // Si la petición menciona la dirección, se adopta tal cual: con
            // valores, la fija; vacía, vuelve a automática.
            if (mentionsAddress) {
                candidate[index].ip = fixedIp;
                candidate[index].gateway = fixedGateway;
                candidate[index].mask = fixedMask;
            }
        } else if (count == kMaxNetworks) {
            error(response, "networks_full", "Se alcanzó el máximo de redes guardadas de este equipo. Olvida una antes de añadir otra.");
            return 409;
        } else {
            candidate[count].ssid = ssid;
            candidate[count].password = password;
            candidate[count].ip = fixedIp;
            candidate[count].gateway = fixedGateway;
            candidate[count].mask = fixedMask;
            ++count;
        }
    }
    if (!persistConfig(revision + 1, deviceName, refreshMs, candidate, count)) {
        error(response, "save_failed", "No se pudieron guardar las redes. La lista activa se conserva.");
        return 503;
    }
    adoptNetworks(candidate, count);
    ++revision;
    configValid = true;
    pendingNetwork = true;
    networkChangedAt = millis();
    config(response);
    response["saved"] = true;
    return 200;
}

int wifiScan(const String& method, JsonDocument& response) {
    if (method == "POST") {
        if (firmware_update::busy()) {
            error(response, "busy", "Hay una carga de firmware en curso. Espera a que termine antes de escanear.");
            return 409;
        }
        // Escanear obliga a la radio a recorrer los canales: una sesión NTRIP en
        // marcha perdería la conexión con el caster a media corrección.
        if (ntrip_input::active()) {
            error(response, "busy", "Hay correcciones NTRIP activas. Detenlas antes de buscar redes: el escaneo interrumpe la radio.");
            return 409;
        }
        if (scanState != ScanState::running) startScan();
    }
    response["state"] = scanState == ScanState::running ? "scanning"
        : (scanState == ScanState::ready ? "ready"
        : (scanState == ScanState::failed ? "failed" : "idle"));
    response["networks_max"] = kMaxNetworks;
    response["networks_saved"] = networkCount;
    // El escaneo interrumpe el AP propio mientras recorre los canales.
    response["disrupts_ap"] = true;
    JsonArray found = response["networks"].to<JsonArray>();
    if (scanState == ScanState::ready) {
        const int reported = scanFound < kMaxScanReported ? scanFound : kMaxScanReported;
        for (int i = 0; i < reported; ++i) {
            const String ssid = WiFi.SSID(i);
            if (ssid.isEmpty()) continue; // red oculta: no se puede guardar por nombre
            JsonObject item = found.add<JsonObject>();
            item["ssid"] = ssid;
            item["rssi_dbm"] = WiFi.RSSI(i);
            item["secure"] = WiFi.encryptionType(i) != WIFI_AUTH_OPEN;
            item["saved"] = findNetwork(ssid) >= 0;
        }
        response["truncated"] = scanFound > kMaxScanReported;
        response["age_ms"] = millis() - scanFinishedAt;
    } else {
        response["truncated"] = false;
        response["age_ms"] = nullptr;
    }
    return method == "POST" ? 202 : 200;
}

void status(JsonDocument& response) {
    response["api_version"] = 1;
    response["firmware_version"] = kVersion;
    response["device_name"] = deviceName;
    response["phase"] = "commissioning";
    response["uptime_ms"] = static_cast<uint64_t>(esp_timer_get_time() / 1000);
    memory_health::status(response["memory"].to<JsonObject>());
    response["free_heap_bytes"] = ESP.getFreeHeap();
    response["min_free_heap_bytes"] = ESP.getMinFreeHeap();
    response["chip"] = ESP.getChipModel();
    response["chip_revision"] = ESP.getChipRevision();
    response["cpu_mhz"] = ESP.getCpuFreqMHz();
    response["flash_bytes"] = ESP.getFlashChipSize();
    response["psram_enabled_bytes"] = ESP.getPsramSize();
    response["reset_reason_code"] = static_cast<int>(esp_reset_reason());
    response["config_ready"] = storageReady && configValid;
    response["refresh_ms"] = refreshMs;
    JsonObject wifi = response["wifi"].to<JsonObject>();
    wifi["ap_ready"] = apReady;
    wifi["ap_ssid"] = networkName;
    wifi["ap_ip"] = WiFi.softAPIP().toString();
    wifi["ap_clients"] = WiFi.softAPgetStationNum();
    const bool connected = WiFi.status() == WL_CONNECTED;
    wifi["station_state"] = !networkCount ? "not_configured"
        : (connected ? "connected" : (scanState == ScanState::running ? "scanning" : "connecting"));
    wifi["station_ssid"] = stationSsid;
    wifi["networks_saved"] = networkCount;
    if (connected) {
        wifi["station_ip"] = WiFi.localIP().toString();
        wifi["rssi_dbm"] = WiFi.RSSI();
    } else {
        wifi["station_ip"] = nullptr;
        wifi["rssi_dbm"] = nullptr;
    }
    for (const char* subsystem : {"gnss", "imu", "microsd", "ntrip", "ble"}) {
        response["subsystems"][subsystem]["state"] = "not_integrated";
    }
    ble_transport::status(response["subsystems"]["ble"].as<JsonObject>());
    ntrip_input::status(response["subsystems"]["ntrip"].as<JsonObject>());
    // Fuente y antigüedad de correcciones en el estado general: la vista de
    // campo las necesita en cada refresco y no debe pedir una segunda ruta.
    // Papel del receptor: sin esto el panel puede afirmar a la vez que el
    // equipo es base y que está recibiendo correcciones.
    response["receiver_role"] = gnss_control::isBase() ? "base"
        : (gnss_control::roverReady() ? "rover" : "unknown");
    correction_router::status(response["corrections"].to<JsonObject>());
    // Alarmas: lo que hay que mirar, no números que haya que interpretar. Los
    // dos fallos que más costaron en banco (receptor mudo y NTRIP esperando red
    // para siempre) no los delataba ningún contador a simple vista.
    JsonArray alerts = response["alerts"].to<JsonArray>();
    const auto raise = [&alerts](const char* code, const char* level, const char* text) {
        JsonObject item = alerts.add<JsonObject>();
        item["code"] = code; item["level"] = level; item["message"] = text;
    };
    const auto receiver = gnss_receiver::snapshot();
    if (receiver.enabled && !receiver.accepted) {
        raise("receiver_silent", "error",
              "El enlace con el receptor funciona pero no emite posiciones. Suele ser que perdió sus salidas: aplica una frecuencia en GPS avanzado.");
    }
    if (receiver.start_failed) {
        raise("uart_failed", "error", "La UART del receptor no arrancó.");
    }
    {
        const uint32_t age = correction_router::ageMs();
        if (correction_router::sourceCode() && age != UINT32_MAX && age > 30000) {
            raise("corrections_stale", "warning",
                  "Hay una fuente de correcciones activa pero no llega ninguna desde hace más de 30 s.");
        }
    }
    if (gnss_control::isBase() && correction_router::sourceCode()) {
        raise("base_consuming_corrections", "warning",
              "El receptor es base y además tiene una entrada de correcciones activa. Una base emite correcciones, no las consume: detén la entrada.");
    }
    if (correction_output::active() && !gnss_control::isBase()) {
        raise("publishing_without_base", "warning",
              "Se está publicando correcciones pero el receptor no está en modo base: no hay RTCM que enviar.");
    }
    if (!networkCount) {
        raise("no_network", "info", "No hay redes Wi-Fi guardadas: el equipo no puede salir a internet.");
    }
    if (esp_reset_reason() == ESP_RST_PANIC) {
        raise("last_reset_panic", "warning", "El último reinicio fue por un fallo del firmware, no por corte de corriente.");
    }
    if (esp_reset_reason() == ESP_RST_BROWNOUT) {
        raise("last_reset_brownout", "warning", "El último reinicio fue por caída de tensión. Revisa cable y alimentación.");
    }
    // Que el watchdog actúe es una buena noticia (el equipo se recuperó solo)
    // pero significa que una tarea se quedó bloqueada: hay que saberlo.
    if (esp_reset_reason() == ESP_RST_TASK_WDT || esp_reset_reason() == ESP_RST_INT_WDT ||
        esp_reset_reason() == ESP_RST_WDT) {
        raise("last_reset_watchdog", "warning",
              "El último reinicio lo provocó el watchdog: una tarea dejó de responder y el equipo se reinició solo. Anota qué estabas haciendo.");
    }
    correction_output::status(response["corrections_out"].to<JsonObject>());
    sd_recorder::status(response["subsystems"]["microsd"].as<JsonObject>());
    response["solution"]["fix"] = nullptr;
    response["solution"]["latitude_deg"] = nullptr;
    response["solution"]["longitude_deg"] = nullptr;
    response["solution"]["height_m"] = nullptr;
    response["solution"]["height_reference"] = nullptr;
    response["solution"]["hdop"] = nullptr;
    // Estimación del receptor, no exactitud verificada. Nula mientras no llegue GST.
    response["solution"]["horizontal_sigma_m"] = nullptr;
    response["solution"]["vertical_sigma_m"] = nullptr;
    response["solution"]["arrival_time_us"] = nullptr;
    const auto gnss = gnss_receiver::snapshot();
    JsonObject health = response["subsystems"]["gnss"].as<JsonObject>();
    health["state"] = gnss.start_failed ? "start_failed" : "not_integrated";
    health["accepted_gga"] = gnss.accepted;
    health["rejected_gga"] = gnss.rejected;
    health["line_overflows"] = gnss.overflow;
    health["uart_errors"] = gnss.uart_errors;
    // Ultimo salto de la cadena RTK: sin estas cifras no se puede saber si el
    // RTCM aceptado por el router llegó realmente al receptor.
    health["correction_frames_sent"] = gnss.correction_frames_sent;
    health["correction_frames_dropped"] = gnss.correction_frames_dropped;
    // Salud del binario nativo Unicore; es el formato de OBSVMB usado para PPK.
    health["native_frames_valid"] = gnss.native_valid;
    health["native_frames_invalid"] = gnss.native_invalid;
    if (gnss.enabled) {
        const uint64_t now = esp_timer_get_time();
        const uint64_t age = now - gnss.solution.arrival_us;
        const bool fresh = gnss.accepted && age <= 500000;
        health["state"] = !gnss.accepted ? "waiting_data" : (fresh ? "receiving" : "stale");
        if (gnss.accepted) health["age_ms"] = age / 1000;
        if (fresh) {
            auto out = response["solution"].as<JsonObject>();
            out["quality_code"] = gnss.solution.quality;
            static const char* const qualities[] = {"invalid", "standalone", "differential",
                "pps", "rtk_fixed", "rtk_float", "dead_reckoning", "manual", "simulated"};
            out["fix"] = qualities[gnss.solution.quality];
            if (gnss.solution.has_satellites) out["satellites_used"] = gnss.solution.satellites;
            if (std::isfinite(gnss.solution.hdop)) out["hdop"] = gnss.solution.hdop;
            // GST llega en su propia trama: solo se publica si es tan reciente
            // como la posición, para no mezclar una sigma vieja con un fix nuevo.
            if (gnss.precision_accepted && now - gnss.precision.arrival_us <= 2000000) {
                if (std::isfinite(gnss.precision.horizontal_sigma_m))
                    out["horizontal_sigma_m"] = gnss.precision.horizontal_sigma_m;
                if (std::isfinite(gnss.precision.altitude_sigma_m))
                    out["vertical_sigma_m"] = gnss.precision.altitude_sigma_m;
            }
            out["arrival_time_us"] = gnss.solution.arrival_us;
            if (gnss.solution.has_utc) out["utc_time_of_day_ms"] = gnss.solution.utc_ms;
            // GGA no aporta fecha ni demuestra el datum configurado.
            if (gnss.solution.has_position) {
                out["latitude_deg"] = gnss.solution.latitude_deg;
                out["longitude_deg"] = gnss.solution.longitude_deg;
                if (std::isfinite(gnss.solution.altitude_msl_m)) {
                    out["height_m"] = gnss.solution.altitude_msl_m;
                    out["height_reference"] = gnss_control::heightReference();
                }
                if (std::isfinite(gnss.solution.geoid_separation_m))
                    out["geoid_separation_m"] = gnss.solution.geoid_separation_m;
            }
        }
    }
}
}

void begin() {
    storageReady = preferences.begin("tresvizo", false);
    if (storageReady) {
        const String saved = preferences.getString("config", "");
        if (!saved.isEmpty()) {
            JsonDocument record;
            // La lista de redes añade un nivel: objeto raíz, array y objeto.
            const auto parsed = deserializeJson(record, saved, DeserializationOption::NestingLimit(4));
            const int schema = record["schema_version"] | 0;
            configValid = !parsed && (schema == 1 || schema == 2) &&
                validString(record["device_name"], config_rules::deviceName) &&
                record["revision"].is<uint32_t>() && record["refresh_ms"].is<uint32_t>() &&
                config_rules::refresh(record["refresh_ms"].as<uint32_t>());
            SavedNetwork loaded[kMaxNetworks];
            size_t loadedCount = 0;
            if (configValid && schema == 1) {
                // Registro de una sola red: se migra a la lista sin perderla.
                configValid = validString(record["wifi_ssid"], config_rules::ssid) &&
                    record["wifi_password"].is<const char*>();
                if (configValid) {
                    const String ssid = record["wifi_ssid"].as<const char*>();
                    if (!ssid.isEmpty()) {
                        configValid = validString(record["wifi_password"], config_rules::password);
                        if (configValid) {
                            loaded[0].ssid = ssid;
                            loaded[0].password = record["wifi_password"].as<const char*>();
                            loadedCount = 1;
                        }
                    }
                }
            } else if (configValid) {
                configValid = record["networks"].is<JsonArrayConst>();
                if (configValid) {
                    for (JsonVariantConst item : record["networks"].as<JsonArrayConst>()) {
                        if (loadedCount == kMaxNetworks) break;
                        if (!validString(item["ssid"], config_rules::ssid) ||
                            !validString(item["password"], config_rules::password)) {
                            configValid = false;
                            break;
                        }
                        const String ssid = item["ssid"].as<const char*>();
                        if (ssid.isEmpty()) {
                            configValid = false;
                            break;
                        }
                        loaded[loadedCount].ssid = ssid;
                        loaded[loadedCount].password = item["password"].as<const char*>();
                        loaded[loadedCount].ip = item["ip"].is<const char*>() ? item["ip"].as<const char*>() : "";
                        loaded[loadedCount].gateway = item["gateway"].is<const char*>() ? item["gateway"].as<const char*>() : "";
                        loaded[loadedCount].mask = item["mask"].is<const char*>() ? item["mask"].as<const char*>() : "";
                        ++loadedCount;
                    }
                }
            }
            if (configValid) {
                deviceName = record["device_name"].as<const char*>();
                revision = record["revision"].as<uint32_t>();
                refreshMs = record["refresh_ms"].as<uint32_t>();
                adoptNetworks(loaded, loadedCount);
            }
        }
    }
    stationPresent = networkCount > 0;
    WiFi.persistent(false);
    WiFi.mode(WIFI_AP_STA); // radio activa para la fuente de entropía del RNG
    // Solo se respeta una contraseña guardada si el propietario la fijó a
    // propósito desde Configuración. Un equipo que venía con la aleatoria de
    // 0.6.0 vuelve así al valor de fábrica, que sí se puede teclear.
    apKey = "";
    if (storageReady && preferences.getBool("ap_custom", false)) {
        apKey = preferences.getString("ap_password", "");
    }
    if (!config_rules::password(apKey.c_str())) apKey = kDefaultApPassword;
    // Sin sufijo de MAC: el nombre es del producto, no de la unidad. Si algún día
    // hay dos equipos encendidos en la misma obra, sus redes se verán iguales.
    deviceName = kDeviceName;
    networkName = kDeviceName;
    WiFi.setAutoReconnect(true);
    WiFi.setHostname("meridianv");
    // Nombre en la red local: "meridianv.local" sigue funcionando aunque el
    // DHCP reparta otra dirección en la siguiente conexión.
    MDNS.begin("meridianv");
    MDNS.addService("http", "tcp", 80);
    WiFi.softAPConfig(IPAddress(192, 168, 4, 1), IPAddress(192, 168, 4, 1), IPAddress(255, 255, 255, 0));
    apReady = WiFi.softAP(networkName.c_str(), apKey.c_str(), 1, false, 4);
    // Al encender no se fuerza una red concreta: el primer tick escanea y se
    // une a la red guardada que esté realmente a la vista.
    joinRequested = networkCount > 0;
}

void tick() {
    const uint32_t now = millis();
    if (pendingRestart && config_rules::elapsed(now, restartRequestedAt, 1000)) ESP.restart();
    if (pendingNetwork && config_rules::elapsed(now, networkChangedAt, 1000)) {
        pendingNetwork = false;
        joinRequested = networkCount > 0;
    }
    if (scanState == ScanState::running) {
        const int16_t found = WiFi.scanComplete();
        if (found >= 0) {
            scanFound = found;
            scanState = ScanState::ready;
            scanFinishedAt = now;
            // Los resultados se aprovechan venga el escaneo de donde venga: si
            // el equipo está suelto, se une sin pedir otro barrido.
            if (networkCount && WiFi.status() != WL_CONNECTED && !joinBestVisible()) {
                lastConnectionAttempt = now;
            }
        } else if (found == WIFI_SCAN_FAILED || config_rules::elapsed(now, scanStartedAt, 20000)) {
            scanState = ScanState::failed;
            scanFinishedAt = now;
            lastConnectionAttempt = now;
        }
    }
    if (networkCount && scanState != ScanState::running && WiFi.status() != WL_CONNECTED &&
        (joinRequested || config_rules::elapsed(now, lastConnectionAttempt, 30000))) {
        joinRequested = false;
        startScan();
    }
}

const String& apPassword() { return apKey; }
bool stationConfigured() { return stationPresent.load(); }
// Nota: informa de que hay al menos una red guardada, no de que haya enlace.
const String& apName() { return networkName; }

int previewBase(JsonVariantConst body, JsonDocument& response) {
    if (!body.is<JsonObjectConst>()) { error(response, "invalid_plan", "Se esperaba un plan de base."); return 400; }
    for (JsonPairConst field : body.as<JsonObjectConst>()) {
        const String name = field.key().c_str();
        // Marco siempre WGS84 y altura siempre elipsoidal: pedir datum, época o
        // a qué punto corresponde la altura era ceremonia sin efecto.
        if (name != "method" && name != "station_id" &&
            name != "latitude_deg" && name != "longitude_deg" && name != "ellipsoid_height_m" &&
            name != "antenna_vertical_m" && name != "average_seconds" && name != "reuse_distance_m") {
            error(response, "invalid_plan", "Campo de plan desconocido."); return 400;
        }
    }
    if (!body["station_id"].is<unsigned>() || body["station_id"].as<unsigned>() > 4095) {
        error(response, "invalid_station", "Identificador de estación: 0 a 4095."); return 400;
    }
    const String method = body["method"] | "";
    JsonDocument plan;
    plan["station_id"] = body["station_id"];
    plan["method"] = method;
    if (method == "known") {
        if (!body["latitude_deg"].is<double>() || !body["longitude_deg"].is<double>() ||
            !body["ellipsoid_height_m"].is<double>() || !body["antenna_vertical_m"].is<double>()) {
            error(response, "invalid_coordinates", "Revisa que latitud, longitud, altura y antena sean números."); return 400;
        }
        double arp;
        // La altura introducida es siempre la del punto en el suelo: se le suma
        // la antena y la constante del case.
        if (!base_plan::known(body["latitude_deg"], body["longitude_deg"],
            body["ellipsoid_height_m"], body["antenna_vertical_m"], true, arp)) {
            error(response, "invalid_height", "Coordenadas o alturas fuera de rango. La altura es elipsoidal y la medida de antena, vertical."); return 400;
        }
        arp += base_plan::kCaseOffsetM;
        for (const char* field : {"latitude_deg", "longitude_deg", "ellipsoid_height_m", "antenna_vertical_m"}) plan[field] = body[field];
        plan["arp_ellipsoid_height_m"] = arp;
        plan["case_offset_m"] = base_plan::kCaseOffsetM;
        plan["height_reference"] = "ellipsoidal";
        plan["datum"] = "WGS84";
    } else if (method == "average") {
        if (!body["average_seconds"].is<unsigned>() || !body["reuse_distance_m"].is<double>() ||
            !base_plan::average(body["average_seconds"], body["reuse_distance_m"])) {
            error(response, "invalid_average", "Promedio: 1–3600 s; reutilización: 0–10 m."); return 400;
        }
        plan["average_seconds"] = body["average_seconds"];
        plan["reuse_distance_m"] = body["reuse_distance_m"];
    } else { error(response, "invalid_method", "Elige coordenadas conocidas o promedio."); return 400; }
    response["schema_version"] = 1;
    response["applied"] = false;
    response["persisted"] = false;
    response["plan"] = plan.as<JsonVariant>();
    response["message"] = "Plan validado. Pulsa aplicar para enviarlo al receptor; aceptar el modo no verifica la exactitud de la coordenada.";
    return 200;
}

int request(const String& method, const String& path, JsonVariantConst body, JsonDocument& response) {
    if (path == "/api/update" || path.startsWith("/api/update/")) {
        if(method!="GET" && (gnss_control::busy() || ntrip_input::active() || sd_recorder::active())) {error(response,"busy","Detén NTRIP y espera al GPS antes de actualizar.");return 409;}
        return firmware_update::request(method,path,body,response);
    }
    if (firmware_update::busy() && method != "GET") { error(response,"updating","Actualización en curso. Espera antes de modificar el equipo."); return 409; }
    if(path=="/api/recording" || path.startsWith("/api/recording/"))return sd_recorder::request(method,path,body,response);
    if(path=="/api/ntrip/input") return ntrip_input::request(method,body,response);
    if(path=="/api/ntrip/profiles") return ntrip_input::profileRequest(method,body,response);
    if(path=="/api/ble") return ble_transport::request(method,body,response);
    if(path=="/api/base/survey") return base_survey::request(method,body,response);
    if(path=="/api/ntrip/server") return correction_output::serverRequest(method,body,response);
    if(path=="/api/ntrip/caster") return correction_output::casterRequest(method,body,response);
    if(path=="/api/ntrip/sourcetable") return ntrip_input::sourcetableRequest(method,body,response);
    if(path=="/api/gnss/control") {
        if(method=="GET"){gnss_control::status(response.to<JsonObject>());return 200;}
        if(method=="POST")return gnss_control::start(body,response);
        return 400;
    }
    // Configuración avanzada conocida del receptor: máscara, constelaciones,
    // salidas, perfil RTCM y persistencia. Refleja lo aplicado o leído por este
    // firmware, no una consulta continua al UM980.
    if(path=="/api/gnss/profile" && method=="GET"){gnss_control::profile(response.to<JsonObject>());return 200;}
    if(path=="/api/base/apply" && method=="POST") {
        JsonDocument preview;int code=previewBase(body,preview);
        if(code!=200){response=preview;return code;}
        return gnss_control::applyBase(preview["plan"],response);
    }
    if (path == "/api/corrections/source") {
        if(method=="PUT" && (ntrip_input::active() || gnss_control::busy())) {error(response,"busy","Detén NTRIP y espera al GPS antes de cambiar fuente.");return 409;}
        if (method == "PUT") {
            if (!body.is<JsonObjectConst>() || body.size() != 1 || !validString(body["source"], config_rules::deviceName) || !correction_router::select(body["source"])) {
                error(response,"unsupported_source","Fuente no instalada. Disponibles: none, ble, ntrip."); return 400;
            }
        } else if (method != "GET") { error(response,"invalid_method","Usa GET o PUT."); return 400; }
        correction_router::status(response.to<JsonObject>()); return 200;
    }
    if (method == "POST" && path == "/api/base/plan") return previewBase(body, response);
    if (method == "GET" && path == "/api/operations") {
        response["base"]["state"] = "uart_control_available";
        response["base"]["can_preview"] = true;
        response["base"]["can_apply"] = gnss_receiver::snapshot().enabled;
        JsonDocument storage;sd_recorder::status(storage.to<JsonObject>());
        response["recording"]["state"] = storage["state"];
        response["recording"]["can_start"] = storage["available"].as<bool>() && !sd_recorder::active();
        response["recording"]["can_stop"] = sd_recorder::active();
        response["recording"]["can_export"] = storage["available"].as<bool>() && !sd_recorder::active();
        response["recording"]["sessions"] = nullptr;
        for (const char* role : {"input", "publisher", "local_caster"}) {
            response["corrections"][role]["state"] = "not_integrated";
            response["corrections"][role]["can_start"] = false;
        }
        response["corrections"]["input"]["can_start"] = true;
        response["corrections"]["input"]["state"] = "available_ntrip_v1_tcp";
        return 200;
    }
    if (method == "GET" && path == "/api/status") { status(response); return 200; }
    if (method == "GET" && path == "/api/config") { config(response); return 200; }
    if (method == "PUT" && path == "/api/config") return saveConfig(body, response);
    if ((method == "GET" || method == "POST") && path == "/api/wifi/networks") {
        return wifiNetworks(method, body, response);
    }
    if ((method == "GET" || method == "POST") && path == "/api/wifi/scan") {
        return wifiScan(method, response);
    }
    if (method == "POST" && path == "/api/restart") {
        if(sd_recorder::active()||gnss_control::busy()){error(response,"busy","Cierra grabación y espera al GPS antes de reiniciar.");return 409;}
        pendingRestart = true;
        restartRequestedAt = millis();
        response["restarting"] = true;
        return 202;
    }
    error(response, "not_found", "Esta función no está disponible en el firmware actual.");
    return 404;
}
}
