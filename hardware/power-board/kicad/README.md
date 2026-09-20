# KiCad D0

Abrir `power-board.kicad_pro` para alimentación y `usb-native.kicad_pro` para USB. Símbolos propios incluidos en `PowerDraft.kicad_sym` y `sym-lib-table`. Las dos hojas se consolidarán antes de obtener la netlist completa para PCB.

`power-board.kicad_pcb` contiene únicamente un contorno provisional 35 × 30 mm, espesor 1.6 mm, cuatro capas, sin huellas ni pistas. No es un layout terminado.

[Estado del diseño y pendientes](../DESIGN_D0.md). Las vistas e informes ERC están en `review/`. Regeneración mediante `python3 ../tools/build_draft.py`; sobrescribe los archivos D0.
