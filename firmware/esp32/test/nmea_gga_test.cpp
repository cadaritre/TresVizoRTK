#include "nmea_gga.h"
#include <cassert>
#include <cstdio>
#include <string>

std::string sentence(const std::string& body) {
    unsigned char checksum = 0;
    for (char c : body) checksum ^= c;
    char suffix[8]; std::snprintf(suffix, sizeof(suffix), "*%02X\r\n", checksum);
    return "$" + body + suffix;
}
bool send(gnss::GgaParser& p, gnss::Gga& g, const std::string& line) {
    bool accepted = false;
    for (char c : line) accepted |= p.feed(c, 123456, g);
    return accepted;
}
int main() {
    gnss::GgaParser p; gnss::Gga g;
    const std::string valid = "GNGGA,120000.10,2800.000000,N,10600.000000,W,4,20,0.7,100.1,M,-20.2,M,,";
    assert(send(p, g, sentence(valid)));
    assert(g.utc_ms == 43200100 && g.arrival_us == 123456 && g.has_position);
    assert(g.latitude_deg == 28 && g.longitude_deg == -106);
    assert(g.quality == 4 && g.satellites == 20);
    assert(std::fabs(g.altitude_msl_m - 100.1) < 1e-9);
    assert(std::fabs(g.geoid_separation_m + 20.2) < 1e-9);
    auto corrupt = sentence(valid); corrupt[10] = '9';
    assert(!send(p, g, corrupt));
    assert(g.quality == 4); // Rejection is transactional.
    assert(!send(p, g, sentence("GNGGA,120000.00,2860.00,N,10600.00,W,4,20,1,0,M,0,M,,")));
    assert(!send(p, g, sentence("GNGGA,240000.00,2800.00,N,10600.00,W,4,20,1,0,M,0,M,,")));
    assert(!send(p, g, sentence("GNGGA,120000.00,2800.00,X,10600.00,W,4,20,1,0,M,0,M,,")));
    assert(!send(p, g, sentence("GNGGA,120000.00,2800.00,N,10600.00,W,4,20,nan,0,M,0,M,,")));
    assert(!send(p, g, sentence("GNGGA,120000.00,2800.00,N,10600.00,W,4,20,1,0,F,0,M,,")));
    assert(!send(p, g, sentence("GNGGA,120000.00,2800.00,N,10600.00,W,4,20,1,0,M,0,M,,,extra")));
    assert(!send(p, g, "$" + std::string(300, 'x') + "\n"));
    assert(p.overflow == 1);
    assert(send(p, g, "$broken" + sentence(valid)));
    assert(send(p, g, sentence("GNGGA,120001.00,,,,,0,00,,,,,,,")));
    assert(!g.has_position && std::isnan(g.latitude_deg) && std::isnan(g.altitude_msl_m));
    assert(send(p, g, sentence("GNGGA,,,,,,0,00,,,,,,,")));
    assert(!g.has_utc && !g.has_position);
    assert(send(p, g, sentence("GNGGA,235959.90,9000.00,S,18000.00,E,1,10,1,0,M,0,M,,")));
    assert(g.utc_ms == 86399900 && g.latitude_deg == -90 && g.longitude_deg == 180);
    assert(send(p, g, sentence("GNGGA,000000.00,0000.00,N,00000.00,E,1,10,1,0,M,0,M,,")));
    assert(g.utc_ms == 0);
    assert(send(p, g, "$GNGGA,,,,,,0,,,,,,,,*78\r\n"));
    assert(!g.has_satellites && !g.has_utc && !g.has_position);
    std::puts("GGA: validación, pérdida de fix, límites y resincronización OK");
}
