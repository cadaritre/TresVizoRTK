#include "correction_router.h"
#include "gnss_receiver.h"
#include "firmware_update.h"
#include "rtcm3.h"
#include <atomic>
#include <cstring>
namespace correction_router {
namespace {
std::atomic<Source> selected{Source::None};
std::atomic<uint32_t> revision{0}, accepted{0}, rejected{0};
}
bool select(const char* name) {
    Source next;
    if (!strcmp(name,"none")) next = Source::None;
    else if (!strcmp(name,"ble")) next = Source::Ble;
    else return false; // NTRIP/radio solo se habilitan al registrar y probar su controlador.
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
    ++accepted; return true;
}
uint32_t generation() { return revision; }
void status(JsonObject out) {
    out["active_source"] = selected == Source::Ble ? "ble" : "none";
    out["format"] = "rtcm3"; out["generation"] = revision.load();
    out["accepted_frames"] = accepted.load(); out["rejected_frames"] = rejected.load();
    out["drivers"]["ble"] = true; out["drivers"]["ntrip"] = false; out["drivers"]["radio"] = false;
    out["receiver_ready"] = gnss_receiver::snapshot().enabled;
    out["hot_load_modules"] = false;
}
}
