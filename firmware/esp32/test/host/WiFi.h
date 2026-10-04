#pragma once
#include "Arduino.h"
constexpr int WL_CONNECTED=3;
struct HostIp {String toString()const{return "127.0.0.1";}};
struct HostWiFi {unsigned softAPgetStationNum()const{return 0;}HostIp localIP()const{return {};}HostIp softAPIP()const{return {};}int state=WL_CONNECTED;int status()const{return state;}};
inline HostWiFi WiFi;
