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


## Actualización 0.3.0 — apartados de registro/base/NTRIP

- Compilación y carga verificadas. Captura de GNSS y modo del receptor no modificados en esta entrega.
- `tests/operations_smoke.py`: 27 comprobaciones de capacidades, coordenadas, límites, tipos, autenticación, altura ARP sin doble suma y conservación de ajustes. La primera ejecución detectó un error de comparación en la prueba (ID de solicitud variable); se corrigió para comparar el cuerpo de configuración y la ejecución posterior pasó.
- `base_plan_test.cpp`: límites y cálculo con AddressSanitizer/UndefinedBehaviorSanitizer. Pasó también `tests/gnss_panel_test.js`.
- Navegador: revisados los tres apartados, controles pendientes deshabilitados y un plan sintético con altura del punto 100 m + antena 2 m que devolvió ARP 102 m. Plan de prueba retirado recargando, sin persistencia ni aplicación al GPS.
- Ajustada y revisada visualmente la navegación de siete apartados en pantalla estrecha. Grabación real, RINEX, aplicación de base y conexiones NTRIP no probadas porque sus controladores siguen pendientes.

## Actualización 0.4.0 — OTA, BLE y banco USB

- Compilación del firmware estándar y de la variante UART con GPIO 18/17 completadas. Solo se cargó la variante estándar, sin habilitar GPIO externos. Nueva imagen instalada por OTA en `app0`, arranque confirmado y ajustes NVS idénticos antes/después.
- `tests/hardware_smoke.py`: 29 comprobaciones en placa; `tests/operations_smoke.py`: 27. `tests/update_smoke.py --install`: 27 comprobaciones de rechazo/abortado y actualización completa. Incluyen hardware/tamaño/hash inválidos, autenticación, duplicados, offsets, imagen incompleta y rechazo de restauración de un candidato inválido.
- Cargas posteriores mostraron reinicios `USB_UART_CHIP_RESET`, perdiendo la sesión antes de activar el candidato. Se añadió exclusividad del dispositivo (`TIOCEXCL`, además del flock de pyserial) y diagnóstico de arranque al cliente USB. La siguiente carga completa pasó. Esto no demuestra todavía la causa externa exacta ni resistencia prolongada a desconexiones. No abrir monitores simultáneos; una transferencia interrumpida se inicia de nuevo.
- CRC/fragmentación RTCM3 C++ con AddressSanitizer/UndefinedBehaviorSanitizer; 14 pruebas Python de banco GNSS y 3 de NTRIP por sockets reales de loopback; pruebas de render GNSS y sintaxis JS superadas.
- Registro real del UM980: 393285 bytes, cero pérdidas de cola, 105 observaciones binarias con CRC válido. Conversión RTKLIB produjo RINEX 3.04 con 105 épocas OBS y 35 registros NAV. No constituye procesamiento PPK ni validación de precisión.
- BLE iniciado en el ESP32 y capacidades consultadas; pendientes emparejamiento de un cliente real, latencia/rendimiento y transferencia de correcciones hasta el GPS. NTRIP se ejecuta en banco Mac, no en firmware ESP32.
- Pendientes: Wi-Fi OTA con cliente independiente, restauración manual de ida/vuelta, fallo inducido antes de confirmar arranque, firmas de distribución, base real, caster externo, UART cableado, microSD e IMU. No se exige posición GNSS para confirmar un arranque: el receptor fue trasladado al interior.


## Validación UART física — 0.4.1, 2026-09-20

Cableado confirmado por el propietario: GPS TTL_TXD2 → ESP32 GPIO18, TTL_RXD2 → GPIO17, GND común; alimentación USB separada sin unir los pines de alimentación. Perfil predeterminado actualizado. Compilación, OTA a app1 y conservación de ajustes comprobadas.

En 58.969 s entre muestras: 589 GGA nuevos (9.988 mensajes/s), cero rechazos, desbordes y errores UART; 332 consultas USB, todas en estado receiving. RAM libre final: 138024 bytes. Sin UTC ni posición válida en interior, por lo que esto demuestra transporte de mensajes cercano a 10 Hz, no diez soluciones de posición por segundo. Métricas locales sin coordenadas: captures/local/uart-20260920-validation.json.

El panel prioriza UART del ESP32 sobre el banco USB de la Mac. Pasaron las pruebas existentes de render GNSS y comprobaciones de sintaxis JS. Pendientes transmisión ESP32→GPS, correcciones reales, pérdidas bajo carga completa y persistencia del perfil COM2 tras apagar (no se envió SAVECONFIG).


## 0.5.0 — 2026-09-20: servicios autónomos y PSRAM

- PSRAM Quad habilitada: 2094703 bytes de heap utilizable; prueba de 1 MiB con tres patrones superada. RAM interna libre observada ~154 kB, PSRAM libre ~2066 kB. No implica que cada servicio futuro esté validado bajo carga simultánea.
- Control UART real: VERSIONA identificó UM980 R4.10Build13504; MODE confirmó rover; cambios de GGA a 5 Hz y 10 Hz verificados en recepción. Se deja 10 Hz. Base aplica planes validados pero coordenadas/convergencia siguen pendientes de prueba exterior. No se aplicaron coordenadas sintéticas.
- BLE físico con Mac: cifrado SC+MITM (auth mode 13), clave inválida rechazada, respuestas fragmentadas recompuestas, recuperación de credenciales bloqueada y consulta VERSIONA/MODE realizada por BLE→ESP32→UART. Repetido después de reinicios con PIN persistente. Telemetría con UTC y RTCM real por BLE pendientes.
- Cliente NTRIP Wi-Fi implementado y panel disponible. Validación de parámetros y espera sin red comprobadas; flujo real con caster pendiente de que el propietario configure su cuenta. Inicialmente v1/TCP, sin TLS/GGA para VRS; no confundir con servicio plenamente validado.
- Controlador SD de flujo original, cola, cierre, catálogo y lectura por bloques preparado. Perfil con SD compilado, pero nunca cargado; pines de esa compilación son solo para verificar código. El propietario confirma lector desconectado. Perfil instalado mantiene SD not_configured, sin conducir pines supuestos.
- Pruebas: 24 comprobaciones API de servicios; 27 de operaciones; 29 de hardware; 14 Python GNSS y 3 NTRIP de banco. Parser de binario con sanitizadores y render GNSS JS superados. Primera prueba corta de frecuencia capturó transición; se añadió estabilización y cálculo por tiempo real del ESP32: 4.96 y 10.12 Hz en ventanas de unos 5 s. Pruebas históricas se actualizaron para UART activo y respuesta 503 de SD ausente.
- Firmware instalado por OTA, arranque confirmado y ajustes conservados. Detalles y límites: [servicios del ESP32](esp32-services.md).
