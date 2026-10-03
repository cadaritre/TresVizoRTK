# Cableado vigente — Thing Plus ESP32-S3 + UM980 + OLED

Revisión del 2 de octubre de 2026. Placa definitiva seleccionada por el propietario: **SparkFun Thing Plus ESP32-S3, WRL-24408**, con OLED Tecneu I2C de 0.96 pulgadas y 128×64. Firmware **0.8.0**. Sustituye el cableado de la Tiny de las notas de septiembre. La integración del Soft Power Switch Mk2 ya está implementada. Batería confirmada: **LiPo 1S, 3.7 V, 3000 mAh**. Falta identificar el elevador de 5 V del UM980; el arnés portátil completo no está validado.

## Conectar ahora

Hacer las conexiones sin alimentación y seguir los nombres impresos en cada módulo, no el orden de los pines de otra fotografía. Los números de esta tabla son GPIO, no posiciones en la hilera.

| Pin del módulo | Pin de la Thing Plus | Función |
| --- | --- | --- |
| UM980 **TTL_TXD2** | **RX / RXI — GPIO44** | Del GNSS al ESP32. |
| UM980 **TTL_RXD2** | **TX / TXO — GPIO43** | Órdenes y RTCM del ESP32 al GNSS. |
| UM980 **GND** | **GND** | Referencia común de señales. |
| OLED **VCC** | **3V3 / 3.3V** | Alimentación a 3.3 V. No usar V_USB/5 V. |
| OLED **GND** | **GND** | Tierra común. |
| OLED **SDA** | **SDA — GPIO8** | Datos I2C. |
| OLED **SCL** | **SCL — GPIO9** | Reloj I2C. |

El UM980 conserva su puerto **COM2 a 115200 baud, 8N1**. Se emplean los terminales **TTL** de la carrier BDLX ya utilizados con la Tiny; **no** los terminales RS232. El ESP32 espera señales de 3.3 V. El historial confirma comunicación, pero no una medición eléctrica independiente de esa carrier.

Por ahora, alimentar **Thing Plus por su USB-C** y **carrier UM980 por su propio USB**, como en el banco anterior. Compartir GND, sin unir sus líneas de 5 V, batería ni reguladores de 3.3 V. La alimentación del GNSS desde la batería del instrumento requiere un elevador todavía no identificado. No alimentarlo desde el pin 3V3 de la Thing Plus por inferencia del pinout.

El conector Qwiic también lleva SDA/SCL/3.3 V/GND. Puede usarse un cable Qwiic a terminales para la OLED, respetando las señales. Basta una de las dos formas de conexión.

## microSD integrada

Insertar la tarjeta en el **socket de la propia Thing Plus**, antes de encender. No se usa el lector SPI externo de la compra anterior. El firmware monta FAT32 sin formatear automáticamente. La tarjeta debe permanecer puesta durante la sesión; después de extraerla/reinsertarla, reiniciar el equipo para volver a montarla.

| Señal interna | GPIO |
| --- | --- |
| CLK | 38 |
| CMD | 34 |
| D0 / D1 / D2 / D3 | 39 / 40 / 47 / 33 |
| Detección de tarjeta | 48, HIGH cuando está insertada |

Estas conexiones ya están en el PCB; **no se cablean ni se reutilizan para otros módulos**. El backend usa SD_MMC a cuatro bits y 20 MHz. Una sesión empieza como `stream.part`; solo termina como `stream.bin` tras el cierre sin pérdidas. La extracción durante una grabación no se considera un cierre correcto. No se ha ensayado todavía el comportamiento físico de una tarjeta retirada.

## OLED

El driver configurado es **SSD1306**, con detección de dirección **0x3C o 0x3D**. Se eligió según la ficha de Tecneu del módulo de cuatro pines; la publicación de Mercado Libre no fue accesible para inspección automatizada. La ficha dice SSD1306 «o compatible»: queda pendiente confirmar la unidad entregada. Un ACK I2C confirma dirección, no modelo de controlador; si responde pero no dibuja, revisar esa compatibilidad antes de cambiar cableado.

La pantalla muestra versión, calidad GNSS, satélites, fuente/edad de RTCM, grabación y dirección IP. El FIX caduca a los dos segundos sin nuevas GGA, igual que el paquete de salud. No presenta FIX como precisión garantizada. Si la pantalla no responde, el firmware continúa con GNSS, BLE, USB y Wi-Fi; vuelve a buscarla cada segundo desde una tarea independiente.

`GET /api/status` informa `subsystems.display` con estado, dirección, controlador y GPIO, y `subsystems.microsd` con disponibilidad, detección y estado de grabación. Sin OLED o tarjeta no se inventan estados de éxito.

## Pines reservados y trabajo pendiente

