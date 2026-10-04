#pragma once
#include "Arduino.h"
#include <arpa/inet.h>
class IPAddress {
    uint32_t value=0;
public:
    bool fromString(const String& s){return inet_pton(AF_INET,s.c_str(),&value)==1;}
    IPAddress& operator=(uint32_t v){value=v;return *this;}
    explicit operator uint32_t()const{return value;}
};
