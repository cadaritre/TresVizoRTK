#pragma once
#include <cstddef>
#include <cstdint>
#include <cstring>
#include "rtcm3.h"

namespace radio_usb {
// Enlace por USB-C entre el MeridianV y su radio LoRa externo (docs/radio/USB_LINK.md).
// El receptor es el dispositivo USB (su CDC de siempre); el radio, el anfitrión.
//
// Por el mismo CDC viajan, cada cosa con su propia forma de reconocerse:
//   - líneas de texto: las órdenes JSON de siempre (`{...}\n`, hasta 1024 bytes),
//     sus respuestas y el texto del receptor (arranque, avisos);
//   - tramas RTCM3 crudas: 0xD3, 6 bits a 0, 10 de longitud, carga y CRC-24Q;
//   - tramas del enlace: F5 52, versión, tipo, longitud (LE), carga JSON y CRC-24Q.
//
// El demultiplexor solo entrega tramas binarias con CRC correcto. Si una falla (CRC,
// cabecera imposible, corte), vuelve a mirar desde el byte siguiente los que ya tenía:
// la basura o un corte cuestan esa trama y nada más. Las mismas reglas que el parser
// RTCM3 (rtcm3.h): una trama a medias se abandona en cuanto **dentro del búfer** se
// completa otra posterior con CRC correcto, y se suelta si pasa kStaleFrameMs sin bytes.
//
// Sin Arduino a propósito: lo usan los dos firmwares y se prueba con g++
// (firmware/radio/test/radio_usb_test.cpp).

// --- Trama del enlace -----------------------------------------------------------
// 0xF5 nunca aparece en UTF-8 (ni, por tanto, en JSON ni en el texto del receptor) y
// no es 0xD3 ni '{': una trama del enlace no se confunde con lo demás.
constexpr uint8_t kSync0 = 0xF5;
constexpr uint8_t kSync1 = 0x52;            // 'R'
constexpr uint8_t kFrameVersion = 1;        // del entramado; el protocolo va en el saludo
constexpr uint8_t kRtcmPreamble = 0xD3;
constexpr size_t kHeaderBytes = 6;          // F5 52 versión tipo longitud(2)
constexpr size_t kCrcBytes = 3;             // CRC-24Q, como RTCM3, el más significativo primero
constexpr size_t kMaxPayloadBytes = 1024;
constexpr size_t kMaxFrameBytes = kHeaderBytes + kMaxPayloadBytes + kCrcBytes;   // 1033
constexpr size_t kMaxRtcmBytes = 1029;      // 3 + 1023 + 3
constexpr size_t kMaxLineBytes = 1024;      // = config_rules::kMaxRequestBytes del receptor

// Versión del juego de mensajes; va en `hello` y `welcome`. Las claves JSON y los
// tipos nuevos se añaden sin subirla (quien no los conoce los ignora).
constexpr int kProtocol = 1;

enum class Type : uint8_t {
    hello = 0x01,       // radio → receptor: quién es (JSON); hasta recibir `welcome`
    role = 0x02,        // receptor → radio: {"role":"base"|"rover"|"idle"}; 1 Hz, es su latido
    // 0x03 era el RTCM envuelto del enlace por Wi-Fi; por USB el RTCM va crudo.
    status = 0x04,      // radio → receptor, 1 Hz: estado del aire; es su latido
    config = 0x05,      // receptor → radio: {"seq":n, "network", "channel", "power_dbm"}
    welcome = 0x06,     // receptor → radio: respuesta al saludo
    config_ack = 0x07,  // radio → receptor: resultado de `config` con su `seq`
};
inline bool validType(uint8_t type) { return type >= 0x01 && type <= 0x7f; }

// --- Tiempos (los dos lados) ----------------------------------------------------
constexpr uint32_t kHelloPeriodMs = 1000;      // saludo mientras no haya `welcome`...
constexpr uint32_t kHelloFastTries = 10;       // ...las 10 primeras veces;
constexpr uint32_t kHelloSlowPeriodMs = 5000;  // luego cada 5 s (un receptor viejo no lo entiende)
constexpr uint32_t kStatusPeriodMs = 1000;     // `status` del radio
constexpr uint32_t kRolePeriodMs = 1000;       // `role` del receptor
constexpr uint32_t kSilenceTimeoutMs = 3500;   // sin latido del otro lado: enlace caído
constexpr uint32_t kStaleFrameMs = 1000;       // trama binaria a medias sin bytes nuevos
constexpr uint32_t kLineTimeoutMs = 5000;      // línea a medias (el 408 de la consola)

// Escribe una trama del enlace en `out`. Devuelve los bytes escritos o 0 si no cabe.
// Quien la manda la escribe entera de una vez (sin otra escritura en medio).
inline size_t encode(uint8_t type, const uint8_t* payload, size_t length, uint8_t* out, size_t capacity) {
    if (!validType(type) || length > kMaxPayloadBytes) return 0;
    const size_t total = kHeaderBytes + length + kCrcBytes;
    if (capacity < total) return 0;
    out[0] = kSync0;
    out[1] = kSync1;
    out[2] = kFrameVersion;
    out[3] = type;
    out[4] = static_cast<uint8_t>(length & 0xff);
    out[5] = static_cast<uint8_t>(length >> 8);
    if (length) std::memcpy(out + kHeaderBytes, payload, length);
    const uint32_t crc = gnss::crc24q(out, kHeaderBytes + length);
    out[kHeaderBytes + length] = static_cast<uint8_t>(crc >> 16);
    out[kHeaderBytes + length + 1] = static_cast<uint8_t>(crc >> 8);
    out[kHeaderBytes + length + 2] = static_cast<uint8_t>(crc);
    return total;
}
inline size_t encode(Type type, const uint8_t* payload, size_t length, uint8_t* out, size_t capacity) {
    return encode(static_cast<uint8_t>(type), payload, length, out, capacity);
}

// --- Demultiplexor --------------------------------------------------------------
// `Handler` (plantilla, sin virtuales) recibe:
//   onFrame(uint8_t type, const uint8_t* payload, size_t length)  trama del enlace válida
//   onRtcm(const uint8_t* frame, size_t length)                   trama RTCM3 válida, entera
//   onLine(const char* text, size_t length)    línea de texto sin '\r' ni '\n' (JSON o no)
//   onLineOverflow()   una línea pasó de kMaxLineBytes; se avisa al llegar su '\n' (413)
//   onLineTimeout()    una línea a medias sin '\n' durante kLineTimeoutMs (408)
// Los punteros solo valen durante la llamada.
class Demux {
public:
    struct Counters {
        uint32_t frames = 0, rtcm = 0, lines = 0;
        uint32_t crcErrors = 0;         // tramas binarias completas con CRC malo
        uint32_t expired = 0;           // tramas binarias a medias sin bytes durante kStaleFrameMs
        uint32_t abandoned = 0;         // tramas a medias que perdieron frente a una completa posterior
        uint32_t brokenLines = 0;       // líneas cortadas por un byte que no es texto
        uint32_t lineOverflows = 0, lineTimeouts = 0;
        uint32_t junkBytes = 0;         // bytes que no eran nada
    };
    Counters counters;

