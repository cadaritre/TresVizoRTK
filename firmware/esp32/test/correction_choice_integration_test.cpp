#include "host/Arduino.h"
#include "../src/correction_router.cpp"
namespace gnss_receiver {Snapshot snapshot(){Snapshot s;s.enabled=true;return s;}bool enqueueCorrections(const uint8_t*,size_t){return true;}}
namespace radio_module {bool connected(){return false;}}
int main(){
 correction_router::begin();
 assert(correction_router::ntripAllowed()); // instalación anterior sin elección guardada
 assert(correction_router::choose("none"));
 assert(!correction_router::ntripAllowed());
 assert(correction_router::store.isKey("chosen")); // None -> None también se persiste
 correction_router::choiceKnown=false;correction_router::begin();
 assert(!correction_router::ntripAllowed());
 correction_router::choose("ntrip");assert(correction_router::ntripAllowed());
 correction_router::lastAccepted=1;hostMillis=100;
 assert(correction_router::ageMs()==99);
 correction_router::choose("ble");assert(!correction_router::ntripAllowed());
 assert(correction_router::ageMs()==UINT32_MAX); // no hereda edad de NTRIP
 const uint32_t generation=correction_router::generation();
 assert(!correction_router::choose("unknown"));
 assert(correction_router::generation()==generation && correction_router::bleChosen());
 std::puts("correction_choice_integration: OK");
}
