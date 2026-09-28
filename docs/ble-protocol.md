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
| 3 | uint8 | Satélites **usados** (GGA); 255 desconocido. En 0.7.5 y 0.7.6, rastreados |
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
| 1 | uint16 | **Precisión horizontal mostrada por Meridian V**, mm (ver abajo); 0xFFFF sin estimación. Hasta 0.7.8, sigma cruda del peor eje |
| 3 | uint16 | **Precisión vertical mostrada por Meridian V**, mm; 0xFFFF sin estimación. Hasta 0.7.8, sigma vertical cruda |
| 5 | uint16 | Edad de la última corrección en s; 0xFFFF sin fuente |
| 7 | uint8 | Fuente activa: 0 ninguna, 1 BLE, 2 NTRIP, 3 radio |
| 8 | uint8 | Calidad GGA, espejo del paquete de solución |
| 9 | uint8 | IMU: reservado, siempre 0 |
| 10 | uint8 | Satélites **rastreados** (GSV); 255 sin GSV reciente. En 0.7.5 y 0.7.6, usados; antes, 0 |
| 11 | uint8 | Satélites **visibles** (geometría sobre la máscara del receptor, calculados en el ESP32); 255 sin órbitas o sin posición. Antes de 0.7.10, 0 |
| 12 | uint16 | Sigma **cruda** del UM980, horizontal del peor eje (N/E), mm; 0xFFFF sin estimación. Desde 0.7.9 |
| 14 | uint16 | Sigma **cruda** del UM980, vertical, mm; 0xFFFF sin estimación. Desde 0.7.9 |
| 16 | uint8 | Banderas: bit 0 = bytes 1-4 son precisión mostrada; bit 1 = bytes 12-15 traen la cruda. 0 en firmware anterior |
| 17–19 | — | Sin usar |

**Precisión mostrada (desde 0.7.9).** Métrica de producto que fijó el
propietario el 27-09-2026; **no es una sigma del receptor**. La gobierna la sigma
horizontal cruda del UM980 (peor eje), en mm: `exceso = max(0, H − 35)`,
horizontal mostrada `10 + exceso`, vertical mostrada `15 + exceso`. Solo la
calcula el firmware (`lib/protocol/src/health_packet.h`, pruebas en
`test/health_packet_test.cpp`); las apps pintan lo que llega. Las sigmas crudas
no se modifican: van en los bytes 12-15 y en `/api/status` como `um980_raw_*`.

**Desde 0.7.7 cada byte trae lo que dice su nombre.** En 0.7.5 el propietario
pidió que la telemetría enseñara lo mismo que el panel, y se hizo cambiando el
byte 3 a rastreados. Salió mal: las apps lo seguían leyendo como usados, así que
por Bluetooth enseñaban rastreados con el nombre de usados, por Wi-Fi enseñaban
los usados de verdad y **cada punto se guardaba con los rastreados como si
fueran usados**. En 0.7.7 el byte 3 vuelve a ser usados, los rastreados pasan al
byte 10 de la salud y las apps enseñan esos; los puntos siguen guardando los
usados. La sigma horizontal sigue siendo la del peor eje, como en el panel.

La versión del paquete sigue en `1`, a propósito: una versión nueva podía dejar
sin sigmas ni edad de correcciones a una app que exige `1`. Quien lea un equipo
más viejo lo distingue por `firmware_version` de `/api/status`:

| Firmware | Byte 3 de la solución | Byte 10 de la salud | Sigma horizontal |
| --- | --- | --- | --- |
| Hasta 0.7.4 | Usados | 0 | Combinada √(σN² + σE²) |
| 0.7.5 y 0.7.6 | Rastreados | Usados | Peor eje |
| 0.7.7 y 0.7.8 | Usados | Rastreados | Peor eje |
| 0.7.9 | Usados | Rastreados | Bytes 1-4 = mostrada; cruda en 12-15 |
| Desde 0.7.10 | Usados | Rastreados (byte 11 = visibles) | Bytes 1-4 = mostrada; cruda en 12-15 |

Por HTTP (`/api/status` → `solution`): `satellites_used`, `satellites_tracked` y,
desde 0.7.10, `satellites_visible` (se omite si no se sabe). Desde 0.7.9,
`horizontal_sigma_m`, `north_sigma_m`, `east_sigma_m` y `vertical_sigma_m` traen
la **precisión mostrada** (los campos que la app ya pinta), más
`display_horizontal_precision_mm` y `display_vertical_precision_mm`; las sigmas
crudas de GST están en `um980_raw_horizontal_sigma_m` (combinada),
`um980_raw_north_sigma_m`, `um980_raw_east_sigma_m` y `um980_raw_vertical_sigma_m`.
`/api/gnss/sky` → `orbits` da el estado de las órbitas y los visibles por constelación.

## Correcciones

Seleccionar `PUT /api/corrections/source {"source":"ble"}` después de autenticar. Escribir tramas RTCM3 fragmentadas; máximo de trama 1029 bytes, CRC24Q obligatorio. Antes de autenticar, los bytes no se procesan. Una sola fuente activa y generación por cambio de fuente; mensajes antiguos no deben pasar al nuevo transporte. Cola UART de cuatro tramas, caducidad 2 s y contadores de descartes. El callback BLE no escribe directamente a UART. Sin UART habilitado, se descartan y se informa `rtcm_available:false`.

Firmware y archivos grandes se transfieren por Wi-Fi/USB. BLE admite consultar estado OTA, pero no iniciar cargas ni restauraciones. Ningún módulo de radio está instalado todavía.
