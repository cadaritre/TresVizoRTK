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
}
