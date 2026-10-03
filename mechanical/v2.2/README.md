# TresVizo V2.2 — 79 mm, panel con pantalla y botón, sin trineo, IMU en la tapa

Revisión de [V2.1](../v2.1/README.md) pedida por el propietario el 2 de octubre
de 2026:

1. 1 cm más ancha y 2 cm más de cuerpo.
2. Panel frontal más grande, con la pantalla OLED y el botón metálico de 12 mm
   que compró, cada uno con su montaje.
3. Fuera el trineo universal: el botón, la pantalla y su cableado no caben con
   él. Todo se amarra con bridas a un respaldo que forma parte del tubo.
4. El IMU va en una plataforma que se incrusta en la tapa de antena, con el
   **chip** en el eje del receptor.

**Nada de V2.2 se ha impreso ni ensayado.** La geometría es coherente en CAD y
pasa las comprobaciones automáticas; eso no es validación.

## Qué cambió frente a V2.1

| | V2.1 | V2.2 |
| --- | ---: | ---: |
| Diámetro exterior | 69 mm | **79 mm** |
| Altura total, del asiento del jalón a la cara de la antena | 136.9 mm | **156.9 mm** |
| Largo útil interior | 114 mm | **134 mm** |
| Panel frontal | 66° × 58 mm: USB-C, botón de 10.4, dos LEDs | **72° × 96 mm**: OLED 0.96" en su marco, botón de 12 mm, USB-C con repisa, dos LEDs |
| Interior | trineo atornillado a la base | **respaldo ranurado, parte del tubo** |
| IMU | repisa del trineo, con los **agujeros** en el eje | **plataforma incrustada en la tapa**, con el **chip** en el eje |
| Tornillos del IMU | M2 con tuerca y arandela en ranuras de ±1.5 | **M2.5 avellanados en piloto**: el cono centra la placa en sus agujeros |
| Tornillos con largo definido | 13 | 15 |
| Material | 187 cm³ | 241 cm³ |

## El IMU: qué estaba mal en V2.1 y cómo queda

En el BMI088V1.0 los dos agujeros están en el borde largo **opuesto** a los
pines y el chip queda **5.65 mm** hacia los pines. V2.1 ponía en el eje la línea
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
  agujeros, +Z fuera de la cara de componentes) coinciden con los del equipo, y
  los cables bajan por detrás, al canal del respaldo.
- La cruz grabada en la plataforma, fuera de la placa, y la flecha al frente
  permiten comprobar el centrado con una regla con todo montado.

Error esperado del chip respecto del eje: ±0.15 de la posición del chip en la
placa más lo que se desvíe la impresión de los pilotos, unos ±0.1. Para
confirmarlo antes de imprimir, medir con vernier en la placa real la distancia del
centro del chip a la recta de los agujeros: si no da 5.65, se cambia
`imu.chip.desde_linea_agujeros` y se regenera.

## Plataforma del IMU

Cuarta pieza. Disco con falda que entra por abajo en el cuello de la tapa.

- **Centrado y altura.** La falda entra en el taladro del cuello con 0.15 mm de
  holgura y su borde superior asienta contra la cara inferior de la tapa: la
  plataforma queda concéntrica con la antena y paralela a ella, porque las dos
  van en la misma pieza.
- **Retención.** Tres uñas en lengüetas de 12 × 6 × 1.6 entran en tres ventanas
  del cuello. La cara de retención va a 30° y la ventana se coloca de modo que la
  lengüeta quede todavía doblada 0.3 mm: ese resto empuja la plataforma contra la
  tapa y le quita el juego aunque la impresión se desvíe ±0.2 mm. La flexión al
  entrar es del 1.25 %.
- **Una sola orientación.** Las uñas están a 35°, 145° y 320°: girada, alguna no
  encuentra su ventana. Así los ejes del IMU no pueden quedar girados respecto del
  equipo.
- **Sitio para el coaxial.** Quedan 18.4 mm entre los componentes del IMU y la
  tapa, para el SMA macho acodado que conecta la antena. El coaxial y los cables
  del IMU salen por el paso trasero de la plataforma, justo encima del canal del
  respaldo.
- **Para sacarla**, con la tapa fuera del tubo: apretar las tres uñas por sus
  ventanas desde fuera del cuello y tirar.

## Respaldo de amarre

Sustituye al trineo. Es una placa vertical de 44 mm de ancho en la cara trasera
del tubo (−Y), unida a la pared por dos costillas, con un canal detrás:

- 36 ranuras cuadradas de 4.5 mm en cuatro columnas (x = ±6 y ±17) y filas cada
  10 mm, de z = 33 a 113. Admiten bridas de 2.5 a 3.6 mm en cualquier sentido.
