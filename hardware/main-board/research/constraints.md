# Placa principal — restricciones de partida

Investigación del 04-10-2026 para la placa principal propia (JLCPCB, fabricación y
montaje, hasta 4 capas) que sustituye a la Thing Plus ESP32-S3, al carrier BDLX del
UM980 y a los módulos de alimentación. Lleva el UM980 desnudo, el
ESP32-S3-MINI-1-N4R2, la microSD, el cargador BQ25792, el medidor MAX17048, la
fuente de 3.3 V, el interruptor de carga del UM980, el u.FL y, por decisión del
propietario del 04-10-2026, **el IMU BMI088 soldado en la placa** (ya no hay
breakout ni conector de IMU).

**Nada de esto está validado en hardware.** Las cotas mecánicas salen del CAD de
V2.2 (no impreso), los datos eléctricos de hojas de datos y fichas, y las
comprobaciones geométricas nuevas de un modelo FreeCAD hecho para este estudio sobre
una copia del generador (ver 1.4). Fuentes del repositorio: checkout principal
`TresVizoRTK/`, con los cambios sin commitear del 04-10-2026; las líneas citadas
son de esos archivos.

Archivos de esta carpeta: `gpio_map.csv` (mapa de GPIO propuesto),
`connectors.md` (conectores y pinouts) y `parts_connectors.csv` (abastecimiento).

## 0. Conflictos y decisiones pendientes detectados

| # | Hallazgo | Fuente | Qué pide decidir |
| --- | --- | --- | --- |
| C1 | El panel de V2.2 **ya no lleva USB-C**: el 04-10-2026 se cambió por un header **JST-XH de 2 pines (B2B-XH-A)** a z = 93.5, «solo mecánico; qué cargador entra y su polaridad lo define la electrónica». El encargo de esta investigación (y el mensaje del coordinador) siguen hablando de USB-C en el panel. | `mechanical/v2.2/README.md:18-20`, `:192`, `:212-219`; `parameters.json:424-442`; `components.json:73-77`; `build_v2_2.py:14-15` | Si el panel queda con JST-XH, el panel solo trae VIN/GND (sin D+/D−/CC) y el USB de datos del ESP32 tiene que ir en la propia placa. Ver `connectors.md`, PANEL_PWR y PANEL_USBD. |
| C2 | Los dos LEDs del panel van en barrenos de **Ø3.2** (LED de 3 mm). El RGB Steren LED-5/RGB es de **5 mm**: no entra sin cambiar la tapa del panel. | `parameters.json:443-448`; `hardware/power-modules/SOURCING_MX.md:10` | Usar un RGB de 3 mm de ánodo común, o agrandar el barreno (cambio de la tapa del panel, no del tubo). |
| C3 | El anillo LED del botón de 12 mm es de **12 V**; con 3.3 o 5 V «encenderá poco o nada». | `parameters.json:404`, `:422`; `README.md:209`; `components.json:50` | Comprar la variante de 3–6 V del mismo botón o alimentar el anillo desde una tensión mayor. |
| C4 | El firmware 0.8.x no maneja ningún LED, PPS ni IMU; la IMU figura como `not_integrated`. | `src/instrument.cpp:655-656`; `hardware/wiring.md:53` | Todo lo nuevo (PPS, IMU, RGB, LED del botón, COM3, RESET_N) es firmware nuevo. |
| C5 | Un disco perpendicular al eje de Ø55–58 mm (opción del coordinador) **no puede entrar**: los collares de las dos bayonetas dejan Ø52 y el cuello de la tapa Ø46.3. | 1.3 | Se descarta; ver la comparación. |
| C6 | El `hardware_id` es parte del contrato con las apps y de la imagen firmada (byte 320): una placa nueva necesita identidad y entorno de compilación propios. | `docs/api-contract/app-contract.json` (`hardware_id`, `board`); `include/board_profile.h:5` | Nuevo `TRESVIZO_HARDWARE_ID` y entorno PlatformIO; la API solo crece. |

## 1. Envolvente mecánica y ubicación de la placa

### 1.1 Lo que fija V2.2 (sistema de ejes del CAD)

Ejes del modelo: Z es el eje del jalón, hacia arriba, con origen en el asiento del
jalón; **el frente (panel) es +Y**; mirando el panel de frente, +X queda a la
**izquierda** (`build_v2_2.py:31-32`). Todo en mm.

| Dato | Valor | Fuente |
| --- | --- | --- |
| Diámetro exterior / pared | 64.0 / 2.5 → **interior Ø59 (r = 29.5)** | `parameters.json:16-17`; `capacity.json:3` |
| Collares de las bayonetas (base y tapa) | espesor 3.5, alto 13 → **paso libre Ø52 (r = 26.0)**, en z 8–21 (abajo) y 111.9–124.9 (arriba) | `parameters.json:18`, `:256-257`; `capacity.json:2`; `build_v2_2.py:451-458` |
| Piso interior (cara de la base) / techo | z = 15.91 / 122.91; largo útil 107 | `model-index.json:8-10`; `parameters.json:61` |
| Cuello de la tapa | baja hasta z = **99.41**; interior r = 23.15 (**Ø46.3**), exterior r = 25.65; cierre girando 28.7° | `model-index.json:13`; `build_v2_2.py:82-86`, `:118`; `parameters.json:259-262` |
| Antena | HA-901A Ø43.5 × 40.8 sobre la cara de la tapa, z = 129.91 (ARP); paso del coaxial Ø12 en el eje; SMA macho acodado de 15 mm bajo la tapa (z 109.9–124.9) | `parameters.json:205-221`; `model-index.json:11`; `build_v2_2.py:537-538`, `:921-925` |
| Refuerzo del seguro dentro del cuello | a 181–205°, desde z ≈ 116.4 hacia arriba | `parameters.json:166-173`; `build_v2_2.py:548-554` |
| Respaldo actual | placa vertical, cara de apoyo en y = −7.5, espesor 2.5, ancho 49 (x = ±24.5), costillas en x = ±12, de z = 16.9 a 97.4; arranca con rampa a 45° (en x = 0 la placa empieza hacia z ≈ 34) | `parameters.json:65-102`; `build_v2_2.py:335-375`; `README.md:148-164` |
| Ranuras del respaldo | 24 cuadradas de 4.5 en x = ±5 y ±18.5, filas z = 33…83 cada 10 | `parameters.json:81-91`; `capacity.json:31-36` |
| Toalleros | barras 4 × 4 a 4.5 de la pared: verticales a 30° y 150° (z 40–80) y horizontales de 14 a 10° y 170° (z = 92) | `parameters.json:486-520`; `README.md:166-176` |
| Paquete actual | carrier UM980 32 × 52 × 11 y Thing Plus 22.9 × 58.4 × 8 lado a lado delante del respaldo (y −7.5 → 3.5), desde z = 22; 18650 detrás, centro (0, −19.6), z 22–91 | `components.json:9-34`, `:78-86`; `build_v2_2.py:958-973`; `capacity.json:4-29` |
| 18650 | Ø18.6 × 65 (69 con protección, peor caso); a 0.6 de la pared | `components.json:78-86`; `capacity.json:26-29` |
| Ventana del panel en el tubo | 72.4° (53.8°–126.2°), z 33.5–98.4; pared engrosada 3.3 hacia dentro (r = 26.2) entre 40° y 140°, z 15.5–116.4 | `parameters.json:280-298`; `build_v2_2.py:311-332`; `README.md:212-215` |
| Tapa del panel | 86° × 82.9, centro z = 65.95; tornillos en z = 29.0 y 102.9 | `parameters.json:280-294` |
| OLED | PCB 27.5 × 27.8, z 55.5–83.3, plano del vidrio y = 24.85; área activa centrada en z = 71.5; pines y cables soldados hasta **y = 13.25** (x ±5.25, z 80.5–83.8) | `parameters.json:299-402`; `components.json:35-45`; `capacity.json:78-86`; `build_v2_2.py:929-938` |
| Botón 12 mm | eje en z = 43.5, x = 0; rosca hasta y = 15.3; terminales con cables hasta **y = 5.6** (x ±3.5, z 40–47) | `parameters.json:403-423`; `components.json:46-51`; `build_v2_2.py:940-956` |
| Conector de carga | JST-XH B2B-XH-A en z = 93.5; patas y termofit hasta y = 15.35 | `parameters.json:424-442`; `build_v2_2.py:993-999` |
| LEDs | Ø3.2 en z = 93.5, x = ±13.5 | `parameters.json:443-448` |
| IMU en V2.2 | plataforma en el cuello de la tapa (disco z 99.91–102.41), chip en el eje, z ≈ 106 | `model-index.json:16-20`; `README.md:80-144` |
| Ruta del coaxial y cables del IMU en V2.2 | paso trasero de la plataforma 235°–305° desde r = 15, bajando por el canal del respaldo; conexión por la ventana del panel | `parameters.json:174-181`; `README.md:140-143`, `:259-262` |

