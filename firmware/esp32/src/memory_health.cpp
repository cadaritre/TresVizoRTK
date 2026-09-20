#include "memory_health.h"
#include <Arduino.h>
#include <esp_heap_caps.h>
namespace memory_health {
namespace {const char* result="not_tested";size_t tested=0;}
void begin(){
    if(!psramFound()){result="not_detected";return;}
    const size_t size=1024*1024;
    auto memory=static_cast<volatile uint32_t*>(heap_caps_malloc(size,MALLOC_CAP_SPIRAM|MALLOC_CAP_8BIT));
    if(!memory){result="allocation_failed";return;}
    bool valid=true;
    for(uint32_t pattern: {0x55555555U,0xaaaaaaaaU,0x12345678U}) {
        for(size_t i=0;i<size/4;++i)memory[i]=uint32_t(i)^pattern;
        for(size_t i=0;i<size/4;++i)if(memory[i]!=(uint32_t(i)^pattern)){valid=false;break;}
        delay(1);
    }
    free(const_cast<uint32_t*>(memory));tested=size;result=valid?"passed":"failed";
}
void status(JsonObject out){
 out["psram_test"]=result;out["tested_bytes"]=tested;
 out["internal_free_bytes"]=heap_caps_get_free_size(MALLOC_CAP_INTERNAL|MALLOC_CAP_8BIT);
 out["internal_min_free_bytes"]=heap_caps_get_minimum_free_size(MALLOC_CAP_INTERNAL|MALLOC_CAP_8BIT);
 out["internal_largest_block_bytes"]=heap_caps_get_largest_free_block(MALLOC_CAP_INTERNAL|MALLOC_CAP_8BIT);
 out["psram_total_bytes"]=ESP.getPsramSize();out["psram_free_bytes"]=ESP.getFreePsram();
}
}
