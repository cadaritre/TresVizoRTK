# Placa principal TresVizo MeridianV (exploratoria, v0.3 compacta)

> **Estado:** diseño generado con scripts y revisado con el ERC y el DRC de KiCad 10.0.6 y con una
> auditoría eléctrica independiente (08-10-2026), cuyos cambios ya están aplicados. **No se ha
> fabricado ni probado.** Vive en la rama `hw/compact-v03`, fuera de `main`, porque el propietario la
> pidió como exploración (07-10-2026). Los resultados de las comprobaciones están en
> [Verificaciones](#verificaciones).
>
> La v0.2 (placa de 46 × 64 mm más la panel-usb, para la carcasa V2.3) sigue en la rama
> `hw/main-board-kicad`.

La v0.3 es la versión compacta del receptor. Mantiene el concepto de la v0.2: el UM980 en su
carrier BDLX, por cable, y el ESP32-S3-WROOM-1 en la placa. Pero va en un tubo de **Ø56 × 116** con
una cara plana al frente ([carcasa V3.0](../../mechanical/v3.0/README.md)). La placa mide
**36 × 71.5 mm** (4 capas, 1.6 mm, componentes solo por la cara de arriba) y lleva lo que en la v0.2
iba en el panel: el USB-C, la OLED (soldada a la placa), un pulsador y un LED de estado. El BMI088
vuelve a la placa. No hay panel-usb: la placa se pide sola, en un panel de JLCPCB con un BOM y un
CPL. La batería pasa a un pack comercial 1S2P de dos 18650.

| Bloque | Pieza | Notas |
| --- | --- | --- |
| GNSS | Carrier BDLX RTK_UM98_V1.0.1, fuera de la placa | J301 (SH de 8 pines): COM2 a 115200, PPS, EVENT, RESET_N y su 5 V. Arnés soldado a la carrier |
| 5 V del GNSS | TI TPS63070 (buck-boost) | 4.88 V desde VSYS; GPIO45 lo enciende; apagado desconecta la carga |
| MCU | ESP32-S3-WROOM-1-N16R2 | 16 MB de flash y 2 MB de PSRAM quad. Antena hacia el canto −X. Mismos GPIO que la v0.2, salvo GPIO48 (ver [Firmware](#firmware-qué-tiene-que-cambiar)) |
| IMU | Bosch BMI088 en la placa (U401) | I2C en un segundo bus (GPIO41/42), INT1 en GPIO2 e INT3 en GPIO1; 0x18 y 0x68 |
| Registro | microSD de empuje TF-015 (J401), SD_MMC 4 bits | CLK GPIO6, CMD 7, D0 5, D1 4, D2 16, D3 15 y detección en 17 (HIGH con tarjeta). Boca hacia el costado +X |
| USB-C | HRO TYPE-C-31-M-12 (J101) | Rd de 5.1 kΩ en CC1 y CC2, TVS SMF15A en VBUS y USBLC6 (U101) en D+/D−. Boca hacia el costado +X |
| Carga | TI BQ25798 (buck-boost NVDC) | USB-C a 5 V, techo de entrada ~1.45 A (ILIM); 1S; usar y cargar a la vez. Carga de 1 A por omisión; el firmware no debe pasar de 1.5 A |
| Apagado | Modo *ship* del cargador + FET externo | El pulsador despierta la placa (QON) |
| 3.3 V | TI TPS62903 | 3–17 V, 3 A, modo 100 % |
| Medidor | MAX17048 | I2C 0x36 |
| Interfaz | OLED 0.96" de 4 pines (J403), pulsador SW401 y LED rojo D403 | La OLED es la del propietario y la suelda él sobre pads SMD. El LED va en GPIO48 |
| Batería | Pack 1S2P (2 × 18650 en paralelo) por J102 (GH de 4 pines) | NTC 10k B3435 obligatoria por J404 (SH de 2 pines) |

Esquema en [fab/tresvizo-main-schematic.pdf](fab/tresvizo-main-schematic.pdf), mapa de pines y
conectores en [fab/pinout.md](fab/pinout.md) y vistas en `fab/*-top.png` / `fab/*-bottom.png`. La
especificación de la v0.3, la colocación, las desviaciones, el ruteo y la auditoría eléctrica están
en [research/v03-compacta.md](research/v03-compacta.md); la investigación de la v0.2, en
[research/v02.md](research/v02.md). El esquema en PDF, las vistas y los Gerber los genera
`build.py` y solo se guardan en git en los hitos (ver [Regenerar](#regenerar)).

## Decisiones

### De la v0.3 (07-10-2026 y auditoría del 08-10-2026)

Pedido del propietario: un receptor más chico, con el panel dentro de la placa principal, dos 18650
y la carrier tal cual. Lo que resultó al aplicarlo, con su motivo:

1. **Tubo de Ø56 × 116 y placa de 36 × 71.5 mm.** Unos dos tercios del volumen de V2.3.
   - Empezó en Ø52 × 100. El endurecimiento del 08-10-2026 lo agrandó para dejar holguras de
     impresión y de montaje, y el coaxial con curvas de R 12 o más (ver [Mecánica](#mecánica)); la
     placa no cambió de lugar.
   - Los cantos laterales corren por los rieles del chasis, con una franja de 1 mm sin componentes.
   - Componentes solo por la cara de arriba: el dorso mira a la carrier a 0.5 mm.
   - El alto de cada pieza lo limitan la curva del tubo y la cara plana.
   - Dos muescas en el contorno: la clavija del SMA de la carrier y la funda de la clavija del USB-C.
   - Ver [Mecánica](#mecánica).
2. **El panel entra en la placa.** Motivos: no hay cables al panel y el botón metálico de 12 mm de
   la v0.2 es difícil de conseguir.
   - USB-C J101 (TYPE-C-31-M-12, C165948, el de la panel-usb): Rd de 5.1 kΩ en CC1 y CC2 (R119,
     R120), TVS SMF15A en VBUS y USBLC6 (U101) junto al conector.
   - Pulsador táctil SW401 (TS-1187A-B-A-B, 5.1 × 5.1 × 1.5 mm) a BTN_N: despierta al cargador (QON)
     y llega a GPIO18 por D402. Conserva la ESD D401, porque la tecla deja llegar descargas a su botón
     de latón.
   - LED de estado D403 (0603 rojo) directo desde GPIO48, con 330 Ω: unos 4.4 mA. Con 1 kΩ quedaba
     tenue detrás de la guía de luz (auditoría). R409 era la resistencia del anillo del botón.
   - Se van J101 GH 8 (USB del panel), J402 (botón), J405 (IMU por cable), Q402 y R410 (anillo del
     botón). J403 sigue, ahora como huella del módulo OLED. Los números R106 y R410 quedan sin usar,
     para no renumerar.
3. **OLED soldada a la placa (J403).** Es el mismo módulo I2C de 4 pines que ya tiene el propietario.
   - Va girado 180° (pines abajo), sobre separadores de 1.3 mm, con el vidrio detrás de la ventana de
     la cara plana. Sobresale por encima del canto de arriba de la placa.
   - **Pads SMD de 1.7 × 2.4 mm, sin agujeros** (auditoría). Detrás de la fila de pines está el SMA
     de la carrier, a 0.4 mm del dorso, y una soldadura pasante recortada podía cortocircuitar +3V3 y
     SCL con su carcasa (GND).
   - La única unión pasante de la placa son las cuatro patas de la carcasa del USB-C (GND), que no
     salen por detrás.
   - JLCPCB no monta la OLED: sus pads llevan pasta y salen estañados. El propietario corta los pines
     a la altura del separador y los suelda sobre los pads calentando desde el frente del módulo.
4. **BMI088 en la placa (U401)**, como en v0.1, en el bus que usaba J405. No hacen falta cable ni
   plataforma, y queda rígido con el resto del equipo.
   - Conexión según la hoja de Bosch (BST-BMI088-DS001 rev 1.9): PS a VDDIO (I2C), CSB1 a VDDIO y
     CSB2 al aire.
   - SDO1 y SDO2 a GND: acelerómetro 0x18 y giróscopo 0x68, las direcciones del breakout de la v0.2.
   - INT2 e INT4 sin conectar, 100 nF en VDD y en VDDIO, pull-ups de 4.7 kΩ y sin cobre de la cara
     de arriba bajo el encapsulado (DS §8.2).
   - Sigue en un **segundo bus** (GPIO41 SDA, GPIO42 SCL, 400 kHz), aparte del de la OLED, el
     cargador y el medidor, y con sus dos interrupciones.
   - Va en la esquina de abajo a la izquierda, lejos de L101, del botón y de los puentes del panel.
5. **Pack 1S2P por un GH 4 (J102).** El PH 2 lateral de la v0.2 mide 5.5 mm sobre la placa y aquí
   caben unos 4.6.
   - JST GH 4 lateral (SM04B-GHS-TB, C189895, unos 4.25 mm de alto) con dos contactos por polo: 1 y
     2 a GND, 3 y 4 a VBATT_IN.
   - JST da 1 A por contacto con cable AWG #26: unos 2 A por polo. El firmware limita la carga a
     1.5 A como mucho (ver [Firmware](#firmware-qué-tiene-que-cambiar)).
6. **Conectores de cable solo en el canto de abajo**, con la boca hacia abajo: a los lados no hay
   sitio para las clavijas. Son J404 (NTC), J102 (batería) y J301 (GNSS), y se alcanzan quitando la
   base.
7. **La carrier BDLX tal cual**, con el arnés soldado a sus filas de agujeros, como en la v0.2. Sus
   agujeros solo se conocen a ±1 mm (foto): una mezzanine pediría medidas exactas.
8. **Antena del ESP32 hacia el canto −X**, con un área sin pistas, vías ni rellenos en las cuatro
   capas que la auditoría amplió (ver
   [research/v03-compacta.md](research/v03-compacta.md#colocación)).
9. **Resto de la auditoría eléctrica** (detalle en
   [research/v03-compacta.md](research/v03-compacta.md#auditoría-eléctrica-08-10-2026)):
   - puentes del panel lejos de U401 y de los condensadores de potencia;
   - relleno de GND de J102 con cuatro vías, y dos vías en cada cambio de capa de VPACK;
   - cuatro vías de GND en el pad central del WROOM;
   - puntos de prueba de UART0 (TP208 y TP209).
10. **Endurecimiento eléctrico (08-10-2026)**, sin mover ni agregar piezas (detalle en
    [research/v03-compacta.md](research/v03-compacta.md#endurecimiento-eléctrico-08-10-2026)):
    - VBUS y PMID con 10 µF en lugar de 22 µF (C104, C106 y C107; C15850, *Basic*): menos irrupción
      al enchufar el USB, sin bajar de los mínimos de TI (ver [Pendientes y riesgos](#pendientes-y-riesgos));
    - VSYS al TPS62903 por In2.Cu con 1.2 mm (antes 0.6), dos vías de 0.6/0.3 en el relleno y una
      de 0.8/0.4 junto a C116; GNSS_5V por In2.Cu con 0.6 mm (antes 0.4);
    - los valores de seguridad que dependen del firmware, en una tabla (ver
      [Firmware](#firmware-qué-tiene-que-cambiar)).

### De la v0.2 que siguen valiendo

Decisiones del propietario del 04-10-2026 (sin UM980 en la placa, 5 V conmutable para la carrier,
piezas Basic donde las haya y cables del kit precrimpado GH y SH) que la v0.3 conserva:

1. **GNSS por conector (J301, SH 8).** Pinout del propietario: 1 5V, 2 GND, 3 RXD2 (TX del ESP32),
   4 TXD2, 5 PPS, 6 EVENT, 7 RESET_N, 8 GND. La carrier reparte esas señales en **dos** conectores
   (5 pines: 5V_IN, GND, PPS_OUT; 8 pines: TTL_RXD2, TTL_TXD2, GND, EVENT), así que el cable es un
   **arnés en Y** ([research/v02.md](research/v02.md) §1). **La BDLX no saca RESET_N**: J301.7 queda
   para otra carrier o para soldarlo a mano.
   - Resistencias en serie: **1 kΩ hacia la carrier y 100 Ω desde ella**, como en v0.1. Con la
     carrier apagada, 1 kΩ limita a ~3 mA lo que GPIO8 le mete por sus entradas si queda en alto.
     Con el WROOM-1 el TX ya no es U0TXD, así que la ROM no escribe ahí al arrancar.
   - ESD: dos USBLC6 (U302 y U303) en RXD2, TXD2, PPS y EVENT; RESET_N solo lleva 1 kΩ.
   - SH y no GH, para que no se pueda cruzar con J102 (GH 4).
2. **5 V de la carrier: TPS63070** en lugar de un elevador simple. Desconecta la carga apagado (un
   boost común deja la carrier unida a VSYS) y sirve igual en 1S y en 2S. Salida 4.88 V; la carrier
   pide 4.0–5.5 V (160 mA a 5 V).
3. **Lazos del cargador como en el ejemplo de TI** (hoja del BQ25798, 8.4). El bloque se conserva
   de la v0.2:
   - Los 100 nF de PMID (C108) y de SYS (C112) van sobre los pines 29/27 y 25/27, con la GND en T
     al pin 27. PMID lleva 2 × 10 µF (2 × 22 µF hasta el endurecimiento del 08-10-2026) y SYS
     2 × 22 µF, en columnas a cada lado, sin cuellos.
   - **SW1 y SW2 bajan por 3 vías cada uno bajo el chip** y van por B.Cu (1 mm) a la bobina. Bajo
     el chip, la bobina y esas pistas, la capa interna 3 es GND en lugar de +3V3 (en la v0.2 era bajo
     todo el bloque).
   - *Bootstrap* en la cara superior, cada condensador recto bajo su pin: BTST1 → C101 en 0.9 mm y
     BTST2 → C102 en 1.6 mm. El lado SW de cada uno baja por una vía y llega por B.Cu (4.3 y 5.7 mm)
     a la columna de vías de su nodo SW bajo el chip.
   - La fila inferior del cargador (pines 17–24, paso 0.4) sale en abanico prerruteado: ILIM, BATP,
     PROG, INT, BAT y SDRV, con R103 (PROG) y R107 (BATP) junto a sus pines y C113 (BAT) a la derecha.
   - Potencia por las capas externas: VBUS va de J101 a la TVS por F.Cu de 0.6 mm y al 10 µF de
     entrada (C104) por B.Cu de 0.8 mm; VPACK va de Q102 al cargador por B.Cu de 1.0 y 0.8 mm.
   - Dos excepciones nuevas de la v0.3: VSYS al TPS62903 (1.2 mm) y GNSS_5V (0.6 mm) van por
     In2.Cu, de 0.5 oz, porque por fuera ya no había paso. Los anchos son los del endurecimiento del
     08-10-2026 (antes 0.6 y 0.4 mm; ver [Pendientes y riesgos](#pendientes-y-riesgos)).
4. **TVS de VBUS SMF15A** (limita a 24.4 V, por debajo de los 30 V de VBUS del BQ25798) en lugar de
   la SMF20A (32.4 V).
5. **D+/D− del cargador sin conectar y techo de entrada de ~1.45 A** (05-10-2026). El ESP32-S3
   activa el pull-up de D+ desde el reset, lo que confundiría la detección BC1.2. Con D+/D− al aire,
   el BQ25798 ve un «adaptador desconocido» y el límite lo pone ILIM.
   - **R102 = 8.2 kΩ** (10k/8.2k desde REGN, 4.6–5.0 V): techo de **1.34–1.56 A**, que alcanza para
     cargar 1S a 1 A con el equipo encendido (~1.3 A de entrada).
   - La placa sigue sin saber cuánto da el puerto: CC1 y CC2 solo llevan Rd. La detección por CC hacia
     un ADC del ESP32, prevista para la v0.3, **no se hizo** (ver
     [Pendientes y riesgos](#pendientes-y-riesgos)).
6. **Serigrafía sin solapes.** `silk_clean.py` revisa con el DRC de KiCad que ningún texto ni trazo
   pise pads u otra serigrafía; las huellas cuya serigrafía pisaba sus propios pads se recortaron en
   la biblioteca (`fp_silk_trim.py`). En la v0.3 la cara de componentes no tiene sitio para rótulos:
   la función de cada conector («BAT J102», «NTC J404», «GNSS J301») y las notas de variante van en
   la cara trasera, detrás de cada pieza.
7. **Logotipo de TresVizo** (el de www.tresvizo.com, tomado del SVG del firmware,
   `firmware/esp32/assets/tresvizo-logo.svg`): completo, de 26 mm, con «www.tresvizo.com» en la cara
   trasera, detrás del WROOM. El distintivo de la cara de componentes de la v0.2 no cabe.
8. **NTC de la celda obligatoria en J404** (decisión del propietario del 07-10-2026). El cargador
   deja de cargar fuera de ~2–61 °C y baja el voltaje de carga arriba de ~45 °C; sin NTC enchufada no
   carga. Ver [Conectores](#conectores).

## Mecánica

Carcasa [V3.0](../../mechanical/v3.0/README.md), exploratoria y sin imprimir: tubo de Ø56 × 116
(pared de 2.4) con una cara plana al frente, base desmontable con la tuerca 5/8"-11 del bastón y tapa de antena sujeta
con tres M2.5 radiales. Dentro, un chasis que se arma fuera del tubo y entra por arriba lleva los
rieles de la placa, las ranuras de la carrier y dos salientes para los tornillos de la OLED. Ejes:
**z = eje del bastón hacia arriba** (z 0 en la cara de apoyo), **+Y hacia la cara plana**, **+X a
la izquierda mirando el frente**; medidas en mm. Especificación y contrato con la placa en
[research/v03-compacta.md](research/v03-compacta.md).

- **Placa:** 36 × 71.5 mm, FR-4 de 1.6 mm, 4 capas (JLC04161H-7628).
  - Va en x −18…+18, z 8.5…80, con el dorso en y 13.8 y la cara de componentes en y 15.4, mirando a
    la cara plana.
  - Coordenadas de KiCad: u = 18 − x, v = 80 − z (u de 0 a 36 de izquierda a derecha mirando el
    frente; v de 0 a 71.5 hacia abajo).
  - Alto máximo de los componentes, con 0.5 de aire medido en radio hasta el tubo (cara plana
    interior en y 20.5, radio interior 25.6): 4.6 hasta |x| 15.17; 4.34 en |x| 15.5; 3.94 en 16;
    3.51 en 16.5; 3.07 en 17.
  - Franjas de 1.0 sin componentes en los cantos laterales (áreas `canto_*` del DRC), para los
    rieles en C del chasis.
  - Muescas: la del SMA de la carrier en el canto de arriba (u 14.2–24.2, v 0–6.5; x −6.2…3.8,
    z 73.5–80) y la de la funda de la clavija USB-C en el canto +X (u 0–3.1, v 48.5–61.5).
  - Se sujeta con dos M2 × 8 autorroscantes. Pasan por los agujeros de abajo del módulo OLED, sus
    separadores de 1.3 y dos agujeros sin metalizar de Ø2.2 de la placa (x ±11.75, z 70.2), y
    roscan en dos salientes del chasis detrás de la placa. **El del lado de la antena del WROOM
    (x −11.75) conviene que sea de nailon** (auditoría).
- **Pila de adelante hacia atrás (y):**
  - cara plana por dentro, 20.5; vidrio de la OLED, hasta 20.0;
  - componentes de la placa, hasta 15.4 + h(x); PCB, 13.8–15.4; aire de 0.6;
  - componentes de la carrier, 6.8–13.2; PCB de la carrier, 5.2–6.8; patas del SMA, hasta 3.2;
  - pack 1S2P, de −18.6 a 1.4.
- **Carrier BDLX** detrás de la placa, centrada (x −16…+16, z 17…69), con los componentes hacia la
  placa y el SMA arriba (eje en x −1.2, y 10.2). Entra al chasis por abajo y la sostienen dos
  ganchos.
- **Batería:** pack comercial 1S2P (2 × 18650 con BMS y funda; 37.5 × 68 × 20 según el anuncio,
  tomado como peor caso con 0.5 de holgura), en una cuna detrás de la carrier: x 0, y −18.6…1.4,
  z 18.8…86.8. El BMS va abajo; un solo mazo (rojo, negro y la NTC) baja por detrás y corre por el
  piso hasta J102 y J404. La NTC va pegada con kapton en la cara de atrás del pack. Detalle en
  [research/v03-compacta.md](research/v03-compacta.md#celdas).
- **Antena GNSS:** la HA-901A del kit de BDLX (hélice cuádruple, Ø43.5 × 40.8; la tienda da 42.2 de
  alto).
  - La tienda da conector «SMA-J» (macho) y dice que se enrosca directo al SMA de la carrier. Falta
    confirmarlo en la antena.
  - La tapa lleva al centro un SMA hembra de panel, donde se enrosca la antena, que además queda
    fija con sus 3 M2.5 (arandelas ISO 7092).
  - Por dentro va un cable RG 178 B/U de unos 77 mm entre conectores, con SMA macho acodado de
    crimpar en la carrier. Sus curvas son de R 12.27 o más; la hoja actual de Lapp (versión 06)
    pide 6 × Ø (10.9–11.6) en instalación fija.
  - Si la antena resulta hembra, el parámetro `antena.conector.tipo = "hembra"` cambia la tapa a
    un paso de 12 mm para una clavija macho.
- **Frente:** ventana de la OLED, tecla de TPU sobre SW401 (x 0, z 22) y guía de luz de Ø2 sobre
  D403 (x −6, z 22). **Costado +X:** túnel cerrado del USB-C (z 25) y ranura justa de la microSD
  (z 40.88, con muesca para la uña), con 0.3 por lado; los tapa una tapa de TPU con tres anclas.
- **Orden de montaje** (detalle en V3.0):
  1. pack por arriba;
  2. carrier al chasis por abajo, con el arnés de J301 ya soldado;
  3. clavija SMA en la carrier, antes que la placa;
  4. placa al chasis por abajo, con la OLED soldada, y sus dos M2;
  5. chasis al tubo por arriba y tapa con la antena;
  6. batería y NTC por abajo, con la base quitada;
  7. tecla, lámina de la ventana y guía de luz por fuera.

**Comprobación en CAD** (FreeCAD 1.1.3, `mechanical/v3.0/check_v3_0.py`, 08-10-2026), con el STEP
final de la placa, ya con los cambios de la auditoría ([cad/README.md](cad/README.md)), y las zonas
de clavijas de `kicad/plugs.json`:

- 0 choques en posición final y los 11 barridos del montaje sin choques;
- la guarda de la pared del tubo pasa;
- se cumplen los objetivos de holgura: 0.4 entre impresas, 0.25 por cara en los rieles, 0.5 a lo
  comprado (pack incluido), coaxial con R 12.27 y mazos separados 8.8 o más;
- contra la placa real, el émbolo de la tecla queda a 0.505 de SW401 y la guía de luz a 0.545 de
  los componentes.

Lo que no se verificó (módulo OLED real, carrier medida, cables, antena, impresión) está en el
[README de V3.0](../../mechanical/v3.0/README.md#verificaciones).

La v0.2 y su carcasa V2.3 están en la rama `hw/main-board-kicad`.

## Conectores

Los de cable son JST GH (1.25 mm) o SH (1.0 mm) de entrada lateral, todos en el canto de abajo con
la boca hacia abajo. Los cables se arman con el kit de cables precrimpados GH y SH del propietario:
cada cable se inserta en su cavidad, **pin 1 con pin 1**, y se mide con el multímetro antes de
enchufar. Tablas completas, generadas desde la netlist, en [fab/pinout.md](fab/pinout.md).

Delante de cada boca se reserva, sin componentes, lo que asoma la clavija enchufada, el doblez de
sus cables (3 mm) y 1 mm a cada lado para tomarla:

- GH: la clavija asoma 3.1 mm y mide 4.35 mm de alto (JST eGH, «Assembly layout»).
- SH: se toman 3.0 mm de asomo; la carcasa SHR mide 2.8 mm de alto (JST eSH).

Esas reservas son áreas de regla `clavija_*` en el PCB: el DRC falla si una pieza entra en ellas.
También van en `kicad/plugs.json` para la comprobación en CAD.

| Ref. | Uso | Dónde y hacia dónde | En la placa (LCSC) | Carcasa del cable (LCSC) | Contacto (LCSC) | Cable armado (búsqueda) |
| --- | --- | --- | --- | --- | --- | --- |
| J102 | Batería: 1-2 = BAT− (GND), 3-4 = BAT+ | Canto de abajo, al centro (x −2.0…6.2); boca hacia abajo | GH 4 lateral SM04B-GHS-TB (C189895) | GHR-04V-S (C160418) | SSHL-002T-P0.2 (C189897), cable AWG #26 | El del pack, con cable GH de 4 hilos: **confirmar el pinout y medirlo** |
| J404 | NTC 10k B3435 de la celda (obligatoria) | Canto de abajo, a la izquierda de J102 (x 6.9…10.9); boca hacia abajo | SH 2 lateral SM02B-SRSS-TB (C160402) | SHR-02V-S (C398472) | SSH-003T-P0.2-H (C263995) | «cable JST SH 1.0 2 pines una cabeza» |
| J301 | Carrier GNSS (arnés en Y) | Canto de abajo, a la derecha (x −3.0…−13.0); boca hacia abajo. El arnés sube por el lado −X | **SH 8** lateral SM08B-SRSS-TB (C160407) | SHR-08V-S (C265412); en la carrier, **soldado** a sus filas de agujeros | SSH-003T-P0.2-H (C263995) | «cable JST SH 1.0 8 pines una cabeza» |
| J101 | USB-C: carga y USB nativo del ESP32 | Costado +X, z ≈ 25; boca en u 3.1, hacia +X | HRO TYPE-C-31-M-12 (C165948) | — | — | — |
| J401 | microSD (zócalo de empuje) | Costado +X, z 32–48; boca en u 1.5, hacia +X | TF-015 (C113206) | — | — | — |
| J403 | OLED: 1 VCC (+3V3), 2 GND, 3 SCL, 4 SDA (según la foto del anuncio; **confirmar en la unidad**) | Bajo la fila de pines del módulo, v 8.95–11.35 | Cuatro pads SMD de 1.7 × 2.4, sin pieza de JLCPCB | — | — | Lo suelda el propietario |

- **NTC obligatoria en J404.** TS del cargador es un divisor de REGN (5.1 kΩ arriba, 30 kΩ abajo)
  con la NTC en paralelo con los 30 kΩ. Con una NTC 10k B3435 (tipo 103AT) y los umbrales por
  omisión del BQ25798 (hoja de datos: VT1 73.3 %, TS_COOL 68.4 %, TS_WARM 44.8 %, VT5 34.2 % de REGN):

  | Temperatura de la celda | Qué hace el cargador |
  | --- | --- |
  | < ~2 °C o > ~61 °C | No carga |
  | ~2–11 °C | Carga al 20 % de la corriente (JEITA_ISETC) |
  | ~11–45 °C | Carga normal |
  | ~45–61 °C | Carga con el voltaje 400 mV más bajo (JEITA_VSET): una celda casi llena ya no sube |

  - **En todos los casos el sistema sigue encendido con el USB**: el cargador solo suspende la
    carga; VSYS sigue saliendo de VBUS.
  - El firmware puede ajustar los umbrales por I2C (REG17/REG18), por ejemplo TS_WARM a 40 °C.
  - **Sin NTC enchufada**, TS sube a ~85 % de REGN: frío extremo y no carga.
  - **Ojo al comprarla:** 10 kΩ a 25 °C con B = 3435 (tipo 103AT o «NTC 10K 3435»). Las de las
    impresoras 3D son de 100 kΩ (B3950): con esas el cargador cree que siempre hace frío y nunca
    carga.
  - En V3.0 va pegada entre las dos celdas, en el valle de delante, y su cable baja con el de la
    batería.

Cuidados:

- **J301 es SH 8 y J102 GH 4**: con familias distintas no se pueden cruzar. Ningún par de
  conectores comparte familia y número de pines.
- **J102 lleva dos contactos por polo.** Un cable en espejo (pin 1 con pin 4) pone la batería al
  revés. La placa tiene protección contra inversión (Q102 y Q103), pero hay que medir el cable del
  pack antes de enchufarlo.
- **USB-C:** CC1 y CC2 solo llevan Rd, así que la placa pide 5 V y no sabe cuánto da la fuente (ver
  [Pendientes y riesgos](#pendientes-y-riesgos)).

## Firmware: qué tiene que cambiar

Todavía no hay firmware para esta placa: el de `firmware/esp32` es para la SparkFun Thing Plus. El
WROOM-1 se ruteó con GPIO nuevos (en el S3 la SD_MMC, las UART y el I2C van por la matriz de GPIO,
así que solo cambia la configuración). La v0.3 usa los mismos que la v0.2, salvo las dos filas
marcadas:

| Función | GPIO |
| --- | --- |
| microSD (SD_MMC 4 bits) | CLK 6, CMD 7, D0 5, D1 4, D2 16, D3 15: `SD_MMC.setPins(6, 7, 5, 4, 16, 15)` |
| Detección de la microSD | 17 (HIGH con tarjeta) |
| UART del GNSS (COM2 a 115200) | TX 8 (a RXD2), RX 9 (de TXD2) |
| PPS, EVENT, RESET_N | 10, 11 (salida, 100 k a GND), 12 |
| I2C de la OLED, cargador y medidor | SDA 13, SCL 14 |
| IMU BMI088 (`Wire1`, 400 kHz) | SDA 41, SCL 42, INT1 2, INT3 1 |
| Botón | 18 (activo bajo) |
| **LED de estado (v0.3; antes, anillo del botón)** | **48 (activo alto)** |
| INT del cargador / ALRT del medidor | 21 / 47 |
| 5 V de la carrier (TPS63070) | 45 |
| **Consola (UART0; v0.3: con puntos de prueba)** | **43 (TP208) / 44 (TP209)** |
| Libres | 35, 36 y 37 (con punto de prueba), 38, 39, 40 y 46 |

**Valores de seguridad para el firmware** (endurecimiento del 08-10-2026; los mismos en
[research/v03-compacta.md](research/v03-compacta.md#valores-para-el-firmware)). Salen de las hojas de
datos; ninguno se probó en una placa:

| Valor | Qué hace el firmware | De dónde sale |
| --- | --- | --- |
| Corriente de carga (ICHG, REG0x03 del BQ25798) | **1.5 A como mucho.** Al arrancar: `SFET_PRESENT = 1` (REG0x14 bit 7), ICHG = 1 A y *watchdog* desactivado | J102 tiene dos contactos GH por polo, de 1 A cada uno con cable AWG #26. El BQ25798 arranca con 1 A y el *watchdog* y REG_RST lo devuelven a 1 A (hoja SLUSDV2C, REG03). ILIM no alcanza como tope: con 5 V y 1.34–1.56 A de entrada podría dar ~1.8 A a la celda a 3.7 V y hasta ~2.4 A cerca de 3.0 V, donde empieza la carga rápida, si se le pidiera más (estimado con 90–93 % de eficiencia y el sistema apagado) |
| Techo de entrada (IINDPM, REG0x06) | Puede **bajarlo** (p. ej. a 500 mA en un puerto de PC), nunca subirlo. No escribir `EN_EXTILIM = 0` | Por hardware, ILIM_HIZ con 10k/8.2k desde REGN (4.6–5.0 V): **1.34–1.56 A**, 1.45 A típ. Es el techo de IINDPM salvo con EN_EXTILIM = 0 (§7.3.4.3). Con D+/D− del cargador al aire manda ILIM ([research/power.md](research/power.md) §2.4) |
| Botón mantenido | Gestos muy por debajo de 10 s (apagar con 2–3 s) | QON en bajo durante tRST (10 s típ.) es un reset por hardware: el BQ25798 abre el FET de envío ~350 ms (típ.) y el equipo rearranca, con o sin USB (§7.3.12.3). Ya pasaba con el botón del panel de la v0.2 |
| OLED | Girar la imagen 180° (no espejarla) | El módulo va girado 180° en su plano, con los pines abajo. Controlador SSD1315 según el anuncio (compatible con las bibliotecas del SSD1306) |
| Ejes del IMU (acelerómetro y giróscopo) | X carcasa = +X sensor, Y carcasa = +Z sensor, Z carcasa = −Y sensor. Con el bastón vertical y quieto, el acelerómetro da Y ≈ −1 g y X, Z ≈ 0 | Deducido de la hoja de Bosch (BST-BMI088-DS001 rev 1.9, figura 6 y tabla 15) con U401 a 0° en KiCad: los pines 1–7 miran a −u (+X de la carcasa) y el 16 a +v (abajo). **Confirmarlo con la placa armada**, leyendo la gravedad en varias posiciones |

Lo nuevo de la v0.3 respecto de la v0.2:

- **LED de estado en GPIO48** en lugar del anillo del botón (BTN_LED_EN, que movía Q402): activo
  alto, unos 4.4 mA. En el reset GPIO48 queda como entrada sin pull, así que el LED no se enciende
  mientras arranca. Sin LEDs del panel ni anillo: quitar o desactivar su código sin quitar claves de
  la API («la API solo crece»).
- **IMU en la placa:** mismo bus (`Wire1`, GPIO41/42), mismas interrupciones (INT1 en GPIO2, INT3 en
  GPIO1) y mismas direcciones (0x18 y 0x68).
  - **Cambia la orientación.** El BMI088 ya no va en la plataforma horizontal de la tapa, sino en la
    placa, que en el tubo es vertical: plano XZ de la carcasa, con la cara de componentes hacia +Y.
    U401 va girado 0° en KiCad (u = 18 − x, v = 80 − z). Los ejes están en la tabla de arriba.
  - **INT1 e INT3 en push-pull:** en la placa no tienen pull-up.
- **OLED girada 180°, carga de 1.5 A como mucho y botón de 10 s:** ver la tabla de arriba.
- **Puntos de prueba de UART0:** TP208 (U0TXD, GPIO43) y TP209 (U0RXD, GPIO44). Sirven para leer los
  mensajes de la ROM al arrancar y como consola por un adaptador serie si el USB nativo no responde.

Lo que sigue igual que en la v0.2:

- **Particiones:** con 16 MB de flash las dos ranuras OTA pueden crecer a ~6 MB (hoy 1.875 MB).
- **Identidad nueva** (`hardware_id`, entorno de compilación): la API solo crece.
- **Apagado = modo *ship* del BQ25798 por I2C:** cerrar la microSD, apagar el GNSS, esperar a que se
  **suelte** el botón y escribir REG0x11 `SDRV_CTRL = 10` con `SDRV_DLY = 1`. Con USB conectado la
  orden se ignora (estado `power_still_present`).
- **GPIO45 enciende el 5 V de la carrier** (TPS63070); el firmware 0.8.x ya lo pone alto al
  arrancar. En modo «solo carga» se deja bajo. Con la carrier apagada, dejar GPIO8 en alta
  impedancia para no alimentarla por sus entradas.
  - GPIO45 es pin de arranque con 100k a GND (VDD_SPI a 3.3 V, lo correcto para el N16R2): en
    **cualquier reinicio del ESP32, también por software, la carrier se apaga** y el GNSS arranca
    de cero (pierde el fix RTK). El firmware no debe reiniciar el ESP32 a la ligera.
- **Modo «solo carga»:** si al arrancar hay VBUS y no se pulsa el botón, dejar el GNSS apagado y
  mostrar la carga en la OLED. Un toque del botón pasa a modo normal; al quitar el USB se escribe el
  modo *ship*.
- RESET_N se usa en drenador abierto con un pulso de ≥ 5 ms, pero la BDLX no lo saca.
- El STAT del cargador queda al aire: el estado de carga se lee por I2C.
- **1S:** apagar por batería baja con ≥ 3.5 V en reposo; en modo *ship* el BQ2579x necesita la
  celda por encima de ~3.4 V.

## Variantes 1S / 2S

La v0.3 está pensada para un pack **1S2P** (dos 18650 en paralelo; el elegido es uno comercial con
BMS): para la placa es una
celda 1S de doble capacidad, con la variante 1S por defecto. Las piezas de la variante 2S siguen en
el esquema y la tabla vale igual, pero 2S no está previsto en la v0.3: la cuna de V3.0 lleva las
celdas en paralelo y no se buscó sitio para un BMS de equilibrado.

| Ref. | 1S (por defecto) | 2S |
| --- | --- | --- |
| R103 (PROG) | 4.7 kΩ | 8.2 kΩ (C25924) |
| R102 (ILIM, techo de entrada) | 8.2 kΩ: ~1.45 A | 22 kΩ (C25768): ~2.9 A |
| R116 (EN del TPS62903) | 10 kΩ | 3.9 kΩ (C51721) |
| U103 | MAX17048G+T10 | MAX17049G+T10 (C18185545; JLCPCB tenía 50 a 9.60 USD) |
| R112 (VPACK → VDD del medidor) | 0 Ω | sin montar |
| R114 (+3V3 → VDD del medidor) | sin montar | 0 Ω |
| Batería | 1S2P: 2 × 18650 en paralelo (pack comercial con BMS) | 2 × 18650 en serie **con BMS de equilibrado** (el BQ25798 no equilibra) |

- **5 V de la carrier:** el TPS63070 trabaja igual en las dos variantes.
- **Cargador USB-C:** con 2S el cargador eleva desde 5 V y pide ~2.2 A de entrada; usar uno de 3 A.
  La placa no lee CC: no sabe si la fuente los da.
- La serigrafía trasera resume las dos variantes (R103, R116, U103, R112 y R114).

## Pedido en JLCPCB

Archivos del pedido, con **la placa sola en un panel**:

- `fab/tresvizo-panel-gerbers-jlcpcb.zip` (lo genera `build.py`; en git solo en los hitos)
- `fab/tresvizo-panel-bom-jlcpcb.csv`
- `fab/tresvizo-panel-cpl-jlcpcb.csv`

Los `fab/tresvizo-main-*` son de la placa sin panel, por si se pide así.

1. **PCB:**
   - Subir el zip del panel.
   - 4 capas, 1.6 mm, apilado JLC04161H-7628 (por defecto).
   - **Delivery Format: Panel by Customer**, un solo diseño, tamaño del panel **50 × 85.5 mm** y
     cantidad en paneles (un panel = una placa).
   - Acabado ENIG recomendado (o HASL sin plomo).
2. **Montaje:**
   - PCBA **Standard** (la estimación de costo la usa).
   - Una cara (top).
   - El panel ya trae rieles de 5 mm en los cuatro cantos, 3 fiduciales de 1 mm con el centro a
     3.85 mm del canto y 4 agujeros de herramienta de 2 mm, como pide JLCPCB.
   - La placa va unida al marco con 4 puentes de 5 mm con *mouse bites* (agujeros de 0.6 mm), dos en
     cada canto lateral: v 6.5 y 41 a la izquierda, v 13 y 24 a la derecha. Los cantos de arriba y
     de abajo no llevan puentes (en el de abajo están las bocas de los conectores).
   - Los puentes caen en los cantos por donde corren los rieles del chasis: **lijar la rebaba** al
     separar la placa.
3. Subir BOM y CPL del panel y elegir «Complete File, just proceed with my own files».
   **Revisar la orientación de cada pieza en la vista previa**, sobre todo:
   - U102, que usa la huella de TI de KiCad y no la de LCSC;
   - la polaridad de D403 (pad 1 = cátodo; los pads están renumerados respecto de EasyEDA);
   - U201, con la antena hacia el canto derecho mirando el frente (−X);
   - las piezas nuevas con huella de LCSC: J101, J102, SW401 y U401.
4. Fuera del BOM:
   - R114 (0 Ω de la variante 2S, sin montar);
   - J403: la OLED la suelda el propietario. Sus pads llevan pasta y salen estañados;
   - TP208 y TP209, que son solo pads.

   J404 sí se monta; la NTC va aparte, con su cable.

## Costo

Estimación de [fab/costo-jlcpcb.md](fab/costo-jlcpcb.md) para **5 placas** (un panel cada una), con
precios y existencias de la API pública de JLCPCB del 08-10-2026 y las tarifas de su página (no es
una cotización):

| Concepto | USD |
| --- | ---: |
| Piezas | 127.87 |
| Preparación Standard | 25.56 |
| Plantilla | 8.21 |
| Alimentadores: 40 piezas distintas × 1.53 | 61.20 |
| Juntas: 1940 × 0.0016 | 3.10 |
| Rayos X: 5 componentes (los BMI088) | 8.20 |
| **Montaje + piezas** | **234.15** |
| Por placa | 46.83 |

- **No incluye el PCB desnudo** (4 capas, en panel) ni el envío: salen en el cotizador.
- Lo que más pesa: los alimentadores (61.20 USD) y las piezas, sobre todo el BMI088 (6.79 USD;
  33.96 los cinco), el ESP32-S3-WROOM-1-N16R2 (5.80), el BQ25798 (2.93) y el MAX17048 (2.17).
- El BMI088 es LGA y JLCPCB lo marca para rayos X: 8.20 USD para los cinco.
- Frente a la v0.2 (209.08 USD por 5 juegos con la panel-usb, 07-10-2026) sube 25.07 USD. El
  BMI088 y sus rayos X suman 42.16; se ahorran el cargo por panel de dos diseños (8.21) y los
  conectores de cable que ya no van.
- El endurecimiento del 08-10-2026 cambia tres 22 µF (C45783) por 10 µF (C15850, *Basic*, que ya
  estaba en el BOM): unos 2.3 USD menos en los cinco juegos.
- 17 de las 40 piezas son *Extended*. Las nuevas de la v0.3 (LED KT-0603R, pulsador TS-1187A-B-A-B
  y la de 330 Ω) son *Basic*.
- **PCBA Standard:** no se comprobó si Economic admite el BMI088 (pide rayos X) y el WROOM;
  confirmarlo en el cotizador.
- Existencias: todas alcanzan para 5 placas. La menor es la del **BMI088: 409** (396 esa misma
  mañana, 682 el 07-10-2026 y 4 482 el 04-10-2026), que cambia rápido. Después vienen el
  ESP32-S3-WROOM-1-N16R2 (1165) y el TPS62903 (2172).

## Antes de mandar a fabricar

| Punto | ¿Frena el pedido? | Qué hacer |
| --- | --- | --- |
| Orden de VCC y GND de la OLED | Sí | El esquema usa VCC, GND, SCL, SDA, de la foto del anuncio del módulo (08-10-2026). Confirmarlo en la serigrafía de la unidad: si no coincide, cambiar `OLED_PINS` en `scripts/circuit.py` y regenerar. Cruzados, el módulo recibe la alimentación invertida |
| Fila de pines de la OLED | Sí | Se tomó a 1.4 mm del canto del módulo, deducido del plano del vendedor. Medirla con calibrador: si está unos 1.4 mm más lejos del canto, el módulo toca la lata del WROOM |
| Medidas de la carrier BDLX | Sí | Salen de una foto (±1 mm). Medirla con calibrador: de ellas dependen la muesca del SMA, el aire de 0.5 mm detrás de la placa y las ranuras del chasis |
| Antena GNSS: conector | Sí, para la tapa y el coaxial | Es la HA-901A del kit de BDLX. La tienda da «SMA-J» (macho) y conexión directa al SMA de la carrier, y la tapa está hecha para eso (SMA hembra de panel). Confirmar en la antena: macho = tuerca que gira y pin al centro; hembra = rosca por fuera y agujero al centro. Si es hembra se cambia un parámetro de la tapa |
| Existencias del BMI088 | Sí | 409 en la API de JLCPCB el 08-10-2026 por la tarde (396 esa mañana, 682 el 07-10): comprobarlas justo antes de pedir |
| Orientación en el CPL | Sí | En la vista previa de JLCPCB: U102 (huella de TI de KiCad), polaridad de D403 (pad 1 = cátodo) y también U201, J101, J102, SW401 y U401. Corregir el giro ahí |
| Cable del pack (J102) | Sí | GH 4: pines 1-2 BAT−, 3-4 BAT+, dos contactos por polo con cable AWG #26. Armarlo o confirmar el del pack y medir la polaridad con multímetro. La placa tiene protección contra inversión |
| Pinout de los conectores de la carrier | Sí, para el arnés | Leído de la serigrafía de la foto oficial; que el pin 1 sea el pad cuadrado es una suposición (no hay plano). **Antes de conectar el arnés, medir con multímetro en la carrier cuál pin es GND y cuál 5V_IN**: si estuviera al revés, los 5 V de J301 entrarían a una línea TTL del UM980 |
| NTC de la celda | Sí, para cargar | Comprar una NTC 10k B3435 con cable (no las de 100k de impresora 3D) y crimpar o comprar un cable SH 1.0 de 2 pines. Sin ella el cargador no carga (el GPS sí funciona con el USB) |
| Coaxial de la antena | No para la placa | RG 178 B/U de unos 77 mm entre conectores, con SMA hembra de panel en la tapa y SMA macho acodado de crimpar en la carrier. Sus curvas son de R 12.27 o más, por encima del mínimo fijo de la hoja actual de Lapp (6 × Ø, 10.9–11.6); para dobleces repetidos pide 10 × Ø: al dar servicio no doblarlo más. Falta elegir el conector de panel y el acodado |
| Irrupción al enchufar el USB | No | Reducida en el endurecimiento del 08-10-2026, no cerrada. **Decisión del propietario (08-10-2026): se acepta así**, sin piezas nuevas. Con el prototipo, medir la caída de VBUS al enchufar con un cable A–C a una computadora. Ver [Pendientes y riesgos](#pendientes-y-riesgos) |
| Soldar la OLED sobre pads SMD | No | Probar el método en una placa antes de montar el módulo bueno |
| Rebabas de los puentes del panel | No | Lijarlas antes de meter la placa en los rieles |
| Firmware para esta placa | No para fabricar | Todavía no existe; ver [Firmware](#firmware-qué-tiene-que-cambiar) |
| Nada medido | — | Pedir pocas placas y probar por bloques, empezando por la alimentación |

## Verificaciones

Lo comprobado con las herramientas (nada se ha fabricado ni medido):

| Comprobación | Resultado |
| --- | --- |
| ERC (KiCad 10.0.6, [fab/erc.rpt](fab/erc.rpt)) | 0 errores, 0 avisos |
| DRC de la placa ([fab/drc.rpt](fab/drc.rpt)) | 0 violaciones (errores y avisos), 0 sin conectar, 0 diferencias de paridad con el esquema |
| DRC del panel ([fab/drc-panel.rpt](fab/drc-panel.rpt)) | 0 violaciones, 0 sin conectar. Panel de 50 × 85.5 mm: rieles de 5 mm, 4 puentes con *mouse bites*, 3 fiduciales y 4 agujeros de herramienta |
| Áreas de regla | `clavija_*`, `canto_*`, `esp32_antena` y `guia_de_luz_D403` entran en el DRC de la placa: sin violaciones |
| Ruteo | En `build.py`, `route_rest.py` rutea 88 de 88 conexiones y, después de los rellenos, 1 de 1. Total: 1885 tramos (F.Cu 704 mm, In2.Cu 305 mm, B.Cu 1068 mm) y 282 vías, con el endurecimiento del 08-10-2026 |
| Reproducible, casi siempre | Con las entradas del endurecimiento (08-10-2026), dos `build.py` completos, uno en la rama y otro en una copia aparte, dieron iguales byte a byte el PCB de la placa y el del panel, y también los esquemáticos, `board.json`, BOM, CPL y posiciones. Antes, con las entradas de la auditoría, se corrió cuatro veces: dos `build.py` completos y dos réplicas de sus pasos. Tres dieron el mismo PCB byte a byte, y también los mismos esquemáticos, JSON, BOM, CPL, posiciones y mapa de pines. En la cuarta, el DRC de KiCad con `--refill-zones` contó 90 conexiones pendientes en lugar de 89, y salieron unos 10 tramos de GND y +3V3 distintos; esa placa también pasaba el DRC sin violaciones. Cada script da lo mismo con la misma entrada: la variación viene del relleno de zonas y del DRC de KiCad. Los archivos de la rama son los de las tres corridas que coincidieron. Los Gerber, el netlist, el esquema en PDF y los informes solo cambian en la fecha |
| Altos (`cad/check_heights.py`, sale con 0) | Las 106 piezas con modelo 3D (las 105 del BOM y R114) caben en el tubo de Ø56 con 0.5 mm de aire medido en radio, y fuera de las franjas. Lo más justo, además de esos 0.5: J102, 0.34 mm; U302, U303, J401, SW201 y SW202, 1.16; U201, 1.18; J101, 1.19. En el tubo anterior de Ø52, con 0.3 de aire medido en y, lo más justo era 0.05 mm |
| Endurecimiento eléctrico (08-10-2026) | Ninguna huella cambió de sitio, de giro ni de cara: se compararon con el PCB anterior las 117 de la placa y las 128 del panel. El plano de +3V3 de In2.Cu sigue de una pieza (1728 mm²; antes 1740). El STEP reexportado (`cad/export_board_step.py`) da las mismas cajas de todas las piezas; `cad/placa-principal.json` se dejó como estaba, porque solo cambiaba el orden de algunas listas. Detalle en [research/v03-compacta.md](research/v03-compacta.md#endurecimiento-eléctrico-08-10-2026) |
| Auditoría eléctrica independiente (08-10-2026) | Siete puntos, todos corregidos en `build.py`: OLED en pads SMD; puentes del panel lejos de U401 y de los condensadores de potencia; zona sin cobre de la antena ampliada; relleno de GND de J102 con 4 vías y vías dobles de VPACK; 4 vías de GND en el pad del WROOM; R409 de 330 Ω; TP208 y TP209. Lo que aceptó como riesgo está en [Pendientes y riesgos](#pendientes-y-riesgos) |
| *Bootstrap* del cargador | BTST1 → C101: 0.9 mm; BTST2 → C102: 1.6 mm (cara superior). Retorno a SW por vía y 4.3 / 5.7 mm de B.Cu |
| BOM y CPL | 40 líneas y 105 piezas montadas; el CPL tiene las mismas 105 |
| Carcasa V3.0 (`check_v3_0.py`, 08-10-2026) | Con el STEP final de la placa y sus zonas de clavijas: 0 choques en posición final, 11 barridos de montaje sin choques y la guarda de la pared del tubo pasa. Es de antes del endurecimiento; no se volvió a correr porque no cambiaron ni las piezas ni el contorno |
| Costo y existencias | API de JLCPCB del 08-10-2026, tras el endurecimiento: todas las piezas con existencias para 5 placas (la menor, el BMI088: 409) |

No comprobado: fabricación y montaje; ninguna medida eléctrica; el firmware para esta placa; el
orden de pines y la fila de la OLED; las medidas de la carrier y el pinout real de sus conectores;
el modelo de la antena GNSS; el soldado de la OLED sobre pads SMD; las pruebas de RF, de C/N0 y de
carga de [Pendientes y riesgos](#pendientes-y-riesgos); la carcasa impresa. La irrupción al enchufar el
USB y el calentamiento de las pistas internas son cálculos, no medidas.

## Pendientes y riesgos

Riesgos que la auditoría eléctrica del 08-10-2026 aceptó y lo que dejó el endurecimiento del mismo
día, con la prueba o el límite que piden:

- **Antena del WROOM.** Queda delante de la carrier (sus componentes a 0.5 mm del dorso de la placa
  y su PCB a 6.9 mm), cerca del plástico (la pared del tubo a 0.29 mm de la esquina del módulo) y de
  la OLED. Espressif pide 15 mm libres.
  - Hacer una prueba de RSSI y de caudal con todo montado.
  - Poner un M2 de nailon en el agujero de la OLED del lado de la antena (x −11.75).
  - Plan B: ESP32-S3-WROOM-1U-N16R2 (C3013945, con conector para antena externa) en la misma huella.
- **Desensibilización del GNSS.** Los armónicos del reloj de 40 MHz de la microSD caen en 1560 y
  1600 MHz, dentro de las bandas B1 de BeiDou (1561 MHz) y G1 de GLONASS (1598–1606 MHz). Medir el
  C/N0 con el Wi-Fi y la microSD activos. Si cae, lo primero a probar es la menor fuerza de salida de
  los GPIO de la microSD, sobre todo GPIO6 (CLK): sus líneas no tienen resistencias en serie y
  agregarlas sería una pieza nueva.
- **Corriente de carga.** Limitar ICHG a 1.5 A como mucho en el firmware (el BQ25798 arranca con
  1 A). El cable del pack va en AWG #26 a un GH 4, con dos contactos por polo de 1 A cada uno según
  JST. El techo de entrada no basta como tope por hardware: ver la tabla de
  [Firmware](#firmware-qué-tiene-que-cambiar).
- **Potencia por In2.Cu: cerrado en el endurecimiento del 08-10-2026** (cálculo, sin medir). VSYS
  al TPS62903 (13.7 mm) y GNSS_5V (26.1 mm) van por cobre interno de 0.5 oz.
  - Peor caso de la entrada del TPS62903: ~0.75 A de pico. Espressif pide una fuente de 0.5 A para
    el WROOM (355 mA de pico en TX); se suponen hasta 0.2 A de la microSD y ~40 mA del resto. Con
    VSYS de 3.0–3.4 V el TPS62903 va al 100 %: entra lo mismo que sale.
  - GNSS_5V: la carrier pide 160 mA (220 con UM982); con la antena y margen, 0.3 A.
  - Según IPC-2221, VSYS con 0.6 mm daba 0.5 A con 10 °C de subida (unos 25 °C a 0.75 A); con
    1.2 mm da 0.83 A (unos 8 °C). GNSS_5V con 0.6 mm da 0.5 A (unos 3 °C a 0.3 A; con 0.4 mm eran
    0.37 A y unos 6 °C).
  - Las vías de VSYS pasan a dos de 0.6/0.3 en el relleno y una de 0.8/0.4 junto a C116 (antes una
    de 0.6/0.3 en cada punta).
- **Plano de +3V3 cortado.** In2.Cu lleva 305 mm de pistas, 211 de ellas del bus del IMU. Las líneas
  de la microSD van por B.Cu sobre ese plano y cruzan sus ranuras: cada una tiene de 2.8 a 3.2 mm sin
  plano debajo y 14 cambios de referencia.
- **USB:** D+ mide 55.8 mm y D− 62.4 mm, no van juntos como par y tienen 4.9 y 9.0 mm sin plano
  debajo. Para USB Full Speed (12 Mb/s, lo único que tiene el ESP32-S3) el auditor lo da por bueno:
  la diferencia de largo son unas decenas de ps frente a un bit de 83 ns. Espressif recomienda, aun
  así, par diferencial con referencia continua.
- **Irrupción al enchufar el USB** (endurecimiento del 08-10-2026). En el BQ25798, entre VBUS y PMID
  solo hay la resistencia de medida de 8 mΩ, sin FET de bloqueo (hoja SLUSDV2C, diagrama de bloques
  y pines 2–3): al enchufar, la fuente carga de golpe los condensadores de VBUS y de PMID.
  - TI pide como mínimo 2 µF efectivos en VBUS y 4 µF en PMID (70 µF con el modo *backup*, que aquí
    no se usa) y recomienda 2 × 10 µF y 3 × 10 µF, más 100 nF en cada uno; no da otra guía de
    irrupción. La regla de USB 2.0, según TI (hoja del TPS2061, SLVS490K §9.1.8): si la carga al
    conectar supera 44 Ω ∥ 10 µF, hay que limitar la irrupción. La norma USB no se consultó.
  - C104 (VBUS), C106 y C107 (PMID) bajan de 22 a 10 µF (C15850, *Basic*): 30.2 µF nominales en
    lugar de 66.2. Con las curvas de Samsung (25 °C), a 5 V quedan ~15 µF efectivos (antes ~32) y
    ~118 µC de carga de 0 a 5 V (antes ~259), un 54 % menos. VBUS conserva ~5 µF efectivos y PMID
    ~10 µF, por encima de los mínimos de TI. PMID queda por debajo de los 3 × 10 µF que TI sugiere
    para 3.3 A de entrada, pero aquí ILIM la limita a ~1.45 A.
  - Sigue por encima de los 10 µF. Un cargador USB-C da VBUS recién al ver las Rd; el caso que queda
    es un cable A–C a un puerto ya encendido: un pico de corriente corto que puede hacer caer el VBUS
    de ese puerto o de su hub. El sobreimpulso del cable no pasa del doble de la fuente (~10.5 V),
    lejos de la TVS (15 V de trabajo).
  - Cerrarlo del todo pide piezas nuevas, y no se agregó ninguna: un par ACFET1/RBFET1 (dos
    N-MOSFET espalda con espalda entre J101 y VBUS, con VAC1 del lado del conector y las compuertas en
    ACDRV1, §7.3.5.3; la hoja no dice cuán despacio los enciende, habría que medirlo) o un
    interruptor de carga con arranque suave entre J101 y VBUS.
- **Entrada USB sin detección de CC**, igual que en la v0.2. Con una fuente de 500 mA la placa pide
  más de lo que da y el cargador baja la corriente cuando cae VBUS (VINDPM). El firmware puede bajar
  IINDPM por I2C (modo de carga lenta). Leer CC con un ADC del ESP32 y fijar IINDPM según lo que
  anuncie la fuente (0.5 / 1.5 / 3 A) queda pendiente.
- **Nodos SW del cargador:** unos 9 mm por B.Cu, como en la v0.2.

De la placa (detalle en [research/v03-compacta.md](research/v03-compacta.md#riesgos-de-la-placa)):

- Márgenes de alto de 0.05 a 0.07 mm en J401, SW201, SW202, U302, U303, U201 y J101.
- El canto del módulo OLED pasa 0.47 mm por encima del PCB del WROOM y a 1.4 mm de su lata, con la
  fila de pines sin medir.
- Bajo el cuerpo del WROOM (fuera de la antena) pasan unos 74 mm de pistas de señal en F.Cu, con
  máscara. En la v0.2 también las había.
- Los cuatro puentes del panel quedan en los 45 mm de arriba de la placa, y la parte de abajo cuelga
  unos 30 mm sin puente. Si JLCPCB pide otro puente, habría que mover piezas.
- Las vías del pad central del WROOM quedan a 0.05 mm de las esquinas de sus ventanas de máscara:
  tapadas, pero con muy poca máscara entre la vía y la ventana.
- El punto de pin 1 de la huella SOT-23-6 (U101, U302 y U303) quedó bajo el cuerpo; el CPL no
  depende de él.

De la v0.2, que siguen valiendo:

- **Nada medido:** carga 1S, modo *ship*, arranque del TPS63070 con la carrier y su consumo, ruido
  del GNSS (C/N0) con el ESP32 transmitiendo, alcance de BLE/Wi-Fi.
- **Bootstrap del BQ25798:** los condensadores quedan junto a sus pines en la cara superior, pero
  su retorno a SW pasa por una vía y 4–6 mm de B.Cu; TI lo muestra con los condensadores en la cara
  inferior, que aquí no se puede usar.
- **Plano interno de 3V3 perforado por las vías del ruteo automático:** quedan tiras y cuellos finos
  (el DRC no encuentra cuellos bajo 0.127 mm, pero conviene mirarlo a mano antes de pedir). Los
  planos internos van con 0.12 mm de margen a otras redes (JLCPCB admite 0.09 mm en capas internas)
  para que las vías dejen menos tiras.
- **Hoja del BQ2579x rev D:** la copia pública dice «TI Confidential»; pedir la oficial.
- **Ruteo automático** con `route_rest.py`, un ruteador propio (A* en rejilla con arranque y
  reruteo). Las pistas críticas están prerruteadas en `layout.py`:
  - lazos del cargador, nodos SW, *bootstrap*, BAT y la salida en abanico de su fila inferior;
  - el TPS62903 según su hoja de datos, el lazo del TPS63070 y su EN, y CELL y VDD del medidor;
  - en la v0.3, además, los buses de la microSD y del GNSS (B.Cu), el del IMU (In2.Cu), la
    alimentación y lo agregado tras la auditoría (ver
    [research/v03-compacta.md](research/v03-compacta.md#ruteo)).

  El resto se nota automático (escaleras de tramos de 0.1 mm, pistas bajo el ESP32).
  `finish_pcb.py` une con un tramo corto las vías que el ruteador deja tocando de canto una pista de
  su misma red.
- **Modelo 3D del BQ25798:** KiCad no trae el del RQM0029A; el STEP usa un VQFN de 4 × 4 mm.

## Regenerar

Requisitos: KiCad 10 (con su Python), Python 3 y FreeCAD 1.1 para el STEP en los ejes de la
carcasa. KiCad tiene que tener sus bibliotecas estándar en las tablas globales (Preferencias →
Gestionar bibliotecas); si no, el ERC y el DRC añaden cientos de avisos de «biblioteca no incluida»
que no son errores del diseño.

```bash
cd hardware/main-board/scripts
KICAD_APP=/Applications/KiCad/KiCad.app python3 build.py
```

Después del build, el STEP de la placa en los ejes de la carcasa y la comprobación de altos (desde
`hardware/main-board`; ver [cad/README.md](cad/README.md)):

```bash
PYTHONPATH=/Applications/FreeCAD.app/Contents/Resources/lib \
  /Applications/FreeCAD.app/Contents/Resources/bin/python cad/export_board_step.py
python3 cad/check_heights.py
```

- `export_board_step.py` escribe `cad/placa-principal.step` (el PCB y un sólido por componente, con
  su referencia) y `cad/placa-principal.json` (la caja de cada pieza). La carcasa V3.0 los usa.
- `check_heights.py` comprueba que cada pieza quepa bajo el tubo de `mechanical/v3.0` con 0.5 de aire
  medido en radio y fuera de las franjas de los cantos; si alguna no cabe, sale con 1.

El costo (desde `scripts`):

```bash
python3 cost_jlc.py ../fab/costo-jlcpcb.md 5 ../fab/tresvizo-main-bom-jlcpcb.csv ../kicad/tresvizo-main.kicad_pcb
```

- Consulta la API pública de JLCPCB y guarda lo leído en `fab/jlc_parts_cache.json` (fuera de
  git). Si ese archivo existe, reutiliza los precios y existencias guardados: borrarlo para
  consultarlos de nuevo.
- Con la panel-usb de la v0.2 se le pasan además su BOM y su PCB, y compara el panel de las dos
  placas con dos pedidos separados.

`build.py` hace todo el pedido:

- Placa principal:
  - `circuit.py` escribe el esquemático.
  - `layout.py` fija contorno, colocación, pistas críticas, zonas, clases de red y el panel.
  - `build_pcb.py` construye el PCB y `fanout.py` baja los pads de GND y +3V3 a sus planos.
  - `route_rest.py` rutea el resto y `finish_pcb.py` añade los rellenos de GND con vías de cosido.
    En la última vuelta (`finish_pcb.py --final`) quita además las vías que quedaron sin uso.
- Panel: `panelize.py` junta las placas de `kicad/panel.json` con rieles, fiduciales, agujeros de
  herramienta y mouse bites. En la v0.3 lleva solo la placa principal.
- Pedido: `export_jlc.py` saca BOM y CPL de la placa y del panel.

Otros scripts:

- `cost_jlc.py` estima el costo de montaje (arriba).
- `mklib.py` genera los símbolos propios.
- `logo.py` convierte el logotipo del repositorio en polígonos de serigrafía.
- `silk_clean.py` (dentro de `build.py`) corrige la serigrafía que el DRC marca encimada.
- `fp_silk_trim.py` recorta la serigrafía de una huella de la biblioteca que pisa sus propios pads
  (se usó una vez, con L2520, SOD-882 y `SolderJumper-2_P1.3mm_Bridged_RoundedPad1.0x1.5mm`,
  copiada de la biblioteca estándar de KiCad).
- `layout.py` escribe además `kicad/plugs.json`: las clavijas enchufadas, los agujeros y las muescas
  del contorno (`cutouts`: USB-C y SMA de la carrier), para comprobarlos en CAD contra la carcasa.
- El proyecto del panel usa la biblioteca de la placa principal, que ya tiene el USB-C (en la v0.2,
  `build.py` se lo copiaba de `../panel-usb`).
- Las huellas de `kicad/lib/lcsc.pretty` vienen de LCSC/EasyEDA (easyeda2kicad), para que la
  orientación coincida con la de JLCPCB. La del LED (D403) tiene los pads renumerados (1 = cátodo) y
  la de la OLED (`OLED_0.96in_I2C_4P_P2.54mm`) es propia, para el módulo del propietario.

No se guardan en git, por pesados y regenerables:

- los modelos STEP de LCSC (los `.wrl` sí);
- la caché de easyeda2kicad;
- los STEP de las placas;
- los Gerber (`fab/*-gerbers-jlcpcb.zip`), las vistas (`fab/*-top.png`, `fab/*-bottom.png`) y el
  esquema en PDF: cambian en cada vuelta. Se guardan solo en los hitos (pedido a JLCPCB, versión
  cerrada), con `git add -f`.

El build casi siempre es reproducible. Con las mismas entradas, `build.py` da los mismos PCB,
esquemáticos, JSON, BOM, CPL, posiciones y mapa de pines, byte a byte; los Gerber, el netlist, el
esquema en PDF y los informes solo cambian en la fecha. La excepción: en una de cuatro corridas, el
relleno de zonas y el DRC de KiCad dieron una conexión pendiente más, y el ruteo cambió en unos pocos
tramos de GND y +3V3. Esa placa también pasaba el DRC; ver [Verificaciones](#verificaciones). Para lo
demás:

- `kiid_seed.py` siembra los identificadores (KIID) de KiCad en cada paso con el contenido de sus
  entradas. KiCad ordena el PCB por esos identificadores, que de otro modo son aleatorios.
- `route_rest.py` toma del DRC solo qué dos islas faltan por unir y elige siempre los mismos extremos.
  El DRC no nombra siempre el mismo objeto de cada isla.

Si un paso se cae, `build.py` dice cuál y, si fue por una señal, cuál. Por ejemplo, el rellenador de
zonas de KiCad 10 se ha caído con la señal 11 con ciertas geometrías. `route_rest.py` guarda lo ruteado
antes de rellenar, para no perderlo.

La investigación con sus fuentes está en `research/`: v0.1 en los archivos originales, v0.2 en
[research/v02.md](research/v02.md) y v0.3 en [research/v03-compacta.md](research/v03-compacta.md).
