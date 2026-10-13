# Auditoría final de lógica del firmware (MeridianV y MeridianVI)

13-10-2026. Revisión de punta a punta de los tres firmwares terminados:

- **MeridianV**, repositorio TresVizoRTK (`main`): `firmware/esp32`, entornos `esp32s3_usb`
  (Thing Plus) y `meridianv_v03` (placa v0.3 fabricada, 97000ef), y `firmware/radio` (radio LoRa
  externo por el USB-C).
- **MeridianVI**, repositorio MeridianVI (`main`): `firmware/esp32`, entorno `meridianvi`
  (LG290P, E22 integrado, BQ25798 con LiFePO4, MAX17260, Hall y latch, IIM-42652).

Este documento es el mismo en los dos repositorios; cada hallazgo dice a cuál toca. Se buscó lo que
no cubrían las auditorías anteriores (`firmware-audit-meridianvi.md`, `docs/connectivity/*`,
`board-v03-bringup.md`, `gnss-lg290p.md`, `power-meridianvi.md`, `docs/radio/*`). **No hay
hardware**: todo se comprobó leyendo el código, con pruebas nativas en la Mac y compilando.

## Resumen

| Severidad | Hallazgos | Corregidos |
| --- | --- | --- |
| Alta | 0 | — |
| Media | 7 (M1–M7) | 5 (M1–M5) |
| Baja | 13 (B1–B13) | 0 (documentados) |
| Banco | 9 (K1–K9) | — |

Lo genérico se cambió igual en los dos repositorios (`config_rules.h`, `instrument.cpp`,
`gnss_control.cpp` del UM980 y sus pruebas). La verificación independiente de los pines de la v0.3
no encontró ninguna diferencia (tabla al final).

## Hallazgos de severidad media

### M1 · Corregido · MeridianVI · el LG290P se reencendía sin su segundo apagado

- **Dónde:** `src/gnss_receiver.cpp:237` (antes encendía GNSS_PWR_EN sin esperar).
- **Escenario:** cualquier reinicio del ESP32 (OTA, `/api/restart`, watchdog, salida de «solo
  carga» con `ESP.restart()`). GNSS_PWR_EN (GPIO46) tiene 100 kΩ a GND: el reset apaga el LG290P y
  `gnss_receiver::begin` lo volvía a encender unos cientos de ms después.
- **Efecto:** la spec §17 pide **≥ 1 s apagado** antes de volver a encender (Quectel pide que el MCU
  controle VCC). Con menos, el módulo puede no reiniciarse limpio. Además, GPIO43 (U0TXD) queda en
  alto desde la ROM: por los 470 Ω alimentaba RXD2 del LG290P apagado durante todo ese tiempo.
- **Corrección:** `lg290p::powerOnWaitMs` (`lib/gnss/src/lg290p_protocol.h`) da lo que falta
  hasta 1 s desde el arranque (esp_timer, que empieza después del reset: la espera queda por
  exceso) y `gnss_receiver::begin` lo espera antes de encender. `power_manager_meridianvi.cpp`
  pone, lo primero, GNSS_PWR_EN en bajo y GPIO35 y GPIO43 como entradas hasta que se abre la UART.
  Tras un arranque por imán (que ya espera 1 s) no hay espera nueva; tras un reinicio, ~0.5 s más
  de arranque. **Prueba:** `test/lg290p_protocol_test.cpp`.

### M2 · Corregido · MeridianVI · el I2C de la IMU seguía activo en el SPI del radio

- **Dónde:** `src/imu.cpp:52` (antes solo leía WHO_AM_I).
- **Escenario:** la IIM-42652 comparte SCK/MOSI/MISO con la E22. La spec §17 y `gpio_map.csv`
  (GPIO14) piden «deshabilitar I2C/I3C de la IMU al arrancar»; el firmware no lo hacía.
- **Efecto:** con su I2C activo, la IMU puede tomar el tráfico SPI del radio (SCK = SCL, MOSI =
  SDA) por una trama I2C y tirar de MOSI para contestar: órdenes corrompidas al SX1262
  (frecuencia, potencia, paquetes).
