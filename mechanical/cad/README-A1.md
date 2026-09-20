# Carcasa A1: HA-901A y montaje del jalón

**Montaje sustituido por [A3 — base imprimible](README-A3.md). Las placas y casquillos metálicos descritos aquí son históricos y no se requieren en A3.**

**Corrección posterior: [A2 — paso y recorrido del coaxial](README-A2.md).** Conserva el cartucho A1 y corrige el soporte de antena y el paso lateral del bastidor.

**Revisión mecánica; no liberada para fabricación final.** A1 corrige la base sin rosca de A0 y elimina la segunda cubierta sobre la antena. Se conserva A0. Sus pendientes de electrónica, batería, alimentación y cableado siguen abiertos.

## Archivos

- `TresVizo-case-A1.FCStd`: conjunto con 52 sólidos separados, colores y tabla informativa.
- `TresVizo-case-A1-MOUNT-SECTION.FCStd`: corte ilustrativo de la base. No fabricar las piezas cortadas.
- `../exports/review-a1/case-a1-review.png`: lámina obtenida de los sólidos CAD.
- `../exports/review-a1/`: STEP del conjunto y piezas; STL sólo de plásticos para prototipo. Los `-METAL.step` requieren metal.
- `case-a1.json`, `build_case_a1.py`: parámetros y generador. Usa geometría de `TresVizo-case-A0.FCStd` y utilidades de `build_case.py`.

El FCStd admite operaciones posteriores sobre sólidos. No tiene un historial de croquis gobernado por la hoja: editar sus celdas no reconstruye piezas. Guardar modificaciones manuales en una copia antes de regenerar.

## Antena y plástico

La foto de compra identifica **HA-901A** y muestra tres agujeros inferiores. La inscripción incluye `43.5 × 40.8 mm`; falta un plano que asigne diámetro, altura y salientes y documente círculo, rosca y profundidad de agujeros. Se mantiene una **reserva de diseño Ø46 × 46**, no una medida certificada. Su base está en Z=168 y el conjunto reservado alcanza Z=214; diámetro máximo de carcasa 74.

