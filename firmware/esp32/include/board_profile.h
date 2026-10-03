#pragma once

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
// Header A0 y A1: libres de UART, Qwiic, almacenamiento y straps.
constexpr int kPowerPush = 10, kPowerOff = 14;
}
