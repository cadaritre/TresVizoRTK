# Placa del USB-C del panel (TresVizo MeridianV, exploratoria v0.1)

> **En la v0.3 (rama `hw/compact-v03`) esta placa no se usa:** el USB-C va en la placa principal
> ([../main-board](../main-board/README.md)).

> **Estado:** diseño generado con scripts y revisado con el ERC y el DRC de KiCad 10.0.6.
> **No se ha fabricado ni probado.** Vive en la rama `hw/main-board-kicad`, junto a la placa principal
> ([../main-board](../main-board/README.md)), y se pide en el mismo panel de JLCPCB que ella.

## Para qué sirve

Lleva un receptáculo USB-C 2.0 al ras de la cara exterior de la tapa curva del panel de la carcasa
V2.2 y lo une con un cable corto JST GH de 8 pines a J101 de la placa principal (carga a 5 V y
USB nativo del ESP32-S3). Es una placa de 4 capas y 1.6 mm, con todas las piezas por la cara superior.

Esquema en [fab/tresvizo-panel-usb-schematic.pdf](fab/tresvizo-panel-usb-schematic.pdf) y vistas en
[fab/tresvizo-panel-usb-top.png](fab/tresvizo-panel-usb-top.png) /
[fab/tresvizo-panel-usb-bottom.png](fab/tresvizo-panel-usb-bottom.png). Los genera `build.py`, igual que el ZIP
de Gerber: cambian en cada vuelta y solo se guardan en git en los hitos (`git add -f`).

## Circuito

| Ref. | Pieza | Función |
| --- | --- | --- |
| J501 | HRO TYPE-C-31-M-12 (USB-C 16 contactos, horizontal) | A6/B6 = D+ y A7/B7 = D− unidos en la placa; SBU sin conectar; carcasa a GND |
| R501, R502 | 5.1 kΩ 0402 | Rd de CC1 y CC2 a GND: el cargador ve un sumidero y entrega 5 V |
| U501 | USBLC6-2SC6 (UMW) | ESD de D+/D−; pin 5 a VBUS y pin 2 a GND |
| D501 | SMF15A (SOD-123FL) | TVS unidireccional de VBUS (la misma pieza que usa la placa principal) |
| J502 | JST GH 8 lateral, XUNPU WAFER-GH1.25-8PWB | Cable a J101 de la placa principal |

Redes: VBUS, GND, USB_DP, USB_DN, CC1, CC2. VBUS se queda en 5 V: solo hay Rd (sin PD) y el cargador
BQ25798 de la placa principal no tiene conectados sus D+/D− (sin HVDCP), así que el pin 5 del USBLC6
puede ir a VBUS.

Detalles de la placa:

- **Cruce de D+/D−.** En el receptáculo los contactos quedan D+, D−, D+, D− (B6, A7, A6, B7). D+ se une
  por la capa superior con una U que rodea la vía de A7; D− se une por la capa inferior y vuelve arriba
  debajo de la U. Desde ahí el par va a 0.25 mm con 0.2 mm entre pistas.
- **U501 cerca de J502.** D+ atraviesa el USBLC6 (pin 6 → pin 1, bajo el cuerpo) y entra a J502.8; D− le
  llega con un ramal de unos 4.5 mm por la capa inferior. Entre J501 y U501 hay unos 10 mm de pista:
  junto al receptáculo no cabía con el cruce, las Rd y VBUS. La placa principal tiene su propio USBLC6
  (U101) junto a J101.
- **VBUS (≥ 0.6 mm).** Cada pad de VBUS del USB-C baja por dos vías a una pista de 0.8 mm en la capa
  inferior, que sube por tres vías a los pines 1-3 de J502. D501 va junto a J502.1. Así VBUS cruza por
  debajo del par de datos sin cortar nada.
- **GND.** Rellenos de GND en las cuatro capas (las internas enteras), 18 vías de cosido y 9 vías de
  bajada de pads (fanout). Los pads de GND del USB-C y las Rd van directo a las patas de la carcasa.
  Todas las vías van tapadas por las dos caras.

## Elección del receptáculo

Se compararon los planos de los dos candidatos (stock de la API de JLCPCB del 04-10-2026):

| | HRO TYPE-C-31-M-12 (C165948) | SHOU HAN TYPE-C 16PIN 2MD(073) (C2765186) |
| --- | --- | --- |
| Stock / precio unitario | 424 026 / 0.19 USD | 882 909 / 0.07 USD |
| Valores nominales | 20 V, 5 A | 5 V, 3 A |
| Canto de la placa | **Dibujado** («PCB EDGE»): 5.79 mm por delante de los postes de centrado | No lo da: su «PRODUCT EDGE» es el frente del propio conector |
| Cara de acoplamiento | 6.28 mm por delante de los postes (2.60 mm por delante de las patas delanteras) → **sobresale 0.49 mm** del canto dibujado | 6.28 mm por delante de los postes; sin referencia al canto |
| Altura del eje | No acotada; altura total 3.26 mm | No acotada; altura total 3.16 mm |

