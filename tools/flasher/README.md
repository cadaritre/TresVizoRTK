# Cargador de firmware por USB

Ventana para cargar el firmware del **MeridianV** o del **Meridian3** por el cable USB, sin
abrir la terminal ni recordar direcciones. Por dentro hace lo mismo que
`pio run -t upload`: el esptool de PlatformIO, las mismas direcciones y el mismo modo de
flash.

## Abrirlo

- Doble clic en **`Cargar firmware.command`** (macOS). La primera vez, si macOS lo bloquea:
  clic derecho › Abrir.
- O desde la terminal: `python3 tools/flasher/meridian_flasher.py` (Python de python.org,
  que trae tkinter).

Necesita PlatformIO instalado (`~/.platformio`), que es con lo que ya se compila el firmware.
Sin PlatformIO sirve cualquier Python con `pip install esptool pyserial`.

## Pasos

1. **Modelo**: MeridianV o Meridian3.
2. **Imagen**: `firmware-signed.bin` (o `firmware.bin`) de `firmware/esp32/.pio/build/<modelo>/`
   o de un paquete de `tools/firmware_package.py`. La ventana dice de qué modelo es, su
   versión y si trae la firma del propietario.
3. **Puerto**: el del equipo conectado por USB («Buscar» los vuelve a leer).
4. **Cargar firmware**.

## Qué comprueba

- Que la imagen sea de aplicación para ESP32-S3 (no un bootloader ni un volcado entero).
- **Que la imagen sea del modelo elegido**, por su `hardware_id` (el de cada producto está en
  `firmware/esp32/lib/protocol/src/product.h`). Si no coincide, no deja cargar.
- Si trae firma, que sea válida con la clave pública embebida en el firmware. Una firma
  inválida bloquea la carga. Por USB también se puede cargar una imagen sin firma (el cable
  es acceso físico); la OTA por Wi-Fi o por las apps, no.
- Antes de cargar lee el equipo conectado. **Si es de otro modelo, pregunta antes de
  convertirlo** (cambian su nombre, su red Wi-Fi y su nombre en la red local).
- Después de cargar espera a que arranque, lo vuelve a leer y confirma modelo y versión.

## Actualización o instalación completa

- **Actualización** (por omisión): escribe la aplicación en `0x10000` y `boot_app0` en
  `0xe000`, que devuelve el arranque a esa partición. Sin `boot_app0`, un equipo que se
  actualizó antes por OTA seguiría arrancando la otra partición.
- **Instalación completa** (placa nueva): además `bootloader.bin` en `0x0` y
  `partitions.bin` en `0x8000`, tomados de junto a la imagen o de la compilación de ese modelo.
- Ninguna de las dos borra los ajustes guardados en el equipo (red Wi-Fi, perfiles NTRIP,
  contraseña del AP). A la flash va la imagen sin los 72 bytes de la firma, igual que en una OTA.

## Pruebas

`python3 -m unittest tools/flasher/test_meridian_flasher.py` — reconoce el modelo y la
versión de imágenes de prueba y de las compiladas por `pio run`, rechaza lo que no es una
imagen de aplicación, arma la orden de esptool con las direcciones de PlatformIO y lee el
progreso.
