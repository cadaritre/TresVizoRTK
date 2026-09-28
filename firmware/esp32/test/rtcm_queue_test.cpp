#include "rtcm_queue.h"
#include <cassert>
#include <cstdio>
#include <vector>

// Cola de correcciones hacia el UM980: por bytes, solo tramas enteras, las más
// viejas fuera cuando no cabe, caducidad y generación al sacar.

static std::vector<uint8_t> frame(size_t length, uint8_t fill) {
    std::vector<uint8_t> f(length, fill);
    f[0] = 0xd3;
    return f;
}

int main() {
    constexpr uint32_t kMaxAge = 2000;
    uint8_t out[1029];
    size_t evicted = 0;

    // Entra y sale igual, en orden.
    {
        protocol::RtcmFrameQueue<4096> q;
        const auto a = frame(100, 1), b = frame(200, 2);
        assert(q.push(a.data(), a.size(), 1000, 7, evicted) && evicted == 0);
        assert(q.push(b.data(), b.size(), 1001, 7, evicted) && evicted == 0);
        assert(q.frames() == 2 && q.usedBytes() == 2 * 10 + 300);
        assert(q.pop(out, 1002, kMaxAge, 7) == 100 && out[1] == 1);
        assert(q.pop(out, 1003, kMaxAge, 7) == 200 && out[1] == 2);
        assert(q.pop(out, 1004, kMaxAge, 7) == 0);
        assert(q.counters().framesDelivered == 2 && q.counters().bytesDelivered == 300);
    }

    // **Una época entera cabe.** Con la cola de cuatro tramas de 0.7.10, la
    // quinta de una época se perdía. Diez tramas de 600 bytes = 6 kB.
    {
        protocol::RtcmFrameQueue<8192> q;
        for (int i = 0; i < 10; ++i) {
            const auto f = frame(600, uint8_t(i));
            assert(q.push(f.data(), f.size(), 5000, 1, evicted) && evicted == 0);
        }
        assert(q.frames() == 10 && q.counters().framesEvicted == 0);
    }

    // Si no cabe, se van **las más viejas, enteras**, y se cuentan.
    {
        protocol::RtcmFrameQueue<2100> q;  // caben dos de 1029 con cabecera, no tres
        const auto a = frame(1029, 0xa), b = frame(1029, 0xb), c = frame(1029, 0xc);
        assert(q.push(a.data(), a.size(), 1, 1, evicted) && evicted == 0);
        assert(q.push(b.data(), b.size(), 2, 1, evicted) && evicted == 0);
        assert(q.push(c.data(), c.size(), 3, 1, evicted) && evicted == 1);
        assert(q.counters().framesEvicted == 1 && q.frames() == 2);
        assert(q.pop(out, 4, kMaxAge, 1) == 1029 && out[1] == 0xb);
        assert(q.pop(out, 5, kMaxAge, 1) == 1029 && out[1] == 0xc);
    }

    // Caducadas y de otra generación no salen, y se cuentan como caducadas.
    {
        protocol::RtcmFrameQueue<4096> q;
        const auto old = frame(50, 1), otherSource = frame(60, 2), fresh = frame(70, 3);
        q.push(old.data(), old.size(), 0, 4, evicted);
        q.push(otherSource.data(), otherSource.size(), 2500, 3, evicted);
        q.push(fresh.data(), fresh.size(), 2600, 4, evicted);
        assert(q.pop(out, 2700, kMaxAge, 4) == 70 && out[1] == 3);
        assert(q.counters().framesExpired == 2);
    }

    // La vuelta de millis() a los 49 días no hace caducar lo recién llegado.
    {
        protocol::RtcmFrameQueue<4096> q;
        const auto f = frame(40, 9);
        q.push(f.data(), f.size(), 0xFFFFFF00u, 1, evicted);
        assert(q.pop(out, 0x00000010u, kMaxAge, 1) == 40);
    }

    // Da muchas vueltas al anillo sin corromper nada: tramas de tamaños
    // variados, contenido comprobado byte a byte.
    {
        protocol::RtcmFrameQueue<3000> q;
        uint32_t now = 0;
        size_t pushed = 0, popped = 0;
        for (int round = 0; round < 2000; ++round) {
            const size_t length = 6 + size_t((round * 37) % 1000);
            auto f = frame(length, uint8_t(round));
            q.push(f.data(), f.size(), now, 1, evicted);
            ++pushed;
            if (round % 3 != 0) {
                const size_t got = q.pop(out, now, kMaxAge, 1);
                if (got) {
                    ++popped;
                    for (size_t i = 1; i < got; ++i) assert(out[i] == out[1]);
                }
            }
            now += 5;
        }
        const auto& c = q.counters();
        assert(c.framesQueued == pushed);
        assert(c.framesQueued == c.framesDelivered + c.framesEvicted + c.framesExpired + q.frames());
        assert(popped == c.framesDelivered);
        assert(q.highWaterBytes() <= q.capacityBytes());
    }

    // Una trama mayor que el máximo RTCM3 no entra y se cuenta.
    {
        protocol::RtcmFrameQueue<4096> q;
        std::vector<uint8_t> big(1030, 0xd3);
        assert(!q.push(big.data(), big.size(), 0, 1, evicted));
        assert(q.counters().framesTooLarge == 1 && q.frames() == 0);
    }

    // Vaciar al cambiar de fuente cuenta lo tirado como caducado.
    {
        protocol::RtcmFrameQueue<4096> q;
        const auto f = frame(100, 1);
        q.push(f.data(), f.size(), 0, 1, evicted);
        q.push(f.data(), f.size(), 0, 1, evicted);
        q.clearAsExpired();
        assert(q.frames() == 0 && q.usedBytes() == 0 && q.counters().framesExpired == 2);
    }

    std::printf("rtcm_queue_test: todo bien\n");
    return 0;
}
