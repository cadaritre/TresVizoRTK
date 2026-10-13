#pragma once
#include <cstddef>
#include <cstdint>
#include <cstdio>
#include <cstring>

// Identidad de la unidad (docs/api-contract/receiver-identity.md). Sin Arduino:
// se prueba en la PC (test/device_identity_test.cpp).
//
// - `serial`: los 4 bytes bajos de la MAC base de fábrica (eFuse), en 8 hex
//   mayúsculas. No cambia al reflashear ni al borrar la NVS.
// - `unit_name`: modelo + guion + los 4 últimos hex del serial
//   («MeridianVI-F1A2»). Es lo que anuncia el MeridianVI por BLE, Wi-Fi y OLED.
// - `hostname`: `unit_name` en minúsculas («meridianvi-f1a2»), para mDNS.
// - Datos de fabricante del anuncio BLE: 10 bytes (12 con la cabecera AD).
namespace device_identity {
constexpr size_t kMacBytes = 6;
constexpr size_t kSerialChars = 8;
constexpr size_t kMaxModelChars = 15;
constexpr size_t kNameBytes = kMaxModelChars + 1 + 4 + 1;  // modelo-XXXX\0
constexpr size_t kManufacturerDataBytes = 10;
// Identificador de compañía 0xFFFF: el reservado para pruebas por el Bluetooth
// SIG. Va en little-endian, como todo identificador de compañía.
constexpr uint16_t kCompanyId = 0xFFFF;
constexpr uint8_t kBlockVersion = 1;

struct Identity {
    char model[kMaxModelChars + 1] = {};
    char serial[kSerialChars + 1] = {};
    char unitName[kNameBytes] = {};
    char hostname[kNameBytes] = {};
    uint8_t serialBytes[4] = {};
    uint8_t modelCode = 0;
};

// Falso si el modelo no cabe o está vacío; entonces `out` queda vacía.
inline bool make(const uint8_t mac[kMacBytes], const char* model, uint8_t modelCode, Identity& out) {
    out = Identity();
    if (!mac || !model) return false;
    const size_t length = std::strlen(model);
    if (!length || length > kMaxModelChars) return false;
    std::memcpy(out.model, model, length);
    for (size_t i = 0; i < 4; ++i) out.serialBytes[i] = mac[2 + i];
    std::snprintf(out.serial, sizeof(out.serial), "%02X%02X%02X%02X",
                  out.serialBytes[0], out.serialBytes[1], out.serialBytes[2], out.serialBytes[3]);
    std::snprintf(out.unitName, sizeof(out.unitName), "%s-%s", model, out.serial + 4);
    for (size_t i = 0; out.unitName[i]; ++i) {
        const char c = out.unitName[i];
        out.hostname[i] = (c >= 'A' && c <= 'Z') ? char(c - 'A' + 'a') : c;
    }
    out.modelCode = modelCode;
    return true;
}

// Bloque de datos de fabricante, sin la cabecera AD (longitud y tipo 0xFF):
//   0–1 compañía 0xFFFF (LE) · 2–3 'T' 'V' · 4 versión 1 · 5 modelo · 6–9 serial (BE)
inline size_t manufacturerData(const Identity& identity, uint8_t out[kManufacturerDataBytes]) {
    out[0] = uint8_t(kCompanyId & 0xff);
    out[1] = uint8_t(kCompanyId >> 8);
    out[2] = 'T';
    out[3] = 'V';
    out[4] = kBlockVersion;
    out[5] = identity.modelCode;
    for (size_t i = 0; i < 4; ++i) out[6 + i] = identity.serialBytes[i];
    return kManufacturerDataBytes;
}

// Respuesta de escaneo BLE: nombre local completo (AD 0x09) y datos de
// fabricante (AD 0xFF); la potencia de emisión (AD 0x0A) solo si cabe en los
// 31 bytes. Devuelve los bytes escritos o 0 si el nombre no cabe con el bloque.
constexpr size_t kAdvertisingPayloadBytes = 31;
inline size_t scanResponse(const Identity& identity, const char* localName, bool withTxPower, int8_t txPowerDbm,
                           uint8_t out[kAdvertisingPayloadBytes]) {
    if (!localName) return 0;
    const size_t name = std::strlen(localName);
    const size_t needed = 2 + name + 2 + kManufacturerDataBytes;
    if (!name || needed > kAdvertisingPayloadBytes) return 0;
    size_t n = 0;
    out[n++] = uint8_t(name + 1);
    out[n++] = 0x09;
    std::memcpy(out + n, localName, name);
    n += name;
    out[n++] = uint8_t(kManufacturerDataBytes + 1);
    out[n++] = 0xFF;
    n += manufacturerData(identity, out + n);
    if (withTxPower && n + 3 <= kAdvertisingPayloadBytes) {
        out[n++] = 2;
        out[n++] = 0x0A;
        out[n++] = uint8_t(txPowerDbm);
    }
    return n;
}
}  // namespace device_identity
