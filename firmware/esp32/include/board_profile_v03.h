#pragma once

// MeridianV, placa principal v0.3 compacta (hardware/main-board, pedido a JLCPCB
// en el commit 97000ef). ESP32-S3-WROOM-1-N16R2 soldado: 16 MB de flash quad y
// 2 MB de PSRAM quad, así que GPIO33-37 quedan libres (los usaría una PSRAM octal).
//
// **Fuente de verdad: el netlist de esa placa** (hardware/main-board/kicad/
// tresvizo-main.net, idéntico al que exporta kicad-cli del esquema de 97000ef).
// Cada pin lleva su red y el pin del módulo U201. `tools/board_check/
// check_v03_pins.py` compara este archivo con el netlist y falla si algo no
// coincide: si la placa cambia, se cambia aquí y se vuelve a correr.
// Hojas: Espressif ESP32-S3-WROOM-1 v1.8 (tabla 3-1, pines del módulo), TI
// BQ25798 SLUSDV2C (rev. C, junio 2026), Bosch BST-BMI088-DS001 rev 1.9.
#define TRESVIZO_HARDWARE_ID "tresvizo-meridianv-v03-s3-16m-v1"
// UART del UM980: COM2 de la carrier BDLX a 115200 (J301.3/4).
#define TRESVIZO_GNSS_RX 9    // U201.17, GNSS_TXD2_MCU, R305 100 Ω ← TXD2 (J301.4)
#define TRESVIZO_GNSS_TX 8    // U201.12, GNSS_TX_MCU, R304 1 kΩ → RXD2 (J301.3)
#define TRESVIZO_GNSS_BAUD 115200