- **GPIO19/20:** USB nativo; sin cables de sensores.
- **GPIO45:** enable del regulador de periféricos integrado. El firmware lo mantiene alto para I2C/microSD; esto no implementa apagado del equipo. Conservar los jumpers como vienen de fábrica.
- **GPIO0/46:** BOOT/LED de estado y RGB integrados; sin nuevas conexiones.
- **MAX17048 en 0x36:** lectura de voltaje y porcentaje cada segundo, desde la misma tarea I2C que la OLED, incluso sin pantalla. No se reinicia el medidor al arrancar.
- **Soft Power Switch Mk2:** PUSH a A0/GPIO10; OFF a A1/GPIO14. Secuencia y límites abajo.
- **IMU BMI088, PPS y radio:** siguen pendientes de identificar/integrar; esta revisión no les asigna pines ni habilita sensores inexistentes.

## Primera instalación

Conectar solamente la **nueva Thing Plus** por USB-C y cargar el perfil `esp32s3_usb`, que ahora usa la definición local `sparkfun_thing_plus_esp32s3`. No cargar este binario a la Tiny: los GPIO son distintos.

```sh
cd firmware/esp32
pio run -e esp32s3_usb
pio run -e esp32s3_usb -t upload --upload-port PUERTO_DE_LA_THING_PLUS
```

La segunda orden es una instrucción para el montaje: no se ejecutó durante esta adaptación. En una placa nueva, el cargador gráfico necesita **Instalación completa**. Si no entra al cargador: mantener BOOT, pulsar y soltar RESET, soltar BOOT y volver a buscar el puerto. La consola del instrumento usa el USB nativo, no ocupa RX44/TX43.

Comprobar después: versión 0.8.0 e identidad `tresvizo-thingplus-s3-4m-v1`, PSRAM detectada, pantalla con datos y microSD disponible. Verificar GNSS con antena conectada y cielo visible; probar una grabación corta y cerrarla antes de retirar la tarjeta. Estas comprobaciones físicas siguen pendientes.

El panel, en Diagnóstico, informa la placa, OLED y microSD. La prueba física `tests/hardware_smoke.py` admite `--require-oled --require-sd` para exigir pantalla y tarjeta detectadas; cambia temporalmente ajustes y reinicia el equipo. No se ejecutó en esta adaptación. La respuesta I2C no sustituye comprobar que la OLED dibuja correctamente.

## Referencias

