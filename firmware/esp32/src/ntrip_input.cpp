#include "ntrip_input.h"
#include "gnss_control.h"
#include "instrument.h"
#include "correction_router.h"
#include "firmware_update.h"
#include "rtcm3.h"
#include <Preferences.h>
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

// Perfiles guardados. Hasta ahora las credenciales vivían solo en memoria y se
// perdían en cada arranque: en campo eso obliga a teclear un caster completo
// después de cada corte de alimentación.
constexpr size_t kMaxProfiles=5;
struct Profile {String name,host,mount,user,password;uint16_t port=2101;};
Profile profiles[kMaxProfiles];
size_t profileCount=0;
// Índice del último perfil usado y decisión explícita del usuario. "Ninguno"
// es una elección que se guarda: no es lo mismo que no haber elegido nunca.
int lastUsed=-1;
bool autoConnect=false;
Preferences store;
bool storeReady=false;

// Sourcetable del caster. Se resuelve en el mismo worker porque la radio y el
// socket son uno solo; pedirla mientras se transmite cortaría las correcciones.
constexpr size_t kMaxMounts=24;
struct Mount {String name,format,country;bool needsGga=false;};
Mount mounts[kMaxMounts];
size_t mountCount=0;
std::atomic<bool> tableWanted{false};
std::atomic<const char*> tableState{"idle"};
String tableHost;uint16_t tablePort=2101;
std::atomic<bool> wanted{false};std::atomic<uint32_t> generation{0},frames{0},rejected{0},bytes{0},reconnects{0},crcErrors{0};
std::atomic<const char*> state{"stopped"}, failure{""};
bool valid(JsonVariantConst field,size_t max,bool empty=false){
 if(!field.is<const char*>())return false;
 JsonString s=field.as<JsonString>();if((!empty&&!s.size())||s.size()>max)return false;
 for(size_t i=0;i<s.size();++i)if(uint8_t(s.c_str()[i])<33 || uint8_t(s.c_str()[i])>126)return false;
 return true;
}
bool current(uint32_t id){return wanted && generation==id && !firmware_update::busy();}

int findProfile(const String& name){
 for(size_t i=0;i<profileCount;++i)if(profiles[i].name==name)return int(i);
 return -1;
}
// Un solo registro NVS: o se guarda entero o no se toca nada.
bool persistProfiles(){
 if(!storeReady)return false;
 JsonDocument doc;
 doc["schema"]=1;doc["last"]=lastUsed;doc["auto"]=autoConnect;
 JsonArray list=doc["profiles"].to<JsonArray>();
 for(size_t i=0;i<profileCount;++i){
  JsonObject o=list.add<JsonObject>();
  o["name"]=profiles[i].name;o["host"]=profiles[i].host;o["port"]=profiles[i].port;
  o["mount"]=profiles[i].mount;o["user"]=profiles[i].user;o["pass"]=profiles[i].password;
 }
 String encoded;serializeJson(doc,encoded);
 return store.putString("profiles",encoded)==encoded.length();
}
void loadProfiles(){
 if(!storeReady)return;
 const String saved=store.getString("profiles","");
 if(saved.isEmpty())return;
 JsonDocument doc;
 if(deserializeJson(doc,saved,DeserializationOption::NestingLimit(4)))return;
 if((doc["schema"]|0)!=1||!doc["profiles"].is<JsonArrayConst>())return;
 size_t n=0;
 for(JsonVariantConst item:doc["profiles"].as<JsonArrayConst>()){
  if(n==kMaxProfiles)break;
  if(!item["name"].is<const char*>()||!item["host"].is<const char*>())break;
  profiles[n].name=item["name"].as<const char*>();
  profiles[n].host=item["host"].as<const char*>();
  profiles[n].mount=item["mount"].as<const char*>();
  profiles[n].user=item["user"].as<const char*>();
  profiles[n].password=item["pass"].as<const char*>();
  profiles[n].port=item["port"].is<unsigned>()?uint16_t(item["port"].as<unsigned>()):2101;
  if(profiles[n].name.isEmpty()||profiles[n].host.isEmpty())break;
  ++n;
 }
 profileCount=n;
 autoConnect=doc["auto"]|false;
 const int last=doc["last"]|-1;
 lastUsed=(last>=0&&size_t(last)<profileCount)?last:-1;
 if(lastUsed<0)autoConnect=false;
}
void applyProfile(const Profile& p){
 xSemaphoreTake(lock,portMAX_DELAY);
 config.host=p.host;config.mount=p.mount;config.user=p.user;config.password=p.password;config.port=p.port;
 xSemaphoreGive(lock);
}
void profilesJson(JsonObject out){
 JsonArray list=out["profiles"].to<JsonArray>();
 for(size_t i=0;i<profileCount;++i){
  JsonObject o=list.add<JsonObject>();
  o["name"]=profiles[i].name;o["host"]=profiles[i].host;o["port"]=profiles[i].port;
  o["mountpoint"]=profiles[i].mount;o["username"]=profiles[i].user;
  // La contraseña guardada no sale del equipo.
  o["has_password"]=!profiles[i].password.isEmpty();
 }
 out["profiles_max"]=kMaxProfiles;
 // Nulo cuando el usuario eligió "ninguno" a propósito; autoconnect lo distingue
 // de no haber elegido nunca.
 if(lastUsed>=0)out["selected"]=profiles[lastUsed].name; else out["selected"]=nullptr;
 out["autoconnect"]=autoConnect;
 out["storage_ready"]=storeReady;
}
// Fuera de la pila del worker (6 KiB) y con una sola tarea usandolo.
char header[2049];
char tableLine[256];

