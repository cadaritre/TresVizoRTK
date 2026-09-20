# Fuentes eléctricas futuras

Sin esquemático en P0. Después de aprobar arquitectura y comprobar herramientas, partición propuesta: `main.ato`, `usb.ato`, `charger.ato`, `power_path.ato`, `regulators.ato`, `soft_power.ato`, `fuel_gauge.ato`, `usb_uart.ato`, `leds.ato`, `connectors.ato`.

`power_path` puede ser interfaz del propio charger, no un segundo circuito duplicado. Mantener lock/versiones y huellas rastreables. No hay archivos .ato vacíos que simulen diseño compilable.