Holguras medidas en V2.2 con el paquete actual: 2.1 entre el botón con cables y el
UM980, 11.7 entre la pantalla con cables y las placas (`capacity.json:85`, `:91`;
`README.md:178-182`).

### 1.2 Qué se puede cambiar

Según el propietario: fijo el exterior (Ø64, ~130 de alto, posiciones de la ventana
y de los elementos del panel, interfaz de la tapa de antena y asiento del jalón); se
puede rehacer lo interior (respaldo, toalleros, plataforma del IMU, posición de la
batería). Los collares de bayoneta (Ø52) son parte de las interfaces fijas: **todo
lo que entre al tubo pasa por Ø52** (la ventana del panel deja ~31 × 65 y no sirve
para meter una placa grande).

### 1.3 Opciones comparadas

Comprobación con FreeCAD 1.1 sobre una copia del generador V2.2 **sin respaldo ni
toalleros**, con base, tapa cerrada, tapa del panel y las piezas de referencia
(botón, OLED, JST; los LEDs de 3 mm se modelaron como Ø4 × 15 hacia dentro,
supuesto). Volúmenes de choque en mm³. El script de esta comprobación se ejecutó
fuera del repositorio (reutiliza las funciones de `build_v2_2.py` sin el respaldo ni
los toalleros) y no se guardó aquí; los resultados están en las tablas.

| | (a) Placa en un plano que contiene el eje | (b) Disco perpendicular bajo la tapa | (c) Placa en el plano del respaldo actual |
| --- | --- | --- | --- |
| Tamaño máximo | **50 × 76** (3 800 mm² por cara) | Ø55–58: **no entra** (choca con el tubo 26.5/58.7 mm³ y no pasa el collar Ø52). Ø50 bajo el cuello choca con el bolsillo del JST y los LEDs (z 88–97: 9.4–18.9 mm³) o con el cuello (z ≥ 98: 13.8–175.6 mm³). Solo cabe **Ø45.9 dentro del cuello** (z 100.5–108): 1 655 mm² por cara | ~49 × 75 (z 22–97); en las esquinas de arriba (z > 80, x más allá de ±18.5) solo componentes de ≤ 1.5 mm por los toalleros horizontales; pasa el collar con solo 0.4 de margen (cálculo, sin modelo) |
| IMU en el eje | sí (chip en x = 0, y = 0) | sí, en el centro | no: queda a 5.4 del eje (brazo conocido) |
| Brazo IMU → ARP (z 129.91) | vertical, 129.91 − z_IMU (≈ 58 con z_IMU = 72) | vertical, ≈ 22–28 | 3D, ≈ 58 vertical + 5.4 horizontal |
| Coaxial u.FL → SMA | ~25 en línea recta; latiguillo de 60–100 | ~10–20 | ~60 por el canal del respaldo |
| Panel | los conectores quedan frente a la ventana: se enchufan con la tapa del panel quitada | los cables suben 50–60 hasta la cara inferior del disco, difícil de alcanzar | como hoy |
| Batería | detrás, 1S en (0, −19.6) o 2S en (±9.3, −17.37) | debajo, en el eje | detrás del respaldo (solo 1S) |
| Montaje | rieles impresos en el tubo + 2 tornillos | el disco va en la tapa: gira 28.7° al cerrar y arrastra todos los mazos | bridas o tornillos por las ranuras actuales |
| Calor junto al IMU | se puede separar 15–25 mm de cargador, ESP32 y UM980 | todo a ≤ 23 mm del centro y bajo una tapa cerrada | igual que (a) |
| Ensamble a una cara | sí | no: hace falta montaje por las dos caras | sí |
| Cambios interiores | quitar respaldo, toalleros y plataforma; añadir rieles, brazos y cuna de batería | quitar plataforma; rehacer el cuello como soporte | ninguno |

**Recomendación: (a).** Es la única que deja el IMU sobre el eje con área suficiente
para montar todo por una sola cara, con los conectores del panel accesibles. (c)
queda como plan B si no se quiere reimprimir el tubo.

### 1.4 Opción (a): números para el diseño

| Concepto | Valor | Comprobado |
| --- | --- | --- |
| Plano de la placa | cara de componentes (frontal) en **y = −0.475**, cara trasera en y = −2.075 (FR-4 de 1.6). Así el centro del BMI088 (0.95 de alto) cae en y = 0 | — |
| Contorno máximo | rectángulo **50.0 × 76.0**: x = ±25.0, z = 21.0 → 97.0. Chaflanes de 1 × 1 en las esquinas solo para entrar en los rieles; la curvatura no los exige | sin choques con tubo, tapa, base ni tapa del panel |
| Paso por los collares (Ø52) | la placa con su envolvente pasa en su posición final, sin descentrarla: radios de esquina 25.09 (placa), 24.43 (componentes de 10 mm a 2.5 del canto), 25.98 (componentes traseros de 5 mm en el canto: no usar, ver alturas) | barrido axial: 0 mm³ |
| Holguras | canto superior a 2.41 del cuello de la tapa; canto inferior a 5.09 de la base; 9.5 a las cabezas de los M3 de la tuerca del jalón | sí |
| Altura máx. cara frontal (hacia el panel) | **10 mm** en general (queda 3.7 a los cables de la OLED, 5.8 al JST, 4.5 a los LEDs supuestos, 12.2 a la tapa del panel); **4 mm** bajo el botón (x ±5.5, z 38–49; 2.0 al botón con cables); **0 mm** en los 2.5 mm de cada canto lateral (rieles) | sí |
| Altura máx. cara trasera | **sin componentes** (montaje a una cara). Si hiciera falta: ≤ 5 mm y dentro de x = ±22 (queda 3.2 a una 18650 y 1.0 a dos) | sí |
| Montaje | **dos rieles impresos** en el tubo (ranura 2.3 de fondo × 2.2 de ancho, 0.3 de holgura, z 21–97, tope abajo en z = 21, entrada achaflanada arriba) + **2 tornillos M2.5** en (x = ±13, z = 94) hacia dos brazos impresos detrás de la placa (z 91.5–96.5, y −6.5 → −2.1). La placa entra desde arriba con la tapa quitada | rieles sin choques; brazos a 7.2 de una 18650 y 1.7 de dos |
| Agujeros en la placa | 2 × Ø2.7 sin metalizar en (±13, 94), anillo libre de cobre Ø6.0 | — |
| Alcance por la ventana | con la tapa del panel quitada se ve la franja x = ±15.5, z 33.5–98.4 de la cara frontal: ahí van los conectores del panel, el u.FL, los tornillos y BOOT/RESET | cálculo |
| Cara hacia el panel | la frontal (componentes) | — |
| Cara hacia la batería | la trasera (lisa) | — |
| Canto hacia la tapa de antena | el superior (z = 97): u.FL y UM980 arriba | — |
| Canto inferior (z = 21) | «canto de servicio»: microSD de expulsión por empuje con la ranura hacia abajo y USB-C de programación, accesibles quitando la base | — |
| Cantos laterales | en los rieles; el ESP32-S3-MINI-1 con su antena en un canto lateral, en la mitad de abajo, fuera de la sombra de la batería (más allá de x = ±19) y lejos del UM980 y del u.FL | propuesta, sin ensayo de RF |
| IMU | BMI088 con su centro en **(0, 0, z_IMU)**; propuesta z_IMU ≈ 72 (brazo al ARP ≈ 57.9), ≥ 10 del UM980, ≥ 20 del cargador y del ESP32, ≥ 20 de los tornillos y lejos de conectores. Ejes: Z del sensor = +Y del equipo; elegir el giro de la huella para que Y del sensor = +Z (eje del jalón), y entonces X del sensor = −X del equipo. Serigrafiar los ejes | propuesta |
| Coaxial | u.FL en el canto superior, dentro de x = ±15.5; latiguillo u.FL → SMA macho acodado de 60–100 mm, con holgura para el giro de 28.7° de la tapa | — |
| Batería | cuna impresa en la pared trasera: 1S en (0, −19.6), a 0.6 de la pared, o 2S en (±9.3, −17.37), a 0.5; z 22–91. Entra por un extremo del tubo pasando el collar con su centro en y ≈ −11.9 y luego se lleva atrás. Cables por debajo del canto inferior de la placa (5 mm libres hasta la base). La 2S necesita además su placa de protección y balanceo, que no está modelada (sitio posible: sobre las celdas, z 91–97 detrás de los brazos con y < −8; sin comprobar) | radios 21.2 (1S) y 24.4 (2S) frente a 26.0 |

