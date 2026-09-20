#include "sd_recorder.h"
#include "ntrip_input.h"
#include "gnss_control.h"
#include "memory_health.h"
#include "instrument.h"
#include "gnss_receiver.h"
#include "ble_transport.h"
#include "firmware_update.h"
#include "correction_router.h"
#include "config_rules.h"
#include "base_plan.h"

#include <Preferences.h>
#include <WiFi.h>
#include <esp_system.h>
#include <esp_timer.h>

namespace instrument {
namespace {
Preferences preferences;
String deviceName = "TresVizo RTK";
String stationSsid;
String stationPassword;
String key;
String networkName;
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
    response["persistence_ready"] = storageReady;
    response["stored_config_valid"] = configValid;
}

void connectStation() {
    WiFi.disconnect(false, false);
    lastConnectionAttempt = millis();
    if (!stationSsid.isEmpty()) WiFi.begin(stationSsid.c_str(), stationPassword.c_str());
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
            name != "wifi_ssid" && name != "wifi_password" && name != "forget_wifi") {
            error(response, "unknown_setting", "La solicitud contiene un ajuste no admitido.");
            return 400;
        }
    }
    if (!body["revision"].is<uint32_t>() || body["revision"].as<uint32_t>() != revision) {
        error(response, "revision_conflict", "Los ajustes cambiaron. Vuelve a cargarlos antes de guardar.");
        return 409;
    }
    String nextName = deviceName;
    String nextSsid = stationSsid;
    String nextPassword = stationPassword;
    uint32_t nextRefresh = refreshMs;
    if (!body["device_name"].isNull()) {
        if (!validString(body["device_name"], config_rules::deviceName)) {
            error(response, "invalid_name", "Usa entre 1 y 32 letras sin acentos, números, espacios, guiones o guiones bajos.");
            return 400;
        }
        nextName = body["device_name"].as<const char*>();
    }
    if (!body["refresh_ms"].isNull()) {
        if (!body["refresh_ms"].is<uint32_t>() || !config_rules::refresh(body["refresh_ms"].as<uint32_t>())) {
            error(response, "invalid_refresh", "El intervalo debe ser 1000, 2000 o 5000 ms.");
            return 400;
        }
        nextRefresh = body["refresh_ms"].as<uint32_t>();
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
        nextSsid = body["wifi_ssid"].as<const char*>();
        if (nextSsid != stationSsid) nextPassword = "";
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
        if (value.size()) nextPassword = value.c_str();
    }
    if (body["forget_wifi"] == true) {
        nextSsid = "";
        nextPassword = "";
    }
    if (nextSsid.isEmpty()) nextPassword = "";
    if (!nextSsid.isEmpty() && nextPassword.isEmpty()) {
        error(response, "password_required", "Introduce la contraseña de la red seleccionada. Solo se admiten redes protegidas.");
        return 400;
    }
    if (!storageReady) {
        error(response, "storage_unavailable", "No se pudo abrir el almacenamiento interno de ajustes.");
        return 503;
    }
    const bool changed = nextName != deviceName || nextRefresh != refreshMs ||
        nextSsid != stationSsid || nextPassword != stationPassword || !configValid;
    if (!changed) {
        config(response);
        response["saved"] = true;
        response["changed"] = false;
        return 200;
    }
    JsonDocument record;
    record["schema_version"] = 1;
    record["revision"] = revision + 1;
    record["device_name"] = nextName;
    record["refresh_ms"] = nextRefresh;
    record["wifi_ssid"] = nextSsid;
    record["wifi_password"] = nextPassword;
    String encoded;
    serializeJson(record, encoded);
    // Una única entrada NVS: no publicar ajustes parcialmente persistidos.
    if (preferences.putString("config", encoded) != encoded.length()) {
        error(response, "save_failed", "No se pudieron guardar los ajustes. La configuración activa se conserva.");
        return 503;
    }
    if (nextSsid != stationSsid || nextPassword != stationPassword) {
        pendingNetwork = true;
        networkChangedAt = millis();
    }
    deviceName = nextName;
    stationSsid = nextSsid;
    stationPassword = nextPassword;
    refreshMs = nextRefresh;
    ++revision;
    configValid = true;
    config(response);
    response["saved"] = true;
    response["changed"] = true;
    return 200;
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
    wifi["station_state"] = stationSsid.isEmpty() ? "not_configured" : (connected ? "connected" : "connecting");
    wifi["station_ssid"] = stationSsid;
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
    sd_recorder::status(response["subsystems"]["microsd"].as<JsonObject>());
    response["solution"]["fix"] = nullptr;
    response["solution"]["latitude_deg"] = nullptr;
    response["solution"]["longitude_deg"] = nullptr;
    response["solution"]["height_m"] = nullptr;
    response["solution"]["height_reference"] = nullptr;
    response["solution"]["measurement_time"] = nullptr;
    response["solution"]["arrival_time_us"] = nullptr;
    const auto gnss = gnss_receiver::snapshot();
    JsonObject health = response["subsystems"]["gnss"].as<JsonObject>();
    health["state"] = gnss.start_failed ? "start_failed" : "not_integrated";
    health["accepted_gga"] = gnss.accepted;
    health["rejected_gga"] = gnss.rejected;
    health["line_overflows"] = gnss.overflow;
    health["uart_errors"] = gnss.uart_errors;
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
        key = preferences.getString("access_key", "");
        const String saved = preferences.getString("config", "");
        if (!saved.isEmpty()) {
            JsonDocument record;
            const auto parsed = deserializeJson(record, saved, DeserializationOption::NestingLimit(3));
            configValid = !parsed && record["schema_version"] == 1 &&
                validString(record["device_name"], config_rules::deviceName) &&
                record["revision"].is<uint32_t>() && record["refresh_ms"].is<uint32_t>() &&
                config_rules::refresh(record["refresh_ms"].as<uint32_t>()) &&
                validString(record["wifi_ssid"], config_rules::ssid) &&
                record["wifi_password"].is<const char*>();
            if (configValid) {
                const String ssid = record["wifi_ssid"].as<const char*>();
                configValid = ssid.isEmpty() || validString(record["wifi_password"], config_rules::password);
            }
            if (configValid) {
                deviceName = record["device_name"].as<const char*>();
                revision = record["revision"].as<uint32_t>();
                refreshMs = record["refresh_ms"].as<uint32_t>();
                stationSsid = record["wifi_ssid"].as<const char*>();
                stationPassword = record["wifi_password"].as<const char*>();
            }
        }
    }
    WiFi.persistent(false);
    WiFi.mode(WIFI_AP_STA); // radio activa para la fuente de entropía del RNG
    if (!config_rules::password(key.c_str())) {
        char randomKey[25];
        snprintf(randomKey, sizeof(randomKey), "%08lx%08lx%08lx",
            static_cast<unsigned long>(esp_random()), static_cast<unsigned long>(esp_random()),
            static_cast<unsigned long>(esp_random()));
        key = randomKey;
        if (storageReady && preferences.putString("access_key", key) != key.length()) storageReady = false;
    }
    char suffix[5];
    snprintf(suffix, sizeof(suffix), "%04X", static_cast<unsigned int>(ESP.getEfuseMac() >> 32) & 0xffff);
    networkName = String("TresVizo-") + suffix;
    WiFi.setAutoReconnect(true);
    WiFi.setHostname("tresvizo-rtk");
    WiFi.softAPConfig(IPAddress(192, 168, 4, 1), IPAddress(192, 168, 4, 1), IPAddress(255, 255, 255, 0));
    apReady = WiFi.softAP(networkName.c_str(), key.c_str(), 1, false, 4);
    connectStation();
}

