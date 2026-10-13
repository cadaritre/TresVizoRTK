// Identidad de la unidad: serial, unit_name, nombre mDNS y anuncio BLE
// (docs/api-contract/receiver-identity.md).
#include "device_identity.h"
#include <cassert>
#include <cstdio>
#include <cstring>

int main() {
    using namespace device_identity;
    const uint8_t mac[kMacBytes] = {0x7c, 0xdf, 0xa1, 0x0b, 0xf1, 0xa2};
    Identity vi;
    assert(make(mac, "MeridianVI", 6, vi));
    // Los 4 bytes bajos de la MAC, en hex mayúsculas.
    assert(!std::strcmp(vi.serial, "A10BF1A2"));
    assert(!std::strcmp(vi.unitName, "MeridianVI-F1A2"));
    assert(!std::strcmp(vi.hostname, "meridianvi-f1a2"));
    assert(!std::strcmp(vi.model, "MeridianVI"));

    Identity v;
    assert(make(mac, "MeridianV", 5, v));
    assert(!std::strcmp(v.unitName, "MeridianV-F1A2") && !std::strcmp(v.serial, vi.serial));

    // Bloque de fabricante: 0xFFFF LE, 'T' 'V', versión 1, modelo, serial BE.
    uint8_t block[kManufacturerDataBytes];
    assert(manufacturerData(vi, block) == 10);
    const uint8_t expected[10] = {0xFF, 0xFF, 'T', 'V', 1, 6, 0xA1, 0x0B, 0xF1, 0xA2};
    assert(!std::memcmp(block, expected, sizeof(expected)));

    // Respuesta de escaneo: nombre completo (0x09) + fabricante (0xFF), dentro de 31 bytes.
    uint8_t scan[kAdvertisingPayloadBytes];
    const size_t viBytes = scanResponse(vi, vi.unitName, true, 9, scan);
    assert(viBytes == 2 + 15 + 2 + 10);          // 29: la potencia (3) no cabe
    assert(scan[0] == 16 && scan[1] == 0x09 && !std::memcmp(scan + 2, "MeridianVI-F1A2", 15));
    assert(scan[17] == 11 && scan[18] == 0xFF && !std::memcmp(scan + 19, expected, 10));
    // El MeridianV sigue anunciando «MeridianV» y sí le cabe la potencia.
    const size_t vBytes = scanResponse(v, "MeridianV", true, 9, scan);
    assert(vBytes == 2 + 9 + 2 + 10 + 3);
    assert(scan[0] == 10 && scan[1] == 0x09 && !std::memcmp(scan + 2, "MeridianV", 9));
    assert(scan[11] == 11 && scan[12] == 0xFF && scan[17] == 1 && scan[18] == 5);
    assert(scan[23] == 2 && scan[24] == 0x0A && scan[25] == 9);
    // Un nombre que no cabe con el bloque no produce una respuesta truncada.
    assert(scanResponse(v, "UnNombreDemasiadoLargoParaElAnuncio", false, 0, scan) == 0);

    // Modelo vacío o demasiado largo: identidad vacía, nunca un nombre a medias.
    Identity bad;
    assert(!make(mac, "", 6, bad) && !bad.serial[0]);
    assert(!make(mac, "ModeloDemasiadoLargo", 6, bad) && !bad.unitName[0]);
    std::puts("device_identity_test: OK");
    return 0;
}
