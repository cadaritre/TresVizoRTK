#include "board_profile.h"
// Alimentación de la placa v0.3: cargador TI BQ25798 (0x6B) con FET de envío
// Q101, medidor MAX17048 (0x36), botón SW401 en GPIO18 y LED D403 en GPIO48.
// La Thing Plus compila power_manager.cpp (Soft Power Switch Mk2) con la misma
// interfaz. Qué hace y por qué: docs/board-v03-bringup.md.
#if defined(TRESVIZO_BOARD_V03)
#include "power_manager.h"
#include "power_sequence.h"
#include "sd_recorder.h"
#include "firmware_update.h"
#include "bq25798.h"
#include <Arduino.h>
#include <Wire.h>
#include <atomic>
namespace power_manager {
namespace {
// 0 activo, 1 cerrando la memoria, 2 corte pedido, 3 sigue alimentado.
std::atomic<unsigned> state{0};
std::atomic<const char*> reason{nullptr};
// El botón lo lee el bucle; la tarea dueña de Wire solo necesita saber si está suelto.
std::atomic<bool> buttonDown{false};
power_sequence::Button button;
portMUX_TYPE mux = portMUX_INITIALIZER_UNLOCKED;
// Bajo `mux`: lo que escribe la tarea de Wire y leen el bucle, HTTP y BLE.
bool gaugeValid = false; float voltage = 0, soc = 0; uint32_t sampled = 0;
bq25798::Status charger;
const char* chargerSetup = "not_started";
const char* shipResult = nullptr;
uint16_t vregMv = 0, ichgMa = 0;
uint32_t chargerSampled = 0;
// Solo la tarea de Wire.
bq25798::ByteOrder order = bq25798::ByteOrder::unknown;
bool configured = false;
uint32_t configuredAt = 0, shipAt = 0;
// Solo el bucle.
uint32_t lowSince = 0;

// Bus del cargador sobre Wire (lecturas y escrituras de varios bytes, §7.3.14.7).
struct ChargerBus {
    bool read(uint8_t reg, uint8_t* data, size_t n) {
        Wire.beginTransmission(board_profile::kChargerAddress);
        Wire.write(reg);
        if (Wire.endTransmission(false) != 0) return false;
        if (Wire.requestFrom(board_profile::kChargerAddress, uint8_t(n)) != n) return false;
        for (size_t i = 0; i < n; ++i) data[i] = uint8_t(Wire.read());
        return true;
    }
    bool write(uint8_t reg, const uint8_t* data, size_t n) {
        Wire.beginTransmission(board_profile::kChargerAddress);
        Wire.write(reg);
        Wire.write(data, n);
        return Wire.endTransmission() == 0;
    }
};

bool readGauge(uint8_t reg, uint16_t& value) {
    Wire.beginTransmission(board_profile::kGaugeAddress); Wire.write(reg);
    if (Wire.endTransmission(false) != 0) return false;
    if (Wire.requestFrom(board_profile::kGaugeAddress, uint8_t(2)) != 2) return false;
    value = (uint16_t(Wire.read()) << 8) | Wire.read(); return true;
}

bool shutdownFor(const char* why) {
    if (state.load() != 0) return true;
    if (firmware_update::busy()) return false;
    reason = why; state = 1; return true;
}

void drive(bool on) { if (board_profile::kStatusLed >= 0) digitalWrite(board_profile::kStatusLed, on ? HIGH : LOW); }
}

void begin() {
    // LED encendido en cuanto arranca: el equipo responde. GPIO48 no es pin de arranque.
    if (board_profile::kStatusLed >= 0) { digitalWrite(board_profile::kStatusLed, HIGH); pinMode(board_profile::kStatusLed, OUTPUT); }
    // R408 (10 kΩ a +3V3) ya fija el reposo; INT y ALRT tienen el suyo (R108, R113).
    pinMode(board_profile::kPowerButton, INPUT);
    if (board_profile::kChargerInt >= 0) pinMode(board_profile::kChargerInt, INPUT);
    if (board_profile::kGaugeAlert >= 0) pinMode(board_profile::kGaugeAlert, INPUT);
    // La pulsación que despertó al cargador (QON ≥ 1 s) puede seguir: no cuenta
    // hasta verla suelta (power_sequence::Button).
    button.changed = millis(); button.previous = digitalRead(board_profile::kPowerButton) == LOW;
    buttonDown = button.previous;
}
bool pending() { return state.load() != 0; }
bool requestShutdown() { return shutdownFor("request"); }

void tick() {
    const uint32_t now = millis();
    const bool pressed = digitalRead(board_profile::kPowerButton) == LOW;
    buttonDown = pressed;
    // 2 s, muy por debajo de los 10 s del reset por hardware del BQ25798.
    if (button.held(pressed, now) && shutdownFor("button")) button.consumed();
    // Batería baja sin USB durante un minuto seguido: apagado ordenado, con la
    // memoria cerrada, antes de que la celda baje de lo que el modo ship necesita.
    bool usb = false, gauge = false, chargerKnown = false; float volts = 0;
    portENTER_CRITICAL(&mux);
    chargerKnown = charger.valid && now - chargerSampled < 6000;
    usb = chargerKnown && charger.vbusPresent; gauge = gaugeValid && now - sampled < 6000; volts = voltage;
    portEXIT_CRITICAL(&mux);
    if (state.load() == 0 && gauge && chargerKnown && !usb && volts <= board_profile::kAutoShutdownVolts) {
        if (!lowSince) lowSince = now ? now : 1;
        else if (now - lowSince >= board_profile::kAutoShutdownHoldMs) shutdownFor("low_battery");
    } else lowSince = 0;
    if (state.load() == 1 && sd_recorder::prepareShutdown()) state = 2;
    // LED: fijo en marcha; 1 Hz con batería baja; 4 Hz mientras se apaga.
    const unsigned s = state.load();
    if (s != 0) drive((now / 125) % 2 == 0);
    else if (gauge && volts <= board_profile::kLowBatteryVolts) drive((now / 500) % 2 == 0);
    else drive(true);
}

void sampleGauge() {
    // Exclusivamente desde la tarea dueña de Wire (local_display), una vez por segundo.
    ChargerBus bus;
    const uint32_t now = millis();
    if (!configured && (!configuredAt || now - configuredAt >= 5000)) {
        configuredAt = now ? now : 1;
        const auto result = bq25798::configure(bus, board_profile::kChargeVoltageMv,
                                               board_profile::kChargeCurrentMa, board_profile::kChargeCurrentMaxMa);
        order = result.order;
        // Configurado o con la carga deshabilitada: no se reintenta. Un error de bus sí.
        configured = result.result != bq25798::Setup::bus_error;
        portENTER_CRITICAL(&mux);
        chargerSetup = bq25798::setupName(result.result); vregMv = result.vregMv; ichgMa = result.ichgMa;
        portEXIT_CRITICAL(&mux);
    }
    const bq25798::Status polled = configured
        ? bq25798::poll(bus, order, board_profile::kChargeCurrentMa, board_profile::kChargeCurrentMaxMa)
        : bq25798::Status{};
    // Otro POR del cargador con el ESP32 vivo (p. ej. se cambió el pack con USB
    // puesto): SFET_PRESENT vuelve a 0 y hay que configurarlo de nuevo.
    if (polled.valid && !polled.sfetPresent && configured && order != bq25798::ByteOrder::unknown) {
        configured = false; configuredAt = 0;
    }
    uint16_t v = 0, s = 0;
    bool ok = readGauge(0x02, v) && readGauge(0x04, s);   // VCELL y SOC del MAX17048
    const float volts = v * 0.000078125f, percent = s / 256.0f;
    ok = ok && volts >= 2.5f && volts <= 4.5f && percent <= 110.0f;
    portENTER_CRITICAL(&mux);
    gaugeValid = ok; voltage = volts; soc = percent > 100 ? 100 : percent; sampled = millis();
    charger = polled; if (polled.valid) { chargerSampled = millis(); if (polled.ichgMa) ichgMa = polled.ichgMa; }
    portEXIT_CRITICAL(&mux);

    // Corte: memoria cerrada (estado 2) o ya intentado (3). Solo con el botón
    // suelto: con QON en bajo el cargador vuelve a despertar al equipo.
    const unsigned current = state.load();
    if ((current == 2 || current == 3) && !buttonDown.load()) {
        if (current == 2 && shipAt && now - shipAt < 1500) return;   // la orden ya salió: esperar el corte
        const auto ship = bq25798::enterShip(bus);
        const char* result = ship == bq25798::Ship::written ? "written" : ship == bq25798::Ship::vbus_present
            ? "vbus_present" : ship == bq25798::Ship::not_allowed ? "sfet_not_present" : "bus_error";
        portENTER_CRITICAL(&mux); shipResult = result; portEXIT_CRITICAL(&mux);
        if (ship == bq25798::Ship::written && !shipAt) { shipAt = now ? now : 1; return; }
        // Sigue vivo: con USB la orden se ignora; se reintenta cada segundo y se
        // apaga solo al quitar el cable.
        state = 3; shipAt = 0;
    }
}

void status(JsonObject out) {
    bool ok, valid; float v, s; uint32_t t, ct; bq25798::Status c; const char* setup; const char* ship; uint16_t vreg, ichg;
    portENTER_CRITICAL(&mux);
    ok = gaugeValid; v = voltage; s = soc; t = sampled; c = charger; ct = chargerSampled;
    setup = chargerSetup; ship = shipResult; vreg = vregMv; ichg = ichgMa;
    portEXIT_CRITICAL(&mux);
    ok = ok && millis() - t < 6000;
    valid = c.valid && millis() - ct < 6000;
    const char* states[] = {"running", "closing_storage", "cut_requested", "power_still_present"};
    out["state"] = states[state.load()]; out["shutdown_pending"] = pending();
    out["gauge_available"] = ok; out["battery_capacity_mah"] = board_profile::kBatteryCapacityMah;
    if (valid) {
        out["battery_present"] = c.batteryPresent;
        out["charging"] = bq25798::charging(c.status1);
        out["usb_present"] = c.vbusPresent;
    } else { out["battery_present"] = nullptr; out["charging"] = nullptr; out["usb_present"] = nullptr; }
    if (ok) { out["voltage_v"] = v; out["percent"] = s; out["low_battery"] = s <= 10 || v <= board_profile::kLowBatteryVolts; }
    else { out["voltage_v"] = nullptr; out["percent"] = nullptr; out["low_battery"] = nullptr; }
    out["push_gpio"] = board_profile::kPowerButton; out["off_gpio"] = nullptr;
    // Aditivo (placa v0.3).
    out["cut_method"] = "bq25798_ship";
    out["led_gpio"] = board_profile::kStatusLed;
    out["shutdown_reason"] = reason.load();
    out["auto_shutdown_volts"] = board_profile::kAutoShutdownVolts;
    JsonObject ch = out["charger"].to<JsonObject>();
    ch["chip"] = "BQ25798"; ch["i2c_address"] = board_profile::kChargerAddress;
    ch["setup"] = setup;
    if (vreg) ch["vreg_mv"] = vreg; else ch["vreg_mv"] = nullptr;
    if (ichg) ch["ichg_ma"] = ichg; else ch["ichg_ma"] = nullptr;
    ch["ichg_max_ma"] = board_profile::kChargeCurrentMaxMa;
    ch["available"] = valid;
    if (valid) {
        ch["charge_state"] = bq25798::chargeState(c.status1);
        ch["vbus_status"] = (c.status1 >> 1) & 0x0F;
        ch["power_good"] = c.powerGood;
        ch["thermal_regulation"] = c.thermalRegulation;
        ch["sfet_present"] = c.sfetPresent;
        ch["fault_status_0"] = c.fault0; ch["fault_status_1"] = c.fault1;
    }
    ch["ship"] = ship;
}
}
#endif  // TRESVIZO_BOARD_V03