// Registro STR de una sourcetable NTRIP:
// STR;mount;id;formato;detalle;portadora;sistema;red;pais;lat;lon;nmea;...
void parseStr(const char* line){
 if(mountCount>=kMaxMounts)return;
 const char* field[12]={nullptr};
 unsigned count=0;const char* p=line;
 field[count++]=p;
 for(;*p&&count<12;++p)if(*p==';')field[count++]=p+1;
 if(count<12)return;
 auto cut=[](const char* s)->String{
  String v;for(const char* q=s;*q&&*q!=';';++q)v+=*q;return v;
 };
 const String name=cut(field[1]);
 if(name.isEmpty())return;
 mounts[mountCount].name=name;
 mounts[mountCount].format=cut(field[3]);
 mounts[mountCount].country=cut(field[8]);
 // El campo 11 indica si el caster espera recibir GGA del rover. Este firmware
 // todavía no la envía: un punto con 1 puede no fijar nunca.
 mounts[mountCount].needsGga=cut(field[11])=="1";
 ++mountCount;
}

void fetchSourcetable(WiFiClient& client){
 if(WiFi.status()!=WL_CONNECTED){tableState="waiting_network";vTaskDelay(pdMS_TO_TICKS(200));return;}
 String host;uint16_t port;
 xSemaphoreTake(lock,portMAX_DELAY);host=tableHost;port=tablePort;xSemaphoreGive(lock);
 tableState="loading";mountCount=0;
 client.setTimeout(2000);
 if(!client.connect(host.c_str(),port,3000)){client.stop();tableState="failed";tableWanted=false;return;}
 client.print("GET / HTTP/1.0\r\nHost: "+host+"\r\nUser-Agent: NTRIP TresVizo/0.6\r\nConnection: close\r\n\r\n");
 size_t len=0;const uint32_t start=millis();
 while(millis()-start<8000 && (client.connected()||client.available())){
  const int b=client.read();
  if(b<0){vTaskDelay(1);continue;}
  if(b=='\n'){
   tableLine[len]=0;
   if(!strncmp(tableLine,"STR;",4))parseStr(tableLine);
   len=0;
   if(!strncmp(tableLine,"ENDSOURCETABLE",14))break;
   continue;
  }
  if(b=='\r')continue;
  if(len<sizeof(tableLine)-1)tableLine[len++]=char(b);
 }
 client.stop();
 tableState=mountCount?"ready":"empty";
 tableWanted=false;
}
void worker(void*) {
 WiFiClient client;gnss::Rtcm3Parser parser;unsigned backoff=1000;
 for(;;){
  // La sourcetable solo se pide cuando no hay flujo: comparten socket y radio.
  if(tableWanted && !wanted){fetchSourcetable(client);continue;}
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
void begin(){
 lock=xSemaphoreCreateMutex();
 if(lock)ready=xTaskCreate(worker,"ntrip_rx",6144,nullptr,1,nullptr)==pdPASS;
 storeReady=store.begin("ntrip",false);
 loadProfiles();
 // Autoconexión al encender. No se exige confirmar modo rover como en el
 // arranque manual: ese control es una guía para quien configura a mano, y
 // pedirlo aquí obligaría a tocar el panel tras cada corte de corriente, que
 // es justo lo que esta función existe para evitar.
 if(ready && autoConnect && lastUsed>=0){
  applyProfile(profiles[lastUsed]);
  correction_router::select("ntrip");
  ++generation;wanted=true;state="starting";
 }
}
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

int profileRequest(const String& method,JsonVariantConst body,JsonDocument& out){
 if(method=="GET"){profilesJson(out.to<JsonObject>());return 200;}
 if(method!="POST"||!body.is<JsonObjectConst>())return 400;
 if(!storeReady){out["message"]="No se pudo abrir el almacenamiento de perfiles.";return 503;}
 const String action=body["action"]|"";
 if(action=="save"){
  if(!valid(body["name"],24)||!valid(body["host"],128)||!valid(body["mountpoint"],96)||
     !valid(body["username"],64,true)||!valid(body["password"],128,true)||
     !body["port"].is<unsigned>()||body["port"].as<unsigned>()<1||body["port"].as<unsigned>()>65535)return 400;
  const String host=body["host"].as<const char*>(),mount=body["mountpoint"].as<const char*>();
  for(char c:host)if(!isalnum(static_cast<unsigned char>(c))&&c!='.'&&c!='-')return 400;
  for(char c:mount)if(!isalnum(static_cast<unsigned char>(c))&&c!='_'&&c!='-'&&c!='.')return 400;
  if(String(body["username"].as<const char*>()).indexOf(':')>=0)return 400;
  const String name=body["name"].as<const char*>();
  const int index=findProfile(name);
  if(index<0&&profileCount==kMaxProfiles){out["message"]="Ya hay cinco perfiles guardados. Borra uno antes de añadir otro.";return 409;}
  const size_t slot=index>=0?size_t(index):profileCount;
  const Profile previous=profiles[slot];const size_t previousCount=profileCount;
  profiles[slot].name=name;profiles[slot].host=host;profiles[slot].mount=mount;
  profiles[slot].user=body["username"].as<const char*>();
  profiles[slot].port=uint16_t(body["port"].as<unsigned>());
  // Contraseña vacía sobre un perfil existente conserva la guardada.
  const String pass=body["password"].as<const char*>();
  if(pass.length()||index<0)profiles[slot].password=pass;
  if(index<0)++profileCount;
  if(!persistProfiles()){profiles[slot]=previous;profileCount=previousCount;out["message"]="No se pudo guardar el perfil. La lista activa se conserva.";return 503;}
  profilesJson(out.to<JsonObject>());out["saved"]=true;return 200;
 }
 if(action=="delete"){
  if(!valid(body["name"],24))return 400;
  const int index=findProfile(body["name"].as<const char*>());
  if(index<0){out["message"]="Ese perfil no está guardado.";return 404;}
  for(size_t i=size_t(index);i+1<profileCount;++i)profiles[i]=profiles[i+1];
  profiles[--profileCount]=Profile();
  if(lastUsed==index){lastUsed=-1;autoConnect=false;}
  else if(lastUsed>index)--lastUsed;
  if(!persistProfiles()){out["message"]="No se pudo guardar el cambio.";return 503;}
  profilesJson(out.to<JsonObject>());out["saved"]=true;return 200;
 }
 if(action=="select"){
  // Elegir "ninguno" es una decisión que se persiste: al arrancar no debe
  // conectarse solo a un caster que el usuario descartó a propósito.
  if(body["name"].isNull()||String(body["name"]|"").isEmpty()){
   lastUsed=-1;autoConnect=false;
   if(!persistProfiles()){out["message"]="No se pudo guardar el cambio.";return 503;}
   profilesJson(out.to<JsonObject>());out["saved"]=true;return 200;
  }
  if(!valid(body["name"],24))return 400;
  const int index=findProfile(body["name"].as<const char*>());
  if(index<0){out["message"]="Ese perfil no está guardado.";return 404;}
  lastUsed=index;autoConnect=true;
  if(!persistProfiles()){out["message"]="No se pudo guardar el cambio.";return 503;}
  profilesJson(out.to<JsonObject>());out["saved"]=true;return 200;
 }
 if(action=="connect"){
  if(!valid(body["name"],24))return 400;
  const int index=findProfile(body["name"].as<const char*>());
  if(index<0){out["message"]="Ese perfil no está guardado.";return 404;}
  if(!ready)return 503;
  if(!instrument::stationConfigured()){out["message"]="No hay red Wi-Fi configurada. Añade tu hotspot de 2.4 GHz en Configuración antes de conectar NTRIP.";return 409;}
  if(active()||strcmp(state.load(),"stopped")!=0){out["message"]="Hay una conexión NTRIP activa. Pulsa «Detener» antes de cambiar de perfil.";return 409;}
  lastUsed=index;autoConnect=true;persistProfiles();
  applyProfile(profiles[index]);
  correction_router::select("ntrip");++generation;wanted=true;state="starting";
  status(out.to<JsonObject>());return 202;
 }
 return 400;
}

int sourcetableRequest(const String& method,JsonVariantConst body,JsonDocument& out){
 if(method=="POST"){
  if(!body.is<JsonObjectConst>()||!valid(body["host"],128)||
     !body["port"].is<unsigned>()||body["port"].as<unsigned>()<1||body["port"].as<unsigned>()>65535)return 400;
  const String host=body["host"].as<const char*>();
  for(char c:host)if(!isalnum(static_cast<unsigned char>(c))&&c!='.'&&c!='-')return 400;
  if(!ready)return 503;
  if(!instrument::stationConfigured()){out["message"]="No hay red Wi-Fi configurada. El equipo no puede consultar el caster.";return 409;}
  if(wanted){out["message"]="Detén la conexión NTRIP antes de pedir la lista de puntos de montaje: comparten la misma radio.";return 409;}
  xSemaphoreTake(lock,portMAX_DELAY);tableHost=host;tablePort=uint16_t(body["port"].as<unsigned>());xSemaphoreGive(lock);
  mountCount=0;tableState="loading";tableWanted=true;
 }
 out["state"]=tableState.load();
 out["host"]=tableHost;
 JsonArray list=out["mountpoints"].to<JsonArray>();
 for(size_t i=0;i<mountCount;++i){
  JsonObject o=list.add<JsonObject>();
  o["mountpoint"]=mounts[i].name;o["format"]=mounts[i].format;o["country"]=mounts[i].country;
  // Este firmware no envía GGA: un punto que la exige puede no llegar a fijar.
  o["requires_gga"]=mounts[i].needsGga;
 }
 out["truncated"]=mountCount==kMaxMounts;
 return method=="POST"?202:200;
}
}
