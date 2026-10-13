#pragma once

#include <cstddef>
#include <cstdint>
#include <cstring>

namespace config_rules {
constexpr size_t kMaxNameBytes = 32;
constexpr size_t kMaxSsidBytes = 32;
constexpr size_t kMaxPasswordBytes = 63;
constexpr size_t kMaxRequestBytes = 1024;

inline bool deviceName(const char* value) {
    if (!value) return false;
    const size_t length = std::strlen(value);
    if (!length || length > kMaxNameBytes || value[0] == ' ' || value[length - 1] == ' ') return false;
    for (size_t i = 0; i < length; ++i) {
        const unsigned char c = value[i];
        if (!((c >= 'a' && c <= 'z') || (c >= 'A' && c <= 'Z') ||
              (c >= '0' && c <= '9') || c == ' ' || c == '-' || c == '_')) return false;
    }
    return true;
}

inline bool ssid(const char* value) {
    if (!value || std::strlen(value) > kMaxSsidBytes) return false;
    for (const unsigned char* p = reinterpret_cast<const unsigned char*>(value); *p; ++p) {
        if (*p < 32 || *p == 127) return false;
    }
    return true;
}

inline bool password(const char* value) {
    if (!value) return false;
    const size_t length = std::strlen(value);
    if (length < 8 || length > kMaxPasswordBytes) return false;
    for (size_t i = 0; i < length; ++i) {
        if (static_cast<unsigned char>(value[i]) < 32 || static_cast<unsigned char>(value[i]) > 126) return false;
    }
    return true;
}

inline bool refresh(uint32_t value) { return value == 1000 || value == 2000 || value == 5000; }
inline bool elapsed(uint32_t now, uint32_t then, uint32_t period) { return now - then >= period; }

// Espera entre escaneos automáticos de la red externa cuando no se ve ninguna de
// las guardadas. Cada escaneo recorre los canales y **corta el AP propio unos
// segundos**: en campo, con las redes guardadas fuera de alcance, el teléfono
// conectado al AP del equipo perdía el panel y el WebSocket cada 30 s.
//
// 30 s tras el primer intento fallido, luego el doble hasta 4 min. Con alguien
// conectado al AP, nunca menos de 2 min. Una decisión del usuario (guardar,
// conectar, escanear) o un enlace conseguido vuelve a empezar desde 30 s.
constexpr uint32_t kRescanBaseMs = 30000;
constexpr uint32_t kRescanMaxMs = 240000;
constexpr uint32_t kRescanWithApClientsMs = 120000;
inline uint32_t rescanDelayMs(uint32_t misses, bool apClients) {
    uint32_t delay = kRescanBaseMs;
    for (uint32_t i = 1; i < misses && delay < kRescanMaxMs; ++i) delay *= 2;
    if (delay > kRescanMaxMs) delay = kRescanMaxMs;
    if (apClients && delay < kRescanWithApClientsMs) delay = kRescanWithApClientsMs;
    return delay;
}

// Trabajo automático con la red externa (escanear, unirse, reconectar). Con el
// apagado en curso no se hace nada: un escaneo o un `WiFi.begin` vuelven a
// encender la radio Wi-Fi. Eso incluye «sigue alimentado» (MeridianV con USB) y
// «solo carga» del MeridianVI, que apaga el Wi-Fi a propósito (spec §17.5): con
// redes guardadas, el siguiente escaneo lo volvía a encender.
inline bool stationWorkAllowed(bool shutdownPending) { return !shutdownPending; }
inline bool startStationScan(bool shutdownPending, bool networksSaved, bool paused, bool scanRunning,
                             bool connected, bool joinRequested, bool backoffElapsed) {
    if (!stationWorkAllowed(shutdownPending) || !networksSaved || paused || scanRunning || connected) return false;
    return joinRequested || backoffElapsed;
}
}
