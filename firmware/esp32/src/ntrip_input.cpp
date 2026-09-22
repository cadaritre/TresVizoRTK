#include "ntrip_input.h"
#include "gnss_control.h"
#include "instrument.h"
#include "correction_router.h"
#include "firmware_update.h"
#include "rtcm3.h"
#include <WiFi.h>
#include <WiFiClient.h>
#include <mbedtls/base64.h>
#include <atomic>
#include <cctype>
#include <cstring>
namespace ntrip_input {
namespace {
struct Config {String host,mount,user,password;uint16_t port=2101;};
Config config;
SemaphoreHandle_t lock;bool ready=false;
std::atomic<bool> wanted{false};std::atomic<uint32_t> generation{0},frames{0},rejected{0},bytes{0},reconnects{0},crcErrors{0};
std::atomic<const char*> state{"stopped"}, failure{""};
bool valid(JsonVariantConst field,size_t max,bool empty=false){
 if(!field.is<const char*>())return false;
 JsonString s=field.as<JsonString>();if((!empty&&!s.size())||s.size()>max)return false;
 for(size_t i=0;i<s.size();++i)if(uint8_t(s.c_str()[i])<33 || uint8_t(s.c_str()[i])>126)return false;
 return true;
}
bool current(uint32_t id){return wanted && generation==id && !firmware_update::busy();}
// Fuera de la pila del worker (6 KiB) y con una sola tarea usandolo.
char header[2049];
void worker(void*) {
 WiFiClient client;gnss::Rtcm3Parser parser;unsigned backoff=1000;
 for(;;){
  if(!wanted){state="stopped";vTaskDelay(pdMS_TO_TICKS(100));continue;}
  if(firmware_update::busy() || WiFi.status()!=WL_CONNECTED){state="waiting_network";vTaskDelay(pdMS_TO_TICKS(100));continue;}
  Config c;xSemaphoreTake(lock,portMAX_DELAY);c=config;xSemaphoreGive(lock);const uint32_t id=generation;
  state="connecting";failure="";client.setTimeout(2000);
  if(client.connect(c.host.c_str(),c.port,2000) && current(id)) {
   String credentials=c.user+":"+c.password;unsigned char encoded[264];size_t encodedSize=0;
   const int encodeError=mbedtls_base64_encode(encoded,sizeof(encoded),&encodedSize,reinterpret_cast<const uint8_t*>(credentials.c_str()),credentials.length());
   credentials="";
   if(encodeError||!encodedSize){
    memset(encoded,0,sizeof(encoded));client.stop();failure="credentials_encode_failed";
    state="retry_wait";vTaskDelay(pdMS_TO_TICKS(1000));continue;
   }
   String request="GET /"+c.mount+" HTTP/1.0\r\nHost: "+c.host+"\r\nUser-Agent: NTRIP TresVizo/0.5\r\nAuthorization: Basic "+String(reinterpret_cast<char*>(encoded),encodedSize)+"\r\nConnection: close\r\n\r\n";
   client.print(request);request="";memset(encoded,0,sizeof(encoded));
   // Lectura byte a byte deliberada: un bloque se tragaria RTCM del flujo. Se
   // acumula en un buffer fijo porque concatenar String por byte era cuadratico.
   size_t headerLength=0;uint32_t start=millis();bool accepted=false,headersDone=false;
   while(current(id) && millis()-start<5000 && headerLength<sizeof(header)-1 && (client.connected()||client.available())){
    const int byte=client.read();
    if(byte<0){vTaskDelay(1);continue;}
    header[headerLength++]=char(byte);header[headerLength]=0;
    if(headerLength==12 && !memcmp(header,"ICY 200 OK\r\n",12)){accepted=headersDone=true;break;}
    if(headerLength>=4 && !memcmp(header+headerLength-4,"\r\n\r\n",4)){
     accepted=!strncmp(header,"HTTP/1.0 200 ",13)||!strncmp(header,"HTTP/1.1 200 ",13);
     for(size_t i=0;i<headerLength;++i)header[i]=char(tolower(static_cast<unsigned char>(header[i])));
     if(strstr(header,"transfer-encoding:")||strstr(header,"content-encoding:"))accepted=false;
     headersDone=true;break;
    }
   }
   if(accepted && headersDone && current(id)){
    state="streaming";parser.reset();uint32_t last=millis();backoff=1000;
    while(current(id) && WiFi.status()==WL_CONNECTED && (client.connected()||client.available()) && millis()-last<10000){
     const auto badBefore=parser.rejected;
     for(int n=0;n<2048 && client.available();++n){
      int b=client.read();if(b<0)break;++bytes;
      parser.feed(uint8_t(b),[&](const uint8_t* p,size_t size){
       last=millis();if(correction_router::submit(correction_router::Source::Ntrip,p,size))++frames;else ++rejected;
      });
     }
     crcErrors+=parser.rejected-badBefore;
     vTaskDelay(1);
    }
    failure="stream_ended_or_no_valid_rtcm";
   } else failure="caster_response_rejected";
  } else failure="connect_failed";
  client.stop();c.password="";
  if(!current(id))continue;
  ++reconnects;state="retry_wait";uint32_t since=millis();
  while(current(id)&&millis()-since<backoff)vTaskDelay(pdMS_TO_TICKS(50));
  backoff=std::min(backoff*2,30000U);
 }
}
}
void begin(){lock=xSemaphoreCreateMutex();if(lock)ready=xTaskCreate(worker,"ntrip_rx",6144,nullptr,1,nullptr)==pdPASS;}
bool active(){return wanted;}
void status(JsonObject out){out["state"]=state.load();out["error"]=failure.load();out["available"]=ready;out["enabled"]=wanted.load();out["network_configured"]=instrument::stationConfigured();out["frames_forwarded"]=frames.load();out["frames_dropped"]=rejected.load();out["bytes_received"]=bytes.load();out["reconnects"]=reconnects.load();out["rtcm_crc_errors"]=crcErrors.load();out["tls_supported"]=false;out["gga_vrs_supported"]=false;out["credentials_persisted"]=false;}
int request(const String& method,JsonVariantConst body,JsonDocument& out){
 if(method=="GET"){status(out.to<JsonObject>());return 200;}
 if(method!="POST"||!body.is<JsonObjectConst>())return 400;
 if(body["action"]=="stop" && body.size()==1){wanted=false;++generation;correction_router::select("none");xSemaphoreTake(lock,portMAX_DELAY);config.password="";xSemaphoreGive(lock);state="stopping";status(out.to<JsonObject>());return 200;}
 if(body["action"]!="start"||body.size()!=6||!valid(body["host"],128)||!valid(body["mountpoint"],96)||!valid(body["username"],64,true)||!valid(body["password"],128,true)||!body["port"].is<unsigned>()||body["port"].as<unsigned>()<1||body["port"].as<unsigned>()>65535)return 400;
 String host=body["host"].as<const char*>(),mount=body["mountpoint"].as<const char*>(),user=body["username"].as<const char*>();
 // Cast explicito: isalnum() con char con signo es comportamiento indefinido.
 for(char c:host)if(!isalnum(static_cast<unsigned char>(c))&&c!='.'&&c!='-')return 400;
 for(char c:mount)if(!isalnum(static_cast<unsigned char>(c))&&c!='_'&&c!='-'&&c!='.')return 400;
 if(user.indexOf(':')>=0)return 400;
 if(!ready)return 503;
 // Sin red externa configurada la tarea se quedaría en waiting_network para
 // siempre, que parece un problema pasajero y no lo es.
 if(!instrument::stationConfigured()){out["message"]="No hay red Wi-Fi configurada. Añade tu hotspot de 2.4 GHz en Configuración antes de conectar NTRIP.";return 409;}
 if(active() || strcmp(state.load(),"stopped")!=0){out["message"]="Hay una conexión NTRIP activa. Pulsa «Detener» en este mismo apartado y vuelve a intentarlo.";return 409;}
 if(!gnss_control::roverReady()){out["message"]="Consulta y confirma el modo rover del receptor antes de conectar.";return 409;}
 xSemaphoreTake(lock,portMAX_DELAY);config.host=host;config.mount=mount;config.user=user;config.password=body["password"].as<const char*>();config.port=body["port"];xSemaphoreGive(lock);
 correction_router::select("ntrip");++generation;wanted=true;state="starting";status(out.to<JsonObject>());return 202;
}
}
