#pragma once
#include <cstddef>
#include <cstdint>

// Cargador TI BQ25798 de la placa v0.3 (U102). Sin Arduino: se prueba en la PC
// con un bus simulado (test/bq25798_test.cpp).
//
// Hoja: SLUSDV2C (rev. C, junio de 2026), §7.5 «Register Map». Lo que el
// firmware hace con él, y por qué, está en hardware/main-board/README.md
// («Valores de seguridad para el firmware») y en docs/board-v03-bringup.md:
//
// - Solo escribe tres cosas: SFET_PRESENT = 1 (la placa lleva el FET de envío
//   Q101), WATCHDOG = desactivado e ICHG = 1 A. Nunca VREG, IINDPM, CELL ni
//   EN_EXTILIM = 0. ICHG nunca pasa de 1.5 A.
// - Antes comprueba que es un BQ25798 (REG48) y que VREG es 4.2 V, el de 1S que
//   fija PROG (R103 4.7 kΩ, tabla 7-1). Si VREG no es 4.2 V, el pack Li-ion 1S2P
//   no se debe cargar con eso: deshabilita la carga (EN_CHG = 0) y no escribe más.
// - La hoja no dice en qué orden van los dos bytes de los registros de 16 bits
//   (REG01/02, REG03/04). El orden se deduce de VREG al arrancar: 4.2 V (420 en
//   pasos de 10 mV) solo se lee bien en uno de los dos órdenes. Si no se reconoce,
//   no se escribe ICHG.
// - Apagado: modo «ship» (REG11 SDRV_CTRL = 10, SDRV_DLY = 1), solo sin VBUS:
//   con adaptador el cargador ignora la orden (§7.3.12, REG11).
namespace bq25798 {
constexpr uint8_t kAddress = 0x6B;            // §7.3.14.5, figura 7-19
constexpr uint8_t kRegVreg = 0x01;            // REG01: VREG[10:0], 10 mV/bit (16 bits)
constexpr uint8_t kRegIchg = 0x03;            // REG03: ICHG[8:0], 10 mA/bit (16 bits)
constexpr uint8_t kRegControl0 = 0x0F;        // REG0F: bit 5 EN_CHG
constexpr uint8_t kRegControl1 = 0x10;        // REG10: [2:0] WATCHDOG (0 = desactivado)
constexpr uint8_t kRegControl2 = 0x11;        // REG11: [2:1] SDRV_CTRL, bit 0 SDRV_DLY
constexpr uint8_t kRegControl5 = 0x14;        // REG14: bit 7 SFET_PRESENT, bit 1 EN_EXTILIM
constexpr uint8_t kRegStatus0 = 0x1B;         // REG1B: bit 0 VBUS_PRESENT, bit 3 PG, bit 5 WD
constexpr uint8_t kRegStatus1 = 0x1C;         // REG1C: [7:5] CHG_STAT, [4:1] VBUS_STAT
constexpr uint8_t kRegStatus2 = 0x1D;         // REG1D: bit 0 VBAT_PRESENT, bit 2 TREG
constexpr uint8_t kRegFault0 = 0x20, kRegFault1 = 0x21;
constexpr uint8_t kRegPartInfo = 0x48;        // REG48: [5:3] PN = 011b (BQ25798)

constexpr uint8_t kEnChg = 0x20;
constexpr uint8_t kWatchdogMask = 0x07;
constexpr uint8_t kSdrvMask = 0x07;           // SDRV_CTRL[2:1] + SDRV_DLY
constexpr uint8_t kSdrvShipNow = (2u << 1) | 1u;
constexpr uint8_t kSfetPresent = 0x80, kEnExtIlim = 0x02;
constexpr uint8_t kPartBq25798 = 3;
constexpr unsigned kVregStepMv = 10, kIchgStepMa = 10;

enum class ByteOrder : uint8_t { unknown, msbFirst, lsbFirst };

inline uint16_t join(const uint8_t raw[2], ByteOrder order) {
    return order == ByteOrder::lsbFirst ? uint16_t(raw[0] | (raw[1] << 8)) : uint16_t((raw[0] << 8) | raw[1]);
}
inline void split(uint16_t value, ByteOrder order, uint8_t raw[2]) {
    const uint8_t high = uint8_t(value >> 8), low = uint8_t(value);
    raw[0] = order == ByteOrder::lsbFirst ? low : high;
    raw[1] = order == ByteOrder::lsbFirst ? high : low;
}
// El orden en que VREG da exactamente `expectedMv`, o unknown.
inline ByteOrder orderFromVreg(const uint8_t raw[2], unsigned expectedMv) {
    const unsigned want = expectedMv / kVregStepMv;
    const bool msb = (join(raw, ByteOrder::msbFirst) & 0x7FF) == want;
    const bool lsb = (join(raw, ByteOrder::lsbFirst) & 0x7FF) == want;
    if (msb == lsb) return ByteOrder::unknown;   // ninguno, o ambos (no se puede saber)
    return msb ? ByteOrder::msbFirst : ByteOrder::lsbFirst;
}

const char* const kChargeStates[8] = {"not_charging", "trickle", "pre_charge", "fast_charge",
                                      "taper_charge", "reserved", "top_off", "done"};
inline const char* chargeState(uint8_t status1) { return kChargeStates[(status1 >> 5) & 0x07]; }
// Corriente entrando a la celda: lenta, previa, rápida, final o de remate.
inline bool charging(uint8_t status1) {
    const uint8_t s = (status1 >> 5) & 0x07;
    return s >= 1 && s <= 4 ? true : s == 6;
}

enum class Setup : uint8_t {
    configured,          // SFET_PRESENT, watchdog fuera e ICHG = 1 A, comprobados
    bus_error,           // no contesta o falló una lectura/escritura
    unexpected_part,     // REG48 no dice BQ25798: no se escribe nada
    charge_disabled,     // VREG no es el de 1S Li-ion: carga deshabilitada
    readback_mismatch,   // se escribió y no se leyó lo esperado
};
inline const char* setupName(Setup s) {
    switch (s) {
    case Setup::configured: return "configured";
    case Setup::bus_error: return "bus_error";
    case Setup::unexpected_part: return "unexpected_part";
    case Setup::charge_disabled: return "charge_disabled_unexpected_vreg";
    case Setup::readback_mismatch: return "readback_mismatch";
    }
    return "bus_error";
}

// Bus: `bool read(uint8_t reg, uint8_t* data, size_t n)` y
// `bool write(uint8_t reg, const uint8_t* data, size_t n)`, con lecturas y
// escrituras de varios bytes seguidos (§7.3.14.7).
template<class Bus>
bool update(Bus& bus, uint8_t reg, uint8_t clear, uint8_t set) {
    uint8_t value = 0;
    if (!bus.read(reg, &value, 1)) return false;
    const uint8_t next = uint8_t((value & ~clear) | set);
    return next == value || bus.write(reg, &next, 1);
}

struct Config {
    Setup result = Setup::bus_error;
    ByteOrder order = ByteOrder::unknown;
    uint16_t vregMv = 0, ichgMa = 0;
};

template<class Bus>
Config configure(Bus& bus, unsigned vregMv, unsigned ichgMa, unsigned ichgMaxMa) {
    Config out;
    uint8_t part = 0, raw[2] = {};
    if (!bus.read(kRegPartInfo, &part, 1)) return out;
    if (((part >> 3) & 0x07) != kPartBq25798) { out.result = Setup::unexpected_part; return out; }
    if (!bus.read(kRegVreg, raw, 2)) return out;
    out.order = orderFromVreg(raw, vregMv);
    if (out.order == ByteOrder::unknown) {
        // EN_CHG lo restablece el watchdog (REG0F): primero se apaga el watchdog
        // para que la carga no vuelva sola a los 40 s.
        out.result = update(bus, kRegControl1, kWatchdogMask, 0) && update(bus, kRegControl0, kEnChg, 0)
            ? Setup::charge_disabled : Setup::bus_error;
        return out;
    }
    out.vregMv = uint16_t((join(raw, out.order) & 0x7FF) * kVregStepMv);
    if (ichgMa > ichgMaxMa) ichgMa = ichgMaxMa;
    // SFET_PRESENT habilita el modo ship (sin él SDRV_CTRL queda en 00, REG14) y
    // EN_EXTILIM = 1 deja ILIM_HIZ (~1.45 A) como techo de la entrada.
    if (!update(bus, kRegControl5, 0, kSfetPresent | kEnExtIlim)) return out;
    if (!update(bus, kRegControl1, kWatchdogMask, 0)) return out;
    uint8_t ichg[2];
    split(uint16_t(ichgMa / kIchgStepMa), out.order, ichg);
    if (!bus.write(kRegIchg, ichg, 2)) return out;
    uint8_t control5 = 0, control1 = 0;
    if (!bus.read(kRegControl5, &control5, 1) || !bus.read(kRegControl1, &control1, 1) || !bus.read(kRegIchg, raw, 2))
        return out;
    out.ichgMa = uint16_t((join(raw, out.order) & 0x1FF) * kIchgStepMa);
    const bool ok = (control5 & (kSfetPresent | kEnExtIlim)) == (kSfetPresent | kEnExtIlim) &&
                    (control1 & kWatchdogMask) == 0 && out.ichgMa == ichgMa;
    out.result = ok ? Setup::configured : Setup::readback_mismatch;
    return out;
}

struct Status {
    bool valid = false;
    bool vbusPresent = false, powerGood = false, batteryPresent = false, thermalRegulation = false;
    bool sfetPresent = false;
    uint8_t status0 = 0, status1 = 0, status2 = 0, fault0 = 0, fault1 = 0;
    uint16_t ichgMa = 0;
};

// Lectura periódica (1 s). Si ICHG aparece por encima del máximo (otro POR del
// cargador con el ESP32 vivo por USB, o una escritura ajena), vuelve a `ichgMa`.
template<class Bus>
Status poll(Bus& bus, ByteOrder order, unsigned ichgMa, unsigned ichgMaxMa) {
    Status s;
    uint8_t st[3] = {}, faults[2] = {}, control5 = 0;
    if (!bus.read(kRegStatus0, st, 3) || !bus.read(kRegFault0, faults, 2) || !bus.read(kRegControl5, &control5, 1)) return s;
    s.status0 = st[0]; s.status1 = st[1]; s.status2 = st[2];
    s.fault0 = faults[0]; s.fault1 = faults[1];
    s.vbusPresent = st[0] & 0x01; s.powerGood = st[0] & 0x08;
    s.batteryPresent = st[2] & 0x01; s.thermalRegulation = st[2] & 0x04;
    s.sfetPresent = control5 & kSfetPresent;
    if (order != ByteOrder::unknown) {
        uint8_t raw[2];
        if (!bus.read(kRegIchg, raw, 2)) return s;
        s.ichgMa = uint16_t((join(raw, order) & 0x1FF) * kIchgStepMa);
        if (s.ichgMa > ichgMaxMa) {
            if (ichgMa > ichgMaxMa) ichgMa = ichgMaxMa;
            split(uint16_t(ichgMa / kIchgStepMa), order, raw);
            if (!bus.write(kRegIchg, raw, 2)) return s;
            s.ichgMa = uint16_t(ichgMa);
        }
    }
    s.valid = true;
    return s;
}

enum class Ship : uint8_t { written, vbus_present, not_allowed, bus_error };
// Modo ship inmediato. Solo con SFET_PRESENT = 1 y sin VBUS; el llamador ya
// comprobó que el botón está suelto (si QON sigue en bajo, se despierta solo).
template<class Bus>
Ship enterShip(Bus& bus) {
    uint8_t status0 = 0, control5 = 0;
    if (!bus.read(kRegStatus0, &status0, 1) || !bus.read(kRegControl5, &control5, 1)) return Ship::bus_error;
    if (status0 & 0x01) return Ship::vbus_present;
    if (!(control5 & kSfetPresent)) return Ship::not_allowed;
    return update(bus, kRegControl2, kSdrvMask, kSdrvShipNow) ? Ship::written : Ship::bus_error;
}
}  // namespace bq25798
