# Firmware inicial del instrumento

**Alimentación — 02/10/2026:** LiPo 1S 3.7 V / 3000 mAh confirmada. Lectura MAX17048 y apagado coordinado Mk2 implementados; falta identificar el elevador de 5 V y validar físicamente el conjunto con UM980. Ver `hardware/wiring.md` desde la raíz. La carga es autónoma por hardware; USB impide el corte total de batería.
## 0.8.0 — Thing Plus ESP32-S3 y OLED (02/10/2026)

Placa seleccionada: **SparkFun WRL-24408, MINI-1-N4R2**. La definición local `boards/sparkfun_thing_plus_esp32s3.json` fija flash de 4 MB, PSRAM Quad de 2 MB, USB CDC/JTAG y el perfil de CPU. El entorno sigue llamándose `esp32s3_usb` para mantener las rutas de las herramientas. El cableado está en [hardware/wiring.md](../../hardware/wiring.md); las referencias posteriores a Tiny/18/17 son históricas.

- UART del UM980: **RX44/TX43**, COM2 a 115200. Pines centrales en `include/board_profile.h`.
- OLED SSD1306 128×64: **SDA8/SCL9**, dirección 0x3C o 0x3D, alimentación 3.3 V. Estado GNSS, satélites, RTCM, microSD e IP. Una tarea propia refresca a 1 Hz; sin GGA fresca en dos segundos deja de afirmar FIX. Sin pantalla continúa el resto del equipo. La ficha Tecneu indica SSD1306 o compatible; validar el controlador de la unidad recibida.
- Socket microSD integrado: **SD_MMC a cuatro bits / 20 MHz**, CLK38, CMD34, D0/1/2/3=39/40/47/33 y detección48 activa alta. Insertar FAT32 antes de encender. Sin formateo automático; después de retirar/reinsertar, reiniciar para montar. Se conserva el registro `.part`/`.bin` y la cola UART. Una extracción durante grabación no permite marcar la sesión completa.
- GPIO45 habilita únicamente el regulador de periféricos integrado. **Soft Power Switch Mk2:** PUSH=GPIO10/A0, OFF=GPIO14/A1; cierre antes del corte y lectura MAX17048.
- `/api/status` añade `hardware_id`, `board` y `subsystems.display`; microSD informa detección e interfaz. El `hardware_id` es **`tresvizo-thingplus-s3-4m-v1`**.
- La imagen conserva versión en byte 288 y añade identidad de placa en byte 320 (48 bytes, NUL). Ese campo pertenece a la imagen firmada: OTA y rollback rechazan otra placa aunque el manifiesto diga Thing Plus. Se conservan los registros de firma verificada introducidos en 0.7.14.
- Empaquetador, actualizador USB y cargador gráfico reconocen esta identidad. Para la placa nueva usar **Instalación completa** o `pio run -e esp32s3_usb -t upload` con su puerto confirmado. No cargar el binario nuevo a la Tiny.
- Panel adaptado: Diagnóstico muestra placa, UART, OLED y microSD desde la API. Registro bloquea acciones durante cierre y al perder el enlace; descargas incompletas conservan `.part`. `closing` se publica separado de `active` para reflejar el archivo aún ocupado en un cierre parcial. Puente USB y diagnóstico BLE actualizados. Detalle y pruebas de software en [panel-campo.md](../../docs/panel-campo.md).
- El almacenamiento se presenta como **Memoria interna del dispositivo**; la OLED muestra **MEM INT.** y la API añade `storage_label` para aplicaciones. Corregido el inicio de grabación desde el estado real `idle`, que el panel anterior no reconocía. La prueba local recorre inicio, parada, espera de cierre y descarga de contenido binario por bloques; no valida la escritura física.

**Verificado en esta entrega:** compilación y firma, 24 pruebas C++ host, 14 pruebas del banco GNSS, 12 pruebas del cargador (incluido el binario real), panel GNSS y preflight OTA del panel. La adaptación posterior del software añade pruebas de estados OLED/microSD, descargas y pérdida de enlace, más 14 pruebas de análisis BLE e inspección del panel en navegador con datos de prueba. La compilación final ocupa 101,024 bytes de RAM estática y 1,712,161 bytes de flash de aplicación (87.1% del slot). El paquete local está en `data/local/releases/0.8.0/`.

**Sin probar físicamente:** carga/arranque en Thing Plus, respuesta de la OLED, microSD/retirada de tarjeta, transición base/rover, OTA/rollback y estabilidad del conjunto. No se flasheó ningún equipo, se rediseñó la alimentación ni se modificó la carcasa. Las cifras históricas de validación de Tiny no se trasladan a esta placa.

## Historial anterior a Thing Plus


Versión 0.6.2 para el ESP32-S3 conectado por USB. El perfil usa 4 MB de flash comprobados por esptool. La placa de referencia de PlatformIO aporta la configuración de CPU/USB; no identifica la carrier como DevKitC ni autoriza sus pines externos. PSRAM Quad de 2 MB habilitada, con prueba de integridad y métricas separadas de RAM interna.

## Funciones del primer firmware

- Arranque sin esperar a que se conecte una consola USB.
- Red Wi-Fi propia protegida con una clave aleatoria por equipo, persistida en NVS y recuperable por acceso físico USB.
- Panel web en español con la identidad visual y el logo de TresVizo; los recursos están comprimidos en flash. No requiere microSD ni Internet.
- Estado real del controlador: tiempo encendido, memoria, flash, firmware y Wi-Fi.
- Ajustes persistentes: nombre, intervalo del panel y conexión a un hotspot protegido de 2.4 GHz. El AP permanece activo.
- Validación de tipos y límites, detección de conflictos de revisión y guardado de la configuración en una sola entrada NVS. Las solicitudes inválidas no modifican ajustes.
- Servidor HTTP de ESP-IDF con límites de cuerpo y espera; exclusión mutua para acceso desde HTTP/USB.
- Consola JSON USB con buffer acotado, tiempo límite y recuperación tras mensajes demasiado grandes.
- Reinicio solicitado y exportación de diagnóstico sin contraseñas ni nombres de redes.

Esa lista describe el primer firmware. GNSS, microSD, NTRIP, BLE y modos base/rover llegaron después; su estado real está en las secciones de versión de más abajo. Siguen sin implementarse la IMU y la compensación de inclinación, y la app de campo sigue sin iniciarse. No hay posiciones ni soluciones FIX simuladas.

## Compilar y cargar desde macOS

Abrir esta carpeta en VS Code con PlatformIO. Se usa PlatformIO Espressif32 6.12.0, Arduino-ESP32 2.0.17 y ArduinoJson 7.4.2. Esta base permite un primer arranque reproducible con las herramientas instaladas; los controladores posteriores pueden usar APIs ESP-IDF sin acoplarlos al panel.

Desde esta carpeta:

```sh
~/.platformio/penv/bin/pio run
~/.platformio/penv/bin/pio device list
~/.platformio/penv/bin/pio run -t upload --upload-port /dev/cu.usbmodem11201
```

El puerto puede cambiar. Detener el puente USB y cerrar otros monitores antes de cargar. La carga inicial contó con respaldo completo local de la flash, excluido de Git. No usar `erase_flash` como preparación habitual; borraría también ajustes y clave.

Los recursos web se empaquetan al compilar, sin `uploadfs`.

