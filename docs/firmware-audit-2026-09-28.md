# Auditoría del firmware 0.7.12 — 28 de septiembre de 2026

Código revisado: `179b3f6d506c42429f71af1b4ce7326fa5e71fc7`. Perfil `esp32s3_usb`, Arduino-ESP32 2.0.17 y ArduinoJson 7.4.2. El árbol estaba limpio al comenzar.

**Resultado:** se identificaron siete defectos de prioridad alta (P1), dos de prioridad media (P2) y una decisión de producto que altera la precisión mostrada. Se reprodujeron localmente la pérdida de bytes RTCM, la aplicación de un promedio después de perder FIX, la suma de altura adicional y la publicación de salud con datos vencidos. No se modificó el firmware ni se cargó ninguna imagen al equipo.

La revisión abarcó los servicios C++ propios, parsers y colas, configuración de compilación y las rutas del panel relacionadas con los hallazgos. No demuestra ausencia de otros defectos ni certifica precisión topográfica. No incluyó ejecución física, pruebas eléctricas, sesiones prolongadas ni una auditoría completa de dependencias o de las apps móviles.

P1 significa corregir antes de depender de la función afectada en campo. P2 significa corregir en la siguiente iteración. La severidad describe el impacto potencial; no afirma que todos los problemas hayan sucedido ya en el equipo real.

## F01 — P1: el filtro de binario corrompe las correcciones RTCM de salida

**Ubicación:** `firmware/esp32/src/gnss_receiver.cpp:90–99` y `firmware/esp32/lib/gnss/src/wire_filter.h:14–16`.

El parser de RTCM que alimenta al caster y al publicador recibe los bytes que salen de `WireFilter`. Este filtro retiene cualquier `0xAA` buscando una cabecera Unicore. Si el siguiente byte no coincide, descarta el prefijo retenido en vez de entregarlo al consumidor. `0xAA` puede aparecer legítimamente dentro de una trama RTCM; el filtro no conoce sus límites.

**Reproducción:** una trama de diez bytes con cabecera RTCM, carga `3e d0 aa 00` y CRC24Q calculado pasa directamente por `Rtcm3Parser` como una trama válida. Al encadenar los dos componentes exactamente como lo hace la adquisición, quedan nueve bytes y el parser no entrega ninguna trama. Se usaron las cabeceras reales del repositorio. El contenido es sintético: verifica transporte y CRC, no una observación GNSS física.

**Impacto:** pérdida dependiente del contenido de las correcciones producidas por la base, aunque la UART entregue bien los bytes. Afecta al caster local y a la publicación; esta ruta no es la entrada BLE/NTRIP hacia el UM980.

**Corrección propuesta:** demultiplexar RTCM, binario Unicore y texto respetando los límites de cada trama. No pasar RTCM por un filtro de texto. Verificar cargas con `0xAA`, prefijos parciales y mezcla de formatos.

## F02 — P1: se vuelve a sumar la altura de antena a una coordenada tomada del receptor

**Ubicación:** `firmware/esp32/src/base_survey.cpp:95–99,131–134`; `firmware/esp32/web/device.js:229–234`; `firmware/esp32/src/instrument.cpp:991–999`.

El promedio usa alturas GNSS del propio receptor y luego añade `antennaVertical + 0.10`. No hay una resta previa que lleve esas alturas al punto del suelo. Con el desplazamiento de antena del receptor configurado en cero por `receiver_baseline.h`, esa coordenada ya corresponde a la antena, no al terreno. La ruta «usar la actual» copia igualmente la altura del receptor a un campo que la API interpreta como altura del suelo y vuelve a elevarla.

**Reproducción:** con altura GNSS de 100.000 m, ondulación cero y antena introducida de 2.000 m, el código real de `base_survey.cpp` entregó a `applyBase` **102.100 m**. No se trata de una conversión geoidal: el desplazamiento adicional es la altura introducida más el case.

**Impacto:** sesgo vertical sistemático en la coordenada declarada a la base, potencialmente propagado a los rovers. Una solución FIX no corrige una coordenada de base mal declarada.

**Corrección propuesta:** distinguir coordenada conocida del terreno y coordenada observada en la antena. Aplicar la transformación de altura una sola vez. Medir y definir la referencia mecánica del case; `0.10` está expresamente declarado como no medido y además está duplicado en dos archivos.

## F03 — P1: un promedio que exige FIX puede aplicarse después de perder la posición

**Ubicación:** `firmware/esp32/src/base_survey.cpp:89–123`.

