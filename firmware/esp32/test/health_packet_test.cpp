#include "health_packet.h"
#include <cassert>
#include <cstdio>

// Precision mostrada por Meridian V: la regla del propietario (27-09-2026) y los
// casos que el pidio como minimo. La entrada es la precision del UM980 en mm.
static void expect(uint16_t input, uint16_t h, uint16_t v) {
    const auto d = protocol::meridianDisplayPrecision(input);
    if (d.horizontal != h || d.vertical != v) {
        std::printf("FALLA input %u -> H %u / V %u (esperado H %u / V %u)\n", input, d.horizontal, d.vertical, h, v);
        assert(false);
    }
}

static uint16_t get16(const uint8_t* p) { return uint16_t(p[0] | (p[1] << 8)); }

int main() {
    expect(0, 10, 15);
    expect(10, 10, 15);
    expect(30, 10, 15);
    expect(35, 10, 15);
    expect(36, 11, 16);
    expect(39, 14, 19);
    expect(50, 25, 30);
    expect(80, 55, 60);
    expect(100, 75, 80);
    // Sin estimacion del receptor no se inventa una precision.
    expect(protocol::kUnknownMm, protocol::kUnknownMm, protocol::kUnknownMm);
    // El maximo de 16 bits sigue la regla sin tocar el «desconocido» (0xFFFF).
    expect(65534, 65509, 65514);

    // Metros de GST a mm: la misma regla de siempre.
    assert(protocol::sigmaToMm(0.028) == 28);
    assert(protocol::sigmaToMm(0.0355) == 36);
    assert(protocol::sigmaToMm(-1) == protocol::kUnknownMm);
    assert(protocol::sigmaToMm(70.0) == protocol::kUnknownMm);

    // Peor eje horizontal: el mayor de norte y este; sin ejes, la combinada.
    assert(protocol::um980WorstAxisHorizontalSigmaM(0.011, 0.010, 0.015) == 0.011);
    assert(protocol::um980WorstAxisHorizontalSigmaM(NAN, 0.010, 0.015) == 0.015);

    // **Gobierna la horizontal cruda.** Un fix real de hoy: H 12 mm y V 39 mm.
    // La vertical cruda pasa de 35, pero no cuenta: se muestra 10 / 15.
    {
        const auto d = protocol::meridianDisplayFromRaw(12);
        assert(d.horizontal == 10 && d.vertical == 15);
    }
    // Con la horizontal cruda en 39 mm, el ejemplo del propietario: 14 / 19.
    {
        const auto d = protocol::meridianDisplayFromRaw(39);
        assert(d.horizontal == 14 && d.vertical == 19);
    }

    // **La cruda del UM980 sale intacta**, en sus bytes, al lado de la mostrada.
    protocol::HealthInputs in;
    in.um980RawHorizontalSigmaMm = 12;
    in.um980RawVerticalSigmaMm = 39;
    in.meridianDisplay = protocol::meridianDisplayFromRaw(in.um980RawHorizontalSigmaMm);
    in.correctionAgeSeconds = 1;
    in.source = 2;
    in.quality = 4;
    in.tracked = 31;
    in.visible = 39;
    uint8_t report[20];
    protocol::encodeHealth(report, in);
    assert(report[0] == 1);
    assert(get16(report + 1) == 10 && get16(report + 3) == 15);   // mostrada (gobierna H = 12)
    assert(get16(report + 12) == 12 && get16(report + 14) == 39); // cruda, sin tocar
    assert(get16(report + 5) == 1 && report[7] == 2 && report[8] == 4 && report[10] == 31);
    assert(report[9] == 0);
    assert(report[11] == 39);  // visibles
    // Sin visibles conocidos, 255 (no 0, que diria «ninguno»).
    {
        protocol::HealthInputs unknown;
        uint8_t r[20];
        protocol::encodeHealth(r, unknown);
        assert(r[11] == 255 && get16(r + 1) == protocol::kUnknownMm && get16(r + 12) == protocol::kUnknownMm);
    }
    assert(report[16] == (protocol::kFlagDisplayPrecision | protocol::kFlagRawPrecision));
    for (unsigned i = 17; i < 20; ++i) assert(report[i] == 0);

    // Desde 0.7.11: contadores de RTCM en 17-19, con su bandera. Sin la bandera,
    // los bytes siguen en 0 (lo de arriba).
    {
        protocol::HealthInputs c;
        c.hasRtcmCounters = true;
        c.rtcmFramesDiscarded = uint8_t(300);  // da la vuelta: 300 mod 256 = 44
        c.rtcmFramesRejected = 3;
        c.rtcmQueuePercent = protocol::queuePercent(4100, 8192);
        uint8_t r[20];
        protocol::encodeHealth(r, c);
        assert(r[16] == (protocol::kFlagDisplayPrecision | protocol::kFlagRawPrecision | protocol::kFlagRtcmCounters));
        assert(r[17] == 44 && r[18] == 3 && r[19] == 51);
    }
    assert(protocol::queuePercent(0, 8192) == 0);
    assert(protocol::queuePercent(1, 8192) == 1);        // algo dentro nunca es 0
    assert(protocol::queuePercent(8192, 8192) == 100);
    assert(protocol::queuePercent(10, 0) == protocol::kUnknownPercent);

    std::printf("health_packet_test OK\n");
    return 0;
}
