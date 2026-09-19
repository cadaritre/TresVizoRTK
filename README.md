# TresVizoRTK

TresVizoRTK es un proyecto personal para desarrollar un prototipo funcional de receptor GNSS RTK orientado a trabajos de topografía. El repositorio reunirá el firmware de un ESP32-S3, una aplicación móvil, la documentación electrónica, la lista de materiales y los archivos mecánicos de una carcasa imprimible en 3D.

El objetivo de desarrollo es alcanzar aproximadamente 2 cm de precisión en condiciones favorables. Esa cifra no representa una capacidad implementada, medida ni garantizada. La operación bajo árboles es un interés de investigación del proyecto y tampoco implica una garantía de precisión bajo vegetación.

## Estado actual

El repositorio se encuentra en su etapa inicial de organización y documentación. No hay firmware, aplicación, diseño electrónico ni modelo mecánico implementado o validado. Se ha recibido la mayoría de los componentes, pero falta completar su identificación y verificación; la batería continúa pendiente.

Consulta [el estado detallado](docs/project-status.md) antes de interpretar cualquier elemento como funcional.

## Alcance previsto

El prototipo busca llegar a:

- Operación como rover RTK o como base.
- Recepción y transmisión de correcciones por los enlaces que se validen.
- Acceso a correcciones NTRIP.
- Registro de observaciones GNSS para postproceso externo.
- Integración GNSS/IMU y compensación de inclinación del jalón, todavía por desarrollar y validar.
- Configuración, operación y visualización de estado desde una aplicación móvil.
- Registro de diagnósticos para análisis y mejora del sistema.

## Arquitectura resumida

- **Receptor GNSS:** calcula la solución GNSS/RTK y produce observaciones y mensajes compatibles con su modelo y firmware.
- **ESP32-S3:** controla el receptor, enruta RTCM, adquiere la IMU, gestiona tiempos, almacenamiento, comunicaciones y apagado seguro. La fusión GNSS/IMU es trabajo futuro.
- **Aplicación móvil:** gestiona mapas, proyectos, captura, replanteo, configuración, intercambio de archivos y visualización del estado del instrumento.

La aplicación se comunicará mediante un protocolo propio del instrumento, separado de los comandos específicos de Unicore o u-blox. BLE se prevé como enlace principal de control y telemetría; el objetivo de 20 Hz está pendiente de pruebas. Wi-Fi, conectado al hotspot del teléfono, permitiría al ESP32 acceder a NTRIP. USB se reserva para desarrollo y diagnóstico, y Wi-Fi o USB para transferencias grandes.

La [arquitectura](docs/architecture.md) describe las responsabilidades y los flujos de datos con mayor detalle.

## Hardware previsto

La base considerada incluye:

- Unicore UM980 en una placa de desarrollo o carrier como GNSS principal.
- u-blox ZED-F9P disponible para posibles pruebas.
- ESP32-S3; se considera una Waveshare ESP32-S3-Tiny N8R8, con variante física por confirmar.
- Bosch BMI088 en breakout.
- Almacenamiento microSD.
- Antena multibanda HA-901A, con unidad y especificaciones por confirmar.
- Batería LiPo de una celda, nominal 3.7 V y aproximadamente 5000 mAh, aún pendiente.
- Carcasa cilíndrica impresa en 3D y montaje sobre jalón.

No se han fijado GPIO, conectores, niveles eléctricos, dimensiones ni diseño de alimentación. La disponibilidad de PPS en la carrier UM980 concreta está pendiente de verificación. Consulta la [lista de materiales](hardware/bom.md) y las [conexiones pendientes](hardware/wiring.md).

## Mapa del repositorio

| Ruta | Contenido previsto |
| --- | --- |
| `firmware/esp32/` | Firmware del controlador ESP32-S3. |
| `app/` | Aplicación móvil del instrumento. |
| `hardware/` | BOM, conexiones y futuros esquemas electrónicos. |
| `mechanical/` | Requisitos, fuentes CAD y exportaciones mecánicas. |
| `docs/` | Arquitectura, estado, hoja de ruta y entorno de desarrollo. |
| `tools/` | Futuras herramientas auxiliares del proyecto. |
| `tests/fixtures/` | Datos de prueba pequeños y anonimizados. |

## Documentación

- [Arquitectura del sistema](docs/architecture.md)
- [Estado del proyecto](docs/project-status.md)
- [Hoja de ruta](docs/roadmap.md)
- [Entorno y prácticas de desarrollo](docs/development.md)
- [Lista de materiales](hardware/bom.md)
- [Interfaces y conexiones](hardware/wiring.md)
- [Concepto mecánico](mechanical/README.md)

No se ha seleccionado una licencia. El contenido del repositorio no debe interpretarse como publicado bajo una licencia específica hasta que el propietario la defina expresamente.