Una época GGA con calidad cero actualiza `lastEpoch`, pero sale por `!s.has_position` antes de comprobar y cancelar la pérdida de calidad. En la siguiente pasada, la época repetida permite terminar el promedio por tiempo con las muestras antiguas. No se exige que la muestra final siga cumpliendo la calidad ni que se haya cubierto el intervalo solicitado con muestras válidas.

**Reproducción con el archivo C++ real y sustitutos de reloj/receptor:** iniciar dos segundos exigiendo `rtk_fixed`; aceptar una época FIX; recibir GGA de calidad cero al segundo; ejecutar otra pasada al cumplirse los dos segundos. Resultado: **`state=applying`, `samples=1`**, y se llamó a `applyBase`. Lo esperado era cancelar.

**Impacto:** el operador cree haber promediado bajo la calidad exigida durante el plazo elegido, pero se instala una coordenada basada en una muestra anterior a la pérdida de solución.

**Corrección propuesta:** evaluar pérdida de posición/calidad antes del retorno temprano y validar continuidad, frescura y duración efectiva antes de aplicar el promedio.

## F04 — P1: la salud BLE sigue afirmando FIX y precisión con muestras vencidas

**Ubicación:** `firmware/esp32/include/health_report.h:18–32`; `firmware/esp32/src/ble_transport.cpp:236–249`.

`health_report::build` usa `precision_accepted` como si implicara frescura y copia la calidad de la última solución sin comprobar `arrival_us`. BLE manda salud cada segundo incluso cuando ya no llegan posiciones. La ruta HTTP sí caduca la solución a 500 ms y GST a dos segundos (`instrument.cpp:753,775`), por lo que las interfaces pueden contradecirse.

**Reproducción:** a tiempo local 60 s se suministró un snapshot con GGA/GST recibidos a 0.001 s. La función real produjo **calidad 4 (FIX), horizontal mostrada 10 mm y vertical mostrada 15 mm**, conservando también las sigmas crudas antiguas. No incorpora una marca que diga que esa solución y esas precisiones vencieron.

**Impacto:** una conexión BLE viva puede parecer un instrumento que sigue midiendo con la calidad anterior, aunque el GNSS haya dejado de entregar datos. La app podría protegerse con su propio temporizador de posiciones, pero el paquete del firmware sigue siendo engañoso y las apps no fueron auditadas aquí.

**Corrección propuesta:** mantener el latido, pero invalidar por separado calidad y precisión cuando venza cada medición; compartir las reglas de frescura con HTTP.

## F05 — P1: «Usar como rover» deja de entregar posiciones al panel

**Ubicación:** `firmware/esp32/src/gnss_control.cpp:491,545–547`; `firmware/esp32/web/device.js:340–342`.

La acción `rover` envía `UNLOG COM2`, cambia de modo, configura la altura, consulta MODE y guarda. No vuelve a habilitar GGA, GST, GSV ni GSA. El comentario presupone que todos los clientes mandan después `telemetry`, pero los dos botones del panel que cambian a rover solo mandan `rover` (`device.js:12,342`).

**Impacto:** al usar el panel para volver de base a rover, COM2 se queda sin las salidas que necesita el ESP32. El panel acabará mostrando datos vencidos o ausencia de datos; `SAVECONFIG` conserva la situación después de apagar. Se recupera al aplicar explícitamente un perfil de telemetría.

**Corrección propuesta:** restaurar las salidas necesarias dentro de la operación rover, antes de guardar, o hacer que todos los clientes ejecuten y esperen la secuencia completa. Preferible que la operación del firmware sea autosuficiente.

