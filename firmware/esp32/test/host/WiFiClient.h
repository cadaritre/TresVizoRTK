#pragma once
#include "Arduino.h"
#include <unistd.h>
inline std::function<bool(const std::string&)> hostOnConnect;
inline std::function<void()> hostOnRead;
inline std::string hostSocketInput;
inline std::vector<std::string> hostSocketRequests;
class WiFiClient {
    bool open=false;
    int ownedFd=-1;
    size_t cursor=0;
public:
    WiFiClient()=default;
    explicit WiFiClient(int fd):open(true),ownedFd(fd){}
    int fd()const{return ownedFd;}
    explicit operator bool()const{return open;}
    size_t write(const uint8_t*,size_t n){return n;}
    void setTimeout(unsigned){}
    bool connect(const char* host,uint16_t,unsigned){cursor=0;open=hostOnConnect?hostOnConnect(host):true;return open;}
    bool connected()const{return open;}
    int available()const{return int(hostSocketInput.size()-cursor);}
    int read(){if(hostOnRead)hostOnRead();return cursor<hostSocketInput.size()?uint8_t(hostSocketInput[cursor++]):-1;}
    void print(const String& s){hostSocketRequests.push_back(s);}
    void stop(){if(ownedFd>=0){::close(ownedFd);ownedFd=-1;}open=false;cursor=hostSocketInput.size();}
};
