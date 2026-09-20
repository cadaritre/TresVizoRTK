# Conexión y contrato de firmware — Rev A

No se asignan GPIO de aplicación de la Tiny: siguen bajo control de su firmware/cableado existente. Los números siguientes pertenecen a **nuestra placa**, no al orden de pines de la Tiny. Tierra de señales es GND, no CELL_N antes del protector.

| Conector | Contactos y función |
| --- | --- |
| J1 USB-C | Host 5 V, D+/D− nativos y CC1/CC2; sin PD |
| J2 batería, JST PH 2 | 1=CELL_P (+), 2=CELL_N (−). Comprobar polaridad del cable comprado |
| J3 NTC, JST SH 2 | 1=BAT_NTC, 2=GND. Semitec 103AT-2 externo en contacto térmico con la celda |
| J4 GNSS, JST PH 2 | 1=SYSTEM_5V, 2=GND |
| J5 FPC candidato DNP | 1=GND, 2=SYSTEM_5V, 3=RUN, 4=BOOT, 5=GND, 6=D+, 7=D−, 8=GND |

J5 sigue el lado adaptador del plano oficial como **candidato**, no prueba el cable ni la revisión N8R8. Conductor/contacto, cara de contacto y reversión extremo-a-extremo deben comprobarse por continuidad antes de montarlo. No conectar alimentación basándose sólo en que ambas placas dicen Tiny. En servicio se puede comprobar la interfaz en pads, con cableado apropiado y alimentación limitada; no se certifica USB sobre cables arbitrarios.

## J6 — auxiliar JST SH 14, señales a 3.3 V

| Pin | Señal | Dirección respecto de Power Board | Uso |
| --- | --- | --- | --- |
| 1 | GND | — | Retorno |
| 2 | TINY_3V3 | Entrada | Referencia/alimentación de interfaces desde la Tiny; no alimenta el ESP |
| 3 | POWER_HOLD | Entrada | Alto mantiene ON; pull-down 100 kΩ |
| 4 | POWER_REQUEST_N | Salida open-drain | Petición de apagado; pull-up al dominio Tiny |
| 5 | I2C_SDA | Bidireccional | Gauge; pull-up 4.7 kΩ |
| 6 | I2C_SCL | Entrada | Gauge; pull-up 4.7 kΩ |
| 7 | BATTERY_ALERT_N | Salida open-drain | Alerta gauge; pull-up 47 kΩ |
| 8 | USB_VBUS_VALID | Salida | Host presente; nunca 5 V sobre GPIO |
| 9 | USB_SUSPEND | Entrada | Alto corta rama de carga en fuente sin anuncio CC alto |
| 10 | RGB_R | Entrada | Alto enciende rojo |
| 11 | RGB_G | Entrada | Alto enciende verde |
| 12 | RGB_B | Entrada | Alto enciende azul |
| 13 | GND | — | Retorno |
| 14 | USB_FAULT_LOGIC_N | Salida | Estado de fallo del interruptor de entrada, adaptado a dominio Tiny |

Tres LEDs discretos R/G/B permiten una ventana/luz común; no se añadió un controlador LED ni una MCU. LED1 de carga depende del charger y no del ESP. UART/PPS entre GNSS y ESP siguen fuera de esta placa.

## Secuencia de firmware

1. Configurar HOLD alto al principio del arranque, objetivo <2 s. No esperar a SD, GNSS, Wi-Fi o interfaz de usuario. La ventana de respaldo de ~5.7 s es nominal y varía.
2. Atender flanco bajo de POWER_REQUEST_N y confirmar estado del botón. Guardar estado, vaciar buffers/cerrar microSD y bajar HOLD. No bloquear indefinidamente el cierre; el long press corta independientemente.
3. Dejar RGB y USB_SUSPEND definidos, con sus pull-downs de placa durante reset. En suspend de USB legacy elevar USB_SUSPEND y recuperar al reanudar; verificar el mecanismo real del stack seleccionado.
4. Leer gauge sólo con dominio Tiny activo. MAX17048 usa dirección I2C de 7 bits 0x36; SOC/alerta y compensación se configuran según su hoja de datos. Un PACK_P válido no prueba batería presente. No emitir porcentaje válido con celda ausente.
5. Para USB-OTG/TinyUSB aplicar `self_powered=true` y `vbus_monitor_io` al GPIO conectado a J6.8. USB Serial/JTAG hardware y boot ROM son distintos; no asumir que esos ajustes cambian sus descriptores.

No se modificó ni probó firmware del receptor en esta tarea. La desconexión hardware de datos funciona independientemente de esas configuraciones por diseño; cumplimiento USB y suspend requieren ensayos.

## Servicio

JP1 PROGRAM_MODE normalmente abierto. Cerrarlo temporalmente, conectar USB válido y encender mediante SW1 permite detener el ESP en JTAG/flashear sin que venza HOLD. Reabrir al terminar. Con JP1 cerrado el apagado sólo por firmware no es efectivo mientras haya USB; long press/UVLO sí.

JP2 une RUN/RESET a GND y JP3 une BOOT a GND. Para recuperación ROM: BOOT bajo, pulsar/resetear RUN y soltar después de iniciar download, tras verificar señales de la Tiny concreta. No son botones exteriores adicionales. No quemar eFuses para probar.

| Punto | Red |
| --- | --- |
| TP1 | GND |
| TP2 | PACK_P |
| TP3 | SYSTEM_POWER |
| TP4 | SYSTEM_5V |
| TP5 | AON_3V0 |
| TP6 | USB_VBUS |
| TP7 | BOOST_EN |
| TP8 | KILL_SAFE |
| TP9 / TP10 | D+ / D− del lado Tiny |

HOLD, REQUEST, I2C, alerta y sensing son accesibles en J6. PGOOD del charger está en U10.7/R14; CHG en U10.9/LED1. Usar sonda de baja capacitancia en USB y retorno corto en la medida del boost.