    void reset() {
        len = 0; scanned = 0; lineChars = 0;
        overflowLine = false; lastDropped = 0;
        candidates = 0; candidateFrom = 1;
    }

    template <class Handler> void feed(const uint8_t* data, size_t length, uint32_t nowMs, Handler& handler) {
        for (size_t i = 0; i < length; ++i) {
            const uint8_t value = data[i];
            lastByteMs = nowMs;
            if (!len && !overflowLine && space(value)) continue;   // entre mensajes
            // No debería pasar (drain deja sitio siempre); por si acaso, nunca se escribe fuera.
            if (len == kCapacity) { ++counters.junkBytes; shift(1); }
            buf[len++] = value;
            drain(nowMs, handler);
        }
    }

    // Caducidades: llamarla de vez en cuando (p. ej. en cada vuelta), aunque no lleguen bytes.
    template <class Handler> void tick(uint32_t nowMs, Handler& handler) {
        // Una trama binaria a medias que ya no avanza se suelta y se mira lo que traía.
        while (len && binaryStart(buf[0]) && nowMs - lastByteMs >= kStaleFrameMs) {
            ++counters.expired;
            shift(1);
            drain(nowMs, handler);
        }
        if ((overflowLine || (len && lineStart(buf[0]))) && nowMs - lineStartMs >= kLineTimeoutMs) {
            ++counters.lineTimeouts;
            overflowLine = false;
            len = 0; scanned = 0; lineChars = 0;
            handler.onLineTimeout();
        }
    }

    // Lo que hay retenido (para pruebas y diagnóstico).
    size_t pending() const { return len; }

private:
    // Una trama completa más un margen: nunca hace falta más (las líneas largas se descartan).
    static constexpr size_t kCapacity = kMaxFrameBytes + 8;
    uint8_t buf[kCapacity] = {};
    size_t len = 0;
    size_t scanned = 0;         // bytes de la línea en curso ya mirados
    size_t lineChars = 0;       // caracteres de la línea en curso (sin '\r')
    bool overflowLine = false;  // se está tirando el resto de una línea demasiado larga
    uint8_t lastDropped = 0;    // último byte tirado de esa línea
    uint32_t lastByteMs = 0, lineStartMs = 0;
    // Comienzos de trama binaria posteriores al 0 (y dónde acabarían) mientras se espera
    // una trama a medias. `candidateFrom`: primera posición sin mirar.
    static constexpr size_t kCandidates = 16;
    uint16_t candidateStart[kCandidates] = {}, candidateEnd[kCandidates] = {};
    size_t candidates = 0, candidateFrom = 1;

