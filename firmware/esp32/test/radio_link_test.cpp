#include "radio_link.h"
#include <cassert>
#include <cstdio>
#include <string>
#include <vector>

using radio_link::Type;

int main() {
    // Ida y vuelta, aunque TCP lo entregue byte a byte.
    const std::string hello = R"({"radio_version":"0.1.0","network":1})";
    std::vector<uint8_t> wire(radio_link::kHeaderBytes + radio_link::kMaxPayloadBytes);
    size_t n = radio_link::encode(Type::hello, reinterpret_cast<const uint8_t*>(hello.data()), hello.size(),
                                  wire.data(), wire.size());
    assert(n == radio_link::kHeaderBytes + hello.size());
    const uint8_t rtcm[] = {0xD3, 0x00, 0x00, 0x47, 0xEA, 0x4B};
    n += radio_link::encode(Type::rtcm, rtcm, sizeof(rtcm), wire.data() + n, wire.size() - n);

    radio_link::Decoder decoder;
    std::vector<std::pair<Type, std::string>> got;
    for (size_t i = 0; i < n; ++i) {
        decoder.feed(wire.data() + i, 1, [&](Type type, const uint8_t* payload, size_t length) {
            got.emplace_back(type, std::string(reinterpret_cast<const char*>(payload), length));
        });
    }
    assert(!decoder.broken && got.size() == 2);
    assert(got[0].first == Type::hello && got[0].second == hello);
    assert(got[1].first == Type::rtcm && got[1].second.size() == sizeof(rtcm));

    // Una trama vacía (p. ej. un rol sin carga) también vale.
    uint8_t empty[radio_link::kHeaderBytes];
    assert(radio_link::encode(Type::status, nullptr, 0, empty, sizeof(empty)) == radio_link::kHeaderBytes);

    // No cabe: no escribe nada.
    std::vector<uint8_t> big(radio_link::kMaxPayloadBytes + 1, 0);
    assert(radio_link::encode(Type::rtcm, big.data(), big.size(), wire.data(), wire.size()) == 0);

    // Tipo desconocido o longitud imposible: el flujo queda roto y se cierra.
    radio_link::Decoder bad;
    const uint8_t junk[] = {0x7F, 0x01, 0x00, 0x00};
    bad.feed(junk, sizeof(junk), [](Type, const uint8_t*, size_t) { assert(false); });
    assert(bad.broken);
    radio_link::Decoder tooLong;
    const uint8_t header[] = {0x03, 0xFF, 0xFF};
    tooLong.feed(header, sizeof(header), [](Type, const uint8_t*, size_t) { assert(false); });
    assert(tooLong.broken);

    std::puts("radio_link_test: OK");
    return 0;
}
