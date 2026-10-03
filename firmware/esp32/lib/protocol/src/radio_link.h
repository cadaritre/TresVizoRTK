#pragma once
#include <cstddef>
#include <cstdint>
#include <cstring>

namespace radio_link {
// Enlace entre el MeridianV y su módulo de radio LoRa (docs/radio/RADIO_MODULE.md).
//
// El módulo es un aparato aparte con su propio ESP32: se une a la red Wi-Fi del
// MeridianV y abre una conexión TCP a 192.168.4.1:kPort. Por ella van tramas
// sencillas: tipo (1 byte), longitud (2 bytes, little-endian) y carga. El control
// va en JSON; el RTCM, en bruto (una trama RTCM3 entera por trama del enlace).
//
// Sin Arduino a propósito: lo comparten los dos firmwares y se prueba con g++ en
// test/radio_link_test.cpp.
constexpr uint16_t kPort = 2102;            // 2101 es NTRIP; el radio va al lado
constexpr size_t kHeaderBytes = 3;
constexpr size_t kMaxPayloadBytes = 1100;   // una trama RTCM3 (≤ 1029) o un JSON de control

enum class Type : uint8_t {
    hello = 0x01,   // radio → MeridianV: quién es (JSON)
    role = 0x02,    // MeridianV → radio: "base" | "rover" | "idle" (JSON)
    rtcm = 0x03,    // en los dos sentidos: una trama RTCM3 completa
    status = 0x04,  // radio → MeridianV, 1 Hz: estado del aire (JSON); sirve de latido
    config = 0x05,  // MeridianV → radio: red, canal y potencia (JSON)
};

inline bool knownType(uint8_t value) { return value >= 0x01 && value <= 0x05; }

// Escribe una trama en `out` (cabe `kHeaderBytes + length`). Devuelve los bytes
// escritos, o 0 si la carga no cabe.
inline size_t encode(Type type, const uint8_t* payload, size_t length, uint8_t* out, size_t capacity) {
    if (length > kMaxPayloadBytes || capacity < kHeaderBytes + length) return 0;
    out[0] = static_cast<uint8_t>(type);
    out[1] = static_cast<uint8_t>(length & 0xff);
    out[2] = static_cast<uint8_t>(length >> 8);
    if (length) std::memcpy(out + kHeaderBytes, payload, length);
    return kHeaderBytes + length;
}

// Rearma tramas de un flujo TCP que puede llegar a trozos. Un tipo desconocido o
// una longitud imposible dejan el flujo inservible: se marca `broken` y quien lo
// usa cierra la conexión (no hay forma fiable de resincronizar un TCP mal cortado).
class Decoder {
    uint8_t buffer[kHeaderBytes + kMaxPayloadBytes] = {};
    size_t filled = 0;
public:
    bool broken = false;
    uint32_t frames = 0;
    void reset() { filled = 0; broken = false; }

    template <class Consumer> void feed(const uint8_t* data, size_t length, Consumer consume) {
        for (size_t i = 0; i < length && !broken; ++i) {
            buffer[filled++] = data[i];
            if (filled == 1 && !knownType(buffer[0])) { broken = true; return; }
            if (filled < kHeaderBytes) continue;
            const size_t payload = buffer[1] | (static_cast<size_t>(buffer[2]) << 8);
            if (payload > kMaxPayloadBytes) { broken = true; return; }
            if (filled == kHeaderBytes + payload) {
                ++frames;
                consume(static_cast<Type>(buffer[0]), buffer + kHeaderBytes, payload);
                filled = 0;
            }
        }
    }
};
}  // namespace radio_link