- **Corrección:** `include/icm426xx.h`: INTF_CONFIG0 (0x4C) UI_SIFS_CFG = 11 (I2C deshabilitado)
  con lectura, escritura de solo esos dos bits y relectura, solo si WHO_AM_I es 0x6F o 0x47.
  Fuente: el controlador de InvenSense para la familia en Linux (`inv_icm42600`), que en SPI hace
  exactamente esto. `subsystems.imu.i2c_disabled` (aditivo) dice si quedó. El I3C (registros del
  banco 1) no se tocó: queda para banco (K6). **Prueba:** `test/icm426xx_test.cpp` (nueva).

### M3 · Corregido · MeridianVI (herramienta) · el cargador USB grababa la cabecera en QIO

- **Dónde:** `tools/flasher/meridian_flasher.py:73`.
- **Escenario:** «Instalación completa» de un MeridianVI con el cargador gráfico.
- **Efecto:** pasaba `--flash_mode qio`; esptool reescribe la cabecera del segundo cargador y la ROM
  tendría que leerlo en QIO. `pio run -t upload` (platform-espressif32 6.12.0,
  `_get_board_flash_mode`) usa **dio** para los entornos qio, igual que el modelo de la v0.3 del
  MeridianV; el segundo cargador es el que pasa la flash a QIO. Con una flash sin el bit QE puesto,
  el módulo puede no arrancar tras la primera carga.
- **Corrección:** `dio`, como el entorno. **Prueba:** `tools/flasher/test_meridian_flasher.py`.

### M4 · Corregido · los dos · el Wi-Fi volvía a encenderse apagándose o en «solo carga»

- **Dónde:** `src/instrument.cpp:981-1028` (TresVizoRTK) y `:980-1027` (MeridianVI); regla en
  `include/config_rules.h` (`stationWorkAllowed`, `startStationScan`).
- **Escenario:** MeridianVI con USB al que se le pide apagar (queda en «solo carga», que hace
  `WiFi.mode(WIFI_OFF)`, spec §17.5) o MeridianV en «sigue alimentado», con redes guardadas.
- **Efecto:** el bucle de reconexión seguía escaneando (`WiFi.scanNetworks` enciende la STA) y
  uniéndose cada 30 s–4 min: el equipo «apagado» volvía a emitir y a gastar mientras carga.
- **Corrección:** con `power_manager::pending()` no se escanea, no se une tras un escaneo ni
  ejecuta una conexión diferida (desconectar sí). **Prueba:** `test/config_rules_test.cpp`.

### M5 · Corregido · los dos (UM980) · la única lectura del modo al arrancar podía salir antes de que el receptor hablase

- **Dónde:** `src/gnss_control.cpp:41-45` y `:458` (copia del UM980 en los dos repositorios).
- **Escenario:** placa v0.3: el ESP32 enciende el 5 V de la carrier (GPIO45) en cada arranque, así
  que el UM980 arranca a la vez. La reconciliación del arranque salía a los 5 s pasara lo que pasara
  y no se repite.
- **Efecto:** si el UM980 tarda en contestar, la reconciliación termina `partial_or_unknown`, el
  equipo no se sabe rover ni base (`receiver_role` `unknown`), no hay autoconexión NTRIP
  (`ntrip_input.cpp:321` exige `isRover()`) y el radio externo queda en `idle` (sin RTCM) hasta que
  alguien pregunte.
- **Corrección:** la lectura espera, desde los 5 s, a haber oído una GGA (válida o no) del
  receptor, o a los 20 s si no habla; como ya hace el controlador del LG290P. **Prueba:**
  `test/gnss_priority_integration_test.cpp` (los dos repositorios).

### M6 · Documentado · MeridianVI (hardware en diseño) · un firmware equivocado habilita la carga a 4.2 V

- **Escenario:** cargar por USB en una placa MeridianVI la imagen de la Thing Plus (es el
  `default_envs` de `firmware/esp32/platformio.ini` en los dos repos: un `pio run -t upload` sin
  `-e`) o la de la v0.3. Las dos ponen **GPIO45 en alto** nada más arrancar
  (`board_profile.h:25` regulador Qwiic; `board_profile_v03.h:67` 5 V del GNSS), y en el MeridianVI
  GPIO45 es CHG_EN: CE baja y el BQ25798 carga la LiFePO4 con sus valores de fábrica (VREG 4.2 V,
  1 A). Ninguno de esos firmwares escribe en el cargador (la v0.3 usa otro bus I2C; la Thing Plus
  usa el mismo, GPIO8/9, pero solo lee el medidor en 0x36 y la OLED).
