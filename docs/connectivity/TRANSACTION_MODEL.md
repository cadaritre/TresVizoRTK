# Modelo de transacciones de órdenes (CONTROL)

## Lo que ya había y se conserva

El protocolo de órdenes **ya tenía correlación**: cada petición lleva un `id` numérico que
vuelve en la respuesta, y las tramas de respuesta llevan su `messageId` con desplazamiento y
banderas de inicio y final. No es «mandar, esperar un rato y suponer». No se reescribe.

- Petición: `{id, method, path, key?, body?}` + LF, ≤ 1024 B, por `a04c0002` con respuesta.
- Respuesta: `{id, status, body}` ≤ 4096 B, por `a04c0003` en tramas del MTU.
- El equipo encola **2** peticiones; la 3.ª se tira y se cuenta (`dropped_requests`). Una
  petición de otra conexión o de más de 5 s se tira sin ejecutar.
- Las operaciones largas del receptor (configurar, perfiles, base) son **trabajos asíncronos**
  con `job_id` (`GnssJobRunner` en las apps): la orden devuelve 202 y se consulta el estado del
  trabajo. Nunca bloquean el bucle.
- Medido hoy: orden `GET /api/ble` = 60–93 ms de ida y vuelta; `max_request_dispatch_ms` = 2.

## Semántica del cliente

- **Una finalización**: éxito con `status`, error del equipo con su texto, plazo vencido o
  sesión cerrada. Nunca dos. Una respuesta con `id` desconocido o ya resuelto se descarta.
- **Plazo** desde que se confirmó la **última** escritura de la petición, no desde que se
  encoló (con RTCM delante, contar desde el encolado inventaba plazos vencidos: defecto D2 de la auditoría iOS).
- **Reintento solo de lo que es seguro repetir** (tabla). Una mutación con resultado incierto
  **no se repite sola**: se consulta el estado y se decide con lo que diga el equipo. El
  `GnssJobRunner` ya lo hace así («una respuesta perdida lanza exactamente una orden»).
- Al cortarse el enlace, las peticiones en vuelo terminan con «sesión cerrada»; al reconectar
  **no se reenvían**: la app vuelve a leer el estado.

## Clasificación de las rutas (firmware 0.7.11)

| Ruta | Método | Clase | ¿Reintento automático? |
| --- | --- | --- | --- |
| `/api/status`, `/api/ble`, `/api/config`, `/api/operations`, `/api/gnss/profile`, `/api/gnss/sky`, `/api/ntrip/profiles`, `/api/ntrip/sourcetable`, `/api/recording`, `/api/wifi/networks`, `/api/update` | GET | Consulta | Sí, acotado (una vez) |
| `/api/config`, `/api/corrections/source`, `/api/ntrip/input`, `/api/ntrip/server`, `/api/ntrip/caster`, `/api/ntrip/profiles`, `/api/ble` (`enabled`) | PUT / POST de estado | Idempotente (fija un valor) | **No** en caliente: tras plazo vencido, leer el estado y comparar |
| `/api/gnss/control`, `/api/base/plan`, `/api/wifi/scan` | POST | No idempotente (lanza un trabajo o un escaneo) | **No**: consultar el trabajo/estado |
| `/api/base/survey`, `/api/base/apply` | POST | Cambia el papel del receptor | **No**, nunca |
| `/api/restart` | POST | Destructiva | **Nunca**; tras reconectar, confirmar por `uptime_ms` |
| `/api/update/*`, `/api/recording/read`, `/api/access` | — | No admitidas por BLE (400 `unsupported_operation`) | — |

## Qué no se añadió y por qué

- **Deduplicación en el equipo por `id`**: haría falta guardar ids por conexión y la app ya no
  repite mutaciones. Si algún día hay reintento automático de mutaciones, primero va esto.
- **Id de transacción nuevo**: el `id` actual ya lo es. Cambiarlo rompería las apps de hoy sin
  ganar nada.
