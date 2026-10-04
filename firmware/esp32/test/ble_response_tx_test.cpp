#include "ble_response_tx.h"
#include "ble_frames.h"
#include <cassert>
#include <string>
#include <cstdio>

int main() {
    // Pérdidas locales inyectadas: el receptor ve cada byte exactamente una
    // vez aunque fallen varios intentos seguidos, en MTU mínimo y negociado.
    for (uint16_t mtu : {23, 185, 247}) {
        const std::string json(4096, 'x');
        std::string received;
        protocol::BleResponseTx tx;
        uint32_t now = UINT32_MAX - 500; // incluye vuelta del reloj
        tx.begin(json.size(), now);
        unsigned attempts = 0;
        while (!tx.complete()) {
            assert(!tx.expired(now));
            assert(tx.due(now));
            uint8_t frame[protocol::kMaxNotificationBytes];
            const auto size = protocol::encodeResponseFrame(frame, 65535, tx.offset(), json.data(), json.size(),
                                                            protocol::responsePayloadBytes(mtu));
            const bool accepted = (++attempts % 3) == 0;
            if (accepted) {
                assert(size_t(frame[2] | frame[3] << 8) == received.size());
                assert(bool(frame[4] & 1) == received.empty());
                received.append(reinterpret_cast<char*>(frame + 5), size - 5);
                assert(bool(frame[4] & 2) == (received.size() == json.size()));
            }
            tx.attempted(now, size - 5, accepted);
            assert(tx.offset() == received.size());
            assert(!tx.due(now + 4));
            now += 5;
        }
        assert(received == json);
    }
    protocol::BleResponseTx tx;
    tx.begin(100, UINT32_MAX - 20);
    assert(!tx.expired(uint32_t(UINT32_MAX - 20) + 4499));
    assert(tx.expired(uint32_t(UINT32_MAX - 20) + 4500));
    tx.attempted(4479, 10, false);
    assert(tx.expired(4480)); // reintentar no reinicia el plazo
    tx.begin(3, 5000); // sesión nueva: no arrastra el offset anterior
    assert(tx.offset() == 0 && !tx.expired(5000));
    tx.attempted(5000, 4, true); // nunca desbordar
    assert(tx.offset() == 0);
    tx.attempted(5005, 3, true);
    assert(tx.complete() && !tx.expired(10000));
    puts("ble_response_tx: OK");
}
