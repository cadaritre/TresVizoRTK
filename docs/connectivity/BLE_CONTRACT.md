# Contrato BLE del Meridian V — versión 3 (firmware 0.7.11)

Acordado el 27-09-2026 entre el firmware y las dos apps (canal: AGENT_COORDINATION.md). **Todo
es aditivo sobre la versión 2**: una app que solo sabe v2 sigue funcionando igual con 0.7.11, y
una app v3 funciona con un firmware v2 (se queda en el comportamiento v2). Nada cambió de UUID,
ni de formato de trama, ni de semántica de un campo existente.

## Tabla GATT

Sufijo común: `-8f24-4adb-a350-77ef6339c320`. Servicio `a04c0001`.

| UUID | Propiedades | Clase de tráfico | Uso |
| --- | --- | --- | --- |
| `a04c0002` | write (con respuesta) | CONTROL | Petición JSON `{id, method, path, key?, body?}` + LF, UTF-8, ≤ 1024 B, en trozos de `MTU − 3` |
| `a04c0003` | notify | CONTROL | Respuesta JSON ≤ 4096 B en tramas: `uint16 messageId`, `uint16 offset`, `uint8 flags` (bit0 inicio, bit1 final), carga de `MTU − 8` |
| `a04c0004` | notify | TELEMETRÍA (estado) | Solución, 20 B, ≤ 5 Hz, solo época nueva |
| `a04c0005` | write **y write-without-response (v3)** | RTCM | Flujo RTCM3 en trozos; el equipo rearma tramas y comprueba CRC-24Q |
| `a04c0006` | notify | TELEMETRÍA (estado) + LATIDO (v3) | Salud, 20 B, **1 Hz siempre** con el enlace arriba (v3) |

MTU: el equipo ofrece 247 (`protocol::kPreferredAttMtu`). Medido hoy con una Mac: 247. Nunca
suponer 20 B: el tamaño de escritura sale de `maximumWriteValueLength` (iOS) o del MTU
negociado − 3 (Android).

Conexión: el equipo pide **15–30 ms**, latencia 0, supervisión 4 s (dentro de las reglas de
Apple). El teléfono decide; el estado BLE dice el que quedó (`conn_interval_ms`).

## Reglas del cliente (v3)

1. **Órdenes**: siempre con respuesta. Una orden en vuelo por sesión (el equipo encola 2 y
   tira la 3.ª). El `id` correlaciona; el cliente descarta respuestas con `id` desconocido o
   repetido. Plazo por orden (el de hoy en las apps), contado desde que la **última** escritura
   se confirmó, no desde que se encoló. Tras un plazo vencido de una mutación: **no se
   repite**; se consulta el estado (ver TRANSACTION_MODEL.md).
2. **RTCM**:
   - Si `a04c0005` **anuncia** `writeWithoutResponse` en las propiedades **descubiertas**, el
     RTCM va sin respuesta, con el ritmo de la pila: iOS `canSendWriteWithoutResponse` y
     `peripheralIsReady(toSendWriteWithoutResponse:)`; Android, una escritura
     `WRITE_TYPE_NO_RESPONSE` en vuelo y la siguiente tras `onCharacteristicWrite`.
   - Si no la anuncia (firmware v2 o tabla GATT en caché), con respuesta, **una escritura en
     vuelo** y la siguiente tras la confirmación.
   - Nunca se decide por la versión del firmware: una tabla en caché puede esconder la propiedad
     (ver KNOWN_LIMITATIONS.md).
   - **Las órdenes pasan antes**: si hay una orden esperando, el siguiente hueco del carril es
     suyo. El RTCM nunca se encola en la pila del sistema más allá de una escritura.
   - Cola del teléfono acotada **por bytes y por edad**: solo tramas enteras, al llenarse se
     van las más viejas, lo que lleva más de 2 s desde que llegó de la red se tira. Todo
     descarte se cuenta con su motivo.
   - Al desconectar, la cola se vacía; al reconectar **no se reenvía nada viejo**.
3. **Latido**: tras conectar la app pide el estado BLE (`GET /api/ble`). Si `protocol_version
   >= 3` y la característica de salud se descubrió y se suscribió, se espera salud a 1 Hz; 3 s
   sin salud con el enlace arriba ⇒ estado degradado y **una** orden de estado; si esa orden
   vence ⇒ reconectar. Si no (v2 o sin la característica), la vida se juzga como en v2:
   cualquier notificación o respuesta completa, y las órdenes vencidas.
4. **Tabla GATT incompleta**: si falta `a04c0006` o `a04c0005` no trae `writeWithoutResponse`
   con un equipo que dice `protocol_version >= 3`, la sesión **sigue** (no se exige la salud
   para estar lista) y el diagnóstico lo dice. iOS: atender `peripheral(_:didModifyServices:)`
   redescubriendo y resuscribiendo sin duplicar. Android: `BluetoothGatt.refresh()` (oculto,
   por reflexión) una sola vez por conexión y volver a descubrir.

## Salud (a04c0006), bytes nuevos

| Byte | Tipo | v3 |
| --- | --- | --- |
| 16 | uint8 banderas | bit 0 precisión mostrada, bit 1 sigma cruda, **bit 2 (`0x04`) contadores RTCM en 17-19** |
| 17 | uint8 | Tramas RTCM **tiradas camino del UM980** (desalojadas por falta de sitio o caducadas). Contador módulo 256: la app mira la diferencia |
| 18 | uint8 | Tramas RTCM **rechazadas al llegar** (CRC o formato, en el router o en el rearmado BLE). Módulo 256 |
| 19 | uint8 | Ocupación de la cola hacia el UM980, % (0–100, redondeo hacia arriba); 255 = no se sabe |

Sin el bit 2, los bytes 17–19 no significan nada. Código: `lib/protocol/src/health_packet.h`,
pruebas en `test/health_packet_test.cpp`.

## Estado (`GET /api/ble` = `subsystems.ble` de `/api/status`)

Nuevos en v3: `protocol_version: 3`, `rtcm_write_without_response: true`,
`health_period_ms: 1000`, `conn_interval_ms` (número o `null`), `telemetry_skipped`,
`max_loop_gap_ms`, `max_request_dispatch_ms` (estos dos, desde la última conexión).

`subsystems.gnss` gana `correction_bytes_written`, `correction_frames_evicted`,
`correction_frames_expired`, `correction_queue_bytes`, `correction_queue_high_water_bytes`,
`correction_queue_capacity_bytes` (8192). `correction_frames_dropped` = desalojadas +
caducadas, como antes. Cuadre: `corrections.accepted_frames` = `correction_frames_sent` +
desalojadas + caducadas + las que queden en cola.

## Lo que no cambió (a propósito)

- Ni emparejamiento ni cifrado (decisión del propietario desde 0.6.2): ver SECURITY en
  KNOWN_LIMITATIONS.md.
- Versión del paquete de salud y de solución: siguen en 1; los campos nuevos van en bytes que
  estaban a 0.
- El RTCM va **sin envoltorio**: los bytes nativos RTCM3, que ya traen longitud y CRC-24Q. No
  hace falta secuencia propia: el enlace ATT es ordenado y fiable en capa de enlace; lo que se
  pierde en el equipo se cuenta en la salud.
