# Placa principal TresVizo MeridianV (exploratoria, v0.1)

> **Estado:** diseño generado con scripts y revisado con el ERC y el DRC de KiCad 10.0.6.
> **No se ha fabricado ni probado.** Vive en la rama `hw/main-board-kicad`, fuera de `main`,
> porque el propietario la pidió como exploración. Los resultados de las comprobaciones están en
> [Verificaciones](#verificaciones).

Sustituye a la Thing Plus ESP32-S3, a la carrier BDLX del UM980 y a los módulos de
alimentación por una sola placa de 50 × 76 mm y 4 capas, fabricada y montada por JLCPCB,
que entra en la carcasa V2.2 sin cambiar su exterior (Ø64, ventana del panel, tapa de antena).

| Bloque | Pieza | Notas |
| --- | --- | --- |
| GNSS | Unicore UM980 (LGA soldado) | COM2 y COM3 al ESP32, COM1 al conector auxiliar; antena activa con alimentación propia limitada a 100–200 mA |
| MCU | ESP32-S3-MINI-1-N4R2 | El mismo módulo que la Thing Plus: los GPIO del firmware 0.8.x se conservan |
| IMU | Bosch BMI088 en la placa | SPI; el chip queda sobre el eje del jalón |
| Registro | microSD push-push (SD_MMC 4 bits) | Mismos GPIO que la Thing Plus; detección HIGH con tarjeta |
| Carga | TI BQ25798 (buck-boost NVDC) | USB-C 5 V a 1 A; 1S por defecto, 2S cambiando una resistencia; usar y cargar a la vez |
| Apagado | Modo *ship* del cargador + FET externo | El botón del panel despierta la placa (QON) |
| 3.3 V | TI TPS62903 | 3–17 V, 3 A, modo 100 % (llega al final de la descarga 1S) |
| Riel GNSS | TI TPS22919 | El firmware apaga el UM980 en modo «solo carga» |
| Medidor | MAX17048 (MAX17049 en 2S) | I2C 0x36, como en la Thing Plus |

Esquema en [fab/tresvizo-main-schematic.pdf](fab/tresvizo-main-schematic.pdf), mapa de pines y
conectores en [fab/pinout.md](fab/pinout.md) y vistas en `fab/*-top.png` / `fab/*-bottom.png`.

## Decisiones y cambios respecto al plan

Decisiones del propietario (04-10-2026): UM980 soldado en la placa, un solo cargador TI para
1S/2S, USB-C del panel con carga a 1 A y datos del ESP32, OLED que muestra la carga con el equipo
«apagado», IMU en la placa, exterior de la carcasa fijo. Lo que cambió al investigar, con su motivo:

1. **BQ25798 en lugar de BQ25792.** Es compatible pin a pin y comparte la tabla PROG, pero su
   corriente de carga por defecto es **1 A** (la del BQ25792 es 2 A y vuelve a 2 A cada vez que
   vence su *watchdog*). Así la carga a 1 A no depende de que el firmware arranque. Cuesta
   ~0.8 USD más; el BQ25792 cabe en la misma huella si se prefiere ([research/power.md](research/power.md) §0).
2. **FET externo de *ship mode* (Q101).** La revisión D de la hoja del BQ2579x aclara que el
   modo *ship* no apaga el FET de batería interno; sin Q101 el equipo no se puede apagar.
3. **TPS62903** para 3.3 V (el TPS62133 resultó ser de 5 V fijo).
4. **USB-C en el panel con datos.** El V2.2 sin commitear del repositorio cambió el USB-C del
   panel por un JST-XH de dos pines; esta placa sigue lo que pidió el propietario: el panel lleva
   un breakout USB-C (con 5.1 kΩ en CC1/CC2, p. ej. Adafruit 4090 o SparkFun BOB-15100) cableado a
   J101 (VBUS ×2, GND ×2, D+, D−). **Hay que devolver el USB-C a la tapa del panel en el CAD.**
5. **Conectores JST verticales** (entrada desde arriba) para panel, OLED y puerto auxiliar: los
   cables se enchufan de frente a través de la ventana del panel, sin zonas libres laterales.
6. **IMU sobre el eje**: el BMI088 va en u = 25 mm de la placa, que se monta en un plano que
   contiene el eje del jalón ([research/constraints.md](research/constraints.md) §1.4).
7. **Menos condensadores con la misma capacidad efectiva**: VBUS 22 µF + 100 nF, SYS 2 × 22 µF +
   10 µF + 100 nF, BAT 22 µF (los mínimos efectivos de TI se cumplen holgadamente).
8. **Medidor en 2S**: en vez de un LDO dedicado, el MAX17049 se alimenta de +3V3 con un 0 Ω
   (pierde su estado en cada apagado; se hace *quick-start* al arrancar).

## Mecánica

- Contorno 50.0 × 76.0 mm con chaflanes de 1 mm; FR-4 de 1.6 mm, 4 capas, apilado
  **JLC04161H-7628** (el que JLCPCB aplica por defecto).
- Posición en la carcasa V2.2 (ejes del CAD): cara de componentes en y = −0.475 mirando al panel,
  x = ±25, z = 21 → 97. Origen de la placa (esquina superior izquierda vista desde el panel)
  en x = +25, z = 97. En la placa: **u = 25 − x**, **v = 97 − z**.
- Montaje: dos rieles impresos en los cantos laterales (2.5 mm sin componentes en cada canto) y
  2 tornillos M2.5 en agujeros sin metalizar Ø2.7 en (u, v) = (12, 3) y (38, 3), es decir
  x = ±13, z = 94. **Hay que rehacer el interior del tubo** (quitar respaldo, toalleros y la
  plataforma del IMU de la tapa; añadir rieles, brazos y cuna de la 18650): ver
  [research/constraints.md](research/constraints.md) §1.
- Cara trasera sin componentes (mira a la batería). Altura máxima en la cara frontal: 10 mm
  (4 mm bajo el botón, zona u 19.5–30.5, v 48–59).
- Canto superior (hacia la antena): UM980 y u.FL. Latiguillo u.FL → SMA macho acodado de 60–100 mm.
- Canto inferior («de servicio», quitando la base): microSD con la ranura hacia abajo y el
  conector de batería con la boca hacia abajo.
- Antena del ESP32 en el canto derecho (u 42–50, v 45–61.5 sin cobre en ninguna capa).
- BMI088 en (u, v) = (25, 36.5), girado 180°: según la descripción de la hoja de Bosch, el eje X
  del sensor apunta a la derecha de la placa (−X del equipo) y el Y hacia la antena (+Z). **Hay
  que confirmarlo con la figura 12 de la hoja antes de calibrar**; por eso los ejes van en la capa
  de fabricación y no en la serigrafía.

## Conectores

| Ref. | Conector | Uso |
| --- | --- | --- |
| J101 | JST PH 6 vertical (B6B-PH-SM4-TB) | USB-C del panel: 1-2 VBUS, 3 GND, 4 D−, 5 D+, 6 GND |
| J402 | JST SH 9 vertical (BM09B-SRSS-TB) | Panel: 1 GND, 2 botón, 3-4 anillo LED (ánodo/cátodo), 5 +3V3 (ánodo común), 6-8 cátodos R/G/B, 9 cátodo del LED de carga |
| J403 | JST SH 4 vertical (BM04B-SRSS-TB) | OLED, orden Qwiic: GND, 3V3, SDA, SCL |
| J302 | JST SH 5 vertical (BM05B-SRSS-TB) | UM980 COM1 para UPrecise (adaptador USB-UART de **3.3 V**): GND, TXD1, RXD1, PPS, EVENT |
| J102 | JST PH 2 lateral (S2B-PH-SM4-TB) | Batería: 1 = −, 2 = + (medir la polaridad del pack antes de enchufar) |
| J301 | u.FL | Antena GNSS activa |
| J404 | JST SH 2 vertical, sin montar | NTC 10 k B3435 opcional pegada a la celda (quitar R108) |

Tabla completa generada desde la netlist en [fab/pinout.md](fab/pinout.md).

## Firmware: qué tiene que cambiar

Se conservan todos los GPIO del firmware 0.8.x (UART del UM980 en 43/44, I2C en 8/9, SD_MMC en
33/34/38/39/40/47 y detección en 48 HIGH con tarjeta, botón en 10). Cambia:

- **Identidad nueva** (`hardware_id`, entorno de compilación): la API solo crece.
- **Apagado = modo *ship* del BQ25798 por I2C**: al arrancar escribir `SFET_PRESENT = 1`
  (REG0x14 bit 7), ICHG = 1 A y desactivar el *watchdog*; para apagar, cerrar la microSD, apagar el
  UM980, esperar a que se **suelte** el botón y escribir REG0x11 `SDRV_CTRL = 10` con
  `SDRV_DLY = 1`. Con USB conectado la orden se ignora (estado `power_still_present`).
- **Modo «solo carga»**: si al arrancar hay VBUS y no se pulsa el botón, dejar el UM980 apagado
  (GPIO45 bajo) y mostrar la carga en la OLED; un toque del botón pasa a modo normal y al quitar
  el USB se escribe el modo *ship*.
- **GPIO45 ahora enciende el UM980** (el firmware 0.8.x ya lo pone alto al arrancar). Esperar
  ≥ 600 ms tras el arranque antes de encenderlo y ≥ 1 s entre apagar y encender (Unicore pide
  > 500 ms con VCC < 0.4 V). Con el UM980 apagado, dejar GPIO43 y GPIO6 en alta impedancia.
- **GPIO14 queda libre** (era OFF del Mk2).
- Nuevo: PPS (GPIO1), RESET_N del UM980 (GPIO4), COM3 (GPIO5/6), IMU por SPI (11/12/13, CS en
  15/16, INT en 17/18), LED RGB (7/21/36), anillo del botón (37), INT del cargador (2), ALRT del
  medidor (35), falla de antena (41).
- **1S**: apagar por batería baja con ≥ 3.5 V en reposo (en modo *ship* el BQ2579x necesita la
  celda por encima de ~3.4 V).

## Variantes 1S / 2S

| Ref. | 1S (por defecto) | 2S |
| --- | --- | --- |
| R105 (PROG) | 4.7 kΩ | 8.2 kΩ (C25924) |
| R119 (EN del TPS62903) | 10 kΩ | 3.9 kΩ (C51721) |
| U103 | MAX17048G+T10 | MAX17049G+T10 (C18185545; JLCPCB tenía 50 a 9.60 USD) |
| R115 (VPACK → VDD del medidor) | 0 Ω | sin montar |
| R117 (+3V3 → VDD del medidor) | sin montar | 0 Ω |
| Batería | 1 × 18650 protegida | 2 × 18650 en serie **con BMS de equilibrado** (el BQ25798 no equilibra) |

Con 2S el cargador eleva desde 5 V y pide ~2.2 A de entrada: usar un cargador USB-C de 3 A.
El anillo LED del botón se alimenta de VSYS: con 2S usar la versión de 6 V del botón.

## Pedido en JLCPCB

1. **PCB**: subir `fab/tresvizo-main-gerbers-jlcpcb.zip`; 4 capas, 1.6 mm, apilado
   JLC04161H-7628 (por defecto), acabado **ENIG** recomendado para los LGA (o HASL sin plomo),
   tamaño 50 × 76 mm.
2. **Montaje**: PCBA **Standard** (las fichas de UM980, ESP32-S3-MINI y BMI088 piden Standard y
   rayos X), una cara (top). Standard exige ≥ 70 × 70 mm: pedir **rieles** (p. ej. 10 mm en los
   lados de 50 mm) o panel; JLCPCB lo ofrece en el pedido.
3. Subir `fab/tresvizo-main-bom-jlcpcb.csv` y `fab/tresvizo-main-cpl-jlcpcb.csv` y **revisar la
   orientación de cada pieza en la vista previa de JLCPCB** (sobre todo U102, U105, U201, U301,
   U401, Q1xx, D1xx y conectores).
4. **UM980**: LCSC no lo vende. Opciones: comprarlo (DigiKey 188 USD/u en 5, GNSS.STORE 139.99 EUR)
   y **consignarlo** a JLCPCB (MSL 3: bolsa sellada y horneado), o pedir la placa sin U301 y
   soldarlo después con aire caliente/horno (54 pads + 48 de GND, plantilla de 0.12–0.15 mm).
5. Las piezas sin montar (DNP) quedan fuera del BOM: R101, R102, R117, J404.

Costo estimado en [fab/costo-jlcpcb.md](fab/costo-jlcpcb.md), con precios de la API pública de
JLCPCB del 04-10-2026: **237 USD por 5 placas montadas (47 USD por placa)**, sin el UM980
(140–188 USD cada uno) ni el PCB desnudo de 4 capas. Lo caro son el UM980, el BMI088
(6.79 USD), el ESP32-S3 (4.97 USD) y las cuotas fijas de montaje Standard; las 92 resistencias y
condensadores suman unos 8 USD por placa, casi todo en cuotas de alimentador (1.53 USD por
valor distinto). Confirmar en el cotizador antes de pedir.

## Verificaciones

Hechas el 04-10-2026 con KiCad 10.0.6 (`kicad-cli`) sobre los archivos de este directorio.
**No** se ha fabricado, montado ni medido nada, y no hay simulación eléctrica ni de RF.

| Comprobación | Resultado |
| --- | --- |
| ERC del esquemático | 0 errores, 0 avisos ([fab/erc.rpt](fab/erc.rpt)) |
| DRC con reglas de JLCPCB: pista y separación ≥ 0.127 mm (clases: 0.15 mm, RF 0.2 mm), vía ≥ 0.5/0.3 mm, anillo ≥ 0.1 mm, agujero–agujero ≥ 0.5 mm, cobre–canto ≥ 0.3 mm | **0 errores**. 14 avisos de serigrafía: 12 trazos recortados por la máscara (el gerber ya los recorta) y los contornos de Q103 y J102, que se tocan ([fab/drc.rpt](fab/drc.rpt)) |
| Conexiones sin rutear | 0 |
| Paridad esquemático ↔ PCB | 0 diferencias |
| Vías | Tapadas (*tented*) por las dos caras |
| Reproducibilidad | Tres ejecuciones completas de `build.py`: la pasada principal del ruteo salió idéntica; los remates de GND difieren en unos pocos tramos; el DRC, igual en las tres |

Resultado del ruteo: 3423 tramos (F.Cu 1031 mm, B.Cu 952 mm, capa interna 3 326 mm) y 457 vías
(447 de 0.6/0.3 mm y 10 de 0.8/0.4 mm), 77 de ellas de cosido de GND. L2 es un plano de GND
entero; L3 es el plano de +3V3 con los huecos de esas pistas.

Pistas de potencia más delgadas que su clase (0.4 mm) porque no caben en pines de 0.4–0.5 mm
o en el hueco disponible; conviene revisarlas a mano:

- VSYS hacia la entrada del buck (U105, C117, R118): 0.30 mm.
- BUCK_SW (L102 → U105): 0.30 mm.
- VBUS entre los pines 8 y 3 del BQ25798: 0.20 mm. Los pines 2 y 3 reciben VBUS por la pista de 0.6 mm.
- CHG_SW1 hacia C101 (condensador de *bootstrap*): 0.20 mm; lleva poca corriente.
- VPACK hacia el medidor (U103, R112, R115): 0.20 mm; solo mide.

## Pendientes y riesgos

- **Nada medido**: carga 1S/2S, modo *ship*, rampa del riel del UM980, nivel de ruido del GNSS
  (C/N0) con el ESP32 transmitiendo, alcance de BLE/Wi-Fi con la antena a 4 mm de la pared.
- **Antena del ESP32**: Espressif pide 15 mm libres; en el tubo hay ~4 mm hasta la pared. Medir
  RSSI en el primer prototipo.
- **Antena GNSS**: su LNA se alimenta a 3.3 V con límite de 100–200 mA; comprobar que la helix
  comprada funciona a 3.3 V (si pide 5 V hay que cambiar U302 de fuente).
- **Ejes del BMI088**: confirmar con la figura 12 de Bosch.
- **TS sin NTC**: R106–R108 fijan 25 °C; la celda no tiene protección térmica de carga dentro de
  un tubo al sol. Recomendado: NTC en J404.
- **Panel**: LEDs de 3 mm (el RGB Steren es de 5 mm), anillo del botón de 3–6 V (el comprado es
  de 12 V), USB-C de vuelta en la tapa del panel.
- **Hoja del BQ2579x rev D**: la copia pública dice «TI Confidential»; pedir la oficial.
- **Orientaciones en el CPL**: las huellas de LCSC usan la orientación de JLCPCB; las de la
  biblioteca de KiCad (U102 RQM, pasivos) deben revisarse en la vista previa.
- **Ruteo automático**: las pistas críticas (línea de 50 Ω, lazos del cargador) están
  prerruteadas en `layout.py`; el resto lo rutea `route_rest.py`, un ruteador propio (A* en rejilla
  de 0.1 mm con arranque y reruteo). Freerouting 2.1 se probó primero y se quedaba en 35–150
  conexiones sin rutear. El resultado pasa el DRC, pero es ruteo automático y se nota:
  - muchas pistas en escalera de tramos de 0.1 mm (feo, eléctricamente igual);
  - la capa interna 3 lleva pistas, así que el plano de +3V3 tiene huecos;
  - hay pistas entre los pads bajo el ESP32-S3-MINI-1 (cubiertas por máscara);
  - bajo el BQ25798 se usa la mitad izquierda para sacar sus pines; la mitad de SW1/SW2/PMID
    está prohibida.

  Antes de pedir conviene revisar a mano los lazos del cargador y del buck, la línea de 50 Ω y
  las pistas de potencia delgadas de [Verificaciones](#verificaciones).
- **Modelo 3D del BQ25798**: KiCad no trae el del RQM0029A; el STEP usa un VQFN de 4 × 4 mm
  del mismo tamaño, solo como volumen.

## Regenerar

Requisitos: KiCad 10 (con su Python) y Python 3; nada más. KiCad tiene que tener sus bibliotecas
estándar en las tablas globales (Preferencias → Gestionar bibliotecas); si no, el ERC y el DRC
añaden cientos de avisos de «biblioteca no incluida» que no son errores del diseño.

```bash
cd hardware/main-board/scripts
KICAD_APP=/Applications/KiCad/KiCad.app python3 build.py
python3 cost_jlc.py ../fab/tresvizo-main-bom-jlcpcb.csv ../kicad/tresvizo-main.kicad_pcb ../fab/costo-jlcpcb.md 5
```

`circuit.py` describe el circuito y escribe el esquemático; `layout.py` fija contorno,
colocación, pistas críticas, zonas y clases de red; `build_pcb.py` construye el PCB,
`fanout.py` baja los pads de GND y +3V3 a sus planos, `route_rest.py` rutea el resto y
`finish_pcb.py` añade los rellenos de GND con vías de cosido; `export_jlc.py` y `cost_jlc.py`
preparan el pedido. `mklib.py` genera la biblioteca propia (símbolos y la huella del UM980 a partir de las
cotas del manual de Unicore). Las huellas de `kicad/lib/lcsc.pretty` vienen de LCSC/EasyEDA
(easyeda2kicad) para que la orientación coincida con la de JLCPCB.

No se guardan en git, por pesados y regenerables: los modelos STEP de LCSC (61 MB; los `.wrl`
sí están, y son los que usa el visor 3D de KiCad), la caché de easyeda2kicad y el STEP de la
placa. `easyeda2kicad --3d --lcsc_id=<código>` vuelve a bajar un modelo y `build.py` regenera el
STEP. `probe_pcb.py` sirve para consultar posiciones y choques de pads mientras se coloca.

La investigación con sus fuentes está en `research/`.
