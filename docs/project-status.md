# Estado del proyecto

Fecha de referencia: septiembre de 2026.

**Actualización mecánica/power del 20/09:** existe CAD A5 y propuesta por módulos comerciales. La [revisión conjunta](INTEGRATION_REVIEW.md) corrige la integración local del panel, pero detecta bloqueo de montaje axial del cuerpo y pendientes de soportes power, arnés e inserto. No hay receptor completo liberado para imprimir o energizar. Las filas históricas que indican ausencia de CAD o propuesta de alimentación quedaron superadas por estos archivos; no implican validación física.

## Significado de los estados

- **Previsto:** forma parte del alcance o de la arquitectura deseada, pero puede no estar diseñado ni implementado.
- **Por confirmar:** requiere identificar hardware, consultar documentación, medir o tomar una decisión.
- **Implementado:** existe una realización concreta en el repositorio o en el prototipo; no implica que esté validada.
- **Validado:** cuenta con pruebas documentadas y criterios de aceptación cumplidos.

## Resumen

| Área | Estado | Evidencia o pendiente |
| --- | --- | --- |
| Estructura y documentación inicial | Implementado | Directorios, metadatos y documentos iniciales presentes en el repositorio. |
| Inventario de componentes | Parcialmente identificado | Capturas y confirmaciones registradas en hardware/identification.md. Falta verificar revisiones físicas y paquete UM980. |
| Batería | Por confirmar | Aún no se ha recibido o seleccionado la unidad definitiva. |
| GNSS principal UM980 | Previsto | Falta identificar la carrier, firmware, interfaces y señales expuestas. |
| Receptor RTK de triple banda | Objetivo de desarrollo | Verificar cobertura del conjunto real de receptor, firmware y antena. |
| PPS del UM980 | Por confirmar | Debe comprobarse su disponibilidad en el conector de la carrier concreta. |
| ZED-F9P | Previsto para pruebas | Está disponible como opción de ensayo; no se ha definido integración. |
| ESP32-S3 | Arranque comprobado | USB identifica 4 MB de flash y 2 MB de PSRAM; captura selecciona ESP32-S3-Tiny. Primer firmware cargado. GPIO externos pendientes. |
| BMI088 | Previsto | Falta identificar el breakout, orientación, interfaz y características eléctricas. |
| Lector y tarjeta microSD | Previsto | Módulo o socket, interfaz, circuito y política de cierre seguro pendientes. |
| Antena Helix | Compra confirmada | El propietario confirmó la compra; modelo, bandas y referencia mecánica pendientes. HA-901A no confirmada. |
| Alimentación y carga | Por confirmar | No existe todavía un diseño verificado para protección, regulación, carga y encendido. |
| Firmware del instrumento | Base implementada | Versión 0.1.0 compilada y cargada. Arranque, estado real, ajustes y consola USB comprobados; capacidades topográficas pendientes. |
| Interfaz de configuración del instrumento | Implementado | Panel web en flash con marca TresVizo; nombre, intervalo del panel y ajustes Wi-Fi. Puente USB local para desarrollo. |
| Persistencia de ajustes y consola USB | Comprobaciones iniciales superadas | Pruebas de validación, conflictos de revisión, reinicio y recuperación del parser en placa. No equivalen a validación de campo. |
| Wi-Fi AP/STA | Implementado; validación parcial | Arranque del AP comprobado desde el controlador. Conexión directa de un cliente Wi-Fi y hotspot externo pendientes de prueba. |
| Aplicación móvil independiente | Previsto | Destinada a levantamientos, replanteos y trazo. No hay framework, proyecto ni protocolo implementado. |
| Carcasa | Previsto | Solo existe el concepto cilíndrico; no hay dimensiones ni CAD. |
| Operación rover/base | Previsto | Sin implementación ni pruebas. |
| NTRIP y transporte RTCM | Previsto | Sin implementación ni pruebas. |
| Registro para postproceso | Previsto | Sin implementación, formatos seleccionados ni pruebas. |
| Fusión GNSS/IMU | Previsto | Sin algoritmo, calibración ni validación. |
| Telemetría BLE a 20 Hz | Previsto | Es un objetivo pendiente de mediciones de rendimiento y estabilidad. |
| Precisión aproximada de 2 cm | Objetivo de desarrollo | No implementada, medida ni garantizada. |
| Operación bajo árboles | Interés de investigación | No existe garantía ni evidencia de precisión bajo vegetación. |

