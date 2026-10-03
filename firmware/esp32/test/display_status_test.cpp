#include "display_status.h"
#include <cassert>
#include <cstring>
#include <iostream>

int main() {
    gnss_receiver::Snapshot receiver;
    auto text=display_status::build(receiver,10000000,0,UINT32_MAX,"card_missing");
    assert(!std::strcmp(text.fix,"ESPERA"));
    assert(!std::strcmp(text.satellites,"SAT --"));
    assert(!std::strcmp(text.storage,"MEM INT. NO DISP."));
    text=display_status::build(receiver,10000000,0,UINT32_MAX,"idle");
    assert(!std::strcmp(text.storage,"MEM INT. LISTA"));
    receiver.enabled=true;receiver.accepted=1;
    receiver.solution.arrival_us=10000000;
    receiver.solution.has_position=true;receiver.solution.quality=4;
    receiver.solution.has_satellites=true;receiver.solution.satellites=18;
    text=display_status::build(receiver,11000000,2,1200,"recording");
    assert(!std::strcmp(text.fix,"FIX"));
    assert(!std::strcmp(text.satellites,"SAT 18"));
    assert(!std::strcmp(text.corrections,"RTCM NTRIP 1.2s"));
    assert(!std::strcmp(text.storage,"MEM INT. GRABANDO"));
    // El FIX y sus satélites desaparecen al caducar, aun con OLED y Wi-Fi vivos.
    text=display_status::build(receiver,12000001,2,UINT32_MAX,"closing");
    assert(!std::strcmp(text.fix,"ANTIGUO"));
    assert(!std::strcmp(text.satellites,"SAT --"));
    assert(!std::strcmp(text.corrections,"RTCM NTRIP --"));
    assert(!std::strcmp(text.storage,"MEM INT. CERRANDO"));
    receiver.solution.has_position=false;receiver.solution.quality=0;
    text=display_status::build(receiver,11000000,1,150000,"partial");
    assert(!std::strcmp(text.fix,"SIN FIX"));
    assert(!std::strcmp(text.corrections,"RTCM BLE >99s"));
    assert(!std::strcmp(text.storage,"MEM INT. REVISAR"));
    // 128 px: hasta 21 caracteres a 6 px; la calidad usa fuente doble.
    assert(std::strlen(text.fix)*12<=128);
    for(auto row:{text.satellites,text.corrections,text.storage}) assert(std::strlen(row)*6<=128);
    std::cout<<"display_status: frescura, perdida de FIX, RTCM y SD OK\n";
}
