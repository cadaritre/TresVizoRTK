# Clases de tráfico

Cada mensaje del enlace tiene una clase, y la clase decide cómo se entrega, qué pasa si no cabe
y qué prioridad tiene. Nada se trata igual «porque va por el mismo Bluetooth».

| Clase | Mensajes (hoy) | Sentido | Entrega | Si no cabe | Prioridad |
| --- | --- | --- | --- | --- | --- |
| **CONTROL** | Peticiones JSON (`a04c0002`), respuestas (`a04c0003`) | ↔ | Fiable: escritura con respuesta; respuesta con `id`, trozos con offset; plazo y consulta de estado | Petición: 3.ª en cola se tira y se cuenta; respuesta: espera hasta 50 ms por hueco y se fuerza | **1** (primero en el carril ATT del teléfono y en cada pasada del equipo) |
| **RTCM** | Tramas RTCM3 nativas (`a04c0005`) | teléfono → equipo | Flujo ordenado; sin respuesta si la característica lo anuncia, con ritmo de la pila; nada de ACK por trozo | Cola por bytes y edad en los dos lados; las más viejas fuera, enteras; contado | **2** |
| **TELEMETRÍA de estado** | Solución (`a04c0004`, ≤ 5 Hz), salud (`a04c0006`, 1 Hz); por WebSocket, tramas `0x01` y `0x02` con el mismo ritmo, la salud también sin solución | equipo → teléfono | Notificación sin confirmación; vale la más nueva | No se encola: se salta y sale la siguiente (`telemetry_skipped`) | **3** (solo con hueco, detrás de las respuestas) |
| **LATIDO** | La propia salud a 1 Hz (v3) | equipo → teléfono | Implícito | — | con la telemetría |
| **EVENTOS** | Hoy **no hay** notificaciones de evento: los cambios (alertas, fin de trabajo, cambio de papel) se leen por estado (`/api/status` → `alerts`, trabajos por `job_id`) | — | Consultas fiables | — | CONTROL |
| **DIAGNÓSTICO** | Contadores en `GET /api/ble` y `/api/status`, bytes 17–19 de la salud | ↔ | Por consulta y a 1 Hz | — | CONTROL / telemetría |
| **IMU futura** | No existe todavía | equipo → teléfono | Ver IMU_READINESS.md | — | — |

## WebSocket (`/ws/telemetry`)

Las mismas cargas que el Bluetooth (trama `0x01` solución y `0x02` salud: el tipo y los 20 bytes
del BLE) y las mismas reglas de estado: la salud a 1 Hz aunque no haya solución; la solución,
solo época nueva llegada hace ≤ 500 ms y a ≤ 5 Hz.

- **Envía la tarea httpd, no el bucle principal.** En cada pasada (20 ms) `loopTask` arma lo que
  toque y lo encola con `httpd_queue_work`; la lista de clientes solo la toca httpd. Hasta
  0.7.12 enviaba el bucle principal: un cliente que dejaba de confirmar lo paraba hasta 2 s
  (`send_wait_timeout`), Bluetooth y consola incluidos, y la lista se cambiaba desde dos tareas
  sin cerrojo.
- **Una tanda en vuelo como mucho.** Si la anterior no ha salido no se apila otra: nada se da por
  enviado y en la pasada siguiente se arma lo más nuevo (`sends_deferred`). Lo que espera más de
  500 ms en la tarea httpd —ocupada con una petición del panel o de la API, que puede esperar
  hasta 1 s al mutex del instrumento— se tira (`sends_expired`). Es el precio de no tocar sus
  sesiones desde otra tarea: mientras httpd atiende una petición, la telemetría espera.
- **Envío sin esperar** (`MSG_DONTWAIT`, `httpd_sess_set_send_override`). Si el búfer TCP del
  cliente está lleno (5760 bytes, unos 40 s de telemetría sin confirmar) o solo cabe parte de la
  trama, el cliente se cierra (`clients_dropped`) en el acto en vez de parar la tarea httpd 2 s.
  Una escritura parcial cuenta como fallo: la capa WebSocket de IDF 4.4 solo mira si el envío dio
  negativo (comprobado desensamblando `httpd_ws_send_frame_async`), y una trama cortada dejaría
  el flujo ilegible.
- Antes de escribir se comprueba que el descriptor sigue siendo un WebSocket
  (`httpd_ws_get_fd_info`): la sesión puede haberse cerrado y el número, reutilizado.
- Contadores en `/api/status` → `telemetry_stream`: `clients`, `frames_sent`, `clients_dropped`,
  `sends_deferred`, `sends_expired`.

## Qué es estado y qué es evento

- **Estado** (se puede coalescer, vale el último): posición, calidad, satélites, precisión,
  edad de correcciones, fuente activa, ocupación de la cola, batería cuando exista.
- **Evento** (no se puede coalescer ni perder): terminó un trabajo, cambió el papel base/rover,
  se reinició el equipo, falló una orden. Hoy ninguno viaja como notificación: todos se deducen
  de estado fiable (el `job_id` y su resultado, `uptime_ms`, `alerts`) y por eso no se pierden
  aunque se salte una notificación. Los contadores de la salud son acumulados por la misma razón:
  si se pierde un paquete, el siguiente trae la suma.

## Medido hoy (sin fix, bajo techo; firmware 0.7.11, Mac como central)

- Órdenes: 60–93 ms de ida y vuelta sin RTCM; 90–153 ms con RTCM con respuesta en marcha.
- RTCM con respuesta: ≈2.8 kB/s máximo a 30 ms de intervalo y MTU 247.
- Bucle del equipo: nunca más de 6 ms entre pasadas (`max_loop_gap_ms`) durante la prueba.
- Solución: 0 notificaciones, correcto sin fix ni hora UTC. Salud: no se pudo ver (la Mac tiene
  la tabla GATT vieja en caché y no descubre `a04c0006`).
