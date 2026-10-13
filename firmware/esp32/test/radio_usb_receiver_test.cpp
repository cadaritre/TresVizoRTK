// El enlace del radio externo visto desde el MeridianV (lib/protocol/src/radio_usb_receiver.h).
#include "radio_usb_receiver.h"
#include <cassert>
#include <cstdio>

using radio_usb::LinkRole;
using radio_usb::ReceiverSession;

namespace {
struct Counts { int roles = 0, changes = 0, losses = 0; };
Counts advance(ReceiverSession& s, LinkRole wanted, uint32_t& now, uint32_t ms) {
    Counts c;
    for (uint32_t i = 0; i < ms; ++i) {
        const auto due = s.tick(wanted, ++now);
        c.roles += due.role; c.changes += due.changed; c.losses += due.lost;
    }
    return c;
}

void run(uint32_t start) {
    ReceiverSession s;
    uint32_t now = start;
    // Sin saludo no hay enlace ni papel: un computador en el USB no recibe nada.
    assert(!s.linked && s.role() == LinkRole::idle);
    assert(advance(s, LinkRole::base, now, 5000).roles == 0);

    // Saludo sin protocolo común (0 o ausente): se rechaza y no se enlaza.
    assert(s.hello(0, now) == 0 && !s.linked && s.refused == 1);
    assert(advance(s, LinkRole::base, now, 2000).roles == 0);

    // Saludo de un radio 1: enlazado; el papel sale enseguida y luego cada segundo.
    assert(s.hello(1, now) == 1 && s.linked && s.links == 1);
    assert(s.role() == LinkRole::idle);                  // todavía no se le dijo
    auto due = s.tick(LinkRole::rover, now);
    assert(due.role && due.changed && s.role() == LinkRole::rover);
    for (int i = 0; i < 3; ++i) {
        const Counts c = advance(s, LinkRole::rover, now, 1000);
        assert(c.roles == 1 && c.changes == 0 && c.losses == 0);
        s.heard(now);                                    // su `status` cada segundo
    }
    // El modo cambia: el papel sale en la misma vuelta, sin esperar al segundo.
    due = s.tick(LinkRole::base, ++now);
    assert(due.role && due.changed && s.role() == LinkRole::base);

    // Un radio que habla un protocolo más nuevo: se usa el de este firmware.
    assert(s.hello(7, now) == radio_usb::kProtocol && s.links == 2);
    assert(s.role() == LinkRole::idle);                  // cada saludo empieza de cero
    assert(s.tick(LinkRole::base, now).changed);

    // Sin nada del radio 3.5 s: se cae, el papel vuelve a idle y no se manda más.
    Counts c = advance(s, LinkRole::base, now, radio_usb::kSilenceTimeoutMs);
    assert(c.losses == 0 && s.linked);
    c = advance(s, LinkRole::base, now, 1);
    assert(c.losses == 1 && !s.linked && s.silences == 1 && s.role() == LinkRole::idle);
    assert(advance(s, LinkRole::base, now, 5000).roles == 0);
    s.heard(now);                                        // una trama suelta no enlaza
    assert(!s.linked);

    // Y un saludo nuevo lo vuelve a enlazar.
    assert(s.hello(1, now) == 1 && s.linked && s.links == 3);
}
}  // namespace

int main() {
    run(0);
    run(0xFFFFFFFFu - 6000);   // el reloj de millis() da la vuelta
    std::puts("radio_usb_receiver_test OK");
    return 0;
}
