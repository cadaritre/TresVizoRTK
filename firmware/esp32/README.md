# Firmware inicial del instrumento

Versión 0.1.0 para el ESP32-S3 conectado por USB. El perfil usa 4 MB de flash comprobados por esptool. La placa de referencia de PlatformIO aporta la configuración de CPU/USB; no identifica la carrier como DevKitC ni autoriza sus pines externos. PSRAM desactivada en esta etapa.

## Funciones implementadas

- Arranque sin esperar a que se conecte una consola USB.
- Red Wi-Fi propia protegida con una clave aleatoria por equipo, persistida en NVS y recuperable por acceso físico USB.
- Panel web en español con la identidad visual y el logo de TresVizo; los recursos están comprimidos en flash. No requiere microSD ni Internet.
- Estado real del controlador: tiempo encendido, memoria, flash, firmware y Wi-Fi.
- Ajustes persistentes: nombre, intervalo del panel y conexión a un hotspot protegido de 2.4 GHz. El AP permanece activo.
- Validación de tipos y límites, detección de conflictos de revisión y guardado de la configuración en una sola entrada NVS. Las solicitudes inválidas no modifican ajustes.
- Servidor HTTP de ESP-IDF con límites de cuerpo y espera; exclusión mutua para acceso desde HTTP/USB.
- Consola JSON USB con buffer acotado, tiempo límite y recuperación tras mensajes demasiado grandes.
- Reinicio solicitado y exportación de diagnóstico sin contraseñas ni nombres de redes.

GNSS, IMU, microSD, NTRIP, BLE, modos base/rover y compensación de inclinación no están implementados. No se inicializan sus GPIO. No hay posiciones ni soluciones FIX simuladas. La app de campo sigue sin iniciarse.

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
