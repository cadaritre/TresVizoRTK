# Placa principal v0.3: firmware y pruebas de banco

12-10-2026. Firmware **0.9.0**, entorno de PlatformIO **`meridianv_v03`** (en `firmware/esp32`).
Es el mismo producto, el **MeridianV**, con la placa principal v0.3 compacta
(`hardware/main-board/`) que se mandó a JLCPCB en el commit **97000ef**. La placa no se toca:
lo que haga falta se resuelve en el firmware o con un parche de banco documentado aquí.

**Estado:** compila y pasa las pruebas en la Mac. **No hay placa todavía: nada de esto se
probó en hardware.** Las pruebas de banco del final son las que faltan.

## Fuente de verdad y comprobación

- Pines: el netlist de la placa del pedido, `hardware/main-board/kicad/tresvizo-main.net` en
  97000ef. Exportado de nuevo con `kicad-cli sch export netlist` (KiCad 10.0.6) desde el esquema
  de ese commit, sale igual línea a línea salvo fecha y ruta. Desde 97000ef solo cambió
  `hardware/main-board/README.md` (texto de la carcasa).
- `research/gpio_map.csv` es de la v0.2 y **no** se usó.
- El perfil del firmware es [`include/board_profile_v03.h`](../firmware/esp32/include/board_profile_v03.h):
  cada pin lleva su red y el pin del módulo U201.
- **Comprobador repetible:** `python3 tools/board_check/check_v03_pins.py` lee el netlist de
  97000ef (por git) y el perfil, y falla si no coinciden un GPIO, una polaridad, una dirección
  I2C o un periférico. Comprueba también:
  - el símbolo del WROOM-1 contra la tabla 3-1 de Espressif;
  - las resistencias en serie hasta J301;
  - pull-ups y pull-downs;
  - el inversor de la detección de la microSD;
  - PROG del cargador (1S) y su FET de envío;
  - PS, CSB1, SDO1 y SDO2 del BMI088;
  - los pines de arranque, la flash y la PSRAM.

  Opciones:
  - `--kicad` exporta el esquema de 97000ef con kicad-cli en una carpeta temporal y avisa si no
    coincide con el netlist guardado;
  - `--markdown` saca la tabla de abajo.

  Pruebas del comprobador: `python3 -m unittest discover -s tools/board_check`. Cambian a
  propósito UART, polaridades, direcciones, pines de arranque y la propia placa, y comprueban
  que el comprobador falla.

## Qué cambia respecto de la Thing Plus

