#pragma once
#include <cstdint>
#include <cstring>

namespace protocol {
// El UM980 no etiqueta respuestas con un ID de solicitud. Antes de sustituir
// una secuencia se consume la respuesta del único comando ya transmitido.
// El resto de la secuencia vieja nunca se envía. No bloquea el handler.
class CommandHandoff {
public:
    enum class Result { Ready, Waiting, TimedOut };
    bool active() const { return command_[0] != 0; }
    bool begin(const char* command, bool ack, bool readback, uint32_t started) {
        if (active()) return true; // tres cambios rápidos conservan el mismo vuelo
        if (std::strlen(command) >= sizeof(command_)) return false;
        std::strcpy(command_, command);
        ack_ = ack; readback_ = readback; started_ = started;
        return true;
    }
    // Solo líneas con checksum ya validado. Ninguna llega al trabajo nuevo.
    void consume(const char* line) {
        if (!active()) return;
        constexpr const char* prefix = "$command,";
        const size_t n = std::strlen(command_);
        if (!std::strncmp(line, prefix, 9) && !std::strncmp(line + 9, command_, n) &&
            !std::strncmp(line + 9 + n, ",response: ", 11)) {
            ack_ = true;
            if (std::strcmp(line + 9 + n + 11, "OK")) readback_ = true;
        }
        if ((!std::strcmp(command_, "MODE") && !std::strncmp(line, "#MODE,", 6)) ||
            (!std::strcmp(command_, "VERSIONA") && !std::strncmp(line, "#VERSIONA,", 10)) ||
            (!std::strcmp(command_, "MASK") && !std::strncmp(line, "$CONFIG,MASK,", 13))) readback_ = true;
    }
    Result poll(uint32_t now) {
        if (!active()) return Result::Ready;
        const uint32_t elapsed = now - started_;
        const bool query = !std::strcmp(command_, "MODE") || !std::strcmp(command_, "VERSIONA") || !std::strcmp(command_, "MASK");
        const bool config = !std::strcmp(command_, "CONFIG");
        if (ack_ && (config ? elapsed > 700 : !query || readback_)) {
            command_[0] = 0;
            return Result::Ready;
        }
        if (elapsed > 4000) {
            command_[0] = 0;
            return Result::TimedOut;
        }
        return Result::Waiting;
    }
private:
    char command_[192]{};
    bool ack_ = false, readback_ = false;
    uint32_t started_ = 0;
};
}
