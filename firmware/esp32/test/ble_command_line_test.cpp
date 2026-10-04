#include "ble_command_line.h"
#include <cassert>
#include <string>
#include <vector>
#include <cstdio>

int main() {
    protocol::BleCommandLine parser;
    std::vector<std::string> received;
    auto accept = [&](const char* s, size_t n) { received.emplace_back(s, n); };
    auto feed = [&](const std::string& s, uint32_t time) {
        unsigned rejected = 0;
        for (char c : s) rejected += parser.feed(c, time, accept);
        return rejected;
    };
    assert(feed(std::string(1024, 'a') + "\r\n", 0) == 0);
    assert(received.size() == 1 && received.back().size() == 1024);
    assert(feed(std::string(1025, 'b') + "\n", 100) == 1);
    assert(received.size() == 1);
    feed("inicio", UINT32_MAX - 100);
    // Caso visto en el equipo: 1025 B en escrituras pequeñas durante >5 s.
    // También un sufijo JSON válido debe descartarse completo.
    assert(feed("{\"id\":1}\n", 5000) == 1);
    assert(received.size() == 1);
    assert(feed("{\"id\":2}\n", 5010) == 0);
    assert(received.back() == "{\"id\":2}");
    assert(feed(std::string("abc\0def\n", 8), 5020) == 1);
    assert(received.size() == 2);
    feed("parcial", 5100);
    parser.reset(); // desconexión: la sesión nueva sí empieza de cero
    feed("nueva\n", 5101);
    assert(received.back() == "nueva" && received.size() == 3);
    assert(feed("\n", 5200) == 1);
    puts("ble_command_line: OK");
}
