#pragma once

#include <cstddef>
#include <cstdint>
#include <cstring>

namespace config_rules {
constexpr size_t kMaxNameBytes = 32;
constexpr size_t kMaxSsidBytes = 32;
constexpr size_t kMaxPasswordBytes = 63;
constexpr size_t kMaxRequestBytes = 1024;

inline bool deviceName(const char* value) {
    if (!value) return false;
    const size_t length = std::strlen(value);
    if (!length || length > kMaxNameBytes || value[0] == ' ' || value[length - 1] == ' ') return false;
    for (size_t i = 0; i < length; ++i) {
        const unsigned char c = value[i];
        if (!((c >= 'a' && c <= 'z') || (c >= 'A' && c <= 'Z') ||
              (c >= '0' && c <= '9') || c == ' ' || c == '-' || c == '_')) return false;
    }
    return true;
}

inline bool ssid(const char* value) {
    if (!value || std::strlen(value) > kMaxSsidBytes) return false;
    for (const unsigned char* p = reinterpret_cast<const unsigned char*>(value); *p; ++p) {
        if (*p < 32 || *p == 127) return false;
    }
    return true;
}

inline bool password(const char* value) {
    if (!value) return false;
    const size_t length = std::strlen(value);
    if (length < 8 || length > kMaxPasswordBytes) return false;
    for (size_t i = 0; i < length; ++i) {
        if (static_cast<unsigned char>(value[i]) < 32 || static_cast<unsigned char>(value[i]) > 126) return false;
    }
    return true;
}

inline bool refresh(uint32_t value) { return value == 1000 || value == 2000 || value == 5000; }
inline bool elapsed(uint32_t now, uint32_t then, uint32_t period) { return now - then >= period; }
}
