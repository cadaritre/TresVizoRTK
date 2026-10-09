# Carcasa V3.0 (exploratoria): tubo compacto para la placa principal v0.3

> **Estado:** geometría generada con scripts y comprobada en FreeCAD 1.1.3 contra la **placa v0.3
> real** (`hardware/main-board/cad/placa-principal.step` y las zonas de clavijas de
> `kicad/plugs.json` v0.3), la carrier BDLX modelada desde una foto, el pack 1S2P comercial, la tuerca y su
> retén, la antena con sus tornillos, el latiguillo coaxial con sus conectores y los mazos de cables,
> en posición final y en el montaje paso a paso. Revisión endurecida del 08-10-2026: **Ø56 × 116**
> (con las correcciones de la segunda auditoría externa: coaxial a R ≥ 12, mazos que no se cruzan,
> aberturas del costado justas, tapa de puertos con tres anclas y cuna para un pack 1S2P comercial).
> 09-10-2026: **marco del USB-C** (pieza 08) para que por el túnel solo se vea el receptáculo, y
> muesca de la microSD de verdad ciega (su chaflán atravesaba la pared). Después, **bandas de TPU**
> (piezas 09 y 10, de 40 mm, abajo y arriba), que tapan los seis tornillos radiales: el distintivo sube a
> z 56.3 y las rayas decorativas quedan entre las bandas (z 41.5–74.5). Ver
> [Bandas de TPU](#bandas-de-tpu-09-y-10).
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
> 4. **Probar el marco del USB-C en la placa real** (que entre por −X, que el resorte lo sujete y que
>    el labio quede bajo el dorso de la placa) antes de cerrar.
> 5. **Probar impresa la tapa de puertos de TPU** (que la bisagra aguante abrirla y cerrarla muchas
>    veces, que selle el túnel y la ranura y que las tres setas sujeten) y **el acceso a la microSD con
>    la uña** por su muesca. El modelo solo comprueba la tapa girada como sólido rígido: no prueba
>    cómo se dobla el TPU ni si una uña llega.
> 6. **Probar impresas las bandas de TPU** sobre el tramo de prueba: que el apriete de 0.3 por lado las
>    sujete sin que cueste demasiado ponerlas, que pasen por encima de las cabezas de los tornillos (sus
>    cantos asoman 0.11) y que la tapa de puertos se abra con la banda puesta.

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
Con las bandas de TPU puestas mide unos Ø60 en sus 40 mm de abajo y de arriba.

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
| Distintivo grabado | Hexágono con el 3, como en las carcasas V2.x: 18 × 20.7, centro z 56.3 (z 45.9–66.7, entre las bandas), grabado 0.8 en la cara plana (quedan 1.6 de pared) |
| Bandas de TPU | Abajo z 0–40 y arriba z 76–116; por fuera, 1.7 sobre el cuerpo (la cara plana de la banda en y 24.6) |

## Piezas

| Pieza | Qué es |
| --- | --- |
| 01-base | Disco de 2 mm con el anillo del redondeo R4 hasta z 4 y un **labio** de 0.8 × 1.5 que entra en el rebaje del tubo con 0.4 de juego. **Tuerca 5/8"-11 de latón** en un alojamiento hexagonal (0.3 por cara) sobre un anillo de asiento de 2; saliente r 16 recortado en y 13.3, hasta z 15.5; retén M2 detrás. Tres lengüetas (210°, 270°, 330°; r 22.2–25.2, z 2–10.6) para los tornillos radiales; nervio a 270°. Desagüe de Ø1.5 delante |
| 02-tube | Pared de 2.4 (R28, z 4–112) con la **cara plana** al frente. Rebajes de 1.2 × 1.9 por dentro en los dos extremos (uniones). Frente: ventana de la OLED con bolsillo exterior y chaflán por dentro, tecla, LED y **distintivo grabado** (hexágono con el 3). Costado +X: **túnel cerrado del USB-C**, **ranura justa de la microSD** con una **muesca estrecha para la uña** y tres agujeros para las **anclas de la tapa de puertos**. **Apoyos del chasis** (z 8–9.5), **cuna** de las celdas y **rayas decorativas** atrás |
| 03-antenna-cap | Disco de 4 mm (z 112–116) con el redondeo R4 de arriba y un **labio** que baja al rebaje del tubo. **Pasamuros SMA** en el centro (agujero Ø6.5 con cara plana, rebaje Ø13 por dentro: panel de 3). Pasos y rebajes Ø6 × 2.4 de los tres M2.5 de la antena. Dos **topes sobre las celdas** y tres lengüetas para los tornillos radiales |
| 04-chassis | Se arma fuera del tubo. **Rieles en C** sobre las franjas de 1 mm de la placa (0.25 por cara), con tope en z 80; **ranuras de la carrier** con topes arriba y **ganchos** flexibles abajo (0.3 de juego); **dos salientes** M2 detrás de la placa; **puente** con hueco para la tuerca de la clavija SMA y ventana para la llave; paredes laterales con un **tirador** cada una; la de +X, con una muesca por donde pasa el marco del USB-C |
| 05-key-tpu | Tecla de TPU que se pone y se saca por fuera: pestaña pegada en el rebaje exterior, membrana de 0.4, cabeza que asoma 1.0 y émbolo a 0.5 de SW401 |
| 06-port-cover-tpu | **Tapa de puertos** de TPU, atada: ala curva de 0.9 sobre el costado +X que tapa el túnel del USB-C y la ranura de la microSD (con sus cuerpos a presión por dentro), lengüeta delante para abrirla, bisagra fina y **tres setas** de anclaje por agujeros de Ø2 de la pared, repartidas por su canto de atrás |
| 07-logo-inlay-tpu | **Distintivo de TPU** (hexágono con el 3) para imprimir aparte, de otro color, y pegar en el grabado del frente: los mismos contornos reducidos 0.1 por lado, 0.8 de espesor, a ras de la cara plana. Son 6 islas: el hexágono, el 3 y cuatro rayas de unos 2 mm². Para imprimir: `generated/stl/07-logo-inlay-tpu-para-imprimir.stl`, acostado con la cara que se ve contra la cama |
| 08-usb-bezel | **Marco del USB-C**, de PA12 como la carcasa: pieza chica (0.32 cm³) que se pone en la placa, deslizándola por −X sobre el receptáculo, para que por el túnel solo se vea el receptáculo. Sigue el túnel desde la boca hasta el paso del chasis, cierra alrededor del blindaje de J101 con un collar, pasa un labio bajo el dorso de la placa y la abraza por el canto con dos ranuras; un dedo elástico sobre el blindaje lo sujeta mientras se arma. Con el chasis en el tubo queda atrapado. Ver [Marco del USB-C](#marco-del-usb-c-08-usb-bezel) |
| 09-band-bottom-tpu | **Banda de TPU de abajo**, z 0–40: 2.0 de espesor, 0.3 por lado más chica que el cuerpo (apriete), cantos de fuera redondeados 1.0. **Tapa** los tres tornillos de la base con bolsillos ciegos por dentro (Ø6.4 × 0.8; quedan 1.2 de TPU por fuera), ventana sobre la tecla y el LED y una **muesca abierta hacia arriba** alrededor de la tapa de puertos, con sitio para la uña delante de la lengueta. Debajo de la muesca queda un anillo completo de 15.9. Ver [Bandas de TPU](#bandas-de-tpu-09-y-10) |
| 10-band-top-tpu | **Banda de TPU de arriba**, z 76–116, a ras de la cara de arriba de la tapa: como la de abajo, tapa los tres tornillos de la tapa con bolsillos ciegos por dentro y lleva una **muesca abierta hacia abajo** alrededor de la ventana de la OLED y el bolsillo de su lámina |

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
7. **Marco del USB-C (08), por fuera, hacia −X**, con la placa ya en el chasis y antes de meter el
   chasis en el tubo. Se presenta en el eje del receptáculo con el labio por debajo del canto de la
   placa (por el dorso) y el collar por encima, y se empuja hacia −X: el canto de la placa entra en
   sus dos ranuras, el labio pasa bajo el dorso (chaflán de entrada), el collar rodea el blindaje de
   J101 y el tope del resorte sube por la boca y aprieta el techo del blindaje. Para cuando el fondo
   de las ranuras toca el canto de la placa (x 18). El suelo del marco pasa por encima de la muesca de
   la pared lateral +X del chasis. El resorte lo sostiene mientras se mete el chasis; dentro del tubo
   queda atrapado.
8. **Chasis armado al tubo, por arriba**, con el pack puesto y **sin la tecla**. Las paredes
   laterales, los rieles y el marco del USB-C bajan junto a la pared (0.4) y el pie de los rieles
   apoya en los apoyos del tubo (z 9.5). La tapa baja a la vez, colgada del latiguillo.
9. **Tapa** en su sitio. El latiguillo queda en su recorrido: hacia −X sobre el puente, por fuera
   del extremo −X del pack (entre él y la pared), por detrás de él y por encima del pack sube hacia el
   eje y el pasamuros. Tres M2.5 radiales en z 107.
10. **Por abajo, sin la base:** clavija de la batería a J102 y de la NTC a J404 (con la tapa ya
   puesta). Se recogen los mazos en su recorrido y se pone la base con sus tres M2.5 radiales en
   z 8.5.
11. **Bandas de TPU** (09 y 10), con la carcasa cerrada y **antes de la tecla**: la de abajo se desliza
    por abajo, con la muesca hacia la tapa de puertos (la cara plana de la banda contra la cara plana),
    hasta que su canto queda a ras de la cara de abajo de la base; la de arriba, por arriba, por encima de
    la antena, con la muesca hacia la ventana de la OLED, hasta que queda a ras de la cara de arriba de la
    tapa. Cada banda **tapa** los tres M2.5 de su lado (bolsillos por dentro): se giran hasta que la cara
    plana coincide y los bolsillos quedan sobre los tornillos. Al pasar, el TPU se estira 0.11 sobre los
    cantos de las cabezas, que asoman de la pared curva. La tecla asoma 1.0: con ella puesta la banda de
    abajo no pasa. Ver [Bandas de TPU](#bandas-de-tpu-09-y-10).
12. **Tecla, lámina de la ventana y guía de luz**, por fuera. La tecla entra por la ventana de la banda
    de abajo y se pega con cinta adhesiva fina de doble cara o un adhesivo flexible que se pueda
    despegar: hay que sacarla para sacar el chasis.
    **Distintivo de TPU** en su grabado: pegado con un adhesivo para TPU (cianoacrilato flexible o
    de contacto), una gota en el fondo de cada isla. Para no perder las rayas chicas, al despegarlas
    de la cama ponerles encima cinta de enmascarar y pasarlas juntas, como una calcomanía.
13. **microSD** por la ranura del costado; la tapa de puertos cierra el túnel del USB-C y la ranura.

## Desmontaje y servicio

**Para abrir la base o la tapa hay que sacar antes su banda**, como en V2.3: las bandas tapan los seis
M2.5 radiales. La tapa de puertos (el USB-C y la microSD) se abre con la banda puesta y la tecla sale
por su ventana.

1. **Tecla fuera**, por fuera, por la ventana de la banda de abajo. Con la tecla puesta el chasis no
   sale: su émbolo queda delante de la placa y J102 choca con él a los pocos milímetros de subir; la
   banda de abajo tampoco.
2. **Banda de abajo fuera**, por abajo, y **base fuera** (tres M2.5 de z 8.5). Desenchufar **J102**
   (batería) y **J404** (NTC) por abajo.
3. **Banda de arriba fuera**, por arriba (pasa por encima de la antena), y **tapa suelta** (tres M2.5
   de z 107). No sale del todo: sigue unida a la carrier por el latiguillo. Se levanta lo que deja el
   cable y se sostiene.
4. **Chasis fuera, por arriba**, tirando de los dos tiradores con un gancho o un alambre (agujeros
   Ø2.5: el de +X arriba, en z 107–111.6; el de −X en z 79–83, por debajo del paso del coaxial). La
   tapa sale con él, colgada del latiguillo. El pack se queda en el tubo.
5. **Marco del USB-C fuera:** tirar de él hacia +X (el resorte suelta el blindaje). Con el marco
   puesto la placa no baja: sus ranuras abrazan el canto.
6. **Placa fuera del chasis:** desenchufar J301, quitar los dos M2 de la OLED y bajar la placa por
   los rieles.
7. **Clavija SMA acodada fuera:** llave fija de 8 por delante, por la ventana del puente. La tapa
   con la antena y el latiguillo queda libre.
8. **Carrier fuera:** abrir los dos ganchos (apartar el labio hacia fuera) y bajarla por las ranuras.
9. **Pack fuera,** por arriba (dejar una cinta bajo el pack para tirar de ella).
10. **Antena:** los tres M2.5 por dentro de la tapa y desenroscarla del pasamuros. El pasamuros sale
   aflojando su tuerca (por dentro o por fuera, según el montaje).
11. **Tuerca del bastón:** quitar el retén M2 y sacarla por arriba.

Para volver a armar, al revés: la clavija acodada siempre antes que la placa, el marco del USB-C
después de la placa y antes de meter el chasis, las bandas con la carcasa cerrada y la tecla siempre al
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
  entrada de 0.4 a 45° por dentro; tecla (Ø6.4 y rebaje Ø9 × 0.6); LED (Ø2); distintivo grabado 0.8 (hexágono con el 3),
  centrado en z 56.3, entre las bandas.
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
  - **muesca ciega para la uña** en el centro de la tarjeta: 8 de ancho (z 36.88–44.88), de la
    ranura hasta y 20.2, con fondo plano en x 20.51: no atraviesa y no deja ver el lector (elección
    del propietario, 09-10-2026). El fondo cae a 90° sobre el techo de la ranura, donde la pared de
    detrás mide 1.2 (r 26.8), y más arriba es más gruesa. Con un fondo curvo en r 26.8 el encuentro
    con el techo de la ranura era un filo de ~50° que dejaba la pared en 0.71.
  - **Posiciones de la tarjeta**, de la hoja de SOFNG del TF-015 (LCSC C113206), medidas desde la
    boca de J401 (x 16.5):
    - trabada, asoma 2.50 (x 19.0), dentro de la ranura;
    - para soltarla se empuja hasta 1.32 (x 17.82), 1.2 más: con la uña o un clip, 2.7 dentro de
      la ranura desde el rebaje;
    - expulsada, asoma 5.60 (x 22.1): queda 1.6 al descubierto en el rebaje, de donde se toma con
      la uña. En el plano de la ranura queda 0.6 por dentro de la cara exterior.

    Antes el modelo la tenía trabada en x 17.5, 1.5 más adentro de lo real, y la muesca atravesaba
    la pared.
  - chaflanes de 45° en los cantos de fuera de arriba de la ranura y de la muesca (1.2), y uno de
    0.8 por dentro en el canto del suelo de la ranura (cuña de ~53°; no se ve desde fuera). El de la
    muesca también se queda delante del fondo plano, en x ≥ 20.51 (corregido el 09-10-2026: empezaba en
    x 18.19 con todo el alto de la muesca y atravesaba la pared de detrás entre y 17.25 y ~18; de frente
    se veía el interior);
  - **agujeros de las anclas** de la tapa de puertos: Ø2 radiales a 19°, en z 20, 32.5 y 45.
  - **Qué se ve desde fuera sin la tapa:** por el túnel, la boca del receptáculo al fondo, rodeada
    por el collar del **marco del USB-C** (pieza 08), que sigue el túnel desde la cara interior hasta
    la boca; debajo de la boca, el canto de la placa. Por la ranura, el canto de la tarjeta (o la boca
    de J401). La muesca es ciega: su fondo es pared. Lo que aún se ve, medido con rayos, en
    [Marco del USB-C](#marco-del-usb-c-08-usb-bezel). El túnel no se alarga con paredes del tubo
    por dentro: el chasis con la placa entra por arriba y pasaría por ahí; por eso el marco es una
    pieza aparte que baja con el chasis.
- **Rayas decorativas** como las de V2.3: 1.3 de ancho y 0.5 de hondo (quedan 1.9 de pared), en dos
  grupos de 5 a 9° (198–234° y 306–342°: simétricos respecto al eje frente-atrás), **z 41.5–74.5,
  solo entre las bandas de TPU** (1.5 de cada canto; como en V2.3, «en z 34–98, entre las bandas»), lejos
  de la cara plana, el logo, la tapa de puertos y las aberturas. Antes iban de z 11.5 a 105 y las
  bandas las tapaban.

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
  - El riel +X se corta en z 16.6–47.2, frente al marco del USB-C (que empieza en z 17.02: 0.4) y a la
    tarjeta. Antes empezaba en z 18.0: el marco no cabía.
  - **Antena del WROOM (U201):** el riel −X y la punta de la pared lateral se quitan en z 44.5–73
    (x −22.5…−15.5, y 11.5–17): nada de plástico del chasis a menos de 5 mm de la antena, salvo el
    saliente M2 de la OLED del lado −X, detrás de la placa.
- **Paredes laterales** x ±19.6–21.6, y 4.3–12.76, desde z 9.5 (pie sobre los apoyos del tubo):
  la de +X hasta z 111.6, con el **tirador** arriba (z 107–111.6, agujero Ø2.5); la de −X acaba en
  z 83, por debajo del coaxial, con su tirador en z 79–83. La de +X baja a y 11.4 entre z 16.6 y
  33.4 (**muesca**): por encima pasa el suelo del marco del USB-C con 0.4.
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

### Marco del USB-C (08-usb-bezel)

Pieza de PA12, como la carcasa, para que con la tapa de puertos abierta por el túnel solo se vea el
receptáculo. Antes se veía la placa verde, componentes y huecos hacia dentro: el túnel del tubo solo
existe donde hay pared (r ≥ 25.6) y entre la cara interior y la boca de J101 (x 14.9) quedaban
hasta 7 mm abiertos.

**Por qué es una pieza aparte:** una pared fija al tubo por dentro de r 25.6 cortaría el paso del
chasis al bajar, y una pared fija al chasis alrededor del receptáculo cortaría el de la placa, que
sube por los rieles con J101, J401 y el resto de componentes de cara. El marco se pone **con la
placa ya en el chasis y antes de meter el chasis en el tubo**, deslizándolo por −X sobre el
receptáculo, y baja con el chasis dentro del paso de este (r ≤ 25.2, y ≤ 20.1: 0.4 al tubo).

Qué tiene (`costado.usb_c.marco`):
- **Túnel:** el mismo rectángulo redondeado del tubo (12.95 × 7.1, R1.3: la funda máxima de
  12.35 × 6.5 más 0.3 por lado), en el eje de J101, desde x 14.7 hacia fuera hasta el paso del
  chasis. Suelo de 1.2 (y 11.85–13.05) y paredes de 1.5 a los lados (z 17.02–18.53 y 31.47–32.98).
  **Sin techo:** el túnel llega a y 20.15 y nada del chasis armado puede pasar de y 20.1. Encima
  queda la cara plana del tubo (y 20.5). Por encima de y 18.85 los lados siguen rectos: las esquinas
  R1.3 del techo, que queda fuera, dejaban cuñas en lo alto de las paredes.
- **Collar** de x 13.5 a 14.7, alrededor del blindaje de J101 (0.1 por lado y por arriba) y a 0.2
  sobre la cara de la placa. Va 0.2 por detrás de la boca: con la tolerancia de MJF no puede quedar
  delante de ella, donde llega la funda.
- **Labio** bajo el dorso de la placa, apoyado en él (y 13.8), de x 13.5 a 14.7: cierra la franja
  de y 13.05 a 13.8 que el túnel tiene por debajo del canto de la placa. Chaflán de entrada de 0.3.
  Queda a 0.5 de los agujeros de las patas de J101 (x 13.0).
- **Ranuras para el canto de la placa** fuera de la muesca (y 13.8–15.6, por encima y por debajo de
  los lados del túnel). Su fondo, en x 18.0, apoya en el canto de la placa: es el tope al empujarlo.
  La ranura mide 1.8 para una placa de 1.6 ± 0.16.
- **Resorte:** dedo de 0.8 × 8 sobre el techo del blindaje, de la cara de atrás del collar (x 13.5)
  a x 8.0, a 0.1 del techo, con un tope cilíndrico de R0.5 en la punta que baja 0.2 por debajo del
  techo nominal (0.17 contra el STEP real). Al montar, el tope sube por el canto de la boca y el
  dedo se dobla: unos 2.8 N con 0.2 (cálculo, no medido); con las tolerancias de MJF, de la placa y de
  J101, entre 0 y unos 0.45 mm, hasta 36 MPa en la raíz (PA12: unos 48). Empuja el marco hacia +y y lo
  deja con el labio contra el dorso de la placa: así la rendija que deja la tolerancia del espesor de
  la placa queda en la cara, solo a los lados del blindaje, y no bajo el canto en todo el ancho. El
  resorte solo hace falta mientras se arma: dentro del tubo el marco queda atrapado y, si el resorte se
  afloja con el tiempo, no pasa nada.
- **Zonas prohibidas:** cada componente de la placa salvo J101 (`placa-principal.json`, y las partes
  reales de J401 en `cajas_placa_real`), crecido 0.5 y alargado hacia −X, porque el marco pasa por
  encima al entrar. R412 (bajo el lado −z del túnel, a 0.88) y J401 (sobre el lado +z, a 1.13) dejan
  menos de 1.0 de pared entre su zona y el túnel entre x 14.7 y 17: ahí las paredes de los lados se
  quitan (son los huecos de «Qué se ve todavía», abajo). La esquina de la zona de J401 quedaba además a
  0.55 del paso del chasis: esa esquina de la pared también se quita, para no dejar un cuello fino.
- **Cambios en el chasis** para que pase con 0.4: el riel +X se corta desde z 16.6 (antes 18.0) y la
  pared lateral +X baja de y 12.76 a 11.4 entre z 16.6 y 33.4.

Por qué un resorte y no otra cosa: un enganche al chasis obligaría a tocarlo (se pide 0.4 al chasis)
y un ajuste a presión sobre el blindaje depende de la tolerancia de MJF (±0.2–0.3), de la de la placa
(±0.16) y de la de J101: o no entra o queda suelto. El dedo absorbe esa diferencia. Sin pegamento.

**Holguras, medidas** (`holguras` y `marco_usb_c` en [check.json](generated/check.json)): 0.4 al tubo,
0.425 al chasis, 0.45 a los cuerpos de la tapa de puertos, 0.5 a R412 y a J401 (los componentes más
cercanos; luego Q103 1.45 y U401 1.68), 1.75 a la carrier (su USB-C), 11 al pack y sus cables; 0.1 al
blindaje de J101 sin contar el resorte; la funda, 0.3 por lado en el túnel del marco y 0.2 en x hasta el
collar y el labio. Al deslizarlo por −X (barrido de 15 mm) no toca nada y las holguras mínimas son las
de su sitio. El tope del resorte entra 0.17 en el techo del blindaje del STEP real (0.34 mm³): es el
apriete.

**Atrapado** (parte rígida movida hasta tocar algo, con el chasis en el tubo): 0.45 hacia el tubo (+X;
el collar y el labio siguen 0.95 sobre el blindaje y bajo la placa), 0.13 hacia atrás (−y, el collar
llega al techo del blindaje; el resorte empuja al revés), 0.1 a cada lado en z (lados del blindaje) y
nada hacia dentro (−X: fondo de las ranuras en el canto de la placa) ni hacia +y (labio en el dorso).
Fuera del tubo solo sale tirando hacia +X, contra el resorte.

**Qué se ve todavía** (`visibilidad` en check.json). Rayos desde la piel del tubo, dentro del túnel,
hacia dentro, con la tapa de puertos abierta: de frente (rejilla de 0.05 mm, 36 178 rayos) y en 49
direcciones de hasta 30° en y y en z (110 677 rayos). Cuenta como permitido J101, J401, la tarjeta, el
tubo, el marco, la tapa de puertos y el canto de la placa bajo J101 (x 14.9, y 13.8–15.4).
- **De frente, 98.3 % permitido:** marco 43.4 %, J101 31.2 %, canto de la placa bajo J101 22.9 %, tubo
  0.9 %. El 1.7 % restante:
  - **rendija de 0.2 sobre la cara de la placa**, a los lados del blindaje (z 18.5–20.4 y 29.6–31.5):
    es el juego de la ranura para el espesor de la placa (1.6 ± 0.16 en 1.8; el resorte la deja en
    la cara y no bajo el canto). Por ahí se ven de canto componentes bajos de detrás de J101: D101
    0.28 %, SW401 0.25 %, Q103 0.24 %, U101 0.11 % y otros de menos de 0.1 %;
  - **rendijas de 0.1 entre el collar y los lados del blindaje** y la **franja de y 20.1–20.15**
    encima del marco (el túnel llega a 20.15 y nada del chasis armado puede pasar de 20.1): por ahí
    se ve la tecla de TPU por dentro (0.38 %) y la cara plana del tubo por dentro (cuenta como tubo).
- **En las 49 direcciones, 97.9 % permitido.** Lo demás:
  - **lados de la muesca de la placa** (z 18.5 y 31.5, x 14.9–18, 0.96 %): la muesca mide lo mismo que
    el túnel y sus lados quedan dentro de los 0.3 de guía de la funda; taparlos metería material en esa
    holgura;
  - **cara de la placa** (0.95 %): por la rendija de 0.2 y por los dos huecos de las paredes de los
    lados entre x 14.7 y 17 (R412 bajo el túnel, a 0.88 de él, y J401 encima, a 1.13: con 0.5 de aire
    no queda pared de 1.0; desde ahí también se ve R412);
  - componentes sueltos por esas mismas rendijas (Q103, J102, D101, J404, SW401, R411…: 0.03 % o menos
    cada uno), la tecla y la base (0.01 %).

**microSD** (la misma prueba por la ranura y la muesca, sin tarjeta y con ella trabada; el marco no
llega ahí y no se cambió nada salvo el chaflán de la muesca, ver el costado del tubo): de frente solo
se ve J401 o la tarjeta y el tubo (el fondo de la muesca ciega): 0 % de otra cosa. Inclinando la vista
10° o más: mirando hacia abajo, el canto exterior de la placa (x 18) y su cara entre la boca de J401 y
el canto (la ranura va 0.25 sobre la cara); mirando hacia arriba, el ESP32 (U201) por encima de J401 y
el riel del chasis donde vuelve a empezar (z 47.2). En total 11.4 % de los rayos sin tarjeta (canto
exterior de la placa 6.9 %, su cara 4.2 %, U201 0.2 %, riel 0.2 %) y 8.7 % con ella. Antes del arreglo
del chaflán, de frente se veía el interior por la parte baja de la muesca (6.9 % de los rayos de
frente).

### Bandas de TPU (09 y 10)

Dos fundas de protección de TPU de **40 mm** de alto (pedido del propietario: «una de 4 cm arriba y
otra de 4 cm abajo»), el mismo concepto que las de V2.2 y V2.3 adaptado a V3.0. Van por fuera, sobre
la superficie, **tapan los seis M2.5 radiales** (pedido del propietario, como V2.2 y V2.3) y no cambian
nada de la carcasa, que ya está pedida.

| | Banda de abajo (09) | Banda de arriba (10) |
| --- | --- | --- |
| Alto | z 0–40, a ras de la cara de abajo de la base | z 76–116, a ras de la cara de arriba de la tapa |
| Cubre | la base (su redondeo R4) y el arranque del tubo | el final del tubo y la tapa (su redondeo R4) |
| Tornillos | los tapa: bolsillos ciegos por dentro sobre los tres M2.5 de la base (z 8.5; 210°, 270° y 330°) | los tapa: bolsillos ciegos sobre los tres M2.5 de la tapa (z 107; 0°, 180° y 270°) |
| Aberturas | ventana de la tecla y el LED; muesca abierta hacia arriba alrededor de la tapa de puertos | muesca abierta hacia abajo alrededor de la ventana de la OLED y su bolsillo |
| Anillo completo | z 0–15.86 (solo con los bolsillos de los tornillos, por dentro) | z 88.78–116 |

**Perfil** (`bandas` en [parameters.json](parameters.json)):
- Sigue el contorno del cuerpo: el círculo R28 cortado por la cara plana en y 22.9 (en V3.0 esa unión es
  viva; el redondeo del cuerpo es el R4 de arriba y de abajo). **Espesor 2.0.**
- **Apriete 0.3 por lado** (0.6 en diámetro, como V2.2 y V2.3): por dentro, el contorno del cuerpo
  desplazado 0.3 hacia dentro; por fuera, 1.7 hacia fuera, con la esquina de la cara plana en arco
  (R1.7). Por fuera mide Ø59.4 impresa (unos Ø60 puesta) y su cara plana queda en y 24.6. El modelo
  dibuja la banda con su medida de impresión: el solape de 0.3 con el tubo, la base y la tapa es el
  apriete (no es un choque; se informa aparte).
- **Recta por dentro hasta el canto**, también delante de los redondeos R4 de la base y de la tapa (no
  los abraza). Toca el canto de la base (y el de la tapa) solo donde el R4 pasa de r 27.7 (los últimos
  1.5 mm, z 2.5–4 y 112–113.5); más abajo queda una rendija que se abre hasta 3.7 en la cara de abajo.
  El canto de la banda apoya en la mesa junto con la base, como un pie blando. Abajo empieza en r 27.7: el hombro de un
  bastón normal queda muy por dentro (el bastón no está modelado).
- **Sin tope:** se deja a ras a mano y la sujeta el apriete. Los bolsillos de los tornillos fijan el giro
  junto con la cara plana, no la altura.
- **Cantos redondeados:** 1.0 en todos los de fuera (los dos cantos libres y los bordes de las
  aberturas) y 0.5 en el de dentro que entra primero al ponerla (el de arriba de la de abajo y el de
  abajo de la de arriba), que tiene que pasar por encima del canto vivo de la cara plana (abajo en la
  base y arriba en la tapa, donde no hay R4) y de las cabezas de los tornillos. El canto de dentro que va
  contra la cama queda vivo. Las esquinas de las dos muescas, **R2** por dentro, para que el TPU no se
  rasgue desde una esquina viva.

**Aberturas y holguras** (medidas en [check.json](generated/check.json), `bandas`):
- **Tornillos de la base y de la tapa: bolsillos ciegos por dentro** (`bandas.bolsillos_tornillos`), uno
  por tornillo (no una ranura corrida: la cara plana fija el giro de la banda). Ø6.4 = cabeza de 5 + 0.7
  por lado, y 0.8 de hondo desde la cara de dentro, con el fondo curvo, concéntrico con la banda: quedan
  **1.2 de TPU por fuera** de cada tornillo (medido con un rayo por su eje). La cabeza avellanada es
  plana y la pared curva (R28): con su centro a ras, sus cantos asoman **0.11**. El bolsillo tiene que
  salvar esos 0.11 más el apriete de 0.3 (0.41): con 0.8, la banda puesta queda a **0.7** de cada cabeza
  (0.71 del fondo a los cantos, 0.7 a los lados). Con su medida de impresión, que en la carcasa no se da
  (está 0.3 dentro del cuerpo), quedaría a 0.39 del fondo.
- **Tecla y LED:** una sola ventana, la envolvente convexa de un círculo de Ø11 en la tecla (pestaña de
  8.8: 1.1 por lado, pedido 1.0 o más para que la banda no la toque nunca) y uno de Ø5 en el LED (guía de
  luz de Ø2: 1.5 por lado). La cabeza de la tecla (asoma 1.0) queda 1.0 por debajo de la cara de la
  banda puesta, en una ventana de 11: se aprieta con la yema y la protege de golpes. Holguras medidas: tecla
  1.1, guía de luz 1.5.
- **Tapa de puertos:** muesca abierta hacia el canto de arriba alrededor de toda su huella (ala,
  bisagra, ancla, lengüeta). Detrás, un plano paralelo al canto de atrás del ala (16.5°) a 0.94; delante,
  el canto en x 9.1 (3.5 delante de la lengüeta, que está en x 12.6: **sitio para la uña**); abajo,
  z 15.86 (0.94 bajo el ala, que empieza en z 16.8). Con las esquinas R2, la holgura mínima, en la
  esquina de atrás y abajo, es **0.5** (pedido para una pieza de TPU que se mueve); en los lados rectos,
  0.94. Holgura medida a la tapa cerrada 0.5; a la lengüeta, 3.5.
- **Anillo completo** debajo de la muesca: **z 0–15.86** (pedido: 12 o más). La ventana de la tecla
  empieza más arriba (z 16.5).
- **Desagüe:** queda dentro del contorno del cuerpo, en la cara de abajo de la base (y 19.2); la banda
  queda a 2.65 del agujero.
- **OLED:** muesca abierta hacia el canto de abajo, x ±14.21, de z 76 a 88.78 (esquinas R2): 1.29 al
  bolsillo de la lámina en los lados rectos y 1.0 en las esquinas, para que la banda no tape la pantalla
  al mirarla de lado. Holgura medida al bolsillo 1.0 y a la lámina 1.14.
- **Cara de arriba de la tapa y antena:** la banda de arriba acaba en z 116, a ras, y no entra por
  dentro de su contorno de apriete: no tapa la cara de arriba de la tapa. La antena (Ø43.5) apoya en esa
  cara: el canto de dentro de la banda le queda a 0.85 en planta (delante, donde la banda va en y 22.6) y
  sus tornillos, por dentro de la tapa, a 6.8.

**Orden de montaje y servicio.** Las bandas se ponen con la carcasa cerrada (base, tapa y sus seis M2.5
puestos) y **antes de la tecla**, que entra al final por la ventana de la banda de abajo (asoma 1.0: con
ella puesta la banda no pasa). Para abrir la base o la tapa hay que sacar antes su banda (ver
[Cómo se arma](#cómo-se-arma), paso 11, y [Desmontaje y servicio](#desmontaje-y-servicio)).

**Margen de estiramiento sobre las cabezas de los tornillos.** Al poner cada banda, su cara de dentro pasa
por encima de las seis cabezas avellanadas, cuyos cantos asoman **0.11** de la pared curva. La carcasa
ya está pedida y los avellanados no se cambian, así que ahí el TPU se tiene que estirar 0.11 (en el
modelo, la banda estirada rígida entra 0.82 mm³ como máximo en las cabezas al pasar; va a 0.02 de la
pared, así que la entrada es de 0.09). Es el único sitio donde las bandas cuentan con estirarse: el
barrido contra todo lo demás sale limpio. En su sitio cada cabeza queda en su bolsillo.

**Tapa de puertos con la banda puesta.** La parte de delante de la bisagra se gira como sólido rígido,
como en la comprobación de 135° y 180°, ahora con la banda de abajo **estirada** (como está montada:
por fuera llega a r 30.02) como obstáculo, en pasos de 1° con bisección. Llega a **155.5°** antes de
tocar el canto de atrás de la muesca (con la medida de impresión, 158.8°). En ese ángulo quedan
2.63 a la funda del USB-C y 5.24 a la tarjeta (a 135°: 1.62 y 5.12, como sin la banda). A 180° la
tapa rígida ya entraría en la banda; el TPU de verdad se dobla.

**Distintivo y rayas entre las bandas.** El distintivo grabado (y su incrustación de TPU, que sale de
los mismos parámetros) sube de z 49.5 a **56.3** (z 45.9–66.7): en el medio del hueco entre la banda de
abajo (z 40) y el bolsillo de la lámina de la OLED (desde z 72.52), 5.9 a cada lado (pedido 2 o más). Las
rayas decorativas van solo **entre las bandas**, como en V2.3: z 41.5–74.5, 1.5 de cada canto.

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
| Ajuste entre piezas impresas | ≥ 0.4 | **0.4** | chasis–tubo, chasis–base, chasis–tapa, marco del USB-C–tubo y labios y lengüetas de base y tapa en el tubo, también al bajar el chasis. Marco–chasis 0.425; marco–tapa de puertos 0.45; tapa de puertos–chasis 0.61; cabezas de las tres setas al barrer el chasis 0.61 |
| Placa en los rieles, por cara | ≥ 0.25 | **0.25** | en su sitio y al subir la placa por los rieles |
| Aire a piezas compradas | ≥ 0.5 | **0.5** | en el límite de diseño: componentes de la placa–tubo (h(x)), pack–cuna, topes de la tapa y retén, placa–base, SMA de la carrier–placa, cables–piezas, clavija acodada–chasis, tornillos de la antena–tapa, componentes de la carrier–chasis y marco del USB-C–R412 y –J401 (también al deslizarlo); las celdas al bajar por la cuna. El coaxial, 0.59 o más. El resto, más |
| Funda del USB-C y tarjeta | 0.3 por lado (aberturas justas) | **0.3** | túnel cerrado, también en el marco del USB-C, y ranura justa, pedidos por el propietario: van guiadas, no es aire de 0.5. La tarjeta trabada (asoma 2.5 de J401) queda dentro de su ranura |
| Carrier en sus ranuras | juego 0.3 por cara | 0.3 en su sitio y al subirla | ajuste de posición: ver [Carrier](#carrier-medir-y-suplementar) |
| Pared del tubo | ≥ 1.2 (local ≥ 1.0) | **1.19**, local | chaflán de la ventana de la OLED bajo el bolsillo de la lámina (barrido del 08-10-2026, z 86.9). Uniones 1.2; túnel del USB-C 1.33; agujeros de las anclas 1.34; ranura y muesca ciega de la microSD 1.75 (con el fondo plano; con fondo curvo era 0.71) |
| Paredes del marco del USB-C | ≥ 1.0 (local ≥ 0.8) | **0.8** | el dedo del resorte, a propósito; sin él, 1.1 o más |
| Radio de curva del coaxial | ≥ 12 en todas las curvas | **12.27** | todo el recorrido (6 × Ø de la hoja actual: 10.9–11.6) |
| Mazos entre sí | ≥ 0.3 | **8.8** | mazo del pack–arnés de J301 (los hilos de la NTC se juntan con el mazo del pack a propósito) |
| Bandas de TPU a piezas de TPU que se mueven | ≥ 0.5 (tecla ≥ 1.0) | **0.5** | tapa de puertos, en la esquina redondeada de la muesca (0.94 en los lados); tecla 1.1. La tapa de puertos se abre hasta 155.5° sin tocar la banda |
| Bandas de TPU a piezas compradas | ≥ 0.5 | **0.7** | cabezas de los M2.5 en sus bolsillos, con la banda puesta (0.7 a los lados, 0.71 al fondo); antena 0.85; lámina de la OLED 1.14 (bolsillo 1.0); guía de luz 1.5 |

Nada queda por debajo en las categorías de aire y ajustes. Con la envolvente de la especificación
(`--envelope`) no se volvió a pasar después del marco (ver [Verificaciones](#verificaciones)).

**Ajustes de posición** (no son aire; van guiados a propósito):

| Dónde | Juego de diseño |
| --- | --- |
| Placa en los rieles del chasis | 0.25 por cara (y y fondo en x) |
| Carrier en sus ranuras, topes y ganchos | 0.3 por cara |
| Tuerca del bastón en su hexágono | 0.3 entre caras (0.15 por cara) |
| Pasamuros en su agujero en D | Ø6.5 y cara plana a 5.8 sobre rosca de 6.35 |
| Setas de la tapa de puertos en sus agujeros | vástago Ø1.95 en Ø2.0 |
| Lámina de la ventana en su bolsillo | 0.1 por lado |
| Funda del USB-C en su túnel | 0.3 por lado (pedido del propietario: abertura justa), también en el túnel del marco |
| Marco del USB-C en la placa | labio apoyado en el dorso (y 13.8) y fondo de las ranuras en el canto (x 18.0); 0.2 sobre la cara y 0.1 alrededor del blindaje de J101 |
| Tarjeta microSD en su ranura | 0.3 por lado (ídem) |
| Guía de luz en su agujero | Ø2 en Ø2, pegada |
| Bandas de TPU sobre el cuerpo | apriete de 0.3 por lado (0.6 en diámetro), como V2.2 y V2.3 |

**Contactos a propósito:** pie de los rieles del chasis en los apoyos del tubo (z 9.5); placa
contra los salientes (y 13.8) y contra el tope (z 80); pack en sus repisas (z 18.8); base y tapa
contra los cantos del tubo; cabezas de los tornillos en sus avellanados y arandelas en sus
asientos; tecla pegada en su rebaje y membrana sellando el agujero; tapa de puertos apoyada en el
tubo, con sus cuerpos de TPU a presión en el túnel y en la ranura (sellan); NTC e hilos de la NTC
pegados con kapton en la cara de atrás del pack; cables del pack saliendo de su extremo; clavijas
enchufadas; marco del USB-C con el labio en el dorso de la placa y el fondo de sus ranuras en el canto,
y su resorte apretando el techo del blindaje de J101 (0.2 nominal; 0.17 y 0.34 mm³ contra el STEP real);
bandas de TPU sobre el tubo, la base y la tapa (apriete de 0.3 por lado; en el modelo, 1605.4 y 1722.2
mm³ de solape con el tubo y 78.3 con la base y con la tapa) y, al ponerlas, sobre los cantos de las
cabezas de los M2.5, que asoman 0.11 (margen de estiramiento: ver [Bandas de TPU](#bandas-de-tpu-09-y-10)).

**Rasgos finos a propósito** (menos de 1.0; medidos en secciones horizontales de cada pieza):
brazos de los ganchos 0.6 × 0.8 con ranuras de 0.6; labios de las ranuras de la carrier 0.65;
labios y dorso de los rieles 0.8; labios de las uniones de base y tapa 0.8; dedo del resorte del
marco del USB-C 0.8; en TPU, ala de la tapa de puertos 0.9, su bisagra 0.6 y membrana de la tecla 0.4. La pared más fina de la base es la de
delante del alojamiento de la tuerca (1.24).

## Verificaciones

Hechas el 09-10-2026, con el marco del USB-C y las bandas de TPU, con FreeCAD 1.1.3 sobre los archivos
de esta carpeta ([generated/check.json](generated/check.json), [generated/exports.json](generated/exports.json)).
- **Placa real:** `hardware/main-board/cad/placa-principal.step` (PCB y componentes) y su
  `placa-principal.json`, reexportados a las 15:37 del 08-10-2026 tras los cambios de la placa (sin
  mover ninguna pieza). Los ejes de la microSD (J401) y del USB-C (J101) salen de ese `.json`.
- **Clavijas reales:** zonas de J102, J404 y J301 de `kicad/plugs.json` v0.3.
- El módulo OLED no está en el STEP: se dibuja desde sus medidas (separador de 1.3, vidrio hasta
  y 20.0).
- El 08-10-2026 se pasó además la pared del tubo cada 1.5 mm de alto (72 secciones, sin los nervios
  de dentro): ningún punto bajaba de 1.2 salvo el chaflán de la ventana de la OLED bajo el bolsillo de
  la lámina (1.19, z 86.9), y las uniones quedaban en 1.2. No se repitió: desde entonces la pared solo
  cambió en la muesca de la microSD, que mide `check_v3_0.py` (1.75: ver la tabla).

> **Corregido el 08-10-2026 (primera versión).** El tubo salía **sin la pared de la cara plana**
> en el centro, en todo el alto, y ningún choque lo mostraba. Desde entonces `export_v3_0.py` y
> `check_v3_0.py` sondean la pared y `check_v3_0.py` compara su volumen y mide su espesor.

> **Corregido el 09-10-2026.** El chaflán de fuera de la muesca ciega de la microSD empezaba en
> x 18.19 con todo el alto de la muesca y atravesaba su pared de detrás entre y 17.25 y ~18: la muesca
> no era ciega (de frente se veía el interior) y la pared quedaba en 0.64. Las sondas no lo veían
> porque van a media pared, dentro de la muesca. Lo mostró la prueba de visibilidad del marco del
> USB-C. Ahora el chaflán se queda delante del fondo plano de la muesca (x ≥ 20.51).

> **Valor conocido de la carcasa pedida (09-10-2026).** Midiendo en 3D la pared alrededor de los
> avellanados de los M2.5 radiales, la de la **base queda en 0.92** (por debajo del 1.0 local): el
> punto fino va en diagonal desde el cono del avellanado hasta el canto del rebaje de la unión de abajo
> (r 26.8, z 5.9). Las secciones horizontales en el eje del tornillo (2.24) no lo veían. La de la tapa,
> 1.27. La carcasa ya está pedida y no se cambia: `check_v3_0.py` lo mide y lo informa
> (`guarda_pared_tubo.avellanados_3d_solo_informativo`), sin contarlo como objetivo. Si se rehace la
> carcasa: subir los tornillos de la base a z 9.15 (y las lengüetas a z 11.3) y bajar los de la tapa a
> z 106.85 dejaría unos 1.23, también hundiendo 0.21 los avellanados para que las cabezas no asomen
> (cálculo con el cono a 45°, no pasado por el modelo).

| Comprobación | Resultado |
| --- | --- |
| Piezas | 10 piezas, válidas (el distintivo, 6 islas; el resto, un sólido cada una). Mallas STL cerradas, sin no-manifold ni autointersecciones; sin interferencias entre ellas, salvo el apriete de las bandas sobre el tubo, la base y la tapa, que va aparte. Triángulos: base 5122, tubo 7328, tapa 6084, chasis 1930, tecla 812, tapa de puertos 2392, distintivo 1396, marco del USB-C 544, banda de abajo 8974, banda de arriba 7702. Volúmenes en cm³: 8.98, 45.30, 10.48, 6.59, 0.09, 0.99, 0.08, 0.32, 12.52 y 13.37 |
| Pared del tubo: sondas a media pared cada 0.5 mm | Cara plana: 11 715 puntos, 1 473 en las aberturas, **0 sin material**. Anillo: 58 543 puntos, 3 425 en las aberturas, **0 sin material** |
| Pared alrededor de los avellanados de los M2.5 (3D, solo se informa) | Del avellanado (cono, sin el paso del tornillo) al hueco interior y a los rebajes de las uniones: base (z 8.5) **0.92**, en diagonal hasta el canto del rebaje de abajo (r 26.8, z 5.9); tapa (z 107) 1.27. Valor conocido de la carcasa pedida (ver abajo) |
| Pared del tubo: volumen | 45 298.6 mm³; esperado 45 298.0 (+0.001 %, tolerancia 0.5 %). Sube 0.39 cm³ porque las rayas son más cortas |
| Pared del tubo: espesor (sin nervios) | Túnel del USB-C 1.34; ventana de la OLED 1.4; tecla y LED 1.8; uniones 1.2; tornillos radiales 2.24; pared normal y rayas 1.9 (z 15, 70 y 95: en z 60 ahora está el distintivo); agujeros de las anclas 1.34; ranura y muesca ciega de la microSD 1.77 (fondo plano a 90° sobre el techo de la ranura). El túnel y la ranura no cambiaron: la diferencia de 0.01 con la pasada anterior (1.33 y 1.75) es de la discretización de las secciones, que ya no cortan rayas en esas alturas |
| Choques en posición final | 0 entre piezas (sin contar el apriete de las bandas), 0 de las piezas con las referencias y 0 entre referencias |
| Barridos (pasos de 0.5 mm) | 0 choques en los quince (lista de abajo). Las bandas, al ponerlas, se estiran 0.11 sobre las cabezas de los M2.5 (margen medido aparte, ver abajo) |
| Holgura lateral en los barridos verticales | Compradas 0.5 (el pack por su cuna); impresas 0.4 (chasis por el tubo); placa por los rieles 0.25; carrier por sus ranuras 0.3 (ajuste). La placa roza los salientes M2 a propósito (contacto) |
| Chasis armado con la tecla puesta | Bloqueado: J102 choca con el émbolo a los 10.5 mm de subida. Sin la tecla sale limpio |
| Llave fija de 8 en la tuerca de la clavija, sin la placa | Holgura al chasis 0.94 recta y 0.5 girada ±30° |
| Chasis armado (chasis, placa real, OLED, carrier, clavija, marco del USB-C) | Radio máximo 25.2: 0.4 al tubo |
| Marco del USB-C (08) | Una pieza, sin huecos cerrados, 0.32 cm³. 0.4 al tubo, 0.425 al chasis, 0.45 a la tapa de puertos, 0.5 a R412 y J401, 1.75 a la carrier; funda a 0.3 por lado en su túnel. Contactos: labio en el dorso de la placa y fondo de las ranuras en su canto (0), resorte en el techo de J101 (0.17, 0.34 mm³). Atrapado en el tubo: +X 0.45, −y 0.13, ±z 0.1, −X y +y 0. Paredes 0.8 en el dedo del resorte, 1.1 o más en el resto. Al deslizarlo por −X: 0.425 al chasis y 0.5 a los componentes |
| Qué se ve por el túnel del USB-C (tapa abierta) | De frente, 98.3 % J101, el canto de la placa bajo J101, el marco o el tubo; 1.7 % otra cosa (rendija de 0.2 sobre la cara a los lados del blindaje, rendijas de 0.1 del collar y franja de y 20.1–20.15). Hasta 30°: 97.9 % y 2.1 % (lados de la muesca de la placa 0.96 %, cara de la placa 0.95 %). Ver [Marco del USB-C](#marco-del-usb-c-08-usb-bezel). Con las bandas puestas (en la escena de rayos) sale idéntico, también por la ranura de la microSD |
| Qué se ve por la ranura de la microSD | De frente, solo J401 o la tarjeta y el tubo. Inclinado 10–30°: el canto y la cara de la placa delante de J401, U201 y el riel del chasis (11.4 % sin tarjeta, 8.7 % con ella) |
| Pack 1S2P (envolvente de 37.5 × 68 × 20) | 0.5 a la cuna por encima de las repisas, 0.5 a los topes de la tapa, 0.6 al chasis, 0.5 al retén de la tuerca, 1.8 a la carrier, 2.9 a la base; también al bajar por arriba |
| Holguras a la cara plana | Vidrio de la OLED 0.5; PCB, cinta y tornillos de la OLED 0.9; componentes 0.84; clavijas 0.75. La pestaña de la tecla va en su rebaje (contacto) |
| Tecla y guía de luz contra la placa real | Émbolo–SW401 0.5; tecla–otros componentes 1.9; guía de luz–D403 0.55 |
| Aberturas del costado | Funda del USB-C (12.35 × 6.5) a 0.3 de su túnel; tarjeta a 0.3 de su ranura al entrar y salir, y también trabada, porque queda dentro de la ranura |
| Otras holguras | Clavija acodada–placa 0.54 (el cuerpo sobre el canto; la tuerca pasa por la muesca); perno de 15.5–soldaduras de la carrier 1.2; perno–pack 3.3; tuerca del bastón–placa y carrier 0.81; cables–piezas 0.5, –pack 8.9 (sin los que van pegados), –placa y carrier 2.6 |
| Tapa de puertos (tres setas: 19°, z 20, 32.5 y 45) | Cada cabeza: 0.61 al chasis al barrerlo; en su sitio, 0.86 a la pared y 8.6 o más a lo demás. Pared entre cada agujero y las aberturas: 2.66 o más (túnel del USB-C a 2.66 de la seta de abajo). Cerrada, su cuerpo queda a 0.54 del canto de la tarjeta trabada. Abierta 135°: 1.62 a la funda del USB-C y 5.12 a la tarjeta; abierta 180°: 2.63 y 5.24. Con la banda de abajo puesta, se abre hasta 155.5° (ver Bandas) |
| Antena del WROOM (U201: x −15.15…−9.15, z 49.9–67.9) | Plástico del chasis a menos de 5 mm: 45.1 mm³, solo el saliente M2 de la OLED del lado −X, detrás de la placa (a 1.6). La pared del tubo queda a 1.69 del módulo |
| Nada de la placa por detrás de su dorso delante del SMA de la carrier (x −6…3, y < 13.8, z 60–80) | Cumple |
| Coaxial | Radio mínimo 12.27 en todo el recorrido; recorrido de 82.7; eje del cable hasta r 24.1; 0.59 a las piezas, 0.6 al pack, 4.4 a la placa y la OLED, 2.9 a la tapa |
| Mazos entre sí | Mazo del pack–arnés de J301 8.8; coaxial a 32 o más de todos |
| Bandas de TPU (09 y 10): apriete | Solape con su medida de impresión (0.3 por lado), a propósito: tubo 1605.4 y 1722.2 mm³, base 78.3, tapa 78.3. Contra todo lo demás, 0 |
| Bandas de TPU: aberturas y bolsillos | Bolsillos de los M2.5 (Ø6.4 × 0.8, fondo curvo): 1.2 de TPU por fuera de cada tornillo; cabezas a 0.7 con la banda puesta (0.39 al fondo con la medida de impresión). Tecla 1.1; guía de luz 1.5; tapa de puertos cerrada 0.5 (esquina de la muesca); sitio para la uña delante de la lengüeta 3.5; agujero del desagüe 2.65; bolsillo de la lámina de la OLED 1.0 y lámina 1.14; antena 0.85; tornillos de la antena 6.8. Nada por encima de z 116 ni por dentro del contorno de apriete junto a la cara de arriba de la tapa |
| Bandas de TPU: anillo completo de la de abajo | z 0–15.86 (15.86; pedido 12 o más), con solo los tres bolsillos de los tornillos, por dentro |
| Tapa de puertos abierta con la banda de abajo puesta | Banda estirada (como está montada): gira hasta **155.5°** antes de tocar el canto de atrás de la muesca (158.8° con la medida de impresión). En ese ángulo, 2.63 a la funda del USB-C y 5.24 a la tarjeta; a 135°, 0 mm³ con la banda y las holguras de antes (1.62 y 5.12) |
| Bandas de TPU al ponerlas | Con la carcasa cerrada y sin la tecla. Banda estirada (contorno interior = cuerpo + 0.02), barrida contra lo que sobresale del contorno del cuerpo + 0.01 (la tapa de puertos y, si estuviera, la funda del USB-C): limpias; 0.5 a la tapa de puertos al pasar. La banda estirada queda toda fuera de ese contorno (0 mm³). **Margen de estiramiento solo sobre las cabezas de los M2.5**, cuyos cantos asoman 0.11: 0.82 mm³ como máximo, medido aparte (no cuenta como choque). Con la tecla puesta la banda de abajo no pasa (19.2 mm³): la tecla va al final |
| Distintivo y rayas | Distintivo z 45.9–66.7: 5.94 a la banda de abajo y 5.86 al bolsillo de la lámina (pedido 2). Rayas z 41.5–74.5: 1.5 a cada banda (pedido 1.5) |

Los barridos (pasos de 0.5 mm; choque si el volumen común pasa de 0.05 mm³):
- pack 1S2P por arriba (94.2 mm, hasta salir del tubo) contra el tubo y la base;
- carrier al chasis por abajo (60 mm; sin los labios de los ganchos, que se apartan);
- clavija SMA acodada por arriba con la carrier en el chasis y sin la placa (25 mm; tuerca con su
  barrido de 9.2);
- llave fija de 8 por delante (30 mm) y girada ±30°;
- placa real con la OLED por los rieles, por abajo (92 mm), con la carrier y la clavija puestas;
- chasis armado por arriba (103.5 mm, hasta salir del tubo), con el arnés de J301, el pack, su mazo
  y la tapa de puertos con sus tres setas, sin la tecla;
- base por abajo (20 mm) contra todo lo de dentro, con las clavijas y los cables reales (sin la
  banda de abajo, que se saca antes);
- tapa con la antena y el pasamuros por arriba (20 mm; sin la banda de arriba, que se saca antes);
- tecla por fuera (12 mm), por la ventana de la banda de abajo;
- tarjeta microSD por el costado (15 mm, por la ranura justa), con la banda de abajo;
- tapa de puertos abriéndose hacia fuera (12 mm; las setas se quedan en sus agujeros), con el marco
  del USB-C y la banda de abajo puestos;
- **marco del USB-C por fuera, hacia −X**, sobre el receptáculo con la placa y la carrier en el chasis
  (15 mm, medido al revés: la parte rígida contra todo, J101 incluido; el resorte contra todo menos
  J101, que aprieta a propósito);
- **funda máxima del USB-C por el costado** (15 mm) con el marco puesto: tubo, marco, chasis, placa,
  carrier y banda de abajo;
- **banda de abajo por abajo** (42 mm, hasta salir) y **banda de arriba por arriba** (82.8 mm, hasta
  pasar la antena), estiradas, con la carcasa cerrada y sin la tecla (método en la tabla; las cabezas de
  los M2.5, aparte: margen de estiramiento).

El chasis armado baja con el marco del USB-C puesto.

En los barridos verticales se mide además la **holgura lateral** mínima: cada sección horizontal
de la pieza que se mueve contra las secciones del obstáculo por las que pasa (cada 0.5 mm de alto,
contornos cada 0.05 mm).

Con la envolvente de la especificación (`--envelope`), el 08-10-2026 (antes del marco): 0 choques de
la carcasa, los once barridos de entonces limpios y los mismos mínimos (impresas 0.4, rieles 0.25,
compradas 0.5); solo marcaba referencia contra referencia (las zonas de clavija reales entran en la
envolvente de componentes, que las rellena). **No se volvió a pasar con el marco:** la envolvente
llena toda la cara de la placa y el marco solo se puede comprobar con la placa real (con `--envelope`
el marco se compara solo con la PCB).

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
- **Marco del USB-C:** la fuerza y la duración del resorte (2.8 N y hasta 36 MPa son cálculos de viga,
  no medidos), si el tope sube bien por la boca de J101 y si el marco entra por −X sin forzar con la
  tolerancia real de MJF y el espesor real de la placa (ranura de 1.8). La rendija de la cara depende de
  ese espesor (0.2 con 1.6; de 0.04 a 0.36 con ±0.16). El modelo de J101 no trae soldadura por debajo de
  la placa: si las patas del blindaje asoman más de lo normal por el dorso, quedan a 0.5 del labio
  (agujeros hasta x 13.0, labio desde 13.5). Hay que imprimirlo y probarlo en la placa real.
- **Bandas de TPU:** el apriete real (0.3 por lado supone TPU de 95A impreso a su medida; el TPU de FDM
  suele salir algo grueso), que no se corran sin tope, cuánto cuesta ponerlas y quitarlas, y que pasen
  bien por encima de los cantos de las cabezas de los M2.5 (0.11) sin engancharse (el modelo usa la banda
  estirada como sólido rígido de 2.0, no calcula cómo se estira el TPU ni si la parte plana de la banda
  queda pegada a la cara plana). La tapa de puertos abierta contra la banda es un giro rígido: el TPU de
  verdad se dobla.
- **Acceso a la microSD con la uña:** según la hoja del zócalo, para soltar la tarjeta hay que
  empujarla 2.7 dentro de la ranura desde la muesca ciega (con la uña o un clip) y expulsada queda
  1.6 al descubierto. Que se tome cómodo con la uña solo se sabe probándolo impreso.
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

Pensada para **MJF (PA12 o PA11)**, como V2.3. La tecla, la tapa de puertos, el distintivo y las dos
bandas, en TPU; el distintivo y las bandas, del color que se quiera. **Probar primero un tramo de tubo y
el chasis** (ver el principio).

**Bandas de TPU (09 y 10):** en TPU de dureza 95A, supuesta (en uno más blando el apriete de 0.3 por
lado sujeta menos). En FDM, cada una **de pie sobre su canto entero, sin soportes** (en MJF con TPU la
orientación casi no importa): la de abajo sobre su canto de z 0 (la muesca queda arriba) y la de arriba
dada vuelta, sobre su canto de z 116 (la muesca de la OLED queda arriba). Así salen en `generated/stl/09-band-bottom-tpu-para-imprimir.stl` y
`10-band-top-tpu-para-imprimir.stl`, centradas en el origen. Las paredes son verticales y los bordes de
las ventanas, cortos: no necesitan soportes. Los bolsillos de los tornillos quedan de pie como agujeros
ciegos horizontales de Ø6.4 y 0.8 de hondo: salen sin soporte. El canto de la cama lleva el redondeo de
1.0 por fuera: apoya 1.0 de los 2.0 de espesor; si se despega, poner un borde (brim) de 3–5 mm. Medir el
contorno interior impreso: si sale más chico que el modelo (el TPU suele salir algo grueso), aprieta más.

**Marco del USB-C (08):** en MJF la orientación casi no importa (no lleva soportes). Si se puede
elegir, con su **eje y en vertical** (la cara de y 20.1 arriba o abajo): así el dedo del resorte
queda en el plano de las capas y se dobla a lo largo de ellas, no separándolas. No tiene huecos
cerrados. Pedirlo junto con la carcasa y probarlo en la placa real antes de dar por buena la
fuerza del resorte (ver [No verificado](#verificaciones)).

**En FDM, como plan B:**
- las repisas del pack, los apoyos del chasis, los nervios de la cuna y los topes de la tapa
  tienen voladizos planos sin chaflán: necesitan soportes, o un chaflán de 45° que habría que
  añadir;
- los redondeos R4 de la base y de la tapa quedan bien solo con esa cara contra la cama;
- los ganchos de la carrier (brazos de 0.8 × 0.6 con ranuras de 0.6), los labios de 0.8 de los
  rieles, la bisagra de 0.6 de la tapa de puertos y la membrana de 0.4 de la tecla son demasiado
  finos para FDM con boquilla de 0.4: habría que rediseñarlos;
- el grabado del distintivo tiene detalles finos: en FDM con boquilla de 0.4 sale, pero con bordes redondeados;
- el marco del USB-C, con su eje y en vertical y el suelo contra la cama, necesita soporte bajo el
  dedo del resorte, y el dedo (0.8) queda al límite para una boquilla de 0.4.

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
/Applications/FreeCAD.app/Contents/Resources/bin/python check_v3_0.py   # placa real: unos 30 minutos
# con la envolvente de la especificacion (unos 20 minutos):
/Applications/FreeCAD.app/Contents/Resources/bin/python check_v3_0.py --envelope
```

- `build_v3_0.py` genera `generated/TresVizo-V3.0.FCStd` (piezas y referencias `ref_*`) y
  `model-index.json`.
- `export_v3_0.py` genera los STL y STEP de las piezas (y los STL para imprimir del distintivo y de
  las bandas) y comprueba las mallas, las interferencias entre piezas y la pared del tubo (sondas cada
  1 mm). El apriete de las bandas sobre el tubo, la base y la tapa no cuenta como interferencia: va
  aparte, en `apriete_de_las_bandas`. Si falta pared, termina con código 1.
- `check_v3_0.py` escribe `check.json`:
  - `guarda_pared_tubo`: sondas, volumen y espesores;
  - choques en posición final y en los barridos del montaje;
  - `holguras` en posición final y `holguras_laterales_en_barridos`;
  - `objetivos`: el mínimo conseguido en cada categoría (B1–B7) y lo que queda por debajo;
  - tapa de puertos, antena del WROOM, nada detrás de la placa delante del SMA, radio del chasis
    armado y coaxial;
  - `marco_usb_c` (cuánto se mueve atrapado, espesores, una sola pieza), `marco_al_montarlo`
    (holguras al deslizarlo) y `contactos_con_apriete_a_proposito` (resorte sobre J101);
  - `visibilidad`: qué se ve desde fuera por el túnel del USB-C y por la ranura de la microSD;
  - `bandas`: apriete, aberturas y bolsillos con sus holguras y el TPU que queda sobre cada tornillo,
    anillo completo, tapa de puertos abierta con la banda puesta, barridos de las bandas (`al_ponerlas`,
    con el margen de estiramiento sobre las cabezas de los M2.5), distintivo y rayas entre las bandas;
  - `guarda_pared_tubo.avellanados_3d_solo_informativo`: pared en 3D alrededor de los avellanados de los
    M2.5 radiales (solo se informa).
