# Firmware inicial del instrumento

Versión 0.6.0 para el ESP32-S3 conectado por USB. El perfil usa 4 MB de flash comprobados por esptool. La placa de referencia de PlatformIO aporta la configuración de CPU/USB; no identifica la carrier como DevKitC ni autoriza sus pines externos. PSRAM Quad de 2 MB habilitada, con prueba de integridad y métricas separadas de RAM interna.

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


## Cambio de clave del equipo (0.2.0)

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

**No ejecutado:** compilación del firmware, carga al ESP32 y
`tests/device_services_smoke.py`. La máquina de trabajo no tiene compilador C++ ni
PlatformIO, y el receptor no estaba conectado. Nada de esta versión se ha
comprobado sobre el equipo real.

### Herramientas en Windows

`tools/usb_console.py` importaba `fcntl` y `termios`, que solo existen en POSIX, de
modo que no arrancaba en Windows. Ahora esos módulos son opcionales: en Windows el
puerto ya se abre en exclusiva y pyserial rechaza una segunda apertura, así que no
hace falta el refuerzo con `TIOCEXCL`.
