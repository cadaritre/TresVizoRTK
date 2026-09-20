# A4 — siete piezas impresas y base única

**CAD de revisión reconstruido el 19 de septiembre de 2026.** A4 sí contiene geometría distinta de A3. No es todavía una liberación para fabricar el receptor completo: faltan los planos de fijación del BMI088 y HA-901A, el patrón del inserto seleccionado y la integración de alimentación/encendido.

## Abrir

- En este Mac, `Abrir A4.app` abre directamente las tres vistas con la copia oficial de FreeCAD 1.0.2 ubicada en `~/Applications/FreeCAD-1.0.2.app`. El acceso depende de esa instalación local; no contiene FreeCAD ni es portable a otro ordenador. No utiliza una macro de arranque.
- `TresVizo-case-A4.FCStd`: conjunto completo; las reservas electrónicas interiores están ocultas inicialmente.
- **`TresVizo-case-A4-INTERIOR.FCStd`**: muestra la estructura nueva, los componentes reservados y el coaxial azul. Es la vista más clara para revisar la simplificación.
- `TresVizo-case-A4-EXPLODED.FCStd`: las siete piezas impresas separadas. Es un despiece de revisión, no posiciones de montaje.
- `../exports/review-a4/a4-overview.png`: lámina extraída del CAD real.

A0–A3 se conservan. No renombrar A3 como A4 ni usar la fecha del esquema anterior para identificar el CAD.

### Símbolo TresVizo integrado

