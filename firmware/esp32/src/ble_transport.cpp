#include "ble_transport.h"
#include "instrument.h"
#include "gnss_receiver.h"
#include "gnss_sky.h"
#include "rtcm3.h"
#include "correction_router.h"
#include "correction_output.h"
#include "ble_frames.h"
#include "ble_address.h"
#include "health_report.h"
#include <BLEDevice.h>
#include <BLEServer.h>
#include <BLE2902.h>
#include <esp_timer.h>
#include <esp_gatt_common_api.h>
#include <esp_mac.h>
#include <atomic>
#include <Preferences.h>

namespace ble_transport {
namespace {
constexpr char serviceId[] = "a04c0001-8f24-4adb-a350-77ef6339c320";
constexpr char commandId[] = "a04c0002-8f24-4adb-a350-77ef6339c320";
constexpr char responseId[] = "a04c0003-8f24-4adb-a350-77ef6339c320";
constexpr char correctionId[] = "a04c0005-8f24-4adb-a350-77ef6339c320";
constexpr char solutionId[] = "a04c0004-8f24-4adb-a350-77ef6339c320";
constexpr char healthId[] = "a04c0006-8f24-4adb-a350-77ef6339c320";
struct Request { uint32_t generation, arrival; char json[1025]; };
QueueHandle_t requests = nullptr;
Dispatch dispatchRequest;
Authenticate authenticateRequest;
BLECharacteristic *responses = nullptr, *solutions = nullptr, *health = nullptr;
BLEServer* server = nullptr;
std::atomic<bool> connected{false}, authorized{false}, advertise{false};
// Interruptor del transporte. Se persiste: apagar la radio debe seguir apagada
// después de un corte de corriente, no volver sola en la siguiente jornada.
std::atomic<bool> enabled{true};
std::atomic<uint32_t> generation{0}, dropped{0}, correctionAccepted{0}, correctionRejected{0}, correctionDropped{0};
// MTU ATT negociado con el telefono y la conexion a la que se refiere. Hasta
// que el telefono lo negocia rige el minimo, 23.
std::atomic<uint16_t> attMtu{protocol::kMinimumAttMtu}, connectionId{0};
// Si la controladora dice que no hay hueco, se espera; pero no mas de esto. Si
// la consulta fallara por algo que no se ha visto en el equipo, el canal de
// ordenes seguiria vivo, a una trama cada 50 ms, en vez de quedarse mudo.
constexpr uint32_t kFlowControlMaxWaitMs = 50;
// Tramas de respuesta mandadas **sin hueco** en la controladora, al vencer la
// espera. Lo que se arriesga a perderse se cuenta: si en campo vencen
// peticiones y este numero sube, la causa es esta y no la antena ni la
// distancia. Si se queda en cero, los 50 ms bastan.
std::atomic<uint32_t> forcedFrames{0};
// Conexion rapida para ordenes y correcciones: 15 a 30 ms, en unidades de
// 1.25 ms. Dentro de lo que Apple admite para accesorios (minimo >= 15 ms y
// multiplo de 15, maximo >= minimo + 15, latencia <= 30, supervision de 2 a 6 s
// y maximo * (latencia + 1) * 3 < supervision). Android lo acepta o lo ajusta.
// Sin pedirlo, iOS se queda en 30 ms y Android en unos 45 ms: una orden con
// respuesta tarda al menos dos intervalos en ir y volver.
constexpr uint16_t kConnIntervalMinUnits = 12;   // 15 ms
constexpr uint16_t kConnIntervalMaxUnits = 24;   // 30 ms
constexpr uint16_t kPeripheralLatency = 0;       // el equipo contesta en cada evento: latencia de ordenes minima
constexpr uint16_t kSupervisionTimeoutUnits = 400;  // 4 s, en unidades de 10 ms
// Intervalo de conexion vigente, en unidades de 1.25 ms (0 = no se sabe).
std::atomic<uint16_t> connIntervalUnits{0};
// Paquete de salud: 1 Hz **siempre** que haya alguien conectado, haya posicion
// o no. Hasta 0.7.10 solo salia detras de una solucion nueva y sin fix no
// llegaba ni la edad de las correcciones ni señal de vida. Ahora es tambien el
// latido del protocolo: 20 bytes por segundo, que ya se mandaban.
constexpr uint32_t kHealthPeriodMs = 1000;
// Telemetria que no salio porque la controladora no tenia hueco. Es estado: se
// manda la siguiente epoca (la mas nueva), no se encola la vieja. Si sube mucho,
// la radio va saturada.
std::atomic<uint32_t> telemetrySkipped{0};
// Mediciones del propio transporte, desde la ultima conexion: el mayor hueco
// entre dos pasadas del bucle (si pasa de unos 50 ms, algo bloquea el bucle y
// retrasa posicion y respuestas) y la orden mas lenta en despacharse.
std::atomic<uint32_t> maxTickGapMs{0}, maxDispatchMs{0};
uint32_t lastTickMs = 0;
bool ready = false;
Preferences settings;
String pending;
size_t offset = 0;
uint16_t messageId = 0, sampleSequence = 0;
uint32_t lastSend = 0, lastEpoch = UINT32_MAX, lastSample = 0, lastHealth = 0, lastSolution = 0;
uint32_t responseGeneration = 0;

class ConnectionCallbacks : public BLEServerCallbacks {
    void onConnect(BLEServer*, esp_ble_gatts_cb_param_t* parameters) override {
        // Sin emparejamiento: quien se conecta queda autorizado. La única
        // barrera que queda es el alcance de la radio.
        connectionId = parameters->connect.conn_id;
        attMtu = protocol::kMinimumAttMtu;
        connIntervalUnits = parameters->connect.conn_params.interval;
        maxTickGapMs = 0; maxDispatchMs = 0; lastTickMs = 0;
        ++generation; connected = true; authorized = true;
        esp_ble_conn_update_params_t wanted = {};
        memcpy(wanted.bda, parameters->connect.remote_bda, sizeof(esp_bd_addr_t));
        wanted.min_int = kConnIntervalMinUnits;
        wanted.max_int = kConnIntervalMaxUnits;
        wanted.latency = kPeripheralLatency;
        wanted.timeout = kSupervisionTimeoutUnits;
        esp_ble_gap_update_conn_params(&wanted);
    }
    // El telefono negocia el MTU nada mas conectarse; iPhone pide 185 o mas.
    void onMtuChanged(BLEServer*, esp_ble_gatts_cb_param_t* parameters) override {
        attMtu = parameters->mtu.mtu;
    }
    void onDisconnect(BLEServer*) override {
        attMtu = protocol::kMinimumAttMtu;
        connIntervalUnits = 0;
        ++generation; connected = false; authorized = false;
        // Solo volver a anunciarse si el transporte sigue habilitado.
        advertise = enabled.load();
    }
};
class CommandCallbacks : public BLECharacteristicCallbacks {
    char buffer[1025] = {};
    size_t length = 0;
    bool overflow = false;
    uint32_t started = 0, seenGeneration = 0;
    void onWrite(BLECharacteristic* characteristic) override {
        if (!enabled) return;
        const uint32_t currentGeneration = generation.load();
        if (seenGeneration != currentGeneration || (length && millis() - started > 5000)) {
            length = 0; overflow = false; seenGeneration = currentGeneration;
        }
        const std::string data = characteristic->getValue();
        for (const char byte : data) {
            if (!length && !overflow) started = millis();
            if (byte == '\n') {
                if (!overflow && length) {
                    Request request = {};
                    request.generation = currentGeneration; request.arrival = millis();
                    memcpy(request.json, buffer, length);
                    if (xQueueSend(requests, &request, 0) != pdTRUE) ++dropped;
                } else ++dropped;
                length = 0; overflow = false;
            } else if (byte != '\r') {
                if (length < 1024 && !overflow) buffer[length++] = byte;
                else overflow = true;
            }
        }
    }
};
class CorrectionCallbacks : public BLECharacteristicCallbacks {
    gnss::Rtcm3Parser parser;
    uint32_t seenGeneration = 0, lastByte = 0, sourceGeneration = 0;
    void onWrite(BLECharacteristic* characteristic) override {
        // El teléfono actúa de puente: recibe RTCM de un caster por datos
        // móviles y lo escribe aquí cuando el equipo no tiene red propia.
        // Sin emparejamiento, cualquiera dentro del alcance puede escribir:
        // al menos no se admite mientras el equipo trabaja como base, donde
        // recibir correcciones ajenas no tiene ningún sentido legítimo.
        if (!enabled || !authorized || correction_output::active()) return;
        if (seenGeneration != generation.load() || sourceGeneration != correction_router::generation() || millis() - lastByte > 2000) parser.reset();
        sourceGeneration = correction_router::generation();
        seenGeneration = generation.load(); lastByte = millis();
        const auto data = characteristic->getValue();
        for (uint8_t byte : data) parser.feed(byte, [](const uint8_t* frame, size_t length) {
            if (!correction_router::submit(correction_router::Source::Ble, frame, length)) ++correctionDropped;
        });
        correctionAccepted = parser.accepted; correctionRejected = parser.rejected;
    }
};
// El intervalo que de verdad quedo tras negociar (el telefono decide).
// La direccion con la que se anuncia el equipo (lib/protocol/src/ble_address.h)
// y si la pila la acepto: el aviso de la pila llega despues, por onGapEvent.
uint8_t advertisedAddress[protocol::kBleAddressBytes] = {};
std::atomic<bool> advertisedAddressIsRandom{false};
std::atomic<int> randomAddressStatus{-1};  // -1: la pila aun no contesto
void onGapEvent(esp_gap_ble_cb_event_t event, esp_ble_gap_cb_param_t* parameters) {
    if (event == ESP_GAP_BLE_UPDATE_CONN_PARAMS_EVT && parameters->update_conn_params.status == ESP_BT_STATUS_SUCCESS)
        connIntervalUnits = parameters->update_conn_params.conn_int;
    if (event == ESP_GAP_BLE_SET_STATIC_RAND_ADDR_EVT)
        randomAddressStatus = int(parameters->set_rand_addr_cmpl.status);
}
// **La tabla GATT que guarda el cliente puede ser de otro firmware.** Medido
// el 27-09-2026: una Mac que se conecto a un firmware antiguo seguia viendo,
// con 0.7.11 cargado, cuatro caracteristicas (sin la de salud) y la de RTCM sin
// escritura sin respuesta. Sin emparejamiento la pila no avisa de «servicios
// cambiados» a nadie. Desde 0.7.12 lo resuelve la direccion atada a la tabla
// (ble_address.h). Lo de abajo queda como sonda.
//
// Mandarlo al conectar no basta: el cliente aun no se ha suscrito a ese aviso.
// Se manda una vez, un rato despues de conectar.
//
// **Apagado por defecto** (`-DTRESVIZO_BLE_SERVICE_CHANGED` lo enciende). Con la
// Mac, el aviso sale (ESP_OK) pero macOS no redescubre; en un iPhone no se ha
// probado. Si iOS lo atiende, invalida lo descubierto a mitad de sesion y una
// app que no implemente didModifyServices se quedaria con caracteristicas
// muertas: no se enciende hasta probarlo con las apps de campo.
constexpr uint32_t kServiceChangedDelayMs = 1500;
std::atomic<esp_gatt_if_t> gattsInterface{ESP_GATT_IF_NONE};
esp_bd_addr_t peerAddress = {};
uint32_t connectedAtMs = 0;
bool serviceChangedSent = true;
#ifdef TRESVIZO_BLE_SERVICE_CHANGED
esp_err_t serviceChangedResult = ESP_OK;
#endif
void onGattsEvent(esp_gatts_cb_event_t event, esp_gatt_if_t gattsIf, esp_ble_gatts_cb_param_t* parameters) {
    if (event != ESP_GATTS_CONNECT_EVT) return;
    gattsInterface = gattsIf;
    memcpy(peerAddress, parameters->connect.remote_bda, sizeof(esp_bd_addr_t));
    connectedAtMs = millis();
    serviceChangedSent = false;
}
// Hay hueco en la controladora para una notificacion mas en esta conexion.
bool controllerHasRoom() { return esp_ble_get_cur_sendable_packets_num(connectionId.load()) > 0; }
void put32(uint8_t* p, int32_t value) {
    const uint32_t encoded = static_cast<uint32_t>(value);
    for (int i = 0; i < 4; ++i) p[i] = encoded >> (8*i);
}
void sendResponseFrame() {
    // Tramas del tamano del MTU negociado: con 247, una respuesta de 2 kB son 9
    // tramas en vez de 134. Con 23 siguen siendo de 20 bytes.
    //
    // Y solo si la controladora tiene hueco para esta conexion, como hace el
    // ejemplo de caudal de ESP-IDF: una notificacion que no cabe se pierde en
    // silencio, y la app descarta la respuesta entera por el hueco en los
    // desplazamientos. Con tramas de 244 el riesgo de llenarla es mucho mayor
    // que con las de 20.
    const bool due = !pending.isEmpty() && millis() - lastSend >= 5;
    const bool room = due && controllerHasRoom();
    if (due && (room || millis() - lastSend >= kFlowControlMaxWaitMs)) {
        if (!room) ++forcedFrames;
        uint8_t frame[protocol::kMaxNotificationBytes];
        const size_t length = protocol::encodeResponseFrame(frame, messageId, offset, pending.c_str(), pending.length(),
                                                            protocol::responsePayloadBytes(attMtu.load()));
        responses->setValue(frame, length); responses->notify();
        offset += length - protocol::kResponseHeaderBytes; lastSend = millis();
        if (offset == pending.length()) pending = "";
    }
}
void publishTelemetry() {
    if (!authorized || millis() - lastSample < 20) return;
    lastSample = millis();
    const auto snapshot = gnss_receiver::snapshot();
    // Salud a 1 Hz, independiente de la posicion: es tambien el latido.
    if (millis() - lastHealth >= kHealthPeriodMs) {
        if (controllerHasRoom()) {
            lastHealth = millis();
            // Armada en `health_report.h`, igual que por WebSocket. Bytes 1-4 =
            // precision mostrada por Meridian V; 12-15 = sigma cruda del UM980;
            // 17-19 = contadores de RTCM.
            uint8_t report[20];
            health_report::build(report, snapshot);
            health->setValue(report, sizeof(report)); health->notify();
        } else ++telemetrySkipped;
    }
    const auto& s = snapshot.solution;
    if (!snapshot.enabled || !snapshot.accepted || !s.has_utc || esp_timer_get_time() - s.arrival_us > 500000 || s.utc_ms == lastEpoch) return;
    // Máximo 5 Hz (`protocol::kMinSolutionIntervalMs`). Se sigue mirando cada
    // 20 ms para mandar cada época en cuanto se puede, no con retraso.
    if (millis() - lastSolution < protocol::kMinSolutionIntervalMs) return;
    // Sin hueco no se fuerza: la epoca se da por no enviada y en la siguiente
    // pasada se manda la mas nueva que haya.
    if (!controllerHasRoom()) { ++telemetrySkipped; return; }
    lastSolution = millis();
    lastEpoch = s.utc_ms;
    uint8_t sample[20] = {};
    ++sampleSequence;
    sample[0] = sampleSequence; sample[1] = sampleSequence >> 8;
    sample[2] = s.quality;
    // Satélites **usados** en la solución (GGA), como dice el protocolo desde el
    // principio: las apps los guardan con cada punto. En 0.7.5 y 0.7.6 iban aquí
    // los rastreados y los puntos se registraban con la cifra equivocada; los
    // rastreados van en el byte 10 de la salud. 255 = desconocido.
    sample[3] = s.has_satellites ? uint8_t(std::min(s.satellites, 254u)) : 255;
    put32(sample + 4, s.utc_ms);
    put32(sample + 8, s.has_position ? lround(s.latitude_deg * 1e7) : INT32_MIN);
    put32(sample + 12, s.has_position ? lround(s.longitude_deg * 1e7) : INT32_MIN);
    put32(sample + 16, s.has_position && std::isfinite(s.altitude_msl_m) && fabs(s.altitude_msl_m) < 2147483.0 ? lround(s.altitude_msl_m * 1000) : INT32_MIN);
    solutions->setValue(sample, sizeof(sample)); solutions->notify();
}
void dispatchNextRequest() {
    Request request;
    if (xQueueReceive(requests, &request, 0) != pdTRUE) return;
    if (request.generation != generation.load() || millis() - request.arrival > 5000) { ++dropped; return; }
    const uint32_t startedMs = millis();
    JsonDocument input, output, body;
    const auto error = deserializeJson(input, request.json, DeserializationOption::NestingLimit(5));
    int code = 400;
    if (error || !input.is<JsonObject>() || !input["id"].is<uint32_t>()) {
        body["error"] = "invalid_request";
    } else {
        output["id"] = input["id"];
        if (!authenticateRequest(input["key"] | "")) {
            code = 401; body["error"] = "unauthorized";
        } else {
            authorized = true;
            const String method = input["method"] | "";
            const String path = input["path"] | "";
            // La recuperación/cambio de credenciales permanece exclusivamente por USB.
            if (path == "/api/recording/read" || path == "/api/access" || (path.startsWith("/api/update/") && method != "GET") || (method != "GET" && method != "POST" && method != "PUT")) {
                code = 400; body["error"] = "unsupported_operation";
            } else code = dispatchRequest(method, path, input["body"].as<JsonVariantConst>(), body);
        }
    }
    output["status"] = code; output["body"] = body;
    serializeJson(output, pending);
    if (pending.length() > 4096) pending = "{\"status\":413,\"body\":{\"error\":\"response_too_large\"}}";
    responseGeneration = request.generation; offset = 0; ++messageId;
    const uint32_t took = millis() - startedMs;
    if (took > maxDispatchMs.load()) maxDispatchMs = took;
}
}
void begin(Dispatch dispatch, Authenticate authenticate) {
    dispatchRequest = dispatch; authenticateRequest = authenticate;
    requests = xQueueCreate(2, sizeof(Request));
    if (!requests) return;
    if (settings.begin("ble", false)) enabled = settings.getBool("enabled", true);
    // Sin emparejamiento ni PIN, por decisión del propietario: la app de campo
    // debe conectarse de un toque. La contrapartida es real y conviene tenerla
    // presente: cualquier equipo dentro del alcance puede escribir en las
    // características, incluidas las correcciones que van al receptor.
    BLEDevice::init(instrument::apName().c_str());
    // Ofrecer un MTU mayor (hueco G5): el telefono elige el menor de los dos.
    // Un cliente que no negocia sigue en 23 y recibe tramas de 20 bytes.
    BLEDevice::setMTU(protocol::kPreferredAttMtu);
    BLEDevice::setCustomGapHandler(onGapEvent);
    BLEDevice::setCustomGattsHandler(onGattsEvent);
    server = BLEDevice::createServer();
    server->setCallbacks(new ConnectionCallbacks());
    auto service = server->createService(serviceId);
    auto commands = service->createCharacteristic(commandId, BLECharacteristic::PROPERTY_WRITE);
    commands->setAccessPermissions(ESP_GATT_PERM_WRITE);
    commands->setCallbacks(new CommandCallbacks());
    responses = service->createCharacteristic(responseId, BLECharacteristic::PROPERTY_NOTIFY);
    responses->addDescriptor(new BLE2902());
    solutions = service->createCharacteristic(solutionId, BLECharacteristic::PROPERTY_NOTIFY);
    solutions->addDescriptor(new BLE2902());
    // Con y **sin** respuesta (desde 0.7.11). En ATT solo cabe una escritura con
    // respuesta en vuelo por enlace, asi que el RTCM y las ordenes iban por un
    // solo carril; y la respuesta ATT la manda la biblioteca **antes** de
    // llamar a onWrite, de modo que nunca decia que la trama hubiera entrado a
    // la cola del UM980. Sin respuesta, el RTCM deja libre el carril de las
    // ordenes; la perdida se ve en los contadores (salud, bytes 17-19, y
    // /api/status). Las apps viejas siguen escribiendo con respuesta.
    auto corrections = service->createCharacteristic(correctionId,
        BLECharacteristic::PROPERTY_WRITE | BLECharacteristic::PROPERTY_WRITE_NR);
    corrections->setAccessPermissions(ESP_GATT_PERM_WRITE);
    corrections->setCallbacks(new CorrectionCallbacks());
    // Salud del equipo, aparte de la posición: precisión estimada, antigüedad de
    // las correcciones y presencia de IMU. La app necesita saber con qué calidad
    // está midiendo, no solo dónde. Va en su propia característica para no
    // romper el paquete de 20 bytes que cabe en un MTU ATT sin negociar.
    health = service->createCharacteristic(healthId, BLECharacteristic::PROPERTY_NOTIFY);
    health->addDescriptor(new BLE2902());
    service->start();
    auto advertising = BLEDevice::getAdvertising();
    // Una direccion por tabla GATT (ble_address.h): un telefono que guardo la
    // tabla de otro firmware ve un equipo nuevo y la lee entera. Si algo falla
    // se queda la publica del chip, como hasta 0.7.11: el enlace sigue, solo
    // vuelve el riesgo de la tabla vieja.
    uint8_t chip[protocol::kBleAddressBytes];
    if (esp_read_mac(chip, ESP_MAC_BT) == ESP_OK) {
        protocol::advertisedAddress(chip, protocol::kGattTableGeneration, advertisedAddress);
        if (esp_ble_gap_set_rand_addr(advertisedAddress) == ESP_OK) {
            advertising->setDeviceAddress(advertisedAddress, BLE_ADDR_TYPE_RANDOM);
            advertisedAddressIsRandom = true;
        }
    }
    advertising->addServiceUUID(serviceId);
    advertising->setScanResponse(true);
    if (enabled) BLEDevice::startAdvertising();
    ready = true;
}
void tick() {
    if (!ready) return;
    const uint32_t tickMs = millis();
    if (connected && lastTickMs && tickMs - lastTickMs > maxTickGapMs.load()) maxTickGapMs = tickMs - lastTickMs;
    lastTickMs = connected ? tickMs : 0;
    // Apagado: dejar de anunciarse y soltar a quien esté conectado. La radio BLE
    // del SDK no se desinicializa aquí: hacerlo y rehacerlo fragmenta el heap.
    if (!enabled) {
        if (connected && server) server->disconnect(server->getConnId());
        pending = ""; offset = 0;
        return;
    }
    if (advertise.exchange(false)) BLEDevice::startAdvertising();
    if (!connected) { pending = ""; offset = 0; return; }
    if (responseGeneration != generation.load()) { pending = ""; offset = 0; }
#ifdef TRESVIZO_BLE_SERVICE_CHANGED
    if (!serviceChangedSent && millis() - connectedAtMs >= kServiceChangedDelayMs) {
        serviceChangedSent = true;
        const esp_gatt_if_t gattsIf = gattsInterface.load();
        if (gattsIf != ESP_GATT_IF_NONE) serviceChangedResult = esp_ble_gatts_send_service_change_indication(gattsIf, peerAddress);
    }
#endif
    // Orden de prioridad en cada pasada: primero la respuesta a una orden (el
    // telefono espera por ella), luego la telemetria si queda hueco (es estado:
    // si no sale, sale la siguiente, mas nueva), y al final se despacha la
    // siguiente orden. Asi la telemetria nunca empuja a una respuesta, y una
    // orden lenta no retrasa la posicion que ya estaba lista.
    sendResponseFrame();
    publishTelemetry();
    if (pending.isEmpty()) dispatchNextRequest();
}

void status(JsonObject out) {
    out["state"] = !ready ? "start_failed" : (!enabled ? "disabled" : (connected ? "connected" : "advertising"));
    out["enabled"] = enabled.load();
    // Sin emparejamiento ni PIN por decisión del propietario: cualquier equipo
    // dentro del alcance puede escribir, incluidas las correcciones.
    out["pairing_required"] = false;
    // 3 desde 0.7.11: RTCM con escritura sin respuesta, salud a 1 Hz siempre y
    // contadores de RTCM en sus bytes 17-19. Todo aditivo: una app de la
    // version 2 sigue funcionando igual.
    out["protocol_version"] = 3;
    // Desde 0.7.12: la direccion anunciada y la generacion de la tabla GATT que
    // la produce (ble_address.h). Si la pila rechazo la aleatoria, lo dice.
    out["gatt_table_generation"] = protocol::kGattTableGeneration;
    if (advertisedAddressIsRandom.load()) {
        char text[18];
        snprintf(text, sizeof text, "%02X:%02X:%02X:%02X:%02X:%02X", advertisedAddress[0], advertisedAddress[1],
                 advertisedAddress[2], advertisedAddress[3], advertisedAddress[4], advertisedAddress[5]);
        out["address"] = text;
        out["address_type"] = "random_static";
        const int stackStatus = randomAddressStatus.load();
        if (stackStatus >= 0 && stackStatus != ESP_BT_STATUS_SUCCESS) out["address_error"] = stackStatus;
    } else {
        out["address"] = nullptr;
        out["address_type"] = "public";
    }
    out["rtcm_write_without_response"] = true;
    out["health_period_ms"] = kHealthPeriodMs;
    const uint16_t interval = connIntervalUnits.load();
    if (connected && interval) out["conn_interval_ms"] = interval * 1.25; else out["conn_interval_ms"] = nullptr;
    out["telemetry_skipped"] = telemetrySkipped.load();
    out["max_loop_gap_ms"] = maxTickGapMs.load();
    out["max_request_dispatch_ms"] = maxDispatchMs.load();
#ifdef TRESVIZO_BLE_SERVICE_CHANGED
    out["service_changed_result"] = int(serviceChangedResult);
#endif
    out["dropped_requests"] = dropped.load();
    // MTU negociado con el telefono conectado (23 = sin negociar) y tramas de
    // respuesta mandadas sin hueco en la controladora (hueco G5).
    out["att_mtu"] = attMtu.load();
    out["response_frames_forced"] = forcedFrames.load();
    out["control_available"] = ready;
    out["rtcm_available"] = gnss_receiver::snapshot().enabled;
    out["rtcm_valid_frames"] = correctionAccepted.load();
    out["rtcm_crc_errors"] = correctionRejected.load();
    out["rtcm_dropped_frames"] = correctionDropped.load();
    out["file_download_available"] = false;
    out["telemetry_hardware_validated"] = false;
}
uint32_t rtcmParserRejected() { return correctionRejected.load(); }
int request(const String& method, JsonVariantConst body, JsonDocument& out) {
    if (method == "GET") { status(out.to<JsonObject>()); return 200; }
    if (method != "POST" || !body.is<JsonObjectConst>() || body.size() != 1) return 400;
    if (!body["enabled"].is<bool>()) return 400;
    const bool next = body["enabled"].as<bool>();
    if (next != enabled) {
        enabled = next;
        if (!settings.putBool("enabled", next)) {
            out["message"] = "No se pudo guardar el ajuste; el cambio se perderá al reiniciar.";
        }
        if (next) advertise = true;
    }
    status(out.to<JsonObject>());
    return 200;
}
}
