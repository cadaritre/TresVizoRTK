# Registro para postproceso, base y distribución NTRIP

## Alcance y estado

Requisito del propietario: el instrumento debe operar como rover o base, grabar sesiones para postproceso, permitir iniciar/detener grabación y exportar datos desde su panel web, recibir correcciones, publicarlas en un caster externo y ofrecer distribución dentro de una red local propia. Estos flujos también deben quedar disponibles para la futura app por BLE salvo las descargas grandes, que usarán Wi-Fi.

Esta entrega agrega los apartados del panel, preparación y exportación de un plan de base y consulta de capacidades del firmware. Preparar/exportar un plan no aplica comandos, guarda ajustes en el receptor ni exporta observaciones. Grabación, conversión RINEX y transporte NTRIP siguen deshabilitados hasta integrar sus controladores. El GPS y ESP32 continúan conectados por USB por separado; microSD sin cablear.

## Navegación del panel

| Apartado | Contenido |
| --- | --- |
| Base / rover | Modo efectivo y solicitado; coordenadas conocidas o promedio; identificación de estación; referencias y alturas; previsualización de configuración. |
| Registro / PPK | Nombre y tipo de sesión; tasa de observaciones; antena y altura; iniciar, detener/cerrar; espacio, bytes, duración, pérdidas y sesiones exportables. |
| Correcciones | Entrada NTRIP; publicación de RTCM a caster externo; caster propio local; estados y estadísticas independientes. |

## Alturas y coordenadas de base

Guardar latitud/longitud en grados decimales, hemisferio por signo, sistema de referencia/datum y época de coordenadas cuando aplique, origen de las coordenadas y calidad estimada. No confundir época de coordenadas con hora UTC de una medición. Una transformación entre marcos de referencia necesita parámetros verificados; cambiar la etiqueta no transforma coordenadas.

La interfaz debe distinguir:

- Cota del punto materializado frente a coordenada del punto de referencia de antena (ARP).
- Altura elipsoidal h frente a altura ortométrica H; separación geoidal N y modelo usado: h = H + N.
- Altura vertical desde el punto al ARP frente a distancia inclinada medida a una marca del instrumento.
- ARP frente a centro de fase: modelo de antena, PCO/PCV y calibración pendientes para la Helix concreta.

El preparador inicial acepta coordenadas geográficas, altura elipsoidal y altura vertical al ARP. Si la cota corresponde al punto, calcula h_ARP = h_punto + altura_vertical; si ya corresponde al ARP, no vuelve a sumarla. Este cálculo presupone montaje vertical; no convierte altura inclinada ni aplica correcciones de centro de fase. No introduce valores de latitud/longitud predeterminados que puedan convertirse accidentalmente en una base real.

Para altura ortométrica, ECEF, UTM o coordenadas de otro datum, ampliar el adaptador y validar conversión antes de habilitar aplicación. Debe mostrarse siempre el punto/altura resultante que se enviaría al receptor. Un error en las coordenadas de base se transmite a las soluciones rover.

## Comandos UM980 investigados

Referencia: manual N4, UM980 R4.10Build13504 identificado en banco. Sintaxis documentada no equivale a ejecución validada. Los ejemplos siguientes son plantillas, no comandos enviados durante esta entrega.

| Operación | Comando / observación |
| --- | --- |
| Identificación | `VERSIONA`; ya comprobado por USB. |
| Consultar modo | `MODE`; respuesta ASCII del modo efectivo. |
| Rover topográfico | `MODE ROVER SURVEY`; verificar respuesta y estado al integrar. |
| Base conocida | `MODE BASE <ID> <latitud> <longitud> <altura>`; ID opcional, 0–4095. |
| Base por promedio | `MODE BASE <ID> TIME <segundos> <distancia>`; periodo y reutilización de coordenadas requieren control explícito. |
| Convención de altura | La FAQ de Unicore describe altura sobre nivel del mar por defecto y `CONFIG UNDULATION 0.0` para trabajar con elipsoidal; leer configuración previa, verificar efectos sobre salida de alturas y restaurar la convención al salir del modo. |
| Posición de estación RTCM | `RTCM1005 COM2 10` como perfil de referencia; 1006 incorpora altura de antena pero debe verificarse su configuración antes de usarlo. |
| Descripción | `RTCM1033 COM2 10`. |
| Observaciones para rover | Perfil inicial MSM4: `RTCM1074 COM2 1`, `RTCM1084 COM2 1`, `RTCM1094 COM2 1`, `RTCM1114 COM2 1`, `RTCM1124 COM2 1`. Validar constelaciones activas, receptores destino y presupuesto de ancho de banda. |
| Observaciones nativas | `OBSVMB COM1 1` (binario), o `OBSVMA COM1 1` (ASCII), documentados para UM980. Deben acompañarse de efemérides y metadatos adecuados a la conversión elegida. |
| Persistencia | `SAVECONFIG` solo después de aplicar y verificar; evitar escrituras repetidas. `MODE BASE TIME` puede guardar su resultado por sí mismo. |

