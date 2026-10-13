// Entramado del enlace USB del radio (lib/protocol/src/radio_usb.h, docs/radio/USB_LINK.md).
#include "radio_usb.h"
#include <cassert>
#include <cstdio>
#include <random>
#include <string>
#include <vector>

namespace {
using Bytes = std::vector<uint8_t>;

// Lo que entrega el demultiplexor, en orden y en texto para comparar fácil.
struct Recorder {
    std::vector<std::string> events;
    void onFrame(uint8_t type, const uint8_t* payload, size_t length) {
        events.push_back("F" + std::to_string(type) + ":" + std::string(reinterpret_cast<const char*>(payload), length));
    }
    void onRtcm(const uint8_t* frame, size_t length) {
        events.push_back("R:" + std::string(reinterpret_cast<const char*>(frame), length));
    }
    void onLine(const char* text, size_t length) { events.push_back("L:" + std::string(text, length)); }
    void onLineOverflow() { events.push_back("OVERFLOW"); }
    void onLineTimeout() { events.push_back("TIMEOUT"); }
};

Bytes frame(radio_usb::Type type, const std::string& payload) {
    Bytes out(radio_usb::kMaxFrameBytes);
    const size_t n = radio_usb::encode(type, reinterpret_cast<const uint8_t*>(payload.data()), payload.size(),
                                       out.data(), out.size());
    assert(n == radio_usb::kHeaderBytes + payload.size() + radio_usb::kCrcBytes);
    out.resize(n);
    return out;
}

Bytes rtcm(const Bytes& body) {
    Bytes out = {0xD3, uint8_t(body.size() >> 8), uint8_t(body.size() & 0xff)};
    out.insert(out.end(), body.begin(), body.end());
    const uint32_t crc = gnss::crc24q(out.data(), out.size());
    out.push_back(uint8_t(crc >> 16)); out.push_back(uint8_t(crc >> 8)); out.push_back(uint8_t(crc));
    return out;
}

Bytes text(const std::string& s) { return Bytes(s.begin(), s.end()); }
void append(Bytes& to, const Bytes& more) { to.insert(to.end(), more.begin(), more.end()); }
std::string asString(const Bytes& b) { return std::string(b.begin(), b.end()); }

// Todo de una vez, byte a byte y a trozos al azar: el resultado no cambia.
std::vector<std::string> run(const Bytes& stream, uint32_t seed = 0) {
    radio_usb::Demux demux;
    Recorder rec;
    if (!seed) { demux.feed(stream.data(), stream.size(), 0, rec); return rec.events; }
    std::mt19937 rng(seed);
    for (size_t i = 0; i < stream.size();) {
        const size_t n = std::min<size_t>(stream.size() - i, 1 + rng() % 70);
        demux.feed(stream.data() + i, n, 0, rec);
        i += n;
    }
    return rec.events;
}

void same(const Bytes& stream, const std::vector<std::string>& expected) {
    assert(run(stream) == expected);
    for (uint32_t seed = 1; seed < 20; ++seed) assert(run(stream, seed) == expected);
    radio_usb::Demux demux;   // byte a byte
    Recorder rec;
    for (uint8_t b : stream) demux.feed(&b, 1, 0, rec);
    assert(rec.events == expected);
}

std::string F(radio_usb::Type type, const std::string& payload) { return "F" + std::to_string(int(type)) + ":" + payload; }
std::string R(const Bytes& frame) { return "R:" + asString(frame); }
}  // namespace

