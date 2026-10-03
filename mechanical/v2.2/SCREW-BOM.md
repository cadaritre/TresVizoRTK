# Tornilleria de V2.2

Generado por `bom.py` desde `parameters.json` (lo ejecuta `regenerate.py`). Las longitudes salen de
la geometria del modelo, no de una estimacion: se mide desde el asiento
de la cabeza hasta el fondo del barreno y se elige la medida comercial que cabe.

**Nada de esto se ha montado ni ensayado.**

## Carcasa

| Pieza | Largo | Cant. | Donde | Calculo |
| --- | ---: | ---: | --- | --- |
| M3 cabeza boton ISO 7380 | 12 mm | **1** | Seguro de la base. Rosca en el macizo de la base. | piloto util 13.2 mm; rosca 7.4 mm |
| M3 cabeza boton ISO 7380 | 12 mm | **1** | Seguro de la tapa. Rosca en el refuerzo del cuello. | piloto util 12.5 mm; rosca 7.4 mm |
| M3 cabeza boton ISO 7380 | 4 mm | **2** | Tapa del panel principal. Rosca en el engrosamiento. | rosca 3.1 mm; la punta no sale del engrosamiento |
| M3 cabeza boton ISO 7380 | 4 mm | **2** | Tapa del panel auxiliar. Rosca en el engrosamiento. | rosca 3.1 mm; la punta no sale del engrosamiento |
| M2.5 cilindrica ISO 4762 | 10 mm | **3** | Antena. Sube desde dentro y rosca en la antena. | tapa 5 + 5 de 6 de rosca en la antena |
| M2.5 cabeza avellanada ISO 10642 o DIN 965 | 6 mm | **2** | BMI088 sobre la plataforma. Rosca en el separador. | cabeza 1.0 sobre la placa + PCB 1.6 + piloto 5.0 |
| M2 cilindrica ISO 4762 o cabeza plana | 4 mm | **4** | Pantalla OLED contra su marco. Rosca en el marco. | PCB 1.6 + piloto 3.0 |
| Tuerca M12x0.75 del boton | — | **1** | Viene con el boton. Asienta en el plano interior de la tapa. | panel de 4.0 mm en el eje del boton |
| M4 formando rosca, o M3 con tuerca | — | **2** | Barrenos de accesorios, 3.3 mm pasantes. | a discrecion segun lo que montes |
| McMaster 90611A121 | — | **1** | Rosca 5/8-11 UNC hembra del jalon. | capturado en la base; ver el pendiente del README |

**15 tornillos con longitud definida.** Sin tuercas sueltas: todos roscan en el plastico o en la antena.

## Lo de dentro

Nada de lo de dentro se atornilla: bateria, carrier UM980, Thing Plus y
lo demas se amarran con bridas al respaldo del tubo. Varias de esas
placas no tienen patron de agujeros publicado.

## Advertencias

- Tornillos de los paneles: NO poner uno mas largo que el de la lista. El de arriba del panel principal queda a 0.4 mm del cuello de la tapa, que gira al cerrar la bayoneta: si asoma, la tapa no cierra.
- Los tres tornillos de la antena van ANTES que la plataforma del IMU: sus cabezas quedan dentro del cuello de la tapa.
- Los dos M2.5 del IMU tienen que ser de cabeza AVELLANADA: el cono asienta en el canto del agujero de 3.0 y centra la placa sobre el piloto. Con cabeza cilindrica quedan 0.25 mm de juego por lado y el chip ya no cae en el eje. Sin tuercas ni arandelas.
- Los agujeros de la pantalla son de 2.0 segun el plano del vendedor y el M2 entra justo. Si no pasa, repasar el agujero con broca de 2.2 o usar M1.6x4.

## Consumibles

| Consumible | Cantidad | Uso |
| --- | ---: | --- |
| Brida de 2.5 a 3.6 mm, 150-200 mm | 10-15 | Paquete contra el respaldo |
| Brida de 2.5 mm, 100 mm | 2 | Placa del USB-C a su repisa |
| Lamina transparente de 1 mm (acrilico o PETG), 27 x 19.5 | 1 | Mica de la pantalla |
| Cinta de espuma o fieltro adhesivo | segun bateria | Entre bateria y respaldo |
| Llave Allen 2 mm | 1 | M3 cabeza boton y M2.5 cilindrica de la antena |
| Llave Allen 1.5 mm o desarmador Phillips 0 | 1 | M2 de la pantalla y M2.5 avellanado del IMU |
| Llave de 14 mm o pinzas | 1 | Tuerca del boton |
