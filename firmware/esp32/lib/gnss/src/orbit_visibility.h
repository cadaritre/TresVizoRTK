#pragma once
#include <cctype>
#include <cmath>
#include <cstdint>
#include <cstdio>
#include <cstdlib>
#include <cstring>

namespace gnss {
// Satélites VISIBLES: los que la geometría pone sobre la máscara del receptor,
// se oigan o no. Es la cifra comparable a la lista del Emlid; no son los
// RASTREADOS (los que el UM980 oye, de GSV) ni los USADOS (los de la solución).
//
// El UM980 no expone su almanaque en ningún log (manual N4 R1.4 y R1.6: SATELLITE
// y SATECEF solo traen lo rastreado), así que el ESP32 lo calcula con los TLE
// públicos de CelesTrak y la posición de la GGA.
//
// Propagación Kepler + J2 desde los elementos medios del TLE. Frente a SGP4
// difiere menos de 0.15° en elevación durante 72 h en las 163 órbitas GNSS
// (medido el 27-09-2026); un satélite a menos de ~0.15° de la máscara puede
// contarse distinto. Sin Arduino a propósito: se prueba en la PC
// (test/orbit_visibility_test.cpp).

struct OrbitElements {
    char sys[4] = {};           // "GPS", "GLO", "GAL", "BDS", "QZS"
    double epochUnix = 0;       // s
    double inc = 0, raan = 0, ecc = 0, argp = 0, m = 0;  // rad
    double n = 0;               // rad/s
};

// Las constelaciones que rastrea el UM980 con SIGNALGROUP 1. Sin SBAS (el grupo
// gnss de CelesTrak no las trae) ni NavIC. nullptr si no es ninguna.
inline const char* orbitSystem(const char* name) {
    char upper[40] = {};
    for (size_t i = 0; i + 1 < sizeof(upper) && name[i]; ++i) upper[i] = char(std::toupper((unsigned char)name[i]));
    if (!std::strncmp(upper, "GPS", 3)) return "GPS";
    if (std::strstr(upper, "COSMOS") || std::strstr(upper, "GLONASS")) return "GLO";
    if (std::strstr(upper, "GSAT") || std::strstr(upper, "GALILEO")) return "GAL";
    if (std::strstr(upper, "BEIDOU")) return "BDS";
    if (!std::strncmp(upper, "QZS", 3) || std::strstr(upper, "MICHIBIKI")) return "QZS";
    return nullptr;
}

// Suma de control de una línea TLE: dígitos, y 1 por cada signo menos, módulo 10.
inline bool tleChecksumOk(const char* line) {
    if (std::strlen(line) < 69) return false;
    unsigned sum = 0;
    for (unsigned i = 0; i < 68; ++i) {
        if (line[i] >= '0' && line[i] <= '9') sum += unsigned(line[i] - '0');
        else if (line[i] == '-') sum += 1;
    }
    return line[68] >= '0' && line[68] <= '9' && sum % 10 == unsigned(line[68] - '0');
}

// Días desde 1970-01-01 (algoritmo de calendario civil de H. Hinnant).
inline int64_t daysFromCivil(int y, unsigned m, unsigned d) {
    y -= m <= 2;
    const int64_t era = (y >= 0 ? y : y - 399) / 400;
    const unsigned yoe = unsigned(y - era * 400);
    const unsigned doy = (153 * (m > 2 ? m - 3 : m + 9) + 2) / 5 + d - 1;
    const unsigned doe = yoe * 365 + yoe / 4 - yoe / 100 + doy;
    return era * 146097 + int64_t(doe) - 719468;
}

// Campo de ancho fijo de una línea TLE, como número.
inline double tleField(const char* line, unsigned from, unsigned to) {
    char buffer[24] = {};
    const unsigned width = to - from < sizeof(buffer) - 1 ? to - from : unsigned(sizeof(buffer) - 1);
    std::memcpy(buffer, line + from, width);
    return std::strtod(buffer, nullptr);
}

inline bool parseTle(const char* name, const char* l1, const char* l2, OrbitElements& out) {
    const char* sys = orbitSystem(name);
    if (!sys || l1[0] != '1' || l2[0] != '2' || !tleChecksumOk(l1) || !tleChecksumOk(l2)) return false;
    const double deg = 3.14159265358979323846 / 180.0;
    const int yy = int(tleField(l1, 18, 20));
    const int year = yy < 57 ? 2000 + yy : 1900 + yy;
    const double doy = tleField(l1, 20, 32);
    std::memcpy(out.sys, sys, 4);
    out.epochUnix = (double(daysFromCivil(year, 1, 1)) + doy - 1.0) * 86400.0;
    out.inc = tleField(l2, 8, 16) * deg;
    out.raan = tleField(l2, 17, 25) * deg;
    char ecc[12] = "0.";
    std::memcpy(ecc + 2, l2 + 26, 7);
    out.ecc = std::strtod(ecc, nullptr);
    out.argp = tleField(l2, 34, 42) * deg;
    out.m = tleField(l2, 43, 51) * deg;
    out.n = tleField(l2, 52, 63) * 2.0 * 3.14159265358979323846 / 86400.0;
    return out.n > 0 && out.ecc < 1;
}

// «Date: Sun, 28 Sep 2026 01:05:07 GMT» (RFC 7231) a segundos Unix.
inline bool parseHttpDate(const char* value, double& unix) {
    // «Www, DD Mmm AAAA hh:mm:ss GMT», campo a campo.
    const char* p = std::strchr(value, ',');
    if (!p) return false;
    char* end = nullptr;
    const long day = std::strtol(p + 1, &end, 10);
    if (end == p + 1 || *end != ' ') return false;
    const char* month = end + 1;
    static const char* const months[] = {"Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"};
    unsigned m = 0;
    for (unsigned i = 0; i < 12; ++i) if (!std::strncmp(month, months[i], 3)) m = i + 1;
    if (!m || month[3] != ' ') return false;
    const long year = std::strtol(month + 4, &end, 10);
    if (*end != ' ') return false;
    const long hour = std::strtol(end + 1, &end, 10);
    if (*end != ':') return false;
    const long minute = std::strtol(end + 1, &end, 10);
    if (*end != ':') return false;
    const long second = std::strtol(end + 1, &end, 10);
    if (day < 1 || day > 31 || year < 2020 || hour < 0 || hour > 23 || minute < 0 || minute > 59 || second < 0 || second > 60) return false;
    unix = double(daysFromCivil(int(year), m, unsigned(day))) * 86400.0 + double(hour) * 3600.0 + double(minute) * 60.0 + double(second);
    return true;
}

// Posición en TEME (km), Kepler con las tasas seculares de J2.
inline void positionTeme(const OrbitElements& el, double tUnix, double r[3]) {
    const double mu = 398600.4418, re = 6378.137, j2 = 1.08262668e-3;
    const double a = std::cbrt(mu / (el.n * el.n));
    const double p = a * (1 - el.ecc * el.ecc);
    const double k = 1.5 * j2 * (re / p) * (re / p) * el.n;
    const double dt = tUnix - el.epochUnix;
    const double si = std::sin(el.inc);
    const double raan = el.raan - k * std::cos(el.inc) * dt;
    const double argp = el.argp + k * (2 - 2.5 * si * si) * dt;
    const double m = el.m + (el.n + k * std::sqrt(1 - el.ecc * el.ecc) * (1 - 1.5 * si * si)) * dt;
    double e = m;
    for (int i = 0; i < 12; ++i) e -= (e - el.ecc * std::sin(e) - m) / (1 - el.ecc * std::cos(e));
    const double xp = a * (std::cos(e) - el.ecc);
    const double yp = a * std::sqrt(1 - el.ecc * el.ecc) * std::sin(e);
    const double cw = std::cos(argp), sw = std::sin(argp), cO = std::cos(raan), sO = std::sin(raan), ci = std::cos(el.inc);
    r[0] = (cw * cO - sw * sO * ci) * xp + (-sw * cO - cw * sO * ci) * yp;
    r[1] = (cw * sO + sw * cO * ci) * xp + (-sw * sO + cw * cO * ci) * yp;
    r[2] = (sw * si) * xp + (cw * si) * yp;
}

// Tiempo sidéreo medio de Greenwich (IAU-82), con UT1 ≈ UTC.
inline double gmstRad(double tUnix) {
    const double jd = tUnix / 86400.0 + 2440587.5;
    const double t = (jd - 2451545.0) / 36525.0;
    const double g = 67310.54841 + (876600.0 * 3600 + 8640184.812866) * t + 0.093104 * t * t - 6.2e-6 * t * t * t;
    double s = std::fmod(g, 86400.0);
    if (s < 0) s += 86400.0;
    return s / 240.0 * 3.14159265358979323846 / 180.0;
}

inline void topocentric(const OrbitElements& el, double tUnix, double latDeg, double lonDeg, double hM,
                        double& elevationDeg, double& azimuthDeg) {
    const double deg = 3.14159265358979323846 / 180.0;
    double r[3];
    positionTeme(el, tUnix, r);
    const double th = gmstRad(tUnix);
    const double x = (r[0] * std::cos(th) + r[1] * std::sin(th)) * 1000;
    const double y = (-r[0] * std::sin(th) + r[1] * std::cos(th)) * 1000;
    const double z = r[2] * 1000;
    const double a = 6378137.0, f = 1 / 298.257223563, e2 = f * (2 - f);
    const double la = latDeg * deg, lo = lonDeg * deg;
    const double nrad = a / std::sqrt(1 - e2 * std::sin(la) * std::sin(la));
    const double dx = x - (nrad + hM) * std::cos(la) * std::cos(lo);
    const double dy = y - (nrad + hM) * std::cos(la) * std::sin(lo);
    const double dz = z - (nrad * (1 - e2) + hM) * std::sin(la);
    const double east = -std::sin(lo) * dx + std::cos(lo) * dy;
    const double north = -std::sin(la) * std::cos(lo) * dx - std::sin(la) * std::sin(lo) * dy + std::cos(la) * dz;
    const double up = std::cos(la) * std::cos(lo) * dx + std::cos(la) * std::sin(lo) * dy + std::sin(la) * dz;
    elevationDeg = std::atan2(up, std::sqrt(east * east + north * north)) / deg;
    azimuthDeg = std::fmod(std::atan2(east, north) / deg + 360.0, 360.0);
}

struct VisibleCount {
    unsigned total = 0, gps = 0, glo = 0, gal = 0, bds = 0, qzs = 0;
};

inline VisibleCount countVisible(const OrbitElements* elements, unsigned count, double tUnix,
                                 double latDeg, double lonDeg, double hM, double maskDeg) {
    VisibleCount out;
    for (unsigned i = 0; i < count; ++i) {
        double el = 0, az = 0;
        topocentric(elements[i], tUnix, latDeg, lonDeg, hM, el, az);
        if (el < maskDeg) continue;
        ++out.total;
        const char* s = elements[i].sys;
        if (!std::strcmp(s, "GPS")) ++out.gps;
        else if (!std::strcmp(s, "GLO")) ++out.glo;
        else if (!std::strcmp(s, "GAL")) ++out.gal;
        else if (!std::strcmp(s, "BDS")) ++out.bds;
        else if (!std::strcmp(s, "QZS")) ++out.qzs;
    }
    return out;
}

// Lector de TLE línea a línea (el cuerpo HTTP llega por trozos): con nombre,
// línea 1 y línea 2 consecutivas entrega un elemento. Descarta el resto.
class TleReader {
public:
    // Devuelve true cuando `out` trae un elemento nuevo.
    bool feed(const char* raw, OrbitElements& out) {
        char line[80] = {};
        size_t n = 0;
        for (; raw[n] && raw[n] != '\r' && raw[n] != '\n' && n < sizeof(line) - 1; ++n) line[n] = raw[n];
        while (n && line[n - 1] == ' ') line[--n] = 0;
        if (!n) return false;
        std::memcpy(slots_[0], slots_[1], sizeof(slots_[0]));
        std::memcpy(slots_[1], slots_[2], sizeof(slots_[0]));
        std::memcpy(slots_[2], line, sizeof(line));
        if (slots_[1][0] == '1' && slots_[1][1] == ' ' && slots_[2][0] == '2' && slots_[2][1] == ' ') {
            const bool ok = parseTle(slots_[0], slots_[1], slots_[2], out);
            slots_[0][0] = slots_[1][0] = slots_[2][0] = 0;
            return ok;
        }
        return false;
    }

private:
    char slots_[3][80] = {};
};
}  // namespace gnss
