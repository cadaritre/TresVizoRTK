#pragma once
#include <ArduinoJson.h>
#include <cstddef>
#include <cstring>

namespace protocol {
// Deja en un JSON solo las claves de una lista de rutas («solution.fix»,
// «alerts[].code»…) y quita todo lo demás, a cualquier profundidad.
//
// **Para qué.** Por Bluetooth una respuesta no puede pasar de 4096 bytes (las dos
// apps descartan lo que pase de ahí) y `/api/status` creció con el 0.8.0 y el
// módulo de radio hasta ≈5 kB. Por BLE solo hace falta lo que las apps leen, que
// es el contrato (`docs/api-contract/app-contract.json`, ≈3.4 kB); por Wi-Fi y en
// el panel la respuesta sigue completa. Así, lo que se añada al estado en el futuro
// no vuelve a romper el estado por Bluetooth.
//
// Una clave se conserva si alguna ruta de la lista es ella misma o empieza por
// ella («solution» se conserva por «solution.fix»). Un arreglo usa «[]»: sus
// elementos se recortan con las rutas «x[].…». Sin ArduinoJson ajeno al proyecto:
// se prueba con g++ en test/json_allowlist_test.cpp.
namespace detail {
inline bool allowed(const char* path, size_t pathLength, const char* const* paths, size_t count) {
    for (size_t i = 0; i < count; ++i) {
        const char* candidate = paths[i];
        if (std::strncmp(candidate, path, pathLength) != 0) continue;
        const char next = candidate[pathLength];
        if (next == '\0' || next == '.' || next == '[') return true;
    }
    return false;
}

constexpr size_t kMaxPathBytes = 160;   // la ruta más larga del contrato ronda 60

inline void keepOnly(JsonVariant node, char* path, size_t length, const char* const* paths, size_t count) {
    if (node.is<JsonObject>()) {
        JsonObject object = node.as<JsonObject>();
        // Primero se decide y luego se quita: quitar mientras se recorre invalida el iterador.
        const char* doomed[64];
        size_t doomedCount = 0;
        bool more = true;
        while (more) {
            more = false; doomedCount = 0;
            for (JsonPair member : object) {
                const char* key = member.key().c_str();
                const size_t keyLength = std::strlen(key);
                const size_t childLength = length + (length ? 1 : 0) + keyLength;
                bool keep = false;
                if (childLength < kMaxPathBytes) {
                    char* cursor = path + length;
                    if (length) *cursor++ = '.';
                    std::memcpy(cursor, key, keyLength);
                    path[childLength] = '\0';
                    keep = allowed(path, childLength, paths, count);
                    if (keep) keepOnly(member.value(), path, childLength, paths, count);
                    path[length] = '\0';
                }
                if (!keep) {
                    if (doomedCount == sizeof(doomed) / sizeof(doomed[0])) { more = true; break; }
                    doomed[doomedCount++] = key;
                }
            }
            for (size_t i = 0; i < doomedCount; ++i) object.remove(doomed[i]);
        }
    } else if (node.is<JsonArray>()) {
        if (length + 2 >= kMaxPathBytes) return;
        path[length] = '['; path[length + 1] = ']'; path[length + 2] = '\0';
        for (JsonVariant element : node.as<JsonArray>()) keepOnly(element, path, length + 2, paths, count);
        path[length] = '\0';
    }
}
}  // namespace detail

inline void keepOnly(JsonVariant root, const char* const* paths, size_t count) {
    char path[detail::kMaxPathBytes] = {};
    detail::keepOnly(root, path, 0, paths, count);
}
}  // namespace protocol
