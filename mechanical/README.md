# Mecánica — revisión A5

Abrir **[A5/TresVizo-A5.FCStd](A5/TresVizo-A5.FCStd)** desde FreeCAD. Es el único archivo maestro activo: contiene todos los sólidos, colores y grupos. No necesita macros, scripts, STEP ni archivos de revisiones anteriores para abrirse.

## Estado real

A5 consolida la geometría de A4 con el símbolo TresVizo (3 + hexágono) en un documento autónomo, y añade la fijación de tres tornillos para la antena HA-901A. **Todavía no cambia el panel ni integra una nueva PCB.** El propietario pidió esperar con el botón porque otro agente está diseñando la placa de alimentación e interfaz. USB-C, botón y LEDs se coordinarán con su geometría final, evitando comprar y montar un cargador comercial adicional por adelantado.

El árbol contiene siete piezas impresas, tornillería comercial y volúmenes de referencia. Para inspeccionar el interior, ocultar `MainShell`, `ServiceCover` y `AntennaCap` con la barra espaciadora y mostrar el grupo de referencias. Son los mismos sólidos del montaje, sin documentos INTERIOR/EXPLODED duplicados. Los sólidos se pueden modificar con las herramientas de FreeCAD; no se conserva la cadena de generadores A0–A4 ni se presenta como un historial paramétrico reconstruido.

## Archivos

- `A5/TresVizo-A5.FCStd`: maestro independiente.
- `A5/PCB-INTERFACE.md`: coordenadas y restricciones para integrar la PCB.
- `A5/COMPONENT-DIMENSIONS.md`: medidas investigadas, fuentes y límites; incluye el plano localizado del BMI088 azul V1.0 y la batería 955565 confirmada por el propietario.
- `legacy/`: todos los archivos mecánicos anteriores, incluida una copia de la sesión abierta en FreeCAD. Está excluida de Git. `legacy/archive-sha256.json` registra los 228 archivos trasladados; se verificó que sus contenidos no cambiaron.

Los archivos antiguos ya versionados aparecerán como eliminaciones en la próxima revisión de Git: los originales siguen guardados localmente en `legacy`. Esta reorganización no ejecutó comandos de commit ni push, ni borró el historial.

## Validación y límites

La consolidación inicial se comprobó con 43 sólidos válidos y apertura aislada en FreeCAD 1.0.2 / Qt 5.15.15. La actualización de antena contiene **49 sólidos válidos y siete piezas impresas**: modifica únicamente `AntennaCap` y `ElectronicsTray`, y añade tres tornillos y tres arandelas comerciales. Se volvió a abrir una copia aislada y se recomputó con **FreeCAD 1.1.3 sin interfaz gráfica**; esto no certifica la estabilidad de su interfaz Qt. Se verificaron los tres pasos completos, el paso SMA, la ausencia de colisiones de la nueva tornillería y la conservación del resto de la geometría. La envolvente conservadora de antena se excluye de la comprobación de colisión porque no representa su material interior. La comprobación geométrica no sustituye una prueba de impresión o ensamble.

La batería comprada ya está identificada como 955565, 3.7 V y 5000 mAh; falta confirmar su envolvente terminada. Se encontró el plano del breakout BMI088 azul V1.0 (dos agujeros Ø3 separados 18.5), pendiente de trasladar al asiento del CAD. Siguen pendientes el patrón documentado de agujeros del carrier UM980, la referencia comercial del inserto del jalón y la prueba física del montaje de antena. Véase [el registro de dimensiones](A5/COMPONENT-DIMENSIONS.md) para distinguir cotas publicadas de reservas. La carcasa **no está liberada para fabricación ni tiene un grado IP validado**.

La PCB en preparación está documentada en [hardware/power-board](../hardware/power-board/README.md). Esa documentación pertenece al trabajo paralelo; A5 no altera su arquitectura eléctrica.

## Montaje de la antena HA-901A

La etiqueta aportada por el propietario identifica HA-901A, Ø43.5 × 40.8 mm. El [plano publicado por XYANT Wireless para ese modelo](https://www.ebay.com/itm/315222778620) muestra `3-M2.5*6` sobre Ø26.6 mm ([imagen del plano](https://i.ebayimg.com/images/g/F2sAAOSwLzJl8nTm/s-l1600.webp)). Es documentación del vendedor del producto; no se dispone de certificado del fabricante que identifique el lote comprado. La ficha mezcla otras dimensiones en su texto; se utilizó la vista inferior del plano que coincide con la etiqueta y la fotografía, no esas descripciones contradictorias.

- Tapa: tres barrenos pasantes Ø3 mm a 120°, asiento de 3 mm, paso central SMA Ø16 mm.
- Centros en mm, desde el eje del receptor: `(11.518138, 6.650)`, `(-11.518138, 6.650)`, `(0, -13.300)`; atraviesan Z165–168.
- Tornillería: tres M2.5×8 DIN 912 / ISO 4762 y arandelas Ø2.7 interior × Ø6 exterior × 0.5 mm. Penetración nominal: **4.5 mm**; no confundir la llamada de profundidad 6 con la longitud del tornillo.
- Bandeja: dos rebajes superiores R3.5 desde Z161.2 para evitar interferencias. Holgura mínima nominal con arandelas: 0.5 mm; con cabezas: 0.8 mm.

Atornillar la antena a la tapa retirada usando Allen de 2 mm; conectar el SMA por el centro y después cerrar la tapa sobre el cuerpo. Verificar que los tornillos aprieten el asiento sin alcanzar el fondo de la antena. No hay torque ni estanqueidad validados. Dimensiones de cabeza y llave: [ficha PTS M2.5×8](https://www.pts-uk.com/products/socket-screws/socket-cap-screws/metric-a2/a91202508).
