#include "radio_config.h"
#include <Preferences.h>

namespace radio_config {
namespace {
constexpr const char* kNamespace = "radio";

int8_t limitPower(int value) {
    if (value > kMaxOutputDbm) return kMaxOutputDbm;
    if (value < 0) return 0;
    return int8_t(value);
}
}  // namespace

Settings load() {
    Settings settings;
    Preferences store;
    if (!store.begin(kNamespace, false)) return settings;
    settings.network = store.getUChar("network", radio_air::kDefaultNetwork);
    settings.channel = store.getUChar("channel", radio_air::kDefaultChannel);
    settings.powerDbm = store.getChar("power", kDefaultOutputDbm);
    // La 0.1.0 guardaba la red Wi-Fi del MeridianV y su contraseña; ya no se usan y la
    // contraseña no debe quedarse en el radio.
    if (store.isKey("ssid")) store.remove("ssid");
    if (store.isKey("pass")) store.remove("pass");
    store.end();
    if (settings.channel >= radio_air::kChannelCount) settings.channel = radio_air::kDefaultChannel;
    // La 0.1.0 guardaba 30 dBm por omisión: se recorta al tope legal.
    settings.powerDbm = limitPower(settings.powerDbm);
    return settings;
}

bool save(const Settings& settings) {
    Preferences store;
    if (!store.begin(kNamespace, false)) return false;
    bool ok = store.putUChar("network", settings.network) == 1;
    ok = store.putUChar("channel", settings.channel) == 1 && ok;
    ok = store.putChar("power", settings.powerDbm) == 1 && ok;
    store.end();
    return ok;
}

bool apply(JsonVariantConst body, Settings& settings, String& error, bool& powerLimited) {
    powerLimited = false;
    if (!body.is<JsonObjectConst>()) { error = "Se esperaba un objeto JSON."; return false; }
    Settings next = settings;
    bool limited = false;
    for (JsonPairConst field : body.as<JsonObjectConst>()) {
        const String key = field.key().c_str();
        JsonVariantConst value = field.value();
        if (key == "seq") continue;
        if (key == "network" && value.is<int>() && value.as<int>() >= 0 && value.as<int>() <= 255) {
            next.network = uint8_t(value.as<int>());
        } else if (key == "channel" && value.is<int>() && value.as<int>() >= 0 && value.as<int>() < radio_air::kChannelCount) {
            next.channel = uint8_t(value.as<int>());
        } else if (key == "power_dbm" && value.is<int>() && value.as<int>() >= 0 && value.as<int>() <= radio_air::kMaxOutputDbm) {
            limited = value.as<int>() > kMaxOutputDbm;
            next.powerDbm = limitPower(value.as<int>());
        } else {
            error = "Ajuste no válido: " + key + ". Se cambian network (0–255), channel (0–12) y power_dbm (0–27).";
            return false;
        }
    }
    settings = next;
    powerLimited = limited;
    return true;
}
}  // namespace radio_config
