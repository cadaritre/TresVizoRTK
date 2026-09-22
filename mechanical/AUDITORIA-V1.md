# Auditoría de la carcasa V1

Revisión del 22 de septiembre de 2026, en rama aislada `worktree-case-v2-simplificado`.
No modifica V1. Mediciones tomadas de los STL entregados con
`mechanical/audit/measure_stl.py`, que no necesita FreeCAD.

## Lo que hay hoy, medido

| Pieza | X | Y | Z | cm³ |
| --- | ---: | ---: | ---: | ---: |
| 01 cuerpo | 74.0 | 74.0 | 138.2 | 75.2 |
| 02 chasis-base | 64.3 | 64.3 | 163.6 | 74.7 |
| 03 cuna batería/IMU/power | 60.6 | 37.2 | 122.3 | 55.7 |
| 04 tapa antena | 74.0 | 74.0 | 23.6 | 17.6 |
| 05 panel USB/botón | 28.0 | 25.5 | 53.0 | 3.9 |
| 06 prensa IMU | 30.0 | 10.0 | 4.0 | 1.1 |
| 07 actuador botón | 13.0 | 13.0 | 3.4 | 0.3 |
| 08 cartucho botón | 24.1 | 13.0 | 7.2 | 0.9 |
| 09 + 10 difusores | 5.5 | 5.5 | 3.6 | ~0 |
| 11 plantilla IMU | 35.0 | 20.0 | 21.3 | 1.7 |

**Envolvente: Ø74 × 164 mm. 231 cm³ de material, ~143 g en PETG a relleno medio.
Diez piezas permanentes más una plantilla, 19 tornillos, 13 tuercas, 10 bridas y un
inserto McMaster.** 51 232 triángulos en total.

## Hallazgos

### 1. El modelo no expresa intención: parchea un sólido heredado

`build_v1.py` no construye la carcasa, la **corrige**. Abre un `.FCStd` intermedio
derivado de A5 y le aplica 221 líneas de booleanas. De ahí salen constantes como:

```python
outer = Part.makeCone(36.5545454545, 37.1, 12, V(0,0,88)).fuse(
        Part.makeCone(37.1, 37.1+43/88, 43, V(0,0,100)))
```

Ese `36.5545454545` no es una decisión de diseño: es el resultado aritmético de
reconstruir una pared que ya existía. Consecuencia directa: **cambiar la cota de un
componente no se propaga a nada**. Hay que volver a calcular a mano dónde cortar.

Es la causa raíz de lo que notaste. No es que el diseño sea "ajustado" por elección;
es que está compuesto de recortes calculados contra una geometría concreta, y
cualquier pieza distinta obliga a rehacer los recortes.

### 2. Alojamientos exactos sobre cotas que el propio repo declara no verificadas

Esto es lo más serio. `COMPONENT-DIMENSIONS.md` es explícito sobre lo que no se sabe,
y aun así el CAD tiene bolsillos ajustados:

| Componente | Lo que el repo admite no saber | Lo que el CAD asume |
| --- | --- | --- |
| Carrier UM980 | «No se encontró diámetro, coordenadas ni distancias entre centros de sus cuatro agujeros» | Reserva 36×12×64 con apoyos de borde y bridas |
| microSD | Patrón «de la familia», identidad del lote no demostrada | Ranuras y retención a medida |
| Batería | Nominal 9.5×55×65; una hoja real de otro fabricante del mismo código da **10×55.5×68** | Reserva 56×12×69 |
| Antena HA-901A | El `README.md` raíz dice «La HA-901A mencionada inicialmente **no está confirmada**» | Tres agujeros M2.5 en círculo Ø26.6 ya taladrados en la tapa |
| BMI088 | «No usar el centro geométrico de la placa como supuesto centro del sensor» | Asiento con datum, resuelto con plantilla ajustable |

El caso del BMI088 está bien resuelto: se admite la incertidumbre y se compensa con
plantilla y ajuste. **El resto no.** La antena es el ejemplo más caro: si el modelo
que llegó no es HA-901A, la tapa se reimprime entera.

