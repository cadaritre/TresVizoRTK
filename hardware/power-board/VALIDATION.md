# Verificación digital — Power Board Rev A

20 de septiembre de 2026. KiCad CLI 10.0.6, PCB ruteado de 45 × 40 mm, cuatro capas y ocho hojas de esquema.

| Comprobación ejecutada | Resultado | Evidencia |
| --- | --- | --- |
| ERC del esquema completo | 0 incidencias | [erc.json](rev-a/review/erc.json) |
| DRC de la placa ruteada | 0 incidencias, 0 conexiones pendientes | [drc.json](rev-a/review/drc.json) |
| Paridad esquema–PCB | 0 diferencias | Mismo informe DRC, opción schematic-parity |
| Auditoría de conexiones/MPN/valores/DNP | 450 terminales conectados correctos; 149 referencias eléctricas | [static-checks.json](rev-a/review/static-checks.json) |
| Fabricación | Gerbers de 4 cobres, máscaras, serigrafías, pastas y taladros exportados | [fabricación](rev-a/MANUFACTURING.md) |
| BOM y CPL | 135 componentes poblados; J5 excluido | [assembly](manufacturing/rev-a/assembly/bom.csv) |
| STEP canónico + adaptador FreeCAD | Geometría válida; 142 sólidos y 9 reservas de acceso | [mechanical-checks.json](rev-a/review/mechanical-checks.json) |
| PDF y visuales | Ocho páginas exportadas; inspección visual de esquema y PCB en ambas caras | [PDF](rev-a/output/pdf/power-board.pdf), [3D](rev-a/review/power-board-3d.png) |
| Paquete | ZIP comprobado y hashes SHA256 por archivo | [SHA256SUMS](manufacturing/rev-a/SHA256SUMS.txt) |

El PCB contiene 1,907 segmentos: 635 F.Cu, 764 B.Cu y 508 In2.Cu, además de 218 vías. In1.Cu es el plano GND, sin pistas de señales. ERC/DRC no demuestran por sí mismos funcionamiento, compatibilidad de pinout físico ni calidad RF/USB.

## Revisión eléctrica adicional

La auditoría compara `circuit.json`, netlist XML y pads del PCB; comprueba separación USB_VBUS/SYSTEM_5V, conexiones de datos host/Tiny, polaridad de LEDs, dominios de batería y tabla lógica de KILL. Los cálculos incluyen tolerancia del TPS3808, histéresis, corriente de entrada, tolerancia y deriva térmica de los divisores.

- VBUS: caída nominal 4.4955 V; mínimo calculado 4.3871 V; subida máxima calculada 4.7427 V. R28/R29 exigen 0.1 %, 10 ppm/°C. No reemplazar por resistencias de 1 %.
- Tiny 3V3: subida máxima calculada 3.2227 V con R31/R32 de 0.1 %, 25 ppm/°C; menor que 3.234 V, límite inferior supuesto del regulador de 3.3 V ±2 %.
- PROGRAM_HOLD: nivel alto mínimo calculado 2.530 V; salida boost nominal 4.992 V.
- Las sumas de pistas USB incluyen ramas a puntos de prueba: no son longitudes de vuelo medidas ni certificación de impedancia. Las tolerancias calculadas no incluyen envejecimiento, contaminación o fugas de la PCB.

## Verificación física que corresponde al prototipo

No se han realizado ensayos de banco, simulación de transitorios, validación térmica/ESD/EMC, certificación USB ni fit en carcasa. El plan de prueba reproducible está en [BRINGUP.md](rev-a/BRINGUP.md): estados batería/USB, carga, desconexión, backfeed, arranque/apagado, suspensión, flashing y debug.

J5 conserva huella candidata DNP; la serigrafía ESP32-S3-TINY y los esquemas genéricos oficiales no prueban el mapeo del cable de la unidad. La batería de la foto declara 3.7 V/5000 mAh; límites de carga, polaridad y protección interna requieren comprobación física/datasheet del pack. El NTC externo forma parte del montaje. La revisión DFM y abastecimiento preceden a cualquier pedido; no se ha comprado ni fabricado.

Los resultados D0/P1 se conservan en [VALIDATION_D0.md](VALIDATION_D0.md); no describen el estado actual.
