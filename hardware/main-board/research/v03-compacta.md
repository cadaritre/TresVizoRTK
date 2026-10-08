# v0.3 compacta: especificación de trabajo

Rama `hw/compact-v03`. Versión compacta del receptor a pedido del propietario (07-10-2026):
mismo concepto que V2.3 (tubo en el bastón, antena atornillada arriba), pero más chico, con
el panel dentro de la placa principal y dos 18650. Es exploratoria: no se ha fabricado nada.

Este documento fija las medidas y las interfaces para que la placa y la carcasa se diseñen
en paralelo. Lo que cambie durante el diseño se corrige aquí.

## Decisiones

| Tema | v0.2 / V2.3 | v0.3 compacta | Motivo |
| --- | --- | --- | --- |
| Carcasa | Tubo Ø64 × 130 con chasis de rieles | Tubo Ø52 × 100 con una cara plana al frente | Menos de la mitad de volumen |
| Batería | 1 × 18650 | 2 × 18650 en paralelo (1S2P), detrás de la carrier | Doble autonomía; la placa sigue en 1S |
| Panel | Placa panel-usb, OLED, botón metálico de 12 mm y cables | OLED, botón táctil, LED, USB-C y microSD en la placa principal | Sin cables al panel; el botón de 12 mm es difícil de conseguir |
| OLED | Módulo de 4 pines por cable (J403) | El mismo módulo, soldado por sus 4 pines a la placa, girado 180° | El propietario ya lo tiene; el firmware voltea la imagen |
| IMU | Breakout BMI088 en la tapa por J405 | BMI088 en la placa principal, en el mismo bus I2C (GPIO41/42, INT 2 y 1) | No hacen falta cable ni plataforma; queda rígido con el resto |
| Carrier | Arnés soldado a J301 | Igual: la carrier tal cual, arnés soldado a sus filas de agujeros | Sus agujeros solo se conocen a ±1 mm (foto): una mezzanine exige medidas exactas |
| NTC | Obligatoria (J404) | Igual | Decisión del propietario (4d1f15c) |
| Antena | HA-901A sobre la tapa de antena: 3 M2.5 desde dentro y su coaxial por un paso de 12 mm en el eje | Igual, sobre una tapa de arriba de Ø52 | La HA-901A mide Ø43.5: cabe en la cara de arriba. El modelo no está confirmado (`hardware/bom.md`: «Helix; modelo exacto por confirmar») |

## Ejes

Los de V2.x: **z = eje del bastón hacia arriba** (z 0 en la cara de apoyo de abajo), **+Y hacia
el frente** (la cara plana) y **+X a la izquierda mirando el frente**. Medidas en mm.

## Tubo

- Radio exterior 26 (Ø52), pared 1.8: radio interior 24.2. Alto 100 (z 0–100).
- Redondeo exterior de R 4 en los cantos de arriba y de abajo.
- Cara plana al frente, de 27.3 de ancho (|x| ≤ 13.65): por fuera en y 22.13 y por dentro en
  y 20.33.
- Por dentro, la cara plana (y 20.33) llega hasta |x| 13.65, no solo hasta donde la corta el
  círculo de r 24.2 (|x| 13.13). Así el vidrio de la OLED (|x| ≤ 13.35, frente en y 20.0) queda
  con 0.33 de aire. La pared queda de 1.8, salvo en la esquina interior de la cara plana
  (x ±13.65), donde baja a 1.5 hasta el círculo de fuera.
- Abajo: base desmontable con la tuerca 5/8"-11 de latón (23.8 entre caras, 13.9 de alto) en el
  eje, z 0–16, como en V2.3.
  - Sus retenes van lejos del frente: delante de la tuerca bajan la placa (hasta z 8.5) y las
    clavijas de J102, J404 y J301 con sus cables.
  - Con la base quitada se enchufan la batería y la NTC por abajo, como en V2.3.
- Arriba: tapa de antena desmontable, como la de V2.2 y V2.3, pero sujeta con tres M2.5
  radiales: el collar de una bayoneta no cabe dentro de r 24.2 con la OLED tan cerca del frente.
  - La HA-901A va atornillada por fuera con 3 M2.5 desde dentro, en un círculo de 26.6, y su
    coaxial pasa por un paso de 12 mm en el eje. Es la antena supuesta: `hardware/bom.md` dice
    «Helix; modelo exacto por confirmar».
  - Datos en `mechanical/v2.3/parameters.json`, `antena`.
- Interior como V2.3: un chasis que se arma fuera del tubo y entra por arriba, con la tapa quitada.
  - Lleva los rieles de la placa (en sus franjas de 1 mm), las ranuras de la carrier y dos
    salientes detrás de la placa.
  - Los dos M2 de abajo de la OLED atraviesan el módulo, su separador y la placa, y roscan en esos
    salientes. Esos tornillos sujetan la OLED y la placa.
  - Las dos celdas bajan antes por arriba a su cuna, en la pared de atrás. No hay tapa trasera.
  - La carrier entra al chasis por abajo y la sostienen dos ganchos. No puede entrar por delante
    ni por arriba: chocaría con los salientes de la OLED.
  - Detalle y comprobaciones en `mechanical/v3.0/README.md`.
