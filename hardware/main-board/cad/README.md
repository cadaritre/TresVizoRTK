# Referencias para la carcasa

Datos de la placa v0.2 (ESP32-S3-WROOM-1 y J301 SH 8) en los ejes de la carcasa, para diseñar y
comprobar la carcasa V2.3 (`mechanical/v2.3`). Ejes: **z = eje del jalón hacia arriba, +Y hacia el
panel, +X a la izquierda mirando el panel**. Medidas en mm.

Los STEP tienen la placa con el dorso en y 1.5, como en el primer estudio sobre V2.2. En V2.3 la placa
va `chasis.desplazamiento_placa_y` (1.0 mm) más hacia el panel, y las comprobaciones la mueven.

| Archivo | Qué es |
| --- | --- |
| `placement.json` | Placa (agujeros, franjas de los rieles, antena del ESP32, botón, clavijas), panel-usb y carrier medida. Lo del primer estudio en V2.2 (18650, coaxial, collares y holguras) va marcado |
| `placa-principal.step` | PCB y componentes (106 objetos con su referencia), ya en la carcasa. Los modelos `.step` de LCSC están corridos a la posición de sus `.wrl`, que son los que se usaron para diseñar las huellas. El STEP de `kicad-cli` deja algunos mal puestos: el GH 8 de J101, 3.9 mm hundido; el SH 8 de J301, 3.5 mm de lado |
| `panel-usb.step` | Placa del USB-C del panel con sus componentes, en su sitio (cara del USB-C en y 31.70) |
| `clavijas.step` | Clavijas enchufadas (`Jxxx_clavija`) y reserva para doblar sus cables (`Jxxx_cables`), incluida la J502 de la panel-usb |
| `envolventes-supuestas.step` | Envolventes del primer estudio, **sin plano**: carrier de 32 × 52 × 11, su SMA acodado, la 18650, el coaxial y las cabezas M2 de la panel-usb. V2.3 ya no las usa: tiene su carrier medida y `carrier_bdlx.py` |
| `propuesta-rieles-brazos.step` | La propuesta anterior a V2.3: rieles de los cantos (z 39–90, el +X cortado en z 54–71) y salientes Ø6 detrás de H1 y H2 |
| `carrier_bdlx.py` | Carrier BDLX aproximada **con sus componentes**, de una foto rectificada (±1 mm). No tiene margen en los cantos: su USB-C sobresale ~0.9 mm de uno y la columna de agujeros donde se suelda el arnés de J301 está pegada al otro |
| `check_v02b.py` | Copia de la comprobación en FreeCAD que genera estos STEP (choques, clavijas, collar, rieles, brazos). Lee piezas de V2.2 en BREP que quedaron en la carpeta de trabajo de la sesión: es de referencia, no corre desde aquí |
| `check_montaje_v2_3.py` | Comprobación del **montaje paso a paso** de V2.3: mueve cada pieza por su recorrido y busca choques con lo que ya está puesto; también el recorrido del cable de la 18650 a J102. Mueve la placa y sus clavijas `desplazamiento_placa_y` y prueba la carrier dos veces: la envolvente medida de V2.3 y `carrier_bdlx.py`. Escribe `montaje-v2.3/resultado.json` y cortes en `montaje-v2.3/*.png` |
| `v02_params.py` | Parámetros del primer estudio: envolventes del carrier, la 18650, el coaxial, los rieles y los brazos |

Los STEP no se guardan en git (`.gitignore`): pesan 37 MB y se rehacen con la comprobación. Cada
pieza es un solo sólido con su referencia: así FreeCAD conserva el nombre al importarla (con varios
sólidos la renombraba, p. ej. J102 salía como J107).

## Montaje de V2.3

### 06-10-2026: placa con el WROOM y J301 SH 8, carcasa de `b94647d`

