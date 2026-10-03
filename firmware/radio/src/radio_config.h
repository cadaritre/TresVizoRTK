#pragma once
#include <Arduino.h>
#include <ArduinoJson.h>
#include "radio_air.h"

// Ajustes del módulo de radio, guardados en su NVS. Los pone la app por Bluetooth
// (red Wi-Fi y contraseña del MeridianV) y, ya unido, el MeridianV por su API
// (red, canal y potencia).
namespace radio_config {
constexpr const char* kVersion = "0.1.0";
// Identidad de la imagen: con ella el cargador por USB (tools/flasher/) sabe que un
// .bin es del módulo de radio y no de un MeridianV.
constexpr const char* kHardwareId = "tresvizo-radio-e22-esp32s3-v1";
// Lo de fábrica del MeridianV (su red propia). Si el propietario cambia la contraseña
// del MeridianV, la app se la vuelve a pasar al radio por Bluetooth.
constexpr const char* kDefaultSsid = "MeridianV";
constexpr const char* kDefaultPassword = "TresVIzoRTK";
constexpr size_t kMaxSsidBytes = 32;
constexpr size_t kMinPasswordBytes = 8;
constexpr size_t kMaxPasswordBytes = 63;

struct Settings {
    String wifiSsid = kDefaultSsid;
    String wifiPassword = kDefaultPassword;
    uint8_t network = radio_air::kDefaultNetwork;
    uint8_t channel = radio_air::kDefaultChannel;
    int8_t powerDbm = radio_air::kDefaultOutputDbm;
};

Settings load();
bool save(const Settings& settings);

// Aplica lo que traiga `body` (solo las claves conocidas y válidas) sobre `settings`.
// Devuelve false y deja `error` si algo no vale; entonces no cambia nada.
bool apply(JsonVariantConst body, Settings& settings, String& error, bool allowWifi);
}  // namespace radio_config
