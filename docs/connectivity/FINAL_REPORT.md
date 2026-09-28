# Informe final — endurecimiento del Bluetooth del Meridian V (27-09-2026)

Rama `los-residentes` en los tres repositorios. Trabajo de una noche: auditoría del código real,
medidas en el equipo real (por USB en la Mac, bajo techo, sin fix) con la Mac como central BLE,
cambios en el firmware y en las dos apps, y pruebas. **Lo que no se probó se dice.**

## 1. Qué era inestable

La conexión funcionaba, pero con correcciones en marcha las órdenes se atrasaban, la app podía
parecer colgada y las correcciones podían envejecer sin que nadie lo viera. Sin fix, además, el
equipo no mandaba ni la edad de las correcciones.

## 2. Causas confirmadas

| # | Causa | Evidencia |
| --- | --- | --- |
| C1 | **El RTCM iba por escritura con respuesta**, que en ATT admite una sola escritura en vuelo por enlace: RTCM y órdenes compartían un carril. La respuesta ATT la manda la biblioteca antes de `onWrite`: no confirmaba nada | `ble_transport.cpp` 0.7.10 (`PROPERTY_WRITE`), `BLECharacteristic.cpp:303-322` de Arduino. **Medido: tope de ≈2.8 kB/s**; órdenes de 75–93 ms a 90–153 ms |
| C2 | **iOS entregaba todo el RTCM a CoreBluetooth sin esperar confirmación**: la cola real era la interna de CoreBluetooth, sin límite, y las órdenes esperaban detrás. Con un caster por encima de 2.8 kB/s (MSM7) el atraso crece sin fin | Auditoría iOS: `BLETransport.swift:333-348` (D1). Unido a C1 es la explicación de la inestabilidad con RTCM + órdenes |
| C3 | **Cola hacia el UM980 de 4 tramas** con UART a 115200: una época MSM de 6–10 tramas que llega de golpe perdía tramas en cada época | `gnss_receiver.cpp` 0.7.10; `adbf364` de Android ya había visto lo mismo en el teléfono (se perdía la 1006) |
| C4 | **La salud solo salía detrás de una solución nueva**: sin fix o sin hora UTC, ni edad de correcciones ni señal de vida | `ble_transport.cpp:233` 0.7.10 |
| C5 | **Tabla GATT vieja en caché del cliente**: un cliente que se conectó a un firmware viejo no ve lo nuevo (ni la salud ni la escritura sin respuesta), porque sin emparejamiento no le llega «servicios cambiados» | Mac: 4 de 5 características; el equipo sí las tiene (handle 52). Con una dirección nueva, la misma Mac vio las 5 al instante |

## 3. Sospechas no confirmadas (o descartadas)

- **Coexistencia Wi-Fi/BLE: descartada con la medida de hoy.** Con escaneos Wi-Fi cada 30 s,
  220 órdenes en 70 s: mediana 40 ms, máximo 126 ms, sin picos periódicos. Falta medirla con el
  NTRIP del equipo activo por Wi-Fi.
- Fragmentación de respuestas: estaba bien (offset, huecos, generación). Se dejó igual.
- Tareas del ESP32: el bucle nunca pasó de 7 ms entre pasadas en ninguna prueba; la microSD no
  bloquea (búfer sin espera); los trabajos del UM980 son asíncronos.
- Memoria: la biblioteca BLE de Arduino reserva y libera en cada escritura; el heap mínimo bajó a
  84.9 KB tras ~800 KB de RTCM. No es un fallo hoy; hay que mirarlo en una sesión larga.

## 4. Cambios en el firmware (0.7.11)

- `a04c0005` admite escritura **sin respuesta** (aditivo).
- Cola hacia el UM980 **por bytes (8 KiB)**, solo tramas enteras, las más viejas fuera, 2 s de
  caducidad, trama empezada se termina (`lib/protocol/src/rtcm_queue.h`, con pruebas).
- Salud a **1 Hz siempre** = latido; bytes 17–19 con contadores de RTCM.
- Telemetría solo con hueco en la controladora y detrás de las respuestas; lo saltado se cuenta.
- Conexión pedida de 15–30 ms; métricas nuevas en `/api/ble` y `subsystems.gnss`.
- «Servicios cambiados» tras conectar, **apagado** por defecto (bandera de compilación).

Commits en `los-residentes` del firmware: `3adf6c4` (cambios), `f19722f` (aviso tras bandera),
documentos `9d5594e`, `2408a85`, `6c51b6c`, `b930f6b`, README `e34114e`, banco Mac `df33400`, y
el banco en Python (`tools/ble_bench/`, siete commits hasta `b8201e5`).

