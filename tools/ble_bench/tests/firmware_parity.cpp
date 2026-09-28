// Volcado de lo que codifica el firmware, para compararlo con Python
// (tests/test_firmware_parity.py). Usa las cabeceras del firmware tal cual: si
// alguien cambia un offset o una regla alla, esta prueba lo delata aqui.
//
// Lee de la entrada estandar un flujo de bytes y lo pasa por gnss::Rtcm3Parser.
#include "ble_frames.h"
#include "health_packet.h"
#include "rtcm3.h"
#include <cstdio>
#include <string>
#include <vector>

// Contadores de RTCM de la salud (contrato v3, 0.7.11). Con las cabeceras de
// antes no existen: se detectan con SFINAE para que el volcado compile con las dos.
template <class T>
auto setRtcmCounters(T& in, uint8_t discarded, uint8_t rejected, uint8_t percent, int)
    -> decltype(in.hasRtcmCounters, bool()) {
    in.hasRtcmCounters = true;
    in.rtcmFramesDiscarded = discarded;
    in.rtcmFramesRejected = rejected;
    in.rtcmQueuePercent = percent;
    return true;
}
template <class T>
bool setRtcmCounters(T&, uint8_t, uint8_t, uint8_t, long) { return false; }

static void hex(const uint8_t* data, size_t length) {
    for (size_t i = 0; i < length; ++i) std::printf("%02x", data[i]);
}

int main() {
    // Tramas de respuesta: tamanos y MTU de ble_frames_test.cpp.
    for (size_t size : {size_t(1), size_t(16), size_t(240), size_t(700)}) {
        std::string json(size, 'x');
        for (size_t i = 0; i < size; ++i) json[i] = char('a' + i % 26);
        for (uint16_t mtu : {uint16_t(0), uint16_t(23), uint16_t(185), uint16_t(247), uint16_t(517)}) {
            std::printf("frames %zu %u ", size, mtu);
            size_t offset = 0;
            uint8_t frame[protocol::kMaxNotificationBytes];
            do {
                const size_t length = protocol::encodeResponseFrame(frame, 0x1234, offset, json.data(), json.size(),
                                                                    protocol::responsePayloadBytes(mtu));
                hex(frame, length); std::printf(",");
                offset += length - protocol::kResponseHeaderBytes;
                if (frame[4] & 2) break;
            } while (true);
            std::printf("\n");
        }
    }
    // Precision mostrada para todo el rango util y los extremos.
    for (uint32_t raw = 0; raw <= 300; ++raw) {
        const auto d = protocol::meridianDisplayPrecision(uint16_t(raw));
        std::printf("display %u %u %u\n", raw, d.horizontal, d.vertical);
    }
    for (uint32_t raw : {65533u, 65534u, 65535u}) {
        const auto d = protocol::meridianDisplayPrecision(uint16_t(raw));
        std::printf("display %u %u %u\n", raw, d.horizontal, d.vertical);
    }
    // Sigma en metros a mm.
    for (double m : {0.0, 0.0004, 0.0005, 0.028, 0.0355, 1.2345, 64.9999, 65.0, 65.001, -0.001}) {
        std::printf("sigma %.6f %u\n", m, protocol::sigmaToMm(m));
    }
    // Paquetes de salud.
    struct Case { uint16_t h, v, age; uint8_t source, quality, tracked, visible; };
    for (const Case c : {Case{12, 39, 1, 2, 4, 31, 39}, Case{0xFFFF, 0xFFFF, 0xFFFF, 0, 0, 255, 255},
                         Case{80, 120, 65534, 1, 5, 0, 12}, Case{36, 0, 0, 3, 1, 254, 254}}) {
        protocol::HealthInputs in;
        in.um980RawHorizontalSigmaMm = c.h; in.um980RawVerticalSigmaMm = c.v;
        in.meridianDisplay = protocol::meridianDisplayFromRaw(c.h);
        in.correctionAgeSeconds = c.age; in.source = c.source; in.quality = c.quality;
        in.tracked = c.tracked; in.visible = c.visible;
        uint8_t report[20];
        protocol::encodeHealth(report, in);
        std::printf("health %u %u %u %u %u %u %u ", c.h, c.v, c.age, c.source, c.quality, c.tracked, c.visible);
        hex(report, sizeof(report)); std::printf("\n");
    }
    // Salud con contadores de RTCM, si las cabeceras los tienen.
    for (const uint8_t* c : {(const uint8_t*)"\x2c\x03\x33", (const uint8_t*)"\x00\x00\xff", (const uint8_t*)"\xff\xfe\x64"}) {
        protocol::HealthInputs in;
        const bool supported = setRtcmCounters(in, c[0], c[1], c[2], 0);
        uint8_t report[20];
        protocol::encodeHealth(report, in);
        std::printf("health_rtcm %d %u %u %u ", supported ? 1 : 0, c[0], c[1], c[2]);
        hex(report, sizeof(report)); std::printf("\n");
    }
    // RTCM3: el flujo de la entrada estandar, byte a byte.
    std::vector<uint8_t> stream;
    int value;
    while ((value = std::getchar()) != EOF) stream.push_back(uint8_t(value));
    gnss::Rtcm3Parser parser;
    std::vector<size_t> lengths;
    for (uint8_t byte : stream) parser.feed(byte, [&](const uint8_t*, size_t length) { lengths.push_back(length); });
    std::printf("rtcm %u %u %u", parser.accepted, parser.rejected, parser.overflow);
    for (size_t length : lengths) std::printf(" %zu", length);
    std::printf("\n");
    return 0;
}
