#pragma once
#include <cstdint>
#include <cstdlib>
#include <cstring>

namespace gnss {
// GSV: los satelites a la vista, uno a uno. Es lo unico que trae elevacion,
// azimut y relacion senal-ruido por satelite; GGA solo dice cuantos se usaron.
//
// Tres cosas de NMEA 4.10 que hay que respetar o los numeros salen mal:
//
// 1. **La trama lleva identificador de senal al final.** El mismo satelite
//    aparece una vez por senal —L1 y L5 del mismo GPS son dos tramas— con C/N0
//    distinto. Quien guarde por PRN a secas sobreescribe una con otra y ensena
//    una relacion senal-ruido que no es la que cree.
// 2. **El emisor dice la constelacion**: GP, GL, GA, GB, GQ. Deducirla del
//    rango del PRN funciona hasta que deja de funcionar, y los rangos de BeiDou
//    y QZSS no coinciden entre fabricantes.
// 3. **C/N0 vacio no es cero.** Vacio significa a la vista y sin rastrear;
//    cero seria una senal medida de potencia nula, que no existe. Se distinguen
//    con `tracked`.
struct SvObservation {
    uint8_t prn = 0;
    // -1 cuando la trama no la trae. La elevacion vale 0 de verdad en el
    // horizonte, asi que el desconocido no puede ser cero.
    int8_t elevation_deg = -1;
    int16_t azimuth_deg = -1;
    uint8_t cno_dbhz = 0;
    bool tracked = false;
};

struct GsvMessage {
    uint64_t arrival_us = 0;
    // "GP", "GL", "GA", "GB", "GQ"… tal como vino, sin interpretar.
    char talker[3] = {};
    // 0 cuando la trama no lo trae (NMEA anterior a 4.10).
    uint8_t signal_id = 0;
    uint8_t total_messages = 0, message_number = 0, satellites_in_view = 0;
    uint8_t count = 0;
    SvObservation satellites[4];
};

class GsvParser {
public:
    uint32_t accepted = 0, rejected = 0, overflow = 0;

    bool feed(char byte, uint64_t arrival_us, GsvMessage& output) {
        if (byte == '$') { length_ = 0; collecting_ = true; return false; }
        if (!collecting_) return false;
        if (byte == '\n') {
            collecting_ = false;
            if (length_ && buffer_[length_ - 1] == '\r') --length_;
            buffer_[length_] = '\0';
            if (length_ < 6 || std::strncmp(buffer_ + 2, "GSV,", 4)) return false;
            GsvMessage next;
            next.arrival_us = arrival_us;
            next.talker[0] = buffer_[0];
            next.talker[1] = buffer_[1];
            if (!decode(next)) { ++rejected; return false; }
            output = next;
            ++accepted;
            return true;
        }
        // Una GSV llena son 4 satelites: cabecera, 16 campos y la suma. Con 100
        // bytes sobra, y el limite del estandar son 82 caracteres.
        if (length_ == sizeof(buffer_) - 1) { collecting_ = false; ++overflow; return false; }
        if (byte == '\0') { collecting_ = false; ++rejected; return false; }
        buffer_[length_++] = byte;
        return false;
    }

private:
    char buffer_[100] = {};
    size_t length_ = 0;
    bool collecting_ = false;

    static int hex(char c) {
        if (c >= '0' && c <= '9') return c - '0';
        if (c >= 'A' && c <= 'F') return c - 'A' + 10;
        if (c >= 'a' && c <= 'f') return c - 'a' + 10;
        return -1;
    }

    // Entero sin signo y sin nada mas. `strtol` acepta espacios, signos y se
    // para en la basura devolviendo lo que llevaba leido; aqui una basura tiene
    // que invalidar el campo, no dejar la mitad.
    static bool integer(const char* s, long& result) {
        if (!*s) return false;
        for (const char* p = s; *p; ++p) if (*p < '0' || *p > '9') return false;
        result = std::strtol(s, nullptr, 10);
        return true;
    }

    static bool optionalInteger(const char* s, long& result, bool& present) {
        present = *s != '\0';
        if (!present) return true;
        return integer(s, result);
    }

    bool decode(GsvMessage& result) {
        char* star = std::strchr(buffer_, '*');
        if (!star || std::strlen(star) != 3 || hex(star[1]) < 0 || hex(star[2]) < 0) return false;
        uint8_t check = 0;
        for (char* p = buffer_; p < star; ++p) check ^= static_cast<uint8_t>(*p);
        if (check != ((hex(star[1]) << 4) | hex(star[2]))) return false;
        *star = '\0';

        // Cabecera + 3 campos + hasta 4 grupos de 4 + identificador de senal.
        char* fields[21] = {buffer_};
        unsigned count = 1;
        for (char* p = buffer_; *p; ++p) if (*p == ',') {
            if (count == 21) return false;
            *p = '\0'; fields[count++] = p + 1;
        }
        // Sin los tres primeros campos no hay trama. Con o sin identificador de
        // senal, el resto tiene que venir en grupos completos de cuatro.
        if (count < 4) return false;
        const unsigned tail = count - 4;
        const unsigned groups = tail / 4;
        const unsigned leftover = tail % 4;
        if (leftover > 1) return false;          // un resto de 2 o 3 es una trama rota
        if (groups > 4) return false;
        const bool hasSignalId = leftover == 1;

        long total = 0, number = 0, inView = 0;
        if (!integer(fields[1], total) || !integer(fields[2], number) || !integer(fields[3], inView)) return false;
        if (total < 1 || total > 9 || number < 1 || number > total || inView > 200) return false;
        result.total_messages = uint8_t(total);
        result.message_number = uint8_t(number);
        result.satellites_in_view = uint8_t(inView);

        if (hasSignalId) {
            long signal = 0;
            if (!integer(fields[count - 1], signal) || signal > 15) return false;
            result.signal_id = uint8_t(signal);
        }

        for (unsigned g = 0; g < groups; ++g) {
            const unsigned base = 4 + g * 4;
            long prn = 0;
            // Un grupo entero vacio es relleno del receptor, no un satelite.
            if (!*fields[base] && !*fields[base + 1] && !*fields[base + 2] && !*fields[base + 3]) continue;
            if (!integer(fields[base], prn) || prn < 1 || prn > 255) return false;

            SvObservation sv;
            sv.prn = uint8_t(prn);

            long elevation = 0; bool present = false;
            if (!optionalInteger(fields[base + 1], elevation, present)) return false;
            if (present) {
                if (elevation > 90) return false;
                sv.elevation_deg = int8_t(elevation);
            }

            long azimuth = 0;
            if (!optionalInteger(fields[base + 2], azimuth, present)) return false;
            if (present) {
                if (azimuth > 359) return false;
                sv.azimuth_deg = int16_t(azimuth);
            }

            long cno = 0;
            if (!optionalInteger(fields[base + 3], cno, present)) return false;
            if (present) {
                if (cno > 99) return false;
                sv.cno_dbhz = uint8_t(cno);
                // Vacio es "a la vista sin rastrear"; un cero declarado tambien
                // lo es, porque una senal medida de potencia nula no existe.
                sv.tracked = cno > 0;
            }
            result.satellites[result.count++] = sv;
        }
        return true;
    }
};
}