## 4 bis. Cambios en las apps

**iOS** (rama `los-residentes`, compila; núcleo 733 pruebas en verde, 1 omitida). Detalle en
[IOS_BLE_ARCHITECTURE.md](IOS_BLE_ARCHITECTURE.md) §8.
- Máquina del enlace pura en el núcleo (`BLELinkMachine`: fases, transiciones legales, plazos con
  nombre, número de intento en cada plazo), causa de cada corte y descarte de avisos tardíos de
  una conexión anterior.
- RTCM trozo a trozo esperando a la pila (una escritura en vuelo), sin respuesta si la
  característica lo anuncia; las órdenes pasan antes; cola del teléfono por bytes (8 KiB) y edad;
  contadores del puente que cuadran.
- Latido con la salud v3 y una sola orden de comprobación antes de soltar un enlace mudo; no se
  exige la característica de salud; `didModifyServices` redescubre sin duplicar.
- Diagnóstico: sección «Enlace visto desde el teléfono» en Equipo › Bluetooth y aviso «Tabla
  Bluetooth desactualizada».
- Tirones: barra de estado, Equipo, Estado, Correcciones, Puente e importación de dibujos leen la
  posición en vistas hijas. Medido en el simulador (redibujos en 4 s con la pantalla quieta):
  Equipo 21 → 2, Estado 29 → 0, Correcciones 24 → 2.

**Android** (rama `los-residentes`: compila, 1 764 pruebas en verde, APK de depuración). Detalle en
[ANDROID_BLE_ARCHITECTURE.md](ANDROID_BLE_ARCHITECTURE.md).
- La auditoría encontró bien lo esencial (operaciones GATT en serie, `close()` en cada salida,
  callbacks de otra conexión descartados). Se añadieron: fases y causas con los mismos nombres
  que iOS, vida del protocolo, carril con las órdenes primero, RTCM sin respuesta donde se
  declara, cola por bytes, `bluetoothOff`, tres operaciones rechazadas seguidas ⇒ enlace perdido.
- Multimarca intacta: el Meridian no sale de su adaptador; `CorrectionSink` común para el
  Meridian y para cualquier receptor genérico.
- Tirones de Compose: el estado rápido se lee donde se pinta.
- Las pruebas rotas desde `a9259a6` (desfase de base) se pasaron a la API nueva: el dominio vuelve
  a compilar sus pruebas y queda en verde; el modo LEGACY de SQLite no corre en Apple Silicon.

## 4 ter. Lo demás que pidió el propietario esta noche

- **GPS del teléfono** en las dos apps: el aviso de errores altísimos **cada vez** que se
  conecta, calidad autónoma, altura elipsoidal, radio declarado sin porcentaje, y un origen
  propio (`phone_gps`) que ningún desfase de base mueve y que manda sobre la procedencia de una
  línea en el replanteo.
- **Receptores de otras marcas en Android**: «Conectar receptor NMEA» al pie de Equipo
  (Bluetooth SPP o USB CDC-ACM), comprobación de que es un GPS, marca y modelo con «Otro / nuevo»,
  desfase de antena (47 modelos, 38 con valor L1 de las calibraciones de NGS y su fuente; el resto
  lo teclea el usuario), receptor guardado, puente NTRIP del teléfono y servicio en primer plano.
- **Respaldo en ZIP** desde Cuenta en las dos apps, el mismo formato (`docs/BACKUP_ZIP_FORMAT.md`):
  preferencias, receptores, casters sin contraseñas, códigos y, si se pide, proyectos como `.mvz`
  comprobados pero **no restaurados**. Fuera iCloud y la copia en la cuenta de Google.
- **Paridad iOS ↔ Android**: inventario de ~290 diferencias con archivo y línea de los dos lados
  (`docs/UI_PARITY.md` de Android) y las que no tenían motivo, arregladas en Android.

## 5. Cambios de protocolo

Contrato v3, todo aditivo: [BLE_CONTRACT.md](BLE_CONTRACT.md). Compatibilidad en
[PROTOCOL_VERSIONING.md](PROTOCOL_VERSIONING.md).

## 6. RTCM antes y después (medido en el equipo real)

