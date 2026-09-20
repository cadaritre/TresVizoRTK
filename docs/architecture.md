# Arquitectura del sistema

La arquitectura separa el procesamiento del receptor GNSS, la coordinación del instrumento en el ESP32-S3 y la experiencia de operación en la aplicación. Esta separación evita acoplar la app a comandos específicos de un fabricante y permite validar cada frontera de forma independiente.

El producto previsto es un receptor GNSS RTK de triple banda con IMU y lector microSD. El software del ESP32-S3 debe concentrar la configuración y operación del instrumento, con robustez y experiencia de uso tipo Emlid como referencia de producto, sin asumir equivalencia funcional ni rendimiento demostrado. La app topográfica es un desarrollo independiente, todavía sin iniciar.

La versión 0.1.0 implementa el arranque del ESP32, un panel web de configuración y diagnóstico, Wi-Fi AP/STA y persistencia de ajustes. El resto de las responsabilidades siguientes describe el alcance previsto; consulta el [estado](project-status.md) para distinguirlo de lo implementado.

La cobertura de triple banda deberá verificarse para el conjunto real de receptor, firmware y antena. Las interfaces eléctricas y los modelos de placa siguen pendientes de identificación.

## Responsabilidades

### Receptor GNSS

- Adquirir señales GNSS y calcular la solución de posición, velocidad y tiempo.
- Ejecutar la solución RTK cuando disponga de correcciones compatibles.
- Generar observaciones y mensajes admitidos por su modelo y firmware.
- Informar indicadores de calidad sin convertir el estado FIX en garantía de exactitud.

El UM980 es el receptor principal previsto. El ZED-F9P queda disponible para pruebas; no se presume equivalencia de comandos, formatos o conexiones entre ambos.

### ESP32-S3

- Configurar y controlar el receptor GNSS.
- Centralizar la configuración del instrumento: modo base/rover, opciones GNSS admitidas, correcciones, comunicaciones, adquisición IMU y registro. Validar, aplicar y conservar los ajustes compatibles con el hardware y firmware verificados.
- Leer posición, velocidad, tiempo y estado.
- Gestionar y enrutar mensajes RTCM.
- Actuar como cliente NTRIP cuando disponga de conectividad Wi-Fi adecuada.
- Adquirir la IMU y conservar información temporal suficiente para estudiar su alineación con GNSS.
- Desarrollar en el futuro la fusión GNSS/IMU y la compensación geométrica de inclinación.
- Registrar observaciones y diagnósticos en microSD con recuperación y cierre seguro.
- Exponer a la app un protocolo propio del instrumento.
- Gestionar estado, energía y apagado seguro.

El firmware será responsable del estado y la configuración efectiva del equipo. La interfaz inicial es un panel web alojado en la flash del ESP32, accesible por su red Wi-Fi. Para desarrollo existe un puente local USB que muestra los mismos archivos del panel y consulta el ESP32 real. La app futura podrá consultar y solicitar ajustes mediante el protocolo propio.

La robustez deberá demostrarse con pruebas de desconexión y reconexión, pérdida de correcciones, reinicios, configuración inválida, falta de espacio y cierre o recuperación de registros. Los diagnósticos deberán permitir conocer el estado real de cada subsistema.

### IMU y lector microSD

- **IMU BMI088:** componente central del instrumento para adquirir aceleración y velocidad angular. La fusión GNSS/IMU y la compensación de inclinación requieren desarrollo, sincronización, calibración y validación propios.
- **Lector y tarjeta microSD:** almacenamiento local de observaciones GNSS, datos IMU y diagnósticos. El ESP32-S3 gestionará escritura, estado de la tarjeta, recuperación y cierre seguro; el módulo o socket y la interfaz están por confirmar.

### Aplicación móvil

- Administrar mapas y proyectos.
- Realizar levantamientos mediante captura de puntos, códigos y notas.
- Asistir en tareas de replanteo y trazo.
- Consultar y solicitar cambios de configuración al firmware mediante el protocolo público del instrumento.
- Importar y exportar archivos.
- Mostrar calidad GNSS, estado de IMU, batería y diagnósticos relevantes.
- Considerar a futuro puntos remotos mediante dirección de apuntado y una distancia introducida desde un distanciómetro externo.

