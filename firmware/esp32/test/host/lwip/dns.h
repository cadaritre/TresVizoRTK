#pragma once
#include <cstdint>
#include <functional>
using err_t=int;
constexpr err_t ERR_OK=0,ERR_INPROGRESS=-5,ERR_MEM=-1;
struct ip_addr_t {uint32_t addr=0;};
#define IP_IS_V4(p) ((p)!=nullptr)
#define ip_2_ip4(p) (p)
#define ip4_addr_get_u32(p) ((p)->addr)
using dns_found_callback=void(*)(const char*,const ip_addr_t*,void*);
inline std::function<err_t(const char*,ip_addr_t*,dns_found_callback,void*)> hostDns;
inline err_t dns_gethostbyname(const char* name,ip_addr_t* ip,dns_found_callback fn,void* arg){return hostDns(name,ip,fn,arg);}
