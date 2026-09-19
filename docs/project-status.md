# Estado del proyecto

Fecha de referencia: septiembre de 2026.

## Significado de los estados

- **Previsto:** forma parte del alcance o de la arquitectura deseada, pero puede no estar diseñado ni implementado.
- **Por confirmar:** requiere identificar hardware, consultar documentación, medir o tomar una decisión.
- **Implementado:** existe una realización concreta en el repositorio o en el prototipo; no implica que esté validada.
- **Validado:** cuenta con pruebas documentadas y criterios de aceptación cumplidos.

## Resumen

| Área | Estado | Evidencia o pendiente |
| --- | --- | --- |
| Estructura y documentación inicial | Implementado | Directorios, metadatos y documentos iniciales presentes en el repositorio. |
| Inventario de componentes | Por confirmar | Se reporta que llegó la mayoría, pero falta identificar y documentar cada unidad y revisión. |
| Batería | Por confirmar | Aún no se ha recibido o seleccionado la unidad definitiva. |
| GNSS principal UM980 | Previsto | Falta identificar la carrier, firmware, interfaces y señales expuestas. |
| PPS del UM980 | Por confirmar | Debe comprobarse su disponibilidad en el conector de la carrier concreta. |
| ZED-F9P | Previsto para pruebas | Está disponible como opción de ensayo; no se ha definido integración. |
| ESP32-S3 | Previsto | La variante física de Waveshare ESP32-S3-Tiny N8R8 debe confirmarse antes de fijar placa, memoria o pinout. |
| BMI088 | Previsto | Falta identificar el breakout, orientación, interfaz y características eléctricas. |
| microSD | Previsto | Interfaz, circuito y política de cierre seguro pendientes. |
| Antena HA-901A | Por confirmar | Falta confirmar unidad, especificaciones, conector y referencia mecánica. |
| Alimentación y carga | Por confirmar | No existe todavía un diseño verificado para protección, regulación, carga y encendido. |
| Firmware | Previsto | No hay código, configuración de compilación ni primer flash documentado. |
| Aplicación móvil | Previsto | No hay framework, proyecto ni protocolo implementado. |
| Carcasa | Previsto | Solo existe el concepto cilíndrico; no hay dimensiones ni CAD. |
| Operación rover/base | Previsto | Sin implementación ni pruebas. |
| NTRIP y transporte RTCM | Previsto | Sin implementación ni pruebas. |
| Registro para postproceso | Previsto | Sin implementación, formatos seleccionados ni pruebas. |
| Fusión GNSS/IMU | Previsto | Sin algoritmo, calibración ni validación. |
| Telemetría BLE a 20 Hz | Previsto | Es un objetivo pendiente de mediciones de rendimiento y estabilidad. |
| Precisión aproximada de 2 cm | Objetivo de desarrollo | No implementada, medida ni garantizada. |
| Operación bajo árboles | Interés de investigación | No existe garantía ni evidencia de precisión bajo vegetación. |

## Validación

Actualmente no hay subsistemas funcionales validados. El estado FIX de una solución futura no bastará para declarar exactitud: deberán realizarse ensayos independientes, repetibles y documentados contra referencias adecuadas.

Este documento debe actualizarse cuando cambie la evidencia, no solo cuando cambien las intenciones. La secuencia prevista se describe en la [hoja de ruta](roadmap.md).

