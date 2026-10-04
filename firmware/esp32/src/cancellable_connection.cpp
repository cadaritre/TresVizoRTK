#include "cancellable_connection.h"
#include <IPAddress.h>
#include <lwip/dns.h>
#include <lwip/tcpip.h>
#include <atomic>
#include <cerrno>
#include <cstring>
#include <fcntl.h>
#include <new>
#include <sys/socket.h>
#include <sys/select.h>
#include <netinet/in.h>
#include <unistd.h>

namespace cancellable_connection {
namespace {
struct Query {
    // Un dueño en el worker y otro en TCP/IP. Cancelar no libera la memoria
    // que una respuesta DNS tardía todavía puede usar.
    std::atomic<unsigned> references{2};
    std::atomic<bool> done{false};
    uint32_t address=0;
    char host[129]{};
};
void release(Query* q){if(q->references.fetch_sub(1)==1)delete q;}
void found(const char*,const ip_addr_t* address,void* argument){
    auto* q=static_cast<Query*>(argument);
    if(address && IP_IS_V4(address))q->address=ip4_addr_get_u32(ip_2_ip4(address));
    q->done.store(true,std::memory_order_release);
    release(q);
}
void startDns(void* argument){
    auto* q=static_cast<Query*>(argument);
    ip_addr_t address{};
    const err_t result=dns_gethostbyname(q->host,&address,found,q);
    if(result!=ERR_INPROGRESS)found(nullptr,result==ERR_OK?&address:nullptr,q);
}
bool resolve(const String& host,IPAddress& address,const std::function<bool()>& current){
    if(!current())return false;
    if(address.fromString(host))return true;
    if(host.length()>128)return false;
    auto* q=new(std::nothrow) Query;
    if(!q)return false;
    std::memcpy(q->host,host.c_str(),host.length()+1);
    // try_callback no espera a que haya hueco en el buzón TCP/IP.
    if(tcpip_try_callback(startDns,q)!=ERR_OK){release(q);release(q);return false;}
    const uint32_t began=millis();
    while(!q->done.load(std::memory_order_acquire) && current() && millis()-began<5000)
        vTaskDelay(pdMS_TO_TICKS(10));
    const bool ready=q->done.load(std::memory_order_acquire) && q->address && current();
    if(ready)address=q->address;
    release(q);
    return ready;
}
}
bool write(WiFiClient& client,const uint8_t* data,size_t size,const std::function<bool()>& current,uint32_t budgetMs){
    const int fd=client.fd();
    size_t offset=0;const uint32_t began=millis();
    while(fd>=0 && offset<size && current() && millis()-began<budgetMs){
        const int sent=::send(fd,data+offset,size-offset,MSG_DONTWAIT);
        if(sent>0){offset+=size_t(sent);continue;}
        if(sent==0 || (errno!=EAGAIN && errno!=EWOULDBLOCK && errno!=EINTR))break;
        fd_set writes;FD_ZERO(&writes);FD_SET(fd,&writes);timeval wait{0,20000};
        if(::select(fd+1,nullptr,&writes,nullptr,&wait)<0 && errno!=EINTR)break;
    }
    if(offset==size)return true;
    // Una trama parcialmente escrita no se retoma después de sustituir la sesión.
    client.stop();return false;
}
bool connect(WiFiClient& client,const String& host,uint16_t port,const std::function<bool()>& current){
    client.stop();
    IPAddress ip;
    if(!resolve(host,ip,current) || !current())return false;
    const int fd=::socket(AF_INET,SOCK_STREAM,0);
    if(fd<0)return false;
    auto failed=[&](){::close(fd);return false;};
    const int flags=fcntl(fd,F_GETFL,0);
    if(flags<0 || fcntl(fd,F_SETFL,flags|O_NONBLOCK)<0)return failed();
    sockaddr_in destination{};
    destination.sin_family=AF_INET;destination.sin_port=htons(port);
    destination.sin_addr.s_addr=static_cast<uint32_t>(ip);
    const int result=::connect(fd,reinterpret_cast<sockaddr*>(&destination),sizeof(destination));
    if(result<0 && errno!=EINPROGRESS)return failed();
    bool connected=result==0;
    const uint32_t began=millis();
    while(!connected && current() && millis()-began<2000){
        fd_set writes;FD_ZERO(&writes);FD_SET(fd,&writes);
        timeval wait{0,20000}; // comprobar sustitución al menos cada 20 ms
        const int selected=::select(fd+1,nullptr,&writes,nullptr,&wait);
        if(selected<0){if(errno==EINTR)continue;return failed();}
        if(!selected)continue;
        int error=0;socklen_t size=sizeof(error);
        if(getsockopt(fd,SOL_SOCKET,SO_ERROR,&error,&size)<0 || error)return failed();
        connected=true;
    }
    if(!connected || !current())return failed();
    timeval timeout{2,0};
    if(setsockopt(fd,SOL_SOCKET,SO_SNDTIMEO,&timeout,sizeof(timeout))<0 ||
       setsockopt(fd,SOL_SOCKET,SO_RCVTIMEO,&timeout,sizeof(timeout))<0 ||
       fcntl(fd,F_SETFL,flags)<0)return failed();
    client=WiFiClient(fd); // transfiere propiedad; solo el worker cierra este socket
    client.setTimeout(2000);
    return true;
}
}