    static bool space(uint8_t b) { return b == ' ' || b == '\t' || b == '\r' || b == '\n'; }
    static bool binaryStart(uint8_t b) { return b == kSync0 || b == kRtcmPreamble; }
    // Lo que cabe en una línea de texto UTF-8 ('\n' aparte): sin controles ni bytes
    // que UTF-8 no usa nunca (0xC0, 0xC1, 0xF5–0xFF). 0xF5 es además el inicio de trama.
    static bool textByte(uint8_t b) {
        if (b == '\t' || b == '\r') return true;
        if (b < 0x20 || b == 0x7f) return false;
        return b != 0xc0 && b != 0xc1 && b < 0xf5;
    }
    static bool lineStart(uint8_t b) { return !binaryStart(b) && !space(b) && textByte(b); }

    static bool crcOk(const uint8_t* frame, size_t total) {
        const uint32_t sent = (static_cast<uint32_t>(frame[total - 3]) << 16) |
                              (static_cast<uint32_t>(frame[total - 2]) << 8) | frame[total - 1];
        return gnss::crc24q(frame, total - 3) == sent;
    }

    void shift(size_t by) {
        if (by >= len) len = 0;
        else { len -= by; std::memmove(buf, buf + by, len); }
        scanned = 0; lineChars = 0;
        size_t kept = 0;   // el que queda en 0 es la trama principal: sale de la lista
        for (size_t i = 0; i < candidates; ++i) {
            if (candidateStart[i] <= by) continue;
            candidateStart[kept] = uint16_t(candidateStart[i] - by);
            candidateEnd[kept] = uint16_t(candidateEnd[i] - by);
            ++kept;
        }
        candidates = kept;
        candidateFrom = candidateFrom > by + 1 ? candidateFrom - by : 1;
    }

    void remember(size_t start, size_t end) {
        if (end > kCapacity) return;   // no cabría: si es buena, saldrá al volver a mirar
        if (candidates == kCandidates) {   // sin sitio: se olvida el más viejo
            std::memmove(candidateStart, candidateStart + 1, sizeof(candidateStart[0]) * (kCandidates - 1));
            std::memmove(candidateEnd, candidateEnd + 1, sizeof(candidateEnd[0]) * (kCandidates - 1));
            --candidates;
        }
        candidateStart[candidates] = uint16_t(start);
        candidateEnd[candidates] = uint16_t(end);
        ++candidates;
    }

    // Con una trama a medias en el 0: ¿se completó dentro del búfer otra posterior con
    // CRC correcto? Entonces la de medias se abandona y sale la buena.
    template <class Handler> bool innerFrame(Handler& handler) {
        for (; candidateFrom + kHeaderBytes <= len; ++candidateFrom) {
            const size_t s = candidateFrom;
            if (buf[s] == kRtcmPreamble && !(buf[s + 1] & 0xfc)) {
                remember(s, s + ((static_cast<size_t>(buf[s + 1] & 3) << 8) | buf[s + 2]) + 6);
            } else if (buf[s] == kSync0 && buf[s + 1] == kSync1 && buf[s + 2] == kFrameVersion && validType(buf[s + 3])) {
                const size_t payload = buf[s + 4] | (static_cast<size_t>(buf[s + 5]) << 8);
                if (payload <= kMaxPayloadBytes) remember(s, s + kHeaderBytes + payload + kCrcBytes);
            }
        }
        for (size_t i = 0; i < candidates; ++i) {
            const size_t start = candidateStart[i], end = candidateEnd[i];
            if (end > len) continue;
            if (crcOk(buf + start, end - start)) {
                ++counters.abandoned;
                counters.junkBytes += uint32_t(start);
                if (buf[start] == kSync0) {
                    ++counters.frames;
                    handler.onFrame(buf[start + 3], buf + start + kHeaderBytes, end - start - kHeaderBytes - kCrcBytes);
                } else {
                    ++counters.rtcm;
                    handler.onRtcm(buf + start, end - start);
                }
                shift(end);
                return true;
            }
            // Completa y con CRC malo: no era un comienzo.
            std::memmove(candidateStart + i, candidateStart + i + 1, sizeof(candidateStart[0]) * (candidates - i - 1));
            std::memmove(candidateEnd + i, candidateEnd + i + 1, sizeof(candidateEnd[0]) * (candidates - i - 1));
            --candidates; --i;
        }
        return false;
    }