- **Efecto:** solo lo para la protección de cada portapilas (HY2112-CB, 3.75 V), la «última
  barrera» de la spec §5.1.
- **Recomendación (hardware, la placa está en pausa de layout):** mover CHG_EN a un GPIO que ningún
  otro firmware de TresVizo maneje. GPIO46 no lo usan ni la Thing Plus ni la v0.3: basta con
  intercambiar CHG_EN (45) y GNSS_PWR_EN (46); un firmware equivocado solo encendería el GNSS. En
  firmware, además, cambiar `default_envs` del repositorio MeridianVI a `meridianvi` (no se hizo:
  `run_native.py` toma ArduinoJson de `.pio/libdeps/esp32s3_usb`).

### M7 · Documentado · MeridianVI · «rover» reinicia el LG290P aunque ya sea rover

- **Dónde:** `src/gnss_control_lg290p.cpp:590`.
- **Efecto:** cada `POST /api/gnss/control {"action":"rover"}` guarda y reinicia el módulo
  (`PQTMSRR`): se pierde el fijo RTK durante el arranque y la reconvergencia. Con el UM980 la misma
  orden no reinicia nada (paridad de comportamiento). `applyBase` ya evita el cambio de papel si el
  módulo es base.
- **Por qué no se tocó:** saltarlo depende de qué devuelve `PQTMCFGRCVRMODE,R` entre escritura y
  reinicio (pendiente de banco 3 de `gnss-lg290p.md`). Tras ese banco, hacer como `applyBase`:
  si la última lectura fue rover, solo leer el papel y configurar las salidas.

## Hallazgos de severidad baja (documentados)

