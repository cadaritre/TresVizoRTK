#pragma once
#include <cstddef>
#include <cstdint>

// SSD1306 128x64 I2C: comandos del fabricante, tablas 9-1 y 9-3.
// Bus sigue la interfaz de TwoWire. No se anuncia un cuadro completo si algún
// bloque falla; el llamador reinicializa y reenvía desde la columna/página 0.
namespace oled_transport {
constexpr size_t kWidth = 128, kHeight = 64, kBufferBytes = kWidth * kHeight / 8;
template<class Bus>
bool packet(Bus& bus, uint8_t address, uint8_t control, const uint8_t* data, size_t size) {
    bus.beginTransmission(address);
    const bool complete = bus.write(control) == 1 && bus.write(data, size) == size;
    const auto result = bus.endTransmission(); // STOP también tras una escritura corta.
    return complete && result == 0;
}
template<class Bus>
bool off(Bus& bus, uint8_t address) {
    const uint8_t command = 0xae;
    return packet(bus, address, 0x00, &command, 1);
}
template<class Bus>
bool initialize(Bus& bus, uint8_t address) {
    // Un reinicio puede interrumpir los parámetros de un comando. Consumir
    // hasta 6 parámetros pendientes antes de emitir una inicialización nueva.
    const uint8_t sync[] = {0xe3,0xe3,0xe3,0xe3,0xe3,0xe3,0xe3,0xe3};
    const uint8_t commands[] = {
        0xae,       // Apagada hasta recibir los 1024 bytes del primer cuadro.
        0xd5,0x80, 0xa8,0x3f, 0xd3,0x00, 0x40,
        0x8d,0x14, 0x20,0x00, 0xa1,0xc8, 0xda,0x12,
        0x81,0xcf, 0xd9,0xf1, 0xdb,0x40, 0xa4,0xa6,0x2e
    };
    return packet(bus,address,0x00,sync,sizeof(sync)) &&
           packet(bus,address,0x00,commands,sizeof(commands));
}
template<class Bus>
bool frame(Bus& bus, uint8_t address, const uint8_t* bitmap, bool turnOn) {
    if (!bitmap) return false;
    // Restablecer modo y ventana completa, incluso después de un cuadro fallido.
    const uint8_t window[] = {0x20,0x00,0x21,0,127,0x22,0,7};
    if (!packet(bus,address,0x00,window,sizeof(window))) return false;
    // GFXcanvas1 guarda filas horizontales; SSD1306 recibe columnas de 8 píxeles.
    // 16 bytes + control caben también en un bus con buffer de sólo 32 bytes.
    uint8_t data[16];
    for (size_t page = 0; page < 8; ++page) {
        for (size_t x = 0; x < kWidth; x += sizeof(data)) {
            for (size_t column = 0; column < sizeof(data); ++column) {
                const size_t cx = x + column;
                uint8_t value = 0;
                for (size_t bit = 0; bit < 8; ++bit)
                    if (bitmap[(page * 8 + bit) * (kWidth / 8) + cx / 8] & (0x80 >> (cx % 8)))
                        value |= uint8_t(1 << bit);
                data[column] = value;
            }
            if (!packet(bus,address,0x40,data,sizeof(data))) return false;
        }
    }
    const uint8_t on = 0xaf;
    return !turnOn || packet(bus,address,0x00,&on,1);
}
}
