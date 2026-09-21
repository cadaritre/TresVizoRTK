# Configuración avanzada del receptor UM980

Versión 0.6.0. Este documento describe los comandos expuestos al usuario avanzado,
su sintaxis verificada, la API del firmware y lo que **no** está comprobado.

## Verificación de sintaxis

Todos los comandos siguientes se contrastaron contra el
[manual de comandos Unicore N4, R1.6](https://en.unicore.com/uploads/file/Unicore%20Reference%20Commands%20Manual%20For%20N4%20High%20Precision%20Products_V2_EN_R1.6.pdf),
capítulos 4 (CONFIG), 5 (MASK) 7 (salidas de datos) y 8 (otros comandos). Se
indica el apartado del manual junto a cada uno. Sintaxis documentada no equivale
a ejecución validada: ver los límites al final.

| Operación | Comando | Rango y notas del manual |
| --- | --- | --- |
| Máscara de elevación | `MASK <ángulo>` | §5.2. De −90° a 90°. Valor de fábrica: 5°. |
| Deshabilitar constelación | `MASK GPS\|BDS\|GLO\|GAL\|QZSS` | §5.2. Detiene el seguimiento de ese sistema. |
| Habilitar constelación | `UNMASK GPS\|BDS\|GLO\|GAL\|QZSS` | §5.3. Inverso del anterior. |
| Consultar máscara | `MASK` | §5.1. Responde líneas `$CONFIG,MASK,<valor>`. |
| Undulación | `CONFIG UNDULATION Auto` o `CONFIG UNDULATION <separación>` | §4.4. Separación de −1000.0000 a +1000.0000 m, cuatro decimales. |
| Edad máxima de correcciones | `CONFIG DGPS TIMEOUT <segundos>` | §4.5. `0` desactiva el cálculo diferencial; `1`–`1800` s, enteros. |
| Salidas de mensajes | `<mensaje> [puerto] [tasa]` | §7. Ejemplo: `GPGGA COM2 0.1`. |
| Detener salidas | `UNLOG [puerto] [mensaje]` | §8.1. Sin mensaje detiene todas las de ese puerto. |
| Guardar en el receptor | `SAVECONFIG` | §8.4. Escribe la memoria no volátil. |

### Tasas de salida

El manual (§7) fija la correspondencia entre frecuencia y parámetro. El firmware
solo admite estos valores y los traduce con una tabla, no con `1/hz`:

| Frecuencia | Parámetro |
| --- | --- |
| 1 Hz | `1` |
| 2 Hz | `0.5` |
| 5 Hz | `0.2` |
| 10 Hz | `0.1` |
| 20 Hz | `0.05` |

Hasta 0.5.0 el firmware solo ofrecía 1, 5 y 10 Hz, y formateaba el parámetro con
un decimal, de modo que 20 Hz era inexpresable. Las 50 Hz que menciona el manual
dependen del producto y del firmware del receptor y no se ofrecen.

Las sentencias NMEA deben pedirse con prefijo `GP`, según indica el manual, aunque
la respuesta llegue como `GN`. El firmware admite `GPGGA`, `GPGST`, `GPRMC`,
`GPGSV`, `GPGSA`, `GPVTG` y `GPZDA`.

## API del firmware

`POST /api/gnss/control` conserva el modelo de una operación a la vez, con ACK
asociado al texto exacto del comando y lectura de estado cuando procede. **No hay
endpoint de comando libre**: cada acción arma una secuencia fija validada antes de
enviar nada.

| Cuerpo | Efecto |
| --- | --- |
| `{"action":"mask","elevation_deg":10}` | `MASK 10.00` |
| `{"action":"constellations","gps":true,"bds":true,"glo":true,"gal":false,"qzss":true}` | Un `MASK`/`UNMASK` por sistema |
| `{"action":"outputs","messages":[{"name":"GPGGA","hz":10}]}` | `GPGGA COM2 0.1` |
| `{"action":"rtcm_base","messages":[{"name":"RTCM1005","hz":5}]}` | `RTCM1005 COM2 0.2` |
| `{"action":"dgps_timeout","seconds":60}` | `CONFIG DGPS TIMEOUT 60` |
| `{"action":"stop_outputs"}` | `UNLOG COM2` |
| `{"action":"config_query"}` | `MASK`, con lectura de las líneas `$CONFIG,MASK,…` |
| `{"action":"save","confirm":true}` | `SAVECONFIG` |

Reglas de validación aplicadas antes de enviar: campos desconocidos se rechazan;
la lista de mensajes admite de 1 a 8 entradas de una lista blanca; no se permite
deshabilitar todas las constelaciones; `save` exige `confirm: true`. Un cuerpo
inválido devuelve 400 y **no** envía ningún comando.

`GET /api/gnss/profile` devuelve la configuración conocida. Distingue
explícitamente lo aplicado por este firmware de lo que solo se asume por defecto:

- `elevation_mask_deg` con `elevation_mask_applied`.
- `constellations` con `constellations_applied`.
- `nmea_outputs`, `rtcm_profile`, `dgps_timeout_s`.
- `height_reference`, `mask_readback`, `persisted_to_receiver`.

Cuando `*_applied` es `false`, el valor mostrado es el de fábrica según el manual,
no una lectura del receptor. El panel lo dice con esas palabras.

## Persistencia

Hasta 0.5.0 el firmware nunca enviaba `SAVECONFIG`, por diseño. La consecuencia
práctica se observó el 20/09/2026: tras apagar el receptor, la salida `GPGGA` de
COM2 configurada en caliente se perdió y el ESP32 quedó en `waiting_data` con cero
GGA, con el enlace UART intacto.

0.6.0 mantiene el valor por defecto de no guardar, y añade la operación explícita:

- Requiere `confirm: true` en la API y una casilla marcada en el panel.
- El panel advierte que guardar también hace persistente una configuración errónea.
- `persisted_to_receiver` solo pasa a `true` cuando el receptor confirma el comando
  en esta sesión; no se conserva entre reinicios del ESP32.

`FRESET` y `RESET` del manual (§8.2 y §8.3) **no** se exponen: borran efemérides,
posición y configuración del receptor y no forman parte de esta entrega.

## Bloqueos vigentes

Las operaciones de configuración siguen rechazándose, como antes, si hay grabación
activa, correcciones seleccionadas o un trabajo GNSS en curso. `raw_profile`
tampoco cambió: sigue requiriendo comprobar capacidad del enlace y almacenamiento.

## Límites y pendientes

- **Ningún comando nuevo se ha ejecutado contra el UM980 real.** La sintaxis está
  verificada contra el manual; la ejecución no. Al conectar el receptor debe
  repetirse `tests/device_services_smoke.py`, que ya cubre estas acciones.
- La lectura `MASK` se interpreta como texto y se muestra tal cual. No se convierte
  a un estado estructurado ni se usa para contradecir lo aplicado.
- Subir la máscara de elevación no mejora la exactitud por sí sola: reduce
  multitrayecto a costa de geometría. El panel lo advierte.
- `RTCM1006` queda fuera de la lista blanca: incorpora altura de antena y exige
  verificar su configuración antes de ofrecerlo.
- El perfil RTCM no comprueba que la base esté configurada ni que sus coordenadas
  se hayan verificado. Sigue vigente la regla de no publicar correcciones antes de
  contrastar coordenadas, referencia de altura y convergencia.
- No se controla el presupuesto de ancho de banda: varias sentencias a tasa alta
  pueden saturar los 115200 baudios del enlace. Debe medirse.

## Fuentes

- [Manual de comandos Unicore N4, R1.6](https://en.unicore.com/uploads/file/Unicore%20Reference%20Commands%20Manual%20For%20N4%20High%20Precision%20Products_V2_EN_R1.6.pdf).
- [Comandos investigados previamente](recording-base-ntrip.md) para base, RTCM y observaciones.
- [Servicios del ESP32](esp32-services.md) para el resto de la API.
