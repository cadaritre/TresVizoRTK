# Estuche del receptor (carry-case): rígido tipo Pelican, todo impreso

> **Estado:** geometría generada con scripts y comprobada en FreeCAD 1.1.3 contra el modelo
> real de la carcasa V3.0 (piezas 01–10, con las bandas de TPU) y la antena HA-901A. Primera
> versión del 12-10-2026. **No se ha impreso ni montado nada.** Rama `hw/compact-v03`.
> Resultados en [Verificaciones](#verificaciones).

> **Antes de imprimir todo:**
> 1. **Imprimir una prueba de bisagra y de cierre:** un tramo de la base y de la tapa con dos
>    nudillos, un perno 07, un cierre 03 y su perno 08. Probar:
>    - que los pernos entren y que su punta trabe;
>    - que el cierre haga clic y no se abra solo.
>
>    El modelo comprueba sólidos rígidos: no sabe cuánto se doblan la uña del perno ni el labio de la junta.
> 2. **Probar la junta de TPU** en un tramo, con el TPU que se vaya a usar: cuánto cuesta cerrar y si sella.
>    Si cuesta demasiado, adelgazar el labio (`seal.lip_thickness`).
> 3. **Probar el forro con las letras** en un recorte de la tapa: que las letras entren por dentro
>    y queden a ras.

Estuche pequeño para llevar el receptor Meridian V v0.3 con su antena y, aparte, el cargador y
extras. Lleva el logo de TresVizo y "MeridianV / TRIPLE BAND / RTK RECEIVER" en la tapa, con
letras de TPU azul.

Sin tornillería: bisagras y cierres con **pernos impresos** de punta partida, como los estuches
"rugged box" imprimibles. Esos usan pernos impresos, trozos de filamento o piezas a presión, y
junta de TPU (ver por ejemplo
[Rugged Box (Parametric)](https://printables.com/model/258431-rugged-box-parameterizable) y
[Super Customizable Rugged Box](https://makerworld.com/models/788747)).

Medidas y notas de cada decisión en [parameters.json](parameters.json).

## Medidas

- **Por fuera:** 172 × 140 × 66.5 (cuerpo). Con costillas, cierres, bisagra, candado y argolla:
  183.5 × 164.5 × 66.5.
- **Union base–tapa:** en z 44.5. La base tiene 41.5 de hondo por dentro y la tapa 18.5.
- **Receptor:** acostado delante, a lo largo del lado largo, con la pantalla hacia arriba, la
  base con la tuerca a la izquierda y la antena a la derecha. Con la antena mide **156.8**
  (116 del cuerpo + 40.8 de la HA-901A). Entre sus extremos y el reborde interior del canto
  quedan 2.6.
- **Compartimento de extras:** detrás, 163 × 54.5 × 60 de alto, partido por un tabique bajo en x 14.
  - A la derecha, 65.5 × 54.5 para el cargador.
  - A la izquierda, 93.5 × 54.5 para el cable enrollado, un adaptador o una llave.
  - En el tabique, 4 ranuras para microSD.

## Piezas

| Pieza | Material | Cant. | Volumen | Peso |
|---|---|---|---|---|
| 01-base | PA12-HP negro (MJF) | 1 | 194.6 cm³ | ~197 g |
| 02-lid (tapa) | PA12-HP negro | 1 | 122.9 cm³ | ~124 g |
| 03/04-latch (cierres) | PA12-HP negro | 2 | 2.8 cm³ c/u | ~3 g c/u |
| 07-hinge-pin (perno de bisagra) | PA12-HP negro | 2 | 0.8 cm³ c/u | ~0.8 g c/u |
| 08-latch-pin (perno de cierre) | PA12-HP negro | 2 | 0.4 cm³ c/u | ~0.4 g c/u |
| 05-seal-tpu (junta de labio) | TPU | 1 | 3.1 cm³ | ~4 g |
| 06-liner-tpu (forro con las letras) | TPU azul #008AFC | 1 | 44.8 cm³ | ~54 g |

Total **325 cm³ de PA12 (~329 g) y 48 cm³ de TPU (~57 g): unos 386 g**. MJF imprime macizo, así que el
peso es el volumen por la densidad (1.01 y 1.2). En FDM, con relleno, la base y la tapa pesarían menos.

## Cómo va

### Receptor: cuna con holgura

Costillas en U a lo ancho del hueco, en z del receptor. El receptor **no queda justo** (pedido del
propietario):

- **Cuatro bajo las bandas de TPU**, con R 30.5: 0.8 más que la banda.
  - El receptor apoya en el fondo y le quedan 0.8 a los lados.
  - La boca mide 60.8 para 59.4: entra derecho.
- **Dos entre las bandas**, contra el tubo de Ø56: le quedan 1.0 a los lados y 0.5 por debajo.
  - No lo tocan. Solo hacen de tope a lo largo contra los cantos de las bandas, con **1.0 de juego hacia cada lado**.
- **Una bajo la antena**, con 1.5 a los lados y 0.75 por debajo. La antena no carga nada: la
  costilla solo evita que cabecee si el estuche se cae.

Lo que lo sujeta es el **forro de TPU de la tapa**: dos almohadillas aprietan 0.5 los hombros de
las bandas. Tienen un hueco en medio para no tocar la pantalla, la tecla ni el LED.

Entre las costillas del medio quedan unos 11 a cada lado del tubo para meter los dedos. El tabique
de atrás tiene una muesca en ese tramo.

### Bisagra con pernos impresos

Dos tramos de 60 con 5 nudillos de Ø10, alternados: base, tapa, base, tapa, base. El eje va 7 por
fuera de la pared.

- **Perno 07:** Ø4, con cabeza de Ø7.5 que entra en un rebaje del nudillo de fuera.
- **Agujeros:** de 4.3 en la base y de 4.4 en la tapa, que es la que gira.
- **Punta partida:** ranura de 1.2 × 8 y uña de Ø4.8.
  - La uña se cierra al pasar por los nudillos y se abre al salir en el rebaje del último nudillo: queda trabada.
  - Para sacarlo, apretar las dos mitades de la punta con unas pinzas y empujar.
- **Apertura:** la tapa abre hasta 180 grados sin tocar nada.

### Cierres

Un cierre por lado, de una pieza, que gira sobre un perno impreso (08, Ø3.5, de punta partida
como el de la bisagra). El perno pasa por las dos costillas de la base que lo flanquean.

- **Sobre centro:** el gancho apoya en el canto de fuera del tope de la tapa, 3.9 por fuera del
  eje. El empuje del labio de la junta lo aprieta contra el tope y lo mantiene cerrado.
- **Para abrirlo:** jalar la pestaña de arriba. El gancho hunde la tapa como máximo **0.46**
  antes de soltar (medido en el modelo), a los 16 grados, y se nota el clic.
- **Para cerrarlo:** el chaflán de la punta empuja la tapa hacia abajo.

### Junta de labio (05, TPU)

- **Tira:** de 3.0 × 1.0, entra a presión en el fondo de la ranura de la tapa.
- **Labio:** de 0.9 × 2.6, inclinado 20 grados.
- **Cerrado:** la lengüeta de la base (2.0 × 2.15) dobla la punta del labio 0.6. El labio
  aprieta la tapa contra los cierres y las bisagras.
- **Cantos:** quedan a 0.4 y no se tocan.

Sella contra polvo y salpicaduras. **No es estanca** como un Pelican con junta tórica: para eso
haría falta un cordón de silicona comprado.

### Rótulo: letras de TPU en una sola pieza

Bloque discreto de 62 × 49.4 en un panel rebajado 0.8 en el centro de la tapa:

- el logo completo de TresVizo (hexágono con el 3 y VIZO), de 40 de ancho;
- **MeridianV**, de 62;
- **TRIPLE BAND / RTK RECEIVER** en dos líneas de 4.4 de alto de mayúscula.

La fuente es Ubuntu Bold, la que trae FreeCAD (Ubuntu Font Licence).

Cómo se hace:

- **Ventanas:** las letras y el logo están **calados** en el techo de la tapa.
- **Forro (06):** una placa de TPU azul de 1.6 que va pegada al techo por dentro. Lleva las
  letras en relieve, que entran **desde dentro** por las ventanas y quedan a ras por fuera (0.1
  de más). Son **una sola pieza**: no hay que pegar letra por letra.
  - Holgura de 0.05 por lado en la tapa y en el forro: 0.1 entre la letra y la ventana.
- **Sujeción:** el forro entra justo en la tapa y lo retienen 6 topes de 0.6.

**Lo que se ve:** como las letras entran por dentro, cada contraforma es una isla del techo y
necesita un **puente** que la una al resto. Son las de la e, a, d, R, P, B, A, D, el interior del
hexágono y la O.

- Hay 14 puentes, de 0.9 de ancho en el logo y MeridianV y de 0.7 en las líneas chicas.
- Se ven como una raya negra fina que corta el trazo, al estilo de las letras de plantilla (esténcil).
- La otra opción, sin puentes, son letras sueltas pegadas una por una: unas 40 piezas.

### Detalle rugged

- **Banda en la unión:** de 1.5 alrededor, en la base y en la tapa.
- **Costillas verticales en la base:** de 4 × 3.
  - Los cierres van entre dos de ellas, que además son sus orejas.
  - Dos en cada costado.
  - Dos atrás, que sostienen las bisagras, y una bajo el candado.
- **Costillas de la tapa:** de 2.5, alineadas con las de la base.
- **Esquinas:** defensas de 1.6 en las cuatro, en la base y en la tapa.
- **Costados:** paneles rebajados.
- **Abajo:** un borde de 8 que hace de pie y dos patines, con el centro rebajado.
- **Candado:** orejas al frente, con un agujero de 6.
- **Argolla:** en el costado izquierdo, para un mosquetón o una correa.

## Cómo se arma

1. **Junta:** meter la tira de la junta (05) en la ranura de la tapa, con el labio hacia abajo, empujándola con el dedo todo alrededor.
2. **Forro:** meter el forro (06) en la tapa con las letras hacia el techo, haciendo coincidir cada letra con su
   ventana. Apretar hasta que pase los topes y las letras queden a ras por fuera. Si queda flojo,
   unas gotas de pegamento de contacto en el borde.
3. **Bisagra:** poner la tapa sobre la base y meter los dos pernos de bisagra (07), cada uno desde su extremo de
   fuera, hasta que la cabeza entre en su rebaje y la punta trabe del otro lado.
4. **Cierres:** poner cada cierre (03, 04) entre sus dos costillas y meter su perno (08) desde el lado del centro del estuche.

## Impresión

- **PA12-HP negro (MJF), como la carcasa V3.0:** base, tapa, cierres y pernos. MJF no necesita
  soportes ni orientación especial.
  - Los pernos son piezas chicas (Ø4 × 60 y Ø3.5 × 36): pedirlos aparte o junto con lo demás.
- **TPU:** junta y forro. El forro tiene que ser **azul #008AFC**, como las bandas del receptor.
  - Para TPU por FDM sin soportes:
    - `stl/05-seal-tpu-para-imprimir.stl`: la tira contra la cama y el labio hacia arriba;
    - `stl/06-liner-tpu-sin-almohadillas-fdm.stl`: la placa contra la cama y las letras hacia arriba;
    - `stl/06b-liner-pads-tpu-fdm.stl`: las 4 almohadillas aparte, para pegarlas.
  - En polvo (MJF o SLS) vale `stl/06-liner-tpu.stl` de una pieza.

Archivos en [generated](generated): `TresVizo-CarryCase.FCStd` (con el receptor de referencia), `step/`, `stl/`,
`model-index.json` y `check.json`.

## Verificaciones

`check_carry_case.py`, con el modelo real de V3.0 (piezas 01–10 y la antena):

- **Cerrado:** no choca nada salvo lo que se busca:
  - el labio de la junta doblado por la lengüeta (335 mm³);
  - las almohadillas del forro sobre las bandas (551 mm³, 0.5 de apriete).
- **Receptor:** apoyado, desplazado ±0.75 a lo largo y 0.5 de lado (subido 0.4), no toca la
  base. Con 1.5 a lo largo topa con las costillas del medio, que es lo que tienen que hacer.
  A la base le quedan 0.75 bajo la antena.
- **Tapa:** de 5 a 180 grados, con los cierres abiertos a 60, no toca la base, los pernos, los
  cierres ni el receptor.
- **Cierres:** de 0 a 60 grados no tocan la base. El gancho hunde la tapa como máximo 0.46 (a los
  12 grados) y suelta a los 16.
- **Pernos:** puestos, no chocan con nada.
- **Rótulo:** ninguna pieza con trazo de menos de 0.8.
- **Mallas:** todas las piezas son un sólido válido con la malla cerrada.

**No se comprobó** (pendiente de la impresión de prueba):

- la fuerza de la uña de los pernos;
- cuánto empuja de verdad el labio de TPU, ni si sella;
- la fuerza del clic de los cierres;
- el ajuste real de las letras en las ventanas, con las tolerancias de MJF y del TPU.

## Regenerar

```
PYTHONPATH=/Applications/FreeCAD.app/Contents/Resources/lib \
  /Applications/FreeCAD.app/Contents/Resources/bin/python build_carry_case.py     # ~1 min
PYTHONPATH=/Applications/FreeCAD.app/Contents/Resources/lib \
  /Applications/FreeCAD.app/Contents/Resources/bin/python check_carry_case.py     # ~2 min
```