Presupuesto de área (estimación propia): las huellas con su margen suman ~2 300 mm²
(UM980 17 × 22, módulo ESP32 con su antena en el canto, microSD, cargador con bobina,
fuente de 3.3 V, conectores, BMI088 con su zona libre, pulsadores y ~400 mm² de
pasivos) frente a ~3 400 mm² útiles de una cara (45 × 76 sin los cantos de los
rieles): **~68 %**. Cabe a una cara, pero con poco margen; las 4 capas ayudan a
rutear.

Zonas prohibidas en la cara frontal: bajo el botón solo ≤ 4 mm; 2.5 mm en cada canto
lateral sin nada (rieles); Ø6 sin cobre alrededor de los dos agujeros; bajo el
BMI088 nada en la capa superior (sección 5.3); la zona de antena del módulo ESP32
(sección 3.1). En la cara trasera, nada.

Cambios interiores que implica (fuera del alcance de este documento): quitar
respaldo, ranuras, costillas y toalleros del tubo y la plataforma del IMU de la tapa;
añadir rieles, brazos y cuna. El exterior, la ventana y la tapa del panel no cambian.

## 2. Mapa de pines del firmware actual (Thing Plus, firmware 0.8.x)

Compilación: entorno `esp32s3_usb`, placa `sparkfun_thing_plus_esp32s3`
(MINI-1-N4R2, 4 MB de flash DIO, 2 MB de PSRAM quad), USB CDC al arrancar
(`platformio.ini:4-18`; `boards/sparkfun_thing_plus_esp32s3.json`).

| GPIO | Uso en firmware | Detalle | Fuente |
| --- | --- | --- | --- |
| 43 | TX de UART2 → UM980 COM2 RX (TTL_RXD2) | 115200 8N1, búfer RX de 8 KiB | `include/board_profile.h:6-8`; `src/gnss_receiver.cpp:28`, `:146`, `:158`; `hardware/wiring.md:11-19` |
| 44 | RX de UART2 ← UM980 COM2 TX (TTL_TXD2) | idem | idem |
| 8 / 9 | I2C SDA / SCL | 100 kHz; OLED SSD1306 en 0x3C o 0x3D; MAX17048 en 0x36; una sola tarea dueña de `Wire` | `board_profile.h:13`; `src/local_display.cpp:19`, `:77`, `:109`; `src/power_manager.cpp:15-20` |
| 45 | Habilita el regulador de periféricos (Qwiic/microSD) | salida HIGH al arrancar, 10 ms antes de usar I2C | `board_profile.h:14`; `local_display.cpp:149-151`; `wiring.md:49` |
| 38 / 34 | SD_MMC CLK / CMD | 4 bits, 20 MHz, sin formatear | `board_profile.h:15`; `src/sd_recorder.cpp:77-83` |
| 39 / 40 / 47 / 33 | SD_MMC D0 / D1 / D2 / D3 | | `board_profile.h:16`; `wiring.md:29-36` |
| 48 | Detección de tarjeta | **HIGH = tarjeta puesta**, `INPUT_PULLDOWN`; sin tarjeta no monta y la grabación se corta | `board_profile.h:17`; `sd_recorder.cpp:30`, `:57`, `:75-76`, `:107` |
| 10 | PUSH del Soft Power Switch Mk2 | `INPUT_PULLUP`, activo bajo | `board_profile.h:19`; `power_manager.cpp:24`, `:35` |
| 14 | OFF del Mk2 | salida LOW desde el arranque; HIGH corta | `board_profile.h:19`; `power_manager.cpp:23`, `:39` |
| 19 / 20 | USB nativo (consola JSON y carga de firmware) | reservado | `wiring.md:48`; `platformio.ini:18` |
| 0 / 46 | BOOT/LED de estado y RGB WS2812 de la Thing Plus | el firmware no los usa | `wiring.md:50`; esquema Thing Plus v10 (redes `ESP0/STAT`, `ESP46/LED`) |

Lo que la Thing Plus cablea y el firmware no usa (esquema v10,
`SparkFun_Thing_Plus_ESP32-S3.pdf`, redes): `ESP35/~ALRT` (alerta del MAX17048 en
GPIO35), `ESP41/LP_CTL`, SPI del conector en GPIO11/12/13 (PICO/SCK/POCI), A0–A5 =
GPIO10/14/15/16/17/18. El mismo esquema anota que en los módulos -N4R2 **GPIO26 está
conectado a la PSRAM** y que 0, 3, 45 y 46 son pines de arranque.

No hay en el firmware: LEDs propios, PPS, IMU, SPI ni RESET del UM980 (`grep` sobre
`src/`, `include/`, `lib/`; `instrument.cpp:655-656` publica la IMU como
`not_integrated`).

### 2.1 Encendido y apagado (Mk2)

- `setup()` empieza por `power_manager::begin()` (OFF = LOW, PUSH con pull-up) y
  `local_display::begin()` (GPIO45 = HIGH) (`src/main.cpp:189-192`).
- Para apagar hay que **soltar** el botón ≥ 30 ms y después **sostenerlo 2 s**
  (`include/power_sequence.h:5-14`), o pedirlo por la API. Si hay una OTA en curso se
  rechaza (`power_manager.cpp:28-32`).
- Se cierra la grabación de la microSD y **solo entonces** OFF pasa a HIGH; a los
  500 ms, si sigue vivo, el estado es `power_still_present`
  (`power_manager.cpp:33-42`; `local_display.cpp:39-45`).
- El Mk2 corta por hardware a los ~10 s de pulsación aunque el firmware no cierre
  (`wiring.md:101`).

### 2.2 Batería y carga

- Lee el MAX17048 (0x36) cada segundo desde la tarea de la OLED: VCELL (0x02) ×
  78.125 µV y SOC (0x04) / 256; acepta 2.5–4.5 V; capacidad fija 3000 mAh; batería
  baja con ≤ 10 % o ≤ 3.4 V (`power_manager.cpp:43-63`; `local_display.cpp:132-138`).
- La OLED alterna cada 5 s la IP con «BAT nn% x.xxV» (`local_display.cpp:66-74`).
- `charging`, `usb_present` y `battery_present` salen `null`: el MCP73831 de la Thing
  Plus solo enciende su LED (`power_manager.cpp:59-61`; `wiring.md:97-103`). Estas
  claves **no** están en `docs/api-contract/app-contract.json`; rellenarlas no rompe
  las apps (correr igualmente `tools/api_contract/check_contract.py`).

### 2.3 Qué tendría que cambiar el firmware en la placa nueva

