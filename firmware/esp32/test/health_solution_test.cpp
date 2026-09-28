// Caducidad de la calidad y la precisión en el paquete de salud
// (include/health_solution.h, lib/protocol/src/health_timing.h), con la
// instantánea de verdad del receptor. La salud sale a 1 Hz siempre: si la GGA o
// la GST dejan de llegar, lo que lleva tiene que decirlo.
#include "health_solution.h"
#include <cassert>
#include <cstdio>
#include <random>

static uint16_t get16(const uint8_t* p) { return uint16_t(p[0] | (p[1] << 8)); }

struct Decoded {
    unsigned quality;
    uint16_t displayH, displayV, rawH, rawV;
};

static Decoded build(const gnss_receiver::Snapshot& s, uint64_t nowUs) {
    protocol::HealthInputs in;
    health_report::fillFromReceiver(in, s, nowUs);
    uint8_t r[20];
    protocol::encodeHealth(r, in);
    return {r[8], get16(r + 1), get16(r + 3), get16(r + 12), get16(r + 14)};
}

static bool solutionStale(const Decoded& d) { return d.quality == 0; }
static bool precisionUnknown(const Decoded& d) {
    return d.displayH == protocol::kUnknownMm && d.displayV == protocol::kUnknownMm
        && d.rawH == protocol::kUnknownMm && d.rawV == protocol::kUnknownMm;
}

static constexpr uint64_t kSecondUs = 1000000;

// GGA RTK fijo y GST de 8/6 mm (H) y 15 mm (V), llegadas en `ggaUs` y `gstUs`.
static gnss_receiver::Snapshot fixed(uint64_t ggaUs, uint64_t gstUs) {
    gnss_receiver::Snapshot s;
    s.enabled = true;
    s.accepted = 1;
    s.solution.quality = 4;
    s.solution.has_utc = true; s.solution.utc_ms = 43200000; s.solution.arrival_us = ggaUs;
    s.solution.has_position = true; s.solution.latitude_deg = 40; s.solution.longitude_deg = -3;
    s.solution.altitude_msl_m = 650;
    s.precision_accepted = 1;
    s.precision.arrival_us = gstUs;
    s.precision.latitude_sigma_m = 0.008; s.precision.longitude_sigma_m = 0.006;
    s.precision.altitude_sigma_m = 0.015; s.precision.horizontal_sigma_m = 0.010; s.precision.has_sigma = true;
    return s;
}

