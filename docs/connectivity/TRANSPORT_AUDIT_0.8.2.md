# Auditoría Wi-Fi/BLE con las apps — 0.8.2

Fecha: 04-10-2026. Firmware para SparkFun Thing Plus ESP32-S3. Revisión de los transportes y del contrato que consumen iOS y Android; cambios en el firmware, sin modificar las apps.

## Hallazgos corregidos

| Prioridad | Fallo y consecuencia | Corrección |
| --- | --- | --- |
| Alta | BLE forzaba un fragmento tras 50 ms sin espacio y avanzaba el offset aunque `notify()` fallase. La app recibía huecos y descartaba el JSON completo. | Espera a la controladora, consulta el resultado síncrono de `notify()` y conserva el offset si la pila no lo acepta. Un fallo GATT posterior cierra la sesión; no se repite una mutación. |
| Alta | Una línea BLE tardaba más de 5 s: se borraba el acumulador y su sufijo pasaba a interpretarse como otra orden. Reproducido físicamente con escrituras de 7 bytes. | Descarta hasta LF las líneas vencidas, de más de 1024 bytes o con NUL. Sólo una sesión nueva o el siguiente LF permiten empezar otra línea. |
| Alta | OTA iniciada antes de los 5 s podía quedar bloqueada por la reconciliación GNSS que arrancaba después. Incluso `abort` recibía `busy`. | La puerta de ocupación se aplica a `begin` y `rollback`. Una sesión abierta puede continuar y abortar. GNSS y autoconexión NTRIP esperan durante OTA; `busy()` usa atómicos y sigue activo durante la activación final. |
| Media | El error BLE 413 no llevaba el `id` de la petición; la app esperaba hasta vencer. | Se conserva `id` y se mide el JSON antes de reservar la cadena de respuesta. |
| Media | WebSocket medía sólo el tiempo desde encolar. Una posición de 400 ms podía esperar otros 400 ms y salir con 800 ms de edad. | Al enviar verifica también el instante de llegada GNSS: máximo 500 ms. La salud puede salir aunque se descarte la posición de esa tanda. |
| Media | Si fallaba instalar el envío sin bloqueo del WebSocket, la sesión seguía con envíos bloqueantes en la tarea HTTP. | La sesión se rechaza si no puede garantizar ese modo de envío. |
| Media | BLE daba una época y un latido por enviados aunque no hubiera suscripción o la pila rechazase el envío. El contador de bucle se escribía desde dos tareas. | La cadencia avanza sólo con aceptación local; el reloj del bucle queda en su tarea. Al cambiar de sesión se reinicia el seguimiento de época y salud. |
| Media | Apagar BLE desde su propia API cerraba el enlace antes de enviar la respuesta. | Deja terminar la respuesta, con plazo acotado y margen de 150 ms antes del cierre. No equivale a un acuse de lectura del teléfono. |
| Baja | NTRIP en modo base devolvía 409 sin el código que las apps ya reconocen. | Añade `error: receiver_is_base` y conserva el mensaje existente en ambas rutas. |

Una respuesta BLE atascada tiene un plazo total de 4.5 s. Al vencer se cierra la sesión y se vuelve a anunciar el equipo. Las notificaciones siguen siendo notificaciones: aceptación por la pila **no prueba recepción por la aplicación**. Las apps conservan sus comprobaciones de offset, límite de 4096 bytes, correlación por `id`, caducidad y reconexión. No se han introducido reintentos automáticos de mutaciones.

## Compatibilidad

Se conservaron UUID, propiedades GATT, versión 3 del protocolo, cabecera de 5 bytes, solución y salud de 20 bytes, WebSocket binario de 21 bytes, rutas, unidades y campos existentes. No se cambió la generación de la tabla GATT. Las órdenes siguen siendo JSON más LF, con una orden en vuelo por cliente y cola de dos en firmware.

Diagnóstico aditivo en `GET /api/ble`: `response_frames_deferred`, `notification_failures`, `response_timeouts`. Se conserva `response_frames_forced`, que ahora permanece en cero. WebSocket añade `stale_solutions_dropped`. El estado abreviado por BLE sigue usando la lista generada del contrato; las lecturas completas siguen disponibles por HTTP/USB.

Se inspeccionaron los reensambladores actuales de iOS y Android y su correlación por el `id` JSON. La evidencia estática del contrato se ajustó a la ubicación del nuevo limitador y al nombre local de la secuencia; se añadió una comprobación de que el limitador se llama antes de serializar. No se alteró el esquema de datos de las apps.

## Pruebas realizadas

