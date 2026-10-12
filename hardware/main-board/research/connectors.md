# Placa principal — conectores

Propuesta del 04-10-2026. Complementa `constraints.md` (envolvente y ubicación) y
`gpio_map.csv` (GPIO). Los números de pieza, clase JLC, existencias y precios están
en `parts_connectors.csv`. Nada de esto se ha montado ni probado.

**El IMU va soldado en la placa** (BMI088, decisión del propietario del
04-10-2026): ya no hay conector de IMU ni breakout. Su circuito está en
`constraints.md`, sección 5.

## Resumen

| Conector | Familia y contactos | Pieza propuesta (LCSC) | Notas |
| --- | --- | --- | --- |
| PANEL_PWR | JST PH 4, SMD lateral | S4B-PH-SM4-TB(LF)(SN), C265102 | Era «PANEL_USB» del encargo: el panel de V2.2 ya solo trae VIN/GND (JST-XH) |
| PANEL_USBD | JST SH 6, SMD lateral | HC-1.0-6PWT (HCTL), C2845365 | Opcional, sin montar mientras el panel no tenga USB-C con datos |
| PANEL_UI | JST SH 9, SMD lateral | SM09B-SRSS-TB(LF)(SN), C160408 | Botón, LED del botón, RGB y LED de carga |
| OLED | JST SH 4 (Qwiic), SMD lateral | SM04B-SRSS-TB(LF)(SN), C160404 | |
| UM980_AUX | JST SH 5, SMD lateral | SM05B-SRSS-TB(LF)(SN), C136657 | COM1, PPS, EVENT |
| BATTERY | JST PH 2, SMD lateral | S2B-PH-SM4-TB(LF)(SN), C295747 | |
| IMU | — | — | Ya no existe: BMI088 en la placa |
| Antena | u.FL | U.FL-R-SMT-1(10), C88373 | |
| USB de la placa | USB-C 16 contactos | TYPE-C-31-M-12, C165948 | Canto inferior |

## Familias elegidas

| Uso | Familia | Por qué |
| --- | --- | --- |
| Señales | **JST SH, paso 1.0 mm, SMD de entrada lateral** (`SMxxB-SRSS-TB`) | Bajo (el header mide 2.9 mm sobre la placa según LCSC; la altura con la clavija puesta no se pudo verificar porque los planos de JST están cifrados), con traba, 1 A por contacto (AWG28), 50 V; el de 4 pines es Qwiic, el estándar que ya usan la OLED y la Thing Plus. Genuinos de JST con existencias en JLC en 4, 5 y 9 contactos; el de 6 solo como clon. |
| Potencia | **JST PH, paso 2.0 mm, SMD de entrada lateral** (`SxB-PH-SM4-TB`) | 2 A por contacto con cable AWG24, 100 V; es el conector habitual de baterías LiPo con clavija. Para la entrada de carga se usan **dos contactos por polo**. Altura sobre la placa sin verificar (~5–6 mm por catálogo): fuera de la zona del botón. |

Reglas de uso:

- **Ningún par de conectores de la misma familia tiene el mismo número de
  contactos**, para que no se pueda enchufar un mazo en el sitio de otro: SH de 4
  (OLED), 5 (UM980_AUX), 6 (PANEL_USBD, opcional) y 9 (PANEL_UI); PH de 2
  (BATTERY) y 4 (PANEL_PWR).
- Todos en la **cara frontal**, dentro de la franja visible por la ventana del panel
  (x = ±15.5, z 33.5–98.4; `constraints.md` 1.4), salvo BATTERY, que va abajo.
- Entrada lateral con la boca hacia arriba o hacia abajo (paralela a la placa): con
  la clavija puesta no pasa de la altura máxima de la cara frontal (10 mm; 4 mm bajo
  el botón).
- Pin 1 marcado en serigrafía con el nombre de cada señal. El pin 1 de JST está a la
  izquierda mirando la boca con la traba arriba; comprobarlo con el plano de la
  pieza elegida antes de fijar la huella.

## Corriente de la entrada de carga