El cuerpo principal lleva el **3, sus cuatro trazos y el hexágono**, sin «VIZO», tomados del [logo publicado en tresvizo.com](https://tresvizo.com/). Es un grabado de **36 mm de alto y 0.6 mm de profundidad radial**, centrado a Z=60 mm en el frente +Y, debajo del portillo. Sigue la curvatura exterior y pertenece al mismo sólido del cuerpo: no añade placas, adhesivos ni piezas de montaje. La pared nominal restante en la zona es 2.2 mm; la impresión real todavía requiere prueba.

`branding/tresvizo-logo-source.png` conserva el original descargado; `branding/tresvizo-symbol.svg` y `.json` contienen el contorno utilizado, con una simplificación máxima objetivo de 0.65 píxeles (aproximadamente 0.053 mm a este tamaño). `case_branding.py` realiza el grabado y `case-a4.json` define su tamaño y ubicación. El cuerpo actualizado aparece tanto en el conjunto como en el despiece; se actualizan su STL, su STEP y el STEP general. El documento interior permanece igual porque oculta el cuerpo.

`../exports/review-a4/branding-checks.json` registra un sólido válido, seis regiones grabadas, malla cerrada y cero material añadido o retirado del interior. `gui-checks.json` registra el guardado y la reapertura del modelo con logo en FreeCAD 1.0.2.

### Cierres en macOS y reparación del 19 de septiembre

Los tres documentos A4 se reconstruyeron como sólidos `Part::Feature`, con BREP independiente y proveedores visuales nuevos, conservando la geometría. Se guardaron y reabrieron desde FreeCAD. La restauración correcta del archivo no implica que la aplicación sea estable.

Los cierres posteriores de FreeCAD 1.1.3 ocurrieron en `QMacAccessibilityElement dealloc`, dentro de Qt 6.8.3. Coinciden con el [fallo confirmado de FreeCAD en macOS 26](https://github.com/FreeCAD/FreeCAD/issues/30720). `QT_ACCESSIBILITY=0` y el modo seguro **no corrigieron** los cierres observados en este Mac. El intento de lanzar `open_case_a4.FCMacro` también produjo «Unknown file»; el acceso ahora pasa los tres `.FCStd` directamente.

La [distribución oficial 1.0.2 para Apple Silicon](https://github.com/FreeCAD/FreeCAD/releases/tag/1.0.2) usa Qt 5.15.15 y se instaló por separado para comprobar las vistas A4 sin sustituir `/Applications/FreeCAD.app`. Su descarga se comprobó contra el SHA256 publicado en esa versión.

**Prueba GUI completada a las 21:57:** apertura, validación de colores y proveedores visuales, guardado de copias y reapertura de las tres vistas (43, 7 y 38 sólidos válidos). La sesión duró aproximadamente siete minutos hasta cerrarla deliberadamente, sin un nuevo cierre inesperado. Después se abrió otra instancia desde `Abrir A4.app`, que cargó los tres archivos canónicos sin errores de lectura. El acceso usa Launch Services de macOS; la ejecución directa del binario desde el acceso anterior no disponía de permiso para leer todos los archivos en Documentos.

Los resultados están en `../exports/review-a4/gui-checks.json` y `gui-launch-checks.json`; la prueba anterior con Qt 6 se conserva en `gui-checks-qt6.json`. Estas comprobaciones no equivalen a una garantía de estabilidad indefinida. En este Mac, usar el acceso indicado: abrir un `.FCStd` por doble clic puede seguir llamando a la instalación 1.1.3 con Qt 6.

## Qué cambió realmente

| A3 | A4 |
| --- | --- |
| 13 piezas impresas | **7 piezas impresas**; las siete se cuentan explícitamente |
| Base + tapa de retención + calce | **Una base** con asiento interior para inserto con brida |
| Cuatro varillas Ø5 de 123 mm | Espina continua de **4 mm**, con bordes de refuerzo y apoyos integrados |
| Placas separadas GNSS, SD, ESP, USB | GNSS/USB/ESP/biestable en la bandeja; SD integrado en la cuna de batería |
| Hombro y soporte de antena con columnas | **Una tapa** que incorpora el asiento de antena y paso central |
| Plataforma IMU independiente sin referencia de montaje resuelta | Soporte pequeño, con dos llaves distintas y unión fija M3; patrón del breakout aún pendiente |

Las piezas son: cuerpo, base, tapa superior, bandeja electrónica, cuna de batería con soporte SD, asiento IMU y portillo. No hay placas o casquillos metálicos a fabricar. El inserto roscado, tornillos, tuercas y arandelas se compran terminados.

## Montaje del jalón

La interfaz objetivo sigue siendo **5/8-11 UNC**, conforme al [Reach RX](https://emlid.com/es/reachrx/). No equivale a 3/8-16. Lo universal en esa interfaz es la designación de rosca; el contorno del inserto interno depende del diseño.

La referencia comercial candidata es el [inserto con brida atornillable McMaster 90611A121](https://www.mcmaster.com/90611A121/), con datos de su [catálogo](https://www.mcmaster.com/products/inserts/nut-type~screw-mount/). En esta revisión se dispone con **brida interior apoyada a Z=4 y barril hacia arriba**, de forma que el asiento impreso recibe la carga y los tornillos de brida limitan extracción/giro. El barril no necesita asomar por debajo del plano de apoyo del jalón. La pieza comercial aparece como una envolvente oculta, sin rosca helicoidal ni agujeros inventados.

La base tiene tres ranuras de diseño de ancho 3.4, con recorrido de centro entre radios 12 y 15.5 mm a 120°. **Ese reparto no se presenta como el patrón verificado del producto**. Debe comprobarse contra el plano real antes de cerrar la base; si el patrón no cae en ese rango, se regenera la base con las cotas correctas. Tampoco está confirmada entrega del inserto a México ni si su altura publicada se mide incluyendo la brida. No imprimir la base como pieza final ni comprar tornillos de brida por una longitud supuesta.

No hay techo central que obligue a asumir una longitud universal del espárrago. Debe comprobarse que el hombro del jalón apoye sin que su punta toque el módulo interior o el cable. No se ha ensayado resistencia ni definido par de apriete.

## Placas y referencias fijas

- **GNSS:** cuatro filas de ranuras a Z49/53/97/101, con centros que recorren X10–15 y X−15–−10. Ancho 2.4. Son opciones de ajuste limitadas, no compatibilidad con cualquier placa. Hay una ventana central y espacio bajo el componente. El agujero real de la PCB gobierna el tornillo.
- **microSD:** soportes integrados en la cuna, X±10 y ranuras en Z49–53 / Z87–91. Referencia de familia, no patrón certificado de la unidad del propietario.
- **USB:** cuatro centros 14 × 14 del plano Waveshare, integrados en una repisa. Pasos Ø2.2 de diseño; verificar diámetro real. Se retrasa el módulo para que pueda atravesar el collar al extraer el conjunto.
- **ESP y biestable:** cunas por borde integradas. Los contactos eléctricos no se usan como taladros. Las lengüetas, el FPC, pines y zonas de componentes deben probarse con las placas reales; el CAD no demuestra que sus extremos estén libres de componentes.
- **Batería:** conserva una reserva 56 × 12 × 69, desplazada 1.5 mm hacia −Y. El pack sigue pendiente de selección. No se aprieta la celda con tornillos. La cuna se abre al separar las dos mitades del módulo.
- **IMU:** unión del soporte al módulo por M3 y dos llaves distintas, sin correderas. El soporte tiene plano rígido, pero **no tiene agujeros del breakout** porque no hay plano legible. La reserva no fija el centro del chip ni sus ejes. Debe colocarse y calibrarse según el componente real.
- **Antena:** externa, sobre su propio radomo. La tapa integra el apoyo y un paso central **Ø16 de diseño**, reservado para enhebrar el conector. No es el recorte definitivo de un SMA de panel. Los tres agujeros HA-901A y la solución de sellado/alivio siguen pendientes.

El coaxial azul conserva la reserva Ø5 y radio mínimo de centro 10 de A2. Ahora atraviesa una escotadura simple de la bandeja; el paso no depende de varillas ni plataformas superpuestas. No representa el conector SMA ni certifica el radio del cable comprado.

## Uniones dibujadas

Se representan sin hélices: 2 M3 × 35 con tuercas y arandelas para base–bandeja; 2 M3 × 20 inferiores y 2 M3 × 25 superiores para unir las bandejas; 2 M3 × 12 para el soporte impreso del IMU; y los cuatro M3 × 8 radiales de cuerpo–base heredados. La vista CAD omite deliberadamente tornillos de PCB, antena e inserto cuyos datos están pendientes. Cabezas y tuercas son envolventes de referencia, no dibujos de fabricación de herrajes.

Las tuercas de las bandejas se colocan por detrás antes de montar la batería. El soporte IMU tiene escotaduras para no tapar las cabezas superiores de unión entre bandejas. Las fijaciones del collar y portillo incluyen alojamientos en el cuerpo, pero el cierre completo y las herramientas reales aún requieren ensayo.

## Impresión y orden de armado

Los STL en `../exports/review-a4/` están orientados y rotulados **REVIEW**. No se deben confundir con piezas liberadas para uso topográfico.

1. Bandeja electrónica: espalda plana sobre la cama. Sus salientes crecen hacia arriba; ya no hay cuatro postes esbeltos impresos verticalmente.
2. Cuna de batería: de pie sobre su apoyo inferior. Revisar soporte local bajo las orejas superiores; no se afirma impresión sin soportes.
3. Soporte IMU y tapa superior: invertidos, con la cara plana como apoyo. Revisar puentes y voladizos en el laminador.
4. Base y cuerpo: eje Z vertical. Portillo: orientar/laminar según la superficie curva y acabado requerido.

Montar las placas y tuercas con las bandejas fuera del cuerpo, colocar batería, unir bandejas y soporte IMU, pasar y conectar coaxial, insertar módulo por arriba, fijarlo a la base y cerrar tapa/antena. Para extraer el módulo deben soltarse su fijación inferior y la tapa superior; no arrastrar el cable ni los conectores. Esa secuencia debe ensayarse físicamente: la comprobación CAD de traslación no valida un destornillador ni el acceso a cada conector.

## Comprobaciones reproducibles

`build_case_a4.py` verifica que cada pieza sea un sólido válido, calcula intersecciones entre sólidos, comprueba el volumen reservado del cable, muestrea extracción axial cada 5 mm y comprueba cierre de las siete mallas. Los resultados efectivos están en `../exports/review-a4/cad-checks.json`. `verify_case_a4.py` reabre los documentos y las exportaciones para evitar depender sólo del estado del generador.

No se ejecutó un laminador, una impresión física, una prueba de carga o una validación RF/IP. Quedan por resolver el cargador/protección/regulación y **el pulsador exterior de encendido**; el hueco reservado al biestable no cumple esa función.

Regeneración desde la raíz del repositorio, usando el Python incluido en FreeCAD:

```sh
PYTHONPATH=/Applications/FreeCAD.app/Contents/Resources/lib /Applications/FreeCAD.app/Contents/Resources/bin/python mechanical/cad/build_case_a4.py
```

Las cotas de decisión están en `case-a4.json`; varios detalles de construcción permanecen en el generador. Cambiar JSON no modifica automáticamente un archivo ya abierto.
