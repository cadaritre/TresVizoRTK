# Tornilleria de V2.1

Generado por `bom.py` desde `parameters.json` (lo ejecuta `regenerate.py`). Las longitudes salen de
la geometria del modelo, no de una estimacion: se mide desde el asiento
de la cabeza hasta el fondo del barreno y se redondea a medida comercial.

**Nada de esto se ha montado ni ensayado.**

## Carcasa

| Pieza | Largo | Cant. | Donde | Calculo |
| --- | ---: | ---: | --- | --- |
| M3 cabeza boton ISO 7380 | 12 mm | **1** | Seguro de la base. Rosca en el macizo de la base. | piloto util 13.2 mm; rosca 7.4 mm |
| M3 cabeza boton ISO 7380 | 12 mm | **1** | Seguro de la tapa. Rosca en el refuerzo del cuello de la tapa. | piloto util 12.5 mm; rosca 7.4 mm |
| M3 cabeza boton ISO 7380 | 10 mm | **2** | Pie del trineo contra el piso de la base. Rosca en la base. | pie 3 + piloto 9; no pasar de 12 |
| M3 cabeza boton ISO 7380 | 6 mm | **2** | Tapa del panel principal. Rosca en el engrosamiento. | rosca 3.3 mm; carrier UM980 detras: nunca mas largo |
| M3 cabeza boton ISO 7380 | 4 mm | **2** | Tapa del panel auxiliar. Rosca en el engrosamiento. | rosca 3.1 mm; bateria detras: nunca mas largo |
| M2.5 cilindrica ISO 4762 | 10 mm | **3** | Antena. Sube desde dentro y rosca en la antena. | tapa 5 + 5 de 6 de rosca en la antena |
| M2 cilindrica ISO 4762 | 10 mm | **2** | BMI088 sobre la repisa del trineo. | PCB 1.6 + separador 2.5 + repisa 3.0 + tuerca |
| Tuerca M2 DIN 934 | — | **2** | BMI088. Obligatoria: los agujeros son ranurados. | una ranura no puede sujetar una rosca |
| Arandela M2 | — | **2** | BMI088. Reparte el apriete sobre el agujero de 3.0 del PCB. | M2 en un agujero de 3.0 deja holgura |
| M4 formando rosca, o M3 con tuerca | — | **2** | Barrenos de accesorios, 3.3 mm pasantes. | a discrecion segun lo que montes |
| McMaster 90611A121 | — | **1** | Rosca 5/8-11 UNC hembra del jalon. | capturado entre base y tubo; sin tornillos |

**13 tornillos con longitud definida y 2 tuercas.** El resto queda a criterio al accesorizar.

## Tornilleria de las placas interiores

El diseno **no necesita tornillos para las placas**: la rejilla del
trineo las sujeta con brida contra un plano de apoyo. Esto es
deliberado, porque el repositorio declara no conocer el patron de
agujeros de varias de ellas.

Si aun asi quieres atornillar alguna, esto es lo que admite cada una
segun su ficha. **Confirmar midiendo la placa real antes de comprar.**

| Placa | Metrica | Patron | Confianza del dato |
| --- | --- | --- | --- |
| Breakout BMI088 V1.0 azul | M2.5 | dos agujeros de 3.0, separacion 18.5 | publicado |
| Lector microSD azul con regulador | M2 | 38 x 20 segun la familia | familia |
| Adaptador USB Waveshare | M2 | 14 x 14 | publicado |
| Waveshare ESP32-S3-Tiny | — | sus pads no son agujeros de montaje | publicado |
| BDLX RTK_UM98_V1.0.1 | — | cuatro agujeros sin cotas publicadas | publicado |
| Adafruit PowerBoost 1000C sin USB-A | M2.5 | sin plano acotado localizado | publicado |
| SparkFun Soft Power Switch Mk2 | M2.5 | sin plano acotado localizado | publicado |

Solo el BMI088 tiene plano publicado, y por eso es el unico que el
modelo atornilla. Para el resto, atornillar a un patron supuesto es
exactamente el error que se corrigio de V1.

Si decides atornillar alguna, lo necesario seria:

| Consumible | Uso previsto |
| --- | --- |
| M2 x 6 cilindrica + tuerca M2 | microSD y Tiny-Adapter, cuatro por placa |
| M2.5 x 6 cilindrica + tuerca M2.5 | PowerBoost y Soft Power Switch |
| Separadores nylon M2 y M2.5, 3 a 5 mm | separar la placa del plano de apoyo |

Las tuercas son necesarias porque el trineo no lleva torres roscadas:
su cara es plana a proposito, para que sirva con cualquier placa.

## Advertencias

- Los dos tornillos del pie del trineo van ANTES que las placas: quedan debajo de ellas. Son los que quitan el juego que tenian las dos pestanas de V2; apretarlos con el trineo asentado en sus cuatro ranuras.
- Tornillos de los paneles: NO poner uno mas largo que el de la lista. Detras del panel auxiliar esta el canto de la bateria a menos de 1 mm del engrosamiento, y un M3x8 ya la pincharia.
- Los M2.5 de la antena los impone la ANTENA, no el diseno: la HA-901A trae tres roscas de esa metrica en su base. Es la unica pieza del equipo que no usa M3 o M2. Si la antena que llega usa otra, se cambian dos parametros y se reimprime SOLO la tapa.
- La profundidad de las roscas de la antena se supone 6 mm, de la referencia 3-M2.5x6. Medirla antes de comprar: un tornillo largo de mas toca fondo y no aprieta.
- El IMU es el unico punto donde la tuerca no es opcional. Sus agujeros son ranuras de +-1.5 mm para poder centrar el sensor, y una ranura no da rosca.
- El IMU usa M2 y no M2.5 porque se consigue en cualquier kit de hobby. M3 no pasa: los agujeros del BMI088 son de 3.0 y no dejan holgura.
- Los barrenos de accesorios son pasantes de 3.3 mm y sin refuerzo interior. Sirven como piloto de M4 formando rosca en los 2.5 mm de pared, o como paso holgado de M3 con tuerca y arandela por dentro. Para colgar peso, la tuerca es lo sensato.

## Consumibles

| Consumible | Cantidad | Uso |
| --- | ---: | --- |
| Brida de 2.5 mm, 100-150 mm | 6-10 | Sujecion de placas y bateria en la rejilla |
| Lamina aislante fina | segun placas | Entre placa y plano de apoyo |
| Llave Allen 2 mm | 1 | M3 cabeza boton |
| Llave Allen 2 mm | 1 | M2.5 cilindrica |
| Llave Allen 1.5 mm | 1 | M2 cilindrica del IMU |
