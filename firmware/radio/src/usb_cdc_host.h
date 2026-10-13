#pragma once
#include <cstddef>
#include <cstdint>

// El USB-C del radio como **anfitrión** (USB-OTG del ESP32-S3, PHY interno en GPIO19/20)
// con un cliente CDC-ACM mínimo sobre la USB Host Library de ESP-IDF 4.4: abre el
// primer dispositivo que tenga una interfaz de datos CDC (el USB-Serial/JTAG del
// MeridianV, 303A:1001), le pone DTR = RTS = 0 y mueve bytes. Qué hay del otro lado lo
// decide el saludo del enlace (docs/radio/USB_LINK.md), no este módulo.
namespace usb_cdc_host {
struct Info {
    bool installed = false;         // la USB Host Library arrancó
    bool open = false;              // hay un CDC abierto y listo
    uint16_t vid = 0, pid = 0;      // del último dispositivo abierto
    uint32_t sessions = 0;          // CDC abiertos desde el arranque
    uint32_t refused = 0;           // dispositivos sin interfaz CDC (teclado, memoria...)
    uint32_t rxDropped = 0;         // bytes recibidos sin sitio (el bucle no leyó a tiempo)
    uint32_t txDropped = 0;         // escrituras rechazadas por falta de sitio
    uint32_t transferErrors = 0;
};

bool begin();
// Cambia cada vez que se abre un CDC: quien lee reinicia su demultiplexor y su saludo.
uint32_t session();
bool open();
size_t read(uint8_t* out, size_t capacity);
// Encola `data` entera o nada: una trama nunca sale partida ni mezclada con otra.
bool write(const uint8_t* data, size_t length);
Info info();
}  // namespace usb_cdc_host