Peor caso: cargar una batería **2S a 1 A** desde 5 V con el equipo funcionando.
8.4 V × 1 A = 8.4 W en la batería; con un rendimiento de ~90 % en elevación son
~9.3 W, y el equipo suma ~1.2 W (UM980 ~0.5 W y ESP32 con Wi-Fi; cifras
aproximadas, sin medir). Total ≈ 10.5 W → **≈ 2.2 A a 4.8 V**. Con 1S a 1 A son
≈ 1.3 A. El PH admite 2 A por contacto: con dos contactos por polo quedan 4 A
para 2.2 A. El límite de entrada lo programa el firmware en el BQ25792; una fuente
USB sin negociación solo garantiza 0.5–0.9 A (USB 2.0/3.x) o lo que anuncie por CC
(1.5/3 A), así que el firmware tiene que bajar la corriente de carga a lo que dé
la fuente.

## PANEL_PWR — entrada de carga desde el panel (JST PH, 4 contactos)

El panel de V2.2 lleva ahora un **header JST-XH de 2 pines** en lugar del USB-C
(`constraints.md`, C1). Su mazo llega a este conector.

| Pin | Señal | Dirección | Nota |
| --- | --- | --- | --- |
| 1 | VIN | entrada | Del conector de carga del panel (5 V USB; el BQ25792 admite hasta 24 V en VBUS, ver `constraints.md` 3). |
| 2 | VIN | entrada | Segundo contacto en paralelo. |
| 3 | GND | — | |
| 4 | GND | — | |

En la placa: protección contra polaridad inversa (el panel no tiene llave para
evitarla con cualquier cargador), TVS a GND y fusible o PTC, antes de VBUS/VAC1 del
BQ25792. Con dos entradas (este conector y el USB-C de la placa), usar la selección
de doble entrada del BQ25792 (VAC1/VAC2 con sus MOSFET ACDRV) o un diodo ideal; no
unir dos VBUS directamente.

## PANEL_USBD — datos USB del panel (JST SH, 6 contactos) — opcional

Solo si el panel vuelve a llevar un USB-C con datos. Con el JST-XH actual se deja
sin montar y el USB del ESP32 sale por el USB-C de la placa.

| Pin | Señal | Nota |
| --- | --- | --- |
| 1 | GND | Masa del par |
| 2 | USB_DN | A GPIO19 por 0 Ω (DNP si se usa el USB-C de la placa) |
| 3 | USB_DP | A GPIO20 por 0 Ω (idem) |
| 4 | GND | |
| 5 | CC1 | 5.1 kΩ a GND en la placa (DNP si el breakout del panel ya los trae) |
| 6 | CC2 | idem |

VBUS de ese USB-C entra por PANEL_PWR. Sin 5.1 kΩ en CC1 y CC2 (en el panel o en
la placa), un cargador USB-C a USB-C no entrega 5 V. Las dos tomas USB (panel y
placa) no se usan a la vez: se elige una con los 0 Ω, porque un ramal largo en D+/D−
y dos anfitriones en paralelo no son aceptables.

## PANEL_UI — botón y LEDs del panel (JST SH, 9 contactos)

| Pin | Señal | Dirección | En la placa |
| --- | --- | --- | --- |
| 1 | GND | — | Común del interruptor y del LED del botón |
| 2 | BTN_N | entrada | Contacto NA del botón a GND. Va a **QON** del BQ25792 (salir del modo ship) y a **GPIO10** (PUSH) a través de un diodo Schottky (ánodo en GPIO10), porque QON tiene pull-up interno de 200 kΩ y en reposo queda a 3.6–3.8 V, más de lo que admite el GPIO (`constraints.md` 3.3). Pulsación de 1 s: sale del modo ship; 2 s: el firmware apaga; 10 s: el BQ25792 reinicia la alimentación |
| 3 | BTN_LED_A | salida | Ánodo del anillo LED del botón, desde VSYS por resistencia/PTC |
| 4 | BTN_LED_K | salida | Cátodo del anillo LED, a un MOSFET N en el lado bajo (GPIO37) |
| 5 | LED_A | salida | Ánodo común del RGB y del LED de carga, a 3V3 |
| 6 | LED_R_K | salida | Cátodo rojo, resistencia en la placa, sumidero por GPIO7 |
| 7 | LED_G_K | salida | Cátodo verde, GPIO21 |
| 8 | LED_B_K | salida | Cátodo azul, GPIO36 |
| 9 | CHG_LED_K | salida | Cátodo del LED de carga al pin **STAT** (drenador abierto) del BQ25792, con resistencia; funciona sin firmware |