Se eligió el **HRO TYPE-C-31-M-12**: su plano fija la cara respecto del canto. Ningún plano acota la
altura del eje. El modelo 3D de LCSC tiene la carcasa de 0.05 a 3.25 mm sobre la placa, lo que pone el
eje a **1.65 mm**. Concuerda con la altura total de 3.26 mm del plano y con la vista frontal medida a
escala (1.65-1.69 mm).

La huella sale de LCSC/EasyEDA (orientación de JLCPCB), con estos ajustes (ver `scripts/mklib.py`):

- pads dobles separados por contacto;
- ranuras de la carcasa con las medidas del plano (0.6 × 1.7 y 0.6 × 1.4 mm), anillo de 0.2 mm y pasta;
- postes de centrado sin metalizar;
- modelo 3D corrido 2.22 mm, porque el de EasyEDA quedaba fuera de sus ranuras (comprobado en la
  exportación VRML).

## Mecánica

Ejes de la carcasa V2.2 (del estudio CAD): z = eje del jalón hacia arriba, +Y hacia el panel, +X a la
izquierda mirando el panel. La placa es horizontal: cara inferior en z = 90.17 y cara de componentes en
z = 91.77, hacia arriba. Coordenadas de la placa, vista desde arriba con el USB-C arriba:
**u = x + 10.4**, **v = 31.3 − y**.

- **Contorno:** cuerpo u 0–20.8, v 4.7–19.8; lengüeta frontal u 5.2–15.6, v **0.89**–4.7; esquinas de
  R0.5.
  - **El USB-C sobresale 1.29 mm** del frente de la lengüeta (decisión del propietario del
    05-10-2026). El frente quedó 0.8 mm más atrás que el canto del plano de HRO: v = 0.89
    (y = 30.41). La cara sigue en v = −0.40.
  - El cobre más cercano al frente es el de las ranuras delanteras de la carcasa del USB-C, a
    0.41 mm (la regla pide 0.3 mm). Los rellenos de GND paran a 0.3 mm.
  - Los agujeros no cambian: están en el cuerpo, a 0.5 mm de su canto delantero (v 4.7) y a 1.4 mm
    de los laterales.
- **J501:** centrado en u = 10.4 (x = 0), **cara en v = −0.40 (y = 31.70)**, a ras de la tapa curva.
  **Eje a 1.65 mm de la cara de componentes → z = 93.42** (el estudio buscaba 93.50; la abertura de la
  tapa está centrada en z = 93.2 con ±3.5 mm). Carcasa de x = ±4.47, z 91.82–95.02.
- **Agujeros:** H501 y H502, M2 sin metalizar de Ø2.2 en (u, v) = (2.5, 6.3) y (18.3, 6.3), es decir
  x = ∓7.9, y = 25.0, sin cobre en Ø4.4.
- **J502 (GH 8):** en el canto trasero con la boca hacia −Y. Pines 1-8 de izquierda a derecha (u 6.02 a
  14.77), pads en v 14.07–15.77, cuerpo en v 15.5–19.5 y 4.35 mm de alto (llega a z = 96.12).
  - Los anclajes llegan hasta v 19.48 para dejar 0.3 mm de cobre al canto.
  - El plano de XUNPU pone el frente del cuerpo a ras del extremo de los anclajes, y el modelo 3D de
    LCSC 0.09 mm más afuera: la boca queda 0.23–0.32 mm dentro del canto.
  - El GH original de JST dibuja los anclajes 0.25 mm por delante del cuerpo.
- **Resto de piezas:**

  | Ref. | (u, v) | Por qué |
  | --- | --- | --- |
  | R501 | (14.0, 9.75) | Dentro de la zona prevista |
  | R502 | (6.8, 9.75) | Dentro de la zona prevista |
  | U501 | (17.1, 13.4) | Fuera de la zona: con el GH los pads de J502 empiezan en v = 14.07 y queda sitio debajo |
  | D501 | (3.4, 13.0) | Fuera de la zona, junto a J502.1 |

  Todo queda a más de 1 mm de los agujeros (la zona sin cobre es de Ø4.4) y de los cantos laterales.
- **Puentes del panel:** uno en cada canto lateral (u = 0 y u = 20.8), centrados en v = 16.0, de 5 mm.
  - Medido desde la esquina superior izquierda del rectángulo que encierra la placa (u 0, v 0.89):
    **canto izquierdo y canto derecho, a 15.11 mm**.
  - Zona sin cobre de 1 mm de fondo en v 13.0–19.0.
  - El canto trasero no sirve: allí están la boca y los anclajes de J502.
  - En el panel, el USB-C asoma 1.29 mm sobre la fresa. Con la fresa normal de 2 mm quedaría a
    0.71 mm del marco. Por eso, frente a la lengüeta, la fresa del panel se ensancha a 3 mm y quedan
    **1.71 mm** (`cuts` en `../main-board/kicad/panel.json`).

