#include <cassert>
#include <cstdint>
#include "config_rules.h"

int main() {
    using namespace config_rules;
    assert(deviceName("TresVizo RTK-01"));
    assert(deviceName("12345678901234567890123456789012"));
    assert(!deviceName("123456789012345678901234567890123"));
    assert(!deviceName(""));
    assert(!deviceName(nullptr));
    assert(!deviceName(" equipo"));
    assert(!deviceName("equipo "));
    assert(!deviceName("equipo\n"));
    assert(!deviceName("<script>"));
    assert(ssid("Teléfono"));
    assert(ssid(""));
    assert(!ssid("SSID\x01"));
    assert(!ssid("123456789012345678901234567890123"));
    assert(password("test-123"));
    assert(!password("1234567"));
    assert(!password(""));
    assert(!password("test\n1234"));
    assert(!password("clave-áé"));
    assert(refresh(1000) && refresh(2000) && refresh(5000));
    assert(!refresh(0) && !refresh(999) && !refresh(1001));
    assert(!elapsed(9, 0xfffffff0U, 30));
    assert(elapsed(14, 0xfffffff0U, 30));
    // Reintentos de la red externa: 30 s, luego el doble hasta 4 min; con
    // alguien en el AP propio, al menos 2 min.
    assert(rescanDelayMs(0, false) == 30000 && rescanDelayMs(1, false) == 30000);
    assert(rescanDelayMs(2, false) == 60000 && rescanDelayMs(3, false) == 120000);
    assert(rescanDelayMs(4, false) == 240000 && rescanDelayMs(40, false) == 240000);
    assert(rescanDelayMs(0, true) == 120000 && rescanDelayMs(2, true) == 120000);
    assert(rescanDelayMs(4, true) == 240000 && rescanDelayMs(UINT32_MAX, true) == 240000);
    return 0;
}
