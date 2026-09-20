# Revisión conjunta de integración

Resultado y decisiones: [INTEGRATION_REVIEW.md](../../docs/INTEGRATION_REVIEW.md). Tornillería: [MECHANICAL_BOM.md](../MECHANICAL_BOM.md).

El A5 de `../A5/TresVizo-A5.FCStd` sigue siendo la base autoritativa. Se conserva byte a byte. La variante derivada usa el generador del panel actualizado y sus parámetros; **no es una liberación de receptor completo**.

- `generated/TresVizo-panel-modules.FCStd`: panel corregido y copias embebidas del A5 actual.
- `generated/TresVizo-integration-review.FCStd`: mismos sólidos más reservas de estudio de power y cableado. Las reservas no son soportes ni piezas imprimibles.
- `generated/case-integration.step`: panel, cuerpo y chasis modificados; no contiene todo el receptor.
- `generated/panel-assembly.step`: panel y referencias del panel.
- `generated/stl/`: exportaciones para ensayos parciales; usar `A5_Chassis`, no la vieja `A5_ElectronicsTray`.
- `generated/fit-report.json`: colisiones de panel contra A5.
- `generated/integration-audit.json`: pares completos, movimientos muestreados, reservas, enchufe, herramienta, inserto y exportaciones.
- `review_parameters.json`: reservas explícitamente estimadas y medidas pendientes del jalón en `null`.
- `evidence/`: huellas de entradas, estado Git inicial y reproducción del fallo anterior.

## Reproducir en esta Mac

Desde la raíz del repositorio:

```sh
PYTHONPATH=/Applications/FreeCAD.app/Contents/Resources/lib /Applications/FreeCAD.app/Contents/Resources/bin/python mechanical/panel-modules/build_panel.py
PYTHONPATH=/Applications/FreeCAD.app/Contents/Resources/lib /Applications/FreeCAD.app/Contents/Resources/bin/python mechanical/integration-review/audit_integration.py
/Applications/FreeCAD.app/Contents/Resources/bin/python mechanical/panel-modules/render_panel.py
PYTHONPATH=/Applications/FreeCAD.app/Contents/Resources/lib /Applications/FreeCAD.app/Contents/Resources/bin/python mechanical/integration-review/plot_assembly.py
```

FreeCAD 1.1.3 con OpenCascade. En otro entorno usar el Python que pueda importar `FreeCAD`, `Part`, `Mesh` y `MeshPart`; para render, NumPy y Pillow; para secciones, Matplotlib. No depende de macros de `legacy`. El render prepara presentación del archivo del panel; la auditoría usa BREP, nunca píxeles.

El generador escribe por defecto en `generated/`, para conservar el paquete anterior del panel. Admite `--output-dir`; el render admite `--input-dir`. La auditoría lee la salida predeterminada. No ejecutar `evidence/baseline-build-panel.py` dentro del repositorio: es evidencia congelada del generador anterior, que esperaba otra estructura de carpetas. Su ejecución original se reprodujo sobre una copia temporal y falló por `A5_ElectronicsTray`.

Los JSON conservan también colisiones intencionales (tornillo/piloto, rosca representada dentro de la envolvente de antena) y estudios que fallan; consultar su clasificación en el informe. **Ausencia de choque de un tramo recto no significa arnés completo resuelto.** Las muestras de movimiento no prueban todos los puntos intermedios ni la flexibilidad de cables reales.

Imprimir primero cupón y componentes pequeños de panel para ajustar el AU-101 y USB reales. La base/inserto, fijaciones power/placas, cables y ensayos eléctricos impiden liberar el receptor completo.
