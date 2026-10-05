# TresVizoRTK

**Alimentación — 02/10/2026:** LiPo 1S 3.7 V / 3000 mAh confirmada. Lectura MAX17048 y apagado coordinado Mk2 implementados; falta identificar el elevador de 5 V y validar físicamente el conjunto con UM980. Ver `hardware/wiring.md` desde la raíz. La carga es autónoma por hardware; USB impide el corte total de batería.
TresVizoRTK es un proyecto personal para desarrollar un prototipo funcional de receptor GNSS RTK de triple banda con IMU y lector microSD, orientado a trabajos de topografía. El repositorio reunirá el firmware de un ESP32-S3, una aplicación móvil, la documentación electrónica, la lista de materiales y los archivos mecánicos de una carcasa imprimible en 3D. La cobertura de bandas del conjunto receptor y antena deberá verificarse con el hardware real.

El objetivo es disponer de un software de instrumento robusto en el ESP32-S3, tomando la experiencia de equipos Emlid como referencia de producto. El firmware concentrará la configuración y operación del equipo; una app independiente, todavía sin iniciar, resolverá levantamientos, replanteos y trazo. Esta referencia no implica equivalencia de funciones o rendimiento validada.

El objetivo de desarrollo es alcanzar aproximadamente 2 cm de precisión en condiciones favorables. Esa cifra no representa una capacidad implementada, medida ni garantizada. La operación bajo árboles es un interés de investigación del proyecto y tampoco implica una garantía de precisión bajo vegetación.

## Estado actual

El firmware **0.8.0** está adaptado y compilado para **SparkFun Thing Plus ESP32-S3 WRL-24408**. El equipo conserva el nombre **MeridianV**, el panel, BLE, NTRIP y los servicios GNSS. La nueva placa sustituye a la Tiny; las pruebas físicas históricas de esa placa no validan este montaje.

Esta entrega añade OLED SSD1306 I2C de 128×64, microSD integrada por SDIO y una identidad de hardware independiente para las imágenes firmadas. La pantalla muestra calidad GNSS, satélites, correcciones, grabación e IP; caduca la calidad cuando dejan de llegar datos. La tarjeta no se formatea automáticamente.

El panel identifica la placa, muestra el estado de OLED y microSD y controla el registro según la disponibilidad real y el cierre de archivos. Las descargas incompletas conservan `.part`. Cargador USB y diagnóstico BLE actualizados para la nueva placa; [detalle del software](docs/panel-campo.md).

El almacenamiento se llama **Memoria interna del dispositivo** en la interfaz y en las etiquetas de la API para aplicaciones; en la OLED, **MEM INT.**. El soporte físico sigue documentado como microSD. Grabación, cierre, catálogo y descarga implementados; comprobación física pendiente.

**Pendiente de banco:** primera carga en Thing Plus, OLED recibida, microSD, enlace UART y operación prolongada. La adaptación no cargó firmware en ningún equipo. **Encendido/apagado con el SparkFun Soft Power Switch implementado; prueba física pendiente.** Durante el banco, Thing Plus y UM980 mantienen alimentación USB separada y GND común.

**Sin integrar:** IMU, radio UHF y aplicación móvil. La carcasa diseñada para Tiny requiere revisión para la Thing Plus y la OLED; no se ha dado por compatible ni se ha regenerado CAD.

El [cableado vigente](hardware/wiring.md) reúne los pines y la primera instalación. Detalle de cambios y pruebas en el [README del firmware](firmware/esp32/README.md). Las imágenes OTA llevan la [firma del propietario](tools/firmware_signing/README.md).

## Alcance previsto

El prototipo busca llegar a:

- Operación como rover RTK o como base.
- Recepción y transmisión de correcciones por los enlaces que se validen.
- Acceso a correcciones NTRIP.
- Registro de observaciones GNSS para postproceso externo.
- Integración GNSS/IMU y compensación de inclinación del jalón, todavía por desarrollar y validar.
- Configuración y operación del instrumento gestionadas por el firmware del ESP32-S3.
- Aplicación móvil independiente para levantamientos, replanteos y trazo, con acceso a configuración y estado mediante el protocolo del instrumento.
- Registro de diagnósticos para análisis y mejora del sistema.

## Arquitectura resumida

