> Actualización D0, 20-09-2026: el propietario autoriza iniciar esquemático y pide compacidad; mecánica se adaptará después. Las restricciones previas de aprobación/carcasa no bloquean el inicio. Ver [DESIGN_D0.md](DESIGN_D0.md).

# Requisitos P1

| ID | Requisito | Criterio de aceptación / evidencia pendiente |
| --- | --- | --- |
| S01 | Una placa de alimentación e interfaz; módulos actuales externos | BOM sin ESP32, UM980, BMI088, microSD, RF o antena integrados. GNSS UART/PPS directo al ESP32. |
| M01 | Case A4 autoritativo | Fit check con sólidos actuales, plugs, cables, acceso y extracción. Ningún desplazamiento automático. |
| M02 | Cotas desconocidas = null/TBD | No exportar placa ficticia ni considerar ausencia de geometría como fit aprobado. |
| U01 | Un USB-C 5 V sink con datos USB 2.0 | CC1/CC2 independientes, Rd correcto, ambas orientaciones, cables A-C/C-C, protección ESD y VBUS, sin backfeed. |
| U02 | No exceder corriente permitida | Consumo total: sistema, carga, detector y lógica. Probar pre-enumeración, configurado, suspendido, Rp default/1.5/3 A y fuente débil. |
| B01 | LiPo 1S nominal 3.7 V, objetivo 5000 mAh, carga típica 4.2 V | Confirmar ficha de celda antes de fijar tensión, corriente, NTC, temporizadores y protección. |
| B02 | Power-path real | Probar seis estados A–F de ARCHITECTURE.md. Carga no confundida con corriente del sistema. |
| B03 | Descarga excesiva y fallos | Aviso temprano para cierre de SD, UVLO hardware con histéresis y protección final de pack. Umbrales TBD según batería. |
| P01 | Tensiones según placas reales | POWER_BUDGET con evidencia; medir ripple, caída de cables, transitorios Wi-Fi/SD/GNSS y tolerancias. |
| P02 | Un pulsador momentáneo | Encendido temporal, POWER_HOLD, petición de apagado, cierre limpio, liberación y corte real. |
| P03 | Long press ~8–10 s por hardware | Cortar con ESP congelado, HOLD atascado y USB presente. Medir tolerancias y no rearrancar hasta soltar/rearmar. |
| P04 | Bajo consumo OFF | Objetivo de ingeniería inicial <100 µA en batería, por aprobar; medir total, no sólo el controlador. Sin LED permanente en batería. |
| D01 | USB nativo hacia Tiny-N8R8 externa; sustituir Tiny-Adapter | ESD + desconexión USB + FPC verificado. Flashing, CDC/JTAG/OpenOCD, recuperación BOOT/RUN. Sin CP2102N en P1. |
| D02 | Evitar alimentación parásita | USB/FPC/sensing/I2C/ALERT/LEDs aislados o con Ioff apropiado en ambos sentidos; verificar placa apagada con USB. |
| L01 | RGB por ESP32 y estado de carga opcional | Drivers/resistencias apropiados, estados por firmware, estado OFF sin consumo LED salvo carga USB. |
| T01 | Diagnóstico V1 | TP VBUS, BAT+, GND, SYSTEM_POWER, SYSTEM_5V, 3V3 si existe, USB D+/D− con TP de baja discontinuidad, USB_VBUS_VALID, HOLD, REQUEST, CHG/PG y SDA/SCL/ALERT si gauge. |
| F01 | JLCPCB preferente | MPN, encapsulado, código LCSC, clase, stock, precio, alternativa; verificar justo antes del pedido. |

GNSS: plano GND continuo, loops de conmutación cortos y nodo SW mínimo siguiendo fabricante; separar del receptor/coaxial dentro del espacio real. Ferrita/filtro sólo tras evaluar estabilidad, caída y ruido; comparar C/N0 y comportamiento RTK con carga, Wi-Fi y SD activos. No hay validación RF realizada.

Protección requerida: sobrecorriente/corto de entrada y salidas, ESD USB/botón, sobretensión de VBUS, polaridad de batería, NTC, protección de pack y transición entre fuentes. MPN de auxiliares pendiente del presupuesto y geometría; no sustituir estas funciones por el nombre comercial «power-bank».

## Criterios adicionales P1

| ID | Requisito | Criterio |
| --- | --- | --- |
| D03 | USB self-powered | Separar USB_VBUS/SYSTEM_5V; sensing del host adaptado a lógica segura, sin backfeed, desconectar datos incluso en ROM/reset/debug detenido. |
| D04 | FPC sin supuestos | Número de conductores, anclajes, paso, orientación, cable y pinout de revisión física verificados antes de huella. |
