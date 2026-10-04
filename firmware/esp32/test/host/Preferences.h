#pragma once
#include "Arduino.h"
#include <map>
inline bool hostStorageFails=false;
class Preferences {
    std::map<std::string,String> values;
public:
    bool isKey(const char* key)const{return values.count(key);}
    uint8_t getUChar(const char* key,uint8_t fallback)const{const auto i=values.find(key);return i==values.end()?fallback:uint8_t(std::atoi(i->second.c_str()));}
    size_t putUChar(const char* key,uint8_t v){values[key]=String(unsigned(v));return 1;}
    bool begin(const char*,bool){return true;}
    String getString(const char* key,const char* fallback){const auto i=values.find(key);return i==values.end()?String(fallback):i->second;}
    size_t putString(const char* key,const String& value){if(hostStorageFails)return 0;values[key]=value;return value.size();}
};
