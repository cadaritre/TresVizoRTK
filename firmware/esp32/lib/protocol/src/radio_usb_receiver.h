#pragma once
#include <cstdint>
#include "radio_usb.h"

namespace radio_usb {
// El enlace del radio LoRa externo visto desde el MeridianV (docs/radio/USB_LINK.md §4–§8).
// Sin Arduino ni JSON: src/radio_module.cpp le pasa lo que llega por el USB y hace lo
// que pida `tick`. Se prueba con g++ (test/radio_usb_receiver_test.cpp).
//
// Un `hello` válido enlaza (o vuelve a enlazar: el radio se reinició o lo reconectaron).
// Enlazado, el papel sale enseguida, al cambiar y cada segundo (es el latido del
// MeridianV); sin ninguna trama del radio durante kSilenceTimeoutMs, el enlace se cae.

enum class LinkRole : uint8_t { idle, base, rover };
inline const char* linkRoleName(LinkRole role) {
    return role == LinkRole::base ? "base" : role == LinkRole::rover ? "rover" : "idle";
}

// Versión más baja del juego de mensajes que entiende este firmware.
constexpr int kMinProtocol = 1;

class ReceiverSession {
    uint32_t lastHeardMs = 0, nextRoleMs = 0;
    LinkRole told = LinkRole::idle;
    bool roleSent = false;
public:
    bool linked = false;
    uint32_t links = 0;         // saludos aceptados
    uint32_t refused = 0;       // saludos sin protocolo común
    uint32_t silences = 0;      // enlaces caídos por falta de latido

    // `hello` con el protocolo más alto del radio. Devuelve el que se usará (para
    // `welcome`) o 0 si no hay uno común: entonces se contesta `accepted: false`.
    int hello(int radioProtocol, uint32_t now) {
        const int agreed = radioProtocol < kProtocol ? radioProtocol : kProtocol;
        if (agreed < kMinProtocol) { linked = false; roleSent = false; ++refused; return 0; }
        linked = true;
        ++links;
        lastHeardMs = now;
        roleSent = false;           // el papel se le dice otra vez, enseguida
        told = LinkRole::idle;
        return agreed;
    }

    // Cualquier otra trama válida del radio (`status`, `config_ack`…).
    void heard(uint32_t now) { if (linked) lastHeardMs = now; }

    struct Due {
        bool role = false;      // mandar `role` con role()
        bool changed = false;   // ...y es distinto del último que se le dijo
        bool lost = false;      // el enlace se acaba de caer
    };
    // `wanted`: el papel según el modo del receptor en este momento.
    Due tick(LinkRole wanted, uint32_t now) {
        Due out;
        if (!linked) return out;
        if (now - lastHeardMs > kSilenceTimeoutMs) {
            linked = false; roleSent = false; told = LinkRole::idle;
            ++silences;
            out.lost = true;
            return out;
        }
        out.changed = !roleSent || wanted != told;
        if (out.changed || static_cast<int32_t>(now - nextRoleMs) >= 0) {
            out.role = true;
            told = wanted;
            roleSent = true;
            nextRoleMs = now + kRolePeriodMs;
        }
        return out;
    }

    // El papel que tiene el radio según lo que se le dijo (idle sin enlace).
    LinkRole role() const { return linked && roleSent ? told : LinkRole::idle; }
};
}  // namespace radio_usb
