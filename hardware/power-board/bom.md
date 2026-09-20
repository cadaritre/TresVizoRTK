# Compra y montaje — Power Board Rev A

La [BOM completa](manufacturing/rev-a/assembly/bom.csv) contiene 61 filas agrupadas por MPN, con fabricante, encapsulado/huella, cantidad, DNP, código LCSC, clase JLC, observaciones de stock, precio/tramo, fuente y alternativa. El montaje incluye **135 componentes**. Los datos comerciales son observaciones de catálogo del 19–20 de septiembre de 2026; no son una cotización ni una reserva.

[Fuente comercial editable](rev-a/procurement.json) · [BOM JLCPCB](manufacturing/rev-a/assembly/bom-jlcpcb.csv) · [CPL JLCPCB](manufacturing/rev-a/assembly/cpl-jlcpcb.csv) · [revisión de abastecimiento](manufacturing/rev-a/assembly/purchasing-review.csv).

`TBD` significa que no se confirmó el código, precio o clasificación exactos. Una pieza listada por LCSC puede requerir precompra/consignación para PCBA. Para MPN sin código confirmado, adquirir el MPN exacto en distribuidor y acordar consignación; no cargar un código de valor o sufijo parecido. No se ha calculado un precio total ficticio con campos faltantes. `purchasing-review.csv` reúne las filas sin código y las observaciones de falta de stock.

## Selección que debe preservarse

- **Carga/power-path:** TI BQ24074RGTR, 500 mA nominales; la celda de 5 Ah requiere más de diez horas más fase CV en condiciones favorables. NTC externo obligatorio; timer total desactivado deliberadamente, con explicación en DESIGN.md.
- **5 V:** TPS61023DRLR y Coilcraft XAL4020-102MEC; no sustituir inductor por otro de igual inductancia sin revisar saturación, RMS, pérdidas y huella. Capacitores 22 µF/1206 X7R seleccionados considerando polarización DC.
- **Botón:** LTC2954ITS8-1#TRMPBF, grado industrial I. La variante C de investigación P1 no es la pieza montada.
- **USB:** TUSB320LAIRWBR, TPS22950YBHR con bloqueo inverso y TS3USB31ERSER. CP2102N/CH34x no están en el circuito ni la BOM de montaje.
- **Protección de celda:** BQ29700DSER, CSD13202Q2 y shunt WSL1206R0100FEA. No cambiar sufijo del protector: cambia umbrales. Mantener CELL_N separado de GND.
- **Gauge:** MAX17048G+T10 y TMUX1511PWR para aislar las señales cuando los dominios se apagan.
- **Divisores críticos:** R28/R29 0.1 % y 10 ppm/°C; R31/R32 0.1 % y 25 ppm/°C. Las alternativas de 1 % incumplen el análisis de márgenes.
- **Fusibles:** 046601.5NRHF / 0466002.NRHF, serie Littelfuse 466 en 1206. La serie 467 no comparte esta huella.
- **FPC J5:** FH12-8S-0.5SH(55), sólo candidato DNP. No comprar/montar cable ni conector como compatibles con la Tiny sin verificar orientación/continuidad.

Las alternativas indicadas por función requieren revisión eléctrica y de layout, salvo reemplazo con el mismo MPN. Una etiqueta «direct replacement» del catálogo no autoriza sustituir un IC crítico.

## Material externo al montaje SMD

| Elemento | Especificación / uso |
| --- | --- |
| Pack del usuario | LiPo anunciada 955565, 3.7 V/5000 mAh, dos hilos. Verificar polaridad y ficha antes de conectar J2; el conector fotografiado no está identificado |
| NTC | Semitec 103AT-2, 10 kΩ a 25 °C, conectado a J3 y térmicamente unido a la celda con aislamiento adecuado. No puentear TS con resistencia fija |
| Arnés batería / salida GNSS | Pareja compatible con JST PH de 2 contactos; polaridad según INTERFACES.md, no por colores del cable |
| Arnés NTC | Pareja compatible con JST SH de 2 contactos |
| Arnés ESP auxiliar | Pareja compatible con JST SH de 14 contactos; lleva la referencia 3V3 desde la Tiny y señales de control |
| FPC Tiny | Tipo de contacto, orientación y longitud pendientes de la unidad física; J5 queda sin montar |
| Cables / tornillería | Longitud y curvatura según integración mecánica; dos agujeros de 2.2 mm con separación de componentes por ambas caras |

Los arneses y el NTC no forman parte del CPL SMD. Consulte [MANUFACTURING.md](rev-a/MANUFACTURING.md) para capacidades de montaje, vías en pad y revisión de rotaciones. La BOM de alternativas anterior permanece en [BOM_P1.md](BOM_P1.md), identificada como histórica.