La semántica de `UNLOG` sin mensaje está documentada en el [manual oficial N4, sección 8.1](https://ko.unicore.com/uploads/file/unicore-reference-commands-manual-for-n4-high-precision-products-v2-en-r1.2.pdf). Se verificó la ruta estáticamente; no se enviaron comandos a un receptor físico.

## F06 — P1: aplicar una base no la guarda, aunque el estado puede decir que sí

**Ubicación:** `firmware/esp32/src/gnss_control.cpp:189–193,555–570`.

`applyBase` construye `CONFIG UNDULATION`, `MODE BASE ...` y `MODE`. Esa función no pasa por el bloque de `start` que añade `SAVECONFIG`. Sin embargo, `commitProfile` marca `profileState.saved=true` para `action=="base"` al completar el trabajo.

**Impacto:** un cambio de coordenada de base puede parecer persistido sin haberse enviado la orden de guardado. Si no hay después otra operación que guarde, al reiniciar el UM980 puede volver a su configuración anterior. El publicador/caster del ESP32 sí persiste su activación, lo que agrava la discrepancia.

**Corrección propuesta:** guardar explícitamente al final de `applyBase` y asociar `saved` al ACK de ese guardado, o informar correctamente que la base es temporal. La lectura posterior de MODE tampoco verifica por sí sola la coordenada ni su persistencia.

Unicore incluye `saveconfig` en la [secuencia oficial de configuración de base N4](https://en.unicorecomm.com/uploads/file/Unicore%20Reference%20Commands%20Manual%20For%20N4%20High%20Precision%20Products_V2_EN_R1.13.pdf). El defecto de la cola de comandos está confirmado por lectura; el retorno concreto después de un corte requiere ensayo físico.

## F07 — P1: BLE expone la contraseña Wi-Fi y permite saltar a la OTA sin firma

**Ubicación:** `firmware/esp32/src/ble_transport.cpp:87–93,285–294`; `firmware/esp32/src/instrument.cpp:128–130,1101`; `firmware/esp32/src/main.cpp:30–34,108–110`.

El acceso BLE sin emparejamiento y la API sin autenticación son decisiones explícitas. El problema adicional es que el filtro BLE bloquea `/api/access`, pero permite `GET /api/config`, cuya respuesta incluye `ap_password`. `GET /api/wifi/networks` devuelve la misma configuración. Así, una contraseña personalizada del AP también se puede recuperar por BLE cuando el equipo acepta una conexión.

**Impacto:** un cliente cercano puede obtener la contraseña, unirse al AP y acceder a las operaciones HTTP, incluida OTA sin firma. Bloquear la carga OTA directamente por BLE no corta ese camino. Contradice la afirmación de que las credenciales no viajan por BLE en `docs/connectivity/KNOWN_LIMITATIONS.md`.

**Corrección propuesta:** separar las respuestas por capacidad de transporte, retirar las credenciales de las rutas genéricas y definir una autorización real para operaciones privilegiadas. Esto no exige decidir ahora volver al emparejamiento. Cambiar solamente la contraseña del AP no resuelve la exposición.

La cadena está confirmada por las rutas del código; no se intentó recuperar credenciales reales ni instalar otra imagen.

## F08 — P2: WebSocket accede al servidor y a sus clientes desde tareas distintas sin sincronización

**Ubicación:** `firmware/esp32/src/telemetry_ws.cpp:38–89`; `firmware/esp32/src/main.cpp:238–239`.

`handler` modifica `clients` y `clientCount` desde la tarea HTTP. `broadcast` los lee y también puede modificarlos desde `loopTask`; no hay mutex ni transferencia de propiedad a una única tarea. Además, llama directamente a `httpd_ws_send_frame_async` desde ese bucle. El sufijo `async` no significa que esta función encole el envío: la implementación de ESP-IDF envía cabecera y contenido mediante el socket en esa llamada.

**Impacto:** altas/bajas concurrentes pueden producir listas inconsistentes; envíos pueden competir con el manejo de la sesión. Un cliente lento también puede detener `loopTask` hasta el plazo de envío y retrasar BLE, consola, encuesta de base y control del instrumento. No se reprodujo una caída física por esta causa.

**Corrección propuesta:** mantener la lista y los envíos en la tarea HTTP mediante `httpd_queue_work` o la API de envío encolado adecuada, con límite de pendientes y vida de buffers explícita. Validar que el descriptor siga siendo WebSocket antes de reutilizarlo.

Se contrastó con `esp_http_server.h` instalado (línea 1650) y con la [implementación oficial de ESP-IDF 4.4.7](https://github.com/espressif/esp-idf/blob/v4.4.7/components/esp_http_server/src/httpd_ws.c#L343).

## F09 — P2: WebSocket pierde también la salud cuando deja de llegar GGA

**Ubicación:** `firmware/esp32/src/telemetry_ws.cpp:145–175`.

La emisión de salud está después de los retornos por ausencia de UTC, GGA vencida, época repetida o límite de envío de posición. Por eso deja de informar edad de correcciones y estado precisamente cuando desaparecen las épocas GNSS. BLE ya separa ambos flujos.

**Impacto:** un cliente WebSocket no recibe el mismo latido que un cliente BLE y no puede distinguir por ese canal la pérdida de medición de la pérdida de conexión. Es independiente de la frescura del contenido descrita en F04.

**Corrección propuesta:** programar salud a 1 Hz con independencia del flujo de posiciones y aplicar F04 al contenido de ese paquete.

## D01 — decisión explícita: la «precisión» mostrada no es la estimación del receptor

**Ubicación:** `firmware/esp32/lib/protocol/src/health_packet.h:21–45`; `firmware/esp32/src/instrument.cpp:784–799`.

La regla implementada es:

```text
exceso = max(0, sigma_horizontal_UM980_mm - 35)
horizontal_mostrada = 10 + exceso
vertical_mostrada   = 15 + exceso
```

Con sigma horizontal real de 35 mm y sigma vertical real de **1000 mm**, la prueba devolvió **10 mm horizontal y 15 mm vertical**. La vertical real no interviene en la cifra vertical mostrada. Las cifras crudas se conservan en otros campos/bytes, pero la API también pone las cifras transformadas en campos llamados `horizontal_sigma_m` y `vertical_sigma_m`, usados por el panel.

Los comentarios registran esto como decisión del propietario del 27 de septiembre. No se atribuye a código malicioso ni a un error accidental, y esta auditoría no lo cambia. **La consecuencia técnica es que esas cifras no permiten evaluar la incertidumbre real ni demostrar exactitud.** Conviene presentarlas como un indicador de producto claramente diferenciado y conservar las sigmas reales para decisiones de calidad, registros y aceptación de puntos.

## Otras observaciones

- `ellipsoid` comienza en `false` y solo cambia con ACK de una escritura `CONFIG UNDULATION`. Si la reconciliación lee que ya está correctamente en cero y no escribe nada, `heightReference()` puede seguir etiquetando la altura como `receiver_msl`. Revisar la actualización de estado desde la lectura (`gnss_control.cpp:24,126–127,260–266`).
- La consulta de perfiles puede anunciar valores como aplicados antes del ACK: `start` modifica varios campos de `profileState` al encolar y no restaura el estado anterior ante rechazo. El diagnóstico debe separar solicitado, confirmado y leído.
- Hay accesos entre tareas a `mode` y a perfiles NTRIP que no comparten el mutex de escritura. Requieren revisión de concurrencia adicional; no se afirma haber reproducido corrupción de memoria.
- NTRIP del equipo declara que no soporta GGA para VRS ni TLS. Un mountpoint que exige GGA puede no entregar correcciones aunque las credenciales sean correctas; es una limitación declarada, no prueba de avería del GNSS.
- La documentación tiene descripciones antiguas que contradicen la configuración actual: autenticación, frecuencias, watchdog y persistencia. El código compilado tiene `TRESVIZO_TASK_WDT` habilitado. Los documentos históricos no deben usarse como especificación única de 0.7.12.
- La búsqueda de conexiones salientes en el código propio encontró los destinos NTRIP configurados y la descarga de órbitas de CelesTrak. No se encontró indicio de exfiltración intencional en esas rutas. Esto no certifica el binario instalado ni sus dependencias.

## Verificación realizada

| Comprobación | Resultado |
| --- | --- |
| `pio run -e esp32s3_usb` | Correcto. RAM estática 99,728 / 327,680 bytes; aplicación 1,591,513 / 1,966,080 bytes. No mide consumo dinámico bajo carga. |
| 13 ejecutables de `firmware/esp32/test/*_test.cpp`, Clang C++11, `-Wall -Wextra -Werror` | Todos correctos. |
| Banco BLE: `python3 -m unittest discover -s tools/ble_bench/tests -t tools/ble_bench` | 85 pruebas correctas, con simulador y paridad de protocolo; no es BLE físico. |
| `tests/gnss_bench_test.py`, usando Python de PlatformIO | 14 pruebas correctas. |
| `tests/ntrip_bench_test.py`, usando Python de PlatformIO | 3 pruebas correctas, sockets de loopback. |
| `node tests/gnss_panel_test.js` | Correcto. |
| Reproducciones de F01–F04 y D01 | Resultados adversos descritos arriba, ejecutando componentes reales con entradas sintéticas y sustitutos de hardware cuando hizo falta. |

El primer intento de GNSS con Python del sistema falló por ausencia de `pyserial`; con el entorno existente de PlatformIO pasó. Un intento de ejecución C++ con AddressSanitizer/UndefinedBehaviorSanitizer quedó detenido en el primer ejecutable y se terminó; **no se acredita una pasada con sanitizadores**. Las trece pruebas sin ellos sí finalizaron.

No se ejecutaron los smoke tests físicos, actualizaciones OTA, reinicios, cambios de configuración del receptor ni cortes de alimentación. Las reproducciones se hicieron fuera del firmware de producción.

## Orden propuesto de corrección

Corregir primero F01–F04, porque afectan a las correcciones y a la confiabilidad de coordenadas/calidad. Resolver F05–F06 en la misma revisión del ciclo base/rover y persistencia. Cerrar F07 antes de tratar una contraseña personalizada como protección de la OTA. Después ajustar WebSocket (F08–F09) y reconciliar documentación y estado reportado. D01 necesita una decisión consciente sobre qué significa la precisión que ve el operador.
