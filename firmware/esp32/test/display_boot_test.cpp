#include "display_boot.h"
#include <cassert>
#include <iostream>

int main() {
    display_boot::Window boot(120,10000);
    assert(boot.active(120));
    assert(boot.active(10119));
    assert(!boot.active(10120));
    // No reaparece tras reconectar la OLED, un retraso ni una vuelta de millis.
    assert(!boot.active(14000));
    assert(!boot.active(120));
    display_boot::Window lateDisplay(120,10000);
    assert(!lateDisplay.active(12000)); // OLED detectada después del plazo.
    display_boot::Window retries(120,10000);
    for (uint32_t attempt=120;attempt<10120;attempt+=1000) assert(retries.active(attempt));
    assert(!retries.active(10120)); // Los reintentos no compran otros 10 segundos.
    display_boot::Window interrupted(120,10000);
    assert(interrupted.active(200));
    assert(!interrupted.active(201,true));
    assert(!interrupted.active(202));
    display_boot::Window wrap(UINT32_MAX-4999,10000);
    assert(wrap.active(4999));
    assert(!wrap.active(5000));
    std::cout << "display_boot: plazo, reintentos, apagado y rollover OK\n";
}
