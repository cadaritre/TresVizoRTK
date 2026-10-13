#pragma once

// Un perfil por placa. El entorno de PlatformIO elige cuál con su macro:
//   esp32s3_usb   -> SparkFun Thing Plus ESP32-S3 + UM980 (este archivo, sin macro).
//   meridianv_v03 -> placa principal v0.3 compacta (-DTRESVIZO_BOARD_V03), en
//                    board_profile_v03.h.
// Las dos placas son el mismo producto, el MeridianV. Todo lo que depende de la
// placa (pines, identidad de imagen, capacidades que se informan a las apps)
// está en el perfil y en ningún otro sitio. Un pin a -1 = la placa no lo tiene.
#if defined(TRESVIZO_BOARD_V03)
#include "board_profile_v03.h"
#else

// SparkFun WRL-24408, esquema v1.0. Cableado: hardware/wiring.md.
// Identidad distinta de la Tiny aunque ambas tengan 4 MB / 2 MB.
#define TRESVIZO_HARDWARE_ID "tresvizo-thingplus-s3-4m-v1"
#define TRESVIZO_GNSS_RX 44
#define TRESVIZO_GNSS_TX 43
#define TRESVIZO_GNSS_BAUD 115200

namespace board_profile {
constexpr char kHardwareId[] = TRESVIZO_HARDWARE_ID;
constexpr char kName[] = "SparkFun Thing Plus ESP32-S3 WRL-24408";
constexpr int kSda = 8, kScl = 9;
constexpr int kPeripheralEnable = 45;
constexpr int kSdClock = 38, kSdCommand = 34;
constexpr int kSdD0 = 39, kSdD1 = 40, kSdD2 = 47, kSdD3 = 33;
constexpr int kSdDetect = 48;  // HIGH con tarjeta; INPUT_PULLDOWN.
constexpr bool kSdDetectActiveLow = false;
constexpr bool kSdDetectInternalPull = true;
// Header A0 y A1: libres de UART, Qwiic, almacenamiento y straps.
constexpr int kPowerPush = 10, kPowerOff = 14;
// La OLED va derecha y no hay LED de estado, IMU ni corte del GNSS por GPIO.
constexpr int kOledRotation = 0;            // en cuartos de vuelta (Adafruit GFX)
constexpr int kStatusLed = -1;
constexpr int kGnssPowerEnable = -1, kGnssPps = -1, kGnssReset = -1;
constexpr int kImuSda = -1, kImuScl = -1, kImuInt1 = -1, kImuInt3 = -1;
constexpr int kBatteryCapacityMah = 3000;   // LiPo 1S 3000 mAh (hardware/wiring.md)
constexpr float kLowBatteryVolts = 3.4f;

// Identidad del producto (docs/api-contract/receiver-identity.md). El MeridianV
// sigue anunciando «MeridianV» por BLE, Wi-Fi y mDNS: hay apps y radios en campo
// que lo buscan por ese nombre. `unit_name` se informa igualmente en la API.
constexpr char kModel[] = "MeridianV";
constexpr unsigned char kModelCode = 5;          // byte 5 de los datos de fabricante BLE
constexpr bool kPerUnitNetworkName = false;      // SSID, BLE y mDNS fijos: «MeridianV»
// Capacidades que se publican en /api/status → capabilities.
constexpr char kGnssModule[] = "UM980";
constexpr bool kLoraIntegrated = false;          // el radio, si hay, es el aparato aparte
constexpr const char* kImu = nullptr;            // sin IMU en esta placa
constexpr char kBatteryChemistry[] = "li-ion";   // LiPo 1S 3.7 V (hardware/wiring.md)
constexpr bool kRemovableStorage = true;         // microSD en zócalo con detección
constexpr const char* kIpRating = nullptr;       // sin clasificación declarada
}
#endif