### Actualización por OTA: solo firmware firmado (desde 0.7.13)

Las dos particiones de aplicación permiten actualizar sin cable desde el panel,
las apps o `tools/firmware_upload.py` (por USB). **El equipo solo instala
`firmware-signed.bin`**: `firmware.bin` seguido de 72 bytes con la firma ECDSA
P-256 del propietario. `pio run` lo deja junto a `firmware.bin`
(`.pio/build/esp32s3_usb/`) si la clave privada está en la Mac; sin ella avisa y
compila igual, y `firmware.bin` sigue valiendo para cargar por USB con
`pio run -t upload`. Clave, respaldo y firma a mano en
[`tools/firmware_signing/`](../../tools/firmware_signing/README.md).

- `begin` recibe tamaño y SHA-256 del **archivo firmado**, como antes; a la flash
  solo va la imagen. En `finish`, tras el SHA del archivo, se comprueba la firma
  con la clave pública embebida (`include/firmware_signing_key.h`) **antes** de
  validar la imagen y de tocar el arranque. Sin firma: «El firmware no trae la
  firma del propietario. Usa el archivo firmware-signed.bin.» Firma que no
  verifica: «La firma del firmware no es válida; no se instala.» En los dos casos
  se invalida la partición destino y el arranque no cambia (estados
  `signature_missing` y `signature_invalid`).
- `/api/update/rollback` solo vuelve a una imagen que **también exija firma**
  (0.7.13 o posterior); si no, 409 «La imagen anterior no exige firma; no se
  restaura por la API. Usa el cable USB.». Volver a 0.7.12 reabriría la carga de
  firmware ajeno. La versión de la otra partición se lee de una identidad propia
  en el byte 288 de la imagen (`.rodata_custom_desc`), porque en Arduino-ESP32
  `esp_app_desc_t.version` dice siempre «esp-idf: v4.4.7 38eeba213a».
- `GET /api/update` informa `image_authenticity: "owner_signed_ecdsa_p256"`,
  `signature_required: true` y `previous_image_signature_required`.
- Formato y lógica en `lib/protocol/src/signed_firmware.h`, probados en
  `test/signed_firmware_test.cpp`. La verificación ECDSA en sí es de mbedtls y
  solo corre en el equipo.

## Abrir el panel

### Por USB desde la Mac

Desde la raíz del repositorio:

```sh
~/.platformio/penv/bin/python tools/usb_console.py serve
```

Abrir `http://127.0.0.1:8765`. El puente entrega los archivos web locales y obtiene estado y configuración del ESP32 real por USB. No contiene simulación. Sus archivos deben corresponder al firmware cargado. Solo escucha en loopback, restringe Host/Origin y exige una cabecera propia en la API. Usa el acceso físico USB para autenticar, sin devolver la clave al navegador.

Ctrl+C detiene el puente y libera el puerto. Con el puente abierto no debe usarse otro monitor serie. Al desconectar el equipo, la interfaz muestra pérdida de comunicación y oculta los valores anteriores; vuelve a intentar la conexión.

### Por Wi-Fi del instrumento

Con el puente detenido, consultar localmente la red y clave:

```sh
~/.platformio/penv/bin/python tools/usb_console.py access
```

Este comando muestra una credencial privada: no subir su salida al repositorio. Conectar el teléfono a la red `TresVizo-…`, abrir `http://192.168.4.1` e introducir la misma clave en el panel. La clave se mantiene solo en memoria de la pestaña; recargar puede exigir introducirla de nuevo.

El HTTP del prototipo depende de la protección y confianza de la red Wi-Fi. No exponerlo a Internet. Las credenciales de hotspot se guardan en NVS sin cifrado de flash; endurecimiento de credenciales y transporte queda pendiente antes de uso fuera del prototipo.

## API versión 1

Desde 0.6.2 ninguna ruta pide clave (`X-Device-Key` se retiró). No hay CORS habilitado.

| Método y ruta | Comportamiento |
| --- | --- |
| `GET /api/status` | Estado real, capacidades pendientes y campos GNSS nulos. |
| `GET /api/config` | Ajustes, revisión y disponibilidad NVS. Por HTTP y USB incluye `ap_password` (el panel la lee y la reenvía); **por BLE sale sin ella** desde 0.7.13. Las contraseñas de redes externas y NTRIP no salen nunca. |
| `PUT /api/config` | Actualización parcial con `revision` obligatoria; 409 si está obsoleta. |
| `POST /api/restart` | 202; programa reinicio después de responder. |

Cuerpo HTTP máximo: 1024 bytes; JSON con profundidad limitada. El nombre admite 1–32 caracteres ASCII de letras, números, espacios y guiones, sin espacios extremos. Intervalos del panel: 1000, 2000 o 5000 ms. El SSID admite hasta 32 bytes UTF-8; contraseñas de hotspot, 8–63 caracteres ASCII imprimibles. No se admiten redes abiertas en esta etapa. Vacío conserva la contraseña solo para la misma red; cambiar SSID exige contraseña nueva. `forget_wifi: true` elimina la red externa. Guardar sin cambios no vuelve a escribir en NVS.

La consola USB recibe una línea JSON de hasta 1024 bytes con `id`, `method`, `path`, `key` y `body` opcional; responde con `id`, `status` y `body`. Solo por USB existe `GET /api/access`, sin clave, para recuperar acceso físico. La consola es para diagnóstico; no fija el futuro protocolo BLE.

Las unidades de diagnóstico se indican en los nombres: milisegundos, bytes, MHz y dBm. El tiempo encendido es monotónico y no equivale a época GNSS. Las futuras mediciones deberán distinguir tiempo de medición, llegada, marco y referencia de altura.

## Verificación

Desde esta carpeta:

```sh
clang++ -std=c++11 -Wall -Wextra -Werror -I include test/config_rules_test.cpp -o /tmp/tresvizo-config-test
/tmp/tresvizo-config-test
node --check web/app.js
```

`test/secret_redaction_test.cpp` necesita además ArduinoJson, que queda en
`.pio/libdeps/` tras un `pio run`: añadir
`-I .pio/libdeps/esp32s3_usb/ArduinoJson/src`.

Desde la raíz, con el puente detenido:

```sh
~/.platformio/penv/bin/python tests/hardware_smoke.py
```

La prueba de hardware guarda ajustes temporales, reinicia el equipo y restaura los ajustes originales. No ejecutarla durante una operación de campo. Consultar los resultados y pendientes en `docs/firmware-validation.md`.


## Cambio de clave del equipo (0.2.0, retirado en 0.6.2)

> **Esta sección es histórica.** Desde 0.6.2 no hay clave de panel y el
> subcomando `set-access` se eliminó de `usb_console.py`. La contraseña del
> Wi-Fi propio es la única credencial y se cambia desde Configuración.

Con el puente detenido, ejecutar `python tools/usb_console.py set-access` e introducir dos veces la nueva clave en el prompt oculto. La operación solo existe por USB, requiere la clave actual (la consola la recupera por acceso físico), valida 8–63 caracteres ASCII imprimibles y reinicia después de guardar en NVS. Una solicitud inválida no cambia la clave. La clave anterior permanece activa hasta el reinicio; la nueva no se incluye en la respuesta ni en estado/configuración. No pasar credenciales como argumentos del shell ni guardarlas en el repositorio.