- [Esquema oficial SparkFun, revisión v1.0](https://cdn.sparkfun.com/assets/5/e/6/5/0/SparkFun_Thing_Plus_ESP32-S3.pdf): redes UART/I2C, SDIO y regulador de periféricos.
- [Hardware y pinout de la Thing Plus](https://docs.sparkfun.com/SparkFun_Thing_Plus_ESP32-S3/hardware_overview/).
- [Ejemplos oficiales SparkFun](https://docs.sparkfun.com/SparkFun_Thing_Plus_ESP32-S3/arduino_example/): USB CDC/JTAG, PSRAM Quad, GPIO45 y detección de tarjeta.
- [Ficha Tecneu: OLED 0.96 I2C de cuatro pines](https://www.tecneu.com/products/modulo-de-pantalla-led-oled-7-pin-0-96-i2c): 128×64, alimentación 3.3–5 V, SSD1306 o compatible. Aquí se usa 3.3 V.
- [Soft Power Switch comprado](https://www.sparkfun.com/sparkfun-soft-power-switch-jst-2mm.html), pendiente de integración.
- [Historial del enlace TTL con UM980](../docs/gnss-bringup.md).

## Batería, carga y encendido/apagado

La batería actual es **LiPo 1S 3.7 V, 3000 mAh** (11.1 Wh nominales). Sustituye la referencia anterior de 5000 mAh. Capacidad declarada, no medida; comprobar polaridad y protección del pack. No conectar una celda LiHV ni varias en serie.

| Origen | Destino | Condición |
| --- | --- | --- |
| LiPo + / − | Soft Power Switch **IN + / GND** | Verificar polaridad del JST con multímetro. |
| Switch **OUT + / GND** | JST de batería de Thing Plus **+ / −** | No conectar a 3V3 ni V_USB. |
| Switch **PUSH** | Thing Plus **A0 / GPIO10** | Entrada activa baja, pull-up interno a 3.3 V. |
| Switch **OFF** | Thing Plus **A1 / GPIO14** | Mk2: HIGH corta, LOW permite funcionar. |
| Pulsador externo, opcional | **BTN ↔ GND** del switch | Pulsador momentáneo normalmente abierto. |
| USB-C de Thing Plus | Fuente USB de 5 V | Alimentación USB y cargador integrado. |
| Qwiic negro / rojo | OLED **GND / VCC** | 0 V / 3.3 V. |
| Qwiic azul / amarillo | OLED **SDA / SCL** | GPIO8 / GPIO9; seguir señales, no orden físico de la OLED. |
| Futuro elevador **5 V regulados** | Entrada USB de alimentación de la **carrier UM980** | **Pendiente del modelo del elevador y confirmación de carrier. No cablear un VIN desconocido.** |
| UM980 TTL_TXD2 / TTL_RXD2 / GND | Thing Plus RX44 / TX43 / GND | COM2, 115200, señales TTL; no RS232. |

El cargador MCP73831 trabaja por hardware. Su STAT va al LED de carga, no a un GPIO; no soldarlo directamente al ESP32: ese circuito incluye VUSB. El firmware no puede activar/desactivar la carga ni cambiar su corriente. La guía indica 214 mA y el esquema publicado muestra R16=2 kΩ / 500 mA: comprobar la revisión y R16 de la unidad antes de fijar corriente o tiempo de carga. No se presupone una carga de 1 A por tener 3000 mAh.

El Soft Power Switch permite el retorno de corriente del cargador hacia la batería según SparkFun. **No es un power-path ni un cargador**. Con USB conectado la Thing Plus sigue encendida aunque se corte el switch. Un elevador colgado del nodo de batería puede consumir corriente del cargador y afectar su terminación; no considerar resuelta la carga simultánea con el UM980. El elevador elegido necesita revisar EN, bloqueo de corriente inversa, consumo, tensión mínima y distribución. No unir dos salidas de 5 V ni alimentar UM980 desde 3V3 de Thing Plus. Hasta resolverlo, mantener el banco con los USB independientes y tierra común.

Secuencia implementada: soltar el botón de encendido; después sostenerlo **2 s** para apagar, o usar «Apagar dispositivo» en el panel. Se bloquean nuevas operaciones, se drena la cola de grabación, se cierra archivo/manifiesto y sólo entonces se lleva OFF a HIGH. Durante OTA se rechaza el apagado por software. Si el almacenamiento no termina de cerrar, no se fuerza el corte por temporizador. El botón físico puede forzarlo tras aproximadamente **10 s** y perder datos: esa función de hardware no la puede impedir el firmware.

Si sigue llegando alimentación tras solicitar OFF, OLED y API lo indican. No se afirma «apagado» ni se identifica USB sin medirlo. El equipo queda bloqueado para nuevas operaciones hasta reiniciar o quitar alimentación externa; no es un modo de suspensión. La batería se muestra como estimación de porcentaje/voltaje; «cargando», presencia de batería y presencia de USB quedan desconocidos, porque la placa no proporciona esas señales al firmware. Con USB, VBAT puede tener tensión sin una celda conectada. El aviso de batería baja (≤10 % o ≤3.4 V) no sustituye la protección del pack; no hay corte automático por una lectura del medidor.

Fuentes: [esquema oficial Thing Plus](https://github.com/sparkfun/SparkFun_Thing_Plus_ESP32-S3/blob/main/docs/assets/board_files/SparkFun_Thing_Plus_ESP32-S3.pdf), [guía Thing Plus](https://docs.sparkfun.com/SparkFun_Thing_Plus_ESP32-S3/hardware_overview/), [guía Soft Power Mk2](https://docs.sparkfun.com/SparkFun_Soft_Power_Switch_Mk2/single_page/), [driver de referencia MAX1704x](https://github.com/sparkfun/SparkFun_MAX1704x_Fuel_Gauge_Arduino_Library).

Validación pendiente en hardware: carga real, polaridades, lectura del medidor, caída de tensión, apagado con y sin USB, cierre con grabación activa, consumo total/picos de UM980 y compatibilidad de su alimentación. Las pruebas de compilación y lógica no reemplazan estos ensayos.

### Verificación de alimentación de la carrier BDLX

La [tabla publicada por BDLX](https://www.bdlxgnss.com/static/upload/image/20250804/1754279536807539.png) especifica **4.0–5.5 V, típico 5.0 V** para su placa UM980. La [fotografía posterior del mismo producto](https://www.bdlxgnss.com/static/upload/image/20250804/1754279537213094.png) muestra la revisión **RTK_UM98_V1.0.1** y el terminal **5V_IN**, coincidentes con la identificación conservada. La entrada externa de esta carrier no debe confundirse con VCC del módulo UM980: [Unicore especifica 3.0–3.6 V](https://en.unicore.com/uploads/file/UM980_User%20Manual_EN_R1.7.pdf) para el módulo sin carrier.

Una LiPo convencional llena puede alcanzar 4.2 V y hacer arrancar la carrier, pero al bajar de 4.0 V queda fuera del rango publicado; arrancar no valida la descarga completa. Para la alimentación portátil a través de esta entrada se mantiene la necesidad de regulación: OUT del switch → elevador 5 V → **5V_IN de la carrier**, con GND común. Modelo del elevador y gestión de fuentes simultáneas pendientes; no conectar simultáneamente 5V_IN y USB sin verificar el aislamiento de la placa.