void tick() {
    const uint32_t now = millis();
    if (pendingRestart && config_rules::elapsed(now, restartRequestedAt, 1000)) ESP.restart();
    if (pendingNetwork && config_rules::elapsed(now, networkChangedAt, 1000)) {
        pendingNetwork = false;
        connectStation();
    }
    if (!pendingNetwork && !stationSsid.isEmpty() && WiFi.status() != WL_CONNECTED &&
        config_rules::elapsed(now, lastConnectionAttempt, 30000)) connectStation();
}

int changeAccessKey(JsonVariantConst body, JsonDocument& response) {
    if(sd_recorder::active() || gnss_control::busy() || firmware_update::busy()) {error(response,"busy","Espera al cierre de la operación antes de cambiar la clave y reiniciar.");return 409;}
    if (pendingRestart) { error(response, "restarting", "Reinicio en curso."); return 409; }
    if (!body.is<JsonObjectConst>() || body.size() != 1 ||
        !validString(body["access_key"], config_rules::password)) {
        error(response, "invalid_key", "La clave debe tener entre 8 y 63 caracteres ASCII imprimibles.");
        return 400;
    }
    const String next = body["access_key"].as<const char*>();
    if (next == key) { response["changed"] = false; return 200; }
    if (!storageReady || preferences.putString("access_key", next) != next.length()) {
        error(response, "storage_failed", "No se pudo guardar la clave."); return 503;
    }
    // Mantener la clave activa inmutable hasta reiniciar evita carreras con HTTP.
    pendingRestart = true;
    restartRequestedAt = millis();
    response["changed"] = true;
    response["restarting"] = true;
    return 202;
}

