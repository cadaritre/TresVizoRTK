# A2 — entrada y recorrido del coaxial

**Revisión actual: [A3 — montaje inferior imprimible](README-A3.md).** Conserva este paso coaxial y elimina las piezas metálicas a medida de A1/A2.

Corrección localizada sobre A1. **A1 ya tenía agujeros Ø14 y Ø12 en el soporte**, ocultos por el cilindro que representa la antena. No tenía un recorrido definido hasta la carrier: bajar por el centro interfería con la zona de la IMU.

## Cambios

- Entrada superior **Ø16** centrada bajo la antena. Es una elección de diseño; hay que verificar paso y acceso del conector adquirido.
- Salida lateral abierta de **8 mm** en la plataforma inferior del soporte. Permite colocar el cable durante el montaje sin enhebrarlo por un segundo agujero pequeño.
- Escotadura de **8 mm** en el anillo del bastidor próximo a la IMU. Se conserva la plataforma de la IMU sin atravesarla.
- Ruta reservada **Ø5**, situada por el costado trasero derecho (X positivo, Y negativo), después bajo el apoyo de batería y hasta la zona inferior de conexión del UM980. Longitud de línea central **207.276 mm**. No es una longitud de compra: faltan los conectores y holgura de montaje.

El recorrido combina arcos tangentes de radios 10 y 12 mm y tramos rectos. Como referencia de cable fino, el [RG_178_B/U de HUBER+SUHNER, ficha del fabricante alojada por Mouser](https://www.mouser.com/datasheet/3/1498/1/H_S_RG_178_BU_EN.PDF) tiene cubierta Ø1.8 ±0.1 y radio estático mínimo 10. **No se ha identificado el coaxial comprado ni se debe aplicar ese límite a cualquier RG178 o a otro cable.** Las curvas propuestas son para montaje fijo, no flexión repetida.

La ruta termina en X=0, Y=20.087, Z=40, antes de la reserva de carrier. Los conectores SMA, su género, longitud, zona rígida y punto exacto de conexión siguen pendientes. No hay una conexión eléctrica certificada ni se ha modelado un conector ficticio. El patrón de tres tornillos de la antena también permanece pendiente. Se requiere fijación y alivio de tensión del cable; la escotadura por sí sola no lo sujeta. Resolver junta/pasacables al conocer el conector: el agujero no implica estanqueidad.

## Archivos y revisión

- `TresVizo-case-A2.FCStd`: conjunto principal corregido. Conserva el montaje metálico A1 y sus limitaciones.
- `TresVizo-case-A2-CABLE-ROUTE.FCStd`: vista interior de revisión con el volumen reservado del coaxial, objeto `CoaxRouteReserve`. La carcasa y la antena se omiten de esta vista para exponer el agujero. No imprimir los bloques electrónicos ni el recorrido azul.
- `../exports/review-a2/coax-route-a2.png`: vista general y detalles del agujero y de la escotadura junto a IMU.
- `../exports/review-a2/`: STEP del conjunto y plásticos; STL de prototipo; STEP de la reserva de cable expresamente marcado no imprimible.

Para ver el agujero en el conjunto principal, ocultar `HA901Reserve` y observar `AntennaSupport` desde arriba. El cilindro de reserva no representa los detalles del cuerpo real de la antena y no se perforó artificialmente.

Se verificaron 52 sólidos válidos, sus intersecciones por parejas y el recorrido Ø5 contra todos ellos: no hay intersecciones mayores a 0.02 mm³. Una galga cilíndrica Ø15.9 atraviesa el soporte axialmente entre Z=147 y Z=169 sin intersección. Las mallas de plástico son cerradas. Se reabrieron FCStd y STEP y ambos conservan 52 sólidos válidos. No se ha ensayado montaje del cable real, conectores, acceso de herramientas, estanqueidad o RF.

Regenerar desde la raíz del repositorio usando el Python incluido en FreeCAD:

```sh
PYTHONPATH=/Applications/FreeCAD.app/Contents/Resources/lib \
  /Applications/FreeCAD.app/Contents/Resources/bin/python mechanical/cad/build_case_a2.py
PYTHONPATH=/Applications/FreeCAD.app/Contents/Resources/lib \
  /Applications/FreeCAD.app/Contents/Resources/bin/python mechanical/cad/render_case_a2.py
```

El generador conserva A1 y utiliza sus utilidades y archivo como origen. La presentación principal se conserva por nombres de objetos. La vista de recorrido reutiliza los estilos nativos y asigna al cable el material azul de referencia. La lámina PNG no depende de la interfaz gráfica.
