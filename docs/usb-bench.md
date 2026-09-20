# Banco GNSS por USB en la Mac

El banco permite avanzar sin conectar GPS–ESP32. Mantiene dueños seriales independientes: ESP32 JSON y UM980 COM3 a 115200. La adquisición no depende del navegador. El panel muestra explícitamente `source: mac_usb`; no altera ni simula el estado UART del ESP32.

## Arranque

```sh
~/.platformio/penv/bin/python tools/usb_console.py serve --gnss-port /dev/cu.usbserial-1110
```

Abrir `http://127.0.0.1:8765`. Cerrar otros monitores del GPS antes de arrancar. No hay exposición LAN del panel de banco. La dirección puede cambiar al reconectar USB; `pio device list` permite identificar CH340 VID:PID 1A86:7523.

### Resumen

Posición GGA, satélites usados, HDOP, edad, calidad, GST y señales GSV. Contar señales por separado de satélites. GST solo se asocia a GGA cuando coinciden sus épocas; campos ausentes no son cero. Hora UTC del día y llegada monotónica separadas. Caducidad de solución 500 ms y de ciclos GSV 3 s. La lista de señales se actualiza a 1 Hz; la API de banco devuelve las últimas épocas desde una secuencia y conserva hasta 200 GGA. El panel consulta aproximadamente cada 100 ms, sin garantía de tiempo real del navegador; la tasa calculada corresponde a épocas GNSS distintas, no refrescos de pantalla.

El demultiplexor separa NMEA/control, RTCM3 y Unicore binario antes de interpretar líneas. Valida XOR NMEA, XOR de control Unicore (incluye `$`/`#`), CRC24Q RTCM y CRC32 nativo. Limita líneas a 8192 bytes, paquetes nativos a 16384 y conserva contadores. Las unidades y alturas no se transforman implícitamente.

### Comandos y base

Comandos predefinidos, sin consola arbitraria: consultar MODE; perfil GGA/GST/RMC 10 Hz y GSV 1 Hz; rover topográfico; observaciones/efemérides; perfil RTCM de base. Una operación a la vez, ACK asociado al comando exacto y timeout. Timeout implica resultado incierto; no reenviar mutaciones automáticamente.

Base conocida: plan validado nuevamente por el firmware, solo WGS84 en este adaptador; calcula ARP, configura UNDULATION=0, aplica MODE BASE y verifica modo y GGA contra coordenadas/altura solicitadas. No transforma realizaciones/épocas de WGS84. La ejecución con coordenadas de base reales aún debe probarse. Ante aplicación parcial se informa error y se conserva el detalle, sin anunciar base preparada.

Promedio: MODE BASE ID TIME segundos distancia. ACK y modo no son una coordenada convergida; estado `averaging`. El receptor puede guardar la posición por su cuenta. No se envía SAVECONFIG. Al solicitar rover se configura UNDULATION AUTO explícitamente. No cambiar modo durante grabación o transporte de correcciones activo.

### Sesiones y RINEX

Las sesiones actuales se guardan **en la Mac**, `captures/local/sessions/<id>` ignorado por Git, con permisos privados. Cola de 256 bloques, escritura separada, flush/fsync periódico, cierre final, tamaño, SHA-256, contadores y manifiesto. Archivo `.part` si el proceso se interrumpe; se conserva y se anuncia interrumpido. Sesiones activas no se descargan. Descargas cerradas por bloques de 64 KiB y HTTP Range.

`Activar observaciones y efemérides` habilita OBSVMB a 1 Hz y GPSEPHB/GLOEPHB/GALEPHB/BDSEPHB/BD3EPHB cada 30 s en COM3. La solución GGA continúa a 10 Hz. No confundir la frecuencia de observación del perfil inicial con la frecuencia de solución. El archivo de flujo conserva bytes originales; registrar NMEA solo no sirve para PPK.

