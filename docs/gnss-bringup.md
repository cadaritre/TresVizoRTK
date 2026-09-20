# Primera adquisición GNSS

## Estado

**Actualización 2026-09-20:** el propietario confirmó TTL_TXD2 → GPIO18, TTL_RXD2 → GPIO17 y GND común, sin unir alimentación; cada placa se alimenta por su USB. Firmware 0.4.1 habilita UART2 a 115200 y se instaló por OTA con arranque confirmado y ajustes conservados. El UM980 confirmó `CONFIG COM2 115200` y `GPGGA COM2 0.1` enviados por COM3 USB. No se envió SAVECONFIG; la persistencia del perfil GNSS tras apagar sigue pendiente. La identificación eléctrica de la carrier a 3.3 V no se ha medido con instrumental.

El panel principal prioriza la adquisición UART del ESP32; la lectura USB directa a la Mac permanece separada como banco. La recepción de GGA confirma GPS→ESP32. No demuestra todavía el enlace de transmisión ESP32→GPS, ni RTCM real, ni precisión. Las secciones siguientes conservan el historial anterior, cuando UART estaba desactivada.

El receptor conectado a la Mac responde a `VERSIONA` como UM980, firmware `R4.10Build13504`, por `/dev/cu.usbserial-1110` (USB 1A86:7523). El puerto físico puede cambiar al reconectar. Respondió `devicename,COM3` a 115200 baudios. El ESP32 continúa conectado por separado; los datos USB del GPS no llegan al ESP32 por el hecho de compartir la Mac.

El receptor aceptó `GPGGA 0.1` en su puerto actual. No se envió `SAVECONFIG`. La captura inicial posterior contiene mensajes GGA sin hora ni posición: esto demuestra comunicación, pero no demuestra diez posiciones distintas por segundo ni RTK. Las capturas y la respuesta completa de versión se guardan en `captures/local/`, excluido de Git.

## Código

- `firmware/esp32/lib/gnss/src/nmea_gga.h`: parser incremental compartido por firmware y herramienta de banco. Memoria fija; checksum obligatorio; validación de coordenadas, calidad, hora, unidades y números. Resincroniza al recibir `$` y descarta líneas demasiado largas. Un mensaje válido sin fix sustituye la posición anterior por datos ausentes.
- `firmware/esp32/src/gnss_receiver.cpp`: tarea UART dedicada, independiente del refresco HTTP, con buffer de recepción de 8192 bytes y snapshot protegido. Registra errores UART y de parser. No envía comandos al GPS.
- La adquisición física está desactivada en el perfil predeterminado: solo se activa al definir conjuntamente `TRESVIZO_GNSS_RX`, `TRESVIZO_GNSS_TX` y `TRESVIZO_GNSS_BAUD`, después de comprobar conexiones y niveles. No conectar señales RS232 directamente al ESP32.
- `/api/status` incorpora los contadores GNSS. Con UART habilitada distingue espera, recepción y datos antiguos; después de 500 ms sin GGA válido omite la solución vigente. No interpreta el código de calidad como garantía de precisión.
- GGA proporciona UTC de hora del día, no fecha; se conserva separado del tiempo monotónico de llegada. Altitud MSL y separación geoidal permanecen separadas. El datum y el modelo de geoide del receptor necesitan verificación. No equivale a sincronización PPS ni a latencia absoluta medida.

## Prueba de software

Desde la raíz del repositorio:

```sh
c++ -std=c++17 -Wall -Wextra -Werror -fsanitize=address,undefined -I firmware/esp32/lib/gnss/src firmware/esp32/test/nmea_gga_test.cpp -o /tmp/tresvizo-gga-test
/tmp/tresvizo-gga-test
```

## Captura pasiva USB

```sh
c++ -std=c++17 -Wall -Wextra -Werror -I firmware/esp32/lib/gnss/src tools/gnss_probe.cpp -o /tmp/tresvizo-gnss-probe
mkdir -p captures/local
/tmp/tresvizo-gnss-probe /dev/cu.usbserial-1110 captures/local/um980-new-session.nmea
```

Verificar el puerto antes de ejecutar. La herramienta abre el puerto en exclusiva a 115200 8N1 durante 60 s y no transmite comandos. No sobrescribe archivos existentes; crea la captura con permisos 0600. Rechaza puertos `usbmodem` para evitar confundir la consola ESP32 con GNSS en este banco.

Muestra mensajes aceptados/rechazados, duplicados, discontinuidades, frecuencia de épocas UTC y de llegada de épocas distintas. La frecuencia se refiere al segmento temporal continuo actual. Sin UTC no calcula una frecuencia de posiciones. Antigüedad y máximo intervalo de llegada se refieren a la Mac y pueden incluir agrupación por USB; no prueban latencia GNSS absoluta. Si no se informó el número de satélites muestra -1. Código de salida 2 indica que no se decodificó ningún GGA; 1 señala un error de puerto/archivo.

## Pendiente de banco

- Antena con cielo visible, solución válida y comprobación sostenida de 10 épocas distintas/s.
- Confirmar niveles TTL de la carrier y cablear UART al ESP32. Verificar la tasa/configuración de COM2 independientemente de COM3.
- Validar pérdidas, interrupciones UART, caída de alimentación, carga concurrente HTTP/BLE y microSD.
- BLE, RTCM/NTRIP, observaciones crudas/RINEX e IMU no se implementan en esta etapa de adquisición GGA.

## Fuentes

- [Unicore: comandos y estructura GGA para productos N4](https://en.unicorecomm.com/uploads/file/Unicore%20Reference%20Commands%20Manual%20For%20N4%20High%20Precision%20Products_V2_EN_R1.13.pdf).
- [Unicore: salida NMEA y periodos en productos NebulasIV](https://www.unicorecomm.com/assets/Html/N4/N4-NTRIP.html).
- [SparkFun: verificación de UM980 mediante VERSIONA](https://docs.sparkfun.com/SparkFun_UM980_Triband_GNSS_RTK_Breakout/verification/).

## Resultado de la captura de 60 segundos

La captura `um980-gga-validated.nmea` contiene 600 líneas GGA completas sin fix, además de una línea inicial con ruido previo al encabezado. El parser resincronizó; el último reporte periódico registró 594 GGA aceptados, 0 rechazos y 0 desbordes antes del cierre. Todos los GGA carecían de UTC y posición: hay salida de mensajes cercana a 10 Hz, pero aún no se han validado 10 soluciones/s.

Las pruebas del parser pasaron con AddressSanitizer y UndefinedBehaviorSanitizer. Compilaron el perfil predeterminado y la variante UART habilitada (solo compilación, sin cargar esta última). No se cargó nuevo firmware al ESP32 durante esta sesión. La clave Wi-Fi sigue pendiente del cambio solicitado anteriormente.


### Captura posterior con UTC

`um980-sky-epochs.nmea` y su archivo de métricas muestran 10.00 Hz de épocas UTC distintas y 10.00 Hz de llegada en el segmento continuo final. Sin duplicados; una discontinuidad inicial de UTC; máximo intervalo de llegada observado 102 ms. La calidad continuó en 0 con cero satélites usados. No se interpreta como una solución topográfica a 10 Hz. Después de esta prueba se cargó firmware 0.2.0 y se aplicó el cambio de clave solicitado; la mención anterior de firmware sin cargar corresponde únicamente a la primera sesión.
