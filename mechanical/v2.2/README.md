# TresVizo V2.2 — 79 mm, panel con pantalla y botón, IMU en la tapa, hombro y bandas de TPU

Revisión de [V2.1](../v2.1/README.md) pedida por el propietario el 2 de octubre
de 2026, en dos rondas:

1. 1 cm más ancha. El cuerpo creció 2 cm y, visto el modelo, se acortó 1.
2. Panel frontal más grande, con la pantalla OLED y el botón metálico de 12 mm
   que compró, cada uno con su montaje. Sin panel auxiliar.
3. Fuera el trineo universal: el botón, la pantalla y su cableado no caben con
   él. Todo se amarra con bridas a un respaldo que forma parte del tubo, con
   huecos grandes en sus costillas, o a cuatro toalleros de las paredes.
4. El IMU va en una plataforma que se incrusta en la tapa de antena, con el
   **chip** en el eje del receptor, y con un paso amplio para el coaxial.
5. Un hombro redondeado que lleva el cuerpo hasta la antena sin escalón, y dos
   bandas de protección de TPU, arriba y abajo.

Después de la primera ronda, una revisión independiente del modelo encontró
fallos que también quedan corregidos aquí (ver [abajo](#lo-que-corrigió-la-revisión)).

**Nada de V2.2 se ha impreso ni ensayado.** La geometría es coherente en CAD y
pasa las comprobaciones automáticas; eso no es validación.

## Qué cambió frente a V2.1

| | V2.1 | V2.2 |
| --- | ---: | ---: |
| Diámetro exterior | 69 mm | **79 mm** (82.4 con las bandas) |
| Del asiento del jalón a la cara de la antena | 136.9 mm | **146.9 mm** |
| Hasta lo alto del hombro | — | 153.9 mm |
| Largo útil interior | 114 mm | **124 mm** |
| Panel frontal | 66° × 58 mm: USB-C, botón de 10.4, dos LEDs | **72° × 87 mm**: OLED 0.96" en su marco, botón de 12 mm, USB-C con repisa, dos LEDs |
| Panel auxiliar | 50° × 40 mm con USB-C | **no hay** |
| Interior | trineo atornillado a la base | **respaldo ranurado en el tubo y cuatro toalleros** |
| IMU | repisa del trineo, con los **agujeros** en el eje (chip 5.65 mm fuera) | **plataforma incrustada en la tapa**, con el **chip** en el eje |
| Bayonetas | tres dientes iguales: la tapa cerraba en tres posiciones | **un diente índice**: una sola posición |
| Transición a la antena | escalón de 79 a 43.5 | **hombro redondeado** que abraza la antena |
| Protección | — | **bandas de TPU** arriba y abajo |
| Piezas | 6 | 8 (6 rígidas y 2 de TPU) |
| Tornillos con largo definido | 13 | 16 |

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
- **Para sacarla**, con la tapa fuera del tubo: tirar con firmeza, unos 30-37 N.
  A 45° la uña no se autobloquea con rozamientos normales.
- **Una sola orientación.** Las uñas están a 35°, 145° y 320°: girada, alguna no
  encuentra su ventana.
- **Sitio para el coaxial.** Quedan 18.4 mm entre los componentes del IMU y la
  tapa, para el SMA macho acodado que conecta la antena. El coaxial y los cables
  del IMU salen por el **paso trasero**, ahora de 70° y desde r = 15 (antes 40° y
  r = 21), justo encima del canal del respaldo.

## Respaldo de amarre y toalleros

**Respaldo.** Placa vertical de 50 mm de ancho en la cara trasera del tubo (−Y),
unida a la pared por dos costillas, con un canal detrás:

- 32 ranuras cuadradas de 4.5 mm en cuatro columnas (x = ±6 y ±17) y filas cada
  10 mm, de z = 33 a 103. Admiten bridas de 2.5 a 3.6 mm en cualquier sentido.
- **Cómo se amarra:** la brida entra por una ranura, pasa por detrás de la placa
  y sale por la vecina, de la misma fila o de la misma columna, y rodea lo que se
  quiera sujetar. También puede dar la vuelta por los extremos libres de la placa,
  que quedan a 3.3 mm de la pared.
- **Costillas con huecos:** cada costilla lleva cuatro huecos hexagonales de
  7 × 14 mm. Por ahí pasan bridas y cables de una celda del canal a otra.
- El canal trasero está abierto arriba: por ahí bajan el coaxial y los cables
  del IMU desde la tapa y salen por la ranura más cercana a donde se conectan.

**Toalleros.** Cuatro barras de amarre por dentro, para componentes extra:

| Barra | Ángulo | Altura z | Separación de la pared |
| --- | ---: | ---: | --- |
| Vertical | 15° | 40-80 | 4.5 mm |
| Vertical | 165° | 40-80 | 4.5 mm |
| Horizontal, 26 mm | 0° | 99 | 4.5 mm en los postes, 7.2 en el centro |
| Horizontal, 26 mm | 180° | 99 | 4.5 mm en los postes, 7.2 en el centro |

Barra de 4 × 4. Una brida la rodea por detrás. Los postes llevan escuadra a 45°
por debajo.

**Paquete comprobado** (objetos `ref_*` del modelo): batería del peor caso
(10 × 55.5 × 68) plana contra el respaldo, de z = 24 a 92; carrier UM980 y Thing
Plus lado a lado sobre su cara delantera. Quedan **13.8 mm** hasta la parte
trasera del botón con sus cables, **14.1 mm** hasta los Dupont de la pantalla y
más de 5.9 mm hasta los toalleros.

- La batería es una bolsa blanda: apoyarla plana, con fieltro o espuma, y no
  apretar las bridas hasta marcarla. Las bridas que la rodean cargan sus cantos:
  sin apretar de más.
- La brida que rodea la esquina de la batería queda a 0.7 mm de la pared.
- Nada por debajo de z = 24 en las esquinas traseras: ahí está el collar
  inferior.

## Panel frontal

Tapa curva a ras de 72° × 87 mm, entre las dos bandas. Todo va montado en la tapa
y entra por la ventana del tubo al cerrarla.

| Elemento | Altura z | Montaje |
| --- | ---: | --- |
| USB-C | 106.2 | Hueco exterior de 12.5 × 7, del tamaño del sobremolde de un cable común. Por dentro, asiento plano para el canto de la placa: el receptáculo queda 0.4-1.4 mm bajo la cara exterior. Detrás, repisa con dos costillas; una brida rodea placa y repisa. |
| Dos LEDs | 106.2, a ±14.5 | Barrenos de 3.2, uno a cada lado del USB-C. |
| Pantalla OLED 0.96" | área activa centrada en 79 | Marco por dentro: el PCB apoya por la cara del vidrio en un plano en toda su altura; vidrio y mica en un bolsillo; cuatro M2×4 a sus agujeros. Ventana del área visible, con chaflán hacia fuera de 45° arriba y abajo, porque la pantalla se mira desde abajo, y de 20° a los lados. |
| Botón de 12 mm | 50.5 | Barreno de 12.3. Rebaje plano de 15 por fuera para la ceja y asiento plano de 20 por dentro para la tuerca: panel de 3.6 mm en el eje, 4.6 con la junta; el fabricante más restrictivo admite 6. |

- **Mica:** lámina transparente de 1 mm (acrílico o PETG) recortada a
  **26.7 × 19.3**, delante del vidrio, en el mismo bolsillo. Sella la ventana. Si
  baila, una gota de silicón.
- La pantalla queda 3.8 mm detrás de la cara exterior en el centro, con 1.3 mm de
  tapa sobre el canto del bolsillo y 1.4 sobre los pilotos.
- Los agujeros de la pantalla son de 2.0 según el plano del vendedor: el M2 entra
  justo. Si no pasa, repasar con broca de 2.2 o usar M1.6.
- La tuerca del botón queda a unos 10 mm del marco de la pantalla: apretarla con
  pinzas o una llave de 14 delgada, antes de montar la pantalla.
- **El LED del botón es de 12 V.** Con 3.3 o 5 V encenderá poco o nada.
- El tornillo de arriba de la tapa queda a 0.75 mm del cuello de la tapa de
  antena: es **M3×4** y no puede ser más largo.

## Hombro de la antena

Sexta pieza. Anillo que asienta sobre la tapa y lleva el cuerpo hasta la antena:
perfil de cuarto de elipse que sale vertical del cuerpo de 79 y llega horizontal,
7 mm más arriba, a 0.5 mm de la antena. El borde que la abraza va redondeado.

- Es pieza aparte porque impresa con la tapa (boca abajo, por su cuello) pediría
  soportes en la cara vista. Sola se imprime de pie, sin soportes.
- La antena sigue apoyando en la tapa, como antes: la posición del SMA no cambia.
- La sujetan tres **M2.5×10** desde dentro de la tapa, a r = 24.5, entre los de
  la antena.
- Entre la tapa y el hombro queda una línea en V: los dos cantos llevan chaflán.

## Bandas de TPU

Piezas 7 y 8. Dos fundas de 28 mm de alto y 2 mm de pared, para imprimir en TPU:

- **Abajo:** de z = 0 a 28. Cubre la base y el arranque del tubo.
- **Arriba:** de z = 118.9 a 146.9. Cubre el final del tubo y la tapa, hasta el
  hombro.
- Diámetro interior 0.6 menor que el cuerpo: el TPU se estira y aprieta.
- Por dentro, una ranura corrida de 8 × 1.2 a la altura de cada seguro de
  bayoneta, por si la cabeza del M3 asoma. Es corrida para que la banda entre en
  cualquier giro.
- Cantos exteriores redondeados.
- Para abrir la bayoneta hay que quitar antes la banda: aprieta las dos piezas.

## Montaje

1. **Base:** inserto del jalón (ver el pendiente de abajo).
2. **Tapa del panel:** botón con su tuerca por dentro; pantalla con la mica y
   cuatro M2×4; placa del USB-C en su asiento con una brida; LEDs; cables
   soldados con largo de sobra.
3. **Paquete:** amarrar batería, UM980, Thing Plus y demás al respaldo o a los
   toalleros, por la ventana del panel y por los extremos del tubo.
4. **Tapa de antena:** antena con tres M2.5×10 desde dentro; hombro con otros
   tres M2.5×10 desde dentro; SMA acodado; IMU en la plataforma con dos M2.5×6
   avellanados; meter la plataforma por abajo hasta el clic, con el coaxial y los
   cables por el paso trasero.
5. **Tubo sobre la base:** el diente ancho por su entrada ancha, girar en
   sentido horario visto desde arriba hasta el tope y M3×12 del seguro.
6. **Tapa sobre el tubo:** bajar los cables del IMU y el coaxial por el canal del
   respaldo, conectar por la ventana del panel, diente ancho por su entrada, girar
   en sentido horario hasta el tope (28.7°: dejar cable de sobra) y M3×12 del
   seguro.
7. **Tapa del panel:** conectar pantalla, botón, USB-C y LEDs y cerrar con dos
   M3×4.
8. **Bandas de TPU:** deslizarlas, una por abajo y otra por arriba.

La lista completa está en [SCREW-BOM.md](SCREW-BOM.md).

## Impresión

| Pieza | Material | Orientación | Soportes |
| --- | --- | --- | --- |
| `01-threaded-base` | PETG o ASA | Cara del jalón en la cama. | Los mismos que V2.1. |
| `02-logo-tube` | PETG o ASA | De pie. | **Solo dentro de la ventana del panel**: su techo es una franja curva que no se puede puentear. La tapa del panel lo cubre. El respaldo, sus costillas, el piso del canal y los toalleros se imprimen sin soporte. |
| `03-antenna-cap` | PETG o ASA | Boca abajo, con la cara de la antena en la cama. | **Bajo los tres dientes de la bayoneta**, apoyado en la placa: son su cara de carga. El refuerzo del seguro ya va unido a la placa y el canto que retiene cada uña es un puente de 6.3 mm. |
| `04-imu-platform` | PETG o ASA | Disco en la cama. | Ninguno. |
| `05-panel-cover` | PETG o ASA | De pie, sobre su canto inferior, con **brim**. | Ninguno: el techo del bolsillo de la pantalla es un puente de 27 mm y la repisa del USB-C, un puente entre sus costillas. |
| `06-antenna-shoulder` | PETG o ASA | De pie, sobre su cara plana. | Ninguno. |
| `07-bumper-bottom` y `08-bumper-top` | **TPU 95A** | De pie. | Ninguno. |

Las uñas flexionan 1.2 % al entrar: el PETG lo aguanta de sobra; el PLA también,
pero perdona menos y se ablanda al sol.

El barreno de 12.3 del botón se imprime en horizontal y puede salir algo cerrado
arriba: si el botón no entra, repasarlo con lima redonda.

## Altura del ARP: el firmware usa otra cifra

Del asiento del jalón (cara inferior de la base) a la cara de la tapa donde apoya
la antena hay **146.9 mm** en V2.2; en V2.1 eran 136.9. El firmware usa
`kCaseOffsetM = 0.10` (`firmware/esp32/include/base_plan.h:9`), una cifra
declarada y sin medir que no corresponde a ninguna de las dos. Aquí no se cambió:
se corrige cuando se imprima la carcasa y se mida la real.

## Lo que corrigió la revisión

Una revisión del modelo de la primera ronda encontró:

| Hallazgo | Corrección |
| --- | --- |
| El barreno de accesorios de 324° apuntaba a la esquina de la batería: un M4 que asomara 1.9 mm la tocaba. | Barrenos de accesorios desactivados (`accesorios.activo`). Flanqueaban el panel auxiliar, que ya no está. |
| El USB-C quedaba 2 a 3.6 mm hundido y el hueco no dejaba entrar el plástico de la clavija. | Asiento plano por dentro y hueco exterior del tamaño del sobremolde. |
| La tapa cerraba también girada 120° o 240°, con el IMU y la antena girados. | Diente índice en las dos bayonetas. |
| La uña a 30° absorbía poco error y casi se autobloqueaba. | Uña a 45°. |
| Los dos M2 de abajo de la pantalla apretaban contra el chaflán del marco. | Cara plana del marco en toda la altura del PCB. |
| La comprobación de las uñas no detectaba una ventana que faltara, y la de los pilotos repetía la fórmula del generador. | Uña por uña contra su valor de diseño; pilotos contra las distancias de las fuentes. |
| El refuerzo del seguro de la tapa quedaba en ménsula al imprimirla boca abajo. | Alma que lo une a la placa. |
| El piso del canal del respaldo arrancaba con una cornisa plana. | Rampa a 45° desde la pared. |
| Pieles de 0.75 a 0.9 mm sobre la pantalla. | Pantalla 0.5 mm más adentro y labio superior más ancho: 1.3 mm o más. |
| La mica de 27 × 19.5 no cabía con holgura. | 26.7 × 19.3. |
| El canto superior de la tapa era un escalón que, boca abajo, dejaba un voladizo visto. | Chaflán a 45°. |

## Pendientes

- **Posición del chip del IMU:** 5.65 ± 0.15 de la recta de agujeros, de
  fuentes del vendedor. Conviene medirla en la placa real (ver arriba). El
  espesor del PCB tampoco está publicado: se supone 1.6.
- **Placa del USB-C:** sin referencia confirmada. Si su receptáculo no queda a
  3.2 mm sobre la cara inferior de la placa, se cambia
  `panel.usb_c.eje_sobre_cara_inferior_placa`.
- **Inserto del jalón:** viene de V2 y **no se tocó**. La brida (Ø36.5) no pasa
  por ninguna de las dos aberturas de su alojamiento (Ø18). Salida posible sin
  cambiar la geometría: pausar la impresión de la base en la capa de z = 11.9,
  la cara superior del alojamiento de la brida, meter el inserto con sus
  agujeros en los tres pilotos y seguir. No se ha ensayado.
- **La opción del domo** ([option-oem-dome](../option-oem-dome/README.md)) es
  para V2.1 (Ø69) y no está adaptada a V2.2.

## Piezas

| Archivo | Qué es |
| --- | --- |
| `01-threaded-base.stl` | Base: inserto 5/8" y bayoneta con diente índice. |
| `02-logo-tube.stl` | Tubo: logo grabado, respaldo de amarre, toalleros, panel frontal, líneas de diseño. |
| `03-antenna-cap.stl` | Tapa: cuello con las tres ventanas de la plataforma y bayoneta con diente índice. |
| `04-imu-platform.stl` | Plataforma del IMU: disco, falda, tres uñas, separadores con piloto, apoyos y cruz grabada. |
| `05-panel-cover.stl` | Panel principal: pantalla, botón de 12 mm, USB-C y dos LEDs. |
| `06-antenna-shoulder.stl` | Hombro redondeado entre el cuerpo y la antena. |
| `07-bumper-bottom.stl` | Banda de TPU de abajo. |
| `08-bumper-top.stl` | Banda de TPU de arriba. |

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
5. Ejecuta `capacity_check.py`: paquete contra el respaldo, huecos de ranuras y
   costillas, toalleros, entrada de la tapa del panel con todo montado en 35 mm
   de recorrido, pieles sobre la pantalla, botón, pilotos del IMU, sitio para el
   SMA, uñas una por una, bayonetas indexadas, seguros, tornillos del panel,
   bandas y hombro.

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
- La antena sigue siendo la HA-901A atornillada por fuera.
