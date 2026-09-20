#pragma once
#include <cmath>
#include <cstdint>
#include <cstdlib>
#include <cstring>

namespace gnss {
// GGA UTC contains time of day only. It does not establish a date or datum.
struct Gga {
    uint32_t utc_ms = 0;
    uint64_t arrival_us = 0;
    double latitude_deg = NAN, longitude_deg = NAN;
    double altitude_msl_m = NAN, geoid_separation_m = NAN, hdop = NAN;
    unsigned quality = 0, satellites = 0;
    bool has_utc = false, has_position = false, has_satellites = false;
};

class GgaParser {
public:
    uint32_t accepted = 0, rejected = 0, overflow = 0;
    // Call from acquisition, independently of HTTP/BLE refresh. No heap allocation.
    bool feed(char byte, uint64_t arrival_us, Gga& output) {
        if (byte == '$') { length_ = 0; collecting_ = true; return false; }
        if (!collecting_) return false;
        if (byte == '\n') {
            collecting_ = false;
            if (length_ && buffer_[length_ - 1] == '\r') --length_;
            buffer_[length_] = '\0';
            if (length_ < 6 || std::strncmp(buffer_ + 2, "GGA,", 4)) return false;
            Gga next;
            next.arrival_us = arrival_us;
            if (!decode(next)) { ++rejected; return false; }
            output = next;
            ++accepted;
            return true;
        }
        if (length_ == sizeof(buffer_) - 1) {
            collecting_ = false; ++overflow; return false;
        }
        if (byte == '\0') { collecting_ = false; ++rejected; return false; }
        buffer_[length_++] = byte;
        return false;
    }
private:
    char buffer_[256] = {};
    size_t length_ = 0;
    bool collecting_ = false;
    static int hex(char c) {
        if (c >= '0' && c <= '9') return c - '0';
        if (c >= 'A' && c <= 'F') return c - 'A' + 10;
        if (c >= 'a' && c <= 'f') return c - 'a' + 10;
        return -1;
    }
    static bool number(const char* s, double& result, bool signed_value = false) {
        if (signed_value && (*s == '-' || *s == '+')) {
            // Keep the original sign for conversion below.
        } else if (*s == '-' || *s == '+') return false;
        const char* p = s;
        if (signed_value && (*p == '-' || *p == '+')) ++p;
        unsigned digits = 0, dots = 0;
        for (; *p; ++p) {
            if (*p == '.') { if (++dots > 1) return false; }
            else if (*p >= '0' && *p <= '9') ++digits;
            else return false;
        }
        if (!digits) return false;
        result = std::strtod(s, nullptr);
        return std::isfinite(result);
    }
    static bool integer(const char* s, unsigned max, unsigned& result) {
        if (!*s) return false;
        unsigned n = 0;
        for (; *s; ++s) {
            if (*s < '0' || *s > '9') return false;
            n = n * 10 + (*s - '0');
            if (n > max) return false;
        }
        result = n; return true;
    }
    static bool coordinate(const char* s, const char* dir, bool lat, double& out) {
        const size_t width = lat ? 4 : 5;
        if (std::strlen(s) < width || (s[width] && s[width] != '.')) return false;
        for (size_t i = 0; i < width; ++i) if (s[i] < '0' || s[i] > '9') return false;
        double value;
        if (!number(s, value) || std::strlen(dir) != 1) return false;
        if (lat ? (*dir != 'N' && *dir != 'S') : (*dir != 'E' && *dir != 'W')) return false;
        const double degrees = std::floor(value / 100), minutes = value - degrees * 100;
        if (minutes >= 60 || degrees > (lat ? 90 : 180) ||
            (degrees == (lat ? 90 : 180) && minutes != 0)) return false;
        out = (degrees + minutes / 60) * ((*dir == 'S' || *dir == 'W') ? -1 : 1);
        return true;
    }
    bool decode(Gga& result) {
        char* star = std::strchr(buffer_, '*');
        if (!star || std::strlen(star) != 3 || hex(star[1]) < 0 || hex(star[2]) < 0) return false;
        uint8_t check = 0;
        for (char* p = buffer_; p < star; ++p) check ^= static_cast<uint8_t>(*p);
        if (check != ((hex(star[1]) << 4) | hex(star[2]))) return false;
        *star = '\0';
        char* fields[15] = {buffer_};
        unsigned count = 1;
        for (char* p = buffer_; *p; ++p) if (*p == ',') {
            if (count == 15) return false;
            *p = '\0'; fields[count++] = p + 1;
        }
        if (count != 15 || !integer(fields[6], 8, result.quality)) return false;
        if (*fields[7]) {
            if (!integer(fields[7], 255, result.satellites)) return false;
            result.has_satellites = true;
        } else if (result.quality) return false;
        if (*fields[1]) {
            const char* t = fields[1];
            if (std::strlen(t) < 6 || (t[6] && t[6] != '.')) return false;
            for (unsigned i = 0; i < 6; ++i) if (t[i] < '0' || t[i] > '9') return false;
            double raw;
            if (!number(t, raw)) return false;
            unsigned h = (t[0]-'0')*10+t[1]-'0', m = (t[2]-'0')*10+t[3]-'0';
            const double sec = raw - h*10000 - m*100;
            if (h > 23 || m > 59 || sec >= 60) return false;
            result.utc_ms = h*3600000 + m*60000 + static_cast<uint32_t>(std::llround(sec*1000));
            if (result.utc_ms >= 86400000) return false;
            result.has_utc = true;
        }
        if (result.quality) {
            if (!result.has_utc || !coordinate(fields[2], fields[3], true, result.latitude_deg) ||
                !coordinate(fields[4], fields[5], false, result.longitude_deg)) return false;
            result.has_position = true;
        }
        if (*fields[8] && (!number(fields[8], result.hdop) || result.hdop < 0)) return false;
        if (*fields[9] && (!number(fields[9], result.altitude_msl_m, true) || std::strcmp(fields[10], "M"))) return false;
        if (*fields[11] && (!number(fields[11], result.geoid_separation_m, true) || std::strcmp(fields[12], "M"))) return false;
        return true;
    }
};
}