El panel representa estado GNSS, calidad y coordenadas recibidas por el ESP32, diferenciando datos antiguos y falta de posición. La tarea UART y el parser compartido se describen en [adquisición GNSS](../../docs/gnss-bringup.md). En 0.4.1 se habilita UART2 a 115200: RX GPIO18, TX GPIO17, tras confirmar el cableado TTL cruzado y GND común. Ambos equipos mantienen alimentación USB separada, sin unir alimentación. Tener ambos USB en la Mac por sí solo no los comunica.


## Apartados de operación (0.3.0)

El panel incluye Base / rover, Registro / PPK y Correcciones (entrada, publicación y caster local). El preparador de base valida datos y calcula altura elipsoidal ARP; permite exportar un plan JSON. No aplica comandos ni persiste ese plan. Los controles de registro/transferencia/cambio de modo permanecen deshabilitados con su motivo real.

- `GET /api/operations`: capacidades actuales; catálogo de sesiones nulo mientras no pueda consultarse almacenamiento.
- `POST /api/base/plan`: preparación autenticada con `method` (`known`/`average`) e `station_id`; devuelve `applied: false` y `persisted: false`. Los campos y límites se describen en [registro, base y NTRIP](../../docs/recording-base-ntrip.md).
- `python tests/operations_smoke.py`: valida la API en el ESP32 sin cambiar modo, guardar coordenadas ni transmitir correcciones.

## Versión 0.4.0

- Servicio BLE de control autenticado y telemetría; [protocolo y límites](../../docs/ble-protocol.md).
- OTA en doble partición, SHA-256, carga por bloques y recuperación; [paquetes y procedimiento](../../docs/firmware-updates.md).
- Router de correcciones desacoplado; solo BLE instalado en el firmware, UART aún deshabilitado sin verificar cableado.
- [Banco USB de Mac](../../docs/usb-bench.md) con GPS real, sesiones, conversión RINEX y NTRIP. No confundir sus controladores con capacidades autónomas del ESP32.

Las pruebas del controlador OTA están en `tests/update_smoke.py`; `--install` escribe la imagen compilada en la partición inactiva, reinicia y verifica el cambio de slot. No correr junto al puente USB ni a otro monitor.


## Versión 0.5.0

Control bidireccional UM980, PSRAM verificada y cliente NTRIP directo; microSD preparada sin activar pines hasta cableado. Ver [servicios autónomos](../../docs/esp32-services.md) para API, límites y pruebas. BLE comprobado con la Mac: cifrado, autenticación, fragmentación y consulta del UM980 a través del ESP32.


## Versión 0.6.0

### Credenciales separadas — leer antes de actualizar

La contraseña del Wi-Fi propio y la clave del panel/API dejan de ser la misma
cadena. **Al arrancar esta versión sobre un equipo anterior se genera una
contraseña Wi-Fi nueva**, de modo que el teléfono no podrá reconectarse con la
credencial guardada. Con el puente detenido:

```sh
python tools/usb_console.py access
```

Ese comando ahora imprime las dos credenciales etiquetadas por separado, más el PIN
de emparejamiento BLE. Su salida es privada: no subirla al repositorio.
`set-access` sigue cambiando únicamente la clave del panel/API; la rotación de la
contraseña del AP desde el panel está pendiente.

El motivo del cambio: hasta 0.5.0, dar acceso al Wi-Fi equivalía a entregar el
control total del instrumento, incluida la carga de firmware, que no está firmado.

### Panel reorganizado para campo

Pantalla inicial **Campo**, con calidad de solución y coordenadas en un mismo
bloque grande, más satélites, HDOP, edad de la última época y tramas RTCM
entregadas al receptor. UART, memoria, versiones y estado de integración pasan a
Diagnóstico. Criterio completo en [panel de campo](../../docs/panel-campo.md).

### Configuración avanzada del GPS

Nueva sección del panel y nuevas acciones de `POST /api/gnss/control`: máscara de
elevación, constelaciones, salidas NMEA, perfil RTCM de base, edad máxima de
correcciones, detener salidas, leer configuración y `SAVECONFIG` con confirmación
explícita. Las tasas admitidas pasan a 1, 2, 5, 10 y 20 Hz. Sintaxis verificada
contra el manual Unicore N4 R1.6; comandos y límites en
[configuración avanzada del receptor](../../docs/gps-advanced.md).

Sigue sin existir un endpoint de comando libre: cada acción arma una secuencia fija
validada antes de enviar nada al receptor.

### Cambios en la API

| Ruta | Cambio |
| --- | --- |
| `GET /api/gnss/profile` | Nueva. Configuración avanzada conocida, distinguiendo lo aplicado de lo asumido por defecto. |
| `GET /api/status` | `solution.hdop` añadido; `solution.measurement_time` retirado por estar siempre vacío y sin consumidores. |
| `GET /api/status` | `subsystems.gnss` añade `correction_frames_sent`, `correction_frames_dropped`, `native_frames_valid` y `native_frames_invalid`. |
| `POST /api/gnss/control` | Acciones nuevas y tasas 2 y 20 Hz; `GET` añade `total_commands`. |
| `GET /api/access` (solo USB) | Añade `ap_password`. |

### Correcciones de la auditoría

Plazo global para los trabajos GNSS, consumo de la UART por bloques en vez de por
byte, resincronización del parser RTCM sin coste cuadrático, `Correction` fuera de
la pila de la tarea, cabeceras NTRIP sin concatenación cuadrática, y castes
explícitos en `isxdigit`/`isalnum`. El detalle está en
[el estado del proyecto](../../docs/project-status.md).

El watchdog de las tareas propias existe tras `-DTRESVIZO_TASK_WDT` pero queda
**desactivado por defecto**: convierte un bloqueo en un reinicio y ese cambio no se
ha ensayado.

### Verificación de esta entrega

Ejecutado y correcto:

```sh
node --check web/app.js
node tests/gnss_panel_test.js
python -m py_compile tests/device_services_smoke.py tools/usb_console.py
```

Compilación y carga, ejecutadas en Windows con PlatformIO Core 6.2.0:

```sh
python -m platformio run -e esp32s3_usb
python -m platformio run -e esp32s3_usb -t upload --upload-port COM4
```

La compilación termina en `[SUCCESS]`: 22,6 % de la RAM interna (73.984 de 327.680
bytes) y 74,3 % de la partición de aplicación (1.461.545 de 1.966.080). La carga
verifica el hash de los 1.461.904 bytes escritos y, tras el reinicio, el equipo
imprime `TresVizo RTK 0.6.0. Consola JSON USB disponible.` por la consola USB.

**No ejecutado:** `tests/device_services_smoke.py`. Arrancar no es validar: ninguna
función de esta versión —panel, NTRIP, configuración del GPS, BLE, microSD— se ha
comprobado sobre el equipo real.

### Herramientas en Windows

`tools/usb_console.py` importaba `fcntl` y `termios`, que solo existen en POSIX, de
modo que no arrancaba en Windows. Ahora esos módulos son opcionales: en Windows el
puerto ya se abre en exclusiva y pyserial rechaza una segunda apertura, así que no
hace falta el refuerzo con `TIOCEXCL`.

