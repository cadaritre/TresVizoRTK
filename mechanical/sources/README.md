# Fuentes necesarias de V1

Esta carpeta contiene las entradas que utiliza el generador de [V1](../v1/README.md):

- `a5/TresVizo-A5.FCStd`: geometría original de partida, conservada byte a byte.
- `a5/print/07-plantilla-centrado.stl`: plantilla de referencia que reutiliza la exportación V1.
- `a5/IMU-ALIGNMENT.md`, `COMPONENT-DIMENSIONS.md` y `sources/`: referencias de datum y componentes; el montaje final manda en V1.
- `panel/build_panel.py` y `panel/parameters.json`: etapa base del generador, todavía utilizada.

Para fabricar, usar únicamente [v1/generated](../v1/generated/).

`panel/build_panel.py` escribe resultados intermedios en `.cache/mechanical-v1/baseline/`, fuera de las entregas. `zsh mechanical/v1/regenerate.sh` recrea esa caché cuando hace falta y ejecuta el flujo completo con FreeCAD 1.0.2.