## Validación

La base de firmware cuenta con comprobaciones iniciales de compilación, carga y funcionamiento en el ESP32. Los resultados y límites están en [validación del firmware](firmware-validation.md). No hay subsistemas topográficos validados. El estado FIX de una solución futura no bastará para declarar exactitud: deberán realizarse ensayos independientes, repetibles y documentados contra referencias adecuadas.

Este documento debe actualizarse cuando cambie la evidencia, no solo cuando cambien las intenciones. La secuencia prevista se describe en la [hoja de ruta](roadmap.md).

## Adquisición GNSS en desarrollo

UM980 identificado por USB y salida GGA activada temporalmente a 0.1 s. Parser compartido y tarea UART opcional implementados en código; la adquisición UART está desactivada por defecto hasta verificar el cableado. Las pruebas de software no validan el enlace físico ESP32–GNSS. Véase [primera adquisición GNSS](gnss-bringup.md) para evidencia y límites.


## Firmware cargado: 0.2.0

Clave de acceso actualizada por USB y persistencia comprobada. Panel GNSS conectado a la API y adquisición UART opcional preparada; UART desactivada mientras las placas sigan separadas. Repetidas las 28 pruebas de hardware con éxito. La captura del UM980 en la Mac entrega UTC a 10 Hz, todavía sin solución válida. BLE continúa pendiente de implementación; su papel principal de operación/correcciones está definido en la arquitectura.


## Firmware cargado: 0.3.0 — apartados de operación

Agregados Base / rover, Registro / PPK y Correcciones con entrada NTRIP, publicación externa y caster local. Preparación y exportación de planes de base operativas; aplicación física, grabación, RINEX y transportes todavía no integrados. Pasaron 27 comprobaciones de la API en el ESP32 y pruebas del cálculo de alturas con sanitizadores. El plan de implementación y comandos investigados está en [registro, base y NTRIP](recording-base-ntrip.md).

## Estado actual: 0.4.0 — actualización y banco USB

Esta sección sustituye los estados históricos anteriores para estos componentes:

| Componente | Implementado y límite actual |
| --- | --- |
| Actualización ESP32 | Panel y API autenticada, doble partición, SHA-256, comprobación de hardware e imagen, confirmación de arranque y restauración anterior. Cargas completas reales comprobadas conservando NVS. Firma de distribución pendiente. |
| Extensiones de correcciones | Router RTCM3 con CRC, fuente única y colas limitadas; BLE integrado. Interfaces reservadas para NTRIP y radio en ESP32; necesitan su controlador y validación por modelo. |
| BLE | Servicio, comandos autenticados, telemetría y recepción RTCM compilados y anunciados por la placa. Emparejamiento con la futura app y rendimiento extremo a extremo pendientes. |
| GNSS por USB | Banco real en la Mac, demultiplexado Unicore/NMEA/RTCM, épocas GGA a 10 Hz y estado sin posición cuando corresponde. UART GPS–ESP32 permanece desactivada y sin cablear. |
| Base / rover | Comandos y verificación implementados en banco; planes comprobados con pruebas. Aplicación de coordenadas de base reales pendiente. |
| Registro / RINEX | Inicio, parada, originales, recuperación y exportación en la Mac; conversión real a RINEX 3.04. microSD física y PPK con una base solapada pendientes. |
| NTRIP | Cliente, publicador y caster local de banco probados por sockets de loopback. NTRIP v1 inicial, sin GGA para VRS; sin ensayo con caster externo ni ejecución en ESP32. |

Detalles: [actualizaciones y módulos](firmware-updates.md), [protocolo BLE](ble-protocol.md), [banco USB](usb-bench.md). La pérdida de posición del UM980 trasladado al interior no impide desarrollar ni confirmar un arranque saludable. IMU, compensación de inclinación y exactitud topográfica siguen sin validación física.


## Validación UART física — 0.4.1, 2026-09-20

