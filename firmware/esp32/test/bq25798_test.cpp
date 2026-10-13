// Cargador BQ25798 de la placa v0.3 contra un banco de registros simulado con
// los valores de encendido de la hoja (SLUSDV2C rev. C, §7.5). Comprueba que el
// firmware solo escribe lo que debe y que nunca deja la carga por encima de lo
// que admite el pack 1S2P Li-ion.
#include "bq25798.h"
#include <cassert>
#include <cstdio>
#include <cstring>
#include <set>

struct Chip {
    uint8_t reg[0x49] = {};
    bool msbFirst = true;      // orden de los registros de 16 bits en el bus
    bool vbus = false;
    size_t failAfter = SIZE_MAX, operations = 0;
    std::set<uint8_t> written;
    void set16(uint8_t at, uint16_t value) {
        reg[at] = msbFirst ? uint8_t(value >> 8) : uint8_t(value);
        reg[at + 1] = msbFirst ? uint8_t(value) : uint8_t(value >> 8);
    }
    uint16_t get16(uint8_t at) const {
        return msbFirst ? uint16_t((reg[at] << 8) | reg[at + 1]) : uint16_t(reg[at] | (reg[at + 1] << 8));
    }
    // Valores POR de 1S con PROG = 4.7 kΩ (tablas 7-1 y 7-2 y figuras del §7.5).
    explicit Chip(bool msb = true, uint16_t vregMv = 4200) : msbFirst(msb) {
        set16(0x01, uint16_t(vregMv / 10));
        set16(0x03, 100);          // ICHG 1 A
        reg[0x0F] = 0xA2;          // EN_AUTO_IBATDIS, EN_CHG, EN_TERM
        reg[0x10] = 0x85;          // WATCHDOG 40 s
        reg[0x11] = 0x40;          // AUTO_INDET_EN
        reg[0x14] = 0x16;          // EN_IINDPM, EN_EXTILIM, IBAT_REG
        reg[0x48] = 0x19;          // PN 011b (BQ25798), DEV_REV 001b
    }
    bool read(uint8_t at, uint8_t* data, size_t n) {
        if (++operations > failAfter || at + n > sizeof(reg)) return false;
        reg[0x1B] = vbus ? 0x09 : 0x00;   // VBUS_PRESENT y PG
        std::memcpy(data, reg + at, n);
        return true;
    }
    bool write(uint8_t at, const uint8_t* data, size_t n) {
        if (++operations > failAfter || at + n > sizeof(reg)) return false;
        for (size_t i = 0; i < n; ++i) {
            written.insert(uint8_t(at + i));
            // SDRV_CTRL queda en 00 sin SFET_PRESENT o con VBUS (REG14, §7.3.12).
            if (at + i == 0x11 && (!(reg[0x14] & 0x80) || vbus)) { reg[0x11] = data[i] & ~0x06; continue; }
            reg[at + i] = data[i];
        }
        return true;
    }
};

