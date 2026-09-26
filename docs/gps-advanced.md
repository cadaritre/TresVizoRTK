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

## Los satélites uno a uno · `GET /api/gnss/sky`

Hasta ahora el firmware solo publicaba **cuántos** satélites entraron en la
solución, que es lo que trae GGA. Con eso no se puede dibujar un cielo ni se
puede distinguir el problema más común del campo: un equipo que **ve** veinte y
**usa** ocho tiene una máscara de elevación o una constelación apagada; uno que
ve ocho tiene una antena, un cable o un cielo tapado. El número solo no separa
los dos casos, y llevan a arreglos distintos.

Se añadieron dos analizadores —`lib/gnss/src/nmea_gsv.h` y `nmea_gsa.h`— y la
tabla que los junta, `lib/gnss/src/sky_table.h`. Los tres se prueban en el Mac
con `test/nmea_gsv_test.cpp`, `test/nmea_gsa_test.cpp` y `test/sky_table_test.cpp`.

### Lo que hay que respetar de NMEA 4.10, o los números salen mal

El firmware configura `CONFIG NMEAVERSION V410`, y esa versión cambia tres cosas:

1. **Cada trama GSV lleva identificador de señal al final.** El mismo satélite
   aparece una vez por señal —L1 y L5 del mismo GPS son dos tramas— con C/N0
   distinto. Guardar por PRN a secas hace que una tape a la otra y la pantalla
   enseñe una relación señal-ruido que no es la que cree.
2. **Cada GSA lleva identificador de sistema**, y sin él dos GSA seguidas son
   indistinguibles: el PRN 12 de GLONASS no es el 12 de GPS. Cuando el
   identificador falta y el emisor es el genérico `GN`, **no se marca nada**:
   encender el 12 en todas las constelaciones diría que la solución usó
   satélites que no usó.
3. **C/N0 vacío no es cero.** Vacío es «a la vista y sin rastrear»; cero sería
   una señal medida de potencia nula, que no existe.

### Cómo se mantiene la tabla

Cada entrada lleva su marca de tiempo y **caduca**: diez segundos sin aparecer y
se va, cinco para la marca de «usado». La alternativa era vaciar la tabla al
empezar cada ciclo de GSV; se descartó porque un ciclo se reparte en varias
tramas y el vaciado deja la tabla a medias justo cuando alguien la lee, con el
cielo parpadeando. Con caducidad la tabla nunca está incompleta, solo un poco
vieja, **y la edad se publica** para poder decidir con ella.

Un satélite que deja de aparecer no se extrapola: se deja de decir que está.

### La respuesta

```json
{
  "satellites": [
    {"sys":"GP","prn":7,"el":67,"az":300,"cno":45,"use":true,"sig":[[1,45],[6,31]]},
    {"sys":"GL","prn":68,"el":21,"az":95,"cno":null,"use":false,"sig":[[1,null]]}
  ],
  "in_view": 28, "used": 18, "published": 28, "omitted": 0, "dropped": 0,
  "age_ms": 380,
  "fix_type": 3, "pdop": 1.8, "hdop": 0.9, "vdop": 1.5, "dop_age_ms": 420
}
```

- `sys` es el emisor de la trama —`GP`, `GL`, `GA`, `GB`, `GQ`—, no una
  deducción a partir del rango del PRN. Los rangos no coinciden entre
  fabricantes.
- **Agrupado por satélite, no por observación.** `cno` es la mejor de sus
  señales y `sig` las trae todas, `[identificador, C/N0]`. Una gráfica de barras
  que no agrupe pinta el mismo PRN dos veces.
- `el`, `az` y `cno` van **nulos** cuando no se saben. Cero es el horizonte,
  cero es el norte y cero no es una señal.
- `fix_type` y los tres DOP salen de GSA. **`pdop` y `vdop` no estaban
  disponibles antes**: GGA solo trae HDOP.
- `omitted` es cuántos satélites no se publicaron y `dropped` cuántas
  observaciones no cupieron en la tabla. Los dos deberían ser cero.

### Por qué hay un límite de cuarenta

No es de memoria, es del transporte: una respuesta por BLE se corta en 4096
bytes y devuelve `413` (`ble_transport.cpp:181`). Con cuarenta satélites y sus
señales la respuesta ronda los 2.5 KB. **Si hay que recortar se recortan los más
bajos, nunca los que entraron en la solución**: un cielo recortado al azar es
peor que uno corto, porque el operador busca justo el satélite que le falta.

Va en su propia ruta y no en `/api/status` porque son varios kilobytes que solo
hacen falta con la pantalla de satélites abierta, y el estado se consulta una vez
por segundo desde todas partes.

### El coste en la UART

La acción `telemetry` añade ahora `GPGSV COM2 1` y `GPGSA COM2 1` junto a
`GPGGA` y `GPGST`, por el mismo motivo por el que GST ya iba ahí: sin ellas la
pantalla no puede decir nada del cielo.

Van a **1 Hz aunque la posición vaya a diez**. El cielo no cambia en cien
milisegundos, y a 10 Hz cargarían el enlace de verdad. Con GGA a 10 Hz y las
otras tres a 1 Hz, la estimación con el tamaño máximo de sentencia ronda el 20 %
de los 115200 baudios. **Es una estimación, no una medida.**

### Lo que falta comprobar

Todo lo anterior está probado en el Mac con tramas construidas a mano y el
firmware compila. **No se ha comprobado contra el UM980 real**: el equipo no
estaba conectado. Queda pendiente verificar contra tramas de verdad que el
UM980 con `V410` emite el identificador de señal y el de sistema, y con qué
emisores anuncia BeiDou y QZSS.

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
