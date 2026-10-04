#pragma once
#include <cstdint>

namespace display_boot {
// El plazo pertenece al arranque, no a cada detección/reintento de la OLED.
class Window {
public:
    Window(uint32_t started, uint32_t duration) : started_(started), duration_(duration) {}
    bool active(uint32_t now, bool interrupted = false) {
        if (interrupted || uint32_t(now - started_) >= duration_) finished_ = true;
        return !finished_;
    }
private:
    uint32_t started_, duration_;
    bool finished_ = false;
};
}
