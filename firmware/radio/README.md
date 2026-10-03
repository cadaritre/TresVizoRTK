# Firmware del módulo de radio LoRa

Aparato aparte del MeridianV: un ESP32-S3 con una **Ebyte E22-900M30S** (SX1262 + amplificador,
hasta 30 dBm a 915 MHz). Diseño, protocolos y pendientes en
[`docs/radio/RADIO_MODULE.md`](../../docs/radio/RADIO_MODULE.md).

```bash
cd firmware/radio
~/.platformio/penv/bin/pio run                 # compila
~/.platformio/penv/bin/pio run -t upload       # carga por USB
```

## Qué hace

- **Bluetooth** «TresVizo Radio XXXX»: la app le pasa la red y la contraseña del Wi-Fi de su
  MeridianV (por omisión, las de fábrica: `MeridianV` / la del README del firmware) y puede
  cambiar red, canal y potencia. La contraseña se escribe pero nunca se lee de vuelta.
- **Wi-Fi**: se une a la red propia del MeridianV y abre TCP a su puerta de enlace
  (`192.168.4.1:2102`). Si se corta, reintenta cada pocos segundos.
- **Papel**: lo decide el MeridianV según su modo. En **base** transmite el RTCM que le llega
  (tira lo que lleve más de 2 s esperando); en **rover** escucha, rearma el RTCM con el parser
  RTCM3 y entrega al MeridianV solo tramas con CRC válido.
- **Estado** cada segundo al MeridianV y a la app: papel, red, canal, potencia, RSSI y SNR del
  último paquete, paquetes enviados, recibidos, perdidos y de otras redes.

## Cableado (por confirmar con la placa real)

Los pines viven en `platformio.ini` (`-DRADIO_PIN_*`): si la placa es otra, se cambian ahí.

| E22-900M30S | ESP32-S3 | Nota |
| --- | --- | --- |
| VCC | 5 V | A 1 W consume ≈650 mA transmitiendo: no la alimentes del 3V3 de la placa |
| GND | GND | |
| SCK | GPIO 12 | SPI |
| MISO | GPIO 13 | SPI |
| MOSI | GPIO 11 | SPI |
| NSS | GPIO 10 | Selección del SPI |
| BUSY | GPIO 9 | |
| DIO1 | GPIO 8 | Aviso de paquete recibido o enviado |
| NRST | GPIO 7 | Reinicio del SX1262 |
| TXEN | GPIO 6 | Conmutador de antena: emitir |
| RXEN | GPIO 5 | Conmutador de antena: recibir |
| ANT | — | Antena de 915 MHz **siempre conectada antes de encender**: transmitir sin antena daña el amplificador |

El TCXO de la E22 se alimenta por DIO3 a 1.8 V (`RADIO_TCXO_VOLTS`), según Ebyte; por
confirmar con la hoja de datos del lote.

## Sin probar

Nada se ha probado con hardware: compila, y la lógica del aire y del enlace está probada en
el host (`firmware/esp32/test/radio_air_test.cpp`, `radio_link_test.cpp`). Falta: que la E22
arranque con estos pines y este TCXO, potencia real a la salida, alcance, y una base y un rover
de punta a punta.
