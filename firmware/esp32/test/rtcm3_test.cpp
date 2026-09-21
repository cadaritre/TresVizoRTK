#include "rtcm3.h"
#include <cassert>
#include <vector>
int main() {
    std::vector<uint8_t> packet{0xd3, 0, 4, 0x3e, 0xd0, 0, 0};
    const auto crc = gnss::crc24q(packet.data(), packet.size());
    packet.push_back(crc >> 16); packet.push_back(crc >> 8); packet.push_back(crc);
    gnss::Rtcm3Parser parser;
    unsigned count = 0;
    auto consume = [&](const uint8_t* data, size_t size) { assert(size == packet.size()); assert(data[0] == 0xd3); ++count; };
    for (const auto byte : packet) parser.feed(byte, consume);
    assert(count == 1);
    packet.back() ^= 1;
    for (const auto byte : packet) parser.feed(byte, consume);
    assert(count == 1 && parser.rejected == 1);
    packet.back() ^= 1;
    for (const auto byte : packet) parser.feed(byte, consume);
    assert(count == 2);
    for (int i = 0; i < 5000; ++i) parser.feed(0xff, consume);
    for (const auto byte : packet) parser.feed(byte, consume);
    assert(count == 3);

    // Resincronización: basura con 0xD3 intercalados no debe perder la trama
    // siguiente ni dejar el buffer bloqueado.
    gnss::Rtcm3Parser noisy;
    unsigned recovered = 0;
    auto collect = [&](const uint8_t*, size_t size) { assert(size == packet.size()); ++recovered; };
    for (int i = 0; i < 40; ++i) { noisy.feed(0xd3, collect); noisy.feed(0xff, collect); }
    for (const auto byte : packet) noisy.feed(byte, collect);
    assert(recovered == 1);

    // Cabecera con la longitud máxima y CRC inválido: ocupa el buffer entero y
    // el parser debe recuperarse para aceptar la trama siguiente.
    gnss::Rtcm3Parser flooded;
    unsigned after = 0;
    auto tally = [&](const uint8_t*, size_t) { ++after; };
    flooded.feed(0xd3, tally); flooded.feed(0x03, tally); flooded.feed(0xff, tally);
    for (int i = 0; i < 4000; ++i) flooded.feed(0x00, tally);
    for (const auto byte : packet) flooded.feed(byte, tally);
    assert(after == 1);
}
