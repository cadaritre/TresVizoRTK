#pragma once
#include <cstddef>
#include <cstdint>
#include <cstring>
namespace gnss {
inline uint32_t crc24q(const uint8_t* data, size_t length) {
    uint32_t crc = 0;
    for (size_t i = 0; i < length; ++i) {
        crc ^= static_cast<uint32_t>(data[i]) << 16;
        for (int bit = 0; bit < 8; ++bit) {
            crc <<= 1;
            if (crc & 0x1000000) crc ^= 0x1864CFB;
        }
    }
    return crc & 0xffffff;
}
class Rtcm3Parser {
    uint8_t bytes[1029] = {};
    size_t length = 0;
    // Descarta el primer byte y salta hasta el siguiente 0xD3 con un solo memmove.
    // Byte a byte el coste era cuadratico ante ruido o arranque a mitad de trama.
    void resync() {
        size_t next = 1;
        while (next < length && bytes[next] != 0xd3) ++next;
        length -= next;
        if (length) memmove(bytes, bytes + next, length);
    }
public:
    uint32_t accepted = 0, rejected = 0, overflow = 0;
    void reset() { length = 0; }
    template<class Consumer> void feed(uint8_t value, Consumer consume) {
        // Una trama RTCM3 valida nunca supera 1029 bytes, asi que el buffer solo se
        // llena con basura; resincronizar deja sitio en vez de perder el byte en silencio.
        if (length == sizeof(bytes)) { ++overflow; resync(); }
        bytes[length++] = value;
        while (length) {
            if (bytes[0] != 0xd3 || (length >= 2 && (bytes[1] & 0xfc))) { resync(); continue; }
            if (length < 3) return;
            const size_t total = (((bytes[1] & 3) << 8) | bytes[2]) + 6;
            if (length < total) return;
            const uint32_t actual = (static_cast<uint32_t>(bytes[total-3]) << 16) |
                (static_cast<uint32_t>(bytes[total-2]) << 8) | bytes[total-1];
            if (crc24q(bytes, total-3) == actual) {
                ++accepted; consume(bytes, total);
                length -= total; memmove(bytes, bytes + total, length);
            } else { ++rejected; resync(); }
        }
    }
};
}