### 3. Holguras menores que la variación admitida en el mismo documento

Las bandejas power dan **0.4 mm** de holgura nominal a la placa de respaldo. Pero el
propio `INTEGRATION_REVIEW.md` documenta dos envolventes distintas para el mismo
módulo: 23×10×45 nominal y 26×8×47 alternativa. Es decir, el documento admite hasta
**3 mm** de variación entre versiones del mismo producto y el alojamiento ofrece 0.4.

Lo mismo con el USB: «admite el sobremolde compacto comprobado de 13×5.5 mm; no
equivale a cualquier sobremolde de mercado». Un cable distinto no entra.

### 4. Pared local de 1.25 mm

El alivio inferior deja «pared local mínima de aproximadamente 1.25 mm». En PETG con
boquilla de 0.4 son tres extrusiones. Para una pieza que va roscada a un jalón y
recibe el par de apriete de campo, es delgado. Está respaldado por el collar de base,
pero conviene no depender de eso.

### 5. Complejidad de montaje

- **8 pasos con direcciones obligadas** (+Y, −Y, +Z) y orden estricto.
- **5 combinaciones de tornillo**, dos llaves Allen.
- Tuercas que «hay que sostener durante el primer roscado».
- **Cambiar la batería exige retirar cuerpo y cuna.** Es el consumible que más se
  manipula y es de los accesos más profundos.
- Las 10 bridas se cortan y se reponen en cada servicio.

### 6. El volumen se va en apilar

La altura de 164 mm sale de apilar casi todo en serie sobre el eje: inserto (10) +
batería (69) + electrónica + antena (41). Batería y carrier UM980 son dos losas
planas de ~11 mm; **puestas lado a lado en vez de en serie** ocupan unos 23 mm del
diámetro y liberan decenas de milímetros de altura.

En diámetro pasa lo contrario: el paso interior es Ø61 y el exterior Ø74, o sea
6.5 mm por lado entre pared y funciones. La batería de 55 de ancho ya obliga a un
interior de ~Ø59 mínimo, así que **el diámetro interior casi no se puede bajar, pero
el exterior sí**.

### 7. Reproducibilidad rota fuera de la máquina del autor

`regenerate.sh` tiene la ruta absoluta del FreeCAD del propietario:

```sh
freecad_python='/Users/cadaritre/Applications/FreeCAD-1.0.2.app/Contents/Resources/bin/python'
```

Y es `#!/bin/zsh`. No corre en Windows ni en otra Mac con FreeCAD en otro sitio. El
baseline cacheado sí es regenerable desde el A5 del repo, así que el problema es solo
el arranque, pero hoy nadie más puede regenerar el modelo.

### 8. El logo vive dentro de geometría heredada

El objeto se llama «01 / cuerpo con logo». El relieve está fundido en el BREP del
cuerpo A5; no hay fuente vectorial ni paramétrica. Reusarlo obliga a arrastrar ese
sólido o a reconstruirlo desde el arte original.

## Lo que está bien y hay que conservar

No todo sobra:

- **El tratamiento del BMI088.** Admitir que no se conoce la posición del sensor y
  resolverlo con plantilla de centrado y bloqueo rígido es la decisión correcta, y es
  exactamente el criterio que falta en el resto.
- **La honestidad del `INTEGRATION_REVIEW`**: declara las intersecciones permitidas,
  el muestreo a 1 mm y que nada se ha impreso. No infla resultados.
- **Las bandejas sin patrón de PCB**, con apoyo plano y bridas, en vez de tornillos a
  agujeros supuestos. Ese principio hay que extenderlo a todo.
- Los ejes: FRONT en +Y, antena e inserto en X=Y=0.

## Propuesta para V2

### Criterio

Tres cosas exigen posición exacta: **antena**, **rosca 5/8"** e **IMU** — y el IMU
con ajuste, no con alojamiento ajustado. **Todo lo demás se sujeta, no se encaja.**