`fab/check3d.txt` (lo escribe `build.py`) mide estas posiciones sobre los modelos 3D de la placa armada.

### Cambios que necesita la tapa del panel del V2.2 (solo propuesta; no se tocó el CAD)

- Quitar el bolsillo del JST-XH.
- Abrir un hueco de 12.8 × 7.0 mm con radios de 1.2 mm, centrado en x = 0, z = 93.2.
  - Con el eje en z = 93.42, el sobremolde del cable tiene 3.28 mm hacia arriba: entran sobremoldes de
    hasta unos 6.5 mm de alto.
  - Si se centra el hueco en el eje (z = 93.42), su borde inferior queda a 0.25 mm de la cara inferior de
    la placa.
  - La lengüeta (x = ±5.2) entra en el hueco con 0.95 mm por lado en las esquinas redondeadas, a la
    altura de la cara inferior.
  - Con el USB-C sobresaliendo 1.29 mm, la lengüeta entra 0.8 mm menos en la pared y el hueco no
    cambia. La pared mide 2.5 mm, de r = 29.5 a r = 32 (`mechanical/v2.2/parameters.json`). El
    frente de la lengüeta (y = 30.41) queda:
    - 1.16 mm detrás de la cara exterior en sus extremos (x = ±5.2) y 1.59 mm en el centro;
    - 1.37 mm (extremos) y 0.91 mm (centro) por delante de la cara interior.
- Dos soportes, de x = 5.9 a 10.2 a cada lado (es decir, x ±5.9 a ±10.2), con la cara de apoyo en
  z = 90.17 sobre el marco de la OLED.
- Agujeros guía de Ø1.6 × 4.5 mm en (x ±7.9, y 25.0) para tornillos autorroscantes M2×5.

## Conectores y cable

| J502 (GH 8, igual que J101 de la placa principal) | Red |
| --- | --- |
| 1, 2, 3 | VBUS |
| 4, 5, 6 | GND |
| 7 | USB_DN (D−) |
| 8 | USB_DP (D+) |
| MP (anclajes) | GND |

- Tres contactos por lado porque el GH admite **1.0 A por contacto con cable AWG26** (hoja de JST GH)
  y el peor caso, la carga en 2S, pide unos 2.2 A.
- Pieza montada: XUNPU WAFER-GH1.25-8PWB (C3029383), con la huella de JST SM08B-GHS-TB. El JST
  original (C265111) estaba sin stock.
- Carcasa del cable: **GHR-08V-S** (C485357). Contactos: **SSHL-002T-P0.2** (C189897), para AWG 26–30;
  conviene AWG26 por la corriente.
- El cable lo arma el propietario con un kit GH precrimpado: **1 a 1** (pin 1 con pin 1), de unos
  80 mm; la longitud se confirma al montar la carcasa.

> **Cuidado:** con este orden de pines, un cable en espejo (pin 1 con pin 8) pone **VBUS contra GND**
> (y 5 V en D+/D−). **Comprobar el cable pin a pin con un multímetro antes de enchufarlo.**

## Lista de materiales (por placa)

Precios y stock de la API de JLCPCB del 04-10-2026, por unidad.

| Ref. | Pieza | LCSC | Tipo en JLCPCB | Stock | Precio |
| --- | --- | --- | --- | --- | --- |
| J501 | HRO TYPE-C-31-M-12 | C165948 | Extendida | 424 026 | 0.19 USD |
| J502 | XUNPU WAFER-GH1.25-8PWB | C3029383 | Extendida | 8 408 | 0.19 USD |
| U501 | UMW USBLC6-2SC6 | C2687116 | Extendida | 81 290 | 0.05 USD |
| D501 | hongjiacheng SMF15A | C19077509 | Extendida | 268 169 | 0.03 USD |
| R501, R502 | UNI-ROYAL 0402WGF5101TCE (5.1 kΩ 1 %) | C25905 | Básica | 5 944 304 | 0.002 USD |

- Archivos: [fab/tresvizo-panel-usb-bom-jlcpcb.csv](fab/tresvizo-panel-usb-bom-jlcpcb.csv) y
  [fab/tresvizo-panel-usb-cpl-jlcpcb.csv](fab/tresvizo-panel-usb-cpl-jlcpcb.csv).
- J502, U501, D501 y las 5.1 kΩ coinciden con piezas de la placa principal y comparten línea en el
  BOM del panel. La única pieza extendida nueva es el USB-C.
- Fuera del montaje (cable): 2 × GHR-08V-S y 16 × SSHL-002T-P0.2 (o un kit GH precrimpado de 8 vías).

