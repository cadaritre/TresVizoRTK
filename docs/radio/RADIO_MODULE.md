# Módulo de radio LoRa

El radio del MeridianV **no va dentro del equipo**: es un aparato aparte, que se vende por
separado, con su propio ESP32 y **su propia pila**. Se conecta con un cable USB-C al puerto
USB-C del MeridianV y por ese cable entran y salen las correcciones. Decisiones del
propietario del 02-10-2026 (radio aparte) y del 12-10-2026 (enlace por USB-C en lugar del
Wi-Fi del MeridianV y sin alta por Bluetooth).

| | |
| --- | --- |
| Placa | ESP32-S3 + **Ebyte E22-900M30S** (SX1262 + amplificador, hasta 30 dBm = 1 W; versión SPI «M»). Elegida por alcance frente a la Heltec LoRa 32 V3 (≈22 dBm). El firmware la limita a **27 dBm** (IFT-008-2015) |
| Banda | **915 MHz** (902–928 MHz, libre en México) |
| Papel | **Los dos sentidos**: si su MeridianV está en base, transmite el RTCM; si está en rover, lo recibe y se lo entrega |
| Enlace con el MeridianV | **USB-C**: el radio es el anfitrión USB y el MeridianV el dispositivo CDC de siempre. Protocolo en [USB_LINK.md](USB_LINK.md) |
| Configuración | Desde las apps, por `/api/radio` del MeridianV, que la reenvía por el cable. El radio no usa Wi-Fi ni Bluetooth |

```mermaid
flowchart LR
    subgraph Base
      UM1[UM980 base] -->|RTCM por UART| MV1[MeridianV]
      MV1 -->|USB-C · RTCM crudo| R1[Radio]
    end
    R1 -. LoRa 915 MHz .-> R2[Radio]
    subgraph Rover
      R2 -->|USB-C · RTCM crudo| MV2[MeridianV]
      MV2 -->|fuente «radio» del router| UM2[UM980 rover]
    end
    APP[App] -->|/api/radio: red, canal, potencia| MV2
```

## Por el aire (`firmware/esp32/lib/protocol/src/radio_air.h`)

- **LoRa SF7, 500 kHz, CR 4/5**: ≈21.9 kbit/s brutos. Un paquete de 255 bytes ocupa el aire
  ≈100 ms, así que caben ≈2.5 kB/s. Un RTCM MSM4 de cuatro constelaciones a 1 Hz son
  1–1.5 kB/s: cabe. **MSM7 no cabe**: la base que transmita por radio debe ir en MSM4.
- **13 canales** de 903 a 927 MHz cada 2 MHz; por omisión el 6 (915 MHz). Base y rover en el
  mismo canal.
- **Red** (0–255) en cada paquete: dos bases en el mismo canal no se mezclan; el rover solo
  acepta la suya.
- **Paquete**: `0xA7`, red, secuencia de 16 bits y hasta 251 bytes del flujo RTCM. El rover
  concatena en orden y su parser RTCM3 (CRC-24Q, con reloj: `feedAt`) saca las tramas; un
  paquete perdido solo estropea las que lo cruzaban, y al ver un salto de secuencia se
  reinicia el parser.
- La base espera 25 ms tras el último byte antes de mandar un paquete a medio llenar: junta
  las tramas de una época en menos paquetes.
- **Potencia: 27 dBm de tope y por omisión** en el firmware del radio
  (`firmware/radio/src/radio_config.h`). La IFT-008-2015 (§4.3, modulación digital) limita la
  densidad a 8 dBm en 3 kHz: 30 dBm en ~500 kHz dan ≈7.8 dBm/3 kHz, sin margen para la
  tolerancia de +1 dB del amplificador; 27 dBm dejan 3 dB (mismo criterio que el MeridianVI,
  `MeridianVI/hardware/meridian-vi/research/spec.md` §11.1). La norma tampoco admite controles
  que pasen el límite: un valor mayor que llegue al radio se recorta a 27 y se avisa. El
  SX1262 a +19 dBm da ≈27 dBm a la salida de la E22 (ganancia nominal de 8 dB, por medir).
  `radio_air.h` conserva `kMaxOutputDbm = 30` como capacidad de la E22; el tope legal es el
  del radio.

**Pendiente antes de vender:** medir el ancho de banda a 6 dB (≥ 500 kHz para contar como
modulación digital, §4.3.3) y la densidad espectral del equipo armado, y homologarlo con sus
antenas (§4.1.4; PIRE ≤ 4 W).

## Entre el radio y el MeridianV

Todo en [USB_LINK.md](USB_LINK.md). En resumen: por el mismo CDC del MeridianV viajan las
órdenes JSON de siempre, el RTCM crudo (con su CRC-24Q) y tramas del enlace (`F5 52`, JSON y
CRC-24Q): saludo con versión, papel, estado cada segundo, configuración con su
confirmación. **El radio no da VBUS** al MeridianV: no se descarga cargándolo y el MeridianV
se puede apagar con el radio puesto.

## En el MeridianV

**Pendiente (fase 2).** El firmware del MeridianV todavía tiene el enlace anterior
(`src/radio_module.cpp`: servidor TCP en el puerto 2102 de su red propia) y no habla con
este radio por USB. Lo que cambiará: demultiplexor en el canal USB, fuente y sumidero `radio`
por el cable, reenvío de la configuración, detección del radio, cargador de la v0.3 en HIZ
mientras esté conectado y `link: "usb"` en `/api/radio` y `subsystems.radio` (aditivo).

## En el radio (`firmware/radio/`)

Proyecto de PlatformIO aparte (ESP32-S3, Arduino, RadioLib). Pines de la E22 en
`platformio.ini`, **por confirmar con el cableado real**. El USB-C nativo es el enlace, como
anfitrión; el firmware se carga y la consola se lee por UART0 (puerto «Carga» con puente
USB-UART, ver USB_LINK.md §9). Estado en un LED.

## Estado (12-10-2026)

- **Hecho y compilando**: el firmware 0.2.0 del radio con el enlace USB (`firmware/radio/`),
  con pruebas nativas del entramado y del saludo (`python3 tools/firmware_tests/run_native.py`).
- **Pendiente**: el lado del MeridianV (fase 2).
- **Sin probar con hardware**: no hay radios todavía.

## Lo que falta

- La placa del radio: requisitos de USB-C y energía en USB_LINK.md §9.
- Probarlo con dos radios en campo: alcance, pérdidas, latencia de la corrección.
- Las apps: la pantalla de radio deja el Bluetooth del radio y el alta Wi-Fi; todo va por
  `/api/radio` del MeridianV (estado, red, canal y potencia hasta 27 dBm), y elegir la fuente
  «Radio».
- Medir la ganancia real del amplificador y el consumo a 27 dBm.