    template <class Handler> void drain(uint32_t nowMs, Handler& handler) {
        while (len || overflowLine) {
            bool progressed;
            if (overflowLine) progressed = stepOverflowLine(handler);
            else if (buf[0] == kSync0) progressed = stepLink(handler);
            else if (buf[0] == kRtcmPreamble) progressed = stepRtcm(handler);
            else if (space(buf[0])) { shift(1); progressed = true; }
            else if (!textByte(buf[0])) { ++counters.junkBytes; shift(1); progressed = true; }
            else progressed = stepLine(nowMs, handler);
            if (!progressed) return;
        }
    }

    // Cabecera imposible: el primer byte no era un comienzo; se mira desde el siguiente.
    bool notAStart() { ++counters.junkBytes; shift(1); return true; }

    template <class Handler> bool stepRtcm(Handler& handler) {
        if (len < 2) return false;
        if (buf[1] & 0xfc) return notAStart();
        if (len < 3) return false;
        const size_t total = ((static_cast<size_t>(buf[1] & 3) << 8) | buf[2]) + 6;
        if (len < total) return innerFrame(handler);
        if (crcOk(buf, total)) {
            ++counters.rtcm;
            handler.onRtcm(buf, total);
            shift(total);
        } else { ++counters.crcErrors; shift(1); }
        return true;
    }

    template <class Handler> bool stepLink(Handler& handler) {
        if (len < 2) return false;
        if (buf[1] != kSync1) return notAStart();
        if (len < 3) return false;
        if (buf[2] != kFrameVersion) return notAStart();
        if (len < 4) return false;
        if (!validType(buf[3])) return notAStart();
        if (len < kHeaderBytes) return false;
        const size_t payload = buf[4] | (static_cast<size_t>(buf[5]) << 8);
        if (payload > kMaxPayloadBytes) return notAStart();
        const size_t total = kHeaderBytes + payload + kCrcBytes;
        if (len < total) return innerFrame(handler);
        if (crcOk(buf, total)) {
            ++counters.frames;
            handler.onFrame(buf[3], buf + kHeaderBytes, payload);
            shift(total);
        } else { ++counters.crcErrors; shift(1); }
        return true;
    }

    template <class Handler> bool stepLine(uint32_t nowMs, Handler& handler) {
        if (!scanned) { scanned = 1; lineChars = 1; lineStartMs = nowMs; }
        while (scanned < len) {
            const uint8_t b = buf[scanned];
            if (b == '\n') {
                size_t kept = 0;   // la línea sin '\r', como la consola de siempre
                for (size_t i = 0; i < scanned; ++i)
                    if (buf[i] != '\r') buf[kept++] = buf[i];
                ++counters.lines;
                handler.onLine(reinterpret_cast<const char*>(buf), kept);
                shift(scanned + 1);
                return true;
            }
            if (!textByte(b)) {
                // Algo binario cortó la línea: se tira lo de antes y se mira desde ahí. Si
                // el byte anterior era 0xD3, ese es el comienzo de una RTCM (su segundo
                // byte, 0x00–0x03, es justo el que no es texto).
                ++counters.brokenLines;
                const size_t from = buf[scanned - 1] == kRtcmPreamble ? scanned - 1 : scanned;
                counters.junkBytes += uint32_t(from);
                shift(from);
                return true;
            }
            if (b != '\r') ++lineChars;
            ++scanned;
            if (lineChars > kMaxLineBytes || scanned >= kCapacity - 1) {
                // Demasiado larga: se tira lo guardado y el resto hasta su '\n'.
                lastDropped = buf[scanned - 1];
                shift(scanned);
                overflowLine = true;
                return true;
            }
        }
        return false;
    }

    template <class Handler> bool stepOverflowLine(Handler& handler) {
        for (size_t i = 0; i < len; ++i) {
            const uint8_t b = buf[i];
            if (b == '\n') {
                overflowLine = false;
                ++counters.lineOverflows;
                shift(i + 1);
                handler.onLineOverflow();
                return true;
            }
            if (!textByte(b)) {
                overflowLine = false;
                ++counters.brokenLines;
                const uint8_t previous = i ? buf[i - 1] : lastDropped;
                shift(i);
                if (previous == kRtcmPreamble) {   // el 0xD3 ya tirado vuelve al frente
                    std::memmove(buf + 1, buf, len);
                    buf[0] = kRtcmPreamble;
                    ++len;
                    candidates = 0; candidateFrom = 1;   // las posiciones se movieron
                }
                return true;
            }
        }
        if (len) lastDropped = buf[len - 1];
        len = 0;
        return false;
    }
};
}  // namespace radio_usb