- Frente: ventana de la OLED, tecla del botón (de TPU, que se pone por fuera después del chasis) y
  ventanita o guía de luz del LED.
- Costado izquierdo (+X): USB-C y ranura de la microSD.

## Pila de adelante hacia atrás (y)

| Pieza | y |
| --- | --- |
| Cara plana, por dentro | 20.33 |
| Componentes de la placa (cara de arriba hacia el frente), con 0.3 de aire | 15.4 a 20.03 |
| PCB principal (1.6) | 13.8 a 15.4 |
| Aire | 13.3 a 13.8 |
| Componentes de la carrier (6.4, hacia la placa) | 6.9 a 13.3 |
| PCB de la carrier (1.6) | 5.3 a 6.9 |
| Patas del SMA (no se cortan), solo bajo el SMA | 3.3 a 5.3 |
| Celdas: ejes en x ±9.5, y −7.9; Ø18.6 | −17.2 a 1.4 |

## Placa principal v0.3

- Plano: dorso en y 13.8 y cara en y 15.4; componentes solo por la cara (la de atrás mira a la
  carrier a 0.5 mm). Ninguna soldadura atraviesa la placa (auditoría del 08-10-2026):
  - la OLED va sobre pads SMD (ver abajo);
  - las únicas uniones pasantes son las cuatro patas de la carcasa del USB-C (GND). Miden 0.91 mm
    en el modelo 3D (1.01 según la auditoría) y se quedan dentro de los 1.6 de la placa.
- Contorno de trabajo: **x −18…+18 (36 de ancho) y z 8.5…80 (71.5 de alto)**. Los cantos
  laterales corren por los rieles del chasis. Si no cabe o no rutea, se puede proponer Ø54 o 105 de
  alto, con el motivo.
- Coordenadas de KiCad: **u = 18 − x, v = 80 − z** (u de 0 a 36 de izquierda a derecha mirando
  el frente; v de 0 a 71.5 hacia abajo).
- Alto máximo de los componentes según x, por la curva del tubo y la cara plana:
  `h(x) = min(4.63, sqrt(24.2² − x²) − 15.7)`.

  | \|x\| | 0–13.6 | 14 | 15 | 16 | 17 | 18 |
  | --- | --- | --- | --- | --- | --- | --- |
  | h máx. | 4.63 | 4.04 | 3.29 | 2.45 | 1.52 | 0.47 |

- **OLED:** el módulo de 4 pines I2C que ya tiene el propietario (27.5 × 27.8 × 1.6; vidrio u
  0.4–27.1 y v 4.27–23.53 del módulo; 4 agujeros de Ø2 en las esquinas; datos en
  `mechanical/v2.3/parameters.json`, `panel.pantalla`).
  - Va girado 180°, centrado en x 0, con sus pines abajo, soldados a la placa cerca de su canto
    de arriba.
  - Sobresale por encima del canto de arriba de la placa, hasta z ≈ 96. Su vidrio queda detrás de
    la ventana de la cara plana.
  - Debajo del tramo que pisa la placa no van componentes, solo pistas y vías.
  - Con z = 68.2 + v del módulo:
    - PCB del módulo en x −13.75…13.75, z 68.2–96;
    - pines en z 68.2–71.0 (columna central, paso 2.54);
    - vidrio en z 72.47–91.73;
    - cinta flexible hasta z ≈ 97;
    - agujeros de abajo en x ±11.75, z 70.2 (sobre la placa); los de arriba, en z 94.0.
  - Alto: el módulo lleva componentes por detrás (regulador SOT-23, unos 1.1 mm), así que va
    separado 1.3 mm de la placa. Encima van su PCB (1.6) y el vidrio (1.7): el vidrio llega a y 20.0
    (la cara plana, por dentro, está en 20.33).
  - **Montaje:** pines sin el separador de plástico de 2.5 mm, con uno de 1.3 a 1.5 mm o con
    arandelas. Si el módulo viene con la tira soldada, hay que quitarle el separador. Con el de
    2.5 mm, el vidrio quedaría en y 21.2, dentro de la cara plana.
  - **Pines sobre pads SMD (08-10-2026):** la placa no lleva agujeros para los pines.
    - Detrás de la fila de pines están el cuerpo y el cañón del SMA de la carrier (x −4.6…2.2, hasta
      y 13.4), con 0.4 mm de aire hasta el dorso.
    - Una soldadura pasante recortada asoma 0.3–0.8 mm. Al entrar la carrier por abajo, podía
      cortocircuitar +3V3 y SCL con la carcasa del SMA (GND).
    - J403 lleva cuatro pads de 1.7 × 2.4 en F.Cu, con pasta: JLCPCB los deja estañados. Van en v
      8.95–11.35, a 0.25 mm de los pads del WROOM.
    - Los pines del módulo se cortan a la altura del separador (1.3 mm) y se sueldan sobre los
      pads calentando cada pin desde el frente del módulo.
  - En la placa, agujeros sin metalizar de Ø2.2 bajo los dos agujeros de abajo del módulo.
    - Por ellos pasan dos M2 que roscan en dos salientes del chasis, detrás de la placa, y
      sujetan la OLED y la placa.
    - Ahí no hay carrier: llega a z 69 y su SMA está en x −1.2.
