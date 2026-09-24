# TresVizoRTK

TresVizoRTK es un proyecto personal para desarrollar un prototipo funcional de receptor GNSS RTK de triple banda con IMU y lector microSD, orientado a trabajos de topografía. El repositorio reunirá el firmware de un ESP32-S3, una aplicación móvil, la documentación electrónica, la lista de materiales y los archivos mecánicos de una carcasa imprimible en 3D. La cobertura de bandas del conjunto receptor y antena deberá verificarse con el hardware real.

El objetivo es disponer de un software de instrumento robusto en el ESP32-S3, tomando la experiencia de equipos Emlid como referencia de producto. El firmware concentrará la configuración y operación del equipo; una app independiente, todavía sin iniciar, resolverá levantamientos, replanteos y trazo. Esta referencia no implica equivalencia de funciones o rendimiento validada.

El objetivo de desarrollo es alcanzar aproximadamente 2 cm de precisión en condiciones favorables. Esa cifra no representa una capacidad implementada, medida ni garantizada. La operación bajo árboles es un interés de investigación del proyecto y tampoco implica una garantía de precisión bajo vegetación.

## Estado actual

El firmware **0.6.2** corre sobre el ESP32-S3 y el equipo se llama **MeridianV**.
Panel web propio, sin clave de acceso: la contraseña del Wi-Fi del instrumento es
su única credencial. Enlace UART con el UM980 verificado en ambos sentidos, GGA y
GST a 10 Hz, precisión estimada en metros y solución RTK alcanzada con
correcciones NTRIP reales.

Funciona sin intervención tras un corte de corriente: el equipo recupera su red
Wi-Fi guardada, reconecta el perfil NTRIP y vuelve a corregir solo. La
configuración del receptor se graba en su memoria no volátil en cada cambio.

**Implementado pero sin probar contra hardware o servicio real:** publicación
NTRIP hacia un caster, caster propio sirviendo a un rover, lectura de sourcetable,
estacionamiento de base, promedio de coordenadas y los paquetes BLE de
telemetría. Compilan y están cargados; nadie los ha ejecutado de principio a fin.

**Sin integrar:** IMU (no hay hardware), radio UHF, firma de firmware y la
aplicación móvil. La microSD está preparada en código y deshabilitada hasta
validar el cableado. La carcasa vigente es la [V2 mecánica](mechanical/v2/README.md),
todavía sin imprimir ni ensayar.

Detalle de cada entrega en el [README del firmware](firmware/esp32/README.md) y
en el [estado del proyecto](docs/project-status.md).

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
- ESP32-S3-Tiny: la captura selecciona Tiny y el chip conectado reporta 4 MB de flash y 2 MB de PSRAM; no corresponde al perfil N8R8 considerado inicialmente.
- Bosch BMI088 en breakout.
- Lector y tarjeta microSD, con módulo o socket e interfaz por confirmar.
- Antena Helix, cuya compra confirmó el propietario; modelo y bandas por verificar. La HA-901A mencionada inicialmente no está confirmada.
- Batería LiPo de una celda, nominal 3.7 V y aproximadamente 5000 mAh, aún pendiente.
- Módulo de interruptor biestable para estudiar el encendido, aún sin verificar ni integrar.
- Carcasa cilíndrica impresa en 3D y montaje sobre jalón.

El enlace GNSS usa RX del ESP32 en GPIO18 y TX en GPIO17, con GND común; ambos equipos reciben alimentación USB por separado. El resto de interfaces requiere seguir la documentación de cableado y sus validaciones. La disponibilidad de PPS en la carrier UM980 concreta está pendiente de verificación. Consulta la [lista de materiales](hardware/bom.md) y las [conexiones pendientes](hardware/wiring.md).

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
- [Mecánica vigente, V2](mechanical/README.md)
- [Auditoría de la carcasa V1](mechanical/AUDITORIA-V1.md)
- [BOM de tornillería](mechanical/v2/BOM-TORNILLERIA.md)
- [Revisión de integración de V1, antecedente](docs/INTEGRATION_REVIEW.md)

No se ha seleccionado una licencia. El contenido del repositorio no debe interpretarse como publicado bajo una licencia específica hasta que el propietario la defina expresamente.
