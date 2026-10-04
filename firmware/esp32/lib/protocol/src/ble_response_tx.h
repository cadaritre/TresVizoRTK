#pragma once
#include <cstddef>
#include <cstdint>

namespace protocol {
// Una respuesta conserva su offset hasta que la pila acepta el fragmento.
// Plazo inferior a los 5 s del reensamblador de las apps; no se prolonga con
// cada reintento. Ante un fallo tardío de GATT se cierra la sesión.
class BleResponseTx {
public:
    void begin(size_t bytes, uint32_t now) { total_ = bytes; offset_ = 0; started_ = now; attempted_ = now - 5; }
    size_t offset() const { return offset_; }
    bool complete() const { return offset_ == total_; }
    bool expired(uint32_t now) const { return !complete() && uint32_t(now - started_) >= 4500; }
    bool due(uint32_t now) const { return !complete() && uint32_t(now - attempted_) >= 5; }
    void attempted(uint32_t now, size_t bytes, bool accepted) {
        attempted_ = now;
        if (accepted && bytes <= total_ - offset_) offset_ += bytes;
    }
private:
    size_t total_ = 0, offset_ = 0;
    uint32_t started_ = 0, attempted_ = 0;
};
}
