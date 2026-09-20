#include "sd_recorder.h"
#include "gnss_control.h"
#include "gnss_receiver.h"
#include "correction_router.h"
#include <atomic>
namespace gnss_control {
namespace {
SemaphoreHandle_t mutex;
String commands[10], mode, version, action, failure;
String expectedMode;
unsigned count=0, index=0;
bool sent=false, ack=false, readback=false;
uint32_t started=0, job=0;
std::atomic<uint32_t> modeAt{0};
std::atomic<bool> running{false}, rover{false}, ellipsoid{false};
const char* phase="idle";
char line[1024]; size_t length=0;
void finish(const char* state, const char* error="") { phase=state;failure=error;running=false; }
void add(const String& c) { if(count<10) commands[count++]=c; }
bool needsReply() { return commands[index]=="MODE" || commands[index]=="VERSIONA"; }
void acceptLine() {
    line[length]=0; char* star=strrchr(line,'*');
    if(!star || (strlen(star+1)!=2 && strlen(star+1)!=8)) return;
    char* end=nullptr; unsigned long expected=strtoul(star+1,&end,16);
    if(*end) return;
    uint32_t sum=0;
    if(strlen(star+1)==2) {for(char* p=line;p<star;++p) sum^=*p;}
    else {for(char* p=line+1;p<star;++p) {sum^=uint8_t(*p);for(int bit=0;bit<8;++bit)sum=(sum>>1)^((sum&1)?0xedb88320U:0);}}
    if(sum!=expected) return;
    *star=0;
    if(!running || !sent) return;
    const String prefix="$command,"+commands[index]+",response: ";
    if(String(line).startsWith(prefix)) {
        if(String(line+prefix.length())!="OK") {finish("failed","Receptor rechazó el comando.");return;}
        ack=true;
        if(commands[index]=="CONFIG UNDULATION 0.0000") ellipsoid=true;
        if(commands[index]=="CONFIG UNDULATION AUTO") ellipsoid=false;
    }
    if(commands[index]=="MODE" && !strncmp(line,"#MODE,",6)) {
        char* p=strchr(line,';'); if(!p)return;
        mode=p+1;while(mode.endsWith(","))mode.remove(mode.length()-1);
        rover=mode=="MODE ROVER SURVEY";modeAt=millis();readback=true;
    }
    if(commands[index]=="VERSIONA" && !strncmp(line,"#VERSIONA,",10)) {
        char* p=strchr(line,';');if(!p)return;
        version=String(p+1).substring(0,192);readback=true;
    }
}
int prepare(const String& name, JsonDocument& out) {
    if(!gnss_receiver::snapshot().enabled) {out["message"]="UART no disponible.";return 503;}
    if(sd_recorder::active()){out["message"]="Cierra la grabación antes de configurar el GPS.";return 409;}
    if(running) {out["message"]="Operación GNSS en curso.";return 409;}
    JsonDocument router;correction_router::status(router.to<JsonObject>());
    if(router["active_source"]!="none") {out["message"]="Detén las correcciones antes de configurar el GPS.";return 409;}
    count=index=0;sent=ack=readback=false;failure="";expectedMode="";action=name;
    return 0;
}
int launch(JsonDocument& out) {
    phase="running";running=true;++job;out["job_id"]=job;out["state"]=phase;out["saved"]=false;return 202;
}
}
void begin(){mutex=xSemaphoreCreateMutex();}
bool busy(){return running;}
bool roverReady(){return rover && !running && millis()-modeAt.load()<30000;}
const char* heightReference(){return ellipsoid?"ellipsoidal_user_configured":"receiver_msl";}
void feed(char byte) {
    if(!mutex || xSemaphoreTake(mutex,portMAX_DELAY)!=pdTRUE)return;
    if(byte=='$'||byte=='#')length=0;
    if(byte=='\n') {if(length)acceptLine();length=0;}
    else if(byte!='\r') {if(length<sizeof(line)-1)line[length++]=byte;else length=0;}
    xSemaphoreGive(mutex);
}
void tick(HardwareSerial& uart) {
    if(!mutex || xSemaphoreTake(mutex,portMAX_DELAY)!=pdTRUE)return;
    if(running) {
        if(!sent) {
            String wire=commands[index]+"\r\n";
            if(uart.availableForWrite()>=int(wire.length())) {
                uart.write(reinterpret_cast<const uint8_t*>(wire.c_str()),wire.length());
                sent=true;ack=readback=false;started=millis();
            }
        } else if(ack && (!needsReply() || readback)) {
            if(++index==count) {
                if(expectedMode.length() && !mode.startsWith(expectedMode))finish("partial_or_unknown","Modo leído distinto del solicitado.");
                else finish(action=="base"?"base_mode_confirmed_coordinates_unverified":"confirmed");
            } else sent=false;
        } else if(millis()-started>4000) finish("partial_or_unknown","Sin ACK/lectura a tiempo; consulta antes de repetir.");
    }
    xSemaphoreGive(mutex);
}
int start(JsonVariantConst body,JsonDocument& out) {
    if(!mutex)return 503;
    if(!body.is<JsonObjectConst>() || !body["action"].is<const char*>())return 400;
    String name=body["action"].as<const char*>();
    if(body["action"].as<JsonString>().size()!=name.length())return 400;
    if(name!="query" && name!="rover" && name!="telemetry" && name!="raw_profile")return 400;
    if(body.size()!=(name=="telemetry"?2:1))return 400;
    if(name=="telemetry" && (!body["hz"].is<unsigned>() || (body["hz"]!=1 && body["hz"]!=5 && body["hz"]!=10)))return 400;
    xSemaphoreTake(mutex,portMAX_DELAY);
    int code=prepare(name,out);
    if(!code) {
        if(name=="raw_profile") {
            add("OBSVMB COM2 1");
            for(const char* log:{"GPSEPHB","GLOEPHB","GALEPHB","BDSEPHB","BD3EPHB"})add(String(log)+" COM2 30");
        }
        if(name=="query") {add("VERSIONA");add("MODE");}
        if(name=="rover") {rover=false;mode="";add("MODE ROVER SURVEY");add("CONFIG UNDULATION AUTO");add("MODE");expectedMode="MODE ROVER SURVEY";}
        if(name=="telemetry")add("GPGGA COM2 "+String(1.0/body["hz"].as<unsigned>(),1));
        code=launch(out);
    }
    xSemaphoreGive(mutex);return code;
}
int applyBase(JsonVariantConst plan,JsonDocument& out) {
    if(!mutex)return 503;
    if(plan["method"]=="known") {
        String datum=plan["datum"]|"";datum.toUpperCase();datum.replace(" ","");
        if(datum!="WGS84" && datum!="WGS-84"){out["message"]="Solo WGS84; no se transforman coordenadas.";return 400;}
    }
    xSemaphoreTake(mutex,portMAX_DELAY);int code=prepare("base",out);
    if(!code){
        rover=false;mode="";
        String command="MODE BASE "+String(plan["station_id"].as<unsigned>())+" ";
        if(plan["method"]=="known") {
            add("CONFIG UNDULATION 0.0000");
            command+=String(plan["latitude_deg"].as<double>(),11)+" "+String(plan["longitude_deg"].as<double>(),11)+" "+String(plan["arp_ellipsoid_height_m"].as<double>(),4);
        } else command+="TIME "+String(plan["average_seconds"].as<unsigned>())+" "+String(plan["reuse_distance_m"].as<double>(),4);
        add(command);add("MODE");expectedMode="MODE BASE";code=launch(out);
    }
    xSemaphoreGive(mutex);return code;
}
void status(JsonObject out){
    if(!mutex){out["state"]="unavailable";return;}
    xSemaphoreTake(mutex,portMAX_DELAY);
    out["state"]=phase;out["job_id"]=job;out["action"]=action;out["completed_commands"]=index;
    out["mode"]=mode;out["version"]=version;out["error"]=failure;out["saved"]=false;
    out["base_coordinates_verified"]=false;out["source"]="esp32_uart";
    xSemaphoreGive(mutex);
}
}