| # | Firmware | Dónde | Escenario y efecto | Propuesta |
| --- | --- | --- | --- | --- |
| B1 | MeridianVI | `power_manager_meridianvi.cpp:203` | La espera del ADC del cargador (2 s) se cuenta desde que se pidió apagar, no desde `kWaitRelease`. Si cerrar la microSD tarda más de 2 s y se suelta el imán antes de la siguiente pasada del bus, se corta con el ADC encendido (540 µA del pack con el equipo apagado). | Marcar la hora al entrar en `kWaitRelease`. |
| B2 | los dos | `power_manager_v03.cpp:109`, `power_manager_meridianvi.cpp:195` | Si la microSD se cuelga dentro de un `write`/`close`, el apagado espera para siempre. En la v0.3 queda el reset de 10 s del botón; el MeridianVI (IP67, sin reset accesible) no se puede apagar hasta agotar la batería. | Plazo (p. ej. 15 s) y corte con `shutdown_reason` que lo diga; decisión del propietario por la regla del cierre de archivos. |
| B3 | MeridianV | `radio_module.cpp:296-302` | Dos `POST /api/radio` antes de que la tarea USB mande el primero: el segundo sustituye al primero entero; las claves del primero no llegan al radio, y su `config_seq` nunca se confirma. Si la escritura por USB falla, `config_state` queda `pending` mientras dure el enlace. | Fusionar las claves pendientes; reenviar si no hay `config_ack` en 2 s. |
| B4 | MeridianV | `usb_channel.cpp:40` | Si el demultiplexor suelta dos líneas en la misma pasada (tras abandonar una trama binaria a medias), la segunda pisa `line` con `linePending` ya en verdadero. Solo con una computadora que mande basura binaria. | Descartar la línea si ya hay una pendiente. |
| B5 | MeridianVI | `gnss_control_lg290p.cpp:319` | El `PQTMSAVEPAR` del paso a 921 600 guarda también las demás correcciones de la reconciliación (tasas, FIXRATE) y el resumen dice «se guarda solo la velocidad». Inocuo (son las del producto), pero el texto no es exacto. | Corregir el texto o reordenar para guardar antes de corregir. |
| B6 | los dos | `firmware_update.cpp:270` | El rechazo por placa dice «Se requiere firmware de Thing Plus ESP32-S3» también en la v0.3 y el MeridianVI. | Usar `board_profile::kName`. |
| B7 | MeridianVI | `lora_radio.cpp:321` | Paridad con el radio externo: el integrado contesta 400 a `power_dbm` 28–30 (el externo los acepta y recorta a 27 con `power_limited`), no publica `max_power_dbm` arriba (solo en `air_profile`) ni `config_seq`/`config_state`. Está así en el contrato del MeridianVI. | Decidir un solo comportamiento para las apps (avisar en COORDINACION-AGENTES.md antes de tocar el contrato). |
| B8 | MeridianVI | `instrument.cpp`, `gnss_receiver.h` | Paridad: la v0.3 publica `subsystems.gnss.power_on`, `power_gpio` y `pps_gpio`; el MeridianVI también enciende el GNSS por GPIO y tiene PPS, pero no los publica. | Añadirlos (aditivo). |
| B9 | los dos | `correction_router.cpp:46` | `adoptRadio` mira y luego selecciona: si el usuario elige otra fuente justo entre las dos cosas, el radio se la quita. Ventana de microsegundos al pasar a rover. | `compare_exchange` sobre `selected`. |
| B10 | radio (MeridianV) | `firmware/radio/src/main.cpp:97` | `packetArrived` lo pone también el fin de emisión en base; al pasar a rover se lee un paquete que no existe (cuenta como malformado). | Borrarlo en `applyAirRole`. |
| B11 | MeridianVI | `board_profile_meridianvi.h:53,75` | Comentarios viejos: «el firmware NO habilita la carga» (ya la habilita, con el supervisor) y «Hall push-pull, sin pull» (es de drenador abierto con 100 kΩ a +3V3 por D403; el código es correcto). | Corregir los comentarios. |
| B12 | MeridianVI | `power_manager_meridianvi.cpp:127` | Enchufar el USB con el equipo apagado lo enciende entero (`usb_or_reset`), no en «solo carga». La spec §17.2 distingue el motivo pero no dice qué hacer. | Decisión del propietario. |
| B13 | los dos | `memory_health.cpp:29` | `stack_free_min_bytes` no incluye las tareas nuevas `usb_link` (MeridianV) y `lora` (MeridianVI). | Añadirlas (aditivo). |

## Paridad entre los dos firmwares

Iguales byte a byte: `ntrip_input`, `ble_transport`, `telemetry_ws`, `correction_output`,
`correction_router`, `sd_recorder`, `base_survey`, `firmware_update`, `cancellable_connection`,
`gnss_sky`, `gnss_visible`, `memory_health`, `device_identity.h`, `config_rules.h` y el controlador
del UM980 (salvo el `#ifndef` que lo deja fuera del entorno `meridianvi`). `instrument.cpp` difiere solo en lo de cada placa (IMU, antena, GPIO del GNSS). Las
demás diferencias son de hardware (cargador, medidor, botón, LG290P, radio integrado o externo) o
están arriba (B7, B8). Nota: el entorno `esp32s3_usb` del repositorio MeridianVI es un MeridianV
anterior al enlace USB del radio (radio por Wi-Fi, radio 0.1.0); el MeridianV vigente es el de
TresVizoRTK.

## Revisado sin hallazgos nuevos

- **Cargador v0.3:** solo escribe SFET_PRESENT, WATCHDOG e ICHG (≤ 1.5 A); comprueba PN y VREG =
  4.2 V antes; HIZ con el radio enlazado, reaplicado cada segundo y quitado solo si lo puso el
  firmware; modo *ship* solo sin VBUS y con el botón suelto. Registros y bits contrastados con el
  mapa del BQ25798 (REG0F, REG10, REG11, REG14, REG1B-1D, REG48).
- **Cargador MeridianVI:** CE solo sube tras escribir y releer en el mismo paso; VREG, VSYSMIN,
  WATCHDOG y STOP_WD_CHG verificados cada segundo; JEITA, TS, VRECHG, IPRECHG, ITERM, IINDPM por CC
  y ADC con los campos de REG00-REG2E. Nunca se carga con 4.2 V salvo el caso M6.