Cableado confirmado por el propietario: GPS TTL_TXD2 → ESP32 GPIO18, TTL_RXD2 → GPIO17, GND común; alimentación USB separada sin unir los pines de alimentación. Perfil predeterminado actualizado. Compilación, OTA a app1 y conservación de ajustes comprobadas.

En 58.969 s entre muestras: 589 GGA nuevos (9.988 mensajes/s), cero rechazos, desbordes y errores UART; 332 consultas USB, todas en estado receiving. RAM libre final: 138024 bytes. Sin UTC ni posición válida en interior, por lo que esto demuestra transporte de mensajes cercano a 10 Hz, no diez soluciones de posición por segundo. Métricas locales sin coordenadas: captures/local/uart-20260920-validation.json.

El panel prioriza UART del ESP32 sobre el banco USB de la Mac. Pasaron las pruebas existentes de render GNSS y comprobaciones de sintaxis JS. Pendientes transmisión ESP32→GPS, correcciones reales, pérdidas bajo carga completa y persistencia del perfil COM2 tras apagar (no se envió SAVECONFIG).


## 0.5.0 — 2026-09-20: servicios autónomos y PSRAM

- PSRAM Quad habilitada: 2094703 bytes de heap utilizable; prueba de 1 MiB con tres patrones superada. RAM interna libre observada ~154 kB, PSRAM libre ~2066 kB. No implica que cada servicio futuro esté validado bajo carga simultánea.
- Control UART real: VERSIONA identificó UM980 R4.10Build13504; MODE confirmó rover; cambios de GGA a 5 Hz y 10 Hz verificados en recepción. Se deja 10 Hz. Base aplica planes validados pero coordenadas/convergencia siguen pendientes de prueba exterior. No se aplicaron coordenadas sintéticas.
- BLE físico con Mac: cifrado SC+MITM (auth mode 13), clave inválida rechazada, respuestas fragmentadas recompuestas, recuperación de credenciales bloqueada y consulta VERSIONA/MODE realizada por BLE→ESP32→UART. Repetido después de reinicios con PIN persistente. Telemetría con UTC y RTCM real por BLE pendientes.
- Cliente NTRIP Wi-Fi implementado y panel disponible. Validación de parámetros y espera sin red comprobadas; flujo real con caster pendiente de que el propietario configure su cuenta. Inicialmente v1/TCP, sin TLS/GGA para VRS; no confundir con servicio plenamente validado.
- Controlador SD de flujo original, cola, cierre, catálogo y lectura por bloques preparado. Perfil con SD compilado, pero nunca cargado; pines de esa compilación son solo para verificar código. El propietario confirma lector desconectado. Perfil instalado mantiene SD not_configured, sin conducir pines supuestos.
- Pruebas: 24 comprobaciones API de servicios; 27 de operaciones; 29 de hardware; 14 Python GNSS y 3 NTRIP de banco. Parser de binario con sanitizadores y render GNSS JS superados. Primera prueba corta de frecuencia capturó transición; se añadió estabilización y cálculo por tiempo real del ESP32: 4.96 y 10.12 Hz en ventanas de unos 5 s. Pruebas históricas se actualizaron para UART activo y respuesta 503 de SD ausente.
- Firmware instalado por OTA, arranque confirmado y ajustes conservados. Detalles y límites: [servicios del ESP32](esp32-services.md).

## 0.6.0 — 2026-09-20: auditoría del firmware, panel de campo y GPS avanzado

Esta sección sustituye los estados anteriores de los componentes que menciona.

### Auditoría del firmware

Revisión completa de las 2065 líneas del firmware. Corregido:

