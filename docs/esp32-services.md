# Servicios autónomos del ESP32 — 0.5.0

**Actualización 0.8.0 (Thing Plus):** los apartados de GPIO18/17 y lector SPI
sin configurar describen la placa anterior. El montaje vigente usa RX44/TX43,
OLED I2C8/9 y microSD integrada por SDIO; ver [cableado](../hardware/wiring.md).
`/api/status` publica `board`, `hardware_id`, `subsystems.display`, y los campos
`rx_gpio`, `tx_gpio`, `baud` de GNSS. Tanto `subsystems.microsd` como
`GET /api/recording` publican `card_present`, `interface` y `closing` además del
estado previo. `active` significa recepción de bytes; `closing` indica que el
archivo sigue ocupado aunque se haya detenido la recepción. El panel impide
operar o descargar hasta terminar ese cierre. La validación física está pendiente.

El nombre de producto es **Memoria interna del dispositivo**. Se publica como
`storage_label` en el estado del almacenamiento y en `/api/operations.recording`
para los clientes de la API. Los identificadores técnicos `microsd` se conservan
por compatibilidad; no deben usarse como etiquetas de interfaz. Repetir una orden
de parada conserva el estado parcial de un cierre fallido. La OLED abrevia
**MEM INT.**; la RAM se identifica por separado.

## Memoria

ESP32-S3FH4R2: PSRAM Quad habilitada con `BOARD_HAS_PSRAM` y `dio_qspi`, flash DIO de 4 MB sin cambiar particiones. El SDK inicializa y prueba PSRAM. Antes de iniciar servicios se reserva 1 MiB explícitamente en PSRAM, se escriben y leen tres patrones dependientes de dirección, y se libera. No es una prueba de envejecimiento ni temperatura. `/api/status.memory` distingue RAM interna libre/mínima/bloque mayor de PSRAM total utilizable/libre y resultado del ensayo. `ESP.getPsramSize()` informa capacidad del heap utilizable, ligeramente inferior a los 2097152 bytes físicos.

## Control UM980 por UART

GPIO18 RX y GPIO17 TX, 115200, COM2 del UM980. `GET /api/gnss/control` informa trabajo, modo, versión, errores y comandos completados. `POST` inicia un trabajo asíncrono y devuelve 202:

- `{"action":"query"}`: VERSIONA y MODE.
- `{"action":"rover"}`: MODE ROVER SURVEY, UNDULATION AUTO y lectura MODE.
- `{"action":"telemetry","hz":10}`: GPGGA COM2; frecuencias 1, 5 o 10 Hz.

> **Superado.** Así era en 0.5.0. Después de 0.7.12, `rover` envía `UNLOG COM2`,
> `MODE ROVER SURVEY`, `CONFIG UNDULATION 0.0000` (elipsoidal, no AUTO), `MODE`,
> repone `GPGGA` a la última tasa aplicada (5 Hz por defecto) con `GPGST`, `GPGSV`
> y `GPGSA` a 1 Hz, y termina con `SAVECONFIG` solo si el modo leído es rover.
> `telemetry` envía `GPGGA COM2 <tasa>`, `GPGST`, `GPGSV` y `GPGSA` a 1 Hz y
> `SAVECONFIG`; admite 1, 2 y 5 Hz (tope de 0.7.6). Contrato vigente en
> [configuración avanzada del receptor](gps-advanced.md).
- `{"action":"raw_profile"}`: OBSVMB COM2 1, efemérides GPS/GLO/GAL/BDS/BD3 cada 30 s. Requiere verificar capacidad del enlace a 115200 y almacenamiento; no se activa durante el ensayo inicial sin tarjeta.

El dueño de UART envía comandos y RTCM sin intercalar sus bytes. Un comando a la vez; ACK asociado al texto exacto, checksum XOR de control y CRC32 de VERSIONA, lectura MODE cuando procede. Timeout de respuesta 4 s: estado parcial/incierto, sin reintento automático de mutaciones. Se mantiene recepción GGA durante consultas. Se bloquea reconfiguración con correcciones seleccionadas o grabación activa. No hay endpoint de comando libre y no se envía SAVECONFIG.

