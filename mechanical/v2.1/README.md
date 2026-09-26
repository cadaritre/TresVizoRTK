# TresVizo V2.1 — más grande, trineo rígido y seguros que sí coinciden

Revisión de [V2](../v2/README.md) pedida por el propietario después de probarla:
15 mm más ancha, 30 mm más alta, un trineo que no se dobla ni se descentra y
los seguros de la bayoneta alineados de verdad.

**Nada de V2.1 se ha impreso ni ensayado.** La geometría es coherente en CAD y
pasa las comprobaciones automáticas; eso no es validación.

## Qué cambió frente a V2

| | V2 | V2.1 |
| --- | ---: | ---: |
| Diámetro exterior | 54 mm | **69 mm** |
| Altura del cuerpo | 106.9 mm | **136.9 mm** |
| Largo útil interior | 84 mm | **114 mm** |
| Material | 101 cm³ | **181 cm³** |
| Tornillos con largo definido | 11 | **13** |
| Rigidez del trineo a flexión | 1 | **11.8×** |

La rigidez es la razón entre los momentos de inercia de la sección del trineo, a
media altura y entre dos filas de ranuras (88 → 1039 mm⁴). Es una cuenta sobre el
CAD con el mismo material, no un ensayo.

## El trineo: por qué se doblaba y qué se hizo

En V2 el trineo era una hoja de 3 mm llena de ranuras, sujeta solo por **dos
pestañas** sueltas en la base y libre por arriba hasta que la tapa lo alcanzaba.
Se doblaba con la mano y el cuello de la tapa tropezaba con la repisa del IMU.

| Problema | Solución en V2.1 |
| --- | --- |
| Dos pestañas con juego | **Pie horizontal** que apoya plano en el piso de la base y se **atornilla con dos M3**. Encima, **cuatro pestañas** en sus ranuras, con 0.3 de holgura en vez de 0.35. |
| Hoja de 3 mm | Placa de **4 mm** con **dos alas** en la cara +Y: la sección es una U. Por la cara −Y, **cartelas** entre pie y placa. |
| Arriba quedaba libre | La repisa del IMU entra en el cuello de la tapa con **0.3 de holgura radial** (0.5 en V2), con **chaflán** en su canto y **chaflán de entrada** en el cuello. Al bajar la tapa, el cuello empuja la repisa al centro. Es un cono, así que no depende del ángulo: la tapa todavía gira al cerrar. |
| El espárrago del jalón podía tocar el trineo | Hueco libre de radio 10.5 en el pie y en el canto de la placa. |

**La placa sigue desplazada del eje a propósito.** La batería va contra la cara −Y
y queda centrada, porque es lo único que pasa por el collar de la bayoneta. Lo
que tiene que quedar en el eje es el IMU, y ahí sigue, con su marca pasante y
±1.5 mm de ajuste.

El trineo queda perpendicular por el pie, ubicado por las cuatro pestañas y
apretado por los dos tornillos, con lo que no le queda juego. Girado 180° no
entra: la placa caería en y = −7.

## Los seguros de la bayoneta

**Fallo de V2:** base y tapa se dibujaban en la posición de **entrada** de la
bayoneta. Al cerrar giran **28.7°** (la entrada tiene 2° de más y la holgura
suma 0.7, no son los 30 de `tope_grados`). El barreno del seguro de cada una
acababa a 28.7° del que tiene el tubo y el tornillo no entraba. Comprobado sobre
los STEP de V2: al girarlas hasta el tope, el núcleo del tornillo choca con la
base y con la tapa.

**En V2.1** base, trineo y tapa se dibujan **cerrados**: los dientes están contra
el fondo de su ranura y el seguro de las tres piezas cae a 193°, donde está el
del tubo. `capacity_check.py` pasa un tornillo recto por los tres y exige que su
núcleo no toque nada y que su rosca muerda plástico.

