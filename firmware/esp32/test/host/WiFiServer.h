#pragma once
#include "WiFiClient.h"
inline std::vector<uint16_t> hostListeners;
class WiFiServer {
public:
    explicit WiFiServer(uint16_t port){hostListeners.push_back(port);}
    void stop(){}
    void begin(){}
    void setNoDelay(bool){}
    WiFiClient available(){return {};}
};
