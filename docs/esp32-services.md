# Servicios autónomos del ESP32 — 0.5.0

## Memoria

ESP32-S3FH4R2: PSRAM Quad habilitada con `BOARD_HAS_PSRAM` y `dio_qspi`, flash DIO de 4 MB sin cambiar particiones. El SDK inicializa y prueba PSRAM. Antes de iniciar servicios se reserva 1 MiB explícitamente en PSRAM, se escriben y leen tres patrones dependientes de dirección, y se libera. No es una prueba de envejecimiento ni temperatura. `/api/status.memory` distingue RAM interna libre/mínima/bloque mayor de PSRAM total utilizable/libre y resultado del ensayo. `ESP.getPsramSize()` informa capacidad del heap utilizable, ligeramente inferior a los 2097152 bytes físicos.

## Control UM980 por UART

GPIO18 RX y GPIO17 TX, 115200, COM2 del UM980. `GET /api/gnss/control` informa trabajo, modo, versión, errores y comandos completados. `POST` inicia un trabajo asíncrono y devuelve 202:

- `{"action":"query"}`: VERSIONA y MODE.
- `{"action":"rover"}`: MODE ROVER SURVEY, UNDULATION AUTO y lectura MODE.
- `{"action":"telemetry","hz":10}`: GPGGA COM2; frecuencias 1, 5 o 10 Hz.
- `{"action":"raw_profile"}`: OBSVMB COM2 1, efemérides GPS/GLO/GAL/BDS/BD3 cada 30 s. Requiere verificar capacidad del enlace a 115200 y almacenamiento; no se activa durante el ensayo inicial sin tarjeta.

El dueño de UART envía comandos y RTCM sin intercalar sus bytes. Un comando a la vez; ACK asociado al texto exacto, checksum XOR de control y CRC32 de VERSIONA, lectura MODE cuando procede. Timeout de respuesta 4 s: estado parcial/incierto, sin reintento automático de mutaciones. Se mantiene recepción GGA durante consultas. Se bloquea reconfiguración con correcciones seleccionadas o grabación activa. No hay endpoint de comando libre y no se envía SAVECONFIG.

`POST /api/base/apply` recibe el mismo plan validado por `/api/base/plan`. Para coordenadas conocidas solo acepta WGS84, usa altura ARP elipsoidal calculada y UNDULATION=0. Promedio usa MODE BASE ID TIME. La respuesta final **base_mode_confirmed_coordinates_unverified** solo confirma modo: aún deben contrastarse coordenadas GGA, altura y convergencia antes de publicar correcciones. No se configura una base con coordenadas de prueba en el GPS real. La referencia de altura del panel sigue la configuración aplicada.

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

La entrega del RTCM al receptor deja de ser invisible: `subsystems.gnss` publica
`correction_frames_sent` y `correction_frames_dropped`, y el binario nativo Unicore
publica `native_frames_valid` y `native_frames_invalid`. El consumo de la UART pasa
a hacerse por bloques en vez de byte a byte. Las correcciones de la auditoría están
en [el estado del proyecto](project-status.md).
