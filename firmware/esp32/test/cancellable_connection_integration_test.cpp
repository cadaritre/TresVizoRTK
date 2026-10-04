#include "host/Arduino.h"
#include "../src/cancellable_connection.cpp"
using namespace cancellable_connection;
int main(){
 hostTcpip=[](auto fn,void* arg){fn(arg);return ERR_OK;};
 auto always=[](){return true;};
 IPAddress ip;assert(resolve("127.0.0.1",ip,always));
 dns_found_callback pending=nullptr;void* context=nullptr;
 hostDns=[&](const char*,ip_addr_t*,dns_found_callback fn,void* arg){pending=fn;context=arg;return ERR_INPROGRESS;};
 bool current=true;
 hostOnDelay=[&](){current=false;};
 assert(!resolve("old.test",ip,[&](){return current;}));
 assert(hostMillis==10 && pending && context);
 auto* abandoned=static_cast<Query*>(context);assert(abandoned->references==1);
 ip_addr_t answer{htonl(0x7f000001)};
 pending(nullptr,&answer,context); // respuesta tardía después de cancelar: dueño TCP/IP aún válido
 hostOnDelay={};
 hostDns=[&](const char*,ip_addr_t* target,dns_found_callback,void*){*target=answer;return ERR_OK;};
 assert(resolve("new.test",ip,always));
 // Cancelación antes de que TCP/IP haya tomado el mensaje de su buzón.
 void(*queued)(void*)=nullptr;void* queuedArg=nullptr;
 hostTcpip=[&](auto fn,void* arg){queued=fn;queuedArg=arg;return ERR_OK;};
 current=true;hostOnDelay=[&](){current=false;};
 assert(!resolve("queued.test",ip,[&](){return current;}));
 assert(static_cast<Query*>(queuedArg)->references==1);queued(queuedArg);
 hostOnDelay={};hostTcpip=[](auto fn,void* arg){fn(arg);return ERR_OK;};
 // DNS nunca responde: plazo local acotado y callback tardío sin puntero a pila.
 hostDns=[&](const char*,ip_addr_t*,dns_found_callback fn,void* arg){pending=fn;context=arg;return ERR_INPROGRESS;};
 const uint32_t began=hostMillis;assert(!resolve("timeout.test",ip,always));
 assert(hostMillis-began==5000);pending(nullptr,nullptr,context);
 hostTcpip=[](auto,void*){return ERR_MEM;};assert(!resolve("full.test",ip,always));
 hostTcpip=[](auto fn,void* arg){fn(arg);return ERR_OK;};
 hostDns=[](const char*,ip_addr_t*,dns_found_callback,void*){return ERR_MEM;};assert(!resolve("failed.test",ip,always));
 // TCP real en loopback: adopta el descriptor solo si la decisión sigue vigente.
 const int listener=::socket(AF_INET,SOCK_STREAM,0);assert(listener>=0);
 sockaddr_in address{};address.sin_family=AF_INET;address.sin_addr.s_addr=htonl(INADDR_LOOPBACK);
 assert(::bind(listener,reinterpret_cast<sockaddr*>(&address),sizeof address)==0);
 assert(::listen(listener,1)==0);socklen_t size=sizeof address;
 assert(getsockname(listener,reinterpret_cast<sockaddr*>(&address),&size)==0);
 WiFiClient client;assert(connect(client,"127.0.0.1",ntohs(address.sin_port),always));
 const int peer=::accept(listener,nullptr,nullptr);assert(peer>=0);
 assert(client.connected() && client.fd()>=0);
 const uint8_t data[]{1,2,3};assert(write(client,data,sizeof data,always));
 uint8_t received[3]{};assert(::recv(peer,received,sizeof received,0)==3 && !std::memcmp(data,received,3));
 std::vector<uint8_t> flood(4*1024*1024,7);unsigned checksWrite=0;
 assert(!write(client,flood.data(),flood.size(),[&](){return ++checksWrite<3;}));
 assert(!client.connected());::close(peer);
 unsigned checks=0;
 assert(!connect(client,"127.0.0.1",ntohs(address.sin_port),[&](){return ++checks<4;}));
 assert(!client.connected());::close(listener);
 std::puts("cancellable_connection_integration: OK");
}
