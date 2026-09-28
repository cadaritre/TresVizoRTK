# Matriz de aceptación

Estado al 27-09-2026 por la noche. **Nada se da por pasado sin evidencia.** El equipo estaba
por USB en la Mac, bajo techo (sin fix), con firmware 0.7.11 de `los-residentes`; el cliente BLE
fue la Mac (CoreBluetooth, app de banco hecha para esto), que tiene la tabla GATT del equipo en
caché de un firmware viejo (ver KNOWN_LIMITATIONS.md). Cómo correr cada prueba:
[ACCEPTANCE_PROCEDURES.md](ACCEPTANCE_PROCEDURES.md) y `tools/ble_bench/` (Barry).

| # | Prueba | Se espera | Resultado de hoy | Estado |
| --- | --- | --- | --- | --- |
| 1 | Conexión en frío | Descubre, MTU 247, suscripciones, lista para órdenes | Conecta en ~1 s tras el escaneo; MTU 247; intervalo 30 ms; `GET /api/ble` en 40–93 ms. Con una dirección de prueba (sin caché): **5 características**, `a04c0005` con `write` + `write no response` | **Pasa** (Mac) |
| 2 | Ciclos de conexión/desconexión | Sin suscripciones duplicadas ni estado viejo | 4 conexiones seguidas de la Mac sin fallos; el equipo vuelve a anunciarse cada vez | Parcial (sin apps) |
| 3 | RTCM continuo | Cuadran bytes enviados, aceptados y escritos | Con respuesta: 55 410 B en 20 s (**≈2.8 kB/s**, tope del carril). **Sin respuesta: 24.3 kB/s** saturando (1 423 tramas válidas de 1 424, la última cortada al parar; 0 CRC) y **5 kB/s en ráfagas de una época por segundo sin una sola pérdida** (160/160) | **Pasa** hasta el UART del equipo (la fuente activa era NTRIP: el router las rechazó por fuente, a propósito, y nada llegó al UM980) |
| 4 | RTCM + telemetría | La telemetría no se atrasa | **Salud a 1 Hz exacto sin fix** (intervalos 0.96–1.05 s) durante RTCM saturado y en ráfagas; `telemetry_skipped` = 0. Sin fix no hay solución que medir | Salud: **pasa**. Solución: pendiente con fix |
| 5 | Orden durante RTCM | La orden no espera detrás del RTCM | Con respuesta: 75–93 ms → 90–153 ms. **Sin respuesta, 5 kB/s en ráfagas: mediana 67 ms, p90 126 ms, máx. 221 ms** (61 órdenes, una cada 250 ms). Sin respuesta y enlace saturado a propósito (24 kB/s): 270–510 ms | **Pasa** con tráfico real; saturar el enlace no es uso real |
| 6 | Reinicio del receptor | La app detecta, reconecta y no repite órdenes | — | Pendiente (apps) |
| 7 | Bluetooth del teléfono apagado/encendido | Reconexión con backoff, sin bucles | — | Pendiente (teléfono) |
| 8 | Fuera de alcance y vuelta | Degradado → reconexión; sin RTCM viejo | — | Pendiente (campo) |
| 9 | Segundo plano / primer plano | Según la plataforma, sin estado corrupto | — | Pendiente (teléfono) |
| 10 | Pantalla bloqueada | Igual que 9 | — | Pendiente (teléfono) |
| 11 | Corte de NTRIP con BLE arriba | Se vacía la cola, edad de correcciones sube, nada viejo al volver | — | Pendiente (apps + NTRIP real) |
| 12 | FLOTANTE → FIJO | Transiciones sin saltos ni placas equivocadas | — | Pendiente (fix) |
| 13 | Datos malformados o parciales | Se descartan y se cuentan, nada se cuelga | Pruebas unitarias del rearmado de respuestas (C++ y apps) y de la cola RTCM (C++): en verde | Pasa en pruebas; sin inyección por radio |
| 14 | Telemetría alta | Solución a 5 Hz sin huecos de secuencia | Sin fix, 0 soluciones: correcto | Pendiente (fix) |
| 15 | Sesión larga (30–60 min) | Heap estable, sin reconexiones, contadores cuadran | — | Pendiente |
| 16 | Colas saturadas | Descartes contados, las más viejas fuera, tramas enteras | `rtcm_queue_test` (2 000 vueltas del anillo, cuadre exacto) en verde | Pasa en pruebas; sin ráfaga real |

## Cifras del equipo en la prueba (firmware 0.7.11)

- Heap interno libre tras arrancar ≈ 97 KB; 0.7.10 daba ≈ 106 KB. Tras las pruebas de estrés (≈ 800 KB de RTCM por BLE sin respuesta), libre 92.9 KB y **mínimo 84.9 KB**: la biblioteca BLE reserva memoria en cada escritura; vigilarlo en la sesión larga.
- Pila libre mínima: `gnss_rx` 4.7 KB, `loopTask` 5.1 KB, `ntrip_rx` 3.9 KB, `rtcm_out` 2.9 KB.
- UART del UM980: 5 GGA/s aceptadas, 0 rechazadas, 0 errores (el cable RX está bien).
- `max_loop_gap_ms` ≤ 6 y `max_request_dispatch_ms` ≤ 2 durante las pruebas.
- Cambiar la fuente de correcciones a BLE con NTRIP activo: 409 «Detén NTRIP y espera al GPS
  antes de cambiar fuente.» Correcto; la prueba de RTCM no tocó la configuración.

## Coexistencia Wi-Fi / BLE (hipótesis descartada con esta medida)

Con dos redes Wi-Fi guardadas y ninguna al alcance, el equipo lanza un escaneo Wi-Fi completo
cada 30 s (`instrument.cpp:954-957`), y el ESP32 comparte la radio entre Wi-Fi y BLE. Medido:
220 órdenes `GET /api/ble` seguidas durante 70 s, cada 250 ms, mientras escaneaba: **mediana
40 ms, p95 98 ms, máximo 126 ms**, sin picos cada 30 s; las latencias caen en múltiplos del
intervalo de conexión (30 ms). El escaneo no explica tirones del Bluetooth. Falta medirlo con el
NTRIP del propio equipo por Wi-Fi activo al mismo tiempo que RTCM por BLE.

## Lo primero para mañana

1. Con un teléfono que nunca se haya conectado: ¿ve 5 características y `a04c0005` con
   `write no response`? Si sí, repetir 3 y 5 sin respuesta con las apps de `los-residentes`.
2. Con fix y NTRIP real (MSM4 y MSM7): 3, 4, 5, 11, 12, 14, y 15 de al menos 30 min.
3. Reconexiones: 6, 7, 8 con las dos apps.
