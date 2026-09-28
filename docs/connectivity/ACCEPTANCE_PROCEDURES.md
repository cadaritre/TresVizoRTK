# Procedimientos de aceptación del Bluetooth

Cómo se ejecuta cada prueba de la matriz de [`ACCEPTANCE_TESTS.md`](ACCEPTANCE_TESTS.md), qué
se espera, qué mirar y cuándo se declara «pasa» o «falla». La numeración es la de esa matriz.

Herramienta: `tools/ble_bench/` (banco desde la Mac). Lo que el banco no puede hacer (segundo
plano, pantalla bloqueada, Bluetooth del teléfono) se hace con las apps y aquí se dice cómo.

> **Qué demuestra y qué no.** El banco mide el enlace entre la Mac y el Meridian V con el
> firmware real. No mide las apps: una prueba que pasa con el banco y falla con una app señala
> a la app. Y lo que corre sin radio (simulador, reproducción, pruebas unitarias) solo demuestra
> que el banco mide bien, **nada del equipo**.

## 0. Preparación (una vez)

### Instalar el banco

`bleak` no viene con Python. En un entorno propio, sin tocar el Python del sistema:

```sh
python3 -m venv ~/.venvs/meridian-bench
~/.venvs/meridian-bench/bin/python -m pip install "bleak>=0.22"
```

Si `pip` no encuentra ruedas de `pyobjc` para Python 3.14 (bleak las necesita en macOS), crear
el entorno con un Python anterior (`python3.13 -m venv …`). La primera conexión hace que macOS
pida permiso de Bluetooth para la Terminal (Ajustes → Privacidad y seguridad → Bluetooth).

En lo que sigue, desde la raíz del repositorio del firmware:

```sh
BANCO="$HOME/.venvs/meridian-bench/bin/python tools/ble_bench"
$BANCO list                       # escenarios y sus valores por defecto
$BANCO run telemetria --sim       # ensayo contra el simulador, sin radio
```

Cada `run` deja en `tools/ble_bench/sesiones-banco/<fecha>-<escenario>/` (fuera de git):

- `sesion.jsonl`: todo lo que pasó, con marca de tiempo monotónica de la Mac; se reproduce con
  `$BANCO replay …/sesion.jsonl` y da el mismo resumen.
- `eventos.csv`: lo mismo, plano, para una hoja de cálculo.
- `resumen.txt`: el resumen en español que sale al final.

**Nunca se graban credenciales**: el banco solo pide rutas de estado (lista cerrada en
`bench/runner.py`) y borra cualquier clave con pinta de secreto antes de escribir.

### Antes de cada sesión de pruebas

1. **Un solo cliente.** El firmware atiende una conexión BLE: cerrar la app en todos los
   teléfonos cercanos o apagarles el Bluetooth. Si el banco dice «no se encontró el Meridian V
   anunciándose», casi siempre es esto.
2. **Firmware.** El resumen trae `firmware_version` y la línea «estado BLE al conectar» con
   `protocol_version`. Estos procedimientos son para el contrato v3 (0.7.11); con v2 la salud
   no sale sin solución y la escritura sin respuesta no existe.
3. **Tabla GATT en caché.** Si el resumen dice «⚠ tabla GATT en caché», la pila de ese lado
   recuerda la tabla de un firmware viejo: falta la salud y el RTCM irá **con respuesta**
   (tope medido ≈2.8 kB/s). Así está hoy la Mac del banco (KNOWN_LIMITATIONS.md). Las pruebas
   de RTCM sin respuesta necesitan un cliente sin esa caché (un teléfono que nunca se conectó,
   u otra Mac). No hay forma soportada y comprobada de borrarla en macOS; el 27-09 se esquivó
   con un firmware de prueba que cambiaba la dirección del equipo (ya retirado).
4. **Fuente de correcciones.** El ESP32 solo admite RTCM por BLE si la fuente activa es `ble`.
   El banco la consulta y avisa; con `--select-ble-source` la cambia él
   (`PUT /api/corrections/source`, lo único que el banco modifica en el equipo). Con NTRIP
   activo en el equipo el firmware contesta 409: detener NTRIP antes, desde el panel.