1. **Identidad**: nuevo `TRESVIZO_HARDWARE_ID`, nombre y entorno de compilación
   (`board_profile.h:5`, `:12`; ver C6).
2. **Apagado**: el BQ25792 no tiene un pin de corte; el apagado pasa a ser **modo
   ship por I2C** (REG0x11 SDRV_CTRL = 10, sección 3.3), escrito por la tarea dueña
   de `Wire` después de cerrar la microSD. La secuencia de botón, el cierre y el
   estado `power_still_present` (con cargador conectado, la orden se ignora) se
   conservan. **Escribir el modo ship solo con el botón ya suelto**: el mismo botón
   va a QON y, si sigue pulsado, el BQ25792 sale del modo ship al cabo de ~1 s y el
   equipo vuelve a encender (deducción de la hoja; comprobar en banco).
3. **GPIO14** deja de ser OFF del Mk2 y pasa a **apagar el UM980** con la misma
   polaridad: HIGH = sin alimentación. El firmware 0.8.x ya lo pone LOW al arrancar
   (UM980 encendido) y HIGH al apagar (UM980 apagado), así que sigue funcionando sin
   cambios. Una resistencia de pull-up externa lo deja apagado en reset; el pulso
   de arranque y los reinicios del ESP32 piden un filtro en la puerta (sección 3.2).
4. **PUSH** (GPIO10) sigue igual; el mismo botón va también a QON del BQ25792 para
   salir del modo ship.
5. **Carga**: leer el estado del BQ25792 para `charging`/`usb_present`; el LED de
   carga lo maneja el pin STAT del BQ25792 sin firmware.
6. **Batería 2S**: el MAX17048 es de una celda; con 2S haría falta el MAX17049 o
   la lectura de tensión del BQ25792, y cambiar los 3000 mAh fijos.
7. **Nuevo**: PPS, RESET_N y COM3 del UM980, IMU por SPI, RGB y LED del botón.
8. **microSD**: mantener la detección HIGH = tarjeta puesta eligiendo zócalo y
   cableado (ver `connectors.md`); si no, invertir la lectura en `sd_recorder.cpp`.

## 3. Restricciones de los chips (base del mapa de GPIO)

El mapa propuesto está en `gpio_map.csv`. Fuentes: hoja del ESP32-S3-MINI-1/1U v1.7
(https://www.espressif.com/sites/default/files/documentation/esp32-s3-mini-1_mini-1u_datasheet_en.pdf,
**[M]**), hoja de la serie ESP32-S3 v2.2
(https://www.espressif.com/sites/default/files/documentation/esp32-s3_datasheet_en.pdf,
**[S]**), guía de diseño de hardware de Espressif
(https://docs.espressif.com/projects/esp-hardware-design-guidelines/en/latest/esp32s3/schematic-checklist.html
y `.../pcb-layout-design.html`, **[H]**), manual del UM980 R1.9 de dic-2025
(https://en.unicore.com/uploads/file/UM980_User%20Manual_EN_R1.9.pdf, **[U]**; la
R1.7 ya da 404), hoja del BQ25792 SLUSDG1C
(https://download.mikroe.com/documents/datasheets/BQ25792_datasheet.pdf, **[T]**;
ti.com devolvió 404 a la consulta automática). Las mismas claves se usan en `gpio_map.csv`.

### 3.1 ESP32-S3-MINI-1-N4R2

- **GPIO expuestos**: 0–21, 26 y 33–48; pin del módulo = GPIO + 4 para IO0–IO21;
  GPIO27–32 no salen ([M] tabla 3-1, pp. 11–12).
- **GPIO26 no se puede usar en -N4R2**: va a la PSRAM integrada ([M] p. 12, nota b).
- **GPIO33–37 sí se pueden usar en -N4R2**: la PSRAM y la flash quad usan GPIO26–32
  y 33–37 solo se ocupan en modo octal ([S] tabla 2-14, p. 31; §2.3.4, p. 25). Es
  una deducción de esas tablas: la hoja del MINI-1 no lo dice en una frase. La Thing
  Plus ya usa 33, 34 y 35 con este mismo módulo.
- **Pines de arranque** ([M] tablas 4-1 a 4-5, pp. 13–16): GPIO0 con pull-up débil
  (LOW en reset = descarga), GPIO3 **sin pulls internos** (con los eFuse por defecto
  se ignora, pero la hoja pide que no quede en alta impedancia: ponerle una
  resistencia), GPIO45 y GPIO46 con pull-down débil. **GPIO45 tiene que estar LOW en
  reset** (con LOW la VDD_SPI es de 3.3 V); la hoja no dice si el módulo sale con el
  eFuse que lo fuerza. GPIO46 decide además si la ROM imprime su registro. Retención
  de los niveles: ≥ 3 ms tras subir EN.
- **EN**: 10 kΩ a 3V3 y 1 µF a GND; no dejarlo al aire ([M] §9, p. 41).
- **USB**: GPIO19/20 van por defecto al USB-Serial/JTAG ([S] p. 25). Reservar
  resistencias serie de 22–33 Ω y prever un pull-up externo en D+ si su nivel al
  encender molesta ([H], sección USB).
- **JTAG por pines** (GPIO39–42): con los eFuse por defecto el JTAG va por USB y esos
  cuatro pines quedan como GPIO ([S] tabla 2-4, p. 22). El modo de descarga por
  USB-OTG sí mueve MTDO, MTCK y GPIO38 ([H]).
- **Pulsos al encender** ([S] tabla 2-2, pp. 18–19): GPIO1–17 dan un pulso bajo de
  ~60 µs; GPIO18 bajo y alto; GPIO19 bajo y dos altos; GPIO20 dos altos. Afecta
  sobre todo a **GPIO14** (corte del UM980): ver 3.2.
