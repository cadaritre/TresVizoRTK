# Mecánica — revisión A5

Abrir **[A5/TresVizo-A5.FCStd](A5/TresVizo-A5.FCStd)** desde FreeCAD 1.0.2. Es el único archivo maestro activo: contiene todos los sólidos, colores y grupos. No necesita macros, scripts, STEP ni archivos de revisiones anteriores para abrirse.

## Estado real

A5 consolida la geometría de A4 con el símbolo TresVizo (3 + hexágono) en un documento autónomo. **Esta entrega organiza y consolida; todavía no cambia el panel ni integra una nueva PCB.** El propietario pidió esperar con el botón porque otro agente está diseñando la placa de alimentación e interfaz. USB-C, botón y LEDs se coordinarán con su geometría final, evitando comprar y montar un cargador comercial adicional por adelantado.

El árbol contiene siete piezas impresas, tornillería comercial y volúmenes de referencia. Para inspeccionar el interior, ocultar `MainShell`, `ServiceCover` y `AntennaCap` con la barra espaciadora y mostrar el grupo de referencias. Son los mismos sólidos del montaje, sin documentos INTERIOR/EXPLODED duplicados. Los sólidos se pueden modificar con las herramientas de FreeCAD; no se conserva la cadena de generadores A0–A4 ni se presenta como un historial paramétrico reconstruido.

## Archivos

- `A5/TresVizo-A5.FCStd`: maestro independiente.
- `A5/PCB-INTERFACE.md`: coordenadas y restricciones para integrar la PCB.
- `legacy/`: todos los archivos mecánicos anteriores, incluida una copia de la sesión abierta en FreeCAD. Está excluida de Git. `legacy/archive-sha256.json` registra los 228 archivos trasladados; se verificó que sus contenidos no cambiaron.

Los archivos antiguos ya versionados aparecerán como eliminaciones en la próxima revisión de Git: los originales siguen guardados localmente en `legacy`. No se hizo commit, push ni se borró el historial.

## Validación y límites

Se comprobó que los 43 objetos sólidos del archivo tienen geometría válida, que las siete piezas estructurales conservan exactamente el volumen de su origen y que el archivo vuelve a abrir sin vínculos externos. El resultado de comprobación queda dentro del documento, en `VerificacionGeometrica`. La comprobación geométrica no sustituye una prueba de impresión o ensamble.

Continúan pendientes de cerrar la batería concreta, el patrón real del breakout BMI088, la fijación de la antena y el inserto comercial del jalón. Las reservas se identifican como tales en el árbol. La carcasa **no está liberada para fabricación ni tiene un grado IP validado**.

La PCB en preparación está documentada en [hardware/power-board](../hardware/power-board/README.md). Esa documentación pertenece al trabajo paralelo; A5 no altera su arquitectura eléctrica.
