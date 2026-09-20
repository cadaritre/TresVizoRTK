#include "sd_recorder.h"
#include "gnss_control.h"
#include <Arduino.h>
#include <SD.h>
#include <SPI.h>
#include <freertos/stream_buffer.h>
#include <mbedtls/base64.h>
#include <atomic>
#if defined(TRESVIZO_SD_CS) && defined(TRESVIZO_SD_SCK) && defined(TRESVIZO_SD_MISO) && defined(TRESVIZO_SD_MOSI)
#define SD_CONFIGURED
#endif
namespace sd_recorder {
namespace {
std::atomic<bool> recording{false},closing{false};std::atomic<unsigned> inFlight{0};std::atomic<uint32_t> dropped{0};
SemaphoreHandle_t mutex=nullptr;StreamBufferHandle_t queue=nullptr;
const char* phase="not_configured";String id;uint32_t written=0;bool available=false;
#ifdef SD_CONFIGURED
SPIClass spi(FSPI);File file;uint32_t flushed=0;bool stopRequested=false;
void manifest(const char* state){
 File metadata=SD.open(("/sessions/"+id+"/manifest.json").c_str(),FILE_WRITE);
 if(!metadata)return;
 JsonDocument doc;doc["id"]=id;doc["state"]=state;doc["bytes"]=written;doc["dropped_bytes"]=dropped.load();doc["rinex_available"]=false;doc["ppk_accuracy_validated"]=false;doc["source"]="esp32_uart";doc["antenna_metadata_confirmed"]=false;
 serializeJson(doc,metadata);metadata.flush();metadata.close();
}
void worker(void*){
 uint8_t buffer[1024];
 for(;;){
  size_t n=xStreamBufferReceive(queue,buffer,sizeof(buffer),pdMS_TO_TICKS(20));
  xSemaphoreTake(mutex,portMAX_DELAY);
  if(file && n){
   size_t count=file.write(buffer,n);written+=count;
   if(count!=n || written>=64*1024*1024){dropped+=n-count;recording=false;stopRequested=true;closing=true;phase="partial";}
  }
  if(file && millis()-flushed>2000){file.flush();flushed=millis();}
  if(file && stopRequested && !inFlight && !xStreamBufferBytesAvailable(queue)){
   file.flush();file.close();bool complete=!dropped && strcmp(phase,"partial")!=0;
   if(complete)complete=SD.rename(("/sessions/"+id+"/stream.part").c_str(),("/sessions/"+id+"/stream.bin").c_str());
   phase=complete?"closed":"partial";manifest(phase);stopRequested=false;closing=false;
  }
  xSemaphoreGive(mutex);
 }
}
#endif
}
bool active(){return recording||closing;}
void begin(){
 mutex=xSemaphoreCreateMutex();if(!mutex)return;
#ifdef SD_CONFIGURED
 spi.begin(TRESVIZO_SD_SCK,TRESVIZO_SD_MISO,TRESVIZO_SD_MOSI,TRESVIZO_SD_CS);
 if(!SD.begin(TRESVIZO_SD_CS,spi,4000000)){phase="card_unavailable";return;}
 if(!SD.exists("/sessions")&&!SD.mkdir("/sessions")){phase="directory_failed";return;}
 queue=xStreamBufferCreate(32768,1);
 if(!queue || xTaskCreate(worker,"sd_writer",4096,nullptr,1,nullptr)!=pdPASS){phase="allocation_failed";return;}
 available=true;phase="idle";
#endif
}
void feed(uint8_t byte){if(!recording)return;++inFlight;if(recording && queue && xStreamBufferSend(queue,&byte,1,0)!=1)++dropped;--inFlight;}
void status(JsonObject out){
 if(!mutex){out["state"]="start_failed";return;}
 xSemaphoreTake(mutex,portMAX_DELAY);out["state"]=phase;out["available"]=available;out["active"]=recording.load();out["session_id"]=id;out["bytes"]=written;out["dropped_bytes"]=dropped.load();out["storage"]="microsd";out["max_session_bytes"]=64*1024*1024;out["rinex_available"]=false;xSemaphoreGive(mutex);
}
int request(const String& method,const String& path,JsonVariantConst body,JsonDocument& out){
 if(method=="GET" && path=="/api/recording"){status(out.to<JsonObject>());return 200;}
 if(!available){out["message"]="microSD sin conectar/configurar; no se activan pines supuestos.";return 503;}
#ifdef SD_CONFIGURED
 xSemaphoreTake(mutex,portMAX_DELAY);int code=400;
 if(method=="GET" && path=="/api/recording/sessions") {
  auto rows=out["sessions"].to<JsonArray>();File directory=SD.open("/sessions");
  for(unsigned i=0;directory&&i<32;++i){File folder=directory.openNextFile();if(!folder)break;
   if(folder.isDirectory()){
    String identity=folder.name();identity=identity.substring(identity.lastIndexOf('/')+1);
    String root="/sessions/"+identity;bool complete=SD.exists((root+"/stream.bin").c_str());
    File stream=SD.open((root+(complete?"/stream.bin":"/stream.part")).c_str());
    if(stream){auto row=rows.add<JsonObject>();row["session_id"]=identity;row["bytes"]=stream.size();row["state"]=(identity==id && file)?phase:(complete?"closed":"interrupted");stream.close();}
   }folder.close();
  }directory.close();code=200;
 }
 if(method=="POST" && path=="/api/recording/start"){
  if(recording||file||gnss_control::busy())code=409;
  else if(SD.totalBytes()-SD.usedBytes()<8*1024*1024){code=409;out["message"]="Espacio insuficiente.";}
  else {
   char name[25];snprintf(name,sizeof(name),"%08lx%08lx%08lx",(unsigned long)esp_random(),(unsigned long)esp_random(),(unsigned long)esp_random());id=name;
   String folder="/sessions/"+id;
   if(SD.exists(folder.c_str())||!SD.mkdir(folder.c_str()))code=503;
   else {
    file=SD.open((folder+"/stream.part").c_str(),FILE_WRITE);
    if(!file)code=503;
    else {written=0;dropped=0;stopRequested=false;xStreamBufferReset(queue);phase="recording";manifest("recording");recording=true;out["session_id"]=id;code=202;}
   }
  }
 }
 if(method=="POST" && path=="/api/recording/stop"){
  if(!file)code=409;else {recording=false;stopRequested=true;closing=true;phase="closing";code=202;}
 }
 if(method=="POST" && path=="/api/recording/read"){
  String session=body["session_id"]|"";bool valid=session.length()==24 && body["session_id"].as<JsonString>().size()==24 && body["offset"].is<uint32_t>();
  for(char c:session)if(!isxdigit(c))valid=false;
  if(valid && !file){
   String path="/sessions/"+session+"/stream.bin";
   if(!SD.exists(path.c_str()))path="/sessions/"+session+"/stream.part";
   File input=SD.open(path.c_str(),FILE_READ);
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