Se compiló RTKLIB demo5 b34L en macOS desde [el repositorio del proyecto](https://github.com/rtklibexplorer/RTKLIB), commit `75a2e56275485b21a67bd35bc94bbeb8936e1a74`. Ejecutable y licencia completos en `.cache/rtklib/`, ignorados por Git. Compilación en `app/consapp/convbin/gcc` con:

```sh
make -j4 CFLAGS='-std=c99 -O2 -include stdio.h -I../../../../src -DTRACE -DENAGLO -DENAQZS -DENAGAL -DENACMP -DENAIRN -DNFREQ=4 -DNEXOBS=3'
```

`-include stdio.h` resuelve una declaración ausente detectada por Clang; no se modifica la fuente externa. Copiar `convbin`, `license.txt` y un `build.json` con el commit/opciones a `.cache/rtklib/`. El panel lanza conversión en segundo plano: `convbin -r unicore -v 3.04`, genera OBS/NAV y exige cabeceras y registros presentes antes de ofrecer descarga.

**Límites:** metadatos de antena/altura todavía no confirmados; no usar ceros predeterminados del conversor como una medición de altura. El decodificador revisado declara BD3EPH pero no lo despacha en su switch; conservar originales y auditar cobertura antes de exigir todas las señales. La conversión lograda no valida pérdidas de fase, precisión ni un cálculo PPK. Inicialmente OBS/NAV son archivos de banco, con ese estado en el manifiesto. No ejecutamos un ajuste PPK sin datos de base solapados.

### NTRIP de banco

Implementación inicial NTRIP v1, cliente (entrada) y publicador SOURCE, con TLS opcional y verificación de certificados del sistema. Sin bypass de certificados. No envía GGA; casters VRS que la exijan necesitan ampliar ese flujo. Chunked y negociación NTRIP v2 se rechazan explícitamente, no se anuncian compatibles. Credenciales solo en memoria, nunca en catálogo/estado/exportaciones.

Caster local en la Mac: una fuente seleccionada (GPS USB en base o publicador externo), un mountpoint y dos rovers. Autenticación, sourcetable y límites de conexiones/colas. Default solo loopback; opción LAN escucha 0.0.0.0 sin modificar router. Usar la IP LAN de la Mac desde otros equipos. TCP local sin TLS: destinado a red privada de confianza. Este controlador **no está ejecutándose dentro del ESP32**.

RTCM con CRC incorrecto se descarta; colas de publicación y clientes limitadas, mensajes de más de 2 s descartados, reconexión con espera creciente. No mezclar fuente externa con el GPS local. Las pruebas de loopback utilizan fixtures RTCM y no inyectan correcciones ficticias al receptor real.

## Validación reproducible

- `python tests/gnss_bench_test.py`: checksum, coordenadas, ceros válidos, épocas duplicadas, reloj, pérdida de fix, GSV completo/caducidad, GST y cierre/recuperación.
- `python tests/ntrip_bench_test.py`: socket real de loopback, fuente, dos rovers, autenticación, límite de clientes, cliente/publicador y CRC.
- `tests/gnss_panel_test.js`: ocultar posición antigua y mantener referencias.
- Prueba real de captura: 393285 bytes, cero pérdidas de cola; 105 mensajes OBSVM y efemérides con CRC nativo válido. Conversión produjo 105 épocas OBS y 35 registros NAV. Hubo líneas NMEA dañadas aisladas, rechazadas; no confundir pérdidas de cola con integridad perfecta del receptor/enlace.

El propietario trasladó el GPS al interior durante el trabajo. Ausencia de solución válida es esperada y no se presenta como fallo del lector.

Fuentes de comandos y estructuras: [manual Unicore N4 R1.6](https://en.unicore.com/uploads/file/Unicore%20Reference%20Commands%20Manual%20For%20N4%20High%20Precision%20Products_V2_EN_R1.6.pdf), código oficial de [RTKLIB demo5](https://github.com/rtklibexplorer/RTKLIB), [BKG NTRIP](https://igs.bkg.bund.de/ntrip/).
