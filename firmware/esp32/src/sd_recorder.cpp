#include "sd_recorder.h"
#include "gnss_control.h"
#include <Arduino.h>
#include "board_profile.h"
#include <SD_MMC.h>
#include <freertos/stream_buffer.h>
#include <mbedtls/base64.h>
#include <atomic>
#define SD_CONFIGURED  // Socket SDIO integrado en la Thing Plus.
namespace sd_recorder {
namespace {
std::atomic<bool> shutdownRequested{false};
std::atomic<bool> recording{false},closing{false};std::atomic<unsigned> inFlight{0};std::atomic<uint32_t> dropped{0};
SemaphoreHandle_t mutex=nullptr;StreamBufferHandle_t queue=nullptr;
const char* phase="not_configured";String id;uint32_t written=0;std::atomic<bool> available{false};
#ifdef SD_CONFIGURED
fs::SDMMCFS& card = SD_MMC;
File file;uint32_t flushed=0;bool stopRequested=false;
void manifest(const char* state){
 File metadata=card.open(("/sessions/"+id+"/manifest.json").c_str(),FILE_WRITE);
 if(!metadata)return;
 JsonDocument doc;doc["id"]=id;doc["state"]=state;doc["bytes"]=written;doc["dropped_bytes"]=dropped.load();doc["rinex_available"]=false;doc["ppk_accuracy_validated"]=false;doc["source"]="esp32_uart";doc["antenna_metadata_confirmed"]=false;
 serializeJson(doc,metadata);metadata.flush();metadata.close();
}
void worker(void*){
 uint8_t buffer[1024];
 for(;;){
  size_t n=xStreamBufferReceive(queue,buffer,sizeof(buffer),pdMS_TO_TICKS(20));
  xSemaphoreTake(mutex,portMAX_DELAY);
  if(digitalRead(board_profile::kSdDetect)!=HIGH){
   available=false;
   if(file){
    // No renombrar como completa una sesión cuya tarjeta se retiró. Drenar
    // la cola permite terminar el cierre incluso si el GNSS dejó de emitir.
    recording=false;stopRequested=true;closing=true;phase="partial";
    dropped+=n;n=0;
   }
  }
  if(file && n){
   size_t count=file.write(buffer,n);written+=count;
   if(count!=n || written>=64*1024*1024){dropped+=n-count;recording=false;stopRequested=true;closing=true;phase="partial";}
  }
  if(file && millis()-flushed>2000){file.flush();flushed=millis();}
  if(file && stopRequested && !inFlight && !xStreamBufferBytesAvailable(queue)){
   file.flush();file.close();bool complete=!dropped && strcmp(phase,"partial")!=0;
   if(complete)complete=card.rename(("/sessions/"+id+"/stream.part").c_str(),("/sessions/"+id+"/stream.bin").c_str());
   phase=complete?"closed":"partial";manifest(phase);stopRequested=false;closing=false;
  }
  xSemaphoreGive(mutex);
 }
}
#endif
}
bool active(){return recording||closing;}
const char* displayState(){
 if(!mutex)return "not_configured";
 if(digitalRead(board_profile::kSdDetect)!=HIGH)return "card_missing";
 if(closing)return "closing";
 if(recording)return "recording";
 if(xSemaphoreTake(mutex,0)!=pdTRUE)return "busy";
 const char* result=phase; // phase siempre apunta a literales, nunca al archivo.
 xSemaphoreGive(mutex);return result;
}
bool prepareShutdown(){
 shutdownRequested=true;
 if(!mutex)return true;
 if(xSemaphoreTake(mutex,0)!=pdTRUE)return false;
 if(file){recording=false;closing=true;stopRequested=true;if(strcmp(phase,"partial")!=0)phase="closing";}
 const bool ready=!file && !active() && !inFlight;
 xSemaphoreGive(mutex);return ready;
}
void begin(){
 mutex=xSemaphoreCreateMutex();if(!mutex)return;
#ifdef SD_CONFIGURED
 pinMode(board_profile::kSdDetect, INPUT_PULLDOWN);
 if(digitalRead(board_profile::kSdDetect)!=HIGH){phase="card_missing";return;}
 if(!card.setPins(board_profile::kSdClock,board_profile::kSdCommand,board_profile::kSdD0,
                  board_profile::kSdD1,board_profile::kSdD2,board_profile::kSdD3)){
  phase="pin_setup_failed";return;
 }
 // Cuatro bits, 20 MHz y sin formateo automático: una tarjeta que no monta no
 // autoriza a borrar los datos del operador.
 if(!card.begin("/sdcard",false,false,SDMMC_FREQ_DEFAULT)){phase="card_unavailable";return;}
 if(!card.exists("/sessions")&&!card.mkdir("/sessions")){phase="directory_failed";return;}
 queue=xStreamBufferCreate(32768,1);
 if(!queue){phase="allocation_failed";return;}
 available=true;phase="idle";
 if(xTaskCreate(worker,"sd_writer",4096,nullptr,1,nullptr)!=pdPASS){
  available=false;phase="allocation_failed";vStreamBufferDelete(queue);queue=nullptr;return;
 }
#endif
}
void feed(const uint8_t* data,size_t length){
 if(!recording||!length)return;
 ++inFlight;
 // Segunda comprobacion tras marcar inFlight: el cierre espera a que no haya
 // productores en vuelo antes de cerrar el archivo.
 if(recording && queue){
  const size_t stored=xStreamBufferSend(queue,data,length,0);
  if(stored!=length)dropped+=length-stored;
 }
 --inFlight;
}
void status(JsonObject out){
 if(!mutex){out["state"]="start_failed";return;}
 xSemaphoreTake(mutex,portMAX_DELAY);
 const bool present=digitalRead(board_profile::kSdDetect)==HIGH;
 out["state"]=phase;out["available"]=available && present;out["card_present"]=present;
 out["shutdown_pending"]=shutdownRequested.load();
 out["interface"]="sdmmc_4bit";out["active"]=recording.load();out["closing"]=closing.load();
 out["session_id"]=id;out["bytes"]=written;out["dropped_bytes"]=dropped.load();
 out["storage"]="microsd"; // Identificador técnico conservado para clientes existentes.
 out["storage_label"]="Memoria interna del dispositivo";
 out["max_session_bytes"]=64*1024*1024;out["rinex_available"]=false;
 xSemaphoreGive(mutex);
}
int request(const String& method,const String& path,JsonVariantConst body,JsonDocument& out){
 if(method=="GET" && path=="/api/recording"){status(out.to<JsonObject>());return 200;}
 if(!mutex){out["message"]="No se pudo iniciar la memoria interna del dispositivo.";return 503;}
 if(path!="/api/recording/stop" && (!available || digitalRead(board_profile::kSdDetect)!=HIGH)){out["message"]="Memoria interna del dispositivo no disponible. Revisa el almacenamiento y reinicia el equipo; no se borra ni formatea automáticamente.";return 503;}
#ifdef SD_CONFIGURED
 xSemaphoreTake(mutex,portMAX_DELAY);int code=400;
 if(method=="GET" && path=="/api/recording/sessions") {
  auto rows=out["sessions"].to<JsonArray>();File directory=card.open("/sessions");
  for(unsigned i=0;directory&&i<32;++i){File folder=directory.openNextFile();if(!folder)break;
   if(folder.isDirectory()){
    String identity=folder.name();identity=identity.substring(identity.lastIndexOf('/')+1);
    String root="/sessions/"+identity;bool complete=card.exists((root+"/stream.bin").c_str());
    File stream=card.open((root+(complete?"/stream.bin":"/stream.part")).c_str());
    if(stream){auto row=rows.add<JsonObject>();row["session_id"]=identity;row["bytes"]=stream.size();row["state"]=(identity==id && file)?phase:(complete?"closed":"interrupted");stream.close();}
   }folder.close();
  }directory.close();code=200;
 }
 if(method=="POST" && path=="/api/recording/start"){
  if(shutdownRequested||recording||file||gnss_control::busy()){code=409;out["message"]="Espera a que termine la operación del GPS o el cierre de la grabación antes de iniciar otra sesión.";}
  else if(card.totalBytes()-card.usedBytes()<8*1024*1024){code=409;out["message"]="Espacio insuficiente.";}
  else {
   char name[25];snprintf(name,sizeof(name),"%08lx%08lx%08lx",(unsigned long)esp_random(),(unsigned long)esp_random(),(unsigned long)esp_random());id=name;
   String folder="/sessions/"+id;
   if(card.exists(folder.c_str())||!card.mkdir(folder.c_str())){code=503;out["message"]="No se pudo crear la sesión en la memoria interna del dispositivo.";}
   else {
    file=card.open((folder+"/stream.part").c_str(),FILE_WRITE);
    if(!file){code=503;out["message"]="No se pudo abrir el archivo de grabación en la memoria interna del dispositivo.";}
    else {written=0;dropped=0;stopRequested=false;xStreamBufferReset(queue);phase="recording";manifest("recording");recording=true;out["session_id"]=id;code=202;}
   }
  }
 }
 if(method=="POST" && path=="/api/recording/stop"){
  if(!file){code=409;out["message"]="No hay una grabación abierta para cerrar.";}
  else {
   recording=false;stopRequested=true;closing=true;
   // Repetir stop no debe convertir un cierre fallido en uno completo.
   if(strcmp(phase,"partial")!=0)phase="closing";
   code=202;
  }
 }
 if(method=="POST" && path=="/api/recording/read"){
  String session=body["session_id"]|"";bool valid=session.length()==24 && body["session_id"].as<JsonString>().size()==24 && body["offset"].is<uint32_t>();
  // isxdigit() con char con signo es comportamiento indefinido para bytes >0x7F.
  for(char c:session)if(!isxdigit(static_cast<unsigned char>(c)))valid=false;
  if(valid && !file){
   String file_path="/sessions/"+session+"/stream.bin";
   if(!card.exists(file_path.c_str()))file_path="/sessions/"+session+"/stream.part";
   File input=card.open(file_path.c_str(),FILE_READ);
   if(input){uint32_t offset=body["offset"];if(offset<=input.size()&&input.seek(offset)){
    uint8_t block[384],encoded[513];size_t n=input.read(block,sizeof(block)),encodedSize=0;mbedtls_base64_encode(encoded,sizeof(encoded),&encodedSize,block,n);
    out["offset"]=offset;out["size"]=input.size();out["data"]=String(reinterpret_cast<char*>(encoded),encodedSize);out["next_offset"]=offset+n;code=200;
   }input.close();}else code=404;
  }else code=409;
 }
 xSemaphoreGive(mutex);return code;
#else
 (void)body;return 503;
#endif
}
}