const String& accessKey() { return key; }
const String& apName() { return networkName; }

int previewBase(JsonVariantConst body, JsonDocument& response) {
    if (!body.is<JsonObjectConst>()) { error(response, "invalid_plan", "Se esperaba un plan de base."); return 400; }
    for (JsonPairConst field : body.as<JsonObjectConst>()) {
        const String name = field.key().c_str();
        if (name != "method" && name != "station_id" && name != "datum" && name != "coordinate_epoch" &&
            name != "latitude_deg" && name != "longitude_deg" && name != "ellipsoid_height_m" &&
            name != "antenna_vertical_m" && name != "height_point" && name != "average_seconds" && name != "reuse_distance_m") {
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
        if (!validString(body["datum"], config_rules::deviceName) ||
            !body["latitude_deg"].is<double>() || !body["longitude_deg"].is<double>() ||
            !body["ellipsoid_height_m"].is<double>() || !body["antenna_vertical_m"].is<double>() ||
            (!body["coordinate_epoch"].isNull() && (!body["coordinate_epoch"].is<double>() ||
                body["coordinate_epoch"].as<double>() < 1900 || body["coordinate_epoch"].as<double>() > 2200))) {
            error(response, "invalid_coordinates", "Revisa coordenadas numéricas, datum y época decimal opcional."); return 400;
        }
        const String point = body["height_point"] | "";
        double arp;
        if ((point != "marker" && point != "arp") || !base_plan::known(body["latitude_deg"], body["longitude_deg"],
            body["ellipsoid_height_m"], body["antenna_vertical_m"], point == "marker", arp)) {
            error(response, "invalid_height", "Coordenadas o alturas fuera de rango; usa altura elipsoidal y medida vertical."); return 400;
        }
        for (const char* field : {"datum", "coordinate_epoch", "latitude_deg", "longitude_deg", "ellipsoid_height_m", "antenna_vertical_m", "height_point"}) plan[field] = body[field];
        plan["arp_ellipsoid_height_m"] = arp;
        plan["height_reference"] = "ellipsoidal";
        plan["datum_transformed"] = false;
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
    response["message"] = "Plan preparado. No enviado al GPS ni guardado en el equipo. Datum, antena y aplicación física pendientes de verificación.";
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
    if(path=="/api/gnss/control") {
        if(method=="GET"){gnss_control::status(response.to<JsonObject>());return 200;}
        if(method=="POST")return gnss_control::start(body,response);
        return 400;
    }
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
