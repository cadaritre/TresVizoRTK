# Mecánica vigente — TresVizo V1

**Abrir [TresVizo-V1.FCStd](v1/generated/TresVizo-V1.FCStd) con FreeCAD 1.0.2.**

| Carpeta / archivo | Uso |
| --- | --- |
| [v1/generated/stl](v1/generated/stl/) | Imprimir: diez piezas del receptor y una plantilla. |
| [v1/generated](v1/generated/) | CAD, STEP, vistas y resultados finales de V1. |
| [v1](v1/README.md) | Montaje, parámetros y scripts de regeneración vigentes. |
| [sources](sources/README.md) | A5 y generador base necesarios para regenerar; no son entregables de impresión. |
| [MECHANICAL_BOM.md](MECHANICAL_BOM.md) | Compra mecánica: 19 tornillos, 13 tuercas y McMaster 90611A121. |

Estado y comprobaciones: [INTEGRATION_REVIEW.md](../docs/INTEGRATION_REVIEW.md). V1 está comprobada en CAD para la primera impresión completa; falta el ensayo físico. Conserva exterior, FRONT +Y, datum del BMI088 y ejes de antena/jalón.

Los intermedios regenerables están en `.cache/mechanical-v1/`, ignorados por Git.
