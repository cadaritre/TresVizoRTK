# Diseño mecánico

Revisión actual: [A3 — base imprimible para el jalón](cad/README-A3.md). Sustituye el montaje de placas metálicas por una base con alojamiento hexagonal, tapa y calce impresos. Sólo requiere tornillería comercial. Conserva la entrada bajo la antena y el recorrido coaxial A2.

El concepto es una carcasa cilíndrica impresa en 3D, inspirada en el Reach RX, para un receptor montado sobre jalón. A3 retiene una tuerca comercial 5/8-11 y deja la HA-901A arriba con su envolvente original. Las [fuentes iniciales](research/component-dimensions.md) se complementan con las referencias de cada revisión. A0/A1/A2 se conservan como historial; sus montajes anteriores no son la propuesta actual. Todavía no es un modelo validado para fabricar y montar el receptor completo.

## Criterios previstos

- Fabricar todas las piezas estructurales adicionales por impresión 3D; sólo tornillos, tuercas y arandelas comerciales de metal. No exigir placas ni casquillos metálicos a medida.
- Mantener la antena y el montaje del jalón alineados mecánicamente.
- Montar la IMU rígidamente y cerca del eje del jalón.
- Incorporar una referencia física inequívoca de “frente” en la carcasa.
- Permitir acceso a carga, desarrollo, diagnóstico y extracción o mantenimiento de la microSD según el diseño electrónico definitivo.
- Proteger cableado y conectores sin imponer radios de curvatura o esfuerzos no permitidos.
- Considerar ventilación, disipación, sellado y mantenimiento después de conocer el consumo y los componentes reales.
- Omitir un botón dedicado para medir; la operación de medición se realizará desde la aplicación.
- Integrar el encendido exterior cuando se defina pulsador y alimentación. La reserva del módulo biestable no equivale a un botón funcional; sigue pendiente.

## Referencias y mediciones necesarias

Antes de modelar la carcasa deben medirse o documentarse:

- Dimensiones, revisiones, masas y zonas de exclusión de cada placa y de la batería.
- Posición del centro de fase o referencia aplicable de la antena según su documentación.
- Distancia y orientación entre la referencia de la antena, el origen de la IMU y el eje del jalón.
- Orientación de los ejes de la IMU respecto del frente físico y del sistema de coordenadas del instrumento.
- Altura de antena y punto al que se referirán las coordenadas reportadas.
- Interfaz mecánica con el jalón, tolerancias, holguras y repetibilidad del montaje.
- Acceso real a conectores, indicadores y elementos de mantenimiento.

La calibración de offsets mecánicos y la inicialización dinámica de una solución GNSS/IMU son problemas distintos y deberán validarse por separado.

## Directorios

- `cad/`: revisiones A0–A3, generadores y parámetros del estudio mecánico.
- `exports/`: exportaciones deliberadamente versionadas para fabricación o revisión.

No debe añadirse geometría ficticia para completar estos directorios.