- **MAX17260:** registros, LSB (78.125 µV, 1.5625 µV/Rs, 5 µVh/Rs, 1/256 °C, 5.625 s), orden de
  bytes y secuencia EZ (ver K5).
- **Umbrales de batería baja:** v0.3 3.45 V 60 s sin USB; MeridianVI 0 % o 2.90 V 5 s sin USB.
- **OTA firmada:** cada entorno lleva su `hardware_id` en la imagen firmada y se comprueba tras la
  firma; el cargador conoce las tres identidades.
- **Correcciones:** una sola fuente activa, la elección del usuario guardada; el radio solo se
  adopta si nadie eligió otra cosa; colas por bytes con caducidad de 2 s; el MeridianVI escribe las
  correcciones por la UART2 del LG290P sin esperar a las órdenes.
- **Alturas:** UM980 con `UNDULATION 0.0000` y LG290P sumando la separación de la GGA: elipsoidal
  en los dos, también en el promedio de base y la coordenada ECEF.
- **Concurrencia:** cerrojos y atómicos de los estados compartidos, un solo dueño de Wire, el
  demultiplexor USB, la cola de la base hacia el radio y los `millis()` con resta sin signo
  (las comparaciones absolutas que quedan solo valen en el primer arranque).

## Verificación independiente de los pines de la v0.3

Sin usar `check_v03_pins.py`: se extrajo `hardware/main-board/kicad` de **97000ef** con
`git archive` a la carpeta temporal de la sesión, se exportó el netlist con **kicad-cli 10.0.6**
(`sch export netlist`) y se leyó con un analizador propio de S-expresiones. Resultado:

- El netlist exportado es igual al guardado (`tresvizo-main.net`) salvo fecha y ruta.
- **Esquema contra PCB:** las 117 huellas y todos sus pads tienen la misma red en el
  `.kicad_pcb` del pedido que en el esquema (0 diferencias).
- **Símbolo y huella de U201:** pines 1-41 contra la tabla de pines del ESP32-S3-WROOM-1
  (1 GND, 2 3V3, 3 EN, 4-7 IO4-7, 8 IO15 … 39 IO1, 40-41 GND); en la huella, 1-14 a la izquierda,
  15-26 abajo y 27-40 a la derecha, paso de 1.27 mm. Coinciden.
- Después, cada red de U201 hasta su otro extremo y contra `board_profile_v03.h` y lo que hace el
  firmware con el pin:

