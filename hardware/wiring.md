# Interfaces y conexiones pendientes

Este documento identifica las conexiones que deberán resolverse. No constituye un esquema, no asigna GPIO y no confirma compatibilidad eléctrica.

## Matriz de interfaces

| Enlace | Uso previsto | Aspectos por verificar antes de conectar |
| --- | --- | --- |
| Carrier UM980 ↔ ESP32-S3 | Configuración, solución GNSS, observaciones y transporte RTCM | Carrier exacta, conector, pinout, niveles lógicos, dirección de señales, tasas, control de flujo, formatos y comportamiento al arranque. |
| PPS del UM980 ↔ ESP32-S3 | Referencia temporal potencial | La disponibilidad de PPS en el conector de la carrier concreta está pendiente de verificación. Confirmar nivel, polaridad, anchura, relación con la época GNSS y latencias. |
| ZED-F9P ↔ ESP32-S3 | Pruebas opcionales | Placa concreta, interfaz expuesta, niveles y protocolo. Mantener su integración separada de la del UM980. |
| BMI088 breakout ↔ ESP32-S3 | Adquisición de IMU y señales de datos listos | Breakout exacto, interfaz disponible, niveles, pinout, orientación de ejes, frecuencia y características de las señales de interrupción. |
| microSD ↔ ESP32-S3 | Registro de observaciones y diagnósticos | Módulo o socket, interfaz, niveles, consumo, detección de tarjeta y estrategia de recuperación y cierre seguro. |
| USB ↔ ESP32-S3 | Desarrollo, diagnóstico y posible transferencia | Conector y circuito presentes en la placa real, funciones USB disponibles y método de alimentación durante pruebas. |
| Batería ↔ sistema de potencia | Operación portátil | Celda real, conector, polaridad, protección, carga, regulación, corriente y comportamiento del encendido y apagado. |
| Sistema de potencia ↔ módulos | Distribución de alimentación | Tensiones de cada placa, corrientes máximas y transitorias, secuencia, tierras, ruido y protección. No definir el esquema hasta comprobar los módulos. |

## Sincronización y tiempos

- Conservar por separado el instante de medición informado por cada sensor y el instante en que sus datos llegan al ESP32.
- Medir las latencias de UART y de las señales de datos listos antes de diseñar la fusión temporal.
- No considerar PPS suficiente por sí solo: debe conocerse a qué época corresponde y cómo se relaciona con los mensajes de datos.
- Definir unidades, escalas de tiempo y tratamiento de reinicios o pérdida de sincronía antes de persistir registros.

## Alimentación

El diseño de carga, protección, regulación, encendido y apagado está pendiente. Debe partir de la identificación de las placas y de documentación del fabricante, complementada con mediciones seguras. No se publica todavía un diagrama de alimentación ni se presume que los conectores disponibles acepten directamente una LiPo 1S.

## Criterio para futuros esquemas

Los esquemas deberán registrar revisión de hardware, nombres de red, niveles, conectores y puntos de prueba. Cualquier pinout deberá citar la placa concreta, no solo el chip principal.

