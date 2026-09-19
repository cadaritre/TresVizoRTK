# Lista de materiales inicial

Esta lista documenta la configuración prevista, no un diseño electrónico cerrado. No confirma compatibilidades eléctricas o mecánicas entre componentes. La mayoría de los componentes se reporta como recibida, pero falta realizar y documentar un inventario físico detallado; la batería está pendiente.

| Componente | Función | Modelo previsto | Estado de confirmación | Observaciones |
| --- | --- | --- | --- | --- |
| Receptor GNSS principal | Solución GNSS/RTK y generación de observaciones | Unicore UM980 en placa de desarrollo o carrier | Previsto; carrier concreta por identificar | Verificar modelo de placa, firmware, conectores, interfaces y acceso real a señales. PPS en el conector queda pendiente de verificación. |
| Receptor GNSS alternativo | Pruebas y comparación | u-blox ZED-F9P | Disponible para posibles pruebas | No es el receptor principal definido y no implica que ambos receptores sean intercambiables. |
| Microcontrolador | Control, comunicaciones, registro e integración | ESP32-S3 | Previsto | Debe verificarse la placa física antes de fijar configuración. |
| Placa del microcontrolador | Soporte del ESP32-S3 | Waveshare ESP32-S3-Tiny N8R8 | Considerada; variante física por confirmar | No fijar pinout, memoria ni perfil de compilación hasta identificar la unidad recibida. |
| IMU | Aceleración y velocidad angular | Bosch BMI088 en breakout | Prevista; breakout por identificar | Verificar fabricante de la placa, orientación de ejes, interfaz, niveles y requisitos de montaje. |
| Lector y tarjeta microSD | Observaciones GNSS, datos IMU, estado y diagnóstico | Lector microSD mediante módulo o socket y tarjeta | Previsto; solución concreta por confirmar | Identificar lector y tarjeta; verificar interfaz, alimentación, detección y estrategia de cierre seguro. |
| Antena GNSS | Recepción multibanda | HA-901A | Considerada; unidad y especificaciones por confirmar | Verificar ficha técnica, conector, alimentación si aplica, montaje y referencia del centro de fase. |
| Batería | Alimentación portátil | LiPo 1S, 3.7 V nominal, aproximadamente 5000 mAh | Pendiente | Capacidad, dimensiones, conector, corriente admisible y protecciones deben confirmarse. |
| Alimentación y carga | Carga, protección, regulación y encendido | Por definir | Pendiente de diseño y verificación | Diseñar a partir de los módulos reales y sus requisitos medidos o documentados. |
| Carcasa | Protección y referencia mecánica | Cilíndrica, impresa en 3D | Concepto previsto | Dimensiones y material pendientes; debe mantener alineación entre antena, IMU y jalón. |
| Interfaz de usuario física | Encendido y estado local | Por definir | Pendiente | No se prevé un botón dedicado para medir; las mediciones se operarán desde la app. |

## Antes de cerrar la BOM

- Fotografiar e identificar cada placa, revisión y conector sin publicar números de serie sensibles.
- Contrastar las marcas de los módulos con sus manuales oficiales.
- Medir las dimensiones y masas relevantes para la carcasa.
- Confirmar requisitos eléctricos y térmicos antes de elegir regulación, carga y batería.
- Registrar sustituciones como decisiones explícitas, sin asumir equivalencia por nombre de chip.
