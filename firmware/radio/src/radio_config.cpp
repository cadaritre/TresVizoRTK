#include "radio_config.h"
#include <Preferences.h>

namespace radio_config {
namespace {
constexpr const char* kNamespace = "radio";

bool printable(const String& text) {
    for (size_t i = 0; i < text.length(); ++i) {
        const char c = text[i];
        if (c < 0x20 || c > 0x7e) return false;
    }
    return true;
}
}  // namespace

Settings load() {
    Settings settings;
    Preferences store;
    if (!store.begin(kNamespace, true)) return settings;
    settings.wifiSsid = store.getString("ssid", kDefaultSsid);
    settings.wifiPassword = store.getString("pass", kDefaultPassword);
    settings.network = store.getUChar("network", radio_air::kDefaultNetwork);
    settings.channel = store.getUChar("channel", radio_air::kDefaultChannel);
    settings.powerDbm = store.getChar("power", radio_air::kDefaultOutputDbm);
    store.end();
    if (settings.channel >= radio_air::kChannelCount) settings.channel = radio_air::kDefaultChannel;
    if (settings.powerDbm > radio_air::kMaxOutputDbm) settings.powerDbm = radio_air::kMaxOutputDbm;
    return settings;
}

bool save(const Settings& settings) {
    Preferences store;
    if (!store.begin(kNamespace, false)) return false;
    bool ok = store.putString("ssid", settings.wifiSsid) == settings.wifiSsid.length();
    ok = store.putString("pass", settings.wifiPassword) == settings.wifiPassword.length() && ok;
    ok = store.putUChar("network", settings.network) == 1 && ok;
    ok = store.putUChar("channel", settings.channel) == 1 && ok;
    ok = store.putChar("power", settings.powerDbm) == 1 && ok;
    store.end();
    return ok;
}

bool apply(JsonVariantConst body, Settings& settings, String& error, bool allowWifi) {
    if (!body.is<JsonObjectConst>()) { error = "Se esperaba un objeto JSON."; return false; }
    Settings next = settings;
    for (JsonPairConst field : body.as<JsonObjectConst>()) {
        const String key = field.key().c_str();
        JsonVariantConst value = field.value();
        if (allowWifi && key == "wifi_ssid" && value.is<const char*>()) {
            const String ssid = value.as<const char*>();
            if (!ssid.length() || ssid.length() > kMaxSsidBytes || !printable(ssid)) {
                error = "El nombre de la red debe tener de 1 a 32 caracteres imprimibles."; return false;
            }
            next.wifiSsid = ssid;
        } else if (allowWifi && key == "wifi_password" && value.is<const char*>()) {
            const String password = value.as<const char*>();
            if (password.length() < kMinPasswordBytes || password.length() > kMaxPasswordBytes || !printable(password)) {
                error = "La contraseña debe tener de 8 a 63 caracteres imprimibles."; return false;
            }
            next.wifiPassword = password;
        } else if (key == "network" && value.is<int>() && value.as<int>() >= 0 && value.as<int>() <= 255) {
            next.network = uint8_t(value.as<int>());
        } else if (key == "channel" && value.is<int>() && value.as<int>() >= 0 && value.as<int>() < radio_air::kChannelCount) {
            next.channel = uint8_t(value.as<int>());
        } else if (key == "power_dbm" && value.is<int>() && value.as<int>() >= 0 && value.as<int>() <= radio_air::kMaxOutputDbm) {
            next.powerDbm = int8_t(value.as<int>());
        } else {
            error = "Ajuste no válido: " + key + "."; return false;
        }
    }
    settings = next;
    return true;
}
}  // namespace radio_config
