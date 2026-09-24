#include "correction_output.h"
#include "instrument.h"
#include "firmware_update.h"
#include <Preferences.h>
#include <WiFi.h>
#include <WiFiClient.h>
#include <WiFiServer.h>
#include <mbedtls/base64.h>
#include <atomic>
#include <cctype>
#include <cstring>

namespace correction_output {
namespace {
// Tramas RTCM del receptor. 1029 bytes es el máximo de RTCM3.
struct Frame {uint16_t length;uint8_t bytes[1029];};
QueueHandle_t queue=nullptr;
SemaphoreHandle_t lock=nullptr;
bool ready=false;
// La entrada NTRIP se reconecta sola tras un corte; la salida no lo hacia y
// era justo la que vive fija en el tripode. Se guarda y se reanuda igual.
Preferences store;
bool storeReady=false;

// --- publicación hacia un caster externo ---------------------------------
struct ServerConfig {String host,mount,password;uint16_t port=2101;};
ServerConfig serverConfig;
std::atomic<bool> serverWanted{false};
std::atomic<const char*> serverState{"stopped"},serverError{""};
std::atomic<uint32_t> serverFrames{0},serverDropped{0},serverReconnects{0};

// --- caster propio --------------------------------------------------------
constexpr size_t kMaxClients=2;
struct CasterConfig {String mount="MERIDIANV",password;uint16_t port=2101;};
CasterConfig casterConfig;
std::atomic<bool> casterWanted{false};
std::atomic<const char*> casterState{"stopped"};
std::atomic<uint32_t> casterClients{0},casterFrames{0};
// Tramas RTCM capturadas del receptor. Sin este contador no habia forma de
// distinguir "la base no emite" de "nadie se ha conectado a recogerlo".
std::atomic<uint32_t> captured{0};
std::atomic<uint32_t> lastCapture{0};
WiFiServer* listener=nullptr;
WiFiClient clients[kMaxClients];
uint16_t listeningPort=0;

// Fuera de la pila de la tarea: la trama es grande y el stack son 4 KiB.
Frame outbound;
char request[513];

bool valid(JsonVariantConst field,size_t max,bool empty=false){
 if(!field.is<const char*>())return false;
 JsonString s=field.as<JsonString>();
 if((!empty&&!s.size())||s.size()>max)return false;
 for(size_t i=0;i<s.size();++i){
  const uint8_t c=uint8_t(s.c_str()[i]);
  if(c<33||c>126)return false;
 }
 return true;
}

// El rover manda "GET /<mount>" y, si hay contraseña, Basic. El usuario no se
// comprueba: en una base de obra la credencial compartida es la contraseña.
bool authorized(const char* headers,const String& mount,const String& password){
 char wanted[64];
 snprintf(wanted,sizeof(wanted),"GET /%s",mount.c_str());
 if(strncmp(headers,wanted,strlen(wanted)))return false;
 const char after=headers[strlen(wanted)];
 if(after&&after!=' '&&after!='\r'&&after!='\n')return false;
 if(password.isEmpty())return true;
 const char* auth=strstr(headers,"Authorization: Basic ");
 if(!auth)return false;
 auth+=strlen("Authorization: Basic ");
 char encoded[128];size_t n=0;
 while(*auth&&*auth!='\r'&&*auth!='\n'&&n<sizeof(encoded)-1)encoded[n++]=*auth++;
 encoded[n]=0;
 unsigned char decoded[128];size_t decodedSize=0;
 if(mbedtls_base64_decode(decoded,sizeof(decoded)-1,&decodedSize,
    reinterpret_cast<const uint8_t*>(encoded),n))return false;
 decoded[decodedSize]=0;
 const char* colon=strchr(reinterpret_cast<char*>(decoded),':');
 const bool ok=colon&&password==String(colon+1);
 memset(decoded,0,sizeof(decoded));
 return ok;
}

void closeCaster(){
 for(size_t i=0;i<kMaxClients;++i)if(clients[i])clients[i].stop();
 if(listener){listener->stop();delete listener;listener=nullptr;}
 listeningPort=0;casterClients=0;
}

void serveCaster(){
 if(!casterWanted){if(listener)closeCaster();casterState="stopped";return;}
 if(WiFi.status()!=WL_CONNECTED&&!WiFi.softAPgetStationNum()){
  // El AP propio basta: un rover puede unirse a la red del equipo sin internet.
 }
 CasterConfig c;
 xSemaphoreTake(lock,portMAX_DELAY);c=casterConfig;xSemaphoreGive(lock);
 if(!listener||listeningPort!=c.port){
  closeCaster();
  listener=new WiFiServer(c.port);
  if(!listener){casterState="failed";casterWanted=false;return;}
  listener->begin();listener->setNoDelay(true);
  listeningPort=c.port;
 }
 if(WiFiClient incoming=listener->available()){
  size_t n=0;const uint32_t start=millis();
  while(millis()-start<2000&&n<sizeof(request)-1){
   if(!incoming.available()){vTaskDelay(1);continue;}
   const int b=incoming.read();
   if(b<0)break;
   request[n++]=char(b);request[n]=0;
   if(n>=4&&!memcmp(request+n-4,"\r\n\r\n",4))break;
  }
  request[n]=0;
  if(authorized(request,c.mount,c.password)){
   size_t slot=kMaxClients;
   for(size_t i=0;i<kMaxClients;++i)if(!clients[i]){slot=i;break;}
   if(slot<kMaxClients){
    incoming.print("ICY 200 OK\r\n\r\n");
    clients[slot]=incoming;
   } else incoming.print("HTTP/1.0 503 Service Unavailable\r\n\r\n"),incoming.stop();
  } else incoming.print("HTTP/1.0 401 Unauthorized\r\n\r\n"),incoming.stop();
  memset(request,0,sizeof(request));
 }
 uint32_t live=0;
 for(size_t i=0;i<kMaxClients;++i){
  if(clients[i]&&!clients[i].connected())clients[i].stop();
  if(clients[i])++live;
 }
 casterClients=live;
 casterState=live?"serving":"listening";
}

void worker(void*){
 WiFiClient upstream;
 unsigned backoff=1000;
 uint32_t lastAttempt=0;
 for(;;){
  serveCaster();
  // Publicación: conectar si se pidió y no hay socket vivo.
  if(serverWanted&&!firmware_update::busy()){
   if(!upstream.connected()){
    if(WiFi.status()!=WL_CONNECTED){serverState="waiting_network";}
    else if(millis()-lastAttempt>=backoff){
     ServerConfig c;
     xSemaphoreTake(lock,portMAX_DELAY);c=serverConfig;xSemaphoreGive(lock);
     serverState="connecting";lastAttempt=millis();
     upstream.setTimeout(2000);
     if(upstream.connect(c.host.c_str(),c.port,3000)){
      // NTRIP v1: el equipo se anuncia como fuente del punto de montaje.
      upstream.print("SOURCE "+c.password+" /"+c.mount+"\r\nSource-Agent: NTRIP TresVizo/0.6\r\nSTR: \r\n\r\n");
      size_t n=0;const uint32_t start=millis();
      while(millis()-start<5000&&n<sizeof(request)-1){
       if(!upstream.available()){vTaskDelay(1);continue;}
       const int b=upstream.read();
       if(b<0)break;
       request[n++]=char(b);request[n]=0;
       if(n>=2&&!memcmp(request+n-2,"\r\n",2))break;
      }
      if(!strncmp(request,"ICY 200 OK",10)||!strncmp(request,"OK",2)){
       serverState="publishing";serverError="";backoff=1000;
      } else {
       upstream.stop();serverError="caster_rejected_source";serverState="retry_wait";
       ++serverReconnects;backoff=std::min(backoff*2,30000U);
      }
      memset(request,0,sizeof(request));
     } else {
      serverError="connect_failed";serverState="retry_wait";
      ++serverReconnects;backoff=std::min(backoff*2,30000U);
     }
    }
   }
  } else if(upstream.connected()){upstream.stop();serverState="stopped";}
  if(!serverWanted)serverState=upstream.connected()?"stopping":"stopped";

  // Reparto de una trama a los dos destinos.
  if(xQueueReceive(queue,&outbound,pdMS_TO_TICKS(50))==pdTRUE){
   if(serverWanted&&upstream.connected()){
    if(upstream.write(outbound.bytes,outbound.length)==outbound.length)++serverFrames;
    else {++serverDropped;upstream.stop();serverError="write_failed";}
   }
   bool delivered=false;
   for(size_t i=0;i<kMaxClients;++i){
    if(!clients[i]||!clients[i].connected())continue;
    if(clients[i].write(outbound.bytes,outbound.length)==outbound.length)delivered=true;
    else clients[i].stop();
   }
   if(delivered)++casterFrames;
  }
  vTaskDelay(1);
 }
}
}

namespace {
void persist(){
 if(!storeReady)return;
 JsonDocument doc;
 doc["srv"]=serverWanted.load();
 doc["host"]=serverConfig.host;doc["mount"]=serverConfig.mount;
 doc["pass"]=serverConfig.password;doc["port"]=serverConfig.port;
 doc["cast"]=casterWanted.load();
 doc["cmount"]=casterConfig.mount;doc["cpass"]=casterConfig.password;doc["cport"]=casterConfig.port;
 String encoded;serializeJson(doc,encoded);
 store.putString("out",encoded);
}
void restore(){
 if(!storeReady)return;
 const String saved=store.getString("out","");
 if(saved.isEmpty())return;
 JsonDocument doc;
 if(deserializeJson(doc,saved,DeserializationOption::NestingLimit(3)))return;
 serverConfig.host=doc["host"]|"";serverConfig.mount=doc["mount"]|"";
 serverConfig.password=doc["pass"]|"";serverConfig.port=uint16_t(doc["port"]|2101);
 casterConfig.mount=doc["cmount"]|"MERIDIANV";casterConfig.password=doc["cpass"]|"";
 casterConfig.port=uint16_t(doc["cport"]|2101);
 // Solo se reanuda lo que estaba activo y tiene destino completo.
 if((doc["srv"]|false)&&serverConfig.host.length()&&serverConfig.mount.length()){
  serverWanted=true;serverState="starting";
 }
 if(doc["cast"]|false){casterWanted=true;casterState="starting";}
}
}

void begin(){
 lock=xSemaphoreCreateMutex();
 queue=xQueueCreate(6,sizeof(Frame));
 if(lock&&queue)ready=xTaskCreate(worker,"rtcm_out",4096,nullptr,1,nullptr)==pdPASS;
 storeReady=store.begin("rtcmout",false);
 if(ready)restore();
}

void publish(const uint8_t* frame,size_t length){
 if(!ready||!length||length>sizeof(Frame::bytes))return;
 captured.fetch_add(1);lastCapture=millis();
 if(!serverWanted&&!casterWanted)return; // nadie escucha: no llenar la cola
 Frame item;item.length=uint16_t(length);
 memcpy(item.bytes,frame,length);
 if(xQueueSend(queue,&item,0)!=pdTRUE)++serverDropped;
}

bool active(){return serverWanted||casterWanted;}

void status(JsonObject out){
 out["available"]=ready;
 // Lo que el receptor produce, independientemente de si alguien lo consume.
 out["frames_from_receiver"]=captured.load();
 const uint32_t mark=lastCapture.load();
 if(mark) out["last_frame_age_ms"]=millis()-mark; else out["last_frame_age_ms"]=nullptr;
 JsonObject server=out["ntrip_server"].to<JsonObject>();
 server["enabled"]=serverWanted.load();
 server["state"]=serverState.load();
 server["error"]=serverError.load();
 server["frames_sent"]=serverFrames.load();
 server["frames_dropped"]=serverDropped.load();
 server["reconnects"]=serverReconnects.load();
 JsonObject caster=out["local_caster"].to<JsonObject>();
 caster["enabled"]=casterWanted.load();
 caster["state"]=casterState.load();
 caster["clients"]=casterClients.load();
 caster["clients_max"]=kMaxClients;
 caster["frames_sent"]=casterFrames.load();
 caster["port"]=listeningPort;
 // Direcciones por las que un rover puede alcanzar el caster.
 caster["ap_address"]=WiFi.softAPIP().toString();
 caster["station_address"]=WiFi.status()==WL_CONNECTED?WiFi.localIP().toString():String();
}

int serverRequest(const String& method,JsonVariantConst body,JsonDocument& out){
 if(method=="GET"){status(out.to<JsonObject>());return 200;}
 if(method!="POST"||!body.is<JsonObjectConst>())return 400;
 if(!ready)return 503;
 if(body["action"]=="stop"&&body.size()==1){
  serverWanted=false;
  xSemaphoreTake(lock,portMAX_DELAY);serverConfig.password="";xSemaphoreGive(lock);
  persist();
  status(out.to<JsonObject>());return 200;
 }
 if(body["action"]!="start"||body.size()!=5||!valid(body["host"],128)||
    !valid(body["mountpoint"],96)||!valid(body["password"],128,true)||
    !body["port"].is<unsigned>()||body["port"].as<unsigned>()<1||body["port"].as<unsigned>()>65535)return 400;
 const String host=body["host"].as<const char*>(),mount=body["mountpoint"].as<const char*>();
 for(char c:host)if(!isalnum(static_cast<unsigned char>(c))&&c!='.'&&c!='-')return 400;
 for(char c:mount)if(!isalnum(static_cast<unsigned char>(c))&&c!='_'&&c!='-'&&c!='.')return 400;
 if(!instrument::stationConfigured()){out["message"]="No hay red Wi-Fi configurada. El equipo no puede alcanzar un caster externo.";return 409;}
 if(serverWanted){out["message"]="La publicación ya está activa. Deténla antes de cambiar el destino.";return 409;}
 xSemaphoreTake(lock,portMAX_DELAY);
 serverConfig.host=host;serverConfig.mount=mount;
 serverConfig.password=body["password"].as<const char*>();
 serverConfig.port=uint16_t(body["port"].as<unsigned>());
 xSemaphoreGive(lock);
 serverFrames=serverDropped=serverReconnects=0;
 serverError="";serverState="starting";serverWanted=true;
 persist();
 status(out.to<JsonObject>());return 202;
}

int casterRequest(const String& method,JsonVariantConst body,JsonDocument& out){
 if(method=="GET"){status(out.to<JsonObject>());return 200;}
 if(method!="POST"||!body.is<JsonObjectConst>())return 400;
 if(!ready)return 503;
 if(body["action"]=="stop"&&body.size()==1){
  casterWanted=false;casterState="stopping";
  persist();
  status(out.to<JsonObject>());return 200;
 }
 if(body["action"]!="start"||body.size()!=4||!valid(body["mountpoint"],32)||
    !valid(body["password"],63,true)||
    !body["port"].is<unsigned>()||body["port"].as<unsigned>()<1||body["port"].as<unsigned>()>65535)return 400;
 const String mount=body["mountpoint"].as<const char*>();
 for(char c:mount)if(!isalnum(static_cast<unsigned char>(c))&&c!='_'&&c!='-')return 400;
 // El panel web vive en el 80: compartir puerto dejaría ambos inservibles.
 if(body["port"].as<unsigned>()==80){out["message"]="El puerto 80 lo usa el panel del equipo. Elige otro, por ejemplo 2101.";return 400;}
 if(casterWanted){out["message"]="El caster local ya está activo. Detenlo antes de cambiar sus ajustes.";return 409;}
 xSemaphoreTake(lock,portMAX_DELAY);
 casterConfig.mount=mount;
 casterConfig.password=body["password"].as<const char*>();
 casterConfig.port=uint16_t(body["port"].as<unsigned>());
 xSemaphoreGive(lock);
 casterFrames=0;casterState="starting";casterWanted=true;
 persist();
 status(out.to<JsonObject>());return 202;
}
}
