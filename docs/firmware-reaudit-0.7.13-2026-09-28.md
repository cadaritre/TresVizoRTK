# Reauditoría del firmware 0.7.13 — 28 de septiembre de 2026

Código revisado: `930aad162c3da59a1fd57fe749cea0a6e1ecbfa3`. Comparación con `179b3f6d506c42429f71af1b4ce7326fa5e71fc7`, correspondiente a la [auditoría de 0.7.12](firmware-audit-2026-09-28.md). Perfil `esp32s3_usb`, Arduino-ESP32 2.0.17 / ESP-IDF 4.4.7.

**Resultado:** los nueve hallazgos anteriores tienen correcciones en el código y pasan las comprobaciones descritas abajo. Quedan un defecto P1 en la nueva recuperación OTA y un defecto P2 preexistente en la referencia de altura publicada al arrancar. La transformación deliberada de la precisión mostrada sigue vigente.

Se revisaron los cambios entre ambas versiones, las rutas de integración y los componentes relacionados. Se compilaron el firmware y las pruebas locales. No se modificó el firmware, no se cargaron imágenes ni se accedió al receptor físico. Esta revisión no certifica precisión topográfica ni ausencia de otros defectos.

## Estado de los hallazgos anteriores

| ID | Resultado en 0.7.13 | Evidencia y límite |
| --- | --- | --- |
| F01: pérdida de RTCM al pasar por el filtro | Corregido para el defecto reproducido. | `ReceiverStream` entrega los bytes UART originales al parser RTCM. La prueba mixta conserva 60/60 tramas RTCM con `0xAA`, 20/20 Unicore y 72/72 GGA. No es una medición de latencia física. |
| F02: altura de antena sumada dos veces | Corregido. | El promedio declara la altura observada de antena sin volver a elevarla; «usar la actual» convierte primero a la marca del suelo. Repetición con 100 m y jalón de 2 m: se declara **100 m**, no 102.1 m; la marca informativa queda en 97.9 m. El offset de case de 0.10 m sigue siendo un parámetro pendiente de validación mecánica. |
| F03: promedio aplicado después de perder FIX | Corregido para el caso reproducido. | La misma secuencia FIX → calidad cero → fin del plazo termina en **`cancelled`**, con una muestra y sin llamar a `applyBase`. Se añadieron límites de edad y cantidad mínima de muestras. |
| F04: salud con FIX y sigmas vencidas | Corregido. | GGA y GST caducan a los dos segundos en salud. El caso con muestras de 0.001 s a tiempo 60 s devuelve **calidad 0** y **65535** en las cuatro precisiones, es decir, desconocidas. |
| F05: rover sin salidas de posición | Corregido por inspección de la secuencia. | `rover` repone GGA, GST, GSV y GSA después de `UNLOG COM2` y antes de guardar. Falta probar la transición contra el UM980 físico. |
| F06: base sin guardar, pero `saved=true` | Corregido por inspección de la secuencia. | `applyBase` añade `SAVECONFIG`; `saved` se confirma con su ACK. La encuesta informa si no quedó guardado. Falta comprobar persistencia con un corte real. |
| F07: contraseña por BLE y OTA sin firma | La lectura de secretos y la carga OTA normal están corregidas; ver R01. | Redacción recursiva de secretos en la respuesta BLE y verificación ECDSA P-256 en `finish`. Las pruebas de redacción pasan; el binario firmado verifica y dos alteraciones se rechazan. El acceso BLE abierto y las operaciones de configuración permitidas siguen siendo decisiones explícitas del producto. |
| F08: clientes/envíos WebSocket entre tareas | Corregido por inspección. | La lista y los envíos quedan en la tarea HTTP, mediante `httpd_queue_work`, con un lote pendiente como máximo y control de cliente lento. Falta una prueba de carga con conexiones reales. |
| F09: salud WebSocket dependiente de GGA | Corregido por inspección. | El latido se programa independientemente de las posiciones; el contenido aplica la caducidad de F04. Falta una prueba de desconexión GNSS en hardware. |

## R01 — P1: restaurar puede activar una imagen cuya firma nunca se verificó

