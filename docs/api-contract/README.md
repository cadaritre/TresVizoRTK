# Contrato de la API entre el firmware y las apps

`app-contract.json` es la lista de lo que las dos apps de campo —**TresVizo
Field** para iOS y su versión Android— **usan de verdad** del firmware del
MeridianV:

- cada ruta que llaman (método y ruta; por BLE son las mismas rutas dentro del
  canal de órdenes);
- cada clave que leen de la respuesta, con su tipo, si admiten `null` y si
  toleran que falte;
- cada clave que mandan en el cuerpo;
- la envoltura del canal de órdenes BLE, los paquetes binarios de solución y
  salud, el WebSocket de telemetría y la identidad dentro de la imagen firmada;
- los valores que dependen de la placa o del equipo y que ninguna app debe
  escribir a mano (`identifiers`);
- lo que no cuadra hoy entre apps y firmware (`discrepancies`).

Se sacó del **código** de las dos apps (decodificadores `Codable` y
`@Serializable`, y lecturas sueltas de JSON), no de la especificación. Lo que el
firmware manda y ninguna app lee **no está** en el contrato: eso se puede cambiar
con libertad.

## Por qué existe

En 0.8.0 el equipo cambió de placa (Tiny → Thing Plus ESP32-S3) y las apps
mandaban en `POST /api/update/begin` el `hardware_id` de la placa anterior,
escrito a mano en su código (las dos lo tenían). El firmware nuevo rechaza esa
carga («Manifiesto incompatible con este equipo») y hubo que cambiar las apps
para que lean la placa del equipo. El contrato y su prueba
están para que eso no se repita: **el firmware no puede romper una app sin que
alguien se entere antes de commitear.**

## La regla: la API solo crece

Sobre todo lo que figura en el contrato:

- **Nunca** se quita una ruta ni una clave.
- **Nunca** se renombra.
- **Nunca** se cambia su tipo (número ↔ cadena, entero ↔ decimal, objeto ↔
  arreglo…), ni se manda nula o se deja de mandar una clave marcada
  `"nullable": false` u `"optional": false`. Ojo con `integer`: un decimal donde
  las apps esperan un entero (`satellites[].el`, por ejemplo) tumba la respuesta
  entera.
- **Nunca** se cambia su significado ni su unidad aunque el tipo siga igual
  (metros que pasan a milímetros, usados que pasan a rastreados: ya pasó con el
  byte 3 de la solución en 0.7.5).
- **Nunca** se mueve un byte de los paquetes binarios ni cambia su escala, y la
  versión del paquete de salud se queda en 1 (las apps lo comparan por igualdad).

Lo que **sí** se puede:

- Añadir rutas, claves nuevas y bytes nuevos en los huecos reservados.
- Añadir valores a un enumerado **solo** si la clave tiene
  `"unknown_values_ok": true`. Con `false` (`receiver_role`, `alerts[].level`,
  `height_reference`) iOS decodifica en estricto y un valor nuevo hace fallar la
  respuesta entera: es un cambio que rompe.

Y un límite que convierte el «crecer» en romper: **por BLE ninguna respuesta
puede pasar de 4096 bytes** (el equipo contesta 413). Añadir claves a una ruta que
las apps piden por BLE —sobre todo `/api/status`— puede dejarla sin servicio por
Bluetooth aunque no se haya quitado nada. Hoy `/api/status` ya parece pasarse (ver
`discrepancies`).

Si un cambio de los prohibidos es inevitable:

1. Se actualizan **antes** las dos apps para que acepten la forma vieja y la
   nueva, y se publican.
2. Se sube la versión de la API: `api_version` en `/api/status`
   (`src/instrument.cpp`) para HTTP/USB, o `protocol_version` en
   `subsystems.ble` (`src/ble_transport.cpp`) para el canal binario de BLE.
3. Se cambia el firmware y, en el mismo commit, el contrato.

## Cómo se corre la prueba

**Antes de commitear cualquier cambio de firmware que toque una respuesta JSON,
una ruta, un cuerpo que se lee o un paquete binario:**

```sh
python3 tools/api_contract/check_contract.py          # = static
```

No necesita equipo ni dependencias (Python 3 estándar). Lee
`firmware/esp32/src`, `include` y `lib` **sin comentarios** y comprueba:

- que cada ruta sigue apareciendo en el archivo que la despacha
  (`firmware.dispatch`);
- que cada clave de respuesta se sigue **escribiendo** —`x["clave"] = …`,
  `x["clave"]["otra"] = …`, `x["clave"].to<…>()`, o en una lista
  `{"a", "clave"}` que recorre un `for`— **en la función que arma esa
  respuesta** (`firmware.writers`). Una lectura como `body["clave"]` no cuenta, y
  una clave comentada tampoco;
- que, cuando la clave se escribe con un literal (`= 3`, `= "x"`, `= true`,
  `= nullptr`), el literal es del tipo del contrato y no es nulo si las apps no lo
  admiten;
- que cada clave que mandan las apps se sigue leyendo en el manejador
  (`firmware.readers`);
- la envoltura de órdenes BLE, las respuestas de error y los códigos de error que
  distinguen las apps;
- que los UUID, longitudes, desplazamientos y versiones de los paquetes de BLE,
  del WebSocket y de la imagen firmada siguen en el código
  (`binary.firmware_evidence`).

Sale con `0` si todo cumple, `1` si algo se rompió (dice qué clave, de qué ruta,
qué app la lee y dónde se buscó) y `2` si el propio contrato está mal formado.

Es una comprobación de texto, no un compilador: ve que la clave sigue escrita en
su función, no que se escriba en todos los casos ni el tipo de una expresión. Por
eso hay un segundo modo, contra un equipo de verdad:

