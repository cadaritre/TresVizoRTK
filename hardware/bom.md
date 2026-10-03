# Lista de materiales — hardware seleccionado

**Alimentación — 02/10/2026:** LiPo 1S 3.7 V / 3000 mAh confirmada. Lectura MAX17048 y apagado coordinado Mk2 implementados; falta identificar el elevador de 5 V y validar físicamente el conjunto con UM980. Ver `hardware/wiring.md` desde la raíz. La carga es autónoma por hardware; USB impide el corte total de batería.
**Selección del 02/10/2026:** Thing Plus ESP32-S3 WRL-24408, OLED Tecneu 0.96 I2C 128×64 y SparkFun Soft Power Switch JST 2 mm. Firmware y cableado actualizados; encendido/apagado implementado; prueba física pendiente.

Esta lista documenta la configuración prevista, no un diseño electrónico cerrado. No confirma compatibilidades eléctricas o mecánicas entre componentes. La mayoría de los componentes se reporta como recibida, pero falta realizar y documentar un inventario físico detallado; la referencia de batería ya fue indicada y su caracterización sigue pendiente.

| Componente | Función | Modelo previsto | Estado de confirmación | Observaciones |
| --- | --- | --- | --- | --- |
| Receptor GNSS principal | Solución GNSS/RTK y generación de observaciones | Unicore UM980 en placa de desarrollo o carrier | Previsto; carrier concreta por identificar | Verificar modelo de placa, firmware, conectores, interfaces y acceso real a señales. PPS en el conector queda pendiente de verificación. |
| Receptor GNSS alternativo | Pruebas y comparación | u-blox ZED-F9P | Disponible para posibles pruebas | No es el receptor principal definido y no implica que ambos receptores sean intercambiables. |
| Microcontrolador | Control y comunicaciones | ESP32-S3 en Thing Plus | Seleccionado | Configuración específica en firmware/esp32/boards; no es una DevKitC ni una Tiny. |
| Placa del microcontrolador | Control, Wi-Fi, BLE y USB | SparkFun Thing Plus ESP32-S3 WRL-24408, MINI-1-N4R2 | Compra y elección definitivas del propietario | 4 MB flash / 2 MB PSRAM Quad según fabricante; sustituye a la Tiny. Firmware 0.8.0 compilado; prueba física pendiente. |
| IMU | Aceleración y velocidad angular | Bosch BMI088 en breakout | Prevista; breakout por identificar | Verificar fabricante de la placa, orientación de ejes, interfaz, niveles y requisitos de montaje. |
| Lector y tarjeta microSD | Registro local | Socket SDIO integrado de la Thing Plus + tarjeta FAT32 | Lector definido; tarjeta por verificar | Backend de cuatro bits habilitado; reemplaza el módulo SPI externo. |
| Antena GNSS | Recepción GNSS | Helix; modelo exacto por confirmar | Compra confirmada por el propietario | Verificar bandas, conector, alimentación, montaje y referencia del centro de fase. La HA-901A mencionada inicialmente no está confirmada. |
| Batería | Alimentación portátil | LiPo 1S, 3.7 V / 3000 mAh / 11.1 Wh nominales | Capacidad corregida por el propietario; sin caracterización física | Dos cables en imagen; capacidad real, dimensiones, conector, PCM, corriente admisible y NTC por confirmar. Ver [referencia de batería](references/BATTERY_REFERENCE.md). |
| Alimentación y carga | Operación de banco y futura batería | USB-C de Thing Plus y USB propio del UM980 durante pruebas | Encendido/apagado en espera | La Thing Plus incorpora cargador y MAX17048; no se ha cerrado distribución portátil ni alimentación de UM980. |
| Carcasa | Protección y referencia mecánica | Cilíndrica, impresa en 3D | Concepto previsto | Dimensiones y material pendientes; debe mantener alineación entre antena, IMU y jalón. |
| Interruptor | Encendido/apagado futuro | SparkFun Soft Power Switch JST 2 mm | Compra confirmada | PUSH=GPIO10/A0, OFF=GPIO14/A1; pendiente de banco. |
| Interfaz de usuario física | Estado local | OLED Tecneu 0.96 pulgadas, I2C, cuatro pines, 128×64 con estuche | Compra confirmada | Driver SSD1306 según referencia del vendedor, dirección 0x3C/0x3D y VCC a 3.3 V; validar unidad recibida. |

Cableado vigente en [hardware/wiring.md](wiring.md). La carcasa diseñada para Tiny requiere revisión mecánica antes de alojar Thing Plus/OLED; no se ha regenerado CAD con dimensiones supuestas.

## Antes de cerrar la BOM

- Fotografiar e identificar cada placa, revisión y conector sin publicar números de serie sensibles.
- Contrastar las marcas de los módulos con sus manuales oficiales.
- Medir las dimensiones y masas relevantes para la carcasa.
- Confirmar requisitos eléctricos y térmicos antes de elegir regulación, carga y batería.
- Registrar sustituciones como decisiones explícitas, sin asumir equivalencia por nombre de chip.

La [identificación de componentes](identification.md) conserva la evidencia y las diferencias entre opciones de la tienda y unidades verificadas.
