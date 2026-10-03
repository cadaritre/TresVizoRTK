#include "local_display.h"
#include "power_manager.h"
#include "board_profile.h"
#include "display_status.h"
#include "instrument.h"
#include "correction_router.h"
#include "sd_recorder.h"
#include <Adafruit_SSD1306.h>
#include <WiFi.h>
#include <Wire.h>
#include <atomic>

namespace local_display {
namespace {
constexpr uint32_t kBusHz = 400000;
Adafruit_SSD1306 display(128,64,&Wire,-1,kBusHz,kBusHz);
std::atomic<const char*> phase{"not_started"};
std::atomic<uint8_t> address{0};
bool responds(uint8_t candidate) {
    Wire.beginTransmission(candidate);
    return Wire.endTransmission() == 0;
}
void line(int y, const char* text) {
    display.setCursor(0,y);
    display.print(text);
}
void worker(void*) {
    if (!Wire.begin(board_profile::kSda,board_profile::kScl,kBusHz)) {
        phase="bus_failed";
        vTaskDelete(nullptr);
        return;
    }
    Wire.setTimeOut(20);
    for (;;) {
        power_manager::sampleGauge();
        if (!address.load()) {
            uint8_t found = responds(0x3c) ? 0x3c : responds(0x3d) ? 0x3d : 0;
            // El ACK detecta la dirección; el controlador SSD1306 procede de
            // la referencia de Tecneu, no se puede identificar por un ACK.
            if (!found) phase="not_detected";
            else if (!display.begin(SSD1306_SWITCHCAPVCC,found,false,false)) phase="allocation_failed";
            else {
                display.setTextColor(SSD1306_WHITE);
                display.setTextWrap(false);
                address=found;
                phase="ready";
            }
            if (!address.load()) { vTaskDelay(pdMS_TO_TICKS(1000)); continue; }
        }
        if (!responds(address.load())) {
            address=0;phase="disconnected";
            vTaskDelay(pdMS_TO_TICKS(1000));continue;
        }
        const auto gnss=gnss_receiver::snapshot();
        const uint64_t nowUs=esp_timer_get_time();
        JsonDocument sd;
        sd_recorder::status(sd.to<JsonObject>());
        const char* sdState=sd["state"] | "unknown";
        if (sd["card_present"].is<bool>() && !sd["card_present"].as<bool>()) sdState="card_missing";
        else if (sd_recorder::active() && !sd["active"].as<bool>()) sdState="closing";
        const auto text=display_status::build(gnss,nowUs,correction_router::sourceCode(),
                                              correction_router::ageMs(),sdState);
        display.clearDisplay();
        display.setTextSize(1);
        display.setCursor(0,0);display.print("MeridianV ");display.print(instrument::kVersion);
        display.drawFastHLine(0,10,128,SSD1306_WHITE);
        display.setTextSize(2);line(13,text.fix);
        display.setTextSize(1);line(31,text.satellites);
        line(39,text.corrections);line(47,text.storage);
        display.setCursor(0,56);
        const bool station=WiFi.status()==WL_CONNECTED;
        display.print(station ? "IP " : "AP ");
        display.print(station ? WiFi.localIP() : WiFi.softAPIP());
        JsonDocument power;
        power_manager::status(power.to<JsonObject>());
        if(power["shutdown_pending"].as<bool>()) {
            display.clearDisplay();display.setTextSize(1);
            line(8,"APAGANDO");line(24,sd_recorder::active()?"Cerrando memoria":"Corte solicitado");
            if(strcmp(power["state"]|"","power_still_present")==0)line(40,"Sigue alimentado");
        } else if((millis()/5000)%2==1) {
            display.fillRect(0,56,128,8,SSD1306_BLACK);display.setCursor(0,56);
            if(power["gauge_available"].as<bool>()) {
                display.print("BAT ");display.print(power["percent"].as<float>(),0);display.print("% ");
                display.print(power["voltage_v"].as<float>(),2);display.print("V");
            } else display.print("BAT sin lectura");
        }
        display.display();
        vTaskDelay(pdMS_TO_TICKS(1000));
    }
}
}
void begin() {
    // El dueño de Wire es esta tarea. Una OLED ausente o un bus atascado no
    // detienen la adquisición GNSS ni el bucle USB/BLE/WebSocket.
    phase="starting";
    if (xTaskCreate(worker,"oled",4096,nullptr,1,nullptr)!=pdPASS) phase="task_failed";
}
void status(JsonObject out) {
    out["state"]=phase.load();
    out["available"]=address.load()!=0;
    out["driver"]="ssd1306";
    out["width"]=128;out["height"]=64;
    if (address.load()) out["i2c_address"]=address.load();
    else out["i2c_address"]=nullptr;
    out["sda_gpio"]=board_profile::kSda;out["scl_gpio"]=board_profile::kScl;
}
}
