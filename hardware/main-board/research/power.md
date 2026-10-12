# Alimentación de la placa principal (MeridianV) — investigación de diseño

Fecha de la investigación: 2026-10-04. Alcance: cargador BQ25792, protección de batería, *ship mode*, riel de 3.3 V, conmutación del UM980, medidor de batería y protección USB, con piezas de JLCPCB/LCSC. Lista de piezas en [`parts_power.csv`](parts_power.csv).

Convenciones:

- **[VERIFICADO]**: dato leído en el datasheet/documento del fabricante (o respuesta de un empleado de TI en E2E, indicado como tal). Se cita la fuente.
- **[INFERIDO]**: cálculo propio, decisión de diseño o comportamiento deducido. Debe confirmarse en banco.
- Stock y precio: API de piezas de JLCPCB, 2026-10-04, precio del tramo de 10–29 unidades (USD). El stock cambia a diario.

Nada de este documento se ha probado en hardware.

---

## 0. Resumen y diferencias con el plan

**Valores elegidos**

| Bloque | Elección |
| --- | --- |
| PROG | 1S: **4.7 kΩ 1 %** (750 kHz); 2S: **8.2 kΩ 1 %** (750 kHz) [VERIFICADO, tabla PROG] |
| Inductor del cargador | **2.2 µH**, Sunlord MWSA0603S-2R2MT (15 mΩ máx., Isat 8 A nominal / 10 A típ.) — TI exige 2.2 µH a 750 kHz [VERIFICADO] |
| ILIM_HIZ | REGN–**10 kΩ**–ILIM–**22 kΩ**–GND → ≈ 2.9 A (2.7–3.05 A según REGN) [INFERIDO, fórmula VERIFICADA] |
| TS sin NTC | REGN–**5.1 kΩ**–TS–**30 kΩ**–GND y **10 kΩ** fijo TS–GND → 59.5 % de REGN ≈ 25 °C [INFERIDO] |
| TS con NTC | mismas resistencias; NTC 10 kΩ B25/85 ≈ 3435 K en lugar del 10 kΩ fijo → corte en frío ≈ 1 °C, corte en caliente ≈ 61 °C [INFERIDO] |
| Ship FET (nuevo) | **AO3400A** (N, S→BAT, D→PACK+, G→SDRV), obligatorio para *ship mode* y reset por QON |
| Inversión de batería | **AO3401A** (P, en el positivo) + **AO3400A** que maneja su compuerta referido a la celda |
| Buck 3.3 V | **TPS62903RPJR** (3–17 V, 3 A, modo 100 %, EN preciso), 1 µH, FB 100 k/22 k = 3.33 V |
| Riel UM980 | **TPS22919DCKR** (rampa ≈ 1.1 ms, descarga rápida de salida, OFF por defecto) |
| Medidor | MAX17048G+T10 (1S); MAX17049G+T10 (2S) en la misma huella, con VDD desde un LDO HT7533-1 |
| USB | USBLC6-2SC6 en D+/D− (pin 5 a +3V3), TVS SMF20A en VBUS, 5.1 kΩ en CC1/CC2 |

**Lo que contradice o cambia el plan**