Una helicoidal puede instalarse dentro de un equipo, pero una cubierta dieléctrica adicional puede cambiar su sintonía y patrón. [u-blox, GNSS antennas, secciones 5.2 y 5.3](https://content.u-blox.com/sites/default/files/products/documents/GNSS-Antennas_AppNote_%28UBX-15030289%29.pdf) explica estos efectos; no certifica esta HA-901A ni fija su separación admisible.

**Decisión A1:** antena al exterior con su envolvente original, arriba del hombro. El soporte llega a su base y tiene paso coaxial; quedan pendientes sus tres taladros reales. No desmontar la cubierta original ni utilizar el SMA como soporte mecánico. No se confirmó el grado IP de la antena o del conjunto.

Una tapa exterior continua tipo RX requeriría comparar con/sin tapa manteniendo posición y orientación: C/N0 por satélite/banda, seguimiento y observaciones, alternando configuraciones. Después contrastar posiciones con referencia independiente. FIX solo no valida la tapa. No copiar el APC ni la altura de Emlid al instrumento.

## Rosca y compra propuesta

[Emlid especifica 5/8″-11 UNC para Reach RX](https://emlid.com/reachrx/). La pieza fotografiada parece un adaptador **3/8″ macho exterior a 1/4″ hembra interior**, no hembra de 3/8″. Su paso no puede certificarse sólo por la foto. No se utiliza en A1.

Se propone una **tuerca hexagonal metálica 5/8″-11 UNC, rosca interior 2B**. Referencia de fabricante: [L.H. Dottie HN58](https://lhdottie.com/pdf/product-specification-sheet/HN58), acero cincado; ancho entre caras 23.4188–23.8252 mm y altura 13.589–14.1986 mm. Una tuerca pesada, acopladora o de brida puede tener otra envolvente. No sustituir por M16, 5/8-18 UNF ni insertos de cámara.

El jalón concreto está pendiente de confirmación. Medir diámetro mayor, paso, longitud saliente de espiga y apoyo del hombro. 5/8″ equivale a 15.875 mm; 11 hilos/pulgada a paso 2.309 mm. El diámetro solo no identifica una rosca.

## Retención

De abajo hacia arriba: placa de apoyo, placa con hueco hexagonal, tuerca comercial con calce y placa superior. Las tres placas son **metálicas, de 3 mm**. La inferior recibe el apoyo del jalón; la superior impide extracción en el sentido opuesto. El hexágono bloquea el giro de la tuerca.

Cuatro M4 pasantes, a radio 19 mm (X/Y = ±13.435 mm), unen placas y bastidor. Casquillos metálicos reparten la compresión. Cuatro M3 radiales con tuercas cautivas unen cuerpo y base. La trayectoria de carga incluye estas uniones y el bastidor impreso: el cartucho metálico no valida automáticamente el receptor completo.

La retención no requiere un prisionero presionando la rosca del jalón. **Sí hace falta evitar que el receptor completo se desenrosque:** usar el collar/contratuerca del jalón o una contratuerca 5/8-11 compatible si hay espiga suficiente. El bloqueo de la tuerca dentro de la carcasa y el bloqueo del receptor sobre el jalón son funciones distintas.

El espacio axial nominal para tuerca y calce es 14.7 mm. Según la altura publicada, el calce teórico es 0.5014–1.111 mm. Medir y seleccionar al montar; no compensar un calce incorrecto deformando piezas al apretar. Ajuste del hexágono, casquillos y precarga requieren prueba física.

## Lista para cotizar después de confirmar el jalón

| Cantidad | Pieza | Condición |
| --- | --- | --- |
| 1 | Tuerca hexagonal de acero 5/8-11 UNC-2B | HN58 o equivalente dimensional comprobado. Es la rosca hembra del receptor. |
| 3 | Placas de acero de 3 mm | Inferior, llave hexagonal y superior; STEP incluidos. No imprimir en plástico para servicio. |
| 4 | Tornillos M4 × 30 avellanados a 90° | Longitud total 30; cabeza compatible con avellanado Ø9. Verificar norma y proveedor. |
| 4 + 4 | Tuercas y arandelas M4 | Reservas: AF7 × 3.2; arandela Ø9 × 0.8, interior Ø4.3. Elegir seguro contra aflojamiento y comprobar altura. |
| 4 + 4 | Casquillos metálicos Ø6 / interior Ø4.3 | Largos de diseño 11.7 y 1.3; ajustar con la pila real de piezas. |
| 4 + 4 | Tornillos M3 × 8 y tuercas M3 | Unión radial cuerpo/base; no presionan la espiga del jalón. |
| Según ajuste | Calces metálicos Ø24 / interior Ø17 | Espesor elegido después de medir; STEP representa el caso nominal. |

No se realizaron compras ni se comprobó disponibilidad local. HN58 es referencia dimensional; no es obligatorio importar esa marca.

## Montaje y pendientes

1. Ensayar el hexágono en una probeta. Insertar las tuercas radiales desde arriba antes de cerrar la base.
2. Introducir la placa hexagonal por abajo y la tuerca en su alojamiento. Colocar casquillos, placa inferior y tornillos; completar calce, retención superior y separadores.
3. Fijar bastidor con M4 y arandelas **antes de instalar electrónica**. Comprobar acceso de llave, paralelismo y juego. No se definió torque de servicio.
4. La rosca del cartucho empieza 3 mm por encima del apoyo. El piso del bastidor está en Z=22: la espiga debe lograr suficiente rosca útil sin tocarlo. Ajustar cartucho si el jalón concreto tiene espiga demasiado corta o larga.
5. Completar patrón de antena, coaxial y conectores, alimentación, batería, soportes y juntas.
6. Ensayar torsión, tracción y flexión con masa de prueba antes de montar electrónica. Definir cargas según masa final y uso; no se asignó una capacidad admisible.

Se verificaron **52 sólidos válidos**, sin intersecciones mayores a 0.02 mm³ entre piezas y reservas, incluidos herrajes simplificados. Las **11 mallas de plástico están cerradas**. Se comprobó la entrada superior de las cuatro tuercas radiales en pasos de 0.5 mm, sin choques con la base y antes de colocar el bastidor. Se reabrieron FCStd y STEP, conservando ambos los 52 sólidos válidos. Esto no valida roscas reales, esfuerzos, precarga, cables, acceso de herramientas, sellado, RF o tolerancias de impresión. La prueba de extracción A0 no se transfiere automáticamente a A1.

## Regenerar

Desde la raíz del repositorio:

```sh
PYTHONPATH=/Applications/FreeCAD.app/Contents/Resources/lib \
  /Applications/FreeCAD.app/Contents/Resources/bin/python mechanical/cad/build_case_a1.py
```

El generador también crea el corte separado. Si ya existe una presentación guardada por FreeCAD GUI y coincide la lista de objetos, conserva sólo sus estilos y cámara; nunca reutiliza la geometría anterior. `show_case_a1.py` permite aplicar colores por primera vez en FreeCAD. Asignar el retorno de `runpy.run_path` para no imprimir todo el entorno. Consultar accesibilidad después de actualizar la vista causó un cierre de FreeCAD 1.1.3 en `QMacAccessibilityElement`; los archivos guardados se verificaron por separado. No se cambió ninguna preferencia global para evitarlo.

`render_case_a1.py` genera la lámina PNG y comprueba reapertura nativa/STEP con el Python incluido en FreeCAD.
