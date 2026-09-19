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
    return 0;
}
