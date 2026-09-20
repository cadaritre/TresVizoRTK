# Power & Interface Board — propuesta P0

Estado: **arquitectura para aprobación; no es un diseño fabricable**. Revisión documental: 19 de septiembre de 2026. Una PCB auxiliar para el receptor existente. ESP32-S3-Tiny, carrier BDLX UM980, BMI088, microSD, antena y batería continúan siendo módulos externos.

## Decisiones propuestas

| Bloque | Propuesta P0 | Condición antes del esquemático |
| --- | --- | --- |
| Cargador + power-path | TI BQ24074 | Aprobar carga moderada; verificar pérdidas y temperatura dentro de A4. BQ25606 es alternativa si hace falta mayor eficiencia/corriente. |
| 5 V | TPS61023 desde SYSTEM_POWER, con apagado por EN | Confirmar que las placas necesitan 5 V y medir picos. Su corriente de switch no es corriente de salida garantizada. |
| Soft-power | LTC2954-1, con corte hardware independiente del ESP32 | Resolver ventana de arranque, programación y disponibilidad de grado industrial. |
| Fuel gauge | MAX17048, TDFN | Validar estimación con la celda elegida; no sustituye protección. |
| USB-UART | CP2102N-A02-GQFN24R | Ensayar macOS real y confirmar acceso a UART/EN/BOOT de la Tiny. |
| USB-C | Sink de 5 V, USB 2.0; detección CC de corriente | Sin PD; dimensionar límite de consumo total y suspensión USB. |
| PCB mecánica | Outline, espesor, montaje y altura: TBD | Las reservas USB/biestable no constituyen una cavidad única validada. |

Esta es una selección de partida, no autorización implícita de compra o fabricación. La preferencia por BQ24074 responde al espacio y a reducir fuentes de ruido; si no cumple térmica/potencia, **se vuelve a aprobar el cargador**, no se sube la corriente sin verificar.

## Documentos para revisar

- [Requisitos y criterios de aceptación](REQUIREMENTS.md).
- [Arquitectura, alternativas y estados](ARCHITECTURE.md).
- [Presupuesto eléctrico inicial](POWER_BUDGET.md).
- [BOM de investigación y aprovisionamiento](bom.md).
- [Fuentes oficiales y límites de verificación](datasheets/README.md).
- [Interfaz mecánica y restricciones A4](../../mechanical/integration/POWER_BOARD_INTEGRATION.md).

## Pendientes que bloquean el cierre

1. Volumen continuo disponible, fijación, espesor y tolerancias de la nueva PCB; posición del USB, botón y LEDs. A4 no define agujero para el pulsador ni ventana LED.
2. Revisión física, esquema/pinout de alimentación de Tiny y BDLX; consumos simultáneos y transitorios. No confundir UM980 desnudo con carrier.
3. Pack 1S concreto: corriente, NTC, PCM, conector, polaridad, hinchamiento y límites térmicos.
4. Aprobación de los siete bloques de la tabla, junto con el comportamiento del modo de programación descrito en arquitectura.

## Etapas y herramientas

Se propone atopile para fuentes eléctricas textuales y KiCad para revisión/layout/STEP. [Documentación de atopile](https://docs.atopile.io/). No se encontraron `ato` ni `kicad-cli` en PATH; no se instalaron ni se afirmó una compilación. `ato/README.md` define la partición futura, sin pseudocódigo presentado como esquemático compilable. Al aprobar arquitectura, fijar versiones y dependencias, comprobar el flujo en un diseño mínimo y entonces crear las fuentes eléctricas.

Después: esquemático y ERC → aprobación/revisión → placement bajo restricciones mecánicas → routing y DRC → STEP/fit check → fabricación. Esta ejecución no crea esquemático, layout, Gerbers ni commits. No cambia firmware ni carcasa.