La distribución de Python de la Microsoft Store trae `install.user = yes` fijado a
nivel *site*, de modo que PlatformIO falla al instalar las dependencias de
`tool-esptoolpy` con `Can not combine '--user' and '--target'`. Anteponer
`PIP_USER=0` al comando lo evita sin tocar configuración global. Si una descarga
de paquete se interrumpe, el toolchain queda a medio extraer y la compilación
falla con `fatal error: stdint.h`; se corrige borrando
`~/.platformio/packages/toolchain-xtensa-esp32s3` para que se reinstale.


## Versión 0.6.2

### El equipo se llama MeridianV

Nombre y SSID fijos, no editables desde el panel: la red que emite tiene que ser
reconocible en campo sin consultar a nadie. 3Vizo sigue siendo la marca del
panel. **Sin sufijo de MAC**: dos equipos encendidos en la misma obra emitirán
redes con nombre idéntico.

### Se retiró la clave del panel

El panel y la API **ya no piden clave**. `X-Device-Key`, el cambio de clave por
USB y el diálogo de acceso desaparecieron. La contraseña del Wi-Fi propio es la
única credencial del equipo, sale de fábrica como `TresVIzoRTK` y se cambia desde
Configuración.

Consecuencia que conviene tener presente: **la carga de firmware por OTA no lleva
firma**, así que quien alcance la red del equipo puede sustituir su firmware.
Decisión explícita del propietario para un instrumento de campo.

### Bluetooth sin emparejamiento, con interruptor

Se retiraron el PIN y el cifrado MITM. Cualquier equipo dentro del alcance puede
conectarse y escribir en las características. A cambio, BLE se enciende y apaga
desde Conexiones y ese ajuste se guarda en NVS.

Se añadió una característica de salud (`a04c0006-…`) a 1 Hz con sigma horizontal
y vertical en milímetros, antigüedad de correcciones, fuente activa y calidad de
solución. El byte de IMU está reservado y vale siempre 0: **no hay IMU**.

Las correcciones por BLE se rechazan mientras el receptor trabaja como base.

### Redes Wi-Fi: hasta cinco, con autoconexión

El equipo guarda cinco redes, escanea al encender y se une a la de mejor señal
entre las que estén realmente a la vista. Cada red admite **dirección fija
opcional** (IP, puerta de enlace y máscara) o DHCP; la dirección es por red y no
global, porque con varias subredes una sola IP fija sería correcta en una y
errónea en el resto. El equipo responde además a `meridianv.local`.

| Ruta | Comportamiento |
| --- | --- |
| `GET /api/wifi/networks` | Redes guardadas, tope y dirección de cada una. |
| `POST /api/wifi/networks` | `ssid`, `password`, `ip`, `gateway`, `mask` añade o edita; `forget` elimina. |
| `POST /api/wifi/scan` | Inicia un escaneo asíncrono. **Interrumpe el AP propio** unos segundos. |
| `GET /api/wifi/scan` | Estado y redes vistas, con señal y si ya están guardadas. |

### Perfiles NTRIP y lista de puntos de montaje

Cinco perfiles persistentes con contraseña. El equipo se reconecta solo al último
usado, también tras un corte de corriente. «Ningún perfil» es una elección que
también se guarda. La autoconexión no exige confirmar modo rover, al contrario
que el arranque manual: pedirlo obligaría a tocar el panel tras cada reinicio.

| Ruta | Comportamiento |
| --- | --- |
| `GET /api/ntrip/profiles` | Perfiles, tope, seleccionado y si hay autoconexión. |
| `POST /api/ntrip/profiles` | `save`, `delete`, `select` (nombre nulo = ninguno) y `connect`. |
| `POST /api/ntrip/sourcetable` | Pide al caster su lista de puntos. Requiere el flujo detenido. |
| `GET /api/ntrip/sourcetable` | Puntos publicados, formato y si exigen GGA. |

### Salida de correcciones

Entrada y salida quedan separadas en el panel, con hueco previsto para radio en
ambos sentidos. El RTCM que emite el receptor se reconstruye desde la UART y
alimenta dos destinos simultáneos:

| Ruta | Comportamiento |
| --- | --- |
| `GET/POST /api/ntrip/server` | Publicación hacia un caster externo (NTRIP v1, `SOURCE`). |
| `GET/POST /api/ntrip/caster` | Caster propio del equipo, hasta dos rovers. |

Ambos se guardan en NVS y **se reanudan tras un reinicio**. El juego de mensajes
por defecto usa MSM7 (1005, 1033, 1077, 1087, 1097, 1127) para aprovechar la
triple banda; MSM4 queda disponible por compatibilidad. Los mnemónicos MSM7 se
añadieron por numeración estándar RTCM y **no se contrastaron con el manual
Unicore**.

**Sin verificar:** ni la publicación ni el caster se han probado contra un caster
real o un rover. Solo consta que el caster abre el puerto y escucha.

### Modo base reescrito

- Marco **siempre WGS84** y altura **siempre elipsoidal**. Se retiraron los
  campos de datum, época de coordenadas y «la altura corresponde a»: el equipo no
  transforma coordenadas, así que declararlo no tenía efecto.
- La altura introducida es la del punto en el suelo. Se le suma la altura de
  antena medida y **10 cm de case**, constante declarada en `base_plan.h` que
  **todavía no se ha medido sobre la carcasa real**.
- **Un solo botón de acción visible.** El origen de la coordenada es un selector
  segmentado —usar la actual o promediar— y según lo elegido aparece «Estacionar
  la base aquí» o «Iniciar promedio», nunca ambos. Se retiraron el paso de
  validación por separado, la exportación a JSON, que no salía del navegador, y
  el desplegable «Origen de coordenadas», que duplicaba exactamente el selector.
- El papel del receptor y el botón «Usar como rover» están arriba del todo. **El
  modo se consulta solo**; no hay botón de consultar porque el equipo ya sabe
  preguntárselo al receptor.

**Estacionar una base no la hace emitir correcciones.** Hay que aplicarle además
el juego de mensajes RTCM desde Correcciones. `GET /api/status` expone
`corrections_out.frames_from_receiver` justamente para distinguir «la base no
emite» de «nadie se ha conectado a recoger lo que emite».

**Estacionar cierra la entrada de correcciones por su cuenta**, igual que cambiar
de papel. Pedirle al usuario que vaya a otra pestaña a detener algo que él no
inició, para poder hacer lo que acaba de pedir, era trasladarle nuestro orden
interno.

### Promedio de coordenadas en el ESP32

`POST /api/base/survey` promedia en el controlador, no en el receptor. El UM980
sabe promediar solo, pero no distingue con qué calidad lo hace ni avisa si la
pierde: promediar cien épocas autónomas da una coordenada muy repetible y
exactamente igual de equivocada.

Se elige la calidad exigida (`rtk_fixed`, `rtk_float`, `standalone` o `any`) y el
tiempo, **de 2 a 900 s**, con 30 s por defecto. Dos segundos son veinte épocas a
10 Hz: con solución fija es un promedio legítimo, y exigir más era una regla
inventada. **Si la calidad se pierde a mitad, el promedio se cancela y se explica
por qué.**

El panel muestra barra de progreso, épocas usadas y la coordenada que se va
formando, desde el instante del clic y no desde la primera respuesta del equipo.

Estados: `averaging` mientras acumula, **`applying` mientras el receptor decide**
y `applied` solo cuando el receptor **confirma** el modo base. Antes decía
`applied` en cuanto se lanzaba el trabajo, que no es lo mismo: el receptor podía
seguir en rover y el panel lo daba por hecho.

