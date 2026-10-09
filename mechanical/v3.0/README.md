# Carcasa V3.0 (exploratoria): tubo compacto para la placa principal v0.3

> **Estado:** geometría generada con scripts y comprobada en FreeCAD 1.1.3 contra la **placa v0.3
> real** (`hardware/main-board/cad/placa-principal.step` y las zonas de clavijas de
> `kicad/plugs.json` v0.3), la carrier BDLX modelada desde una foto, el pack 1S2P comercial, la tuerca y su
> retén, la antena con sus tornillos, el latiguillo coaxial con sus conectores y los mazos de cables,
> en posición final y en el montaje paso a paso. Revisión endurecida del 08-10-2026: **Ø56 × 116**
> (con las correcciones de la segunda auditoría externa: coaxial a R ≥ 12, mazos que no se cruzan,
> aberturas del costado justas, tapa de puertos con tres anclas y cuna para un pack 1S2P comercial).
> **No se ha impreso ni montado nada.** Rama `hw/compact-v03`. Resultados en
> [Verificaciones](#verificaciones).

> **Antes de imprimir todo:**
> 1. **Imprimir primero un tramo de prueba** del tubo (una rodaja con la cara plana, una unión y un
>    apoyo del chasis) y el chasis, y probar con las piezas reales: placa en los rieles, carrier en
>    sus ranuras, el pack en la cuna, base y tapa en sus escalones.
> 2. **Medir la carrier con calibre** (canto a canto en x, alto en z, espesor del PCB y dónde asoma
>    el USB-C) y ajustar `carrier` y `chasis.ranura_carrier` en [parameters.json](parameters.json).
>    Sus medidas salen de una foto (±1 mm). Ver [Carrier: medir y suplementar](#carrier-medir-y-suplementar).
> 3. **Confirmar la antena y su conector** (HA-901A, "SMA-J") y la longitud del perno del bastón.
> 4. **Probar impresa la tapa de puertos de TPU** (que la bisagra aguante abrirla y cerrarla muchas
>    veces, que selle el túnel y la ranura y que las tres setas sujeten) y **el acceso a la microSD con
>    la uña** por su muesca. El modelo solo comprueba la tapa girada como sólido rígido: no prueba
>    cómo se dobla el TPU ni si una uña llega.

Especificación y contrato con la placa:
[hardware/main-board/research/v03-compacta.md](../../hardware/main-board/research/v03-compacta.md).
Copia la arquitectura de [V2.3](../v2.3/README.md): chasis que se arma fuera y entra por arriba,
base con la tuerca del bastón y tapa de antena. Lleva una cara plana al frente (OLED, tecla, LED y
logo), un pack 1S2P de dos 18650 detrás y la placa principal en medio.

## Tamaño elegido: Ø56 × 116, y por qué

La placa no se mueve (x ±18, y 13.8–15.4, z 8.5–80, mismas muescas). Lo que fija el tamaño:

- **Pared de 2.4.** En las uniones el tubo lleva por dentro un rebaje para el labio de la base o de
  la tapa: 0.8 de labio + 0.4 de juego entre impresas + **1.2 de pared mínima** = 2.4.
- **Radio interior 25.6** (Ø56 con pared de 2.4). La cara plana interior va en y 20.5: vidrio de la
  OLED (y 20.0) + 0.5 de aire. Con 25.6 llega a |x| 15.33, así que la placa tiene h(x) = 4.6 con
  0.5 de aire hasta |x| 15.17. Lo que no cabe con Ø54 (radio interior 24.6):
  - las esquinas de los rieles del chasis (r 25.17) y sus paredes laterales (r 25.1) con 0.4 al
    tubo: harían falta ranuras en la pared y apretar las ranuras de la carrier y los tiradores;
  - el coaxial con R ≥ 12, que pasa entre el extremo −X del pack y la pared (eje del cable hasta r 24.1, más
    0.9 de cable y 0.5 de aire): con Ø54 no cabe;
  - h(x) junto a la franja del canto (x 17) bajaría de 3.07 a 1.68.
  
  Con Ø56 los rieles no necesitan ranuras: su esquina queda a 0.43 del tubo.
- **Alto 116.** El RG 178 necesita R ≥ 12 en todas sus curvas (la hoja actual de Lapp da 6 × Ø
  en instalación fija: 10.9, y 11.6 con el Ø máximo). El recorrido más bajo que lo cumple, con 0.6
  de aire a todo, llega al pasamuros en z 104 (con R 10 llegaba en z 99). El pasamuros tiene 9 de
  cuerpo por dentro: cara interior del panel en z 113, panel de 3, tapa arriba en z 116. Es 5 mm
  más que la revisión anterior (Ø56 × 111).

Diámetro exterior 56 (radio 28); cara plana exterior en y 22.9 (de x −16.11 a 16.11); alto
total 116 (base z 0–4, tubo z 4–112, tapa z 112–116). Antes: Ø52 × 100 (primera V3.0) y Ø56 × 111.

### h(x): alto máximo de componentes en la cara de la placa

Con 0.5 de aire a la cara plana interior y **0.5 en radial** a la pared redonda (no 0.5 en y: en
los cantos la pared va inclinada y 0.5 en y dejaba solo 0.37):
`h(x) = min(4.6, √(25.1² − x²) − 15.4)`, medido desde la cara de la placa (y 15.4). En las franjas
de 1 mm de los cantos (|x| 17–18) van los rieles y no puede ir ningún componente: los dos últimos
valores son solo de la pared.

| \|x\| | 0–15.17 | 15.5 | 16 | 16.5 | 17 | 17.5 | 18 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| h máx. | 4.6 | 4.34 | 3.94 | 3.51 | 3.07 | 2.59 | 2.09 |

Por detrás de la placa (y < 13.8) no puede asomar nada delante del SMA de la carrier (x −6…3,
z 60–80): ver la comprobación en [Verificaciones](#verificaciones).

### Cara plana: posiciones

| Qué | Dónde |
| --- | --- |
| Cara plana exterior | y 22.9, \|x\| ≤ 16.11, z 4–112 |
| Cara plana interior | y 20.5, \|x\| ≤ 15.33 |
| Ventana de la OLED | x ±12.12, z 73.32–86.68 (área visible del módulo girado 180° más 0.25) |
| Bolsillo de la lámina | 0.8 más grande por lado, 1.0 de hondo (quedan 1.4 de pared) |
| Tecla | eje (0, 22): agujero Ø6.4 y rebaje exterior Ø9 × 0.6 |
| LED (guía de luz) | eje (−6, 22): agujero Ø2 |
| Distintivo grabado | Hexágono con el 3, como en las carcasas V2.x: 18 × 20.7, centro z 49.5, grabado 0.8 en la cara plana (quedan 1.6 de pared) |

## Piezas

| Pieza | Qué es |
| --- | --- |
| 01-base | Disco de 2 mm con el anillo del redondeo R4 hasta z 4 y un **labio** de 0.8 × 1.5 que entra en el rebaje del tubo con 0.4 de juego. **Tuerca 5/8"-11 de latón** en un alojamiento hexagonal (0.3 por cara) sobre un anillo de asiento de 2; saliente r 16 recortado en y 13.3, hasta z 15.5; retén M2 detrás. Tres lengüetas (210°, 270°, 330°; r 22.2–25.2, z 2–10.6) para los tornillos radiales; nervio a 270°. Desagüe de Ø1.5 delante |
| 02-tube | Pared de 2.4 (R28, z 4–112) con la **cara plana** al frente. Rebajes de 1.2 × 1.9 por dentro en los dos extremos (uniones). Frente: ventana de la OLED con bolsillo exterior y chaflán por dentro, tecla, LED y **distintivo grabado** (hexágono con el 3). Costado +X: **túnel cerrado del USB-C**, **ranura justa de la microSD** con una **muesca estrecha para la uña** y tres agujeros para las **anclas de la tapa de puertos**. **Apoyos del chasis** (z 8–9.5), **cuna** de las celdas y **rayas decorativas** atrás |
| 03-antenna-cap | Disco de 4 mm (z 112–116) con el redondeo R4 de arriba y un **labio** que baja al rebaje del tubo. **Pasamuros SMA** en el centro (agujero Ø6.5 con cara plana, rebaje Ø13 por dentro: panel de 3). Pasos y rebajes Ø6 × 2.4 de los tres M2.5 de la antena. Dos **topes sobre las celdas** y tres lengüetas para los tornillos radiales |
| 04-chassis | Se arma fuera del tubo. **Rieles en C** sobre las franjas de 1 mm de la placa (0.25 por cara), con tope en z 80; **ranuras de la carrier** con topes arriba y **ganchos** flexibles abajo (0.3 de juego); **dos salientes** M2 detrás de la placa; **puente** con hueco para la tuerca de la clavija SMA y ventana para la llave; paredes laterales con un **tirador** cada una |
| 05-key-tpu | Tecla de TPU que se pone y se saca por fuera: pestaña pegada en el rebaje exterior, membrana de 0.4, cabeza que asoma 1.0 y émbolo a 0.5 de SW401 |
| 06-port-cover-tpu | **Tapa de puertos** de TPU, atada: ala curva de 0.9 sobre el costado +X que tapa el túnel del USB-C y la ranura de la microSD (con sus cuerpos a presión por dentro), lengüeta delante para abrirla, bisagra fina y **tres setas** de anclaje por agujeros de Ø2 de la pared, repartidas por su canto de atrás |
| 07-logo-inlay-tpu | **Distintivo de TPU** (hexágono con el 3) para imprimir aparte, de otro color, y pegar en el grabado del frente: los mismos contornos reducidos 0.1 por lado, 0.8 de espesor, a ras de la cara plana. Son 6 islas: el hexágono, el 3 y cuatro rayas de unos 2 mm². Para imprimir: `generated/stl/07-logo-inlay-tpu-para-imprimir.stl`, acostado con la cara que se ve contra la cama |

Tornillería y piezas compradas:

- tuerca hexagonal 5/8"-11 UNC de latón, estándar;
- 1 × M2 × 8 de cabeza alomada (ISO 7045) o botón con arandela DIN 9021 **de M3** (Ø9 × 0.8):
  retén de la tuerca, a 270° y r 15;
- 6 × M2.5 × 6 avellanados **ISO 14581** (Torx) o **ISO 7046** (cruz), radiales: 3 de la base
  (z 8.5) y 3 de la tapa (z 107);
- 3 × M2.5 × 6 de cabeza alomada **ISO 7045** con arandela **ISO 7092** (Ø5 × 0.5): antena, desde
  dentro de la tapa;
- 2 × M2 × 8 autorroscantes: OLED y placa a los salientes del chasis, con **separadores de 1.3**
  entre el módulo y la placa (pines de J403 cortados y soldados en pads SMD). El del lado −X, junto
  a la antena del ESP32, mejor **de nailon**;
- lámina de PC o acrílico de 1.0 × 25.64 × 14.76 para la ventana, pegada;
- guía de luz de Ø2, pegada en su agujero, desde y 16.65 (0.54 sobre D403);
- **latiguillo coaxial:** pasamuros SMA hembra, unos 77 mm de RG 178 B/U y clavija SMA macho
  **acodada** de crimpar. Ver [Antena, conector y coaxial](#antena-conector-y-coaxial);
- kapton para la fila de 5 agujeros de la carrier (perno del bastón).

## Cómo se arma

1. **Tuerca en la base.** Entra por arriba en su alojamiento hexagonal. El retén M2 × 8 con su
   arandela ancha, a 270° y r 15, pisa 1.4 mm del borde trasero de la tuerca.
2. **Tapa de puertos** (06) en el tubo: las tres setas entran por fuera en sus agujeros de Ø2 (el
   cono de cada cabeza abre paso; el TPU se deja). Mejor ahora, con el tubo vacío.
3. **Pack 1S2P** (comercial: 2 × 18650 en funda termorretráctil, con BMS), con la tapa quitada y
   sin el chasis. Baja por arriba a su cuna, con el **extremo del BMS (de donde salen sus cables)
   abajo**, y apoya en dos repisas (z 18.8). Medirlo: si es más fino que 20 o más corto que 68,
   calzarlo con espuma (ver [Pack](#pack-1s2p)).
   - La NTC va pegada con kapton en la **cara de atrás** del pack, a media altura, y sus dos hilos
     bajan pegados por esa cara hasta el extremo del BMS.
   - Mazo del pack (rojo, negro y los dos hilos de la NTC): sale del extremo del BMS por detrás,
     baja por detrás del saliente de la tuerca, lo rodea por +X pegado al piso (z 4.2) y va por el
     piso, delante, hasta J404 y J102. Ver [Cables](#cables).
   - El extremo con las clavijas queda colgando por abajo del tubo: se enchufa al final.
4. **Carrier al chasis, POR ABAJO**, con el arnés de J301 ya soldado. Sube por sus ranuras, abre
   los dos ganchos y queda entre los topes de arriba y los labios de los ganchos.
5. **Latiguillo coaxial.**
   - El pasamuros va ya en la tapa, con la antena atornillada (sus tres M2.5 desde dentro y la
     antena enroscada en el pasamuros). Ver [montaje del pasamuros](#antena-conector-y-coaxial).
   - La **clavija SMA acodada** se enrosca en el SMA de la carrier **antes de la placa**, con el
     cable hacia −X. El frente del chasis está abierto: una llave fija de 8 entra por delante (+Y)
     y gira ±30° por la ventana del puente. Desde aquí la tapa cuelga del latiguillo: sostenerla.
6. **Placa al chasis, POR ABAJO**, con la OLED soldada. La muesca del canto de arriba (u 14.2–24.2,
   v 0–6.5) pasa alrededor de la tuerca de la clavija.
   - Dos M2 × 8 autorroscantes por los agujeros de abajo de la OLED, los separadores de 1.3 y la
     placa, hasta los salientes del chasis.
   - Arnés de J301 a su clavija (x −13.5…−2.5).
7. **Chasis armado al tubo, por arriba**, con el pack puesto y **sin la tecla**. Las paredes
   laterales y los rieles bajan junto a la pared (0.4) y el pie de los rieles apoya en los
   apoyos del tubo (z 9.5). La tapa baja a la vez, colgada del latiguillo.
8. **Tapa** en su sitio. El latiguillo queda en su recorrido: hacia −X sobre el puente, por fuera
   del extremo −X del pack (entre él y la pared), por detrás de él y por encima del pack sube hacia el
   eje y el pasamuros. Tres M2.5 radiales en z 107.
9. **Por abajo, sin la base:** clavija de la batería a J102 y de la NTC a J404 (con la tapa ya
   puesta). Se recogen los mazos en su recorrido y se pone la base con sus tres M2.5 radiales en
   z 8.5.
10. **Tecla, lámina de la ventana y guía de luz**, por fuera. La tecla, con cinta adhesiva fina de
    doble cara o un adhesivo flexible que se pueda despegar: hay que sacarla para sacar el chasis.
    **Distintivo de TPU** en su grabado: pegado con un adhesivo para TPU (cianoacrilato flexible o
    de contacto), una gota en el fondo de cada isla. Para no perder las rayas chicas, al despegarlas
    de la cama ponerles encima cinta de enmascarar y pasarlas juntas, como una calcomanía.
11. **microSD** por la ranura del costado; la tapa de puertos cierra el túnel del USB-C y la ranura.

## Desmontaje y servicio

1. **Tecla fuera**, por fuera. Con la tecla puesta el chasis no sale: su émbolo queda delante de la
   placa y J102 choca con él a los pocos milímetros de subir.
2. **Base fuera** (tres M2.5 de z 8.5). Desenchufar **J102** (batería) y **J404** (NTC) por abajo.
3. **Tapa suelta** (tres M2.5 de z 107). No sale del todo: sigue unida a la carrier por el
   latiguillo. Se levanta lo que deja el cable y se sostiene.
4. **Chasis fuera, por arriba**, tirando de los dos tiradores con un gancho o un alambre (agujeros
   Ø2.5: el de +X arriba, en z 107–111.6; el de −X en z 79–83, por debajo del paso del coaxial). La
   tapa sale con él, colgada del latiguillo. El pack se queda en el tubo.
5. **Placa fuera del chasis:** desenchufar J301, quitar los dos M2 de la OLED y bajar la placa por
   los rieles.
6. **Clavija SMA acodada fuera:** llave fija de 8 por delante, por la ventana del puente. La tapa
   con la antena y el latiguillo queda libre.
7. **Carrier fuera:** abrir los dos ganchos (apartar el labio hacia fuera) y bajarla por las ranuras.
8. **Pack fuera,** por arriba (dejar una cinta bajo el pack para tirar de ella).
9. **Antena:** los tres M2.5 por dentro de la tapa y desenroscarla del pasamuros. El pasamuros sale
   aflojando su tuerca (por dentro o por fuera, según el montaje).
10. **Tuerca del bastón:** quitar el retén M2 y sacarla por arriba.

Para volver a armar, al revés: la clavija acodada siempre antes que la placa y la tecla siempre al
final. No doblar el coaxial a menos de unos 19 mm cuando se manipula (10 × Ø: radio para flexiones
ocasionales de la hoja actual del RG 178).

## Geometría

Ejes de V2.x: z = eje del bastón hacia arriba (z 0 en la cara de apoyo), +Y al frente (cara
plana), +X a la izquierda mirando el frente. Todo sale de [parameters.json](parameters.json); las
holguras objetivo están en `holguras` (0.4 entre impresas, 0.25 por cara en los rieles, 0.5 a
piezas compradas, pared de 1.2 y 1.0 en lo local).

**Pila de adelante hacia atrás:** cara plana por dentro y 20.5; vidrio de la OLED hasta y 20.0;
componentes de la placa hasta y 15.4 + h(x); PCB y 13.8–15.4; componentes de la carrier y 6.8–13.2;
PCB de la carrier y 5.2–6.8 (0.1 más atrás que en la especificación, para dejar 0.5 entre su SMA y la
placa); patas del SMA hasta y 3.2; pack 1S2P (estadio de 37.5 × 20, centro (0, −8.6)) de y 1.4 a −18.6.

**Tubo (02-tube):**
- Pared de 2.4 (R28 por fuera, R25.6 por dentro), z 4–112. Uniones en escalón: rebaje de 1.2 de
  hondo y 1.9 de alto por dentro en cada extremo, donde entran los labios de 0.8 × 1.5 de la base y
  de la tapa con 0.4 de juego; quedan 1.2 de pared.
- **Apoyos del chasis:** dos repisas en z 8–9.5, de r 21.4 a la pared, a 12–30° y 155–168°, bajo
  las paredes laterales del chasis. Los rieles ya no necesitan ranuras en la pared.
- **Cuna del pack:** tres nervios de 1.6 por extremo redondo del pack (costado, atrás y un labio
  delante-fuera), a 0.5 de su envolvente, de z 18.8 a 84.5 (el labio a 84, bajo el paso del coaxial),
  y repisas bajo su parte de fuera (r ≥ 16.6, z 17.6–18.8). Ver [Pack](#pack-1s2p).
- **Frente:** ventana de la OLED con bolsillo exterior (0.8 por lado, 1.0 de hondo) y chaflán de
  entrada de 0.4 a 45° por dentro; tecla (Ø6.4 y rebaje Ø9 × 0.6); LED (Ø2); distintivo grabado 0.8 (hexágono con el 3).
- **Costado +X:**
  - **túnel del USB-C, cerrado:** sección de rectángulo redondeado de 12.95 × 7.1 (R1.3): la funda
    máxima de la clavija (12.35 × 6.5, con esquinas de R1.0 supuestas) más 0.3 por lado, centrado
    en el eje de J101 de la placa real (y 16.6, z 25.0, de `placa-principal.json`), de la cara
    exterior a la boca del receptáculo (x 14.9). Sin cortes abiertos; solo un chaflán de 45° en el
    canto de fuera de arriba (1.2 hacia dentro por el techo), donde el techo salía en cuña;
  - **ranura de la microSD, justa:** 11.6 × 1.6 (la tarjeta de 11 × 1.0 más 0.3 por lado; y
    15.65–17.25, z 35.08–46.68), centrada en **z 40.88**: el eje de la tarjeta sale de J401 en la
    placa real (caja de J401 más el desplazamiento del canal, 0.9), no de la ranura. La tarjeta
    entra y sale recta en x;
  - **muesca para la uña** en el centro de la tarjeta: 8 de ancho (z 36.88–44.88), de la ranura
    hasta y 20.2, atravesando la pared. Arriba de la muesca la cara exterior está en x 19.39.
  - **Posiciones de la tarjeta**, de la hoja de SOFNG del TF-015 (LCSC C113206), medidas desde la
    boca de J401 (x 16.5):
    - trabada, asoma 2.50 (x 19.0): queda 0.4 por debajo de la cara exterior en la muesca y 3.7 en
      el plano de la ranura;
    - para soltarla se empuja hasta 1.32 (x 17.82), 1.2 más;
    - expulsada, asoma 5.60 (x 22.1): sobresale 2.7 de la cara exterior en la muesca, de donde se
      toma con la uña o la yema. En el plano de la ranura queda 0.6 por dentro.

    Antes el modelo la tenía trabada en x 17.5, 1.5 más adentro de lo real, y la muesca era de 5.
  - chaflanes de 45° en los cantos de fuera de arriba de la ranura y de la muesca (1.2), y uno de
    0.8 por dentro en el canto del suelo de la ranura (cuña de ~53°; no se ve desde fuera);
  - **agujeros de las anclas** de la tapa de puertos: Ø2 radiales a 19°, en z 20, 32.5 y 45.
  - **Qué se ve desde fuera sin la tapa:** por el túnel, la boca del receptáculo al fondo (a 4.2 de
    la cara interior), el canto de la placa debajo de ella y, encima, las paredes del túnel; por la
    ranura, el canto de la tarjeta (o la boca de J401) y, por la muesca de 8, la parte de arriba de
    J401. Por dentro del tubo no puede haber paredes que alarguen el túnel: el chasis con la placa
    entra por arriba y pasaría por ahí.
- **Rayas decorativas** como las de V2.3: 1.3 de ancho y 0.5 de hondo (quedan 1.9 de pared), en dos
  grupos de 5 a 9° (198–234° y 306–342°: simétricos respecto al eje frente-atrás), z 11.5–105,
  entre las uniones, por encima de las cabezas de los tornillos de la base y lejos de la cara
  plana, el logo, la tapa de puertos y las aberturas.

**Base (01-base):**
- Tuerca con las caras hacia ±Y (su frente en y 11.9). Delante bajan la placa (dorso y 13.8, hasta
  z 8.5) y las clavijas (hasta z 2.75).
- Saliente de la tuerca: r 16, recortado en y 13.3 (0.5 a la placa) y hasta z 15.5, 0.4 por debajo
  del pie de las ranuras de la carrier; la tuerca asoma 0.39.
- **Perno del bastón:** como máximo 15.5 mm de rosca desde el asiento (z 0). Las soldaduras de la
  fila de 5 de la carrier están en z 16.7. Poner kapton en esa fila. Parámetro
  `base.tuerca.perno_max`.
- **Retén:** M2 × 8 a 270°, r 15, con arandela DIN 9021 de M3 (Ø9 × 0.8); pisa 1.4 mm de la
  tuerca. La cabeza llega a z 18.3, 0.5 por debajo del pack (por eso el pack apoya en z 18.8); la
  arandela pasa por debajo de él.
- Lengüetas r 22.2–25.2, z 2–10.6, con un M2.5 avellanado radial en z 8.5: el borde de la cabeza
  (z 6.0) queda por encima del rebaje de la unión (z 5.9) y la pared no baja de 1.2 (en z 8 bajaba
  a 0.83); nervio a 270° hasta el saliente de la tuerca.

**Tapa (03-antenna-cap):**
- Lengüetas r 22.7–25.2, z 102–112, a 0°, 180° y 270°; M2.5 avellanado radial en z 107.
- **Pasamuros:** agujero Ø6.5 con cara plana a 5.8 (antigiro) y rebaje Ø13 × 1 por dentro (panel de
  3).
- Tornillos de la antena: rebaje Ø6 × 2.4 para la cabeza ISO 7045 y la arandela ISO 7092 (0.5 de
  aire alrededor). Quedan 1.6 de tapa encima y el M2.5 × 6 entra 3.9 en la antena (rosca de 6
  supuesta).
- **Topes sobre el pack:** Ø6 en (±12.5, −12.5), desde z 87.3 (0.5 sobre el pack, que mide 68):
  lo sujetan en vertical con 0.5 de juego. Fuera del recorrido del coaxial.

**Chasis (04-chassis):**
- Todo en r ≤ 25.2 (0.4 al tubo) e y ≤ 20.1.
- **Rieles en C**, z 9.5–81: ranura de la placa y 13.55–15.65 y fondo en |x| 18.25 (**0.25 por
  cara**); labio delantero desde |x| 17.5, dentro de la franja de 1 mm (monta 0.5 sobre la placa y
  queda a 0.5 de la envolvente de componentes, que llega a |x| 17, y a 0.69 de U302 y U303 de la
  placa real); tope de la placa en z 80.
  - El riel +X se corta en z 18–47.2, frente a la funda del USB-C y a la tarjeta.
  - **Antena del WROOM (U201):** el riel −X y la punta de la pared lateral se quitan en z 44.5–73
    (x −22.5…−15.5, y 11.5–17): nada de plástico del chasis a menos de 5 mm de la antena, salvo el
    saliente M2 de la OLED del lado −X, detrás de la placa.
- **Paredes laterales** x ±19.6–21.6, y 4.3–12.76, desde z 9.5 (pie sobre los apoyos del tubo):
  la de +X hasta z 111.6, con el **tirador** arriba (z 107–111.6, agujero Ø2.5); la de −X acaba en
  z 83, por debajo del coaxial, con su tirador en z 79–83.
- **Ranuras de la carrier**, sacadas de `carrier` (x ±16, z 17–69, PCB y 5.2–6.8) con **0.3 de
  juego** por cara (`chasis.ranura_carrier.holgura`): topes arriba (z 69.3), labios delanteros en
  z 59.5–69 que montan 0.9 sobre el PCB, y **ganchos** abajo (labio que monta 0.7 bajo el PCB, en
  z 15.9–16.7, con rampa por debajo; brazo de 0.8 × 0.6 y 10 de largo en y 5.7–6.3, con ranuras de
  0.6 a los lados y 1.3 libres detrás: se abre 0.7, deformación ~0.8 %).
  - +X: sin pared delante del PCB por debajo de z 30.9 (USB-C que sobresale 0.9).
  - −X: el labio trasero empieza en z 40.8 y por debajo la pared se aparta a x −16.7 (soldaduras
    del arnés de J301 detrás del PCB).
- **Salientes** Ø5 en x ±11.75, z 70.2, de y 8.0 a 13.8; piloto Ø1.6 × 5.
- **Puente** x ±20.1, y 2.0–5.9, z 72.5–84, detrás de la clavija SMA y delante del pack:
  hueco en x −12.8…4.1 (y ≤ 5.0) para la clavija y su tuerca, **ventana** en z 75.5–80,
  x −10.5…8.5, para la llave fija de 8 girada ±30°, y esquinas de fuera quitadas (|x| > 18.6,
  y < 4.3), donde pasan los labios de la cuna.

**Tecla (05-key-tpu):** pestaña Ø8.8/6.4 × 0.6 en el rebaje exterior, a ras; membrana de 0.4;
cabeza Ø5 que asoma 1.0; émbolo Ø3 hasta 0.5 de SW401 (1.55 de alto en la placa real; recorrido
del pulsador 0.25).

**Tapa de puertos (06-port-cover-tpu):**
- Ala de 0.9 sobre el costado +X (R28, de 16.5° hasta la cara plana), z 16.8–48.4: cubre el túnel
  del USB-C y la ranura de la microSD con más de 1.5 de solape.
- Cuerpos a presión con la forma de las aberturas nuevas: el rectángulo redondeado del túnel y la
  ranura con su muesca (sin holgura nominal: sellan). El de la ranura empieza en r 26.0, a 0.54 del
  canto de la tarjeta trabada: cerrar la tapa no la empuja (el zócalo es de empuje y la soltaría).
- Lengüeta para abrirla en el canto delantero (x 12.6–14.6, z 22.5–27.5, 1.0 de alto).
- Bisagra a 22.5°: franja de 2° donde el ala queda en 0.6.
- **Tres setas** a 19°, en z 20, 32.5 y 45 (abajo, en medio y arriba del ala, por detrás de la
  bisagra): vástago Ø1.95 por un agujero de Ø2 y cabeza Ø3.4 × 1.0 con cono de entrada de 45°,
  apoyada en la cara interior del tubo.
- **Hay que probarla impresa:** la duración de la bisagra de TPU de 0.6 al abrir y cerrar, el sellado
  de los cuerpos a presión y lo que sujetan las setas. El modelo solo gira la parte de delante como
  sólido rígido.

## Antena, conector y coaxial

**Antena:** HA-901A del kit BDLX (hélice, Ø43.5 × 40.8; la tienda da "SMA-J", que en la
nomenclatura china es SMA **macho**), con su conector en una cavidad de la base y tres agujeros
M2.5 en un círculo de 26.6. **Modelo y conector sin confirmar** por el propietario.

**Pasamuros en la tapa** (`antena.conector.tipo = "macho"`, por defecto):
- SMA **hembra** pasamuros en el centro de la tapa: rosca 1/4"-36 UNS con caras planas, agujero
  Ø6.5 con cara plana a 5.8, tuerca de 8 entre caras. Panel de 3 (rebaje Ø13 por dentro); el
  conector elegido tiene que admitir al menos 3 (`pasamuros.panel_max` 4).
- La antena se enrosca en el pasamuros y además se atornilla con sus tres M2.5 desde dentro de la
  tapa, antes de poner la tapa.
- **Dos montajes posibles, misma tapa:**
  - **frontal** (cuerpo por fuera, tuerca por dentro, en el rebaje Ø13; se aprieta con una llave
    de tubo de 8 de pared fina o con una fija sobre los 1.5 mm de tuerca que asoman): el cable
    tiene que pasar por el agujero de 6.5 **antes** de crimpar la clavija acodada del otro extremo;
  - **trasero** (cuerpo por dentro con su hexágono en el rebaje, tuerca por fuera, bajo la
    antena): vale un latiguillo ya hecho, si la cavidad de la antena admite la tuerca y su arandela.
- **Riesgo abierto:** si el SMA macho de la antena es fijo (gira con la antena), al enroscarla los
  tres agujeros pueden no quedar enfrente de los de la tapa. Entonces: atornillar solo con los
  M2.5 y no apretar el SMA a tope, o hacer los agujeros de la tapa colisos. Pendiente de ver la
  antena real.
- **Alternativa** (`antena.conector.tipo = "hembra"`): si la antena trae SMA hembra, la tapa lleva
  un paso de 12 en el eje para la clavija macho del cable y no hay pasamuros.

**Latiguillo** (del pasamuros al SMA de la carrier):
- **Cable:** RG 178 B/U (MIL-C-17/93), FEP de Ø1.81 ± 0.13, 50 Ω. **Hoja actual de Lapp 2170002**
  (DB2170002EN, versión 06, válida desde el 30-04-2020): radio de curva mínimo **6 × Ø en
  instalación fija** (10.9 con Ø1.81; 11.6 con el máximo de 1.94) y **10 × Ø con flexiones
  ocasionales** (18–19). La de 2008 daba 10 fijo; esta revisión usa la actual y pide **R ≥ 12 en
  todas las curvas**. Unos 77 mm de cable entre los cuerpos de los conectores (el recorrido modelado
  mide 79.4 desde 2 mm dentro de la clavija acodada hasta el pasamuros).
- **Clavija acodada:** SMA macho de 90° de crimpar para RG178/RG316. Envolvente que se le pide:
  tuerca de 5/16" (7.94 entre caras, 9.2 entre esquinas, 5.5 de largo, z 74.5–80), cuello de Ø5 y
  cuerpo acodado de 7 de ancho **desde z 80.5** (0.5 por encima del canto de la placa, que está a
  3.7 del eje) hasta 88.5, con el cable saliendo hacia −X a 8.3 del eje, en (−9.5, 10.1, 85).
  **Comprobar con la hoja de la clavija elegida** (`coaxial.clavija.acodada`).
- **Recorrido** (`coaxial.ruta`): B-spline cúbico de 18 puntos de control, sacado con una
  optimización (radio ≥ 12.3 en todo el recorrido y 0.6 o más de aire a todo, con el pasamuros lo
  más bajo posible). Sale de la clavija hacia −X sobre el puente, baja por fuera del extremo −X del
  pack (entre él y la pared), pasa por detrás de él y sube hacia el eje por encima del pack hasta el
  pasamuros, vertical, en z 104.
  - **Radio mínimo 12.27** en todas las curvas (objetivo ≥ 12): cumple con margen sobre el 6 × Ø de
    la hoja, también con el Ø máximo.
  - Para eso el pasamuros sube de z 99 a 104: **el receptor crece 5 mm** (Ø56 × 116). Con el alto
    de antes no hay sitio: el mejor recorrido con R 12.3 que encontró la optimización (probando
    varios caminos: por detrás de las celdas, por encima de la celda −X y dando la vuelta por +X)
    necesitaba el pasamuros en z 103.6 o más con las celdas sueltas; con el pack se volvió a sacar
    con el pasamuros en z 104.
  - Radio máximo del eje del cable 24.1: 0.59 al tubo y a los nervios de la cuna, 0.6 al pack,
    0.63 al chasis, 2.9 a la tapa.
- **Servicio:** la tapa queda unida a la carrier por el latiguillo hasta que se quita la clavija
  acodada, que solo es accesible con la placa fuera del chasis. Ver
  [Desmontaje y servicio](#desmontaje-y-servicio).

## Cables

Reservas modeladas como tubos (`cables` en parameters.json) y comprobadas a 0.5 de todo, en su
sitio y al mover la base, el chasis y la tapa. Recorridos supuestos: no se sabe todavía por dónde
salen exactamente los cables del pack real.

| Mazo | Qué lleva | Recorrido |
| --- | --- | --- |
| Del pack, Ø3.4 | Rojo y negro del pack (Ø1.5 supuestos, AWG22) y los dos hilos de la NTC | Sale del extremo del BMS, **abajo**, por detrás (6.8, −16.8, 17.8), baja por detrás del saliente de la tuerca (x 6.8, y −20), lo rodea por +X **pegado al piso** (z 4.2, 0.5 sobre la base) y va por el piso, delante, a J404 (x 6.4…11.4) y J102 (x −2.0…6.2) |
| Hilos de la NTC, Ø1.6 | Dos hilos de Ø0.8 | De la NTC, por la cara de atrás del pack, pegados con kapton, hasta el mazo del pack abajo (se juntan con él) |
| Arnés de J301, Ø3 | 8 hilos soldados en la carrier | De la columna de 8 agujeros de la carrier (canto −X, z 22–39), por delante, baja por el canal −X (x −17.4, y 10.4–10.6) y va por el piso (z 4–4.2), bajo el canto de la placa, a J301 (x −13.5…−2.5); sube y baja con el chasis |
| NTC | 3 × 2 × 8 con su funda | Pegada con kapton en la cara de atrás del pack, entre los nervios de atrás (x 1.5–4.5, z 47–55) |

El extremo del BMS va **abajo**: los cables del pack quedan cortos hasta J102 y J404, y arriba queda
libre el paso del coaxial. Las clavijas de J102, J404 y J301 bajan hasta z 2.75 (`kicad/plugs.json`
v0.3). **Los mazos no se cruzan:** entre el mazo del pack, el arnés de J301 y el coaxial hay 8.8 o
más (los hilos de la NTC se juntan con el mazo del pack a propósito). En la realidad los cables pueden
tocarse; el modelo no los deja interpenetrar. No hacen falta guías: quedan a 0.5 o más de las piezas
(ver [Verificaciones](#verificaciones)).

## Pack 1S2P

El propietario usa un **pack comercial 1S2P**: 2 × 18650 lado a lado en funda termorretráctil, con BMS
dentro, dos cables (rojo y negro) y sin hilo de NTC. Anuncio: 37.5 × 68 × 20, 110 g.

| Parámetro (`celdas.pack`) | Valor | Qué es |
| --- | --- | --- |
| `ancho` | 37.5 | de canto a canto |
| `grueso` | 20 | peor caso (el de verdad será de unos 19) |
| `largo` | 68 | con el BMS |
| `holgura` | 0.5 | a la cuna, al tubo y a todo lo demás |
| `centro` | (0, −8.6) | en planta |

- **Envolvente de peor caso:** un estadio (dos cilindros de Ø20 con los valles puenteados por la funda)
  de 37.5 × 20 y 68 de largo.
- **Posición:** el frente queda donde estaban las celdas sueltas (y 1.4, 0.6 al puente del chasis);
  la cuna se corre **1.4 hacia atrás** (cara de atrás en y −18.6, a 3.3 o más del tubo).
- **Alto:** apoya en dos repisas en z 18.8 (1.3 más arriba que las celdas sueltas: su cara de abajo
  es plana y tapa el valle donde cabía la cabeza del retén de la tuerca, que llega a z 18.3) y acaba
  en z 86.8. Los topes de la tapa bajan a z 87.3: queda sujeto en vertical con **0.5 de juego**. No
  hace falta suplemento impreso.
- **Si el pack real es más fino o más corto:** queda más suelto. Medirlo y calzarlo con espuma
  (adhesiva, de 1–2 mm) en la cara de atrás o en los topes de la tapa.
- La NTC va en la cara de atrás, bajo kapton (unos 2 de grueso), no en el valle de delante.

## Carrier: medir y suplementar

**Las ranuras salen de las medidas de la carrier**, que vienen de una foto rectificada (±1 mm):

| Parámetro | Valor | Qué es |
| --- | --- | --- |
| `carrier.x` | −16 … 16 | cantos (ancho 32) |
| `carrier.z` | 17 … 69 | canto de abajo y de arriba (alto 52) |
| `carrier.y`, `carrier.pcb` | 5.2 … 6.8, 1.6 | dorso y cara del PCB (0.1 más atrás que en la especificación) y espesor |
| `chasis.ranura_carrier.holgura` | **0.3** | juego por cara en x, en y y en z (topes y ganchos) |

1. **Medir** la carrier con calibre: ancho, alto, espesor del PCB, dónde asoma el USB-C del canto
   +X (0.9 en el modelo) y la posición del SMA respecto al canto de arriba.
2. **Si es más grande** que el modelo + 0.3 en alguna dirección, no entra: cambiar `carrier` y
   regenerar el chasis (las ranuras, topes y ganchos se recalculan). Si cambia el canto de arriba
   (`carrier.z[1]`), mover también `coaxial.clavija` (la clavija acodada sube o baja con el SMA).
3. **Si es más pequeña**, sobra juego:
   - en x o en y: suplementos de cinta (kapton de 0.06 o PET de 0.1, en capas) en las caras de la
     ranura, o una tira impresa pegada;
   - en z: una almohadilla de EPDM o silicona de 0.5–1 adhesiva en los topes de arriba: además
     sujeta la carrier contra los ganchos y amortigua.
4. Probarlo en el tramo de prueba del chasis antes de imprimir el resto.

## Tolerancias y ajustes

Objetivos de esta revisión (`holguras` en parameters.json) y el mínimo conseguido con la placa
real, en posición final y en los barridos del montaje (`objetivos` en
[generated/check.json](generated/check.json)).

| Categoría | Objetivo | Mínimo | Dónde |
| --- | --- | --- | --- |
| Ajuste entre piezas impresas | ≥ 0.4 | **0.4** | chasis–tubo, chasis–base, chasis–tapa y labios y lengüetas de base y tapa en el tubo, también al bajar el chasis. Tapa de puertos–chasis 0.57; cabezas de las tres setas al barrer el chasis 0.61 |
| Placa en los rieles, por cara | ≥ 0.25 | **0.25** | en su sitio y al subir la placa por los rieles |
| Aire a piezas compradas | ≥ 0.5 | **0.5** | en el límite de diseño: componentes de la placa–tubo (h(x)), pack–cuna, topes de la tapa y retén, placa–base, SMA de la carrier–placa, cables–piezas, clavija acodada–chasis, tornillos de la antena–tapa y componentes de la carrier–chasis; las celdas al bajar por la cuna. El coaxial, 0.59 o más. El resto, más |
| Funda del USB-C y tarjeta | 0.3 por lado (aberturas justas) | **0.3** | túnel cerrado y ranura justa, pedidos por el propietario: van guiadas, no es aire de 0.5. La tarjeta trabada (asoma 2.5 de J401) queda dentro de su ranura |
| Carrier en sus ranuras | juego 0.3 por cara | 0.3 en su sitio y al subirla | ajuste de posición: ver [Carrier](#carrier-medir-y-suplementar) |
| Pared del tubo | ≥ 1.2 (local ≥ 1.0) | **1.19**, local | chaflán de la ventana de la OLED bajo el bolsillo de la lámina (z 86.9). Uniones 1.2; túnel del USB-C 1.33; ranura y muesca de la microSD 1.32; agujeros de las anclas 1.31 |
| Radio de curva del coaxial | ≥ 12 en todas las curvas | **12.27** | todo el recorrido (6 × Ø de la hoja actual: 10.9–11.6) |
| Mazos entre sí | ≥ 0.3 | **8.8** | mazo del pack–arnés de J301 (los hilos de la NTC se juntan con el mazo del pack a propósito) |

Nada queda por debajo en las categorías de aire y ajustes, tampoco con la envolvente de la
especificación (`--envelope`).

**Ajustes de posición** (no son aire; van guiados a propósito):

| Dónde | Juego de diseño |
| --- | --- |
| Placa en los rieles del chasis | 0.25 por cara (y y fondo en x) |
| Carrier en sus ranuras, topes y ganchos | 0.3 por cara |
| Tuerca del bastón en su hexágono | 0.3 entre caras (0.15 por cara) |
| Pasamuros en su agujero en D | Ø6.5 y cara plana a 5.8 sobre rosca de 6.35 |
| Setas de la tapa de puertos en sus agujeros | vástago Ø1.95 en Ø2.0 |
| Lámina de la ventana en su bolsillo | 0.1 por lado |
| Funda del USB-C en su túnel | 0.3 por lado (pedido del propietario: abertura justa) |
| Tarjeta microSD en su ranura | 0.3 por lado (ídem) |
| Guía de luz en su agujero | Ø2 en Ø2, pegada |

**Contactos a propósito:** pie de los rieles del chasis en los apoyos del tubo (z 9.5); placa
contra los salientes (y 13.8) y contra el tope (z 80); pack en sus repisas (z 18.8); base y tapa
contra los cantos del tubo; cabezas de los tornillos en sus avellanados y arandelas en sus
asientos; tecla pegada en su rebaje y membrana sellando el agujero; tapa de puertos apoyada en el
tubo, con sus cuerpos de TPU a presión en el túnel y en la ranura (sellan); NTC e hilos de la NTC
pegados con kapton en la cara de atrás del pack; cables del pack saliendo de su extremo; clavijas
enchufadas.

**Rasgos finos a propósito** (menos de 1.0; medidos en secciones horizontales de cada pieza):
brazos de los ganchos 0.6 × 0.8 con ranuras de 0.6; labios de las ranuras de la carrier 0.65;
labios y dorso de los rieles 0.8; labios de las uniones de base y tapa 0.8; en TPU, ala de la tapa
de puertos 0.9, su bisagra 0.6 y membrana de la tecla 0.4. La pared más fina de la base es la de
delante del alojamiento de la tuerca (1.24).

## Verificaciones

Hechas el 08-10-2026 con FreeCAD 1.1.3 sobre los archivos de esta carpeta
([generated/check.json](generated/check.json), [generated/exports.json](generated/exports.json)).
- **Placa real:** `hardware/main-board/cad/placa-principal.step` (PCB y componentes) y su
  `placa-principal.json`, reexportados a las 15:37 del 08-10-2026 tras los cambios de la placa (sin
  mover ninguna pieza). Los ejes de la microSD (J401) y del USB-C (J101) salen de ese `.json`.
- **Clavijas reales:** zonas de J102, J404 y J301 de `kicad/plugs.json` v0.3.
- El módulo OLED no está en el STEP: se dibuja desde sus medidas (separador de 1.3, vidrio hasta
  y 20.0).
- Además se pasa la pared del tubo cada 1.5 mm de alto (72 secciones, sin los nervios de dentro):
  ningún punto baja de 1.2 salvo el chaflán de la ventana de la OLED bajo el bolsillo de la lámina
  (1.19, z 86.9), y las uniones quedan en 1.2. Nada baja de 1.0.

> **Corregido el 08-10-2026 (primera versión).** El tubo salía **sin la pared de la cara plana**
> en el centro, en todo el alto, y ningún choque lo mostraba. Desde entonces `export_v3_0.py` y
> `check_v3_0.py` sondean la pared y `check_v3_0.py` compara su volumen y mide su espesor.

| Comprobación | Resultado |
| --- | --- |
| Piezas | 7 piezas, válidas (el distintivo, 6 islas; el resto, un sólido cada una). Mallas STL cerradas, sin no-manifold ni autointersecciones. Triángulos: base 5122, tubo 7364, tapa 6084, chasis 1916, tecla 812, tapa de puertos 2404, distintivo 1396. Volúmenes en cm³: 8.98, 44.87, 10.48, 6.65, 0.09, 1.02 y 0.08 |
| Pared del tubo: sondas a media pared cada 0.5 mm | Cara plana: 11 715 puntos, 1 473 en las aberturas, **0 sin material**. Anillo: 58 543 puntos, 3 405 en las aberturas, **0 sin material** |
| Pared del tubo: volumen | 44 867.7 mm³; esperado 44 867.2 (+0.001 %, tolerancia 0.5 %) |
| Pared del tubo: espesor (sin nervios) | Túnel del USB-C 1.33; ranura y muesca de la microSD 1.32; agujeros de las anclas 1.31; ventana de la OLED 1.4; tecla y LED 1.8; uniones 1.2; tornillos radiales 2.24; pared normal y rayas 1.9. Barrido cada 1.5 mm: 1.19 en el chaflán de la ventana bajo el bolsillo (z 86.9), el resto ≥ 1.2 |
| Choques en posición final | 0 entre piezas, 0 de las piezas con las referencias y 0 entre referencias |
| Barridos (pasos de 0.5 mm) | 0 choques en los once (lista de abajo), también la funda del USB-C por su túnel y la tarjeta por su ranura |
| Holgura lateral en los barridos verticales | Compradas 0.5 (el pack por su cuna); impresas 0.4 (chasis por el tubo); placa por los rieles 0.25; carrier por sus ranuras 0.3 (ajuste). La placa roza los salientes M2 a propósito (contacto) |
| Chasis armado con la tecla puesta | Bloqueado: J102 choca con el émbolo a los 10.5 mm de subida. Sin la tecla sale limpio |
| Llave fija de 8 en la tuerca de la clavija, sin la placa | Holgura al chasis 0.94 recta y 0.5 girada ±30° |
| Chasis armado (chasis, placa real, OLED, carrier, clavija) | Radio máximo 25.2: 0.4 al tubo |
| Pack 1S2P (envolvente de 37.5 × 68 × 20) | 0.5 a la cuna por encima de las repisas, 0.5 a los topes de la tapa, 0.6 al chasis, 0.5 al retén de la tuerca, 1.8 a la carrier, 2.9 a la base; también al bajar por arriba |
| Holguras a la cara plana | Vidrio de la OLED 0.5; PCB, cinta y tornillos de la OLED 0.9; componentes 0.84; clavijas 0.75. La pestaña de la tecla va en su rebaje (contacto) |
| Tecla y guía de luz contra la placa real | Émbolo–SW401 0.5; tecla–otros componentes 1.9; guía de luz–D403 0.55 |
| Aberturas del costado | Funda del USB-C (12.35 × 6.5) a 0.3 de su túnel; tarjeta a 0.3 de su ranura al entrar y salir, y también trabada, porque queda dentro de la ranura |
| Otras holguras | Clavija acodada–placa 0.54 (el cuerpo sobre el canto; la tuerca pasa por la muesca); perno de 15.5–soldaduras de la carrier 1.2; perno–pack 3.3; tuerca del bastón–placa y carrier 0.81; cables–piezas 0.5, –pack 8.9 (sin los que van pegados), –placa y carrier 2.6 |
| Tapa de puertos (tres setas: 19°, z 20, 32.5 y 45) | Cada cabeza: 0.61 al chasis al barrerlo; en su sitio, 0.86 a la pared y 8.6 o más a lo demás. Pared entre cada agujero y las aberturas: 2.66 o más (túnel del USB-C a 2.66 de la seta de abajo). Cerrada, su cuerpo queda a 0.54 del canto de la tarjeta trabada. Abierta 135°: 1.62 a la funda del USB-C y 5.12 a la tarjeta; abierta 180°: 2.63 y 5.24 |
| Antena del WROOM (U201: x −15.15…−9.15, z 49.9–67.9) | Plástico del chasis a menos de 5 mm: 45.1 mm³, solo el saliente M2 de la OLED del lado −X, detrás de la placa (a 1.6). La pared del tubo queda a 1.69 del módulo |
| Nada de la placa por detrás de su dorso delante del SMA de la carrier (x −6…3, y < 13.8, z 60–80) | Cumple |
| Coaxial | Radio mínimo 12.27 en todo el recorrido; recorrido de 82.7; eje del cable hasta r 24.1; 0.59 a las piezas, 0.6 al pack, 4.4 a la placa y la OLED, 2.9 a la tapa |
| Mazos entre sí | Mazo del pack–arnés de J301 8.8; coaxial a 32 o más de todos |

Los barridos (pasos de 0.5 mm; choque si el volumen común pasa de 0.05 mm³):
- pack 1S2P por arriba (94.2 mm, hasta salir del tubo) contra el tubo y la base;
- carrier al chasis por abajo (60 mm; sin los labios de los ganchos, que se apartan);
- clavija SMA acodada por arriba con la carrier en el chasis y sin la placa (25 mm; tuerca con su
  barrido de 9.2);
- llave fija de 8 por delante (30 mm) y girada ±30°;
- placa real con la OLED por los rieles, por abajo (92 mm), con la carrier y la clavija puestas;
- chasis armado por arriba (103.5 mm, hasta salir del tubo), con el arnés de J301, el pack, su mazo
  y la tapa de puertos con sus tres setas, sin la tecla;
- base por abajo (20 mm) contra todo lo de dentro, con las clavijas y los cables reales;
- tapa con la antena y el pasamuros por arriba (20 mm);
- tecla por fuera (12 mm);
- tarjeta microSD por el costado (15 mm, por la ranura justa);
- tapa de puertos abriéndose hacia fuera (12 mm; las setas se quedan en sus agujeros).

En los barridos verticales se mide además la **holgura lateral** mínima: cada sección horizontal
de la pieza que se mueve contra las secciones del obstáculo por las que pasa (cada 0.5 mm de alto,
contornos cada 0.05 mm).

Con la envolvente de la especificación (`--envelope`), el mismo día: 0 choques de la carcasa, los
once barridos limpios y los mismos mínimos (impresas 0.4, rieles 0.25, compradas 0.5). Solo marca
referencia contra referencia: las zonas de clavija reales entran en la envolvente de componentes,
que las rellena.

**No verificado:**
- **El módulo OLED real** (no está en el STEP): separador de 1.3 y vidrio hasta y 20.0, dibujados
  desde sus medidas.
- **La carrier:** modelo sacado de una foto (±1 mm). Ver [Carrier: medir y suplementar](#carrier-medir-y-suplementar).
- **Cables:** reservas de Ø3.4, Ø1.6 y Ø3 por recorridos supuestos; no se sabe por dónde ni a qué
  altura del extremo del BMS salen los del pack real ni su calibre (se supone AWG22).
- **El pack:** medidas del anuncio; el modelo usa el peor caso (20 de grueso).
- **Antena:** modelo y conector sin confirmar; tamaño de su cavidad (¿cabe la tuerca del pasamuros
  si se monta por detrás?); si los tres M2.5 coinciden con el SMA apretado; rosca de 6 supuesta.
- **Pasamuros y clavija acodada:** no hay pieza elegida. Hay que comprobar en sus hojas el panel
  admitido (≥ 3), el largo por dentro (9 en el modelo) y la envolvente de la clavija acodada
  (cuerpo desde 0.5 por encima de la placa, 7 de ancho, salida del cable a 8.3 del eje).
- **Coaxial:** el recorrido tiene R 12.3, por encima del 6 × Ø de la hoja actual de Lapp; el cable
  real buscará su propio camino dentro de la reserva modelada.
- **Tapa de puertos de TPU:** la duración de la bisagra, el sellado de sus cuerpos a presión y lo que
  sujetan las tres setas. La comprobación gira la tapa como sólido rígido: no prueba cómo se dobla
  el TPU. Hay que imprimirla y probarla.
- **Acceso a la microSD con la uña:** según la hoja del zócalo, la tarjeta trabada queda 0.4 por
  debajo de la cara exterior en la muesca, se empuja 1.2 más para soltarla y expulsada sobresale
  2.7. Que se tome cómodo con la uña o la yema en la muesca de 8 solo se sabe probándolo impreso.
- **Antena del WROOM:** cuánto la desafinan el saliente M2 de la OLED, detrás de la placa, y la
  pared del tubo.
- **Perno del bastón:** el largo real de la rosca. Con más de 15.5 mm toca la carrier.
- **Impresión:** tolerancias de MJF (±0.3) frente a ajustes de 0.25–0.4; flexión de los ganchos;
  la pared de 1.19 junto a la ventana; agarre de los M2.5 radiales y del retén M2;
  ajuste a presión de la tapa de puertos; la membrana de la tecla; el pegado de la lámina y de la
  guía de luz; la estanqueidad de las uniones en escalón.
- **Llave:** envolvente de una llave fija de 8 genérica (bocas hasta 3.4 detrás del eje, cabeza de
  15 de ancho, 3.5 de grueso).
- **La unión base–tubo:** tornillos atrás y a los lados; delante solo el escalón. No se sabe si el
  borde se abre al cargar el bastón (ver [Lo que no se hizo](#lo-que-no-se-hizo)).

## Lo que no se hizo

- **Segundo retén de la tuerca.** Alrededor de la tuerca solo queda libre arriba hasta el pack
  (z 18.8) y la carrier (z 17), y delante está la placa. A 0° o 180° solo cabría un M2 de cabeza
  baja sin arandela que pisaría 0.5 mm de una esquina de la tuerca: no retiene. Queda el M2 de 270°
  con su arandela ancha.
- **Fijación delantera de la base** (cuarto tornillo o lengüeta). Delante, las clavijas de J301,
  J102 y J404 ocupan x −13.5…11.4 hasta z 2.75. Solo queda un hueco en x 11.9–15.5: una lengüeta
  de 3.6 de ancho con el tornillo en el canto de la cara plana. No se puso; la base queda sujeta
  delante solo por el escalón de la unión.

## Impresión

Pensada para **MJF (PA12 o PA11)**, como V2.3. La tecla, la tapa de puertos y el distintivo, en TPU; el distintivo, del color que se quiera. **Probar
primero un tramo de tubo y el chasis** (ver el principio).

**En FDM, como plan B:**
- las repisas del pack, los apoyos del chasis, los nervios de la cuna y los topes de la tapa
  tienen voladizos planos sin chaflán: necesitan soportes, o un chaflán de 45° que habría que
  añadir;
- los redondeos R4 de la base y de la tapa quedan bien solo con esa cara contra la cama;
- los ganchos de la carrier (brazos de 0.8 × 0.6 con ranuras de 0.6), los labios de 0.8 de los
  rieles, la bisagra de 0.6 de la tapa de puertos y la membrana de 0.4 de la tecla son demasiado
  finos para FDM con boquilla de 0.4: habría que rediseñarlos;
- el grabado del distintivo tiene detalles finos: en FDM con boquilla de 0.4 sale, pero con bordes redondeados.

## Regenerar

Requisitos: FreeCAD 1.1 (su Python). `geom_v3_0.py` tiene la geometría común, las referencias y
las guardas de la pared. Usa `hardware/main-board/cad/carrier_bdlx.py`,
`hardware/main-board/scripts/logo.py` (logo) y, si están, `hardware/main-board/cad/placa-principal.step`
y `.json` (placa real y eje de J401) y `hardware/main-board/kicad/plugs.json` (v0.3). Sin ellos, la
envolvente y la zona de clavijas de respaldo de `parameters.json`.

```bash
cd mechanical/v3.0
export PYTHONPATH=/Applications/FreeCAD.app/Contents/Resources/lib
/Applications/FreeCAD.app/Contents/Resources/bin/python build_v3_0.py
/Applications/FreeCAD.app/Contents/Resources/bin/python export_v3_0.py
/Applications/FreeCAD.app/Contents/Resources/bin/python check_v3_0.py   # placa real: unos 35 minutos
# con la envolvente de la especificacion (unos 20 minutos):
/Applications/FreeCAD.app/Contents/Resources/bin/python check_v3_0.py --envelope
```

- `build_v3_0.py` genera `generated/TresVizo-V3.0.FCStd` (piezas y referencias `ref_*`) y
  `model-index.json`.
- `export_v3_0.py` genera los STL y STEP de las piezas y comprueba las mallas, las interferencias
  entre piezas y la pared del tubo (sondas cada 1 mm). Si falta pared, termina con código 1.
- `check_v3_0.py` escribe `check.json`:
  - `guarda_pared_tubo`: sondas, volumen y espesores;
  - choques en posición final y en los barridos del montaje;
  - `holguras` en posición final y `holguras_laterales_en_barridos`;
  - `objetivos`: el mínimo conseguido en cada categoría (B1–B6) y lo que queda por debajo;
  - tapa de puertos, antena del WROOM, nada detrás de la placa delante del SMA, radio del chasis
    armado y coaxial.