**Otro fallo heredado, también corregido:** la lista de tornillería elegía un
M3×14 para la base y un M3×10 para la tapa que pasaban 0.8 y 1.3 mm del fondo
del piloto y tenían que abrirse paso en plástico macizo. Los pilotos son ahora
más profundos y `bom.py` elige el tornillo más largo que cabe.

## Qué cabe

Todo lo que va en el trineo tiene que pasar por el collar de la bayoneta
(radio 28.5), porque el tubo baja por encima al montar.

| | Cota | Holgura en el collar |
| --- | --- | ---: |
| Trineo | radio máximo 27.9 | 0.6 mm |
| Batería 955565 nominal | 9.5 × 55 × 65 | **0.56 mm** en las esquinas |
| Batería, peor caso documentado | 10 × 55.5 × 68 | **0.29 mm** |
| Carrier UM980, entre las alas | 11 × 32 × 52 | 2.85 mm (hueco entre alas 41.8) |

La batería **cabe, pero justa**. La envolvente de `components.json` con margen de
hinchazón (13 × 58) no pasa: si la bolsa se hincha, no sale sin desmontar.
Medir la batería real antes de imprimir.

## Montaje

1. Inserto del jalón en la base (ver el pendiente de abajo).
2. Trineo sobre la base: cuatro pestañas en sus ranuras y los **dos M3 del pie**.
   Van antes que la batería porque quedan debajo de ella.
3. Batería contra la cara −Y, placas en la cara +Y entre las alas, con brida.
4. Tubo desde arriba, dientes por las entradas, **girar hasta el tope** y M3 del
   seguro de la base.
5. Tapa: el cuello recoge la repisa del IMU; girar hasta el tope y M3 del seguro.

## Pendiente que sigue impidiendo el montaje

Viene de V2 y **no se tocó**: la brida del inserto del jalón (Ø36.5) no pasa por
ninguna de las dos aberturas de su alojamiento (Ø18). Hay que decidir cómo se
mete antes de imprimir la base. Está en `_PENDIENTE_montaje` de
[`parameters.json`](parameters.json).

## Piezas

| Archivo | Qué es |
| --- | --- |
| `01-base-rosca.stl` | Base. Captura el inserto 5/8", ranuras de las cuatro pestañas y pilotos del pie. |
| `02-tubo-logo.stl` | Tubo: logo grabado, dos paneles, barrenos de accesorios y líneas de diseño. |
| `03-tapa-antena.stl` | Placa superior: antena HA-901A por fuera, chaflán de entrada en el cuello. |
| `04-trineo-universal.stl` | Trineo: pie atornillado, placa en U, rejilla, repisa del IMU. |
| `05-tapa-panel.stl` | Panel principal: USB, botón y dos LEDs. |
| `06-tapa-panel-aux.stl` | Panel auxiliar: USB-C hembra. |

La tornillería está en [BOM-TORNILLERIA.md](BOM-TORNILLERIA.md), generada por
`bom.py`.

## Regenerar

```sh
python mechanical/v2.1/regenerate.py
```

Localiza FreeCAD y funciona también en macOS, donde el Python de FreeCAD
necesita su carpeta `lib`. Ejecuta el reparto angular, construye, exporta y
comprueba sólidos, mallas, interferencias, capacidad y seguros. Sale con
código distinto de cero si algo falla.

Para verlo con colores, abrir `view_v2_1.py` desde la interfaz de FreeCAD.

## Límites

- **Sin imprimir ni ensayar.** Sin datos de resistencia, ajuste, temperatura ni
  estanqueidad.
- La **holgura de 0.3** de las pestañas y de la repisa supone una impresora que
  saca las cotas a ±0.1. Si la tuya cierra los huecos, sube `holgura` en
  `pestanas` y `holgura_cuello` en `imu`.
- La **captura del inserto sin tornillos**, la **bayoneta impresa** y el
  **roscado en plástico** siguen sin ensayo, igual que en V2.
- La antena sigue siendo la HA-901A atornillada por fuera. La opción con antena
  de topografía dentro de un domo está en
  [`../option-oem-dome`](../option-oem-dome/README.md).