La app no debe depender directamente de comandos Unicore, UBX ni de detalles internos del hardware. La lógica de levantamientos, replanteos y trazo pertenece a esta app; la gestión del receptor, la IMU, el almacenamiento y la configuración efectiva pertenece al firmware del instrumento.

## Flujos de datos previstos

### Solución y telemetría

1. El receptor GNSS produce solución, tiempo y estado.
2. El ESP32 recibe los mensajes, conserva el tiempo de medición y registra su tiempo de llegada.
3. El ESP32 normaliza la información al protocolo del instrumento.
4. La app recibe control y telemetría principalmente por BLE.

El requisito mínimo es recibir 10 épocas GNSS distintas por segundo y entregarlas a la app; el objetivo ampliado es 20 Hz. Deben medirse frecuencia de medición, llegada, pérdidas y antigüedad por separado. El refresco de diagnósticos HTTP (2 s por defecto) no gobierna la adquisición UART. Frecuencia y latencia extremo a extremo siguen pendientes de validación.

### Correcciones NTRIP directas

1. El teléfono ofrece conectividad mediante su hotspot Wi-Fi.
2. El ESP32 se conecta por Wi-Fi y actúa como cliente NTRIP.
3. El ESP32 entrega RTCM compatible al receptor GNSS.
4. El sistema supervisa antigüedad, continuidad y pérdida de correcciones.

### Correcciones y operación principal por BLE (pendiente de implementar)

La app obtendrá RTCM desde NTRIP usando el internet del teléfono y lo reenviará al ESP32 por BLE. El ESP32 lo entregará al GNSS. Este es el flujo principal solicitado; NTRIP directo por Wi-Fi queda como opción. BLE no proporciona acceso genérico del ESP32 a Internet.

El control BLE deberá cubrir configuración del instrumento, estado, solución, correcciones y control de registro. Las descargas de archivos grandes se realizarán por Wi-Fi. La app debe manejar reconexión, continuidad en segundo plano y antigüedad de las correcciones; la recepción UART y el registro no deben depender de tener el panel abierto.

Referencia: [Emlid BLE y sus excepciones Wi-Fi](https://community.emlid.com/t/bluetooth-is-now-main-connectivity-option-for-r-series-reach-receivers/42233). Describe una experiencia de operación, no compatibilidad con el protocolo propietario de Emlid. En Emlid también existen funciones de registro, reportes y actualización que requieren Wi-Fi u otra conexión a internet.

### Registro y postproceso

El ESP32 podrá guardar observaciones GNSS, datos IMU y diagnósticos con metadatos temporales. Registrar observaciones para PPK no significa ejecutar el postproceso en el ESP32; el postproceso se realizaría externamente con herramientas y formatos todavía por seleccionar.

### Compensación de inclinación

La IMU y GNSS aportarán mediciones con tiempos y marcos de referencia distintos. La compensación requerirá sincronización, calibración de offsets, definición geométrica, inicialización dinámica y validación de campo. La dirección de desplazamiento GNSS no debe tratarse como dirección de apuntado de la carcasa.

## Enlaces físicos y lógicos

- **BLE:** control y telemetría principal con la app.
- **Wi-Fi:** acceso del ESP32 a NTRIP mediante el hotspot del teléfono y posible transferencia de archivos.
- **USB:** desarrollo, carga y consola JSON de diagnóstico/configuración implementados; transferencia de archivos futura.
- **microSD:** persistencia local de observaciones y diagnósticos.
- **Interfaz GNSS:** pendiente de confirmar en la carrier real, incluidos niveles, tasas y señales temporales.

Los detalles eléctricos se mantienen en [interfaces y conexiones](../hardware/wiring.md). Las decisiones deben reflejarse también en [el estado del proyecto](project-status.md).

## Registro, base y distribución de correcciones

El alcance ampliado, los comandos investigados, referencias de altura, sesiones PPK y los roles de entrada/publicación/caster local se detallan en [registro, base y NTRIP](recording-base-ntrip.md).
