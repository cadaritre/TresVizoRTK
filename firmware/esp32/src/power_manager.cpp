#include "power_manager.h"
#include "power_sequence.h"
#include "board_profile.h"
#include "sd_recorder.h"
#include "firmware_update.h"
#include <Arduino.h>
#include <Wire.h>
#include <atomic>
namespace power_manager {
namespace {
std::atomic<unsigned> state{0}; // 0 activo, 1 cerrando, 2 señal OFF, 3 aún alimentado.
portMUX_TYPE gaugeMux = portMUX_INITIALIZER_UNLOCKED;
bool valid=false; float voltage=0, soc=0; uint32_t sampled=0;
power_sequence::Button button; uint32_t cutAt=0;
bool readRegister(uint8_t reg,uint16_t& value) {
    Wire.beginTransmission(0x36); Wire.write(reg);
    if(Wire.endTransmission(false)!=0) return false;
    if(Wire.requestFrom(uint8_t(0x36),uint8_t(2))!=2) return false;
    value=(uint16_t(Wire.read())<<8)|Wire.read(); return true;
}
}
void begin() {
    digitalWrite(board_profile::kPowerOff,LOW); pinMode(board_profile::kPowerOff,OUTPUT);
    pinMode(board_profile::kPowerPush,INPUT_PULLUP);
    button.changed=millis(); button.previous=digitalRead(board_profile::kPowerPush)==LOW;
}
bool pending(){ return state.load()!=0; }
bool requestShutdown(){
    if(pending()) return true;
    if(firmware_update::busy()) return false;
    state=1; return true;
}
void tick(){
    const uint32_t now=millis();
    const bool pressed=digitalRead(board_profile::kPowerPush)==LOW;
    // La pulsación de encendido nunca debe provocar el apagado al arrancar.
    if(button.held(pressed,now) && requestShutdown()) button.consumed();
    if(state==1 && sd_recorder::prepareShutdown()) {
        digitalWrite(board_profile::kPowerOff,HIGH);cutAt=now;state=2;
    }
    if(state==2 && now-cutAt>=500) state=3;
}
void sampleGauge(){
    uint16_t v=0,s=0;
    bool ok=readRegister(0x02,v) && readRegister(0x04,s);
    float volts=v*0.000078125f, percent=s/256.0f;
    ok=ok && volts>=2.5f && volts<=4.5f && percent<=110.0f;
    portENTER_CRITICAL(&gaugeMux);
    valid=ok;voltage=volts;soc=percent>100?100:percent;sampled=millis();
    portEXIT_CRITICAL(&gaugeMux);
}
void status(JsonObject out){
    bool ok;float v,s;uint32_t t;
    portENTER_CRITICAL(&gaugeMux);ok=valid;v=voltage;s=soc;t=sampled;portEXIT_CRITICAL(&gaugeMux);
    ok=ok && millis()-t<6000;
    const char* states[]={"running","closing_storage","cut_requested","power_still_present"};
    out["state"]=states[state.load()];out["shutdown_pending"]=pending();
    out["gauge_available"]=ok;out["battery_capacity_mah"]=3000;
    out["battery_present"]=nullptr; // Con USB, VBAT puede tener tensión sin celda.
    out["charging"]=nullptr; // STAT del MCP73831 sólo está conectado al LED.
    out["usb_present"]=nullptr;
    if(ok){out["voltage_v"]=v;out["percent"]=s;out["low_battery"]=s<=10 || v<=3.4f;}
    else {out["voltage_v"]=nullptr;out["percent"]=nullptr;out["low_battery"]=nullptr;}
    out["push_gpio"]=board_profile::kPowerPush;out["off_gpio"]=board_profile::kPowerOff;
}
}