5. **RTCM sintético.** Sin `--rtcm-file`, el banco genera MSM7 (o `--msm 4`) de cuatro
   constelaciones con 1005/1033/1230 cada 10 s, ~1 kB por época. El contenido es inventado:
   **el UM980 no fija con él**. Con `--inert` las tramas llevan el número de mensaje 4095 en vez
   de los reales (no se ha comprobado qué hace el UM980 con un número desconocido). Para las
   pruebas con fix (4, 11, 12, 14) las correcciones tienen que venir de un caster real, por la
   app. Si hay una captura real (`.rtcm3`), `$BANCO rtcm-check archivo` la valida como lo haría
   el ESP32 y `--rtcm-file archivo` la repite en bucle.

## Cómo leer el resumen

| Línea | Qué es | De dónde sale |
| --- | --- | --- |
| `notificaciones: solution/health` | Cuántas, ritmo medio dentro de cada conexión, intervalo máximo entre dos y p95 | Marca de llegada en la Mac |
| `solución: N paquetes perdidos por secuencia` | Huecos en el `uint16` de secuencia (con vuelta a 0). Desde 0.7.11 una solución que el equipo no pudo mandar por falta de hueco **no** consume secuencia y se cuenta en `telemetry_skipped`: un hueco de secuencia es pérdida después del equipo | Bytes 0-1 de `a04c0004` |
| `saltos atrás o repetidos` | La secuencia volvió atrás o se repitió dentro de una conexión (se cuenta por conexión) | Ídem |
| `⚠ el equipo se reinició` | `uptime_ms` volvió atrás entre dos fotos del estado; el cuadre se corta ahí | `/api/status` |
| `cambios de calidad` | Transiciones de la calidad GGA con su instante | Byte 2 de la solución |
| `⚠ 0 bytes de telemetría del receptor` | `accepted_gga` y `native_frames_valid` a 0 en `/api/status`: el ESP32 no oye al UM980. **No es un fallo de Bluetooth** | `subsystems.gnss` |
| `✘ latido` | Más de 3 s sin salud con el enlace arriba y `protocol_version ≥ 3` | Contrato v3, regla 3 |
| `órdenes … vencidas / cortadas por desconexión / respuestas sin petición` | Correlación por `id`; «sin petición» = una respuesta cuyo `id` no esperaba nadie | `a04c0003` |
| `latencia de órdenes p50/p95/máx` | Desde que se empieza a escribir la orden hasta la última trama de la respuesta, por ruta | Reloj monotónico de la Mac |
| `rearmado de respuestas: anomalías` | `gap` (falta una trama), `duplicate`, `out_of_order`, `orphan`, `restarted`, `invalid_length`, `too_large`, `expired` | `bench/protocol.py` |
| `RTCM: modo de escritura` | `sin respuesta` si la característica descubierta anuncia `write-without-response`; si no, `con respuesta`. Se decide por las propiedades descubiertas, nunca por la versión | `bench/runner.py` |
| `descartes de la Mac` | La cola de la Mac imita la del teléfono (contrato v3): tramas enteras, lo que lleva más de 2 s se tira y, pasados 16 KiB, se van las más viejas. Al cortar se vacía: nada se reenvía | `bench/runner.py` |
| `⚠ caudal por debajo del pedido` | El carril no da el ritmo pedido (típico con respuesta, ≈2.8 kB/s medidos); lo que no cupo se tiró por viejo, no se acumuló | Ídem |
| Cuadre RTCM | generadas → enviadas → válidas en el ESP32 → aceptadas por el enrutador → escritas al UM980 + desalojadas + caducadas + en cola, con ✔/✘ en cada salto | Eventos del banco y `/api/status` antes y después |
| `según la salud (v3)` | Lo mismo visto desde los bytes 17-19 de la salud (diferencias módulo 256) | `a04c0006` |
| `equipo (v3)` | `conn_interval_ms`, `telemetry_skipped`, `max_loop_gap_ms`, `max_request_dispatch_ms` | `subsystems.ble` |

## Umbrales

Propuestos para declarar «pasa»; **se confirman o se cambian** en ACCEPTANCE_TESTS.md antes de
la sesión con el equipo.
Cada uno con su motivo.

