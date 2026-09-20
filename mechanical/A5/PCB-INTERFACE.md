# Interfaz mecánica para la PCB — A5

**Estado: referencia para coordinación; no es un volumen asignado ni un fit check aprobado.** El botón está en espera por indicación del propietario. No fijar su perforación ni comprar el módulo comercial estudiado antes de recibir el STEP de la PCB.

Maestro: `TresVizo-A5.FCStd`, en esta carpeta. A5 conserva las geometrías físicas de A4; cambia el empaquetado del archivo y su documentación. Toda geometría está embebida. No importar archivos de `legacy` como dependencias.

## Coordenadas

Unidades mm. Z coincide con el eje vertical del receptor/jalón. Z=0 en la cara inferior de la base; X=Y=0 en el eje del conjunto. Frente de controles: +Y. El cuerpo va de Z12 a Z150.2; tapa/asiento de antena hasta Z168. La referencia externa de antena se extiende hasta Z214. Estas son cotas del CAD existente, no nuevas medidas de componentes.

| Objeto existente | X mín…máx | Y mín…máx | Z mín…máx | Interpretación |
| --- | --- | --- | --- | --- |
| Panel `ServiceCover` | −14.191…14.191 | 31.515…37.577 | 89…142 | Curvo, provisional; anclajes en X0/Z96 y X0/Z139, eje Y. |
| Reserva del biestable antiguo | −9…9 | 16…28 | 109.3…123.3 | Reemplazable; no equivale a cavidad libre. |
| Adaptador USB Tiny | −9…9 | 10.5…28.5 | 129…134 | Conservar acceso de desarrollo o resolverlo con la nueva PCB. |
| ESP32 Tiny | −9…9 | 12.5…14.95 | 139…162.5 | Conector FPC y cable necesitan espacio adicional. |
| Reserva GNSS | −18…18 | 12.5…24.5 | 43…107 | Envolvente conservadora, no PCB fabricable. |
| Reserva batería | −28…28 | −7.5…4.5 | 38…107 | Pack final pendiente. |
| Asiento IMU | −26…26 | −16…15.7 | 111…123 | Geometría real del soporte; no mover su referencia al integrar la placa. |
| Reserva BMI088 | −14…14 | −15…9 | 123…131 | El patrón del breakout sigue sin confirmar. |

No sumar las reservas USB y biestable como una caja única: existen plataformas, nervios y asiento IMU entre ellas. El STEP de la PCB debe incluir espesor, componentes, salientes, fijaciones, conector USB, botón/actuador, LEDs, plugs y salida de cables. Luego se ajustarán la bandeja y el panel en este mismo maestro, manteniendo la silueta, el grabado y la base de una pieza.

## Entrega necesaria del diseño electrónico

- Origen y orientación del STEP; contorno, espesor y alturas máximas por ambas caras.
- Centros y diámetros de agujeros, zonas sin cobre y superficies permitidas de apoyo.
- Plano de acoplamiento del USB-C, barrido del enchufe y alivio de tensión.
- Modelo exacto del pulsador y su recorrido; posición óptica de los LEDs.
- Acceso a conectores, tornillos y extracción de la placa.

Objetivo de integración: conector, botón e indicadores al ras de su panel, apoyos integrados en piezas impresas y tornillería comercial. El ajuste final se valida contra esos modelos y contra impresión real; no se inventan cotas para hacer encajar una placa todavía sin diseñar.