## Regenerar

Requisitos: KiCad 10 instalado (con su Python) y Python 3. Usa los scripts de
`../main-board/scripts` sin cambiarlos.

```bash
cd hardware/panel-usb/scripts
KICAD_APP=/Applications/KiCad/KiCad.app python3 build.py
```

Qué hace cada script:

| Script | Función |
| --- | --- |
| `circuit.py` | Circuito, esquemático, proyecto y `kicad/board.json` |
| `layout.py` | Contorno, colocación, pistas fijadas, zonas y zonas sin cobre (puentes y agujeros); toma las clases de red de la placa principal |
| `build.py` | ERC (`fab/erc.rpt`), netlist, PCB (`build_pcb.py`, `fanout.py`, `route_rest.py` solo en F.Cu/B.Cu, `finish_pcb.py`), DRC con paridad (`fab/drc.rpt`), gerbers en zip, BOM/CPL (`export_jlc.py`), vistas y `fab/check3d.txt` |

Salidas que usa la placa principal para armar el panel: `kicad/tresvizo-panel-usb.kicad_pcb` y
`kicad/tresvizo-panel-usb.net`.

La biblioteca `kicad/lib/` se genera una vez con `python3 mklib.py <dir>`, donde `<dir>` es la salida de
`easyeda2kicad --footprint --3d --lcsc_id=<código> --output <dir>/lcsc` para C165948, C2687116 y
C19077509. El GH se copia de la biblioteca de la placa principal. Los STEP no se guardan en git.

## Verificaciones

Hechas el 05-10-2026 con KiCad 10.0.6 (`kicad-cli`). **No** se ha fabricado, montado ni medido nada.

| Comprobación | Resultado |
| --- | --- |
| ERC | 0 errores, 0 avisos ([fab/erc.rpt](fab/erc.rpt)) |
| DRC con las reglas de la placa principal (separación ≥ 0.127 mm, clases 0.15 mm; vías 0.6/0.3 mm; agujero-agujero ≥ 0.5 mm; cobre-canto ≥ 0.3 mm; cobre-agujero ≥ 0.25 mm) | 0 errores, 0 avisos ([fab/drc.rpt](fab/drc.rpt)) |
| Conexiones sin rutear | 0; todo va prerruteado en `layout.py` y `route_rest.py` no tuvo nada que rutear |
| Paridad esquemático ↔ PCB | 0 diferencias |
| Reproducibilidad | Dos ejecuciones seguidas de `build.py` dieron las mismas huellas, pistas y vías (59 tramos, 39 vías) |
| Máscara | Solo hay aberturas en pads y agujeros (vías tapadas por las dos caras, según los gerbers) |
| Posición en el modelo 3D ([fab/check3d.txt](fab/check3d.txt)) | Cara del USB-C en y = 31.70, sobresale 1.29 mm del canto (v = 0.89), eje a 1.65 mm (z = 93.42); boca del GH 0.23 mm dentro del canto |
| Cobre al canto frontal | 0.41 mm (ranuras delanteras del USB-C); rellenos a 0.3 mm |
| Planos consultados | HRO TYPE-C-31-M-12, SHOU HAN TYPE-C 16PIN 2MD(073), JST GH, XUNPU WAFER-GH1.25 |

## Lo que no está verificado

- Nada fabricado ni medido: ni el ajuste en la tapa, ni la carga, ni el USB de datos.
- **Orientación en el CPL:** las huellas de LCSC conservan la orientación de JLCPCB (J501 va girado
  180°), pero hay que revisar cada pieza en la vista previa de JLCPCB.
- **Altura del eje (1.65 mm):** sale del modelo 3D de LCSC; el plano de HRO no la acota.
- **Tolerancias:** la cara de J501 depende de la tolerancia del receptáculo y de su colocación sobre
  los postes. El estudio admite ±0.25 mm. El canto ya no la toca: queda 1.29 mm atrás.
- **Pasta en las patas del USB-C:** las cuatro ranuras llevan pasta para soldarlas en el reflujo,
  como indica JLCPCB para esta pieza. Confirmar con JLCPCB que la plantilla y el proceso son los
  adecuados.
- **ESD:** la eficacia del USBLC6 a 10 mm del receptáculo no está evaluada.
- **J101 de la placa principal:** debe tener el mismo orden de pines (1-3 VBUS, 4-6 GND, 7 D−, 8 D+).
  Comprobarlo en la placa principal antes de pedir.
- **Carcasa:** el hueco, los soportes y los agujeros guía de la tapa del panel no se han hecho en el
  CAD; tampoco el recorrido ni la longitud del cable.
- **Apilado:** en el archivo de KiCad el apilado es el genérico de 4 capas. El JLC04161H-7628 se elige
  en el pedido, como en la placa principal.