| Hallazgo | Corrección |
| --- | --- |
| Tramas RTCM entregadas al receptor no se publicaban en ninguna API | `correction_frames_sent` y `correction_frames_dropped` expuestos en `subsystems.gnss` y en la vista de Campo |
| Un trabajo GNSS podía quedar en `running` indefinidamente: el plazo de 4 s solo corría tras enviar el comando, y vivía en la rama `else` del caso «aún no enviado» | Plazo global de 20 s desde el lanzamiento, independiente del envío |
| `isxdigit()` e `isalnum()` con `char` con signo: comportamiento indefinido con bytes >0x7F procedentes de JSON | Cast explícito a `unsigned char` |
| Un `xStreamBufferSend` y una toma de semáforo **por byte** desde la tarea UART | Lectura y entrega por bloques de 512 bytes |
| `Rtcm3Parser` hacía `memmove` de hasta 1028 bytes por cada byte de ruido | Resincronización buscando el siguiente `0xD3` con un solo `memmove` |
| `Correction` de 1039 bytes como local en una tarea de 4 KiB | Movido fuera de la pila |
| Cabeceras NTRIP concatenadas byte a byte sobre `String` | Buffer fijo, lectura byte a byte conservada a propósito para no tragarse RTCM del flujo |
| El bucle de cabeceras NTRIP usaba `client.connected()` sin `|| available()` | Corregido; un caster que cierre rápido ya no pierde cabeceras |
| `mbedtls_base64_encode` sin comprobar retorno | Comprobado; si falla no se envía una credencial vacía |
| `hdop` se parseaba y nunca se publicaba | Expuesto en `solution.hdop` |
| `measurement_time` siempre nulo y sin consumidores | Retirado de la API |
| Contadores del binario nativo Unicore invisibles | `native_frames_valid` / `native_frames_invalid` expuestos |
| `String path` sombreaba el parámetro `path` | Renombrado |

No corregido a propósito: el watchdog de las tareas propias queda tras
`-DTRESVIZO_TASK_WDT`, **desactivado por defecto**, porque convierte un bloqueo en
un reinicio y ese cambio de comportamiento no se ha ensayado.

Descartado tras verificación: la doble convención de checksum entre `nmea_gga.h` y
`gnss_control.cpp` no es un error. El XOR de control Unicore incluye el `$`/`#`
inicial, como ya documentaba [el banco USB](usb-bench.md); el de NMEA no.

### Credenciales separadas

Hasta 0.5.0 la contraseña del Wi-Fi propio y la clave de la API eran la misma
cadena. Quien recibía acceso a la red obtenía control total del equipo, incluida
la carga de firmware, que no está firmado. Desde 0.6.0 son dos credenciales
independientes en NVS.

**Al actualizar desde una versión anterior, el equipo genera una contraseña Wi-Fi
nueva.** Hay que leerla por USB con `python tools/usb_console.py access` antes de
volver a conectarse a la red del instrumento. La rotación de la contraseña del AP
desde el panel sigue pendiente.

### Panel reorganizado

Vista de Campo como pantalla inicial, con coordenadas y calidad en un solo bloque
grande; UART, memoria y versiones trasladadas a Diagnóstico. Criterio y límites en
[panel de campo](panel-campo.md).

### Configuración avanzada del GPS

Máscara de elevación, constelaciones, salidas NMEA, perfil RTCM de base, edad
máxima de correcciones, lectura de configuración y persistencia explícita con
`SAVECONFIG`. Sintaxis verificada contra el manual Unicore N4 R1.6; las tasas se
amplían a 1/2/5/10/20 Hz. Detalle y límites en
[configuración avanzada del receptor](gps-advanced.md).

### Pruebas realizadas

- `node --check` sobre los cinco archivos JS del panel: correcto.
- `tests/gnss_panel_test.js`: pasa sin cambios, incluida la ocultación de posiciones
  no vigentes.
- Comprobación cruzada de que los 74 identificadores que el JS manipula existen en
  `index.html`, y de equilibrio de etiquetas por sección.
- Vista previa del panel servida localmente y revisada a 1280 px y a ancho de
  teléfono.
- `python -m py_compile` sobre las herramientas y pruebas modificadas.

### Pruebas pendientes

- **Nada de esto se ha compilado para el ESP32 ni cargado al equipo.** No hay
  compilador C++ ni PlatformIO en la máquina donde se hizo el trabajo.
- Ningún comando nuevo se ejecutó contra el UM980 real; los puertos se
  desconectaron durante la sesión.
- `tests/device_services_smoke.py` se amplió con la validación de la configuración
  avanzada y la lectura del perfil, pero no se ejecutó.
- Sin medir: efecto del consumo por bloques sobre la tasa sostenida, presupuesto
  del enlace con varias sentencias a tasa alta, y comportamiento del panel con luz
  solar directa.
