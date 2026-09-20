> D0 usa KiCad directamente. Las particiones atopile siguientes quedan como antecedente; no hay build atopile realizado. Ver [DESIGN_D0.md](../DESIGN_D0.md).

# Fuentes eléctricas futuras

Sin esquemático en P1. Después de aprobar arquitectura y comprobar herramientas, partición propuesta: `main.ato`, `usb.ato`, `charger.ato`, `power_path.ato`, `regulators.ato`, `soft_power.ato`, `fuel_gauge.ato`, `usb_native.ato`, `leds.ato`, `connectors.ato`.

`power_path` puede ser interfaz del propio charger, no un segundo circuito duplicado. Mantener lock/versiones y huellas rastreables. No hay archivos .ato vacíos que simulen diseño compilable.

`usb_native.ato` cubrirá ESD, desconexión de datos, VBUS sensing y enlace FPC, sin incluir el ESP32 externo. `usb_uart.ato` sólo si una contingencia se justifica y aprueba.
