#include "telemetry_ws.h"
#include "correction_router.h"
#include "gnss_receiver.h"
#include "gnss_sky.h"
#include "ble_frames.h"
#include "health_report.h"
#include <algorithm>
#include <cmath>
#include <cstring>
#include <esp_timer.h>

namespace telemetry_ws {
namespace {

httpd_handle_t server = nullptr;

// Cuántos clientes a la vez. Dos: el teléfono que mide y, si acaso, un panel
// abierto para mirar. Más no tiene sentido y cada uno cuesta un socket de los
// pocos que tiene el servidor.
constexpr size_t kMaxClients = 2;
int clients[kMaxClients];
size_t clientCount = 0;

uint32_t lastSample = 0, lastHealth = 0, lastEpoch = 0, lastSolution = 0;
uint16_t sampleSequence = 0;
uint32_t framesSent = 0, dropped = 0;

// Tipo de trama. El BLE distingue posición de salud por característica; aquí
// va todo por la misma tubería, así que el primer byte lo dice. Los 20 que
// siguen son **byte a byte** los del BLE: la app usa el mismo decodificador.
constexpr uint8_t kSolution = 0x01;
constexpr uint8_t kHealth = 0x02;

void put32(uint8_t* target, int32_t value) {
    target[0] = value; target[1] = value >> 8; target[2] = value >> 16; target[3] = value >> 24;
}

void forget(int descriptor) {
    for (size_t i = 0; i < clientCount; ++i) {
        if (clients[i] != descriptor) continue;
        clients[i] = clients[--clientCount];
        return;
    }
}

void broadcast(uint8_t type, const uint8_t* payload) {
    if (!server || !clientCount) return;
    uint8_t frame[21];
    frame[0] = type;
    memcpy(frame + 1, payload, 20);

    httpd_ws_frame_t packet = {};
    packet.type = HTTPD_WS_TYPE_BINARY;
    packet.payload = frame;
    packet.len = sizeof(frame);

    // Copia de la lista: enviar puede expulsar a un cliente, y recorrer el
    // arreglo mientras se encoge se salta al siguiente.
    int destinations[kMaxClients];
    const size_t total = clientCount;
    memcpy(destinations, clients, total * sizeof(int));

    for (size_t i = 0; i < total; ++i) {
        // `_async` es la única forma correcta de empujar desde fuera del
        // manejador: la síncrona da por hecho que hay una petición en curso.
        if (httpd_ws_send_frame_async(server, destinations[i], &packet) == ESP_OK) {
            ++framesSent;
        } else {
            // Un envío que falla es un cliente que se fue sin despedirse, que
            // en campo es lo normal: el teléfono se guarda en el bolsillo y el
            // Wi-Fi se cae. Se olvida y ya.
            ++dropped;
            forget(destinations[i]);
        }
    }
}

esp_err_t handler(httpd_req_t* request) {
    if (request->method == HTTP_GET) {
        // Apretón de manos. Aquí no se manda nada todavía.
        const int descriptor = httpd_req_to_sockfd(request);
        forget(descriptor);
        if (clientCount >= kMaxClients) {
            // Se echa al más antiguo en vez de rechazar al nuevo: el que acaba
            // de llegar es el que tiene a alguien mirando la pantalla.
            httpd_sess_trigger_close(server, clients[0]);
            forget(clients[0]);
        }
        clients[clientCount++] = descriptor;
        return ESP_OK;
    }

    // El cliente no tiene nada que decir por aquí —las órdenes van por HTTP—,
    // pero hay que leer lo que mande para no dejar la trama a medias en el
    // socket. Y hay que contestar al ping, o el navegador cierra por su cuenta.
    httpd_ws_frame_t incoming = {};
    uint8_t buffer[64];
    incoming.payload = buffer;
    if (httpd_ws_recv_frame(request, &incoming, sizeof(buffer)) != ESP_OK) {
        forget(httpd_req_to_sockfd(request));
        return ESP_FAIL;
    }
    if (incoming.type == HTTPD_WS_TYPE_CLOSE) {
        forget(httpd_req_to_sockfd(request));
    }
    return ESP_OK;
}

}  // namespace

void begin(httpd_handle_t handle) {
    server = handle;
    clientCount = 0;
    if (!server) return;
    httpd_uri_t route = {};
    route.uri = "/ws/telemetry";
    route.method = HTTP_GET;
    route.handler = handler;
    route.is_websocket = true;
    // El servidor no debe contestar solo a los ping: se contestan aquí para
    // poder detectar al cliente que se fue.
    route.handle_ws_control_frames = false;
    if (httpd_register_uri_handler(server, &route) != ESP_OK) {
        Serial.println("Error al registrar la ruta de telemetria WebSocket.");
        server = nullptr;
    }
}

void stop() {
    server = nullptr;
    clientCount = 0;
}

void tick() {
    if (!server || !clientCount) return;
    // Se mira cada 20 ms, como en Bluetooth; el tope de envío lo pone
    // `protocol::kMinSolutionIntervalMs`, más abajo.
    if (millis() - lastSample < 20) return;
    lastSample = millis();

    const auto snapshot = gnss_receiver::snapshot();
    const auto& s = snapshot.solution;
    // La misma puerta que el BLE: sin época nueva no se manda nada. Repetir la
    // anterior inflaría la frecuencia medida sin añadir una sola medición.
    if (!snapshot.enabled || !snapshot.accepted || !s.has_utc
        || esp_timer_get_time() - s.arrival_us > 500000 || s.utc_ms == lastEpoch) return;
    // Máximo 5 Hz, el mismo tope que el Bluetooth (`protocol::kMinSolutionIntervalMs`).
    if (millis() - lastSolution < protocol::kMinSolutionIntervalMs) return;
    lastSolution = millis();
    lastEpoch = s.utc_ms;

    uint8_t sample[20] = {};
    ++sampleSequence;
    sample[0] = sampleSequence; sample[1] = sampleSequence >> 8;
    sample[2] = s.quality;
    // Satélites **usados** en la solución (GGA), como dice el protocolo desde el
    // principio: las apps los guardan con cada punto. En 0.7.5 y 0.7.6 iban aquí
    // los rastreados; ahora van en el byte 10 de la salud. 255 = desconocido.
    sample[3] = s.has_satellites ? uint8_t(std::min(s.satellites, 254u)) : 255;
    put32(sample + 4, s.utc_ms);
    put32(sample + 8, s.has_position ? lround(s.latitude_deg * 1e7) : INT32_MIN);
    put32(sample + 12, s.has_position ? lround(s.longitude_deg * 1e7) : INT32_MIN);
    put32(sample + 16, s.has_position && std::isfinite(s.altitude_msl_m)
          && fabs(s.altitude_msl_m) < 2147483.0 ? lround(s.altitude_msl_m * 1000) : INT32_MIN);
    broadcast(kSolution, sample);

    // Salud a 1 Hz, igual que por Bluetooth: la sigma y la antigüedad de las
    // correcciones no cambian a la velocidad de la posición.
    if (millis() - lastHealth < 1000) return;
    lastHealth = millis();

    // Salud: armada en `health_report.h`, igual que por Bluetooth.
    uint8_t report[20];
    health_report::build(report, snapshot, esp_timer_get_time());
    broadcast(kHealth, report);
}

void status(JsonObject out) {
    out["available"] = server != nullptr;
    out["clients"] = clientCount;
    out["max_clients"] = kMaxClients;
    out["path"] = "/ws/telemetry";
    out["frames_sent"] = framesSent;
    out["clients_dropped"] = dropped;
}

}  // namespace telemetry_ws