namespace board_profile {
constexpr char kHardwareId[] = TRESVIZO_HARDWARE_ID;
constexpr char kName[] = "TresVizo MeridianV v0.3 (ESP32-S3-WROOM-1-N16R2)";

// I2C de la OLED (J403), el cargador BQ25798 (U102) y el medidor MAX17048 (U103).
// Pull-ups de 4.7 kΩ en placa (R204, R205).
constexpr int kSda = 13;   // U201.21, I2C_SDA
constexpr int kScl = 14;   // U201.22, I2C_SCL
constexpr unsigned char kChargerAddress = 0x6B;  // BQ25798, SLUSDV2C §7.3.14.5
constexpr unsigned char kGaugeAddress = 0x36;    // MAX17048
// La OLED va a +3V3 directo: no hay regulador de periféricos que encender.
constexpr int kPeripheralEnable = -1;
// El módulo va girado 180° en su plano (research/v03-compacta.md, «Valores para
// el firmware»): se gira la imagen, no se espeja. Cuartos de vuelta de Adafruit GFX.
constexpr int kOledRotation = 2;

// microSD TF-015 (J401), SD_MMC de 4 bits. CMD y D0-D3 con 10 kΩ a +3V3 (R401-R405).
constexpr int kSdClock = 6;     // U201.6, SD_CLK (sin resistencia en serie)
constexpr int kSdCommand = 7;   // U201.7, SD_CMD
constexpr int kSdD0 = 5;        // U201.5, SD_D0
constexpr int kSdD1 = 4;        // U201.4, SD_D1
constexpr int kSdD2 = 16;       // U201.9, SD_D2
constexpr int kSdD3 = 15;       // U201.8, SD_D3
// Detección: el contacto CD del TF-015 cierra a GND con tarjeta (SD_CD_N, 10 kΩ a
// +3V3 por R406); Q401 (AO3401A, canal P) lo invierte: SD_DET en HIGH con tarjeta,
// R407 de 100 kΩ a GND sin ella. No hace falta pull interno.
constexpr int kSdDetect = 17;   // U201.10, SD_DET
constexpr bool kSdDetectActiveLow = false;
constexpr bool kSdDetectInternalPull = false;

// Botón SW401 a BTN_N: despierta al cargador (QON) y llega a GPIO18 por D402
// (1N4148W, ánodo en el GPIO). Activo bajo, R408 de 10 kΩ a +3V3. Mantenerlo
// 10 s es el reset por hardware del BQ25798 (SLUSDV2C §7.3.12.3).
constexpr int kPowerButton = 18;   // U201.11, BTN_SENSE_N
constexpr int kPowerPush = kPowerButton;
// Sin GPIO de corte: el apagado es el modo «ship» del BQ25798 por I2C (Q101).
constexpr int kPowerOff = -1;
// LED rojo D403 por R409 (330 Ω): activo alto, ~4.4 mA. Sin pull en el reset.
constexpr int kStatusLed = 48;     // U201.25, LED_STATUS
// INT del cargador y ALRT del medidor, drenador abierto con 10 kΩ (R108, R113).
constexpr int kChargerInt = 21;    // U201.23, CHG_INT_N
constexpr int kGaugeAlert = 47;    // U201.24, FG_ALRT_N

// GNSS: carrier BDLX por J301 y su 5 V del TPS63070 (U301).
// GPIO45 es pin de arranque (VDD_SPI) con R301 de 100 kΩ a GND: en el reset el
// GNSS queda apagado y el firmware lo enciende. Cualquier reinicio del ESP32 lo
// apaga y el UM980 arranca de cero.
constexpr int kGnssPowerEnable = 45;  // U201.26, GNSS_PWR_EN → EN del TPS63070
constexpr int kGnssPps = 10;          // U201.18, GNSS_PPS_MCU, R306 100 Ω ← J301.5
constexpr int kGnssEvent = 11;        // U201.19, GNSS_EVENT_MCU, R307 1 kΩ → J301.6, R308 100 kΩ a GND
// RESET_N: drenador abierto, pulso ≥ 5 ms. La BDLX no lo saca: el firmware no lo maneja.
constexpr int kGnssReset = 12;        // U201.20, GNSS_RESET_MCU, R309 1 kΩ → J301.7

// BMI088 (U401) en un segundo bus I2C (Wire1), 400 kHz, pull-ups de 4.7 kΩ
// (R411, R412). PS y CSB1 a VDDIO (I2C), CSB2 al aire, SDO1/SDO2 a GND.
constexpr int kImuSda = 41;    // U201.34, IMU_SDA
constexpr int kImuScl = 42;    // U201.35, IMU_SCL
constexpr int kImuInt1 = 2;    // U201.38, IMU_INT1 ← INT1 del acelerómetro (U401.16), sin pull-up
constexpr int kImuInt3 = 1;    // U201.39, IMU_INT3 ← INT3 del giróscopo (U401.12), sin pull-up
constexpr unsigned char kImuAccelAddress = 0x18;  // SDO1 a GND (DS §6.2)
constexpr unsigned char kImuGyroAddress = 0x68;   // SDO2 a GND (DS §6.2)

// USB nativo (USB-C J101, por U101) y consola UART0 en puntos de prueba.
constexpr int kUsbDm = 19, kUsbDp = 20;          // U201.13 / U201.14
constexpr int kConsoleTx = 43, kConsoleRx = 44;  // TP208 / TP209

// Batería: pack comercial 1S2P (2 × 18650 Li-ion en paralelo, BMS 4.30/2.80 V).
constexpr int kBatteryCapacityMah = 5600;   // según el anuncio; sin medir
// En «ship» el BQ2579x necesita la celda por encima de ~3.4 V: se apaga antes.
constexpr float kLowBatteryVolts = 3.5f;
constexpr float kAutoShutdownVolts = 3.45f;
constexpr unsigned long kAutoShutdownHoldMs = 60000;
// Cargador: química y límites del pack (README de la placa, «Valores de seguridad»).
constexpr unsigned kChargeVoltageMv = 4200;   // VREG de 1S que fija PROG (R103 4.7 kΩ)
constexpr unsigned kChargeCurrentMa = 1000;   // ICHG que escribe el firmware
constexpr unsigned kChargeCurrentMaxMa = 1500; // dos contactos GH por polo, AWG #26
static_assert(kChargeCurrentMa <= kChargeCurrentMaxMa, "ICHG por encima del límite del conector J102");

// Identidad del producto (docs/api-contract/receiver-identity.md): es un
// MeridianV y sigue anunciando «MeridianV» por BLE, Wi-Fi y mDNS.
constexpr char kModel[] = "MeridianV";
constexpr unsigned char kModelCode = 5;
constexpr bool kPerUnitNetworkName = false;
constexpr char kGnssModule[] = "UM980";
constexpr bool kLoraIntegrated = false;
constexpr const char* kImu = "BMI088";           // en la placa (U401); sin driver todavía
constexpr char kBatteryChemistry[] = "li-ion";
constexpr bool kRemovableStorage = true;         // microSD de empuje, accesible por el costado
constexpr const char* kIpRating = nullptr;
}
