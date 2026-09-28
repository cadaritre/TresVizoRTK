# Android: varios receptores sin que uno contamine al otro

Dos partes: la genérica (receptores de otras marcas y GPS del teléfono) y el Meridian V por BLE.
Estado al 27-09-2026 por la noche. Integrado en `los-residentes`, compila y sus pruebas pasan
(ver FINAL_REPORT.md); nada se ha probado con un receptor real ni en un teléfono.

## 1. La regla

**El Meridian V es una sesión; lo demás son fuentes de posición.** Un receptor de otra marca o el
GPS del teléfono no tienen estado, configuración, base, operaciones ni contadores que leer; darles
un `DeviceSession` sería prometer lo que no pueden cumplir (ADR-A039). Por eso:

- Nada del Meridian vive en `core/domain/.../generic/`, `core/bluetooth/.../spp/` ni
  `app/.../receivers/`.
- Nada genérico vive en `core/bluetooth/gatt`, `BleReceiverTransport.kt`, `core/domain/.../ble`,
  `TransportRouter.kt` ni el servicio de sesión.
- Lo que comparten es **el modelo de posición** (`SolutionPacket`, `HealthPacket`,
  `DeviceStatus.SolutionStatus`, cada uno con su `AgedValue` y su escala de frescura, ADR-A042), la
  **puerta de calidad** (sin excepciones) y **el sumidero de correcciones**.

## 2. Parte genérica

```
 Equipo (pie de la lista)                         Captura (SessionCaptureSources)
 ├─ receptor NMEA en uso + correcciones           1. sesión del Meridian (si hay)
 ├─ receptores guardados                          2. receptor NMEA conectado
 ├─ «Conectar receptor NMEA» ──► asistente        3. GPS del teléfono (si el modo está puesto)
 └─ «Usar el GPS del teléfono» ──► aviso SIEMPRE

 asistente: dispositivo ─► NmeaStreamCheck ─► marca/modelo ─► desfase ─► SavedReceiver (JSON)

 enlace:   RFCOMM (SPP)  ┐
                         ├─ SerialPort ─► SppReceiverLink ─► GenericNmeaReceiver ─► snapshot
           USB CDC-ACM   ┘                     ▲
                                               │ tramas RTCM enteras (GenericCorrectionSink)
 NTRIP del teléfono ─► GenericCorrectionBridge ┘   ◄── GGA propio del receptor, sin caducar
```

- **Enlace único para las dos radios.** `SerialPort` (entrada, salida, cerrar) lo implementan el
  socket RFCOMM (`AndroidSpp`) y el puerto USB CDC-ACM (`app/.../receivers/UsbCdcAcm.kt`, con
  `UsbManager`, sin biblioteca). `SppReceiverLink` lee y escribe igual los dos; solo cambian sus
  frases («Bluetooth» / «cable USB»).
- **¿Es un GPS?** `NmeaStreamCheck`: frases con suma de comprobación válida, de tipos GNSS, y dos
  GGA en 8 s (de GGA salen posición, calidad y altura; con RMC o GNS solos se pide activar GGA); si no, el motivo en palabras que se pueden seguir.
- **Receptor guardado.** `SavedReceiver` en `filesDir/receivers/saved_receivers.json`, escrito
  entero (`AtomicFile`). El respaldo ZIP lo lleva tal cual (`exportSection` /
  `importSection`, mezcla por `id`).
- **Desfase de antena.** Vertical, del ARP al centro de fase L1; del catálogo (NGS o fabricante,
  con su fuente) o tecleado. Se suma al bastón en **la misma función** que la caja del Meridian
  (`AntennaHeights.mountOffsetMeters`): la captura y la cota en vivo del panel.
- **Origen del punto.** `PointOrigin.NMEA_RECEIVER` y `PointOrigin.PHONE_GPS`, ninguno se desplaza
  por base; la calidad es la que dijo la fuente, nunca subida.
