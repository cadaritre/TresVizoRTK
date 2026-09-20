# Protocolo BLE v1 del instrumento

## Estado

Firmware 0.4.0 incorpora servicio GATT de control, respuestas fragmentadas, solución compacta y entrada RTCM3. La app de topografía no está implementada. Compilar o anunciar el servicio no demuestra entrega a 10 Hz por radio: falta prueba con cliente BLE y UART real. Las características no usan el protocolo propietario de Emlid.

Emparejamiento LE Secure Connections, MITM, PIN de seis dígitos y bonding. Desde 0.5.0 el PIN se genera una vez, se conserva en NVS y se consulta con `GET /api/access` por USB físico (`ble_pairing_pin`), nunca por HTTP/BLE. Una conexión además necesita la clave del instrumento en solicitudes JSON. No publicar el PIN ni la clave en diagnósticos. La recuperación/cambio de clave sigue exclusivamente por USB.

## UUID

Todos comparten sufijo `-8f24-4adb-a350-77ef6339c320`:

| Prefijo | Función |
| --- | --- |
| a04c0001 | Servicio TresVizo |
| a04c0002 | Escritura con respuesta ATT: solicitudes JSON |
| a04c0003 | Notificaciones: respuestas JSON fragmentadas |
| a04c0004 | Notificaciones: solución GNSS compacta |
| a04c0005 | Escritura con respuesta ATT: fragmentos RTCM3 |

## Control

Reutiliza `{id, method, path, key, body}` de la consola USB; máximo 1024 bytes, UTF-8 JSON terminado en LF. Fragmentar a `MTU-3`, inicialmente 20 bytes. `body` solo cuando aplique. Dos solicitudes en cola, antigüedad máxima 5 s; un mensaje incompleto vence a 5 s. Enviar una operación, esperar respuesta y consultar el estado si vence el plazo. No repetir automáticamente mutaciones cuyo resultado es incierto. Los identificadores correlacionan respuestas; no ofrecen deduplicación persistente.

Respuestas de hasta 4096 bytes en paquetes de máximo 20 bytes: uint16 little-endian ID de mensaje, uint16 offset, uint8 flags (bit0 inicio, bit1 final), hasta 15 bytes de JSON. El cliente valida offsets, desecha mensajes incompletos y consulta estado tras pérdidas; las notificaciones no son entrega garantizada. Cambiar de conexión invalida mensajes en cola. GET/PUT de configuración y GET de capacidades/estado usan el mismo controlador que HTTP. Las funciones sin controlador siguen devolviendo indisponibilidad; no hay falsa confirmación de grabación microSD.

## Solución (20 bytes, little-endian)

| Offset | Tipo | Significado |
| --- | --- | --- |
| 0 | uint16 | Secuencia; vuelve a 0 después de 65535 |
| 2 | uint8 | Calidad GGA 0–8 |
| 3 | uint8 | Satélites usados; 255 desconocido |
| 4 | uint32 | Hora UTC del día en ms; **sin fecha** |
| 8 | int32 | Latitud × 10⁷ grados; INT32_MIN inválido |
| 12 | int32 | Longitud × 10⁷ grados; INT32_MIN inválido |
| 16 | int32 | Altura MSL del receptor en mm; INT32_MIN inválido |

Se notifica únicamente una época nueva con llegada menor a 500 ms. La app vence datos si dejan de llegar y distingue secuencia de época. No extrapolar ni repetir una posición para aparentar 10 Hz. No hay reloj UTC absoluto ni sincronización PPS validada. Extensiones de mensaje y otras referencias de altura requieren versión nueva; no reinterpretar campos silenciosamente.

## Correcciones

Seleccionar `PUT /api/corrections/source {"source":"ble"}` después de autenticar. Escribir tramas RTCM3 fragmentadas; máximo de trama 1029 bytes, CRC24Q obligatorio. Antes de autenticar, los bytes no se procesan. Una sola fuente activa y generación por cambio de fuente; mensajes antiguos no deben pasar al nuevo transporte. Cola UART de cuatro tramas, caducidad 2 s y contadores de descartes. El callback BLE no escribe directamente a UART. Sin UART habilitado, se descartan y se informa `rtcm_available:false`.

Firmware y archivos grandes se transfieren por Wi-Fi/USB. BLE admite consultar estado OTA, pero no iniciar cargas ni restauraciones. Ningún módulo de radio está instalado todavía.
