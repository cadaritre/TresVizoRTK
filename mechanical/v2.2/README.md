# TresVizo V2.2 — Ø64 × 130, panel con pantalla y botón, IMU en la tapa, bandas de TPU

Revisión de V2.1 pedida por el propietario el 2 de octubre de 2026:

1. **Diámetro máximo 64 mm** (sin contar las bandas de TPU) y altura de unos
   130 mm. La batería es una **18650**: no hace falta el ancho que pedía la
   955565 de V2.1.
2. Panel frontal con la pantalla OLED y el botón metálico de 12 mm que compró,
   cada uno con su montaje, más el conector de carga y los dos LEDs. Sin panel
   auxiliar.
3. Fuera el trineo universal. Todo se amarra con bridas a un respaldo que forma
   parte del tubo, con huecos grandes en sus costillas, o a cuatro toalleros.
4. El IMU va en una plataforma que se incrusta en la tapa de antena, con el
   **chip** en el eje del receptor, y con un paso amplio para el coaxial.
5. Tapa plana, como V2.1, y dos bandas de protección de TPU, arriba y abajo.

El 4 de octubre pidió dos cambios más: la rosca del jalón con una tuerca que se
compra hecha ([Tuerca del jalón](#tuerca-del-jalón)) y, en el panel, un JST-XH
de 2 pines en lugar del USB-C, para simplificar la carga.

El primer borrador de V2.2 medía Ø79 (commit `5d196e6`). El propietario fijó
después Ø64 como máximo. Entre medias, una revisión independiente del modelo
encontró fallos que quedan corregidos (ver [abajo](#lo-que-corrigió-la-revisión)).

V2.1, V2 y la opción del domo se quitaron del repositorio el 4 de octubre.
Siguen en el historial de git: la última vez que están completas es el commit
`94f00f9`.

**Nada de V2.2 se ha impreso ni ensayado.** La geometría es coherente en CAD y
pasa las comprobaciones automáticas; eso no es validación.

## Qué cambió frente a V2.1

| | V2.1 | V2.2 |
| --- | ---: | ---: |
| Diámetro exterior | 69 mm | **64 mm** (67.4 con las bandas) |
| Del asiento del jalón a la cara de la antena | 136.9 mm | **129.9 mm** |
| Largo útil interior | 114 mm | **107 mm** |
| Batería | LiPo 955565 en el trineo | **18650 detrás del respaldo** |
| Panel frontal | 66° × 58 mm: USB-C, botón de 10.4, dos LEDs | **86° × 83 mm**: OLED 0.96" en su marco, botón de 12 mm, JST-XH de carga a ras, dos LEDs |
| Panel auxiliar | 50° × 40 mm con USB-C | **no hay** |
| Rosca del jalón | inserto de McMaster con brida | **tuerca hexagonal 5/8"-11 de latón**, por dentro de la base |
| Interior | trineo atornillado a la base | **respaldo ranurado en el tubo y cuatro toalleros** |
| IMU | repisa del trineo, con los **agujeros** en el eje (chip 5.65 mm fuera) | **plataforma incrustada en la tapa**, con el **chip** en el eje |
| Bayonetas | tres dientes iguales: la tapa cerraba en tres posiciones | **un diente índice**: una sola posición |
| Protección | — | **bandas de TPU** arriba y abajo |
| Piezas | 6 | 7 (5 rígidas y 2 de TPU) |
| Tornillos con largo definido | 13 | 15 |
| Material rígido | 187 cm³ | 156 cm³ |

## Tuerca del jalón

La rosca del jalón es una **tuerca hexagonal 5/8"-11 UNC de latón**, estándar:
15/16" entre caras y 35/64" de alto. Sustituye al inserto de McMaster que venía
de V2, que solo entraba pausando la impresión.

- Entra **por dentro** de la base, con el tubo quitado, en un alojamiento
  hexagonal de 24.1 mm entre caras que no la deja girar.
- Apoya en un **anillo de 2 mm**. La cara de abajo de ese anillo es el asiento
  contra el bastón: se imprime sobre la cama, plana y a escuadra con el eje. Al
  apretar, el perno jala la tuerca contra el anillo y el anillo contra el hombro
  del bastón: todo trabaja a compresión.
- El perno cruza el anillo con 0.36 mm de holgura por lado, por una entrada a
  45°, y no rosca en el plástico.
- Por arriba la detienen **dos M3×8 con arandela ancha DIN 9021** (9 mm),
  frente a dos caras del hexágono. Cada arandela pisa 1.4 mm de tuerca y deja
  2.6 mm al perno. Solo trabajan mientras entra el perno o con el equipo suelto.
- Se imprime sin pausa, y si se daña la rosca se cambia la tuerca.
- La altura no cambia: la cara de arriba de la base sigue en z = 15.9 y el ARP
  en 129.9 mm.
- En un mismo bastón el receptor queda siempre en el mismo ángulo; en otro
  bastón, en otro. El frente es el panel: se gira el bastón para tenerlo
  enfrente, como pide Emlid con su Reach RS3.

**Qué tuerca comprar:** hexagonal estándar de 5/8"-11 UNC de latón (en ferretería,
"5/8 NC" o "rosca estándar", 11 hilos). No sirven la pesada (1-1/16" entre
caras), la de rosca fina 5/8"-18 ni las de seguridad con nylon. Una que se
encontró el 04-10-2026:
[Los Tornillos, "TUERCA HEXAGONAL NC ESTANDAR 5/8 LATÓN"](https://lostornillos.mx/products/tuerca-hexagonal-nc-laton-5-8-11),
51.79 MXN. Al recibirla, medirla: hasta 24.0 entre caras y 13.9 de alto entra
tal cual. Si no, se cambia `tuerca_jalon` en `parameters.json` y se regenera.

## El IMU: qué estaba mal en V2.1 y cómo queda

En el BMI088V1.0 los dos agujeros están en el borde largo **opuesto** a los
pines, y el chip queda **5.65 mm** hacia los pines. V2.1 ponía en el eje la línea
que une los agujeros (x = ±9.25, y = 0): el sensor acababa 5.65 mm fuera del eje,
y su ajuste de ±1.5 mm no alcanzaba para corregirlo. Además lo sujetaba con M2 en
ranuras, con tuerca y arandela.

Posición del chip en la placa, cruzando el plano del vendedor, un render del
programa de diseño del PCB (KAIHCHIP, AliExpress 1005009869623539) y dos fotos:

| Cota | Valor |
| --- | --- |
| Centro del chip a la recta de los agujeros, hacia los pines | **5.65 ± 0.15** |
| Corrimiento a lo largo de esa recta, lejos del selector IIC/SPI | **0.25 ± 0.15**: 9.0 del agujero lejano y 9.5 del de junto al selector |
| Agujeros | Ø3.0, a 18.5 entre centros |
| Hilera de pines | a 14.0 de la recta de los agujeros |
| Contorno | el plano dice 23.5 × 18; el render y las fotos, **23.1 × 17.4-17.7** |

Como el contorno no es fiable y la relación chip-agujeros sí, V2.2 coloca la
placa **por sus agujeros**:

- Los pilotos están en **x = −9.0 y +9.5, y = +5.65**: ahí tienen que caer los
  agujeros para que el centro del chip quede en X = 0, Y = 0.
- Se sujeta con dos **M2.5×6 de cabeza avellanada**. El cono de la cabeza
  asienta en el canto del agujero de 3.0 y centra la placa sobre el piloto. Con
  cabeza cilíndrica quedarían 0.25 mm de juego por lado.
- Alrededor no hay topes: queda sitio para la mayor de las dos placas, con la
  palanca del selector.
- Orientación: cara de componentes arriba, agujeros al frente (+Y), pines atrás,
  selector a +X. Los ejes serigrafiados (+X hacia el selector, +Y hacia los
  agujeros, +Z fuera de la cara de componentes) coinciden con los del equipo.
  Como la plataforma y la tapa solo entran en una posición, no pueden quedar
  girados.
- La cruz grabada en la plataforma, fuera de la placa, y la flecha al frente
  permiten comprobar el centrado con una regla con todo montado.

Error esperado del chip respecto del eje: ±0.15 de la posición del chip en la
placa más lo que se desvíe la impresión de los pilotos, unos ±0.1. Para
confirmarlo antes de imprimir, medir con vernier en la placa real la distancia del
centro del chip a la recta de los agujeros: si no da 5.65, se cambia
`imu.chip.desde_linea_agujeros` y se regenera.

## Plataforma del IMU

Cuarta pieza. Disco con falda que entra por abajo en el cuello de la tapa.

- **Centrado y altura.** La falda entra en el taladro del cuello con 0.2 mm de
  holgura por lado y su borde superior asienta contra la cara inferior de la
  tapa: la plataforma queda concéntrica con la antena y paralela a ella, porque
  las dos van en la misma pieza.
- **Retención.** Tres uñas en lengüetas de 12 × 6 × 1.6 entran en tres ventanas
  del cuello. La cara de retención va a 45° y la ventana se coloca de modo que la
  lengüeta quede todavía doblada 0.3 mm: ese resto empuja la plataforma contra la
  tapa y le quita el juego. Absorbe de −0.30 a +0.40 mm de error en la altura de
  la ventana. La flexión al entrar es del 1.2 %.
- **Para sacarla**, con la tapa fuera del tubo: tirar con firmeza. A 45° la uña no
  se autobloquea con rozamientos normales.
- **Una sola orientación.** Las uñas están a 35°, 145° y 320°: girada, alguna no
  encuentra su ventana.
- **Sitio para el coaxial.** Quedan 17.4 mm entre los componentes del IMU y la
  tapa, para el SMA macho acodado que conecta la antena (15 mm más margen). El
  coaxial y los cables del IMU salen por el **paso trasero**, de 70° y desde
  r = 15, justo encima del canal del respaldo.
- Separadores de 1.5 mm: el dorso de la placa no lleva componentes.

## Respaldo de amarre, 18650 y toalleros

**Respaldo.** Placa vertical de 49 mm de ancho casi en el centro del tubo (su cara
de apoyo en y = −7.5), unida a la pared trasera por dos costillas:

- **Delante**, el carrier UM980 y la Thing Plus, lado a lado.
- **Detrás**, en el canal entre las costillas, la **18650**. Queda a 0.6 mm de la
  pared y a 1.45 de cada costilla. Sin portapilas, que no cabe: la celda con su
  funda termoencogible, sobre una tira de fieltro o espuma.
- 24 ranuras cuadradas de 4.5 mm en cuatro columnas (x = ±5 y ±18.5) y filas cada
  10 mm, de z = 33 a 83. Admiten bridas de 2.5 a 3.6 mm en cualquier sentido.
  Una brida que entra por la ranura de −5 y sale por la de +5 rodea la 18650 por
  detrás de la placa.
- **Costillas con huecos:** cada costilla lleva tres huecos hexagonales de
  10 × 16 mm. Por ahí pasan bridas y cables de una celda del canal a otra.
- El canal está abierto abajo y arriba: por arriba bajan el coaxial y los cables
  del IMU desde la tapa.
- Los extremos libres de la placa quedan a 3.2 mm de la pared: una brida puede
  dar la vuelta por detrás.

**Toalleros.** Cuatro barras de amarre por dentro, para componentes extra:

| Barra | Ángulo | Altura z | Separación de la pared |
| --- | ---: | ---: | --- |
| Vertical | 30° | 40-80 | 4.5 mm |
| Vertical | 150° | 40-80 | 4.5 mm |
| Horizontal, 14 mm | 10° | 92 | 4.5 mm en los postes |
| Horizontal, 14 mm | 170° | 92 | 4.5 mm en los postes |

Barra de 4 × 4. Una brida la rodea por detrás. Los postes llevan escuadra a 45°
por debajo.

**Paquete comprobado** (objetos `ref_*` del modelo): 18650 del peor caso
(Ø18.6 × 69) detrás del respaldo, de z = 22 a 91; carrier UM980 y Thing Plus
delante, desde z = 22. Quedan **2.1 mm** entre el botón con sus cables y el UM980,
**11.7 mm** entre la pantalla con sus cables y las placas, y más de 5.2 mm hasta
los toalleros. Nada por debajo de z = 22: ahí está el collar inferior.

## Panel frontal

Tapa curva a ras de 86° × 83 mm. Todo va montado en la tapa y entra por la
ventana del tubo al cerrarla. Sus rebordes de arriba y de abajo, con sus dos
tornillos, quedan bajo las bandas de TPU.

| Elemento | Altura z | Montaje |
| --- | ---: | --- |
| Conector de carga JST-XH, 2 pines | 93.5 | Header vertical B2B-XH-A (7.4 × 5.75 × 7.0) en un bolsillo de 7.7 × 6.05, con la cara 0.25 mm bajo la superficie. Entra por fuera, cables primero, hasta el fondo; la ranura del fondo deja pasar las patas con los cables soldados y su termofit. Una gota de epóxico por dentro lo retiene al desconectar. |
| Dos LEDs | 93.5, a ±13.5 | Barrenos de 3.2, uno a cada lado del JST. |
| Pantalla OLED 0.96" | área activa centrada en 71.5 | Marco por dentro: el PCB apoya por la cara del vidrio en un plano en toda su altura; vidrio y mica en un bolsillo; cuatro M2×4 a sus agujeros. Ventana del área visible, con chaflán hacia fuera de 45° arriba y abajo, porque la pantalla se mira desde abajo, y de 20° a los lados. |
| Botón de 12 mm | 43.5 | Barreno de 12.3. Rebaje plano de 15 por fuera para la ceja y asiento plano de 18 por dentro para la tuerca: panel de 3.4 mm en el eje, 4.4 con la junta; el fabricante más restrictivo admite 6. |

- **Cables de la pantalla soldados.** A 64 mm de diámetro no caben los conectores
  Dupont detrás de la pantalla: los cuatro cables se sueldan a los pines o a los
  pads.
- **Mica:** lámina transparente de 1 mm (acrílico o PETG) recortada a
  **26.7 × 19.3**, delante del vidrio, en el mismo bolsillo. Sella la ventana. Si
  baila, una gota de silicón.
- La pantalla queda 4.5 mm detrás de la cara exterior en el centro, con 1.3 mm de
  tapa sobre el canto del bolsillo y 1.45 sobre los pilotos.
- Los agujeros de la pantalla son de 2.0 según el plano del vendedor: el M2 entra
  justo. Si no pasa, repasar con broca de 2.2 o usar M1.6.
- La tuerca del botón queda pegada al marco de la pantalla: apretarla con pinzas o
  una llave de 14 delgada, antes de montar la pantalla.
- **El LED del botón es de 12 V.** Con 3.3 o 5 V encenderá poco o nada.
- El tornillo de arriba de la tapa queda a 0.75 mm del cuello de la tapa de
  antena: es **M3×4** y no puede ser más largo.
- **El JST y los LEDs bajaron de 96 a 93.5.** El bolsillo del header sale 8 mm
  hacia dentro y tiene que pasar por la ventana del tubo, cuyo borde de arriba
  está en 98.4: queda 0.67 mm por debajo. Su cara de abajo va a 45° para
  imprimirse sin soporte.
- JST vende el XH como conector de placa, no como puerto para conectar y
  desconectar a diario: si se afloja, se cambia el header.
- El cambio es solo mecánico. Qué cargador entra por el JST y su polaridad los
  define la electrónica.

## Bandas de TPU

Piezas 6 y 7. Dos fundas de 2 mm de pared, para imprimir en TPU. Cada una tapa
entera la cabeza de los tornillos que tiene debajo: el seguro de bayoneta y un
tornillo de la tapa del panel.

- **Abajo:** de z = 0 a 34.5. Cubre la base, el arranque del tubo y el tornillo de
  abajo de la tapa del panel; su canto queda a 1.5 mm del botón.
- **Arriba:** de z = 97.4 a 129.9 (32.5 de alto). Cubre el final del tubo, la tapa y
  el tornillo de arriba de la tapa del panel; su canto queda a 0.9 mm del hueco
  del JST.
- Diámetro interior 0.6 menor que el cuerpo: el TPU se estira y aprieta. Por
  fuera miden 67.4.
- Por dentro, una **caja redonda en cada tornillo**, 2 mm mayor que su cabeza (Ø8)
  y 1.2 de fondo, por si la cabeza asoma. Entre la caja y el canto de la banda
  quedan 1.5 mm.
- Como las cajas no son corridas, la banda entra en una sola posición: una
  **muesca** de 1.2 × 1 en su canto libre va sobre el centro del panel.
- Se imprimen sin soporte: el techo de cada caja vuela 1.2 mm.
- Cantos exteriores redondeados.
- Para abrir la bayoneta o quitar la tapa del panel hay que quitar antes la banda.

## Detalles de acabado

- Tapa plana, como V2.1, con chaflán a 45° en su canto y una ranura fina de Ø48
  alrededor de la antena que enmarca su base.
- Chaflán de 0.5 en el canto exterior de la tapa del panel: la junta con el tubo
  queda como una línea en V y no como una rendija.
- Logo grabado de 32 mm en la espalda, opuesto al panel.
- Las líneas verticales de diseño y la ventana de la pantalla con su chaflán se
  conservan.

## Montaje

1. **Base:** meter la tuerca de latón por dentro hasta el anillo y poner los dos
   M3×8 con su arandela ancha.
2. **Tapa del panel:** botón con su tuerca por dentro; pantalla con la mica, sus
   cables soldados y cuatro M2×4; header JST con los cables soldados a sus patas
   y termofit, metido por fuera, cables primero, hasta el fondo, y una gota de
   epóxico por dentro; LEDs; cables con largo de sobra.
3. **Paquete:** 18650 detrás del respaldo, por el extremo de abajo del tubo, con
   una brida por las ranuras de ±5; UM980 y Thing Plus delante, por la ventana
   del panel y por los extremos del tubo.
4. **Tapa de antena:** antena con tres M2.5×10 desde dentro; SMA acodado; IMU en
   la plataforma con dos M2.5×6 avellanados; meter la plataforma por abajo hasta
   el clic, con el coaxial y los cables por el paso trasero.
5. **Tubo sobre la base:** el diente ancho por su entrada ancha, girar en
   sentido horario visto desde arriba hasta el tope y M3×10 del seguro.
6. **Tapa sobre el tubo:** bajar los cables del IMU y el coaxial por el canal del
   respaldo, conectar por la ventana del panel, diente ancho por su entrada, girar
   en sentido horario hasta el tope (28.7°: dejar cable de sobra) y M3×12 del
   seguro.
7. **Tapa del panel:** conectar pantalla, botón, JST y LEDs y cerrar con dos
   M3×4.
8. **Bandas de TPU:** deslizarlas, una por abajo y otra por arriba, con la muesca
   sobre el centro del panel.

La lista completa está en [SCREW-BOM.md](SCREW-BOM.md).

## Impresión

| Pieza | Material | Orientación | Soportes |
| --- | --- | --- | --- |
| `01-threaded-base` | PETG o ASA | Cara del jalón en la cama. | Los mismos que V2.1. Sin pausa: el alojamiento de la tuerca queda abierto por arriba. |
| `02-logo-tube` | PETG o ASA | De pie. | **Solo dentro de la ventana del panel**: su techo es una franja curva que no se puede puentear. La tapa del panel lo cubre. El respaldo, sus costillas y los toalleros se imprimen sin soporte; el canto inferior de la placa del respaldo es un puente de unos 22 mm. |
| `03-antenna-cap` | PETG o ASA | Boca abajo, con la cara de la antena en la cama. | **Bajo los tres dientes de la bayoneta**, apoyado en la placa: son su cara de carga. El refuerzo del seguro va unido a la placa y el canto que retiene cada uña es un puente de 6.3 mm. |
| `04-imu-platform` | PETG o ASA | Disco en la cama. | Ninguno. |
| `05-panel-cover` | PETG o ASA | De pie, sobre su canto inferior, con **brim**. | Ninguno: el techo del bolsillo de la pantalla es un puente de 27 mm; el del bolsillo del JST, uno de 7.7, y su cara de abajo va a 45°. |
| `06-bumper-bottom` y `07-bumper-top` | **TPU 95A** | De pie. | Ninguno. |

Las uñas flexionan 1.2 % al entrar: el PETG lo aguanta de sobra; el PLA también,
pero perdona menos y se ablanda al sol.

El barreno de 12.3 del botón se imprime en horizontal y puede salir algo cerrado
arriba: si el botón no entra, repasarlo con lima redonda.

## Altura del ARP: el firmware usa otra cifra

Del asiento del jalón (cara inferior de la base) a la cara de la tapa donde apoya
la antena hay **129.9 mm** en V2.2; en V2.1 eran 136.9. El firmware usa
`kCaseOffsetM = 0.10` (`firmware/esp32/include/base_plan.h:9`), una cifra
declarada y sin medir que no corresponde a ninguna de las dos. Aquí no se cambió:
se corrige cuando se imprima la carcasa y se mida la real.

## Lo que corrigió la revisión

Una revisión del modelo del primer borrador encontró:

| Hallazgo | Corrección |
| --- | --- |
| El barreno de accesorios de 324° apuntaba a la esquina de la batería. | Barrenos de accesorios desactivados (`accesorios.activo`). Flanqueaban el panel auxiliar, que ya no está. |
| El USB-C quedaba 2 a 3.6 mm hundido y el hueco no dejaba entrar el plástico de la clavija. | Asiento plano por dentro y hueco exterior del tamaño del sobremolde. El 04-10-2026 el USB-C se cambió por el JST-XH. |
| La tapa cerraba también girada 120° o 240°, con el IMU y la antena girados. | Diente índice en las dos bayonetas. |
| La uña a 30° absorbía poco error y casi se autobloqueaba. | Uña a 45°. |
| Los dos M2 de abajo de la pantalla apretaban contra el chaflán del marco. | Cara plana del marco en toda la altura del PCB. |
| La comprobación de las uñas no detectaba una ventana que faltara, y la de los pilotos repetía la fórmula del generador. | Uña por uña contra su valor de diseño; pilotos contra las distancias de las fuentes. |
| El refuerzo del seguro de la tapa quedaba en ménsula al imprimirla boca abajo. | Alma que lo une a la placa. |
| Pieles de 0.75 a 0.9 mm sobre la pantalla. | Pantalla más adentro y labio superior más ancho: 1.3 mm o más. |
| La mica de 27 × 19.5 no cabía con holgura. | 26.7 × 19.3. |
| El canto superior de la tapa era un escalón que, boca abajo, dejaba un voladizo visto. | Chaflán a 45°. |

Al pasar a Ø64 apareció otro: el piloto del seguro de la base llegaba sobre el
alojamiento de la brida del inserto y dejaba 0.2 mm de pared. Se acortó y lleva
un M3×10. Con la tuerca en lugar del inserto, quedan 6.8 mm hasta su
alojamiento.

## Pendientes

- **Posición del chip del IMU:** 5.65 ± 0.15 de la recta de agujeros, de
  fuentes del vendedor. Conviene medirla en la placa real (ver arriba). El
  espesor del PCB tampoco está publicado: se supone 1.6.
- **18650:** el modelo usa el peor caso con protección (69 mm). Medir la real.
- **Tuerca del jalón:** el alojamiento sale de la norma ASME B18.2.2. Medir la
  tuerca comprada antes de imprimir la base (ver [arriba](#tuerca-del-jalón)).
- **Header JST-XH:** las medidas son del plano de JST. Un clon puede variar:
  medirlo antes de imprimir la tapa del panel y, si hace falta, cambiar
  `panel.jst_xh`. Si la clavija no entra completa, `hundido` negativo saca el
  header.

## Piezas

| Archivo | Qué es |
| --- | --- |
| `01-threaded-base.stl` | Base: alojamiento hexagonal de la tuerca 5/8" de latón, anillo de asiento y bayoneta con diente índice. |
| `02-logo-tube.stl` | Tubo: logo grabado, respaldo de amarre, toalleros, panel frontal, líneas de diseño. |
| `03-antenna-cap.stl` | Tapa plana: cuello con las tres ventanas de la plataforma, bayoneta con diente índice y ranura alrededor de la antena. |
| `04-imu-platform.stl` | Plataforma del IMU: disco, falda, tres uñas, separadores con piloto, apoyos y cruz grabada. |
| `05-panel-cover.stl` | Panel principal: pantalla, botón de 12 mm, conector de carga JST-XH y dos LEDs. |
| `06-bumper-bottom.stl` | Banda de TPU de abajo. |
| `07-bumper-top.stl` | Banda de TPU de arriba. |

## Regenerar

```sh
python3 mechanical/v2.2/regenerate.py
```

Localiza FreeCAD y funciona también en macOS. Hace, en este orden:

1. Reparte el exterior y coloca el logo (`layout_check.py`).
2. Elige la tornillería (`bom.py`).
3. Construye y exporta las piezas, y dibuja los componentes de referencia.
4. Comprueba sólidos, mallas cerradas e interferencias de hasta 1 mm³ (las
   bandas de TPU, que aprietan por diseño, no cuentan).
5. Ejecuta `capacity_check.py`: paquete y 18650 en el respaldo, huecos de
   ranuras y costillas, toalleros, entrada de la tapa del panel con todo montado
   en 35 mm de recorrido, pieles sobre la pantalla, botón, pilotos del IMU, sitio
   para el SMA, uñas una por una, bayonetas indexadas, seguros, tuerca del
   jalón con sus retenes, tornillos del panel, tornillos bajo las bandas y
   bolsillo del JST.

Si algo falla, sale con código distinto de cero. Los resultados quedan en
[`generated/capacity.json`](generated/capacity.json).

Para verlo con colores, abrir `view_v2_2.py` desde FreeCAD. Los objetos `ref_*`
son los componentes comprados en su sitio: no se imprimen.

## Límites

- **Sin imprimir ni ensayar.** Sin datos de resistencia, ajuste, temperatura ni
  estanqueidad.
- Las holguras (0.2 en la falda de la plataforma, 0.3 en las ventanas de las
  uñas, 0.35 en la bayoneta) suponen una impresora que saca las cotas a ±0.1.
- El apriete de las bandas (0.6 en diámetro) depende del TPU y de la impresora.
- El interior va justo: entre el botón con sus cables y el UM980 quedan 2.1 mm, y
  la 18650 queda a 0.6 de la pared.
- La antena sigue siendo la HA-901A atornillada por fuera.