```sh
~/.platformio/penv/bin/python tools/api_contract/check_contract.py device --port /dev/cu.usbmodem1201
```

Pide por la consola USB (`tools/usb_console.py`; necesita `pyserial`, que trae el
Python de PlatformIO) cada ruta `GET` del contrato y valida clave por clave
presencia, tipo, nulos y valores de los enumerados estrictos. Abrir el puerto
reinicia el ESP32: antes de empezar espera a que conteste, sin cerrar el puerto. Además mide cada respuesta **como saldría por BLE**
(con la envoltura y sin contraseñas, igual que `protocol::stripSecrets`) y marca
error si pasa de 4096 bytes. No cambia nada en el equipo (solo `GET`). Conviene
correrlo tras cargar un firmware nuevo, con el receptor encendido y, si se puede,
con fix y NTRIP: algunas claves solo salen con solución vigente y es entonces
cuando se ve su tipo.

- `--record archivo.json` guarda lo que contestó, con las contraseñas
  sustituidas por `redactado`.
- `--replay archivo.json` repite la validación sin equipo.

`tools/api_contract/fixtures/device_0.8.0_from_source.json` son respuestas
**armadas a mano a partir del código** de 0.8.0, no grabadas: sirven a las pruebas
y, en cuanto haya equipo, conviene sustituirlas por unas grabadas con `--record`.

Las pruebas del propio comprobador:

```sh
python3 -m unittest discover -s tools/api_contract -v
```

## Cuando la prueba falla

- **Quitaste o renombraste algo**: no lo quites. Vuelve a escribir la clave vieja
  junto a la nueva (la API solo crece).
- **Moviste el código o cambiaste el nombre de una función**: la prueba dice qué
  fuente ya no existe. Actualiza `firmware.dispatch`, `firmware.writers` o
  `firmware.readers` de esa ruta. Es el único cambio del contrato que puede hacer
  quien toca el firmware sin hablar con las apps.
- **Una app lee algo que el firmware no manda**: va en `discrepancies`, no en las
  rutas, hasta que el firmware lo mande.

## Cuando una app empieza a leer algo nuevo

Lo actualiza **quien cambia la app**, en el mismo trabajo:

1. Añade la clave a la ruta en `app-contract.json`, con `type`, `nullable`,
   `optional` y `apps`. Si ya estaba y ahora la lee la otra app, añade la app a
   `apps`. Para que un campo cuente como `optional: true` la app tiene que seguir
   funcionando si falta; `nullable: true` si admite `null`. Si las dos apps
   difieren, manda la más estricta.
2. Si es una ruta nueva, añádela con `firmware.dispatch` (archivo donde se compara
   la ruta) y `firmware.writers` (`"archivo#función"` que escribe cada objeto; el
   prefijo más largo manda: `"subsystems.ble"` → `src/ble_transport.cpp#status`).
3. Corre `static`. Si falla porque el firmware aún no la manda, no es del
   contrato: es una petición al firmware (se anota en
   `../MeridianV-App-Spec/02-protocol/firmware-gap-analysis.md`) y, mientras
   tanto, va en `discrepancies`.
4. Commitea el contrato en este repositorio.

Y si una app **deja** de leer algo, se quita de `apps`; la clave sale del contrato
cuando ya no la lee ninguna. Solo entonces el firmware puede retirarla.

## Valores que ninguna app escribe a mano

La lista `identifiers` del contrato: `hardware_id`, `board`, `firmware_version`,
`device_name`, `ap_ssid`, `ap_ip`, el nombre mDNS y el BLE, `max_image_bytes`,
`chunk_bytes`, `chip`. Dependen de la placa, del producto o del usuario. Las apps
los **leen** del equipo —y, para cargar firmware, el `hardware_id` de la propia
imagen firmada, byte 320— y nunca los comparan con un literal. Cada entrada dice
dónde los expone el firmware y en `known_hardcodes` dónde una app todavía los lleva
fijos (por ejemplo, el SSID «MeridianV» en Android, o 1 966 080 y 576 en las dos
apps para la carga de firmware).

## Formato del contrato

- `routes[]`: `method`, `path`, `channels` (por dónde la sirve el firmware:
  `http`, `ble`, `usb`; las apps usan `http` y `ble`), `apps`, `firmware`
  (`dispatch`, `writers`, `readers`), `response[]`, `request[]` y, si hace falta,
  `request_exact_keys`, `device` y `note`.
- Cada clave de `response[]`: `path` (con puntos y `[]` para los elementos de un
  arreglo: `networks[].ssid`), `type` (`string`, `number`, `integer`, `boolean`,
  `object`, `array`), `nullable`, `optional`, `apps` y, si hace falta, `values`,
  `unknown_values_ok` y `note`. Todo contenedor de una clave declarada también va
  declarado, con su tipo.
- `request[]`: lo que mandan las apps en el cuerpo, con su tipo.
  `request_exact_keys: true` quiere decir que el firmware rechaza un cuerpo con
  claves de más: ahí las apps no pueden **añadir** nada sin tocar antes el
  firmware.
- `command_envelope`: `{id, method, path, key, body}` → `{id, status, body}`.
- `error_response`: `error` y `message` de las respuestas fuera de 2xx, y los
  códigos que las apps tratan aparte.
- `binary`: canal BLE (UUID, tramas de respuesta, paquetes de solución y salud),
  WebSocket `/ws/telemetry`, identidad de la imagen firmada y
  `firmware_evidence` (patrones que tienen que seguir en el código).
- `identifiers[]`, `discrepancies[]`.
