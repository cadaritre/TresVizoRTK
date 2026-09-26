#pragma once
#include <cmath>
#include <cstdint>
#include <cstring>
#include "nmea_gsa.h"
#include "nmea_gsv.h"

namespace gnss {
// La tabla del cielo: que satelites hay, donde, con cuanta senal, y cuales
// entraron en la solucion.
//
// Se junta aqui lo que llega en tres sitios distintos —GSV trae posicion y
// senal, GSA trae quien se usa y los DOP— y se mantiene al dia con una regla
// simple: **cada entrada lleva su marca de tiempo y caduca**.
//
// La alternativa era vaciar la tabla al empezar cada ciclo de GSV. Se descarto
// porque un ciclo se reparte en varias tramas y el vaciado deja la tabla a
// medias justo cuando alguien la lee: el usuario veria el cielo parpadear. Con
// caducidad la tabla nunca esta incompleta, solo un poco vieja, y la edad se
// publica para que se pueda decidir con ella.
//
// Lo que **no** hace es inventar. Un satelite que deja de aparecer se va cuando
// caduca; no se le extrapola posicion ni se le mantiene la senal.
class SkyTable {
public:
    // Cabe un cielo lleno de verdad: cuatro constelaciones a la vista con dos
    // senales cada una pasan de sesenta observaciones. Al llegar al tope se
    // cuentan las que no caben en vez de tirarlas en silencio.
    static constexpr unsigned kCapacity = 72;

    // Diez segundos con GSV a 1 Hz: aguanta que se pierdan varias tramas
    // seguidas sin que el cielo parpadee, y no tanto como para ensenar un
    // satelite que ya se puso hace rato.
    static constexpr uint32_t kExpiryMs = 10000;

    // Los satelites usados caducan aparte y antes. Si el receptor deja de
    // mandar GSA, "usado" tiene que apagarse: dejarlo encendido diria que la
    // solucion sigue apoyandose en satelites de los que ya no se sabe nada.
    static constexpr uint32_t kUsedExpiryMs = 5000;

    struct Satellite {
        char talker[3] = {};
        uint8_t signal_id = 0;
        uint8_t prn = 0;
        int8_t elevation_deg = -1;
        int16_t azimuth_deg = -1;
        uint8_t cno_dbhz = 0;
        bool tracked = false;
        bool used = false;
        uint32_t updated_ms = 0;
    };

    // Cuantas observaciones no cupieron. Un numero que deberia ser cero; si
    // deja de serlo, la capacidad se queda corta y hay que saberlo.
    uint32_t dropped = 0;

    void feed(const GsvMessage& message, uint32_t now_ms) {
        for (unsigned i = 0; i < message.count; ++i) {
            const SvObservation& sv = message.satellites[i];
            Satellite* entry = find(message.talker, message.signal_id, sv.prn);
            if (!entry) entry = claim(now_ms);
            if (!entry) { ++dropped; continue; }
            const bool nueva = entry->prn != sv.prn || entry->signal_id != message.signal_id
                || std::strncmp(entry->talker, message.talker, 2) != 0;
            if (nueva) {
                *entry = Satellite();
                std::memcpy(entry->talker, message.talker, 3);
                entry->signal_id = message.signal_id;
                entry->prn = sv.prn;
            }
            entry->elevation_deg = sv.elevation_deg;
            entry->azimuth_deg = sv.azimuth_deg;
            entry->cno_dbhz = sv.cno_dbhz;
            entry->tracked = sv.tracked;
            entry->updated_ms = now_ms;
        }
    }

