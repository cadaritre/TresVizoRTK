# Referencias para la carcasa de la v0.2

Datos de la placa v0.2 (commit `cfc44c9`) en los ejes de la carcasa V2.2, para diseñar la carcasa
nueva. Ejes: **z = eje del jalón hacia arriba, +Y hacia el panel, +X a la izquierda mirando el
panel**. Medidas en mm. La V2.2 usada es la de `main` (94f00f9): `parameters.json`,
`build_v2_2.py` y `components.json` son idénticos.

| Archivo | Qué es |
| --- | --- |
| `placement.json` | Posiciones y zonas: placa, agujeros, franjas de los rieles, antena del ESP32, botón, clavijas, carrier, 18650, panel-usb, coaxial, collares y holguras medidas |
| `placa-principal.step` | PCB y componentes (111 objetos con su referencia), ya en la carcasa. Los modelos `.step` de LCSC están corridos a la posición de sus `.wrl`, que son los que se usaron para diseñar las huellas (el STEP de `kicad-cli` los deja mal puestos) |
| `panel-usb.step` | Placa del USB-C del panel con sus componentes, en su sitio (cara del USB-C en y 31.70) |
| `clavijas.step` | Clavijas enchufadas (`Jxxx_clavija`) y reserva para doblar sus cables (`Jxxx_cables`), incluida la J502 de la panel-usb |
| `envolventes-supuestas.step` | Envolventes **sin plano**: carrier BDLX (32 × 52 × 11), su SMA acodado, la 18650, el coaxial y las cabezas M2 de la panel-usb |
| `propuesta-rieles-brazos.step` | La propuesta anterior: rieles de los cantos (z 39–90, el +X cortado en z 54–71) y salientes Ø6 detrás de H1 y H2 |
| `check_v02b.py` | Copia de la comprobación en FreeCAD (choques, clavijas, collar, rieles, brazos). Lee piezas de V2.2 en BREP que quedaron en la carpeta de trabajo de la sesión: es de referencia, no corre desde aquí |
| `check_montaje_v2_3.py` | Comprobación del **montaje paso a paso** de la carcasa V2.3 (`mechanical/v2.3`): mueve cada pieza por su recorrido y busca choques con lo que ya está puesto; también el recorrido del cable de la 18650 a J102. Escribe `montaje-v2.3/resultado.json` y cortes en `montaje-v2.3/*.png` |
| `v02_params.py` | Parámetros del primer estudio: envolventes del carrier, la 18650, el coaxial, los rieles y los brazos |

Los STEP no se guardan en git (`.gitignore`): pesan 38 MB y se rehacen con la comprobación. Cada
pieza es un solo sólido con su referencia: así FreeCAD conserva el nombre al importarla (con varios
sólidos la renombraba, p. ej. J102 salía como J107).

## Montaje de V2.3 (05-10-2026, `check_montaje_v2_3.py`)

Primera versión (`b33f44a`): tres problemas que se corrigieron en `3d227df`. La 18650 no entraba
recta en su cuna, porque los labios llegaban hasta z 81. U201 chocaba con las lengüetas +X al meter la
placa en el chasis. El cable de la 18650 no tenía salida desde el hueco de la repisa.

Versión corregida (`3d227df`; el canal del cable, en `d939377` y `647f7c9`):

| Paso | Resultado |
| --- | --- |
| 18650 a su cuna | Sin choques: baja corrida 3.2 mm hacia delante (eje en y −16.4), se empuja hacia atrás con su tope 0.4 mm bajo el collar y baja recta a la repisa entre los labios (z 26–42) |
| Carrier al chasis por el frente, sin la placa | Sin choques |
| Placa al chasis por los rieles, desde abajo | Sin choques. Desde arriba siguen chocando U201 (6.5 mm³) y J102 (0.3 mm³): hay que meterla por abajo |
| Chasis armado al tubo, con la 18650 puesta | Sin choques; queda 1.0 mm a la 18650 y la carrier a 0.4 |
| Clavijas de J102 y J404 desde abajo | Sin choques |
| Tapa del panel hacia dentro | Sin choques (solo se tocan las reservas de los dos extremos del cable J101–J502, que es el mismo cable) |
| Plataforma del IMU y tapa de antena desde arriba | Sin choques con lo de dentro. El encaje con el tubo y entre ellas (uñas, bayoneta con giro) es el de V2.2 y no se simula |
| Cable de la 18650 a J102 (Ø2.6, 65 mm) | En `3d227df` le faltaban 0.3 mm en la esquina del hueco de la repisa, sobre la arandela del retén de la tuerca. En `d939377` el techo del canal sube a z 20.2 en x −7…−3 y el recorrido queda libre; en `647f7c9` el canal arranca en el eje del hueco (y −19.6) y el rebaje llega al frente de la repisa (y −14.6). Recorrido **libre**, con holguras mínimas de 0.155 mm al borde del rebaje (x −7, z 19.0), 0.18 al retén, 0.18 al tubo por fuera del riel −X y 0.18 al riel −X |

Los cortes `corte_z*.png` (horizontales, vista desde arriba) y `corte_x*.png` (verticales) muestran
el fondo con el cable propuesto en magenta.

## Lo que hay que respetar

- **Collar Ø52 (r 26)**, abajo en z 8–21 y arriba en z 111.91–124.91; el cuello empieza en z 99.41.
  Todo lo que entra por arriba pasa por r 26. Hoy llegan a r 23.21 la placa, a 23.17 J102 y a 23.22
  el carrier.
- **Sándwich sin aire**: placa ↔ carrier 0.4 mm y carrier ↔ 18650 0.4 mm. El carrier solo se puede
  sujetar por sus cantos (x −21 y +11) y sus extremos (z 16.4 y 68.4).
- **Antena del ESP32** en el canto +X, x 16.8–23, z 54.2–70.2: nada de plástico al lado en z 54–71.
- **Franjas para rieles**: 2.5 mm sin componentes en cada canto lateral (x ±20.5…±23), de z 39 a 87.5.
- **Agujeros**: H1 (x 11.0, z 75.3) y H2 (x −17.4, z 83.8), M2.5 sin metalizar de Ø2.7, sin cobre
  en Ø5.2. Los dos quedan por encima del carrier, que llega a z 68.4.
- **Bajo el canto inferior** (z 15.91–23.5) están las clavijas y los cables de J102, J404 y J301, y
  la entrada de la microSD (J401). La base está en z 15.91. Ranura propuesta en la base bajo J102:
  x −21.5…−13.5, y 2.5…8.5, 3 mm de hondo.
- **Sobre el canto superior** (z 87.5–99.9) están las clavijas que suben de J405, J101 y J406, el
  cable J101↔J502, la panel-usb (z 90.17–91.77) y el coaxial.
- **Botón**: nada delante en x ±5.5, z 38–49; como mucho 2 mm de alto en x ±8.1, z 35.4–51.6.

## Sin verificar

- Espesor real del carrier y dónde quedan sus conectores (sin plano): si están en la cara de
  componentes, de cara a la placa, no se pueden enchufar.
- El cable real de la 18650: se modeló como un haz de Ø2.6 que sale por el extremo de abajo de la
  celda. Hay que confirmar su calibre, por dónde sale y que mida al menos unos 80 mm hasta la clavija.
- El asomo de la clavija PH de la batería (3.5 mm estimado).
- Tolerancias de impresión.