int main() {
    using radio_usb::Type;
    const std::string hello = R"({"protocol":1,"radio_version":"0.2.0","network":1,"channel":6})";
    const Bytes rtcmA = rtcm({0x3E, 0xD0, 0x00, 0x03, 0x8A, 0xD3, 0x00, 0x10});   // 1005 con un D3 00 dentro
    const Bytes rtcmEmpty = rtcm({});
    Bytes big(1023);
    for (size_t i = 0; i < big.size(); ++i) big[i] = uint8_t(i * 7 + 3);
    const Bytes rtcmBig = rtcm(big);
    assert(rtcmBig.size() == radio_usb::kMaxRtcmBytes);

    // --- Cada cosa sola ----------------------------------------------------------
    same(frame(Type::hello, hello), {F(Type::hello, hello)});
    same(frame(Type::role, ""), {F(Type::role, "")});
    same(rtcmA, {R(rtcmA)});
    same(rtcmEmpty, {R(rtcmEmpty)});
    same(rtcmBig, {R(rtcmBig)});
    const std::string order = R"({"id":7,"method":"GET","path":"/api/status"})";
    same(text(order + "\n"), {"L:" + order});
    same(text("  \r\n" + order + "\r\n"), {"L:" + order});            // espacios y CRLF
    same(text("hola\n"), {"L:hola"});                                   // la consola le contesta 400, como siempre
    // UTF-8 con 0xD3 (cirílico «Ӂ» = D3 81) dentro de una cadena: la línea sigue entera.
    const std::string cyrillic = "{\"id\":1,\"method\":\"POST\",\"path\":\"/api/wifi\",\"body\":{\"ssid\":\"\xD3\x81\xD3\x82\"}}";
    same(text(cyrillic + "\n"), {"L:" + cyrillic});

    // Carga máxima del enlace y una de más.
    const std::string maxPayload(radio_usb::kMaxPayloadBytes, 'x');
    same(frame(Type::status, maxPayload), {F(Type::status, maxPayload)});
    Bytes room(radio_usb::kMaxFrameBytes + 10);
    const std::string tooBig(radio_usb::kMaxPayloadBytes + 1, 'x');
    assert(!radio_usb::encode(Type::status, reinterpret_cast<const uint8_t*>(tooBig.data()), tooBig.size(), room.data(), room.size()));
    assert(!radio_usb::encode(uint8_t(0), nullptr, 0, room.data(), room.size()));      // tipo 0 no existe
    assert(!radio_usb::encode(uint8_t(0x80), nullptr, 0, room.data(), room.size()));
    assert(!radio_usb::encode(Type::role, nullptr, 0, room.data(), radio_usb::kHeaderBytes + 2));   // no cabe

    // --- Todo junto, como en el cable ----------------------------------------------
    {
        Bytes s = text("ESP-ROM:esp32s3-20210327\r\nTresVizo RTK 0.9.0. Consola JSON USB disponible.\n");
        append(s, frame(Type::welcome, R"({"protocol":1,"accepted":true})"));
        append(s, rtcmA);
        append(s, text("{\"id\":3,\"status\":200,\"body\":{}}\n"));
        append(s, frame(Type::role, R"({"role":"base"})"));
        append(s, rtcmBig);
        append(s, rtcmEmpty);
        same(s, {"L:ESP-ROM:esp32s3-20210327", "L:TresVizo RTK 0.9.0. Consola JSON USB disponible.",
                 F(Type::welcome, R"({"protocol":1,"accepted":true})"), R(rtcmA),
                 "L:{\"id\":3,\"status\":200,\"body\":{}}", F(Type::role, R"({"role":"base"})"), R(rtcmBig),
                 R(rtcmEmpty)});
    }

    // --- Basura y cortes -------------------------------------------------------------
    {
        // Una trama del enlace cortada a la mitad (el otro lado se reinició) y luego
        // tramas buenas: se pierde la cortada y nada más.
        const Bytes cut = frame(Type::status, R"({"role":"rover","rssi_dbm":-91.5})");
        Bytes s(cut.begin(), cut.begin() + 12);
        append(s, frame(Type::hello, hello));
        append(s, rtcmA);
        same(s, {F(Type::hello, hello), R(rtcmA)});
    }
    {
        // Una RTCM cortada que declara 1023 bytes: lo que viene detrás sale igual.
        Bytes s(rtcmBig.begin(), rtcmBig.begin() + 40);
        append(s, frame(Type::role, R"({"role":"rover"})"));
        append(s, rtcmA);
        same(s, {F(Type::role, R"({"role":"rover"})"), R(rtcmA)});
    }
    {
        // CRC malo: esa trama no sale; la siguiente sí.
        Bytes bad = frame(Type::config, R"({"seq":1,"channel":3})");
        bad[10] ^= 0x01;
        Bytes s = bad;
        append(s, frame(Type::config, R"({"seq":2,"channel":4})"));
        radio_usb::Demux demux; Recorder rec;
        demux.feed(s.data(), s.size(), 0, rec);
        assert(rec.events == std::vector<std::string>({F(Type::config, R"({"seq":2,"channel":4})")}));
        assert(demux.counters.crcErrors == 1 && demux.counters.frames == 1);
        Bytes badRtcm = rtcmA; badRtcm[5] ^= 0x80;
        Bytes t = badRtcm; append(t, rtcmA);
        same(t, {R(rtcmA)});
    }
    {
        // Texto sin '\n' cortado por una RTCM o por una trama del enlace: salen enteras.
        Bytes s = text("Guru Meditation Error: Core 1 panic'ed");
        append(s, rtcmA);
        append(s, text("rst:0x3 (SW_RESET)"));
        append(s, frame(Type::welcome, "{}"));
        append(s, text("\n"));
        same(s, {R(rtcmA), F(Type::welcome, "{}")});
    }
    {
        // Basura binaria entre cosas buenas.
        Bytes s = {0x00, 0xFF, 0xF5, 0x52, 0x09, 0xD3, 0xFF, 0xC0, 0x01};
        append(s, rtcmA);
        append(s, Bytes{0xF5, 0xF5, 0x52});
        append(s, frame(Type::status, "{}"));
        same(s, {R(rtcmA), F(Type::status, "{}")});
    }

    // --- Líneas largas, como la consola de siempre (413 al llegar el '\n') -------------
    {
        const std::string fits(radio_usb::kMaxLineBytes, 'a');
        same(text(fits + "\n"), {"L:" + fits});
        const std::string tooLong(radio_usb::kMaxLineBytes + 1, 'a');
        same(text(tooLong + "\n" + order + "\n"), {"OVERFLOW", "L:" + order});
        same(text(std::string(5000, 'b') + "\r\n"), {"OVERFLOW"});
        // Una línea larga cortada por una RTCM: la RTCM sale (también si el 0xD3 ya se tiró).
        Bytes s = text(std::string(2000, 'c'));
        append(s, rtcmA);
        append(s, frame(Type::role, "{}"));
        same(s, {R(rtcmA), F(Type::role, "{}")});
    }

    // --- Caducidades -------------------------------------------------------------------
    {
        radio_usb::Demux demux; Recorder rec;
        const Bytes partial = text("{\"id\":1,\"method\":\"GET\"");
        demux.feed(partial.data(), partial.size(), 1000, rec);
        demux.tick(5999, rec);
        assert(rec.events.empty());
        demux.tick(6000, rec);                         // 5 s desde el comienzo: 408
        assert(rec.events == std::vector<std::string>({"TIMEOUT"}));
        assert(demux.pending() == 0);
        const Bytes next = text(order + "\n");          // y la consola sigue
        demux.feed(next.data(), next.size(), 6100, rec);
        assert(rec.events.back() == "L:" + order);
    }
    {
        // Una línea demasiado larga que nunca termina también caduca.
        radio_usb::Demux demux; Recorder rec;
        const Bytes s = text(std::string(3000, 'z'));
        demux.feed(s.data(), s.size(), 0, rec);
        demux.tick(radio_usb::kLineTimeoutMs, rec);
        assert(rec.events == std::vector<std::string>({"TIMEOUT"}));
    }
    {
        // La regla de rtcm3.h: una trama completa y buena dentro del búfer gana en el
        // acto a la trama a medias que la envuelve (sin esperar sus 777 bytes ni 1 s).
        radio_usb::Demux demux; Recorder rec;
        Bytes s = {0xF5, 0x52, 0x01, 0x04, 0x00, 0x03};   // dice 768 bytes de carga
        append(s, rtcmA);
        append(s, frame(Type::role, "{}"));
        demux.feed(s.data(), s.size(), 500, rec);
        assert(rec.events == std::vector<std::string>({R(rtcmA), F(Type::role, "{}")}));
        assert(demux.counters.abandoned == 1 && demux.pending() == 0);
    }
    {
        // Trama binaria a medias y luego silencio: al segundo se suelta, y lo que traía
        // detrás (una línea, que no tiene CRC para ganarle) sale.
        radio_usb::Demux demux; Recorder rec;
        Bytes s = {0xD3, 0x02, 0x00};                     // RTCM que dice 512 bytes
        append(s, text(order + "\n"));
        demux.feed(s.data(), s.size(), 500, rec);
        assert(rec.events.empty());
        demux.tick(1499, rec);
        assert(rec.events.empty());
        demux.tick(1500, rec);
        assert(rec.events == std::vector<std::string>({"L:" + order}));
        assert(demux.counters.expired == 1 && demux.pending() == 0);
    }

    // --- Al azar: muchas cosas buenas con basura entre medias --------------------------
    {
        std::mt19937 rng(20261012);
        for (int round = 0; round < 200; ++round) {
            Bytes s;
            std::vector<std::string> expected;
            const int items = 1 + int(rng() % 12);
            for (int i = 0; i < items; ++i) {
                // Basura (binaria o de texto) que termina en '\n', como el texto del receptor.
                if (rng() % 2) {
                    const size_t n = rng() % 40;
                    for (size_t k = 0; k < n; ++k) s.push_back(uint8_t(rng()));
                    s.push_back('\n');
                }
                switch (rng() % 3) {
                    case 0: {
                        std::string payload = "{\"n\":" + std::to_string(rng() % 100000) + "}";
                        payload += std::string(rng() % 300, 'p');
                        append(s, frame(Type::status, payload));
                        expected.push_back(F(Type::status, payload));
                        break;
                    }
                    case 1: {
                        Bytes body(rng() % 600);
                        for (auto& b : body) b = uint8_t(rng());
                        const Bytes r = rtcm(body);
                        append(s, r);
                        expected.push_back(R(r));
                        break;
                    }
                    default: {
                        const std::string line = "{\"id\":" + std::to_string(rng() % 1000) + "}";
                        append(s, text(line + "\n"));
                        expected.push_back("L:" + line);
                        break;
                    }
                }
            }
            const auto got = run(s, uint32_t(round + 1));
            // Lo bueno sale entero y en orden; la basura puede dar líneas de más, nunca
            // tramas de más.
            size_t at = 0;
            size_t binary = 0;
            for (const auto& e : got) {
                if (e[0] != 'L') ++binary;
                if (at < expected.size() && e == expected[at]) ++at;
            }
            size_t expectedBinary = 0;
            for (const auto& e : expected) if (e[0] != 'L') ++expectedBinary;
            assert(at == expected.size());
            assert(binary == expectedBinary);
        }
    }

    std::puts("radio_usb_test OK");
    return 0;
}
