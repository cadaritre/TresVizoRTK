#pragma once
#include <ArduinoJson.h>
#include <esp_http_server.h>

// Telemetría empujada por Wi-Fi.
//
// Existe porque por HTTP solo se puede preguntar, y preguntar por la posición
// diez veces por segundo es pedirle al equipo que serialice su modelo de chip,
// su flash y sus cinco subsistemas diez veces por segundo. El WebSocket le da
// la vuelta: una conexión, y el equipo empuja **las mismas tramas de 20 bytes
// que ya empuja por Bluetooth**.
namespace telemetry_ws {

// Se registra sobre el servidor HTTP que ya existe. No abre otro puerto.
void begin(httpd_handle_t server);
// Se llama desde el bucle principal, al lado de ble_transport::tick().
void tick();
void status(JsonObject out);
void stop();

}
