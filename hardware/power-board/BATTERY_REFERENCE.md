# Batería indicada por el propietario

Fuente: captura aportada de la [publicación AliExpress 1005008867815394](https://es.aliexpress.com/item/1005008867815394.html), variante visible `1PCS`. El propietario indica que ésta es su batería. La consulta directa de la página no estuvo accesible; la evidencia es la captura, no una ficha técnica recuperada. No se guarda la captura completa en el repositorio porque contiene información de cuenta ajena al diseño.

| Dato | Evidencia / estado |
| --- | --- |
| Referencia comercial | 955565, visible en título e imagen |
| Tensión nominal anunciada | 3.7 V |
| Capacidad anunciada | 5000 mAh; no medida |
| Energía nominal anunciada | 18.5 Wh, también coincide con 3.7 V × 5 Ah |
| Tipo anunciado | Batería de polímero de litio; coherente con la arquitectura LiPo 1S prevista |
| Cableado mostrado | Dos conductores rojo/negro y conector blanco; no hay tercera conexión NTC visible |
| Conector/polaridad | MPN, paso, corriente y orden de contactos TBD; no identificarlo como JST-PH por apariencia |
| Protección PCM | Parece haber una pequeña placa bajo la cinta superior; presencia, funciones y umbrales no verificados |
| Dimensiones | TBD del pack completo. El resumen automático dice 9.5 × 55 × 65 mm; no se acepta como plano ni medida real |
| Corriente de carga/descarga, picos y temperatura | TBD; la capacidad de 5000 mAh no define esas corrientes |
| Tensión de carga máxima | 4.2 V sigue siendo hipótesis de diseño, pendiente de ficha del pack |

## Efecto en la Power Board

Se sustituye «batería por seleccionar» por «referencia indicada 955565, pendiente de caracterización». Se conserva arquitectura 1S y energía nominal de trabajo de 18.5 Wh, sin prometer autonomía.

No se asume NTC integrado accesible por el conector de dos cables. Proponer termistor externo en contacto térmico con el pack, con conexión separada al charger y montaje por definir; no puentear TS como solución final sin resolver supervisión térmica. La temperatura de la PCB de potencia no equivale necesariamente a la celda.

No retirar protección de la Power Board suponiendo que el pack incluye PCM. Confirmar la protección del pack y coordinar umbrales/recuperación antes de decidir si hace falta protección adicional. Cargador, corriente de carga, límites de descarga, conector y boost siguen pendientes de cierre eléctrico.

Para mecánica, medir pack completo con cinta/placa de protección, salida de cables y conector; contemplar tolerancias y expansión de la celda. No modificar reserva, carcasa ni contorno de PCB a partir del código 955565 o del resumen automático de la tienda.
