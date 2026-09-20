# Carcasa TresVizo A0

**Revisión posterior: [A1 — HA-901A y montaje del jalón](README-A1.md).** Este documento conserva el estado histórico A0; consultar A1 para el cartucho metálico y la antena exterior.

Estudio de envolvente y distribución inspirado en el Reach RX. **A0 no está liberada para fabricar una carcasa funcional**: faltan patrones de algunas placas, anclajes y componentes de alimentación. Los STL sirven para revisar forma y ensayar ajustes por separado.

## Archivos

- `TresVizo-case-A0.FCStd`: conjunto completo en coordenadas de montaje; piezas separadas y tabla de cotas/evidencia.
- `TresVizo-case-A0-INTERIOR.FCStd`: corte ilustrativo con componentes representados por envolventes. No fabricar este corte.
- `case-a0.json` y `build_case.py`: parámetros de envolvente y generador de sólidos FreeCAD. Otras cotas de detalle están explícitas en el script.
- `show_case.py`: abre el conjunto, aplica colores y genera el corte y las imágenes de revisión.
- `../exports/review-a0/`: STEP, STL de prototipo, imágenes y `cad-checks.json`.
- `../research/component-dimensions.md`: fuentes y límites de cada medida.

Los sólidos del FCStd admiten operaciones posteriores en FreeCAD. **No tienen un historial de croquis/revoluciones gobernado por la hoja de cálculo**: la hoja informa; modificar sus celdas no reconstruye las piezas. Para cambiar las cotas de origen, editar JSON/script, regenerar y volver a abrir. Conservar en otro archivo cualquier modificación manual antes de regenerar.

## Forma y organización

La envolvente mide **204 mm de alto y 74 mm de diámetro máximo**. No pretende tener el tamaño del RX (172 × 51 × 51). El cuerpo ahusado, los cuatro grupos de canales, la tapa superior y el panel frontal retoman su distribución visual. El ensanchamiento permite estudiar una batería plana de la familia 955565 y placas comerciales separadas.

El origen CAD es el centro de la cara inferior, Z apunta hacia la antena y +Y hacia el portillo con flecha. Este origen no es un ARP o APC calibrado. La plataforma de la IMU está centrada sobre el eje mecánico; el sensor real no queda situado hasta conocer su posición en el breakout. No se define un botón de medición.

| Pieza | Estado A0 |
| --- | --- |
| Cuerpo | Hueco, pared radial 2.8; canales exteriores de 0.55 de profundidad. Unión superior con espiga y taladros radiales. Falta resolver retención de tuercas/insertos y sellado. |
| Tapa superior | Pared radial 2.4; canales de 0.45. Reserva Helix centrada; ni espesor ni material están validados para RF. |
| Base | Apoyos para bastidor y zona central maciza. **No contiene rosca para jalón**: requiere inserto metálico definido y diseño de retención/carga. |
| Portillo frontal | Dos pasos para tornillos y marca de frente en bajorrelieve. Se retira para el acceso de desarrollo. Su hueco no es un recorte final para USB de carga. |
| Bastidor | Cuatro postes, bandeja inferior con ranuras de cincha, puente para IMU y puente para antena. Se ensayó extracción axial sin choques entre sólidos del CAD. |
| Adaptador UM980 | Montado frente a la reserva de batería, con pasos hacia bastidor. **En blanco para el patrón de la carrier**. |
| Adaptador microSD | Patrón provisional 20 × 38 para la familia documentada; cuatro apoyos. Verificar revisión de la placa antes de usarlo. Tarjeta accesible tras desmontar y extraer el interior. |
| Plataforma IMU | Placa rígida apoyada en el puente del bastidor. Pasos Ø5.5 para los postes; retención final y patrón del breakout pendientes. |
| Plataforma antena | Disco con paso coaxial Ø12 de diseño y fijaciones hacia bastidor. Patrón, conector, soporte de Helix y cable pendientes. |
| Soporte USB | Centros oficiales 14 × 14. Ø2.2 provisional. Fijación de este soporte al bastidor y posición final del conector pendientes. |
| Cuna ESP32 | Placa de adaptación sin patrón inventado sobre pads eléctricos. Retención de placa y fijación al bastidor pendientes. |

No se han modelado tornillos, tuercas, arandelas, insertos, cinchas, cableado ni cargador/regulador. El interruptor está reservado, sin soporte definido. La ausencia de choques entre envolventes no demuestra que todos esos elementos quepan ni que exista acceso para apretarlos. Las reservas son sólidos de comprobación independientes; no son réplicas detalladas de PCB.

## Regenerar

Con el Python incluido en FreeCAD de esta Mac, desde la raíz del repositorio:

```sh
PYTHONPATH=/Applications/FreeCAD.app/Contents/Resources/lib \
  /Applications/FreeCAD.app/Contents/Resources/bin/python mechanical/cad/build_case.py
```

En la consola Python de FreeCAD, para abrir/colorear el archivo y guardar las vistas:

```python
import runpy
_case_preview = runpy.run_path('/Users/cadaritre/Documents/TresVizo RTK/TresVizoRTK/mechanical/cad/show_case.py', run_name='__main__')
```

El generador escribe los archivos A0; no cierra otros documentos. Cerrar o guardar una copia de A0 antes de regenerarlo si ya está abierto, para evitar trabajar con geometría anterior en memoria. No modificar la configuración global de FreeCAD para ejecutar estos scripts.

## Comprobaciones realizadas

En FreeCAD 1.1.3 se verificaron los 11 sólidos de diseño y las ocho envolventes de componentes con `isValid()`, un solo sólido por pieza y volumen positivo. Se comprobó la intersección entre todas las parejas (umbral 0.02 mm³) y la extracción axial del conjunto interior en incrementos de 10 mm; no se detectaron choques en esas comprobaciones. El muestreo no equivale a una comprobación continua de barrido y no incluye sujetadores ni cables.

Las 11 mallas exportadas se comprobaron cerradas con `isSolid()`. Las tolerancias de impresión, resistencia, sujeción de batería, esfuerzos del jalón, calor, estanqueidad y funcionamiento RF siguen sin ensayar. Debe hacerse primero una prueba de ajustes y montaje, después completar los soportes y finalmente fabricar el conjunto definitivo.

## Siguiente revisión

Priorizar el plano de agujeros de BDLX y el del BMI088. Después fijar el pack de batería y la Helix exactos. Cerrar los anclajes pendientes y el inserto del jalón, incluir alimentación y cables, comprobar el enchufe USB real y revisar una sección impresa de las uniones. Sólo entonces convertir la envolvente A0 en un diseño de fabricación.