| GPIO | U201 | Red | Llega a | Perfil | Firmware y polaridad | ✓ |
| --- | --- | --- | --- | --- | --- | --- |
| 8 | 12 | GNSS_TX_MCU | R304 1 kΩ → J301.3 (RXD2 de la carrier), ESD U302 a +3V3 | `TRESVIZO_GNSS_TX` | TX de UART2 a 115200, abierta tras encender el 5 V | ✓ |
| 9 | 17 | GNSS_TXD2_MCU | R305 100 Ω ← J301.4 (TXD2) | `TRESVIZO_GNSS_RX` | RX de UART2 | ✓ |
| 10 | 18 | GNSS_PPS_MCU | R306 100 Ω ← J301.5, ESD U303 | `kGnssPps` | Entrada, sin uso | ✓ |
| 11 | 19 | GNSS_EVENT_MCU | R307 1 kΩ → J301.6; R308 100 kΩ a GND | `kGnssEvent` | No se toca (estado de reset): EVENT queda en bajo por R308 | ✓ |
| 12 | 20 | GNSS_RESET_MCU | R309 1 kΩ → J301.7 | `kGnssReset` | Entrada (alta impedancia) | ✓ |
| 45 | 26 | GNSS_PWR_EN | EN del TPS63070 (U301.14); R301 100 kΩ a GND | `kGnssPowerEnable` | Salida en alto en `gnss_receiver::begin`; en el reset, bajo → VDD_SPI a 3.3 V | ✓ |
| 13 | 21 | I2C_SDA | J403.4, BQ25798 SDA (U102.15), MAX17048 SDA (U103.8); R204 4.7 kΩ | `kSda` | Wire a 100 kHz (tarea `oled`) | ✓ |
| 14 | 22 | I2C_SCL | J403.3, U102.14, U103.7; R205 4.7 kΩ | `kScl` | Wire | ✓ |
| 6 | 6 | SD_CLK | J401.5 (CLK), sin resistencia | `kSdClock` | SD_MMC CLK | ✓ |
| 7 | 7 | SD_CMD | J401.3; R401 10 kΩ a +3V3 | `kSdCommand` | SD_MMC CMD | ✓ |
| 5 | 5 | SD_D0 | J401.7; R402 a +3V3 | `kSdD0` | SD_MMC D0 | ✓ |
| 4 | 4 | SD_D1 | J401.8; R403 a +3V3 | `kSdD1` | SD_MMC D1 | ✓ |
| 16 | 9 | SD_D2 | J401.1; R404 a +3V3 | `kSdD2` | SD_MMC D2 | ✓ |
| 15 | 8 | SD_D3 | J401.2; R405 a +3V3 | `kSdD3` | SD_MMC D3 | ✓ |
| 17 | 10 | SD_DET | Drenador de Q401 (AO3401A: G = SD_CD_N con R406 a +3V3, S = +3V3); R407 100 kΩ a GND | `kSdDetect`, activo alto, sin pull | Entrada; alto = tarjeta | ✓ |
| 18 | 11 | BTN_SENSE_N | Ánodo de D402 (cátodo en BTN_N = SW401 y QON del BQ25798); R408 10 kΩ a +3V3 | `kPowerButton` | Entrada, activo bajo, 2 s = apagar | ✓ |
| 48 | 25 | LED_STATUS | R409 330 Ω → ánodo de D403, cátodo a GND | `kStatusLed` | Salida, activo alto | ✓ |
| 21 | 23 | CHG_INT_N | INT del BQ25798 (U102.21); R108 10 kΩ a +3V3 | `kChargerInt` | Entrada, sin uso (sondeo cada 1 s) | ✓ |
| 47 | 24 | FG_ALRT_N | ALRT del MAX17048 (U103.5); R113 10 kΩ | `kGaugeAlert` | Entrada, sin uso | ✓ |
| 41 | 34 | IMU_SDA | BMI088 SDI/SDA (U401.9); R411 4.7 kΩ | `kImuSda` | Wire1 a 400 kHz | ✓ |
| 42 | 35 | IMU_SCL | U401.8; R412 4.7 kΩ | `kImuScl` | Wire1 | ✓ |
| 2 | 38 | IMU_INT1 | INT1 del acelerómetro (U401.16), sin pull | `kImuInt1` | Entrada con pull-down interno | ✓ |
| 1 | 39 | IMU_INT3 | INT3 del giróscopo (U401.12), sin pull | `kImuInt3` | Entrada con pull-down interno | ✓ |
| 19 | 13 | USB_DN | J101 A7/B7, USBLC6 U101 (I/O1), TP207 | `kUsbDm` | USB-Serial/JTAG | ✓ |
| 20 | 14 | USB_DP | J101 A6/B6, U101 (I/O2), TP206 | `kUsbDp` | USB-Serial/JTAG | ✓ |
| 43 | 37 | ESP_TXD0 | TP208 | `kConsoleTx` | No se usa (ROM) | ✓ |
| 44 | 36 | ESP_RXD0 | TP209 | `kConsoleRx` | No se usa | ✓ |
| 0 | 27 | ESP_BOOT | R202 10 kΩ a +3V3, SW202 a GND | — | No se toca (arranque desde flash) | ✓ |
| 3 | 15 | ESP_IO3 | R203 10 kΩ a GND | — | No se toca | ✓ |
| 46 | 16 | (al aire) | — | — | No se toca (pull-down interno) | ✓ |
| 35-37 | 28-30 | ESP_IO35-37 | TP203-TP205 | — | Libres (PSRAM quad) | ✓ |
| 38-40 | 31-33 | (al aire) | — | — | Libres | ✓ |

