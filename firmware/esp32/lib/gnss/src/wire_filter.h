#pragma once
#include <cstdint>
#include <cstddef>
namespace gnss {
// Mantiene el binario Unicore fuera de los parsers de texto. El registro conserva el flujo original.
class WireFilter {
 uint8_t prefix[8]={};size_t used=0,total=0;uint32_t crc=0,received=0,last=0;
 static uint32_t update(uint32_t c,uint8_t b){c^=b;for(int i=0;i<8;++i)c=(c>>1)^((c&1)?0xedb88320U:0);return c;}
 void reset(){used=total=0;crc=received=0;}
public:
 uint32_t native_valid=0,native_invalid=0;
 template<class Consumer> void feed(uint8_t byte,uint32_t now,Consumer text){
  if(used && now-last>500){++native_invalid;reset();}last=now;
  if(!used){if(byte==0xaa){prefix[0]=byte;used=1;crc=update(0,byte);}else text(char(byte));return;}
  if((used==1&&byte!=0x44)||(used==2&&byte!=0xb5)){
   reset();if(byte==0xaa){prefix[0]=byte;used=1;crc=update(0,byte);}else text(char(byte));return;
  }
  if(used<8)prefix[used]=byte;
  if(used==7){total=24+size_t(prefix[6])+(size_t(byte)<<8)+4;if(total>16412){++native_invalid;reset();return;}}
  if(!total||used<total-4)crc=update(crc,byte);
  else received|=uint32_t(byte)<<(8*(used-(total-4)));
  ++used;
  if(total&&used==total){if(crc==received)++native_valid;else ++native_invalid;reset();}
 }
};
}
