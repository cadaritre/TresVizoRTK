#include "base_plan.h"
#include <cassert>
#include <limits>
int main() {
 double arp;
 // La altura recibida es siempre la del punto en el suelo: la antena se suma
 // siempre. Desde 0.6.2 no se pregunta a qué punto corresponde la altura.
 assert(base_plan::known(0,0,100,2,arp) && arp==102);
 assert(base_plan::known(0,0,100,0,arp) && arp==100);
 assert(base_plan::known(-90,180,-100,0,arp));
 assert(!base_plan::known(91,0,100,2,arp));
 assert(!base_plan::known(0,-181,100,2,arp));
 assert(!base_plan::known(0,0,30000,2,arp));
 assert(!base_plan::known(0,0,100,-1,arp));
 assert(!base_plan::known(0,0,std::numeric_limits<double>::quiet_NaN(),0,arp));
 // El case es una constante declarada, no medida sobre la carcasa real.
 assert(base_plan::kCaseOffsetM > 0 && base_plan::kCaseOffsetM < 1);
 assert(base_plan::average(1,0) && base_plan::average(3600,10));
 assert(!base_plan::average(0,0) && !base_plan::average(3601,0) && !base_plan::average(1,-1));
}