Notas:

- **RGB**: los barrenos del panel son de Ø3.2 → RGB de 3 mm de ánodo común (el
  Steren de 5 mm no entra). Con el ánodo a 3.3 V, el verde y el azul (Vf típica
  2.8–3.2 V a 20 mA) dan poca corriente: dimensionar las resistencias a 1–5 mA y
  comprobar a pleno sol. Alternativa: ánodo a VSYS y MOSFET N por color (entonces
  no se puede excitar el cátodo directo desde el GPIO).
- **Anillo del botón**: el comprado es de 12 V (C3). Con VSYS de 1S (3.5–4.2 V)
  encenderá poco o nada; comprar la variante de 3 V o 6 V del mismo botón. Con 2S
  (6–8.4 V) una variante de 6 V sirve.
- **LED de carga**: STAT es de drenador abierto; el LED se alimenta de 3V3, que está
  presente siempre que haya VSYS (con cargador conectado el BQ25792 sale del modo
  ship y el equipo arranca).
- Si se prefiere un mazo por pieza: botón y LEDs en conectores separados, pero con
  números de contactos distintos de 4, 5 y 6 (p. ej. 3 y 7) para no confundirlos
  con OLED, UM980_AUX y PANEL_USBD.

## OLED — pantalla SSD1306 I2C (JST SH, 4 contactos, Qwiic)

| Pin | Señal | Nota |
| --- | --- | --- |
| 1 | GND | Cable negro en Qwiic |
| 2 | 3V3_P | Riel de periféricos conmutado por GPIO45 (como en la Thing Plus). La OLED se alimenta a 3.3 V (`hardware/wiring.md:14`) |
| 3 | I2C_SDA | GPIO8. Pull-ups de 2.2–4.7 kΩ a 3V3 en la placa |
| 4 | I2C_SCL | GPIO9 |

El orden es el de Qwiic (SparkFun): el cable Qwiic a terminales sirve tal cual. En
el módulo OLED los cuatro cables van soldados a sus pines siguiendo los nombres
serigrafiados, no la posición (`mechanical/v2.2/README.md:197-199`). En el bus
también están el MAX17048 (0x36) y el BQ25792 (0x6B).

## UM980_AUX — puerto auxiliar del UM980 (JST SH, 5 contactos)

Para UPrecise con un adaptador USB-UART externo de **3.3 V** (no RS232, no 5 V).

| Pin | Señal | Dirección (vista desde el adaptador) | Nota |
| --- | --- | --- | --- |
| 1 | GND | — | |
| 2 | COM1_TXD | entrada al adaptador (RX) | Salida del UM980, por 100–470 Ω |
| 3 | COM1_RXD | salida del adaptador (TX) | Entrada del UM980, por 100–470 Ω |
| 4 | PPS | salida | Copia del PPS (el mismo que va a GPIO1), por 470 Ω |
| 5 | EVENT | entrada | Entrada de evento del UM980, por 470 Ω; pull-down en la placa |

COM1 queda **solo** para este puerto (el ESP32 usa COM2 y COM3). No hay
alimentación en el conector: el adaptador va con su propia USB. Con el UM980
apagado (GPIO14 alto), un adaptador conectado puede alimentarlo por sus pines de
E/S; las resistencias en serie limitan esa corriente, pero conviene desconectar el
adaptador o encender el UM980.

## BATTERY — batería (JST PH, 2 contactos)

| Pin | Señal | Nota |
| --- | --- | --- |
| 1 | BAT− | Convención SparkFun/Adafruit para LiPo con PH-2 |
| 2 | BAT+ | Al BQ25792 (BAT/SRN), MAX17048 (CELL/VDD) y protección |

- **La polaridad de los paquetes con PH-2 no es universal**: medir con multímetro
  antes de enchufar (`hardware/wiring.md:86`). Serigrafiar «+» y «−».
- Carga prevista ≤ 1.5 A (0.5 C en una 18650 de 3000 mAh). Ojo: el BQ25792 arranca con ICHG = 2 A (justo el límite del PH) hasta que el firmware lo baja (`constraints.md` 3.3).
- Sin NTC en la celda: el pin TS del BQ25792 se polariza con un divisor fijo o se
  ignora por registro; es un riesgo de seguridad documentado, no una solución. Si
  se compra una celda con NTC, añadir un SH de 2 contactos para ella.
