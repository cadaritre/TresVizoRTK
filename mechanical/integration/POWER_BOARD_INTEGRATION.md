# Integración de Power Board Rev A

La Power Board se entrega como **un nuevo componente del assembly existente**. Sólo modela la nueva PCB, sus componentes, conectores y reservas de acceso. El propietario autorizó una placa compacta y adaptación de la integración por el responsable de la carcasa; esta entrega no cambia carcasa ni módulos externos.

## Archivos y marco local

- [STEP canónico](../../hardware/power-board/manufacturing/power-board.step), con 142 sólidos válidos.
- [Interfaz JSON](power_board_interface.json): datos de placa, agujeros, seis conectores, botón, LEDs, envolventes y nueve reservas.
- [Adaptador FreeCAD](power_board_reference.py): carga STEP, agrega referencia y comprueba interferencias.
- [Informe geométrico](../../hardware/power-board/rev-a/review/mechanical-checks.json) y [fuentes de modelos](../../hardware/power-board/rev-a/lib/3dmodels/MODEL_SOURCES.md).

El contorno es 45 × 40 mm y espesor nominal 1.6 mm. Centro geométrico XY=(0,0), cara inferior del PCB Z=0, unidades mm, marco derecho. Desde KiCad: `X=x−22.5`, `Y=20−y`. El USB sale hacia +Y; su vector de inserción apunta −Y, desde el cable al receptáculo.

Los agujeros NPTH de 2.2 mm están en (−20,+17.5) y (−20,−17.5). El bounding box STEP completo es **X −22.5…22.5, Y −20…20.15, Z −1.59…5.44 mm**, incluyendo el FPC candidato DNP como reserva. Las envolventes generales conservadoras reservan componentes inferiores Z −1.8…0 y superiores 1.6…5.7. Son reservas de diseño, no medición de una PCB ensamblada.

El STEP original de KiCad usa un sólido dieléctrico de 1.51 mm y otro origen Z. El canónico conserva XY y los taladros reales, normaliza el cuerpo al espesor nominal 1.6 mm y desplaza componentes +0.045 mm. Para integrar usar **manufacturing/power-board.step**, no el STEP original de `manufacturing/rev-a/`.

## Componentes de acceso

| Referencia | Función | Zona de salida |
| --- | --- | --- |
| J1 | USB-C principal | +Y |
| J2 | Batería | −X |
| J3 | NTC externo de batería | −X |
| J4 | Alimentación externa 5 V / GND | +X |
| J5 | FPC candidato, no montado | −Y |
| J6 | Señales auxiliares hacia Tiny | −Y |
| SW1 | Botón momentáneo de encendido | Pulsación hacia −Z |
| LED1 | Carga | Emisión +Z |
| LED2/3/4 | Rojo/verde/azul controlables | Emisión +Z; tres encapsulados |

Las posiciones detalladas proceden del layout en JSON. `position_mm` es la esquina mínima de una envolvente; `size_mm` define sus dimensiones y `rotation_xyzw` el quaternion. Los centros de acople se estiman desde las envolventes y se identifican como aproximados. Confirmar geometría del plug real, carrera de botón, ventana óptica y radios de curvatura antes de recortar la carcasa. Algunos modelos son envolventes conservadoras de encapsulado, identificadas en MODEL_SOURCES.md.

Hay nueve keepouts: plug/inserción USB, cable batería, cable NTC, cable GNSS, arnés auxiliar, FPC, botón, luz de estado y luz de carga. Estas reservas deben transformarse con el mismo placement global que el PCB. `completeness.access_and_cables_reviewed=false` expresa esa revisión física pendiente; no cambiarla sólo para eliminar un pendiente del reporte.

## Uso con FreeCAD

Ejecutar con el repositorio en `sys.path` y Python con FreeCAD/Part:

```python
import FreeCAD as App
from mechanical.integration.power_board_reference import build_geometry, add_reference, check_fit

model = build_geometry()  # STEP válido; sólo Power Board + keepouts
# El responsable mecánico define placement y obstacles en el marco global:
# group = add_reference(doc, placement=placement)
# report = check_fit(model, obstacles, placement=placement, clearance_mm=holgura)
```

`add_reference` agrega un grupo al documento recibido; no mueve objetos existentes ni guarda/rediseña la carcasa. `check_fit` necesita diccionario nombre→Shape de obstáculos globales, placement explícito y holgura. Incluir paredes, bandeja, fijaciones, módulos existentes, batería, antena y cables. Reporta colisiones y distancias sin corregirlas automáticamente.

La prueba de esta entrega confirma que STEP y reservas cargan como formas válidas. **No se ha efectuado fit real en carcasa**: faltan placement, holgura y validación de accesos del responsable de integración. `NO_COLLISIONS_IN_SUPPLIED_GEOMETRY`, cuando se obtenga, sólo tendrá alcance sobre los obstáculos suministrados y no certificará accesibilidad o montaje físico. La geometría de Power Board se cambia en KiCad y luego se reexporta; el JSON no reemplaza el layout como fuente de verdad.
