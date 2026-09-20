# Dimensiones de los componentes comprados

> Referencia heredada de A5. Para fabricar y montar usar [V1](../../v1/README.md); sus cambios y estado sustituyen los pendientes históricos de este documento.

Investigación: 19 de septiembre de 2026. Unidades: mm. Este documento separa las cotas publicadas, la correspondencia visual con la compra y las reservas del CAD. No constituye una inspección dimensional de las piezas recibidas. Actualización del 20 de septiembre: el montaje ajustable del BMI088 ya está incorporado en `TresVizo-A5.FCStd`; véase [montaje y centrado](IMU-ALIGNMENT.md).

## Resultado

| Componente | Datos encontrados | Alcance de la evidencia |
|---|---|---|
| BMI088 azul V1.0 | PCB 18 × 23.5; dos agujeros Ø3; separación 18.5; centros a 2.5 de los bordes próximos | Plano de vendedor con fotografía coincidente con la placa comprada. Resuelve el patrón publicado de fijación. |
| Carrier UM980 BDLX | 32 × 52 × 11 | Ficha del fabricante; no incluye patrón acotado de agujeros. |
| microSD azul | PCB 42 × 24; patrón 38 × 20, tornillos M2 | Ficha de vendedor de la misma familia; no está demostrada la identidad del fabricante o lote de AliExpress. |
| Batería 955565 | Compra confirmada: 3.7 V, 5000 mAh, 18.5 Wh; nominal 9.5 × 55 × 65 | Identificación aportada por el propietario. El máximo del paquete terminado no queda fijado por el código de celda. |
| Antena HA-901A | Ø43.5 × 40.8; 3-M2.5×6 sobre círculo Ø26.6 | Etiqueta del propietario y plano del vendedor; montaje ya incorporado en A5. |
| Waveshare ESP32-S3-Tiny | PCB 18 × 23.5; perfil publicado 2.45 | Plano oficial; los pads de conexión no son agujeros de montaje. |
| Adaptador USB Waveshare | PCB 18 × 18; patrón 14 × 14, centros a 2 de bordes | Plano oficial; no confundir la cota 2 del borde con diámetro de agujero. |

## BMI088: plano localizado