- **Receptor GNSS:** calcula la solución GNSS/RTK y produce observaciones y mensajes compatibles con su modelo y firmware.
- **ESP32-S3:** controla el receptor, enruta RTCM, adquiere la IMU, gestiona tiempos, almacenamiento, comunicaciones y apagado seguro. La fusión GNSS/IMU es trabajo futuro.
- **IMU BMI088:** aporta aceleración y velocidad angular para la futura integración GNSS/IMU y compensación de inclinación.
- **Lector y tarjeta microSD:** proporcionan almacenamiento local de observaciones, datos IMU y diagnósticos bajo control del ESP32-S3.
- **Aplicación móvil independiente:** gestiona mapas, proyectos, levantamientos, replanteos, trazo e intercambio de archivos; consulta el estado y solicita cambios de configuración al firmware.

La aplicación se comunicará mediante un protocolo propio del instrumento, separado de los comandos específicos de Unicore o u-blox. BLE se prevé como enlace principal de control y telemetría; el objetivo de 20 Hz está pendiente de pruebas. Wi-Fi, conectado al hotspot del teléfono, permitiría al ESP32 acceder a NTRIP. USB se reserva para desarrollo y diagnóstico, y Wi-Fi o USB para transferencias grandes.

La [arquitectura](docs/architecture.md) describe las responsabilidades y los flujos de datos con mayor detalle.

## Hardware previsto

La base considerada incluye:

- Unicore UM980 en una placa de desarrollo o carrier como GNSS principal.
- u-blox ZED-F9P disponible para posibles pruebas.
- SparkFun Thing Plus ESP32-S3 WRL-24408, con 4 MB de flash y 2 MB de PSRAM Quad según fabricante.
- Bosch BMI088 en breakout.
- Socket microSD integrado de la Thing Plus, SDIO de cuatro bits y tarjeta FAT32.
- OLED Tecneu 0.96 pulgadas I2C, cuatro pines y 128×64; driver SSD1306 según referencia del vendedor.
- Antena Helix, cuya compra confirmó el propietario; modelo y bandas por verificar. La HA-901A mencionada inicialmente no está confirmada.
- Batería LiPo de una celda, nominal 3.7 V y 3000 mAh, confirmada por el propietario.
- SparkFun Soft Power Switch JST 2 mm comprado; integración de encendido/apagado implementado; prueba física pendiente.
- Carcasa cilíndrica impresa en 3D y montaje sobre jalón.

El enlace GNSS usa RX del ESP32 en **GPIO44** y TX en **GPIO43**, con GND común; ambos equipos reciben alimentación USB por separado. La OLED usa **SDA8/SCL9 y 3.3 V**. El pinout de la Tiny (18/17) queda como historial. La disponibilidad de PPS en la carrier UM980 concreta está pendiente de verificación. Consulta la [lista de materiales](hardware/bom.md) y el [cableado vigente](hardware/wiring.md).

## Mapa del repositorio

| Ruta | Contenido previsto |
| --- | --- |
| `firmware/esp32/` | Firmware del controlador ESP32-S3. |
| `app/` | Aplicación móvil del instrumento. |
| `hardware/` | BOM, módulos comerciales, conexiones y referencias del hardware vigente. |
| `mechanical/` | V1 para imprimir y fuentes necesarias para regenerarla. |
| `docs/` | Arquitectura, estado, hoja de ruta y entorno de desarrollo. |
| `tools/` | Puente USB, diagnóstico GNSS/BLE, empaquetado y actualización de firmware. |
| `tests/fixtures/` | Datos de prueba pequeños y anonimizados. |

## Documentación

- [Arquitectura del sistema](docs/architecture.md)
- [Estado del proyecto](docs/project-status.md)
- [Servicios actuales del ESP32 (0.5.0)](docs/esp32-services.md)
- [Configuración avanzada del receptor (0.6.0)](docs/gps-advanced.md)
- [Panel reorganizado para campo (0.6.0)](docs/panel-campo.md)
- [Hoja de ruta](docs/roadmap.md)
- [Entorno y prácticas de desarrollo](docs/development.md)
- [Lista de materiales](hardware/bom.md)
- [Identificación del hardware recibido](hardware/identification.md)
- [Interfaces y conexiones](hardware/wiring.md)
- [Mecánica vigente, V2.2](mechanical/README.md)
- [Auditoría de la carcasa V1](mechanical/AUDITORIA-V1.md)
- [BOM de tornillería](mechanical/v2.2/SCREW-BOM.md)
- [Revisión de integración de V1, antecedente](docs/INTEGRATION_REVIEW.md)

No se ha seleccionado una licencia. El contenido del repositorio no debe interpretarse como publicado bajo una licencia específica hasta que el propietario la defina expresamente.
