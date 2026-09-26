#include "nmea_gsv.h"
#include <cassert>
#include <cstdio>
#include <string>

std::string sentence(const std::string& body) {
    unsigned char checksum = 0;
    for (char c : body) checksum ^= c;
    char suffix[8]; std::snprintf(suffix, sizeof(suffix), "*%02X\r\n", checksum);
    return "$" + body + suffix;
}
bool send(gnss::GsvParser& p, gnss::GsvMessage& m, const std::string& line) {
    bool accepted = false;
    for (char c : line) accepted |= p.feed(c, 987654, m);
    return accepted;
}

int main() {
    gnss::GsvParser p; gnss::GsvMessage m;

    // Trama llena de NMEA 4.10: cuatro satelites y el identificador de senal.
    assert(send(p, m, sentence("GPGSV,3,1,11,02,45,123,42,05,12,045,38,07,67,300,45,09,23,210,33,1")));
    assert(!std::strcmp(m.talker, "GP"));
    assert(m.total_messages == 3 && m.message_number == 1 && m.satellites_in_view == 11);
    assert(m.signal_id == 1 && m.count == 4);
    assert(m.satellites[0].prn == 2 && m.satellites[0].elevation_deg == 45);
    assert(m.satellites[0].azimuth_deg == 123 && m.satellites[0].cno_dbhz == 42);
    assert(m.satellites[0].tracked);
    assert(m.arrival_us == 987654);

    // Ultima trama del grupo, con un solo satelite.
    assert(send(p, m, sentence("GPGSV,3,3,11,30,08,331,21,1")));
    assert(m.count == 1 && m.message_number == 3 && m.satellites[0].prn == 30);

    // **C/N0 vacio no es cero**: el satelite esta a la vista y no se rastrea.
    // Confundirlos ensena "0 dB-Hz" donde lo cierto es "sin rastrear".
    assert(send(p, m, sentence("GPGSV,1,1,01,12,34,250,,1")));
    assert(m.count == 1 && m.satellites[0].prn == 12);
    assert(m.satellites[0].cno_dbhz == 0 && !m.satellites[0].tracked);
    assert(m.satellites[0].elevation_deg == 34 && m.satellites[0].azimuth_deg == 250);

    // Elevacion y azimut vacios: desconocidos, y **no cero**. Cero es el
    // horizonte y el norte, que son sitios de verdad.
    assert(send(p, m, sentence("GPGSV,1,1,01,12,,,33,1")));
    assert(m.satellites[0].elevation_deg == -1 && m.satellites[0].azimuth_deg == -1);
    assert(m.satellites[0].cno_dbhz == 33 && m.satellites[0].tracked);

    // Sin identificador de senal (NMEA anterior a 4.10): sigue valiendo.
    assert(send(p, m, sentence("GLGSV,1,1,02,65,20,045,30,66,40,130,35")));
    assert(!std::strcmp(m.talker, "GL"));
    assert(m.signal_id == 0 && m.count == 2 && m.satellites[1].prn == 66);

    // **El mismo PRN en dos senales son dos observaciones distintas.**
    // Guardarlas por PRN a secas ensena la C/N0 de la ultima que llegue.
    gnss::GsvMessage l1, l5;
    assert(send(p, l1, sentence("GPGSV,1,1,01,07,67,300,45,1")));
    assert(send(p, l5, sentence("GPGSV,1,1,01,07,67,300,31,6")));
    assert(l1.satellites[0].prn == l5.satellites[0].prn);
    assert(l1.signal_id != l5.signal_id);
    assert(l1.satellites[0].cno_dbhz != l5.satellites[0].cno_dbhz);

    // Grupos de relleno vacios: hay receptores que los mandan al final.
    assert(send(p, m, sentence("GPGSV,2,2,05,18,15,090,28,,,,,1")));
    assert(m.count == 1 && m.satellites[0].prn == 18);

    // Suma de verificacion mala: se rechaza entera, no a medias.
    gnss::GsvMessage previo = m;
    auto corrupta = sentence("GPGSV,1,1,04,02,45,123,42,1");
    corrupta[8] = '9';
    assert(!send(p, m, corrupta));
    assert(m.satellites[0].prn == previo.satellites[0].prn);

    // Rangos imposibles. Un azimut de 400 grados o una elevacion de 91 son
    // basura, y colarlos pinta un satelite en un sitio que no existe.
    assert(!send(p, m, sentence("GPGSV,1,1,01,02,91,123,42,1")));
    assert(!send(p, m, sentence("GPGSV,1,1,01,02,45,400,42,1")));
    assert(!send(p, m, sentence("GPGSV,1,1,01,02,45,123,120,1")));
    assert(!send(p, m, sentence("GPGSV,1,1,01,00,45,123,42,1")));      // PRN cero

    // Numeracion incoherente: la trama 4 de 3 no existe.
    assert(!send(p, m, sentence("GPGSV,3,4,11,02,45,123,42,1")));
    assert(!send(p, m, sentence("GPGSV,0,1,11,02,45,123,42,1")));

    // Campos que no son numeros. `strtol` se pararia en la basura y devolveria
    // lo que llevase leido; aqui la trama entera se rechaza.
    assert(!send(p, m, sentence("GPGSV,1,1,01,0x2,45,123,42,1")));
    assert(!send(p, m, sentence("GPGSV,1,1,01,02,4 5,123,42,1")));
    assert(!send(p, m, sentence("GPGSV,a,1,01,02,45,123,42,1")));

    // Grupo incompleto: un resto de dos o tres campos es una trama rota.
    assert(!send(p, m, sentence("GPGSV,1,1,01,02,45,123")));

    // Otra sentencia con el mismo emisor no es una GSV.
    assert(!send(p, m, sentence("GPGGA,120000.10,2800.000000,N,10600.000000,W,4,20,0.7,100.1,M,-20.2,M,,")));

    // Desbordamiento: una linea larguisima no desborda el buffer ni cuelga.
    gnss::GsvParser desbordado; gnss::GsvMessage descartada;
    std::string larga = "$GPGSV,1,1,01";
    larga.append(500, 'x');
    larga += "\r\n";
    assert(!send(desbordado, descartada, larga));
    assert(desbordado.overflow == 1);

    std::printf("nmea_gsv_test OK (%u aceptadas, %u rechazadas)\n", p.accepted, p.rejected);
    return 0;
}