- **Correcciones.** El NTRIP no sabe qué receptor es: escribe en el sumidero del receptor activo.
  «Enviadas», nunca «aceptadas»: la prueba es que su GGA pase a 4 o 5.
- **GPS del teléfono.** Autónomo, sin satélites, el radio que declara el sistema (ni sigma ni
  porcentaje), altura elipsoidal (`Location.getAltitude()`). Aviso del propietario **cada vez** que
  se conecta, desde Equipo o Cuenta; no se reanuda solo al abrir la app.

## 3. Interfaz común de correcciones

Una sola interfaz, en `core/domain/.../corrections/CorrectionSink.kt`:

```kotlin
fun interface CorrectionSink { suspend fun write(frame: Rtcm3Frame) }
```

y el genérico es `fun interface GenericCorrectionSink : CorrectionSink` (hecho al integrar): el
NTRIP del teléfono escribe en el sumidero del receptor activo sin saber cuál es.

## 4. Parte del Meridian V por BLE

```
 SessionSupervisor ─(escalera 1-2-4-8-16-30 s)─► DeviceSession ──► TransportRouter ──► BleReceiverTransport
        ▲                                            │  (elige BLE/Wi-Fi por capacidad)   │  LinkPhase + LinkStateMachine
        │ connectionState                            │                                    │  ProtocolLiveness (latido v3)
        └────────────────────────────────────────────┘                                    │  LaneGate: órdenes primero
                                                                                          ▼
 NTRIP del teléfono ─► CorrectionBridge ─► CorrectionBridgeController ─► CorrectionSink ─► writeCorrections ─► A04C0005
   (bytes, no sabe      (CRC, tramas enteras,   (fuente «ble» elegida,     (DeviceSession.
    qué receptor es)     8 KiB, edad 2 s)        3 contadores del equipo)   writeCorrections)
```

- **Todo lo específico del Meridian está en su adaptador**: UUIDs, tramas, MTU, CCCD y la
  política de escritura en `core/domain/ble/*` y `core/bluetooth/{gatt,scan}/*` +
  `BleReceiverTransport.kt`; el protocolo JSON (`request(method, path, body)`), las capacidades
  por transporte y el reensamblado en el mismo sitio; la sesión con estado, configuración,
  operaciones y base en `DeviceSession`. Ninguna pantalla pregunta por el transporte ni por el
  nombre: preguntan por capacidad (`TransportRouter.can`). Búsqueda en todo `android/`: ningún
  `name.contains("Meridian")` (27-09-2026).
- **Reglas de reconexión del Meridian** (no se comparten con los genéricos): la escalera del
  supervisor y «reconectar es recargar» (`handshake` relee estado, configuración, perfil y
  operaciones; la generación sube y lo viejo se tira). La vida del protocolo (`ProtocolLiveness`)
  y el latido de salud a 1 Hz son del contrato BLE del Meridian v3; un genérico no tiene nada
  parecido que pedir.
- **Correcciones**: el puente del Meridian comparte con el genérico `CorrectionBridge` (CRC24Q,
  tramas enteras, cola de 8 KiB por bytes, edad 2 s al enviar, sin historia, cuentas que cuadran:
  `Statistics.balances`) y el cliente NTRIP; lo propio del Meridian es elegir la fuente `ble` en el
  equipo antes de puentear, pararse si pasa a base o si otro cambia la fuente, y el diagnóstico de
  tres contadores con `/api/status`. Escribe por `CorrectionSink`, que por defecto es
  `DeviceSession.writeCorrections` (y en pruebas, un enlace que falla a la mitad).
- **Receptor activo**: hoy la sesión del Meridian y el receptor NMEA viven cada uno en su sitio
  (servicio en primer plano el primero, proceso de la app el segundo), y la captura los ordena en
  `SessionCaptureSources` (§2). No hay una interfaz `ReceiverConnection` común, a propósito: lo
  único que de verdad comparten es la posición envejecida y el sumidero de correcciones.
