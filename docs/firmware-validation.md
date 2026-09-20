# Validación inicial del firmware

Fecha: 19 de septiembre de 2026. Versión del instrumento: 0.1.0. Estas comprobaciones cubren la base de control; no validan un receptor RTK ni precisión topográfica.

## Equipo y preparación

- El propietario confirmó que el ESP32 era el único equipo conectado por USB y que ningún módulo externo estaba cableado.
- esptool 4.9.0 identificó ESP32-S3 QFN56 revisión 0.2, flash XMC integrada de 4 MB y PSRAM AP de 2 MB; flash quad a 3.3 V. La variante Tiny seleccionada en la captura concuerda con esas capacidades.
- Se leyó la flash completa antes de la primera carga: 4,194,304 bytes. Respaldo privado en `logs/local/esp32-before-first-flash.bin`, excluido del historial.
- SHA-256 del respaldo: `a604c71d12946300e9a16ff0ac53d4fd650569a501baa30e31f09b6edef29dfb`.
- Perfil de arranque con flash DIO de 4 MB y PSRAM desactivada. No se inicializaron interfaces externas.

## Comprobaciones realizadas

| Área | Evidencia |
| --- | --- |
| Compilación | `pio run` y carga con PlatformIO Espressif32 6.12.0, Arduino-ESP32 2.0.17 y ArduinoJson 7.4.2 completados. |
| Tamaño final | 762,457 bytes de programa (38.8% de la partición de aplicación de 1,966,080 bytes) y 44,280 bytes de RAM estática. El uso dinámico se comprueba por separado. |
| Carga USB | esptool escribió el firmware y verificó los hashes de los segmentos. Reinicio posterior realizado. |
| Validadores locales | Prueba C++ compilada con Clang y `-Wall -Wextra -Werror`: límites, caracteres, tipos admitidos y temporizadores con desbordamiento de 32 bits. |
| JavaScript | `node --check` sin errores de sintaxis. |
| Hardware real | `tests/hardware_smoke.py`: 28 comprobaciones superadas. Incluyen estado, ausencia de datos GNSS simulados, autenticación, campos inválidos, límites, conflictos de revisión, persistencia, reinicios, recuperación del parser y restauración de ajustes. |
| Buffer USB | Una prueba inicial de mensaje de 1200 bytes detectó pérdidas con la cola predeterminada de 256 bytes. Se configuró una cola de 2048 bytes, manteniendo el límite lógico de 1024; la prueba posterior verificó rechazo 413 y recuperación. |
| Memoria dinámica | Veinte consultas consecutivas devolvieron más de 100 KB libres. Esta prueba corta no demuestra estabilidad prolongada. |
| Panel conectado | Navegador mediante puente USB local: datos reales, navegación, edición del intervalo, guardado y recuperación tras recargar. Se restauró el intervalo de 2000 ms. |
| Adaptación móvil | Inspección visual en escritorio y viewport de 390 × 844. Navegación móvil ajustada para mostrar las cuatro secciones. |
| Pérdida del enlace web | Al detener el puente se mostró “Sin conexión” y los valores dinámicos pasaron a `—`. Al restablecerlo, el panel recuperó automáticamente el enlace. |
| Puente local | Siete comprobaciones HTTP: recursos accesibles, cabecera de cliente obligatoria, rechazo de Host/Origin ajenos, ruta de credenciales inaccesible y recorrido fuera del directorio rechazado. |
| Identidad visual | Logo original del sitio y paleta documentados en `firmware/esp32/web/assets/README.md`. Recursos locales empaquetados en flash. |

El diagnóstico en ejecución expone lo que informa la versión de SDK utilizada. Su campo de revisión de chip puede mostrar la revisión mayor (`0`) y no la revisión completa `0.2` de esptool. El código de motivo de reinicio `0` significa que el SDK no lo identificó; no se presenta como un reinicio normal confirmado.

## Límites y pruebas pendientes

- El panel se verificó por el puente USB, que sirve los archivos locales y transporta solicitudes al firmware real. Esto no sustituye una prueba de descarga de recursos HTTP directamente desde el ESP32 por radio.
- Se comprobó que el controlador inició su AP. Quedan pendientes conexión de teléfono al AP, autenticación por HTTP directo y conexión/reconexión a un hotspot real.
- Límites HTTP implementados, pero pruebas de tráfico lento, saturación y carga concurrente sobre Wi-Fi directo pendientes.
- Sin ensayos prolongados de memoria, consumo, temperatura, brownout ni interrupción de alimentación durante escritura NVS.
- GNSS, RTCM, NTRIP, BMI088, sincronización, microSD, apagado coordinado y BLE sin implementar ni probar. No hay pruebas de campo ni de exactitud.
- El módulo biestable no está integrado y no demuestra cierre seguro de registros ni protección/carga de batería.

## Repetición

Los comandos y precauciones específicas del puerto están en el [README del firmware](../firmware/esp32/README.md). La prueba de hardware cambia temporalmente nombre e intervalo y reinicia el ESP32; debe ejecutarse con el puente y otros monitores cerrados. Cada nueva integración requiere pruebas propias, además de estas comprobaciones de base.


## Actualización 0.2.0 — 19 de septiembre de 2026

- Compilación y carga al ESP32 completadas. Flash de programa: 766293 bytes; RAM estática: 44280 bytes.
- Cambio de clave por USB aplicado en NVS y comprobado después del reinicio, sin incluir la credencial en el repositorio. AP iniciado con la nueva configuración y autenticación USB verificada. Contraseñas cortas, mayores de 63 caracteres, NUL incrustado y solicitud no autenticada rechazadas.
- Las 28 comprobaciones de `tests/hardware_smoke.py` volvieron a pasar sobre 0.2.0, incluidos reinicios y restauración de ajustes.
- `node tests/gnss_panel_test.js`: coordenadas cero válidas, referencia de altura, ausencia de posición, datos antiguos y desconexión. Sintaxis JS/Python comprobada.
- Panel local recargado y revisado en navegador: versión 0.2.0, conectado al ESP32, sin enlace GNSS y sin coordenadas inventadas.
- El UM980 por USB a la Mac entrega UTC a 10.00 Hz en el segmento continuo observado, con 0 duplicados y máximo intervalo de llegada de 102 ms. Se detectó una discontinuidad inicial de hora. No hubo solución válida: calidad 0, satélites usados 0. Son épocas de mensajes, no diez posiciones válidas por segundo.
- Quedan pendientes prueba Wi-Fi desde otro cliente con la nueva clave, cableado y adquisición física UART, BLE, RTCM y sensores. El refresco HTTP sigue siendo diagnóstico, no la tasa de adquisición.
