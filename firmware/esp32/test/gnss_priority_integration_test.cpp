#include "../src/gnss_control.cpp"
#include "../src/base_survey.cpp"
namespace {gnss_receiver::Snapshot receiver;bool recording=false;}
namespace gnss_receiver {Snapshot snapshot(){return receiver;}}
namespace sd_recorder {bool active(){return recording;}}
namespace firmware_update {bool busy(){return false;}}
namespace correction_router {bool select(const char*){return true;}}
namespace ntrip_input {void releaseForBase(){}}
JsonDocument requestBody(const char* json){JsonDocument d;assert(!deserializeJson(d,json));return d;}
void feedLine(const std::string& s){uint8_t crc=0;for(char c:s)crc^=uint8_t(c);char tail[8];std::snprintf(tail,sizeof tail,"*%02X\r\n",crc);const std::string wire=s+tail;gnss_control::feed(wire.c_str(),wire.size());}
JsonDocument status(){JsonDocument d;gnss_control::status(d.to<JsonObject>());return d;}
int start(const char* json,JsonDocument& out){return gnss_control::start(requestBody(json).as<JsonVariantConst>(),out);}
int main(){
    receiver.enabled=true;gnss_control::begin();HardwareSerial uart;JsonDocument out;
    hostMillis=5001;gnss_control::tick(uart);
    assert(uart.sent.back()=="VERSIONA\r\n"); // inicialización en vuelo
    const uint32_t bootJob=status()["job_id"];
    assert(start("{\"action\":\"mask\",\"elevation_deg\":15}",out)==202);
    assert(out["job_id"].as<uint32_t>()>bootJob);
    assert(out["waiting_command_reply"]==true);
    // Un tercer cambio sustituye el segundo, conserva el ACK que falta del primero.
    assert(start("{\"action\":\"mask\",\"elevation_deg\":25}",out)==202);
    const uint32_t latest=out["job_id"];
    assert(start("{\"action\":\"mask\",\"elevation_deg\":91}",out)==400);
    assert(status()["job_id"]==latest);
    feedLine("$command,VERSIONA,response: OK");
    feedLine("#VERSIONA,header;UM980");
    gnss_control::tick(uart);
    assert(uart.sent.size()==2 && uart.sent.back()=="MASK 25.00\r\n");
    feedLine("$command,MASK 15.00,response: OK"); // vieja: no confirma la nueva
    gnss_control::tick(uart);assert(uart.sent.size()==2);
    feedLine("$command,MASK 25.00,response: OK");gnss_control::tick(uart);gnss_control::tick(uart);
    assert(uart.sent.back()=="SAVECONFIG\r\n");
    feedLine("$command,SAVECONFIG,response: OK");gnss_control::tick(uart);
    assert(status()["state"]=="confirmed");
    assert(status()["saved"]==true);
    hostMillis+=30000;gnss_control::tick(uart);assert(uart.sent.size()==3); // no resucita boot
    // Una entrada inválida no cancela el trabajo ni toca su perfil.
    assert(start("{\"action\":\"rover\",\"extra\":true}",out)==400);
    assert(status()["job_id"]==latest);
    // Cancelar solo el trabajo dueño de un promedio, no una orden posterior.
    assert(start("{\"action\":\"query\"}",out)==202);const uint32_t query=out["job_id"];
    gnss_control::cancel(latest);assert(gnss_control::busy());
    gnss_control::cancel(query);assert(!gnss_control::busy());
    // Sin respuesta del comando en vuelo: la secuencia nueva no se transmite.
    assert(start("{\"action\":\"query\"}",out)==202);gnss_control::tick(uart);
    const auto written=uart.sent.size();
    assert(start("{\"action\":\"rover\"}",out)==202);
    hostMillis+=4001;gnss_control::tick(uart);
    assert(status()["state"]=="partial_or_unknown" && uart.sent.size()==written);
    // Cancelar un promedio que ya encoló base quita sus comandos sin emitirlos.
    base_survey::state="applying";
    JsonDocument plan=requestBody("{\"method\":\"known\",\"station_id\":1,\"latitude_deg\":1,\"longitude_deg\":2,\"arp_ellipsoid_height_m\":3}");
    assert(gnss_control::applyBase(plan.as<JsonVariantConst>(),out)==202);
    base_survey::applyingJob=out["job_id"];
    assert(base_survey::request("POST",requestBody("{\"action\":\"cancel\"}").as<JsonVariantConst>(),out)==200);
    assert(!gnss_control::busy());gnss_control::tick(uart);assert(uart.sent.size()==written);
    // Repetir promedio acepta el nuevo; rechazo por calidad conserva el anterior.
    receiver.solution.quality=4;
    const char* avg="{\"action\":\"start\",\"seconds\":2,\"station_id\":1,\"antenna_vertical_m\":0,\"quality\":\"rtk_fixed\"}";
    assert(base_survey::request("POST",requestBody(avg).as<JsonVariantConst>(),out)==202);
    hostMillis+=1;
    assert(base_survey::request("POST",requestBody(avg).as<JsonVariantConst>(),out)==202);
    assert(base_survey::samples==0 && base_survey::startedAt==hostMillis);
    receiver.solution.quality=1;
    assert(base_survey::request("POST",requestBody(avg).as<JsonVariantConst>(),out)==409);
    assert(base_survey::active());
    std::puts("gnss_priority_integration: OK");
}
