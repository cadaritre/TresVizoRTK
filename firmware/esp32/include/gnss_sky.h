#pragma once
#include <ArduinoJson.h>
#include "nmea_gsa.h"
#include "nmea_gsv.h"

// El cielo que ve el receptor, satelite a satelite.
//
// Vive aparte de `gnss_receiver` a proposito: su `snapshot()` se llama en media
// docena de sitios, a veces solo para leer un booleano, y copia la estructura
// entera dentro de una seccion critica. Meterle la tabla del cielo —cerca de un
// kilobyte— haria caro cada uno de esos usos sin que ninguno la necesite.
namespace gnss_sky {

struct Summary {
    // Satelites distintos a la vista, contando una vez cada uno aunque llegue
    // por varias senales. Es la cifra que se compara con la de GGA.
    unsigned in_view = 0;
    unsigned used = 0;
    // Observaciones que no cupieron en la tabla. Deberia ser cero.
    uint32_t dropped = 0;
    uint8_t fix_type = 0;
    double pdop = NAN, hdop = NAN, vdop = NAN;
    // Hace cuanto llego la ultima GSV y la ultima GSA. Sin esto no se distingue
    // "el cielo esta asi" de "el cielo estaba asi hace medio minuto".
    uint32_t sky_age_ms = 0, dop_age_ms = 0;
    bool has_sky = false, has_dop = false;
};

void feed(const gnss::GsvMessage& message, uint32_t now_ms);
void feed(const gnss::Gsa& message, uint32_t now_ms);

// Publica el cielo en el objeto dado. Agrupa por satelite —no por observacion—
// porque el mismo satelite llega una vez por senal y una grafica de barras que
// no agrupe pinta el mismo PRN dos veces.
void publish(JsonObject out);
}