Un componente que llegue 3 mm distinto debe seguir montando. Eso significa bahías
dimensionadas al máximo plausible más margen, sujeción por correa o brida sobre
apoyo plano, y cero agujeros a patrones de PCB no verificados.

### Arquitectura propuesta

| Pieza | Función |
| --- | --- |
| 1 · Base con rosca | Captura el inserto 5/8"; interfaz de bayoneta con el tubo |
| 2 · Tubo con logo | Pared exterior, abertura de USB y botón, relieve del logo |
| 3 · Tapa de antena | Bayoneta superior, asiento centrado de antena |
| 4 · Trineo | Chasis interno: bahías de batería, carrier y módulos; asiento del IMU |

**Cuatro piezas impresas en vez de diez.** Cierres por bayoneta de un cuarto de
vuelta en vez de seis tornillos. El trineo entra y sale completo por arriba.

### Tornillería objetivo

| Concepto | V1 | V2 propuesta |
| --- | ---: | ---: |
| Tornillos | 19 | **5** (3 antena M2.5 + 2 prensa IMU M2.5) |
| Tuercas | 13 | **2** (prensa IMU) |
| Combinaciones | 5 | **2** |
| Llaves | 2 | **1** |
| Bridas | 10 | 4–6, solo sujeción de placas |

Los tres M3 del inserto desaparecen si la brida del inserto queda **capturada entre
la base y el tubo** al cerrar la bayoneta, con nervios antigiro que muerden el canto.
Esto hay que ensayarlo: el par de apriete de un jalón es real y si el ensayo falla se
vuelve a los tres tornillos. No lo doy por resuelto.

Los tres M2.5 de la antena los impone la antena. Los dos del IMU conservan el datum y
el ajuste, que es la parte que sí funciona hoy.

### Tamaño: objetivo contra resultado

| | V1 medida | V2 objetivo | **V2 generada** |
| --- | ---: | ---: | ---: |
| Diámetro exterior | 74 mm | ~66 mm | **67 mm** |
| Altura | 164 mm | ~132 mm | **149.4 mm** |
| Volumen de material | 231 cm³ | ~140 cm³ | **162.5 cm³** |

El diámetro y el material salieron cerca. **La altura no**: el objetivo de 132 mm
era aritmética optimista y la geometría real lo desmintió por 17 mm.

La causa es un hallazgo que solo aparece al modelar. Con 58 mm de ancho, ninguna
esquina de la batería puede pasar de |Y| = 10.95 mm dentro de un tubo de Ø62, así
que **la batería tiene que ocupar el centro**: no cabe apoyada en la cara de una
placa diametral, porque su esquina más lejana cae a radio 32.42 contra los 31
disponibles. Eso obliga a desplazar la placa del trineo y a llevar el IMU a una
repisa por encima de la zona de batería, que es la altura que se perdió. La
comprobación está en [`check_battery_fit.py`](v2/parameters.json).

Aun así: **30 % menos de material, 15 mm menos de largo y 7 mm menos de diámetro**,
con 4 piezas en vez de 10 y 5 tornillos en vez de 19. El resultado y sus límites
están en [V2](v2/README.md).

### Lo que no cambia

Exterior cilíndrico, FRONT en +Y, antena e inserto en X=Y=0, datum del BMI088 y el
logo. El logo se reconstruye desde el arte original en
`firmware/esp32/web/assets/tresvizo-logo.png` para que quede paramétrico y deje de
depender del sólido heredado.

## Límites de esta auditoría

- Las medidas salen de los STL entregados, no de piezas impresas. Nada se ha
  fabricado ni ensayado.
- El objetivo de tamaño es aritmética sobre cotas publicadas de componentes que el
  propio repo declara no verificadas. Se confirma midiendo las piezas reales.
- La captura del inserto sin tornillos es una propuesta a ensayar, no una solución
  validada. El par de un jalón puede obligar a conservar fijación mecánica.
- La bayoneta impresa en PETG necesita ensayo de ajuste y de desgaste tras varios
  ciclos. No hay dato de cuántas aperturas aguanta.
