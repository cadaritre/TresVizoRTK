#include "wire_filter.h"
#include <cassert>
#include <string>
#include <vector>
uint32_t crc(const std::vector<uint8_t>& v){uint32_t c=0;for(uint8_t b:v){c^=b;for(int i=0;i<8;++i)c=(c>>1)^((c&1)?0xedb88320U:0);}return c;}
int main(){
 gnss::WireFilter parser;std::string text;uint32_t now=1;
 std::string payload="$GPGGA,fake*00\r\n#MODE,fake*00\r\n";
 std::vector<uint8_t> frame(24,0);frame[0]=0xaa;frame[1]=0x44;frame[2]=0xb5;frame[6]=payload.size();frame.insert(frame.end(),payload.begin(),payload.end());uint32_t c=crc(frame);for(int i=0;i<4;++i)frame.push_back(c>>(8*i));
 auto feed=[&](uint8_t b){parser.feed(b,now++,[&](char b){text+=b;});};
 for(uint8_t b:frame)feed(b);
 assert(text.empty()&&parser.native_valid==1);
 frame.back()^=1;for(uint8_t b:frame)feed(b);assert(text.empty()&&parser.native_invalid==1);
 for(char b:std::string("$GPGGA,real\r\n"))feed(b);assert(text=="$GPGGA,real\r\n");
 feed(0xaa);now+=600;feed('$');assert(text.back()=='$'&&parser.native_invalid==2);
}
