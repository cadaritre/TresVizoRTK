#include "gnss_visible.h"
#include "gnss_control.h"
#include "gnss_receiver.h"
#include "orbit_visibility.h"
#include <Arduino.h>
#include <WiFi.h>
#include <WiFiClient.h>
#include <esp_timer.h>

namespace gnss_visible {
namespace {
// Grupo `gnss` de CelesTrak: unas 170 órbitas, 28 KB. Por HTTP simple (el
// firmware no tiene TLS); se lee línea a línea sin guardar el texto entero.
constexpr const char* kHost = "celestrak.org";
constexpr const char* kPath = "/NORAD/elements/gp.php?GROUP=gnss&FORMAT=tle";
constexpr unsigned kMaxOrbits = 220;
constexpr uint32_t kRefreshMs = 24UL * 3600UL * 1000UL;  // órbitas nuevas cada día
constexpr uint32_t kRetryMs = 5UL * 60UL * 1000UL;       // reintento tras un fallo (CelesTrak pide no insistir)
constexpr uint32_t kComputeMs = 5000;
constexpr uint32_t kFreshMs = 30000;                      // un conteo más viejo no se publica
constexpr uint64_t kPositionFreshUs = 5000000;

// Solo los toca la tarea: descarga y cálculo van en el mismo hilo.
gnss::OrbitElements* orbits = nullptr;
unsigned orbitCount = 0;
// Hora UTC: la cabecera Date de la descarga más el reloj monotónico. Se
// renueva con cada descarga; la deriva del cristal es de segundos al día.
double timeBaseUnix = 0;
int64_t timeBaseUs = 0;
uint32_t downloadedAtMs = 0, lastAttemptMs = 0;
bool attempted = false;

// Lo que se publica, protegido para leerlo desde otras tareas.
portMUX_TYPE lock = portMUX_INITIALIZER_UNLOCKED;
gnss::VisibleCount published;
uint32_t publishedAtMs = 0;
bool havePublished = false;
unsigned publishedOrbits = 0;
double publishedMaskDeg = 5.0;
uint32_t publishedDownloadMs = 0;
const char* orbitState = "sin_descargar";
char lastError[64] = "";

void setError(const char* message) {
    portENTER_CRITICAL(&lock);
    std::strncpy(lastError, message, sizeof(lastError) - 1);
    lastError[sizeof(lastError) - 1] = 0;
    portEXIT_CRITICAL(&lock);
}

bool download() {
    WiFiClient client;
    if (!client.connect(kHost, 80, 5000)) { setError("Sin conexión con celestrak.org"); return false; }
    client.setTimeout(10);  // segundos, en el núcleo Arduino-ESP32 2.x
    client.printf("GET %s HTTP/1.0\r\nHost: %s\r\nUser-Agent: MeridianV\r\nConnection: close\r\n\r\n", kPath, kHost);
    String line = client.readStringUntil('\n');
    if (!line.startsWith("HTTP/1.") || line.indexOf(" 200") < 0) { setError("CelesTrak no respondió 200"); client.stop(); return false; }
    double serverUnix = 0;
    int64_t serverUs = 0;
    for (;;) {
        line = client.readStringUntil('\n');
        line.trim();
        if (!line.length()) break;
        if (line.length() > 5 && line.substring(0, 5).equalsIgnoreCase("date:")) {
            if (gnss::parseHttpDate(line.c_str() + 5, serverUnix)) serverUs = esp_timer_get_time();
        }
    }
    if (!serverUs) { setError("Respuesta sin fecha válida"); client.stop(); return false; }
    auto* fresh = static_cast<gnss::OrbitElements*>(ps_malloc(sizeof(gnss::OrbitElements) * kMaxOrbits));
    if (!fresh) { setError("Sin memoria para las órbitas"); client.stop(); return false; }
    gnss::TleReader reader;
    unsigned count = 0;
    const uint32_t started = millis();
    while ((client.connected() || client.available()) && millis() - started < 30000) {
        if (!client.available()) { delay(10); continue; }
        line = client.readStringUntil('\n');
        gnss::OrbitElements el;
        if (reader.feed(line.c_str(), el) && count < kMaxOrbits) fresh[count++] = el;
    }
    client.stop();
    if (count < 50) { free(fresh); setError("Órbitas incompletas"); return false; }
    free(orbits);
    orbits = fresh;
    orbitCount = count;
    timeBaseUnix = serverUnix;
    timeBaseUs = serverUs;
    downloadedAtMs = millis();
    portENTER_CRITICAL(&lock);
    publishedOrbits = count;
    publishedDownloadMs = downloadedAtMs;
    orbitState = "ok";
    lastError[0] = 0;
    portEXIT_CRITICAL(&lock);
    return true;
}

void compute() {
    if (!orbitCount) return;
    const auto snapshot = gnss_receiver::snapshot();
    const auto& s = snapshot.solution;
    if (!s.has_position || esp_timer_get_time() - s.arrival_us > kPositionFreshUs) return;
    const double now = timeBaseUnix + double(esp_timer_get_time() - timeBaseUs) / 1e6;
    const double height = std::isfinite(s.altitude_msl_m) ? s.altitude_msl_m : 0.0;
    const double mask = gnss_control::elevationMaskDeg();
    const auto count = gnss::countVisible(orbits, orbitCount, now, s.latitude_deg, s.longitude_deg, height, mask);
    portENTER_CRITICAL(&lock);
    published = count;
    publishedAtMs = millis();
    publishedMaskDeg = mask;
    havePublished = true;
    portEXIT_CRITICAL(&lock);
}

void worker(void*) {
    for (;;) {
        const bool due = !attempted || (orbitCount ? millis() - downloadedAtMs > kRefreshMs
                                                   : millis() - lastAttemptMs > kRetryMs);
        if (due && WiFi.status() == WL_CONNECTED) {
            attempted = true;
            lastAttemptMs = millis();
            if (!download() && !orbitCount) {
                portENTER_CRITICAL(&lock);
                orbitState = "error";
                portEXIT_CRITICAL(&lock);
            }
        }
        compute();
        vTaskDelay(pdMS_TO_TICKS(kComputeMs));
    }
}
}  // namespace

void begin() {
    // Pila de 8 KiB: cliente TCP, lectura de líneas y el cálculo en doble precisión.
    if (xTaskCreate(worker, "orbits", 8192, nullptr, 1, nullptr) != pdPASS) setError("No se pudo crear la tarea");
}

bool visible(unsigned& count) {
    portENTER_CRITICAL(&lock);
    const bool fresh = havePublished && millis() - publishedAtMs <= kFreshMs;
    count = fresh ? published.total : 0;
    portEXIT_CRITICAL(&lock);
    return fresh;
}

void status(JsonObject out) {
    portENTER_CRITICAL(&lock);
    const bool fresh = havePublished && millis() - publishedAtMs <= kFreshMs;
    const gnss::VisibleCount count = published;
    const unsigned orbitsLoaded = publishedOrbits;
    const uint32_t downloaded = publishedDownloadMs;
    const double mask = publishedMaskDeg;
    const char* state = orbitState;
    char error[sizeof(lastError)];
    std::memcpy(error, lastError, sizeof(error));
    portEXIT_CRITICAL(&lock);
    out["state"] = state;
    out["source"] = "celestrak_gnss_tle";
    out["orbits"] = orbitsLoaded;
    if (orbitsLoaded) out["age_s"] = (millis() - downloaded) / 1000; else out["age_s"] = nullptr;
    out["error"] = error;
    out["mask_deg"] = mask;
    if (fresh) {
        out["visible"] = count.total;
        JsonObject by = out["by_system"].to<JsonObject>();
        by["gps"] = count.gps; by["glo"] = count.glo; by["gal"] = count.gal; by["bds"] = count.bds; by["qzs"] = count.qzs;
    } else {
        out["visible"] = nullptr;
    }
}
}  // namespace gnss_visible
