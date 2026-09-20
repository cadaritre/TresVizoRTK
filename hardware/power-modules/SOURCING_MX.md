# Compra de componentes desde México

> Actualización mecánica: para la variante de integración revisada, la [BOM mecánica](../../mechanical/MECHANICAL_BOM.md) sustituye los tornillos de panel avellanados por 2 M3×8 ISO7380 de cabeza botón y define los M2 con cabeza ISO4762 Ø3.8×2. El resto de esta página conserva la consulta comercial original; no es una compra ni una verificación de stock posterior.

Consulta del **20 de septiembre de 2026**. Precios publicados por unidad, antes de envío y cargos que correspondan. Existencia web no garantiza inventario en una sucursal de Chihuahua. No se realizó ninguna compra.

| Pieza y cantidad | Dónde conseguirla | Precio observado | Resultado |
| --- | --- | --- | --- |
| 1 pulsador AU-101 | [Steren México](https://www.steren.com.mx/micro-switch-de-push-con-4-terminales.html) | **$2 MXN** | En stock web. Momentáneo NA de cuatro terminales; dos pares internamente comunes. Verificar continuidad. Cotas no publicadas: cartucho mecánico ajustable. |
| 1 LED-5/RGB | [Steren México](https://www.steren.com.mx/led-de-5-mm-rgb.html) | **$5 MXN** | En stock web. Ánodo común; Ø5, longitud de cuerpo publicada 8.45. Sustituye al RGB Adafruit del presupuesto anterior. |
| 1 PowerBoost 1000C **2465** | [DigiKey México, 1528-1349-ND](https://www.digikey.com.mx/es/products/detail/adafruit-industries-llc/2465/5356834) | **$19.95 USD** | 279 en stock al consultar. Venta mediante distribuidor para México; no significa almacén local ni envío incluido. |
| Alternativa del mismo 2465 | [Newark México, 98Y0120](https://mexico.newark.com/adafruit/2465/powerboost-1000-lipo-charger-5v/dp/98Y0120) | $20.53 USD | 6 en stock al consultar. Elegir un solo proveedor para este módulo. |
| 1 USB-C + switch TS3USB30 **5871** | [DigiKey México, 1528-5871-ND](https://www.digikey.com.mx/en/products/detail/adafruit-industries-llc/5871/22596394) | **$3.95 USD** | 85 en stock al consultar. Es la placa comercial cuyos cuatro agujeros usa el panel. |
| 1 encendido electrónico **PRT-26993** | [SparkFun, versión JST 2 mm](https://www.sparkfun.com/sparkfun-soft-power-switch-jst-2mm.html) | **$7.32 USD** | En stock en fabricante. **No encontré stock mexicano confirmado**; considerar importación. Su [política de envío internacional](https://www.sparkfun.com/support) describe transportistas y cargos adicionales; costo/plazo a la dirección final no cotizado. |

**Base seleccionada: $31.22 USD en los tres módulos + $7 MXN en pulsador/RGB.** No convertir esa suma en un total entregado: faltan envíos, importación cuando corresponda, cableado, fusibles, resistencias, transistores, óptica y tornillería. Conviene agrupar 2465 y 5871 en el mismo pedido de DigiKey. El envío separado de SparkFun puede pesar más que su placa.

La compra de Steren reemplaza únicamente pulsador y RGB; el AU-101 acciona BTN/GND del módulo electrónico, no interrumpe directamente la corriente del GNSS.

## Mercado Libre y AliExpress

La [publicación mexicana de PowerBoost AF-2465 por Sandorobotics](https://www.mercadolibre.com.mx/cargador-powerboost-1000--version-micro-usb-arduino/up/MLMU976897609) sí identifica el producto, pero el resultado consultado indica **“no está disponible por el momento”**. No se usa como oferta en stock ni se inventa precio. El AF-2030 de ese vendedor es la versión básica y no sustituye el cargador 1000C.

Se encontraron módulos genéricos “UPS 15 W / 3 A” y combinaciones TP4056/elevador en Mercado Libre, pero sin evidencia suficiente para trasladar a ellos el power-path, apagado y ausencia de alimentación inversa de esta propuesta. El [módulo TP4056 USB-C vendido por UNIT en Mercado Libre](https://www.mercadolibre.com.mx/modulo-tp4056-usb-c-carga-18650-con-proteccion-cable-usb/p/MLM74619274) es un cargador de celda; no es por sí solo un USB de datos ni un reemplazo completo de los tres módulos.

**AliExpress no pudo verificarse:** el acceso fue bloqueado por la política de navegación de esta sesión. No se publican precios, enlaces de compra ni existencias de AliExpress como si se hubieran comprobado.

El biestable que ya posee el proyecto sigue siendo candidato para reutilizar. Hace falta identificar la placa y sus señales antes de asignarle el apagado por firmware y forzado del PRT-26993. No se exige comprar otro sólo para fijar el diseño de la cara del panel.

## Consumibles y especificaciones para pedir localmente

| Elemento | Cantidad inicial / condición |
| --- | --- |
| Tornillos USB | 4 M2 × 5, cabeza compatible con zona libre Ø4 del módulo; pilotos impresos Ø1.7. Probar roscado y apriete. |
| Tornillos cartucho | 2 M2 × 8, cabeza hasta Ø3.6 para la reserva modelada. |
| Tornillos panel | 2 M3 avellanados 90°, cabeza ≤Ø5.6; longitud según la tuerca/boss conservada del case. |
| Cable USB 2.0 de datos interno | USB-C macho compacto hacia Tiny-Adapter; conservar par trenzado/apantallado. El enchufe modelado es una reserva, no una referencia de compra ya seleccionada. |
| Cable USB exterior | Sobremolde que quepa en el rebaje frontal 14 × 6.5. Comprobar ambas orientaciones. |
| NPN y resistencias | Según [WIRING](WIRING.md); seleccionar pinout del transistor real, termoencogible y arnés soldado/aislado. |
| Fusibles y cable de potencia | Según WIRING, tras medir picos y verificar batería. No sustituir un fusible por una protección de celda. |
| Difusores / guía de carga | Dos piezas translúcidas según STL; guía desde los LEDs del cargador. Trayectoria/longitud y brillo aún por probar. |

Los consumibles de esta última tabla no tienen una oferta ni precio verificados en esta consulta; son requisitos de montaje, no una cotización cerrada. El [CAD del panel](../../mechanical/panel-modules/README.md) contiene los soportes y las holguras para prototipar.
