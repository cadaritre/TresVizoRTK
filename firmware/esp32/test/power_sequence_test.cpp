#include "power_sequence.h"
#include <cassert>
#include <cstdint>
int main(){
 power_sequence::Button b;
 assert(!b.held(true,0));assert(!b.held(true,5000)); // Encendido sostenido.
 assert(!b.held(false,5001));assert(!b.held(false,5020));
 assert(!b.held(true,5021));assert(!b.held(true,8000)); // Rebote no arma.
 assert(!b.held(false,8001));assert(!b.held(false,8031));
 assert(!b.held(true,8100));assert(!b.held(true,10099));
 assert(b.held(true,10100));b.consumed();assert(!b.held(true,13000));
 power_sequence::Button wrap;
 wrap.armed=true;wrap.previous=true;wrap.changed=UINT32_MAX-999;
 assert(!wrap.held(true,999));assert(wrap.held(true,1000));
}
