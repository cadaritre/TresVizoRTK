# Firmware actualizable y módulos de correcciones

## ESP32, GPS y módulos tienen firmware distinto

La actualización implementada corresponde a la aplicación del **Thing Plus ESP32-S3 WRL-24408 de 4 MB** y su panel embebido. No actualiza el UM980, radios ni bootloader; cada uno necesita procedimiento del fabricante y comprobación de modelo. No exponer un botón genérico que pueda enviar una imagen del ESP32 al GPS.

El panel ofrece selección de `firmware-signed.bin` y `manifest.json`, carga con progreso y restauración de la imagen anterior. USB JSON y HTTP comparten el controlador; el banco de la Mac lo retransmite al ESP32 real. BLE consulta estado pero no lleva imágenes.

## Particiones y validación

Se conservan NVS y dos particiones OTA de `0x1e0000` (1920 KiB) cada una. Se escribe únicamente la partición inactiva. Antes de activar: ID de hardware `tresvizo-thingplus-s3-4m-v1`, tamaño, cabecera ESP32-S3, descriptor de aplicación, SHA-256 del archivo, **firma del propietario** y validación de imagen de Espressif. No aceptar imágenes de flash completa ni `bootloader.bin`.

**Desde 0.8.0 la identidad de placa está dentro de la imagen firmada:** byte 320, campo de 48 bytes terminado en NUL, después de la identidad de versión. Se comprueba además del manifiesto antes de activar y al restaurar. Las imágenes de Tiny no son intercambiables con Thing Plus. Primera instalación de la nueva placa por USB; el pinout vigente está en [cableado](../hardware/wiring.md).

**Desde 0.7.13 la imagen va firmada.** El archivo que se sube es `firmware-signed.bin`: `firmware.bin` seguido de `TVZSIG01` y la firma ECDSA P-256 `r||s` sobre el SHA-256 de la imagen (72 bytes; `firmware/esp32/lib/protocol/src/signed_firmware.h`). A la flash solo va la imagen. En `finish`, tras el SHA-256 del archivo (integridad del transporte), el equipo comprueba la firma con la clave pública embebida (`firmware/esp32/include/firmware_signing_key.h`); sin firma o con una que no verifica, invalida la partición destino y no cambia el arranque. La clave privada es del propietario y vive fuera del repositorio; custodia, respaldo y firma en [`tools/firmware_signing/`](../tools/firmware_signing/README.md). Un actualizador por Internet seguiría necesitando decidir la distribución de las imágenes; la firma ya certifica quién las publicó. No se queman eFuses ni se activa Secure Boot: con acceso físico, el USB sigue cargando cualquier imagen.

`/api/update/rollback` solo restaura una imagen anterior que también exija firma (0.7.13 o posterior) **y cuya firma haya verificado este mismo equipo** (desde 0.7.14: registro en la NVS por partición, borrado antes de escribir y guardado solo tras verificar; `lib/protocol/src/verified_image.h`). Si no, 409 y hay que usar el USB. Volver a 0.7.12 o anterior reabriría la carga de firmware sin firma, y sin el registro un corte a media carga dejaría una imagen sin autenticar a la que volver.

El SDK/bootloader instalado tiene `CONFIG_BOOTLOADER_APP_ROLLBACK_ENABLE=1`. La aplicación confirma el arranque después de 5 s, con servidor HTTP iniciado y bucle atendiendo. Si una imagen pendiente reinicia antes de confirmarse, el bootloader puede regresar a la imagen anterior válida. La prueba saludable no equivale a validar cada sensor; no exigir posición GNSS para poder arrancar dentro de un edificio. La caída intencionada antes de confirmar debe ensayarse por separado. Recuperación final por USB si no queda una imagen arrancable.

Un upload interrumpido no cambia la partición de arranque. Caduca tras 30 s sin bloques. Se rechazan escrituras fuera de orden; repetir el último bloque idéntico es idempotente. Cambios de configuración/reinicio se bloquean durante la carga. No actualizar durante una medición; la programación de flash puede alterar tiempos.

## Paquetes

Desde la raíz:

```sh
~/.platformio/penv/bin/pio run -d firmware/esp32
~/.platformio/penv/bin/python tools/firmware_package.py
```

`pio run` deja `firmware-signed.bin` junto a `firmware.bin` si está la clave del propietario. Salida local ignorada por Git: `data/local/releases/<versión>/firmware-signed.bin` y `manifest.json` (tamaño y SHA-256 del archivo firmado). Se conserva esquema de configuración NVS v1. Las futuras migraciones deben leer la versión anterior, validar en memoria, escribir atómicamente y mantener compatibilidad con rollback; no borrar ajustes para resolver una migración.

Rutas: GET `/api/update` (con `image_authenticity: "owner_signed_ecdsa_p256"`, `signature_required` y `previous_image_signature_required`); POST `/api/update/begin` con `hardware_id,size,sha256` del archivo firmado; `/chunk` con `session,offset,data` base64 (hasta 576 bytes decodificados); `/finish`, `/abort` con `session`; `/rollback`. Desde 0.6.2 no existe clave de acceso: el token de sesión es lo único que ata los bloques a una carga concreta. Hasta 0.7.12 **la imagen no se verificaba contra ninguna firma** y quien alcanzara la red del equipo podía sustituir su firmware; desde 0.7.13 solo puede cargar lo que firmó el propietario. Firmware y API muestran versión y capacidades, no solo un número comercial.

## Módulos y radios

Los controladores se compilan en la imagen y se incorporan mediante OTA. No se cargan plugins ejecutables arbitrarios en tiempo de ejecución. Separar:

1. Transporte: BLE, TCP/NTRIP, UART/SPI de un radio.
2. Decodificador del protocolo del módulo: encapsulado, fragmentación y verificación según su manual.
3. Trama normalizada RTCM3 con CRC24Q.
4. Router de correcciones: fuente activa única, generación, antigüedad y colas acotadas.
5. Salida al UM980 por el controlador UART.

`correction_router` acepta actualmente `none` y `ble`; enum reserva `Ntrip` y `Radio`, pero sus controladores ESP32 se anuncian ausentes y no pueden seleccionarse. `GET/PUT /api/corrections/source` permite a la misma app configurar el controlador instalado. Añadir un radio no modifica la API de solución GNSS ni la lógica topográfica de la app.

No prometer compatibilidad con cualquier protocolo de radio: transparencias UART, formatos de fabricantes y sus licencias se verifican por modelo. Para un módulo nuevo documentar alimentación/niveles, GPIO, recursos compartidos, formato, tasa útil, límites de carga, reconexión y capacidad de actualización. Radiofrecuencia, modulación y encapsulado son distintos del formato RTCM que recibe el GPS.

## Referencias

- [Espressif: OTA, estados de imagen y rollback](https://docs.espressif.com/projects/esp-idf/en/v4.4.7/esp32s3/api-reference/system/ota.html).
- Código local del SDK Arduino-ESP32 2.0.17: `esp_ota_ops.h`, `sdkconfig.h` de ESP32-S3 y `BLESecurity`.