| Umbral | Valor | Motivo |
| --- | --- | --- |
| Latencia de orden sin RTCM, p95 | ≤ 150 ms | Hoy se midieron 60-93 ms con la Mac a 30 ms de intervalo: el doble deja margen para un teléfono |
| Latencia de orden con RTCM, p95 / máximo | ≤ 250 ms / ≤ 1 s | Por encima de ¼ s el operador nota la espera; un segundo es el límite antes de pensar que no respondió. Referencia del 27-09 (0.7.11, sin respuesta, 5 kB/s en ráfagas de una época): mediana 67, p90 126, máx 221 ms |
| Latencia de orden saturando el carril | sin vencidas; se anota el valor | Saturando a propósito subieron a 270-510 ms (el 27-09): lo ya entregado a la controladora no se adelanta. No es criterio de fallo, sí dato |
| Órdenes vencidas | 0 | El plazo (5 s) es el del firmware: vencer una orden es perder una respuesta |
| Anomalías de rearmado | 0 | ATT es fiable y ordenado en la capa de enlace; cualquier anomalía es un defecto |
| Solución con fix | 4.8-5.0 Hz, 0 huecos de secuencia en 10 min, intervalo máx ≤ 400 ms | 5 Hz es el tope del firmware (190 ms entre envíos); 400 ms = dos épocas |
| Salud (v3) | intervalo máx ≤ 1.5 s; nunca > 3 s | 1 Hz con la fluctuación del bucle; 3 s es el umbral de «medio muerta» del contrato |
| RTCM hasta 6 kB/s | enviadas = válidas en el ESP32; desalojadas + caducadas = 0 | Un caster MSM7 de 4 constelaciones ronda 1-1.5 kB/s; 6 kB/s es 4× eso. El 27-09 el carril sin respuesta llegó a 24.3 kB/s sin pérdidas |
| Heap mínimo en 60 min | no baja más de 2 KB después de los 5 primeros minutos | Una fuga lenta es lo que tumba una jornada; 2 KB separa el ruido de la tendencia |

## 1. Conexión en frío

- **Se espera**: escaneo, conexión, tabla completa (5 características, `a04c0005` con
  `write-without-response`), MTU 247, suscripciones, `GET /api/ble` con `protocol_version: 3`,
  salud a 1 Hz desde el primer segundo y, con fix, solución a 5 Hz.
- **Banco**: equipo recién encendido, `$BANCO run telemetria --duration 60`. Repetir 5 veces
  apagando y encendiendo el equipo entre medias.
- **App**: con la app cerrada del todo, abrirla y conectar; cronometrar hasta que dice «listo».
- **Mirar**: `tiempo hasta listo`, `MTU visto por la Mac`, la línea `estado BLE al conectar`,
  que no haya `⚠ tabla GATT en caché`, ritmo de salud y de solución.
- **Pasa** si las 5 conexiones llegan a listo en < 5 s desde que empieza el escaneo, sin aviso
  de caché y con la salud en ≤ 1.5 s. **Falla** si alguna no conecta, si falta una
  característica con un cliente sin caché, o si la primera salud tarda más de 3 s.

## 2. Ciclos de conexión y desconexión

- **Se espera**: cada ciclo vuelve al mismo estado; ninguna suscripción duplicada (se vería
  como salud a 2 Hz), ninguna respuesta de la conexión anterior en la siguiente.
- **Banco**: `$BANCO run reconexiones --cycles 50`.
- **App**: 20 veces conectar y desconectar desde la interfaz, sin cerrar la app.
- **Mirar**: la nota `ciclos con conexión y respuesta: N de 50`, `tiempo hasta listo` p50 y
  máximo, `respuestas sin petición`, anomalías `orphan`/`restarted`, y en el equipo
  `dropped_requests` (contadores que cambiaron).
- **Pasa** con 50 de 50, máximo hasta listo ≤ 2× el p50, 0 respuestas sin petición y
  `dropped_requests` sin cambios. **Falla** con cualquier ciclo perdido o con salud a más de
  1.1 Hz en una conexión.

## 3. RTCM continuo

- **Se espera**: todo lo enviado llega válido al ESP32 y se escribe al UM980; cuadre exacto.
- **Banco**, 2 min cada uno:
  `$BANCO run rtcm-1k --select-ble-source`, luego `rtcm-3k` y `rtcm-6k`. Repetir `rtcm-3k`
  con `--msm 4`. Con escritura con respuesta (caché), 6 kB/s no es alcanzable: el banco lo
  dice con `⚠ caudal por debajo del pedido` y los descartes por edad en la Mac; anotarlo, no es
  un fallo del equipo.
