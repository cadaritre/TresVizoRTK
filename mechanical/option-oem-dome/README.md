# Opción de diseño: antena de topografía dentro de un domo

**No es una V3.** Es otra posibilidad sobre [V2.1](../v2.1/README.md): cambia
solo la tapa de antena por una **tapa-plato** que lleva dentro una antena de
topografía ArduSimple, y añade un **domo** que la cubre. Base, tubo, trineo y
paneles son los de V2.1 sin cambios.

**Nada de esto se ha impreso ni ensayado.** La geometría es coherente en CAD y
pasa las comprobaciones de `build_dome.py` contra el STEP real de la antena;
eso no es validación.

## Por qué

La hélice actual lleva en la etiqueta «HA-901A» (foto del propietario del
24-09-2026) y se vende como reemplazo de la Harxon HX-CH7609A, de dron. Para
esa antena, [Harxon declara](https://en.harxon.com/product/detail/d-helix-antenna-hx-ch7609a.html)
una repetibilidad del centro de fase «a nivel de centímetro». La
[ArduSimple OEM Survey Tripleband](https://www.ardusimple.com/product/oem-survey-tripleband-gnss-antenna/)
(AS-ANT3B-OEMSUR-L1L2L5-02SMA-00, 99 €) es una antena de topografía de
triple banda pensada para integrarse dentro de una carcasa: declara ±3 mm de
error del centro de fase, 5 dBi y 1.5 dB de ruido.

## Piezas

| Archivo | Qué es | Cómo imprimir |
| --- | --- | --- |
| `07-oem-antenna-lid.stl` | Tapa-plato: cuello, bayoneta y seguro de V2.1; cuenco a 35°; aro Ø136 con seis torres para la antena, junta tórica y tres torres para los tornillos del domo. | **Boca abajo**, con el asiento de la antena en la cama (sale plano). Soportes solo dentro del cuenco, que no se ve. |
| `08-oem-dome.stl` | Domo: casquete elíptico, pared de 2.5, falda recta con tres pasos de tornillo. | **De pie**, sobre el canto plano de la falda. Soportes solo por dentro: por fuera no los necesita. |

Resto de piezas: las de [V2.1](../v2.1/generated/stl/), menos `03-tapa-antena`.

**Material:** ASA o PC; el PLA se ablanda al sol. El **domo, macizo (100 %)** y de
color claro, sin cargas de carbono ni metálicas y sin pintura metálica.

Los soportes se aceptan donde lo justifica la estética. El domo curvo escurre el
agua y el cuenco a 35° deja la cabeza unos 11 mm más baja que a 45°.

- **Domo:** por fuera no pide ningún soporte; la comprobación lo mide.
- **Tapa-plato:** por fuera quedan tres voladizos cortos que se imprimen **sin
  soporte**: el escalón donde apoya el domo (2.8 mm), un flanco de la ranura de la
  junta (1.25 mm) y la cara de los tres dientes (2.5 mm). Los tres quedan tapados
  al montar.

## Medidas

| | |
| --- | ---: |
| Diámetro de la cabeza | **141.6 mm** |
| Altura total del equipo | **203.3 mm** (V2.1 con HA-901A: 177.7 mm) |
| Cabeza sobre el borde del tubo | 71.4 mm |
| Holgura del elemento radiante al domo | **6.1 mm** en perpendicular, 9.4 mm en la cima |
| Junta tórica | fondo de ranura Ø133.5, falda Ø136.6, prensado nominal 22.5 % |

Las cotas de la antena salen de su STEP oficial,
`AS-ANT3B-OEM-L125-02SMA-00-R01.step` de ArduSimple, leído con FreeCAD:

- plato de Ø130 × 1 mm con seis barrenos de Ø3.2 sobre un círculo de Ø120;
- elemento de Ø95 y 18.55 mm de alto;
- caja octogonal de 89.2 mm y 7.2 mm de profundidad bajo el plato.

El STEP no se incluye en el repositorio porque es de ArduSimple.

## Montaje

1. Tapa-plato sobre el tubo de V2.1, **igual que su tapa**: dientes por las
   entradas, girar hasta el tope y el M3 del seguro (mismo tornillo, mismo
   ángulo).
2. Pasar el SMA del coaxial por el cuenco hasta el tubo. Sale del costado de la
   caja hacia −Y: hacer la curva en U inclinada hacia −X, cruzar bajo la caja
   hacia +Y y bajar por la **muesca +Y de la repisa del IMU** hasta el UM980.
   Con radio de curvatura de **13 mm** no toca nada (comprobado, 145 mm de
   recorrido de los 200); con 14 ya roza.
3. Antena sobre el aro: seis **M3×8 cabeza botón** desde arriba, que roscan en
   las torres.
4. Junta tórica **130 × 2 mm NBR**, engrasada, en su ranura. Se estira un 2.7 %
   y no se sale al bajar el domo.
5. Domo: bajarlo sobre la junta hasta que la falda apoye en el escalón; la
   falda tiene entrada suave y los pasos de tornillo el canto matado para no
   pellizcarla. Tres **M3×10 cabeza botón** radiales. Van por debajo de la junta
   y en pilotos ciegos, así que el agua no encuentra camino al interior.

**Tornillería:** 6 × M3×8 cabeza botón (antena), 3 × M3×10 cabeza botón (domo),
1 × M3×12 cabeza botón (seguro, el mismo de V2.1), junta 130 × 2 NBR.

## Lo que se comprueba al generar

`build_dome.py` sale con código distinto de cero si algo falla. Con el STEP real
de la antena:

- las dos piezas son sólidos únicos y válidos, con mallas cerradas;
- **cero interferencias**: tapa-plato con tubo y trineo, domo con tapa-plato y
  tubo, antena con tapa-plato y domo;
- el elemento radiante queda al menos a 6 mm del domo, y la caja del LNA a más de
  1.5 mm de la tapa-plato (2.8);
- un coaxial de 2.2 mm con radio de curvatura de 13 mm llega de la antena al tubo
  sin tocar tapa-plato, antena, tubo ni trineo;
- el tornillo del seguro atraviesa el tubo y entra en el piloto de la tapa-plato
  sin tocar pared, con plástico para la rosca;
- el domo no pide soportes por fuera.

El resultado queda en [`generated/checks.json`](generated/checks.json).

## Pendientes y límites

- **Sin imprimir ni ensayar.** Ajuste de la junta, estanqueidad, resistencia a
  caídas y temperatura: sin datos.
- **Alimentación de la antena:** la ArduSimple admite **3 a 5.5 V**; la etiqueta
  de la HA-901A dice 3–16 V. Comprobar la tensión que da la carrier del UM980 en
  su SMA.
- **La junta depende de la impresora:** con ±0.2 mm en diámetros, el prensado va
  del 12 al 32 %. Probar con una junta antes de fiarse.
- **El recorrido del cable es un modelo:** se comprueba un camino concreto con
  radio de 13 mm. El cable real puede ir por otro; si su radio mínimo es mayor de
  13 mm, no cabe.
- **Centro de fase:** la antena no trae calibración NGS. El PCO se mide con el
  **domo puesto**, porque el domo también lo mueve.
- Sigue vigente el pendiente del inserto del jalón de V2.1.

## Regenerar

Primero hay que regenerar V2.1, porque esta opción lee sus piezas y alturas.

```sh
export PYTHONPATH=/Applications/FreeCAD.app/Contents/Resources/lib
/Applications/FreeCAD.app/Contents/Resources/bin/python mechanical/option-oem-dome/build_dome.py --antena-step ruta/AS-ANT3B-OEM-L125-02SMA-00-R01.step
```

Sin `--antena-step`, las comprobaciones usan la envolvente medida de la antena.
En Windows o Linux, basta el Python de FreeCAD sin `PYTHONPATH`.

Para verlo con colores: abrir `view_dome.py` desde FreeCAD. El ensamble es
`generated/TresVizo-DomeOption.FCStd`.
