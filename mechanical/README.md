# Diseño mecánico

El concepto inicial es una carcasa cilíndrica impresa en 3D para un receptor montado sobre jalón. Todavía no existen dimensiones ni modelos CAD validados.

## Criterios previstos

- Mantener la antena y el montaje del jalón alineados mecánicamente.
- Montar la IMU rígidamente y cerca del eje del jalón.
- Incorporar una referencia física inequívoca de “frente” en la carcasa.
- Permitir acceso a carga, desarrollo, diagnóstico y extracción o mantenimiento de la microSD según el diseño electrónico definitivo.
- Proteger cableado y conectores sin imponer radios de curvatura o esfuerzos no permitidos.
- Considerar ventilación, disipación, sellado y mantenimiento después de conocer el consumo y los componentes reales.
- Omitir un botón dedicado para medir; la operación de medición se realizará desde la aplicación.

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

- `cad/`: futuros archivos fuente del modelo mecánico.
- `exports/`: exportaciones deliberadamente versionadas para fabricación o revisión.

No debe añadirse geometría ficticia para completar estos directorios.

