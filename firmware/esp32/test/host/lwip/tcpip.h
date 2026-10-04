#pragma once
#include "dns.h"
inline std::function<err_t(void(*)(void*),void*)> hostTcpip;
inline err_t tcpip_try_callback(void(*fn)(void*),void* arg){return hostTcpip(fn,arg);}