- **Mirar**: el bloque del cuadre, `caudal`, `tiempo por trama p95`, y la línea de la cola.
- **Pasa** si en los tres ritmos: `✔ enviadas = válidas en el ESP32`, `✔ aceptadas = escritas
  + desalojadas + caducadas + en cola` con desalojadas y caducadas a 0, y el caudal medido está
  a menos del 5 % del pedido (sin respuesta). **Falla** con cualquier `✘`, CRC malos > 0 o
  tramas desalojadas a ≤ 6 kB/s.

## 4. RTCM + telemetría

- **Se espera**: con correcciones fluyendo la solución no se atrasa ni pierde épocas.
- **Condición**: con fix. Las correcciones reales las mete la app (NTRIP del teléfono); el
  banco no puede estar conectado a la vez. Por eso se hace en dos partes:
  1. Referencia con el banco, sin RTCM: `$BANCO run telemetria --duration 300`.
  2. Carga con el banco y RTCM sintético (el receptor perderá el fix, la telemetría sigue):
     `$BANCO run rtcm-ordenes --rate 6000 --duration 300 --select-ble-source`.
  3. Con la app y un caster real: 10 min en FIJO mirando que la placa no parpadee.
- **Mirar**: ritmo de solución, huecos de secuencia, intervalo máximo, `telemetry_skipped`.
- **Pasa** si con carga el ritmo cae menos de 0.2 Hz respecto a la referencia, 0 huecos de
  secuencia, `telemetry_skipped` no sube y el intervalo máximo ≤ 400 ms. **Falla** si no.

## 5. Orden durante RTCM

- **Se espera**: las órdenes no esperan detrás del RTCM (regla 2 del contrato: la orden pasa
  primero).
- **Banco**: `$BANCO run rtcm-ordenes --rate 3000 --command-period 1 --select-ble-source` y la
  misma con `--rate 6000`. Para medir lo que aporta la prioridad, repetir con
  `--no-command-priority`.
- **Mirar**: latencia de `GET /api/ble` p50/p95/máx con y sin RTCM (la referencia sale del
  escenario `telemetria` o de la primera orden de cada conexión), vencidas.
- **Pasa** con los umbrales de la tabla (p95 ≤ 250 ms, máx ≤ 1 s, 0 vencidas) a 3 y 6 kB/s.
  **Falla** si una sola orden vence o si el p95 con RTCM pasa de 250 ms.

## 6. Reinicio del receptor

- **Se espera**: la desconexión se detecta como inesperada, la reconexión llega sola con la
  escalera 1-2-4-8-16-30 s, la secuencia de solución vuelve a empezar, **no se reenvía RTCM
  viejo y no se repite ninguna orden que cambie el equipo**.
- **Banco**: `$BANCO run sesion-larga --duration 300 --select-ble-source` y, hacia el minuto 2,
  apagar y encender el Meridian V (o reiniciarlo desde el panel web). El banco no reinicia el
  equipo por su cuenta.
- **App**: con la app en la pantalla principal, RTCM entrando y una orden de cambio hecha
  justo antes, reiniciar el equipo.
- **Mirar**: `desconexiones inesperadas 1`, la nota de reconexión, `⚠ el equipo se reinició 1
  vez` (lo delata `uptime_ms` en la foto tomada al reconectar), los contadores del equipo desde
  el reinicio (el banco no cuadra el RTCM a través de un reinicio: los contadores del equipo
  vuelven a cero y lo dice con un `✘`), y en la app que la orden de cambio no se volvió a
  mandar (registro de la app o `GET /api/config`).
- **Pasa** si vuelve sola en < 30 s tras el arranque del equipo, los contadores desde el
  reinicio no tienen caducadas ni CRC malos y la app no repitió la mutación. **Falla** si hay
  que tocar algo, si se repite una mutación o si llegan tramas con más de 2 s
  (`correction_frames_expired` sube tras reconectar).

## 7. Bluetooth del teléfono apagado y encendido

- **Solo con la app** (el banco no controla el Bluetooth de la Mac).
- **Pasos**: conectado y con RTCM, apagar el Bluetooth del teléfono 10 s, encender; repetir
  con 60 s.
