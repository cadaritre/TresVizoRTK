#pragma once
#include <Arduino.h>
#include <ArduinoJson.h>
#include "radio_air.h"

// Ajustes del módulo de radio, guardados en su NVS. Los cambia el MeridianV por el
// enlace USB (trama `config`), que a su vez los recibe de las apps por /api/radio.
namespace radio_config {
// Versión e identidad de la imagen: macros porque también van, en tiempo de
// compilación, a la identidad de la imagen (main.cpp) que lee el cargador por USB.
// 0.2.0: enlace por el USB-C del MeridianV (docs/radio/USB_LINK.md), sin Wi-Fi ni Bluetooth.
#define RADIO_VERSION "0.2.0"
#define RADIO_HARDWARE_ID "tresvizo-radio-e22-esp32s3-v1"
constexpr const char* kVersion = RADIO_VERSION;
constexpr const char* kHardwareId = RADIO_HARDWARE_ID;

// **Tope de potencia: 27 dBm** a la salida de la E22, por omisión y como máximo. La
// IFT-008-2015 (§4.3, modulación digital en 902–928 MHz) limita la densidad a 8 dBm en
// 3 kHz: 30 dBm repartidos en ~500 kHz dan ≈7.8 dBm/3 kHz, sin margen para la
// tolerancia de +1 dB del amplificador; 27 dBm dejan 3 dB (MeridianVI, research/spec.md
// §11.1). Tampoco puede haber controles que pasen el límite (§4.1.5): un valor mayor que
// llegue por el enlace se recorta aquí y se avisa (`power_limited`), nunca se aplica.
constexpr int8_t kMaxOutputDbm = 27;
constexpr int8_t kDefaultOutputDbm = kMaxOutputDbm;
static_assert(kMaxOutputDbm <= radio_air::kMaxOutputDbm, "el tope legal no puede pasar del de la E22");

struct Settings {
    uint8_t network = radio_air::kDefaultNetwork;
    uint8_t channel = radio_air::kDefaultChannel;
    int8_t powerDbm = kDefaultOutputDbm;
};

// Lee los ajustes (y borra la red y la contraseña Wi-Fi que guardaba la 0.1.0).
Settings load();
bool save(const Settings& settings);

// Aplica lo que traiga `body` sobre `settings`: `network` (0–255), `channel` (0–12) y
// `power_dbm` (0–30; lo que pase de 27 se recorta y deja `powerLimited`). `seq` se
// ignora (es del enlace). Cualquier otra clave o un valor fuera de rango: false con
// `error`, y no cambia nada.
bool apply(JsonVariantConst body, Settings& settings, String& error, bool& powerLimited);
}  // namespace radio_config
