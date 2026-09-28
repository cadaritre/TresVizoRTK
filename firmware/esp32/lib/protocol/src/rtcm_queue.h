#pragma once
#include <cstddef>
#include <cstdint>
#include <cstring>

namespace protocol {
// Cola de tramas RTCM3 camino del UM980, medida en **bytes** y no en huecos
// fijos. Sin Arduino ni FreeRTOS, para probarla en la PC
// (test/rtcm_queue_test.cpp); el cerrojo lo pone quien la usa
// (src/gnss_receiver.cpp).
//
// Por qué existe: hasta 0.7.10 la cola eran **cuatro tramas**. La UART al UM980
// va a 115200 baudios, unos 11.5 kB/s, y una época de correcciones llega de
// golpe: por NTRIP en el propio equipo el socket entrega toda la época en unos
// milisegundos, y por Bluetooth sin respuesta también puede llegar más rápido
// de lo que la UART la vacía. Con MSM de cuatro constelaciones más 1005, 1033 y
// 1230 una época son 6 a 10 tramas: la quinta ya se tiraba, **en cada época**,
// y el receptor recibía épocas incompletas sin que nadie lo viera.
//
// Reglas:
// - **Solo tramas enteras.** Nunca se parte una trama al descartar: una trama
//   a medias en la UART le cuesta al UM980 la trama siguiente.
// - **Si no cabe, se van las más viejas** (se desalojan desde la cabeza). Para
//   corregir, una época nueva vale más que una atrasada: el receptor descarta
//   las correcciones viejas de todos modos.
// - **Caducidad al sacar**: una trama que esperó más de `maxAgeMs`, o que es
//   de otra generación de fuente (se cambió de fuente o se reconectó), no sale.
// - Todo descarte se cuenta con su motivo. Nada se pierde en silencio.
struct RtcmQueueCounters {
    uint32_t framesQueued = 0;      // tramas que entraron
    uint32_t framesEvicted = 0;     // desalojadas por falta de sitio (las más viejas)
    uint32_t framesExpired = 0;     // caducadas o de otra generación al sacarlas
    uint32_t framesTooLarge = 0;    // no caben ni en la cola vacía (no debería pasar: RTCM3 <= 1029)
    uint32_t framesDelivered = 0;   // tramas entregadas al escritor de la UART
    uint64_t bytesQueued = 0;       // bytes RTCM (sin cabeceras) que entraron
    uint64_t bytesDelivered = 0;    // bytes RTCM entregados al escritor de la UART
};

template <size_t CapacityBytes>
class RtcmFrameQueue {
public:
    // Cabecera de cada registro: longitud (2), llegada en ms (4), generación (4).
    static constexpr size_t kRecordHeaderBytes = 10;
    // Trama RTCM3 más larga: 3 de cabecera + 1023 de carga + 3 de CRC.
    static constexpr size_t kMaxFrameBytes = 1029;
    static_assert(CapacityBytes >= kRecordHeaderBytes + kMaxFrameBytes,
                  "La cola debe admitir al menos una trama de tamaño máximo.");

    // Pone la trama al final. Si no cabe, desaloja tramas enteras desde la
    // cabeza hasta que quepa. Devuelve cuántas desalojó (0 lo normal).
    // Devuelve false solo si la trama no es válida por tamaño.
    bool push(const uint8_t* frame, size_t length, uint32_t arrivalMs, uint32_t generation, size_t& evicted) {
        evicted = 0;
        if (!frame || length == 0 || length > kMaxFrameBytes) {
            ++counters_.framesTooLarge;
            return false;
        }
        const size_t needed = kRecordHeaderBytes + length;
        while (CapacityBytes - used_ < needed && frames_) {
            dropHead();
            ++evicted;
            ++counters_.framesEvicted;
        }
        uint8_t header[kRecordHeaderBytes];
        header[0] = uint8_t(length);
        header[1] = uint8_t(length >> 8);
        put32(header + 2, arrivalMs);
        put32(header + 6, generation);
        write(header, kRecordHeaderBytes);
        write(frame, length);
        ++frames_;
        ++counters_.framesQueued;
        counters_.bytesQueued += length;
        if (used_ > highWater_) highWater_ = used_;
        return true;
    }

    // Saca la trama vigente más vieja a `out` (al menos kMaxFrameBytes).
    // Descarta antes, contándolas, las caducadas y las de otra generación.
    // Devuelve la longitud, o 0 si no queda ninguna vigente.
    size_t pop(uint8_t* out, uint32_t nowMs, uint32_t maxAgeMs, uint32_t currentGeneration) {
        while (frames_) {
            uint8_t header[kRecordHeaderBytes];
            peek(header, kRecordHeaderBytes);
            const size_t length = size_t(header[0]) | (size_t(header[1]) << 8);
            const uint32_t arrival = get32(header + 2);
            const uint32_t generation = get32(header + 6);
            // Resta sin signo: sobrevive a la vuelta de millis() a los 49 días.
            const bool stale = uint32_t(nowMs - arrival) > maxAgeMs || generation != currentGeneration;
            if (stale) {
                dropHead();
                ++counters_.framesExpired;
                continue;
            }
            skip(kRecordHeaderBytes);
            read(out, length);
            --frames_;
            ++counters_.framesDelivered;
            counters_.bytesDelivered += length;
            return length;
        }
        return 0;
    }

    // Vacía la cola sin contarlo como descarte de datos vigentes: se usa al
    // cambiar de fuente, cuando todo lo encolado ya es de otra generación.
    void clearAsExpired() {
        while (frames_) {
            dropHead();
            ++counters_.framesExpired;
        }
    }

    size_t usedBytes() const { return used_; }
    size_t frames() const { return frames_; }
    size_t highWaterBytes() const { return highWater_; }
    static constexpr size_t capacityBytes() { return CapacityBytes; }
    const RtcmQueueCounters& counters() const { return counters_; }

private:
    uint8_t buffer_[CapacityBytes] = {};
    size_t head_ = 0, used_ = 0, frames_ = 0, highWater_ = 0;
    RtcmQueueCounters counters_;

    static void put32(uint8_t* p, uint32_t value) {
        for (int i = 0; i < 4; ++i) p[i] = uint8_t(value >> (8 * i));
    }
    static uint32_t get32(const uint8_t* p) {
        return uint32_t(p[0]) | (uint32_t(p[1]) << 8) | (uint32_t(p[2]) << 16) | (uint32_t(p[3]) << 24);
    }
    void write(const uint8_t* data, size_t length) {
        size_t tail = (head_ + used_) % CapacityBytes;
        const size_t first = length < CapacityBytes - tail ? length : CapacityBytes - tail;
        std::memcpy(buffer_ + tail, data, first);
        std::memcpy(buffer_, data + first, length - first);
        used_ += length;
    }
    void peek(uint8_t* out, size_t length) const {
        const size_t first = length < CapacityBytes - head_ ? length : CapacityBytes - head_;
        std::memcpy(out, buffer_ + head_, first);
        std::memcpy(out + first, buffer_, length - first);
    }
    void read(uint8_t* out, size_t length) {
        peek(out, length);
        skip(length);
    }
    void skip(size_t length) {
        head_ = (head_ + length) % CapacityBytes;
        used_ -= length;
    }
    void dropHead() {
        uint8_t header[2];
        peek(header, 2);
        const size_t length = size_t(header[0]) | (size_t(header[1]) << 8);
        skip(kRecordHeaderBytes + length);
        --frames_;
    }
};
}  // namespace protocol