### Precisión estimada

Parser NMEA **GST** nuevo (`lib/gnss/src/nmea_gst.h`). `GET /api/status` añade
`solution.horizontal_sigma_m` y `vertical_sigma_m`. Es la desviación típica que
declara el receptor, no una exactitud comprobada contra una referencia externa.
`telemetry` activa `GPGST COM2 1` junto a GGA: la sigma no cambia a 10 Hz.

### Endurecimiento

- **`SAVECONFIG` automático** tras cualquier cambio de configuración del receptor,
  incluido el modo base. Sin esto, una base que perdía corriente volvía en el modo
  anterior y seguía emitiendo correcciones desde una coordenada equivocada: los
  rovers fijaban con buena pinta sobre un punto que no era.
- **Watchdog activo** (`-DTRESVIZO_TASK_WDT`). Vigila la tarea de adquisición del
  GPS; un bloqueo pasa de dejar el equipo sordo a reiniciarlo en segundos. **No
  vigila** las tareas de NTRIP, de salida ni el bucle principal. Si llega a
  actuar, el panel lo dice: un reinicio silencioso que «se arregló solo» es justo
  el dato que hace falta para encontrar el bloqueo de fondo.
- **El modo del receptor se consulta solo** cinco segundos después de arrancar.
  Sin ese dato, el guardia que impide que una base consuma correcciones no puede
  decidir, y el panel tendría que pedirle al usuario que pulse un botón para
  saber algo que el equipo puede averiguar por su cuenta. El papel informado **no
  caduca**: antes usaba la ventana de 30 s de `roverReady()`, que existe para
  autorizar conexiones y no para informar, y el panel volvía a «sin confirmar».
- **Alarmas** en `GET /api/status` (`alerts`): receptor mudo, UART caída,
  correcciones detenidas, sin redes guardadas, reinicio por pánico, por caída de
  tensión o por watchdog, y las dos contradictorias —base con entrada de
  correcciones activa, y publicación sin modo base—.
- **La entrada NTRIP no convive con el modo base.** No arranca en un equipo que ya
  es base, y si se encuentra conectada en uno que lo es, se suelta sola.
- **Al volver a rover, las correcciones vuelven sin que nadie las pida.** El
  firmware distingue «lo detuvo el usuario» de «lo soltó el equipo para
  estacionar»: lo primero se respeta, lo segundo se deshace. Respetar una decisión
  del usuario y deshacer un apaño nuestro no son lo mismo.
- **Las consultas de solo lectura funcionan con correcciones activas.** Antes el
  guardia bloqueaba también las lecturas, y no se podía saber en qué modo estaba
  el receptor justo cuando más falta hacía.
- La entrada NTRIP se suelta sola si pasa más de un minuto esperando red: dejarla
  esperando fijaba el enrutador y bloqueaba configurar el GPS.

### Verificación de esta entrega

Comprobado sobre el equipo, no deducido del código:

- Compilación y carga; el panel reporta la versión que corre.
- Escaneo Wi-Fi con 13 redes reales; guardar, olvidar y fijar o liberar dirección.
- Reconexión completa tras reinicio: red guardada, perfil NTRIP, correcciones y
  RTK flotante, sin intervención.
- Precisión GST con valores reales; interruptor BLE encendiendo y apagando.
- **Ciclo completo rover → base → rover**: la base queda confirmada, la entrada
  NTRIP se cierra sola, y al volver a rover se reanuda sola y recupera RTK.
- **La base produce RTCM de verdad**: 1482 tramas capturadas del receptor tras
  aplicarle el juego de mensajes.
- **El modo base sobrevive a un reinicio**, gracias al `SAVECONFIG` automático.
- **El caster local se reanuda solo** tras un reinicio y queda escuchando.
- La alarma `publishing_without_base` salta cuando el caster queda encendido con
  el receptor en rover.
- Watchdog sin reinicios espurios durante la prueba (minutos, no días).

**No ejecutado ni una vez:** publicación NTRIP contra un caster externo, el caster
local **sirviendo a un rover real** —solo consta que abre el puerto y escucha—,
lectura de sourcetable, resolución de `meridianv.local`, conexión con dirección
fija aplicada, y los paquetes BLE, que necesitan una app que todavía no existe.
`tests/hardware_smoke.py`, `tests/operations_smoke.py` y `tools/ble_probe.py` se
pusieron al día con 0.6.2 —sin clave de acceso, sin PIN y con el nombre fijo—,
pero no se han vuelto a ejecutar contra el equipo.

Los mnemónicos MSM7 se añadieron por numeración estándar RTCM y **no se
contrastaron con el manual Unicore**; el receptor aceptó el juego por defecto en
banco, que no es lo mismo que haberlo verificado contra la documentación.

## Versión 0.7.5

Entrega del 26-09-2026. Durante las pruebas se cargaron 0.7.1 a 0.7.4 como pasos
intermedios; **no usar 0.7.1**, que se reinicia por panic con GSV y GSA activas.

### Satélites rastreados y precisión por eje, en el panel y en la telemetría

Hasta 0.7.0 el panel y la telemetría daban los satélites **usados**, la cifra de
GGA, y una precisión horizontal combinada. Con la antena afuera de una ventana el
UM980 rastreaba unos 30 satélites y usaba de 16 a 21, y la combinada salía √2
mayor que el RMS por eje con el que otros equipos dan su precisión. Por decisión
del propietario, Campo y la telemetría enseñan ahora lo mismo:

- **Satélites rastreados**, de GSV. `GET /api/status` → `solution.satellites_tracked`
  (se omite sin GSV reciente); `satellites_used` sigue en la API.
- **Precisión horizontal del peor eje**, la mayor de `solution.north_sigma_m` y
  `solution.east_sigma_m`. `horizontal_sigma_m` sigue siendo la combinada.
