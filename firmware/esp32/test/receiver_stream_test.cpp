// El reparto de la UART del UM980 (lib/gnss/src/receiver_stream.h): el RTCM que
// produce la base sale entero aunque lleve 0xAA, y el texto NMEA que ven los
// parsers es el mismo byte a byte que con el filtro solo.
#include "receiver_stream.h"
#include "nmea_gga.h"
#include <cassert>
#include <cstdio>
#include <random>
#include <string>
#include <vector>

using Bytes = std::vector<uint8_t>;
// La trama RTCM3 más larga: 3 de cabecera, 1023 de carga y 3 de CRC.
constexpr size_t kMaxRtcmFrameBytes = 1029;

static Bytes rtcmFrame(const Bytes& payload) {
    Bytes f{0xd3, uint8_t((payload.size() >> 8) & 3), uint8_t(payload.size() & 0xff)};
    f.insert(f.end(), payload.begin(), payload.end());
    const uint32_t c = gnss::crc24q(f.data(), f.size());
    f.push_back(uint8_t(c >> 16)); f.push_back(uint8_t(c >> 8)); f.push_back(uint8_t(c));
    return f;
}

static uint32_t crc32Unicore(const Bytes& v) {
    uint32_t c = 0;
    for (uint8_t b : v) { c ^= b; for (int i = 0; i < 8; ++i) c = (c >> 1) ^ ((c & 1) ? 0xedb88320U : 0); }
    return c;
}

// Trama binaria Unicore válida (la misma construcción que test/wire_filter_test.cpp).
static Bytes unicoreFrame(const Bytes& payload) {
    Bytes f(24, 0);
    f[0] = 0xaa; f[1] = 0x44; f[2] = 0xb5;
    f[6] = uint8_t(payload.size()); f[7] = uint8_t(payload.size() >> 8);
    f.insert(f.end(), payload.begin(), payload.end());
    const uint32_t c = crc32Unicore(f);
    for (int i = 0; i < 4; ++i) f.push_back(uint8_t(c >> (8 * i)));
    return f;
}

static std::string nmea(const std::string& body) {
    uint8_t check = 0;
    for (char c : body) check ^= uint8_t(c);
    char tail[8];
    std::snprintf(tail, sizeof tail, "*%02X\r\n", check);
    return "$" + body + tail;
}

struct Output {
    std::vector<Bytes> frames;
    std::vector<size_t> deliveredAt;  // índice del byte con el que salió cada trama
    std::string text;
    uint32_t nativeValid = 0, nativeInvalid = 0, ggaAccepted = 0;
};

// Como gnss_receiver.cpp: todo el flujo por ReceiverStream, el texto a un GgaParser.
static Output run(const Bytes& stream) {
    gnss::ReceiverStream receiver;
    gnss::GgaParser gga;
    gnss::Gga solution;
    Output out;
    const uint32_t nowMs = 1;
    for (size_t i = 0; i < stream.size(); ++i) {
        receiver.feed(stream[i], nowMs,
                      [&](const uint8_t* p, size_t n) { out.frames.emplace_back(p, p + n); out.deliveredAt.push_back(i); },
                      [&](char c) { out.text += c; gga.feed(c, 0, solution); });
    }
    out.nativeValid = receiver.filter.native_valid;
    out.nativeInvalid = receiver.filter.native_invalid;
    out.ggaAccepted = gga.accepted;
    return out;
}

// El texto que deja pasar el filtro solo, sin nada más: la referencia.
static std::string filterOnly(const Bytes& stream) {
    gnss::WireFilter filter;
    std::string text;
    for (uint8_t b : stream) filter.feed(b, 1, [&](char c) { text += c; });
    return text;
}

