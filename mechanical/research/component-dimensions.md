# Dimensiones y evidencia mecánica — 19 de septiembre de 2026

Actualización A1: la foto posterior identifica la **HA-901A**, sin resolver su patrón de tres agujeros. La [ficha de revisión A1](../cad/README-A1.md) documenta esa evidencia, el efecto de una cubierta adicional y la tuerca **5/8-11 UNC** propuesta con medidas de fabricante. Las referencias a antena sin identificar y base sin rosca que siguen describen el estudio inicial A0.

Las capturas del propietario identifican publicaciones y familias de placas. No son planos a escala. Se distinguen las cotas declaradas por un fabricante, la posible equivalencia de una placa genérica y las reservas de espacio elegidas para diseñar. Ninguna medida se ha contrastado con el componente físico recibido.

| Componente | Evidencia encontrada (mm) | Agujeros y límites de la evidencia |
| --- | --- | --- |
| Waveshare ESP32-S3-Tiny | Placa principal **18 × 23.5**; perfil total dibujado **2.45**. Esquinas R1. | No tiene taladros de fijación independientes. Los orificios metalizados del perímetro son conexiones eléctricas. No incluye headers soldados, cable FPC ni su espacio de flexión. |
| Adaptador USB del kit Waveshare | **18 × 18**, cuatro centros con patrón **14 × 14**, a **2** de los bordes. | El plano no acota el diámetro de los cuatro agujeros. Las cotas de 2 mm son posiciones, no diámetros. Los pasos Ø2.2 del soporte A0 son una elección provisional, condicionada a verificar la placa. Altura de 5 en A0 es reserva, no cota oficial. |
| Carrier BDLX con UM980 | La ficha de BDLX declara **32 × 52 × 11**. Sus fotos coinciden visualmente con la captura: PCB negra, cuatro agujeros, USB lateral superior, dos conectores blancos, pila y SMA inferior. El reverso publicado muestra `RTK_UM98_V1.0.1`. | No aparece plano con centros/diámetros ni se precisa si los 52 mm incluyen el SMA. Deben comprobarse revisión real, contorno y salientes. La reserva A0 es **36 × 12 × 64** (X/Y/Z), mayor que el cuerpo declarado; no demuestra espacio para el cable o enchufe SMA. El adaptador queda sin patrón comercial. |
| Breakout azul BMI088 V1.0 | La captura muestra dos agujeros y una miniatura de un plano. Las cotas de esa miniatura no se leen con fiabilidad. | El datasheet de Bosch corresponde al encapsulado del sensor, no a la placa azul. No se encontraron fabricante ni plano verificable de esa revisión. Reserva de diseño **28 × 24 × 8**, sin patrón inventado. |
| microSD SPI azul | El proveedor Flux Workshop describe su familia similar como **42 × 24 × 7**, patrón **38 × 20**, fijación M2. | Es otra publicación de placa genérica; la coincidencia con la unidad del propietario no está certificada. El soporte A0 reproduce ese patrón de referencia, marcado provisional. Falta confirmar salida/extracción de tarjeta, headers y cara de apoyo. |
| Interruptor biestable verde | Elecbee publica el IO15B01 como **15.5 × 10 × 2.5**. Coincide con la familia comercial, pero no confirma la revisión recibida. | Sin agujeros de montaje propios. Los pines aumentan la altura. La reserva A0 **18 × 12 × 14** no es una medida validada; retención y accionamiento externo pendientes. |
| Helix | Compra confirmada; modelo sin confirmar en el inventario. | La foto de un paquete no confirma qué antena se recibió. No se transfieren dimensiones del modelo HA701 a HA-901A. Reserva A0 **Ø46 × 46**, sin patrón de montaje de antena ni centro de fase asumido. |
| Batería | La familia LiPo **955565** tiene dimensión nominal de celda **9.5 × 55 × 65** según DNK. | Batería pendiente de elección. PCM, envoltura, pestañas, conector, cables y tolerancias pueden cambiar el volumen del pack. Reserva A0 **56 × 12 × 69**: hipótesis de embalaje, no validación de batería ni de dilatación. |

## Fuentes consultadas

- [Waveshare, ESP32-S3-Tiny: dimensiones](https://docs.waveshare.com/ESP32-S3-Tiny), [plano gráfico oficial](https://docs.waveshare.com/assets/images/ESP32-S3-Tiny-details-1-3cb57dcb7847e1db49d2faee9722d6df.webp). Aplica a la familia mecánica Tiny; el inventario eléctrico del proyecto confirma Tiny 4 MB / 2 MB, aunque la nueva captura muestra seleccionada la variante N8R8 del kit. No se cambia el perfil del firmware a partir de esa captura.
- [BDLX, UM980 GNSS RTK Board](https://www.bdlxgnss.com/?list_22/101.html=), [tabla de dimensiones](https://www.bdlxgnss.com/static/upload/image/20250804/1754279536807539.png), [anverso y reverso](https://www.bdlxgnss.com/static/upload/image/20250804/1754279537213094.png). La imagen de la tabla se leyó directamente, no desde un resumen comercial automático.
- [Bosch, datasheet BMI088](https://www.bosch-sensortec.com/media/boschsensortec/downloads/datasheets/bst-bmi088-ds001.pdf). No especifica agujeros del breakout azul.
- [Flux Workshop, BFAA100021](https://fluxworkshop.com/products/bfaa100021-micro-sd-blue), ficha del proveedor para una placa de referencia similar.
- [Elecbee, IO15B01](https://www.elecbee.com/en/product-detail/io15b01-6a-dc-electronic-switch-latch-bistable-self-locking-trigger-module-board-for-lithium-battery_26686), referencia de familia, sin equivalencia asegurada con la unidad del propietario.
- [DNK, LiPo 955565](https://www.dnkpower.com/products/3-7v-5000mah-lithium-polymer-battery-955565/), celda de referencia, sin selección de proveedor.
- [Emlid, especificaciones mecánicas del Reach RX](https://docs.emlid.com/reachrx/specifications/specs/), [plano oficial](https://files.emlid.com/docs/Reach%2BRX%2Bdrawing.pdf): **172 × 51 × 51**. Se usa como referencia de forma. No se copian sus centros de fase, calibración, sellado ni capacidad estructural.

## Información que falta para cerrar los soportes

1. Plano legible de la miniatura del BMI088 y revisión del breakout: longitud, anchura, espesor, centros, diámetros y posición del sensor respecto de los agujeros.
2. Plano de la carrier BDLX: centros de los cuatro agujeros, diámetro, altura de componentes por ambas caras y proyecciones de conectores, incluyendo SMA con el cable instalado.
3. Confirmar la familia y medidas del lector microSD, del interruptor y del adaptador USB recibidos. Elegir pines rectos/acodados o cable soldado antes de congelar sus volúmenes.
4. Elegir batería, antena, cargador/regulador, interruptor físico e inserto metálico del jalón; documentar sus referencias mecánicas.

Las publicaciones de AliExpress no estuvieron accesibles mediante la herramienta del navegador. No se sustituyeron sus cotas por las de los resúmenes automáticos, ni se escalaron fotografías para obtener agujeros supuestamente exactos.
