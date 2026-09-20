# Panel para módulos comerciales

> **Integración con el A5 simplificado:** el generador y parámetros de esta carpeta fueron actualizados. Las nuevas salidas están en [../integration-review/generated](../integration-review/README.md), conservando los FCStd/STEP/STL y ZIP originales de esta carpeta. Usan `A5_Chassis`, apoyos planos para los M3×8 existentes y cabezas M2 normalizadas. La descripción/render de abajo documenta la entrega anterior de las 12:19, cuyo informe de cero choques no aplica al A5 de las 12:30. Consultar [INTEGRATION_REVIEW.md](../../docs/INTEGRATION_REVIEW.md) antes de imprimir; el producto completo tiene bloqueos de montaje y fijaciones pendientes.

Propuesta mecánica del 20 de septiembre de 2026. **Hay CAD, STEP, STL y soportes físicos modelados.** Es una primera versión para probar ajuste, no una pieza comprobada con componentes e impresión reales. No requiere fabricar ninguna PCB.

![Panel en la carcasa y montaje posterior](panel-preview.png)

## Archivos

- [FreeCAD con panel y A5 embebido](TresVizo-panel-modules.FCStd).
- [STEP del conjunto de panel y referencias comerciales](panel-assembly.step).
- [STEP con panel, carcasa y bandeja modificadas](case-integration.step).
- [Despiece](panel-exploded.png).
- [STL individuales](stl/), incluido un cupón pequeño para probar tolerancias.
- [Parámetros editables](parameters.json), [generador](build_panel.py), [comprobación geométrica](fit-report.json) y [revisión de archivos exportados](export-validation.json).
- [Lista de compra para México](../../hardware/power-modules/SOURCING_MX.md) y [arnés](../../hardware/power-modules/WIRING.md).

El FreeCAD abre mostrando el panel. Las copias `A5_*` y las reservas del Tiny-Adapter están ocultas para inspeccionarlas por separado. Todos los sólidos quedan dentro del archivo; no depende de abrir el maestro A5.

## Diseño y posiciones

Coordenadas del A5: mm, Z vertical, frente +Y, eje del jalón X=Y=0.

| Interfaz | Geometría de esta versión |
| --- | --- |
| Panel | Contorno nominal 28 × 53, Z89…142; misma curva exterior de ServiceCover y pared radial de 2.15. |
| Tornillos del panel | X0 / Z96 y Z139, ejes Y, paso Ø3.4. Avellanado Ø5.8 para cabeza M3 de máximo Ø5.6; seleccionar longitud según tuerca/boss existente. |
| USB-C | Centro X0 / Z132; boca a 1.2 mm dentro de la curva. Paso 9.5 × 3.8, rebaje frontal 14 × 6.5. |
| Estado y carga | X−4 y X+4 / Z121; taladro Ø3.2, difusor Ø2.96 con pestaña trasera. |
| Botón | X0 / Z110; cara Ø9.8, paso Ø10.4, pestaña cautiva Ø13 por dentro. Cara igual a la curva del panel. |
| USB comercial | Cuatro apoyos con piloto Ø1.7; tornillos M2 × 5 a través de los agujeros Ø2.5 del módulo. |
| Cartucho de botón | Dos M2 × 8 en X±9 / Z110; respaldo de 2.5 y cuna para micro-switch nominal de 6 mm. |

**El USB se encastra deliberadamente 1.2 mm.** Su placa es más ancha que el conector: colocarlo tangente a la curva dejaba una pared muy fina junto a las esquinas de FR4. El rebaje permite introducir el enchufe sin un adaptador colgando por fuera. Probar un cable cuyo sobremolde entre en 14 × 6.5; estas cotas no garantizan aceptar todos los cables USB-C gruesos.

