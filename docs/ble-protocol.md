# Protocolo BLE v1 del instrumento

## Estado

Firmware 0.4.0 incorpora servicio GATT de control, respuestas fragmentadas, solución compacta y entrada RTCM3. La app de topografía no está implementada. Compilar o anunciar el servicio no demuestra entrega a 10 Hz por radio: falta prueba con cliente BLE y UART real. Las características no usan el protocolo propietario de Emlid.

**Desde 0.6.2 no hay emparejamiento, PIN ni cifrado**: la app de campo se conecta de un toque y cualquier equipo dentro del alcance puede escribir en las características, incluidas las correcciones que van al receptor. Decisión explícita del propietario. Mitigaciones vigentes: el transporte se apaga desde Conexiones y el ajuste se persiste, y las correcciones por BLE se rechazan mientras el receptor trabaja como base. Hasta 0.6.1 existieron LE Secure Connections con MITM, PIN de seis dígitos en NVS y autenticación por clave del instrumento.

## UUID

Todos comparten sufijo `-8f24-4adb-a350-77ef6339c320`:

| Prefijo | Función |
| --- | --- |
| a04c0001 | Servicio TresVizo |
| a04c0002 | Escritura con respuesta ATT: solicitudes JSON |
| a04c0003 | Notificaciones: respuestas JSON fragmentadas |
| a04c0004 | Notificaciones: solución GNSS compacta |
| a04c0005 | Escritura con respuesta ATT: fragmentos RTCM3 |
| a04c0006 | Notificaciones: salud a 1 Hz |

## Control

Reutiliza `{id, method, path, key, body}` de la consola USB; máximo 1024 bytes, UTF-8 JSON terminado en LF. Fragmentar a `MTU-3`, inicialmente 20 bytes. `body` solo cuando aplique. Dos solicitudes en cola, antigüedad máxima 5 s; un mensaje incompleto vence a 5 s. Enviar una operación, esperar respuesta y consultar el estado si vence el plazo. No repetir automáticamente mutaciones cuyo resultado es incierto. Los identificadores correlacionan respuestas; no ofrecen deduplicación persistente.

Respuestas de hasta 4096 bytes en paquetes del tamaño del MTU negociado: uint16 little-endian ID de mensaje, uint16 offset, uint8 flags (bit0 inicio, bit1 final) y MTU − 8 bytes de JSON, entre 15 (MTU 23, sin negociar: paquetes de 20) y 239 (el equipo ofrece MTU 247: paquetes de 244). Antes de cada paquete se consulta si la controladora tiene hueco para la conexión; si en 50 ms no lo hay, se manda igual y se cuenta en `response_frames_forced`. El estado BLE informa también `att_mtu`, el MTU negociado (23 = sin negociar). Lógica en `lib/protocol/src/ble_frames.h`, probada en `test/ble_frames_test.cpp`; sin probar todavía contra un teléfono. El cliente valida offsets, desecha mensajes incompletos y consulta estado tras pérdidas; las notificaciones no son entrega garantizada. Cambiar de conexión invalida mensajes en cola. GET/PUT de configuración y GET de capacidades/estado usan el mismo controlador que HTTP. Las funciones sin controlador siguen devolviendo indisponibilidad; no hay falsa confirmación de grabación microSD.

## Solución (20 bytes, little-endian)

| Offset | Tipo | Significado |
| --- | --- | --- |
| 0 | uint16 | Secuencia; vuelve a 0 después de 65535 |
| 2 | uint8 | Calidad GGA 0–8 |
| 3 | uint8 | Satélites **rastreados** (GSV); 255 desconocido. Hasta 0.7.4, usados (GGA) |
| 4 | uint32 | Hora UTC del día en ms; **sin fecha** |
| 8 | int32 | Latitud × 10⁷ grados; INT32_MIN inválido |
| 12 | int32 | Longitud × 10⁷ grados; INT32_MIN inválido |
| 16 | int32 | Altura MSL del receptor en mm; INT32_MIN inválido |

Se notifica únicamente una época nueva con llegada menor a 500 ms, y **como máximo a 5 Hz** desde 0.7.6: al menos 190 ms entre envíos, por Bluetooth y por WebSocket (`protocol::kMinSolutionIntervalMs`); hasta 0.7.5 bastaban 20 ms. La app vence datos si dejan de llegar y distingue secuencia de época. No extrapolar ni repetir una posición para aparentar 10 Hz. No hay reloj UTC absoluto ni sincronización PPS validada. Extensiones de mensaje y otras referencias de altura requieren versión nueva; no reinterpretar campos silenciosamente.

## Salud (20 bytes, little-endian, 1 Hz)

La misma carga va por el WebSocket `/ws/telemetry` como trama de tipo `0x02`.

| Offset | Tipo | Significado |
| --- | --- | --- |
| 0 | uint8 | Versión del paquete: `1` |
| 1 | uint16 | Sigma horizontal de GST en mm, **del peor eje** (N/E); 0xFFFF sin estimación. Hasta 0.7.4, combinada |
| 3 | uint16 | Sigma vertical de GST en mm; 0xFFFF sin estimación |
| 5 | uint16 | Edad de la última corrección en s; 0xFFFF sin fuente |
| 7 | uint8 | Fuente activa: 0 ninguna, 1 BLE, 2 NTRIP, 3 radio |
| 8 | uint8 | Calidad GGA, espejo del paquete de solución |
| 9 | uint8 | IMU: reservado, siempre 0 |
| 10 | uint8 | Satélites usados (GGA); 255 desconocido. **Desde 0.7.5**; antes, 0 |
| 11–19 | — | Sin usar |

**Desde 0.7.5 la telemetría enseña lo mismo que el panel**, por decisión del
propietario: rastreados en el byte 3 de la solución y el peor eje en la sigma
horizontal de la salud. Es un cambio de significado de dos campos existentes, y
**no sube la versión, a propósito**: la app del propietario ya los lee y así
enseña lo mismo sin tocarla, mientras que una versión nueva podía dejarla sin
sigmas ni edad de correcciones si exige `1`. Quien necesite el significado
anterior lo distingue por `firmware_version` de `/api/status`: hasta 0.7.4, byte
3 = usados y sigma horizontal = combinada. Los usados siguen en el byte 10 y en
`solution.satellites_used`.

## Correcciones

Seleccionar `PUT /api/corrections/source {"source":"ble"}` después de autenticar. Escribir tramas RTCM3 fragmentadas; máximo de trama 1029 bytes, CRC24Q obligatorio. Antes de autenticar, los bytes no se procesan. Una sola fuente activa y generación por cambio de fuente; mensajes antiguos no deben pasar al nuevo transporte. Cola UART de cuatro tramas, caducidad 2 s y contadores de descartes. El callback BLE no escribe directamente a UART. Sin UART habilitado, se descartan y se informa `rtcm_available:false`.

Firmware y archivos grandes se transfieren por Wi-Fi/USB. BLE admite consultar estado OTA, pero no iniciar cargas ni restauraciones. Ningún módulo de radio está instalado todavía.
