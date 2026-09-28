# Firma del firmware para la OTA

Desde 0.7.13 el Meridian V solo instala por OTA (panel, apps o
`tools/firmware_upload.py`) un firmware **firmado por el propietario**. El
archivo que se da a las apps y al panel es **`firmware-signed.bin`**, nunca
`firmware.bin`: este último lo rechaza el equipo con «El firmware no trae la
firma del propietario».

Formato: `firmware.bin` seguido de 72 bytes, `TVZSIG01` más la firma ECDSA P-256
en bruto `r||s` sobre el SHA-256 de `firmware.bin`. Contrato completo en
`firmware/esp32/lib/protocol/src/signed_firmware.h`.

## La clave

- **Privada**: `~/.tresvizo/firmware-signing/private.pem` en la Mac del
  propietario, o la ruta que diga `TRESVIZO_SIGNING_KEY`. **Nunca** dentro del
  repositorio (`*.pem` está en `.gitignore`), ni en un mensaje, ni en una copia
  sin cifrar en la nube.
- **Pública**: embebida en el firmware, `firmware/esp32/include/firmware_signing_key.h`.

**Hay que respaldar la clave privada** (p. ej. en el gestor de contraseñas o en
un medio cifrado fuera de la Mac). Si se pierde, ningún equipo en campo vuelve a
aceptar firmware por OTA y solo queda cargar cada uno **por cable USB**
(`pio run -t upload`), con un firmware que traiga una clave pública nueva.

## Compilar

`pio run` en `firmware/esp32` deja `firmware-signed.bin` junto a `firmware.bin`
(`.pio/build/esp32s3_usb/`) si encuentra la clave, y lo comprueba en el acto con
la clave pública embebida. Sin clave, avisa y la compilación sigue: `firmware.bin`
vale para cargar por USB. Si hay clave pero no es la del equipo, la compilación
falla: ese archivo no lo instalaría ningún Meridian V.

La firma solo se hace cuando `firmware.bin` se regenera. Si la clave se instaló
después de compilar, basta borrar `firmware.bin` y volver a compilar, o firmar a
mano.

Si la clave tiene contraseña, `openssl` la pide en la terminal.

## Firmar y comprobar a mano

```sh
python3 tools/firmware_signing/sign_firmware.py firmware.bin firmware-signed.bin
python3 tools/firmware_signing/sign_firmware.py firmware.bin firmware-signed.bin --key RUTA
python3 tools/firmware_signing/sign_firmware.py --verify firmware-signed.bin
python3 tools/firmware_signing/sign_firmware.py --verify firmware-signed.bin --pubkey public.pem
```

`--verify` sin `--pubkey` usa la clave pública embebida en el firmware: lo mismo
que comprobará el equipo. Solo biblioteca estándar de Python y el `openssl` del
sistema (OpenSSL o LibreSSL; otro con `OPENSSL=RUTA`). El script no lee la clave
privada: le pasa la ruta a `openssl`.

Para probar sin la clave real, una desechable **fuera del repositorio**:

```sh
openssl ecparam -name prime256v1 -genkey -noout -out /tmp/prueba.pem
openssl ec -in /tmp/prueba.pem -pubout -out /tmp/prueba-pub.pem
python3 tools/firmware_signing/sign_firmware.py firmware.bin /tmp/firmado.bin --key /tmp/prueba.pem --pubkey /tmp/prueba-pub.pem
```

Un archivo firmado así no lo acepta ningún equipo: sirve para probar el formato.

## Paquete para el panel

`tools/firmware_package.py` copia `firmware-signed.bin` a
`data/local/releases/<versión>/` con su `manifest.json` (tamaño y SHA-256 del
archivo firmado), que es lo que pide el panel web.
