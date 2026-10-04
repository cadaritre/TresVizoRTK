#include "command_handoff.h"
#include <cassert>
#include <cstdio>
#include <string>
using H = protocol::CommandHandoff;
int main() {
    H h;
    assert(h.poll(0)==H::Result::Ready);
    // La orden nueva no debe consumir el ACK de la vieja, ni siquiera si son iguales.
    assert(h.begin("MASK 5.00",false,false,100));
    h.consume("$command,MASK 15.00,response: OK");
    assert(h.poll(110)==H::Result::Waiting);
    h.consume("$command,MASK 5.00,response: OK");
    assert(h.poll(111)==H::Result::Ready);
    assert(!h.active());
    // Dos sustituciones mientras espera MODE conservan el vuelo original.
    assert(h.begin("MODE",false,false,200));
    assert(h.begin("SAVECONFIG",true,true,201));
    h.consume("$command,MODE,response: OK");
    assert(h.poll(210)==H::Result::Waiting);
    h.consume("#MODE,header;MODE BASE 1,");
    assert(h.poll(211)==H::Result::Ready);
    // El orden ACK/lectura puede invertirse; error del receptor no exige lectura.
    h.begin("VERSIONA",false,false,300);
    h.consume("#VERSIONA,header;UM980,");
    assert(h.poll(301)==H::Result::Waiting);
    h.consume("$command,VERSIONA,response: OK");
    assert(h.poll(302)==H::Result::Ready);
    h.begin("MASK",false,false,400);
    h.consume("$command,MASK,response: INVALID");
    assert(h.poll(401)==H::Result::Ready);
    // CONFIG puede seguir enviando líneas tras el ACK. Se conserva su ventana.
    h.begin("CONFIG",true,false,500);
    assert(h.poll(1200)==H::Result::Waiting);
    assert(h.poll(1201)==H::Result::Ready);
    // El receptor sin respuesta falla acotado, también al desbordar millis().
    h.begin("MODE",false,false,UINT32_MAX-100);
    assert(h.poll(3899)==H::Result::Waiting);
    assert(h.poll(3900)==H::Result::TimedOut);
    assert(!h.active());
    std::string huge(192,'X');assert(!h.begin(huge.c_str(),false,false,0));
    // Entrada corta/ajena no produce accesos fuera de rango.
    for(const char* line:{"", "$", "$command,", "$command,M", "$command,MODE", "#MODE"}) {
        H other;other.begin("MODE",false,false,1);other.consume(line);
        assert(other.poll(2)==H::Result::Waiting);
    }
    std::puts("command_handoff: OK");
}