- **IMU futura**: el paquete de salud reserva el byte 9 y el protocolo sube de versión de forma
  aditiva (v3 añadió latido y bytes 17–19 detrás de una bandera). Una fuente de orientación sería
  otra característica o otro tipo de mensaje del mismo adaptador, con su propio `AgedValue`, sin
  tocar `LaneGate` (es tráfico de entrada, no ocupa el carril de escritura) ni las pantallas que
  no la pidan.

## 5. Lo que falta (genérico)

(Hecho después: la barra de estado, el replanteo con un genérico o el teléfono, y la reconexión sola de un enlace Bluetooth con la escalera 1–30 s del Meridian; un cable USB desenchufado espera a «Reconectar».)


- Cables USB–RS-232 de fabricante (FTDI, PL2303, CP210x, CH34x): Q-81.
- (Hecho: `OtherReceiverService`, servicio en primer plano propio, mantiene vivo el receptor genérico y su puente con la pantalla apagada; el del Meridian no se toca.)

## 6. Qué probar con equipo (parte genérica)

Nada de esto se probó con un receptor real ni en un teléfono; la app se compiló y sus pruebas
de JVM pasan.

1. **Emlid Reach por Bluetooth.** Emparejar el Reach en Ajustes de Android. Equipo → «Conectar
   receptor NMEA» → el Reach en «Bluetooth emparejados». Debe confirmar «Es un GPS: llegan GGA…»
   en 1–3 s (con la salida NMEA del Reach activa por Bluetooth). Probar también con la salida NMEA
   apagada: debe decir que no llega nada o que falta GGA, y no seguir.
2. **Marca y modelo, y desfase.** Elegir «Reach RS2+» → propone 0.1349 m con la fuente de Emlid;
   guardar. Elegir «Otro / nuevo» → pide marca, modelo y el desfase tecleado (0–30 cm).
3. **Datos.** En Equipo: calidad «RTK fijo · GGA 4» (o la que dé), satélites, HDOP, σ solo si el
   Reach manda GST; la barra de estado con «⌁ BT serie». Apagar el Reach: la posición envejece y
   se apaga a los pocos segundos; volver a encender: se reconecta solo.
4. **Correcciones.** Con un caster guardado en Correcciones: «Enviar correcciones» → «Tramas
   enviadas» sube y el pie pasa a «El receptor dice RTK fijo en su GGA» cuando fije. Con un punto
   de montaje VRS, comprobar que el caster recibe el GGA del Reach.
5. **La cota (la prueba que importa, Q-80).** Mismo punto, bastón conocido: comparar la cota del
   suelo de la app con la de Emlid Flow, **con la altura de antena de Flow en 0** y sin ella. Con
   un Trimble, lo mismo contra Trimble Access (la app usa 128.4 mm de NGS, Trimble dice 149.1).
6. **Cable USB.** Un receptor con USB CDC propio (u-blox, placa Unicore) por OTG: aparece en
   «Puertos serie USB», pide permiso, se elige la velocidad y confirma. Un cable FTDI/CH340 **no**
   aparece (Q-81).
7. **GPS del teléfono.** «Usar el GPS del teléfono» → el aviso **cada vez**; aceptado, «GPS del
   teléfono en uso», «Autónomo · radio declarado N m», la barra con «⌖ teléfono» y AUTÓNOMO; un
   punto se guarda como «GPS del teléfono» en la exportación y no se mueve con un desfase de base.
   Conectar un Meridian: el modo se apaga solo.
8. **Pantalla apagada.** Con el puente hacia un genérico en marcha, apagar la pantalla unos
   minutos: debe seguir la notificación «Emlid Reach RS2+ · RTK fijo · GGA 4 · correcciones del
   teléfono en marcha» y el receptor seguir fijo. «Desconectar» en la notificación lo suelta.