- **Se espera**: la app pasa a desconectado con causa distinguible (no «error»), no reintenta
  en bucle mientras el Bluetooth está apagado, y al encenderlo reconecta sola y rehace las
  suscripciones una sola vez.
- **Pasa** si reconecta en < 10 s tras encender, sin suscripciones dobles (salud a 1 Hz) ni
  RTCM viejo. **Falla** si hay que reconectar a mano o si la app se queda en un estado que no
  corresponde.

## 8. Fuera de alcance y vuelta

- **Se espera**: al perder el enlace, degradado y luego desconexión inesperada; al volver,
  reconexión con la escalera; la cola del teléfono se vacía y no se manda nada con más de 2 s.
- **Banco** (portátil): `$BANCO run sesion-larga --duration 600 --select-ble-source` y alejarse
  con la Mac hasta perder el enlace; volver al minuto.
- **App**: lo mismo con el teléfono, con NTRIP real.
- **Mirar**: la nota de reconexión y en cuántos intentos, `rtcm_discarded`, que tras volver el
  cuadre no tenga caducadas nuevas en el equipo.
- **Pasa** si vuelve sola en ≤ 2 escalones de la escalera tras recuperar la cobertura y no hay
  tramas caducadas en el equipo por RTCM viejo. **Falla** si no vuelve o si al volver sube
  `correction_frames_expired` de golpe.

## 9. Segundo plano / primer plano

- **Solo con la app.** iOS declara el modo de fondo `bluetooth-central`
  (`INFOPLIST_KEY_UIBackgroundModes` en el proyecto) y no usa restauración de estado; Android
  mantiene la sesión en un servicio en primer plano `connectedDevice` (manifiesto).
- **Pasos**: conectado, con RTCM, mandar la app al fondo 1 min, 5 min y 15 min; volver.
- **Se espera**: iOS mantiene el enlace y las correcciones mientras el sistema no la suspenda;
  Android igual con su notificación visible. Al volver, la pantalla refleja el estado real sin
  reconectar si el enlace siguió vivo.
- **Pasa** si en los tres tiempos la sesión sigue o, si el sistema la cortó, vuelve sola al
  primer plano sin estado corrupto (posición congelada que parece viva, placa equivocada).
  **Falla** si al volver hay datos viejos pintados como actuales.

## 10. Pantalla bloqueada

- Igual que 9, bloqueando la pantalla en vez de cambiar de app. Mismos criterios.

## 11. Corte de NTRIP con el Bluetooth arriba

- **Solo con la app** y un caster real (el banco no hace NTRIP).
- **Pasos**: en FIJO, quitar los datos móviles del teléfono (sin tocar el Bluetooth) 30 s y
  devolverlos.
- **Se espera**: la edad de correcciones de la salud (bytes 5-6) sube de segundo en segundo;
  la cola hacia el UM980 (byte 19) baja a 0; al volver la red **no llega un golpe de tramas
  viejas**: el teléfono tira lo que tenga más de 2 s.
- **Banco, complementario**: `$BANCO run rafagas --burst 10 --select-ble-source` imita a un
  caster que entrega 10 s de golpe.
- **Pasa** si al volver la edad baja a ≤ 2 s en menos de 5 s y `correction_frames_expired` no
  sube más que las tramas de un segundo. **Falla** si el equipo recibe tramas viejas en ráfaga.

## 12. FLOTANTE → FIJO

- **Solo con correcciones reales** (app + caster). El banco puede estar conectado *en lugar
  de* la app solo si las correcciones entran por NTRIP del propio equipo.
- **Pasos**: arrancar en autónomo a cielo abierto, meter correcciones, esperar FIJO; tapar la
  antena para caer a FLOTANTE y destaparla.
- **Mirar**: con el banco (`$BANCO run telemetria --duration 600`), la línea `cambios de
  calidad` con sus instantes; con la app, que la placa siga esos cambios sin saltos ni placas
  equivocadas, y sin contador de segundos junto a FIJO.
- **Pasa** si cada cambio del receptor aparece en la app en ≤ 1 s y no hay cambios que el
  receptor no hizo. **Falla** si la app enseña FIJO con el receptor en FLOTANTE, aunque sea un
  instante.

## 13. Datos malformados o parciales

- **Banco**: `$BANCO run malformados --select-ble-source`. Manda una trama de cada 7 con CRC
  roto y una de cada 11 sustituida por ruido que empieza por 0xD3, más una orden que no es JSON.
