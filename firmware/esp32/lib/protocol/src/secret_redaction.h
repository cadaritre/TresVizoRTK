#pragma once
#include <ArduinoJson.h>
#include <cstddef>
#include <cstring>

namespace protocol {
// Recorte de credenciales en las respuestas que salen por Bluetooth.
//
// **Por que.** BLE va sin emparejamiento ni cifrado (decision del propietario
// desde 0.6.2): cualquiera al alcance se conecta y lee lo que el equipo
// contesta. Hasta 0.7.12, `GET /api/config` por BLE daba la contrasena del
// Wi-Fi propio (`ap_password`), y con ella se llegaba al HTTP, que no pide
// clave. Por HTTP, USB y WebSocket sigue saliendo: el panel la lee y la
// reenvia al guardar, y quien ya esta en esa red ya la tiene.
//
// **Regla.** Se quita toda clave cuyo nombre denota una credencial
// (`password`, `pass`, `cpass`, `psk`, `secret`, o que termine en `_password`,
// `_pass`, `_psk` o `_secret`), a cualquier profundidad, **salvo que su valor
// sea booleano**: `has_password` dice si hay credencial guardada, no cual es.
// La regla va por nombre y no por lista cerrada para que una credencial nueva
// que alguien anada a una respuesta no salga por BLE sin que nadie lo decida.
// `ap_password_saved` y `wifi_password_saved` no terminan en `_password` y
// ademas son booleanos.

// Profundidad maxima que se recorre. Las respuestas del equipo no pasan de 4
// niveles (`/api/status`); si alguna se pasara, el subarbol se borra entero en
// vez de salir sin revisar.
constexpr size_t kMaxRedactionDepth = 16;

namespace detail {
inline bool endsWith(const char* text, size_t length, const char* suffix) {
    const size_t tail = std::strlen(suffix);
    return length >= tail && std::memcmp(text + length - tail, suffix, tail) == 0;
}
}  // namespace detail

// El nombre de clave denota una credencial en claro.
inline bool isSecretKeyName(const char* name) {
    if (!name) return false;
    static const char* const exact[] = {"password", "pass", "cpass", "psk", "secret"};
    static const char* const suffixes[] = {"_password", "_pass", "_psk", "_secret"};
    for (const char* candidate : exact)
        if (std::strcmp(name, candidate) == 0) return true;
    const size_t length = std::strlen(name);
    for (const char* suffix : suffixes)
        if (detail::endsWith(name, length, suffix)) return true;
    return false;
}

// Quita las credenciales de `value` y de todo lo que cuelga de el.
inline void stripSecrets(JsonVariant value, size_t depth = 0) {
    if (depth > kMaxRedactionDepth) {
        value.set(nullptr);
        return;
    }
    JsonObject object = value.as<JsonObject>();
    if (!object.isNull()) {
        // Quitar invalida el iterador: se quita una y se vuelve a empezar. Los
        // objetos tienen pocas claves y casi nunca hay nada que quitar.
        bool removed = true;
        while (removed) {
            removed = false;
            for (JsonObject::iterator it = object.begin(); it != object.end(); ++it) {
                if (isSecretKeyName(it->key().c_str()) && !it->value().is<bool>()) {
                    object.remove(it);
                    removed = true;
                    break;
                }
            }
        }
        for (JsonPair pair : object) stripSecrets(pair.value(), depth + 1);
        return;
    }
    JsonArray array = value.as<JsonArray>();
    if (!array.isNull())
        for (JsonVariant item : array) stripSecrets(item, depth + 1);
}
}  // namespace protocol