Los centros USB vienen del [Eagle oficial Adafruit 5871](https://github.com/adafruit/Adafruit-TS3USB30-PCB): placa 20.32 × 22.86, agujeros en (2.54,2.54), (17.78,2.54), (2.54,20.32) y (17.78,20.32), diámetro 2.5. El conector sale hasta Y24.003 en ese sistema. Se aplica X−10.16 y Y+12.260636 al colocarlo en A5. Espesor de placa 1.6 y altura de conector 3.3 son reservas nominales pendientes de confirmar físicamente; el volumen de los componentes pequeños es simplificado.

El pulsador seleccionado es [Steren AU-101](https://www.steren.com.mx/micro-switch-de-push-con-4-terminales.html), normalmente abierto. Steren **no publica sus cotas** en la ficha consultada. El cartucho toma un cuerpo nominal de 6 × 6, profundidad de cuerpo 3.5 y altura total 5.0 como supuestos editables. No se presentan como dimensiones del AU-101 verificadas. Se puede cambiar este cartucho al recibirlo conservando la cara exterior del panel.

Con esos supuestos, el juego inicial del botón es 0.1 y el tope mecánico permite 0.4 de desplazamiento. La carrera eléctrica y la fuerza de retorno del pulsador comprado deben comprobarse. El actuador no debe mantener el switch pulsado; ajustar profundidad del cartucho y tope antes del montaje definitivo.

## Qué cambia en la carcasa

La propuesta incluye su propia copia de `MainShell` y `ElectronicsTray`:

1. Se amplía el paso tras el panel a 25.2 de ancho entre Z102 y Z135. Mantiene los ejes M3 y sus apoyos.
2. Se retira la repisa provisional anterior del USB en la zona X±11.6, Y12…29, Z124…134.8.
3. Se despeja la antigua cuna del biestable en X±12.3, Y24.4…29.1, Z103…117 para el cartucho y sus cabezas de tornillo.

Sólo se sustrae el material existente dentro de esas zonas. Los sólidos resultantes permanecen válidos y de una pieza. El asiento, ajuste y tornillos de la IMU mantienen su posición. El maestro `mechanical/A5/TresVizo-A5.FCStd` no se escribe; `fit-report.json` registra su SHA-256 antes y después.

Se sustituye la antigua reserva horizontal del Tiny-Adapter por una reserva vertical de 18 × 5 × 18 en X±9, Y18…23, Z143…161. Es una **posición de integración**, todavía sin soporte ni ruta FPC/cable finales. El enchufe USB interno tiene una reserva de 9.2 de longitud, no una pieza comprada verificada. La plantilla temporal de alineación IMU se retira antes del panel.

Los soportes del **panel exterior** están diseñados. La fijación interior del cargador, biestable y adaptador, y el recorrido completo del arnés, siguen correspondiendo a la integración mecánica del resto del receptor. Este archivo no los presenta como instalados ni usa el antiguo volumen del biestable como prueba de que todos los módulos caben.

## Montaje e impresión

1. Imprimir `fit-coupon.stl`: tres cavidades 6.2 / 6.4 / 6.6 de izquierda a derecha, y taladros Ø1.7 / Ø2.2 / Ø3.2 respectivamente. Sirve para elegir holguras de esa impresora y contrastar el cuerpo del switch; no verifica altura ni carrera.
2. Imprimir panel, cartucho y actuador. PETG es una propuesta inicial; boquilla 0.4, capa 0.16–0.20 y tres perímetros. El panel en la orientación CAD requiere soportes bajo los largueros USB. No escalar el conjunto para corregir un taladro: ajustar el parámetro o repasar el agujero.
3. Insertar actuador desde atrás, alojar el micro-switch por su cuerpo y atornillar cartucho. Soldar/aislar sus dos hilos; sus patas no sostienen el mecanismo. Comprobar retorno y tope antes de energizar.
4. Colocar el módulo USB sobre los cuatro apoyos y sujetar con M2 × 5. Los pilotos de plástico necesitan prueba y roscado/preparación adecuados; no forzar tornillos ni prensar componentes. Dejar acceso al cableado lateral.
5. Insertar difusores transparentes desde atrás. Para estado, alojar el LED Steren Ø5 detrás del izquierdo; retener con una pequeña cantidad de silicona neutra removible y aislar las patas. Para carga, acoplar una guía óptica desde los LEDs del PowerBoost al derecho. Los tubos separan ambas luces; longitud y acoplamiento de esa guía requieren ensayo.
6. Montar el panel sobre **la carcasa y bandeja revisadas incluidas**, sujetar los cables y comprobar inserción/extracción del USB. No intentar montarlo sin despejar las dos estructuras anteriores.

Los STL de difusores son geometría para resina translúcida o fabricación de guía óptica; imprimirlos en plástico opaco no produce un indicador útil. No hay junta ni calificación de estanqueidad en esta versión.

## Comprobación realizada y límites

Se comprueban sólidos válidos, número de sólidos, invasiones de las piezas nuevas contra las piezas y reservas permanentes A5, bolsillo del USB y movimiento nominal del botón. El informe no incluye cableado, adhesivo, disipación térmica ni comprobación de la óptica. Los tornillos de referencia simplifican rosca y cabeza.

Resultado de esta entrega: 76 sólidos válidos al reabrir el FCStd; ambos STEP se reimportan válidos, con 21 y 3 sólidos respectivamente; los ocho STL exportados son mallas cerradas. No se detectan invasiones de las piezas y tornillos nuevos contra A5 en las reservas modeladas. El SHA-256 del maestro coincide antes y después de generar y verificar.

La revisión eléctrica conserva las limitaciones explícitas del [prototipo con módulos](../../hardware/power-modules/README.md): USB_VBUS separado de SYSTEM_5V, corriente admisible del host, VBUS self-powered, ESD y pack pendiente de comprobación. El panel no resuelve esos puntos eléctricos.

## Regenerar

Ejecutar `build_panel.py` con el Python incluido en FreeCAD y después `render_panel.py` con Python, NumPy y Pillow. El primero lee A5 y `parameters.json`; el segundo usa sus triángulos para las vistas y añade colores/visibilidad al FCStd. Ambos escriben por defecto en `../integration-review/generated/`, sin sustituir el paquete original. Entre ambos ejecutar `../integration-review/audit_integration.py`. Ver [comandos completos](../integration-review/README.md). No se incluyen archivos para fabricar PCB.