int main() {
    // 1) GGA y GST en t = 1 ms y después nada. Vigentes hasta 2 s inclusive;
    //    a los 3 s y a los 60 s, calidad 0 y precisión desconocida.
    {
        const auto s = fixed(1000, 1000);
        for (uint64_t nowUs : {uint64_t(300000), uint64_t(1500000), uint64_t(1000 + 2 * kSecondUs)}) {
            const Decoded d = build(s, nowUs);
            assert(d.quality == 4);
            assert(d.rawH == 8 && d.rawV == 15);        // peor eje (N) y vertical, crudas
            assert(d.displayH == 10 && d.displayV == 15);  // regla del propietario: bajo 35 mm, 10/15
        }
        for (uint64_t nowUs : {uint64_t(1001 + 2 * kSecondUs), 3 * kSecondUs, 60 * kSecondUs}) {
            const Decoded d = build(s, nowUs);
            assert(solutionStale(d) && precisionUnknown(d));
        }
    }

    // 2) GGA fresca y GST de hace 3 s (p. ej. GST rechazada, que deja la
    //    anterior en su sitio): la calidad sigue, la precisión no.
    {
        const uint64_t nowUs = 10 * kSecondUs;
        const Decoded d = build(fixed(nowUs - 100000, nowUs - 3 * kSecondUs), nowUs);
        assert(d.quality == 4 && precisionUnknown(d));
    }

    // 3) GST fresca pero GGA vencida: la sigma describe una solución que ya no
    //    está, así que tampoco hay precisión (como en /api/status).
    {
        const uint64_t nowUs = 10 * kSecondUs;
        const Decoded d = build(fixed(nowUs - 5 * kSecondUs, nowUs - 100000), nowUs);
        assert(solutionStale(d) && precisionUnknown(d));
    }

    // 4) Recién encendido: nunca llegó nada, llegada 0 y reloj en 0.5 s. Sin el
    //    contador de aceptadas parecería fresca.
    {
        gnss_receiver::Snapshot s;
        s.solution.quality = 4;  // lo que hubiera en la estructura no cuenta
        const Decoded d = build(s, 500000);
        assert(solutionStale(d) && precisionUnknown(d));
        // GGA sí, GST nunca: calidad, sin precisión.
        auto t = fixed(400000, 0);
        t.precision_accepted = 0;
        const Decoded e = build(t, 500000);
        assert(e.quality == 4 && precisionUnknown(e));
    }

    // 5) Reloj leído antes que la instantánea: la llegada queda «en el futuro».
    //    Es de hace nada y vale; la resta no da la vuelta.
    {
        const Decoded d = build(fixed(5 * kSecondUs + 10, 5 * kSecondUs + 10), 5 * kSecondUs);
        assert(d.quality == 4 && d.rawH == 8);
    }

    // 6) Equipo sano con GGA a 1 Hz y GST a 1 Hz, las dos con fluctuación de
    //    llegada, y la salud en fases al azar (semilla fija): nunca vencida.
    //    Con los 500 ms de la solución, en cambio, casi la mitad lo estaría.
    {
        std::mt19937 rng(20260928);
        std::uniform_int_distribution<int> jitterUs(-50000, 50000);
        std::uniform_int_distribution<int> phaseUs(0, 999999);
        unsigned stale = 0, staleAt500ms = 0;
        const unsigned kPackets = 2000;
        for (unsigned i = 0; i < kPackets; ++i) {
            const uint64_t second = 100 + i;
            const uint64_t ggaUs = second * kSecondUs + 200000 + jitterUs(rng);
            const uint64_t gstUs = second * kSecondUs + 230000 + jitterUs(rng);
            // La salud cae en cualquier punto hasta la GGA siguiente, que puede
            // llegar hasta 50 ms tarde.
            const uint64_t nowUs = ggaUs + uint64_t(phaseUs(rng)) + 50000;
            const Decoded d = build(fixed(ggaUs, gstUs), nowUs);
            if (solutionStale(d) || precisionUnknown(d)) ++stale;
            if (!protocol::arrivedWithin(1, ggaUs, nowUs, 500000)) ++staleAt500ms;
        }
        std::printf("Sano a 1 Hz: %u/%u paquetes vencidos con 2 s; con 500 ms serían %u/%u\n", stale, kPackets,
                    staleAt500ms, kPackets);
        assert(stale == 0 && staleAt500ms > kPackets / 4);
    }

    // 7) GGA a 5 Hz y GST a 1 Hz: también siempre vigente.
    {
        for (uint64_t phaseMs = 0; phaseMs < 1000; phaseMs += 7) {
            const uint64_t gstUs = 50 * kSecondUs;
            const uint64_t nowUs = gstUs + phaseMs * 1000;
            const uint64_t ggaUs = nowUs - (phaseMs % 200) * 1000;  // la última GGA, de hace menos de 200 ms
            const Decoded d = build(fixed(ggaUs, gstUs), nowUs);
            assert(d.quality == 4 && !precisionUnknown(d));
        }
    }

    // 8) Una GGA vigente con calidad 0 sigue diciendo 0, y una sigma fuera de
    //    rango sigue siendo desconocida aunque la GST sea fresca.
    {
        auto s = fixed(1000, 1000);
        s.solution.quality = 0;
        assert(build(s, 2000).quality == 0);
        s = fixed(1000, 1000);
        s.precision.latitude_sigma_m = 70.0;  // más de 65 m: no cabe en mm
        const Decoded d = build(s, 2000);
        assert(d.quality == 4 && d.rawH == protocol::kUnknownMm && d.displayH == protocol::kUnknownMm && d.rawV == 15);
    }
    std::printf("OK\n");
}
