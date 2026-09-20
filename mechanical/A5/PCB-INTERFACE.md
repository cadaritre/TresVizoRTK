# Interfaz mecánica para la PCB — A5

> Antecedente de coordinación. La espera de PCB/botón indicada abajo quedó sustituida por la solicitud actual de integrar módulos comerciales. Dimensiones del maestro siguen siendo útiles; el panel vigente de revisión y sus límites están en [INTEGRATION_REVIEW.md](../../docs/INTEGRATION_REVIEW.md). No usar esta espera histórica como bloqueo para revisar el panel comercial.

**Estado: referencia para coordinación; no es un volumen asignado ni un fit check aprobado.** El botón está en espera por indicación del propietario. No fijar su perforación ni comprar el módulo comercial estudiado antes de recibir el STEP de la PCB.

Maestro: `TresVizo-A5.FCStd`, en esta carpeta. A5 parte de A4 y modifica la tapa y dos rebajes superiores de la bandeja para fijar la antena HA-901A. La revisión de simplificación fusiona base/bandeja en `Chassis` y cuna/asiento en `BatteryIMUCarrier`. Conserva el marco global y el datum IMU. El antiguo soporte de biestable se retiró; su zona ya no se ofrece como volumen libre. Toda geometría está embebida. No importar archivos de `legacy` como dependencias.

## Coordenadas

Unidades mm. Z coincide con el eje vertical del receptor/jalón. Z=0 en la cara inferior de la base; X=Y=0 en el eje del conjunto. Frente de controles: +Y. El cuerpo va de Z12 a Z150.2; tapa/asiento de antena hasta Z168. La referencia externa de antena se extiende hasta Z214. Estas son cotas del CAD existente, no nuevas medidas de componentes.

| Objeto existente | X mín…máx | Y mín…máx | Z mín…máx | Interpretación |
| --- | --- | --- | --- | --- |
| Panel `ServiceCover` | −14.191…14.191 | 31.515…37.577 | 89…142 | Curvo, provisional; anclajes en X0/Z96 y X0/Z139, eje Y. |
| Zona del biestable anterior | — | — | — | Reserva y soporte retirados. Hay rampas estructurales; no asignar automáticamente esta zona a la nueva PCB. |
| Adaptador USB Tiny | −9…9 | 10.5…28.5 | 129…134 | Conservar acceso de desarrollo o resolverlo con la nueva PCB. |
| ESP32 Tiny | −9…9 | 12.5…14.95 | 139…162.5 | Conector FPC y cable necesitan espacio adicional. |
| Reserva GNSS | −18…18 | 12.5…24.5 | 43…107 | Envolvente conservadora, no PCB fabricable. |
| Reserva batería | −28…28 | −7.5…4.5 | 38…107 | Pack final pendiente. |
| Asiento IMU integrado | ±17.5 máx. | −16…8.8 | 119…123.8 | Parte de `BatteryIMUCarrier`; no mover el datum del sensor. Ver sólido real, no sólo esta caja. |
| PCB BMI088 inicial | −11.75…11.75 | −10…8 | 123.8…125.4 | PCB de 23.5×18 con patrón publicado; espesor 1.6 provisional. Reservar desplazamiento ±0.75 XY, componentes y cables. |
| Plantilla IMU temporal | −17.5…17.5 | −15.5…4.55 | 120.7…142 | Herramienta que se retira verticalmente durante montaje; no ocupa espacio permanente. |

**Restricción IMU del propietario:** la referencia del sensor debe alinearse nominalmente con X=Y=0, el eje del jalón. No desplazarla para acomodar la PCB de alimentación. A5 implementa un asiento con ajuste fino ±0.75 mm XY y una plantilla que permite alinear visualmente el encapsulado real antes de bloquear dos M2.5. `IMUTarget` es el objetivo nominal, no una medición del chip. Véase [montaje y centrado](IMU-ALIGNMENT.md) para tolerancias, tornillería y acceso. Mantener libres la ventana central, los dos tornillos y la extracción de la plantilla. La fijación llega a Z113.4. Prensa impresa `IMUNutBar`: X±15/Y0.5…10.5/Z115…119 más recorrido ±0.75 XY; no utiliza arandelas. El chasis tiene acceso inferior y techo inclinado: revisar el sólido real.

No sumar las reservas USB y biestable como una caja única: existen plataformas, nervios y asiento IMU entre ellas. El STEP de la PCB debe incluir espesor, componentes, salientes, fijaciones, conector USB, botón/actuador, LEDs, plugs y salida de cables. Luego se ajustarán la bandeja y el panel en este mismo maestro, manteniendo la silueta, el grabado y la base de una pieza.

### Fijación de antena integrada en A5

Tres ejes verticales en `(X,Y)=(+11.518138,6.650), (-11.518138,6.650), (0,-13.300)` mm. Las cabezas M2.5 ocupan Z161.5–164 y Ø4.5 mm; no hay arandelas. Los vástagos pasan por la tapa hasta Z172, con asiento Z164…168 de 4 mm. Reservar al menos 0.5 mm adicional alrededor de esta tornillería al integrar la PCB. Los rebajes R3.5 del chasis empiezan en Z160.7 y no son nuevas zonas de apoyo; la espina superior termina en Z163.6. Los barrenos de la tapa son Ø3 mm y el paso coaxial central continúa siendo Ø16 mm. El apriete se hace con la tapa retirada, antes de cerrar el cuerpo. No mover estos ejes ni el eje de antena para acomodar la PCB.

## Entrega necesaria del diseño electrónico

- Origen y orientación del STEP; contorno, espesor y alturas máximas por ambas caras.
- Centros y diámetros de agujeros, zonas sin cobre y superficies permitidas de apoyo.
- Plano de acoplamiento del USB-C, barrido del enchufe y alivio de tensión.
- Modelo exacto del pulsador y su recorrido; posición óptica de los LEDs.
- Acceso a conectores, tornillos y extracción de la placa.

Objetivo de integración: conector, botón e indicadores al ras de su panel, apoyos integrados en piezas impresas y tornillería comercial. El ajuste final se valida contra esos modelos y contra impresión real; no se inventan cotas para hacer encajar una placa todavía sin diseñar.

## Nombres vigentes para integración

`Base` + `ElectronicsTray` → `Chassis`; `BatteryCradle` + `IMUSeat` → `BatteryIMUCarrier`. Los objetos antiguos se retiraron, no son enlaces. Usar los sólidos actuales para colisiones; no confiar en cajas o volúmenes de A4/A5 anteriores. `MainShell`, `ServiceCover`, `AntennaCap`, `IMUReserve` y los datums globales permanecen. La simplificación no modifica archivos de la PCB eléctrica.