- 2S = dos 18650 en serie con su BMS de balanceo; el conector sigue siendo de dos
  contactos.
- Ubicación: cara frontal, abajo, con la boca hacia abajo y a ≥ 10 mm del canto
  inferior; los cables bajan por los 5 mm libres entre el canto inferior y la base
  y suben por detrás hasta la celda (`constraints.md` 1.4).

## Coaxial de la antena (u.FL)

Receptáculo u.FL (IPEX MHF I) en el canto superior, dentro de x = ±15.5, con la
pista de 50 Ω más corta posible hasta ANT_IN del UM980 (sobre plano de masa
continuo; en 4 capas JLC04161H-7628 la microcinta de 50 Ω sale de unos
0.35–0.4 mm según una estimación propia: calcularla con la calculadora de JLC).
Latiguillo u.FL → SMA macho acodado de 60–100 mm hasta la antena. El u.FL está
pensado para pocas conexiones (decenas; ver el catálogo de Hirose): conectarlo solo
al montar. La LNA de la antena activa (HA-901A) se alimenta por el mismo coaxial:
Unicore recomienda un riel ANT_BIAS propio (no VCC_RF) con bobina de 68 nH,
desacoplo, condensador de bloqueo y protección ESD/TVS; SparkFun usa VCC_RF por
defecto (`constraints.md` 3.2). La tensión que admite la LNA de la HA-901A no está
documentada en el repositorio: comprobarla antes de fijar ANT_BIAS.

## USB-C de la placa (programación y carga)

USB-C de 16 contactos (USB 2.0) en el **canto inferior**, con 5.1 kΩ en CC1 y CC2,
protección ESD en D+/D− y VBUS a la segunda entrada del BQ25792. Se usa quitando la
base. Es el único USB de datos si el panel queda con JST-XH.

## microSD

Zócalo de expulsión por empuje con interruptor de detección, en el **canto inferior**
con la ranura hacia abajo. El firmware espera **HIGH con tarjeta** y usa
`INPUT_PULLDOWN` (`include/board_profile.h:17`; `src/sd_recorder.cpp:75-76`):

- Si el interruptor del zócalo es un contacto aislado (CD y su común), llevar el
  común a 3V3 por 1 kΩ y CD a GPIO48 con 100 kΩ a GND → HIGH con tarjeta, sin
  cambiar firmware.
- Si el interruptor cierra contra GND o la carcasa al meter la tarjeta, la lectura
  sale invertida: hace falta cambiar `sd_recorder.cpp` o un inversor.

En JLC no hay ningún zócalo microSD Basic ni Preferred. Los dos candidatos:

| Zócalo | Detección (de su hoja) | Cómo cablearlo |
| --- | --- | --- |
| SOFNG TF-015, C113206, 0.18 USD | Normalmente abierta; con tarjeta cierra CD contra la carcasa (GND) | CD con pull-up de 10 kΩ a 3V3 → LOW con tarjeta. Para no tocar el firmware: un MOSFET P (puerta en CD, fuente a 3V3, drenador a GPIO48 con 100 kΩ a GND) da HIGH con tarjeta. Si no, invertir la lectura en `sd_recorder.cpp` |
| Hirose DM3AT-SF-PEJM5, C114218, 1.16 USD | Normalmente abierta, entre sus propios terminales A y B (la ficha de LCSC dice «sin detección»: contradice la hoja; comprobar en el plano de Hirose antes de elegirlo) | A a 3V3 por 1 kΩ, B a GPIO48 con 100 kΩ a GND → HIGH con tarjeta, sin inversor |

Recomendación: TF-015 con el MOSFET P (más barato, sin cambiar firmware). La
retirada física de la tarjeta sigue sin ensayar (`hardware/wiring.md:36`).

## BOOT y RESET

Dos pulsadores SMD pequeños: BOOT entre GPIO0 y GND (con 10 kΩ de pull-up) y RESET
entre EN y GND (10 kΩ a 3V3 y 1 µF a GND en EN, según la guía de diseño de
Espressif). Van en la cara frontal dentro de la franja de la ventana (z ≥ 34) o en
el canto inferior. Con USB-Serial-JTAG el ESP32 entra en modo de carga sin botones;
se dejan para recuperación.
