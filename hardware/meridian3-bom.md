# Lista de materiales del Meridian3

El Meridian3 es un receptor aparte, más sencillo que el MeridianV. Esta lista
no sustituye a [bom.md](bom.md), que sigue siendo la del MeridianV. La
carcasa y su tornillería están en
[mechanical/meridian3](../mechanical/meridian3/README.md).

**Nada de esto se ha montado ni ensayado.**

| Componente | Modelo | Estado | Observaciones |
| --- | --- | --- | --- |
| Microcontrolador | Waveshare ESP32-S3-Tiny (ESP32-S3FH4R2) | El del proyecto | No tiene USB-C propio: usa un FPC de 0.5 mm y 8 vías hacia la Tiny-Adapter ([esquema](references/waveshare/ESP32-S3-Tiny-Sch.pdf)). |
| Adaptador USB | Waveshare Tiny-Adapter | El del proyecto | Su USB-C es la **única entrada** del equipo. Va atornillado a la tapa del panel ([esquema](references/waveshare/Tiny-Adapter.pdf)). |
| Receptor GNSS | Carrier BDLX RTK_UM98_V1.0.1 con UM980 | El del proyecto | DC 4.0–5.5 V, 160 mA a 5 V según BDLX. Pinout de sus conectores de 1.25 mm **por confirmar**. |
| Antena | Hélice HA-901A | La del proyecto | **Género del SMA por confirmar**; decide la altura de la carcasa. |
| Latiguillo | SMA macho–macho, clavijas rectas, RG174 o RG316 | Por comprar | 44 mm entre las puntas de los dos SMA hembra (41 a 47). Si la antena es macho, cambia. |
| FFC | 0.5 mm, 8 vías, unos 100 mm | Solo si el FPC original no llega | Mismo tipo de contactos que el original. |
| Cables | 4 hilos finos: 5 V, GND, TX, RX | — | De P1 de la Tiny al conector del carrier. |
| Alimentación | Power bank USB-C externo y su cable | Del propietario | Sobremolde ≤ 12.35 × 6.5 y al menos 3.2 mm rectos antes de un posible codo. Comprobar que no se apaga solo. |

**No lleva** IMU, microSD, batería, cargador, interruptor, radio ni puerto
auxiliar.

## 5 V para el UM980 (por confirmar)

Hoy cada placa se alimenta por su propio USB y solo comparten GND y el TTL2
([gnss-bringup](../docs/gnss-bringup.md)). En el Meridian3 hay un solo USB-C,
y la propuesta es tomar **VCC_5V de P1-1 de la Tiny**, que va después del
diodo D1 (B5819WS), junto con GND de P1-2, y llevarlos a los pines de
alimentación del carrier. Faltan tres cosas:

- el pinout del conector del carrier;
- la tensión con carga (unos 4.6 V esperados);
- la temperatura de D1, que pasa a llevar ESP32, UM980 y la LNA de la antena.

Las variantes (tomar VSYS en la Tiny-Adapter, o un USB-C de panel con
prolongador) están en el
[README de la carcasa](../mechanical/meridian3/README.md#alimentación-una-sola-entrada-usb-c).
