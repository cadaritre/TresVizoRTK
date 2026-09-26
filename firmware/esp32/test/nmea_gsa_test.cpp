#include "nmea_gsa.h"
#include <cassert>
#include <cmath>
#include <cstdio>
#include <string>

std::string sentence(const std::string& body) {
    unsigned char checksum = 0;
    for (char c : body) checksum ^= c;
    char suffix[8]; std::snprintf(suffix, sizeof(suffix), "*%02X\r\n", checksum);
    return "$" + body + suffix;
}
bool send(gnss::GsaParser& p, gnss::Gsa& g, const std::string& line) {
    bool accepted = false;
    for (char c : line) accepted |= p.feed(c, 555, g);
    return accepted;
}

int main() {
    gnss::GsaParser p; gnss::Gsa g;

    // NMEA 4.10: emisor GN e identificador de sistema al final.
    assert(send(p, g, sentence("GNGSA,A,3,04,05,,09,12,,,24,,,,,2.50,1.30,2.10,1")));
    assert(!std::strcmp(g.talker, "GN"));
    assert(g.mode == 'A' && g.fix_type == 3 && g.system_id == 1);
    assert(g.count == 5);
    assert(g.prns[0] == 4 && g.prns[1] == 5 && g.prns[2] == 9 && g.prns[3] == 12 && g.prns[4] == 24);
    assert(std::fabs(g.pdop - 2.5) < 1e-9);
    assert(std::fabs(g.hdop - 1.3) < 1e-9);
    assert(std::fabs(g.vdop - 2.1) < 1e-9);
    assert(g.arrival_us == 555);

    // **El identificador de sistema es lo que separa un 12 de otro.** La misma
    // trama con sistema 2 son satelites de GLONASS, no los mismos de GPS.
    gnss::Gsa glonass;
    assert(send(p, glonass, sentence("GNGSA,A,3,12,,,,,,,,,,,,2.50,1.30,2.10,2")));
    assert(glonass.system_id == 2 && glonass.prns[0] == 12);
    assert(glonass.system_id != g.system_id);

    // Sin identificador de sistema, 18 campos: NMEA anterior a 4.10.
    assert(send(p, g, sentence("GPGSA,A,3,04,05,,09,,,,,,,,,2.50,1.30,2.10")));
    assert(g.system_id == 0 && g.count == 3);

    // Doce satelites llenos, que es el maximo del formato.
    assert(send(p, g, sentence("GNGSA,A,3,01,02,03,04,05,06,07,08,09,10,11,12,1.80,0.90,1.50,1")));
    assert(g.count == 12 && g.prns[11] == 12);

    // Sin solucion: la trama es valida y lo dice. No se puede confundir con un
    // fallo de lectura.
    assert(send(p, g, sentence("GNGSA,A,1,,,,,,,,,,,,,,,,1")));
    assert(g.fix_type == 1 && g.count == 0);
    assert(std::isnan(g.pdop) && std::isnan(g.hdop) && std::isnan(g.vdop));

    // Manual en dos dimensiones: se guarda porque da cotas con aspecto de medidas.
    assert(send(p, g, sentence("GNGSA,M,2,04,,,,,,,,,,,,2.50,1.30,2.10,1")));
    assert(g.mode == 'M' && g.fix_type == 2);

    // Lo que hay que rechazar.
    assert(!send(p, g, sentence("GNGSA,X,3,04,,,,,,,,,,,,2.50,1.30,2.10,1")));   // modo raro
    assert(!send(p, g, sentence("GNGSA,A,4,04,,,,,,,,,,,,2.50,1.30,2.10,1")));   // sin ese tipo de fijo
    assert(!send(p, g, sentence("GNGSA,A,3,04,,,,,,,,,,,,-1.0,1.30,2.10,1")));   // DOP negativo
    assert(!send(p, g, sentence("GNGSA,A,3,04,,,,,,,,,,,,dos,1.30,2.10,1")));    // DOP con letras
    assert(!send(p, g, sentence("GNGSA,A,3,04,,,,,,,2.50,1.30,2.10,1")));        // faltan campos

    gnss::Gsa previo = g;
    auto corrupta = sentence("GNGSA,A,3,07,,,,,,,,,,,,2.50,1.30,2.10,1");
    corrupta[9] = '9';
    assert(!send(p, g, corrupta));
    assert(g.prns[0] == previo.prns[0]);   // el rechazo es entero

    std::printf("nmea_gsa_test OK (%u aceptadas, %u rechazadas)\n", p.accepted, p.rejected);
    return 0;
}