| Paso | Resultado |
| --- | --- |
| 18650 a su cuna | Sin choques en los tres tramos (baja corrida hacia delante, se empuja atrás, baja a la repisa) |
| Carrier al chasis por el frente, sin la placa | Sin choques, con la envolvente medida y con sus componentes. Holguras con los componentes: USB-C 1.40 al rebaje del muro +X, placa del UM980 0.86, pasivos del canto −X 0.90, cables del arnés por delante 0.40, pila de botón 1.20, conector de 8 pines 1.40; las soldaduras del arnés tocan solo la arista que guía el canto del PCB, sin volumen |
| Placa al chasis por los rieles, desde abajo | Sin choques (PCB y componentes) |
| Placa desde arriba | Chocan U201 (12.1 mm³) y J102 (0.3 mm³): **se mete por abajo** |
| Chasis armado al tubo, con la 18650 puesta | Sin choques; radio máximo del conjunto 25.5; carrier a 2.6 del tubo, y las patas del SMA a 0.32 de la 18650 |
| Clavijas de J102 y J404 desde abajo | Sin choques |
| Tapa del panel hacia dentro | Solo se tocan las reservas de los dos extremos del cable J101–J502, que son el mismo cable |
| Plataforma del IMU | Sin choques |
| Tapa de antena bajando recta | Toca la plataforma: en la realidad entra girando con la bayoneta, que no se simula |
| Cable de la 18650 a J102 (Ø2.6, 66.4 mm) | **Libre**, con holguras mínimas de 0.17 al tubo, 0.18 al retén de la tuerca, 0.20 al chasis y 0.34 a J102. El tramo que rodea el riel −X va 1 mm más adelante que en el estudio anterior, igual que la placa |

Antes del arreglo de `b94647d`, `carrier_bdlx.py` encontró dos choques que la envolvente de caja no
veía:

- El USB-C de la carrier contra el muro de la ranura +X: 21.7 mm³, y no entraba por el frente.
- Las soldaduras del arnés de J301 contra el labio −X, a 0.2 mm detrás del PCB: 10.2 mm³.

### 05-10-2026 (placa con el ESP32-S3-MINI-1)

- Primera versión (`b33f44a`): tres problemas, corregidos en `3d227df`.
  - La 18650 no entraba recta en su cuna.
  - U201 chocaba con las lengüetas +X al meter la placa.
  - El cable de la 18650 no tenía salida desde el hueco de la repisa.
- `d939377` y `647f7c9` abrieron el canal del cable.
- Todos los pasos quedaron sin choques, con la carrier supuesta de 11 mm.

Los cortes `corte_z*.png` (horizontales, vista desde arriba) y `corte_x*.png` (verticales) muestran
el fondo con el cable propuesto en magenta.

## Lo que hay que respetar

- **Collar Ø52 (r 26)**, abajo en z 8–21 y arriba en z 111.91–124.91; el cuello empieza en z 99.41.
  - Todo lo que entra por arriba pasa por r 26.
  - Hoy la placa llega a r 23.21 y J102 a r 23.17; el chasis armado, a r 25.5.
- **Carrier sin margen en los cantos**: las ranuras del chasis no pueden pegarse a ellos delante de
  la cara ni detrás del PCB donde hay soldaduras (ver `carrier_bdlx.py`). Patas del SMA sin cortar:
  asoman hasta 3 mm por detrás.
- **Antena del ESP32-S3-WROOM-1** en el canto +X, x 16.3–23, z 53.8–71.8: sin cobre en la placa y sin
  plástico al lado.
- **Franjas sin componentes** en los cantos, 2.5 mm (áreas `riel_*` del DRC):
  - +X en z 72.4–87.5 y 39–53.5;
  - −X en z 39–87.5.
  - Las lengüetas de V2.3 pisan solo +X en z 72.4–87.5 y −X en z 39–87.5.
- **Agujeros**: H1 (x 11.0, z 77.9) y H2 (x −17.4, z 83.8), M2.5 sin metalizar de Ø2.7, sin cobre
  en Ø5.2.
- **Bajo el canto inferior** (z 15.91–23.5) están las clavijas y los cables de J102, J404 y J301, y
  la entrada de la microSD (J401). La base está en z 15.91.
- **Sobre el canto superior** (z 87.5–99.9) están las clavijas que suben de J405 y J101, el cable
  J101↔J502, la panel-usb (z 90.17–91.77) y el coaxial.
- **Botón**: nada delante en x ±5.5, z 38–49; como mucho 2 mm de alto en x ±8.1, z 35.4–51.6.

## Sin verificar

- La carrier real. Sus medidas salen de una foto con cinta métrica, sin calibrador (±1 mm). V2.3 le
  deja 1 mm de más en el grueso, pero no en los cantos: el rebaje del USB-C deja 1.4 mm y lo más
  justo queda a 0.4 mm (los cables del arnés).
- El cable real de la 18650: se modeló como un haz de Ø2.6 que sale por el extremo de abajo de la
  celda. Hay que confirmar su calibre, por dónde sale y que mida al menos unos 70 mm hasta la clavija.
- El asomo de la clavija PH de la batería (3.5 mm estimado).
- Tolerancias de impresión.