[Anuncio con la placa y su plano](https://www.ebay.com/itm/206558450820). [Imagen original](https://i.ebayimg.com/images/g/pIEAAeSw-1lqoAi0/s-l1600.webp). [Copia de consulta](sources/BMI088-V1-dimensions.webp).

Coinciden la serigrafía BMI088V1.0, el PCB azul, los dos agujeros en el mismo borde, la hilera de nueve conexiones en el borde opuesto y el selector IIC/SPI. La procedencia es un vendedor de una placa sin marca declarada; no una certificación del fabricante del lote comprado.

Coordenadas para trasladar el plano a CAD, mirando la cara de componentes con la hilera de conexiones abajo: origen en esquina inferior izquierda del PCB; X hacia la derecha, Y hacia arriba. Contorno 23.5 en X × 18 en Y. Agujeros centrados en **(2.5, 15.5)** y **(21.0, 15.5)**, diámetro **3.0**. Son coordenadas derivadas aritméticamente de las cotas, no medidas por píxeles. Alternativamente, en la orientación del dibujo publicado: contorno 18 × 23.5 y centros (15.5, 2.5), (15.5, 21).

No están acotados el espesor del PCB, la altura del selector y pines ni la posición exacta del encapsulado sensor respecto a esos agujeros. No usar el centro geométrico de la placa como supuesto centro del sensor. A5 ya incorpora este patrón en la referencia PCB y un asiento ajustable: dos M2.5 y una plantilla removible alinean el encapsulado real con el eje del receptor. `IMUReserve` usa espesor provisional de 1.6 mm; `IMUTarget` es un objetivo de alineación, no la posición medida del sensor. Véase [montaje y límites](IMU-ALIGNMENT.md).

## UM980: carrier correcto, agujeros sin plano publicado localizado

[Página oficial BDLX](https://www.bdlxgnss.com/?list_22/101.html=). [Tabla oficial de dimensiones](https://www.bdlxgnss.com/static/upload/image/20250804/1754279536807539.png), guardada en [sources](sources/BDLX-UM980-specifications.png). [Fotografía de ambas caras](https://www.bdlxgnss.com/static/upload/image/20250804/1754279537213094.png).

La ficha publica 32 × 52 × 11 y las fotografías permiten reconocer la familia de carrier RTK_UM98_V1.0.1. Se revisaron las doce imágenes de detalle y el enlace Download: éste devuelve una imagen promocional, no un plano mecánico. No se encontró en ellas diámetro, coordenadas ni distancias entre centros de sus cuatro agujeros. Tampoco se especifica inequívocamente si las dimensiones máximas incluyen todas las salientes de los conectores.

Se buscaron la revisión de serigrafía, BDLX, BD LOCATOR y las dimensiones; el anuncio alternativo en [Joom](https://www.joom.com/nb/products/69e9bfbe042817016c51668c) identifica BD LOCATOR pero no aporta esas cotas. Los planos del encapsulado UM980 de Unicore y de las placas de SparkFun no corresponden a este carrier.

Datos que faltan concretamente: diámetro de los cuatro barrenos, centros respecto a dos bordes del PCB y envolventes/posición de SMA, USB y conectores con sus cables enchufados. Para cerrar fijaciones rígidas hace falta el dibujo mecánico de esta revisión o medir la placa. No se adopta un patrón supuesto de 26 × 46 obtenido por proporción de fotografías. Los soportes ajustables propuestos por el propietario siguen siendo una opción para este carrier. Para el IMU, el propietario autorizó después ajuste durante montaje con indicador de centrado y bloqueo rígido final; no debe quedar flotante en uso.

## microSD: patrón de la familia, no certificación del lote

[Ficha del módulo de Robot Pi Shop](https://robotpishop.com/products/micro-sd-card-reader-module): 42 × 24, fijaciones M2 con separación 38 × 20. [Ficha de Flux Workshop BFAA100021](https://fluxworkshop.com/products/bfaa100021-micro-sd-blue): misma familia, envolvente publicada 42 × 24 × 7. La consulta directa de Flux falló en esta revisión; la información recuperada del buscador no sustituye un plano descargado.

El anuncio del propietario muestra la familia azul con regulador y conversor de nivel, seis pines y cuatro agujeros. El patrón encontrado sirve de referencia para soportes ajustables. No se deduce de la denominación M2 el diámetro exacto del barreno, ni se fijan centros a 2 mm del borde sin confirmar que el patrón esté centrado. Falta la cota de la ranura de tarjeta respecto al PCB y el recorrido de inserción/extracción para cerrar el acceso de la carcasa.

## Batería comprada: 955565 de 5000 mAh

El propietario confirmó con captura la [batería comprada](https://es.aliexpress.com/item/1005008867815394.html): 955565, 3.7 V, 5000 mAh y 18.5 Wh, dos cables y conector de dos contactos. El resumen comercial indica 9.5 × 55 × 65. No identifica de forma verificable el fabricante de la celda, el paso del conector, la polaridad de su carcasa ni tolerancias del paquete. El acceso automatizado a AliExpress está bloqueado; no se obtuvo de allí un plano adicional.

Se encontró una **especificación real con plano de otro paquete 955565**, fabricado por Shenzhen Dazheng para Ciel Light: [PDF, página 5](https://ciellight.com/data/item/DZ955565/955565-3.7V-5000mah%20XBL-MP4439A%201.25-2P.pdf). Define máximos **10 × 55.5 × 68**, cables 60 ±5 y conector 1.25-2P para SU producto. El alcance del propio documento restringe su aplicación a ese fabricante. Por tanto, ni el conector ni las especificaciones eléctricas de ese PDF se atribuyen a la batería del propietario.

La diferencia demuestra por qué 9.5 × 55 × 65 de celda nominal no basta para diseñar un alojamiento ajustado. La reserva existente en A5 es 56 × 12 × 69 (ancho × espesor × largo): contiene aquella envolvente de referencia, pero **no demuestra ajuste del paquete comprado ni espacio suficiente para cableado o cambios de espesor durante uso**. Debe sujetarse sin comprimir la bolsa y conservar espacio para la salida de cables; no cambiarla a un hueco exacto de 9.5 × 55 × 65.

La identificación eléctrica y el diseño de carga pertenecen a [BATTERY_REFERENCE.md](../../../hardware/references/BATTERY_REFERENCE.md); este hallazgo no cambia las decisiones de la PCB en desarrollo.

## Fuentes ya disponibles: antena y Waveshare

Antena: [plano HA-901A](https://i.ebayimg.com/images/g/F2sAAOSwLzJl8nTm/s-l1600.webp), [anuncio XYANT Wireless](https://www.ebay.com/itm/315222778620). El montaje incorporado, la tornillería y las verificaciones están descritos en [V1](../../v1/README.md).

Waveshare: [documentación oficial ESP32-S3-Tiny](https://www.waveshare.com/wiki/ESP32-S3-Tiny) y [plano mecánico oficial](https://docs.waveshare.com/assets/images/ESP32-S3-Tiny-details-1-3cb57dcb7847e1db49d2faee9722d6df.webp). El adaptador USB separado no es un cargador de batería. Botón, USB-C de carga y LEDs siguen sujetos a la PCB que se está diseñando; no se seleccionan módulos nuevos ni se cierran perforaciones del panel en esta investigación.

El inserto del jalón tampoco queda definido por estos planos electrónicos: sigue pendiente una referencia comercial concreta con rosca y dimensiones de anclaje documentadas. No se añade una pieza metálica de fabricación especial.
