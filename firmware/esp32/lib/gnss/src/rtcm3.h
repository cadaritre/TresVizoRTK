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
// Rearma tramas RTCM3 (0xD3, 6 bits a 0, 10 de longitud, carga, CRC-24Q) de un
// flujo de bytes. Solo entrega tramas con CRC correcto.
//
// Desde 0.9.0, las mismas reglas que las apps:
// 1. Una trama a medias no retiene el flujo: si **dentro del búfer** empieza en
//    un 0xD3 posterior otra trama que se completa con CRC correcto, la de medias
//    se descarta en el acto (`abandoned`) y la buena sale. Antes había que
//    esperar a completar la longitud declarada por una cabecera falsa (hasta
//    1029 bytes: ~90 ms a 115200 en la UART, o la trama siguiente entera por BLE).
// 2. `feedAt` con el reloj: una trama a medias sin bytes nuevos durante 1 s se
//    descarta (`expired`). `feed` sin reloj no caduca (lo usan quienes ya
//    reinician el parser por su cuenta).
class Rtcm3Parser {
    uint8_t bytes[1029] = {};
    size_t length = 0;
    // Posibles comienzos de trama dentro del búfer (después del 0) y dónde
    // acabarían. Se miran solo cuando el búfer llega justo a ese final.
    static constexpr size_t kCandidates = 16;
    uint16_t candidateStart[kCandidates] = {}, candidateEnd[kCandidates] = {};
    size_t candidates = 0;
    uint32_t lastByteMs = 0;
    bool timed = false;
    void shift(size_t by) {
        length -= by;
        if (length) memmove(bytes, bytes + by, length);
        size_t kept = 0;
        for (size_t i = 0; i < candidates; ++i) {
            if (candidateStart[i] <= by) continue;  // el que queda en 0 es la trama principal
            candidateStart[kept] = uint16_t(candidateStart[i] - by);
            candidateEnd[kept] = uint16_t(candidateEnd[i] - by);
            ++kept;
        }
        candidates = kept;
    }
    // Descarta el primer byte y salta hasta el siguiente 0xD3 con un solo memmove.
    // Byte a byte el coste era cuadratico ante ruido o arranque a mitad de trama.
    void resync() {
        size_t next = 1;
        while (next < length && bytes[next] != 0xd3) ++next;
        shift(next);
    }
    void remember(size_t start) {
        if (start == 0 || start + 3 > length) return;
        if (bytes[start] != 0xd3 || (bytes[start + 1] & 0xfc)) return;
        const size_t end = start + ((((bytes[start + 1] & 3) << 8) | bytes[start + 2]) + 6);
        if (end > sizeof(bytes)) return;
        if (candidates == kCandidates) {  // sin sitio: se olvida el más viejo
            memmove(candidateStart, candidateStart + 1, sizeof(candidateStart[0]) * (kCandidates - 1));
            memmove(candidateEnd, candidateEnd + 1, sizeof(candidateEnd[0]) * (kCandidates - 1));
            --candidates;
        }
        candidateStart[candidates] = uint16_t(start);
        candidateEnd[candidates] = uint16_t(end);
        ++candidates;
    }
    static bool valid(const uint8_t* frame, size_t total) {
        const uint32_t actual = (static_cast<uint32_t>(frame[total - 3]) << 16) |
            (static_cast<uint32_t>(frame[total - 2]) << 8) | frame[total - 1];
        return crc24q(frame, total - 3) == actual;
    }
public:
    uint32_t accepted = 0, rejected = 0, overflow = 0;
    // Tramas a medias descartadas: por otra completa dentro del búfer, o por 1 s sin bytes.
    uint32_t abandoned = 0, expired = 0;
    void reset() { length = 0; candidates = 0; }
    template<class Consumer> void feedAt(uint8_t value, uint32_t nowMs, Consumer consume) {
        if (timed && length && nowMs - lastByteMs > 1000) { ++expired; reset(); }
        timed = true;
        lastByteMs = nowMs;
        feed(value, consume);
    }
    template<class Consumer> void feed(uint8_t value, Consumer consume) {
        // Una trama RTCM3 valida nunca supera 1029 bytes, asi que el buffer solo se
        // llena con basura; resincronizar deja sitio en vez de perder el byte en silencio.
        if (length == sizeof(bytes)) { ++overflow; resync(); }
        bytes[length++] = value;
        // ¿Este byte completa la cabecera de un comienzo posterior al 0?
        if (length >= 3) remember(length - 3);
        while (length) {
            if (bytes[0] != 0xd3 || (length >= 2 && (bytes[1] & 0xfc))) { resync(); continue; }
            if (length < 3) return;
            const size_t total = (((bytes[1] & 3) << 8) | bytes[2]) + 6;
            if (length < total) {
                // Regla 1: otra trama completa y buena dentro del búfer gana.
                for (size_t i = 0; i < candidates; ++i) {
                    if (candidateEnd[i] != length) continue;
                    const size_t start = candidateStart[i];
                    if (!valid(bytes + start, length - start)) continue;
                    ++abandoned; ++accepted;
                    consume(bytes + start, length - start);
                    reset();
                    return;
                }
                return;
            }
            if (valid(bytes, total)) {
                ++accepted; consume(bytes, total);
                shift(total);
            } else { ++rejected; resync(); }
        }
    }
};
}
