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
| Inventario de componentes | Parcialmente identificado | Capturas y confirmaciones registradas en hardware/identification.md. Falta verificar revisiones físicas y paquete UM980. |
| Batería | Por confirmar | Aún no se ha recibido o seleccionado la unidad definitiva. |
| GNSS principal UM980 | Previsto | Falta identificar la carrier, firmware, interfaces y señales expuestas. |
| Receptor RTK de triple banda | Objetivo de desarrollo | Verificar cobertura del conjunto real de receptor, firmware y antena. |
| PPS del UM980 | Por confirmar | Debe comprobarse su disponibilidad en el conector de la carrier concreta. |
| ZED-F9P | Previsto para pruebas | Está disponible como opción de ensayo; no se ha definido integración. |
| ESP32-S3 | Arranque comprobado | USB identifica 4 MB de flash y 2 MB de PSRAM; captura selecciona ESP32-S3-Tiny. Primer firmware cargado. GPIO externos pendientes. |
| BMI088 | Previsto | Falta identificar el breakout, orientación, interfaz y características eléctricas. |
| Lector y tarjeta microSD | Previsto | Módulo o socket, interfaz, circuito y política de cierre seguro pendientes. |
| Antena Helix | Compra confirmada | El propietario confirmó la compra; modelo, bandas y referencia mecánica pendientes. HA-901A no confirmada. |
| Alimentación y carga | Por confirmar | No existe todavía un diseño verificado para protección, regulación, carga y encendido. |
| Firmware del instrumento | Base implementada | Versión 0.1.0 compilada y cargada. Arranque, estado real, ajustes y consola USB comprobados; capacidades topográficas pendientes. |
| Interfaz de configuración del instrumento | Implementado | Panel web en flash con marca TresVizo; nombre, intervalo del panel y ajustes Wi-Fi. Puente USB local para desarrollo. |
| Persistencia de ajustes y consola USB | Comprobaciones iniciales superadas | Pruebas de validación, conflictos de revisión, reinicio y recuperación del parser en placa. No equivalen a validación de campo. |
| Wi-Fi AP/STA | Implementado; validación parcial | Arranque del AP comprobado desde el controlador. Conexión directa de un cliente Wi-Fi y hotspot externo pendientes de prueba. |
| Aplicación móvil independiente | Previsto | Destinada a levantamientos, replanteos y trazo. No hay framework, proyecto ni protocolo implementado. |
| Carcasa | Previsto | Solo existe el concepto cilíndrico; no hay dimensiones ni CAD. |
| Operación rover/base | Previsto | Sin implementación ni pruebas. |
| NTRIP y transporte RTCM | Previsto | Sin implementación ni pruebas. |
| Registro para postproceso | Previsto | Sin implementación, formatos seleccionados ni pruebas. |
| Fusión GNSS/IMU | Previsto | Sin algoritmo, calibración ni validación. |
| Telemetría BLE a 20 Hz | Previsto | Es un objetivo pendiente de mediciones de rendimiento y estabilidad. |
| Precisión aproximada de 2 cm | Objetivo de desarrollo | No implementada, medida ni garantizada. |
| Operación bajo árboles | Interés de investigación | No existe garantía ni evidencia de precisión bajo vegetación. |

## Validación

La base de firmware cuenta con comprobaciones iniciales de compilación, carga y funcionamiento en el ESP32. Los resultados y límites están en [validación del firmware](firmware-validation.md). No hay subsistemas topográficos validados. El estado FIX de una solución futura no bastará para declarar exactitud: deberán realizarse ensayos independientes, repetibles y documentados contra referencias adecuadas.

Este documento debe actualizarse cuando cambie la evidencia, no solo cuando cambien las intenciones. La secuencia prevista se describe en la [hoja de ruta](roadmap.md).

## Adquisición GNSS en desarrollo

UM980 identificado por USB y salida GGA activada temporalmente a 0.1 s. Parser compartido y tarea UART opcional implementados en código; la adquisición UART está desactivada por defecto hasta verificar el cableado. Las pruebas de software no validan el enlace físico ESP32–GNSS. Véase [primera adquisición GNSS](gnss-bringup.md) para evidencia y límites.


## Firmware cargado: 0.2.0

Clave de acceso actualizada por USB y persistencia comprobada. Panel GNSS conectado a la API y adquisición UART opcional preparada; UART desactivada mientras las placas sigan separadas. Repetidas las 28 pruebas de hardware con éxito. La captura del UM980 en la Mac entrega UTC a 10 Hz, todavía sin solución válida. BLE continúa pendiente de implementación; su papel principal de operación/correcciones está definido en la arquitectura.
