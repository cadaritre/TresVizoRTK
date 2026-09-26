#pragma once
#include <cmath>
#include <cstdint>
#include <cstdlib>
#include <cstring>

namespace gnss {
// GSA dice **cuales** de los satelites a la vista entraron en la solucion, y
// trae los tres DOP. GGA solo da el recuento y el HDOP.
//
// La diferencia importa en campo: un equipo que ve veinte satelites y usa ocho
// no tiene el mismo problema que uno que ve ocho. La primera es una mascara de
// elevacion o una constelacion apagada; la segunda es el cielo o la antena.
//
// En NMEA 4.10 cada constelacion manda su propia GSA con emisor GN y un
// identificador de sistema al final. **Sin ese identificador, dos GSA seguidas
// son indistinguibles** y los PRN de GLONASS se mezclan con los de GPS: el 12
// de una no es el 12 de la otra.
struct Gsa {
    uint64_t arrival_us = 0;
    char talker[3] = {};
    // 1 GPS, 2 GLONASS, 3 Galileo, 4 BeiDou, 5 QZSS. 0 si la trama no lo trae.
    uint8_t system_id = 0;
    // 1 sin solucion, 2 en dos dimensiones, 3 en tres.
    uint8_t fix_type = 0;
    // Automatico o manual. Se guarda porque un receptor clavado en 2D manual
    // da cotas que parecen medidas.
    char mode = 0;
    uint8_t count = 0;
    uint8_t prns[12] = {};
    double pdop = NAN, hdop = NAN, vdop = NAN;
};

class GsaParser {
public:
    uint32_t accepted = 0, rejected = 0, overflow = 0;

    bool feed(char byte, uint64_t arrival_us, Gsa& output) {
        if (byte == '$') { length_ = 0; collecting_ = true; return false; }
        if (!collecting_) return false;
        if (byte == '\n') {
            collecting_ = false;
            if (length_ && buffer_[length_ - 1] == '\r') --length_;
            buffer_[length_] = '\0';
            if (length_ < 6 || std::strncmp(buffer_ + 2, "GSA,", 4)) return false;
            Gsa next;
            next.arrival_us = arrival_us;
            next.talker[0] = buffer_[0];
            next.talker[1] = buffer_[1];
            if (!decode(next)) { ++rejected; return false; }
            output = next;
            ++accepted;
            return true;
        }
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
    static bool integer(const char* s, long& result) {
        if (!*s) return false;
        for (const char* p = s; *p; ++p) if (*p < '0' || *p > '9') return false;
        result = std::strtol(s, nullptr, 10);
        return true;
    }
    // Un DOP vacio es corriente y valido: el receptor no lo estima todavia.
    // Un DOP negativo o con letras, no.
    static bool dop(const char* s, double& result) {
        if (!*s) return true;
        unsigned digits = 0, dots = 0;
        for (const char* p = s; *p; ++p) {
            if (*p == '.') { if (++dots > 1) return false; }
            else if (*p >= '0' && *p <= '9') ++digits;
            else return false;
        }
        if (!digits) return false;
        result = std::strtod(s, nullptr);
        return std::isfinite(result) && result >= 0;
    }

    bool decode(Gsa& result) {
        char* star = std::strchr(buffer_, '*');
        if (!star || std::strlen(star) != 3 || hex(star[1]) < 0 || hex(star[2]) < 0) return false;
        uint8_t check = 0;
        for (char* p = buffer_; p < star; ++p) check ^= static_cast<uint8_t>(*p);
        if (check != ((hex(star[1]) << 4) | hex(star[2]))) return false;
        *star = '\0';

        char* fields[20] = {buffer_};
        unsigned count = 1;
        for (char* p = buffer_; *p; ++p) if (*p == ',') {
            if (count == 20) return false;
            *p = '\0'; fields[count++] = p + 1;
        }
        // 18 campos sin identificador de sistema, 19 con el.
        if (count != 18 && count != 19) return false;

        if (std::strlen(fields[1]) != 1) return false;
        result.mode = fields[1][0];
        if (result.mode != 'M' && result.mode != 'A') return false;

        long fix = 0;
        if (!integer(fields[2], fix) || fix < 1 || fix > 3) return false;
        result.fix_type = uint8_t(fix);

        for (unsigned i = 0; i < 12; ++i) {
            const char* field = fields[3 + i];
            if (!*field) continue;                       // hueco: no hay satelite ahi
            long prn = 0;
            if (!integer(field, prn) || prn < 1 || prn > 255) return false;
            result.prns[result.count++] = uint8_t(prn);
        }

        if (!dop(fields[15], result.pdop)) return false;
        if (!dop(fields[16], result.hdop)) return false;
        if (!dop(fields[17], result.vdop)) return false;

        if (count == 19) {
            long system = 0;
            if (!integer(fields[18], system) || system < 1 || system > 15) return false;
            result.system_id = uint8_t(system);
        }
        return true;
    }
};
}
