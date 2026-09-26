#include <Arduino.h>
#include <algorithm>
#include <cmath>
#include "gnss_sky.h"
#include "sky_table.h"

namespace gnss_sky {
namespace {
portMUX_TYPE lock = portMUX_INITIALIZER_UNLOCKED;
gnss::SkyTable table;
uint32_t lastSkyMs = 0;
bool haveSky = false;

// Cuantos satelites se publican como maximo.
//
// El limite no es de memoria, es del transporte: una respuesta por BLE se corta
// en 4096 bytes y devuelve 413 (`ble_transport.cpp:181`). Con cuarenta
// satelites y sus senales la respuesta ronda los 2.5 KB, que deja margen para
// el resto del objeto. Pasar de ahi convertiria esta pantalla en un error.
constexpr unsigned kPublished = 40;

// Copia de trabajo fuera de la pila: la tarea del servidor no tiene sitio para
// un kilobyte y medio de satelites. Solo la toca `publish`, y al servidor HTTP
// lo atiende una sola tarea.
gnss::SkyTable::Satellite scratch[gnss::SkyTable::kCapacity];

// Un satelite, con sus senales juntas.
struct Grouped {
    char talker[3] = {};
    uint8_t prn = 0;
    int8_t elevation_deg = -1;
    int16_t azimuth_deg = -1;
    uint8_t best_cno = 0;
    bool tracked = false;
    bool used = false;
    uint8_t signals = 0;
    uint8_t signal_id[6] = {};
    uint8_t signal_cno[6] = {};
};
Grouped grouped[gnss::SkyTable::kCapacity];
}

void feed(const gnss::GsvMessage& message, uint32_t now_ms) {
    portENTER_CRITICAL(&lock);
    table.feed(message, now_ms);
    lastSkyMs = now_ms;
    haveSky = true;
    portEXIT_CRITICAL(&lock);
}

void feed(const gnss::Gsa& message, uint32_t now_ms) {
    portENTER_CRITICAL(&lock);
    table.feed(message, now_ms);
    portEXIT_CRITICAL(&lock);
}

void publish(JsonObject out) {
    const uint32_t now = millis();
    Summary summary;
    unsigned count = 0;

    portENTER_CRITICAL(&lock);
    count = table.view(scratch, gnss::SkyTable::kCapacity, now);
    summary.in_view = table.distinctInView(now);
    summary.dropped = table.dropped;
    summary.fix_type = table.fix_type;
    summary.pdop = table.pdop;
    summary.hdop = table.hdop;
    summary.vdop = table.vdop;
    summary.has_dop = table.dop_updated_ms != 0;
    summary.dop_age_ms = now - table.dop_updated_ms;
    summary.has_sky = haveSky;
    summary.sky_age_ms = now - lastSkyMs;
    portEXIT_CRITICAL(&lock);

    // Agrupar por satelite. El mismo PRN llega una vez por senal con C/N0
    // distinto; una barra por observacion pintaria el mismo satelite dos veces.
    unsigned total = 0;
    for (unsigned i = 0; i < count; ++i) {
        const auto& sv = scratch[i];
        Grouped* entry = nullptr;
        for (unsigned g = 0; g < total; ++g) {
            if (grouped[g].prn == sv.prn && !std::strncmp(grouped[g].talker, sv.talker, 2)) {
                entry = &grouped[g];
                break;
            }
        }
        if (!entry) {
            if (total == gnss::SkyTable::kCapacity) continue;
            entry = &grouped[total++];
            *entry = Grouped();
            std::memcpy(entry->talker, sv.talker, 3);
            entry->prn = sv.prn;
        }
        // Elevacion y azimut son del satelite, no de la senal: vale la primera
        // que los traiga, y no se sobreescriben con un desconocido.
        if (entry->elevation_deg < 0) entry->elevation_deg = sv.elevation_deg;
        if (entry->azimuth_deg < 0) entry->azimuth_deg = sv.azimuth_deg;
        entry->tracked = entry->tracked || sv.tracked;
        entry->used = entry->used || sv.used;
        if (sv.cno_dbhz > entry->best_cno) entry->best_cno = sv.cno_dbhz;
        if (entry->signals < 6) {
            entry->signal_id[entry->signals] = sv.signal_id;
            entry->signal_cno[entry->signals] = sv.cno_dbhz;
            ++entry->signals;
        }
    }

    for (unsigned g = 0; g < total; ++g) if (grouped[g].used) ++summary.used;

    // **Si hay que recortar, se recortan los de menos abajo, nunca los que
    // entraron en la solucion.** Un cielo recortado al azar es peor que uno
    // corto: el operador busca justo el satelite que le falta.
    std::stable_sort(grouped, grouped + total, [](const Grouped& a, const Grouped& b) {
        if (a.used != b.used) return a.used;
        return a.elevation_deg > b.elevation_deg;
    });

    const unsigned published = total < kPublished ? total : kPublished;
    JsonArray satellites = out["satellites"].to<JsonArray>();
    for (unsigned g = 0; g < published; ++g) {
        const Grouped& sv = grouped[g];
        JsonObject item = satellites.add<JsonObject>();
        item["sys"] = sv.talker;
        item["prn"] = sv.prn;
        // Nulo, no cero: cero es el horizonte y cero es el norte, y los dos son
        // sitios de verdad.
        if (sv.elevation_deg >= 0) item["el"] = sv.elevation_deg; else item["el"] = nullptr;
        if (sv.azimuth_deg >= 0) item["az"] = sv.azimuth_deg; else item["az"] = nullptr;
        // Sin rastrear no lleva C/N0. Un cero seria una senal medida de potencia
        // nula, que no existe.
        if (sv.tracked) item["cno"] = sv.best_cno; else item["cno"] = nullptr;
        item["use"] = sv.used;
        JsonArray signals = item["sig"].to<JsonArray>();
        for (unsigned s = 0; s < sv.signals; ++s) {
            JsonArray pair = signals.add<JsonArray>();
            pair.add(sv.signal_id[s]);
            if (sv.signal_cno[s]) pair.add(sv.signal_cno[s]); else pair.add(nullptr);
        }
    }

    out["in_view"] = summary.in_view;
    out["used"] = summary.used;
    out["published"] = published;
    // Cuantos no se publicaron por el limite del transporte, y cuantas
    // observaciones no cupieron en la tabla. Los dos deberian ser cero.
    out["omitted"] = total - published;
    out["dropped"] = summary.dropped;
    if (summary.has_sky) out["age_ms"] = summary.sky_age_ms; else out["age_ms"] = nullptr;
    if (summary.fix_type) out["fix_type"] = summary.fix_type; else out["fix_type"] = nullptr;
    for (const auto& dop : {std::pair<const char*, double>{"pdop", summary.pdop},
                            {"hdop", summary.hdop}, {"vdop", summary.vdop}}) {
        if (summary.has_dop && std::isfinite(dop.second)) out[dop.first] = dop.second;
        else out[dop.first] = nullptr;
    }
    if (summary.has_dop) out["dop_age_ms"] = summary.dop_age_ms; else out["dop_age_ms"] = nullptr;
}
}
