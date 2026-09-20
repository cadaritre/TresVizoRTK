> **PCB PERSONALIZADA CANCELADA — 20-09-2026.** Por indicación del propietario se retiraron sólo los archivos de diseño PCB, sus generadores y salidas de fabricación. Se conserva la documentación y los datasheets como antecedentes; los enlaces a archivos eliminados de abajo ya no son entregables vigentes. La propuesta actual utiliza [módulos comerciales](../power-modules/README.md). El case y el firmware no se modificaron en esta sustitución.

# Power & Interface Board — Rev A

Diseño digital del prototipo terminado: esquema jerárquico de ocho hojas y PCB **45 × 40 × 1.6 mm**, cuatro capas, montaje en ambas caras. Contiene 149 referencias eléctricas y 135 componentes poblados. USB nativo de la Tiny externa; ESP32, UM980 e IMU permanecen fuera de esta placa. CP2102N eliminado. Revisión del 20 de septiembre de 2026.

- [Proyecto KiCad 10](rev-a/power-board.kicad_pro), [esquema editable](rev-a/power-board.kicad_sch), [PDF de 8 hojas](rev-a/output/pdf/power-board.pdf) y [PCB ruteado](rev-a/power-board.kicad_pcb).
- [Vista 3D](rev-a/review/power-board-3d.png), [cara inferior](rev-a/review/power-board-bottom.png) y [mapas de componentes](rev-a/review/assembly-top.svg).
- [Decisiones de diseño](rev-a/DESIGN.md), [potencia](POWER_BUDGET.md), [conexiones y firmware](rev-a/INTERFACES.md).
- [BOM](manufacturing/rev-a/assembly/bom.csv), [BOM JLCPCB](manufacturing/rev-a/assembly/bom-jlcpcb.csv), [CPL](manufacturing/rev-a/assembly/cpl-jlcpcb.csv) y [notas de compra](bom.md).
- [Fabricación](rev-a/MANUFACTURING.md), [pruebas del prototipo](rev-a/BRINGUP.md) y [verificación realizada](VALIDATION.md).
- [STEP de integración](manufacturing/power-board.step), [JSON mecánico](../../mechanical/integration/power_board_interface.json) y [guía FreeCAD](../../mechanical/integration/POWER_BOARD_INTEGRATION.md).
- [Paquete completo ZIP](manufacturing/power-board-rev-a.zip).

**ERC: 0 incidencias. DRC: 0 incidencias, 0 conexiones pendientes y 0 diferencias esquema–PCB.** Auditoría adicional: 450 conexiones comprobadas y cálculo de márgenes USB. Son verificaciones digitales; no ensayos eléctricos.

J5 queda como **FPC candidato DNP**, sin montar hasta contrastar contactos, orientación y continuidad con la unidad real. La BOM identifica datos comerciales sin confirmar. El prototipo requiere DFM del ensamblador, NTC externo en la batería y pruebas eléctricas/térmicas/USB/mecánicas antes de liberar producción. No se ha pedido fabricación.

`rev-a/` es la revisión vigente. `kicad/`, DESIGN_D0.md y la investigación P1 se conservan como antecedentes, no para fabricación. El propietario autorizó diseño compacto y adaptación mecánica posterior por el responsable de la carcasa.

Fuentes versionables: `rev-a/circuit.json`, `tools/design_rev_a.py`, `tools/render_rev_a.py` y el PCB KiCad ruteado. Se empleó KiCad directamente; no depende de una compilación atopile no comprobada. **No ejecutar layout_rev_a.py sobre el PCB final: es un generador de placement inicial.** La reexportación segura está documentada en MANUFACTURING.md.
