# Identificación inicial de componentes

**Alimentación — 02/10/2026:** LiPo 1S 3.7 V / 3000 mAh confirmada. Lectura MAX17048 y apagado coordinado Mk2 implementados; falta identificar el elevador de 5 V y validar físicamente el conjunto con UM980. Ver `hardware/wiring.md` desde la raíz. La carga es autónoma por hardware; USB impide el corte total de batería.
**Actualización 02/10/2026:** la Thing Plus ESP32-S3 WRL-24408 sustituye a la Tiny como placa definitiva. Se añaden OLED Tecneu I2C 128×64 y SparkFun Soft Power Switch JST 2 mm; el control del interruptor ya está implementado. Selección actual en [BOM](bom.md) y [cableado](wiring.md). Las capturas y verificaciones siguientes pertenecen al hardware previo; no prueban el montaje nuevo.


## Corrección para Power Board P1

El propietario identifica ahora la placa utilizada como **Waveshare ESP32-S3-Tiny-N8R8** y reporta serigrafía trasera `ESP32-S3-TINY`. Esta marca no distingue variante ni revisión del FPC. Los resultados USB 4 MB/2 MB de abajo se conservan como evidencia histórica, cuya correspondencia con la unidad actual está pendiente. Para P1 rige N8R8 declarada; no convertir esa declaración en verificación física ni cambiar firmware automáticamente. Ver [cableado USB vigente](power-modules/WIRING.md). La restricción histórica «No usar el perfil N8R8» de la tabla no es una decisión sobre la unidad actualmente declarada.

Fecha: 19 de septiembre de 2026. Fuentes: capturas de las publicaciones proporcionadas por el propietario, identificación USB y consulta de documentación del fabricante. Las fotografías de una publicación no verifican por sí solas las conexiones de la unidad recibida.

El propietario confirmó que solo el ESP32 está conectado a la Mac por USB. GNSS, IMU, microSD y alimentación externa no están cableados entre sí. También confirmó la compra de una antena Helix.

| Artículo | Evidencia disponible | Pendiente |
| --- | --- | --- |
| [ESP32-S3-Tiny](https://es.aliexpress.com/item/1005012432837911.html) | Captura con variante seleccionada `ESP32-S3-Tiny`. USB identifica ESP32-S3 QFN56, revisión 0.2, flash integrada XMC de 4 MB y PSRAM AP de 2 MB. `flash_id` confirma 4 MB, flash quad y 3.3 V. | Verificar serigrafía/revisión física antes de asignar GPIO externos. No usar el perfil N8R8. |
| [BMI088](https://es.aliexpress.com/item/1005009596235318.html) | Publicación de breakout azul de seis ejes con interfaces IIC/SPI anunciadas. | Identificar fabricante/revisión de la placa y comprobar esquema, orientación, alimentación y pines. No usar las dimensiones del resumen automático de la tienda. |
| [Publicación UM980](https://es.aliexpress.com/item/1005009578780196.html) | Se muestra una carrier BDLX con UM980, USB y SMA. La opción seleccionada en la captura es `Helix Antenna`; el propietario confirma la compra de la Helix. | La fotografía física coincide con RTK_UM98_V1.0.1 de BDLX; por USB responde UM980, R4.10Build13504 (COM3, 115200 baud). Identificar la antena y sus bandas; no asumir que sea HA-901A. Comprobar qué conectores son TTL y cuáles RS232 antes de cablear. |
| [Lector microSD](https://es.aliexpress.com/item/1005011827601230.html) | Módulo azul SPI, opción `1pcs`; la publicación anuncia regulador y conversión de niveles. | Identificar los circuitos reales y verificar alimentación y niveles. La etiqueta comercial 5 V/3.3 V no demuestra que cualquier pin acepte ambas tensiones. Tarjeta concreta pendiente. |
| [Interruptor biestable](https://es.aliexpress.com/item/33054170454.html) | Módulo verde con pines; la publicación anuncia 2.5–6 V y 6 A. | Verificar modelo, esquema, corriente y función de las señales. Las cifras anunciadas no están validadas. No se ha identificado como cargador, regulador ni protector de LiPo. |

## Batería indicada posteriormente

El propietario identifica la [publicación 955565](https://es.aliexpress.com/item/1005008867815394.html), anunciada 3.7 V, 5000 mAh y 18.5 Wh, mediante captura. Cableado mostrado de dos hilos; PCM, NTC, conector, corrientes y medidas reales sin verificar. Véase [referencia de batería](references/BATTERY_REFERENCE.md).

## Fuentes técnicas

- [Waveshare ESP32-S3-Tiny: variantes y recursos](https://www.waveshare.com/wiki/ESP32-S3-Tiny).
- [Ficha de producto Waveshare](https://www.waveshare.com/esp32-s3-tiny.htm): distingue Tiny 4 MB/2 MB de Tiny-N8R8 8 MB/8 MB.
- [esptool: comandos de lectura y escritura](https://docs.espressif.com/projects/esptool/en/latest/esp32s3/esptool/basic-commands.html).

La interfaz del firmware utiliza la detección en ejecución para mostrar flash y RAM. En la versión 0.1.0 la PSRAM no se habilita, aunque es detectada por esptool. El motivo es mantener el primer arranque independiente de memoria externa; no indica ausencia física de PSRAM.
