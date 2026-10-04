# Tornilleria de V2.2

Generado por `bom.py` desde `parameters.json` (lo ejecuta `regenerate.py`). Las longitudes salen de
la geometria del modelo, no de una estimacion: se mide desde el asiento
de la cabeza hasta el fondo del barreno y se elige la medida comercial que cabe.

**Nada de esto se ha montado ni ensayado.**

## Carcasa

| Pieza | Largo | Cant. | Donde | Calculo |
| --- | ---: | ---: | --- | --- |
| M3 cabeza boton ISO 7380 | 10 mm | **1** | Seguro de la base. Rosca en el macizo de la base. | piloto util 10.5 mm; rosca 5.4 mm |
| M3 cabeza boton ISO 7380 | 12 mm | **1** | Seguro de la tapa. Rosca en el refuerzo del cuello. | piloto util 12.5 mm; rosca 7.4 mm |
| M3 cabeza boton ISO 7380 | 4 mm | **2** | Tapa del panel principal. Rosca en el engrosamiento. | rosca 3.1 mm; la punta no sale del engrosamiento |
| M2.5 cilindrica ISO 4762 | 10 mm | **3** | Antena. Sube desde dentro y rosca en la antena. | tapa 5 + 5 de 6 de rosca en la antena |
| M2.5 cabeza avellanada ISO 10642 o DIN 965 | 6 mm | **2** | BMI088 sobre la plataforma. Rosca en el separador. | cabeza 1.0 sobre la placa + PCB 1.6 + piloto 4.0 |
| M2 cilindrica ISO 4762 o cabeza plana | 4 mm | **4** | Pantalla OLED contra su marco. Rosca en el marco. | PCB 1.6 + piloto 3.0 |
| Tuerca M12x0.75 del boton | — | **1** | Viene con el boton. Asienta en el plano interior de la tapa. | panel de 3.4 mm en el eje del boton |
| M3 cabeza boton ISO 7380 | 8 mm | **2** | Detienen la tuerca del jalon por arriba, con arandela ancha. | arandela 0.8 + rosca 7.2 mm en un piloto de 8.5 |
| Arandela plana ancha M3 DIN 9021 (9 x 0.8) | — | **2** | Bajo los dos M3: pisan 1.4 mm de la tuerca. | la de 7 mm (DIN 125) pisa menos de 1 mm |
| Tuerca hexagonal 5/8-11 UNC de laton | — | **1** | Rosca del jalon. Entra por dentro de la base, en su hexagono. | estandar: 15/16 in entre caras, 35/64 in de alto; hueco de 24.1 entre caras |

**15 tornillos con longitud definida.** Ninguno lleva tuerca: todos roscan en el plastico o en la antena. La unica tuerca es la del jalon.

## Conector de carga

| Pieza | Cant. | Donde |
| --- | ---: | --- |
| Header JST-XH de 2 pines, vertical, B2B-XH-A (o clon "XH 2.54 2P macho recto") | 1 | Panel, a ras, en su bolsillo de 7.7 x 6.0. Cables soldados a sus patas. |
| Carcasa XHP-2 con 2 terminales SXH, o un cable XH de 2 pines ya armado | 1 | Del lado del cargador. |

JST lo vende como conector de placa, no para conectar y desconectar a diario.

## Lo de dentro

Nada de lo de dentro se atornilla: la 18650 va detras del respaldo y el
carrier UM980 y la Thing Plus delante, amarrados con bridas; lo demas,
al respaldo o a los cuatro toalleros. Varias de esas placas no tienen
patron de agujeros publicado.

## Advertencias

- Tornillos del panel: NO poner uno mas largo que el de la lista. El de arriba queda a menos de 1 mm del cuello de la tapa, que gira al cerrar la bayoneta: si asoma, la tapa no cierra.
- Los tres tornillos de la antena van ANTES que la plataforma del IMU: sus cabezas quedan dentro del cuello de la tapa.
- Los dos M2.5 del IMU tienen que ser de cabeza AVELLANADA: el cono asienta en el canto del agujero de 3.0 y centra la placa sobre el piloto. Con cabeza cilindrica quedan 0.25 mm de juego por lado y el chip ya no cae en el eje. Sin tuercas ni arandelas.
- Los agujeros de la pantalla son de 2.0 segun el plano del vendedor y el M2 entra justo. Si no pasa, repasar el agujero con broca de 2.2 o usar M1.6x4.
- La tuerca del boton queda a unos 10 mm del marco de la pantalla: apretarla con pinzas o con una llave de 14 delgada, antes de montar la pantalla.
- Tuerca del jalon: hexagonal ESTANDAR de 5/8-11 UNC (5/8 NC, 11 hilos), de laton. No sirve la pesada (1-1/16 in entre caras, no entra), ni la de rosca fina 5/8-18, ni una de seguridad con nylon. Medirla al comprarla: hasta 24.0 entre caras y 13.9 de alto entra en el hueco tal cual. Va con el tubo quitado: se mete por dentro de la base hasta el anillo y se ponen los dos M3 con su arandela.

## Consumibles

| Consumible | Cantidad | Uso |
| --- | ---: | --- |
| Brida de 2.5 a 3.6 mm, 150-200 mm | 10-15 | Placas y 18650 al respaldo |
| Epoxico de 5 minutos | unas gotas | Header JST-XH en su bolsillo, por dentro |
| Termofit de 2.5 mm | 5 cm | Patas del header JST soldadas a sus cables |
| Brida de 2.5 mm, 100-150 mm | 4-8 | Componentes extra en los toalleros |
| Lamina transparente de 1 mm (acrilico o PETG), 26.7 x 19.3 | 1 | Mica de la pantalla |
| Filamento TPU 95A | ~25 g | Las dos bandas de proteccion |
| Cinta de espuma o fieltro adhesivo | 1 tira | Entre la 18650 y el respaldo |
| Llave Allen 2 mm | 1 | M3 cabeza boton y M2.5 cilindrica de la antena |
| Llave Allen 1.5 mm o desarmador Phillips 0 | 1 | M2 de la pantalla y M2.5 avellanado del IMU |
| Llave de 14 mm o pinzas | 1 | Tuerca del boton |