- **Botón:** SW401, pulsador táctil TS-1187A-B-A-B (5.1 × 5.1 × 1.5) con el centro en x 0, z 22
  (u 18, v 58), bajo la tecla. Alrededor, en 5 mm, solo piezas de 1 mm de alto o menos.
- **LED de estado:** D403 (0603 rojo) con el centro en x −6, z 22 (u 24, v 58), bajo su ventanita o
  guía de luz.
  - La guía de luz es de Ø2 y baja sobre D403: en r 1.5 alrededor de su centro solo puede ir D403
    (0.6 de alto); ninguna otra pieza, ni su cuerpo ni su patio. Es aparte de la zona de 5 mm del
    botón.
  - La placa lleva el área `guia_de_luz_D403` (sin huellas, en F.Cu) para que el DRC lo vigile: un
    anillo de r 1.25 a 1.5 alrededor del centro de D403, porque un círculo entero incluiría a D403.
    Lo de dentro del anillo se comprobó aparte (ver [Cómo quedó la placa](#cómo-quedó-la-placa-08-10-2026)).
- **Cantos laterales:** franja de 1.0 mm sin componentes en u 0–1 y u 35–36, para las ranuras o
  los labios de la pared. Ningún componente puede pasar de h(x).
- **Muesca del SMA** (08-10-2026): en el canto de arriba, u 14.2–24.2 y v 0–6.5 (x −6.2…3.8,
  z 73.5–80), abierta al canto, para la clavija del SMA de la carrier (ver
  [Carrier BDLX](#carrier-bdlx-tal-cual)).
  - Esquinas de dentro redondeadas con r 1.0: las corta una fresa de hasta 2 mm.
  - Nada se rutea por ella y el cobre guarda los 0.3 mm al canto, como en el resto de la placa.
  - `kicad/plugs.json` la lista en `cutouts` (`sma_carrier`, con su `r`), junto con la del USB-C
    (`usb_c`), en coordenadas de placa y de carcasa.
- **USB-C** (HRO TYPE-C-31-M-12: 8.94 de ancho, 7.9 de fondo y 3.25 de alto sobre la cara) en el
  costado izquierdo (+X), z ≈ 25.
  - Por su alto no puede ir en el canto: 3.25 pide |x| ≤ 15.0, y la boca queda en u ≈ 3.0
    mirando a +X.
  - La funda de la clavija mide hasta 12.35 × 6.5 (medida máxima recomendada por la norma USB
    Type-C) y va centrada en el eje del conector, y ≈ 17.0: llega hasta y 13.8. Por eso:
    - la placa lleva una muesca en u 0–3.1, a lo largo de z 25 ± 6.5 (v 48.5–61.5). Quedó en 3.1 y
      no en 3.0 porque el modelo 3D del conector mide 3.30 sobre la cara, no 3.25: con la boca en
      u 3.0, `cad/check_heights.py` daba −0.01 mm de margen; en u 3.1 da 0.07;
    - la pared lleva un bolsillo para la funda desde x 15.0 hacia fuera, en y 13.6–20.5 y
      z 25 ± 6.5.
- **microSD** (J401, TF-015 de empuje: 16.0 de ancho, 15.3 de fondo y 1.95 de alto) en el mismo
  costado, z ≈ 45.
  - Su alto pide |x| ≤ 16.5: la boca queda en u ≈ 1.5 mirando a +X.
  - La pared lleva una ranura para la tarjeta (11 de ancho). La tarjeta puesta queda unos 2 a 3 mm
    hacia dentro de la cara exterior: hace falta un rebaje para la uña o usar unas pinzas.
- **Antena del ESP32-S3-WROOM-1:** hacia el canto derecho (−X), a media altura, sin cobre debajo.
  Lejos del coaxial y del SMA de la carrier.
- **Conectores de cable:** solo en el canto de abajo (z 8.5), con la boca hacia abajo, porque a
  los lados no hay sitio para las clavijas:
  - J102 para el pack 1S2P: el JST PH lateral de v0.2 mide 5.5 de alto y no cabe (máximo 4.63).
    Pasa a JST GH de 4 pines lateral (SM04B-GHS-TB, C189895, unos 4.25 de alto), con dos contactos
    por polo: 1 y 2 a GND y 3 y 4 a VBATT_IN, unos 2 A por polo (1 A por contacto con cable
    AWG #26, según JST). El pack lleva un cable GH de 4 en AWG #26 y el firmware limita la carga
    (ICHG) a ~1.5 A (auditoría del 08-10-2026; ver
    [Riesgos aceptados](#riesgos-aceptados-en-la-auditoría-y-pruebas-pendientes));
  - J404 (SH2) para la NTC;
  - J301 (SH8) para el arnés de la carrier. El arnés sube por el costado derecho, detrás del canto
    de la placa, hasta la columna de agujeros de la carrier.
- Bajo el canto de abajo, la tuerca del bastón está en y ≤ 13: no choca con la placa (y ≥ 13.8).

## Carrier BDLX (tal cual)

- Modelo aproximado con sus componentes en `hardware/main-board/cad/carrier_bdlx.py`.
- Va centrada: x −16…+16, z 17…69. La cara de componentes mira a la placa, con el SMA arriba.
- Foto → carcasa: x = 16 − px y z = 69 − py.
- Su USB-C sobresale ~0.9 mm hacia +X.
- La columna de 8 agujeros, donde se suelda el arnés, queda en x −15.3, z 22.1–39.4. La fila de
  5 queda en z 17.6, x 4.1…−5.9.
- El eje del cañón del SMA queda en x −1.2, y 10.2, z 69.5–79.5. El coaxial de la antena baja
  por el paso de la tapa de arriba hasta este SMA.
  - La clavija que se enrosca en él (tuerca de 5/16", hasta 9.2 entre esquinas) llega a
    y ≈ 14.2–14.8, detrás del dorso de la placa (13.8). Por eso la placa lleva una **muesca en su
    canto de arriba: x −6.2…3.8, z 73.5–80 (u 14.2–24.2, v 0–6.5)**.
  - Entre la clavija recta (arriba en z 89.5) y el paso de la tapa (z 96–100, en el eje) solo cabe
    una curva en S de R 5.25. Ese tramo pide un coaxial fino (1.13 mm, que admite unos 5 a 6 mm
    en instalación fija, según los fabricantes) o un SMA acodado de perfil bajo. Un RG316 (Ø2.5)
    pide más radio.
- Se sujeta por sus cantos; no se le corta nada. Las ranuras no pueden pegarse a sus cantos
  delante de la cara ni detrás del PCB donde hay soldaduras. Ver lo aprendido en V2.3: rebaje del
  USB-C y labio cortado frente a la columna de agujeros.

## Celdas

2 × 18650 protegidas de Ø18.6 × 70, en paralelo. Ejes en (x ±9.5, y −7.9), z 17.5–87.5. Van en
una cuna detrás de la carrier, con la NTC pegada entre las dos y los cables al canto de abajo de
la placa (J102, J404).

## Cambios de esquema respecto a v0.2

- Fuera: J101 (USB del panel), J402 (botón), J403 (OLED por cable), J405 (IMU por cable) y la
  alimentación del anillo del botón de 12 mm.
- Dentro:
  - USB-C de 16 pines (el de la panel-usb: HRO TYPE-C-31-M-12, C165948), CC1/CC2 con 5.1 kΩ, TVS
    SMF15A en VBUS y USBLC6 (U101) junto al conector;
  - pulsador táctil a BTN_N, que sigue despertando al cargador (QON) y llega a GPIO18 por D402;
  - LED de estado en GPIO48 (antes BTN_LED_EN);
  - huella del módulo OLED (4 pines a 2.54 y agujeros de montaje);
  - BMI088 en la placa (como en v0.1), por I2C en GPIO41/42 con INT1 en GPIO2 e INT3 en GPIO1.
- J102 pasa de JST PH 2 a JST GH 4 (ver los conectores de cable, arriba).
- Sin cambios: ESP32-S3-WROOM-1-N16R2, cargador, reguladores, medidor, NTC, microSD y J301.
- La placa panel-usb deja de usarse en v0.3.

Cómo quedó el esquema (07-10-2026, ERC 0). Las piezas nuevas van después de las existentes, sin
renumerar nada:

| Ref | v0.2 | v0.3 |
| --- | --- | --- |
| J101 | GH 8 al panel | USB-C TYPE-C-31-M-12 (C165948) |
| J102 | PH 2 (C295747) | GH 4 SM04B-GHS-TB (C189895) |
| J403 | SH 4 a la OLED | Huella del módulo OLED (fuera del montaje de JLCPCB) |
| R409 | 100 Ω del anillo del botón | 330 Ω del LED de estado (C25104, ~4.4 mA; 1 kΩ hasta el 08-10-2026) |
| R119, R120 | — | Rd de 5.1 kΩ en CC1 y CC2 |
| SW401 | — | Pulsador TS-1187A-B-A-B (C318884) |
| D403 | — | LED rojo 0603 KT-0603R (C2286); GPIO48 lo maneja directo (red `LED_STATUS`) |
| U401, C403, C404 | — | BMI088 (C194919) y sus 100 nF |
| J402, J405, Q402, R410 | Botón, IMU por cable, FET y resistencia del anillo | Fuera (el número R410 queda sin usar) |
| TP208, TP209 | — | Puntos de prueba de U0TXD y U0RXD (GPIO43/44, redes `ESP_TXD0` y `ESP_RXD0`; 08-10-2026) |

Pendiente antes de pedir:

- **Orden de GND y VCC en la OLED.** Los pines 3 y 4 son SCL y SDA en las dos variantes conocidas.
  GND y VCC cambian de lugar según el fabricante; si quedan cruzados, el módulo recibe la
  alimentación invertida.
  El esquema usa GND, VCC, SCL, SDA. Hay que leer la serigrafía del módulo; si no coincide, se
  cambia `OLED_PINS` en `circuit.py`.
- **Alto de la fila de pines de la OLED:** está a 1.4 mm del canto del módulo, sacado del plano
  del vendedor. Conviene medirlo con calibrador.
  - En la placa terminada, ese canto (v 11.8) queda a 0.3 mm del canto del PCB del WROOM (v 12.1)
    y a 1.4 mm de su lata (v 13.2 en el modelo 3D). El PCB del módulo (desde y 16.7) pasa
    0.47 mm por encima del PCB del WROOM (hasta y 16.23), pero la lata llega a y 18.51: si la fila
    está unos 1.4 mm más lejos del canto, el módulo toca la lata.
- **Existencias del BMI088 en JLCPCB:** 396 piezas el 08-10-2026 (API de JLCPCB, `cost_jlc.py`),
  682 el 07-10-2026 y 4 482 el 04-10-2026. Bajan rápido: comprobarlas justo antes de pedir.

La lista completa, con las medidas de la carrier, la antena GNSS y la revisión del CPL, está en
[Antes de mandar a fabricar](../README.md#antes-de-mandar-a-fabricar).

## Cómo quedó la placa (08-10-2026)

Generada entera con `scripts/build.py`; el contorno, la colocación y las pistas críticas están en
`scripts/layout.py`. Rehecha el mismo día tras una auditoría eléctrica (ver
[Auditoría eléctrica](#auditoría-eléctrica-08-10-2026)). Nada fabricado ni medido.

### Colocación

Cajas de los cuerpos 3D (de `cad/placa-principal.json`), en coordenadas de placa y de carcasa:

| Bloque | Piezas | u | v | x | z | Alto |
| --- | --- | --- | --- | --- | --- | --- |
| Pines de la OLED | J403 | 14.2–21.8 | 10.4 | 3.8…−3.8 | 69.6 | — |
| ESP32-S3-WROOM-1, antena hacia −X | U201 | 7.65–33.15 | 12.1–30.1 | 10.35…−15.15 | 49.9–67.9 | 3.11 |
| BOOT y RESET | SW201, SW202 | 1.5–4.4 | 14.3–30.4 | 16.5…13.6 | 49.6–65.7 | 1.95 |
| microSD, boca hacia +X | J401 | 1.5–16.75 | 32.0–48.0 | 16.5…1.25 | 32.0–48.0 | 1.95 |
| 5 V del GNSS | U301, L301 | 27.0–30.0 | 32.5–38.0 | −9.0…−12.0 | 42.0–47.5 | 0.90 |
| Cargador | U102, L101, Q101 | 23.7–34.65 | 38.6–53.4 | −5.7…−16.65 | 26.6–41.4 | 3.10 |
| USB-C, boca hacia +X | J101 | 3.1–11.0 | 50.45–59.55 | 14.9…7.0 | 20.45–29.55 | 3.30 |
| ESD del USB | U101 | 13.9–16.8 | 50.0–52.8 | 4.1…1.2 | 27.2–30.0 | 1.65 |
| Botón | SW401 | 14.75–21.25 | 55.4–60.6 | 3.25…−3.25 | 19.4–24.6 | 1.55 |
| LED | D403 | 23.2–24.8 | 57.6–58.4 | −5.2…−6.8 | 21.6–22.4 | 0.71 |
| 3.3 V | U105, L102 | 26.9–31.2 | 58.1–61.8 | −8.9…−13.2 | 18.2–21.9 | 0.92 |
| Medidor | U103 | 17.4–19.4 | 60.9–62.9 | 0.6…−1.4 | 17.1–19.1 | 0.78 |
| IMU | U401 | 2.5–5.5 | 64.65–69.15 | 15.5…12.5 | 10.85–15.35 | 1.00 |
| NTC (boca hacia abajo) | J404 | 7.1–11.1 | 66.05–71.0 | 10.9…6.9 | 9.0–13.95 | 2.91 |
| Batería (boca hacia abajo) | J102 | 11.8–20.0 | 65.9–70.8 | 6.2…−2.0 | 9.2–14.1 | 4.26 |
| GNSS (boca hacia abajo) | J301 | 21.0–31.0 | 65.9–70.85 | −3.0…−13.0 | 9.15–14.1 | 2.91 |
| ESD del GNSS | U302, U303 | 32.0–34.8 | 65.1–71.2 | −14.0…−16.8 | 8.8–14.9 | 1.65 |
| Pruebas de UART0 (solo pads) | TP208, TP209 | 21.15–24.15 | 31.0–32.0 | −3.15…−6.15 | 48.0–49.0 | — |

- Antena del ESP32: área `esp32_antena`, sin pistas, vías ni rellenos en las cuatro capas.
  - Va de donde empieza la antena del módulo (u 26.64, x −8.64) hasta el canto (u 36, x −18).
  - En v va de 9 a 30.6 (z 71–49.4). A la derecha de u 32 baja hasta v 32 (z 48).
  - Hasta la auditoría era solo la antena, v 12.1–30.1, y el cobre llegaba a su borde de arriba y
    de abajo. Ahora el cobre más cercano queda a 3.1 mm por arriba, a 0.5 mm por abajo entre u 27 y
    32 y a 1.9 mm entre u 32 y la punta.
  - Entre u 27 y 32 no se puede bajar más: ahí está la fila de arriba del TPS63070 (R301 y C304,
    con sus pads en v 30.77). El bloque no puede bajar porque L301 queda a 0.6 mm de L101.
- Debajo del tramo de la OLED que pisa la placa (v 0–11.8, u 4.25–31.75) no hay componentes.

### Desviaciones

1. **Punta de la antena del WROOM en u 33.15 (x −15.15), no en el canto.** `check_heights.py` toma
   cada pieza como una caja de su alto entero (3.11 en el módulo, aunque en la antena solo hay
   PCB), y así el módulo no pasa de |x| ≈ 15.2. El área sin cobre llega igual hasta el canto.
2. **Boca del USB-C en u 3.1**, no en 3.0 (ver el USB-C, arriba).
3. **Zona del botón medida desde su centro.** Las piezas cuya caja queda a menos de 5 mm del centro
   de SW401 miden 1 mm o menos: U103 a 2.89 mm (0.78 de alto), R409 a 3.70, R113 a 4.13, D401 a
   4.28 (0.40), R120 a 4.50 y R102 a 4.72. Es como lo toma la carcasa (`placa.boton.radio_bajo`).
   Medida desde el cuerpo del pulsador, U101 (1.65 de alto), Q102 (1.05) y J101 (3.30) quedarían
   dentro.

### Ruteo

- Capas: F.Cu, señales y GND; In1.Cu, GND entero (sin pistas); In2.Cu, +3V3 con GND bajo el
  cargador; B.Cu, señales y GND.
- Prerruteado en `layout.py`, además de lo de v0.2 (lazos del cargador, TPS62903, TPS63070 y
  medidor):
  - el bus de la microSD y el del GNSS (UART, PPS, EVENT y RESET hasta R304–R309, junto a J301), por
    B.Cu;
  - el bus del IMU (I2C, INT1 e INT3, de U201 a U401), por In2.Cu;
  - la esquina de ESD del GNSS (U302 y U303) y las salidas de la fila de abajo del cargador;
  - la alimentación: VBUS de J101 al cargador; VPACK de Q102 al cargador por B.Cu (1.0 y 0.8 mm),
    a lo largo del canto de abajo y del derecho; VSYS al TPS62903, y GNSS_5V del TPS63070 a J301.
  - lo agregado tras la auditoría:
    - las dos vías de cada cambio de capa de VPACK;
    - el relleno y las vías de GND de J102;
    - las vías del pad central del WROOM;
    - la vía de GND de C113 y la del pin 15 del TPS63070;
    - la rama de GNSS_5V a R302 (el divisor de realimentación);
    - la llegada de SD_DET a Q401 por la derecha;
    - U0TXD y U0RXD hasta sus puntos de prueba;
    - una pista de GND de J401.10 a J401.6.
- `route_rest.py` rutea el resto: 89 de 89 conexiones en la primera pasada y 1 de 1 en la segunda,
  después de los rellenos. `finish_pcb.py --final` quita al final las vías que quedaron sin uso
  (dos, de I2C).
- Total: 1880 tramos (F.Cu 703 mm, In2.Cu 304 mm, B.Cu 1067 mm) y 282 vías, con las entradas finales.
- **Potencia por capa interna**, que en v0.2 iba solo por fuera: VSYS al TPS62903 por In2.Cu con
  0.6 mm (12.8 mm de largo) y GNSS_5V con 0.4 mm (26.1 mm). Por fuera ya no había paso: el ruteador
  daba vueltas de 68 a 136 mm. Según IPC-2221, en cobre interno de 0.5 oz, 0.6 mm llevan unos 0.5 A y
  0.4 mm unos 0.37 A con 10 °C de subida. La carrier pide 160 mA. Con los picos de Wi-Fi del ESP32 y
  la microSD, la entrada del TPS62903 puede acercarse a 0.5 A por poco tiempo (estimado, sin medir).
- **Plano de +3V3 cortado.** In2.Cu lleva 304 mm de pistas: el bus del IMU (211 mm), GNSS_5V, I2C,
  FG_ALRT_N, VSYS, ESP_EN y otras cortas.
  - El +3V3 queda de una pieza (1740 mm²), pero las líneas de la microSD van por B.Cu, apoyadas en
    él, y cruzan el bus del IMU.
  - Cada una tiene de 2.8 a 3.2 mm sin plano justo debajo (en los cruces y en los antipads de las
    vías) y 14 cambios de referencia.
- **USB:** D+ mide 55.8 mm y D− 62.4 mm, no van juntos como par y tienen 4.9 y 9.0 mm sin plano
  debajo. Los pines USB del WROOM quedan arriba (v 12.35) y el conector en v 55.

### Comprobaciones

| Comprobación | Resultado |
| --- | --- |
| ERC (`fab/erc.rpt`) | 0 errores, 0 avisos |
| DRC de la placa (`fab/drc.rpt`) | 0 violaciones (errores y avisos), 0 sin conectar, 0 de paridad con el esquema |
| DRC del panel (`fab/drc-panel.rpt`) | 0 violaciones, 0 sin conectar. Panel de 50 × 85.5 mm: rieles de 5 mm, 4 puentes de 5 mm con *mouse bites* (dos por canto lateral), 3 fiduciales y 4 agujeros de herramienta |
| Puentes del panel | Centros en v 6.5 y 41 a la izquierda y en v 13 y 24 a la derecha (z 73.5, 39, 67 y 56). El condensador de potencia más cercano a un puente está a 6.0 mm (C201, del puente de v 13); U401, a 21.3 mm del puente de v 41 |
| Reproducible, casi siempre | Después de la auditoría, dos `build.py` seguidos dieron iguales, byte a byte, los PCB, los esquemáticos, `board.json`, `plugs.json`, `panel.json`, BOM, CPL, posiciones y mapa de pines. Con las entradas finales (nota de J102 corregida) hubo cuatro corridas: dos `build.py` y dos réplicas de sus pasos. En una, el DRC de KiCad contó 90 conexiones pendientes en lugar de 89, por el relleno de zonas, y unos 10 tramos de GND y +3V3 salieron distintos; también pasaba el DRC. Las otras tres coincidieron, y son las de la rama. Los Gerber, los taladros, el netlist, el esquema en PDF y los informes solo cambian en la fecha |
| Altos (`cad/check_heights.py`, sale con 0) | Las 106 piezas con modelo caben con 0.3 de aire y fuera de las franjas. Las más justas: J401, SW201 y SW202 0.05; U302, U303 y U201 0.06; J101 0.07; J102 0.37 |
| Botón | Ver Desviaciones, punto 3 |
| Guía de luz | En r 1.5 alrededor de D403 no hay nada más. Lo más cerca: el patio de R409 a 1.59 mm del centro (su cuerpo a 1.80) y el de R102 a 1.97 |
| Muescas en el STEP | `cad/placa-principal.step`: el centro de la muesca del SMA (u 18, v 3) y el de la del USB-C quedan fuera del sólido de la placa; el redondeo de r 1.0 sí está |
| BOM | 40 líneas, 105 piezas montadas; R409 pasa a 330 Ω (C25104, Basic según la API de JLCPCB del 08-10-2026, en `fab/costo-jlcpcb.md`). TP208 y TP209 no van al BOM (son pads) |
| CPL | La rotación es la de KiCad, sin `jlc_rotations.json`, como en v0.2. Las piezas nuevas con orientación (J101, J102, SW401, D403 y U401) usan huellas de LCSC/EasyEDA, hechas para que su 0° sea el de JLCPCB; U102 sigue con la huella de TI de KiCad. D403 tiene los pads renumerados respecto a EasyEDA (1 = cátodo). Como en v0.2, hay que revisar la orientación y la polaridad en la vista previa de JLCPCB |

### Auditoría eléctrica (08-10-2026)

Una revisión eléctrica independiente de la placa pidió estos cambios; todos quedaron en `build.py`:

| Punto | Qué se hizo |
| --- | --- |
| 1. Pines de la OLED frente al SMA de la carrier (crítico) | J403 con cuatro pads SMD de 1.7 × 2.4, sin agujeros (ver la OLED, arriba). Se quedan los dos NPTH de Ø2.2. La única unión pasante de la placa son las patas de la carcasa del USB-C, que no salen por detrás |
| 2. Puentes del panel junto a piezas sensibles | Antes: v 6.5 y 66 a la izquierda (el de 66, a 2.5 mm de U401) y v 5.5 y 50 a la derecha (a 0.5 mm de C201 y a 1.25 mm de C113). Ahora: v 6.5 y 41 (junto a la carcasa de la microSD) a la izquierda, y v 13 y 24 (en la franja de la antena) a la derecha. Todos a 6 mm o más de los condensadores de potencia y a 21 mm o más de U401 |
| 3. Cobre alrededor de la antena | Zona sin cobre ampliada (ver la colocación). C201 y C202 siguen en u 33.5, v 3–5.7, a unos 9–12 mm del pin 3V3 (pin 2, u 24.37, v 12.35). Más cerca del pin solo hay sitio bajo la OLED (sin componentes) o dentro de la zona de la antena |
| 4. Camino de la batería | J102.1 y J102.2 (GND) van a un relleno propio de F.Cu (39 mm², pads sin alivios térmicos) con los anclajes y cuatro vías de 0.6/0.3. Antes salían por pistas de 0.25 mm a una vía cada uno. VPACK cambia de capa con dos vías de 0.8/0.4 en cada punto: junto a Q102, en (10.95, 63.25) y (11.85, 63.45). Junto a Q101, en (34.35, 46.25) y (35.2, 45.7): la columna del canto derecho sube recta y ya no va la vía de (32.05, 46.6). C113 lleva su vía de GND en (35.35, 48.1) |
| 5. Pad central del WROOM sin vías | Cuatro vías de 0.6/0.3 en los cruces de los huecos entre sus nueve pads, unidas a ellos por F.Cu de 0.3 mm. La cuarta va en el hueco de la derecha: el cruce de arriba a la izquierda cae sobre el bus de la microSD (B.Cu) |
| 6. LED de estado tenue | R409 de 1 kΩ a 330 Ω (C25104): unos 4.4 mA desde GPIO48, que da hasta 20 mA |
| 7. Puntos de prueba de UART0 | TP208 (U0TXD) y TP209 (U0RXD), `TestPoint_Pad_D1.0mm`, en (23.65, 31.5) y (21.65, 31.5), bajo los pines 37 y 36. Para que cupieran se prerrutearon SD_DET hasta Q401, la rama de GNSS_5V a R302 y una pista de GND de J401.10 a J401.6. Sin eso, el ruteador dejaba R302 sin conectar o encerraba el relleno de GND de J401.10 |

Ninguna pieza cambió de sitio; solo se agregaron TP208 y TP209. La huella de J403 cambió (pads SMD), con el
mismo origen.

### Riesgos aceptados en la auditoría y pruebas pendientes

La auditoría dejó estos puntos como riesgos aceptados o como pruebas para el primer prototipo; no
cambian la placa:

| Punto | Qué queda |
| --- | --- |
| Antena del WROOM | Delante de la carrier, cerca del plástico (la pared del tubo a 0.29 mm de la esquina del módulo, según V3.0) y de la OLED. **Prueba de RSSI y de caudal con todo montado.** En el agujero de la OLED del lado de la antena (x −11.75), un **M2 de nailon**. Plan B: ESP32-S3-WROOM-1U-N16R2 (C3013945, antena externa) en la misma huella |
| Desensibilización del GNSS | Los armónicos del reloj de 40 MHz de la microSD caen en 1560 y 1600 MHz. **Medir el C/N0 con el Wi-Fi y la microSD activos** |
| Corriente de carga | **ICHG de ~1.5 A como mucho, en el firmware** (el BQ25798 arranca con 1 A). El pack va con cable **AWG #26** en el GH 4 de J102: dos contactos por polo, de 1 A cada uno según JST |
| Líneas de la microSD sobre las ranuras del plano de +3V3 | Aceptado (ver [Ruteo](#ruteo)) |
| D+/D− sin ir como par | Aceptado: a 12 Mb/s (USB Full Speed) no importa, según el auditor |
| VSYS (0.6 mm) y GNSS_5V (0.4 mm) por In2.Cu, de 0.5 oz | Aceptado: unos 0.5 A con 10 °C de subida (ver [Ruteo](#ruteo)) |
| Entrada USB sin leer CC | Igual que en v0.2: con una fuente de 500 mA la placa pide más de lo que da y el cargador baja la corriente al caer VBUS (VINDPM) |
| Nodos SW del cargador | Unos 9 mm por B.Cu, igual que en v0.2 |

### Riesgos de la placa

- Márgenes de alto de 0.05 a 0.07 mm en J401, SW201, SW202, U302, U303, U201 y J101.
- Los modelos 3D de D403 (0.71 de alto) y SW401 (1.55) son más altos que lo que tomaba la carcasa
  (0.6 y 1.5). Resuelto en V3.0: con la placa real (`cad/placa-principal.step`),
  `mechanical/v3.0/check_v3_0.py` da la guía de luz a 0.345 de D403 y el émbolo de la tecla a 0.355
  de SW401 (ver `mechanical/v3.0/README.md`).
- El canto del módulo OLED pasa 0.47 mm por encima del PCB del WROOM y a 1.4 mm de su lata, con la
  fila de pines sin medir (ver arriba, en lo pendiente).
- La antena del ESP32 tiene la carrier detrás: la envolvente de sus componentes llega a 0.5 mm del
  dorso de la placa y su PCB está a 6.9 mm. Espressif pide 15 mm libres.
- Bajo el cuerpo del WROOM (fuera de la antena) pasan unos 74 mm de pistas de señal en F.Cu, con
  máscara: SD_DET, I2C, GNSS_PWR_EN, CHG_INT_N, USB y otras. En v0.2 también las había.
- Los cuatro puentes del panel quedan en los 45 mm de arriba de la placa. La parte de abajo cuelga
  unos 30 mm sin puente: en el canto de abajo están las bocas de los conectores, U401 y U302/U303;
  a la derecha, C113, C115-C117 y la ESD del GNSS; a la izquierda, la muesca del USB-C y U401. Si
  JLCPCB pide otro puente, habría que mover piezas.
- Las vías del pad central del WROOM van en los huecos entre sus pads, a 0.05 mm de las esquinas de
  sus ventanas de máscara: quedan tapadas, pero con muy poca máscara entre la vía y la ventana.
- Los pines de la OLED se sueldan a mano sobre pads SMD, a 1.3 mm de la placa: conviene probar el
  método en una placa antes de montar el módulo bueno.
- El punto de pin 1 de la huella SOT-23-6 (U101, U302 y U303) quedó bajo el cuerpo: se movió porque
  caía sobre los pads de las piezas vecinas. Después del montaje no se ve; el CPL no depende de él.

## Criterios de aceptación

- ERC 0.
- DRC con 0 violaciones, 0 sin conectar y 0 de paridad; ruteo completo con `build.py` y build
  reproducible.
- Placa dentro del contorno, con los altos de la tabla, clavijas con sus zonas y STEP exportado.
- Carcasa sin choques con:
  - la placa real (STEP);
  - la carrier con componentes;
  - las celdas;
  - la tuerca y sus retenes, la antena con sus tornillos y el SMA;
  - el coaxial y los cables.
  Que todo pueda armarse en orden.
- Documentación en español, sin afirmar nada que no se haya comprobado.
