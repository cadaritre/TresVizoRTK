# Opción de diseño: antena de topografía dentro de un domo

**No es una V3.** Es otra posibilidad sobre [V2.1](../v2.1/README.md): cambia
solo la tapa de antena por una **tapa-plato** que lleva dentro una antena de
topografía ArduSimple, y añade un **domo** que la cubre. Base, tubo, trineo y
paneles son los de V2.1 sin cambios.

**Nada de esto se ha impreso ni ensayado.** La geometría es coherente en CAD y
pasa las comprobaciones de `build_dome.py` contra el STEP real de la antena;
eso no es validación.

## Por qué

La HA-901A es una copia de una hélice de dron: su centro de fase, según el
fabricante del original, solo es repetible «a nivel de centímetro». La
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
agua y el cuenco a 35° deja la cabeza unos 12 mm más baja que a 45°. Ninguna cara
exterior lleva soportes; la comprobación lo mide en el domo. El escalón donde
apoya el domo cuelga 2.8 mm en la impresión boca abajo, pero queda tapado por la
falda.

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
   caja hacia −Y. Bajarlo por el cuenco dejando una curva amplia, sin doblarlo
   en seco, y dentro del tubo **por el lado +Y**, por fuera de la repisa del
   IMU, hasta el UM980. Son 20 cm de cable.
3. Antena sobre el aro: seis **M3×8 cabeza botón** desde arriba, que roscan en
   las torres.
4. Junta tórica en su ranura: **sección 2 mm, diámetro interior de 130 a 133 mm**
   (NBR).
5. Domo: bajarlo sobre la junta hasta que la falda apoye en el escalón. Tres
   **M3×10 cabeza botón** radiales. Van por debajo de la junta y en pilotos
   ciegos, así que el agua no encuentra camino al interior.

## Lo que se comprueba al generar

`build_dome.py` sale con código distinto de cero si algo falla. Con el STEP real
de la antena:

- las dos piezas son sólidos únicos y válidos, con mallas cerradas;
- **cero interferencias**: tapa-plato con tubo y trineo, domo con tapa-plato y
  tubo, antena con tapa-plato y domo;
- el elemento radiante queda al menos a 6 mm del domo;
- el tornillo del seguro atraviesa el tubo y entra en el piloto de la tapa-plato
  sin tocar pared, con plástico para la rosca;
- el domo no pide soportes por fuera.

El resultado queda en [`generated/checks.json`](generated/checks.json).

## Pendientes y límites

- **Sin imprimir ni ensayar.** Ajuste de la junta, estanqueidad, resistencia a
  caídas y temperatura: sin datos.
- **Alimentación de la antena:** la ArduSimple admite **3 a 5.5 V**; la HA-901A
  admitía 3–16 V. Comprobar la tensión que da la carrier del UM980 en su SMA.
- **La junta depende de la impresora:** con ±0.2 mm en diámetros, el prensado va
  del 12 al 32 %. Probar con una junta antes de fiarse.
- **El recorrido del cable no está modelado:** el STEP lo dibuja recto y fuera
  del equipo. El cuenco deja espacio de sobra, pero hay que comprobarlo con el
  cable real.
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

Para verlo con colores: abrir `view_dome.py` desde FreeCAD.
