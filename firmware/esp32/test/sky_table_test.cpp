#include "sky_table.h"
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

gnss::GsvMessage gsv(const std::string& body) {
    gnss::GsvParser p; gnss::GsvMessage m;
    bool ok = false;
    for (char c : sentence(body)) ok |= p.feed(c, 0, m);
    assert(ok);
    return m;
}
gnss::Gsa gsa(const std::string& body) {
    gnss::GsaParser p; gnss::Gsa g;
    bool ok = false;
    for (char c : sentence(body)) ok |= p.feed(c, 0, g);
    assert(ok);
    return g;
}

const gnss::SkyTable::Satellite* find(const gnss::SkyTable::Satellite* v, unsigned n,
                                      const char* talker, uint8_t signal, uint8_t prn) {
    for (unsigned i = 0; i < n; ++i) {
        if (v[i].prn == prn && v[i].signal_id == signal && !std::strncmp(v[i].talker, talker, 2)) return &v[i];
    }
    return nullptr;
}

int main() {
    gnss::SkyTable::Satellite vista[gnss::SkyTable::kCapacity];

    // --- Lo basico: entra una GSV y sale el cielo.
    {
        gnss::SkyTable tabla;
        tabla.feed(gsv("GPGSV,1,1,02,02,45,123,42,05,12,045,38,1"), 1000);
        const unsigned n = tabla.view(vista, gnss::SkyTable::kCapacity, 1000);
        assert(n == 2);
        const auto* sv = find(vista, n, "GP", 1, 2);
        assert(sv && sv->elevation_deg == 45 && sv->azimuth_deg == 123 && sv->cno_dbhz == 42);
        assert(sv->tracked && !sv->used);
    }

    // --- **El mismo PRN en dos senales son dos entradas.**
    // Si se guardara por PRN, la C/N0 de L5 taparia la de L1 y la pantalla
    // ensenaria una senal que no es la que cree.
    {
        gnss::SkyTable tabla;
        tabla.feed(gsv("GPGSV,1,1,01,07,67,300,45,1"), 1000);
        tabla.feed(gsv("GPGSV,1,1,01,07,67,300,31,6"), 1000);
        const unsigned n = tabla.view(vista, gnss::SkyTable::kCapacity, 1000);
        assert(n == 2);
        assert(find(vista, n, "GP", 1, 7)->cno_dbhz == 45);
        assert(find(vista, n, "GP", 6, 7)->cno_dbhz == 31);
        // Pero es **un** satelite a la vista, no dos.
        assert(tabla.distinctInView(1000) == 1);
    }

    // --- El mismo PRN en dos constelaciones tampoco se mezcla.
    {
        gnss::SkyTable tabla;
        tabla.feed(gsv("GPGSV,1,1,01,12,40,100,44,1"), 1000);
        tabla.feed(gsv("GBGSV,1,1,01,12,20,200,30,1"), 1000);
        const unsigned n = tabla.view(vista, gnss::SkyTable::kCapacity, 1000);
        assert(n == 2);
        assert(find(vista, n, "GP", 1, 12)->cno_dbhz == 44);
        assert(find(vista, n, "GB", 1, 12)->cno_dbhz == 30);
        assert(tabla.distinctInView(1000) == 2);
    }

    // --- GSA marca los usados, y **todas las senales del mismo satelite**:
    // la solucion usa el satelite, no una frecuencia.
    {
        gnss::SkyTable tabla;
        tabla.feed(gsv("GPGSV,1,1,02,07,67,300,45,09,23,210,33,1"), 1000);
        tabla.feed(gsv("GPGSV,1,1,01,07,67,300,31,6"), 1000);
        tabla.feed(gsa("GNGSA,A,3,07,,,,,,,,,,,,2.50,1.30,2.10,1"), 1000);
        const unsigned n = tabla.view(vista, gnss::SkyTable::kCapacity, 1000);
        assert(find(vista, n, "GP", 1, 7)->used);
        assert(find(vista, n, "GP", 6, 7)->used);
        assert(!find(vista, n, "GP", 1, 9)->used);
        assert(tabla.fix_type == 3);
        assert(std::fabs(tabla.pdop - 2.5) < 1e-9 && std::fabs(tabla.vdop - 2.1) < 1e-9);
    }

    // --- **El identificador de sistema de GSA decide de quien es el PRN.**
    // Un GSA de GLONASS con el PRN 12 no enciende el 12 de GPS.
    {
        gnss::SkyTable tabla;
        tabla.feed(gsv("GPGSV,1,1,01,12,40,100,44,1"), 1000);
        tabla.feed(gsv("GLGSV,1,1,01,12,20,200,30,1"), 1000);
        tabla.feed(gsa("GNGSA,A,3,12,,,,,,,,,,,,2.50,1.30,2.10,2"), 1000);
        const unsigned n = tabla.view(vista, gnss::SkyTable::kCapacity, 1000);
        assert(!find(vista, n, "GP", 1, 12)->used);
        assert(find(vista, n, "GL", 1, 12)->used);
    }

    // --- **Sin identificador de sistema y con emisor GN, no se marca nada.**
    // Marcar el PRN en todas las constelaciones encenderia satelites que la
    // solucion no uso, y eso es peor que no decir nada.
    {
        gnss::SkyTable tabla;
        tabla.feed(gsv("GPGSV,1,1,01,12,40,100,44,1"), 1000);
        tabla.feed(gsv("GLGSV,1,1,01,12,20,200,30,1"), 1000);
        tabla.feed(gsa("GNGSA,A,3,12,,,,,,,,,,,,2.50,1.30,2.10"), 1000);
        const unsigned n = tabla.view(vista, gnss::SkyTable::kCapacity, 1000);
        assert(!find(vista, n, "GP", 1, 12)->used);
        assert(!find(vista, n, "GL", 1, 12)->used);
        // Los DOP sí valen: no dependen de saber de quién es cada PRN.
        assert(std::fabs(tabla.hdop - 1.3) < 1e-9);
    }

    // --- Sin identificador de sistema pero con emisor propio, sí se marca.
    {
        gnss::SkyTable tabla;
        tabla.feed(gsv("GPGSV,1,1,01,12,40,100,44,1"), 1000);
        tabla.feed(gsa("GPGSA,A,3,12,,,,,,,,,,,,2.50,1.30,2.10"), 1000);
        const unsigned n = tabla.view(vista, gnss::SkyTable::kCapacity, 1000);
        assert(find(vista, n, "GP", 1, 12)->used);
    }

    // --- Caducidad: un satelite que deja de aparecer se va. **No se
    // extrapola**: se deja de decir que esta.
    {
        gnss::SkyTable tabla;
        tabla.feed(gsv("GPGSV,1,1,02,02,45,123,42,05,12,045,38,1"), 1000);
        assert(tabla.view(vista, gnss::SkyTable::kCapacity, 1000 + 9000) == 2);
        // Solo el 02 se refresca; el 05 caduca.
        tabla.feed(gsv("GPGSV,1,1,01,02,46,124,41,1"), 1000 + 9000);
        const unsigned n = tabla.view(vista, gnss::SkyTable::kCapacity, 1000 + 11500);
        assert(n == 1);
        assert(vista[0].prn == 2 && vista[0].elevation_deg == 46);
    }

    // --- **Lo de "usado" caduca antes y por su cuenta.**
    // Si el receptor deja de mandar GSA, dejar la marca encendida diria que la
    // solucion sigue apoyandose en satelites de los que ya no se sabe nada.
    {
        gnss::SkyTable tabla;
        tabla.feed(gsv("GPGSV,1,1,01,07,67,300,45,1"), 1000);
        tabla.feed(gsa("GNGSA,A,3,07,,,,,,,,,,,,2.50,1.30,2.10,1"), 1000);
        tabla.feed(gsv("GPGSV,1,1,01,07,67,300,45,1"), 8000);
        const unsigned n = tabla.view(vista, gnss::SkyTable::kCapacity, 8000);
        assert(n == 1 && !vista[0].used);   // la GSV sigue llegando, la GSA no
    }

    // --- **Un satelite que sale de la solucion deja de estar marcado**, aunque
    // sigan llegando GSA. Visto en el equipo el 27-09-2026: BDS 12 salia como
    // usado en 139 de 146 ciclos sin figurar en ninguna GSA, y el cielo daba 29
    // usados contra 27 de GSA y de GGA. Tramas copiadas de esa captura.
    {
        gnss::SkyTable tabla;
        tabla.feed(gsv("GBGSV,1,1,02,11,24,143,21,12,15,171,18,1"), 1000);
        tabla.feed(gsa("GNGSA,M,3,04,07,,,,,,,,,,,1.1,0.6,0.9,1"), 1000);
        tabla.feed(gsa("GNGSA,M,3,11,12,,,,,,,,,,,1.1,0.6,0.9,4"), 1000);
        tabla.feed(gsv("GBGSV,1,1,02,11,24,143,21,12,15,171,18,1"), 2000);
        tabla.feed(gsa("GNGSA,M,3,04,07,,,,,,,,,,,1.1,0.6,0.9,1"), 2000);
        tabla.feed(gsa("GNGSA,M,3,11,,,,,,,,,,,,1.1,0.6,0.9,4"), 2000);
        const unsigned n = tabla.view(vista, gnss::SkyTable::kCapacity, 2000);
        assert(find(vista, n, "GB", 1, 11)->used);
        assert(!find(vista, n, "GB", 1, 12)->used);
    }

    // --- Lo mismo cuando una constelacion entera deja de usarse: su GSA ya no
    // llega en la epoca siguiente y sus satelites no pueden seguir marcados.
    {
        gnss::SkyTable tabla;
        tabla.feed(gsv("GPGSV,1,1,01,07,60,200,45,1"), 1000);
        tabla.feed(gsv("GLGSV,1,1,01,67,30,100,40,1"), 1000);
        tabla.feed(gsa("GNGSA,M,3,07,,,,,,,,,,,,1.1,0.6,0.9,1"), 1000);
        tabla.feed(gsa("GNGSA,M,3,67,,,,,,,,,,,,1.1,0.6,0.9,2"), 1000);
        tabla.feed(gsv("GPGSV,1,1,01,07,60,200,45,1"), 2000);
        tabla.feed(gsv("GLGSV,1,1,01,67,30,100,40,1"), 2000);
        tabla.feed(gsa("GNGSA,M,3,07,,,,,,,,,,,,1.1,0.6,0.9,1"), 2000);
        const unsigned n = tabla.view(vista, gnss::SkyTable::kCapacity, 2000);
        assert(find(vista, n, "GP", 1, 7)->used);
        assert(!find(vista, n, "GL", 1, 67)->used);
    }

    // --- Un sistema con mas de doce usados manda dos GSA seguidas en la misma
    // epoca: la segunda **no** borra lo que marco la primera.
    {
        gnss::SkyTable tabla;
        tabla.feed(gsv("GBGSV,4,1,14,01,40,010,40,02,40,020,40,03,40,030,40,04,40,040,40,1"), 1000);
        tabla.feed(gsv("GBGSV,4,2,14,05,40,050,40,06,40,060,40,07,40,070,40,08,40,080,40,1"), 1000);
        tabla.feed(gsv("GBGSV,4,3,14,09,40,090,40,10,40,100,40,11,40,110,40,12,40,120,40,1"), 1000);
        tabla.feed(gsv("GBGSV,4,4,14,13,40,130,40,14,40,140,40,1"), 1000);
        tabla.feed(gsa("GNGSA,M,3,01,02,03,04,05,06,07,08,09,10,11,12,1.1,0.6,0.9,4"), 1000);
        tabla.feed(gsa("GNGSA,M,3,13,14,,,,,,,,,,,1.1,0.6,0.9,4"), 1000);
        const unsigned n = tabla.view(vista, gnss::SkyTable::kCapacity, 1000);
        for (uint8_t prn = 1; prn <= 14; ++prn) assert(find(vista, n, "GB", 1, prn)->used);
    }

    // --- Un satelite a la vista sin rastrear se guarda como tal.
    {
        gnss::SkyTable tabla;
        tabla.feed(gsv("GPGSV,1,1,01,18,10,090,,1"), 1000);
        const unsigned n = tabla.view(vista, gnss::SkyTable::kCapacity, 1000);
        assert(n == 1 && !vista[0].tracked && vista[0].cno_dbhz == 0);
        assert(vista[0].elevation_deg == 10);
    }

    // --- La tabla se llena: se cuenta lo que no cupo, **no se tira callando**.
    // 32 PRN por 8 senales son 256 observaciones: pasan del tope.
    {
        gnss::SkyTable tabla;
        unsigned metidos = 0;
        for (unsigned senal = 1; senal <= 8; ++senal) {
            for (unsigned prn = 1; prn <= 32; ++prn) {
                char body[64];
                std::snprintf(body, sizeof(body), "GPGSV,1,1,20,%02u,45,123,42,%u", prn, senal);
                tabla.feed(gsv(body), 1000);
                ++metidos;
            }
        }
        const unsigned n = tabla.view(vista, gnss::SkyTable::kCapacity, 1000);
        assert(metidos > gnss::SkyTable::kCapacity);
        assert(n == gnss::SkyTable::kCapacity);
        assert(tabla.dropped == metidos - gnss::SkyTable::kCapacity);
        // Llena y con cada PRN repetido en seis senales, siguen siendo 32
        // satelites: la cuenta no se deja llevar por el numero de entradas.
        assert(tabla.distinctInView(1000) == 32);
    }

    // --- **Rastreado no es lo mismo que a la vista.** Un satelite que GSV
    // anuncia sin C/N0 esta sobre el horizonte, pero el receptor no lo oye.
    {
        gnss::SkyTable tabla;
        tabla.feed(gsv("GPGSV,1,1,03,02,45,123,42,05,12,045,,09,30,200,,1"), 1000);
        // El 09 no se oye en L1 pero si en L5: con una senal basta.
        tabla.feed(gsv("GPGSV,1,1,01,09,30,200,33,7"), 1000);
        assert(tabla.distinctInView(1000) == 3);
        assert(tabla.distinctTracked(1000) == 2);
        // Lo caducado no cuenta en ninguna de las dos.
        assert(tabla.distinctInView(1000 + 20000) == 0);
        assert(tabla.distinctTracked(1000 + 20000) == 0);
    }

    // --- El mismo PRN en cuatro constelaciones, con varias senales: cuatro
    // satelites, ni uno ni doce.
    {
        gnss::SkyTable tabla;
        for (const char* emisor : {"GP", "GL", "GA", "GB"}) {
            for (unsigned senal = 1; senal <= 3; ++senal) {
                char body[64];
                std::snprintf(body, sizeof(body), "%sGSV,1,1,01,07,40,100,40,%u", emisor, senal);
                tabla.feed(gsv(body), 1000);
            }
        }
        assert(tabla.distinctInView(1000) == 4);
        assert(tabla.distinctTracked(1000) == 4);
    }

    // --- Al llenarse, lo caducado se reutiliza: una constelacion que se anuncia
    // al final no se queda fuera para siempre.
    {
        gnss::SkyTable tabla;
        for (unsigned prn = 1; prn <= gnss::SkyTable::kCapacity; ++prn) {
            char body[64];
            std::snprintf(body, sizeof(body), "GPGSV,1,1,72,%02u,45,123,42,1", prn);
            tabla.feed(gsv(body), 1000);
        }
        assert(tabla.dropped == 0);
        // Mucho despues, una constelacion nueva: hay hueco porque todo caduco.
        tabla.feed(gsv("GBGSV,1,1,01,33,30,200,40,1"), 1000 + 20000);
        const unsigned n = tabla.view(vista, gnss::SkyTable::kCapacity, 1000 + 20000);
        assert(n == 1 && !std::strncmp(vista[0].talker, "GB", 2) && vista[0].prn == 33);
    }

    // --- El buffer de salida del que lee puede ser mas pequeno, y no se pasa.
    {
        gnss::SkyTable tabla;
        tabla.feed(gsv("GPGSV,1,1,04,02,45,123,42,05,12,045,38,07,67,300,45,09,23,210,33,1"), 1000);
        gnss::SkyTable::Satellite pequeno[2];
        assert(tabla.view(pequeno, 2, 1000) == 2);
    }

    std::printf("sky_table_test OK\n");
    return 0;
}