int main() {
    using namespace bq25798;
    // Encendido normal: los dos órdenes de bytes posibles dan lo mismo.
    for (bool msb : {true, false}) {
        Chip chip(msb);
        const Config c = configure(chip, 4200, 1000, 1500);
        assert(c.result == Setup::configured && c.vregMv == 4200 && c.ichgMa == 1000);
        assert(c.order == (msb ? ByteOrder::msbFirst : ByteOrder::lsbFirst));
        assert(chip.reg[0x14] == 0x96);                       // SFET_PRESENT + lo que había
        assert((chip.reg[0x10] & 0x07) == 0 && (chip.reg[0x10] & 0xF8) == 0x80);
        assert(chip.get16(0x03) == 100 && chip.get16(0x01) == 420);
        assert(chip.reg[0x0F] == 0xA2 && chip.reg[0x11] == 0x40);
        // Solo REG14, REG10 y REG03/04. Nunca VREG, IINDPM, CELL ni el resto.
        assert(chip.written == std::set<uint8_t>({0x03, 0x04, 0x10, 0x14}));
    }
    // ICHG pedido por encima del máximo se recorta (1.5 A, J102).
    {
        Chip chip;
        assert(configure(chip, 4200, 3000, 1500).ichgMa == 1500 && chip.get16(0x03) == 150);
    }
    // Otro chip en 0x6B: no se escribe nada.
    {
        Chip chip; chip.reg[0x48] = 0x09;   // PN 001b (BQ25792)
        assert(configure(chip, 4200, 1000, 1500).result == Setup::unexpected_part && chip.written.empty());
    }
    // VREG de 2S (PROG mal montado): la carga queda deshabilitada y el watchdog
    // apagado para que EN_CHG no vuelva a 1; ICHG y SFET_PRESENT no se tocan.
    {
        Chip chip(true, 8400);
        const Config c = configure(chip, 4200, 1000, 1500);
        assert(c.result == Setup::charge_disabled && c.order == ByteOrder::unknown);
        assert(!(chip.reg[0x0F] & 0x20) && (chip.reg[0x10] & 0x07) == 0);
        assert(chip.written == std::set<uint8_t>({0x0F, 0x10}));
    }
    // Sin respuesta del bus en cada operación posible: nunca «configured».
    for (size_t fail = 0; fail < 10; ++fail) {   // las 10 operaciones de configure
        Chip chip; chip.failAfter = fail;
        assert(configure(chip, 4200, 1000, 1500).result == Setup::bus_error);
    }
    // EN_EXTILIM borrado por alguien: vuelve a 1 (ILIM_HIZ sigue siendo el techo).
    {
        Chip chip; chip.reg[0x14] = 0x14;
        assert(configure(chip, 4200, 1000, 1500).result == Setup::configured && chip.reg[0x14] == 0x96);
    }
    // Lectura periódica: estado, y si ICHG aparece alto se corrige.
    {
        Chip chip; configure(chip, 4200, 1000, 1500);
        chip.vbus = true; chip.reg[0x1C] = 0x3 << 5; chip.reg[0x1D] = 0x01;
        Status s = poll(chip, ByteOrder::msbFirst, 1000, 1500);
        assert(s.valid && s.vbusPresent && s.powerGood && s.batteryPresent && s.sfetPresent && s.ichgMa == 1000);
        assert(charging(s.status1) && !std::strcmp(chargeState(s.status1), "fast_charge"));
        chip.set16(0x03, 200);       // 2 A: no debería estar así
        s = poll(chip, ByteOrder::msbFirst, 1000, 1500);
        assert(s.valid && s.ichgMa == 1000 && chip.get16(0x03) == 100);
        chip.reg[0x1C] = 0x7 << 5;   // terminada
        assert(!charging(poll(chip, ByteOrder::msbFirst, 1000, 1500).status1));
        assert(!charging(0) && charging(6 << 5) && !charging(5 << 5));
    }
    // Modo ship: con VBUS no se escribe; sin SFET_PRESENT no se puede; sin VBUS sí.
    {
        Chip chip;
        assert(enterShip(chip) == Ship::not_allowed && chip.reg[0x11] == 0x40);
        configure(chip, 4200, 1000, 1500);
        chip.vbus = true;
        assert(enterShip(chip) == Ship::vbus_present && chip.reg[0x11] == 0x40);
        chip.vbus = false;
        assert(enterShip(chip) == Ship::written && chip.reg[0x11] == 0x45);   // SDRV_CTRL 10, SDRV_DLY 1
        Chip dead; dead.failAfter = 0;
        assert(enterShip(dead) == Ship::bus_error);
    }
    // HIZ con un radio enlazado por USB (REG0F bit 2): solo toca ese bit y solo si cambia.
    {
        Chip chip; configure(chip, 4200, 1000, 1500);
        chip.written.clear();
        bool active = false;
        assert(setHiz(chip, true, active) && active && chip.reg[0x0F] == 0xA6);
        assert(chip.written == std::set<uint8_t>({0x0F}));
        chip.written.clear();
        assert(setHiz(chip, true, active) && active && chip.written.empty());   // ya estaba
        assert(setHiz(chip, false, active) && !active && chip.reg[0x0F] == 0xA2);
        // Con HIZ y VBUS el modo ship sigue sin poder entrar (§7.3.12).
        assert(setHiz(chip, true, active) && active);
        chip.vbus = true;
        assert(enterShip(chip) == Ship::vbus_present);
        Chip dead; dead.failAfter = 0;
        assert(!setHiz(dead, true, active));
    }
    // El orden de bytes solo se acepta si VREG da 4.2 V en exactamente uno de los dos.
    {
        const uint8_t msb[2] = {0x01, 0xA4}, lsb[2] = {0xA4, 0x01}, other[2] = {0x03, 0x48};
        assert(orderFromVreg(msb, 4200) == ByteOrder::msbFirst && orderFromVreg(lsb, 4200) == ByteOrder::lsbFirst);
        assert(orderFromVreg(other, 4200) == ByteOrder::unknown);
    }
    std::puts("bq25798_test: OK");
    return 0;
}