**Ubicación principal:** `firmware/esp32/src/firmware_update.cpp:135–145`. Relacionado: líneas 38–50, 75–80, 168–173 y 179–204; `firmware/esp32/lib/protocol/src/signed_firmware.h:202–210`.

La carga normal comprueba correctamente la firma del propietario en `finish`. Sin embargo, durante `chunk` ya escribe toda la imagen en la partición inactiva. El trailer de firma y el estado de la transferencia permanecen únicamente en RAM. La invalidación al abortar o vencer el plazo depende de ese estado volátil.

Si se reinicia o se corta la alimentación después de escribir todos los bytes de la imagen, pero antes de comprobar la firma, queda una imagen completa sin autenticar en la otra partición. Tras arrancar de nuevo, `active` y `targetTouched` vuelven a falso. La ruta `rollback` comprueba el descriptor ESP y `requiresSignature(next)`, que solo lee la marca **`TVZFWID1`** y una versión igual o posterior a **0.7.13**. Esa marca describe lo que la imagen afirma ser; no demuestra quién la firmó.

La implementación oficial de [ESP-IDF 4.4.7 de `esp_ota_set_boot_partition`](https://github.com/espressif/esp-idf/blob/v4.4.7/components/app_update/esp_ota_ops.c#L402) valida la imagen y cambia `otadata`; no exige que haya terminado una sesión OTA ni conoce el trailer privado de este proyecto. La [validación de imagen de Espressif](https://github.com/espressif/esp-idf/blob/v4.4.7/components/bootloader_support/src/esp_image_format.c#L138) distingue integridad de firma de Secure Boot. El `sdkconfig.h` del perfil `dio_qspi` utilizado no habilita Secure Boot; el rollback automático de aplicaciones sí está habilitado. No se consultaron los eFuses del equipo.

**Condiciones e impacto:** con acceso a la API de actualización, una imagen ESP32-S3 estructuralmente válida con esa marca, y una interrupción en la ventana indicada, `rollback` puede seleccionar una imagen que nunca pasó la verificación ECDSA del propietario. No hace falta romper ECDSA. La autorización criptográfica falta en esa ruta alternativa. No se afirma que un corte cualquiera instale por sí mismo la imagen: también interviene la solicitud de restauración.

**Evidencia local:** usando `Splitter` y `requiresSignature` reales, se entregó el `firmware.bin` compilado por bloques de hasta 576 bytes, anunciando además los 72 bytes del trailer, pero sin entregarlos. La memoria que representaba la partición terminó con todos los bytes de la imagen. Se descartó el estado de recepción para representar un reinicio y se evaluó la barrera de identidad de restauración:

```text
all_image_bytes_written=1 finish_would_be_incomplete=1 signature_checks=0
rollback_identity_gate=1
```

Además, `esptool image_info` confirmó checksum y hash ESP válidos para ese `firmware.bin`; el verificador de firma del proyecto lo rechazó por falta del trailer. Así se comprueba que una imagen válida para Espressif y para la barrera de identidad puede carecer de la firma exigida por el proyecto. La reproducción es de componentes y flujo del código: no ejecutó el endpoint de restauración ni probó el arranque en el ESP32.

**Corrección propuesta:** exigir evidencia persistente de autenticidad antes de restaurar. Por ejemplo, conservar la firma y verificarla contra los bytes de la partición antes de seleccionarla. Si se utiliza un registro de validación, debe vincularse al hash y a la partición, invalidarse de forma persistente antes de la primera escritura y confirmarse únicamente después de verificar. Un corte en cualquier fase debe dejar la imagen sin autorización para restaurar. La marca de versión puede conservarse para compatibilidad, pero no sustituye esa comprobación.

**Prueba de aceptación pendiente:** interrumpir antes y después del final de la imagen, de la firma y de la confirmación; después del reinicio, intentar restaurar. Toda imagen sin firma validada debe rechazarse, y la imagen anterior auténtica debe seguir siendo restaurable cuando corresponda.

## R02 — P2: una altura elipsoidal se etiqueta como MSL después de reiniciar

**Ubicación:** `firmware/esp32/src/gnss_control.cpp:24,176–177,259,315–325`; publicación en `firmware/esp32/src/instrument.cpp:815–816` y presentación en `firmware/esp32/web/app.js:142–155`.

`ellipsoid` arranca en falso y solo cambia a verdadero al recibir el ACK de un comando enviado `CONFIG UNDULATION 0.0000`. Si el receptor ya tiene ese valor guardado, la reconciliación de arranque lo lee, detecta que coincide y no envía el comando. Tampoco actualiza `ellipsoid` desde la lectura. Por tanto, `heightReference()` devuelve `receiver_msl` para un receptor que ya entrega la altura bajo la configuración elipsoidal del proyecto.

**Escenario:** configurar rover o base en 0.7.13, confirmar el guardado de ondulación cero y reiniciar el ESP32. Si la lectura posterior coincide con la línea base, la etiqueta puede permanecer incorrecta hasta que otra acción vuelva a enviar el comando. La secuencia está confirmada por inspección del código; no se reinició el equipo para comprobarla.

**Impacto:** el panel informa una referencia vertical equivocada. Un consumidor que decida una conversión geoidal según ese campo podría aplicar una conversión indebida. La revisión no demuestra que las apps móviles lo hagan.

**Corrección propuesta:** actualizar la referencia a partir del valor observado de `CONFIG`, además de los ACK de cambios. Antes de confirmarla, publicar referencia desconocida. Probar arranque con ondulación cero ya guardada, con AUTO y con lectura fallida.

## D01 — se conserva la transformación deliberada de precisión

`health_packet.h` mantiene la regla `exceso = max(0, horizontal_cruda_mm - 35)`, horizontal mostrada `10 + exceso` y vertical mostrada `15 + exceso`. La sigma vertical cruda no interviene en esas cifras. El caso de 35 mm horizontales y 1000 mm verticales sigue correspondiendo a 10/15 mm mostrados.

Los comentarios declaran la decisión del propietario y se conservan las sigmas crudas en campos independientes. No es un defecto nuevo ni evidencia de intención maliciosa. Sí sigue siendo necesario interpretar lo mostrado como métrica de producto: no como incertidumbre del receptor ni como exactitud medida. Los campos heredados `horizontal_sigma_m` y `vertical_sigma_m` siguen recibiendo las cifras transformadas en `instrument.cpp:802–805`.

## Comprobaciones ejecutadas

| Comprobación | Resultado |
| --- | --- |
| PlatformIO, perfil `esp32s3_usb` | Correcto. RAM estática 99,976 / 327,680 bytes; flash de aplicación 1,598,497 / 1,966,080 bytes. No mide máximos de heap o pila durante operación. |
| Los 19 ejecutables de `firmware/esp32/test`, C++11 con `-Wall -Wextra -Werror` | Todos correctos. |
| Banco BLE, `unittest discover` | 85 pruebas correctas en simulador/paridad; no es BLE físico. |
| `tests/gnss_bench_test.py` | 14 pruebas correctas. |
| `tests/ntrip_bench_test.py` | 3 pruebas correctas con sockets de loopback. |
| `node tests/gnss_panel_test.js` | Correcto. |
| Repetición de F02/F03 con `src/base_survey.cpp` real y sustitutos de reloj/receptor | Altura declarada 100 m; pérdida de FIX cancela y no aplica. |
| Repetición de F04 con `health_report::build` real | Calidad cero y cuatro precisiones desconocidas al vencer las muestras. |
| Verificación de `firmware-signed.bin` con la clave pública embebida | Firma válida; su imagen coincide byte por byte con el `firmware.bin` compilado. |
| Modificar un byte de imagen / un byte de firma, en copias en memoria | Ambas verificaciones rechazadas. No se leyó la clave privada. |
| `esptool image_info` sobre `firmware.bin` | Checksum y hash ESP válidos; tamaño 1,598,896 bytes. |
| Reproducción local de la barrera OTA tras perder el estado de recepción | Imagen completa escrita, cero verificaciones de firma y barrera de identidad aceptada: R01. |

No se ejecutaron pruebas con sanitizadores en esta reauditoría. Quedan pendientes cortes físicos de alimentación, OTA y rollback reales, ciclos base/rover en el UM980, carga de clientes WebSocket y ensayos de precisión independientes.

**Prioridad:** cerrar R01 antes de considerar completa la protección OTA con firma; corregir R02 para que la referencia vertical publicada sea fiable desde el arranque.