`POST /api/base/apply` recibe el mismo plan validado por `/api/base/plan`. Para coordenadas conocidas solo acepta WGS84, usa altura ARP elipsoidal calculada y UNDULATION=0. Promedio usa MODE BASE ID TIME. Después de 0.7.12, UNDULATION 0.0000 va en los dos métodos y el trabajo termina con SAVECONFIG, que solo se envía si el MODE leído es base. La respuesta final **base_mode_confirmed_coordinates_unverified** solo confirma modo: aún deben contrastarse coordenadas GGA, altura y convergencia antes de publicar correcciones. No se configura una base con coordenadas de prueba en el GPS real. La referencia de altura del panel sigue la configuración aplicada.

### Promedio del ESP32 · `/api/base/survey` (después de 0.7.12)

La GGA del receptor ya es la posición de la antena (`CONFIG ANTENNADELTAHEN 0 0 0`,
`include/receiver_baseline.h`), así que **la media se declara tal cual** en
`MODE BASE`. Hasta 0.7.12 se le sumaban además la altura de antena y el case, y
la base quedaba alta en esa cantidad. La altura de antena del operador solo sirve
para informar la cota de la marca (`include/base_plan.h`, `surveyHeights`):

| Campo | Significado |
| --- | --- |
| `height_to_set_m` | Altura elipsoidal que se declara: la media de la antena, sin sumas. Nula sin muestras |
| `mark_ellipsoid_height_m` | Nuevo. Cota elipsoidal de la marca en el suelo = media − `antenna_vertical_m` − `case_offset_m`. Informativa. Nula sin muestras |
| `antenna_vertical_m` | Nuevo. La altura de antena del último `start`. Nula si no se ha pedido promedio |
| `case_offset_m` | La constante única del case (0.10 m, no medida), la de `base_plan.h` |

Se cancela (`state: "cancelled"`, motivo en `reason`) si llega una época sin
posición o sin altura, si se pierde la calidad exigida, si pasan más de 3 s sin
GGA, o si al cumplirse el tiempo la última época aceptada tiene más de 2.5 s o
hay menos de la mitad de las épocas que daría 1 Hz (mínimo dos). Reglas y
motivos en `include/base_average.h`. Si la base queda aplicada pero el receptor no
confirma el `SAVECONFIG`, el estado es `applied` y `reason` lo dice.

«Usar coordenada actual» del panel rellena la altura **del suelo** = altura de la
antena − altura de antena del formulario − case, porque `/api/base/plan` trata
ese campo como suelo y le suma antena y case.

La alarma `receiver_silent` de `/api/status` salta con más de 5 s sin ninguna GGA
(`include/receiver_silence.h`), no solo con el contador de GGA en cero: así sale
en la misma sesión en que el receptor pierde sus salidas.

## NTRIP directo

`GET /api/ntrip/input`; `POST` con action=start, host, port, mountpoint, username, password. Stop usa solo action=stop. Una tarea separada conecta por Wi-Fi STA, valida respuesta ICY/HTTP y RTCM3 con CRC24Q, usa el router de fuente única y reintenta con espera 1–30 s. Sin tramas RTCM válidas durante 10 s se reconecta. Colas UART con caducidad de 2 s. El inicio exige lectura reciente de modo rover (30 s); el panel la solicita antes de conectar. Credenciales solo en RAM; no se devuelven ni se guardan en NVS. Al reiniciar hay que volver a conectar.

**Alcance inicial:** NTRIP v1/TCP, sin TLS ni envío GGA para servicios VRS. Encabezados de transferencia/codificación no soportados se rechazan. No equivale a compatibilidad con cualquier caster. El propietario configurará red de 2.4 GHz y cuenta después; la prueba de flujo RTCM real por Wi-Fi queda pendiente. Publicador y caster dentro del ESP32 siguen sin integrar; sus versiones de banco Mac son independientes.

## microSD preparada, todavía no habilitada

