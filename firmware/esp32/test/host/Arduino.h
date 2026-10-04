#pragma once
// Adaptadores del banco: solo reloj, mutex y UART simulados. La lógica que se
// prueba se compila directamente desde src/, sin otra versión del controlador.
#include <algorithm>
#include <cassert>
#include <cctype>
#include <cstdint>
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <functional>
#include <string>
#include <vector>
#define ARDUINOJSON_ENABLE_ARDUINO_STRING 1
#define ARDUINOJSON_ENABLE_ARDUINO_STREAM 0
#define ARDUINOJSON_ENABLE_ARDUINO_PRINT 0
#define ARDUINOJSON_ENABLE_PROGMEM 0
class String : public std::string {
    using const_iterator=std::string::const_iterator; // evita adapter de iteradores en ArduinoJson
public:
    using std::string::string;
    using std::string::operator=;
    String& operator=(const char* p){assign(p?p:"");return *this;}
    String()=default;
    String(const char* p):std::string(p?p:""){}
    String(const std::string& s):std::string(s){}
    explicit String(unsigned v):std::string(std::to_string(v)){}
    explicit String(int v):std::string(std::to_string(v)){}
    explicit String(double v,unsigned places=2) {char b[128];std::snprintf(b,sizeof b,"%.*f",int(places),v);assign(b);}
    double toDouble()const{return std::strtod(c_str(),nullptr);}
    bool isEmpty() const{return empty();}
    bool startsWith(const String& s)const{return compare(0,s.size(),s)==0;}
    bool endsWith(const String& s)const{return size()>=s.size() && compare(size()-s.size(),s.size(),s)==0;}
    int indexOf(const String& s,size_t from=0)const{const auto i=find(s,from);return i==npos?-1:int(i);}
    int indexOf(char c,size_t from=0)const{const auto i=find(c,from);return i==npos?-1:int(i);}
    String substring(size_t from,size_t to=npos)const{return from>=size()?String():String(substr(from,to==npos?npos:to-from));}
    void remove(size_t from){erase(from);}
    void trim(){const auto a=find_first_not_of(" \t\r\n");if(a==npos)clear();else assign(substr(a,find_last_not_of(" \t\r\n")-a+1));}
    bool concat(const char* s){append(s);return true;}
};
class Printable;
inline uint32_t hostMillis=0;
inline uint32_t millis(){return hostMillis;}
inline int64_t esp_timer_get_time(){return int64_t(hostMillis)*1000;}
struct HostMutex {bool held=false;};
using SemaphoreHandle_t=HostMutex*;
constexpr int pdTRUE=1,pdPASS=1,portMAX_DELAY=-1;
inline uint32_t pdMS_TO_TICKS(uint32_t ms){return ms;}
inline SemaphoreHandle_t xSemaphoreCreateMutex(){static HostMutex locks[16];static unsigned n=0;assert(n<16);return &locks[n++];}
inline int xSemaphoreTake(SemaphoreHandle_t m,int){assert(m && !m->held);m->held=true;return pdTRUE;}
inline void xSemaphoreGive(SemaphoreHandle_t m){assert(m && m->held);m->held=false;}
inline int xTaskCreate(void(*)(void*),const char*,unsigned,void*,int,void*){return pdPASS;}
inline std::function<void()> hostOnDelay;
inline void vTaskDelay(uint32_t ms){hostMillis+=ms;if(hostOnDelay)hostOnDelay();}
struct HardwareSerial {
    std::vector<std::string> sent;
    int availableForWrite()const{return 2048;}
    size_t write(const uint8_t* p,size_t n){sent.emplace_back(reinterpret_cast<const char*>(p),n);return n;}
};
#include <deque>
struct HostQueue {size_t width=0;std::deque<std::vector<uint8_t>> items;};
using QueueHandle_t=HostQueue*;
inline QueueHandle_t xQueueCreate(size_t,size_t width){static HostQueue q;q.width=width;return &q;}
inline int xQueueSend(QueueHandle_t q,const void* p,int){const auto* b=static_cast<const uint8_t*>(p);q->items.emplace_back(b,b+q->width);return pdTRUE;}
inline int xQueueReceive(QueueHandle_t q,void* p,uint32_t wait){if(q->items.empty()){vTaskDelay(wait);return 0;}std::memcpy(p,q->items.front().data(),q->width);q->items.pop_front();return pdTRUE;}
