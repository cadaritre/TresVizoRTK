#pragma once
#include <cstdint>
#include <cstring>
#include "radio_usb.h"

namespace usb_session {
// El enlace visto desde el radio (docs/radio/USB_LINK.md, «Saludo» y «Tiempos»).
// Sin Arduino ni JSON: main.cpp le pasa los eventos ya leídos y hace lo que pida
// `tick`. Se prueba con g++ (firmware/radio/test/usb_session_test.cpp).
//
//   detached ──conexión USB──▶ greeting ──welcome aceptado──▶ linked
//       ▲                         │  ▲                           │
//       │                         │  └──sin latido 3.5 s─────────┘
//       └──────desconexión────────┴── welcome rechazado ──▶ rejected (hasta desconectar)
//
// Solo en `linked` hay papel distinto de idle: sin saludo aceptado el radio no
// transmite nada ni entrega correcciones, sea lo que sea lo que tenga enchufado.

enum class Role : uint8_t { idle, base, rover };
inline const char* roleName(Role role) {
    return role == Role::base ? "base" : role == Role::rover ? "rover" : "idle";
}
// Papel recibido del receptor; lo desconocido es idle (no transmitir).
inline Role parseRole(const char* name) {
    if (name && !std::strcmp(name, "base")) return Role::base;
    if (name && !std::strcmp(name, "rover")) return Role::rover;
    return Role::idle;
}

enum class State : uint8_t { detached, greeting, linked, rejected };
inline const char* stateName(State state) {
    switch (state) {
        case State::greeting: return "greeting";
        case State::linked: return "linked";
        case State::rejected: return "rejected";
        default: return "detached";
    }
}

class Session {
    uint32_t nextHelloMs = 0, nextStatusMs = 0, lastHeardMs = 0;
    static bool due(uint32_t now, uint32_t at) { return static_cast<int32_t>(now - at) >= 0; }
    void greet(uint32_t now) {
        state = State::greeting;
        role = Role::idle;
        hellos = 0;
        nextHelloMs = now;
    }
public:
    State state = State::detached;
    Role role = Role::idle;
    uint32_t hellos = 0;        // saludos de esta conexión sin respuesta
    uint32_t links = 0;         // veces que se aceptó el saludo
    uint32_t silences = 0;      // enlaces caídos por falta de latido

    bool linked() const { return state == State::linked; }

    // Se abrió un dispositivo CDC: a saludar ya.
    void attach(uint32_t now) { greet(now); }
    void detach() { state = State::detached; role = Role::idle; }

    // `welcome` del receptor. Aceptado: enlazado y estado enseguida. Rechazado (p. ej.
    // protocolo que no entiende): callado hasta que lo desconecten.
    void welcome(bool accepted, uint32_t now) {
        if (state != State::greeting && state != State::linked) return;
        if (!accepted) { state = State::rejected; role = Role::idle; return; }
        if (state == State::greeting) { state = State::linked; ++links; nextStatusMs = now; }
        lastHeardMs = now;
    }

    // Cualquier trama válida del enlace que llegue del receptor estando enlazado.
    void heard(uint32_t now) { if (state == State::linked) lastHeardMs = now; }

    // `role` del receptor. Devuelve true si cambia el papel (main.cpp reconfigura la radio).
    bool setRole(Role next, uint32_t now) {
        if (state != State::linked) return false;
        lastHeardMs = now;
        if (next == role) return false;
        role = next;
        return true;
    }

    struct Due {
        bool hello = false;     // mandar `hello`
        bool status = false;    // mandar `status`
        bool lost = false;      // el enlace se acaba de caer (el papel volvió a idle)
    };
    Due tick(uint32_t now) {
        Due out;
        if (state == State::linked && now - lastHeardMs > radio_usb::kSilenceTimeoutMs) {
            ++silences;
            out.lost = true;
            greet(now);
        }
        if (state == State::greeting && due(now, nextHelloMs)) {
            out.hello = true;
            ++hellos;
            nextHelloMs = now + (hellos < radio_usb::kHelloFastTries ? radio_usb::kHelloPeriodMs
                                                                      : radio_usb::kHelloSlowPeriodMs);
        }
        if (state == State::linked && due(now, nextStatusMs)) {
            out.status = true;
            nextStatusMs = now + radio_usb::kStatusPeriodMs;
        }
        return out;
    }
};
}  // namespace usb_session