int main() {
    // 1) El caso de la auditoría: carga 3e d0 aa 00, 10 bytes con CRC24Q válido.
    //    Hasta 0.7.12 el filtro se quedaba el 0xAA y la trama no salía nunca.
    {
        const Bytes frame = rtcmFrame({0x3e, 0xd0, 0xaa, 0x00});
        assert(frame.size() == 10 && frame[0] == 0xd3 && frame[1] == 0x00 && frame[2] == 0x04);
        const Output out = run(frame);
        assert(out.frames.size() == 1 && out.frames[0] == frame);
    }

    // 2) Flujo mezclado como el de COM2 con la base y el perfil PPK a la vez:
    //    GGA, binario Unicore con 0xD3 y cabeceras RTCM falsas dentro, y tramas
    //    RTCM con 0xAA (de 6 a 1023 bytes de carga, aleatoria con semilla fija).
    {
        Bytes uni(200, 0x11);
        uni[10] = 0xd3; uni[11] = 0x00; uni[12] = 0x40;     // falsa cabecera RTCM de 70 bytes
        uni[150] = 0xd3; uni[151] = 0x03; uni[152] = 0xff;  // falsa cabecera de 1029 bytes
        uni[160] = 0xaa;                                    // un 0xAA suelto dentro del binario
        const Bytes unicore = unicoreFrame(uni);

        std::mt19937 rng(20260928);
        std::uniform_int_distribution<int> byte(0, 255);
        const size_t sizes[] = {6, 19, 40, 150, 300, 600, 1023};
        const unsigned kCycles = 60;

        Bytes stream;
        std::vector<Bytes> sent;
        std::vector<size_t> startsAt;
        unsigned ggaSent = 0, unicoreSent = 0, rtcmWithAa = 0;
        for (unsigned cycle = 0; cycle < kCycles; ++cycle) {
            char body[96];
            std::snprintf(body, sizeof body, "GNGGA,1200%02u.00,4000.0000000,N,00300.0000000,W,4,20,0.6,650.000,M,50.000,M,1.0,0000",
                          cycle % 60);
            const std::string gga = nmea(body);
            stream.insert(stream.end(), gga.begin(), gga.end());
            ++ggaSent;
            if (cycle % 3 == 0) { stream.insert(stream.end(), unicore.begin(), unicore.end()); ++unicoreSent; }

            Bytes payload(sizes[cycle % (sizeof sizes / sizeof sizes[0])]);
            for (auto& b : payload) b = uint8_t(byte(rng));
            payload[0] = 0x3e;
            // Siempre al menos un 0xAA en la carga: es el caso que se perdía.
            payload[payload.size() / 2] = 0xaa;
            const Bytes frame = rtcmFrame(payload);
            for (uint8_t b : frame) if (b == 0xaa) { ++rtcmWithAa; break; }
            sent.push_back(frame);
            startsAt.push_back(stream.size());
            stream.insert(stream.end(), frame.begin(), frame.end());
        }
        // Texto de cola, más largo que la trama RTCM más larga: una cabecera
        // falsa del binario hace esperar al parser hasta completar su longitud,
        // así que lo último **se retrasa** hasta 1029 bytes; aquí se comprueba
        // que se retrasa y no que se pierde.
        const std::string last = nmea("GNGGA,120100.00,4000.0000000,N,00300.0000000,W,4,20,0.6,650.000,M,50.000,M,1.0,0000");
        for (size_t tail = 0; tail <= kMaxRtcmFrameBytes; tail += last.size(), ++ggaSent)
            stream.insert(stream.end(), last.begin(), last.end());

        const Output out = run(stream);
        // Todas las tramas RTCM, idénticas y en orden.
        assert(rtcmWithAa == kCycles);
        assert(out.frames.size() == sent.size());
        size_t worstDelayBytes = 0;
        for (size_t i = 0; i < sent.size(); ++i) {
            assert(out.frames[i] == sent[i]);
            // Cota del retraso: sale antes de que lleguen 1029 bytes desde su
            // inicio (≈ 90 ms a 115200 baudios), por muchas cabeceras falsas que
            // hubiera delante.
            assert(out.deliveredAt[i] < startsAt[i] + kMaxRtcmFrameBytes);
            const size_t end = startsAt[i] + sent[i].size() - 1;
            if (out.deliveredAt[i] - end > worstDelayBytes) worstDelayBytes = out.deliveredAt[i] - end;
        }
        // El binario Unicore se sigue reconociendo y apartando.
        assert(out.nativeValid == unicoreSent && out.nativeInvalid == 0);
        // El texto es el mismo que con el filtro solo, y las GGA llegan todas.
        assert(out.text == filterOnly(stream));
        assert(out.ggaAccepted == ggaSent);
        std::printf("Flujo mezclado: %zu/%zu RTCM (todas con 0xAA), %u/%u Unicore, %u/%u GGA, retraso máx. %zu bytes\n",
                    out.frames.size(), sent.size(), out.nativeValid, unicoreSent, out.ggaAccepted, ggaSent, worstDelayBytes);
    }

    // 3) Una trama RTCM cortada a mitad (arranque o byte perdido) no se lleva la
    //    siguiente: el parser se resincroniza en el siguiente 0xD3.
    {
        const Bytes good = rtcmFrame({0x3e, 0xd0, 0xaa, 0x01, 0xaa});
        Bytes stream(good.begin(), good.begin() + 5);
        stream.insert(stream.end(), good.begin(), good.end());
        stream.insert(stream.end(), good.begin(), good.end());
        const Output out = run(stream);
        assert(out.frames.size() == 2 && out.frames[0] == good && out.frames[1] == good);
    }
    std::printf("OK\n");
}
