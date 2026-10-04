#pragma once
#include <Arduino.h>
#include <WiFiClient.h>
#include <functional>
namespace cancellable_connection {
// DNS y TCP pertenecen al worker; la petición del operador solo cambia la
// generación. Ni el DNS de Arduino (15 s), ni connect() retienen el relevo.
bool write(WiFiClient& client,const uint8_t* data,size_t size,const std::function<bool()>& current,uint32_t budgetMs=1000);
bool connect(WiFiClient& client,const String& host,uint16_t port,const std::function<bool()>& current);
}
