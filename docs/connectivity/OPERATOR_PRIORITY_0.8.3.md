# Prioridad del operador — firmware 0.8.3

04-10-2026. La última orden válida del operador sustituye el trabajo pendiente del mismo controlador. Se responde al aceptar la orden y se informa por separado de su ejecución. Una petición inválida no debe interrumpir la operación vigente. Esta regla queda recogida en `AGENTS.md`.

## Fallos corregidos

| Hallazgo | Resultado del cambio |
| --- | --- |
| Una secuencia GNSS ocupada devolvía 409, incluida la reconciliación automática del arranque. | Un trabajo nuevo sustituye la cola anterior y recibe un `job_id` propio con 202. El arranque cancelado no vuelve a imponer su configuración. |
| Sustituir directamente la cola podía atribuir el ACK de un comando anterior a uno nuevo igual. | Se conserva únicamente el comando ya transmitido hasta consumir su ACK/lectura. Los comandos anteriores pendientes no salen. Si el receptor no responde en su plazo de 4 s, la nueva secuencia termina `partial_or_unknown` sin transmitirse. |
| Cambiar perfil, destino de publicación o caster local exigía «detener primero». | Se acepta la nueva configuración y se invalida la sesión anterior mediante una generación. También se invalidan sus tramas encoladas y sus resultados de conexión. |
| `WiFiClient::connect(host, …, 2000)` resolvía DNS antes de aplicar ese timeout. La biblioteca Arduino instalada espera hasta 15 s por DNS; sus escrituras pueden hacer diez esperas de un segundo. | DNS asíncrono en la tarea TCP/IP; TCP y escritura con sondeo cancelable. Se comprueba la generación cada 10 ms mientras se espera DNS y cada 20 ms en esperas de socket. No son garantías de tiempo real del planificador. |
| Cancelar DNS podía dejar un callback apuntando a memoria liberada. | El contexto tiene un dueño en el worker y otro en TCP/IP. Una respuesta tardía libera su referencia sin modificar la conexión nueva. |
| Un socket lento podía retener la publicación y acumular RTCM viejo. | Escrituras de RTCM con presupuesto de 200 ms, cierre ante escritura incompleta y descarte de tramas de salida con más de 2 s. No se continúa una trama parcial en otra sesión. |
| Los perfiles NTRIP se leían desde el worker mientras la app los modificaba. | Las decisiones automáticas y los perfiles pertenecen al controlador serializado del instrumento. El worker toma una copia coherente de configuración y generación. |
| El intento NTRIP anterior podía publicar su error o entregar una última trama después de cambiar de perfil. | Estado y envío RTCM verifican la generación bajo el mismo mutex que sustituye la conexión. |
| «Ninguna» podía no persistirse si el estado inicial ya era `none`, permitiendo autoconectar al reiniciar. | Se distingue ausencia de elección de elección explícita. `none` guardado impide la autoconexión NTRIP, también al volver a arrancar. |
| Un promedio anterior podía aplicar una base después de otra orden; cancelar el promedio no cancelaba su secuencia UART. | El promedio sigue su propio `job_id`. Una nueva orden GNSS lo cancela; cancelar una aplicación elimina sus comandos pendientes sin cancelar un trabajo posterior. Un promedio válido nuevo sustituye el anterior. |
| Un cuerpo rover inválido podía detener NTRIP antes de ser rechazado. | Primero se valida/admite el trabajo, después se hacen las transiciones de correcciones y promedio. |
| Reiniciar o iniciar una OTA exigía esperar a la consulta GNSS. | Reiniciar cancela los trabajos pendientes. Una OTA validada cancela GNSS/promedio/NTRIP antes de preparar la imagen; no exige detenerlos a mano. |
| Escanear redes obligaba a detener NTRIP. | El escaneo solicitado se inicia asíncronamente y la conexión NTRIP se recupera si la radio la interrumpe. |

## Límites y compatibilidad

La cancelación no deshace comandos que el receptor ya ejecutó. Se sustituye una **secuencia completa**: los cambios de una secuencia anterior interrumpida pueden estar parcialmente aplicados y no guardados. Por eso se conserva `partial_or_unknown`, los identificadores de trabajo y la distinción entre 202 y confirmación. Las apps actuales de iOS y Android comparan `job_id` y consideran incierto un trabajo sustituido por otro; no lo toman como confirmado.

