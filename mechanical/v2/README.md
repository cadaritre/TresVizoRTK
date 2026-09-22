# TresVizo V2 — carcasa simplificada

Rediseño desde cero tras la [auditoría de V1](../AUDITORIA-V1.md). Seis piezas
impresas, todos los tornillos roscando en el propio plástico, cero tuercas, e
interior sin alojamientos a medida.

**Nada de esto se ha impreso ni ensayado.** La geometría es coherente en CAD;
eso no es validación.

> ## Pendiente que impide el montaje
>
> **El inserto del jalón no entra en su alojamiento.** Su brida mide 36.5 mm de
> diámetro y las dos aberturas del alojamiento miden 18: no pasa ni por abajo ni
> por arriba, y no hay entrada lateral. V1 lo resolvía con una ventana posterior
> y un pozo de llave; al rehacer la base desde cero esa función se perdió.
>
> Hay al menos tres caminos: abrir el alojamiento por la cara inferior, recuperar
> una ventana lateral como V1, o partir la base en dos piezas. **Decidirlo antes
> de imprimir la base**, porque las tres cambian esa pieza.
>
> La nota queda marcada como `_PENDIENTE_montaje` en
> [`parameters.json`](parameters.json).

## Resultado frente a V1

| | V1 medida | V2 generada |
| --- | ---: | ---: |
| Diámetro exterior | 74 mm | **54 mm** |
| Altura del cuerpo | 164 mm | **106.9 mm** |
| Material | 231 cm³ | **100.9 cm³** |
| Piezas impresas | 10 + plantilla | **6** |
| Tuercas | 13 | **0** |
| Combinaciones de tornillo | 5 | **3** |

**Menos de la mitad del plástico y 57 mm más corto.** El Ø54 es el piso real: no
lo impone la batería sino la **antena**, cuya envolvente de Ø47 no deja bajar de
~Ø53. A este diámetro la batería debe medir como mucho **45 × 8**.

La altura bajó 42 mm al corregir un error de concepto: la antena va montada **por
fuera**, atornillada sobre la cara superior de la tapa. La tapa era un vaso hueco
de 44 mm reservado para meterla dentro, y no tenía ningún sentido.

## Las piezas

| Archivo | Qué es |
| --- | --- |
| `01-base-rosca.stl` | Base. Captura el inserto 5/8" y cierra con bayoneta. |
| `02-tubo-logo.stl` | Tubo: logo grabado, dos paneles, barrenos de accesorios y líneas de diseño. |
| `03-tapa-antena.stl` | Placa superior con los tres pilotos de la antena y el paso del coaxial. |
| `04-trineo-universal.stl` | Chasis interno: rejilla de anclaje, repisa del IMU y marca del eje. |
| `05-tapa-panel.stl` | Tapa del panel principal: USB al ras, botón y dos LEDs. |
| `06-tapa-panel-aux.stl` | Tapa del panel auxiliar: USB-C hembra para ampliaciones. |

## El interior no tiene forma de tus componentes

Rejilla de anclaje universal: ranuras pasantes cada 10 mm en tres separaciones
(12, 22 y 32 mm). Una brida entra por cualquier par y sujeta lo que sea contra el
plano de apoyo. Si cambias de módulo, lo amarras en otro punto y no reimprimes
nada.

La batería va amarrada contra la cara interior de la placa y queda **centrada en el
eje por su propio espesor**. No es una preferencia: con 45 de ancho ninguna esquina
puede pasar de |Y| = 10.9 dentro de un tubo de Ø49, así que la batería tiene que
ocupar el centro y la placa va desplazada 5.5 mm. Lo comprueba
`parameters.json`, nota de `trineo`.

Dos pestañas asimétricas (a +10 y −16 del centro) entran en sus hendiduras de la
base. Dos puntos localizan de verdad e impiden montarlo al revés.

## Lo único con posición definida

| | Cómo se resuelve |
| --- | --- |
| **Rosca 5/8"** | Inserto McMaster capturado entre base y tubo; tres pilotos impresos entran en sus propios agujeros de montaje y toman el par. |
| **Antena** | Se atornilla encima de la tapa con tres M2.5; patrón **paramétrico**. |
| **IMU** | PCB acostado sobre repisa horizontal, elevado en dos separadores, con **±1.5 mm de ajuste en X y en Y** y un **resalte de Ø3 marcando el eje exacto** del cuerpo. |

El resalte del eje es visible con el PCB montado porque este pasa por encima: sirve
para comprobar el centrado al apretar.

## Tornillería

| Comprar | Cantidad | Uso |
| --- | ---: | --- |
| M2.5, ISO 4762 | 3 | Antena, sobre la tapa |
| M2.5×12 | 2 | IMU |
| M3×20 | 1 | Seguro de la base |
| M3×12 | 1 | Seguro de la tapa |
| M3×10 | 4 | Los dos paneles |
| M4 | 2 | Accesorios externos, a discreción |
| McMaster 90611A121 | 1 | Rosca 5/8"-11 UNC |
| Brida 2.5 mm | 4–8 | Sujeción de módulos |

**Cero tuercas.** Todos los tornillos forman su rosca en el plástico. Los pilotos
son de 2.5 para M3 y 3.3 para M4, no 0.1 mm menores que el tornillo: con un piloto
de 2.9 para un M3 no queda material que roscar y el tornillo gira en falso. Son
parámetros; súbelos si tu impresora saca los agujeros estrechos.

## Ampliaciones

El **panel auxiliar** lleva una USB-C hembra sin función asignada, prevista para lo
que montes después. A cada lado hay un **barreno M4 con refuerzo interior** para
colgar radio, powerbank o lo que haga falta; llevan refuerzo porque de ahí va a
colgar peso real y la pared sola son 2.5 mm.

## Regenerar

```bash
python mechanical/v2/regenerate.py --dxf "ruta/al/LOGO.dxf"
```

Localiza FreeCAD solo; `--freecad` fuerza una ruta. Comprueba que cada pieza sea un
único sólido, que las mallas cierren y que no haya interferencias, y devuelve
código distinto de cero si algo falla.

## Límites

- **Sin imprimir ni ensayar.** Sin datos de resistencia, ajuste, temperatura ni
  estanqueidad.
- **La captura del inserto sin tornillos no está validada.** El par de un jalón es
  real. `capturar_sin_tornillos: false` devuelve los tres M3 de V1.
- **La bayoneta impresa no tiene ensayo de ajuste ni desgaste.**
- **El roscado en plástico no está ensayado.** Cuántas veces aguanta un M3 formado
  en PETG antes de barrerse es un dato que falta.
- **La antena no está confirmada.** Su patrón es paramétrico: si llega otra, se
  cambian tres números y se reimprime solo la tapa.
- La forma sigue siendo cilíndrica con detalles, no una silueta esculpida.
