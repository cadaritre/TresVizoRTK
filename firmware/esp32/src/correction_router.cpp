#include <Arduino.h>
#include "correction_router.h"
#include "gnss_receiver.h"
#include "firmware_update.h"
#include "rtcm3.h"
#include <Preferences.h>
#include <atomic>
#include <cstring>
namespace correction_router {
namespace {
std::atomic<Source> selected{Source::None};
// Lo que eligio el usuario, no lo que esta seleccionado ahora.
std::atomic<Source> chosen{Source::None};
Preferences store;
bool storeReady = false;
std::atomic<uint32_t> revision{0}, accepted{0}, rejected{0};
// Instante de la ultima trama aceptada. 0 = todavia no ha llegado ninguna.
std::atomic<uint32_t> lastAccepted{0};
}
void begin() {
    storeReady = store.begin("corrections", false);
    if (!storeReady) return;
    const uint8_t saved = store.getUChar("chosen", uint8_t(Source::None));
    // Solo BLE se aplica aqui. NTRIP lo arranca su propio modulo con el perfil
    // guardado, y "ninguna" es el estado de partida.
    if (saved == uint8_t(Source::Ble)) { chosen = Source::Ble; select("ble"); }
    else if (saved == uint8_t(Source::Ntrip)) chosen = Source::Ntrip;
}
bool choose(const char* name) {
    if (!select(name)) return false;
    const Source next = selected.load();
    if (chosen.exchange(next) != next && storeReady) store.putUChar("chosen", uint8_t(next));
    return true;
}
bool bleChosen() { return chosen == Source::Ble; }
bool select(const char* name) {
    Source next;
    if (!strcmp(name,"none")) next = Source::None;
    else if (!strcmp(name,"ble")) next = Source::Ble;
    else if (!strcmp(name,"ntrip")) next = Source::Ntrip;
    else return false;
    if (selected.exchange(next) != next) ++revision;
    return true;
}
bool submit(Source source, const uint8_t* frame, size_t length) {
    if (source == Source::None || selected != source || length < 6 || length > 1029 ||
        frame[0] != 0xd3 || (frame[1] & 0xfc) || static_cast<size_t>(((frame[1] & 3) << 8) | frame[2]) + 6 != length) {
        ++rejected; return false;
    }
    const uint32_t crc = (static_cast<uint32_t>(frame[length-3]) << 16) | (static_cast<uint32_t>(frame[length-2]) << 8) | frame[length-1];
    if (gnss::crc24q(frame,length-3) != crc || !gnss_receiver::enqueueCorrections(frame,length)) { ++rejected; return false; }
    lastAccepted = millis(); ++accepted; return true;
}
uint32_t generation() { return revision; }
uint32_t rejectedFrames() { return rejected; }
uint32_t ageMs() {
    const uint32_t mark = lastAccepted.load();
    if (selected == Source::None || !mark) return UINT32_MAX;
    return millis() - mark;
}
uint8_t sourceCode() {
    switch (selected.load()) {
        case Source::Ble: return 1;
        case Source::Ntrip: return 2;
        case Source::Radio: return 3;
        default: return 0;
    }
}
void status(JsonObject out) {
    out["active_source"] = selected == Source::Ble ? "ble" : selected == Source::Ntrip ? "ntrip" : "none";
    // La que se restaura al encender. Puede diferir de la activa: una base, por
    // ejemplo, deja la activa en "none" sin cambiar lo que eligio el usuario.
    out["chosen_source"] = chosen == Source::Ble ? "ble" : chosen == Source::Ntrip ? "ntrip" : "none";
    out["format"] = "rtcm3"; out["generation"] = revision.load();
    out["accepted_frames"] = accepted.load(); out["rejected_frames"] = rejected.load();
    out["drivers"]["ble"] = true; out["drivers"]["ntrip"] = true; out["drivers"]["radio"] = false;
    out["receiver_ready"] = gnss_receiver::snapshot().enabled;
    out["hot_load_modules"] = false;
    // Nulo mientras no haya fuente o no haya llegado nada: el panel debe poder
    // decir "sin conectar" en vez de mostrar una antiguedad inventada.
    const uint32_t age = ageMs();
    if (age == UINT32_MAX) out["age_ms"] = nullptr; else out["age_ms"] = age;
}
}
