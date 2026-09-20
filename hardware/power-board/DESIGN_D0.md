> ANTECEDENTE DE INVESTIGACIÓN. La revisión vigente con esquema y PCB ruteado está en [README.md](README.md) y [rev-a/DESIGN.md](rev-a/DESIGN.md). Las indicaciones de fase/pendiente de aprobación siguientes describen su fecha original.

# Diseño D0 — inicio del esquemático

20 de septiembre de 2026. El propietario autoriza empezar y prioriza una PCB compacta; la adaptación de carcasa se hará después. Esto sustituye el bloqueo previo por dimensiones y aprobación P1. Los módulos siguen externos.

## Archivos creados

- `kicad/power-board.kicad_sch`: núcleo con BQ24074, TPS61023, LTC2954-1, MAX17048 y pasivos.
- `kicad/usb-native.kicad_sch`: ESD USBLC6-2SC6, aislamiento TS3USB31E y terminaciones CC.
- `kicad/PowerDraft.kicad_sym`: símbolos locales con los números de terminal verificados en los datasheets enlazados en cada componente. Las asignaciones EP 17/9 son identificadores convencionales del símbolo; deben cotejarse con la huella elegida.
- `draft-netlist.json`: inventario de los 33 componentes y redes del borrador, no BOM de compra.
- `kicad/power-board.kicad_pcb`: **sólo contorno provisional 35 × 30 × 1.6 mm**, cuatro capas declaradas. No contiene componentes ni pistas y no demuestra que el circuito quepa.
- `tools/build_draft.py`: regeneración reproducible. Sobrescribe los archivos D0; dejar de usarlo o incorporar las ediciones antes de editar manualmente KiCad.

Las dos hojas son esquemas independientes durante D0. Las etiquetas no conectan automáticamente un proyecto con el otro. Se consolidarán en una jerarquía antes de obtener la netlist de la PCB completa. No hay huellas seleccionadas, pinout FPC supuesto ni Gerbers.

## Decisiones eléctricas de partida

Carga nominal programada a 500 mA, sujeta a corriente disponible, batería y temperatura. La resistencia ILIM de 3.32 kΩ permite un límite nominal menor en modo externo; no asegura 500 mA de carga simultánea con el sistema. CE se mantiene alto por defecto mientras falta su política de habilitación. Los modos EN tienen pull-down y parten de USB100. El presupuesto debe incluir consumos externos al cargador y tolerancias: no se declara cumplimiento USB por estos valores solos.

La red `USB_INPUT_PROTECTED` entra al cargador; `SYSTEM_POWER` alimenta la conversión y el controlador del botón. El divisor del boost fija 4.992 V nominales. L1 requiere todavía MPN, saturación, DCR y cálculo de pico. Las capacitancias escritas son valores nominales: elegir encapsulados/MPN según capacitancia efectiva bajo polarización.

El LTC2954-1 conserva el corte por pulsación mantenida independiente de firmware. CPDT = 1 µF + 390 nF da aproximadamente 8.97 s nominales; no garantiza todavía el intervalo 8–10 s con dispersión y temperatura. La asistencia de arranque y KILL quedan separadas de EN para no puentear ese corte.

En USB se elige TS3USB31E por su especificación Ioff, con D± del lado host y HSD± del lado Tiny. OE alto desconecta; pull-up al dominio Tiny. El detector pendiente sólo podrá habilitar con VBUS real válido y alimentación Tiny válida. El FPC se representa únicamente por nombres de señales, sin pads ni números físicos. [TI TS3USB31E](https://www.ti.com/lit/ds/symlink/ts3usb31e.pdf).

## Alimentación de la carrier UM980 investigada

La tabla oficial BDLX especifica 4.0–5.5 V, nominal 5.0 V, y 160 mA a 5.0 V para su carrier UM980. Confirma el rail elegido; no documenta aquí corriente máxima de arranque ni el pin de entrada del header de la unidad. El pin de cableado se cerrará con documentación de carrier, sin trasladar el pinout del módulo UM980 desnudo. [Ficha oficial BDLX](https://www.bdlxgnss.com/static/upload/image/20250804/1754279536807539.png).

## Trabajo eléctrico que sigue pendiente

1. Protección de entrada USB y batería, NTC físico, UVLO con histéresis y recuperación. `PACK_PROTECTED` nombra el nodo requerido, no certifica que la batería comercial ya incorpore protección suficiente.
2. Detector VBUS y power-good de Tiny, descarga/sense al desconectar, política CC/USB/suspend y secuencia de arranque con puerto limitado y batería ausente.
3. Lógica de arranque, POWER_HOLD y PROGRAM_MODE, aislamiento de gauge y señales cuando cualquiera de los módulos no tiene alimentación.
4. Conectores, LEDs y drivers; protección ESD de VBUS/CC, protección frente a corto, secuencia de cargas y MPN de pasivos.
5. Consolidación jerárquica, cierre de ERC, selección de huellas, placement, térmica y ruteo. Después se entregará la geometría poblada a mecánica.

D0 inicia el diseño; **no es un esquemático funcional completo ni apto para fabricar o conectar la batería**. No se resuelven estos puntos sustituyendo protecciones por cables o suprimiendo avisos ERC.

## Herramientas y comprobaciones

KiCad CLI 10.0.6 abre y exporta los dos esquemas. La instalación completa vía Homebrew falló al descomprimir por espacio insuficiente; se utiliza el ejecutable desde la imagen oficial montada en `/Volumes/KiCad`. No se requiere instalar toda la biblioteca para los símbolos locales. No se usó atopile: esta iteración usa fuentes KiCad locales directamente.

Las exportaciones SVG están en `kicad/review/`. ERC queda abierto por interfaces sin terminar; ver informes y `VALIDATION.md`. El DRC del contorno vacío sólo comprueba la lectura/geometría básica: cero avisos ahí **no valida ningún circuito, ruteo, huella o ajuste mecánico**. No se hicieron ensayos eléctricos, térmicos ni pruebas con batería.
