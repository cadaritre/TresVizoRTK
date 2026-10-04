#include "local_display.h"
#include "boot_logo.h"
#include "display_boot.h"
#include "oled_transport.h"
#include "power_manager.h"
#include "board_profile.h"
#include "display_status.h"
#include "instrument.h"
#include "correction_router.h"
#include "sd_recorder.h"
#include <Adafruit_GFX.h>
#include <WiFi.h>
#include <Wire.h>
#include <atomic>

namespace local_display {
namespace {
// El cuadro sólo cambia a 1 Hz. Modo estándar da más margen al arnés Qwiic/OLED.
constexpr uint32_t kBusHz = 100000;
constexpr uint16_t kWhite = 1, kBlack = 0;
GFXcanvas1 display(128,64);
std::atomic<const char*> phase{"not_started"};
std::atomic<uint8_t> address{0};
std::atomic<const char*> screen{"none"};
std::atomic<bool> started{false}, ready{false}, restarting{false}, stopped{false};
uint32_t bootAt = 0, restartAt = 0;

bool responds(uint8_t candidate) {
    Wire.beginTransmission(candidate);
    return Wire.endTransmission() == 0;
}
void line(int y, const char* text) {
    display.setCursor(0,y);
    display.print(text);
}
void drawStatus(bool shutdown) {
    display.fillScreen(kBlack);
    display.setTextSize(1);
    if (shutdown) {
        JsonDocument power;
        power_manager::status(power.to<JsonObject>());
        line(8,"APAGANDO");
        line(24,sd_recorder::active()?"Cerrando memoria":"Corte solicitado");
        if(strcmp(power["state"]|"","power_still_present")==0) line(40,"Sigue alimentado");
        return;
    }
    // El plazo del logo no depende de Wi-Fi, montaje de memoria ni BLE.
    // Si setup sigue trabajando, no consultar servicios a medio iniciar.
    if (!ready.load()) {
        line(8,"INICIANDO");
        line(24,"Preparando equipo");
        return;
    }
    const auto gnss=gnss_receiver::snapshot();
    const auto text=display_status::build(gnss,esp_timer_get_time(),correction_router::sourceCode(),
                                          correction_router::ageMs(),sd_recorder::displayState());
    display.setCursor(0,0);display.print("MeridianV ");display.print(instrument::kVersion);
    display.drawFastHLine(0,10,128,kWhite);
    display.setTextSize(2);line(13,text.fix);
    display.setTextSize(1);line(31,text.satellites);
    line(39,text.corrections);line(47,text.storage);
    display.setCursor(0,56);
    const bool station=WiFi.status()==WL_CONNECTED;
    display.print(station ? "IP " : "AP ");
    display.print(station ? WiFi.localIP() : WiFi.softAPIP());
    if((millis()/5000)%2==1) {
        JsonDocument power;
        power_manager::status(power.to<JsonObject>());
        display.fillRect(0,56,128,8,kBlack);display.setCursor(0,56);
        if(power["gauge_available"].as<bool>()) {
            display.print("BAT ");display.print(power["percent"].as<float>(),0);display.print("% ");
            display.print(power["voltage_v"].as<float>(),2);display.print("V");
        } else display.print("BAT sin lectura");
    }
}
void worker(void*) {
    if (!Wire.begin(board_profile::kSda,board_profile::kScl,kBusHz)) {
        phase="bus_failed";stopped=true;
        vTaskDelete(nullptr);
        return;
    }
    Wire.setTimeOut(20);
    display.setTextColor(kWhite);
    display.setTextWrap(false);
    display_boot::Window logo(bootAt,boot_logo::kDurationMs);
    bool panelOn=false, gaugeSampled=false, retry=false;
    uint32_t gaugeAt=0, frameAt=0, retryAt=0;
    for (;;) {
        if (restarting.load()) {
            if (address.load()) oled_transport::off(Wire,address.load());
            Wire.end();
            screen="none";address=0;phase="restarting";stopped=true;
            vTaskDelete(nullptr);
            return;
        }
        const uint32_t now=millis();
        const bool shutdown=power_manager::pending();
        const bool showLogo=logo.active(now,shutdown);
        bool failed=false;
        // Ocultar primero el logo al vencer: ninguna consulta de estado puede
        // dejarlo retenido en la RAM de la OLED durante más tiempo.
        if (!showLogo && strcmp(screen.load(),"logo")==0) {
            if (address.load()) failed=!oled_transport::off(Wire,address.load());
            panelOn=false;screen="none";
        }
        if (!retry || uint32_t(now-retryAt)>=1000) {
            retry=false;
            if (!address.load() && !failed) {
                const uint8_t found=responds(0x3c)?0x3c:responds(0x3d)?0x3d:0;
                if (!found) { phase="not_detected";retry=true;retryAt=now; }
                else if (!oled_transport::initialize(Wire,found)) failed=true;
                else { address=found;panelOn=false;screen="none"; }
            }
            if (address.load() && !failed) {
                const char* next=showLogo?"logo":shutdown?"shutdown":ready.load()?"main":"starting";
                if (!panelOn || strcmp(next,screen.load())!=0 || (!showLogo && uint32_t(now-frameAt)>=1000)) {
                    if (showLogo) {
                        display.fillScreen(kBlack);
                        display.drawBitmap(0,0,boot_logo::kBitmap,boot_logo::kWidth,boot_logo::kHeight,kWhite);
                    } else drawStatus(shutdown);
                    if (!oled_transport::frame(Wire,address.load(),display.getBuffer(),!panelOn)) failed=true;
                    else { screen=next;panelOn=true;phase="ready";frameAt=millis(); }
                }
            }
        }
        if (failed) {
            // Una respuesta al sondeo no demuestra que se transfirió el cuadro.
            if (address.load()) oled_transport::off(Wire,address.load());
            address=0;screen="none";panelOn=false;phase="i2c_error";
            retry=true;retryAt=millis();
        }
        // Sigue leyendo batería aunque falte la OLED. Evitar iniciar lecturas
        // junto al vencimiento del logo (cada operación I2C tiene timeout).
        const uint32_t elapsed=uint32_t(millis()-bootAt);
        const bool nearDeadline=elapsed<boot_logo::kDurationMs && boot_logo::kDurationMs-elapsed<=150;
        if (!nearDeadline && (!gaugeSampled || uint32_t(millis()-gaugeAt)>=1000)) {
            power_manager::sampleGauge();gaugeAt=millis();gaugeSampled=true;
        }
        vTaskDelay(pdMS_TO_TICKS(20));
    }
}
}
void begin() {
    if (started.exchange(true)) return;
    phase="starting";
    // Conservar alimentación estable en Qwiic: una OLED de cuatro pines no
    // expone RESET y puede tener su propio circuito de encendido. Recuperar
    // el controlador con comandos completos, sin pulsar su alimentación.
    digitalWrite(board_profile::kPeripheralEnable,HIGH);
    pinMode(board_profile::kPeripheralEnable,OUTPUT);
    delay(10);
    bootAt=millis();
    if (!display.getBuffer()) { phase="allocation_failed";stopped=true;return; }
    // Única tarea dueña de Wire. El arranque lento de otros servicios no la bloquea.
    if (xTaskCreate(worker,"oled",4096,nullptr,1,nullptr)!=pdPASS) { phase="task_failed";stopped=true; }
}
void servicesReady() { ready=true; }
bool prepareRestart() {
    // Ambas rutas llaman desde el bucle del instrumento, bajo su mutex.
    if (!restarting.exchange(true)) restartAt=millis();
    return !started.load() || stopped.load() || uint32_t(millis()-restartAt)>=300;
}
void status(JsonObject out) {
    out["state"]=phase.load();
    out["screen"]=address.load()?screen.load():"none";
    out["boot_logo_ms"]=boot_logo::kDurationMs;
    out["available"]=address.load()!=0;
    out["driver"]="ssd1306";
    out["width"]=128;out["height"]=64;
    if (address.load()) out["i2c_address"]=address.load();
    else out["i2c_address"]=nullptr;
    out["sda_gpio"]=board_profile::kSda;out["scl_gpio"]=board_profile::kScl;
}
}
