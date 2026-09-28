# Meridian3

El **Meridian3** es el receptor sencillo de TresVizo: **ESP32-S3 + UM980 + un power bank
externo por USB-C**. El **MeridianV** sigue siendo el producto completo que se está
construyendo (microSD, radio, IMU, batería integrada, puerto auxiliar) y no cambia en nada.
Decisión del propietario del 28-09-2026.

## Qué hace y qué no

| | MeridianV | Meridian3 |
| --- | --- | --- |
| Rover RTK (NTRIP del equipo o puente del teléfono por Bluetooth) | Sí | Sí |
| Base (promedio, base conocida, caster/NTRIP por Wi-Fi) | Sí | Sí, **sin grabar** |
| Wi-Fi propio y panel web | Sí | Sí |
| Actualización OTA firmada | Sí | Sí (su propia imagen) |
| Grabación en microSD (registro, PPK en tarjeta) | En el producto | **No** |
| IMU / inclinación | En el producto | **No** |
| Correcciones por radio | En el producto | **No** |
| Batería integrada y su estado | En el producto | **No**: power bank externo |
| Puerto auxiliar | En el producto | **No** |

«En el producto» no quiere decir integrado: lo que falta de integrar en el MeridianV lo dice
cada subsistema en `/api/status`.

## Un solo firmware, dos perfiles

Mismo código y misma placa (ESP32-S3-Tiny, ESP32-S3FH4R2). El producto se elige al compilar:

```bash
~/.platformio/penv/bin/pio run -e esp32s3_usb   # MeridianV (el de siempre)
~/.platformio/penv/bin/pio run -e meridian3     # Meridian3
```

Cada uno deja su `firmware-signed.bin` en `.pio/build/<entorno>/` (firmado con la misma clave
del propietario, `tools/firmware_signing/README.md`). Para empaquetar:
`tools/firmware_package.py --env meridian3`.

La identidad vive en `firmware/esp32/lib/protocol/src/product.h` (prueba en
`test/product_test.cpp`). Los identificadores son distintos a propósito:

| | MeridianV | Meridian3 |
| --- | --- | --- |
| Nombre del equipo, red Wi-Fi y anuncio Bluetooth | `MeridianV` | `Meridian3` |
| Nombre en la red local | `meridianv.local` | `meridian3.local` |
| `hardware_id` de la OTA | `tresvizo-esp32s3-4m-v1` | `tresvizo-meridian3-esp32s3-4m-v1` |

Por el `hardware_id`, una imagen de un producto **no se instala en el otro**. El servicio
Bluetooth (`a04c0001`), el protocolo (v3) y la API son los mismos: las apps hablan igual con
los dos.

## Contrato con las apps (desde 0.7.14)

`GET /api/status` añade:

```json
{
  "product": "meridian3",
  "product_name": "Meridian3",
  "hardware_features": { "microsd": false, "imu": false, "radio": false, "battery": false, "aux_port": false }
}
```

- `product` es la clave interna (`meridianv` | `meridian3`); `product_name`, lo que se muestra.
- `hardware_features` dice qué lleva el producto. En el MeridianV todo es `true`.
- Un firmware sin `product` es un MeridianV: todos los equipos anteriores lo son.
- En un Meridian3, `subsystems.imu.state` y `subsystems.microsd.state` son `"not_present"`,
  `/api/recording…` responde 404 y `/api/operations` da la grabación como `not_present`.
- Las apps esconden por completo lo que el equipo no lleva; el panel web esconde
  Registro / PPK.

## Hardware y carcasa

- Alimentación: power bank externo por el USB-C de la tapa. Cómo llega la alimentación al
  UM980 desde esa única entrada está en `mechanical/meridian3/README.md` y en
  `hardware/`; lo que no esté comprobado va marcado «por confirmar».
- Carcasa: `mechanical/meridian3/`, **Ø54 mm como V2** con los arreglos de V2.1, sin IMU,
  batería ni tapa del puerto auxiliar; el panel solo tiene la abertura del USB-C. **No cabe en
  los 106.9 mm de alto de V2**: con un latiguillo coaxial entre la antena y el carrier queda en
  **150.6 mm**. Si la antena HA-901A trae SMA macho y se enrosca directo al carrier, bajaría a
  ~105.6 mm (sin modelar). Veredicto, pila de alturas y dudas en
  `mechanical/meridian3/README.md`.
- El USB-C no está en la ESP32-S3-Tiny sino en su Tiny-Adapter (unida por un FPC): la
  Tiny-Adapter va atornillada a una repisa de la tapa del panel, alineada con la abertura.
