# Lista de materiales inicial

Esta lista documenta la configuración prevista, no un diseño electrónico cerrado. No confirma compatibilidades eléctricas o mecánicas entre componentes. La mayoría de los componentes se reporta como recibida, pero falta realizar y documentar un inventario físico detallado; la referencia de batería ya fue indicada y su caracterización sigue pendiente.

| Componente | Función | Modelo previsto | Estado de confirmación | Observaciones |
| --- | --- | --- | --- | --- |
| Receptor GNSS principal | Solución GNSS/RTK y generación de observaciones | Unicore UM980 en placa de desarrollo o carrier | Previsto; carrier concreta por identificar | Verificar modelo de placa, firmware, conectores, interfaces y acceso real a señales. PPS en el conector queda pendiente de verificación. |
| Receptor GNSS alternativo | Pruebas y comparación | u-blox ZED-F9P | Disponible para posibles pruebas | No es el receptor principal definido y no implica que ambos receptores sean intercambiables. |
| Microcontrolador | Control, comunicaciones, registro e integración | ESP32-S3 | Identificado y con firmware inicial | CPU y memoria comprobadas por USB. Interfaces externas aún no configuradas. |
| Placa del microcontrolador | Soporte del ESP32-S3 | ESP32-S3-Tiny, 4 MB flash / 2 MB PSRAM | Captura Tiny y memoria comprobada por USB | Primer firmware cargado; PSRAM desactivada. La revisión física y los GPIO externos requieren verificación. No corresponde al perfil N8R8 inicialmente considerado. |
| IMU | Aceleración y velocidad angular | Bosch BMI088 en breakout | Prevista; breakout por identificar | Verificar fabricante de la placa, orientación de ejes, interfaz, niveles y requisitos de montaje. |
| Lector y tarjeta microSD | Observaciones GNSS, datos IMU, estado y diagnóstico | Lector microSD mediante módulo o socket y tarjeta | Previsto; solución concreta por confirmar | Identificar lector y tarjeta; verificar interfaz, alimentación, detección y estrategia de cierre seguro. |
| Antena GNSS | Recepción GNSS | Helix; modelo exacto por confirmar | Compra confirmada por el propietario | Verificar bandas, conector, alimentación, montaje y referencia del centro de fase. La HA-901A mencionada inicialmente no está confirmada. |
| Batería | Alimentación portátil | 955565, LiPo 1S, 3.7 V / 5000 mAh / 18.5 Wh anunciados | Publicación indicada por el propietario; sin caracterización física | Dos cables en imagen; capacidad real, dimensiones, conector, PCM, corriente admisible y NTC por confirmar. Ver power-board/BATTERY_REFERENCE.md. |
| Alimentación y carga | Carga, protección, regulación y encendido | Por definir | Pendiente de diseño y verificación | Diseñar a partir de los módulos reales y sus requisitos medidos o documentados. |
| Carcasa | Protección y referencia mecánica | Cilíndrica, impresa en 3D | Concepto previsto | Dimensiones y material pendientes; debe mantener alineación entre antena, IMU y jalón. |
| Interruptor biestable | Posible control de encendido | Módulo verde con pines de la publicación compartida | Identificado en captura; sin verificación eléctrica | No asumir que carga o protege una LiPo; comprobar posibilidad de apagado coordinado antes de integrarlo. |
| Interfaz de usuario física | Encendido y estado local | Por definir | Pendiente | No se prevé un botón dedicado para medir; las mediciones se operarán desde la app. |

## Antes de cerrar la BOM

- Fotografiar e identificar cada placa, revisión y conector sin publicar números de serie sensibles.
- Contrastar las marcas de los módulos con sus manuales oficiales.
- Medir las dimensiones y masas relevantes para la carcasa.
- Confirmar requisitos eléctricos y térmicos antes de elegir regulación, carga y batería.
- Registrar sustituciones como decisiones explícitas, sin asumir equivalencia por nombre de chip.

La [identificación de componentes](identification.md) conserva la evidencia y las diferencias entre opciones de la tienda y unidades verificadas.
