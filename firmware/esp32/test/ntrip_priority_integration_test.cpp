#include "host/Arduino.h"
#include "../src/ntrip_input.cpp"
namespace cancellable_connection {
bool write(WiFiClient& client,const uint8_t* data,size_t size,const std::function<bool()>& current,uint32_t){if(!current())return false;client.print(String(reinterpret_cast<const char*>(data),size));return true;}
bool connect(WiFiClient& client,const String& host,uint16_t port,const std::function<bool()>& current){return current() && client.connect(host.c_str(),port,2000) && current();}
}
using namespace std::string_literals;
namespace {bool base=false, wantsBase=false, gnssBusy=false;std::string chosen="none",selected="none";uint32_t routeGeneration=0;unsigned submitted=0;}
namespace gnss_control {bool isBase(){return base;}bool baseRequested(){return wantsBase;}bool isRover(){return !base;}bool busy(){return gnssBusy;}}
namespace instrument {bool stationConfigured(){return true;}}
namespace firmware_update {bool busy(){return false;}}
namespace correction_router {
bool select(const char* source){if(selected!=source)++routeGeneration;selected=source;return true;}
bool choose(const char* source){chosen=source;return select(source);}
bool ntripAllowed(){return chosen=="ntrip" || chosen=="none";}
bool bleChosen(){return chosen=="ble";}bool radioChosen(){return chosen=="radio";}
bool submit(Source,const uint8_t*,size_t){++submitted;return true;}
}
JsonDocument body(const char* s){JsonDocument d;assert(!deserializeJson(d,s));return d;}
const char* first="{\"action\":\"start\",\"host\":\"first.test\",\"port\":2101,\"mountpoint\":\"FIRST\",\"username\":\"u\",\"password\":\"p\"}";
const char* second="{\"action\":\"start\",\"host\":\"second.test\",\"port\":2101,\"mountpoint\":\"SECOND\",\"username\":\"u\",\"password\":\"p\"}";
int start(const char* s){JsonDocument out;return ntrip_input::request("POST",body(s).as<JsonVariantConst>(),out);}
struct Done {};
void runWorker(){try{ntrip_input::worker(nullptr);assert(false);}catch(const Done&){}hostOnConnect={};hostOnDelay={};hostOnRead={};}
int main(){
 ntrip_input::begin();JsonDocument out;
 assert(start(first)==202);const uint32_t old=ntrip_input::generation;
 const uint32_t route=routeGeneration;
 assert(start(second)==202 && ntrip_input::generation>old && routeGeneration>route);
 assert(ntrip_input::config.host=="second.test");
 assert(start("{\"action\":\"start\",\"host\":\"bad\\rhost\"}")==400);
 assert(ntrip_input::config.host=="second.test" && ntrip_input::active());
 ntrip_input::publishState(old,"retry_wait","old_error");
 assert(std::string(ntrip_input::state.load())=="starting" && std::string(ntrip_input::failure.load()).empty());
 // Una reconexión atascada en connect no debe mandar credenciales ni error viejos.
 assert(start(first)==202);hostSocketRequests.clear();unsigned attempts=0;
 hostOnConnect=[&](const std::string& host){
  if(attempts++==0){assert(host=="first.test");assert(start(second)==202);return true;}
  assert(host=="second.test");assert(std::string(ntrip_input::failure.load()).empty());throw Done();return false;
 };
 runWorker();assert(attempts==2 && hostSocketRequests.empty());
 // Sustituir sourcetable durante connect: no GET antiguo ni tabla en la nueva sesión.
 ntrip_input::stopForUser();
 assert(ntrip_input::sourcetableRequest("POST",body("{\"host\":\"table.test\",\"port\":2101}").as<JsonVariantConst>(),out)==202);
 hostOnConnect=[&](const std::string&){assert(start(second)==202);return true;};
 WiFiClient client;ntrip_input::fetchSourcetable(client);hostOnConnect={};
 assert(ntrip_input::active() && !ntrip_input::tableWanted && hostSocketRequests.empty());
 // Cambio durante lectura de RTCM: el callback de la trama anterior no la envía.
 std::string frame="\xd3\x00\x04\x3e\xd0\x00\x00"s;
 const uint32_t crc=gnss::crc24q(reinterpret_cast<const uint8_t*>(frame.data()),frame.size());
 frame+=char(crc>>16);frame+=char(crc>>8);frame+=char(crc);
 hostSocketInput="ICY 200 OK\r\n"+frame;assert(start(first)==202);attempts=0;unsigned reads=0;
 hostOnConnect=[&](const std::string&){if(attempts++==1)throw Done();return true;};
 hostOnRead=[&](){if(++reads==hostSocketInput.size())assert(start(second)==202);};
 runWorker();assert(submitted==0);
 // Parar y volver a arrancar no requiere esperar al tick del socket.
 ntrip_input::stopForUser();assert(start(first)==202 && !ntrip_input::userStopped);
 WiFi.state=0;assert(start(second)==202); // se acepta y espera red en segundo plano
 WiFi.state=WL_CONNECTED;
 // Cambiar perfil reemplaza conexión; fallo NVS conserva selección y conexión.
 assert(ntrip_input::profileRequest("POST",body("{\"action\":\"save\",\"name\":\"P\",\"host\":\"profile.test\",\"port\":2101,\"mountpoint\":\"M\",\"username\":\"u\",\"password\":\"p\"}").as<JsonVariantConst>(),out)==200);
 hostStorageFails=true;const uint32_t unchanged=ntrip_input::generation;
 assert(ntrip_input::profileRequest("POST",body("{\"action\":\"connect\",\"name\":\"P\"}").as<JsonVariantConst>(),out)==503);
 assert(ntrip_input::generation==unchanged && ntrip_input::lastUsed==-1);
 hostStorageFails=false;
 assert(ntrip_input::profileRequest("POST",body("{\"action\":\"connect\",\"name\":\"P\"}").as<JsonVariantConst>(),out)==202);
 assert(ntrip_input::config.host=="profile.test");
 // La automatización no contradice Detener, ni reanuda durante transición a base.
 ntrip_input::stopForUser();ntrip_input::tick();assert(!ntrip_input::active());
 ntrip_input::userStopped=false;wantsBase=true;ntrip_input::tick();assert(!ntrip_input::active());
 wantsBase=false;gnssBusy=true;ntrip_input::tick();assert(!ntrip_input::active());
 gnssBusy=false;ntrip_input::tick();assert(ntrip_input::active());
 base=true;ntrip_input::tick();assert(!ntrip_input::active());
 assert(start(second)==409);
 std::puts("ntrip_priority_integration: OK");
}
