#include "telemetry_ws.h"
#include "gnss_receiver.h"
#include "ble_frames.h"
#include "telemetry_freshness.h"
#include "health_report.h"
#include "health_timing.h"
#include <Arduino.h>
#include <algorithm>
#include <atomic>
#include <cerrno>
#include <cmath>
#include <cstdlib>
#include <cstring>
#include <esp_timer.h>
#include <sys/socket.h>

namespace telemetry_ws {
namespace {

// Quién toca qué.
//
// Hasta 0.7.12 el envío corría en `loopTask` (núcleo 1): leía y encogía la
// lista de clientes mientras el manejador la cambiaba desde la tarea httpd, sin
// cerrojo —dos `forget` a la vez podían dejar `clientCount` en SIZE_MAX y el
// `memcpy` siguiente salirse del arreglo—, y llamaba a
// `httpd_ws_send_frame_async`, que en IDF 4.4 escribe en el socket en el acto:
// un cliente que dejaba de confirmar paraba el bucle principal, Bluetooth y
// consola incluidos, hasta `send_wait_timeout` (2 s, main.cpp).
//
// Ahora:
// - `clients` y `clientCount` son **solo de la tarea httpd**: los tocan el
//   manejador y `sendWork`, que corre en ella por `httpd_queue_work`, que es
//   como esp_http_server.h dice que se envía fuera de una petición.
// - `loopTask` solo arma las tramas de cada pasada y las encola.
// - Lo que se lee desde otras tareas (`tick`, `status`) va en atómicos.

httpd_handle_t server = nullptr;  // lo escriben begin() y stop(), desde loopTask

// Cuántos clientes a la vez. Dos: el teléfono que mide y, si acaso, un panel
// abierto para mirar. Más no tiene sentido y cada uno cuesta un socket de los
// pocos que tiene el servidor.
constexpr size_t kMaxClients = 2;
int clients[kMaxClients];                   // solo tarea httpd
size_t clientCount = 0;                     // solo tarea httpd
std::atomic<uint32_t> connectedClients{0};  // reflejo de clientCount para las demás tareas

// Cada cuánto se mira si hay algo que mandar, como en Bluetooth. El tope de la
// solución lo pone `protocol::kMinSolutionIntervalMs`; el de la salud,
// `protocol::kHealthPeriodMs`.
constexpr uint32_t kSamplePeriodMs = 20;

uint32_t lastSample = 0, lastHealth = 0, lastEpoch = UINT32_MAX, lastSolution = 0;  // solo loopTask
uint16_t sampleSequence = 0;                                              // solo loopTask

// Contadores para `/api/status` → `telemetry_stream`.
std::atomic<uint32_t> framesSent{0};     // tramas escritas, sumando clientes
std::atomic<uint32_t> clientsDropped{0}; // clientes olvidados: envío fallido o sesión ya cerrada
std::atomic<uint32_t> sendsDeferred{0};  // pasadas con algo que mandar y el envío anterior aún en httpd
std::atomic<uint32_t> sendsExpired{0};   // tandas que esperaron demasiado en httpd y no salieron
std::atomic<uint32_t> staleSolutions{0}; // posiciones vencidas al salir, contando también su edad antes de encolar

// Tipo de trama. El BLE distingue posición de salud por característica; aquí
// va todo por la misma tubería, así que el primer byte lo dice. Los 20 que
// siguen son **byte a byte** los del BLE: la app usa el mismo decodificador.
constexpr uint8_t kSolution = 0x01;
constexpr uint8_t kHealth = 0x02;
constexpr size_t kPayloadBytes = 20;
constexpr size_t kFrameBytes = 1 + kPayloadBytes;
constexpr size_t kMaxFramesPerBatch = 2;  // la solución y la salud de una misma pasada

// Lo que sale en una pasada, copiado para la tarea httpd. Se reserva al
// encolarlo y lo libera `sendWork`; si no se pudo encolar, lo libera `tick`.
struct Batch {
    httpd_handle_t server;
    uint64_t builtAtUs;
    uint64_t solutionArrivalUs;
    size_t count;
    uint8_t frames[kMaxFramesPerBatch][kFrameBytes];
};

// Una tanda en vuelo como mucho. La telemetría es estado, como en Bluetooth:
// si la anterior no ha salido no se apila otra; se vuelve a mirar en la
// siguiente pasada y sale lo más nuevo que haya.
std::atomic<bool> sendInFlight{false};

// Lo que esperó en la cola de la tarea httpd más que esto ya no es de ahora y no
// se manda. La tarea httpd atiende también el panel y la API, y una petición
// puede tenerla ocupada hasta un segundo (el mutex del instrumento). Medio
// segundo, la misma ventana con la que se notifica una solución.
constexpr uint64_t kMaxQueueWaitUs = protocol::kSolutionMaxAgeUs;

void put32(uint8_t* target, int32_t value) {
    target[0] = value; target[1] = value >> 8; target[2] = value >> 16; target[3] = value >> 24;
}

// Solo tarea httpd.
void publishClientCount() { connectedClients.store(uint32_t(clientCount), std::memory_order_relaxed); }

// Solo tarea httpd.
void forget(int descriptor) {
    for (size_t i = 0; i < clientCount; ++i) {
        if (clients[i] != descriptor) continue;
        clients[i] = clients[--clientCount];
        publishClientCount();
        return;
    }
}

// Envío sin esperar para las sesiones del WebSocket (`httpd_sess_set_send_override`).
//
// Con el envío por defecto, un cliente que deja de confirmar llena el búfer TCP
// (5760 bytes en este sdkconfig, unos 40 s de telemetría) y a partir de ahí
// cada envío espera `send_wait_timeout` (2 s) con la tarea httpd parada: ni
// panel ni API. Aquí no se espera: si no cabe, falla en el acto y el cliente se
// cierra, que es lo mismo que pasaba a los 2 s.
//
// **Una escritura a medias es un fallo.** Sin esperar puede entrar solo parte
// de la trama, y no se da por hecho que la capa WebSocket de IDF reintente el
// resto: una trama cortada dejaría el flujo ilegible sin que nadie se enterase.
// Se devuelve error y la sesión se cierra.
int sendWithoutWaiting(httpd_handle_t, int descriptor, const char* buffer, size_t length, int flags) {
    if (!buffer) return HTTPD_SOCK_ERR_INVALID;
    const int written = send(descriptor, buffer, length, flags | MSG_DONTWAIT);
    if (written < 0) return errno == EAGAIN || errno == EWOULDBLOCK ? HTTPD_SOCK_ERR_TIMEOUT : HTTPD_SOCK_ERR_FAIL;
    if (size_t(written) < length) return HTTPD_SOCK_ERR_FAIL;
    return written;
}

// Corre en la tarea httpd (`httpd_queue_work`).
void sendWork(void* argument) {
    Batch* batch = static_cast<Batch*>(argument);
    if (esp_timer_get_time() - batch->builtAtUs > kMaxQueueWaitUs) {
        // La tarea httpd estuvo ocupada: se tira y en la siguiente pasada sale
        // lo más nuevo.
        sendsExpired.fetch_add(1, std::memory_order_relaxed);
    } else {
        // Copia de la lista: enviar puede olvidar a un cliente, y recorrer el
        // arreglo mientras se encoge se salta al siguiente.
        int destinations[kMaxClients];
        const size_t total = clientCount;
        std::copy(clients, clients + total, destinations);
        for (size_t i = 0; i < total; ++i) {
            const int descriptor = destinations[i];
            // Desde el último envío la sesión pudo cerrarse (el teléfono se fue,
            // el servidor contestó a un CLOSE, el purgado LRU) y el descriptor,
            // reutilizarse para otra conexión HTTP. Se mira antes de escribir.
            if (httpd_ws_get_fd_info(batch->server, descriptor) != HTTPD_WS_CLIENT_WEBSOCKET) {
                forget(descriptor);
                clientsDropped.fetch_add(1, std::memory_order_relaxed);
                continue;
            }
            for (size_t f = 0; f < batch->count; ++f) {
                if (!protocol::telemetryFresh(esp_timer_get_time(), batch->builtAtUs,
                                             batch->solutionArrivalUs, batch->frames[f][0] == kSolution)) {
                    if (batch->frames[f][0] == kSolution) ++staleSolutions;
                    continue;
                }
                httpd_ws_frame_t packet = {};
                packet.type = HTTPD_WS_TYPE_BINARY;
                packet.payload = batch->frames[f];
                packet.len = kFrameBytes;
                if (httpd_ws_send_frame_async(batch->server, descriptor, &packet) != ESP_OK) {
                    // Un envío que falla es un cliente que se fue sin despedirse,
                    // que en campo es lo normal (el teléfono al bolsillo, el
                    // Wi-Fi que se cae), o uno que no da abasto. Se olvida y se
                    // cierra su sesión: con una trama a medias el flujo ya no
                    // se puede leer.
                    forget(descriptor);
                    httpd_sess_trigger_close(batch->server, descriptor);
                    clientsDropped.fetch_add(1, std::memory_order_relaxed);
                    break;
                }
                framesSent.fetch_add(1, std::memory_order_relaxed);
            }
        }
    }
    free(batch);
    sendInFlight.store(false, std::memory_order_release);
}

// Corre en la tarea httpd.
esp_err_t handler(httpd_req_t* request) {
    if (request->method == HTTP_GET) {
        // Apretón de manos, ya contestado por el servidor. Aquí no se manda
        // nada todavía.
        const int descriptor = httpd_req_to_sockfd(request);
        forget(descriptor);
        // No admitir un cliente si sus envíos pudieran bloquear toda la API.
        if (httpd_sess_set_send_override(request->handle, descriptor, sendWithoutWaiting) != ESP_OK)
            return ESP_FAIL;
        if (clientCount >= kMaxClients) {
            // Se echa al más antiguo en vez de rechazar al nuevo: el que acaba
            // de llegar es el que tiene a alguien mirando la pantalla.
            const int oldest = clients[0];
            httpd_sess_trigger_close(request->handle, oldest);
            forget(oldest);
        }
        clients[clientCount++] = descriptor;
        publishClientCount();
        return ESP_OK;
    }

    // El cliente no tiene nada que decir por aquí —las órdenes van por HTTP—,
    // pero hay que leer lo que mande para no dejar la trama a medias en el
    // socket. Los PING y el CLOSE los contesta el propio servidor (ver `begin`).
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
    // Todavía sin manejador registrado: nadie más toca la lista.
    clientCount = 0;
    connectedClients.store(0, std::memory_order_relaxed);
    if (!server) return;
    httpd_uri_t route = {};
    route.uri = "/ws/telemetry";
    route.method = HTTP_GET;
    route.handler = handler;
    route.is_websocket = true;
    // Con `false`, el propio servidor contesta a PING y a CLOSE y no llama al
    // manejador con ellos (esp_http_server.h, `handle_ws_control_frames`). El
    // cliente que se va se detecta al enviar: su descriptor deja de ser un
    // WebSocket (`httpd_ws_get_fd_info`) o el envío falla.
    route.handle_ws_control_frames = false;
    if (httpd_register_uri_handler(server, &route) != ESP_OK) {
        Serial.println("Error al registrar la ruta de telemetria WebSocket.");
        server = nullptr;
    }
}

void stop() {
    // Hoy no la llama nadie. La lista de clientes es de la tarea httpd y no se
    // toca desde aquí: al parar el servidor se cierran sus sesiones, y `begin`
    // la rehace antes de registrar el manejador.
    server = nullptr;
}

void tick() {
    if (!server || !connectedClients.load(std::memory_order_relaxed)) return;
    const uint32_t nowMs = millis();
    if (nowMs - lastSample < kSamplePeriodMs) return;
    lastSample = nowMs;

    const auto snapshot = gnss_receiver::snapshot();
    // Después de la instantánea: una GGA llegada entre las dos lecturas no puede
    // quedar «en el futuro» y dar la vuelta a la resta.
    const uint64_t nowUs = esp_timer_get_time();
    const auto& s = snapshot.solution;

    // Salud a 1 Hz, independiente de la solución, igual que por Bluetooth: es
    // también el latido. Hasta 0.7.12 iba detrás de la puerta de la solución y,
    // sin GGA, época repetida o tope de 5 Hz, no salía.
    const bool healthDue = nowMs - lastHealth >= protocol::kHealthPeriodMs;
    // La misma puerta que el BLE: sin época nueva no se manda solución.
    // Repetir la anterior inflaría la frecuencia medida sin añadir una sola
    // medición. Y como máximo a 5 Hz (`protocol::kMinSolutionIntervalMs`).
    const bool solutionDue = snapshot.enabled && snapshot.accepted && s.has_utc
        && nowUs - s.arrival_us <= protocol::kSolutionMaxAgeUs && s.utc_ms != lastEpoch
        && nowMs - lastSolution >= protocol::kMinSolutionIntervalMs;
    if (!healthDue && !solutionDue) return;

    // La tanda anterior sigue en la tarea httpd: no se apila otra. No se da
    // nada por enviado, así que en la siguiente pasada se arma lo más nuevo.
    if (sendInFlight.load(std::memory_order_acquire)) {
        sendsDeferred.fetch_add(1, std::memory_order_relaxed);
        return;
    }
    Batch* batch = static_cast<Batch*>(malloc(sizeof(Batch)));
    if (!batch) {
        sendsDeferred.fetch_add(1, std::memory_order_relaxed);
        return;
    }
    batch->server = server;
    batch->builtAtUs = nowUs;
    batch->solutionArrivalUs = s.arrival_us;
    batch->count = 0;

    const uint16_t sequence = uint16_t(sampleSequence + 1);
    if (solutionDue) {
        uint8_t* frame = batch->frames[batch->count++];
        frame[0] = kSolution;
        uint8_t* sample = frame + 1;
        memset(sample, 0, kPayloadBytes);
        sample[0] = uint8_t(sequence); sample[1] = uint8_t(sequence >> 8);
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
    }
    if (healthDue) {
        uint8_t* frame = batch->frames[batch->count++];
        frame[0] = kHealth;
        // Armada en `health_report.h`, igual que por Bluetooth; calidad y
        // precisión caducan a los 2 s de la última GGA y GST.
        health_report::build(frame + 1, snapshot, nowUs);
    }

    sendInFlight.store(true, std::memory_order_release);
    if (httpd_queue_work(batch->server, sendWork, batch) != ESP_OK) {
        // No llegó a la tarea httpd: la tanda es nuestra todavía. Se reintenta
        // en la siguiente pasada.
        free(batch);
        sendInFlight.store(false, std::memory_order_release);
        sendsDeferred.fetch_add(1, std::memory_order_relaxed);
        return;
    }
    // Desde aquí `batch` es de `sendWork`, que puede haberla liberado ya.
    if (solutionDue) {
        sampleSequence = sequence;
        lastSolution = nowMs;
        lastEpoch = s.utc_ms;
    }
    if (healthDue) lastHealth = nowMs;
}

void status(JsonObject out) {
    out["available"] = server != nullptr;
    out["clients"] = connectedClients.load(std::memory_order_relaxed);
    out["max_clients"] = kMaxClients;
    out["path"] = "/ws/telemetry";
    out["frames_sent"] = framesSent.load(std::memory_order_relaxed);
    out["clients_dropped"] = clientsDropped.load(std::memory_order_relaxed);
    // El envío va por la tarea httpd con una tanda en vuelo como mucho:
    // pasadas que esperaron a la anterior (sale lo más nuevo después) y tandas
    // que esperaron más de medio segundo en httpd y se tiraron.
    out["sends_deferred"] = sendsDeferred.load(std::memory_order_relaxed);
    out["sends_expired"] = sendsExpired.load(std::memory_order_relaxed);
    out["stale_solutions_dropped"] = staleSolutions.load(std::memory_order_relaxed);
}

}  // namespace telemetry_ws
