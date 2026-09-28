# Protocolo BLE tal como estaba (v2, firmware 0.7.10)

Descripción completa y normativa en [`docs/ble-protocol.md`](../ble-protocol.md); lo que cambió
en v3 está en [BLE_CONTRACT.md](BLE_CONTRACT.md). Aquí, el inventario auditado.

| Aspecto | v2 (0.7.10) | Fuente |
| --- | --- | --- |
| Anuncio | Nombre del equipo (`MeridianV`, el del punto de acceso Wi-Fi) + UUID de servicio `a04c0001`; respuesta de escaneo | `ble_transport.cpp` `begin` |
| Conexión | Una a la vez (el anuncio se detiene al conectar y vuelve al desconectar); sin emparejamiento ni cifrado | `onConnect`/`onDisconnect` |
| MTU | El equipo ofrece 247; el teléfono elige; hasta negociar, 23 | `setMTU(kPreferredAttMtu)` |
| Intervalo de conexión | No se pedía: lo fijaba el teléfono (iOS 30 ms, Android ~45 ms) | — |
| Órdenes | JSON + LF por `a04c0002` **con respuesta**; ≤ 1024 B; `id` de correlación; cola de 2; caducidad 5 s | `CommandCallbacks`, `tick` |
| Respuestas | ≤ 4096 B en tramas del MTU: `uint16 id`, `uint16 offset`, `uint8 flags`; solo con hueco o a los 50 ms | `ble_frames.h` |
| Solución | 20 B binarios, ≤ 5 Hz, época nueva de < 500 ms | `tick` |
| Salud | 20 B binarios, 1 Hz **pero solo detrás de una solución nueva** | `tick` (defecto) |
| RTCM | Bytes RTCM3 nativos por `a04c0005` **solo con respuesta**; rearmado y CRC-24Q en el equipo; parser reiniciado a los 2 s sin bytes o al cambiar de conexión o de fuente | `CorrectionCallbacks` |
| Cola hacia el UM980 | **4 tramas**, caducidad 2 s | `gnss_receiver.cpp` (defecto) |
| Latido | No había: la salud dependía de la solución | — |
| Reconexión | Del lado del teléfono; el equipo solo vuelve a anunciarse | — |
| Descarte por generación | Sí: al conectar/desconectar se tiran peticiones y respuestas en curso | `generation` |

## Clase de cada mensaje

| Mensaje | Clase |
| --- | --- |
| Petición / respuesta JSON | CONTROL fiable |
| RTCM | FLUJO RTCM |
| Solución | TELEMETRÍA (estado) |
| Salud | TELEMETRÍA (estado); desde v3 también LATIDO |
| Contadores del estado BLE | DIAGNÓSTICO |

## Lo que estaba bien y se dejó igual

Fragmentación de respuestas con offset y detección de huecos, tamaño por MTU negociado,
correlación por `id`, descarte por generación, trabajos asíncronos con `job_id`, límites de
tamaño en las dos direcciones, RTCM sin envoltorio con su propio CRC.
