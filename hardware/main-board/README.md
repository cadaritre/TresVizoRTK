# Placa principal TresVizo MeridianV (exploratoria, v0.2)

> **Estado:** diseño generado con scripts y revisado con el ERC y el DRC de KiCad 10.0.6.
> **No se ha fabricado ni probado.** Vive en la rama `hw/main-board-kicad`, fuera de `main`,
> porque el propietario la pidió como exploración. Los resultados de las comprobaciones están en
> [Verificaciones](#verificaciones).

La v0.2 (decisión del propietario del 04-10-2026) deja el UM980 en su carrier BDLX y el IMU en la
tapa, los dos por cable, y achica la placa madre de 50 × 76 a **46 × 64 mm** (4 capas, 1.6 mm). Se
agrega una placa pequeña para el USB-C del panel ([../panel-usb](../panel-usb/README.md)). Las dos
se piden juntas en **un solo panel** de JLCPCB, con un BOM y un CPL.

| Bloque | Pieza | Notas |
| --- | --- | --- |
| GNSS | Carrier BDLX RTK_UM98_V1.0.1, fuera de la placa | J301 (SH de 8 pines): COM2 a 115200, PPS, EVENT, RESET_N y su 5 V |
| 5 V del GNSS | TI TPS63070 (buck-boost) | 4.88 V desde VSYS en 1S y en 2S; GPIO45 lo enciende; apagado desconecta la carga |
| MCU | ESP32-S3-WROOM-1-N16R2 | 16 MB de flash y 2 MB de PSRAM quad (05-10-2026: el firmware ya llenaba el 93 % de las ranuras OTA de 4 MB). Mismo chip que la Thing Plus, pero con **GPIO nuevos** (ver [Firmware](#firmware-qué-tiene-que-cambiar)) para rutear el módulo en la misma placa |
| IMU | Breakout BMI088 V1.0 de la tapa, fuera de la placa | J405 (GH de 7 pines): I2C en un segundo bus, con sus dos interrupciones |
| Registro | microSD push-push (SD_MMC 4 bits) | CLK GPIO6, CMD 7, D0 5, D1 4, D2 16, D3 15 y detección en 17 (HIGH con tarjeta) |
| Carga | TI BQ25798 (buck-boost NVDC) | USB-C 5 V a 1 A; 1S por defecto, 2S cambiando resistencias; usar y cargar a la vez |
| Apagado | Modo *ship* del cargador + FET externo | El botón del panel despierta la placa (QON) |
| 3.3 V | TI TPS62903 | 3–17 V, 3 A, modo 100 % |
| Medidor | MAX17048 (MAX17049 en 2S) | I2C 0x36 |
| USB del panel | Placa `panel-usb` | USB-C con datos a ras de la tapa del panel; GH de 8 pines a J101 |

Esquema en [fab/tresvizo-main-schematic.pdf](fab/tresvizo-main-schematic.pdf), mapa de pines y
conectores en [fab/pinout.md](fab/pinout.md), vistas en `fab/*-top.png` / `fab/*-bottom.png` y la
investigación de esta versión en [research/v02.md](research/v02.md). El esquema en PDF, las vistas y
los Gerber los genera `build.py` y solo se guardan en git en los hitos (ver [Regenerar](#regenerar)).

## Decisiones

Decisiones del propietario para la v0.2 (04-10-2026): sin UM980 ni BMI088 en la placa, conectores
GNSS e IMU de entrada lateral, 5 V conmutable para la carrier, placa más chica, placa del USB-C del
panel, un solo pedido, piezas Basic donde las haya y todos los cables con el kit de cables
precrimpados GH y SH (8 pines como máximo). Lo que resultó al aplicarlas, con su motivo:

1. **GNSS por conector (J301).** Pinout del propietario: 1 5V, 2 GND, 3 RXD2 (TX del ESP32),
   4 TXD2, 5 PPS, 6 EVENT, 7 RESET_N, 8 GND. La carrier reparte esas señales en **dos** conectores
   (5 pines: 5V_IN, GND, PPS_OUT; 8 pines: TTL_RXD2, TTL_TXD2, GND, EVENT), así que el cable es un
   **arnés en Y** ([research/v02.md](research/v02.md) §1). **La BDLX no saca RESET_N**: J301.7 queda
   para otra carrier o para soldarlo a mano.
   - Resistencias en serie: **1 kΩ hacia la carrier y 100 Ω desde ella**. El encargo pedía 33 Ω
     «como en v0.1», pero v0.1 usaba 1 kΩ/100 Ω. Se conserva eso porque con la carrier apagada 1 kΩ
     limita a ~3 mA lo que GPIO8 le mete por sus entradas si queda en alto. Con el WROOM-1 el TX ya no
     es U0TXD, así que la ROM no escribe ahí al arrancar. Además,
     33 Ω sería una pieza distinta más.
   - ESD: dos USBLC6 (las de U101) en RXD2, TXD2, PPS y EVENT; RESET_N solo lleva 1 kΩ.
2. **5 V de la carrier: TPS63070** en lugar de un elevador simple. Sirve en 1S y en 2S con el mismo
   BOM, desconecta la carga apagado (un boost común deja la carrier unida a VSYS) y solo suma una
   pieza nueva al BOM. Salida 4.88 V; la carrier pide 4.0–5.5 V (160 mA a 5 V).
3. **IMU por I2C en un GH de 7 pines** (J405), en el orden del header del breakout sin CSB1/CSB2:
   3V3, GND, SDO a GND, SDA, SCL, INT1, INT3. Por qué I2C:
   - Con el tope de 8 pines por conector, SPI perdía una de las dos interrupciones; I2C las conserva.
   - Va en un **segundo bus** (GPIO41 SDA, GPIO42 SCL, 400 kHz), separado del de la OLED.
   - 400 kHz alcanzan para leer acelerómetro y giróscopo a varios cientos de Hz.
   - Necesita menos hilos en el cable que pasa por la tapa que gira.
   - Direcciones: 0x18 (acelerómetro) y 0x68 (giróscopo), con SDO a GND. El selector del breakout
     va en IIC.
4. **Placa de 46 × 64 mm**, la que dejó el estudio mecánico con al menos 2400 mm² útiles. Va de
   frente: panel, placa, carrier y 18650, con rieles en los cantos laterales. Detalles en
   [Mecánica](#mecánica).
5. **Lazos del cargador como en el ejemplo de TI** (hoja del BQ25798, 8.4), corrigiendo la
   auditoría de v0.1:
   - Los 100 nF de PMID (C108) y de SYS (C112) van sobre los pines 29/27 y 25/27, con la GND en T
     al pin 27.
   - PMID lleva 2 × 22 µF y SYS 2 × 22 µF, en columnas a cada lado con cobre ancho, sin cuellos.
   - **SW1 y SW2 bajan por 3 vías cada uno bajo el chip** y van por B.Cu (1 mm) a la bobina. Bajo
     esa zona, la capa interna 3 es GND en lugar de +3V3.
   - *Bootstrap* en la cara superior, cada condensador recto bajo su pin: BTST1 → C101 en 0.9 mm y
     BTST2 → C102 en 1.6 mm (en v0.1, 9 mm). El lado SW de cada uno baja por una vía y llega por B.Cu
     (4.3 y 5.7 mm) a la columna de vías de su nodo SW bajo el chip.
   - La fila inferior del cargador (pines 17–24, paso 0.4) sale en abanico prerruteado: ILIM, BATP,
     PROG, INT, BAT y SDRV, con R103 (PROG) y R107 (BATP) justo debajo de sus pines y C113 (BAT)
     abajo a la derecha.
   - Potencia solo por capas externas, nunca por las internas de 0.5 oz: VBUS prerruteado de J101
     al 22 µF de entrada con 0.8–1.0 mm (aguanta los ~2.2 A de 2S); VSYS, PMID y BAT con 0.4–0.5 mm
     y cuellos de 0.2 mm junto a pads finos.
6. **Conectores de cable de 8 pines o menos, GH o SH de entrada lateral** (kit del propietario):
   - El panel lleva el botón (J402, GH4). Los LEDs (J406) se quitaron el 05-10-2026: la carcasa V2.3 no los lleva y la OLED ya muestra el estado.
   - La OLED pasa a SH4 lateral.
   - El USB del panel pasa a GH8 (J101) con el pinout del propietario: 1-3 VBUS, 4-6 GND, 7 D−,
     8 D+.
   - La batería conserva su PH de 2 pines.
   - **Cada conector apunta a un canto o a una zona libre** (revisión del propietario sobre el
     borrador): delante de cada boca queda, sin componentes, lo que asoma la clavija enchufada y el
     doblez de sus cables, con 1 mm a cada lado para tomarla. Ver [Conectores](#conectores).
7. **TVS de VBUS SMF15A** (limita a 24.4 V, por debajo de los 30 V de VBUS del BQ25798) en lugar
   de la SMF20A (32.4 V).
8. **D+/D− del cargador sin conectar y techo de entrada de 1.45 A** (05-10-2026): las resistencias de D+/D− de v0.1 (entonces R101/R102)
   nunca se montaban (detección BC1.2), y el ESP32-S3 activa el pull-up de D+ desde el reset, lo que
   confundiría esa detección. Con D+/D− al aire el BQ25798 ve un «adaptador desconocido» y el
   límite lo pone ILIM.
   - Antes era ~2.9 A (10k/22k): demasiado para un puerto de computadora.
   - Ahora **R102 = 8.2 kΩ** (10k/8.2k desde REGN, 4.6–5.0 V): techo de **1.34–1.56 A**, que
     alcanza para cargar 1S a 1 A con el equipo encendido (~1.3 A de entrada).
   - La placa sigue sin saber cuánto da el puerto. Con un puerto USB-A de 0.5/0.9 A, el cargador
     baja la corriente si VBUS se cae (VINDPM), y el firmware puede bajar IINDPM por I2C (modo de
     carga lenta).
   - La detección real (CC del USB-C hacia un ADC del ESP32) queda para v0.3; ver
     [Pendientes y riesgos](#pendientes-y-riesgos).
9. **Un solo pedido en JLCPCB** con las dos placas en un panel. Ver
   [Pedido en JLCPCB](#pedido-en-jlcpcb) y [Costo](#costo).
10. **Serigrafía sin solapes**: cada conector lleva su función y su referencia («IMU J405»,
    «NTC J404»…); `silk_clean.py` revisa con el DRC de KiCad que ninguna referencia ni trazo pise
    pads u otra serigrafía, y las huellas cuya serigrafía pisaba sus propios pads se recortaron en
    la biblioteca (`fp_silk_trim.py`: L2520, SOD-882 y el puente de soldadura de JP101).
11. **Logotipo de TresVizo** (el de www.tresvizo.com, tomado del SVG del firmware,
    `firmware/esp32/assets/tresvizo-logo.svg`): completo, de 30 mm, con «www.tresvizo.com» en la
    cara trasera; y el distintivo (hexágono con el 3, de `mechanical/v2.2/logo.json`) en la cara
    de componentes, en el hueco frente al botón, donde no hay piezas.
12. **J404 (NTC) montado de fábrica, con la NTC opcional** (decisión del propietario del
    05-10-2026): sin NTC el cargador tiene que ver 25 °C, así que la resistencia fija R106 (10 kΩ)
    va a GND por **JP101, un puente de soldadura cerrado de fábrica**. Para usar la NTC se corta
    JP101 y se enchufa en J404. Ver [Conectores](#conectores).

## Mecánica

Primer estudio en FreeCAD 1.1.3 sobre una copia de V2.2 ([research/v02.md](research/v02.md) §7) y
comprobación de la placa terminada, con sus modelos 3D y las clavijas enchufadas, contra esa misma
carcasa ([research/v02.md](research/v02.md) §8). Ejes de V2.2: z = eje del jalón hacia arriba,
+Y = panel, +X a la izquierda mirando el panel.

- **Placa:** 46 × 64 mm, FR-4 de 1.6 mm, 4 capas (JLC04161H-7628).
  - Va en el plano x = −23…+23, **z = 23.5…87.5**, con la cara de componentes en y = 3.1 mirando
    al panel. Sube 2.5 mm respecto del primer estudio para dejar 7.6 mm entre el canto inferior y la
    base: ahí asoman las clavijas de la carrier, del NTC y de la batería (la PH de la batería asoma
    3.5 mm y su cable tiene que doblar).
  - Coordenadas en la placa: u = 23 − x, v = 87.5 − z, desde la esquina superior izquierda vista
    desde el panel.
  - Rieles impresos en los dos cantos laterales, **de z 39 a 90**, con 2.5 mm sin componentes en
    cada canto (u 0–2.5 y 43.5–46, v 0–48.5). El de +X se corta en z 53.5–72.4 frente a la antena. Por
    debajo de z 39 no hay riel: ahí llegan a los cantos la microSD y la batería.
  - **2 × M2.5** en agujeros sin metalizar Ø2.7 (sin cobre en Ø5.2): H1 en (u, v) = (12.0, 9.6),
    es decir (x, z) = (11.0, 77.9), y H2 en (40.4, 3.7) = (−17.4, 83.8). Se atornillan desde el
    frente, antes de poner la tapa del panel, a dos brazos impresos detrás de la placa (|x| ≥ 10
    para no tocar el SMA de la carrier).
- **Detrás de la placa:** la carrier BDLX (x −21…+11, y −9.9…+1.1, z 16.4–68.4) con sus
  componentes hacia la placa (0.4 mm de holgura) y el SMA arriba; detrás, la 18650 (eje (0, −19.6),
  z 22–91).
  - Coaxial: SMA acodado ↔ SMA acodado de 100–120 mm por el paso trasero de la plataforma del IMU.
  - Orden de montaje: 18650 por arriba, carrier por abajo y placa por arriba.
- **Alturas de la cara frontal:**
  - 10 mm en general.
  - **Nada frente al botón** (u 17.5–28.5, v 38.5–49.5; solo pistas y el distintivo en
    serigrafía) y como mucho 2 mm bajo el cuerpo del botón (u 14.9–31.1, v 35.9–52.1).
  - 8.15 mm bajo los cables de la OLED (u 15.75–30.25, v 2.5–9.0).
  - Cara trasera sin componentes.
- **Cantos y clavijas** (detalle en [Conectores](#conectores)):
  - Superior (hacia la tapa), boca hacia arriba: IMU (J405), USB del panel (J101, justo bajo el
    J502 de la placa panel-usb). Sobre el canto hay 12 mm libres hasta la plataforma
    del IMU, salvo bajo la placa panel-usb, donde baja el cable del USB.
  - Inferior, boca hacia abajo: microSD (J401), carrier (J301), NTC (J404) y batería (J102); se
    alcanzan quitando la base.
  - Dentro de la placa, boca hacia una zona libre: OLED (J403) hacia la izquierda, bajo los pines de
    la OLED, y botón (J402) hacia la izquierda, junto al botón.
  - Antena del ESP32-S3-WROOM-1 en el canto izquierdo (+X), u 0–6.7, v 15.7–33.7 sin cobre en
    ninguna capa; el módulo sobresale de ahí hacia dentro hasta u 26.
- **La carcasa necesita cambios** (propuesta, no aplicada al CAD): quitar la placa del respaldo y
  los toalleros; recortar los nervios a y ≤ −10.5; rieles en z 39–90 (cortado en z 53.5–72.4 el de
  +X); brazos detrás de la placa en (x, z) = (11.0, 77.9) y (−17.4, 83.8); **una ranura de 3 mm
  de hondo en la base bajo J102** (x −21.5…−13.5, y 2.5…8.5), para que la base no pellizque los
  cables de la batería; topes del carrier; repisa de la 18650; y en la tapa del panel, el hueco y
  las ménsulas del USB-C (ver [../panel-usb](../panel-usb/README.md)).
- **2S** no cabe en este orden sin un recorte de 11 × 11 mm frente al botón; ver
  [Antes de mandar a fabricar](#antes-de-mandar-a-fabricar).

**Comprobación de la placa terminada** (FreeCAD, [research/v02.md](research/v02.md) §8):

- Placa, componentes y clavijas enchufadas: 0 mm³ de choques con la carcasa y con los rieles
  propuestos.
- Paso por Ø52: radio máximo 23.21 mm.
- Lo más justo:
  - los cables de la batería, a 0.46 mm de la base (de ahí la ranura propuesta en la base, que
    les deja ~3.5 mm);
  - la cara trasera, a 0.40 mm del carrier;
  - la cara de la placa, a 2.51 mm del botón.
- Con el ESP32-S3-WROOM-1 (06-10-2026): la placa (STEP de `kicad-cli`, con el modelo del WROOM
  puesto donde su `.wrl`) contra las piezas de la carcasa V2.3: 0 mm³ de choques; radio máximo
  23.35 mm. Sin plástico frente a la antena (`check_v2_3.py`).
- Los rieles y brazos del primer estudio sí chocan con la placa nueva: hay que hacerlos con la
  propuesta de arriba.

## Conectores

Todos los de cable son JST GH (1.25 mm) o SH (1.0 mm) de entrada lateral, de 8 pines como máximo,
salvo la batería. Los cables se arman con el kit de cables precrimpados GH y SH del propietario:
cada cable se inserta en su cavidad, **pin 1 con pin 1**, y se mide con el multímetro antes de
enchufar. Tablas completas, generadas desde la netlist, en [fab/pinout.md](fab/pinout.md).

**Dónde va cada uno y hacia dónde apunta.** Cada conector lateral apunta a un canto o a una zona
sin componentes. Delante de su boca se reserva lo que asoma la clavija enchufada, más el doblez de
sus cables y 1 mm a cada lado para tomarla:

- GH: la clavija asoma 3.1 mm y mide 4.35 mm de alto (JST eGH, «Assembly layout»).
- SH: asoma 3.0 mm y mide 2.95 mm de alto.
- PH: asoma 3.5 mm (estimado) y mide 4.5 mm.
- Para el doblez de los cables: 3 mm en GH y SH, 4 mm en PH.

Esas reservas son áreas de regla `clavija_*` en el PCB: el DRC falla si una pieza entra en ellas.
También van en `kicad/plugs.json` para la comprobación en CAD.

| Ref. | Uso | Dónde y hacia dónde | Cabezal en la placa (LCSC) | Carcasa del cable (LCSC) | Contacto (LCSC) | Cable armado (búsqueda) |
| --- | --- | --- | --- | --- | --- | --- |
| J405 | IMU: 3V3, GND, SDO, SDA, SCL, INT1, INT3 | Canto superior, a la izquierda; boca hacia arriba (el cable sigue a la tapa) | GH 7 lateral SM07B-GHS-TB (C495552) | GHR-07V-S (C22465387) | SSHL-002T-P0.2 (C189897) | «cable JST GH 1.25 7 pines una cabeza» o precrimpados |
| J101 | USB del panel: 1-3 VBUS, 4-6 GND, 7 D−, 8 D+ | Canto superior, al centro, justo bajo el J502 de la placa panel-usb; boca hacia arriba | GH 8 lateral XUNPU WAFER-GH1.25-8PWB, huella de JST SM08B-GHS-TB (C3029383) | GHR-08V-S (C485357) | SSHL-002T-P0.2 (C189897) | «cable JST GH 1.25 8 pines doble cabeza PIN1-PIN1», el más corto |
| J403 | OLED, orden Qwiic: GND, 3V3, SDA, SCL | Bajo los pines de la OLED; boca hacia la izquierda, sobre una zona libre de 6 × 7 mm | SH 4 lateral SM04B-SRSS-TB (C160404) | SHR-04V-S (C385125) | SSH-003T-P0.2-H (C263995) | «cable Qwiic» o «cable JST SH 1.0 4 pines» |
| J402 | Botón: GND, contacto, anillo LED A, K | A la izquierda del botón; boca hacia la izquierda, sobre una zona libre de 6.1 × 8.3 mm (el cable da la vuelta hacia el botón) | GH 4 lateral SM04B-GHS-TB (C189895) | GHR-04V-S (C160418) | SSHL-002T-P0.2 (C189897) | «cable JST GH 1.25 4 pines una cabeza» |
| J401 | microSD (zócalo push-push) | Canto inferior, a la izquierda; la tarjeta entra por abajo quitando la base | TF-015 (C113206) | — | — | — |
| J301 | Carrier GNSS (arnés en Y) | Canto inferior, al centro; boca hacia abajo | **SH 8** lateral SM08B-SRSS-TB (C160407) | SHR-08V-S (C265412); en la carrier, **soldado** a sus filas de agujeros (sin clavijas) | SSH-003T-P0.2-H (C263995) | «cable JST SH 1.0 8 pines una cabeza» |
| J404 | NTC de la celda (el conector va montado; la NTC es opcional) | Canto inferior, entre J301 y J102; boca hacia abajo | SH 2 lateral SM02B-SRSS-TB (C160402) | SHR-02V-S (C398472) | SSH-003T-P0.2-H (C263995) | «cable JST SH 1.0 2 pines una cabeza» |
| J102 | Batería: 1 = BAT−, 2 = BAT+ | Canto inferior, a la derecha; boca hacia abajo | **JST PH 2.0 mm**, 2 pines, lateral S2B-PH-SM4-TB (C295747) | PHR-2 (C157955) | SPH-002T-P0.5S (C111515) | La del pack: **confirmar paso y polaridad** |

- **J404 viene montado; la NTC es opcional.** TS del cargador es un divisor de REGN (5.1 kΩ
  arriba, 30 kΩ abajo) con la NTC en paralelo con los 30 kΩ:
  - **Sin NTC** no hay que hacer nada: R106 (10 kΩ, lo que mide una NTC 10k a 25 °C) va a GND por
    **JP101**, un puente de soldadura **cerrado de fábrica**, y el cargador ve 25 °C (TS ≈ 60 % de
    REGN).
  - **Con NTC** (10k B3435, pegada a la celda): **cortar JP101** con un cúter (la pista fina entre
    sus dos pads; comprobar con el multímetro que quedó abierto) y enchufar la NTC en J404. Sobre
    JP101 la serigrafía dice «cortar JP101» y, debajo, «NTC J404». Si no se corta, la NTC queda en
    paralelo con R106 y la temperatura que ve el cargador sale mal.
  - **JP101 cortado y sin NTC**: TS sube a ~85 % de REGN, el cargador lo toma como frío extremo y
    no carga. Para volver a la resistencia fija, unir los pads de JP101 con una gota de estaño.
- **J101 va justo bajo la placa panel-usb.** El cable entre J101 y J502 queda muy corto en línea
  recta: usar el más corto del kit y dejar el sobrante doblado en el hueco sobre el canto.

Cuidados:

- **J301 es SH de 8 pines y J101 GH de 8**: con familias distintas no se pueden cruzar. Antes eran
  los dos GH 8, y un cable del USB enchufado en el GNSS ponía VBUS contra GND.
- **Con el pinout de J101, un cable en espejo (pin 1 con 8) pone VBUS contra GND.** Medirlo pin a
  pin antes de enchufar.
- Ningún par de conectores comparte familia y número de pines.

## Firmware: qué tiene que cambiar

El WROOM-1 se ruteó con GPIO nuevos (en el S3 la SD_MMC, las UART y el I2C van por la matriz de
GPIO, así que solo cambia la configuración):

| Función | GPIO |
| --- | --- |
| microSD (SD_MMC 4 bits) | CLK 6, CMD 7, D0 5, D1 4, D2 16, D3 15: `SD_MMC.setPins(6, 7, 5, 4, 16, 15)` |
| Detección de la microSD | 17 (HIGH con tarjeta) |
| UART del GNSS (COM2 a 115200) | TX 8 (a RXD2), RX 9 (de TXD2) |
| PPS, EVENT, RESET_N | 10, 11 (salida, 100 k a GND), 12 |
| I2C de la OLED, cargador y medidor | SDA 13, SCL 14 |
| IMU (`Wire1`, 400 kHz) | SDA 41, SCL 42, INT1 2, INT3 1 |
| Botón / anillo del botón | 18 / 48 |
| INT del cargador / ALRT del medidor | 21 / 47 |
| 5 V de la carrier (TPS63070) | 45 |
| Consola (UART0) | 43/44, sin conectar en la placa |
| Libres | 35, 36 y 37 (con punto de prueba), 38, 39, 40 y 46 |

- **Particiones**: con 16 MB de flash las dos ranuras OTA pueden crecer a ~6 MB (hoy 1.875 MB).
- **Sin LEDs del panel**: quitar o desactivar su código sin quitar claves de la API («la API solo
  crece»).

- **Identidad nueva** (`hardware_id`, entorno de compilación): la API solo crece.
- **Apagado = modo *ship* del BQ25798 por I2C**:
  - Al arrancar, escribir `SFET_PRESENT = 1` (REG0x14 bit 7), ICHG = 1 A y desactivar el
    *watchdog*.
  - Para apagar: cerrar la microSD, apagar el GNSS, esperar a que se **suelte** el botón y
    escribir REG0x11 `SDRV_CTRL = 10` con `SDRV_DLY = 1`.
  - Con USB conectado la orden se ignora (estado `power_still_present`).
- **GPIO45 enciende el 5 V de la carrier** (TPS63070); el firmware 0.8.x ya lo pone alto al
  arrancar. En modo «solo carga» se deja bajo. Con la carrier apagada, dejar GPIO8 en alta
  impedancia para no alimentarla por sus entradas.
  - GPIO45 es pin de arranque con 100k a GND (VDD_SPI a 3.3 V, lo correcto para el N16R2): en
    **cualquier reinicio del ESP32, también por software, la carrier se apaga** y el GNSS arranca
    de cero (pierde el fix RTK). El firmware no debe reiniciar el ESP32 a la ligera.
- **Modo «solo carga»**: si al arrancar hay VBUS y no se pulsa el botón, dejar el GNSS apagado y
  mostrar la carga en la OLED. Un toque del botón pasa a modo normal; al quitar el USB se escribe el
  modo *ship*.
- RESET_N se usa en drenador abierto con un pulso de ≥ 5 ms, pero la BDLX no lo saca.
- El STAT del cargador queda al aire: el estado de carga se lee por I2C.
- **1S**: apagar por batería baja con ≥ 3.5 V en reposo; en modo *ship* el BQ2579x necesita la
  celda por encima de ~3.4 V.

## Variantes 1S / 2S

| Ref. | 1S (por defecto) | 2S |
| --- | --- | --- |
| R103 (PROG) | 4.7 kΩ | 8.2 kΩ (C25924) |
| R102 (ILIM, techo de entrada) | 8.2 kΩ: ~1.45 A | 22 kΩ (C25768): ~2.9 A |
| R116 (EN del TPS62903) | 10 kΩ | 3.9 kΩ (C51721) |
| U103 | MAX17048G+T10 | MAX17049G+T10 (C18185545; JLCPCB tenía 50 a 9.60 USD) |
| R112 (VPACK → VDD del medidor) | 0 Ω | sin montar |
| R114 (+3V3 → VDD del medidor) | sin montar | 0 Ω |
| Batería | 1 × 18650 protegida | 2 × 18650 en serie **con BMS de equilibrado** (el BQ25798 no equilibra) |

- **5 V de la carrier:** el TPS63070 trabaja igual en las dos variantes.
- **Cargador USB-C:** con 2S el cargador eleva desde 5 V y pide ~2.2 A de entrada; usar uno de 3 A.
- **Anillo del botón:** se alimenta de VSYS; con 2S usar la versión de 6 V del botón.
- **Mecánica:** 2S no cabe en la carcasa tal cual (ver [Mecánica](#mecánica)).

## Pedido en JLCPCB

Archivos del pedido, que llevan **las dos placas en un panel**:

- `fab/tresvizo-panel-gerbers-jlcpcb.zip` (lo genera `build.py`; en git solo en los hitos)
- `fab/tresvizo-panel-bom-jlcpcb.csv`
- `fab/tresvizo-panel-cpl-jlcpcb.csv`

Los `fab/tresvizo-main-*` y los de `../panel-usb/fab` son de cada placa sola, por si se piden por
separado.

1. **PCB**:
   - Subir el zip del panel.
   - 4 capas, 1.6 mm, apilado JLC04161H-7628 (por defecto).
   - **Delivery Format: Panel by Customer**, **Different Design: 2**, tamaño del panel
     **82.8 × 79.0 mm** y cantidad en paneles (un panel = un juego de las dos placas).
   - Acabado ENIG recomendado (o HASL sin plomo).
2. **Montaje**:
   - PCBA **Standard** (la estimación de costo la usa; si el cotizador ofrece Economic para el
     ESP32-S3-WROOM-1, también sirve).
   - Una cara (top).
   - El panel ya trae rieles de 5 mm, 3 fiduciales de 1 mm con el centro a 3.85 mm del canto y 4
     agujeros de herramienta de 2 mm, como pide JLCPCB. Las placas van unidas con puentes de 5 mm con
     *mouse bites* (agujeros de 0.6 mm): dos en cada canto lateral de la placa madre (uno de ellos la
     une a la panel-usb) y uno a cada lado de la panel-usb. Arriba y abajo de la placa madre no hay
     puentes porque esos cantos llevan conectores.
   - Los puentes de la placa madre a v 10.5 y 15.1 caen donde van los rieles: **lijar la rebaba** al
     separar las placas.
   - El USB-C de la panel-usb sobresale 1.29 mm del canto de su placa. Frente a él la fresa se
     ensancha de 2 a 3 mm (`cuts` en `kicad/panel.json`), así que quedan 1.71 mm hasta el marco. El
     marco crece 1 mm hacia arriba para que el riel conserve sus 5 mm.
3. Subir BOM y CPL del panel y elegir «Complete File, just proceed with my own files».
   **Revisar la orientación de cada pieza en la vista previa** (sobre todo U201 con la antena hacia el canto
   izquierdo, U102, U105, U301, Q1xx, D1xx y los conectores).
4. La única pieza sin montar (DNP) es R114 (0 Ω de 2S) y queda fuera del BOM. JP101 es un puente
   de cobre de la propia placa: no va en el BOM ni en el CPL. J404 sí se monta.

## Costo

Estimación de [fab/costo-jlcpcb.md](fab/costo-jlcpcb.md) para **5 juegos**, con precios y
existencias de la API pública de JLCPCB del 06-10-2026 y las tarifas de su página (no es una
cotización):

| Pedido | Montaje + piezas | Por juego |
| --- | ---: | ---: |
| (A) Un panel con las dos placas, PCBA Standard | 209.11 USD | 41.82 USD |
| (B) Dos pedidos: principal Standard + panel-usb Economic | 221.86 USD | 44.37 USD |

- El panel único ahorra **12.75 USD** en montaje, y además es un solo envío.
- **No incluye el PCB desnudo** (4 capas, panel con dos diseños): JLCPCB no publica ese precio ni
  el cargo por diseño distinto; sale en el cotizador.
- Lo que más pesa: los alimentadores de PCBA Standard (40 piezas distintas × 1.53 USD = 61.20 USD)
  y las piezas (102.61 USD, sobre todo el ESP32-S3-WROOM-1-N16R2 a 5.80 USD, el BQ25798 y el MAX17048).
- J301 en SH 8 suma 2.25 USD a los 5 juegos frente al GH 8 compartido con J101: un alimentador más
  (1.53 USD) y 5 conectores de 0.33 USD en lugar de 0.19.
- J404, ahora montado, suma 2.22 USD a los 5 juegos: su alimentador (1.53 USD), 5 conectores
  (0.66 USD) y 20 juntas (0.03 USD).
- **PCBA Standard** en la placa madre: la estimación la usa. La API de JLCPCB no dice si el
  ESP32-S3-WROOM-1-N16R2 admite Economic (no pide rayos X); confirmarlo en el cotizador.
- Piezas *Extended* que quedan: no tienen equivalente *Basic* en JLCPCB (cargador, medidor,
  reguladores, ESP32, conectores GH/SH, TVS, ESD y la de 8.2 kΩ de ILIM; ver [research/v02.md](research/v02.md) §4).
- Todas tienen existencias (la menor: ESP32-S3-WROOM-1-N16R2, 1243; sin rayos X).

## Antes de mandar a fabricar

| Punto | ¿Frena el pedido? | Qué hacer |
| --- | --- | --- |
| Orientación de cada pieza en el CPL | Sí | Revisarla en la vista previa de JLCPCB y corregir el giro ahí |
| **Batería: conector y polaridad** | Sí | J102 es JST PH de 2.0 mm, pin 1 = BAT− y pin 2 = BAT+. **Confirmar que el pack tiene ese conector y esa polaridad** (medir con multímetro). La placa tiene protección contra inversión |
| Pinout de los conectores de la carrier | Sí, para el arnés | Leído de la serigrafía de la foto oficial; que el pin 1 sea el pad cuadrado es una suposición (no hay plano). **Antes de enchufar el arnés, medir con multímetro en la carrier cuál pin es GND y cuál 5V_IN**: si estuviera al revés, los 5 V de J301 entrarían a una línea TTL del UM980 |
| Breakout BMI088 | Sí, para el cable | El orden del header (1 VCC … 9 INT3) salió de fotos del vendedor. Comprobarlo con multímetro, poner el selector en IIC y confirmar que SDO va a la hilera |
| Cable GH de 8 pines de J101 | Sí | Con el pinout de J101 un cable en espejo pone VBUS contra GND: medirlo pin a pin. J301 es SH 8 y no se confunde con él |
| Anillo del botón | Sí, si es el de 12 V | La placa lo alimenta con VSYS (3.5–4.2 V en 1S): usar el de 3–6 V |
| Carcasa | No | Hecha: [V2.3](../../mechanical/v2.3/README.md), con chasis deslizable para esta placa (rieles, H1/H2, corte frente a la antena del WROOM, ranuras de la carrier y ménsulas atornilladas de la panel-usb). Comprobada en CAD con la placa final: 0 choques en su sitio y en el montaje paso a paso; nada impreso todavía |
| Cable USB entre J101 y la panel-usb | No | Los dos conectores quedan casi enfrentados: usar el cable GH8 más corto del kit, pin 1 con pin 1, y doblar el sobrante sobre el canto |
| Rebabas de los puentes del panel | No | Lijar las de los cantos laterales de la placa madre antes de meterla en los rieles |
| NTC (J404 montado, JP101 cerrado) | No | Sin NTC no hay que hacer nada. Para la protección térmica de la celda: cortar JP101 y enchufar en J404 una NTC 10k B3435 pegada a la celda. Con JP101 cortado y sin NTC, el cargador no carga |
| Carrier: espesor, cantos y acceso a sus conectores | No | Resuelto en la carcasa V2.3 con las medidas de la foto más 1 mm de holgura (9 mm de grueso, aire para las patas del SMA). La carrier no tiene margen en los cantos: las ranuras del chasis dejan sitio a su USB-C, que sobresale ~0.9 mm, y a las soldaduras del arnés de J301 en la columna de agujeros pegada al otro canto (modelo por componentes en [cad/carrier_bdlx.py](cad/carrier_bdlx.py)). El arnés va soldado a la carrier |
| 2S | No para 1S | No cabe sin recorte frente al botón; decidirlo antes de rehacer la carcasa |
| Antena del ESP32 a 6.8 mm de la carrier | No | Medir RSSI en el primer prototipo |
| Firmware para esta placa | No para fabricar | Todavía no existe; ver [Firmware](#firmware-qué-tiene-que-cambiar) |
| Nada medido | — | Pedir pocas placas y probar por bloques, empezando por la alimentación |

## Verificaciones

Lo comprobado con las herramientas (nada se ha fabricado ni medido):

| Comprobación | Resultado |
| --- | --- |
| ERC (KiCad 10.0.6), placa madre y panel-usb | 0 errores, 0 avisos |
| DRC placa madre ([fab/drc.rpt](fab/drc.rpt)) | 0 errores, 0 avisos, 0 sin conectar, 0 diferencias de paridad con el esquema |
| DRC panel-usb ([../panel-usb/fab/drc.rpt](../panel-usb/fab/drc.rpt)) | 0 errores, 0 avisos, 0 sin conectar, 0 de paridad |
| DRC del panel ([fab/drc-panel.rpt](fab/drc-panel.rpt)) | 0 errores, 0 avisos, 0 sin conectar; 82.8 × 79.0 mm |
| Clavijas enchufadas | Áreas `clavija_*` en el DRC: ninguna pieza dentro. En CAD: 0 mm³ contra la carcasa y los componentes; la más justa, la batería (0.46 mm a la base sin la ranura propuesta) |
| Rieles, botón y antena | Áreas `riel_*`, `boton` y `esp32_antena` en el DRC: sin violaciones |
| Serigrafía | 0 solapes ni serigrafía sobre pads (DRC); textos de 0.8 mm o más; el logotipo no tiene trazos de menos de 0.35 mm (apertura morfológica), sobre el mínimo de 0.15 mm de JLCPCB |
| Ruteo | 133 de 133 conexiones con `route_rest.py`, el bus de la microSD primero; potencia solo por capas externas. Reproducible: dos ejecuciones completas de `build.py` (06-10-2026) dieron los mismos PCB, esquemáticos, BOM, CPL, mapa de pines y Gerber; solo cambian las fechas dentro de los informes, de los netlists y de los Gerber |
| *Bootstrap* del cargador | BTST1 → C101: 0.9 mm; BTST2 → C102: 1.6 mm (cara superior). Retorno a SW por vía y 4.3 / 5.7 mm de B.Cu |
| Mecánica (primer estudio y placa terminada) | Ver [research/v02.md](research/v02.md) §7 y §8 |
| Montaje en la carcasa V2.3 (`b94647d`) | Con la placa de este diseño y la carrier aproximada con sus componentes: sin choques paso a paso, la placa entrando por abajo; ver [cad/README.md](cad/README.md) |
| Costo y existencias | API de JLCPCB del 05-10-2026: todas las piezas con existencias |

No comprobado: fabricación y montaje, ninguna medida eléctrica, el firmware para esta placa, el
pinout real de la carrier y del breakout BMI088, el lugar exacto de los conectores en la carrier, el
asomo de la clavija PH de la batería (3.5 mm estimado; JST no da el plano enchufado) y la carcasa
impresa con los cambios propuestos.

## Pendientes y riesgos

- **Corriente del USB (revisión del 05-10-2026):** sin detección del puerto, el techo fijo (R102)
  es la única protección para una computadora. Para v0.3: llevar CC1/CC2 de la panel-usb (OR con
  diodos) por uno de los GND de J101/J502 a un ADC del ESP32 y fijar IINDPM según lo que anuncie la
  fuente (0.5 / 1.5 / 3 A).
- **D+/D− (revisión del 06-10-2026):** D+ mide 37.6 mm con 3 vías (F.Cu, B.Cu e In2.Cu); D− mide
  34.3 mm con 4 vías (F.Cu y B.Cu). No van juntos como par.
  - Para USB Full Speed (12 Mb/s, lo único que tiene el ESP32-S3) la diferencia, unos 22 ps, es
    despreciable frente a un bit de 83 ns. La pista entera equivale a ~0.25 ns, frente a flancos de
    4 ns o más.
  - Aun así, Espressif recomienda par diferencial con referencia continua.
  - El cruce viene del orden de pines: D− va a la izquierda de D+ en J101 y al revés en U101 y el
    ESP32. Corregirlo pide invertir los pines 7/8 de J101 y de J502 (la panel-usb también) y
    rutear el par junto. Queda para v0.3 junto con el CC.

- **Nada medido**: carga 1S/2S, modo *ship*, arranque del TPS63070 con la carrier y su consumo,
  ruido del GNSS (C/N0) con el ESP32 transmitiendo, alcance de BLE/Wi-Fi.
- **Antena del ESP32**: Espressif pide 15 mm libres; en el tubo hay 5.85 mm hasta la pared y
  6.8 mm hasta la carrier.
- **Bootstrap del BQ25798**: los condensadores quedan junto a sus pines en la cara superior, pero
  su retorno a SW pasa por una vía y 4–6 mm de B.Cu; TI lo muestra con los condensadores en la cara
  inferior, que aquí no se puede usar.
- **Plano interno de 3V3** perforado por las vías del ruteo automático: quedan tiras y cuellos finos
  (el DRC no encuentra cuellos bajo 0.127 mm, pero conviene mirarlo a mano antes de pedir). Los
  planos internos van con 0.12 mm de margen a otras redes (JLCPCB admite 0.09 mm en capas internas)
  para que las vías dejen menos tiras.
- **TS sin NTC**: con JP101 cerrado, R106 pone 25 °C y la celda no tiene protección térmica de
  carga dentro de un tubo al sol. Recomendado: NTC en J404 y JP101 cortado.
- **Hoja del BQ2579x rev D**: la copia pública dice «TI Confidential»; pedir la oficial.
- **Ruteo automático** con `route_rest.py`, un ruteador propio (A* en rejilla con arranque y
  reruteo). Las pistas críticas están prerruteadas en `layout.py`:
  - lazos del cargador, nodos SW, *bootstrap*, BAT y la salida en abanico de su fila inferior;
  - el TPS62903 según su hoja de datos: SW a L102 en 0.9 mm por F.Cu sin vías, C115 (10 µF de entrada)
    a 0.4 mm de VIN y de GND con EN saliendo entre sus pads, C118 y C119 (salida) junto a L102 y GND,
    y FB con su divisor a 1.5 mm. Antes el SW daba un rodeo de 8.7 mm con dos vías y pasaba entre los
    pads de C115;
  - el lazo del TPS63070 y su EN;
  - CELL y VDD del medidor;
  - las GND cercadas del cargador y de C303.
  
  El resto se nota automático (escaleras de tramos de 0.1 mm, pistas bajo el ESP32).
  `finish_pcb.py` une con un tramo corto las vías que el ruteador deja tocando de canto una pista de
  su misma red.
- **Modelo 3D del BQ25798**: KiCad no trae el del RQM0029A; el STEP usa un VQFN de 4 × 4 mm.

## Regenerar

Requisitos: KiCad 10 (con su Python) y Python 3. KiCad tiene que tener sus bibliotecas estándar en
las tablas globales (Preferencias → Gestionar bibliotecas); si no, el ERC y el DRC añaden cientos de
avisos de «biblioteca no incluida» que no son errores del diseño.

```bash
cd hardware/main-board/scripts
KICAD_APP=/Applications/KiCad/KiCad.app python3 build.py
python3 cost_jlc.py ../fab/costo-jlcpcb.md 5 ../fab/tresvizo-main-bom-jlcpcb.csv ../kicad/tresvizo-main.kicad_pcb ../../panel-usb/fab/tresvizo-panel-usb-bom-jlcpcb.csv ../../panel-usb/kicad/tresvizo-panel-usb.kicad_pcb
```

`build.py` hace todo el pedido:

- Placa madre:
  - `circuit.py` escribe el esquemático.
  - `layout.py` fija contorno, colocación, pistas críticas, zonas, clases de red y el panel.
  - `build_pcb.py` construye el PCB y `fanout.py` baja los pads de GND y +3V3 a sus planos.
  - `route_rest.py` rutea el resto y `finish_pcb.py` añade los rellenos de GND con vías de cosido.
- Placa del USB-C: la regenera con su propio `build.py` (`../panel-usb`).
- Panel: `panelize.py` junta las dos placas con rieles, fiduciales, agujeros de herramienta y mouse
  bites.
- Pedido: `export_jlc.py` saca BOM y CPL de cada placa y del panel.

Otros scripts:

- `cost_jlc.py` compara el panel único con dos pedidos separados.
- `mklib.py` genera los símbolos propios.
- `logo.py` convierte el logotipo del repositorio en polígonos de serigrafía.
- `silk_clean.py` (dentro de `build.py`) corrige la serigrafía que el DRC marca encimada.
- `fp_silk_trim.py` recorta la serigrafía de una huella de la biblioteca que pisa sus propios pads
  (se usó una vez, con L2520, SOD-882 y `SolderJumper-2_P1.3mm_Bridged_RoundedPad1.0x1.5mm`,
  copiada de la biblioteca estándar de KiCad).
- `layout.py` escribe además `kicad/plugs.json`: las clavijas enchufadas y los agujeros, para
  comprobarlos en CAD contra la carcasa.
- El proyecto del panel usa la biblioteca de la placa madre; `build.py` le copia la huella y el
  modelo del USB-C que solo tiene `../panel-usb`.
- Las huellas de `kicad/lib/lcsc.pretty` vienen de LCSC/EasyEDA (easyeda2kicad), para que la
  orientación coincida con la de JLCPCB.

No se guardan en git, por pesados y regenerables:

- los modelos STEP de LCSC (los `.wrl` sí);
- la caché de easyeda2kicad;
- los STEP de las placas;
- los Gerber (`fab/*-gerbers-jlcpcb.zip`), las vistas (`fab/*-top.png`, `fab/*-bottom.png`) y el esquema
  en PDF: cambian en cada vuelta. Se guardan solo en los hitos (pedido a JLCPCB, versión cerrada), con
  `git add -f`.

El build es reproducible: con las mismas entradas, dos ejecuciones de `build.py` dan los mismos archivos
byte a byte (solo cambia la fecha dentro de los informes del DRC y del ERC). Para eso:

- `kiid_seed.py` siembra los identificadores (KIID) de KiCad en cada paso con el contenido de sus
  entradas. KiCad ordena el PCB por esos identificadores, que de otro modo son aleatorios.
- `route_rest.py` toma del DRC solo qué dos islas faltan por unir y elige siempre los mismos extremos.
  El DRC no nombra siempre el mismo objeto de cada isla.

Si un paso se cae, `build.py` dice cuál y, si fue por una señal, cuál. Por ejemplo, el rellenador de
zonas de KiCad 10 se ha caído con la señal 11 con ciertas geometrías. `route_rest.py` guarda lo ruteado
antes de rellenar, para no perderlo.

La investigación con sus fuentes está en `research/`: v0.1 en los archivos originales y v0.2 en
[research/v02.md](research/v02.md).
