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
| a04c0005 | Escritura con respuesta ATT **y, desde 0.7.11, sin respuesta**: fragmentos RTCM3 |
| a04c0006 | Notificaciones: salud a 1 Hz (desde 0.7.11, siempre; antes solo detrás de una solución) |

**Dirección (desde 0.7.12).** El equipo se anuncia con una dirección **aleatoria estática**
derivada de la MAC Bluetooth del chip y de la generación de la tabla GATT
(`kGattTableGeneration`, `lib/protocol/src/ble_address.h`; 1 desde 0.7.12). Toda modificación de
esta tabla sube la generación: el equipo aparece con otra dirección y ningún teléfono se queda con
una copia vieja de la tabla (pasaba sin emparejamiento, ver
[KNOWN_LIMITATIONS.md](connectivity/KNOWN_LIMITATIONS.md)). `GET /api/ble` dice
`gatt_table_generation`, `address` y `address_type`. El formato de las tramas no cambió:
`protocol_version` sigue en 3.

## Versión 3 (firmware 0.7.11)

Todo aditivo; el contrato completo y las reglas del cliente están en
[`docs/connectivity/BLE_CONTRACT.md`](connectivity/BLE_CONTRACT.md). En resumen:

- `a04c0005` admite escritura **sin respuesta**. En ATT solo cabe una escritura con respuesta en
  vuelo por enlace, así que el RTCM y las órdenes compartían carril; y la respuesta ATT la manda
  la biblioteca antes de `onWrite`, así que nunca confirmó que la trama entrara a la cola. Medido
  con respuesta: tope de ≈2.8 kB/s a 30 ms de intervalo. La app decide por las propiedades
  descubiertas, no por la versión.
- La salud sale a 1 Hz **siempre** con el enlace arriba (es el latido) y sus bytes 17–19 llevan
  contadores de RTCM (bit 2 del byte 16).
- La cola hacia el UM980 es de 8 KiB por bytes (antes cuatro tramas), con las más viejas fuera
  en tramas enteras y caducidad de 2 s.
- El equipo pide conexión de 15 a 30 ms; la telemetría sale solo con hueco en la controladora y
  detrás de las respuestas.
- `GET /api/ble`: `protocol_version` 3 y métricas nuevas (`conn_interval_ms`,
  `telemetry_skipped`, `max_loop_gap_ms`, `max_request_dispatch_ms`, `health_period_ms`,
  `rtcm_write_without_response`).

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
| 1 | uint16 | **Precisión horizontal mostrada por Meridian V**, mm (ver abajo); 0xFFFF sin estimación **vigente** (ver «Vigencia»). Hasta 0.7.8, sigma cruda del peor eje |
| 3 | uint16 | **Precisión vertical mostrada por Meridian V**, mm; 0xFFFF sin estimación vigente. Hasta 0.7.8, sigma vertical cruda |
| 5 | uint16 | Edad de la última corrección en s; 0xFFFF sin fuente |
| 7 | uint8 | Fuente activa: 0 ninguna, 1 BLE, 2 NTRIP, 3 radio |
| 8 | uint8 | Calidad de la última GGA si llegó hace 2 s o menos; si no, **0 (sin solución vigente)**. Hasta 0.7.12, la última recibida por vieja que fuera |
| 9 | uint8 | IMU: reservado, siempre 0 |
| 10 | uint8 | Satélites **rastreados** (GSV); 255 sin GSV reciente. En 0.7.5 y 0.7.6, usados; antes, 0 |
| 11 | uint8 | Satélites **visibles** (geometría sobre la máscara del receptor, calculados en el ESP32); 255 sin órbitas o sin posición. Antes de 0.7.10, 0 |
| 12 | uint16 | Sigma **cruda** del UM980, horizontal del peor eje (N/E), mm; 0xFFFF sin estimación vigente. Desde 0.7.9 |
| 14 | uint16 | Sigma **cruda** del UM980, vertical, mm; 0xFFFF sin estimación vigente. Desde 0.7.9 |
| 16 | uint8 | Banderas: bit 0 = bytes 1-4 son precisión mostrada; bit 1 = bytes 12-15 traen la cruda; bit 2 = bytes 17-19 traen contadores RTCM (desde 0.7.11). 0 en firmware anterior |
| 17 | uint8 | Desde 0.7.11, con el bit 2 del byte 16: tramas RTCM tiradas camino del UM980 (módulo 256) |
| 18 | uint8 | Desde 0.7.11, con el bit 2: tramas RTCM rechazadas al llegar por CRC o formato (módulo 256) |
| 19 | uint8 | Desde 0.7.11, con el bit 2: ocupación de la cola hacia el UM980 en % (255 = no se sabe) |

**Vigencia de la calidad y la precisión.** La salud es también el latido: sale a
1 Hz **siempre** que el enlace está arriba, haya solución o no, y las apps la
toman por fresca porque llega cada segundo. Por eso lo que viene del receptor
caduca en el equipo, medido con el reloj monotónico del ESP32 desde la llegada
de la sentencia (no con la hora UTC de la GGA):

- Byte 8: la calidad de la última GGA si llegó hace **2 s** o menos; si no, o si
  no ha llegado ninguna desde el arranque, 0.
- Bytes 1–4 y 12–15: la precisión de la última GST si llegó hace 2 s o menos
  **y** hay solución vigente; si no, 0xFFFF en los cuatro (sin estimación). La
  sigma describe una solución: sin solución no hay precisión que enseñar, igual
  que en `/api/status`.
- 2 s y no los 500 ms con que se notifica la solución: la GGA puede ir a 1 Hz,
  la GST va siempre a 1 Hz y la salud sale con una fase cualquiera respecto a
  ellas. Con 500 ms, casi la mitad de los paquetes de un equipo sano saldrían
  vencidos y la precisión parpadearía; 2 s aguantan además una sentencia perdida
  suelta.
- No cambian por esto: la edad de las correcciones y la fuente (bytes 5–7), los
  rastreados y los visibles (10–11, cada uno con su propia vigencia: 10 s de GSV
  y 30 s del cálculo) ni los contadores RTCM (17–19).

Hasta 0.7.12 la salud copiaba la última GGA y la última GST sin mirar cuándo
llegaron: con el receptor mudo, seguía diciendo FIJO y dando la última
precisión indefinidamente, y las apps pintan la precisión de la salud. El
formato no cambia: 0 y 0xFFFF ya significaban «sin solución» y «sin
estimación». Código: `lib/protocol/src/health_timing.h` e
`include/health_solution.h`; pruebas en `test/health_solution_test.cpp`.

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

Seleccionar `PUT /api/corrections/source {"source":"ble"}` después de autenticar. Escribir tramas RTCM3 fragmentadas; máximo de trama 1029 bytes, CRC24Q obligatorio. Antes de autenticar, los bytes no se procesan. Una sola fuente activa y generación por cambio de fuente; mensajes antiguos no deben pasar al nuevo transporte. Cola UART de 8 KiB por bytes desde 0.7.11 (antes cuatro tramas), caducidad 2 s, las tramas más viejas fuera y enteras, y contadores de descartes con su motivo en `/api/status` → `subsystems.gnss`. El callback BLE no escribe directamente a UART. Sin UART habilitado, se descartan y se informa `rtcm_available:false`.

Firmware y archivos grandes se transfieren por Wi-Fi/USB. BLE admite consultar estado OTA, pero no iniciar cargas ni restauraciones. Ningún módulo de radio está instalado todavía.
