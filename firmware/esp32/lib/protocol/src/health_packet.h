#pragma once
#include <cmath>
#include <cstdint>

namespace protocol {
// Paquete de salud (20 bytes, little-endian), el mismo por BLE (a04c0006) y por
// el WebSocket (trama 0x02). Vive aqui, sin Arduino, para que los dos
// transportes lo codifiquen igual y se pueda probar en la PC
// (test/health_packet_test.cpp). Offsets en docs/ble-protocol.md.
//
// **Dos precisiones distintas, que no se mezclan:**
//
// - Cruda del UM980 (`um980Raw...`): la sigma de GST tal como llega, en mm.
//   No se modifica ni se descarta; va en los bytes 12-15 y en `/api/status`.
// - Mostrada por Meridian V (`meridianDisplay...`): una metrica de producto
//   que decidio el propietario el 27-09-2026. Va en los bytes 1-4, que son los
//   que la app pinta como precision. **No es una sigma del receptor.**

constexpr uint16_t kUnknownMm = 0xFFFF;

// Regla del propietario, en milimetros:
//   exceso = max(0, UM980 - 35); horizontal = 10 + exceso; vertical = 15 + exceso.
constexpr uint32_t kDisplayThresholdMm = 35;
constexpr uint32_t kDisplayBaseHorizontalMm = 10;
constexpr uint32_t kDisplayBaseVerticalMm = 15;

struct DisplayPrecisionMm {
    uint16_t horizontal;
    uint16_t vertical;
};

// Sin valor del UM980 no hay precision mostrada: 0xFFFF en las dos, igual que
// «el receptor no la estima». Satura en 65534 para no confundirse con 0xFFFF.
inline DisplayPrecisionMm meridianDisplayPrecision(uint16_t um980PrecisionMm) {
    if (um980PrecisionMm == kUnknownMm) return {kUnknownMm, kUnknownMm};
    const uint32_t excess = um980PrecisionMm > kDisplayThresholdMm ? um980PrecisionMm - kDisplayThresholdMm : 0;
    const auto clamp = [](uint32_t mm) -> uint16_t { return mm > 65534u ? uint16_t(65534u) : uint16_t(mm); };
    return {clamp(kDisplayBaseHorizontalMm + excess), clamp(kDisplayBaseVerticalMm + excess)};
}

// **El exceso lo gobierna la sigma horizontal cruda del UM980** (peor eje,
// max(sigma N, sigma E)), por decision del propietario el 27-09-2026. La
// vertical cruda no interviene en la precision mostrada: se conserva aparte.
inline DisplayPrecisionMm meridianDisplayFromRaw(uint16_t um980RawHorizontalSigmaMm) {
    return meridianDisplayPrecision(um980RawHorizontalSigmaMm);
}

// La horizontal cruda que se usa en todo el equipo: el peor de norte y este. Sin
// los dos ejes, la combinada de GST. Es la misma regla que tenian BLE, WebSocket
// y el panel desde 0.7.5.
inline double um980WorstAxisHorizontalSigmaM(double north, double east, double combined) {
    return std::isfinite(north) && std::isfinite(east) ? (north > east ? north : east) : combined;
}

// Metros de GST a milimetros, con la regla que ya usaba la telemetria:
// 0xFFFF si no es finita, es negativa o pasa de 65 m.
inline uint16_t sigmaToMm(double metres) {
    if (!std::isfinite(metres) || metres < 0 || metres > 65.0) return kUnknownMm;
    return uint16_t(std::lround(metres * 1000));
}

// Byte 16: que traen los bytes 1-4 y 12-15. El firmware anterior deja 0 aqui,
// y entonces los bytes 1-4 son la sigma cruda (hasta 0.7.7).
constexpr uint8_t kFlagDisplayPrecision = 0x01;  // bytes 1-4 = precision mostrada por Meridian V
constexpr uint8_t kFlagRawPrecision = 0x02;      // bytes 12-15 = sigma cruda del UM980
// Desde 0.7.11: bytes 17-19 = contadores de RTCM del equipo. Sin la bandera,
// esos bytes son 0 y no significan nada (firmware anterior).
constexpr uint8_t kFlagRtcmCounters = 0x04;

// Ocupacion de la cola de correcciones hacia el UM980, en por ciento, para el
// byte 19. Redondea hacia arriba: una cola con algo dentro nunca dice 0. Sin
// cola (UART sin configurar) no hay cifra: 255.
constexpr uint8_t kUnknownPercent = 255;
inline uint8_t queuePercent(uint32_t usedBytes, uint32_t capacityBytes) {
    if (!capacityBytes) return kUnknownPercent;
    const uint64_t percent = (uint64_t(usedBytes) * 100 + capacityBytes - 1) / capacityBytes;
    return uint8_t(percent > 100 ? 100 : percent);
}

struct HealthInputs {
    uint16_t um980RawHorizontalSigmaMm = kUnknownMm;  // peor eje, max(sigma N, sigma E)
    uint16_t um980RawVerticalSigmaMm = kUnknownMm;
    DisplayPrecisionMm meridianDisplay = {kUnknownMm, kUnknownMm};
    uint16_t correctionAgeSeconds = kUnknownMm;       // 0xFFFF = sin fuente
    uint8_t source = 0;
    uint8_t quality = 0;
    uint8_t tracked = 255;                            // 255 = sin GSV reciente
    uint8_t visible = 255;                            // 255 = desconocido (sin orbitas o sin posicion)
    // Contadores de RTCM (bytes 17-19), para que el telefono sepa si las
    // correcciones que manda llegan al receptor sin tener que pedir el estado.
    // Los dos primeros son **contadores que dan la vuelta a 256**: la app mira
    // la diferencia entre dos paquetes, no el valor. A 1 Hz y con menos de diez
    // tramas por segundo no pueden dar la vuelta entre dos paquetes.
    bool hasRtcmCounters = false;
    uint8_t rtcmFramesDiscarded = 0;   // desalojadas o caducadas camino del UM980
    uint8_t rtcmFramesRejected = 0;    // descartadas por CRC o formato al llegar
    uint8_t rtcmQueuePercent = kUnknownPercent;
};

inline void put16(uint8_t* target, uint16_t value) {
    target[0] = uint8_t(value);
    target[1] = uint8_t(value >> 8);
}

inline void encodeHealth(uint8_t report[20], const HealthInputs& in) {
    for (unsigned i = 0; i < 20; ++i) report[i] = 0;
    report[0] = 1;  // version del paquete: se mantiene, los campos nuevos van en bytes libres
    put16(report + 1, in.meridianDisplay.horizontal);
    put16(report + 3, in.meridianDisplay.vertical);
    put16(report + 5, in.correctionAgeSeconds);
    report[7] = in.source;
    report[8] = in.quality;
    report[9] = 0;  // IMU: reservado
    report[10] = in.tracked;
    report[11] = in.visible;  // satelites VISIBLES, calculados en el ESP32 (gnss_visible.cpp)
    put16(report + 12, in.um980RawHorizontalSigmaMm);
    put16(report + 14, in.um980RawVerticalSigmaMm);
    report[16] = kFlagDisplayPrecision | kFlagRawPrecision;
    if (in.hasRtcmCounters) {
        report[16] |= kFlagRtcmCounters;
        report[17] = in.rtcmFramesDiscarded;
        report[18] = in.rtcmFramesRejected;
        report[19] = in.rtcmQueuePercent;
    }
}
}  // namespace protocol