- **ADC**: ADC1 = GPIO1–10, ADC2 = GPIO11–20; el ADC2 lo comparte el Wi-Fi ([S]
  tabla 2-8, p. 24; https://docs.espressif.com/projects/esp-idf/en/stable/esp32s3/api-reference/peripherals/adc/adc_oneshot.html).
  El mapa no usa entradas analógicas.
- **Antena del módulo** ([H], principios de layout): antena fuera de la placa o en el
  borde, con la placa recortada a ambos lados y por debajo de la zona de antena;
  nunca el módulo en el centro con un hueco alrededor; y **15 mm libres en todas
  direcciones dentro de la carcasa**. Las cotas exactas de la zona prohibida solo
  vienen en una figura: sin verificar. Dentro de Ø59 no se pueden dar 15 mm hacia
  la pared lateral (4.4 mm); con una 18650 la batería queda a ≥ 10 mm del canto
  lateral, con dos 18650 la celda llega a x = ±18.6 y queda pegada a la zona de
  antena. **Es un riesgo de RF a medir (RSSI) en el primer prototipo**; con 2S
  conviene revisar la posición del módulo.

### 3.2 Unicore UM980 (pines del símbolo KiCad de SparkFun; VCC_RF, V_BCKP, RESET_N, BIF y RSV coinciden con [U])

| Pin | Señal | Uso en la placa |
| --- | --- | --- |
| 2 | ANT_IN | u.FL por 50 Ω coplanar |
| 4 / 5 / 6 | ANT_DETECT / ANT_OFF / ANT_SHORT_N | supervisión de la alimentación de antena (opcional) |
| 7 | VCC_RF | salida VCC − 0.1 V, 50 mA |
| 19 / 20 / 21 | PVT_STAT / RTK_STAT / ERR_STAT | sin GPIO (pads de prueba) |
| 26 / 27 | RXD2 / TXD2 | ESP32 GPIO43 / GPIO44 (como hoy) |
| 30 / 31 | TXD3 / RXD3 | ESP32 GPIO5 / GPIO6 |
| 42 / 43 | TXD1 / RXD1 | UM980_AUX (UPrecise) |
| 33, 34 | VCC | 3.0–3.6 V |
| 36 | V_BCKP | 2.0–3.6 V, < 60 µA |
| 49 | RESET_N | ESP32 GPIO4 (drenador abierto) |
| 51 | EVENT | UM980_AUX y, opcional, GPIO42 |
| 53 | PPS | ESP32 GPIO1 y UM980_AUX |
| 28 / 29 | BIF | 10 kΩ de pull-up y punto de prueba ([U] fig. 3-1) |
| 13 / 22 / 23 | RSV | al aire |

Símbolo: https://github.com/sparkfun/SparkFun_UM980_Triband_GNSS_RTK_Breakout
(`Hardware/SparkFun_GNSS_UM980.kicad_sch`). Datos eléctricos de [U]:

- Paquete **22.00 × 17.00 × 2.60 mm** (tabla 2-6); 54 contactos LGA.
- VCC 3.0–3.6 V con rizado ≤ 50 mV; **145 mA típ., 180 mA máx.** a 3.3 V (480 mW);
  pico de corriente al encender; ≥ 30 µF en VCC (tablas 2-2 y 2-3, fig. 3-1).
- E/S de COM1–3 LVTTL: VIL ≤ 0.6 V, VIH ≥ 0.7·VCC; máximo absoluto de E/S 3.6 V
  (tablas 2-2 y 2-4). Interfaces I2C, SPI y CAN reservadas, sin soporte.
- **RESET_N** activo bajo, ≥ 5 ms. Que tenga pull-up interno **no está en el
  manual**: poner 10 kΩ externo a VCC del UM980.
- **Secuencia de alimentación** (§3.3): VCC parte de < 0.4 V y sube de forma
  monótona; **más de 500 ms** entre apagar y volver a encender (también V_BCKP).
- **V_BCKP**: si no se quiere arranque en caliente, unir a VCC; nunca a GND ni al
  aire. Para conservar efemérides cuando GPIO14 apaga el UM980 con el equipo
  encendido, alimentarlo desde 3V3 (siempre presente con el ESP32 encendido); en modo
  ship todo se apaga y el siguiente arranque es en frío (SparkFun pone una pila de
  3 V/1 mAh).
- **Antena activa**: el manual **no recomienda usar VCC_RF como ANT_BIAS** y pide un
  riel aparte: ANT_BIAS por una bobina de 68 nH a ANT_IN, 100 nF ∥ 100 pF de
  desacoplo, 100 pF de bloqueo de continua, diodo ESD de > 2 GHz y TVS (fig. 3-2);
  ganancia de antena óptima 18–36 dB (tabla 2-5). El breakout de SparkFun alimenta
  por defecto desde VCC_RF con 68 nH, 100 pF, 0.1 µF y PESD0402, con un puente para
  alimentación externa, y usa guía coplanar de 0.349 mm con 0.203 de separación
  sobre 0.2 mm de dieléctrico (`Hardware/UM980_antenna.kicad_sch`).
- Puerto de actualización: [U] no lo dice; SparkFun actualiza con UPrecise por
  UART1 (COM1) (https://docs.sparkfun.com/SparkFun_UM980_Triband_GNSS_RTK_Breakout/single_page/).
  Por eso COM1 va a UM980_AUX.
- MSL: 3 según un extracto de búsqueda del manual R1.9; no confirmado en su tabla
  (sin verificar; ver 6.4).

**Corte del UM980 por GPIO14.** Con la polaridad HIGH = apagado y pull-up, el UM980
está apagado en el arranque, como pide el encargo, pero:

1. GPIO14 da un pulso bajo de ~60 µs al encender el ESP32 ([S] tabla 2-2): sin
   filtro, el MOSFET P daría un pulso de alimentación al UM980.
2. En cualquier reinicio del ESP32 el GPIO queda en entrada y el pull-up apaga el
   UM980 durante el arranque (~0.1–0.5 s), menos que los 500 ms que pide el manual
   entre apagado y encendido.

Propuesta (sin validar): puerta del MOSFET P con condensador puerta-fuente y
resistencias tales que el pulso de 60 µs no la mueva, que un reinicio corto no
llegue a apagarlo (p. ej. pull-up de 1 MΩ con 1 µF, τ ≈ 1 s) y que un HIGH forzado
lo apague en ~10 ms (10 kΩ en serie desde el GPIO); más una descarga de VCC del
UM980 para que vuelva a < 0.4 V. El firmware nuevo debería esperar ≥ 500 ms entre
apagar y encender. Alternativa: conmutador de carga con descarga rápida y entrada
activa en alto, con un inversor.

### 3.3 TI BQ25792 (cargador)

- I2C **0x6B** (§9.3.14.5). En el mismo bus que la OLED (0x3C/0x3D) y el MAX17048
  (0x36): sin choques.
- **QON** (pin 12): pull-up interno de 200 kΩ; en reposo da **3.6–3.8 V** (con VBUS y
  VBAT > 5 V), más de lo que admite un GPIO de 3.3 V: por eso el botón llega a GPIO10
  a través de un diodo. Salir del modo ship: QON bajo **1 s** (o 15 ms con WKUP_DLY,
  REG0x12 bit 3). **QON bajo 10 s** reinicia la alimentación (corta el FET de batería
  350 ms): es el equivalente al corte forzado de ~10 s del Mk2, pero reinicia en
  lugar de apagar (§9.3.12.3).
- **Apagado**: REG0x11 bits [2:1] SDRV_CTRL = **10 ship** (01 shutdown, 11 reinicio),
  bit 0 SDRV_DLY = inmediato o 10 s. No hay bit EN_SHIP. **Con adaptador presente la
  orden se ignora** y el campo vuelve a 00: es el estado `power_still_present` que ya
  tiene el firmware. Consumo de batería: ship 11 µA típ. (16 máx.); shutdown 0.5 µA,
  pero **en shutdown solo despierta al enchufar el cargador**, no con el botón: usar
  ship (§9.3.12; tabla 9-27; características eléctricas p. 9).
- **/INT** (pin 21): drenador abierto, pulso bajo de 256 µs; pull-up de 10 kΩ a 3.3 V,
  no a REGN (§9.3.4.1).
- **STAT** (pin 1): drenador abierto; LOW cargando, HIGH terminada/deshabilitada/solo
  batería, parpadeo de 1 Hz en falla; se puede desactivar (DIS_STAT).
- **CE** (pin 13): activo bajo; no dejarlo al aire. **ILIM_HIZ** (pin 17): V = 1 V +
  0.8 Ω × IINDPM; < 0.75 V detiene el convertidor; a REGN = límite máximo.
- **PROG** fija celdas y frecuencia al encender (tabla 9-1): 1S 3.0 kΩ (1.5 MHz) o
  4.7 kΩ (750 kHz); 2S 6.04 kΩ o 8.2 kΩ. Bobina de **1 µH a 1.5 MHz o 2.2 µH a
  750 kHz** (§10.2.2.1).
- **Valores por defecto** (tablas 9-2 y 9-9): VREG 4.2 V (1S) / 8.4 V (2S); **ICHG
  2 A en 1S y 2S** hasta que el firmware lo cambie (para una 18650 de 3000 mAh y el
  PH de 2 A conviene bajarlo pronto); VSYSMIN 3.5 V (1S) / 7 V (2S); temporizador de
  carga rápida de 12 h.
- **VBUS** 3.6–24 V de trabajo, 30 V máximo absoluto, OVP 25.7 V típ., hasta 3.3 A de
  entrada; **carga 1S–4S desde 5 V** (buck-boost, §9.3.6).
- **Dos entradas**: VAC1/VAC2 a VBUS si no hay FET de entrada; ACDRV1/2 a GND si no se
  usan. Con panel + USB-C de la placa hacen falta los pares de FET de cada entrada.
- **Detección D+/D−** (BC1.2 y HVDCP, tabla 9-4): SDP 500 mA, CDP 1.5 A, DCP 3.25 A,
  desconocido 3 A. Si esas líneas se comparten con el USB del ESP32 hay que comprobar
  que la detección no estorbe la enumeración (sin verificar); la entrada JST-XH del
  panel no trae D+/D−.
- **REGN** 4.8 V típ., 30 mA: no alimentar LEDs desde ahí (el LED de carga va a 3V3).
- Sin batería y con la carga deshabilitada, SYS se regula a VSYSMIN (§9.3.6).
- Revisión más reciente: SLUSDG1D (abr-2026), consultada en una copia de DigiKey con
  marca de agua; su tabla de pines coincide con la C.

### 3.4 MAX17048 / MAX17049 (medidor)

La hoja de Analog Devices no cargó en esta sesión (error HTTP/2 y tiempo agotado):
**nada de esta sección se verificó en la hoja**. Lo que sí consta: dirección 0x36 en
el esquema de la Thing Plus v10 («7-bit I2C Address: 0x36») y en el firmware
(`power_manager.cpp:16`), con VCELL × 78.125 µV y SOC / 256 (`power_manager.cpp:45-46`);
la alerta ~ALRT va a GPIO35 en la Thing Plus. Para 2S existe el MAX17049; su escala
de VCELL para el paquete (¿156.25 µV?) es una inferencia sin comprobar.


## 4. Piezas del panel y externas

Mercado Libre bloqueó la consulta automática (redirige a verificación de cuenta), así
que de la OLED ANPOMNHBUK y del botón MLM-1715951825 no hay datos de su anuncio: se
usan las cotas ya capturadas en el repositorio y fichas de piezas equivalentes.

| Pieza | Lo que hay | Pendiente | Fuentes |
| --- | --- | --- | --- |
| **OLED 0.96" 128×64 I2C, 4 pines** (SSD1306 o compatible) | Alimentación 3.3–5 V; regulador XC6206 de 3.3 V (marca «662K») con puente para saltarlo a 3.3 V; pull-ups de 4.7 kΩ a su 3.3 V en SCL/SDA; dirección 0x3C (0x3D cambiando una resistencia); hasta ~25 mA. PCB 27.5 × 27.8, agujeros Ø2.0, pines a 2.54. El firmware busca 0x3C y 0x3D | **El orden del header no es fijo**: en las fotos de Tecneu aparecen «VDD GND SCK SDA» y «GND VCC SCL SDA» (LCD wiki documenta ambos: MC096VX y MC096GX). Los cables se sueldan siguiendo la serigrafía de la unidad recibida; el conector de la placa (OLED, Qwiic) no cambia | `hardware/wiring.md:14-17`, `:38-40`, `:76`; `parameters.json:299-305`; https://www.tecneu.com/products/modulo-de-pantalla-led-oled-7-pin-0-96-i2c; https://www.lcdwiki.com/0.96inch_OLED_Module_(IIC-4P_SKU:MC096VX); https://www.lcdwiki.com/res/MC096VX/0.96inch-OLED-MC096VX-schematic-diagram.pdf |
| **Botón metálico de 12 mm** | Momentáneo, anillo LED azul de **12 V**; cabeza 13.9, rosca M12 × 0.75, 19.5 detrás de la cara de apoyo, terminales de 3.7. Los equivalentes de fabricante (ONPOW GQ12) son 1 NA, 2 A/36 V CC, LED de 6/12/24 V con resistencia interna y ~15 mA, LED sin polaridad; los genéricos traen 4 terminales: C, NA, LED+ y LED− | Resistencia interna y corriente del comprado: sin verificar. Con 3.3–4.2 V el anillo de 12 V apenas enciende: pedir la versión de 3–6 V (la ofrecen p. ej. APIELE) o generar 12 V | `parameters.json:403-423`; `components.json:46-51`; https://www.onpowbutton.com/high-roundring-illuminatedstainless-steel-product/; https://hongbocn.en.made-in-china.com/product/wvrQzyJuXXWP/China-Onpow-12mm-Flat-Head-Push-Button-Switch-GQ12-AF-10E-R-12V-S-CE-RoHS-.html |
| **RGB de estado** Steren LED-5/RGB | Ánodo común, 5 mm, Vf rojo 1.8 V, verde 2.8 V, azul 2.8 V, 20 mA. Steren no publica corriente máxima ni orden de patas (el habitual R-ánodo-G-B: sin verificar, comprobar con el diodo del multímetro) | **No entra en el barreno de Ø3.2 de V2.2** (C2): usar un RGB de 3 mm de ánodo común | https://www.steren.com.mx/led-de-5-mm-rgb.html; `hardware/power-modules/SOURCING_MX.md:10`; `parameters.json:443-448` |
| **LED de carga** | En V1/V2 era una guía de luz desde los LEDs del PowerBoost; en V2.2 es el segundo LED de 3 mm del panel. En la placa nueva lo enciende el pin STAT del BQ25792 | Elegir color y resistencia | `hardware/power-modules/README.md:26`; `hardware/power-modules/WIRING.md:66` |
| **USB-C del panel** | En V2.2 sin commitear ya no hay USB-C (C1). En el V2.2 commiteado era una placa de 18 mm «sin referencia confirmada». El **Adafruit 5871** (de los planes de la Tiny) no es un breakout de alimentación: es el conmutador de datos **TS3USB30 1 a 2** con USB-C de entrada, regulador AP2127K-3.3 y **5.1 kΩ en CC1 y CC2** (sí se presenta como sumidero: un cargador USB-C le da 5 V); VBUS no se conmuta | Si vuelve un USB-C al panel, un breakout de alimentación y datos con 5.1 kΩ en CC: Adafruit 4090 (GND, VBUS, SBU2, CC1, D−, D+, SBU1, CC2) o SparkFun BOB-15100 (CC2, D+, D−, CC1, GND, VBUS), ambos con 5.1 kΩ | `git show HEAD:mechanical/v2.2/README.md` (líneas 154, 275); `hardware/power-modules/README.md:20`; https://www.adafruit.com/product/5871; https://github.com/adafruit/Adafruit-TS3USB30-PCB; https://github.com/adafruit/Adafruit-USB-C-Downstream-Breakout; https://github.com/sparkfun/USB-C-Breakout |
| **Breakout BMI088V1.0 (KAIHCHIP)** — sustituido por el IMU en placa | Header de 9 pines según las fotos (pin cuadrado = VCC): 1 VCC, 2 GND, 3 MISO/AD0, 4 MOSI/SDA, 5 SCLK/SCL, 6 CSB1, 7 CSB2, 8 INT1, 9 INT3 (INT2 e INT4 no salen). Selector deslizante SPI/IIC (que actúe sobre PS: sin verificar). Un SOT-23-5 sin marca, probablemente regulador; no se ve traductor de niveles. Tensión de alimentación no publicada | Ya no hace falta para la placa nueva; queda como referencia del prototipo con la Thing Plus | AliExpress 1005009596235318 y 1005009869623539 (leídos en navegador; las fichas solo dicen que IIC/SPI se cambia con el interruptor); `parameters.json:104-140`; `hardware/identification.md:18` |

## 5. IMU en la placa: Bosch BMI088

### 5.1 Pieza

| Dato | Valor | Fuente |
| --- | --- | --- |
| Pieza | BMI088 (acelerómetro y giróscopo de 3 ejes), LGA-16 de 3.0 × 4.5 × 0.95 mm, paso 0.5; MSL 1 | datasheet BST-BMI088-DS001 rev 1.9 (ene-2024), pp. 2, 54, 58: https://www.bosch-sensortec.com/media/boschsensortec/downloads/datasheets/bst-bmi088-ds001.pdf |
| JLC/LCSC | **C194919**, Extended, 4 482 en JLC (04-10-2026), **6.79 USD** (1–9) / **6.02 USD** (10–29); «Standard Only» y rayos X obligatorios. JLC ofrece símbolo y huella de EasyEDA para esta pieza (no cotejada con la fig. 11 de Bosch) | API de piezas de JLC; https://jlcpcb.com/partdetail/BoschSensortec-BMI088/C194919 |
| Decisión | **Se mantiene el BMI088**: hay existencias y el precio es razonable. Sus ventajas para un jalón: supresión de vibración por encima de unos cientos de Hz (p. 2) y «Very high» en robustez a vibración en la guía de diseño | DS p. 2; BMI08x design guide, tabla 2: https://community.bosch-sensortec.com/knowledge-base-pg631enp/post/bmi08x-design-guide-ZWU1wwmHYnSw68r |

Alternativas solo si faltara: **ISM330DHCX** (C2655101, 4.91 USD; único de los cuatro
con inestabilidad de sesgo publicada, 3 °/h, y −40…105 °C; DS13012 rev 6, tabla 2) o
**BMI270** (C2836813, 2.56 USD; pensado para ponibles, sin dato de vibración). El
ICM-42688-P de TDK cuesta 17.52 USD en JLC (C1850418) y el C54308212 es una copia de
marca Tokmas. Ninguno es compatible pin a pin con el BMI088.

| Dato típico (DS tablas 4–5, pp. 9–10) | Acelerómetro | Giróscopo |
| --- | --- | --- |
| Offset | 20 mg | ±1 °/s |
| Deriva térmica del offset | < 0.2 mg/K | ±0.015 °/s/K |
| Ruido | 160 µg/√Hz (Z: 190) | 0.014 °/s/√Hz |
| Sensibilidad a la aceleración | — | ≤ 0.1 °/s/g (máx.) |

No hay dato de inestabilidad de sesgo en la hoja del BMI088.

### 5.2 Conexión por SPI (DS fig. 8, p. 53; §6, pp. 44–48)

| Pin BMI088 | Nombre | Conexión |
| --- | --- | --- |
| 3 / 11 | VDD / VDDIO | 3V3 (VDD 2.4–3.6 V, VDDIO 1.2–3.6 V; máximo absoluto 4 V). **100 nF** en cada uno, junto al pin. Sin secuencia obligatoria entre ellos |
| 4 / 6 / 2 | GNDA / GNDIO / NC | GND (NC también a GND) |
| 7 | PS | **GND = SPI** (a VDDIO sería I2C) |
| 8 | SCK | GPIO12 |
| 9 | SDI | GPIO11 (MOSI) |
| 15 + 10 | SDO1 + SDO2 | unidos, a GPIO13 (MISO) |
| 14 | CSB1 (acelerómetro) | GPIO15. Tiene pull-up interno de 75–125 kΩ a VDDIO |
| 5 | CSB2 (giróscopo) | GPIO16. Igual |
| 16 | INT1 (acelerómetro) | GPIO17 |
| 12 | INT3 (giróscopo) | GPIO18 |
| 1 / 13 | INT2 / INT4 | sin conectar (permitido) |

Para el firmware: SPI modo 0 o 3, **máximo 10 MHz**; el acelerómetro arranca en
I2C y pasa a SPI con el primer flanco de subida de CSB1 (hacer una lectura de
ACC_CHIP_ID de descarte); en cada lectura del acelerómetro llega primero un byte de
relleno; tras el encendido el acelerómetro está suspendido: esperar 1 ms, escribir
0x04 en ACC_PWR_CTRL (0x7D) y esperar 450 µs (la guía de diseño dice 50 ms en el
primer encendido); el giróscopo pide hasta 30 ms tras el reset (DS §3, §4.1.2, §6.1).

### 5.3 Huella, ubicación y montaje

- **Ejes** (DS fig. 12, p. 56): con el lado de 4.5 mm horizontal y el pin 1 arriba a
  la izquierda (vista superior), +X apunta hacia el borde de los pines 1–7, +Y hacia
  el pin 16 y +Z sale de la cara superior. Comprobar con la figura antes de dibujar
  la huella. En la placa de la sección 1.4 conviene girarla para que +Y del
  sensor quede a lo largo del eje del jalón (+Z del equipo) y serigrafiar los ejes.
- **Huella** (DS fig. 11 y §8.5, pp. 55–57): pads no definidos por máscara, del ancho
  del pin y 0.1 mm más largos por lado; máscara +0.05 mm; plantilla 80–150 µm con
  aberturas del 70–90 %.
- **Nada en la capa superior bajo el encapsulado**: ni vías, ni pistas, ni cobre
  (DS §8.2 p. 55; las instrucciones de manejo y montaje de Bosch lo prohíben,
  §7). Pistas simétricas saliendo hacia fuera; sin unir los pads directamente a
  rellenos de masa; el indicador del pin 1 sin conectar.
- **Lejos de esfuerzos**: a más de 2 mm de agujeros de tornillo, de cantos y de
  V-cuts; lejos de botones y conectores (puntos de fuerza) y de los apoyos. Al
  separar la placa de sus rieles de montaje en JLC, cortar en vez de partir a mano.
- **Lejos de calor y vibración**: MCU, reguladores, batería, cargador, bobinas de
  conmutación y condensadores cerámicos grandes.
- **Sin resina ni barniz** encima o alrededor.
- **Recalibrar** los offsets con la placa ya montada en la carcasa: la soldadura y
  la flexión los cambian.

Fuente de las cuatro últimas viñetas: «Handling, soldering & mounting instructions»
de Bosch rev 1.6 (may-2025), §6–§7 y §11
(https://www.bosch-sensortec.com/media/boschsensortec/downloads/handling_soldering_mounting_instructions/bst-mis-hs000.pdf).
Ese documento cubre las familias BMI2/BMI3/BMI4/BHI3 y no lista el BMI088, pero la
guía de diseño BMI08x remite a él.


## 6. Fabricación y montaje en JLCPCB (reglas vigentes)

Consultado el 04-10-2026. **No se obtuvo una cotización exacta**: la página de
cotización (https://cart.jlcpcb.com/quote) y la de envíos necesitan JavaScript, y el
API oficial de precios exige solicitar acceso (https://api.jlcpcb.com/). Lo que
sigue son las reglas publicadas. Las páginas de ayuda dicen «Last updated Sep 09,
2026». La fábrica estuvo cerrada del 1 al 4 de octubre y reabre el 5: habrá cola
(https://jlcpcb.com/news/jlcpcb-september-october-2026-holiday-schedule).

### 6.1 Montaje: Economic queda descartado

Las fichas de JLC de las tres piezas principales dicen **«PCBA Type: Standard
Only»** y **«X-ray Inspection: Required»**: UM980 (C9900015354,
https://jlcpcb.com/partdetail/Unicore-UM980/C9900015354), ESP32-S3-MINI-1-N4R2
(C3013941, https://jlcpcb.com/partdetail/3522411-ESP32_S3_MINI_1N4R2/C3013941) y
BMI088 (C194919, https://jlcpcb.com/partdetail/BoschSensortec-BMI088/C194919).
Con cualquiera de ellas el pedido es **Standard**.

| Concepto | Economic | Standard | Fuente |
| --- | --- | --- | --- |
| Preparación | 8.18 USD | **25.56 USD** una cara / 51.12 dos caras | https://jlcpcb.com/help/article/pcb-assembly-price |
| Plantilla (stencil) | 1.53 USD | **8.21 USD** una cara / 16.42 dos | idem |
| Junta SMT | 0.0016 USD | 0.0016 USD (hasta 50 000) | idem |
| Junta manual / THT | 0.0164 USD | 0.0164 USD | idem |
| Carga de alimentador por pieza distinta | 3.07 USD por Extended; Basic y **Preferred Extended exentas** | **1.53 USD por cada pieza distinta, Basic o Extended** (no se publica exención) | idem; https://jlcpcb.com/help/article/pcb-assembly-faqs |
| Rayos X | 1.64 USD/componente (1–10), 0.82 (11–50), 0.49 (51–200) | igual | https://jlcpcb.com/help/article/pcb-assembly-price |
| Embalaje y mínimos | gratis | 0.50 USD + 0.00003 × área (cm²); 0.48 USD mínimo por placa | idem |
| Caras | una | una o dos | https://jlcpcb.com/capabilities/pcb-assembly-capabilities |
| Capas / espesor | 2, 4, 6 / 0.8–1.6 mm | 1–32 / sin límite | idem |
| Tamaño de placa | 10 × 10 a 470 × 500 mm; rieles no necesarios | **70 × 70** a 460 × 500 mm; **rieles necesarios** | idem |
| Cantidad | 2–50 | 2–80 000 | idem |
| LGA/QFN/BGA | sí, con rayos X | sí, con rayos X | idem |

Consecuencias para la placa de 50 × 76 mm de la sección 1.4:

- **Es menor que el mínimo de 70 × 70 de Standard**: hay que pedirla con rieles
  desprendibles (p. ej. 10 mm a cada lado del lado de 50) o en panel de dos
  (≈ 100 × 86 con rieles de 5). Un panel o rieles quitan el precio especial de la
  PCB y suman el cargo de ingeniería
  (https://jlcpcb.com/help/article/in-what-cases-will-there-be-charged-extra).
- **Montaje a una sola cara** (todo en la cara frontal): evita los 51.12 + 16.42 USD
  de dos caras y encaja con la envolvente recomendada.
- Cada pieza distinta cuesta 1.53 USD de alimentador aunque sea Basic: conviene
  repetir valores (pocas referencias de resistencias y condensadores) y la misma
  familia de conectores.

### 6.2 PCB desnuda (5 unidades, FR-4 1.6 mm)

| Concepto | Regla publicada | Fuente |
| --- | --- | --- |
| 2 capas ≤ 100 × 100 mm | 2 USD las 5 (cubre hasta 102 × 102); **desde el 22-08-2026 esa oferta solo se pide desde la aplicación de escritorio JLCONE**. El precio en la web no se verificó | https://jlcpcb.com/help/article/in-what-cases-will-there-be-charged-extra; https://jlcpcb.com/news/jlcpcb-jlcone-desktop-app; https://jlcpcb.com/blog/custom-pcb-cost |
| 4 capas | «4-layer PCBs (10x10cm) start at just $7» (página sin fecha); fuentes secundarias limitan la oferta de 2 USD en 4 capas a ≤ 50 × 50 mm (no confirmado en JLC) | https://jlcpcb.com/features/prototype-pcb-way; https://jlcpcb.com/news/discount-on-quality-4-layer-pcbs (2024) |
| Plazo | 2 capas 24 h; 4 capas 2–5 días (≤ 100 × 100, 5 pzas); con montaje la fabricación de 24 h es gratis | https://jlcpcb.com/help/article/pcb-fabrication-services-and-production-time; https://jlcpcb.com/help/article/smt-service-lead-time-overview |
| Acabado | OSP gratis desde 2 capas; **ENIG ya no es gratis: ≈ 20 USD/m² extra** (30-07-2026; para 5 placas de 50 × 76 son ≈ 0.019 m² → ≈ 0.4 USD más el mínimo que aplique, no publicado); HASL sin plomo: recargo no publicado; ENIG por encima del 30 % de área: 0.8992 USD/m² por cada 1 % | https://jlcpcb.com/news/jlcpcb-pcb-osp-finish; https://jlcpcb.com/help/article/in-what-cases-will-there-be-charged-extra |

Recomendación: **4 capas, ENIG** (pads planos para el LGA de 54 contactos del UM980
y el LGA del módulo ESP32; plano de masa continuo bajo la pista de 50 Ω del u.FL).
Con 2 capas la microcinta de 50 Ω sobre 1.6 mm sale de unos 2.9 mm de ancho y el
UM980 pierde el plano de masa bajo sus pads interiores.

### 6.3 Apilados de 4 capas de 1.6 mm

| Apilado | Preimpregnado L1–L2 y L3–L4 | εr | Núcleo |
| --- | --- | --- | --- |
| **JLC04161H-7628** (el que se aplica con «sin requisito») | 7628, 0.2104 mm | 4.4 | 1.065 mm |
| JLC04161H-3313 | 3313, 0.0994 mm | 4.1 | 1.265 mm |
| JLC04161H-1080 | 1080, 0.0764 mm | 3.91 | 1.265 mm |
| JLC04161H-2116 | 2116, 0.1164 mm | 4.16 | 1.265 mm |

Cobre exterior 0.035 mm, interior 0.0152 mm, núcleo εr 4.6; hay 14 variantes más
(https://jlcpcb.com/impedance). Calculadora: https://jlcpcb.com/pcb-impedance-calculator;
la prueba de impedancia estándar (±20 %) es gratis
(https://jlcpcb.com/help/article/multi-layer-pcb-standard-laminated-structures). Si
hay recargo por elegir un apilado concreto: no verificado.

### 6.4 Piezas que JLC no tiene: el UM980

- **LCSC no vende el UM980.** JLC solo tiene una ficha de encargo, C9900015354
  («Pre-order the parts you need», Standard Only, rayos X, sin precio ni existencias
  publicados).
- DigiKey, 5301-UM980TR-ND: 225 unidades y **188 USD por unidad en 5** (producto de
  marketplace con 50 USD de envío aparte), consultado el 04-10-2026
  (https://www.digikey.com/en/products/detail/unicore-communications-inc/UM980/24387233).
  Paquete LGA de 54 contactos, **17.0 × 22.0 × 2.6 mm** (https://en.unicore.com/products/um980/).
- **Global Sourcing** (JLC compra a distribuidores): 9–20 días hábiles tras 1–3 de
  revisión; no reembolsable; módulos con 3–30 % de arancel; solo para montaje
  (https://jlcpcb.com/help/article/60-how-to-use-jlcpcb-global-sourcing-parts-service;
  https://jlcpcb.com/help/article/pcba-parts-sourcing-instruction).
- **Consignación** desde fuera de China (https://jlcpcb.com/help/article/245-how-to-consign-parts-to-jlcpcb):
  hay que pedir aprobación, enviar al almacén de Hong Kong declarando precio, origen
  y código HS; depósito de arancel + 13 % de IVA (se devuelve al usar las piezas),
  2 % de manejo (mínimo 10 USD); almacenaje gratis 3 años. La página de condiciones
  (https://jlcpcb.com/help/article/246-consignment-part-terms-conditions) da otras
  tarifas (70 USD por 50 referencias, 15 USD de manejo, 8 USD por 48 h de horneado):
  **se contradicen; confirmar con soporte de JLC**.
- Sensibilidad a la humedad del UM980: MSL 3 según un extracto del manual de Unicore
  R1.9 (no leído completo): enviarlo en bolsa sellada y pedir horneado.

### 6.5 Estimación indicativa para 5 placas (cálculo propio, no cotización)

Supuestos: Standard a una cara, ~450 juntas por placa, ~35 piezas distintas, 5
componentes con rayos X por placa (UM980, módulo ESP32, BMI088, BQ25792 QFN y
MAX17048 DFN).

| Partida | Cálculo | USD |
| --- | --- | ---: |
| Preparación + plantilla | 25.56 + 8.21 | 33.77 |
| Alimentadores | 35 × 1.53 | 53.55 |
| Juntas | 5 × 450 × 0.0016 (0.72 por placa: por encima del mínimo de 0.48) | 3.60 |
| Rayos X | 25 × 0.82 | 20.50 |
| Embalaje | 0.50 + 0.00003 × ~270 cm² | 0.51 |
| **Montaje** | | **≈ 112** |
| Piezas sin UM980 (por placa: ESP32 4.48, BMI088 6.02, BQ25792 1.72, MAX17048 1.92, conectores ≈ 2.0, pasivos y resto ≈ 3) | 5 × ≈ 19.1 | ≈ 96 |
| UM980 (DigiKey) | 5 × 188 + 50 de envío | ≈ 990 |
| PCB de 4 capas con rieles o panel, envío a México, impuestos | **no verificado** | — |

Cupones vigentes (no acumulables, uno por pedido): paquete de bienvenida de 123 USD
con 6 USD para PCB, 10 USD para montaje y 10 USD de envío
(https://jlcpcb.com/help/article/new-customer-coupons); los envíos con tarifa especial
y la oferta de 2 USD están ahora en JLCONE. El costo de envío a México no se pudo
calcular.
