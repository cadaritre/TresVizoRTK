> HISTÓRICO. Estado anterior al diseño Rev A; consultar README.md para la entrega vigente.

# BOM de investigación, no de ensamblaje

**P1: CP2102N y alternativas UART son sólo investigación histórica/contingencia; no se incluyen en la BOM prevista.** Se añaden FPC, detector VBUS y switch USB como TBD; sin pinout/huella inventados.

Consulta: 19 de septiembre de 2026. Precios USD de catálogo LCSC, sin envío/impuestos/ensamblaje; no son cotización ni reserva de stock. Stock LCSC **no demuestra** stock utilizable en PCBA JLC. TBD indica dato no confirmado. Alternativas funcionales no son sustituciones pin a pin.

| Función / fabricante | MPN | LCSC y fuente comercial | Encapsulado | Basic/Extended JLC | Disponibilidad observada | USD/unidad (tramo) | Alternativa |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Charger / TI | BQ24074RGTR | [C54313](https://www.lcsc.com/product-detail/C54313.html) | VQFN16 3×3 EP | TBD; página JLC no recuperada | Precio activo; cantidad no verificada | 2.1424 (1+) | BQ25606RGER, rediseño |
| Charger alternativo / TI | BQ25606RGER | [C374063](https://www.lcsc.com/product-detail/C374063.html) | VQFN24 4×4 EP | TBD | 599 LCSC; listado JLC localizado | 1.6374 (1+) | BQ24074, sujeto a térmica |
| Boost / TI | TPS61023DRLR | [C919459](https://www.lcsc.com/product-detail/C919459.html) | SOT563, 6 pines | [Extended](https://jlcpcb.com/partdetail/TPS61023DRLR/C919459) | 10,180 LCSC | 0.2680 (5+) | TPS63070, nueva BOM/layout |
| Soft-power / ADI | LTC2954CTS8-1#TRPBF | [C683782](https://www.lcsc.com/product-detail/C683782.html) | TSOT23-8 | TBD; acceso JLC falló | 2,356 LCSC | 6.6897 (1+) | LTC2954ITS8-1#TRPBF, suministro TBD |
| Gauge / ADI-Maxim | MAX17048G+T10 | [C2682616](https://www.lcsc.com/product-detail/C2682616.html) | TDFN8 2×2 EP | [Extended](https://jlcpcb.com/partdetail/C2682616) | 25,630 LCSC | 2.1980 (1+) | BQ27441-G1A, shunt/configuración |
| Bridge contingente, no poblado / Silicon Labs | CP2102N-A02-GQFN24R | [C969151](https://www.lcsc.com/product-detail/C969151.html) | QFN24 4×4 EP | TBD; acceso JLC falló | Presentación reel listada disponible; cantidad no reconfirmada | 1.9399 (1+) | CH343P/G con revisión eléctrica/macOS |
| Bridge alternativo / WCH | CH343G | [C2844153](https://www.lcsc.com/product-detail/C2844153.html) | SOP16 | TBD | Precio activo; cantidad TBD | 1.2423 (1+) | CH343P QFN16, código TBD |
| Bridge económico / WCH | CH340C | [C84681](https://www.lcsc.com/product-detail/C84681.html) | SOP16 | TBD | 44,205 LCSC | 0.5900 (1+) | CP2102N, distinta huella |

La variante **C** de LTC2954 está especificada 0–70 °C, no equivale a la **I** −40–85 °C. Para un equipo de campo se propone buscar I; el stock/precio C sólo demuestra una opción comercial de laboratorio. Esto y su coste son puntos de decisión, no detalles a ocultar. La presentación CP2102N sin R, C1550551, apareció agotada; preferir investigación de reel R sin confundir los códigos.

## Componentes auxiliares pendientes de dimensionamiento

| Función | Candidato/familia investigada | Datos comerciales pendientes / condición |
| --- | --- | --- |
| CC sink/current detect | TI TUSB320LAI, sufijo de compra TBD | LCSC, precio, stock/clase/huella TBD; revisar Rd integrado y dead-battery |
| Limitación común USB, OVP y reverse blocking | MPN TBD | Debe contar consumo sistema + charger + lógica y cumplir arranque/suspend; no basta fusible para limitar consumo autorizado |
| Protección pack | TI BQ297xx + FETs, variante TBD | Umbrales, Rds(on), corrientes y recuperación según celda; omisión sólo si PCM del pack verificado |
| UVLO / asistencia de arranque / señales Ioff | MPN TBD | Histéresis, corriente OFF, dominios y prioridades por cerrar |
| Load switch opcional | TI TPS22919 | Evaluado conceptualmente; no es timer ni garantía de bloqueo inverso. Sufijo/stock/precio TBD |
| USB-C, ESD/TVS, botón, RGB, CHG | MPN TBD | Mecánica/acceso, capacitancia USB, clamp y corrientes antes de seleccionar |
| Inductor(es), capacitores, resistencias | MPN TBD | Isat/Irms, DCR, tensión, bias DC y térmica; selección posterior a power budget |
| Conectores batería/ESP/GNSS | MPN TBD | Polaridad, corriente/contacto, altura, plug y salida de cables según fit |

No se ha completado la BOM de pasivos ni las alternativas comerciales de todos los auxiliares porque no hay esquemático ni corrientes fijadas. Cada fila futura debe tener fabricante, MPN completo, huella validada con datasheet, LCSC, clase, stock, precio con cantidad/fecha y alternativa. Las características eléctricas se toman del fabricante, no de etiquetas automáticas del distribuidor: la página JLC del MAX17048 mezcla funciones de cargador/protector que no deben atribuírsele.

## Auxiliares USB nativo P1

| Función | Selección | Condición |
| --- | --- | --- |
| FPC/FFC a Tiny-N8R8 | Fabricante/MPN, contactos, paso, huella, LCSC, clase, precio y stock TBD | Contrastar ambas placas y cable; no copiar símbolo 8/10 sin identificar anclajes |
| Detector USB_VBUS | MPN y datos comerciales TBD | Umbrales, histéresis, caída tras desconexión, lógica segura, Ioff |
| Switch USB fail-safe | MPN y datos comerciales TBD | Abrir D+/D− sin VBUS o Tiny apagada, incluso ROM/reset; validar integridad de señal |
| Pads BOOT/RUN y auxiliares | Geometría TBD | Recuperación sin segundo pulsador exterior obligatorio |