1. **El *ship mode* del BQ25792 no apaga el BATFET interno. Hace falta un MOSFET de envío externo en SDRV.** La revisión D del datasheet (SLUSDG1D, abril 2026) borró las frases de la revisión C según las cuales el BATFET se apagaba en *ship/shutdown*. El aviso de cambio de TI (PCN 20260506000.0) dice que el cambio fue «para reflejar con exactitud las características del dispositivo». Un empleado de TI lo confirma en E2E: «An external ship FET is required for ship mode or shutdown mode. The internal battery FET cannot be turned off.» [VERIFICADO: [rev D](https://mm.digikey.com/Volume0/opasdata/d220001/medias/docus/8929/BQ25792RQMR.pdf) §8.3.12 y revisión de cambios; [PCN](https://mm.digikey.com/Volume0/opasdata/d220001/medias/docus/8962/PCN20260506000.0.pdf); [E2E 981616](https://e2e.ti.com/support/power-management-group/power-management/f/power-management-forum/981616/bq25792-do-we-need-a-ship-fet)]. Sin ese FET, ni el apagado ni el reset largo por QON cortan la batería. Además el diodo intrínseco del BATFET siempre conecta BAT con SYS ([E2E 1225212](https://e2e.ti.com/support/power-management-group/power-management/f/power-management-forum/1225212/bq25792-battery-depletion-threshold)). El firmware debe escribir **SFET_PRESENT = 1** (REG0x14 bit 7). Con el valor POR (0), SDRV_CTRL queda bloqueado en 00 [VERIFICADO, tabla REG14]. Según TI, eso también afecta al reset por QON ([E2E 1053051](https://e2e.ti.com/support/power-management-group/power-management/f/power-management-forum/1053051/bq25792-reset-ship-mode-issues)).
2. **Corriente de carga por defecto = 2 A** en 1S y 2S (BQ25792), no 1 A. Cuando vence el *watchdog* (40 s por defecto), ICHG vuelve a 2 A [VERIFICADO, tablas 8-2/8-9, ICHG marcado «Reset by WATCHDOG» en REG03 y guía del EVM; la tabla 8-10 dice 1 A, una incoherencia del propio datasheet]. Hay dos caminos. Uno: el firmware escribe ICHG = 1 A en cada arranque y desactiva o atiende el *watchdog*. El otro: el **BQ25798RQMR**, compatible pin a pin con la misma tabla PROG, cuyo valor POR es **1 A en todas las configuraciones** [VERIFICADO, [BQ25798 ZHCSNY0C rev. C](https://www.ti.com/cn/lit/gpn/bq25798), tabla 7-2]. Cuesta USD 0.79 más por placa.
3. **En 1S, el *ship mode* necesita batería ≥ ≈ 3.4 V.** Mientras el chip está en *ship mode*, el umbral de batería para mantener activo el I2C es 3.25–3.55 V (subida) / 3.05–3.31 V (bajada) [VERIFICADO, VBAT_UVLOZ/VBAT_UVLO]. TI advierte que «for a 1S battery, the thresholds are a bit high» (E2E 1053051). Ver §2.6 y §10.
4. **TPS62133 es de 5.0 V fijo, no de 3.3 V.** La versión de 3.3 V fija es la TPS62132, con stock de 65 [VERIFICADO, [SLVSAG7E](https://wmsc.lcsc.com/wmsc/upload/file/pdf/v2/lcsc/1912111437_Texas-Instruments-TPS62130ARGTR_C337502.pdf) tabla 5]. Se elige TPS62903 (§4).
5. El datasheet del BQ25792 es **SLUSDG1** (rev D, abril 2026), no SLUSE09. La copia pública de la rev D está en DigiKey y lleva el encabezado «TI Confidential – NDA Restrictions». El PCN dice que la rev D no estaba en la web de TI. Se contrastó con la rev C pública ([Mikroe](https://download.mikroe.com/documents/datasheets/BQ25792_datasheet.pdf)).
6. **El P-MOSFET con compuerta a GND no basta si alguien carga con la celda invertida.** Con USB conectado, el cargador eleva el nodo de batería, el P-FET entra en conducción y alimenta la celda invertida. Se añade un segundo FET que solo enciende el P-FET si el borne del portapilas es positivo (§3).
7. **MAX17049 no se alimenta del pack.** Su VDD va a una fuente regulada de 2.5–4.5 V y CELL mide el pack 2S [VERIFICADO]. La huella es la misma, pero la alimentación de VDD cambia por variante. En JLCPCB solo hay 50 unidades, a USD 9.60.
8. **USBLC6-2SC6:** su pin «VBUS» rompe a 6 V. Como el VBUS del equipo puede llegar a 20 V, ese pin va a +3V3, no a VBUS (§7).
9. **D+/D− en paralelo con el ESP32:** TI lo acepta si el microcontrolador no usa las líneas durante los primeros 2 s tras conectar ([E2E 1191864](https://e2e.ti.com/support/power-management-group/power-management/f/power-management-forum/1191864/bq25792-usb-c-charging-and-device-communication)). El ESP32-S3 activa el pull-up de D+ desde el reset ([ESP32-S3 datasheet v2.2](https://documentation.espressif.com/esp32-s3_datasheet_en.pdf), «USB_PU» en GPIO20), así que hace falta manejarlo por firmware (§2.4).

---

## 1. Diagrama de bloques

```
USB-C de panel ──cable (VBUS, GND, D+, D−, CC1, CC2)──► J_USB placa principal
   CC1, CC2 ── 5.1 kΩ ── GND   (sink sin PD)
   VBUS ──┬── D1 SMF20A ── GND
          └──► U1 BQ25792: VBUS(2,3) = VAC1(9) = VAC2(8); ACDRV1/2 = GND
   D+/D− ── U6 USBLC6-2SC6 (pin5 a +3V3) ──┬──► ESP32-S3 GPIO20/GPIO19 (USB nativo)
                                           └──► U1 D+(6)/D−(7)  (derivación en T corta)

U1 BQ25792 (buck-boost NVDC, 750 kHz)
   PMID(29) 3×10 µF+0.1 µF │ SW1(28)──L1 2.2 µH──SW2(26) │ BTST1/2 47 nF │ REGN(5) 4.7 µF
   SYS(25) ─────────────────────────► VSYS (1S: ≈3.0–4.8 V; 2S: ≈6–9.5 V)
   │                                    ├─► U2 TPS62903 ─► +3V3 (ESP32, microSD, OLED, IMU, LED)
   │                                    │                    └─► U3 TPS22919 ─FB1─► +3V3_GNSS (UM980, antena)
   BAT(22,23) ──[Q3 AO3400A ship FET: S=BAT, D=PACK+, G=SDRV(24)]── PACK+
   BATP(18) ──100 Ω──────────────────────────────────────────────── PACK+
PACK+ ──[Q1 AO3401A: S=PACK+, D=BATT_IN, G=Q2.D y 1 MΩ a PACK+]── BATT_IN (+ del portapilas)
   Q2 AO3400A: G ← 100 kΩ ← BATT_IN, 1 MΩ G–GND; S = GND; D = G de Q1
   U4 MAX17048: VDD = CELL = PACK+, 0.1 µF; CTG = QSTRT = GND; ALRT → GPIO; I2C 0x36
− del portapilas = GND

Pulsador del panel ── QON(12) ── GND ; QON ──|◄── GPIO_BTN (1N4148W: ánodo en GPIO, pull-up 47 kΩ a +3V3)
INT(21) → GPIO (10 kΩ a +3V3) ; STAT(1) → LED → 1 kΩ → REGN ; CE(13) → GND ; I2C 0x6B
```

---

## 2. Cargador TI BQ25792

### 2.1 Documento

- Fuente principal: [SLUSDG1D, junio 2020, revisado abril 2026](https://mm.digikey.com/Volume0/opasdata/d220001/medias/docus/8929/BQ25792RQMR.pdf). Contraste: [SLUSDG1C, agosto 2022](https://download.mikroe.com/documents/datasheets/BQ25792_datasheet.pdf) y la guía del EVM [SLUUCB5E](https://www.ti.com/lit/ug/sluucb5e/sluucb5e.pdf).
- Encapsulado RQM0029A, VQFN-HR (HotRod) de 4 × 4 mm y 1 mm de alto, **sin pad térmico expuesto**. La huella debe seguir el patrón de TI (§13 del datasheet), no la de un QFN genérico [VERIFICADO].
- LCSC C2862876 ([JLCPCB](https://jlcpcb.com/partdetail/TexasInstruments-BQ25792RQMR/C2862876)): Extended, 3164 en stock, USD 1.72.

### 2.2 Conexión pin a pin (diseño de entrada única, sin ACFET)

| Pin | Nombre | Conexión en este diseño | Notas |
| ---: | --- | --- | --- |
| 1 | STAT | Cátodo del LED; ánodo a REGN por 1 kΩ | Drenador abierto, sumidero máx. absoluto 6 mA; VOL ≤ 0.4 V a 5 mA [VERIFICADO]. 1 kΩ desde REGN ≈ 4.8 V da ≈ 2.8 mA [INFERIDO]. Bajo = cargando, alto = terminado/deshabilitado, parpadeo a 1 Hz = falla [VERIFICADO]. |
| 2, 3 | VBUS | VBUS del USB: 2 × 10 µF/25 V + 0.1 µF/50 V junto al pin, más la TVS | Valores de TI [VERIFICADO]. |
| 4 | BTST1 | 47 nF (≥10 V) a SW1 | [VERIFICADO] |
| 5 | REGN | 4.7 µF (≥10 V) a GND; alimenta solo los divisores TS e ILIM y el LED STAT | TI no recomienda otras cargas en REGN. REGN = 4.6–5.0 V con VBUS = 5 V; límite de 30 mA [VERIFICADO]. En modo solo batería está apagado. |
| 6 | D+ | D+ del USB, en paralelo con el ESP32 (ver §2.4) | Opcional: 0 Ω en serie para poder aislarlo. |
| 7 | D− | D− del USB, ídem | |
| 8 | VAC2 | **A VBUS** | «Connect to VBUS if the ACFET2 and RBFET2 are not installed» [VERIFICADO] |
| 9 | VAC1 | **A VBUS** | ídem |
| 10 | ACDRV2 | **A GND** | «Tie ACDRV2 to GND if no ACFET2 and RBFET2 installed» [VERIFICADO] |
| 11 | ACDRV1 | **A GND** | ídem |
| 12 | QON | Pulsador a GND, más el diodo hacia el GPIO (§2.4) | Pull-up interno RQON = 200 kΩ a VQON ≈ 3.2 V típ. (3.6–3.8 V con VBUS y VBAT > 5 V). VIL ≤ 0.4 V, VIH ≥ 1.3 V [VERIFICADO]. Opcional: 10 nF a GND contra ruido del cable [INFERIDO]. |
| 13 | CE | **A GND** (carga habilitada; el firmware usa EN_CHG) | «must be pulled HIGH or LOW, do not leave floating» [VERIFICADO] |
| 14 | SCL | Bus I2C de 3.3 V (pull-ups compartidos, p. ej. 4.7 kΩ) | Dirección **0x6B** [VERIFICADO]. Usar ≤ 400 kHz: el texto cita los modos estándar y rápido; la tabla de tiempos llega a 1 MHz. |
| 15 | SDA | ídem | |
| 16 | TS | Red REGN–5.1 kΩ–TS–30 kΩ–GND más 10 kΩ fijo o NTC a GND | §2.4 |
| 17 | ILIM_HIZ | Divisor REGN–10 kΩ–ILIM–22 kΩ–GND | §2.4. Por debajo de 0.75 V deja de conmutar. **No alimentarlo desde +3V3**: se lee antes de que exista SYS. |
| 18 | BATP | **PACK+ por 100 Ω**, después de Q1 y antes de Q3 | «Place 100Ω series resistance» [VERIFICADO]. En *ship mode* el chip se alimenta por BATP (TI en E2E 919857/1307985). Pista Kelvin, lejos de SW1/SW2. |
| 19 | BTST2 | 47 nF (≥10 V) a SW2 | [VERIFICADO] |
| 20 | PROG | 4.7 kΩ 1 % (1S) / 8.2 kΩ 1 % (2S) a GND | 750 kHz. §2.4 |
| 21 | INT | GPIO del ESP32 con pull-up de 10 kΩ a **+3V3** (no a REGN) | Pulso bajo de 256 µs [VERIFICADO]. |
| 22, 23 | BAT | **Fuente de Q3** (ship FET) y 2 × 10 µF/25 V | [VERIFICADO: 2 × 10 µF] |
| 24 | SDRV | **Compuerta de Q3**, pista corta y **sin resistencia a GND** | Bomba de carga de 100 nA, ≈ 5 V sobre BAT [VERIFICADO]. TI: SDRV no admite cargas DC de 50 MΩ o menos (E2E 1053051). Solo si Q3 no se monta: 1 nF/50 V/0402 a GND [VERIFICADO, rev D]. La rev D eliminó la opción «SDRV a BAT». |
| 25 | SYS | Riel VSYS: 5 × 10 µF/25 V + 0.1 µF (el 0.1 µF lo más cerca) | [VERIFICADO] |
| 26 | SW2 | Inductor | |
| 27 | GND | Plano de tierra | |
| 28 | SW1 | Inductor | |
| 29 | PMID | 3 × 10 µF/25 V + 0.1 µF/50 V; sin cargas externas | [VERIFICADO]. Sin OTG. |

Capacidad efectiva mínima recomendada: VBUS 2 µF, PMID 4 µF, SYS 6 µF, BAT 3 µF [VERIFICADO]. Usar 10 µF/25 V/0805 X5R (C15850) en todos: cubre VBUS hasta 20 V (por encima actúa la TVS) y SYS en 2S.

### 2.3 Componentes del cargador

| Ref. | Valor | Pieza | Comentario |
| --- | --- | --- | --- |
| L1 | 2.2 µH, ≤ 15 mΩ, Isat 8 A nominal / 10 A típ. | Sunlord MWSA0603S-2R2MT (C408445), 7 × 6.6 mm | TI: 750 kHz «only works with the 2.2 µH inductor» [VERIFICADO]. Isat por encima de max(IIN, ICHG) más medio rizado [VERIFICADO], y además por encima del límite ciclo a ciclo de Q1/Q4 (7.5 A) [INFERIDO]. Alternativas: TDK SPM6530T-2R2M (C76855); más compacta, MWSA0503S-2R2MT (5.4 × 5.2 mm, 29 mΩ, Isat 5.6 A). |
| C VBUS | 2 × 10 µF/25 V + 100 nF/50 V | C15850 + C307331 | |
| C PMID | 3 × 10 µF/25 V + 100 nF/50 V | ídem | |
| C SYS | 5 × 10 µF/25 V + 100 nF/50 V | ídem | |
| C BAT | 2 × 10 µF/25 V | C15850 | |
| C REGN | 4.7 µF/16 V 0603 | C19666 | TI pide ≥ 10 V. |
| C BTST1/2 | 47 nF/50 V 0603 | C1622 | Basic no hay en 0402. |
| R PROG | 4.7 kΩ (1S) / 8.2 kΩ (2S), 1 % | C25900 / C25924 | |
| R ILIM | 10 kΩ / 22 kΩ | C25744 / C25768 | |
| R TS | 5.1 kΩ / 30 kΩ / 10 kΩ | C25905 / C22984 (0603) / C25744 | |
| R BATP | 100 Ω | C25076 | |
| LED STAT | LED rojo 0603 + 1 kΩ | C2286 + C11702 | |

### 2.4 Detalle de los pines configurables

**PROG** [VERIFICADO, tabla 8-1; se aceptan resistencias de ±1 % o ±2 %]

| Frecuencia | 1S | 2S | 3S | 4S |
| --- | --- | --- | --- | --- |
| 1.5 MHz (1 µH) | 3.0 kΩ | 6.04 kΩ | 10.5 kΩ | 17.4 kΩ |
| 750 kHz (2.2 µH) | **4.7 kΩ** | **8.2 kΩ** | 13.7 kΩ | 27.0 kΩ |

Se elige 750 kHz por tres razones. TI la indica para mayor eficiencia [VERIFICADO §9.2.2.1], y la eficiencia importa en una carcasa cerrada al sol. Y 4.7 k y 8.2 k son Basic o Preferred, mientras que 6.04 k no lo es [INFERIDO].

**ILIM_HIZ.** VILIM_HIZ = 1 V + 0.8 Ω × ILIM. Fija el techo del registro IINDPM; con el pin por debajo de 0.75 V el convertidor no conmuta y REGN sigue activo [VERIFICADO]. Con 10 k/22 k desde REGN = 4.6/4.8/5.0 V se obtiene 3.16/3.30/3.44 V, es decir ILIM ≈ 2.70/2.88/3.05 A [INFERIDO]. Se mide en el arranque, antes de conmutar [VERIFICADO]. El firmware puede superar este techo con EN_EXTILIM = 0, cosa que no se recomienda. Con 5 V de entrada, 2.9 A basta para cargar 2S a 1 A con el sistema encendido (≈ 2.3 A de entrada) [INFERIDO]. **v0.3 (1S por defecto):** 10 k/8.2 k, ILIM ≈ 1.34/1.45/1.56 A; los 22 k quedan para la variante 2S (ver el README).

**TS.**
- Sin NTC: REGN–5.1 kΩ–TS, 30 kΩ y 10 kΩ en paralelo a GND. TS = 59.5 % de REGN, dentro de la ventana normal: más bajo que T2 = 68.4 % (10 °C) y más alto que T3 = 44.8 % (45 °C), umbrales [VERIFICADOS] en REG18. Carga a corriente completa. **No protege la celda por temperatura.**
- Con NTC real: la NTC de 10 kΩ, 103AT-2 o Murata NCP15XH103F03RC (B25/85 = 3434 K), sustituye al 10 kΩ fijo. Con las tablas del 103AT y los porcentajes del datasheet salen T1 (frío, suspende) ≈ 1.0 °C, T2 (fresco, 20 % ICHG) ≈ 10.7 °C, T3 (templado, VREG − 400 mV) ≈ 45.7 °C y T5 (caliente, suspende) ≈ 61.3 °C [INFERIDO]. Con los valores de TI (5.24 k/30.31 k) da 0 °C y 60 °C, lo que confirma el método.
- Si la NTC se abre, TS = 85.5 % y la carga se suspende por frío. Es un fallo seguro.
- **Recomendado:** montar la NTC en contacto térmico con la celda (cable de 2 hilos o NTC SMD bajo el portapilas). El receptor va al sol, y las resistencias fijas dejan la celda sin protección térmica [INFERIDO]. TI asume en E2E 989217 que hay batería con termistor. Sin batería y con la red fija, el cargador puede oscilar BATOVP/SYSOVP; el firmware debe poner EN_CHG = 0 si no detecta celda [VERIFICADO, datasheet §8.3.6 y §10].

**STAT.** LED desde REGN, que solo existe con VBUS. El LED se apaga sin USB y no consume batería [INFERIDO].

**QON y botón.**
- Pulsador entre QON y GND.
- Lectura del ESP32: GPIO con pull-up de 47 kΩ a +3V3 (o pull-up interno) y 1N4148W con el ánodo en el GPIO y el cátodo en QON. Pulsado, el GPIO queda en ≈ 0.5 V (bajo). Suelto o con el ESP32 apagado, el diodo queda en inversa y no carga QON [INFERIDO].
- Diodo de silicio y no Schottky: QON tiene 200 kΩ de pull-up, y la fuga en inversa de un Schottky caliente podría bajar QON por debajo de VIH = 1.3 V y despertar el equipo [INFERIDO].
- No conectar QON directamente a un GPIO. Con el ESP32 sin alimentación, el GPIO tira QON a bajo y el equipo sale del *ship mode* (caso real en [E2E 1381996](https://e2e.ti.com/support/power-management-group/power-management/f/power-management-forum/1381996/bq25792-does-not-enter-into-ship-mode)). Además VQON puede llegar a 3.8 V.

**D+/D− (BC1.2).**
- AUTO_INDET_EN vale 1 por defecto y se restablece con *watchdog* y REG_RST. La detección corre solo en VAC1, después de calificar la fuente y antes de que el convertidor conmute [VERIFICADO §8.3.4].
- Resultado → IINDPM: SDP 500 mA, CDP 1.5 A, DCP 3.25 A, HVDCP 1.5 A, adaptador desconocido 3 A, no estándar 1/2/2.1/2.4 A [VERIFICADO, tabla 8-4]. Siempre recortado por ILIM_HIZ.
- Con D+/D− al aire el resultado es «Unknown adapter»: 3 A, recortado por ILIM a ≈ 2.9 A (≈ 1.45 A en la v0.3 1S) (TI en [E2E 989217](https://e2e.ti.com/support/power-management-group/power-management/f/power-management-forum/989217/bq25790-unknown-adapter) y [E2E 1307985](https://e2e.ti.com/support/power-management-group/power-management/f/power-management-forum/1307985/bq25792-some-technical-question)). Un cargador USB-C sin BC1.2 tiene las líneas de datos abiertas y lo más probable es que caiga en ese caso [INFERIDO].
- No conectar D+/D− a GND: el datasheet no documenta ese caso.
- **Recomendación:** D+/D− del BQ25792 en paralelo con las líneas USB del ESP32, con derivación en T corta después del USBLC6, y con HVDCP_EN = 0, que es el valor por defecto; no pedir 9/12 V. Tras la detección, los pines del cargador pasan a alta impedancia. TI acepta compartir las líneas si el microcontrolador no se comunica en los primeros 2 s (E2E 1191864). El ESP32-S3 activa por hardware el pull-up de D+ desde el reset, y al salir de *ship mode* arranca desde la batería mientras corre la detección [INFERIDO]. Por eso:
  - El firmware, si ve VBUS al arrancar, puede desactivar temporalmente el pull-up USB (override del pad USB Serial/JTAG), forzar FORCE_INDET = 1, esperar BC1.2_DONE_STAT (≤ 2 s) y reactivarlo [INFERIDO; verificar en ESP-IDF].
  - Después fija IINDPM al mínimo entre el resultado BC1.2, el nivel Rp de USB-C si se mide (§7) y el techo de ILIM.
  - Sin esto, el peor caso es un puerto de PC visto como «desconocido 3 A». VINDPM, que por defecto es la tensión de VBUS en vacío − 0.7 V cuando esta es menor de 7 V [VERIFICADO §8.3.4.4], limita el daño, pero un puerto de 500 mA puede cortarse.
- Prever 2 × 0 Ω (0402) en serie con D+/D− del cargador. Sin montarlos queda en «unknown adapter».

### 2.5 Valores POR que importan en modo autónomo

| Parámetro | Valor POR | Lo restablece el *watchdog* | Fuente |
| --- | --- | --- | --- |
| ICHG | **2 A** (1S y 2S); 1 A (3S/4S) | sí | Tablas 8-2/8-9, REG03, EVM SLUUCB5E [VERIFICADO] |
| VREG | 4.2 V (1S) / 8.4 V (2S) | no (solo REG_RST) | REG01 [VERIFICADO] |
| VSYSMIN | 3.5 V (1S) / 7 V (2S); SYS regulado ≈ 200 mV por encima (3.5–4.1 V; 7.12–7.52 V) | no | REG00, tabla EC [VERIFICADO] |
| IINDPM | 3 A, luego lo que diga D+/D− | no | REG06 [VERIFICADO] |
| VINDPM | VBUS en vacío − 0.7 V (VBUS < 7 V) | no | §8.3.4.4 [VERIFICADO] |
| IPRECHG / ITERM | 120 mA / 200 mA | sí | REG08/REG09 [VERIFICADO] |
| Carga lenta (*trickle*) | 100 mA fijo por debajo de VBAT_SHORT ≈ 2.2 V | — | [VERIFICADO] |
| Recarga | VREG − 200 mV | sí | REG0A [VERIFICADO] |
| Temporizadores | lenta 1 h, precarga 2 h, carga rápida 12 h, ×2 en DPM/TREG | sí | REG0E [VERIFICADO] |
| *Watchdog* | 40 s; al vencer, los registros marcados vuelven a defecto | — | REG10, §8.4.1 [VERIFICADO] |
| Terminación | habilitada | sí | REG0F [VERIFICADO] |
| TREG / TSHUT | 120 °C / 150 °C | sí | REG16 [VERIFICADO] |
| JEITA | 0–10 °C: 20 % ICHG; 45–60 °C: VREG − 400 mV | sí | REG17/18 [VERIFICADO] |
| ADC | apagado (ADC_EN = 0). Con ADC encendido, el consumo solo batería sube a 540 µA | sí | REG2E, tabla EC [VERIFICADO] |
| Frecuencia | según PROG | — | REG13 [VERIFICADO] |
| SFET_PRESENT | **0**: *ship mode* y reset bloqueados | sin nota de reset en la tabla | REG14 [VERIFICADO] |

Consecuencia [INFERIDO]: si el firmware atiende el *watchdog* y luego se cuelga, a los 40 s el cargador vuelve a 2 A. Recomendación: escribir ICHG = 1 A y **desactivar el watchdog** (WATCHDOG = 000) en cada arranque. También se puede usar el BQ25798, con 1 A por defecto.

### 2.6 *Ship mode*, *shutdown*, reset y botón — comportamiento para el firmware

Registros [VERIFICADO]:

- REG0x11: bits [2:1] SDRV_CTRL (00 normal, 01 *shutdown*, 10 *ship*, 11 reset de sistema), bit 0 SDRV_DLY (0 = espera 10 s, valor por defecto; 1 = inmediato), bit 6 AUTO_INDET_EN.
- REG0x12 bit 3 WKUP_DLY: tiempo de QON para salir de *ship*. 0 = 1 s, por defecto; 1 = 15 ms.
- REG0x14 bit 7 SFET_PRESENT.

| Estado | Cómo se entra | Qué pasa | Cómo se sale |
| --- | --- | --- | --- |
| **Apagado (*ship*)** | FW: SFET_PRESENT = 1 y SDRV_CTRL = 10, solo **sin VBUS** (con adaptador la escritura se ignora) | Q3 abierto: VSYS = 0 y todo apagado. El BQ25792 sigue alimentado por BATP con I2C activo y reloj lento | QON en bajo ≥ tSM_EXIT (1 s típ. o 15 ms), conectar USB, SDRV_CTRL = 00 o REG_RST. Al salir, Q3 conduce y SDRV_CTRL vuelve a 00 |
| Encendido con batería | salida de *ship*, o inserción de batería (POR: Q3 se enciende solo) | BATFET encendido, el sistema arranca | — |
| Encendido con USB | VBUS presente | NVDC: SYS ≥ VSYSMIN; carga y sistema simultáneos; modo suplemento si la fuente no alcanza | — |
| **Reset por hardware** | QON en bajo ≥ tRST (10 s típ.), o SDRV_CTRL = 11 | Q3 abierto tRST_SFET = 350 ms típ. (HIZ si hay VBUS) con descarga de SYS a 30 mA; luego Q3 se cierra y el equipo rearranca | automático |
| *Shutdown* (opcional, «almacenamiento») | SDRV_CTRL = 01 sin VBUS | Q3 abierto, I2C apagado, 0.5 µA | **solo** conectar USB; QON no despierta |

Notas [VERIFICADO salvo indicación]:
- SDRV_CTRL se ignora si hay VBUS: queda en 00.
- TI: «For ship mode to function, VBUS voltage must be below UVLO» (E2E 1053051).
- Por defecto se añaden **10 s de espera** antes de abrir Q3 (SDRV_DLY = 0).
- tSM_EXIT, tRST y tRST_SFET solo tienen valores típicos en el texto.

Procedimiento de apagado recomendado [INFERIDO]:
1. Cerrar la microSD, apagar el UM980 y desactivar el ADC (REG0x2E bit 7 = 0).
2. Comprobar VBUS_PRESENT_STAT = 0 (REG0x1B bit 0).
3. **Esperar a que se suelte el botón.** Si QON sigue en bajo, el equipo vuelve a despertar al cabo de tSM_EXIT.
4. Comprobar SFET_PRESENT = 1.
5. Escribir REG0x11 por lectura-modificación-escritura: SDRV_CTRL = 10 y SDRV_DLY = 1 para corte inmediato. Con el resto de bits por defecto queda 0x45, el mismo valor que usó un cliente en E2E 1004118. Con SDRV_DLY = 0 el corte llega a los 10 s.
6. Si se quita el USB estando en «solo carga»: mismo procedimiento.

Arranque y causa del despertar [INFERIDO]:
- **Configuración inicial (siempre):** SFET_PRESENT = 1 (REG0x14 = 0x96 si el resto está por defecto), ICHG = 1 A (REG0x03 = 0x0064), *watchdog* desactivado e IINDPM según la fuente.
- **Botón en bajo al arrancar:** despertar por el usuario. Arrancar completo y esperar a que se suelte el botón.
- **VBUS_PRESENT_STAT = 1 sin botón:** modo «solo carga». UM980 apagado y OLED con el estado de carga.
- **Ni botón ni VBUS:** puede ser una batería recién insertada o un reset por QON. Una forma de distinguirlos es leer SFET_PRESENT antes de escribirlo:
  - Si vale 0, el BQ25792 pasó por POR (batería insertada). Política sugerida: volver a *ship mode*.
  - Si vale 1, el cargador ya estaba configurado. Se trata de un reset por QON o similar: arrancar normal.
  - No hay bandera de causa documentada. Verificar en banco.
- Pulsación del usuario para apagar: 2–3 s, muy por debajo de los 10 s del reset por hardware.

**Límite en 1S [VERIFICADO + INFERIDO]:**
- Mientras el chip está en *ship mode*, VBAT_UVLOZ es 3.25–3.40–3.55 V (subida) y VBAT_UVLO 3.05–3.20–3.31 V (bajada). En modo normal son 2.50–2.71 V y 2.30–2.50 V. TI: «For a 1S battery, the thresholds are a bit high».
- Si la celda baja de ≈ 3.2 V en *ship mode*, el BQ25792 deja de responder. El comportamiento de Q3 y del POR siguiente no está documentado. Un POR «normal» con la celda a ≈ 3.1 V volvería a cerrar Q3 y encendería el sistema [INFERIDO].
- Recomendaciones:
  - Apagado por batería baja en 1S a **≥ 3.5 V en reposo** (≈ 3.45 V con carga ligera).
  - El divisor EN del buck (§4) impide arrancar por debajo de ≈ 3.44 V.
  - Usar celdas con PCM, porque el BQ25792 no protege contra sobredescarga. Solo corta en VBAT_SHORT ≈ 2.2 V del pack y TI espera que lo haga el protector del pack ([E2E 1225212](https://e2e.ti.com/support/power-management-group/power-management/f/power-management-forum/1225212/bq25792-battery-depletion-threshold)).
  - Verificar en banco el comportamiento de *ship mode* entre 3.6 V y 3.0 V.

### 2.7 Consumo en reposo

[VERIFICADO, tabla EC, medida a VBAT = 8 V y TJ < 85 °C]:

| Estado | Típico | Máximo | Medido en |
| --- | --- | --- | --- |
| Solo batería, BATFET encendido, ADC apagado | 17 µA | 24 µA | BATP, BAT y SYS |
| *Ship mode* | 11 µA | 16 µA | BATP |
| *Shutdown* | 0.5 µA | 0.7 µA | BATP |
| Solo batería con ADC encendido | 540 µA | — | BATP, BAT y SYS |

Presupuesto del equipo «apagado» en 1S [INFERIDO]:

| Consumidor | Corriente |
| --- | --- |
| BQ25792 en *ship* | ≈ 11 µA |
| MAX17048 en *hibernate* | ≈ 3–4 µA |
| Polarización de Q1/Q2 (3.7 V / 1 MΩ + 3.7 V / 1.1 MΩ) | ≈ 7 µA |
| Fugas de MOSFET | < 1 µA |
| **Total** | **≈ 22 µA**: 3000 mAh durarían más de 10 años; en la práctica manda la autodescarga de la celda |

En 2S, cuenta con ≈ 30 µA.

### 2.8 Estimación térmica (5 V de entrada, ICHG = 1 A, 750 kHz)

[INFERIDO] Pérdidas por conducción calculadas con las RDS(on) del datasheet (RSNS 6, Q1 24, Q2 35, Q3 28, Q4 17, BATFET 8 mΩ; L1 15 mΩ), más una estimación de conmutación. RθJA del datasheet: 44.2 °C/W, que corresponde a una placa tipo JEDEC/EVM; en una carcasa cerrada será peor.

| Caso | Potencia de salida | Entrada a 5 V | Pérdida en el IC | ΔTj |
| --- | --- | --- | --- | --- |
| 1S (VBAT 3.8 V), modo reductor, sistema 0.5 W | ≈ 4.3 W | ≈ 0.9 A | ≈ 0.2–0.25 W | **≈ +9–11 °C** |
| 1S con sistema completo (UM980 + Wi-Fi ≈ 2.5 W) | ≈ 6.3 W | ≈ 1.4 A | ≈ 0.35 W | ≈ +15 °C |
| 2S (VBAT 8 V), modo elevador, sistema 0.5 W | ≈ 8.5 W | ≈ 1.85 A | ≈ 0.45–0.6 W | **≈ +20–27 °C** |
| 2S con sistema completo | ≈ 10.5 W | ≈ 2.3 A | ≈ 0.6–0.8 W | ≈ +27–35 °C |

Otras pérdidas a 1 A: Q1 (AO3401A, ≈ 60 mΩ) ≈ 0.06 W; Q3 (AO3400A, ≈ 25 mΩ) ≈ 0.03 W. La regulación térmica baja ICHG si TJ > 120 °C [VERIFICADO]. En 2S hace falta una fuente de 3 A o DCP; con una fuente menor, IINDPM/VINDPM reducen la carga automáticamente.

### 2.9 Reglas de layout

[VERIFICADO §11, en orden de prioridad de TI; las notas al final de cada punto son INFERIDO]

1. Condensadores de SYS lo más cerca posible de SYS/GND, con el 0.1 µF (0402) más cerca que los de 10 µF.
2. Ídem PMID.
3. Ídem VBUS.
4. Lazo VBUS/PMID/SYS → 0.1 µF → GND en la capa superior, lo más pequeño posible.
5. Inductor pegado a SW1/SW2, con el mínimo cobre en esos nodos. TI lleva SW1/SW2 por vías bajo el IC hasta una capa interna para dejar sitio a los 0.1 µF arriba.
6. Condensadores de BAT y VBUS junto a sus pines.
7. REGN y BTST junto al IC, con pistas mínimas.
8. Vías térmicas bajo los MOSFET de potencia; usar 4 capas (el EVM BMS034 lo es).
9. Vías suficientes para la corriente.
10. BATP lejos de SW1/SW2: **Kelvin a PACK+**.
11. Pista de SDRV corta y limpia, sin residuos de flux. Con 100 nA de excitación, una fuga del orden de µA impide encender Q3.
12. Cargador y buck lejos del BMI088, porque el calor produce deriva térmica en la IMU, y lejos del UM980 y de la antena.

---

## 3. Batería: inversión de polaridad, ship FET, BATP y medidor

Circuito recomendado [INFERIDO; datos de los MOSFET VERIFICADOS en los datasheets AOS [AO3401A](https://www.aosmd.com/res/datasheets/AO3401A.pdf) rev 3.1 y [AO3400A](https://www.aosmd.com/res/datasheets/AO3400A.pdf) rev 3.1]:

```
+portapilas (BATT_IN) ──D─[Q1 AO3401A]─S── PACK+ ──D─[Q3 AO3400A]─S── BAT (U1 22,23)
                           G                           G ── SDRV (U1 24)
                           ├── 1 MΩ ── PACK+
                           └── D─[Q2 AO3400A]─S ── GND
                                  G ──┬── 100 kΩ ── BATT_IN
                                      └── 1 MΩ ── GND
PACK+ ── 100 Ω ── BATP ; PACK+ ── VDD y CELL del MAX17048 (0.1 µF)
```

- **Celda bien colocada.** El diodo intrínseco de Q1 conduce primero. Q2 recibe ≈ 0.91 × Vcelda en compuerta (VGS(th) de 0.65–1.45 V) y enciende desde ≈ 1.5 V de celda. Q2 lleva la compuerta de Q1 a GND: VGS = −Vpack. AO3401A: 50/60/85 mΩ máx. a −10/−4.5/−2.5 V, VGS ±12 V, VDS −30 V. Conduce en ambos sentidos, carga y descarga.
- **Celda invertida, con o sin USB.** BATT_IN queda negativo, Q2 se corta, el 1 MΩ mantiene VGS(Q1) = 0 y el diodo de Q1 queda en inversa. Q1 no conduce aunque el cargador eleve PACK+.
- **Variante simple** (compuerta de Q1 directa a GND, la del plan). Si el cargador eleva PACK+ por carga lenta, Q1 conduce y alimenta la celda invertida en sentido de descarga, con disipación lineal en Q1. Solo vale si el portapilas no admite inversión.
- **2S.** VGS(Q1) = −8.6 V máx. y VGS(Q2) ≈ 7.6 V, dentro de ±12 V. VDS de Q1 ≤ 17 V con la celda invertida y el cargador activo; el máximo es 30 V.
- **Q3, ship FET.** Fuente a BAT, como pide TI en E2E 1053051. Drenador a PACK+ y compuerta a SDRV, con VGS ≈ 5 V. SDRV − BAT tiene un máximo absoluto de 6 V [VERIFICADO]. AO3400A da 32 mΩ máx. a 4.5 V con Qg ≈ 6 nC: con los 100 nA de SDRV el encendido tarda ≈ 60 ms y sirve de arranque suave. Con Q3 abierto su diodo bloquea la descarga.
- **BATP y medidor en PACK+** (después de Q1, antes de Q3):
  - BATP: abs. máx. −0.3 V [VERIFICADO]. Con la celda invertida antes de Q1, recibiría −V con solo 100 Ω.
  - MAX17048: VDD −0.3 V mín., CELL −0.3/+12 V [VERIFICADO]. Mismo problema.
  - PACK+ alimenta el BQ25792 y el medidor durante el *ship mode*, así que el medidor sigue contando.
  - Efecto de medir en PACK+: la caída de Q1 (≈ 60 mΩ × I) queda fuera del lazo. En carga, la celda ve VREG − I·R. Es una subcarga leve que desaparece al terminar (ITERM × R ≈ 12 mV); nunca sobrecarga [INFERIDO].
  - El medidor ve la misma caída, que se suma a la resistencia interna de la celda (≈ 50–100 mΩ). Es la misma situación que medir del lado del host, detrás del PCM del pack [INFERIDO].
- Polarización de Q1/Q2: ≈ 7 µA permanentes en 1S.
- Pista y portapilas para ≥ 3 A de pico.
- Recomendado: celdas 18650 «protegidas» (con PCM), o un PCM en la placa. No hay protección de sobredescarga, sobrecorriente ni cortocircuito propia de la celda.

---

## 4. Riel de 3.3 V

### 4.1 Requisitos

- Entrada mínima: VSYS ≈ 3.0 V (1S casi vacía, sin USB). Con USB, VSYS ≥ VSYSMIN regulado (3.5–4.1 V en 1S).
- Entrada máxima en 2S [VERIFICADO, tabla EC]:
  - Regulación de SYS con VBAT = 8.4 V, carga deshabilitada y PFM deshabilitado: 8.44/8.60/8.77 V.
  - Por encima de la batería, SYS queda 200 mV (PWM) o 600 mV (PFM) [VERIFICADO §8.3.8.1].
  - OVP de SYS: 9.18/9.46/9.67 V.
  - **Diseñar para ≥ 10 V.**
- Salida ≥ 2 A. Consumos [VERIFICADO]:
  - ESP32-S3-MINI-1: 355 mA de pico en TX 802.11b; requiere fuente ≥ 0.5 A y VDD 3.0–3.6 V, máx. absoluto 3.6 V ([datasheet v1.7](https://documentation.espressif.com/esp32-s3-mini-1_mini-1u_datasheet_en.pdf)).
  - UM980: 145–180 mA, VCC 3.0–3.6 V, máx. absoluto 3.6 V, rizado ≤ 50 mV ([manual R1.9](https://en.unicore.com/uploads/file/UM980_User%20Manual_EN_R1.9.pdf)).

### 4.2 Comparación (precios y stock de JLCPCB; datos de los datasheets citados)

| | **TPS62903RPJR (elegido)** | TPS62130ARGTR | TPS62135RGXR |
| --- | --- | --- | --- |
| VIN | 3–17 V; VIN y EN máx. abs. 18 V | 3–17 V; 20 V máx. abs. | 3–17 V |
| IOUT | 3 A | 3 A | 4 A |
| Modo 100 % | sí | sí | sí |
| EN a VSYS | sí (máx. 18 V) | sí (VIN + 0.3 V) | sí (VIN + 0.3 V) |
| Umbral de EN | **1.0 V↑ / 0.9 V↓ ±3 %**, pull-down inteligente de 0.5 MΩ con EN bajo | 0.3–0.9 V, impreciso | 0.8 V↑ / 0.7 V↓ ±3 % |
| IQ / apagado | **4 µA / 0.27 µA** | 17 µA / 1.5 µA | 18 µA / 1 µA |
| RDS(on) alto/bajo | **62 / 22 mΩ** (VIN > 4 V) | 90 / 40 mΩ (12 V); 120 / 50 mΩ (3 V) | 100 / 39 mΩ |
| UVLO | 2.925 V↑ / 2.775 V↓ | 2.9 V↑ / 2.7 V↓ | 2.9 V↑ / 2.6 V↓ |
| Salida | FB 0.6 V o VSET | FB 0.8 V | FB |
| Encapsulado | VQFN-HR-9, 1.5 × 2 mm | VQFN-16, 3 × 3 mm, con EP | VQFN-HR-11, 2 × 3 mm |
| JLCPCB | C2866502, Extended, 2182, USD 0.96 | C337502, Extended, 6717, USD 0.64 | C167238, Extended, 3328, USD 1.05 |

Fuentes: TPS62903 [ZHCSNC0A](https://www.ti.com/cn/lit/gpn/tps62903) (equivale a SLVSES3A, [página de TI](https://www.ti.com/product/TPS62903)); TPS6213x [SLVSAG7E](https://wmsc.lcsc.com/wmsc/upload/file/pdf/v2/lcsc/1912111437_Texas-Instruments-TPS62130ARGTR_C337502.pdf); TPS62135 [SLVSBH3B](https://wmsc.lcsc.com/wmsc/upload/file/pdf/v2/lcsc/1912111437_Texas-Instruments-TPS62135RGXR_C167238.pdf).

Descartados: TPS62133 (5.0 V fijo); TPS62132 (3.3 V fijo, 65 en stock, USD 1.63); TPS62142 (3.3 V fijo, 2 A, 679 en stock, USD 2.03); TPS62140A (299 en stock); TPS62162 (solo 1 A). No hay ningún buck Basic ni Preferred que arranque en 3 V: los Basic de JLC empiezan en 4.5–5.5 V. El buck será Extended en cualquier caso.

**Por qué TPS62903** [INFERIDO]:
- El EN preciso permite un UVLO por divisor: evita arrancar con la celda casi vacía y ayuda con el problema del *ship mode* en 1S.
- RDS(on) bajo: menos caída en modo 100 % al final de la descarga.
- 4 µA de IQ.

La TPS62130A es la alternativa más barata y con más stock (2.2 µH, FSW a VOUT para 1.25 MHz), pero sin UVLO preciso.

### 4.3 Circuito (U2 TPS62903; pines VERIFICADOS en la tabla 5-1)

| Pin | Conexión |
| --- | --- |
| 6 VIN | VSYS. 10 µF/25 V 0805 + 100 nF/50 V junto a VIN/GND. La capacidad efectiva de entrada recomendada es de 3–10 µF [VERIFICADO]. |
| 5 EN | Divisor desde VSYS: 47 kΩ arriba / **20 kΩ (1S)** u **8.2 kΩ (2S)** abajo. |
| 7 MODE/S-CONF | **GND**: FB externo, 2.5 MHz, descarga de salida activada, PFM/PWM automático con AEE [VERIFICADO, tabla 7-1]. |
| 8 SS/TR | 10 nF a GND: tSS = Css × VFB / ISS = 10 nF × 0.6 V / 2.5 µA ≈ 2.4 ms [VERIFICADO, fórmula 14]. |
| 9 FB/VSET | Divisor 100 kΩ (VOUT–FB) / 22 kΩ (FB–GND): VOUT = 0.6 × (1 + 100/22) = **3.327 V**. Con VFB ±0.9 % y resistencias al 1 % queda en ≈ 3.24–3.41 V, por debajo del máximo absoluto de 3.6 V del ESP32 y del UM980 [INFERIDO]. TI: R2 ≤ 400 kΩ [VERIFICADO]. |
| 3 VOS | Directo al positivo del condensador de salida. |
| 2 SW | L2 = 1 µH: Murata DFE252012F-1R0M=P2 (C435392, 2.5 × 2 mm, listado por TI). Alternativa: Sunlord MWSA0402S-1R0MT (27 mΩ, Isat 5.6/7 A). El TPS62903 está diseñado para 1 µH nominal [VERIFICADO]. |
| Salida | 2 × 22 µF/25 V 0805 X5R. TI recomienda 22 µF y admite 10–100 µF efectivos a 2.5 MHz [VERIFICADO]. |
| 1 PG | Sin uso o a un GPIO con pull-up de 100 kΩ a +3V3 (drenador abierto). |
| 4 GND | Plano. |

UVLO por EN [INFERIDO; umbrales y pull-down de 0.5 MΩ VERIFICADOS]:

| Variante | Enciende a | Apaga a | Comentario |
| --- | --- | --- | --- |
| 1S (47 k/20 k) | ≈ 3.44 V (3.34–3.55 V) | ≈ 3.02 V (2.91–3.12 V) | Con USB y celda agotada, VSYSMIN 1S ≥ 3.5 V puede quedar justo por debajo en el peor caso. El sistema arrancaría cuando la carga autónoma suba la celda. Si molesta, usar 22 k (enciende ≈ 3.23 V, apaga ≈ 2.82 V). |
| 2S (47 k/8.2 k) | ≈ 6.83 V (6.62–7.03 V) | ≈ 6.06 V | Por debajo de VSYSMIN 2S (7.12–7.52 V). |

Bajo picos de corriente (≈ 1.5 A) la caída de la celda y de Q1/Q3 puede activar el apagado del UVLO cerca de 3.3 V de celda. El firmware debe apagar antes, por SOC o por tensión [INFERIDO].

Pérdida a 1 A, 3.7 V → 3.3 V: ≈ 0.15 W, ΔTj ≈ 11 °C con RθJA 73.5 °C/W del EVM [INFERIDO].

---

## 5. Riel conmutado del UM980

**Elegido: TPS22919DCKR** (C2149796, Extended, 72 918 en stock, USD 0.125) [VERIFICADO, [ZHCSIW8A](https://wmsc.lcsc.com/wmsc/upload/file/pdf/v2/lcsc/2303011900_Texas-Instruments-TPS22919DCKR_C2149796.pdf)]:
- 1.6–5.5 V, 1.5 A, 90 mΩ típ. a 3.6 V.
- Rampa de 2.7 mV/µs (tR ≈ 1.1 ms, tON ≈ 1.75 ms a 3.6 V).
- Protección contra cortocircuito y apagado térmico.
- **QOD** interna de 24 Ω.
- **Pull-down inteligente en ON** de 530 kΩ.
- Pines: 1 IN, 2 GND, 3 ON, 4 NC, 5 QOD, 6 VOUT.

Circuito [INFERIDO]:
- IN = +3V3 con 1 µF.
- ON = GPIO del ESP32 con **100 kΩ a GND**: queda en OFF durante el reset aunque el GPIO flote.
- QOD unido a VOUT.
- VOUT → FB1 (BLM18PG121SN1D) → VCC del UM980 con 10 µF + 100 nF junto al módulo.

Por qué [INFERIDO; requisitos del UM980 VERIFICADOS en el manual R1.9]:
- El UM980 pide una rampa de VCC **monótona**, VCC inicial < 0.4 V al encender y ≥ 500 ms entre la caída de VCC por debajo de 0.4 V y el siguiente encendido.
- Además avisa de corrientes de arranque por sus condensadores internos. Con ≈ 30 µF y 2.7 V/ms, el pico es ≈ 80 mA.
- La QOD baja VCC rápido, y con 24 Ω a GND evita que el UART alimente el UM980 por las entradas.
- Firmware: esperar ≥ 1 s entre apagado y encendido. Antes de apagar, poner en bajo o en alta impedancia las líneas ESP32 → UM980. Opcional: 1 kΩ en serie en esas líneas.

Elección del GPIO de ON [VERIFICADO en la tabla 2-1/2-2 del ESP32-S3]: evitar los GPIO con pull-up débil en el reset (GPIO0, GPIO43/44, pines SPI y, según el eFuse, MTCK) y los que tienen glitch alto al encender (GPIO18/19/20). GPIO1–14 y GPIO17 no tienen pull en el reset y solo dan glitches bajos.

Alternativas:
- **SY6280AAC** (C55136, USD 0.092): límite de corriente programable, Ilim = 6800/Rset (mínimo 0.4 A), bloqueo inverso y descarga de 150 Ω. Su documento es una «Target Design Specification» preliminar, y el arranque de 120 µs depende del límite de corriente [VERIFICADO, [AN_SY6280](https://wmsc.lcsc.com/wmsc/upload/file/pdf/v2/lcsc/1810121532_Silergy-Corp-SY6280AAC_C55136.pdf)].
- **Discreta Basic** (sin recargo Extended): AO3401A en el positivo con 100 kΩ G–S, compuerta tirada por un AO3400A/2N7002 a través de 22 kΩ, 47 nF G–D para la rampa y 100 kΩ en la compuerta del N-FET [INFERIDO]. Ahorra ≈ USD 3 por pedido, pero no tiene QOD ni protección; la regla de VCC < 0.4 V del UM980 quedaría sin garantizar.

Antena activa [VERIFICADO, manual UM980]: Unicore no recomienda usar VCC_RF como alimentación de antena (sin protección de sobrecorriente ni de sobretensiones). La alimentación de la antena pertenece a la sección GNSS. Conviene limitarla en corriente para que un cable en corto no arrastre +3V3 (§10).

---

## 6. Medidor de batería MAX17048 / MAX17049

[VERIFICADO, [datasheet 19-6171](https://www.100y.com.tw/pdf_file/38-MAXIM-MAX17048,17049.pdf) (copia rev 2 leída); documento canónico en [Analog](https://www.analog.com/media/en/technical-documentation/data-sheets/MAX17048-MAX17049.pdf)]

TDFN-8 (2 × 2 mm) y pad expuesto:

| Pin | Nombre | MAX17048 (1S) | MAX17049 (2S) |
| ---: | --- | --- | --- |
| 1 | CTG | GND | GND |
| 2 | CELL | sin conexión interna; se conecta a PACK+ igualmente | **entrada de medida: PACK+ 2S**, abs. máx. 12 V |
| 3 | VDD | **alimentación y medida: PACK+**, 2.5–4.5 V, 0.1 µF | **fuente regulada de 2.5–4.5 V**, 0.1 µF |
| 4 | GND | GND | GND |
| 5 | ALRT | drenador abierto, a un GPIO (10 kΩ a +3V3) o sin uso | ídem |
| 6 | QSTRT | GND si no se usa | ídem |
| 7 | SCL | bus I2C; tiene pull-down interno | ídem |
| 8 | SDA | ídem | ídem |
| EP | — | GND | GND |

- Dirección I2C fija **0x36** (0x6C/0x6D en 8 bits) en ambos.
- Consumo típico: 23 µA activo, ≈ 3–4 µA en *hibernate* y 0.5 µA en *sleep*.
- El *sleep* solo se activa con MODE.EnSleep = 1 y, además, el bus en bajo durante tSLEEP o CONFIG.SLEEP = 1 [VERIFICADO]. **El firmware debe dejar EnSleep = 0**: en *ship mode* el bus queda en 0 V y el medidor tiene que seguir contando. En la copia rev 2, la nota 6 de la tabla eléctrica habla de «shutdown» tras 2.5 s de bus en bajo, en contradicción con el texto; verificar con la revisión vigente y en banco (§10).
- VCELL se expresa en 78.125 µV por celda. En el MAX17049 mide entre CELL y GND [VERIFICADO]. Que el registro dé la media por celda es [INFERIDO] por la unidad «/cell». Verificar con el pack real.

**Compatibilidad de huella 2S:** sí, mismo pinout. Cambia la alimentación de VDD [VERIFICADO: «MAX17049: Connect to regulated power-supply voltage»; figura 15, alimentado a 3.3 V desde el sistema]. Diseño de variante [INFERIDO]:
- R_FGV1 = 0 Ω (PACK+ → VDD): montado en 1S, sin montar en 2S.
- U5 HT7533-1 (C14289, Basic, 30 V máx., 2.5 µA, SOT-89: 1 GND, 2 VIN, 3 VOUT [VERIFICADO, [HT75xx-1 rev 2.81](https://www.holtek.com/webapi/116711/HT75xx-1v281.pdf)]) desde PACK+ con 4.7 µF a la entrada y a la salida, más R_FGV2 = 0 Ω (LDO → VDD): solo en 2S. Mantiene el medidor activo en *ship mode*. Los valores de los condensadores son [INFERIDO]; confirmar con el datasheet de Holtek.
- Alternativa: VDD desde +3V3. Es más simple, pero el medidor pierde su estado en cada apagado.

Disponibilidad:
- MAX17048G+T10: C2682616, USD 1.92, 25 183 en stock.
- MAX17049G+T10: C18185545, **USD 9.60, solo 50 en stock**. Si falta, se puede montar la variante 2S sin medidor y estimar el SOC con el ADC del BQ25792 (VBAT, IBAT con EN_IBAT = 1) [INFERIDO].

---

## 7. Protección USB

- **D+/D−:** USBLC6-2SC6 de ST (C7519, USD 0.18; alternativa UMW C2687116, USD 0.05) junto al conector por donde entra el cable del panel.
  - El pin 5 del chip va a **+3V3**, no al VBUS del USB: su ruptura VBUS–GND es de 6 V [VERIFICADO, [ficha USBLC6-2](https://pdf.datasheet.support/6df39106/st.com/USBLC6-2SC6.html)] y el VBUS del equipo admite hasta 20 V [INFERIDO].
  - El TPD2E2U06 de TI no tiene pin de riel, pero en JLCPCB solo hay 4 unidades.
  - Par diferencial de 90 Ω y derivación corta al BQ25792.
- **VBUS:** TVS **SMF20A** (VRWM 20 V, VBR 22.2–24.5 V, Vc 32.4 V a 6.2 A, SOD-123FL). MDD C123788, USD 0.03, o Littelfuse C151295, USD 0.12 [VERIFICADO, descripción LCSC/datasheet]. No conduce entre 5 y 20 V.
  - Compromiso [INFERIDO]: a la corriente nominal de pulso, Vc supera los 30 V absolutos de VBUS. Para ESD, los ≈ 50 µF de VBUS + PMID absorben la carga. Una SMF18A protegería mejor, pero conduciría cerca de 20 V.
  - VBUS_OVP del BQ25792: 25.7 V; VAC_OVP: 26 V por defecto [VERIFICADO].
- **CC1/CC2:** 5.1 kΩ a GND en cada línea (Rd de sink). Valor de la especificación USB Type-C, no descargada en esta investigación [INFERIDO].
  - El cable del panel debe llevar CC1 y CC2 por separado, o las Rd deben ir en la placa del conector.
  - Opcional: llevar CC1 y CC2 a dos ADC1 del ESP32 (≥ 47 kΩ en serie) para leer el nivel Rp y ajustar IINDPM.
  - Umbrales típicos vRd: < 0.66 V por defecto; 0.66–1.23 V para 1.5 A; > 1.23 V para 3 A (de la especificación Type-C, [INFERIDO], verificar).
- **Capacidad en VBUS:** ≈ 50 µF entre VBUS y PMID, sin FET de entrada, superan la recomendación clásica de USB 2.0 (10 µF) para la conexión en caliente. Es habitual en cargadores; si se exige conformidad estricta, añadir el par ACFET/RBFET en ACDRV1 [INFERIDO].

---

## 8. Diferencias de BOM 1S / 2S

| Ref. | 1S (por defecto) | 2S |
| --- | --- | --- |
| R_PROG | 4.7 kΩ 1 % (C25900) | 8.2 kΩ 1 % (C25924, Preferred 0402; o C25981 Basic 0603) |
| U4 | MAX17048G+T10 | MAX17049G+T10 (misma huella) |
| R_FGV1 (PACK+ → VDD) | 0 Ω montado | sin montar |
| U5 HT7533-1 + 2 × 4.7 µF + R_FGV2 | sin montar | montados |
| R_EN_BOT (EN del buck) | 20 kΩ | 8.2 kΩ |
| Portapilas | 1 × 18650 | 2 × 18650 en serie |
| Protección de celdas | celda protegida o PCM 1S | **BMS 2S con equilibrado** recomendado: el BQ25792 no equilibra [INFERIDO] |

Sin cambios: condensadores (25 V), MOSFET (30 V, VGS ±12 V), TPS62903 (hasta 17 V), TVS, USB y riel UM980. VREG y VSYSMIN salen solos de PROG. La carga 2S desde 5 V funciona en modo elevador y pide ≈ 2–2.5 A de entrada.

---

## 9. Resumen para el firmware

[Registros y campos VERIFICADOS; secuencias INFERIDAS]

- **Arranque:**
  - Leer REG0x48 (PN[5:3] = 001 → BQ25792).
  - Leer REG0x1B: bit 0 VBUS_PRESENT, bit 3 PG, bit 5 WD.
  - Leer REG0x1C: CHG_STAT[7:5], VBUS_STAT[4:1], BC1.2_DONE[0].
  - Leer REG0x1D bit 0 (VBAT_PRESENT).
- **Configuración, siempre por lectura-modificación-escritura:**
  - SFET_PRESENT = 1 (REG0x14 b7).
  - ICHG = 1000 mA (REG0x03/04, 10 mA por bit → 0x0064).
  - VREG = 4.2 V por defecto (REG0x01/02, 10 mV por bit). Opcional: 4.1 V para alargar la vida de la celda.
  - WATCHDOG = 000 (REG0x10[2:0]).
  - IINDPM (REG0x06/07, 10 mA por bit) según BC1.2/Rp.
  - HVDCP_EN = 0.
  - ADC solo cuando se necesite: REG0x2E b7, modo de disparo único.
- **No hay batería** (VBAT bajo o MAX17048 incoherente): EN_CHG = 0 (REG0x0F b5).
- **Apagado:** procedimiento de §2.6. Corte inmediato con REG0x11 SDRV_CTRL = 10 y SDRV_DLY = 1.
- **Batería baja en 1S:** apagar con ≥ 3.5 V en reposo, o con un SOC de apagado que lo garantice.
- **Botón:** activo en bajo por GPIO (diodo). Antirrebote de ≥ 50 ms; pulsación larga para apagar de 2–3 s; 10 s es el reset por hardware.
- **Medidor:** MAX17048 en 0x36, no tocar EnSleep. ALRT y el INT del BQ25792 pueden compartir GPIO (OR cableado de drenadores abiertos) o ir por separado.
- **UM980:** encender con el GPIO de U3 y esperar ≥ 1 s antes de reencender. Poner los TX hacia el UM980 en bajo o en alta impedancia cuando esté apagado.

---

## 10. Preguntas abiertas y riesgos

1. **Comportamiento de *ship mode* en 1S entre 3.6 y 3.0 V.** Qué ocurre al cruzar VBAT_UVLO en *ship mode*, si hay POR posterior y si Q3 se vuelve a cerrar. Medir en banco antes de fijar el umbral de apagado.
2. **BQ25792 o BQ25798.** El BQ25798 da 1 A por defecto y TI dice que maneja mejor el arranque sin batería (E2E 989217). Cuesta USD 0.79 más. Decisión del propietario.
3. **Detección BC1.2 con el pull-up USB del ESP32 activo.** Probar el procedimiento de firmware y medir el resultado con un puerto de PC, un cargador DCP y un cargador USB-C sin BC1.2.
4. **Medición de CC (Rp)** con ADC: hacen falta 2 GPIO ADC1 libres.
5. **Celdas:** si son protegidas (más largas, ≈ 69–70 mm), el portapilas debe admitirlas. En 2S hace falta BMS con equilibrado.
6. **NTC real:** montaje físico en la celda y cableado al TS.
7. **MAX17049:** disponibilidad y precio. Plan B: estimación por el ADC del BQ25792.
8. **MAX17048 con el bus I2C en 0 V durante el *ship mode*:** comprobar que sigue en *hibernate* y no entra en *sleep*/*shutdown* (nota 6 de la rev 2). Si lo hiciera, un pull-up de SDA/SCL a PACK+ no es aceptable, porque el ESP32 no tolera más de 3.6 V. Habría que despertarlo y hacer *quick-start* en cada arranque.
9. **Huellas:** RQM0029A (BQ25792) y RPJ0009A (TPS62903) son HotRod; usar los patrones de TI. Verificar las asignaciones de pines de USBLC6-2SC6, SOT-23 de AOS y SMF20A con sus datasheets al dibujar.
10. **Alimentación de la antena GNSS:** con límite de corriente (SY6280 o equivalente) o PTC. Alimentar V_BCKP del UM980 desde +3V3 permite arranque en caliente (< 60 µA); si no, va a VCC.
11. **GPIO:** asignar botón, INT, ALRT y GNSS_EN fuera de pines de arranque, con pull-up en el reset o con glitch alto.
12. **Térmica real** del cargador y la celda dentro del cilindro al sol, sobre todo en 2S. Considerar TREG = 100 °C.
13. **Conformidad USB** (capacidad en VBUS, corriente frente a Rp): no evaluada.
14. **Rev D del BQ25792:** la copia pública lleva el encabezado «TI Confidential – NDA Restrictions» y el PCN dice que no estaba en la web de TI. Pedir la versión oficial a TI o al distribuidor antes de cerrar el diseño.
15. **«Preferred Extended» sin recargo:** es la premisa del propietario sobre la política de JLCPCB; no se verificó aquí. El recuento de piezas Extended únicas de esta sección está en el CSV (≈ 8 + el módulo ESP32).

---

## 11. Fuentes

- BQ25792 SLUSDG1D (rev D, abril 2026): <https://mm.digikey.com/Volume0/opasdata/d220001/medias/docus/8929/BQ25792RQMR.pdf>
- BQ25792 SLUSDG1C (rev C, agosto 2022): <https://download.mikroe.com/documents/datasheets/BQ25792_datasheet.pdf>
- TI PCN 20260506000.0: <https://mm.digikey.com/Volume0/opasdata/d220001/medias/docus/8962/PCN20260506000.0.pdf>
- Guía del EVM BQ2579x SLUUCB5E (BOM: CSD17575Q3 como ship FET, SPM6530T-1R0M120): <https://www.ti.com/lit/ug/sluucb5e/sluucb5e.pdf>
- BQ25798 ZHCSNY0C / SLUSDV2 (rev C, 2026): <https://www.ti.com/cn/lit/gpn/bq25798>
- TI E2E: [981616](https://e2e.ti.com/support/power-management-group/power-management/f/power-management-forum/981616/bq25792-do-we-need-a-ship-fet), [1053051](https://e2e.ti.com/support/power-management-group/power-management/f/power-management-forum/1053051/bq25792-reset-ship-mode-issues), [1004118](https://e2e.ti.com/support/power-management-group/power-management/f/power-management-forum/1004118/usb-pd-chg-evm-01-no-ship-mode-because-no-ship-fet-is-populated), [919857](https://e2e.ti.com/support/power-management-group/power-management/f/power-management-forum/919857/bq25792-ship-mode-ilim_hiz-questions), [1225212](https://e2e.ti.com/support/power-management-group/power-management/f/power-management-forum/1225212/bq25792-battery-depletion-threshold), [989217](https://e2e.ti.com/support/power-management-group/power-management/f/power-management-forum/989217/bq25790-unknown-adapter), [1191864](https://e2e.ti.com/support/power-management-group/power-management/f/power-management-forum/1191864/bq25792-usb-c-charging-and-device-communication), [1307985](https://e2e.ti.com/support/power-management-group/power-management/f/power-management-forum/1307985/bq25792-some-technical-question), [1381996](https://e2e.ti.com/support/power-management-group/power-management/f/power-management-forum/1381996/bq25792-does-not-enter-into-ship-mode)
- TPS6213x SLVSAG7E: <https://wmsc.lcsc.com/wmsc/upload/file/pdf/v2/lcsc/1912111437_Texas-Instruments-TPS62130ARGTR_C337502.pdf>
- TPS62135 SLVSBH3B: <https://wmsc.lcsc.com/wmsc/upload/file/pdf/v2/lcsc/1912111437_Texas-Instruments-TPS62135RGXR_C167238.pdf>
- TPS62903 ZHCSNC0A (inglés SLVSES3A): <https://www.ti.com/cn/lit/gpn/tps62903>, <https://www.ti.com/product/TPS62903>
- TPS22919 ZHCSIW8A: <https://wmsc.lcsc.com/wmsc/upload/file/pdf/v2/lcsc/2303011900_Texas-Instruments-TPS22919DCKR_C2149796.pdf>
- SY6280 AN: <https://wmsc.lcsc.com/wmsc/upload/file/pdf/v2/lcsc/1810121532_Silergy-Corp-SY6280AAC_C55136.pdf>
- MAX17048/MAX17049 19-6171: <https://www.100y.com.tw/pdf_file/38-MAXIM-MAX17048,17049.pdf> (copia leída); <https://www.analog.com/media/en/technical-documentation/data-sheets/MAX17048-MAX17049.pdf>
- UM980 User Manual R1.9: <https://en.unicore.com/uploads/file/UM980_User%20Manual_EN_R1.9.pdf>
- ESP32-S3 Series Datasheet v2.2: <https://documentation.espressif.com/esp32-s3_datasheet_en.pdf>
- ESP32-S3-MINI-1 Datasheet v1.7: <https://documentation.espressif.com/esp32-s3-mini-1_mini-1u_datasheet_en.pdf>
- AOS AO3401A / AO3400A (rev 3.1): <https://www.aosmd.com/res/datasheets/AO3401A.pdf>, <https://www.aosmd.com/res/datasheets/AO3400A.pdf>
- Sunlord MWSA-S (inductores): <https://www.alfatec.de/fileadmin/productfiles/datasheets/sunlord_mwsa_s_series.pdf>
- Holtek HT75xx-1 rev 2.81: <https://www.holtek.com/webapi/116711/HT75xx-1v281.pdf>
- USBLC6-2: <https://pdf.datasheet.support/6df39106/st.com/USBLC6-2SC6.html>
- Piezas, stock y precios: API de JLCPCB (<https://jlcpcb.com/parts>), <https://jlcsearch.tscircuit.com>, <https://www.lcsc.com>
