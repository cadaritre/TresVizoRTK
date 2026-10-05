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
| GNSS | Carrier BDLX RTK_UM98_V1.0.1, fuera de la placa | J301 (GH de 8 pines): COM2 a 115200, PPS, EVENT, RESET_N y su 5 V |
| 5 V del GNSS | TI TPS63070 (buck-boost) | 4.88 V desde VSYS en 1S y en 2S; GPIO45 lo enciende; apagado desconecta la carga |
| MCU | ESP32-S3-MINI-1-N4R2 | El mismo módulo que la Thing Plus: se conservan los GPIO del firmware 0.8.x |
| IMU | Breakout BMI088 V1.0 de la tapa, fuera de la placa | J405 (GH de 7 pines): I2C en un segundo bus, con sus dos interrupciones |
| Registro | microSD push-push (SD_MMC 4 bits) | Mismos GPIO que la Thing Plus; detección HIGH con tarjeta |
| Carga | TI BQ25798 (buck-boost NVDC) | USB-C 5 V a 1 A; 1S por defecto, 2S cambiando resistencias; usar y cargar a la vez |
| Apagado | Modo *ship* del cargador + FET externo | El botón del panel despierta la placa (QON) |
| 3.3 V | TI TPS62903 | 3–17 V, 3 A, modo 100 % |
| Medidor | MAX17048 (MAX17049 en 2S) | I2C 0x36 |
| USB del panel | Placa `panel-usb` | USB-C con datos a ras de la tapa del panel; GH de 8 pines a J101 |

Esquema en [fab/tresvizo-main-schematic.pdf](fab/tresvizo-main-schematic.pdf), mapa de pines y
conectores en [fab/pinout.md](fab/pinout.md), vistas en `fab/*-top.png` / `fab/*-bottom.png` y la
investigación de esta versión en [research/v02.md](research/v02.md).

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
     limita a ~3 mA lo que GPIO43 le mete por sus entradas (la ROM escribe ahí al arrancar). Además,
     33 Ω sería una pieza distinta más.
   - ESD: dos USBLC6 (las de U101) en RXD2, TXD2, PPS y EVENT; RESET_N solo lleva 1 kΩ.
2. **5 V de la carrier: TPS63070** en lugar de un elevador simple. Sirve en 1S y en 2S con el mismo
   BOM, desconecta la carga apagado (un boost común deja la carrier unida a VSYS) y solo suma una
   pieza nueva al BOM. Salida 4.88 V; la carrier pide 4.0–5.5 V (160 mA a 5 V).
3. **IMU por I2C en un GH de 7 pines** (J405), en el orden del header del breakout sin CSB1/CSB2:
   3V3, GND, SDO a GND, SDA, SCL, INT1, INT3. Por qué I2C:
   - Con el tope de 8 pines por conector, SPI perdía una de las dos interrupciones; I2C las conserva.
   - Va en un **segundo bus** (GPIO11 SDA, GPIO12 SCL, 400 kHz), separado del de la OLED.
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
   - Potencia solo por capas externas (VBUS, VSYS, PMID, BAT: 0.4–0.5 mm, con cuellos de 0.2 mm
     junto a pads finos), nunca por las internas de 0.5 oz.
