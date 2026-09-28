# Limitaciones conocidas y riesgos

## Tabla GATT vieja en caché del cliente (importante)

Una Mac que se conectó hace tiempo a un firmware antiguo siguió viendo, con 0.7.11 cargado,
**4 características en vez de 5** (sin la de salud `a04c0006`) y la de RTCM **sin** escritura
sin respuesta. El primer escaneo la nombró con el nombre antiguo del equipo («TresVizo-C81D»):
la Mac usa lo que guardó. Sin emparejamiento el cliente no recibe el aviso de «servicios
cambiados» (la pila solo lo manda a emparejados). **Confirmado del lado del equipo**: la
característica de salud existe (handle 52; respuestas 44, solución 47), así que lo que ve la
Mac es su copia vieja. Mandar el aviso a mano, al conectar o 1.5 s después, sale bien del equipo
(`ESP_OK`) pero macOS no redescubre; queda en el firmware **apagado por defecto**
(`-DTRESVIZO_BLE_SERVICE_CHANGED`) para probarlo con un iPhone, porque si iOS lo atiende a mitad
de sesión, una app sin `didModifyServices` se quedaría con características muertas. **Un iPhone o Android que se conectó con un firmware viejo puede estar
igual**: sin salud y sin RTCM sin respuesta, aunque el equipo los tenga.

- Mitigado en las apps: la salud no se exige para estar lista; el modo de escritura del RTCM
  sale de las propiedades descubiertas; iOS atiende `didModifyServices`; Android usa
  `BluetoothGatt.refresh()` si faltan características.
- Para confirmarlo mañana: un teléfono que **nunca** se haya conectado al equipo (o nRF Connect
  recién instalado) debe ver 5 características y `a04c0005` con `write` + `write no response`.
- **Prueba hecha**: con el equipo anunciándose, solo para la prueba, con otra dirección (aleatoria
  estática), la misma Mac vio al instante las 5 características y la escritura sin respuesta.
  Una dirección nueva y fija (derivada de la MAC) arreglaría las tablas viejas de todos los
  clientes de una vez, a cambio de que cada app vuelva a elegir el equipo una vez (el
  identificador que guardan iOS y Android cambia). **Lo decide el propietario.**
- Arreglo de fondo, pendiente: «servicios cambiados» enviado **después** de que el cliente
  active su indicación, o caché robusta (Database Hash, ESP-IDF `BT_GATTS_ROBUST_CACHING`), que
  el Arduino precompilado no trae activada.

## Seguridad (sin cambios, decisión del propietario desde 0.6.2)

- **Cualquiera al alcance puede conectarse** y escribir órdenes y correcciones: no hay
  emparejamiento, PIN ni cifrado. Las órdenes incluyen `POST /api/restart` y cambiar de modo.
- Mitigaciones vigentes: un solo cliente a la vez (el equipo deja de anunciarse mientras hay
  uno conectado); el transporte se apaga desde Conexiones y se persiste; el RTCM por BLE se
  ignora en modo base; la carga de firmware, la lectura de grabaciones y las credenciales no van
  por BLE.
- Riesgo real en obra: alguien cerca con una app genérica puede reiniciar el equipo o mandarle
  correcciones basura (el CRC las filtra si están mal formadas, no si son de otra base).
- Endurecimiento posible sin fricción: exigir que la primera orden de una conexión venga de una
  app que se identifique (no es seguridad fuerte), o volver al emparejamiento «Just Works» con
  cifrado para cortar la escucha pasiva. Lo decide el propietario.

## Rendimiento y memoria

- **RTCM con respuesta** (clientes con tabla vieja o firmware ≤ 0.7.10) topa en ≈2.8 kB/s a
  30 ms de intervalo. Un caster MSM7 de cuatro constelaciones no cabe; MSM4 va justo.
- **UART al UM980 a 115200** (≈11.5 kB/s) compartida por RTCM y órdenes. Suficiente para RTCM a
  1 Hz; subir la velocidad exige verificar la configuración del puerto del UM980 y el cableado
  (AGENTS.md: manuales antes que suposiciones).
- La biblioteca BLE de Arduino arma un volcado hexadecimal con `malloc`/`free` **en cada
  escritura** aunque los registros estén apagados (`BLECharacteristic.cpp`, `buildHexData`), y
  copia cada valor a un `std::string`. Con RTCM sin respuesta son decenas de reservas por
  segundo: vigilar `min_free_heap_bytes` en sesiones largas.
- 0.7.11 bajó el heap interno libre de ~106 KB a ~97 KB tras arrancar (cola estática de 8 KiB).
  Hay 2 MB de PSRAM libres: la cola puede ir ahí si hace falta.

## Menores, vistos al escribir el decodificador del banco

- `Rtcm3Parser::overflow` (`lib/gnss/src/rtcm3.h:25`) no sube nunca: el contador existe pero
  siempre vale 0.
- Una petición BLE con JSON inválido recibe `400 invalid_request` **sin `id`**: el cliente no la
  puede asociar a su orden y la da por vencida al agotar el plazo. Solo pasa con una trama
  corrupta; las apps no mandan JSON inválido.

## Sin validar todavía

RTCM **sin** respuesta de punta a punta (ningún cliente de hoy tenía la tabla al día), sesión
larga, coexistencia Wi-Fi/BLE con NTRIP del equipo activo, Android, segundo plano en iOS,
reconexiones reales fuera de alcance, y todo lo que necesita fix (bajo techo no hubo).
