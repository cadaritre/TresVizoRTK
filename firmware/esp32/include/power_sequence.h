#pragma once
#include <stdint.h>
namespace power_sequence {
// Sólo el hilo del instrumento cambia esta secuencia.
struct Button {
    bool armed=false, previous=false;
    uint32_t changed=0;
    bool held(bool pressed,uint32_t now) {
        if(pressed!=previous){previous=pressed;changed=now;}
        if(!pressed && uint32_t(now-changed)>=30)armed=true;
        return armed && pressed && uint32_t(now-changed)>=2000;
    }
    void consumed(){armed=false;}
};
}