COM1/COM2/COM3 son puertos del receptor, no los UART del ESP32. La conexión USB de esta carrier informó COM3; verificar COM2 cuando se cablee. Los periodos de salida RTCM/observaciones son independientes de los 10 Hz mínimos de solución y del refresco HTTP.

En versiones recientes del manual el promedio admite hasta 3600 s y distancia 0–10 m para reutilización de posición guardada; no interpretar ese segundo parámetro como precisión garantizada. No usar recetas de otros receptores con parámetros adicionales ni tratar 60 s de promedio autónomo como una coordenada centimétrica. El modo sin parámetros activa comportamiento automático; la interfaz no debe invocarlo como sustituto silencioso de datos faltantes.

Aplicación futura: comprobar UART y versión; detener publicaciones incompatibles; leer modo/configuración; validar plan; enviar una operación cada vez; comprobar ACK con timeout y lectura del estado efectivo; publicar RTCM solo con base preparada. Ante error parcial detener publicación y mostrar configuración incompleta. No anunciar éxito solo porque se escribieron bytes. Impedir modificar modo, altura o coordenadas durante una sesión de registro; detener y cerrar primero o implementar segmentación explícita con metadatos.

## Registro y postproceso

El objetivo es conservar observaciones de pseudodistancia, fase portadora, Doppler, calidad/señales y efemérides. Un archivo GGA/CSV de posiciones no sustituye datos crudos para PPK. Un archivo nativo Unicore no se convierte en RINEX cambiando su extensión.

Flujo de sesión:

1. Preparar nombre, función base/rover, tasa, modelo/número de antena, altura y método de medida, coordenadas/datum/época cuando corresponda.
2. Comprobar tarjeta montada, espacio mínimo, enlace y disponibilidad de observaciones. No exigir RTK FIX para grabar crudos; registrar la calidad real y cualquier falta de tiempo GNSS.
3. Iniciar de forma idempotente con identificador de solicitud/sesión y estado confirmado por el dispositivo. Guardar snapshot de configuración. Fecha GNSS y tiempos monotónicos separados.
4. Escribir en tarea separada mediante colas limitadas. Mostrar bytes, duración, tasa efectiva, huecos, desbordes, espacio restante y fallos. Una desconexión de app no detiene la grabación.
5. Detener: dejar de encolar para esa sesión, drenar, sincronizar y cerrar archivo; solo entonces marcar sesión cerrada. No apagar alimentación hasta terminar el cierre.
6. Exportar archivos cerrados por Wi-Fi con tamaño, hash y metadatos. Descarga por bloques/reanudación y control de acceso; no cargar un archivo entero en RAM. Mantener archivos parciales identificados para recuperación tras apagón.

Estados previstos: no disponible → lista → iniciando → grabando → cerrando → cerrada, con error recuperable/parcial. Retirada de tarjeta, disco lleno y pérdida de GNSS deben diferenciarse. Nunca sobrescribir sesiones existentes. Separar almacenamiento, catálogo, transferencia y conversión.

Exportaciones previstas: datos nativos + manifiesto; RINEX OBS/NAV después de validar un conversor con las señales del UM980; CSV de soluciones como producto distinto. Conversión y cálculo PPK inicialmente externos (Mac/app), no prometidos en el ESP32. Mantener originales, versión de conversor y advertencias de señales descartadas. La sesión necesita observaciones de base solapadas temporalmente para PPK relativo.

## Entrada, publicación y caster: roles distintos

Según BKG, NtripClient consume un flujo, NtripServer publica una fuente y NtripCaster recibe/distribuye flujos. Tanto cliente como publicador abren conexiones hacia el caster. El UM980 entrega/recibe RTCM; el ESP32 o la app implementan red y NTRIP.

### Entrada de correcciones (rover)

Configurar transporte (NTRIP por Wi-Fi o desde app BLE), hostname/IP, puerto, TLS, mountpoint, usuario y contraseña; GGA al caster solo cuando lo requiera el servicio y exista posición válida reciente. Mostrar resolución DNS, conexión, autenticación, RTCM válido, bytes/s, última trama y edad de correcciones informada por GNSS por separado. Evitar dos fuentes simultáneas no coordinadas.

