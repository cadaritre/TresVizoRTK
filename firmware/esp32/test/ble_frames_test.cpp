#include "ble_frames.h"
#include <cassert>
#include <cstdio>
#include <string>

// Trocea como lo hace ble_transport.cpp y reensambla como la app
// (BLEResponseReassembler.swift): los desplazamientos tienen que ser exactos y
// consecutivos, o la app descarta el mensaje entero.
static std::string roundTrip(const std::string& json, uint16_t mtu, uint16_t messageId, size_t& frames) {
    std::string rebuilt;
    size_t offset = 0;
    frames = 0;
    uint8_t frame[protocol::kMaxNotificationBytes];
    do {
        const size_t length = protocol::encodeResponseFrame(frame, messageId, offset, json.data(), json.size(),
                                                            protocol::responsePayloadBytes(mtu));
        // Nunca mas grande de lo que admite el MTU, ni del tope del equipo.
        assert(length <= size_t(std::max<uint16_t>(mtu, protocol::kMinimumAttMtu)) - protocol::kAttHeaderBytes);
        assert(length <= protocol::kMaxNotificationBytes);
        const uint16_t id = frame[0] | (frame[1] << 8);
        const size_t at = frame[2] | (frame[3] << 8);
        const bool first = frame[4] & 1, last = frame[4] & 2;
        assert(id == messageId);
        assert(at == rebuilt.size());              // consecutivo, sin huecos
        assert(first == (frames == 0));
        rebuilt.append(reinterpret_cast<const char*>(frame + protocol::kResponseHeaderBytes),
                       length - protocol::kResponseHeaderBytes);
        offset += length - protocol::kResponseHeaderBytes;
        ++frames;
        assert(last == (offset == json.size()));
        if (last) break;
    } while (true);
    return rebuilt;
}

int main() {
    // Sin negociar: 15 bytes de JSON, como siempre.
    assert(protocol::responsePayloadBytes(23) == 15);
    // Un MTU imposible no deja la trama por debajo de la de siempre.
    assert(protocol::responsePayloadBytes(0) == 15);
    // Lo habitual en iPhone y el tope que ofrece el equipo.
    assert(protocol::responsePayloadBytes(185) == 177);
    assert(protocol::responsePayloadBytes(247) == 239);
    // Un telefono que pida mas no rompe el tope de una notificacion.
    assert(protocol::responsePayloadBytes(517) == 239);

    // Compatible byte a byte con la trama de 20 que ya lee la app.
    const std::string corta = "{\"id\":7,\"status\":200,\"body\":{}}";
    uint8_t frame[protocol::kMaxNotificationBytes];
    const size_t length = protocol::encodeResponseFrame(frame, 0x0102, 15, corta.data(), corta.size(), 15);
    assert(length == 20);
    assert(frame[0] == 0x02 && frame[1] == 0x01 && frame[2] == 15 && frame[3] == 0 && frame[4] == 0);
    assert(std::memcmp(frame + 5, corta.data() + 15, 15) == 0);

    // Respuestas de todos los tamanos, con todos los MTU: se reensamblan
    // enteras. El cielo con cuarenta satelites ronda los 2.5 kB; el tope del
    // firmware son 4096.
    size_t frames = 0;
    for (size_t size : {size_t(1), size_t(15), size_t(16), size_t(239), size_t(240), size_t(2048), size_t(2500), size_t(4096)}) {
        std::string json(size, 'x');
        for (size_t i = 0; i < size; ++i) json[i] = char('a' + i % 26);
        for (uint16_t mtu : {uint16_t(23), uint16_t(185), uint16_t(247), uint16_t(517)}) {
            assert(roundTrip(json, mtu, 42, frames) == json);
            const size_t per = protocol::responsePayloadBytes(mtu);
            assert(frames == (size + per - 1) / per);
        }
    }

    // Lo que se gana: 2 kB pasan de 134 tramas a 9.
    roundTrip(std::string(2000, 'x'), 23, 1, frames);
    assert(frames == 134);
    roundTrip(std::string(2000, 'x'), 247, 1, frames);
    assert(frames == 9);

    std::puts("ble_frames_test OK");
    return 0;
}
