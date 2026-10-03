#include "radio_air.h"
#include "rtcm3.h"
#include <cassert>
#include <cstdio>
#include <vector>

namespace {
// Trama RTCM3 válida de `payload` bytes (tipo 1074 de mentira, con su CRC-24Q).
std::vector<uint8_t> frame(size_t payload, uint8_t seed) {
    std::vector<uint8_t> f = {0xD3, static_cast<uint8_t>((payload >> 8) & 3), static_cast<uint8_t>(payload & 0xff)};
    for (size_t i = 0; i < payload; ++i) f.push_back(static_cast<uint8_t>(seed + i * 7));
    if (payload >= 2) { f[3] = 0x43; f[4] = 0x20; }   // 1074 en los 12 primeros bits
    const uint32_t crc = gnss::crc24q(f.data(), f.size());
    f.push_back(static_cast<uint8_t>(crc >> 16)); f.push_back(static_cast<uint8_t>(crc >> 8)); f.push_back(static_cast<uint8_t>(crc));
    return f;
}

struct Air {
    std::vector<std::vector<uint8_t>> packets;
};

// Rover: recibe paquetes, reinicia el parser ante un salto y cuenta tramas.
size_t receive(const Air& air, uint8_t network, const std::vector<size_t>& drop, radio_air::Receiver& receiver) {
    receiver.network = network;
    gnss::Rtcm3Parser parser;
    size_t frames = 0;
    for (size_t i = 0; i < air.packets.size(); ++i) {
        bool skip = false;
        for (size_t d : drop) skip = skip || d == i;
        if (skip) continue;
        size_t length = 0; bool gap = false;
        const uint8_t* chunk = receiver.accept(air.packets[i].data(), air.packets[i].size(), length, gap);
        if (!chunk) continue;
        if (gap) parser.reset();
        for (size_t b = 0; b < length; ++b) parser.feed(chunk[b], [&](const uint8_t*, size_t) { ++frames; });
    }
    return frames;
}
}  // namespace

int main() {
    // Una época de base como la de un MSM4 de cuatro constelaciones: 1005 + 4 MSM.
    std::vector<std::vector<uint8_t>> epoch = {frame(19, 1), frame(160, 2), frame(140, 3), frame(150, 4), frame(170, 5)};
    radio_air::Packetizer base;
    base.network = 12;
    Air air;
    auto send = [&](const uint8_t* p, size_t n) {
        assert(n <= radio_air::kMaxPacketBytes);
        air.packets.emplace_back(p, p + n);
    };
    uint32_t now = 1000;
    size_t bytes = 0;
    for (int second = 0; second < 10; ++second) {
        for (const auto& f : epoch) { base.add(f.data(), f.size(), now, send); bytes += f.size(); }
        base.tick(now + 5, send);                          // aún no: llegan más tramas
        base.tick(now + radio_air::kFlushIdleMs, send);    // fin de la ráfaga: sale el resto
        assert(base.empty());
        now += 1000;
    }
    // ≈ 0.66 kB por época: cabe de sobra en ≈2.5 kB/s.
    assert(bytes == 10 * (25 + 166 + 146 + 156 + 176));

    // Sin pérdidas: llegan las 50 tramas.
    radio_air::Receiver rover;
    assert(receive(air, 12, {}, rover) == 50);
    assert(rover.lost == 0 && rover.accepted == air.packets.size());

    // Se pierde un paquete: solo caen las tramas que lo cruzaban; el resto llega.
    radio_air::Receiver lossy;
    const size_t withLoss = receive(air, 12, {3}, lossy);
    assert(lossy.lost == 1);
    assert(withLoss >= 50 - 3 && withLoss < 50);

    // Otra red en el mismo canal: no se mezcla.
    radio_air::Receiver other;
    assert(receive(air, 13, {}, other) == 0 && other.foreign == air.packets.size());

    // Basura en el aire.
    radio_air::Receiver noise;
    const uint8_t junk[] = {0x00, 0x01, 0x02, 0x03, 0x04};
    size_t length = 0; bool gap = false;
    assert(!noise.accept(junk, sizeof(junk), length, gap) && noise.malformed == 1);

    // Canales y potencia.
    assert(radio_air::channelHz(radio_air::kDefaultChannel) == 915000000);
    assert(radio_air::channelHz(0) == 903000000 && radio_air::channelHz(12) == 927000000);
    assert(radio_air::channelHz(200) == 915000000);
    assert(radio_air::chipDbmFor(30) == 22 && radio_air::chipDbmFor(40) == 22);
    assert(radio_air::chipDbmFor(20) == 12 && radio_air::chipDbmFor(-50) == radio_air::kMinChipDbm);

    std::puts("radio_air_test: OK");
    return 0;
}
