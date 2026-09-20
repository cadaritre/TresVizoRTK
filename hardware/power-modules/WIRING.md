# Arnés del prototipo

Usar con las limitaciones de [README](README.md). Es cableado entre módulos, no un nuevo esquemático de PCB. Todos los nombres siguientes son señales funcionales, no números de contactos FPC ni una asignación nueva de GPIO.

## Alimentación

| Origen | Destino | Observación |
| --- | --- | --- |
| USB-C exterior de Adafruit 5871, VBUS | Fusible de entrada → `CHARGE_LINK` → pad **USB** del PowerBoost | No al pad 5V. Jumper/cable desmontable de carga, dimensionado al menos 2 A. Abierto para datos desde un puerto de capacidad desconocida. |
| Batería protegida, positivo/negativo verificados | BAT/GND o conector de batería del PowerBoost | No identificar polaridad por color o por el aspecto del conector. Fusible del ramal próximo al pack. |
| PowerBoost **VS** | SparkFun **VIN** | VS es la salida del power-path, no BAT ni la salida del elevador. |
| SparkFun **VOUT** | PowerBoost **EN** | Añadir 10 kΩ EN–GND. Mantener esta unión corta. |
| PowerBoost **5V** | `SYSTEM_5V` → fusible de salida → distribución | Aproximadamente 5.2 V. Dejar sin montar el conector USB-A que viene suelto. |
| Masas de los tres módulos y cargas | GND común | Sin aislamiento galvánico. |

Fusibles comerciales en línea: punto de partida 2 A en entrada USB, 3 A en batería y 1 A en distribución; ajustar tipo/curva con los picos medidos y la capacidad del cable/pack. No confundirlos con limitación precisa de corriente USB ni con protección de la celda. El fusible integrado del SparkFun, en esta conexión de control EN, **no protege la salida principal**.

Usar cable de potencia corto, inicialmente 22–24 AWG, y arnés USB 2.0 apantallado. Mantener la batería próxima al cargador; la guía recomienda menos de unas tres pulgadas en su conexión. Las ramas de datos deben conservar el par y la masa; evitar conexiones Dupont largas o protoboard en la ruta USB.

## Conectar Tiny sin alterar el FPC

Se conserva el **Tiny-Adapter y el FPC original de la unidad**. El cable interno hacia el USB-C de ese adaptador se hace a partir de un cable USB 2.0 de datos corto con extremo USB-C macho; se identifica cada conductor por continuidad, sin dar por cierta una convención de colores.

| Conductor del USB-C macho interno | Conectar a |
| --- | --- |
| D+ | D1+ del TS3USB30 |
| D− | D1− del TS3USB30 |
| GND | GND común |
| VBUS del cable interno | **SYSTEM_5V**, después de su protección de salida |

**Los pads VBUS/V+ de ambos canales del TS3USB30 quedan sin conectar al cable interno.** Comparten eléctricamente el VBUS del puerto exterior. Un cable de cuatro hilos directo desde ese módulo al Tiny-Adapter anularía el apagado y podría unir las dos alimentaciones. Aislar y sujetar individualmente las derivaciones.

