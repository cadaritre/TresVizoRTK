# Banco BLE del Meridian V en la Mac

Mide el enlace Bluetooth del equipo desde una Mac, con CoreBluetooth, sin instalar nada
(hace falta Xcode). Es lo que se usó el 27-09-2026 para validar el firmware 0.7.11; cifras en
[`docs/connectivity/ACCEPTANCE_TESTS.md`](../../docs/connectivity/ACCEPTANCE_TESTS.md).

```bash
./build.sh
open -W -n MeridianBench.app --args /tmp/banco.log 20 burst 5000
cat /tmp/banco.log
```

- `burst <bytes>`: una época RTCM de ese tamaño cada segundo, como un caster.
- `sat`: RTCM tan rápido como lo acepte la pila (satura a propósito).
- `none`: solo órdenes y salud.

Cada 250 ms manda `GET /api/ble` y apunta su latencia; cuenta la salud y sus intervalos; al
final pide el estado BLE y la memoria del equipo. Las tramas son RTCM3 de tipo 4095 con CRC
válido (el UM980 las ignora) y **no** cambia la fuente de correcciones del equipo.

La primera vez macOS pide permiso de Bluetooth para «MeridianBench». Con firmware 0.7.11 o
anterior, una Mac que se conectó antes a otro firmware ve la tabla GATT vieja (sin salud y con
la RTCM solo con respuesta); desde 0.7.12 el equipo cambia de dirección con la tabla y eso ya
no pasa: ver `KNOWN_LIMITATIONS.md`. El banco en Python con más escenarios está en
`tools/ble_bench/`.