Periféricos del otro extremo, contra sus hojas: MAX17048 (TDFN-8: 5 ALRT, 7 SCL, 8 SDA),
AO3401A (1 G, 2 S, 3 D), microSD (1 DAT2, 2 DAT3, 3 CMD, 4 VDD, 5 CLK, 6 VSS, 7 DAT0, 8 DAT1),
USBLC6-2SC6 (riel a +3V3), BMI088 (PS y CSB1 a VDDIO → I2C; SDO1 y SDO2 a GND → 0x18 y 0x68),
BQ25798 en 0x6B con PROG 4.7 kΩ (1S), CE a GND y FET de envío Q101, OLED en J403 (1 +3V3, 2 GND,
3 SCL, 4 SDA). Direcciones I2C sin choque (0x3C/0x3D, 0x36, 0x6B; 0x18 y 0x68 en Wire1).

**Resultado: 32 filas ✓, ninguna ✗.** Coincide con lo que dice `check_v03_pins.py` (193
comprobaciones, cumple, también con `--kicad`). Los riesgos de la placa siguen siendo los de
`board-v03-bringup.md` (orden VCC/GND de la OLED, GNSS apagado en cada reinicio, margen del botón,
INT3 en drenador abierto, reloj de la microSD sin resistencia).

## Builds y pruebas (13-10-2026, tras los cambios)

| Qué | Resultado |
| --- | --- |
| `pio run -e esp32s3_usb` (TresVizoRTK) | Compila sin avisos; 1 749 613 B (89.0 % de 1 966 080) |
| `pio run -e meridianv_v03` | Compila; 1 754 721 B |
| `pio run -d firmware/radio` (TresVizoRTK) | Compila; 383 793 B |
| `pio run -e meridianvi` | Compila; 1 803 121 B (≈ 163 KB por debajo de 1 966 080) |
| `pio run -e esp32s3_usb` y `-d firmware/radio` (MeridianVI) | Compilan |
| `run_native.py` | TresVizoRTK 42 suites, MeridianVI 45 suites (nueva `icm426xx_test`), en verde |
| `check_contract.py` | TresVizoRTK 751 comprobaciones, MeridianVI 731: cumplen |
| Pruebas del contrato y del cargador USB (`unittest`) | En verde en los dos |
| `check_v03_pins.py` (y `--kicad`, y sus pruebas) | 193 comprobaciones, cumple. El repositorio MeridianVI no tiene comprobador de la v0.3 |

**Sin probar en equipo:** todo lo de este documento.

## Pendiente de banco

| # | Qué medir | Por qué |
| --- | --- | --- |
| K1 | Que el LG290P mande `$PQTMVER` al arrancar tras `PQTMSRR` | Todo cambio de papel y de constelaciones depende de verlo en 8 s; si no lo manda, rover y base terminan `partial_or_unknown` |
| K2 | Cuánto tarda el UM980 en contestar tras encender su 5 V (v0.3) | M5 espera hasta 20 s; anotar el tiempo real |
| K3 | Que la IIM-42652 acepte UI_SIFS_CFG = 11 y el estado de su I3C (banco 1, INTF_CONFIG6) | M2 sale del controlador de la familia; confirmar con DS-000440 |
| K4 | VCC del LG290P bajo 100 mV durante el segundo apagado | M1 |
| K5 | MAX17260: ModelID en ModelCFG[7:4], orden de bytes y si la guía EZ vigente pide dQAcc/dPAcc | `max17260.h` no los escribe |
| K6 | Que la ROM y el arranque del ESP32 por U0TXD (115 200) no le hagan nada al LG290P por RXD2 | spec §19 |
| K7 | Con el radio externo, latencia de una escritura del MeridianV múltiplo de 64 B | El anfitrión del radio pide IN de 512 B y termina con un paquete corto: sin ZLP del USB-Serial/JTAG, esa escritura espera a la siguiente (≤ 1 s, el latido) |
| K8 | Polaridad del contacto de detección del TF-015 (v0.3) | SD_DET alto con tarjeta solo si CD cierra a GND con tarjeta |
| K9 | Lo de las auditorías anteriores sigue pendiente: VBUS del radio, HIZ real, ship, carga, C/N0 con la microSD, watchdog en sesiones largas | `board-v03-bringup.md`, `USB_LINK.md` §12, `power-meridianvi.md` |
