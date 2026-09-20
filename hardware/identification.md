# Identificación inicial de componentes

Fecha: 19 de septiembre de 2026. Fuentes: capturas de las publicaciones proporcionadas por el propietario, identificación USB y consulta de documentación del fabricante. Las fotografías de una publicación no verifican por sí solas las conexiones de la unidad recibida.

El propietario confirmó que solo el ESP32 está conectado a la Mac por USB. GNSS, IMU, microSD y alimentación externa no están cableados entre sí. También confirmó la compra de una antena Helix.

| Artículo | Evidencia disponible | Pendiente |
| --- | --- | --- |
| [ESP32-S3-Tiny](https://es.aliexpress.com/item/1005012432837911.html) | Captura con variante seleccionada `ESP32-S3-Tiny`. USB identifica ESP32-S3 QFN56, revisión 0.2, flash integrada XMC de 4 MB y PSRAM AP de 2 MB. `flash_id` confirma 4 MB, flash quad y 3.3 V. | Verificar serigrafía/revisión física antes de asignar GPIO externos. No usar el perfil N8R8. |
| [BMI088](https://es.aliexpress.com/item/1005009596235318.html) | Publicación de breakout azul de seis ejes con interfaces IIC/SPI anunciadas. | Identificar fabricante/revisión de la placa y comprobar esquema, orientación, alimentación y pines. No usar las dimensiones del resumen automático de la tienda. |
| [Publicación UM980](https://es.aliexpress.com/item/1005009578780196.html) | Se muestra una carrier BDLX con UM980, USB y SMA. La opción seleccionada en la captura es `Helix Antenna`; el propietario confirma la compra de la Helix. | La fotografía física coincide con RTK_UM98_V1.0.1 de BDLX; por USB responde UM980, R4.10Build13504 (COM3, 115200 baud). Identificar la antena y sus bandas; no asumir que sea HA-901A. Comprobar qué conectores son TTL y cuáles RS232 antes de cablear. |
| [Lector microSD](https://es.aliexpress.com/item/1005011827601230.html) | Módulo azul SPI, opción `1pcs`; la publicación anuncia regulador y conversión de niveles. | Identificar los circuitos reales y verificar alimentación y niveles. La etiqueta comercial 5 V/3.3 V no demuestra que cualquier pin acepte ambas tensiones. Tarjeta concreta pendiente. |
| [Interruptor biestable](https://es.aliexpress.com/item/33054170454.html) | Módulo verde con pines; la publicación anuncia 2.5–6 V y 6 A. | Verificar modelo, esquema, corriente y función de las señales. Las cifras anunciadas no están validadas. No se ha identificado como cargador, regulador ni protector de LiPo. |

## Fuentes técnicas

- [Waveshare ESP32-S3-Tiny: variantes y recursos](https://www.waveshare.com/wiki/ESP32-S3-Tiny).
- [Ficha de producto Waveshare](https://www.waveshare.com/esp32-s3-tiny.htm): distingue Tiny 4 MB/2 MB de Tiny-N8R8 8 MB/8 MB.
- [esptool: comandos de lectura y escritura](https://docs.espressif.com/projects/esptool/en/latest/esp32s3/esptool/basic-commands.html).

La interfaz del firmware utiliza la detección en ejecución para mostrar flash y RAM. En la versión 0.1.0 la PSRAM no se habilita, aunque es detectada por esptool. El motivo es mantener el primer arranque independiente de memoria externa; no indica ausencia física de PSRAM.
