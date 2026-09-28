#include "ble_address.h"
#include <cassert>
#include <cstdio>
#include <cstring>

using protocol::advertisedAddress;
using protocol::kBleAddressBytes;

static bool isStaticRandom(const uint8_t address[kBleAddressBytes]) {
    return (address[0] & 0xC0) == 0xC0;
}

int main() {
    // Direccion Bluetooth publica de un ESP32-S3 real (fabricante Espressif).
    const uint8_t chip[kBleAddressBytes] = {0xDC, 0xDA, 0x0C, 0x21, 0x4F, 0x9A};
    uint8_t first[kBleAddressBytes], second[kBleAddressBytes];

    // Aleatoria estatica, con la parte propia del chip intacta.
    advertisedAddress(chip, 1, first);
    assert(isStaticRandom(first));
    assert(std::memcmp(first + 1, chip + 1, kBleAddressBytes - 1) == 0);

    // Determinista: el mismo equipo con la misma tabla, siempre la misma.
    advertisedAddress(chip, 1, second);
    assert(std::memcmp(first, second, kBleAddressBytes) == 0);

    // Otra tabla, otra direccion: el telefono lo ve como equipo nuevo.
    for (uint8_t generation = 2; generation < 64; ++generation) {
        advertisedAddress(chip, generation, second);
        assert(isStaticRandom(second));
        assert(std::memcmp(first, second, kBleAddressBytes) != 0);
    }

    // Dos equipos con la parte propia distinta nunca chocan, sea cual sea su
    // generacion (ESP32 de un mismo lote tienen direcciones consecutivas).
    const uint8_t neighbour[kBleAddressBytes] = {0xDC, 0xDA, 0x0C, 0x21, 0x4F, 0x9B};
    for (uint8_t a = 1; a < 64; ++a) {
        for (uint8_t b = 1; b < 64; ++b) {
            advertisedAddress(chip, a, first);
            advertisedAddress(neighbour, b, second);
            assert(std::memcmp(first, second, kBleAddressBytes) != 0);
        }
    }

    // Nunca la parte aleatoria toda a unos ni toda a ceros.
    const uint8_t ones[kBleAddressBytes] = {0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF};
    advertisedAddress(ones, 0, first);
    assert(isStaticRandom(first));
    bool allOnes = (first[0] & 0x3F) == 0x3F;
    for (size_t i = 1; i < kBleAddressBytes; ++i) allOnes = allOnes && first[i] == 0xFF;
    assert(!allOnes);
    const uint8_t zeros[kBleAddressBytes] = {0xC0, 0x00, 0x00, 0x00, 0x00, 0x00};
    advertisedAddress(zeros, 0, first);
    bool allZeros = (first[0] & 0x3F) == 0;
    for (size_t i = 1; i < kBleAddressBytes; ++i) allZeros = allZeros && first[i] == 0x00;
    assert(!allZeros);

    std::puts("ble_address_test: OK");
    return 0;
}
