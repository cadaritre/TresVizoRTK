# Entorno de desarrollo

El desarrollo inicial se realiza en macOS con VS Code y la extensión PlatformIO ya instalados. La primera versión usa PlatformIO Core 6.2.0, plataforma Espressif32 6.12.0, Arduino-ESP32 2.0.17 y ArduinoJson 7.4.2. Las dependencias se declaran en `firmware/esp32/platformio.ini`.

El chip conectado por USB reportó 4 MB de flash y 2 MB de PSRAM. Se eligió un perfil genérico ESP32-S3 con flash de 4 MB, DIO a 80 MHz y PSRAM desactivada. Esta selección no asigna GPIO externos ni supone que la carrier sea DevKitC. El primer arranque y las comprobaciones se documentan en [validación](firmware-validation.md).

## Flujo inicial

1. Abrir `firmware/esp32/` como proyecto de PlatformIO en VS Code.
2. Compilar con `pio run` y seleccionar el puerto detectado antes de cargar.
3. Detener monitores o el puente USB antes de una carga o prueba que requiera el puerto.
4. Usar `tools/usb_console.py` para consultar el instrumento o abrir el panel en la Mac.
5. Ejecutar las pruebas adecuadas y actualizar el estado con la evidencia obtenida.

Los comandos completos, recuperación de acceso Wi-Fi y límites del prototipo están en el [README del firmware](../firmware/esp32/README.md). El respaldo previo al primer flash está en `logs/local/`, ignorado por Git.

El framework de la app móvil, CAD y herramientas de diseño electrónico siguen pendientes. La identificación de GPIO externos requiere las revisiones reales y manuales correspondientes.

## Prácticas de desarrollo

- Mantener pequeños y enfocados los cambios.
- Separar controladores de hardware, lógica del instrumento y protocolo de la app.
- Tratar las entradas externas y los mensajes GNSS como datos que pueden ser incompletos, tardíos o corruptos.
- Registrar unidades, marcos de coordenadas, referencias de altura y escalas temporales en interfaces y archivos.
- Diseñar pruebas de desconexión, pérdida de RTCM, reinicio, archivos incompletos y falta de espacio.
- Usar únicamente fixtures pequeños y anonimizados en `tests/fixtures/`.
- Guardar capturas de campo, logs voluminosos o datos sensibles en directorios locales ignorados, no en el historial.
- No almacenar credenciales NTRIP, redes Wi-Fi, tokens ni datos de clientes en el repositorio.

## Evidencia y validación

Cada cambio futuro debe indicar qué comprobaciones se realizaron y qué quedó pendiente. Una compilación no demuestra funcionamiento eléctrico; una comunicación no demuestra sincronización; una solución FIX no demuestra precisión. Los resultados de campo deberán incluir método, referencia, condiciones y datos suficientes para repetición.


La preparación de GNSS por USB, parser compartido, compilación de pruebas y captura pasiva se describe en [primera adquisición GNSS](gnss-bringup.md).


Desde 0.5.0 se habilita PSRAM Quad y se comprueba memoria en la placa. UART GPIO18/17 habilitada desde 0.4.1. Las menciones iniciales a interfaces desactivadas corresponden al primer arranque; ver [servicios actuales](esp32-services.md).
