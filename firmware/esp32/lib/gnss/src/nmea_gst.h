#pragma once
#include <cmath>
#include <cstdint>
#include <cstdlib>
#include <cstring>

namespace gnss {
// GST carries the receiver's own error estimate, which GGA does not. These are
// the receiver's standard deviations: an internal estimate of its solution, not
// a verified accuracy. No independent measurement backs them.
struct Gst {
    uint64_t arrival_us = 0;
    double latitude_sigma_m = NAN, longitude_sigma_m = NAN, altitude_sigma_m = NAN;
    // sqrt(lat^2 + lon^2). Sigma at 1 standard deviation, not a 95% radius.
    double horizontal_sigma_m = NAN;
    bool has_sigma = false;
};

class GstParser {
public:
    uint32_t accepted = 0, rejected = 0, overflow = 0;
    bool feed(char byte, uint64_t arrival_us, Gst& output) {
        if (byte == '$') { length_ = 0; collecting_ = true; return false; }
        if (!collecting_) return false;
        if (byte == '\n') {
            collecting_ = false;
            if (length_ && buffer_[length_ - 1] == '\r') --length_;
            buffer_[length_] = '\0';
            if (length_ < 6 || std::strncmp(buffer_ + 2, "GST,", 4)) return false;
            Gst next;
            next.arrival_us = arrival_us;
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
    char buffer_[128] = {};
    size_t length_ = 0;
    bool collecting_ = false;

    static int hex(char c) {
        if (c >= '0' && c <= '9') return c - '0';
        if (c >= 'A' && c <= 'F') return c - 'A' + 10;
        if (c >= 'a' && c <= 'f') return c - 'a' + 10;
        return -1;
    }
    // Desviaciones: nunca negativas y siempre finitas. Un campo vacío es válido
    // y deja el valor sin definir; el receptor todavía no lo estima.
    static bool sigma(const char* s, double& result) {
        if (!*s) return false;
        const char* p = s;
        unsigned digits = 0, dots = 0;
        for (; *p; ++p) {
            if (*p == '.') { if (++dots > 1) return false; }
            else if (*p >= '0' && *p <= '9') ++digits;
            else return false;
        }
        if (!digits) return false;
        result = std::strtod(s, nullptr);
        return std::isfinite(result) && result >= 0;
    }
    bool decode(Gst& result) {
        char* star = std::strchr(buffer_, '*');
        if (!star || std::strlen(star) != 3 || hex(star[1]) < 0 || hex(star[2]) < 0) return false;
        uint8_t check = 0;
        for (char* p = buffer_; p < star; ++p) check ^= static_cast<uint8_t>(*p);
        if (check != ((hex(star[1]) << 4) | hex(star[2]))) return false;
        *star = '\0';
        char* fields[9] = {buffer_};
        unsigned count = 1;
        for (char* p = buffer_; *p; ++p) if (*p == ',') {
            if (count == 9) return false;
            *p = '\0'; fields[count++] = p + 1;
        }
        if (count != 9) return false;
        // Campos 6, 7 y 8: sigma de latitud, longitud y altura, en metros.
        const bool lat = sigma(fields[6], result.latitude_sigma_m);
        const bool lon = sigma(fields[7], result.longitude_sigma_m);
        const bool alt = sigma(fields[8], result.altitude_sigma_m);
        if (lat && lon) {
            result.horizontal_sigma_m = std::sqrt(
                result.latitude_sigma_m * result.latitude_sigma_m +
                result.longitude_sigma_m * result.longitude_sigma_m);
            result.has_sigma = true;
        } else if (!alt) {
            return false; // una trama sin ninguna desviación no aporta nada
        }
        return true;
    }
};
}
