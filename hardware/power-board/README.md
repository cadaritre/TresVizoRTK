# Power & Interface Board — diseño D0

**Diseño iniciado por instrucción del propietario.** USB nativo del ESP32-S3 externo, batería 955565 de 3.7 V/5000 mAh anunciados y carrier UM980 externa. CP2102N fuera del diseño.

- [Estado y decisiones del diseño D0](DESIGN_D0.md).
- [Esquemático de alimentación](kicad/power-board.kicad_sch) y [vista SVG](kicad/review/power-board.svg).
- [Esquemático USB nativo](kicad/usb-native.kicad_sch) y [vista SVG](kicad/review/usb-native.svg).
- [Contorno PCB provisional 35 × 30 mm, sin placement](kicad/power-board.kicad_pcb).
- [Validación y pendientes](VALIDATION.md).
- [Investigación USB / Waveshare](USB_NATIVE_REVIEW.md).
- [Batería de referencia](BATTERY_REFERENCE.md) y [presupuesto eléctrico](POWER_BUDGET.md).
- [Arquitectura y antecedentes P1](ARCHITECTURE.md).

D0 contiene 33 componentes; los esquemas son parciales y todavía independientes. Faltan supervisión, protección, control de arranque y cierre de interfaces antes de consolidar y rutear. No es un diseño fabricable.

El propietario pide avanzar compacto y adaptar la mecánica después. El contorno es un objetivo de trabajo, no una dimensión final ni un fit check. Las restricciones A4 registradas anteriormente son antecedentes; no bloquean iniciar esta iteración.
