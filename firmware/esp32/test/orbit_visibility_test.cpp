#include "orbit_visibility.h"
#include <cassert>
#include <cmath>
#include <cstdio>
#include <fstream>
#include <sstream>
#include <string>
#include <vector>

// Satélites visibles calculados en el ESP32 (orbit_visibility.h) contra las
// fijaciones públicas de tests/fixtures: TLE de CelesTrak del 27-09-2026 y
// posición redondeada (28.6, -106.1, 1500 m). Las referencias salen de SGP4
// (python-sgp4) y del mismo Kepler + J2 escrito en Python.

static std::string fixture(const char* name) {
    std::string base = __FILE__;
    base = base.substr(0, base.find_last_of("/\\"));
    std::ifstream in(base + "/../../../tests/fixtures/" + name, std::ios::binary);
    assert(in && "falta la fijacion");
    std::stringstream s;
    s << in.rdbuf();
    return s.str();
}

// Lector mínimo de números del JSON de referencia: busca "clave": valor a partir de `from`.
static double number(const std::string& json, const std::string& key, size_t from, size_t* at = nullptr) {
    const size_t k = json.find("\"" + key + "\":", from);
    assert(k != std::string::npos);
    if (at) *at = k;
    return std::strtod(json.c_str() + k + key.size() + 3, nullptr);
}

static std::string text(const std::string& json, const std::string& key, size_t from) {
    const size_t k = json.find("\"" + key + "\": \"", from);
    assert(k != std::string::npos);
    const size_t start = k + key.size() + 5;
    return json.substr(start, json.find('"', start) - start);
}

int main() {
    // Suma de control TLE: una línea buena y la misma con el último dígito cambiado.
    const char* l1 = "1 26407U 00040A   26270.25755789  .00000020  00000+0  00000+0 0  9998";
    assert(gnss::tleChecksumOk(l1));
    std::string bad = l1;
    bad[68] = '7';
    assert(!gnss::tleChecksumOk(bad.c_str()));

    // Fecha HTTP a Unix. 2026-09-28 00:30:00 UTC = 1790555400.
    double unix = 0;
    assert(gnss::parseHttpDate("Mon, 28 Sep 2026 00:30:00 GMT", unix) && unix == 1790555400.0);
    assert(!gnss::parseHttpDate("sin fecha", unix));

    // Constelaciones: solo las que rastrea el UM980.
    assert(!std::strcmp(gnss::orbitSystem("GPS BIIR-5  (PRN 22)"), "GPS"));
    assert(!std::strcmp(gnss::orbitSystem("COSMOS 2545 (760)"), "GLO"));
    assert(!std::strcmp(gnss::orbitSystem("GSAT0202 (GALILEO 6)"), "GAL"));
    assert(!std::strcmp(gnss::orbitSystem("BEIDOU-3 M24 (C46)"), "BDS"));
    assert(!std::strcmp(gnss::orbitSystem("QZS-1R (QZSS/PRN 196)"), "QZS"));
    assert(gnss::orbitSystem("IRNSS-1I") == nullptr);

    // Todas las órbitas del día, leídas línea a línea como llegan por HTTP.
    const std::string tle = fixture("gnss_celestrak_2026-09-27.tle");
    std::vector<gnss::OrbitElements> elements;
    gnss::TleReader reader;
    std::istringstream lines(tle);
    std::string line;
    while (std::getline(lines, line)) {
        gnss::OrbitElements el;
        if (reader.feed(line.c_str(), el)) elements.push_back(el);
    }
    assert(elements.size() > 140);

    const std::string ref = fixture("visibles_referencia.json");
    const double lat = number(ref, "lat_deg", 0), lon = number(ref, "lon_deg", 0), h = number(ref, "altura_elipsoidal_m", 0);
    const double tolerance = number(ref, "tolerancia_recomendada_deg", 0);
    size_t cursor = ref.find("\"instantes\"");
    for (int instant = 0; instant < 3; ++instant) {
        size_t at = 0;
        const double t = number(ref, "t_unix", cursor, &at);
        cursor = at + 1;
        const size_t next = ref.find("\"t_unix\"", cursor);
        const size_t end = next == std::string::npos ? ref.size() : next;
        // Satélites de control de este instante: mismo algoritmo casi exacto; SGP4 dentro de la tolerancia.
        size_t s = ref.find("\"nombre\"", cursor);
        unsigned checked = 0;
        while (s != std::string::npos && s < end) {
            const std::string name = text(ref, "nombre", s), tle1 = text(ref, "tle1", s), tle2 = text(ref, "tle2", s);
            gnss::OrbitElements el;
            assert(gnss::parseTle(name.c_str(), tle1.c_str(), tle2.c_str(), el));
            double elev = 0, az = 0;
            gnss::topocentric(el, t, lat, lon, h, elev, az);
            const double kepler = number(ref, "kepler_j2_el", s), sgp4 = number(ref, "sgp4_el", s);
            if (std::fabs(elev - kepler) >= 0.01 || std::fabs(elev - sgp4) >= tolerance) {
                std::printf("FALLA %s t=%.0f el=%.3f kepler=%.3f sgp4=%.3f\n", name.c_str(), t, elev, kepler, sgp4);
                assert(false);
            }
            ++checked;
            s = ref.find("\"nombre\"", s + 1);
        }
        assert(checked == 10);
        // Conteo sobre la máscara de 5°: exacto contra el mismo algoritmo; SGP4 ±1.
        const auto v = gnss::countVisible(elements.data(), unsigned(elements.size()), t, lat, lon, h, 5.0);
        const double kj2 = number(ref, "total_kepler_j2_mascara_5", cursor), sgp = number(ref, "total_sgp4_mascara_5", cursor);
        if (double(v.total) != kj2 || std::fabs(v.total - sgp) > 1) {
            std::printf("FALLA conteo t=%.0f: %u vs kepler %.0f / sgp4 %.0f\n", t, v.total, kj2, sgp);
            assert(false);
        }
        std::printf("t=%.0f visibles=%u (GPS %u GLO %u GAL %u BDS %u QZS %u)\n", t, v.total, v.gps, v.glo, v.gal, v.bds, v.qzs);
    }
    std::printf("orbit_visibility_test OK (%zu orbitas)\n", elements.size());
    return 0;
}
