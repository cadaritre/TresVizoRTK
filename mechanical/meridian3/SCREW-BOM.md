# Tornillería del Meridian3

Generado por `bom.py` (lo ejecuta `regenerate.py`). Los largos salen de la
geometría: desde el asiento de la cabeza hasta el fondo de cada piloto, y el
tornillo es el más largo comercial que no pasa de ese fondo.

**Nada de esto se ha montado ni ensayado.**

| Pieza | Largo | Cant. | Dónde | Cálculo |
| --- | ---: | ---: | --- | --- |
| M3 cabeza botón ISO 7380 | 14 mm | **1** | Seguro de la base. Rosca en el macizo de la base, sobre la brida del inserto. | piloto útil 14.7; rosca 9.4 |
| M3 cabeza botón ISO 7380 | 12 mm | **1** | Seguro de la tapa. Rosca en el refuerzo del cuello. | piloto útil 12.5; rosca 7.4 |
| M3 cabeza botón ISO 7380 | 8 mm | **2** | Pie del trineo contra el suelo de la base. | pie 3 + piloto 6.5; rosca 5 |
| M3 cabeza botón ISO 7380 | 6 mm | **2** | Tapa del panel USB-C. Rosca en el engrosamiento del tubo. | rosca 3.3; nunca más largo |
| M2.5 cilíndrica ISO 4762 | 10 mm | **3** | Antena. Sube desde dentro de la tapa y rosca en la antena. | tapa 5 + 5 de 6 de rosca en la antena |
| M2 cilíndrica ISO 4762 (o de cabeza plana) | 6 mm | **4** | Tiny-Adapter sobre las torres de la repisa de la tapa del panel. | PCB 1.6 + torre 2.0 + repisa 2.5; rosca 4.4 en piloto de 1.6 |
| McMaster 90611A121 | — | **1** | Rosca 5/8-11 UNC hembra del jalón. | capturado entre base y tubo; sin tornillos |

**13 tornillos con largo definido y ninguna tuerca.** Frente a V2.1 desaparecen el IMU (con sus tuercas), el panel auxiliar y los barrenos de accesorios, y aparecen los cuatro M2 de la Tiny-Adapter.

## Advertencias

- Los dos tornillos del pie van ANTES que el carrier: quedan debajo de él.
- La rosca de la antena se supone de 6 mm (referencia 3-M2.5x6). Medirla: un tornillo largo de más toca fondo y no aprieta.
- Los agujeros de la Tiny-Adapter (patrón 14 x 14) son los de su plano oficial: es la única placa que se atornilla. El carrier y la Tiny van con bridas, como en V2.1.
- Tornillos del panel: el de arriba queda 3 mm por debajo del cuello de la tapa, que baja por dentro y gira al cerrar. **No poner uno más largo que el de la lista.**

## Consumibles

| Consumible | Cantidad | Uso |
| --- | ---: | --- |
| Brida de 2.5 mm, 100-150 mm | 4 | Carrier (dos, a lo largo) y Tiny (dos) |
| Lámina aislante fina | 1 | Entre el carrier y la placa del trineo |
| Latiguillo SMA macho–macho, clavijas rectas, RG174 o RG316 | 1 | Antena a carrier; largo en el README |
| FFC de 0.5 mm, 8 vías | 1 | Tiny a Tiny-Adapter, si el FPC original no llega; largo en el README |
| Llave Allen 2 mm | 1 | M3 cabeza botón y M2.5 cilíndrica |
| Llave Allen 1.5 mm | 1 | M2 cilíndrica |