6. **Conectores de cable de 8 pines o menos, GH o SH de entrada lateral** (kit del propietario):
   - El panel se partió en botón (J402, GH4) y LEDs (J406, SH5).
   - La OLED pasa a SH4 lateral.
   - El USB del panel pasa a GH8 (J101) con el pinout del propietario: 1-3 VBUS, 4-6 GND, 7 D−,
     8 D+.
   - La batería conserva su PH de 2 pines.
   - **Cada conector apunta a un canto o a una zona libre** (revisión del propietario sobre el
     borrador): delante de cada boca queda, sin componentes, lo que asoma la clavija enchufada y el
     doblez de sus cables, con 1 mm a cada lado para tomarla. Ver [Conectores](#conectores).
7. **TVS de VBUS SMF15A** (limita a 24.4 V, por debajo de los 30 V de VBUS del BQ25798) en lugar
   de la SMF20A (32.4 V).
8. **D+/D− del cargador sin conectar**: R101/R102 de v0.1 nunca se montaban (detección BC1.2). Con
   D+/D− al aire el BQ25798 ve un «adaptador desconocido» y el límite lo pone ILIM (~2.9 A), como
   en v0.1.
9. **Un solo pedido en JLCPCB** con las dos placas en un panel. Ver
   [Pedido en JLCPCB](#pedido-en-jlcpcb) y [Costo](#costo).
10. **Serigrafía sin solapes**: cada conector lleva su función y su referencia («IMU J405»,
    «J404 NTC (opc.)»…); `silk_clean.py` revisa con el DRC de KiCad que ninguna referencia ni
    trazo pise pads u otra serigrafía, y las huellas de LCSC cuya serigrafía pisaba sus propios
    pads se recortaron en la biblioteca (`fp_silk_trim.py`: L2520 y SOD-882).
11. **Logotipo de TresVizo** (el de www.tresvizo.com, tomado del SVG del firmware,
    `firmware/esp32/assets/tresvizo-logo.svg`): completo, de 30 mm, con «www.tresvizo.com» en la
    cara trasera; y el distintivo (hexágono con el 3, de `mechanical/v2.2/logo.json`) en la cara
    de componentes, en el hueco frente al botón, donde no hay piezas.

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
    cada canto (u 0–2.5 y 43.5–46, v 0–48.5). El de +X se corta en z 54–71 frente a la antena. Por
    debajo de z 39 no hay riel: ahí llegan a los cantos la microSD y la batería.
  - **2 × M2.5** en agujeros sin metalizar Ø2.7 (sin cobre en Ø5.2): H1 en (u, v) = (12.0, 12.2),
    es decir (x, z) = (11.0, 75.3), y H2 en (40.4, 3.7) = (−17.4, 83.8). Se atornillan desde el
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
    J502 de la placa panel-usb) y LEDs (J406). Sobre el canto hay 12 mm libres hasta la plataforma
    del IMU, salvo bajo la placa panel-usb, donde baja el cable del USB.
  - Inferior, boca hacia abajo: microSD (J401), carrier (J301), NTC (J404, opcional) y batería
    (J102); se alcanzan quitando la base.
  - Dentro de la placa, boca hacia una zona libre: OLED (J403) hacia la izquierda, bajo los pines de
    la OLED, y botón (J402) hacia la izquierda, junto al botón.
  - Antena del ESP32 en el canto izquierdo (+X), u 0–6.2, v 17.3–33.3 sin cobre en ninguna capa.
- **La carcasa necesita cambios** (propuesta, no aplicada al CAD): quitar la placa del respaldo y
  los toalleros; recortar los nervios a y ≤ −10.5; rieles en z 39–90 (cortado en z 54–71 el de
  +X); brazos detrás de la placa en (x, z) = (11.0, 75.3) y (−17.4, 83.8); topes del carrier;
  repisa de la 18650; y en la tapa del panel, el hueco y las ménsulas del USB-C (ver
  [../panel-usb](../panel-usb/README.md)).
- **2S** no cabe en este orden sin un recorte de 11 × 11 mm frente al botón; ver
  [Antes de mandar a fabricar](#antes-de-mandar-a-fabricar).

**Comprobación de la placa terminada** (FreeCAD, [research/v02.md](research/v02.md) §8):

- Placa, componentes y clavijas enchufadas: 0 mm³ de choques con la carcasa y con los rieles
  propuestos.
- Paso por Ø52: radio máximo 23.21 mm.
- Lo más justo:
  - los cables de la batería, a 0.46 mm de la base;
  - la cara trasera, a 0.40 mm del carrier;
  - la cara de la placa, a 2.51 mm del botón.
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
| J406 | LEDs: 3V3 (ánodo común), R, G, B, carga | Canto superior, a la derecha; boca hacia arriba | SH 5 lateral SM05B-SRSS-TB (C136657) | SHR-05V-S (C514174) | SSH-003T-P0.2-H (C263995) | «cable JST SH 1.0 5 pines una cabeza» |
| J403 | OLED, orden Qwiic: GND, 3V3, SDA, SCL | Bajo los pines de la OLED; boca hacia la izquierda, sobre una zona libre de 6 × 7 mm | SH 4 lateral SM04B-SRSS-TB (C160404) | SHR-04V-S (C385125) | SSH-003T-P0.2-H (C263995) | «cable Qwiic» o «cable JST SH 1.0 4 pines» |
| J402 | Botón: GND, contacto, anillo LED A, K | A la izquierda del botón; boca hacia la izquierda, sobre una zona libre de 6.1 × 8.3 mm (el cable da la vuelta hacia el botón) | GH 4 lateral SM04B-GHS-TB (C189895) | GHR-04V-S (C160418) | SSHL-002T-P0.2 (C189897) | «cable JST GH 1.25 4 pines una cabeza» |
| J401 | microSD (zócalo push-push) | Canto inferior, a la izquierda; la tarjeta entra por abajo quitando la base | TF-015 (C113206) | — | — | — |
| J301 | Carrier GNSS (arnés en Y) | Canto inferior, al centro; boca hacia abajo | Igual que J101 (C3029383) | GHR-08V-S (C485357); a la carrier, GHR-08V-S y GHR-05V-S (C160419) | SSHL-002T-P0.2 (C189897) | «cables precrimpados JST GH 1.25 28 AWG» |
| J404 | NTC opcional, **sin montar** | Canto inferior, entre J301 y J102; boca hacia abajo | SH 2 lateral SM02B-SRSS-TB (C160402) | SHR-02V-S (C398472) | SSH-003T-P0.2-H (C263995) | «cable JST SH 1.0 2 pines una cabeza» |
| J102 | Batería: 1 = BAT−, 2 = BAT+ | Canto inferior, a la derecha; boca hacia abajo | **JST PH 2.0 mm**, 2 pines, lateral S2B-PH-SM4-TB (C295747) | PHR-2 (C157955) | SPH-002T-P0.5S (C111515) | La del pack: **confirmar paso y polaridad** |

- **J404 sale «vacío» en las vistas 3D** porque está marcado como *sin montar* (KiCad no dibuja
  esas piezas). Es el conector del NTC de la celda, opcional: sin él, una resistencia fija (R106,
  10 kΩ) le dice al cargador que la celda está a 25 °C. Para usar un NTC 10k B3435 pegado a la
  celda, soldar J404 y **quitar R106**.
- **J101 va justo bajo la placa panel-usb.** El cable entre J101 y J502 queda muy corto en línea
  recta: usar el más corto del kit y dejar el sobrante doblado en el hueco sobre el canto.

Cuidados:

- **J101 y J301 son los dos GH de 8 pines** (los dos los pidió el propietario así). Están en
  cantos opuestos y serigrafiados «USB J101» y «GNSS J301». Cruzarlos pondría VBUS contra GND.
- **Con el pinout de J101, un cable en espejo (pin 1 con 8) pone VBUS contra GND.** Medirlo pin a
  pin antes de enchufar.
- Ningún otro par de conectores comparte familia y número de pines.

## Firmware: qué tiene que cambiar

Se conservan los GPIO del firmware 0.8.x: UART del GNSS en 43/44 (COM2 a 115200), I2C en 8/9, SD_MMC
en 33/34/38/39/40/47 con la detección en 48 (HIGH con tarjeta) y el botón en 10. Cambia:

- **Identidad nueva** (`hardware_id`, entorno de compilación): la API solo crece.
- **Apagado = modo *ship* del BQ25798 por I2C**:
  - Al arrancar, escribir `SFET_PRESENT = 1` (REG0x14 bit 7), ICHG = 1 A y desactivar el
    *watchdog*.
  - Para apagar: cerrar la microSD, apagar el GNSS, esperar a que se **suelte** el botón y
    escribir REG0x11 `SDRV_CTRL = 10` con `SDRV_DLY = 1`.
  - Con USB conectado la orden se ignora (estado `power_still_present`).
- **GPIO45 enciende el 5 V de la carrier** (TPS63070); el firmware 0.8.x ya lo pone alto al
  arrancar. En modo «solo carga» se deja bajo. Con la carrier apagada, dejar GPIO43 en alta
  impedancia para no alimentarla por sus entradas.
- **Modo «solo carga»**: si al arrancar hay VBUS y no se pulsa el botón, dejar el GNSS apagado y
  mostrar la carga en la OLED. Un toque del botón pasa a modo normal; al quitar el USB se escribe el
  modo *ship*.
- **IMU en un segundo bus I2C** (`Wire1` en GPIO11 SDA y GPIO12 SCL, 400 kHz): acelerómetro 0x18,
  giróscopo 0x68, INT1 en GPIO17 e INT3 en GPIO18.
- **PPS en GPIO1, EVENT en GPIO5** (salida, 100 k a GND) y **RESET_N en GPIO4**. RESET_N se usa en
  drenador abierto con un pulso de ≥ 5 ms, pero la BDLX no lo saca.
- **Libres:** GPIO6, 13, 14, 15, 16, 41 y 42 (14 y 42 con punto de prueba).
- Además: LED RGB (7/21/36), anillo del botón (37), INT del cargador (2), ALRT del medidor (35).
- **1S**: apagar por batería baja con ≥ 3.5 V en reposo; en modo *ship* el BQ2579x necesita la
  celda por encima de ~3.4 V.

## Variantes 1S / 2S

| Ref. | 1S (por defecto) | 2S |
| --- | --- | --- |
| R103 (PROG) | 4.7 kΩ | 8.2 kΩ (C25924) |
| R117 (EN del TPS62903) | 10 kΩ | 3.9 kΩ (C51721) |
| U103 | MAX17048G+T10 | MAX17049G+T10 (C18185545; JLCPCB tenía 50 a 9.60 USD) |
| R113 (VPACK → VDD del medidor) | 0 Ω | sin montar |
| R115 (+3V3 → VDD del medidor) | sin montar | 0 Ω |
| Batería | 1 × 18650 protegida | 2 × 18650 en serie **con BMS de equilibrado** (el BQ25798 no equilibra) |

- **5 V de la carrier:** el TPS63070 trabaja igual en las dos variantes.
- **Cargador USB-C:** con 2S el cargador eleva desde 5 V y pide ~2.2 A de entrada; usar uno de 3 A.
- **Anillo del botón:** se alimenta de VSYS; con 2S usar la versión de 6 V del botón.
- **Mecánica:** 2S no cabe en la carcasa tal cual (ver [Mecánica](#mecánica)).

## Pedido en JLCPCB

Archivos del pedido, que llevan **las dos placas en un panel**:

- `fab/tresvizo-panel-gerbers-jlcpcb.zip`
- `fab/tresvizo-panel-bom-jlcpcb.csv`
- `fab/tresvizo-panel-cpl-jlcpcb.csv`

Los `fab/tresvizo-main-*` y los de `../panel-usb/fab` son de cada placa sola, por si se piden por
separado.

1. **PCB**:
   - Subir el zip del panel.
   - 4 capas, 1.6 mm, apilado JLC04161H-7628 (por defecto).
   - **Delivery Format: Panel by Customer**, **Different Design: 2**, tamaño del panel
     **82.8 × 78.0 mm** y cantidad en paneles (un panel = un juego de las dos placas).
   - Acabado ENIG recomendado (o HASL sin plomo).
2. **Montaje**:
   - PCBA **Standard**: el ESP32-S3-MINI-1 la obliga, «Standard Only» y rayos X.
   - Una cara (top).
   - El panel ya trae rieles de 5 mm, 3 fiduciales y 4 agujeros de herramienta de 2 mm, como pide
     JLCPCB. Las placas van unidas con puentes de 5 mm con *mouse bites* (agujeros de 0.6 mm): dos en
     cada canto lateral de la placa madre (uno de ellos la une a la panel-usb) y uno a cada lado de la
     panel-usb. Arriba y abajo de la placa madre no hay puentes porque esos cantos llevan conectores.
   - Los puentes de la placa madre a v 10.5 y 15.9 caen donde van los rieles: **lijar la rebaba** al
     separar las placas.
3. Subir BOM y CPL del panel y elegir «Complete File, just proceed with my own files».
   **Revisar la orientación de cada pieza en la vista previa** (sobre todo U102, U105, U301, Q1xx,
   D1xx y los conectores).
4. Las piezas sin montar (DNP) quedan fuera del BOM: R115 (0 Ω de 2S) y J404 (NTC).

## Costo

Estimación de [fab/costo-jlcpcb.md](fab/costo-jlcpcb.md) para **5 juegos**, con precios y
existencias de la API pública de JLCPCB del 04-10-2026 y las tarifas de su página (no es una
cotización):

| Pedido | Montaje + piezas | Por juego |
| --- | ---: | ---: |
| (A) Un panel con las dos placas, PCBA Standard | 211.38 USD | 42.28 USD |
| (B) Dos pedidos: principal Standard + panel-usb Economic | 224.13 USD | 44.83 USD |

- El panel único ahorra **12.75 USD** en montaje, y además es un solo envío.
- **No incluye el PCB desnudo** (4 capas, panel con dos diseños): JLCPCB no publica ese precio ni
  el cargo por diseño distinto; sale en el cotizador.
- Lo que más pesa: los alimentadores de PCBA Standard (38 piezas distintas × 1.53 USD = 58.14 USD)
  y las piezas (99.45 USD, sobre todo el ESP32, el BQ25798 y el MAX17048).
- **El ESP32-S3-MINI-1 obliga a PCBA Standard** (JLCPCB lo marca «Standard Only» y con rayos X),
  así que el ahorro de Economic no aplica a la placa madre.
- Piezas *Extended* que quedan: no tienen equivalente *Basic* en JLCPCB (cargador, medidor,
  reguladores, ESP32, conectores GH/SH, TVS y ESD; ver [research/v02.md](research/v02.md) §4).
- Todas tienen existencias (la menor: ESP32-S3-MINI-1-N4R2, 1888).

## Antes de mandar a fabricar

| Punto | ¿Frena el pedido? | Qué hacer |
| --- | --- | --- |
| Orientación de cada pieza en el CPL | Sí | Revisarla en la vista previa de JLCPCB y corregir el giro ahí |
| **Batería: conector y polaridad** | Sí | J102 es JST PH de 2.0 mm, pin 1 = BAT− y pin 2 = BAT+. **Confirmar que el pack tiene ese conector y esa polaridad** (medir con multímetro). La placa tiene protección contra inversión |
| Pinout de los conectores de la carrier | Sí, para el arnés | Leído de la serigrafía de la foto oficial (pin 1 = pad cuadrado, sin plano). Comprobarlo en la carrier real antes de armar el arnés en Y |
| Breakout BMI088 | Sí, para el cable | El orden del header (1 VCC … 9 INT3) salió de fotos del vendedor. Comprobarlo con multímetro, poner el selector en IIC y confirmar que SDO va a la hilera |
| Cables GH de 8 pines | Sí | J101 y J301 son iguales: no cruzarlos. Con el pinout de J101 un cable en espejo pone VBUS contra GND |
| LED RGB del panel de ánodo común | Sí, si ya lo compraste | J406 da +3V3 en el pin 1 y los cátodos van a los GPIO |
| Anillo del botón | Sí, si es el de 12 V | La placa lo alimenta con VSYS (3.5–4.2 V en 1S): usar el de 3–6 V |
| Carcasa (rieles en z 39–90, brazos de H1/H2, topes, ménsulas y hueco del USB-C) | No para la PCB | Hacerla en el CAD antes de imprimir. La placa va 2.5 mm más arriba que en el primer estudio (z 23.5–87.5); ver [Mecánica](#mecánica) |
| Cable USB entre J101 y la panel-usb | No | Los dos conectores quedan casi enfrentados: usar el cable GH8 más corto del kit, pin 1 con pin 1, y doblar el sobrante sobre el canto |
| Rebabas de los puentes del panel | No | Lijar las de los cantos laterales de la placa madre antes de meterla en los rieles |
| NTC (J404, sin montar) | No | Si se quiere protección térmica de la celda: soldar J404, quitar R106 y pegar un NTC 10k B3435 a la celda |
| Carrier: espesor real y acceso a sus conectores | No para la PCB | El estudio supuso 11 mm en todo el largo y la carrier de cara a la placa. Medirla |
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
| DRC del panel ([fab/drc-panel.rpt](fab/drc-panel.rpt)) | 0 errores, 0 avisos, 0 sin conectar; 82.8 × 78.0 mm |
| Clavijas enchufadas | Áreas `clavija_*` en el DRC: ninguna pieza dentro. En CAD: 0 mm³ contra la carcasa y los componentes; la más justa, la batería (0.46 mm a la base) |
| Rieles, botón y antena | Áreas `riel_*`, `boton` y `esp32_antena` en el DRC: sin violaciones |
| Serigrafía | 0 solapes ni serigrafía sobre pads (DRC); textos de 0.8 mm o más; el logotipo no tiene trazos de menos de 0.35 mm (apertura morfológica), sobre el mínimo de 0.15 mm de JLCPCB |
| Ruteo | 143 de 143 conexiones con `route_rest.py`; potencia solo por capas externas |
| *Bootstrap* del cargador | BTST1 → C101: 0.9 mm; BTST2 → C102: 1.6 mm (cara superior). Retorno a SW por vía y 4.3 / 5.7 mm de B.Cu |
| Mecánica (primer estudio y placa terminada) | Ver [research/v02.md](research/v02.md) §7 y §8 |
| Costo y existencias | API de JLCPCB del 04-10-2026: todas las piezas con existencias |

No comprobado: fabricación y montaje, ninguna medida eléctrica, el firmware para esta placa, el
pinout real de la carrier y del breakout BMI088, el lugar exacto de los conectores en la carrier, el
asomo de la clavija PH de la batería (3.5 mm estimado; JST no da el plano enchufado) y la carcasa
impresa con los cambios propuestos.

## Pendientes y riesgos

- **Nada medido**: carga 1S/2S, modo *ship*, arranque del TPS63070 con la carrier y su consumo,
  ruido del GNSS (C/N0) con el ESP32 transmitiendo, alcance de BLE/Wi-Fi.
- **Antena del ESP32**: Espressif pide 15 mm libres; en el tubo hay 5.85 mm hasta la pared y
  6.8 mm hasta la carrier.
- **Bootstrap del BQ25798**: los condensadores quedan junto a sus pines en la cara superior, pero
  su retorno a SW pasa por una vía y 4–6 mm de B.Cu; TI lo muestra con los condensadores en la cara
  inferior, que aquí no se puede usar.
- **VBUS por pistas de 0.4–0.5 mm** en la capa externa: holgado para 1S (~1.5 A). Con 2S el cargador
  pide ~2.2 A de entrada: calentará ~20 °C sobre el ambiente; ensancharlas si se fabrica en 2S.
- **Plano interno de 3V3** perforado por las vías del ruteo automático: quedan tiras y cuellos finos
  (el DRC no encuentra cuellos bajo 0.127 mm, pero conviene mirarlo a mano antes de pedir).
- **TS sin NTC**: un divisor fijo pone 25 °C; la celda no tiene protección térmica de carga dentro
  de un tubo al sol. Recomendado: NTC en J404 (sin montar).
- **Hoja del BQ2579x rev D**: la copia pública dice «TI Confidential»; pedir la oficial.
- **Ruteo automático** con `route_rest.py`, un ruteador propio (A* en rejilla con arranque y
  reruteo). Las pistas críticas están prerruteadas en `layout.py`:
  - lazos del cargador, nodos SW, *bootstrap*, BAT y la salida en abanico de su fila inferior;
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
  (se usó una vez, con L2520 y SOD-882).
- `layout.py` escribe además `kicad/plugs.json`: las clavijas enchufadas y los agujeros, para
  comprobarlos en CAD contra la carcasa.
- El proyecto del panel usa la biblioteca de la placa madre; `build.py` le copia la huella y el
  modelo del USB-C que solo tiene `../panel-usb`.
- Las huellas de `kicad/lib/lcsc.pretty` vienen de LCSC/EasyEDA (easyeda2kicad), para que la
  orientación coincida con la de JLCPCB.

No se guardan en git, por pesados y regenerables:

- los modelos STEP de LCSC (los `.wrl` sí);
- la caché de easyeda2kicad;
- los STEP de las placas.

La investigación con sus fuentes está en `research/`: v0.1 en los archivos originales y v0.2 en
[research/v02.md](research/v02.md).
