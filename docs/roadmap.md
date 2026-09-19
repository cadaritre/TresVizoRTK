# Hoja de ruta

Las etapas son deliberadamente pequeñas. Cada una debe dejar evidencia reproducible y actualizar [el estado del proyecto](project-status.md) antes de considerar completada una capacidad.

## 1. Identificación del hardware

- Inventariar placas, revisiones, conectores, antena y accesorios recibidos.
- Reunir manuales y esquemas oficiales correspondientes a las variantes reales.
- Confirmar requisitos eléctricos, dimensiones y señales accesibles, incluido PPS en la carrier UM980.
- Seleccionar batería y definir criterios del sistema de potencia.

## 2. Primer flash del ESP32-S3

- Confirmar la variante de placa, memoria y método de programación.
- Elegir framework y configuración de compilación a partir de compatibilidad verificada.
- Ejecutar un primer flash controlado y documentar recuperación, consola y reinicio.

## 3. Comunicación con GNSS

- Validar niveles y conexión con el UM980.
- Capturar e interpretar mensajes nativos con tiempos y tasas documentados.
- Configurar el receptor de forma reproducible sin exponer detalles de fabricante a la app.
- Ensayar por separado el ZED-F9P si aporta una comparación útil.

## 4. Lectura de IMU

- Confirmar el breakout BMI088, orientación y señales disponibles.
- Adquirir datos con unidades y escalas explícitas.
- Caracterizar ruido, sesgos, temperatura y señales de datos listos.

## 5. Sincronización

- Relacionar épocas GNSS, llegada de mensajes, PPS si está disponible y muestreo IMU.
- Medir latencias y jitter en lugar de asumirlos.
- Definir el modelo temporal de los registros y su comportamiento ante reinicios.

## 6. Almacenamiento

- Seleccionar interfaz y sistema de archivos para microSD.
- Definir formatos, metadatos, rotación y límites de registros.
- Probar pérdida de alimentación, tarjeta ausente, espacio agotado y cierre seguro.

## 7. Comunicaciones

- Definir y versionar el protocolo propio del instrumento.
- Implementar control y telemetría BLE y medir el objetivo de 20 Hz.
- Implementar Wi-Fi y cliente NTRIP con manejo de desconexiones.
- Evaluar el transporte alternativo de RTCM por BLE desde la app.
- Reservar Wi-Fi o USB para transferencias grandes según pruebas.

## 8. Aplicación e integración

- Elegir el framework móvil con criterios explícitos.
- Integrar estado, configuración, proyectos, captura y replanteo por etapas.
- Incorporar exportación e importación sin mezclar el protocolo público con comandos del receptor.
- Integrar GNSS, IMU, almacenamiento y gestión de energía con diagnósticos observables.

## 9. Compensación y validación de campo

- Medir geometría y offsets entre antena, IMU, carcasa y jalón.
- Diseñar calibración mecánica e inicialización dinámica como procesos separados.
- Desarrollar y evaluar la fusión GNSS/IMU y la compensación de inclinación.
- Comparar resultados contra referencias independientes en escenarios controlados.
- Ensayar después condiciones difíciles, incluida vegetación, sin extrapolar garantías.

## Trabajo futuro adicional

Una vez validada la arquitectura básica, podrá estudiarse un modo de puntos remotos que combine una dirección de apuntado con una distancia introducida desde un distanciómetro externo. No forma parte de la validación inicial.

