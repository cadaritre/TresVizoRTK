#include "base_plan.h"
#include <cassert>
#include <limits>
int main() {
 double arp;
 assert(base_plan::known(0,0,100,2,true,arp) && arp==102);
 assert(base_plan::known(0,0,100,2,false,arp) && arp==100);
 assert(base_plan::known(-90,180,-100,0,true,arp));
 assert(!base_plan::known(91,0,100,2,true,arp));
 assert(!base_plan::known(0,-181,100,2,true,arp));
 assert(!base_plan::known(0,0,30000,2,true,arp));
 assert(!base_plan::known(0,0,100,-1,true,arp));
 assert(!base_plan::known(0,0,std::numeric_limits<double>::quiet_NaN(),0,true,arp));
 assert(base_plan::average(1,0) && base_plan::average(3600,10));
 assert(!base_plan::average(0,0) && !base_plan::average(3601,0) && !base_plan::average(1,-1));
}
