# Contrapresión y colas acotadas

Regla: **ninguna cola crece sin límite y ningún descarte es silencioso.** Para cada cola: dónde
está, cuánto cabe, qué pasa al llenarse, qué caduca y dónde se ve.

## Del lado del equipo (firmware 0.7.11)

| Cola | Dónde | Capacidad | Al llenarse | Caducidad | Se ve en |
| --- | --- | --- | --- | --- | --- |
| Peticiones BLE | `ble_transport.cpp`, `requests` | 2 peticiones | Se tira la nueva | 5 s | `dropped_requests` |
| Respuesta en curso | `pending` (String) | 1 respuesta ≤ 4096 B | No se lee otra petición hasta vaciarla | Se tira al cambiar de conexión | — |
| Controladora BLE (notificaciones) | pila Bluedroid | la de la pila | Respuestas: se espera hasta 50 ms y se fuerza; telemetría: **no se manda** y sale la siguiente época | — | `response_frames_forced`, `telemetry_skipped` |
| RTCM hacia el UM980 | `gnss_receiver.cpp` + `lib/protocol/src/rtcm_queue.h` | **8 KiB** por bytes | **Se van las tramas más viejas, enteras** | 2 s o cambio de fuente | `correction_frames_evicted`, `_expired`, `_queue_bytes`, `_high_water_bytes`; salud bytes 17–19 |
| UART RX del UM980 | controlador | 8 KiB | Desborde del controlador | — | `uart_errors`, `line_overflows` |
| Grabación microSD | `sd_recorder.cpp` | búfer de flujo | Se tira lo que no cabe | — | `recording.dropped_bytes` |

**Por qué 8 KiB para el RTCM.** La UART al UM980 va a 115200 baudios (≈11.5 kB/s). Una época
MSM de cuatro constelaciones con 1005/1033/1230 son 6 a 10 tramas y unos 2–6 kB, y llega de
golpe (NTRIP del equipo: el socket la entrega en milisegundos; BLE sin respuesta: más rápido
que la UART). 8 KiB caben la época completa del peor caso mientras sale la anterior, y son unos
0.7 s de UART. Más no sirve: lo que espere más de 2 s se tira igual. Antes eran 4 tramas y se
tiraban tramas **en cada época**.

**Por qué las más viejas fuera.** Para corregir, una época nueva vale más que una atrasada: el
receptor descarta las correcciones viejas por sí mismo. Nunca se parte una trama: una trama a
medias en la UART le cuesta al UM980 también la siguiente, y una trama empezada se termina.

## Del lado del teléfono (las dos apps)

| Cola | Capacidad | Al llenarse | Caducidad | Se ve en |
| --- | --- | --- | --- | --- |
| RTCM del puente | acotada **por bytes** y por edad | las más viejas fuera, tramas enteras | 2 s desde que llegó de la red | contadores del puente (`flushedDropped`, `failedWrites`, `bytesWritten` y los de antes) |
| Escrituras RTCM en la pila del sistema | **1** en vuelo | se espera la confirmación (`didWriteValueFor` / `canSendWriteWithoutResponse` / `onCharacteristicWrite`) | — | — |
| Órdenes | 1 en vuelo | pasan **antes** que el RTCM en el siguiente hueco | plazo por orden | errores de la orden |
| Telemetría | no se encola: se guarda la última | — | edad con el reloj monotónico | — |

## Cuadre de bytes RTCM

red → cola del teléfono → escrito por BLE → aceptado por el equipo (`rtcm_valid_frames` del
rearmado BLE, `corrections.accepted_frames` del router) → escrito a la UART
(`correction_frames_sent`, `correction_bytes_written`) + desalojado + caducado + en cola.

Medido hoy: 215 tramas mandadas por BLE = 214 `rtcm_valid_frames` (la última se cortó al
parar la prueba) y 214 rechazadas por el router **porque la fuente activa era NTRIP**, que es
lo correcto: con la fuente equivocada, nada llega al UM980.
