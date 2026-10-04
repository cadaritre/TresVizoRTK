#include "host/Arduino.h"
#include "../src/correction_output.cpp"
namespace cancellable_connection {
bool write(WiFiClient& client,const uint8_t* data,size_t size,const std::function<bool()>& current,uint32_t){if(!current())return false;client.print(String(reinterpret_cast<const char*>(data),size));return true;}
bool connect(WiFiClient& client,const String& host,uint16_t port,const std::function<bool()>& current){return current() && client.connect(host.c_str(),port,2000) && current();}
}
namespace instrument {bool stationConfigured(){return true;}}
namespace firmware_update {bool busy(){return false;}}
namespace radio_module {void publish(const uint8_t*,size_t){}}
JsonDocument body(const char* s){JsonDocument d;assert(!deserializeJson(d,s));return d;}
const char* first="{\"action\":\"start\",\"host\":\"first.test\",\"port\":2101,\"mountpoint\":\"FIRST\",\"password\":\"p\"}";
const char* second="{\"action\":\"start\",\"host\":\"second.test\",\"port\":2101,\"mountpoint\":\"SECOND\",\"password\":\"p\"}";
int start(const char* json){JsonDocument out;return correction_output::serverRequest("POST",body(json).as<JsonVariantConst>(),out);}
struct Done {};
int main(){
 correction_output::begin();JsonDocument out;
 assert(start(first)==202);const uint32_t old=correction_output::serverGeneration;
 const uint8_t frame[]{0xd3,0,0,0,0,0};correction_output::publish(frame,sizeof frame);
 assert(start(second)==202 && correction_output::serverGeneration>old);
 assert(correction_output::queue->items.size()==1);
 correction_output::Frame queued;assert(xQueueReceive(correction_output::queue,&queued,0)==pdTRUE);
 assert(queued.serverGeneration!=correction_output::serverGeneration); // cola anterior no llega al destino nuevo
 correction_output::setServerState(old,"retry_wait","old_error");
 assert(std::string(correction_output::serverState.load())=="starting");
 assert(start("{\"action\":\"start\",\"host\":\"bad\\r\"}")==400);
 assert(correction_output::serverConfig.host=="second.test");
 // Cambio durante conexión de publicación: no SOURCE/credenciales al caster viejo.
 assert(start(first)==202);unsigned attempts=0;hostSocketRequests.clear();
 hostOnConnect=[&](const std::string& host){if(attempts++==0){assert(host=="first.test");assert(start(second)==202);return true;}assert(host=="second.test");throw Done();return false;};
 try{correction_output::worker(nullptr);assert(false);}catch(const Done&){}
 hostOnConnect={};assert(attempts==2 && hostSocketRequests.empty());
 const char* casterA="{\"action\":\"start\",\"mountpoint\":\"A\",\"port\":2101,\"password\":\"\"}";
 const char* casterB="{\"action\":\"start\",\"mountpoint\":\"B\",\"port\":2101,\"password\":\"\"}";
 assert(correction_output::casterRequest("POST",body(casterA).as<JsonVariantConst>(),out)==202);
 correction_output::serveCaster();const uint32_t listener=correction_output::listeningGeneration;
 assert(correction_output::casterRequest("POST",body(casterB).as<JsonVariantConst>(),out)==202);
 correction_output::serveCaster();assert(correction_output::listeningGeneration!=listener && hostListeners.size()==2);
 assert(correction_output::casterRequest("POST",body("{\"action\":\"start\",\"mountpoint\":\"C\",\"port\":80,\"password\":\"\"}").as<JsonVariantConst>(),out)==400);
 assert(correction_output::casterConfig.mount=="B");
 correction_output::closeCaster();std::puts("output_priority_integration: OK");
}
