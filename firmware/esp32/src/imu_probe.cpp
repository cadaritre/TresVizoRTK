#include "imu_probe.h"
#include "board_profile.h"
#include <Arduino.h>
#include <Wire.h>

namespace imu_probe {
namespace {
// -1: sin respuesta. Solo begin() (en setup) los escribe; luego son de lectura.
int accelId = -1, gyroId = -1;
const char* phase = "no_imu";

#if defined(TRESVIZO_BOARD_V03)
int readId(uint8_t address) {
    Wire1.beginTransmission(address);
    Wire1.write(kChipIdRegister);
    if (Wire1.endTransmission(false) != 0) return -1;
    if (Wire1.requestFrom(address, uint8_t(1)) != 1) return -1;
    return Wire1.read();
}
#endif
}

void begin() {
#if defined(TRESVIZO_BOARD_V03)
    if (board_profile::kImuSda < 0 || board_profile::kImuScl < 0) return;
    // INT1 (acelerómetro) arranca deshabilitado y INT3 (giróscopo) en drenador
    // abierto (DS §5.3.16 y §5.5.10); la placa no les pone pull-up. Con el pull
    // interno a GND no quedan flotando mientras no haya driver que los configure.
    if (board_profile::kImuInt1 >= 0) pinMode(board_profile::kImuInt1, INPUT_PULLDOWN);
    if (board_profile::kImuInt3 >= 0) pinMode(board_profile::kImuInt3, INPUT_PULLDOWN);
    // El bus del BMI088 es solo suyo: Wire (OLED, cargador, medidor) no se toca.
    if (!Wire1.begin(board_profile::kImuSda, board_profile::kImuScl, 400000)) { phase = "bus_failed"; return; }
    Wire1.setTimeOut(20);
    // El acelerómetro necesita hasta 1 ms tras el POR (DS §3); el ESP32 tarda
    // mucho más en llegar aquí. Por I2C no hace falta la lectura de relleno de SPI.
    delay(2);
    accelId = readId(board_profile::kImuAccelAddress);
    gyroId = readId(board_profile::kImuGyroAddress);
    phase = verdict(accelId, gyroId);
    Wire1.end();
#endif
}

void status(JsonObject out) {
    out["probe"] = phase;
    if (!board_profile::kImu) return;
    out["chip"] = board_profile::kImu;
    if (accelId >= 0) out["accel_chip_id"] = accelId; else out["accel_chip_id"] = nullptr;
    if (gyroId >= 0) out["gyro_chip_id"] = gyroId; else out["gyro_chip_id"] = nullptr;
#if defined(TRESVIZO_BOARD_V03)
    out["sda_gpio"] = board_profile::kImuSda;
    out["scl_gpio"] = board_profile::kImuScl;
    out["int1_gpio"] = board_profile::kImuInt1;
    out["int3_gpio"] = board_profile::kImuInt3;
#endif
}
}