- **Se espera**: el ESP32 cuenta CRC malos y sigue aceptando las buenas; la orden malformada
  recibe un 400 `invalid_request` sin `id` (el resumen lo cuenta como «respuesta sin petición»);
  nada se desconecta y la salud no se interrumpe.
- **Mirar**: `rtcm_crc_errors` en los contadores que cambiaron, la línea «corruptas a
  propósito», `estados {400: 1}`, `desconexiones inesperadas 0`, `✘ latido` ausente.
- **Pasa** si `rtcm_crc_errors` sube al menos lo que las de CRC roto, las válidas son al menos
  las buenas enviadas menos una por bloque de ruido (el ruido puede arrastrar la siguiente), hay
  exactamente un 400 y no hay desconexión. **Falla** si el equipo deja de aceptar tramas buenas,
  se reinicia o deja de contestar órdenes.
- Sin radio: `cd tools/ble_bench && python3 -m unittest` cubre rearmado, huecos, duplicados,
  desorden, longitudes inválidas y el parser RTCM contra las cabeceras del firmware compiladas.

## 14. Telemetría alta

- **Condición**: con fix.
- **Banco**: `$BANCO run telemetria --duration 600`.
- **Pasa** con solución a 4.8-5.0 Hz, 0 huecos de secuencia, intervalo máximo ≤ 400 ms y
  `telemetry_skipped` sin subir. **Falla** con cualquier hueco de secuencia (pérdida después
  del equipo) o con `telemetry_skipped` subiendo (el equipo no encuentra hueco en la radio).

## 15. Sesión larga (30-60 min)

- **Banco**: `$BANCO run sesion-larga --duration 3600 --select-ble-source` (RTCM a 1 kB/s,
  `GET /api/ble` cada 10 s, foto del estado cada 5 min, reconexión sola si se cae).
- **App**: una hora de trabajo normal con NTRIP real, midiendo puntos.
- **Mirar**: desconexiones inesperadas, latencias, el cuadre, `min_free_heap_bytes` en las fotos
  periódicas (en `eventos.csv`, eventos `status`), `max_loop_gap_ms`.
- **Pasa** con 0 desconexiones inesperadas, cuadre exacto, heap dentro del umbral y latencias
  dentro de la tabla. **Falla** con cualquier reconexión, `✘` en el cuadre o heap bajando de
  forma sostenida.

## 16. Colas saturadas

- **Se espera**: con más RTCM del que la UART puede sacar (11.5 kB/s a 115200 baudios), la
  cola de 8 KiB se llena, se desalojan **las más viejas en tramas enteras**, todo descarte se
  cuenta, y las órdenes y la telemetría siguen.
- **Banco**: `$BANCO run saturacion --select-ble-source` (14 kB/s). Solo es alcanzable con
  escritura sin respuesta; con la caché de la Mac el carril no pasa de ≈2.8 kB/s y la prueba no
  satura: anotarlo como «no ejecutable con este cliente».
- **Mirar**: `desalojadas` > 0, `✔ aceptadas = escritas + desalojadas + caducadas + en cola`,
  byte 19 de la salud cerca de 100 %, `según la salud (v3)` igual al estado, órdenes sin
  vencer, sin desconexión.
- **Pasa** si todo lo anterior se cumple. **Falla** si el cuadre no cierra, si una orden vence o
  si el equipo se desconecta o se reinicia.

## Pruebas de regresión sin equipo

- `cd tools/ble_bench && python3 -m unittest`: decodificador contra los vectores del firmware y
  contra las cabeceras compiladas (`tests/firmware_parity.cpp`; con
  `MERIDIAN_FIRMWARE_LIB=…/firmware/esp32/lib` se compara con otra copia del firmware),
  escenarios contra el simulador, grabar y reproducir.
- Una sesión grabada se reproduce igual (`$BANCO replay`). Para convertirla en prueba de
  regresión: `$BANCO anonymize …/sesion.jsonl tools/ble_bench/tests/fixtures/<qué-es>.jsonl`
  (tapa nombres de red, IP y el nombre del equipo sin cambiar el troceo) y correr las pruebas:
  la primera vez escriben su `.resumen.txt` de referencia para revisarlo; después, cualquier
  cambio del decodificador o del análisis que cambie las conclusiones hace fallar la prueba.