El [Tiny-Adapter oficial](https://files.waveshare.com/wiki/ESP32-S3-Tiny/Tiny-Adapter.pdf) lleva los datos al FPC y conserva BOOT/RUN. El [plano Tiny](https://files.waveshare.com/wiki/ESP32-S3-Tiny/ESP32-S3-Tiny-Sch.pdf) es de una variante que no certifica la N8R8 física; por eso se reutiliza el conjunto original, sin fabricar otro conector ni trasladar numeración supuesta. El adaptador queda dentro del equipo y su puerto no es un segundo puerto exterior.

## Desconexión de datos y presencia del USB

El [esquema del Adafruit 5871](https://github.com/adafruit/Adafruit-TS3USB30-PCB) tiene `S` a 3.3 V mediante 47 kΩ y `/OE` a GND mediante 47 kΩ. Se usa el canal 1 para Tiny y se deja **todo el canal 2 sin cablear**.

- Q1: NPN de señal, por ejemplo PN2222A. Emisor a GND; colector a S. Base desde **3V3 de la Tiny** mediante 47 kΩ y 100 kΩ base–emisor. Con Tiny encendida selecciona canal 1; apagada queda canal 2 vacío. La base usa la alimentación de la placa, no un GPIO que cambie durante ROM/debug.
- `/OE` se mantiene en su estado predeterminado bajo. La alimentación del switch procede exclusivamente del USB exterior por su regulador incorporado. Su función Ioff limita la fuga con VCC=0; no es una garantía de comportamiento a cualquier tensión intermedia.
- Q2 opcional para información de presencia: base desde 3.3 V **del módulo USB** por 47 kΩ, 100 kΩ base–emisor; emisor GND; colector hacia `USB_PRESENT_N` con pull-up de 10 kΩ a 3V3 de Tiny. No une ambas fuentes de 3.3 V. Permite leer presencia de alimentación USB sin poner 5 V en el ESP32. **No es el detector calibrado VBUS_VALID** exigido para conformidad USB.

La desconexión con host ausente y el estado intermedio al descargar sus condensadores necesitan ensayo. Para TinyUSB, añadir/configurar el detector indicado en README; para Serial/JTAG o ROM, cualquier corrección que deba funcionar con firmware detenido debe ser autónoma. No considerar resuelto el límite de 3 ms por este circuito básico.

## Botón y firmware

| Señal | Conexión |
| --- | --- |
| Pulsador momentáneo | Entre BTN y GND del SparkFun; confirmar qué terminales cambian de abierto a cerrado. |
| PUSH | Entrada ESP32 con pull-up a su propia 3V3; estado activo bajo. |
| OFF | Salida ESP32, iniciar en LOW. HIGH solicita el corte al Mk2. |

El firmware debe esperar la liberación de la pulsación de arranque. Una petición posterior de apagado detiene adquisición, cierra/sincroniza microSD, guarda lo necesario y finalmente eleva OFF. No poner primero OFF y después intentar cerrar archivos. La pulsación larga de emergencia puede perder el último registro: es un corte independiente.

No se ha implementado esa secuencia aquí ni elegido nuevos números de GPIO. La asignación se cruza con UART/PPS del GNSS, SPI/SD e IMU existentes al cablear. La placa de encendido no necesita que el ESP32 mantenga una señal HOLD durante una sesión JTAG. [Guía Mk2](https://docs.sparkfun.com/SparkFun_Soft_Power_Switch_Mk2/single_page/).

## Indicadores

El RGB seleccionado es [Steren LED-5/RGB](https://www.steren.com.mx/led-de-5-mm-rgb.html), de ánodo común; reemplaza al Adafruit 159. Steren publica 1.8 V rojo y 2.8 V verde/azul. Se conservan tres NPN como sumideros para usar la alimentación conmutada de 5 V sin llevarla a los GPIO: ánodo a SYSTEM_5V; emisor a GND, colector al cátodo a través de **1 kΩ**, base desde GPIO a través de **4.7 kΩ** y **100 kΩ** base–emisor. Corrientes nominales de unos 2–3 mA por color con 5.2 V, sujetas a Vf y saturación reales. Se puede montar y aislar este pequeño arnés sin encargar PCB. Identificar E/B/C con la ficha del transistor comprado; no intercambiar pinouts de PN2222A y 2N3904 por apariencia.

Las resistencias limitan cada canal a unos pocos mA. Ajustar brillo por PWM después de probar la ventana óptica, especialmente a la luz del día. Estado propuesto: azul conexión, verde solución válida según el firmware, rojo aviso. El LED por sí solo no certifica precisión GNSS. Al apagar, la alimentación del RGB desaparece.

Para carga, llevar luz del LED amarillo del PowerBoost a la ventana CHG mediante guía óptica. Si se desea visualizar fin de carga, incorporar también su LED verde a esa ventana con dos trayectos ópticos. No puentear ambos LEDs eléctricamente, no conectar sus salidas al ESP32 y no confundir ausencia de luz con batería llena. Su alimentación es independiente del encendido del equipo. [Pinouts y LEDs PowerBoost](https://learn.adafruit.com/adafruit-powerboost-1000c-load-share-usb-charge-boost/pinouts).

## Comprobación del montaje

Antes de conectar computadora: verificar separación USB_VBUS/SYSTEM_5V, masas, polaridad, EN alto/bajo, apagado con USB presente y ausencia de tensión suministrada hacia el puerto exterior desde batería. Medir también con resistencias de carga; una lectura en vacío no descarta corriente de retorno.

Después: arranque con GNSS/Wi-Fi/SD, consumo/tensión de entrada y salida, temperatura de cargador/celda, pulsación corta/larga, cierre de archivo y recuperación BOOT/RUN. Probar USB en ambas orientaciones, flashing, consola y JTAG; conectar/desconectar con firmware detenido y comprobar tiempos de VBUS/datos. Ninguna de esas pruebas físicas se ha ejecutado durante esta entrega.
