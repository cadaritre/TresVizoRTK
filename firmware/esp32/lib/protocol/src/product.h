#pragma once

namespace product {
// Qué equipo es este firmware. Un mismo código, dos productos (decisión del
// propietario, 28-09-2026):
//
// - **MeridianV**: el receptor completo que se está construyendo (microSD para
//   grabar, IMU, radio, batería integrada, puerto auxiliar). Que algo esté en el
//   producto no quiere decir que ya esté integrado: eso lo dice cada subsistema.
// - **Meridian3**: el sencillo. ESP32-S3 + UM980 + un power bank externo por
//   USB-C. Rover y base (sin grabar), NTRIP, puente de correcciones del teléfono
//   y Wi-Fi propio. No tiene microSD, IMU, radio, batería ni puerto auxiliar.
//
// Se elige al compilar: `pio run -e meridian3` define TRESVIZO_PRODUCT_MERIDIAN3;
// el entorno de siempre (`esp32s3_usb`) sigue siendo el MeridianV.
//
// Los identificadores son distintos a propósito, para que en campo no se
// confundan: nombre anunciado por Bluetooth y red Wi-Fi, nombre en la red local
// y el hardware_id de la OTA (una imagen de un producto no se instala en el
// otro). El servicio GATT y el protocolo son los mismos: las apps hablan con los
// dos igual y deciden qué enseñar por `product` y `hardware_features` de
// `/api/status`.
struct Profile {
    const char* key;          // clave interna para las apps; no se muestra
    const char* name;         // nombre del equipo, de su red y de su anuncio BLE
    const char* hostname;     // <hostname>.local en la red externa
    const char* hardwareId;   // identidad de la imagen OTA
    bool microsd;
    bool imu;
    bool radio;
    bool battery;
    bool auxPort;
};

constexpr Profile kMeridianV{"meridianv", "MeridianV", "meridianv", "tresvizo-esp32s3-4m-v1",
                             true, true, true, true, true};
constexpr Profile kMeridian3{"meridian3", "Meridian3", "meridian3", "tresvizo-meridian3-esp32s3-4m-v1",
                             false, false, false, false, false};

// Una copia y no una referencia: una referencia constexpr en un espacio de
// nombres tiene enlace externo en gnu++11 y el enlazador la ve definida en cada
// archivo que incluye esta cabecera.
#if defined(TRESVIZO_PRODUCT_MERIDIAN3)
constexpr Profile kCurrent = kMeridian3;
#else
constexpr Profile kCurrent = kMeridianV;
#endif
}  // namespace product
