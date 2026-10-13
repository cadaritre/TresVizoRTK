// Saludo, latidos y caída del enlace vistos desde el radio (src/usb_session.h).
#include "usb_session.h"
#include <cassert>
#include <cstdio>

using usb_session::Role;
using usb_session::Session;
using usb_session::State;

namespace {
// Avanza de milisegundo en milisegundo contando lo que pide la sesión.
struct Counts { int hellos = 0, statuses = 0, losses = 0; };
Counts advance(Session& s, uint32_t& now, uint32_t ms) {
    Counts c;
    for (uint32_t i = 0; i < ms; ++i) {
        const auto due = s.tick(++now);
        c.hellos += due.hello; c.statuses += due.status; c.losses += due.lost;
    }
    return c;
}
}  // namespace

int run(uint32_t start) {
    Session s;
    uint32_t now = start;
    assert(s.state == State::detached);
    assert(!s.tick(now).hello);                       // sin nada enchufado no se saluda

    // Al conectar se saluda enseguida y luego cada segundo...
    s.attach(now);
    assert(s.tick(now).hello);
    assert(advance(s, now, 999).hellos == 0);
    assert(advance(s, now, 1).hellos == 1);
    // ...10 veces; después cada 5 s (un receptor sin enlace USB no contesta nunca).
    assert(advance(s, now, 8000).hellos == 8);
    assert(s.hellos == 10);
    assert(advance(s, now, 4999).hellos == 0);
    assert(advance(s, now, 1).hellos == 1);

    // Un papel antes de la bienvenida no vale: no se transmite sin saludo aceptado.
    assert(!s.setRole(Role::base, now) && s.role == Role::idle);

    // Bienvenida: enlazado, estado enseguida y cada segundo; ya no se saluda.
    s.welcome(true, now);
    assert(s.linked() && s.links == 1);
    auto due = s.tick(now);
    assert(due.status && !due.hello);
    Counts c = advance(s, now, 1000);
    assert(c.statuses == 1 && c.hellos == 0);

    // Papel: true solo si cambia.
    assert(s.setRole(Role::base, now) && s.role == Role::base);
    assert(!s.setRole(Role::base, now));
    assert(s.setRole(Role::rover, now) && s.role == Role::rover);

    // El papel (1 Hz) es el latido: con él no se cae nunca.
    for (int i = 0; i < 10; ++i) {
        c = advance(s, now, 1000);
        assert(c.losses == 0 && c.statuses == 1);
        s.setRole(Role::rover, now);
    }
    // Otra trama cualquiera también cuenta como latido.
    advance(s, now, 3000);
    s.heard(now);
    assert(advance(s, now, 3500).losses == 0);

    // Sin latido 3.5 s: se cae, el papel vuelve a idle y se saluda otra vez enseguida.
    c = advance(s, now, 1);
    assert(c.losses == 1 && c.hellos == 1);
    assert(s.state == State::greeting && s.role == Role::idle && s.silences == 1);
    s.welcome(true, now);
    assert(s.linked() && s.links == 2);

    // Desconectar: nada más hasta la siguiente conexión.
    s.detach();
    assert(s.state == State::detached && s.role == Role::idle);
    c = advance(s, now, 10000);
    assert(c.hellos == 0 && c.statuses == 0 && c.losses == 0);
    s.welcome(true, now);                              // una bienvenida suelta no enlaza
    assert(s.state == State::detached);

    // Rechazado (p. ej. protocolo que el receptor no entiende): callado hasta desconectar.
    s.attach(now);
    assert(s.tick(now).hello);
    s.welcome(false, now);
    assert(s.state == State::rejected);
    c = advance(s, now, 20000);
    assert(c.hellos == 0 && c.statuses == 0);
    assert(!s.setRole(Role::base, now));
    s.detach();
    s.attach(now);
    assert(s.tick(now).hello && s.hellos == 1);         // la conexión nueva empieza de cero

    assert(usb_session::parseRole("base") == Role::base);
    assert(usb_session::parseRole("rover") == Role::rover);
    assert(usb_session::parseRole("idle") == Role::idle);
    assert(usb_session::parseRole("transmit") == Role::idle);   // lo desconocido no transmite
    assert(usb_session::parseRole(nullptr) == Role::idle);
    return 0;
}

int main() {
    run(0);
    run(0xFFFFFFFFu - 25000);   // el reloj de millis() da la vuelta a los 49.7 días
    std::puts("usb_session_test OK");
    return 0;
}