- BLE y WebSocket **cambian el significado de dos campos**: byte 3 de la solución
  = rastreados, y sigma horizontal de la salud = peor eje. El byte 10 de la salud
  lleva los usados. **0.7.7 devuelve los usados al byte 3 y pasa los rastreados
  al byte 10**; ver abajo. Detalle y compatibilidad en
  [el protocolo BLE](../../docs/ble-protocol.md#salud-20-bytes-little-endian-1-hz).
- `GET /api/gnss/sky` añade `tracked`.

El receptor tiene que mandar GSV y GSA por COM2, que es lo que hace la acción
`telemetry`. Un equipo configurado antes de que esa acción las incluyera no las
manda hasta que se vuelve a aplicar.

La tabla del cielo pasa de 72 a 192 observaciones: con triple banda y máscara de
5° ya llegaban 75 desde una ventana. Cuesta unos 7 KB de RAM interna.

### La tarea UART pasa de 4 a 8 KiB de pila

Con 0.7.1 y GSV/GSA activas por COM2, el equipo se reinició por panic tres veces
en unos doce minutos (`reset_reason_code` 4, alerta `last_reset_panic`). La
consola USB solo alcanzó a mostrar `Backtrace: 0xfffffffe:0x80381d74 |<-CORRUPTED`,
la traza de una pila pisada. `-fstack-usage` dio el camino más hondo de
`gnss_rx`: `acquire` 2112 bytes, su lambda 192 y `correction_output::publish`
1072. Con 8 KiB, la tarea llegó a usar **4092 bytes**: con la pila de 4096 no
quedaba nada. El fallo venía de antes; lo destapó activar GSV y GSA.

`/api/status` publica `memory.stack_free_min_bytes`: lo menos que ha tenido libre
cada pila desde el arranque, para `gnss_rx`, `ntrip_rx`, `rtcm_out`, `httpd` y
`loopTask`.

### La fuente de correcciones elegida sobrevive a un reinicio

Quien elegía BLE desde la app y reiniciaba volvía a NTRIP: la elección vivía en
RAM y la autoconexión del perfil la pisaba al arrancar. Ahora la elección
explícita —`PUT /api/corrections/source`, arrancar NTRIP a mano o conectar un
perfil— se guarda en NVS. Si fue BLE, al encender se restaura BLE y NTRIP no se
autoconecta; pasar a móvil también la devuelve. `GET /api/corrections/source`
añade `chosen_source`, la que se restaurará.

### Verificación de esta entrega

- `test/sky_table_test.cpp`, `nmea_gsv_test.cpp` y `nmea_gsa_test.cpp`
  compilados con MSVC `/W4` y ejecutados: correctos y sin avisos.
- `tests/gnss_panel_test.js` pasa. **Estaba roto desde antes**: el contexto de
  la prueba no tenía `latestStatus` ni `$`, que `renderGnss` usa desde que pinta
  el indicador de fix. Se añadieron.
- Compilación con `-Wall -Wextra` sin avisos nuevos; cada carga OTA verificada
  por `tools/firmware_upload.py`, con ajustes conservados.
- En el equipo: `satellites_tracked` igual a la lectura directa del UM980 por su
  USB; `dropped` 0; diez minutos con 0.7.2 sin reinicios; el WebSocket manda
  rastreados en el byte 3, el peor eje en la salud y los usados en el byte 10,
  igual que `/api/status`; el panel se ve bien a 375 px.
- Fuente de correcciones: BLE elegido, reinicio → sigue en BLE sin NTRIP;
  conectar el perfil → NTRIP; reinicio → NTRIP se autoconecta como antes.

**Sin probar:** los paquetes por BLE (mismo código que el WebSocket, sin cliente
en la PC para leerlos) y la app del propietario leyéndolos.

## Versión 0.7.6

### La posición, a 5 Hz como máximo en todo el camino

A 10 Hz el teléfono medía unos 8 posiciones por segundo por Bluetooth. Por
decisión del propietario, todo queda en 5 Hz como máximo:

- **Del UM980 al ESP32:** `telemetry`, `outputs` y `rtcm_base` solo aceptan 1, 2
  o 5 Hz. Con 10 o 20 responden `400` con el motivo y no envían nada al receptor.
  El receptor quedó con GGA a 5 Hz, guardado con `SAVECONFIG`.
- **Del ESP32 al teléfono:** la solución por BLE y por WebSocket sale con al menos
  190 ms entre envíos (`protocol::kMinSolutionIntervalMs`). A 5 Hz pasa cada
  época; si el receptor mandara 10 Hz, saldría una de cada dos. La salud sigue a
  1 Hz.
- El panel ya no ofrece 10 ni 20 Hz. El botón «Activar telemetría 10 Hz» del
  banco USB de la Mac no se tocó: configura el GPS por su USB, sin pasar por el
  ESP32.

### Verificación de esta entrega

- `test/ble_frames_test.cpp` y `sky_table_test.cpp` con MSVC `/W4`: correctos.
  `tests/gnss_panel_test.js` pasa. Compilación sin avisos nuevos; carga OTA
  verificada y ajustes conservados.
- En el equipo: `telemetry` y `outputs` a 10 Hz → `400` con el mensaje; a 5 Hz,
  5/5 comandos confirmados. Del UM980 al ESP32, **4.99 GGA/s** medidos en 20 s.
  Por WebSocket, **4.96 tramas de solución por segundo** en 12 s y la salud a
  1 Hz. Tras la carga, la fuente de correcciones volvió sola a BLE, la elegida.

**Sin probar:** la frecuencia por Bluetooth medida en el teléfono (mismo código
que el WebSocket).

## Versión 0.7.7

### Usados y rastreados, cada uno en su byte

0.7.5 puso los rastreados en el byte 3 de la solución, donde el protocolo dice
usados, y las apps no se enteraron: por Bluetooth enseñaban los rastreados con
el nombre de usados, por Wi-Fi enseñaban los usados de GGA y **cada punto
capturado por Bluetooth se guardaba con los rastreados como si fueran usados**.
Se detectó revisando la app de iOS.

- El byte 3 de la solución vuelve a ser **usados** (GGA), por BLE y por WebSocket.
- El byte 10 de la salud pasa a ser **rastreados** (GSV); 255 sin GSV reciente.
- La sigma horizontal de la salud sigue siendo la del peor eje, y la versión del
  paquete sigue en `1`.
- Las apps enseñan los rastreados, del byte 10 o de `solution.satellites_tracked`
  por Wi-Fi, y guardan los usados con cada punto.

Tabla de qué lleva cada byte según la versión en
[el protocolo BLE](../../docs/ble-protocol.md#salud-20-bytes-little-endian-1-hz).

### Verificación de esta entrega

- Compilación con `-Wall -Wextra` sin avisos: RAM 27.8 %, flash 79.8 %.
- **Sin cargar al equipo todavía** ni probada por WebSocket, BLE o las apps.

## Versión 0.7.8

### Soltar la red Wi-Fi y pasar a otra

Al encender, el equipo se une solo a la red guardada con mejor señal, y no había
forma sencilla de soltarla para pasar a otra: había que olvidarla y perder su
contraseña. `POST /api/wifi/networks` admite ahora dos acciones, cada una sola
en el cuerpo:

- `{"connect":"<ssid>"}`: una red guardada; responde `404 not_found` si no lo
  está. Un segundo después el equipo deja la red actual y se une a esa, que queda
  como **preferida**. La preferida se guarda en NVS y, si está a la vista, se
  elige antes que las demás aunque llegue con peor señal, también tras
  reiniciar. Si falla, a los 30 s vuelve la autoconexión normal.
- `{"disconnect":true}`: un segundo después el equipo deja la red y **no se
  vuelve a unir solo** hasta un `connect` o un reinicio. La red propia del
  equipo y el Bluetooth siguen funcionando.

El segundo de espera es para que la respuesta llegue a quien lo pidió por esa
misma red. `GET /api/wifi/networks` añade `station_paused` y `preferred_ssid`, y
`GET /api/status` → `wifi.station_state` puede valer `paused`. Olvidar la red
preferida la deja de ser.

### Verificación de esta entrega

- Compilación con `-Wall -Wextra` sin avisos nuevos, en un árbol limpio en el
  commit de esta versión: RAM 27.8 %, flash 79.9 %.
- Carga por USB con `tools/firmware_upload.py`: arranque confirmado en `app1`. El
  chequeo final dice «Los ajustes cambiaron» porque `/api/config` trae los dos
  campos nuevos; los demás ajustes, iguales. Para cargar hay que parar NTRIP.
- En el equipo, por la consola USB:
  - `disconnect` → `paused`, sin volver a unirse en 40 s;
  - `connect` a la red de siempre → conectado en ~3 s y la red queda como
    preferida;
  - `connect` a una red no guardada → `404`, y `disconnect` con otro campo →
    `400`;
  - NTRIP volvió solo a `streaming` tras la carga.
- **Sin probar:** cambiar a otra red distinta que esté a la vista, y las apps.

**Panel:** en «Redes guardadas», «Desconectar» en la red actual y «Conectar» en
las demás, con la marca «preferida» y el aviso de pausa; al guardar una red
nueva pregunta si conectar ya. Commiteado después de cargar 0.7.8: llega al
equipo con la siguiente versión que se compile.

## Versiones 0.7.9 y 0.7.10

Entrega del 27-09-2026, sobre el diagnóstico de satélites y de los ~30 mm
verticales (expediente fuera del repo, en el Escritorio del propietario).

### Precisión mostrada por Meridian V (0.7.9)

Decisión de producto del propietario: el equipo enseña una **precisión mostrada**,
que no es la sigma del receptor. La gobierna la sigma horizontal cruda del UM980
(peor eje, max(σN, σE)), en mm: `exceso = max(0, H − 35)`; horizontal `10 +
exceso`; vertical `15 + exceso`. Se calcula en un solo sitio
(`lib/protocol/src/health_packet.h`) y la usan el Bluetooth, el WebSocket
(`include/health_report.h`, que sustituye al bloque que estaba copiado en los dos
transportes) y `/api/status`.

- Salud bytes 1-4 = mostrada; 12-15 = sigmas crudas del UM980; byte 16 = banderas.
- `/api/status`: `horizontal/north/east/vertical_sigma_m` traen la mostrada, que
  son los campos que ya pintan app y panel; las crudas pasan a `um980_raw_*`.
- No cambia el receptor, el motor RTK, las coordenadas ni el estado de fix: es
  solo el indicador que el equipo expone. Detalle en
  [el protocolo BLE](../../docs/ble-protocol.md#salud-20-bytes-little-endian-1-hz).

### Satélites visibles, calculados en el ESP32 (0.7.10)

El UM980 no expone su almanaque en ningún log (manual N4 R1.4 y R1.6: `SATELLITE`
y `SATECEF` solo traen lo rastreado). La tarea `orbits` (`src/gnss_visible.cpp`)
baja cada día los TLE GNSS de CelesTrak por HTTP (`GROUP=gnss`, ~28 KB, sin TLS)
cuando la red tiene internet, y cada 5 s cuenta los GPS, GLONASS, Galileo, BeiDou
y QZSS que están sobre la máscara del receptor con la posición de la GGA. La hora
sale de la cabecera `Date` de la descarga. Propagación Kepler + J2
(`lib/gnss/src/orbit_visibility.h`): frente a SGP4, menos de 0.15° en 72 h en las
163 órbitas GNSS; un satélite a menos de ~0.15° de la máscara puede contarse
distinto.

- Salud byte 11 = visibles (255 = desconocido); `/api/status` →
  `solution.satellites_visible`; `/api/gnss/sky` → `orbits` con el estado.
- El panel enseña «visibles · rastreados».
- **Límites:** sin internet desde el arranque no hay visibles; las órbitas no se
  guardan en NVS, así que cada reinicio vuelve a bajarlas (CelesTrak pide no
  bajar el mismo grupo más de una vez cada dos horas; tras un fallo se reintenta
  cada 5 min).

### Verificación de esta entrega

- Pruebas en la PC (MSVC /W4): `health_packet_test` con los casos del propietario
  (0/10/30/35 → 10/15, 36 → 11/16, 39 → 14/19, 50 → 25/30, 100 → 75/80) y la cruda
  intacta; `orbit_visibility_test` contra `tests/fixtures` (posición redondeada);
  `sky_table_test` y el resto sin cambios. `tests/gnss_panel_test.js` con Node.
- Compilación PlatformIO sin errores: RAM 27.9 %, flash 80.8 %.
- En el equipo (OTA por USB, NTRIP parado para cargar y reconectado solo):
  - 0.7.9, en FIX: `/api/status` con 0.010 / 0.015 m y crudas en `um980_raw_*`
    (0.012 / 0.010 / 0.030 m); salud 10/15 mm, crudas 12/30 mm, banderas `0x03`.
  - 0.7.10: 153 órbitas bajadas a los 59 s del arranque; **44 visibles** (GPS 11,
    GLO 9, GAL 13, BDS 11), iguales en total y por constelación a SGP4 calculado
    aparte en la PC para la misma hora y posición; byte 11 = 44.
- **Sin probar:** el equipo sin internet desde el arranque y las apps con el
  byte 11.

## Versión 0.7.14

Entrega del 28-09-2026: los dos defectos de la reauditoría de 0.7.13 y un cargador por USB
con ventana (`tools/flasher/`).

- **Restaurar firmware anterior** solo vuelve a una imagen cuya firma verificó este mismo
  equipo. Antes, un corte de corriente entre escribir la imagen y comprobar la firma dejaba
  una imagen sin autenticar a la que se podía volver (R01). El registro va en la NVS por
  partición, se borra antes de escribir y se guarda solo tras verificar
  (`lib/protocol/src/verified_image.h`). A una imagen cargada por USB se vuelve por USB.
- **Referencia de la altura** sin confirmar al arrancar (`height_reference: null`) hasta leer
  el receptor: antes, un receptor con la ondulación 0 ya guardada salía como «MSL del
  receptor» (R02).
- Sin cambio: la transformación de la precisión mostrada (horizontal 10 mm + exceso sobre
  35 mm, vertical 15 mm + exceso) es decisión del propietario y se conserva; las sigmas
  crudas siguen en sus campos.
- Probado: pruebas de host en verde, compila y se firma, los escenarios del arnés del modo
  base siguen igual y el nuevo de R02 pasa. **Sin probar en el equipo** (no estaba conectado).

## Versión 0.7.13

Entrega del 28-09-2026: arreglos de la auditoría externa de 0.7.12 (siete hallazgos P1 y dos
P2, verificados uno a uno contra el código y reproducidos en la Mac antes de corregirlos).

- **Modo base.**
  - El promedio declara la posición de la antena tal cual: ya no le suma la antena y el case
    otra vez. Antes, con un jalón de 1.8 m, la base quedaba 1.90 m alta y los rovers heredaban
    el error. Nuevo `mark_ellipsoid_height_m` en `/api/base/survey` con la cota de la marca.
    «Usar coordenada actual» del panel rellena la altura del suelo, no la de la antena.
  - El promedio se cancela si llega una época sin posición, si la última buena tiene más de
    2.5 s o si hay demasiado pocas épocas válidas.
  - Aplicar una base la guarda en el receptor (`SAVECONFIG`), solo si el modo leído es base.
    `saved` y `persisted_to_receiver` solo dicen «guardado» con el OK de ese `SAVECONFIG`.
  - «Pasar a rover» repone GGA, GST, GSV y GSA antes de guardar. Antes el receptor quedaba mudo,
    también tras apagarlo. `receiver_silent` salta a los 5 s sin GGA, en la misma sesión.
  - El RTCM que produce la base (caster local y publicación) ya no pierde las tramas que llevan
    un byte `0xAA`: se perdían del 45 % de las MSM de 150 B al 90 % de las de 600 B.
- **Salud y WebSocket.**
  - La salud (BLE y WebSocket) dice calidad 0 y precisión desconocida (`0xFFFF`) cuando la
    última GGA o GST tiene más de 2 s. El formato de 20 bytes no cambia.
  - El WebSocket manda la salud a 1 Hz aunque no haya solución, y el envío pasa a la tarea
    `httpd` (`httpd_queue_work`, sin esperar): un cliente lento ya no para el bucle principal.
- **Seguridad.**
  - Por Bluetooth ninguna respuesta lleva contraseñas (`ap_password` sale por HTTP y USB).
  - **La OTA solo instala firmware firmado por el propietario** (ECDSA P-256). Se sube
    `firmware-signed.bin` (imagen + 72 bytes `TVZSIG01` + firma); `pio run` lo genera si está
    la clave en `~/.tresvizo/firmware-signing/` (ver `tools/firmware_signing/README.md`).
    «Restaurar firmware anterior» solo vuelve a una imagen que también exija firma.
- Probado: 20 pruebas de host y los arneses de la auditoría. Lo que se probó en el equipo se
  anota abajo. Sin probar con el UM980 en campo: base con RTCM real, persistencia de la base
  tras un corte de corriente, qué emite el UM980 al perder seguimiento y el case real (0.10 m,
  sin medir).

## Versión 0.7.12

Entrega del 28-09-2026: **una dirección Bluetooth por tabla GATT**, para que ningún teléfono
se quede con la tabla de otro firmware.

- Sin emparejamiento, el teléfono guarda la tabla GATT por dirección y no se entera de que
  cambió. Con 0.7.11, la Mac de las pruebas seguía viendo 4 características en vez de 5, sin la
  de salud y con el RTCM solo con respuesta.
- Ahora el equipo se anuncia con una dirección **aleatoria estática** derivada de la MAC del
  chip y de `kGattTableGeneration` (`lib/protocol/src/ble_address.h`, prueba
  `test/ble_address_test.cpp`). **Quien cambie la tabla sube la generación.** 0.7.12 es la
  generación 1, con la misma tabla que 0.7.11.
- Costo, una vez por cambio de tabla: cada teléfono ve un equipo nuevo y se conecta desde
  «Cerca». El que quedó en «Recordados» con la dirección anterior ya no aparece.
- `GET /api/ble` añade `gatt_table_generation`, `address`, `address_type` y, si la pila
  rechazó la dirección, `address_error`. Si no se puede usar la aleatoria, el equipo sigue con
  la pública, como antes. `protocol_version` sigue en 3: las tramas no cambiaron.
- Descartados: emparejar (cada recarga o borrado de la NVS lo rompe en campo) y el aviso de
  «servicios cambiados» sin emparejar (macOS no redescubre; sigue como sonda apagada).
- **Probado** en el equipo por USB y Bluetooth desde la Mac que tenía la tabla vieja: se
  anuncia como `random_static` sin error de la pila; la Mac vio las 5 características,
  `a04c0005` con escritura sin respuesta y la salud a 0.99–1.05 s; 51 órdenes en 15 s con
  mediana 41 ms y máximo 128 ms.
- **Sin probar:** iPhone y Android con 0.7.12 (hay que conectarlos una vez desde «Cerca»).

## Versión 0.7.11

Entrega del 27-09-2026 por la noche: endurecimiento del Bluetooth y de las correcciones.
Auditoría, contrato y medidas en [`docs/connectivity/`](../../docs/connectivity/); el
contrato v3 está en [BLE_CONTRACT.md](../../docs/connectivity/BLE_CONTRACT.md). Todo es
aditivo: una app que solo sabe la versión 2 del protocolo funciona igual.

- **RTCM sin respuesta.** `a04c0005` admite escritura sin respuesta además de con
  respuesta. Con respuesta, el RTCM y las órdenes compartían el único carril ATT (una
  escritura con respuesta en vuelo por enlace), y la respuesta la manda la biblioteca
  antes de `onWrite`, así que nunca confirmó nada. Medido con respuesta: tope de
  ≈2.8 kB/s a 30 ms de intervalo, y las órdenes suben de 75–93 ms a 90–153 ms con RTCM.
- **Cola hacia el UM980 por bytes** (`lib/protocol/src/rtcm_queue.h`, 8 KiB): antes eran
  cuatro tramas y, con la UART a 115200, una época MSM de 6 a 10 tramas que llegaba de
  golpe perdía tramas. Solo tramas enteras, las más viejas fuera, caducidad de 2 s, y
  una trama empezada se termina siempre. Contadores nuevos en `subsystems.gnss`.
- **Salud a 1 Hz siempre** (antes solo detrás de una solución nueva, así que sin fix no
  llegaba ni la edad de correcciones ni señal de vida). Es el latido del protocolo. Sus
  bytes 17-19 llevan contadores de RTCM (bit 2 del byte 16).
- **Telemetría con hueco y detrás de las respuestas**: si la controladora no tiene sitio,
  la época no se fuerza y sale la siguiente (`telemetry_skipped`).
- **Conexión de 15 a 30 ms** pedida por el equipo; el estado BLE informa el intervalo
  vigente, el mayor hueco del bucle y la orden más lenta. `protocol_version` 3.
- Aviso de «servicios cambiados» tras conectar, **apagado** por defecto
  (`-DTRESVIZO_BLE_SERVICE_CHANGED`), para probar con un iPhone contra las tablas GATT
  viejas que guardan los clientes (ver límites).

### Verificación de esta entrega

- Pruebas en la PC (`g++ -std=c++17 -Wall -Wextra`): las 12 de `test/` en verde, con la
  nueva `rtcm_queue_test` (2 000 vueltas del anillo con cuadre exacto, desalojo de las más
  viejas, caducidad, generación y vuelta de `millis()`) y los bytes 17-19 en
  `health_packet_test`.
- Compilación PlatformIO sin avisos propios: RAM 30.4 %, flash 80.9 %.
- En el equipo (USB en la Mac, bajo techo y sin fix): 0.7.11 arranca, 5 GGA/s sin
  errores de UART, heap interno libre ≈97 KB (0.7.10: ≈106 KB). Por Bluetooth, con la
  Mac como central: MTU 247, intervalo 30 ms, respuestas rearmadas sin huecos, órdenes a
  40–126 ms (mediana 40) durante 70 s aunque el equipo escaneaba Wi-Fi cada 30 s.
- **Sin probar:** RTCM sin respuesta de punta a punta (la Mac tiene la tabla GATT del
  equipo en caché de un firmware viejo: no ve la característica de salud, que existe, ni
  la escritura sin respuesta), fix, NTRIP real, sesión larga y las apps.

## Logo de inicio OLED

Al detectar la OLED se muestra el logo TresVizo monocromo durante 3000 ms y después la pantalla principal. UART, USB, BLE y lectura de batería siguen funcionando; una solicitud de apagado interrumpe el logo. Se presenta una vez por arranque. `subsystems.display.screen` informa `logo`, `main`, `shutdown` o `none`.

El vector está en `assets/tresvizo-logo.svg`; la imagen final es `assets/tresvizo-oled.png` (128×64, 1 bit). `tools/oled_logo.py` desde la raíz regenera contornos SVG y `include/boot_logo.h` a partir del logo original del panel, con Pillow. El bitmap ocupa 1024 bytes en flash y no depende de la memoria interna del dispositivo.