| Tema | Thing Plus (`esp32s3_usb`) | Placa v0.3 (`meridianv_v03`) | En el firmware |
| --- | --- | --- | --- |
| Módulo y flash | MINI-1-N4R2: 4 MB DIO, PSRAM quad 2 MB | WROOM-1-N16R2: 16 MB QIO, PSRAM quad 2 MB (GPIO33-37 libres) | `boards/tresvizo_meridianv_v03.json`, `qio_qspi`. La cabecera de la imagen dice `dio` (PlatformIO lo hace así en el S3; el segundo cargador pone QIO) |
| Particiones | 2 × 1.875 MB | 2 × 4 MB (`partitions_v03.csv`), NVS y otadata en las mismas direcciones | La imagen (1.75 MB) se mantiene bajo 1 966 080 bytes, la cifra que todavía comparan las apps |
| `hardware_id` | `tresvizo-thingplus-s3-4m-v1` | `tresvizo-meridianv-v03-s3-16m-v1` | La OTA rechaza la imagen de la otra placa. `tools/firmware_identity.py`, el cargador USB y el empaquetador la conocen |
| UART del UM980 | RX44 / TX43 | RX9 / TX8 (COM2, 115200) | Perfil |
| 5 V del GNSS | Aparte, siempre encendido | GPIO45 → EN del TPS63070 | `gnss_receiver::begin` lo pone alto **antes** de abrir la UART; `subsystems.gnss.power_on` |
| I2C | SDA8 / SCL9, regulador de periféricos en GPIO45 | SDA13 / SCL14, sin regulador (OLED a +3V3) | `kPeripheralEnable = -1` |
| OLED | SSD1306 derecha | Módulo del propietario (SSD1315 según el anuncio), girado 180° | Se gira el dibujo en el lienzo (`setRotation(2)`), no con comandos del controlador: vale igual para SSD1306 y SSD1315 |
| microSD | CLK38, CMD34, D 39/40/47/33; detección 48 en alto, pull-down interno | CLK6, CMD7, D 5/4/16/15; detección 17 en alto (Q401 invierte), R407 a GND | Misma polaridad; sin pull interno (`kSdDetectInternalPull = false`) |
| Encendido y apagado | Soft Power Switch Mk2: PUSH en GPIO10, OFF en GPIO14 | Botón SW401 a QON del BQ25798 y a GPIO18 por D402; apagado = modo *ship* por I2C | `power_manager_v03.cpp`. En la v0.3, GPIO10 es el PPS y GPIO14 el SCL: el código de la Thing Plus no se compila |
| Cargador | MCP73831 autónomo, sin lectura | BQ25798 en 0x6B | Ver [cargador](#cargador-bq25798) |
| Medidor | MAX17048, 0x36 | MAX17048G+T10, 0x36, VDD desde VPACK (R112; R114 sin montar) | El mismo código (VCELL 0x02 y SOC 0x04) |
| LED | No hay | D403 en GPIO48, activo alto | Fijo en marcha, 1 Hz con batería baja y 4 Hz mientras se apaga |
| IMU | No hay | BMI088 en Wire1 (GPIO41/42), INT1 en GPIO2 e INT3 en GPIO1 | `imu_probe`: lee el identificador de chip al arrancar; sin driver |
| Batería | LiPo 1S 3000 mAh | Pack 1S2P de 18650 Li-ion (5600 mAh según el anuncio, BMS 4.30/2.80 V) | `low_battery` a 3.5 V; apagado ordenado a 3.45 V tras 60 s sin USB |
| Identidad | `model` MeridianV | Igual (`MeridianV`), `capabilities.imu` = `BMI088` | Sigue anunciando «MeridianV» en BLE, SSID y mDNS |

## Pines (netlist de 97000ef)

Generada con `check_v03_pins.py --markdown` y completada con la fuente: el mapa de GPIO de
`hardware/main-board/scripts/circuit.py` (diccionario `esp`, líneas 274-285) y la red en
`kicad/tresvizo-main.net`.

| Red de la placa | GPIO | Pin del módulo | Constante del firmware | Uso en el firmware | Fuente | ✓ |
| --- | --- | --- | --- | --- | --- | --- |
| `GNSS_TX_MCU` | 8 | U201.12 | `TRESVIZO_GNSS_TX` | UART del UM980: TX → RXD2 de la carrier (R304 1 kΩ, J301.3) | circuit.py:279 · .net:11871 | ✓ |
| `GNSS_TXD2_MCU` | 9 | U201.17 | `TRESVIZO_GNSS_RX` | UART del UM980: RX ← TXD2 (R305 100 Ω, J301.4) | circuit.py:280 · .net:11855 | ✓ |
| `GNSS_PPS_MCU` | 10 | U201.18 | `kGnssPps` | PPS (R306, J301.5): entrada, todavía sin uso | circuit.py:280 · .net:11801 | ✓ |
| `GNSS_EVENT_MCU` | 11 | U201.19 | `kGnssEvent` | EVENT (R307, J301.6): no se maneja; R308 de 100 kΩ lo deja en bajo | circuit.py:280 · .net:11780 | ✓ |
| `GNSS_RESET_MCU` | 12 | U201.20 | `kGnssReset` | RESET_N (R309, J301.7): entrada en alta impedancia; la BDLX no lo saca | circuit.py:281 · .net:11839 | ✓ |
| `GNSS_PWR_EN` | 45 | U201.26 | `kGnssPowerEnable` | EN del TPS63070; R301 de 100 kΩ a GND (pin de arranque) | circuit.py:282 · .net:11817 | ✓ |
| `I2C_SDA` | 13 | U201.21 | `kSda` | OLED (J403.4), BQ25798 y MAX17048; R204 4.7 kΩ | circuit.py:281 · .net:11921 | ✓ |
| `I2C_SCL` | 14 | U201.22 | `kScl` | OLED (J403.3), BQ25798 y MAX17048; R205 4.7 kΩ | circuit.py:281 · .net:11887 | ✓ |
| `SD_CLK` | 6 | U201.6 | `kSdClock` | SD_MMC CLK (sin resistencia en serie) | circuit.py:277 · .net:12049 | ✓ |
| `SD_CMD` | 7 | U201.7 | `kSdCommand` | SD_MMC CMD (R401) | circuit.py:277 · .net:12066 | ✓ |
| `SD_D0` | 5 | U201.5 | `kSdD0` | SD_MMC D0 (R402) | circuit.py:277 · .net:12088 | ✓ |
| `SD_D1` | 4 | U201.4 | `kSdD1` | SD_MMC D1 (R403) | circuit.py:277 · .net:12110 | ✓ |
| `SD_D2` | 16 | U201.9 | `kSdD2` | SD_MMC D2 (R404) | circuit.py:278 · .net:12132 | ✓ |
| `SD_D3` | 15 | U201.8 | `kSdD3` | SD_MMC D3 (R405) | circuit.py:278 · .net:12154 | ✓ |
| `SD_DET` | 17 | U201.10 | `kSdDetect` | Detección: HIGH con tarjeta (CD a GND → Q401 canal P), R407 a GND, sin pull interno | circuit.py:278 · .net:12176 | ✓ |
| `BTN_SENSE_N` | 18 | U201.11 | `kPowerButton` | Botón activo bajo (R408 a +3V3, D402 desde BTN_N/QON); 2 s = apagado | circuit.py:278 · .net:11145 | ✓ |
| `LED_STATUS` | 48 | U201.25 | `kStatusLed` | LED D403 por R409 (330 Ω), activo alto | circuit.py:282 · .net:12033 | ✓ |
| `CHG_INT_N` | 21 | U201.23 | `kChargerInt` | INT del BQ25798 (R108): entrada; el estado se lee por I2C cada segundo | circuit.py:281 · .net:11167 | ✓ |
| `FG_ALRT_N` | 47 | U201.24 | `kGaugeAlert` | ALRT del MAX17048 (R113): entrada, sin uso | circuit.py:282 · .net:11216 | ✓ |
| `IMU_SDA` | 41 | U201.34 | `kImuSda` | Wire1 del BMI088, 400 kHz (R411) | circuit.py:284 · .net:12011 | ✓ |
| `IMU_SCL` | 42 | U201.35 | `kImuScl` | Wire1 del BMI088 (R412) | circuit.py:284 · .net:11989 | ✓ |
| `IMU_INT1` | 2 | U201.38 | `kImuInt1` | INT1 del acelerómetro: entrada con pull-down interno | circuit.py:276 · .net:11955 | ✓ |
| `IMU_INT3` | 1 | U201.39 | `kImuInt3` | INT3 del giróscopo: entrada con pull-down interno | circuit.py:276 · .net:11972 | ✓ |
| `USB_DN` | 19 | U201.13 | `kUsbDm` | USB nativo D− (consola JSON y carga de firmware) | circuit.py:279 · .net:12198 | ✓ |
| `USB_DP` | 20 | U201.14 | `kUsbDp` | USB nativo D+ | circuit.py:279 · .net:12239 | ✓ |
| `ESP_TXD0` | 43 | U201.37 | `kConsoleTx` | U0TXD, mensajes de la ROM (TP208) | circuit.py:284 · .net:10819 | ✓ |
| `ESP_RXD0` | 44 | U201.36 | `kConsoleRx` | U0RXD (TP209) | circuit.py:284 · .net:10802 | ✓ |

Libres: GPIO35, 36 y 37 (puntos de prueba TP203-TP205), 38, 39, 40 y 46.

### Direcciones I2C

| Bus | Chip | Dirección | De dónde sale |
| --- | --- | --- | --- |
| Wire (13/14) | OLED (J403) | 0x3C o 0x3D, se sondean las dos | Módulo; el firmware busca las dos |
| Wire | BQ25798 (U102) | 0x6B | SLUSDV2C §7.3.14.5, figura 7-19 (fija) |
| Wire | MAX17048 (U103) | 0x36 | Fija en el MAX17048 |
| Wire1 (41/42) | BMI088 acelerómetro | 0x18 | SDO1 a GND (U401.15), BST-BMI088-DS001 §6.2 |
| Wire1 | BMI088 giróscopo | 0x68 | SDO2 a GND (U401.10), §6.2 |

Del BMI088 (DS rev 1.9, tabla 14 y §6):
- PS a VDDIO selecciona I2C, CSB1 va a VDDIO y CSB2 al aire, como pide la hoja para I2C.
- Por I2C el acelerómetro no necesita la lectura de relleno que exige el SPI.
- Identificadores: 0x1E en ACC_CHIP_ID y 0x0F en GYRO_CHIP_ID, ambos en el registro 0x00.

### Pines de arranque, flash y PSRAM

- **GPIO0** (BOOT): R202 a +3V3 y SW202.
- **GPIO3**: R203 a GND.
- **GPIO46**: al aire (pull-down interno).
- **GPIO45**: R301 de 100 kΩ a GND, así que VDD_SPI queda a 3.3 V en el arranque, lo correcto para
  la flash de 3.3 V del N16R2.
  - El firmware usa GPIO45 como salida **después** del arranque: enciende el GNSS.
  - **Consecuencia:** cualquier reinicio del ESP32 apaga la carrier: por software, por OTA, por el
    watchdog o por caída de tensión. El UM980 arranca de cero y pierde el fix RTK.
  - Por eso el firmware **no** mantiene GPIO45 con `gpio_hold`: alto durante un reinicio, pondría
    VDD_SPI a 1.8 V.
- La flash y la PSRAM del módulo van por GPIO26-32, que el WROOM-1 no saca. Con PSRAM quad,
  GPIO33-37 quedan libres; ninguno se usa salvo los puntos de prueba.

## Cargador BQ25798

Hoja: TI SLUSDV2C (rev. C, junio de 2026), §7.5. Código: [`include/bq25798.h`](../firmware/esp32/include/bq25798.h),
con su prueba nativa `test/bq25798_test.cpp` contra un banco de registros con los valores de encendido.

Comprobaciones antes de escribir nada:

- REG48 PN = 011b (BQ25798). Si no, no escribe nada y lo informa (`unexpected_part`).
- VREG (REG01) = 4.2 V, el de 1S que fija PROG con 4.7 kΩ (R103; tabla 7-1). Si no es 4.2 V,
  la carga **se deshabilita**: watchdog apagado y EN_CHG = 0 (`charge_disabled_unexpected_vreg`).
  El pack Li-ion 1S2P no se debe cargar con otra tensión.
- La hoja no dice en qué orden van los dos bytes de los registros de 16 bits. El orden se
  deduce de VREG: 420 (4.2 V en pasos de 10 mV) solo se lee bien en uno de los dos.

Lo único que escribe:

| Registro | Valor | Por qué |
| --- | --- | --- |
| REG14 bit 7 SFET_PRESENT | 1 (y EN_EXTILIM = 1, como viene) | La placa lleva el FET de envío Q101. Sin este bit, SDRV_CTRL queda bloqueado en 00 y no hay modo *ship* |
| REG10 [2:0] WATCHDOG | 000 (desactivado) | Para que la configuración no vuelva a la de fábrica a los 40 s |
| REG03/04 ICHG | 1000 mA (100 × 10 mA) | J102: dos contactos GH por polo con AWG #26. El firmware no pasa nunca de 1.5 A; si lee más, vuelve a 1 A |
| REG11 SDRV_CTRL / SDRV_DLY | 10 / 1 (0x45 desde 0x40), solo al apagar | Modo *ship* inmediato. Solo sin VBUS: con USB la orden se ignora (§7.3.12) y el equipo queda «sigue alimentado» hasta que se quita el cable |

Nunca escribe VREG, IINDPM, VSYSMIN, CELL (REG0A) ni EN_EXTILIM = 0.

Cada segundo lee REG1B-1D (VBUS, PG, estado de carga, batería presente, regulación térmica),
REG20-21 (fallas, en crudo) y REG14. Si SFET_PRESENT vuelve a 0 (otro encendido del cargador
con el ESP32 vivo por USB), lo configura de nuevo. Todo sale en `subsystems.power.charger` (solo
HTTP y USB; aditivo).

Apagado:
- Botón 2 s (o `POST /api/power/shutdown`, o batería ≤ 3.45 V durante 60 s sin USB).
- Se cierra la microSD.
- Se espera a que **suelten el botón**: con QON en bajo el cargador vuelve a despertar al equipo.
- Se escribe el modo *ship*.
- Mantener el botón 10 s es el reset por hardware del BQ25798 (§7.3.12.3): el equipo se reinicia
  en vez de apagarse. Hay que soltarlo en cuanto la OLED dice «APAGANDO».

## Lo que no se hizo (pendiente, a propósito)

- **Modo «solo carga»** (encender con USB sin pulsar → GNSS apagado y OLED de carga). El equipo
  arranca siempre normal.
- **Política tras meter la batería** (SFET_PRESENT = 0 → volver a *ship*). Arranca normal.
- **IINDPM según el puerto USB:** la placa no lee CC. Manda ILIM (~1.45 A).
- **No se deshabilita la carga sin batería.** La recomendación de `research/power.md` de poner
  EN_CHG = 0 si no hay celda dejaría sin carga un pack con el BMS cortado por descarga profunda
  (VBAT bajo UVLO = «sin batería»). Se deja en manos del hardware (NTC obligatoria y BMS).
- **Driver del BMI088:** ni ejes, ni configuración de INT1/INT3, ni fusión. Solo el
  identificador de chip.
- **PPS y EVENT:** cableados y en el perfil, sin uso.
- **Fuerza de salida de GPIO6** (reloj de la microSD) por si desensibiliza el GNSS: probar en
  banco antes de tocarla.

## Riesgos y posibles fallos de la placa fabricada

Ninguno exige tocar el diseño. Los que se pueden resolver, se resuelven en firmware o con un
parche de banco:

1. **Orden VCC/GND de la OLED sin confirmar.** El esquema pone 1 VCC, 2 GND, 3 SCL y 4 SDA
   (J403), según la foto del anuncio. Si la serigrafía del módulo dice GND VCC, el módulo recibe
   la alimentación invertida.
   - Antes de soldarlo, mirar la serigrafía.
   - Si está cruzado, parche de banco: no soldar los pines 1 y 2 sobre sus pads; unirlos cruzados
     con dos cables cortos aislados (pin 1 del módulo al pad 2 de J403 y pin 2 al pad 1).
   - El firmware no puede corregirlo.
2. **El GNSS se apaga en cada reinicio del ESP32** (GPIO45 es pin de arranque; ver arriba). No hay
   arreglo seguro en firmware; el firmware solo evita reinicios innecesarios.
3. **RESET_N del UM980 no llega:** la BDLX no lo saca. Para reiniciar el receptor queda apagar y
   encender su 5 V por GPIO45 (no implementado).
4. **Margen del botón:**
   - Pulsado, GPIO18 queda a la caída del 1N4148W con ~0.33 mA (unos 0.55-0.7 V según la
     temperatura).
   - El ESP32-S3 lee bajo hasta 0.25 × VDD = 0.825 V: hay margen, pero poco en frío.
   - Medir en banco.
5. **INT3 del BMI088 arranca en drenador abierto** (DS §5.5.10) y la placa no tiene pull-up.
   El firmware deja pull-down interno; un driver futuro tiene que ponerlo en push-pull.
6. **Reloj de la microSD sin resistencia en serie.** SD_MMC va a 20 MHz y sus armónicos 78.° y
   80.° caen en 1560 y 1600 MHz (B1 de BeiDou y G1 de GLONASS). Medir el C/N0 con la microSD
   grabando.
7. **Antena del WROOM** con la carrier detrás y la pared a 0.29 mm: medir RSSI y caudal con todo
   montado.
8. **Sockets:** la sourcetable va ahora por su propia conexión. Con todo encendido a la vez
   (panel con 7 sockets, NTRIP, caster con dos rovers, publicación, radio) se rozan los 16 de
   lwIP. Si un `connect` falla, la lista dice `failed` y el NTRIP sigue.

## Pruebas de banco (cuando llegue la placa)

En orden. Fuente de laboratorio con límite de corriente para los primeros pasos y multímetro.
Anotar cada medida en `docs/firmware-validation.md`.

### 0. Sin alimentar

- Resistencia +3V3–GND, VSYS–GND, GNSS_5V–GND y VBUS–GND: ninguna en corto.
- Polaridad del cable del pack en J102: pines 1-2 a GND y 3-4 a BAT+.
- Serigrafía de la OLED: VCC, GND, SCL y SDA (ver riesgo 1).
- `python3 tools/board_check/check_v03_pins.py`: tiene que decir «cumple».

### 1. Primer encendido, sin carrier ni OLED

- 3.7 V en J102 desde la fuente, límite de 300 mA, con la NTC de 10 kΩ en J404.
- Esperar:
  - VSYS ≈ VBAT;
  - +3V3 entre 3.30 y 3.36 V (TPS62903, FB a 3.33 V);
  - **GNSS_5V = 0 V** (GPIO45 bajo en el reset);
  - el LED se enciende en cuanto arranca el firmware.
- Si no arranca, el botón despierta al cargador si estaba en *ship* (mantener ≥ 1 s).

### 2. Carga del firmware

- USB-C a la Mac. Aparece como «USB JTAG/serial» (303A:1001).
- Primera vez: **Instalación completa** con el cargador gráfico (modelo «MeridianV · Placa v0.3»),
  o `~/.platformio/penv/bin/pio run -e meridianv_v03 -t upload` desde `firmware/esp32`.
- Si el USB no responde: TP208/TP209 (UART0) con un adaptador serie de 3.3 V para leer la ROM, y
  BOOT + RESET (SW202, SW201) para el modo de descarga.

### 3. Estado por la consola USB

`python3 tools/api_contract/check_contract.py device --port <puerto>` y `GET /api/status` con
`tools/usb_console.py`. Esperado:

| Clave | Valor esperado |
| --- | --- |
| `firmware_version` | `0.9.0` |
| `hardware_id` | `tresvizo-meridianv-v03-s3-16m-v1` |
| `model`, `unit_name`, `serial` | `MeridianV`, `MeridianV-XXXX`, 8 hex |
| `capabilities` | `gnss_module` UM980, `lora_radio` false, `imu` BMI088, `battery_chemistry` li-ion, `removable_storage` true |
| `flash_bytes` / `psram_enabled_bytes` | 16 777 216 / ~2 MB |
| `subsystems.power.charger.setup` | `configured` (`vreg_mv` 4200, `ichg_ma` 1000, `sfet_present` true) |
| `subsystems.power.gauge_available`, `voltage_v` | true; igual al multímetro en J102 ± 20 mV |
| `subsystems.power.usb_present` | true con el cable |
| `subsystems.imu.probe` | `ok` (`accel_chip_id` 30 = 0x1E, `gyro_chip_id` 15 = 0x0F) |
| `subsystems.gnss.power_on` | true; medir **4.88 V** en J301.1 |
| `subsystems.display` | sin OLED: `not_detected`; con OLED: `ready`, `i2c_address` 60 (0x3C) o 61, `rotation_deg` 180 |
| `subsystems.microsd.card_present` | según haya tarjeta |

### 4. OLED (apagar, soldar el módulo, encender)

- El logo se ve derecho, no espejado.
- Después, «MeridianV-XXXX 0.9.0», el estado del GNSS, la microSD y la IP o la batería.
- Si se ve espejado o de cabeza, anotar cómo y no tocar la placa: se ajusta `kOledRotation` o los
  comandos de remapeo.

### 5. microSD

- SD_DET (GPIO17): 3.3 V con tarjeta y 0 V sin ella.
- Insertar una FAT32 antes de encender: `card_present` true y `state` listo.
- Grabar una sesión, pararla y bajarla.
- Retirar la tarjeta grabando: la sesión queda `partial`, nunca `closed`.

### 6. Botón y LED

- GPIO18 pulsado: medir; tiene que quedar por debajo de 0.8 V.
- Sin USB, mantener 2 s: OLED «APAGANDO», LED a 4 Hz, cierre de la memoria y, al soltar, corte.
  Después, VSYS en 0 y unos µA desde el pack.
- Mantener ≥ 1 s: vuelve a encender.
- Con USB: el corte queda en «Sigue alimentado» (`power_still_present`); al quitar el cable se
  apaga solo en un segundo.
- Mantener 10 s: el BQ25798 reinicia el equipo (es de hardware).

### 7. Carga del pack (con el pack 1S2P y la NTC pegada)

- Con USB, `charger.charge_state` en `fast_charge` y luego `taper_charge`.
- Corriente en el pack, con medidor en serie: unos 1 A, **nunca más de 1.5 A**.
- Tensión final de carga: 4.2 V.
- Sin NTC no carga (es de hardware).
- Temperatura de U102 y L101 tras 30 min.
- Puerto de PC de 500 mA: VINDPM baja la corriente y la placa no se reinicia.

### 8. GNSS (carrier BDLX por el arnés de J301)

- `accepted_gga` sube cada segundo.
- Correcciones por NTRIP o BLE: `correction_frames_sent` sube y se llega a FIX.
- PPS en GPIO10 con osciloscopio: 1 Hz.
- C/N0 con y sin Wi-Fi y grabación en la microSD (riesgo 6).
- Pedir la lista de puntos de montaje con NTRIP activo: el NTRIP sigue (`ntrip_kept` true) y la
  lista llega.

### 9. Radio y conjunto

- RSSI de Wi-Fi y BLE con la carcasa cerrada, frente a la Thing Plus.
- Bajada lenta de la fuente en J102 sin USB: a 3.45 V durante 60 s, apagado ordenado con la
  memoria cerrada (`shutdown_reason` `low_battery`).
- Sesión larga (≥ 4 h) grabando, con NTRIP y la app conectada: sin reinicios por el watchdog
  (`alerts` sin `last_reset_watchdog`).