`sd_recorder` no configura GPIO si faltan TRESVIZO_SD_CS, TRESVIZO_SD_SCK, TRESVIZO_SD_MISO y TRESVIZO_SD_MOSI. No usar los pines de una compilación de prueba como una propuesta de cableado. Verificar niveles/alimentación de la carrier SD y pines disponibles antes de habilitar.

Con tarjeta configurada: cola de 32 KiB, tarea de disco separada, archivo original `/sessions/<id>/stream.part`, flush periódico y cierre con renombrado a stream.bin. Sesiones de hasta 64 MiB; errores de escritura o pérdidas conservan estado parcial. Manifiesto incluye bytes/pérdidas y declara sin validación PPK/antena. Catálogo muestra archivos parciales de arranques anteriores como interrumpidos. Esto no repara una FAT corrupta: corte de energía y extracción de tarjeta pendientes de ensayos físicos.

API: GET `/api/recording` y `/api/recording/sessions`; POST `/api/recording/start`, `/stop`; `/read` con session_id y offset devuelve hasta 384 bytes en base64. Lectura bloqueada mientras hay un archivo activo. Descarga solo HTTP o puente USB: BLE rechaza `/read`. Conversión RINEX continúa en la Mac. La grabación no garantiza que existan observaciones: activar/verificar el perfil crudo primero. No anuncia precisión ni RINEX disponible en tarjeta.

## BLE

El PIN se guarda en NVS la primera vez para conservarlo entre reinicios; se consulta solo por USB físico. Se mantiene Secure Connections + MITM y autenticación de comandos con la clave del instrumento. `tools/ble_probe.py` usa Bleak en la Mac, solicita emparejamiento al sistema, comprueba clave inválida, fragmentación de respuestas y bloqueo de acceso a credenciales. Puede requerir introducir el PIN en macOS. No elimina emparejamientos existentes ni relaja cifrado para pasar la prueba.

## Referencias

- Manual Unicore N4 R1.6 y CRC consultados en `docs/usb-bench.md`.
- SDK instalado Arduino-ESP32 2.0.17: `esp32-hal-psram.c`, configuración `esp32s3/dio_qspi`, `BLESecurity`.
- [Bleak en macOS](https://bleak.readthedocs.io/en/latest/backends/macos.html): emparejamiento al acceder a características protegidas.

## Evolución 0.6.0

El control UART descrito arriba se amplía con máscara de elevación,
constelaciones, salidas NMEA, perfil RTCM de base, edad máxima de correcciones y
persistencia explícita; las tasas pasan a 1/2/5/10/20 Hz. Contrato completo,
sintaxis verificada y límites en [configuración avanzada del receptor](gps-advanced.md).

Se mantiene que no existe endpoint de comando libre. Cambia la afirmación «no se
envía SAVECONFIG»: ahora puede enviarse, pero solo mediante una acción propia que
exige confirmación explícita, y sigue sin enviarse en ninguna otra operación.
(Superado desde 0.6.2: casi todo cambio termina con SAVECONFIG, y después de 0.7.12
también la base. Ver [configuración avanzada](gps-advanced.md#persistencia).)

La entrega del RTCM al receptor deja de ser invisible: `subsystems.gnss` publica
`correction_frames_sent` y `correction_frames_dropped`, y el binario nativo Unicore
publica `native_frames_valid` y `native_frames_invalid`. El consumo de la UART pasa
a hacerse por bloques en vez de byte a byte. Las correcciones de la auditoría están
en [el estado del proyecto](project-status.md).

## Alimentación Thing Plus

`GET /api/power` y `subsystems.power` informan voltaje, porcentaje estimado, aviso de batería baja, capacidad nominal 3000 mAh y estado de apagado. `charging`, `battery_present` y `usb_present` son null: no se deducen de la tensión del medidor. `POST /api/power/shutdown` devuelve 202 o 409 durante OTA. Tras aceptarlo, las operaciones de escritura quedan bloqueadas y el corte espera al escritor de memoria interna. `power_still_present` significa que el procesador continúa alimentado tras OFF, no que esté apagado. Reiniciar o retirar alimentación para volver a operar.
