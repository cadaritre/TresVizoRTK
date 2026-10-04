#pragma once
#include <cstddef>
#include <cstdint>

namespace protocol {
class BleCommandLine {
public:
    void reset() { length_ = 0; startedLine_ = false; discard_ = false; }
    // true: se descartó una línea. Tras vencer o desbordarse se consume hasta
    // LF: ningún sufijo se convierte accidentalmente en una orden nueva.
    template<class OnLine>
    bool feed(char byte, uint32_t now, OnLine onLine) {
        if (!startedLine_) { startedLine_ = true; started_ = now; }
        if (uint32_t(now - started_) > 5000) discard_ = true;
        if (byte == '\n') {
            const bool rejected = discard_ || !length_;
            if (!rejected) onLine(buffer_, length_);
            reset();
            return rejected;
        }
        if (byte == '\0') discard_ = true;
        else if (byte != '\r' && !discard_) {
            if (length_ < sizeof(buffer_)) buffer_[length_++] = byte;
            else discard_ = true;
        }
        return false;
    }
private:
    char buffer_[1024];
    size_t length_ = 0;
    uint32_t started_ = 0;
    bool startedLine_ = false, discard_ = false;
};
}