- **Cómo se amarra:** la brida entra por una ranura, pasa por detrás de la placa
  y sale por la vecina (de la misma fila o de la misma columna), y rodea lo que se
  quiera sujetar. Las de x = ±6 comparten canal; las de ±17 también admiten la
  vuelta por el extremo libre de la placa.
- Al ser parte del tubo, no se dobla ni se descentra, y el frente queda libre
  para el botón, la pantalla y sus cables.
- El acceso es por la ventana del panel principal, abierta mientras no se pone
  su tapa, y por los dos extremos del tubo.
- El canal trasero está abierto arriba: por ahí bajan el coaxial y los cables
  del IMU desde la tapa y salen por la ranura más cercana a donde se conectan.

Disposición comprobada (objetos `ref_*` del modelo): batería del peor caso
(10 × 55.5 × 68) plana contra el respaldo; carrier UM980 y Thing Plus lado a lado
sobre la cara delantera de la batería. El paquete llega a y = −0.5 y deja
**13.8 mm** hasta la parte trasera del botón con sus cables y **17.5 mm** hasta los
Dupont de la pantalla. Por encima del paquete quedan unos 30 mm de respaldo libres
para el Soft Power Switch y lo que haga falta.

- La batería es una bolsa blanda: apoyarla plana, con fieltro o espuma si se
  quiere, y no apretar las bridas hasta marcarla.
- La brida que rodea la esquina de la batería queda a 0.7 mm de la pared.
- Nada por debajo de z = 24 en las esquinas traseras: ahí está el collar
  inferior.

## Panel frontal

Tapa curva a ras de 72° × 96 mm. Todo va montado en la tapa y entra por la
ventana del tubo al cerrarla (lo comprueba `capacity_check.py`).

| Elemento | Altura z | Montaje |
| --- | ---: | --- |
| USB-C | 114 | Hueco obround de 9.6 × 4.0. Detrás, repisa con dos costillas: la placa del receptáculo entra entre ellas y una brida rodea placa y repisa. |
| Dos LEDs | 114, a ±14.5 | Barrenos de 3.2, uno a cada lado del USB-C. |
| Pantalla OLED 0.96" | área activa centrada en 85 | Marco por dentro: el PCB apoya por la cara del vidrio en un plano; vidrio y mica en un bolsillo; cuatro M2×4 a sus agujeros. Ventana del área visible más 0.25 por lado, con chaflán hacia fuera a 45° arriba y abajo, porque la pantalla se mira desde abajo, y a 20° a los lados. |
| Botón de 12 mm | 55 | Barreno de 12.3. Rebaje plano de 15 por fuera para la ceja y asiento plano de 24 por dentro para la tuerca: panel de 4.0 mm en el eje, 5.0 con la junta; el fabricante más restrictivo admite 6. |

- **Mica:** lámina transparente de 1 mm (acrílico o PETG) recortada a 27 × 19.5,
  delante del vidrio y en el mismo bolsillo. Sella la ventana. Sin ella la
  pantalla queda 1 mm más atrás.
- La pantalla queda 3.3 mm detrás de la cara exterior en el centro. Más afuera,
  el bolsillo rompía la tapa curva por los lados: así quedan 0.85 mm de piel en
  el canto del bolsillo y 0.9 sobre los pilotos.
- Los agujeros de la pantalla son de 2.0 según el plano del vendedor: el M2 entra
  justo. Si no pasa, repasar con broca de 2.2 o usar M1.6.
- **El LED del botón es de 12 V.** Con 3.3 o 5 V encenderá poco o nada.
- El tornillo de arriba de la tapa queda a 0.75 mm del cuello de la tapa de
  antena: es **M3×4** y no puede ser más largo.

## Montaje

1. **Base:** inserto del jalón (ver el pendiente de abajo).
2. **Tapa del panel:** botón con su tuerca por dentro; pantalla con la mica y
   cuatro M2×4; placa del USB-C en su repisa con una brida; LEDs; cables
   soldados con largo de sobra.
3. **Paquete:** amarrar batería, UM980, Thing Plus y demás al respaldo, por la
   ventana del panel y por los extremos del tubo.
4. **Tapa de antena:** antena con tres M2.5×10 desde dentro; SMA acodado;
   IMU en la plataforma con dos M2.5×6 avellanados; meter la plataforma por
   abajo hasta el clic, con el coaxial y los cables por el paso trasero.
5. **Tubo sobre la base:** dientes por las entradas, girar en sentido horario
   visto desde arriba hasta el tope y M3×12 del seguro.
6. **Tapa sobre el tubo:** bajar los cables del IMU y el coaxial por el canal del
   respaldo, conectar por la ventana del panel, girar en sentido horario hasta el
   tope (28.7°: dejar cable de sobra) y M3×12 del seguro.
7. **Tapa del panel:** conectar pantalla, botón, USB-C y LEDs y cerrar con dos
   M3×4.

