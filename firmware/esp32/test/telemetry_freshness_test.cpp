#include "telemetry_freshness.h"
#include <cassert>
#include <cstdio>

int main() {
    using protocol::telemetryFresh;
    // Llegó 400 ms antes de encolar; tras 101 ms de cola ya no es vigente.
    assert(telemetryFresh(1499999, 1400000, 1000000, true));
    assert(telemetryFresh(1500000, 1400000, 1000000, true));
    assert(!telemetryFresh(1500001, 1400000, 1000000, true));
    // La salud de esa tanda sí sale: su edad no depende de la GGA vieja.
    assert(telemetryFresh(1500001, 1400000, 1000000, false));
    assert(!telemetryFresh(1900001, 1400000, 1000000, false));
    assert(!telemetryFresh(1000000, 1000001, 900000, true));
    assert(!telemetryFresh(1000000, 1000000, 1000001, true));
    assert(telemetryFresh(1000000, 1000000, 1000000, true));
    puts("telemetry_freshness: OK");
}
