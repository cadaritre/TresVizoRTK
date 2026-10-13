#pragma once
#include <ArduinoJson.h>
#include <cstdint>

// Comprobación mínima de la IMU de la placa (v0.3: BMI088 en Wire1). No es un
// driver: lee una vez, al arrancar, el identificador de chip del acelerómetro y
// del giróscopo y no configura nada. Sin IMU en la placa no toca ningún pin.
namespace imu_probe {
// Bosch BST-BMI088-DS001 rev 1.9, §5.3.1 y §5.5.1: registro 0x00 de cada parte.
constexpr uint8_t kChipIdRegister = 0x00;
constexpr uint8_t kAccelChipId = 0x1E;
constexpr uint8_t kGyroChipId = 0x0F;
// Resultado de la lectura: los dos chips con su identificador esperado.
inline const char* verdict(int accelId, int gyroId) {
    const bool accel = accelId == kAccelChipId, gyro = gyroId == kGyroChipId;
    if (accel && gyro) return "ok";
    if (accelId < 0 && gyroId < 0) return "not_detected";
    if (!accel && !gyro) return "unexpected_ids";
    return accel ? "gyro_failed" : "accel_failed";
}
void begin();
void status(JsonObject out);
}
