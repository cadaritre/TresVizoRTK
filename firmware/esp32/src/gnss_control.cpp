#include "sd_recorder.h"
#include "receiver_baseline.h"
#include "gnss_control.h"
#include "gnss_receiver.h"
#include "correction_router.h"
#include <atomic>
namespace gnss_control {
namespace {
constexpr unsigned kMaxCommands = 20;
// Presupuesto total del trabajo. El limite por comando solo corre una vez
// enviado; sin este, un puerto que nunca acepte escritura dejaba el trabajo
// en "running" para siempre y bloqueaba NTRIP, grabacion y cambio de clave.
constexpr uint32_t kJobBudgetMs = 20000;
constexpr uint32_t kCommandTimeoutMs = 4000;

SemaphoreHandle_t mutex;
String commands[kMaxCommands], mode, version, action, failure;
String expectedMode;
String maskReadback;
unsigned count=0, index=0;
bool sent=false, ack=false, readback=false, overflowed=false;
uint32_t started=0, launched=0, job=0;
std::atomic<uint32_t> modeAt{0};
std::atomic<bool> running{false}, rover{false}, ellipsoid{false};
bool bootQueried=false;
// Tiempo que se espera a que CONFIG termine de escupir sus lineas.
constexpr uint32_t kConfigSettleMs = 700;
const char* phase="idle";
char line[1024]; size_t length=0;

// Configuracion avanzada conocida. Solo se actualiza cuando el receptor
// confirma el comando; no se muestra como estado leido si no se leyo.
struct Profile {
    double elevation_deg = 5.0;      // valor por defecto del receptor segun manual N4
    bool elevation_known = false;
    bool gps = true, bds = true, glo = true, gal = true, qzss = true;
    bool constellations_known = false;
    String outputs;                  // resumen de salidas NMEA aplicadas
    String rtcm;                     // resumen del perfil RTCM aplicado
    int dgps_timeout_s = -1;         // -1 = desconocido
    bool saved = false;              // SAVECONFIG confirmado en esta sesion
    // Tasa de GGA de la ultima `telemetry` u `outputs` confirmada. La usa
    // `rover` para reponer las salidas que su UNLOG quita. 0 = ninguna en esta
    // sesion del ESP32: `addPositionOutputs` usa entonces el tope del producto
    // (kDefaultGgaRateHz).
    unsigned gga_rate_hz = 0;
} profileState;

// Reconciliación: qué se leyó del receptor, qué difería y qué se corrigió.
//
// Se guarda el informe completo, no solo el resultado, porque «se arregló» sin
// decir qué estaba mal no permite distinguir un equipo recién montado de uno que
// alguien reconfiguró por su cuenta. Lo primero es normal; lo segundo hay que
// saberlo.
struct Reconciliation {
    bool ran = false;
    bool reading = false;            // fase de lectura en curso
    // La del arranque no toca las preferencias del usuario. Ver
    // `applyReconciliation`: forzar la mascara al arrancar le borraria al
    // operador la que acaba de poner, y sin decirselo.
    bool atBoot = false;
    uint32_t readStartedAt = 0;
    String readback;                 // líneas $CONFIG,... tal como llegaron
    String differences;              // clave: leído -> esperado, separadas por " | "
    unsigned checked = 0, fixed = 0;
    String summary;
} reconciliation;

/// El valor que el receptor tiene para una clave, según lo leído. Vacío si esa
/// clave no apareció, que para un receptor de fábrica es lo normal y **no es lo
/// mismo que tener un valor distinto**: una clave ausente puede significar que
/// el receptor usa su valor por defecto, y ese defecto puede ser el correcto o no.
String readValueFor(const String& key) {
    const String marca = "$CONFIG," + key + ",";
    int desde = 0;
    while(true) {
        const int i = reconciliation.readback.indexOf(marca, desde);
        if(i < 0) return "";
        const int fin = reconciliation.readback.indexOf('\n', i);
        String linea = fin < 0 ? reconciliation.readback.substring(i)
                               : reconciliation.readback.substring(i, fin);
        linea.trim();
        return linea.substring(marca.length());
    }
}

void finish(const char* state, const char* error="") { phase=state;failure=error;running=false; }
bool add(const String& c) { if(count>=kMaxCommands){overflowed=true;return false;} commands[count++]=c; return true; }
bool needsReply() {
    const String& c = commands[index];
    return c=="MODE" || c=="VERSIONA" || c=="MASK" || c=="CONFIG";
}

// Tasas admitidas por el UM980 segun manual N4: 1/2/5/10/20 Hz -> 1/0.5/0.2/0.1/0.05.
// No se usa 1.0/hz con un decimal porque 20 Hz necesita dos.
const char* rateFor(unsigned hz) {
    switch (hz) {
        case 1: return "1";
        case 2: return "0.5";
        case 5: return "0.2";
        case 10: return "0.1";
        case 20: return "0.05";
        default: return nullptr;
    }
}
// **Nada por encima de 5 Hz** hacia el ESP32, aunque el UM980 admita 10 y 20.
// Es el mismo tope que la telemetria hacia el telefono
// (`protocol::kMaxSolutionRateHz`): a 10 Hz el Bluetooth se quedaba en unos 8,
// y el propietario fijo 5 Hz para todo el camino (27-09-2026).
constexpr unsigned kMaxOutputRateHz = 5;
constexpr const char* kRateCapMessage = "La frecuencia maxima es 5 Hz: el enlace con el telefono no sostiene mas.";
bool validRate(unsigned hz) { return rateFor(hz) != nullptr && hz <= kMaxOutputRateHz; }
// Tasa de GGA cuando esta sesion del ESP32 aun no ha aplicado ninguna: el tope
// del producto, que es tambien la que ponen las apps.
constexpr unsigned kDefaultGgaRateHz = kMaxOutputRateHz;
// Tasa de GGA pedida por el trabajo en curso; se apunta al confirmarse.
unsigned pendingGgaHz = 0;

// Salidas de posicion hacia el ESP32: GGA a la tasa pedida y GST, GSV y GSA a
// 1 Hz. Las usan `telemetry` y `rover` (que las repone tras su UNLOG).
//
// GST acompaña siempre a GGA: sin ella el panel no puede decir con qué
// precisión estima el receptor. Va a 1 Hz aunque la posición vaya más
// rápido; la desviación no cambia a 5 Hz y cargar la UART no ayuda.
// GSV y GSA acompanan a GGA por el mismo motivo que GST: sin ellas la
// pantalla de satelites no puede decir nada del cielo, y "diez
// satelites" sin saber cuantos hay a la vista no distingue una antena
// mala de un cielo tapado. Van a 1 Hz aunque la posicion vaya mas rapido:
// el cielo no cambia en doscientos milisegundos. Con GGA a 10 Hz, GST, GSV y
// GSA a 1 Hz la estimacion del enlace rondaba el 20 % de los 115200 baudios;
// desde el tope de 5 Hz es menos.
void addPositionOutputs(unsigned ggaHz) {
    const char* rate = rateFor(ggaHz);
    if(!rate || ggaHz > kMaxOutputRateHz) rate = rateFor(kDefaultGgaRateHz);
    add(String("GPGGA COM2 ")+rate);
    add("GPGST COM2 1");
    add("GPGSV COM2 1");
    add("GPGSA COM2 1");
}

void acceptLine() {
    line[length]=0; char* star=strrchr(line,'*');
    if(!star || (strlen(star+1)!=2 && strlen(star+1)!=8)) return;
    char* end=nullptr; unsigned long expected=strtoul(star+1,&end,16);
    if(*end) return;
    uint32_t sum=0;
    // XOR de control Unicore: incluye el '$' inicial (ver docs/usb-bench.md).
    // El CRC32 de los mensajes '#' se calcula desde el caracter siguiente.
    if(strlen(star+1)==2) {for(char* p=line;p<star;++p) sum^=uint8_t(*p);}
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
    // Respuesta de CONFIG: una linea "$CONFIG,<clave>,<valor>" por ajuste. Se
    // acumulan todas y el asentamiento lo decide el tick, no la primera linea:
    // llegan en rafaga y quedarse con la primera perderia el resto.
    if(commands[index]=="CONFIG" && !strncmp(line,"$CONFIG,",8)) {
        if(reconciliation.readback.length()<3072) {
            reconciliation.readback += line;
            reconciliation.readback += "\n";
        }
    }
    // Respuesta de la consulta MASK: varias lineas "$CONFIG,MASK,<valor>".
    if(commands[index]=="MASK" && !strncmp(line,"$CONFIG,MASK,",13)) {
        const String value=String(line+13);
        if(maskReadback.length()<192){if(maskReadback.length())maskReadback+=" | ";maskReadback+=value;}
        readback=true;
    }
}
int prepare(const String& name, JsonDocument& out) {
    if(!gnss_receiver::snapshot().enabled) {out["message"]="UART no disponible.";return 503;}
    if(sd_recorder::active()){out["message"]="Cierra la grabación antes de configurar el GPS.";return 409;}
    if(running) {out["message"]="Operación GNSS en curso.";return 409;}
    // **Configurar el GPS con las correcciones encendidas esta permitido.**
    //
    // Aqui habia un 409 que lo prohibia, con este motivo: «configurar el GPS con
    // una fuente activa mezclaria comandos con RTCM». Ese motivo era falso, y el
    // comentario de al lado ya lo decia para las consultas: **el entrelazado de
    // bytes esta resuelto en el planificador de escritura de la UART**
    // (`gnss_receiver.cpp`), que solo llama a `tick` cuando no hay trama RTCM a
    // medio enviar, y solo saca una trama nueva de la cola cuando este modulo no
    // esta trabajando. Comandos y RTCM no pueden cruzarse, ni leyendo ni
    // escribiendo.
    //
    // El coste real de permitirlo es otro y es pequeno: mientras el comando
    // viaja, las tramas RTCM esperan en la cola y las que pasen de dos segundos
    // se descartan, asi que la solucion puede degradarse un instante. Eso lo
    // decide el operador, no el firmware. Lo que el firmware hacia era mandarle
    // a apagar las correcciones para cambiar una mascara de elevacion, y volver
    // a encenderlas despues: obligarle a perder el fijo entero para evitar
    // perder dos tramas.
    count=index=0;sent=ack=readback=false;overflowed=false;failure="";expectedMode="";action=name;
    pendingGgaHz=0;
    return 0;
}
int launch(JsonDocument& out) {
    if(overflowed||!count){out["message"]="La operación generó demasiados comandos; no se envió nada.";return 400;}
    phase="running";running=true;++job;launched=millis();
    out["job_id"]=job;out["state"]=phase;out["saved"]=profileState.saved;return 202;
}

// Aplica al perfil conocido lo que el trabajo recien confirmado pidio.
void commitProfile() {
    if(action=="mask"){profileState.elevation_known=true;}
    else if(action=="constellations"){profileState.constellations_known=true;}
    if(pendingGgaHz) profileState.gga_rate_hz=pendingGgaHz;
    // Cualquier acción que modifica configuración termina con SAVECONFIG, así
    // que al confirmarse queda persistida en el receptor.
    if(action=="save"||action=="rover"||action=="base"||action=="telemetry"||action=="stop_outputs"||
       action=="mask"||action=="constellations"||action=="dgps_timeout"||
       action=="outputs"||action=="rtcm_base"){profileState.saved=true;}
}

bool boolField(JsonVariantConst body,const char* name,bool& target){
    if(body[name].isNull())return true;
    if(!body[name].is<bool>())return false;
    target=body[name].as<bool>();return true;
}
}
void begin(){mutex=xSemaphoreCreateMutex();}
bool busy(){return running;}
bool roverReady(){return rover && !running && millis()-modeAt.load()<30000;}
bool isBase(){return mode.startsWith("MODE BASE");}
bool isRover(){return mode=="MODE ROVER SURVEY";}
const char* heightReference(){return ellipsoid?"ellipsoidal_user_configured":"receiver_msl";}
double elevationMaskDeg(){
    if(!mutex||xSemaphoreTake(mutex,pdMS_TO_TICKS(100))!=pdTRUE)return 5.0;
    const double mask=profileState.elevation_deg;
    xSemaphoreGive(mutex);
    return mask;
}

void feed(const char* data, size_t size) {
    if(!mutex || !size || xSemaphoreTake(mutex,portMAX_DELAY)!=pdTRUE)return;
    for(size_t i=0;i<size;++i){
        const char byte=data[i];
        if(byte=='$'||byte=='#')length=0;
        if(byte=='\n') {if(length)acceptLine();length=0;}
        else if(byte!='\r') {if(length<sizeof(line)-1)line[length++]=byte;else length=0;}
    }
    xSemaphoreGive(mutex);
}

/// Compara lo leído con lo que debe haber y encola solo lo que difiera.
///
/// Se llama cuando la fase de lectura termina. Los comandos correctores entran
/// en la **misma** cola, así que el trabajo sigue sin que el cliente tenga que
/// pedir nada más: para quien monta un receptor nuevo es una sola operación.
/// Compara lo leido con la linea base y encola lo que falte.
///
/// `userPreferences` decide si tambien se tocan **la mascara de elevacion y las
/// constelaciones**, que no son invariantes de correccion sino decisiones del
/// operador: las cambia por trabajo desde la app.
///
/// La reconciliacion **automatica del arranque no las toca**. Forzarlas ahi
/// significaria que apagar y encender el equipo le devuelve la mascara a 5
/// grados despues de que el operador la puso en 15, sin avisarle. La
/// reconciliacion **que pide el usuario** si las pone: ahi lo que ha pedido es
/// justo devolver el receptor a la linea base, que es el caso del equipo recien
/// montado.
void applyReconciliation(bool userPreferences) {
    reconciliation.reading = false;
    reconciliation.ran = true;
    reconciliation.checked = 0;
    reconciliation.fixed = 0;
    reconciliation.differences = "";

    auto anotar = [&](const String& clave, const String& leido, const String& esperado) {
        if(reconciliation.differences.length() > 900) return;
        if(reconciliation.differences.length()) reconciliation.differences += " | ";
        reconciliation.differences += clave + ": «" + (leido.length()?leido:String("ausente"))
                                    + "» debe ser «" + esperado + "»";
    };

    for(size_t i = 0; i < receiver_baseline::kExpectedCount; ++i) {
        const auto& e = receiver_baseline::kExpected[i];
        ++reconciliation.checked;
        const String leido = readValueFor(e.key);
        // Una clave ausente cuenta como diferente: no se supone que el valor por
        // defecto del receptor sea el que queremos. Aplicarla no cuesta nada y
        // deja el equipo en un estado conocido.
        if(leido != String(e.expected)) {
            anotar(e.key, leido, e.expected);
            if(add(String(e.command))) ++reconciliation.fixed;
        }
    }

    // La mascara se lee con MASK y no con CONFIG. **Se lee siempre**, aunque no
    // se corrija: asi la app puede ensenar la que el receptor tiene de verdad
    // en vez de suponer la de fabrica.
    String mascara = maskReadback;
    mascara.trim();
    if(mascara.startsWith("MASK ")) {
        profileState.elevation_deg = mascara.substring(5).toDouble();
        profileState.elevation_known = true;
    }

    if(userPreferences) {
        ++reconciliation.checked;
        const String esperadaMascara = "MASK " + String(receiver_baseline::kElevationMaskDegrees, 1);
        if(!mascara.startsWith(esperadaMascara.substring(0, esperadaMascara.length()-2))) {
            anotar("MASK", mascara, receiver_baseline::kElevationMaskCommand);
            if(add(String(receiver_baseline::kElevationMaskCommand))) ++reconciliation.fixed;
        }

        // Las constelaciones no salen en CONFIG, asi que no se pueden comparar:
        // se habilitan siempre. Es el unico punto donde se escribe sin haber
        // leido, y se dice en el informe en vez de dejarlo como si se hubiera
        // comprobado.
        for(size_t i = 0; i < receiver_baseline::kConstellationCount; ++i) {
            add(String("UNMASK ") + receiver_baseline::kConstellations[i]);
        }
        profileState.gps=profileState.bds=profileState.glo=profileState.gal=profileState.qzss=true;
        profileState.constellations_known = true;
        profileState.elevation_deg = receiver_baseline::kElevationMaskDegrees;
        profileState.elevation_known = true;
    }

    const String cola = userPreferences
        ? String(" Las constelaciones se habilitaron sin poder comprobarlas antes: "
                 "CONFIG no las devuelve.")
        : String(" La mascara de elevacion y las constelaciones no se tocaron: "
                 "son del operador, no de la linea base.");
    if(reconciliation.fixed == 0) {
        reconciliation.summary = (reconciliation.atBoot
            ? String("Al arrancar, el receptor ya tenia la configuracion correcta.")
            : String("El receptor ya tenia la configuracion correcta.")) + cola;
    } else {
        reconciliation.summary = (reconciliation.atBoot ? String("Al arrancar se corrigieron ")
                                                        : String("Se corrigieron "))
            + String(reconciliation.fixed) + " de " + String(reconciliation.checked)
            + " ajustes." + cola;
    }
}

void tick(HardwareSerial& uart) {
    if(!mutex || xSemaphoreTake(mutex,portMAX_DELAY)!=pdTRUE)return;
    // Preguntar el modo al arrancar, sin que nadie pulse nada. Sin esto el
    // equipo no sabe si es base hasta que alguien lo consulta, y mientras tanto
    // el cliente NTRIP se reconecta a una base que no necesita correcciones.
    if(!bootQueried && !running && millis()>5000 && gnss_receiver::snapshot().enabled) {
        bootQueried=true;
        count=index=0;sent=ack=readback=false;overflowed=false;failure="";expectedMode="";
        // **Al arrancar se reconcilia, no solo se pregunta.**
        //
        // Antes esto solo leia VERSIONA y MODE, y la comparacion con la linea
        // base habia que pedirla a mano. La consecuencia se vio en el equipo el
        // 25-09-2026: `CONFIG UNDULATION AUTO` habia vuelto. La correccion que
        // se aplico dias antes no se guardo en la NVM del receptor —a proposito,
        // porque SAVECONFIG persiste tambien lo que este mal—, asi que al
        // apagarlo volvio a su valor guardado y nadie se enteraba.
        //
        // No se persiste, se vuelve a asegurar en cada arranque. Es idempotente,
        // no escribe la NVM, y arregla de paso el caso que pidio el propietario:
        // un receptor recien montado queda bien la primera vez que se enciende.
        action="reconcile";
        reconciliation = Reconciliation();
        reconciliation.reading = true;
        reconciliation.atBoot = true;
        maskReadback="";
        add("VERSIONA");add("MODE");add("CONFIG");add("MASK");
        phase="running";running=true;++job;launched=millis();
    }
    if(running) {
        if(millis()-launched>kJobBudgetMs) {
            finish("partial_or_unknown","Se agotó el tiempo del trabajo; consulta el estado antes de repetir.");
        } else if(!sent) {
            String wire=commands[index]+"\r\n";
            if(uart.availableForWrite()>=int(wire.length())) {
                uart.write(reinterpret_cast<const uint8_t*>(wire.c_str()),wire.length());
                sent=true;ack=readback=false;started=millis();
            }
        } else if(commands[index]=="CONFIG" && ack) {
            // CONFIG contesta con una rafaga de lineas. No hay marca de fin, asi
            // que se espera a que deje de llegar nada: quedarse con la primera
            // linea perderia el resto y la comparacion saldria mal.
            if(millis()-started > kConfigSettleMs) { readback=true; if(++index==count) finish("confirmed"); else sent=false; }
        } else if(ack && (!needsReply() || readback)) {
            if(++index==count) {
                // Fin de la fase de lectura de una reconciliacion: se compara y
                // se encolan las correcciones en esta misma cola.
                if(reconciliation.reading) {
                    applyReconciliation(!reconciliation.atBoot);
                    if(index < count) { sent=false; xSemaphoreGive(mutex); return; }
                }
                if(expectedMode.length() && !mode.startsWith(expectedMode))finish("partial_or_unknown","Modo leído distinto del solicitado.");
                else {commitProfile();finish(action=="base"?"base_mode_confirmed_coordinates_unverified":"confirmed");}
            } else sent=false;
        } else if(millis()-started>kCommandTimeoutMs) finish("partial_or_unknown","Sin ACK/lectura a tiempo; consulta antes de repetir.");
    }
    xSemaphoreGive(mutex);
}

int start(JsonVariantConst body,JsonDocument& out) {
    if(!mutex)return 503;
    if(!body.is<JsonObjectConst>() || !body["action"].is<const char*>())return 400;
    String name=body["action"].as<const char*>();
    if(body["action"].as<JsonString>().size()!=name.length())return 400;

    // --- Validacion previa fuera del mutex; nada se envia si algo no cuadra. ---
    unsigned telemetryHz=0, dgpsSeconds=0;
    double elevation=0;
    bool wantGps=true,wantBds=true,wantGlo=true,wantGal=true,wantQzss=true;

    if(name=="query"||name=="rover"||name=="raw_profile"||name=="config_query"||
       name=="stop_outputs"||name=="reconcile") {
        if(body.size()!=1)return 400;
    } else if(name=="telemetry") {
        if(body.size()!=2||!body["hz"].is<unsigned>())return 400;
        if(!validRate(body["hz"].as<unsigned>())){if(rateFor(body["hz"].as<unsigned>()))out["message"]=kRateCapMessage;return 400;}
        telemetryHz=body["hz"];
    } else if(name=="mask") {
        if(body.size()!=2||!body["elevation_deg"].is<double>())return 400;
        elevation=body["elevation_deg"].as<double>();
        // Rango del manual N4: -90 a 90 grados.
        if(!(elevation>=-90.0&&elevation<=90.0))return 400;
    } else if(name=="constellations") {
        if(body.size()<2||body.size()>6)return 400;
        if(!boolField(body,"gps",wantGps)||!boolField(body,"bds",wantBds)||!boolField(body,"glo",wantGlo)||
           !boolField(body,"gal",wantGal)||!boolField(body,"qzss",wantQzss))return 400;
        for(JsonPairConst field:body.as<JsonObjectConst>()){
            const String key=field.key().c_str();
            if(key!="action"&&key!="gps"&&key!="bds"&&key!="glo"&&key!="gal"&&key!="qzss")return 400;
        }
        // Deshabilitar todo dejaria el receptor sin seguimiento posible.
        if(!wantGps&&!wantBds&&!wantGlo&&!wantGal&&!wantQzss){
            out["message"]="Deja al menos una constelación habilitada.";return 400;
        }
    } else if(name=="dgps_timeout") {
        if(body.size()!=2||!body["seconds"].is<unsigned>())return 400;
        dgpsSeconds=body["seconds"];
        // Manual N4: 0 desactiva DGPS; 1-1800 segundos.
        if(dgpsSeconds>1800)return 400;
    } else if(name=="outputs"||name=="rtcm_base") {
        if(body.size()!=2||!body["messages"].is<JsonArrayConst>())return 400;
        JsonArrayConst list=body["messages"].as<JsonArrayConst>();
        if(!list.size()||list.size()>8)return 400;
        for(JsonVariantConst entry:list){
            if(!entry.is<JsonObjectConst>()||entry.size()!=2)return 400;
            if(!entry["name"].is<const char*>()||!entry["hz"].is<unsigned>())return 400;
            if(!validRate(entry["hz"].as<unsigned>())){if(rateFor(entry["hz"].as<unsigned>()))out["message"]=kRateCapMessage;return 400;}
            const String messageName=entry["name"].as<const char*>();
            if(name=="outputs"){
                // Solo sentencias NMEA con prefijo GP, como exige el manual N4.
                if(messageName!="GPGGA"&&messageName!="GPGSV"&&messageName!="GPGST"&&messageName!="GPRMC"&&
                   messageName!="GPVTG"&&messageName!="GPZDA"&&messageName!="GPGSA")return 400;
            } else {
                // MSM4 (107x/108x…) y MSM7 (1077/1087/1097/1117/1127). Los MSM7
                // llevan resolución extendida y Doppler, y son los que permiten
                // aprovechar de verdad un receptor de triple banda: MSM4 recorta
                // la resolución de fase que la tercera frecuencia aporta.
                if(messageName!="RTCM1005"&&messageName!="RTCM1006"&&messageName!="RTCM1033"&&
                   messageName!="RTCM1074"&&messageName!="RTCM1084"&&messageName!="RTCM1094"&&
                   messageName!="RTCM1114"&&messageName!="RTCM1124"&&
                   messageName!="RTCM1077"&&messageName!="RTCM1087"&&messageName!="RTCM1097"&&
                   messageName!="RTCM1117"&&messageName!="RTCM1127")return 400;
            }
        }
    } else if(name=="save") {
        // SAVECONFIG escribe la NVM del receptor: exige confirmacion explicita.
        if(body.size()!=2||body["confirm"]!=true)return 400;
    } else return 400;

    xSemaphoreTake(mutex,portMAX_DELAY);
    int code=prepare(name,out);
    if(!code) {
        if(name=="raw_profile") {
            add("OBSVMB COM2 1");
            for(const char* log:{"GPSEPHB","GLOEPHB","GALEPHB","BDSEPHB","BD3EPHB"})add(String(log)+" COM2 30");
        }
        if(name=="query") {add("VERSIONA");add("MODE");}
        if(name=="config_query") {maskReadback="";add("MASK");}
        // Reconciliación: primero se LEE lo que el receptor tiene de verdad.
        // Los comandos correctores se añaden a esta misma cola cuando la lectura
        // termina, en `applyReconciliation()`.
        if(name=="reconcile") {
            reconciliation = Reconciliation();
            reconciliation.reading = true;
            maskReadback="";
            add("CONFIG");
            add("MASK");
        }
        // El movil trabaja en altura ELIPSOIDAL, igual que la base.
        //
        // Aqui habia `CONFIG UNDULATION AUTO`, que le pedia al receptor aplicar
        // su propio modelo geoidal —no documentado, de resolucion desconocida— y
        // entregar altura sobre el nivel del mar. La app no puede deshacer esa
        // correccion ni declarar que modelo se uso, asi que la cota resultante
        // no se puede defender ante nadie: lleva veintitantos metros de origen
        // desconocido.
        //
        // La app aplica su propio geoide, declarado y versionado, sobre la
        // altura elipsoidal. Es lo que exige `geoid-models.md`.
        // **Pasar a movil limpia primero las salidas de COM2.**
        //
        // Sin esto, los mensajes RTCM que se configuraron cuando el equipo fue
        // base **siguen saliendo** despues de volver a movil: `MODE ROVER SURVEY`
        // cambia el modo, no los registros. Visto en el equipo el 25-09-2026 con
        // el receptor en `MODE ROVER SURVEY` y `LOGLIST` devolviendo 1005, 1033,
        // 1077, 1087, 1097 y 1127 a 1 Hz.
        //
        // Cuesta la cuarta parte de la UART en tramas que no sirven para nada, y
        // las mete **entrelazadas con el NMEA de la posicion**, que es la
        // sospecha mas firme de por que se descartaba el 13 % de las tramas GGA.
        //
        // **Y repone las salidas de posicion en el mismo trabajo**, antes del
        // SAVECONFIG. Hasta 0.7.12 este comentario decia que no hacia falta
        // porque «todos los perfiles de la app ponen `rover` y `telemetry`
        // juntos». No era verdad: el boton del panel y el «Pasar a rover» de
        // las dos apps mandan solo `rover`, y el receptor se quedaba sin GGA
        // —y lo guardaba asi, de modo que tampoco volvia al apagarlo—.
        //
        // Se reponen GGA a la ultima tasa aplicada (5 Hz si esta sesion del
        // ESP32 no aplico ninguna) y GST, GSV y GSA a 1 Hz: lo mismo que
        // `telemetry`. Son 9 ordenes, por debajo de las 20 de un trabajo.
        if(name=="rover") {
            rover=false;mode="";
            add("UNLOG COM2");add("MODE ROVER SURVEY");add("CONFIG UNDULATION 0.0000");add("MODE");
            expectedMode="MODE ROVER SURVEY";
            addPositionOutputs(profileState.gga_rate_hz);
        }
        if(name=="telemetry") {
            addPositionOutputs(telemetryHz);
            pendingGgaHz=telemetryHz;
        }
        if(name=="stop_outputs") add("UNLOG COM2");
        if(name=="mask") {
            add("MASK "+String(elevation,2));
            profileState.elevation_deg=elevation;
        }
        if(name=="constellations") {
            const char* names[5]={"GPS","BDS","GLO","GAL","QZSS"};
            const bool wanted[5]={wantGps,wantBds,wantGlo,wantGal,wantQzss};
            for(int i=0;i<5;++i)add(String(wanted[i]?"UNMASK ":"MASK ")+names[i]);
            profileState.gps=wantGps;profileState.bds=wantBds;profileState.glo=wantGlo;
            profileState.gal=wantGal;profileState.qzss=wantQzss;
        }
        if(name=="dgps_timeout") {
            add("CONFIG DGPS TIMEOUT "+String(dgpsSeconds));
            profileState.dgps_timeout_s=int(dgpsSeconds);
        }
        if(name=="outputs"||name=="rtcm_base") {
            String summary;
            for(JsonVariantConst entry:body["messages"].as<JsonArrayConst>()){
                const String messageName=entry["name"].as<const char*>();
                const unsigned hz=entry["hz"];
                add(messageName+" COM2 "+rateFor(hz));
                if(name=="outputs" && messageName=="GPGGA") pendingGgaHz=hz;
                if(summary.length())summary+=", ";
                summary+=messageName+" "+String(hz)+" Hz";
            }
            if(name=="outputs")profileState.outputs=summary;else profileState.rtcm=summary;
        }
        // Todo cambio de configuración se graba en la memoria no volátil del
        // receptor, no solo cuando se pide expresamente. Sin esto, cualquier
        // corte de corriente devuelve el UM980 a su estado anterior y el equipo
        // aparenta estar averiado: el enlace responde pero no llega ni una
        // posición. Ha pasado dos veces. La contrapartida es desgaste de la
        // flash del receptor, acotado porque son cambios manuales, no un bucle.
        // "base" incluido a proposito: una base que pierde corriente y vuelve
        // en el modo anterior seguiria emitiendo correcciones desde una
        // coordenada equivocada, y los rovers fijarian con buena pinta sobre
        // un punto que no es. Es el fallo mas caro de los que puede tener.
        if(name=="rover"||name=="base"||name=="telemetry"||name=="stop_outputs"||name=="mask"||
           name=="constellations"||name=="dgps_timeout"||name=="outputs"||name=="rtcm_base")
            add("SAVECONFIG");
        if(name=="save") add("SAVECONFIG");
        code=launch(out);
        if(code!=202)finish("idle","");
    }
    xSemaphoreGive(mutex);return code;
}

int applyBase(JsonVariantConst plan,JsonDocument& out) {
    if(!mutex)return 503;
    // El marco es siempre WGS84: no se transforman coordenadas ni se pide al
    // usuario que declare un datum que no tendría efecto.
    xSemaphoreTake(mutex,portMAX_DELAY);int code=prepare("base",out);
    if(!code){
        rover=false;mode="";
        String command="MODE BASE "+String(plan["station_id"].as<unsigned>())+" ";
        if(plan["method"]=="known") {
            add("CONFIG UNDULATION 0.0000");
            command+=String(plan["latitude_deg"].as<double>(),11)+" "+String(plan["longitude_deg"].as<double>(),11)+" "+String(plan["arp_ellipsoid_height_m"].as<double>(),4);
        } else command+="TIME "+String(plan["average_seconds"].as<unsigned>())+" "+String(plan["reuse_distance_m"].as<double>(),4);
        add(command);add("MODE");expectedMode="MODE BASE";code=launch(out);
        if(code!=202)finish("idle","");
    }
    xSemaphoreGive(mutex);return code;
}

void status(JsonObject out){
    if(!mutex){out["state"]="unavailable";return;}
    xSemaphoreTake(mutex,portMAX_DELAY);
    out["state"]=phase;out["job_id"]=job;out["action"]=action;out["completed_commands"]=index;
    out["total_commands"]=count;
    out["mode"]=mode;out["version"]=version;out["error"]=failure;out["saved"]=profileState.saved;
    out["base_coordinates_verified"]=false;out["source"]="esp32_uart";
    xSemaphoreGive(mutex);
}

void profile(JsonObject out){
    if(!mutex){out["available"]=false;return;}
    xSemaphoreTake(mutex,portMAX_DELAY);
    out["available"]=true;
    // elevation_known distingue "lo aplicamos nosotros" de "es el valor por defecto del manual".
    out["elevation_mask_deg"]=profileState.elevation_deg;
    out["elevation_mask_applied"]=profileState.elevation_known;
    JsonObject systems=out["constellations"].to<JsonObject>();
    systems["gps"]=profileState.gps;systems["bds"]=profileState.bds;systems["glo"]=profileState.glo;
    systems["gal"]=profileState.gal;systems["qzss"]=profileState.qzss;
    out["constellations_applied"]=profileState.constellations_known;
    out["nmea_outputs"]=profileState.outputs;
    out["rtcm_profile"]=profileState.rtcm;
    if(profileState.dgps_timeout_s>=0)out["dgps_timeout_s"]=profileState.dgps_timeout_s;
    else out["dgps_timeout_s"]=nullptr;
    out["height_reference"]=heightReference();
    // El informe de la última reconciliación. Va aquí y no en un sitio aparte
    // porque es lo mismo: qué sabemos de la configuración del receptor.
    JsonObject rec = out["reconciliation"].to<JsonObject>();
    rec["ran"] = reconciliation.ran;
    if(reconciliation.ran) {
        rec["checked"] = reconciliation.checked;
        rec["fixed"] = reconciliation.fixed;
        rec["differences"] = reconciliation.differences;
        rec["summary"] = reconciliation.summary;
    }
    out["mask_readback"]=maskReadback;
    out["persisted_to_receiver"]=profileState.saved;
    xSemaphoreGive(mutex);
}
}
