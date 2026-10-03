#pragma once
#include <cstddef>
#include <cstdint>
#include <cstring>

namespace radio_air {
// Lo que viaja por el aire entre el radio de la base y el del rover
// (docs/radio/RADIO_MODULE.md). Sin Arduino: se prueba con g++.
//
// **Modulación.** LoRa, SF7, 500 kHz, CR 4/5: ≈21.9 kbit/s brutos. Un paquete de
// 255 bytes ocupa el aire ≈100 ms, así que caben ≈2.5 kB/s; un RTCM MSM4 de cuatro
// constelaciones a 1 Hz son 1–1.5 kB/s. MSM7 no cabe: la base de radio va en MSM4.
// 500 kHz es además el ancho que la norma de 902–928 MHz trata como modulación
// digital (la que admite hasta 1 W); confirmarlo con la norma del IFT antes de vender.
constexpr uint32_t kBandwidthHz = 500000;
constexpr uint8_t kSpreadingFactor = 7;
constexpr uint8_t kCodingRateDenominator = 5;   // 4/5
constexpr uint16_t kPreambleSymbols = 8;
// Palabra de sincronía de red privada del SX126x: no la de LoRaWAN pública.
constexpr uint16_t kSyncWord = 0x1424;

// **Canales.** 13 canales de 903 a 927 MHz, separados 2 MHz (más que el ancho de
// 500 kHz). Base y rover tienen que estar en el mismo canal y la misma red.
constexpr uint32_t kFirstChannelHz = 903000000;
constexpr uint32_t kChannelSpacingHz = 2000000;
constexpr uint8_t kChannelCount = 13;
constexpr uint8_t kDefaultChannel = 6;          // 915 MHz
inline uint32_t channelHz(uint8_t channel) {
    return kFirstChannelHz + uint32_t(channel < kChannelCount ? channel : kDefaultChannel) * kChannelSpacingHz;
}

// **Potencia.** La E22-900M30S lleva un amplificador detrás del SX1262: con el
// SX1262 a +22 dBm entrega ≈30 dBm (1 W). Ganancia nominal del fabricante, por
// confirmar midiendo cada lote.
constexpr int8_t kAmplifierGainDb = 8;
constexpr int8_t kMaxChipDbm = 22;
constexpr int8_t kMinChipDbm = -9;
constexpr int8_t kMaxOutputDbm = kMaxChipDbm + kAmplifierGainDb;   // 30
constexpr int8_t kDefaultOutputDbm = kMaxOutputDbm;
inline int8_t chipDbmFor(int outputDbm) {
    int chip = outputDbm - kAmplifierGainDb;
    if (chip > kMaxChipDbm) chip = kMaxChipDbm;
    if (chip < kMinChipDbm) chip = kMinChipDbm;
    return static_cast<int8_t>(chip);
}

// **Paquete.** Cabecera de 4 bytes y un trozo del flujo RTCM:
//   [0] 0xA7 (versión 1 del formato)  [1] red (0–255)  [2..3] secuencia (LE)
// El RTCM viaja como flujo de bytes: el rover concatena en orden y su parser RTCM3
// (con CRC-24Q) saca las tramas. Un paquete perdido solo estropea las tramas que
// lo cruzaban, que el CRC rechaza; al ver un salto de secuencia se reinicia el
// parser para no esperar una trama que ya no se puede completar.
constexpr uint8_t kMarker = 0xA7;
constexpr size_t kHeaderBytes = 4;
constexpr size_t kMaxPacketBytes = 255;         // máximo del SX1262
constexpr size_t kMaxChunkBytes = kMaxPacketBytes - kHeaderBytes;
constexpr uint8_t kDefaultNetwork = 1;

// Cuánto espera la base después del último byte antes de mandar un paquete a
// medio llenar: el receptor manda las tramas de una época de golpe, y esperar un
// poco junta varias en un paquete (menos cabeceras y preámbulos en el aire).
constexpr uint32_t kFlushIdleMs = 25;

inline size_t writeHeader(uint8_t* packet, uint8_t network, uint16_t sequence) {
    packet[0] = kMarker;
    packet[1] = network;
    packet[2] = static_cast<uint8_t>(sequence & 0xff);
    packet[3] = static_cast<uint8_t>(sequence >> 8);
    return kHeaderBytes;
}

// Base: junta bytes de RTCM y entrega paquetes listos para transmitir.
class Packetizer {
    uint8_t packet[kMaxPacketBytes] = {};
    size_t filled = kHeaderBytes;
    uint16_t sequence = 0;
    uint32_t lastByteMs = 0;
public:
    uint8_t network = kDefaultNetwork;
    bool empty() const { return filled == kHeaderBytes; }
    // Añade bytes; cada vez que se llena un paquete lo entrega a `send`.
    template <class Send> void add(const uint8_t* data, size_t length, uint32_t nowMs, Send send) {
        lastByteMs = nowMs;
        while (length) {
            const size_t room = kMaxPacketBytes - filled;
            const size_t take = length < room ? length : room;
            std::memcpy(packet + filled, data, take);
            filled += take; data += take; length -= take;
            if (filled == kMaxPacketBytes) flush(send);
        }
    }
    // Manda lo que haya si pasó `kFlushIdleMs` sin bytes nuevos.
    template <class Send> void tick(uint32_t nowMs, Send send) {
        if (!empty() && nowMs - lastByteMs >= kFlushIdleMs) flush(send);
    }
    template <class Send> void flush(Send send) {
        if (empty()) return;
        writeHeader(packet, network, sequence++);
        send(packet, filled);
        filled = kHeaderBytes;
    }
};

// Rover: valida paquetes, detecta pérdidas y devuelve el trozo de RTCM.
class Receiver {
    bool started = false;
    uint16_t expected = 0;
public:
    uint8_t network = kDefaultNetwork;
    uint32_t accepted = 0, foreign = 0, malformed = 0, lost = 0;
    void reset() { started = false; }
    // Devuelve el trozo útil (puntero dentro de `packet`) o nullptr si el paquete no
    // es de esta red. `gap` dice si se perdieron paquetes antes de este: quien lo
    // usa reinicia su parser RTCM antes de darle el trozo.
    const uint8_t* accept(const uint8_t* packet, size_t length, size_t& chunkLength, bool& gap) {
        chunkLength = 0; gap = false;
        if (length <= kHeaderBytes || length > kMaxPacketBytes || packet[0] != kMarker) { ++malformed; return nullptr; }
        if (packet[1] != network) { ++foreign; return nullptr; }
        const uint16_t sequence = packet[2] | (static_cast<uint16_t>(packet[3]) << 8);
        if (started && sequence != expected) {
            gap = true;
            lost += static_cast<uint16_t>(sequence - expected);
        }
        started = true;
        expected = static_cast<uint16_t>(sequence + 1);
        ++accepted;
        chunkLength = length - kHeaderBytes;
        return packet + kHeaderBytes;
    }
};
}  // namespace radio_air