- PlatformIO `esp32s3_usb`, compilación y firma verificadas; carga USB terminada con verificación de hashes. Imagen instalada: 0.8.2. RAM estática 101200 B; aplicación 1732045 B, 88.1 % del slot.
- 32 suites C++ con `-Wall -Wextra -Werror`, UndefinedBehaviorSanitizer y parada ante error. Incluyen fragmentación con rechazos inyectados, MTU 23/185/247, respuesta de 4096 bytes, rollover del reloj, límite JSON, líneas vencidas y desbordadas, frescura de telemetría, RTCM/CRC/colas y OLED. Las fixtures de JSON y órbitas se ejecutaron desde sus directorios esperados.
- 86 pruebas del banco BLE y 35 de la herramienta de contrato. Los escenarios simulados se distinguen del banco físico; no demuestran funcionamiento de radio por sí solos.
- 320 comprobaciones del contrato sobre el equipo por USB superadas; `/api/recording/sessions` devolvió 503 por ausencia de memoria y no se validó su listado.
- 644 comprobaciones estáticas del contrato superadas. El catálogo conserva cuatro discrepancias históricas: dos ya tienen resolución anotada; quedan las diferencias menores de cero satélites visibles y la ruta WebSocket fija de iOS, que se conserva.
- Desactivar BLE desde BLE devolvió el JSON completo con `id` correcto en 94.7 ms y después cerró el enlace. Se restauró y verificó `enabled:true` por USB.
- Banco físico BLE desde la Mac: dos series de tres conexiones, 123 respuestas completas por serie, sin errores de reensamblado. Cada serie inyecta seis líneas inválidas y una respuesta sin suscripción; se observaron exactamente seis descartes y un timeout previsto. Fallos GATT y fragmentos forzados: cero. Configuración comparada antes y después, sin cambios.

| Banco físico | Mediana de respuesta | P95 | Máximo | Mayor separación entre latidos |
| --- | ---: | ---: | ---: | ---: |
| MTU negociado 247, notificaciones hasta 244 B | 64.7 ms | 210.1 ms | 241.9 ms | 1077.8 ms |
| Alternando escrituras de 7 B y MTU negociado | 417.2 ms | 573.2 ms | 660.2 ms | 1051.6 ms |

Las mediciones incluyen escribir la orden y recibir el JSON completo; mezclan `/api/status`, `/api/ble` y `/api/config`. No son una medida de latencia de posición ni de renderizado del teléfono. La segunda serie fuerza fragmentación de comandos; no representa el envío normal de las apps. La recuperación del bloqueo deliberado tardó 4533.5 y 4536.8 ms, respectivamente. En la serie normal, el mayor hueco del bucle BLE fue 25 ms y el despacho más lento 23 ms, medidos desde la última conexión.

OTA física por USB: sesión iniciada a 1625 ms de uptime, mantenida hasta 8064 ms; GNSS quedó en `idle` durante ella. Se aceptó el primer bloque de 576 B, se reconoció el duplicado, se rechazó un offset incorrecto y un cierre incompleto, y se aceptó abortar. GNSS retomó `reconcile`; una petición de abortar con sesión inválida llegó al validador OTA aun con GNSS ocupado. Se conservó `app0` como slot activo y la configuración. Esta prueba escribió y borró la partición inactiva; no instaló por OTA una imagen completa.

Paquete firmado final, 1732568 bytes, SHA-256:

```
96a60627c9f8d473f5a09d7acdc754d4c3b51e28dbf2d96ec9e1b96ddb57d06a
```

Bancos repetibles desde la raíz:

```
~/.platformio/penv/bin/python tests/protocol_transport_bench.py --stall
~/.platformio/penv/bin/python tests/protocol_transport_bench.py --fragment-bytes 0 --stall
~/.platformio/penv/bin/python tests/ota_session_bench.py
python3 tools/api_contract/check_contract.py
```

El banco OTA altera la partición inactiva: usar sólo un equipo disponible para pruebas. No ejecutar a la vez dos programas que abran el USB; abrir el puerto en esta placa puede reiniciarla.

## Límites pendientes

- **Wi-Fi físico:** el equipo no tiene red STA configurada; `meridianv.local` no resolvió y el AP `192.168.4.1` no fue accesible desde la Mac. Se revisaron HTTP/WebSocket y se probó la política de frescura, pero no se midieron HTTP, WebSocket, cliente lento ni coexistencia Wi-Fi/BLE en esta sesión.
- **Apps y campo:** falta repetir con iPhone y Android reales, RTCM sostenido y GNSS con posición, interferencias, salida de alcance, segundo plano y una sesión prolongada. No se ha medido aquí la fluidez de sus pantallas ni la latencia de posición. MTU 23 y 185 se probaron en host; la Mac negoció 247.
- **Congestión BLE real:** se inyectaron rechazos en host y se bloqueó una respuesta retirando su suscripción; no se saturó físicamente la controladora. Los fallos GATT asíncronos no aparecieron en el banco físico.
- **OLED:** sigue sin responder en I²C (`not_detected`). El endurecimiento de arranque/reinicio está cargado, pero la comprobación visual del logo de 10 s y los tres reinicios sigue pendiente del ciclo completo de alimentación descrito en `docs/firmware-validation.md`.
- BLE continúa sin emparejamiento ni cifrado por decisión del propietario. Esta entrega no cambia esa política. No se promete ausencia absoluta de pérdidas de radio.

## Referencias de implementación

- [API GATT de Espressif, IDF 4.4.7](https://docs.espressif.com/projects/esp-idf/en/v4.4.7/esp32/api-reference/bluetooth/esp_gatts.html): envío y eventos de confirmación/congestión.
- [Adaptador GATTS de IDF 4.4.7](https://github.com/espressif/esp-idf/blob/v4.4.7/components/bt/host/bluedroid/btc/profile/std/gatt/btc_gatts.c): resultados asíncronos hacia la aplicación.
- SDK local Arduino-ESP32 2.0.17, `libraries/BLE/src/BLECharacteristic.cpp`: `notify()` comunica el resultado inmediato mediante `onStatus`; la aceptación no es un acuse de la app.
- [Contrato con las apps](../api-contract/README.md) y [contrato BLE](BLE_CONTRACT.md).