### Publicación en caster externo (base)

Configurar dirección, puerto, versión NTRIP, TLS, mountpoint y credenciales de fuente; son independientes de las credenciales del rover. El ESP32 consume RTCM generado por el UM980 y lo sube al caster. Implementar negociación compatible v1/v2 según servicio, validación de certificado para TLS, timeout y reconexión con espera creciente. No confundir publicación con abrir un puerto público en el ESP32.

No retransmitir datos atrasados después de reconectar: delimitar tramas RTCM3, validar CRC24Q, mantener colas acotadas y descartar retraso excesivo con contadores. Cliente lento o caída de red no deben bloquear UART, registro ni otros clientes. Probar rechazo de credenciales, mountpoint ocupado/inexistente, fuente caída y cambios de IP.

### Caster propio en LAN

Dos despliegues previstos:

1. Caster local ligero en el ESP32, accesible por su AP o por su IP de la LAN. Un mountpoint de la propia base, autenticación, sourcetable y límite inicial propuesto de dos rovers. Capacidad real pendiente de pruebas de RAM/CPU, Wi-Fi y registro simultáneo. No presentarlo como sustituto de un caster de producción multiestación.
2. Caster propio externo en una Mac/PC/Raspberry Pi de la misma LAN. Referencia: BKG NtripCaster. El ESP32 publica hacia la IP LAN del servidor y los rovers se conectan a esa misma IP/mountpoint. `127.0.0.1` en el ESP32 apunta al propio ESP32, no a la Mac.

El puerto propuesto es 2101, configurable y separado del HTTP del panel. El caster integrado debe permitir seleccionar AP/LAN, limitar clientes, autenticar y mostrar URL/mountpoint sin contraseñas. En una LAN con conectividad directa no hace falta internet ni redirección WAN. Verificar aislamiento de clientes Wi-Fi/firewall local, IP estable y reconexión. Sin exposición pública automática, UPnP ni credenciales en QR/URL/exportaciones.

## Entregas y aceptación

1. Documentación y panel con capacidades explícitas, plan de base validable y exportable; es el alcance de esta entrega.
2. Gestor de comandos UM980 con lectura de estado, ACK, timeout y pruebas en banco; base conocida/promediada y perfil RTCM verificados con decodificador independiente.
3. microSD y sesiones crudas recuperables; exportación Wi-Fi real; validación de RINEX con conversor compatible.
4. Entrada NTRIP y publicador externo, probados contra caster de prueba propio.
5. Caster local, dos rovers y pruebas de clientes lentos, reconexión, huecos y carga concurrente.

La tasa de solución de al menos 10 Hz debe conservarse durante registro y correcciones. Medir throughput, picos de uso, pérdidas y antigüedad; no inferir capacidad por compilar o por obtener un FIX.

## Fuentes consultadas

- [Unicore, manual N4 R1.13: MODE, base, rover y observaciones](https://en.unicorecomm.com/uploads/file/Unicore%20Reference%20Commands%20Manual%20For%20N4%20High%20Precision%20Products_V2_EN_R1.13.pdf).
- [Unicore, manual N4 R1.4: OBSVM](https://en.unicorecomm.com/uploads/file/20241219/Unicore_Reference_Commands_Manual_For_N4_High_Precision_Products_V2_EN_R1.4.pdf).
- [Unicore FAQ: alturas y perfiles RTCM](https://www.unicorecomm.com/support/faq).
- [BKG: arquitectura NTRIP](https://igs.bkg.bund.de/ntrip/).
- [BKG: NtripCaster propio](https://igs.bkg.bund.de/ntrip/bkgcaster).
- [BKG: documentación del protocolo y sourcetable](https://igs.bkg.bund.de/root_ftp/NTRIP/documentation/NtripDocumentation.pdf).

## Avance posterior: banco USB y control BLE

El estado inicial de este documento corresponde a 0.3.0. La implementación 0.4.0 agrega grabación/catálogo/descarga y conversión OBS/NAV en la **Mac**, comandos confirmados del UM980, adaptador de base y NTRIP/caster de banco; ver [alcance y pruebas](usb-bench.md). microSD, NTRIP autónomo en ESP32 y precisión PPK siguen pendientes. BLE y OTA tienen [contrato propio](ble-protocol.md) y [procedimiento de actualización](firmware-updates.md).
