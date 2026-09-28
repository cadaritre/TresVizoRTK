#pragma once
#include <cstdint>

namespace firmware_signing {
// Clave **publica** con la que el equipo comprueba, antes de instalar, que un
// firmware recibido por OTA lo firmo el propietario (desde 0.7.13; formato en
// `lib/protocol/src/signed_firmware.h`).
//
// ECDSA P-256 (secp256r1). Punto sin comprimir: 0x04 || X || Y, 65 bytes, que
// es lo que lee `mbedtls_ecp_point_read_binary`. Es la misma clave que este PEM:
//
//   -----BEGIN PUBLIC KEY-----
//   MFkwEwYHKoZIzj0CAQYIKoZIzj0DAQcDQgAESX/VPbd8UNbNR0dcWAhTF9viTFrd
//   vx6o2R7wTlub9ejHP89yNxkysKAqxVZlZ3CymXv2XKTRvh3x+0LjXvP5Nw==
//   -----END PUBLIC KEY-----
//
// La clave **privada** no esta en el repositorio ni debe estarlo: vive en la
// Mac del propietario, en `~/.tresvizo/firmware-signing/private.pem` (o donde
// diga `TRESVIZO_SIGNING_KEY`), y la usa `tools/firmware_signing/`. Si se
// pierde, ningun equipo en campo acepta ya firmware por OTA: queda el cable USB.
//
// `tools/firmware_signing/sign_firmware.py --verify` lee estos 65 bytes de este
// archivo: verifica con lo mismo que verificara el equipo. Cambiar de clave es
// cambiar este arreglo, y un equipo solo aprende la clave nueva al instalar,
// firmado con la vieja, un firmware que ya la trae.
constexpr uint8_t kPublicKey[65] = {
    0x04,
    0x49, 0x7f, 0xd5, 0x3d, 0xb7, 0x7c, 0x50, 0xd6, 0xcd, 0x47, 0x47, 0x5c, 0x58, 0x08, 0x53, 0x17,
    0xdb, 0xe2, 0x4c, 0x5a, 0xdd, 0xbf, 0x1e, 0xa8, 0xd9, 0x1e, 0xf0, 0x4e, 0x5b, 0x9b, 0xf5, 0xe8,
    0xc7, 0x3f, 0xcf, 0x72, 0x37, 0x19, 0x32, 0xb0, 0xa0, 0x2a, 0xc5, 0x56, 0x65, 0x67, 0x70, 0xb2,
    0x99, 0x7b, 0xf6, 0x5c, 0xa4, 0xd1, 0xbe, 0x1d, 0xf1, 0xfb, 0x42, 0xe3, 0x5e, 0xf3, 0xf9, 0x37,
};
}  // namespace firmware_signing
