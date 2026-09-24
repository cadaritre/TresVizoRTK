# Firmware inicial del instrumento

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

Las dos particiones de aplicación dejan espacio para evolución posterior; no existe actualización OTA en esta versión. Los recursos web se empaquetan al compilar, sin `uploadfs`.

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

Todas las rutas HTTP de API requieren `X-Device-Key`. No hay CORS habilitado.

| Método y ruta | Comportamiento |
| --- | --- |
| `GET /api/status` | Estado real, capacidades pendientes y campos GNSS nulos. |
| `GET /api/config` | Ajustes sin contraseñas, revisión y disponibilidad NVS. |
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
- Un solo botón: «Estacionar la base aquí» valida y envía. Antes había tres, y
  uno exportaba un JSON que no salía del navegador.
- El papel del receptor y el botón «Usar como rover» están arriba del todo.

### Promedio de coordenadas en el ESP32

`POST /api/base/survey` promedia en el controlador, no en el receptor. El UM980
sabe promediar solo, pero no distingue con qué calidad lo hace ni avisa si la
pierde: promediar cien épocas autónomas da una coordenada muy repetible y
exactamente igual de equivocada.

Se elige la calidad exigida (`rtk_fixed`, `rtk_float`, `standalone` o `any`) y el
tiempo, de 5 a 900 s. **Si la calidad se pierde a mitad, el promedio se cancela y
se explica por qué.** El panel muestra barra de progreso, épocas usadas y la
coordenada que se va formando.

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
  vigila** las tareas de NTRIP, de salida ni el bucle principal.
- **Alarmas** en `GET /api/status` (`alerts`): receptor mudo, UART caída,
  correcciones detenidas, sin redes guardadas, reinicio por pánico, por caída de
  tensión o por watchdog, y las dos contradictorias —base con entrada de
  correcciones activa, y publicación sin modo base—.
- **La entrada NTRIP no arranca en un equipo configurado como base**, ni se
  reanuda al encender si quedó así.
- **Las consultas de solo lectura funcionan con correcciones activas.** Antes el
  guardia bloqueaba también las lecturas, y no se podía saber en qué modo estaba
  el receptor justo cuando más falta hacía.
- La entrada NTRIP se suelta sola si pasa más de un minuto esperando red: dejarla
  esperando fijaba el enrutador y bloqueaba configurar el GPS.

### Verificación de esta entrega

Comprobado sobre el equipo:

- Compilación y carga; el panel reporta la versión que corre.
- Escaneo Wi-Fi con 13 redes reales; guardar, olvidar y fijar o liberar dirección.
- Reconexión completa tras reinicio: red guardada, perfil NTRIP, correcciones y
  RTK flotante, sin intervención.
- Precisión GST con valores reales; interruptor BLE encendiendo y apagando.
- Caster local abriendo puerto y escuchando.
- Watchdog sin reinicios espurios durante la prueba (minutos, no días).

**No ejecutado:** estacionar una base, una pasada de promedio, publicación NTRIP,
el caster sirviendo a un rover, lectura de sourcetable, resolución de
`meridianv.local`, conexión con dirección fija aplicada, y los paquetes BLE, que
necesitan una app que todavía no existe. `tests/hardware_smoke.py` **está roto**:
usa la clave de acceso y el nombre editable, que ya no existen.
