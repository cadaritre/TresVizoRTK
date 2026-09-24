#include "base_survey.h"
#include "gnss_receiver.h"
#include "gnss_control.h"
#include "ntrip_input.h"
#include "correction_router.h"
#include "config_rules.h"
#include <Arduino.h>
#include <atomic>
#include <cmath>

namespace base_survey {
namespace {
// Calidad mínima exigida a cada época. Los códigos son los de GGA.
enum class Quality : uint8_t { Any = 0, Single = 1, Float = 5, Fixed = 4 };

std::atomic<const char*> state{"idle"};
std::atomic<const char*> reason{""};
Quality required = Quality::Fixed;
uint32_t wantedSeconds = 60;
uint32_t startedAt = 0;
uint32_t samples = 0;
uint32_t stationId = 0;
double antennaVertical = 0;
// Sumas en doble precisión. A un metro de escala y unas miles de épocas no hay
// pérdida apreciable, y evita el coste de un acumulador compensado.
double sumLat = 0, sumLon = 0, sumHeight = 0;
// El motivo del fallo vive fuera del atomic: este guarda el puntero y necesita
// que la cadena siga existiendo.
String failureText;
JsonDocument stopRequest() {
    JsonDocument body;
    body["action"] = "stop";
    return body;
}
uint32_t lastEpoch = UINT32_MAX;

// La altura del case todavía no está medida. Hasta entonces se suma una
// constante: cambiarla aquí es cambiarla en todo el firmware.
constexpr double kCaseOffsetM = 0.10;

bool matches(unsigned quality) {
    switch (required) {
        case Quality::Fixed: return quality == 4;
        case Quality::Float: return quality == 5;
        case Quality::Single: return quality == 1;
        default: return quality != 0;
    }
}
const char* qualityName(Quality value) {
    switch (value) {
        case Quality::Fixed: return "rtk_fixed";
        case Quality::Float: return "rtk_float";
        case Quality::Single: return "standalone";
        default: return "any";
    }
}
void stop(const char* nextState, const char* why) {
    state = nextState;
    reason = why;
}
}

void begin() { state = "idle"; }

bool active() { return !strcmp(state.load(), "averaging"); }

void tick() {
    // Esperando la confirmación del receptor tras enviar la coordenada.
    if (!strcmp(state.load(), "applying")) {
        if (gnss_control::busy()) return;
        if (gnss_control::isBase()) stop("applied", "");
        else stop("failed", "El receptor no confirmó el modo base. Consulta su estado en GPS avanzado.");
        return;
    }
    if (!active()) return;
    const auto snapshot = gnss_receiver::snapshot();
    const auto& s = snapshot.solution;
    const uint32_t now = millis();

    // Sin épocas frescas no se promedia y, pasados unos segundos, se cancela:
    // seguir contando el tiempo sin datos daría un promedio de nada.
    if (!snapshot.enabled || !snapshot.accepted ||
        esp_timer_get_time() - s.arrival_us > 3000000) {
        if (now - startedAt > 5000) {
            stop("cancelled", "El receptor dejó de entregar posiciones durante el promedio.");
        }
        return;
    }
    if (s.utc_ms == lastEpoch) {
        if (now - startedAt >= wantedSeconds * 1000UL && samples) {
            // Tiempo cumplido: aplicar la media como coordenada de la base.
            JsonDocument plan;
            plan["method"] = "known";
            plan["station_id"] = stationId;
            plan["latitude_deg"] = sumLat / samples;
            plan["longitude_deg"] = sumLon / samples;
            // La coordenada promediada es la del receptor; lo que se declara a
            // la base es la altura del punto más la antena y el case.
            plan["arp_ellipsoid_height_m"] = sumHeight / samples + antennaVertical + kCaseOffsetM;
            // Una base no consume correcciones, y tenerlas activas bloquea la
            // aplicación del modo. Se cierran aquí en vez de fallar al final de
            // un promedio de varios minutos por algo que sabíamos de antemano.
            ntrip_input::releaseForBase();
            correction_router::select("none");
            JsonDocument out;
            const int code = gnss_control::applyBase(plan.as<JsonVariantConst>(), out);
            if (code == 202) {
                // Lanzado no es aplicado: el receptor todavía no ha contestado.
                // Decir "applied" aquí era la misma mentira de siempre.
                stop("applying", "Enviando la coordenada al receptor…");
            } else {
                // El motivo real, no uno inventado: antes decía que lo rechazaba
                // el receptor cuando el receptor no había llegado a verlo.
                failureText = out["message"].is<const char*>()
                    ? String(out["message"].as<const char*>())
                    : String("No se pudo aplicar la coordenada promediada.");
                stop("failed", failureText.c_str());
            }
        }
        return;
    }
    lastEpoch = s.utc_ms;
    if (!s.has_position || !std::isfinite(s.altitude_msl_m)) return;
    if (!matches(s.quality)) {
        // Esto es lo que pidió el propietario: si la calidad exigida se pierde a
        // mitad del promedio, se cancela y se dice por qué, en vez de terminar
        // con una media contaminada que nadie sabría que lo está.
        stop("cancelled", "Se perdió la calidad de solución exigida durante el promedio. La coordenada habría quedado contaminada.");
        return;
    }
    sumLat += s.latitude_deg;
    sumLon += s.longitude_deg;
    // GGA entrega altura sobre el geoide; la base se declara en elipsoidal.
    sumHeight += s.altitude_msl_m + (std::isfinite(s.geoid_separation_m) ? s.geoid_separation_m : 0);
    ++samples;
}

void status(JsonObject out) {
    out["state"] = state.load();
    out["reason"] = reason.load();
    out["required_quality"] = qualityName(required);
    out["seconds_requested"] = wantedSeconds;
    out["samples"] = samples;
    const uint32_t elapsed = active() ? (millis() - startedAt) / 1000 : 0;
    out["seconds_elapsed"] = elapsed;
    out["case_offset_m"] = kCaseOffsetM;
    // Media acumulada hasta ahora: el usuario ve la coordenada que va a quedar
    // mientras se forma, en vez de esperar a ciegas a que termine.
    if (samples) {
        out["latitude_deg"] = sumLat / samples;
        out["longitude_deg"] = sumLon / samples;
        out["height_to_set_m"] = sumHeight / samples + antennaVertical + kCaseOffsetM;
    } else {
        out["latitude_deg"] = nullptr;
        out["longitude_deg"] = nullptr;
        out["height_to_set_m"] = nullptr;
    }
    // Sin ondulación informada la altura elipsoidal sería la del geoide: se
    // advierte en vez de entregar una coordenada con decenas de metros de error.
    const auto snapshot = gnss_receiver::snapshot();
    out["geoid_separation_known"] = std::isfinite(snapshot.solution.geoid_separation_m);
}

int request(const String& method, JsonVariantConst body, JsonDocument& out) {
    if (method == "GET") { status(out.to<JsonObject>()); return 200; }
    if (method != "POST" || !body.is<JsonObjectConst>()) return 400;
    const String action = body["action"] | "";
    if (action == "cancel") {
        stop("cancelled", "Cancelado desde el panel.");
        status(out.to<JsonObject>());
        return 200;
    }
    if (action != "start") return 400;
    if (active()) { out["message"] = "Ya hay un promedio en curso."; return 409; }
    if (gnss_control::busy()) { out["message"] = "Espera a que termine la operación del GPS."; return 409; }
    // Dos segundos son 20 épocas a 10 Hz: con solución fija es un promedio
    // legítimo, y exigir más era una regla inventada.
    if (!body["seconds"].is<unsigned>() || body["seconds"].as<unsigned>() < 2 ||
        body["seconds"].as<unsigned>() > 900) {
        out["message"] = "El tiempo de promedio va de 2 a 900 segundos."; return 400;
    }
    if (!body["station_id"].is<unsigned>() || body["station_id"].as<unsigned>() > 4095) {
        out["message"] = "Identificador de estación: 0 a 4095."; return 400;
    }
    if (!body["antenna_vertical_m"].is<double>() ||
        body["antenna_vertical_m"].as<double>() < 0 || body["antenna_vertical_m"].as<double>() > 100) {
        out["message"] = "Altura de antena: 0 a 100 m."; return 400;
    }
    const String quality = body["quality"] | "rtk_fixed";
    if (quality == "rtk_fixed") required = Quality::Fixed;
    else if (quality == "rtk_float") required = Quality::Float;
    else if (quality == "standalone") required = Quality::Single;
    else if (quality == "any") required = Quality::Any;
    else { out["message"] = "Calidad admitida: rtk_fixed, rtk_float, standalone o any."; return 400; }

    const auto snapshot = gnss_receiver::snapshot();
    if (!matches(snapshot.solution.quality)) {
        out["message"] = "La solución actual no cumple la calidad exigida. Espera a alcanzarla o elige otra.";
        return 409;
    }
    wantedSeconds = body["seconds"];
    stationId = body["station_id"];
    antennaVertical = body["antenna_vertical_m"];
    sumLat = sumLon = sumHeight = 0;
    samples = 0;
    lastEpoch = UINT32_MAX;
    startedAt = millis();
    stop("averaging", "");
    status(out.to<JsonObject>());
    return 202;
}
}