    void feed(const Gsa& message, uint32_t now_ms) {
        fix_type = message.fix_type;
        pdop = message.pdop;
        hdop = message.hdop;
        vdop = message.vdop;
        dop_updated_ms = now_ms;

        // De que constelacion son estos PRN. Con NMEA 4.10 lo dice el
        // identificador de sistema; sin el, solo se sabe cuando el emisor no es
        // el generico GN. **Si no se sabe, no se marca nada**: marcar el PRN 12
        // en todas las constelaciones encenderia satelites que no se usaron.
        const char* talker = talkerFor(message);
        if (!talker) return;
        for (unsigned i = 0; i < message.count; ++i) {
            // El mismo satelite puede estar en varias senales, y **todas las
            // suyas se marcan**: la solucion usa el satelite, no una frecuencia.
            for (unsigned e = 0; e < count_; ++e) {
                if (entries_[e].prn != message.prns[i]) continue;
                if (std::strncmp(entries_[e].talker, talker, 2) != 0) continue;
                entries_[e].used = true;
                used_updated_ms = now_ms;
            }
        }
    }

    uint8_t fix_type = 0;
    double pdop = NAN, hdop = NAN, vdop = NAN;
    uint32_t dop_updated_ms = 0;
    uint32_t used_updated_ms = 0;

    /// Las entradas vivas, compactadas al principio. Devuelve cuantas hay.
    ///
    /// Aqui se aplican las dos caducidades: la entrada entera y la marca de
    /// usado. No se tocan los datos guardados, solo lo que sale.
    unsigned view(Satellite* out, unsigned capacity, uint32_t now_ms) const {
        unsigned written = 0;
        for (unsigned i = 0; i < count_ && written < capacity; ++i) {
            if (!entries_[i].prn) continue;
            if (now_ms - entries_[i].updated_ms > kExpiryMs) continue;
            out[written] = entries_[i];
            if (now_ms - used_updated_ms > kUsedExpiryMs) out[written].used = false;
            ++written;
        }
        return written;
    }

    /// Cuantos satelites distintos hay a la vista, contando una vez cada uno
    /// aunque llegue por varias senales. Es la cifra que se compara con la de
    /// GGA: si GGA dice 10 usados y esto dice 30 a la vista, el problema no es
    /// el cielo.
    unsigned distinctInView(uint32_t now_ms) const {
        unsigned total = 0;
        for (unsigned i = 0; i < count_; ++i) {
            if (!entries_[i].prn) continue;
            if (now_ms - entries_[i].updated_ms > kExpiryMs) continue;
            bool repetido = false;
            for (unsigned j = 0; j < i && !repetido; ++j) {
                if (!entries_[j].prn) continue;
                if (now_ms - entries_[j].updated_ms > kExpiryMs) continue;
                repetido = entries_[j].prn == entries_[i].prn
                    && std::strncmp(entries_[j].talker, entries_[i].talker, 2) == 0;
            }
            if (!repetido) ++total;
        }
        return total;
    }

private:
    Satellite entries_[kCapacity];
    unsigned count_ = 0;

    static const char* talkerFor(const Gsa& message) {
        switch (message.system_id) {
        case 1: return "GP";
        case 2: return "GL";
        case 3: return "GA";
        case 4: return "GB";
        case 5: return "GQ";
        default: break;
        }
        // Sin identificador de sistema: solo vale si el emisor ya lo dice.
        if (std::strncmp(message.talker, "GN", 2) == 0) return nullptr;
        return message.talker[0] ? message.talker : nullptr;
    }

    Satellite* find(const char* talker, uint8_t signal, uint8_t prn) {
        for (unsigned i = 0; i < count_; ++i) {
            if (entries_[i].prn != prn || entries_[i].signal_id != signal) continue;
            if (std::strncmp(entries_[i].talker, talker, 2) != 0) continue;
            return &entries_[i];
        }
        return nullptr;
    }

    /// Un hueco para una observacion nueva: el primero libre, y si no hay, **la
    /// entrada mas vieja**. Quedarse con las primeras que llegaron dejaria
    /// fuera a las constelaciones que se anuncian al final.
    Satellite* claim(uint32_t now_ms) {
        if (count_ < kCapacity) return &entries_[count_++];
        Satellite* oldest = nullptr;
        for (unsigned i = 0; i < count_; ++i) {
            if (!oldest || int32_t(entries_[i].updated_ms - oldest->updated_ms) < 0) oldest = &entries_[i];
        }
        if (oldest && now_ms - oldest->updated_ms > kExpiryMs) return oldest;
        return nullptr;
    }
};
}
