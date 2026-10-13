# Firmware del módulo de radio LoRa

Aparato aparte del MeridianV, con su propia pila: un ESP32-S3 con una **Ebyte E22-900M30S**
(SX1262 + amplificador, hasta 30 dBm a 915 MHz; este firmware la limita a 27 dBm). Se
conecta al USB-C del MeridianV, del que es el **anfitrión USB**. Diseño en
[`docs/radio/RADIO_MODULE.md`](../../docs/radio/RADIO_MODULE.md) y protocolo del cable en
[`docs/radio/USB_LINK.md`](../../docs/radio/USB_LINK.md).

```bash
~/.platformio/penv/bin/pio run -d firmware/radio               # compila
~/.platformio/penv/bin/pio run -d firmware/radio -t upload     # carga por el puerto UART
python3 tools/firmware_tests/run_native.py                     # pruebas nativas (con las del MeridianV)
```

## Qué hace

- **USB-C anfitrión** (`src/usb_cdc_host.cpp`): abre el CDC del MeridianV (su USB-Serial/JTAG)
  con DTR = RTS = 0 y lo saluda (`hello`). Hasta que el MeridianV contesta `welcome` no
  transmite ni entrega nada; luego le manda su estado cada segundo y sigue el papel (`role`)
  que el MeridianV le repite cada segundo. Sin latido 3.5 s, o al desconectarlo, vuelve a
  `idle` y duerme la radio.
- **Papel**: lo decide el MeridianV según su modo. En **base** transmite el RTCM crudo que le
  llega por el cable (tira lo que lleve más de 2 s esperando); en **rover** escucha, rearma el
  RTCM con el parser RTCM3 (`feedAt`: CRC-24Q y la regla de 1 s) y entrega al MeridianV solo
  tramas válidas, crudas.
- **Ajustes** (red, canal, potencia) en su NVS. Los cambia el MeridianV con `config` (que le
  llega de las apps por `/api/radio`) y el radio contesta `config_ack` con lo que aplicó.
  **Potencia: 27 dBm de tope y por omisión** (IFT-008-2015): lo que pase se recorta y se
  avisa. Al arrancar borra la red Wi-Fi y la contraseña que guardaba la 0.1.0.
- **Estado** cada segundo: papel, red, canal, potencia, RSSI y SNR del último paquete,
  paquetes enviados, recibidos, perdidos y de otras redes, tramas por el aire, pila
  (`battery_mv`, si la placa la mide) y diagnóstico del USB.
- **Consola de depuración** por UART0 a 115200: arranque, conexiones, enlace, papel y
  ajustes.

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

| USB y energía | ESP32-S3 | Nota |
| --- | --- | --- |
| USB-C «MeridianV»: D− / D+ | GPIO 19 / GPIO 20 | USB nativo como anfitrión. **Sin VBUS hacia el MeridianV**, Rp de 36 kΩ a 3V3 en CC1 y CC2, ESD con riel a 3V3 (USB_LINK.md §9) |
| USB-C «Carga» | UART0 (GPIO 43/44) por un puente USB-UART | Carga de la pila, firmware y consola |
| Pila (opcional) | `RADIO_PIN_VBAT` | Por un divisor (`RADIO_VBAT_DIVIDER`); -1 = sin medir |

El TCXO de la E22 se alimenta por DIO3 a 1.8 V (`RADIO_TCXO_VOLTS`), según Ebyte; por
confirmar con la hoja de datos del lote.

## Sin probar

Nada se ha probado con hardware: compila sin avisos y el entramado del cable y el saludo están
probados en el host (`test/radio_usb_test.cpp`, `test/usb_session_test.cpp`); la lógica del
aire, en `firmware/esp32/test/radio_air_test.cpp`. Falta: que la USB Host Library abra el CDC
del MeridianV, que la E22 arranque con estos pines y este TCXO, potencia real a la salida,
alcance, y una base y un rover de punta a punta. El MeridianV aún no habla este enlace
(fase 2).