Un comando UART ya transmitido debe terminar su respuesta; CONFIG conserva su ventana de lectura de 700 ms. DNS tiene presupuesto local de 5 s y establecimiento TCP de 2 s, ambos cancelables. Son presupuestos de conexión, no esperas impuestas al handler. Las respuestas DNS pendientes pueden ocupar temporalmente entradas del resolvedor lwIP hasta que éste las cierre.

Se mantienen las protecciones de una grabación abierta y de una OTA activa: todavía se debe cerrar la grabación antes de reconfigurar GNSS, actualizar o reiniciar. No se recorta un archivo abierto ni se interrumpe la activación de firmware para fingir una transición instantánea. Sin red externa configurada se informa del requisito real; con red guardada pero temporalmente desconectada se acepta NTRIP y se publica `waiting_network`. Una base sigue sin consumir NTRIP.

No se cambian UUID, paquetes, rutas, claves existentes ni estados del contrato. GNSS añade `superseded_job_id`, `superseded_jobs` y `waiting_command_reply` como diagnóstico. `select` de perfiles conserva su función de preferencia guardada; `connect` es la acción que cambia la conexión activa. No se modificaron las apps ni la geometría mecánica.

## Pruebas

- 38 suites C++ con `-Wall -Wextra -Werror` y UBSan, incluidas seis nuevas. Los bancos de integración compilan el código de `src/`; simulan reloj, UART, almacenamiento, Wi-Fi y callbacks DNS. El conector también se comprueba contra sockets TCP reales de loopback en la Mac. No equivale a validar un caster sobre la radio ESP32.
- Casos: tres órdenes superpuestas, rechazo sin efectos, ACK de otra orden, timeout UART, cancelación del promedio en fase de aplicación, sustitución de NTRIP durante conexión y al completar una trama RTCM, error tardío, fallo de persistencia al conectar perfil, selección `none` tras reinicio, cambio del caster sin cambiar puerto, DNS tardío tras cancelación y escritura TCP interrumpida.
- 644 comprobaciones estáticas del contrato y 35 pruebas de su herramienta superadas. Las discrepancias históricas anotadas en el catálogo se conservan.
- 320 comprobaciones del contrato en la ESP32 por USB. El listado de sesiones no se validó: no hay memoria instalada y devuelve 503.
- Banco USB en la imagen final: cinco consultas GNSS consecutivas aceptadas; mediana 6.0 ms, máximo 6.1 ms. Solicitud inválida conservó el trabajo y la fuente vigentes. Reinicio durante consulta aceptado en 4.7 ms y equipo de vuelta. Ajustes comparados con 0.8.2, sin cambios.
- BLE físico: 123 respuestas completas en tres conexiones, MTU 247, cero errores de reensamblado. Mediana 87.7 ms, P95 209.3 ms, máximo 237.5 ms. Mayor separación entre latidos 1049.9 ms. Un bloqueo deliberado sin suscripción se recuperó en 4545.4 ms; cero fallos de notificación y cero fragmentos forzados. Configuración sin cambios.
- OTA durante consulta GNSS aceptada en 14.2 ms; consulta sustituida. Bloque de 576 B, duplicado y offset incorrecto comprobados; aborto completado. Slot activo y ajustes sin cambios. La prueba escribió y borró el slot inactivo.
- Compilación, firma y carga USB verificadas. RAM estática 101456 B; aplicación 1737209 B, 88.4 % del slot. Archivo firmado de 1737720 B, SHA-256 `1c23f16627459a28a5727a73b03ca7c0f4e6aab135cc288831830f4078810033`.

Pendiente: caster real, cambios de base con soluciones GNSS y RTCM sostenido, comportamiento visual en iPhone/Android y OLED. El equipo sigue con Wi-Fi externo sin configurar y OLED `not_detected`; estos ensayos no validan esas partes.

## Reproducción

Desde la raíz del repositorio:

```sh
python3 tools/firmware_tests/run_native.py
python3 tools/api_contract/check_contract.py
~/.platformio/penv/bin/pio run -d firmware/esp32
~/.platformio/penv/bin/python tests/operator_priority_bench.py
~/.platformio/penv/bin/python tests/protocol_transport_bench.py --stall --fragment-bytes 0
~/.platformio/penv/bin/python tools/api_contract/check_contract.py device --port /dev/cu.usbmodem21101
```

`operator_priority_bench.py` hace consultas y un reinicio, sin aplicar coordenadas ni perfiles. `ota_priority_bench.py` comprueba la prioridad de OTA; **escribe y borra el slot inactivo**, sin activar la imagen ni cambiar ajustes. No ejecutarlo si interesa conservar la imagen anterior de ese slot.
