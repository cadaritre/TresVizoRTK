#include "oled_transport.h"
#include <array>
#include <cassert>
#include <iostream>
#include <vector>

struct Bus {
    std::vector<std::vector<uint8_t>> packets;
    std::vector<uint8_t> current;
    size_t failAt=SIZE_MAX, shortAt=SIZE_MAX;
    void beginTransmission(uint8_t address) { assert(address==0x3c); current.clear(); }
    size_t write(uint8_t value) { current.push_back(value); return 1; }
    size_t write(const uint8_t* data,size_t size) {
        const size_t written=packets.size()==shortAt?size-1:size;
        current.insert(current.end(),data,data+written);
        return written;
    }
    uint8_t endTransmission() {
        assert(current.size()<=32);
        packets.push_back(current);
        return packets.size()-1==failAt?4:0;
    }
};
bool hasOn(const Bus& bus) {
    for (const auto& packet:bus.packets)
        if(packet==std::vector<uint8_t>({0x00,0xaf})) return true;
    return false;
}
int main() {
    std::array<uint8_t,1024> bitmap{};
    // Patrón distinto en ambas mitades, esquinas y páginas: detecta recortes,
    // inversión de bits, transposición y un desfase del puntero de la OLED.
    for(size_t y=0;y<64;++y)
        for(size_t x=0;x<128;++x)
            if(x==0 || x==127 || y==0 || y==63 || (x*3+y*7)%17==0)
                bitmap[y*16+x/8]|=uint8_t(0x80>>(x%8));
    Bus initialized;
    assert(oled_transport::initialize(initialized,0x3c));
    assert(!hasOn(initialized));
    const auto& init=initialized.packets.back();
    assert(init[1]==0xae);
    for(size_t failure=0;failure<initialized.packets.size();++failure) {
        Bus nack;nack.failAt=failure;
        assert(!oled_transport::initialize(nack,0x3c));
        assert(!hasOn(nack));
    }
    Bus complete;
    assert(oled_transport::frame(complete,0x3c,bitmap.data(),true));
    assert(complete.packets.front()==std::vector<uint8_t>({0,0x20,0,0x21,0,127,0x22,0,7}));
    assert(hasOn(complete));
    std::vector<uint8_t> ram;
    for(const auto& packet:complete.packets)
        if(packet.front()==0x40)ram.insert(ram.end(),packet.begin()+1,packet.end());
    assert(ram.size()==1024);
    for(size_t y=0;y<64;++y)
        for(size_t x=0;x<128;++x)
            assert(bool(ram[(y/8)*128+x]&(1<<(y%8)))==bool(bitmap[y*16+x/8]&(0x80>>(x%8))));
    // Inyectar fallo en CADA paquete, incluso el último y el encendido.
    for(size_t failure=0;failure<complete.packets.size();++failure) {
        Bus nack;nack.failAt=failure;
        assert(!oled_transport::frame(nack,0x3c,bitmap.data(),true));
        assert(nack.packets.size()==failure+1); // No continuar tras perder datos.
        if(failure+1<complete.packets.size())assert(!hasOn(nack));
        nack.failAt=SIZE_MAX;nack.packets.clear();
        assert(oled_transport::initialize(nack,0x3c));
        nack.packets.clear();
        assert(oled_transport::frame(nack,0x3c,bitmap.data(),true));
        assert(nack.packets==complete.packets); // Recuperación completa desde 0.
        Bus truncated;truncated.shortAt=failure;
        assert(!oled_transport::frame(truncated,0x3c,bitmap.data(),true));
        assert(truncated.packets.size()==failure+1);
    }
    Bus refresh;
    assert(oled_transport::frame(refresh,0x3c,bitmap.data(),false));
    assert(!hasOn(refresh)); // Refresco normal sin apagar/encender y parpadear.
    assert(!oled_transport::frame(refresh,0x3c,nullptr,true));
    std::cout<<"oled_transport: 8192 pixeles, NACK/escritura corta por paquete y recuperacion OK\n";
}