La lista completa está en [SCREW-BOM.md](SCREW-BOM.md).

## Impresión

| Pieza | Orientación | Soportes |
| --- | --- | --- |
| `01-threaded-base` | Cara del jalón en la cama, como V2.1. | Los mismos que V2.1. |
| `02-logo-tube` | De pie. | Ninguno: el respaldo, sus costillas y el piso del canal nacen de una rampa a 45° desde el collar; las ranuras son puentes de 4.5 mm. |
| `03-antenna-cap` | Boca abajo, con la cara de la antena en la cama. | Ninguno: el canto que retiene cada uña es el techo de su ventana, un puente de 6.3 mm. |
| `04-imu-platform` | Disco en la cama. | Ninguno. La cara de retención de la uña es un voladizo de 0.9 mm. |
| `05-panel-cover` | De pie, sobre su canto inferior, con **brim**. | Ninguno: el techo del bolsillo de la pantalla es un puente de 27 mm y la repisa del USB-C, un puente entre sus costillas. |
| `06-aux-panel-cover` | De pie, como en V2.1. | Ninguno. |

**Material:** PETG o ASA. Las uñas flexionan 1.25 % al entrar: el PETG lo
aguanta de sobra; el PLA también, pero perdona menos y se ablanda al sol.

El barreno de 12.3 del botón se imprime en horizontal y puede salir algo cerrado
arriba: si el botón no entra, repasarlo con lima redonda.

## Altura del ARP: el firmware usa otra cifra

Del asiento del jalón (cara inferior de la base) a la cara donde apoya la antena
hay **156.9 mm** en V2.2; en V2.1 eran 136.9. El firmware usa
`kCaseOffsetM = 0.10` (`firmware/esp32/include/base_plan.h:9`), una cifra
declarada y sin medir que no corresponde a ninguna de las dos. Aquí no se cambió:
se corrige cuando se imprima la carcasa y se mida la real.

## Pendientes

- **Posición del chip del IMU:** 5.65 ± 0.15 de la recta de agujeros, de
  fuentes del vendedor. Conviene medirla en la placa real (ver arriba). El
  espesor del PCB tampoco está publicado: se supone 1.6.
- **Tuerca del botón:** el plano del vendedor no la acota; en los de
  fabricante mide 13.5-14 entre caras y 2.0-2.7 de espesor. El asiento interior
  es plano en 24 mm.
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
| `01-threaded-base.stl` | Base: inserto 5/8" y bayoneta. El piso queda liso: ya no hay trineo que atornillar. |
| `02-logo-tube.stl` | Tubo: logo grabado, respaldo de amarre, dos paneles, accesorios, líneas de diseño. |
| `03-antenna-cap.stl` | Tapa: HA-901A por fuera, cuello con las tres ventanas de la plataforma. |
| `04-imu-platform.stl` | Plataforma del IMU: disco, falda, tres uñas, separadores con piloto, apoyos y cruz grabada. |
| `05-panel-cover.stl` | Panel principal: pantalla, botón de 12 mm, USB-C y dos LEDs. |
| `06-aux-panel-cover.stl` | Panel auxiliar: USB-C hembra. |

## Regenerar

```sh
python3 mechanical/v2.2/regenerate.py
```

Localiza FreeCAD y funciona también en macOS. Hace, en este orden:

1. Reparte el exterior y coloca el logo (`layout_check.py`).
2. Elige la tornillería (`bom.py`).
3. Construye y exporta las piezas, y dibuja los componentes de referencia.
4. Comprueba sólidos, mallas cerradas e interferencias.
5. Ejecuta `capacity_check.py`: paquete contra el respaldo, hueco detrás de cada
   ranura, entrada de las dos tapas de panel por su ventana con todo montado,
   piel sobre la pantalla, botón, chip en el eje, sitio para el SMA, uñas y
   ventanas, orientación única de la plataforma, seguros y tornillos de panel.

Si algo falla, sale con código distinto de cero. Los resultados quedan en
[`generated/capacity.json`](generated/capacity.json).

Para verlo con colores, abrir `view_v2_2.py` desde FreeCAD. Los objetos `ref_*`
son los componentes comprados en su sitio: no se imprimen.

## Límites

- **Sin imprimir ni ensayar.** Sin datos de resistencia, ajuste, temperatura ni
  estanqueidad.
- Las holguras (0.15 en la falda de la plataforma, 0.3 en las ventanas de las
  uñas, 0.35 en la bayoneta) suponen una impresora que saca las cotas a ±0.1.
- La precarga de las uñas absorbe ±0.2 mm en la altura de las ventanas; más que
  eso y la plataforma queda con juego o no engancha.
- La antena sigue siendo la HA-901A atornillada por fuera.