| | Antes (con respuesta) | Después (sin respuesta, 0.7.11) |
| --- | --- | --- |
| Caudal máximo por BLE | ≈2.8 kB/s | **24.3 kB/s**, 0 pérdidas, 0 CRC |
| Caster MSM7 pesado (5 kB/época) | No cabe: el atraso crece 2.2 kB cada segundo | 160/160 tramas, sin atraso |
| Órdenes durante el RTCM | 90–153 ms (una escritura en vuelo; con la app iOS vieja, sin límite) | mediana 67 ms, p90 126 ms, máx. 221 ms |
| Cola hacia el UM980 | 4 tramas: se perdían tramas por época | 8 KiB por bytes, descartes contados |
| Visibilidad | contadores solo por `/api/status` | salud a 1 Hz con descartes y ocupación |

## 7–9. Colas, estado de la conexión y reconexión

[BACKPRESSURE.md](BACKPRESSURE.md), [CONNECTION_STATE_MACHINE.md](CONNECTION_STATE_MACHINE.md),
[IOS_BLE_ARCHITECTURE.md](IOS_BLE_ARCHITECTURE.md), [ANDROID_BLE_ARCHITECTURE.md](ANDROID_BLE_ARCHITECTURE.md).

## 10. Pruebas

[ACCEPTANCE_TESTS.md](ACCEPTANCE_TESTS.md) (resultados) y
[ACCEPTANCE_PROCEDURES.md](ACCEPTANCE_PROCEDURES.md) (cómo correr cada una). Firmware: 12 pruebas
C++ en verde. Banco en Python: 81 pruebas en verde.

## 11. IMU

[IMU_READINESS.md](IMU_READINESS.md): la IMU entra como otra tarea con su instantánea, otro
mensaje (`a04c0007`) por el mismo publicador que ya respeta hueco y prioridad, y otro
decodificador en las apps. Nada del transporte cambia.

## 12. Riesgos que quedan

[KNOWN_LIMITATIONS.md](KNOWN_LIMITATIONS.md): tablas GATT viejas en teléfonos (decisión: dirección
nueva o «servicios cambiados» probado con iPhone), sin emparejamiento (decisión del
propietario), UART a 115200, heap en sesiones largas, y todo lo que necesita fix y campo.

## 13. Ramas, commits y archivos

Todo en la rama **`los-residentes`** de cada repositorio, integrado commit a commit (sin
reescribir nada) desde las ramas de trabajo `los-residentes-*`, que se conservan.

| Repositorio | Desde | Commits | Archivos |
| --- | --- | --- | --- |
| Firmware (`TresVizoRTK`) | `f982382` (0.7.10) | 26 | 61 (firmware, pruebas C++, `docs/connectivity/`, `tools/ble_bench/`, `tools/ble_bench_mac/`) |
| iOS (`TresVizoField`) | `f57f17f` | 27 | 56 (núcleo BLE, transporte, GPS del teléfono, respaldo ZIP, pantallas sin tirones, documentos) |
| Android (`TresVizoFieldAndroid`) | `ec8b6a4` | 81 | 180 (transporte BLE, receptores de otras marcas, GPS del teléfono, respaldo ZIP, paridad, pruebas del desfase de base, documentos) |

Estado al cerrar: firmware con 12 pruebas C++ y 85 del banco en Python en verde, compilado y
**cargado en el equipo**; iOS compila y 734 pruebas del núcleo en verde; Android compila,
1 764 pruebas en verde y APK de depuración. Nada se ha probado en un teléfono ni con fix.

## 14. Decisiones que quedan para el propietario

1. **Tablas GATT viejas en los teléfonos**: dirección Bluetooth nueva y fija (cada app vuelve a
   elegir el equipo una vez) o probar «servicios cambiados» con un iPhone (bandera de firmware).
2. **Emparejamiento**: sigue sin él (decisión de 0.6.2); riesgo en KNOWN_LIMITATIONS.md.
3. **Proyectos en el ZIP**: se exportan y se comprueban, pero no se restauran (ADR-0008 de
   iOS). Sin iCloud ni Drive, los proyectos ya no se respaldan solos.
4. **Cables USB–serie de fabricante** (FTDI, PL2303, CP210x, CH340) en Android: biblioteca
   usb-serial-for-android o no (Q-81).
5. **Desfase de antena Trimble**: la app usa L1 de NGS (128.4 mm), el fabricante dice 149.1 mm
   a un «centro de fase nominal» (ADR-A123, Q-80).
6. **GPS del teléfono también en Cuenta** (solo Android): quitarlo o dejarlo.
7. **UART al UM980 a más de 115200**.
8. **No dar 0.7.11 a quien use una app de `main`**: enseña un aviso rojo de versión que es falso.
