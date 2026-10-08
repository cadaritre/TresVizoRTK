# Carcasa V3.0 (exploratoria): tubo compacto para la placa principal v0.3

> **Estado:** geometría generada con scripts y comprobada en FreeCAD 1.1.3 contra la **placa v0.3
> real** (`hardware/main-board/cad/placa-principal.step`, 107 sólidos, y las zonas de clavijas de
> `kicad/plugs.json` v0.3), la carrier BDLX modelada desde la foto, las dos 18650, la tuerca y su retén, la antena con sus tornillos, el
> coaxial, las clavijas y los cables, en posición final y en el montaje paso a paso. Incluye las
> correcciones de una auditoría del 08-10-2026. **No se ha impreso ni montado nada.** Rama
> `hw/compact-v03`. Resultados en [Verificaciones](#verificaciones).

Especificación y contrato con la placa:
[hardware/main-board/research/v03-compacta.md](../../hardware/main-board/research/v03-compacta.md).
Copia la arquitectura de [V2.3](../v2.3/README.md) (chasis que se arma fuera y entra por arriba,
base con la tuerca del bastón, tapa de antena), más chica: **Ø52 × 100** con una cara plana al
frente, dos 18650 y el panel dentro de la placa principal.

## Piezas

| Pieza | Qué es |
| --- | --- |
| 01-base | Disco de 2 mm con el anillo del redondeo R4 hasta z 4 y un **labio** de 0.8 × 1.5 que entra en el rebaje del tubo (unión en escalón). **Tuerca 5/8"-11 de latón** en un alojamiento hexagonal (z 2–15.9) sobre un anillo de asiento de 2 mm; saliente r 16 recortado en y 13.5; retén M2 detrás. Tres lengüetas (210°, 270°, 330°; z 2–11) con nervios hasta el saliente, para los tornillos radiales. Desagüe de Ø1.5 delante |
| 02-tube | Pared de 1.8 (R26, z 4–96) con la **cara plana** al frente (fuera y 22.13, dentro y 20.33 hasta \|x\| 13.65). Rebajes interiores de 0.9 en los dos extremos. Frente: ventana de la OLED con **bolsillo exterior** para una lámina pegada y chaflán de entrada por dentro; agujero y rebaje de la tecla; agujero de la guía de luz del LED. Costado +X: **túnel del USB-C** y **ranura de la microSD** con rebaje para la uña. **Ranuras** para las esquinas de los rieles, con sus repisas. **Cuna** de las celdas |
| 03-antenna-cap | Disco de 4 mm (z 96–100) con el redondeo R4 de arriba y un **labio** que baja al rebaje del tubo. Pasos y rebajes de los tres M2.5 de la antena, **paso del coaxial** Ø12 alargado 4 mm hacia el SMA, bolsillo sobre la OLED, dos **topes sobre las celdas** y tres lengüetas para los tornillos radiales |
| 04-chassis | Se arma fuera del tubo. **Rieles en C** sobre las franjas de 1 mm de la placa, con tope en z 80; **ranuras de la carrier** con topes arriba y **ganchos** flexibles abajo; **dos salientes** M2 detrás de la placa; **puente** con hueco para la tuerca de la clavija SMA y ventana para la llave; paredes laterales con un **tirador** arriba |
| 05-key-tpu | Tecla de TPU que se pone y se saca por fuera: pestaña pegada en el rebaje exterior, membrana de 0.4, cabeza que asoma 1.0 y émbolo a 0.35 de SW401 |
| 06-usb-plug-tpu | Tapón de TPU del túnel del USB-C: cuerpo a presión, ala curva sobre la pared y lengüeta |
| 07-sd-plug-tpu | Tapón de TPU de la ranura de la microSD, igual |

Tornillería y piezas compradas:

- tuerca hexagonal 5/8"-11 UNC de latón, estándar;
- 1 × M2 × 8 de cabeza alomada (ISO 7045) o botón, con arandela DIN 9021 **de M3** (Ø9 × 0.8,
  agujero 3.2): retén de la tuerca;
- 6 × M2.5 × 6 avellanados **ISO 14581** (Torx) o **ISO 7046** (cruz), radiales: 3 de la base y 3
  de la tapa. ISO 10642 y DIN 7991 empiezan en M3;
- 3 × M2.5 × 6 de cabeza alomada **ISO 7045** con arandela **ISO 7089**: antena, desde dentro de
  la tapa;
- 2 × M2 × 8 autorroscantes: OLED y placa a los salientes del chasis, con **separadores de 1.3**
  entre el módulo y la placa. Los pines del módulo se cortan a esa altura y se sueldan en pads SMD
  de J403 por la cara de arriba: no atraviesan la placa. El del lado −X, junto a la antena del
  ESP32, mejor **de nailon**, como recomendó la auditoría eléctrica;
- lámina de PC o acrílico de 1.0 × 25.64 × 14.76 para la ventana, pegada;
- guía de luz de Ø2 para el LED, pegada en su agujero, desde y 16.45 (0.34 sobre D403, de 0.71);
- coaxial fino (RG178 de Ø1.8 o de 1.13 mm) con una clavija SMA recta (tuerca de 5/16");
- kapton para la fila de 5 agujeros de la carrier (perno del bastón, ver la geometría).

## Cómo se arma

1. **Tuerca en la base.** Entra por arriba en su alojamiento. El M2 × 8 con su arandela ancha, a
   270° y r 14.5, pisa 1.9 mm de la cara trasera de la tuerca.
2. **Celdas**, con la tapa quitada y sin el chasis. Las dos 18650 (pack 1S2P) bajan por arriba a
   su cuna y apoyan en dos repisas (z 17.5). La NTC va pegada entre las dos, en el valle de
   delante.
   - Cable + e hilos de la NTC: bajan por ese valle (x 0, y −0.5…0.6), pasan al pasillo libre
     y 1.7–3.0 por debajo de z 72, van por él hasta x 17.5, junto al canto de la carrier, bajan
     al piso y van por delante, bajo el canto de la placa, a J404 (x 6.4…11.4) y J102
     (x −2.0…6.2). Sus clavijas bajan hasta z 2.75 (`kicad/plugs.json`).
   - Cable −: sale de una lengüeta bajo la celda +X, más allá de r 16, y baja por el mismo lado.
   - Nada pasa bajo las celdas: sobre el saliente de la tuerca solo hay 1.6 mm.
3. **Carrier al chasis, POR ABAJO**, con el arnés de J301 ya soldado. Sube por sus ranuras, abre
   los dos ganchos (0.85 mm) y queda entre los topes de arriba y los ganchos, con 0.2 de juego.
   No entra por delante ni por arriba: ver el conflicto 4.
4. **Clavija SMA en el SMA de la carrier, ANTES de la placa.** El frente del chasis está abierto:
   una llave fija de 8 entra por delante (+Y) y puede girar ±30° por la ventana del puente.
   - El coaxial es el de la antena: la tapa con la antena queda colgando del cable desde aquí.
5. **Placa al chasis, POR ABAJO**, con la OLED soldada. La muesca del canto de arriba
   (u 14.2–24.2, v 0–6.5) pasa alrededor de la tuerca.
   - Dos M2 × 8 autorroscantes por los agujeros de abajo de la OLED, los separadores de 1.3 y la
     placa.
   - El arnés de J301 va a su clavija (x −13.5…−2.5): por el piso, bajo el canto de la placa,
     hacia −X, y sube por el canal del lado −X.
6. **Chasis armado al tubo, por arriba**, con las celdas puestas. Las esquinas de los rieles
   corren por las ranuras del tubo y su pie apoya en las repisas (z 9.5).
7. **Tapa** con la antena atornillada, por arriba. El coaxial sobrante queda en un bucle sobre la
   placa. Tres M2.5 radiales en z 92. Los topes quedan a 0.3 sobre las celdas y la tapa a 0.3
   sobre el chasis.
8. **Por abajo, con la base quitada:** batería (GH 4) a J102 y NTC a J404, ya con la tapa puesta.
   Se pone la base con sus tres M2.5 radiales en z 8.
9. **Tecla, lámina de la ventana y guía de luz**, por fuera, pegadas. La tecla se puede sacar por
   fuera.
10. **microSD** por la ranura del costado; **tapones de TPU** en el USB-C y en la ranura cuando no
    se usan.

**Para sacar el chasis:** primero la tecla, por fuera (su émbolo está delante de la placa), y la
tapa. Después se tira del chasis con un gancho o un alambre por los agujeros de los tiradores de
las paredes laterales.

## Geometría

Ejes de V2.x: z = eje del bastón hacia arriba (z 0 en la cara de apoyo), +Y al frente (cara
plana), +X a la izquierda mirando el frente. Todo sale de [parameters.json](parameters.json).

**Alturas:** base z 0–4 (disco de 2 y anillo del redondeo; saliente de la tuerca hasta 15.9),
tubo z 4–96, tapa z 96–100. Uniones en escalón: labio de 0.8 × 1.5 de la base (z 4–5.5) y de la
tapa (z 94.5–96) pegado a la cara interior; el tubo tiene ahí un rebaje de 0.9 y le queda 0.9 por
fuera.

**Pila de adelante hacia atrás** (la de la especificación): cara plana por dentro y 20.33; vidrio
de la OLED hasta y 20.0; componentes de la placa hasta y 15.4 + h(x); PCB y 13.8–15.4;
componentes de la carrier y 6.9–13.3; PCB de la carrier y 5.3–6.9; patas del SMA hasta y 3.3;
celdas (ejes x ±9.5, y −7.9) hasta y 1.4.

**Tubo (02-tube):**
- Pared de 1.8. En la esquina interior de la cara plana (x ±13.65, y 20.33) mide **1.51** hasta
  el círculo exterior, no 1.8.
- **Ranuras de los rieles** a 31–47° y 133–149°, de r 24.2 a 24.8 (queda 1.2), con repisas en
  z 8–9.5.
- **Cuna:** tres nervios por celda (costado, atrás y un labio delante-fuera), a 0.3, y repisas bajo
  la parte de fuera de cada celda (r ≥ 16.6, z 16.3–17.5).
- **Frente:**
  - ventana de la OLED x ±12.12, z 73.32–86.68: área visible del módulo girado 180° más 0.25;
  - **bolsillo exterior** 0.8 mayor por lado y 1.0 de hondo (quedan 0.8 de pared) para la lámina
    de 1.0; chaflán de entrada de 0.4 a 45° en los cantos de dentro;
  - tecla: agujero Ø6.4 y rebaje exterior Ø9 × 0.6 para la pestaña;
  - LED: agujero Ø2 para la guía de luz.
- **Costado +X:**
  - **túnel del USB-C** desde x 14.6, 0.3 delante de la boca de J101 (x 14.9, u 3.1), de y 12.4
    hasta la cara exterior, z 18.5–31.5. Ver el conflicto 7;
  - **ranura de la microSD** de 12 × 2.0 (y 15.45–17.45), z 34–46: centro en z 40, el de J401 en la
    placa real (boca en u 1.5, v 32–48). Para una tarjeta de 1.0;
  - **rebaje para la uña:** cilindro R1.9 de 1.2 de hondo centrado en el canto delantero de la
    ranura.

**Base (01-base):**
- Tuerca con las caras hacia ±Y (su frente en y 11.9). Delante bajan la placa (dorso y 13.8, hasta
  z 8.5) y las clavijas (hasta z 2.4).
- **Perno del bastón:** como máximo 15.5 mm de rosca desde el asiento (z 0). La tuerca acaba en
  z 15.89 y las soldaduras de la fila de 5 de la carrier están en z 16.7: con 15.5 quedan a
  1.2 mm. Poner kapton en esa fila. Parámetro `base.tuerca.perno_max`.
- **Retén:** M2 × 8 a 270°, r 14.5, con arandela DIN 9021 de M3 (Ø9 × 0.8). Llega a r 10.0 y pisa
  1.9 mm de la cara trasera de la tuerca. La cabeza (hasta z 18.3) queda fuera de la planta de las
  celdas, a 0.27; la arandela pasa debajo de ellas con 0.8.
- Lengüetas r 21.0–23.9, z 2–11, con un M2.5 avellanado radial en z 8. Tienen nervios de 2 mm
  hasta el saliente de la tuerca (z 2–6). Caben sin tocar cables ni retén.
- Desagüe Ø1.5 en (0, 19.2).

**Tapa (03-antenna-cap):**
- Lengüetas r 21.0–23.9, z 88–96, en 0°, 180° y 270°. M2.5 avellanado radial en z 92.
- Tornillos de la antena: rebaje Ø5.4 × 2.4 para la cabeza ISO 7045 y la arandela. Quedan 1.6 de
  tapa encima y el M2.5 × 6 entra 3.9 en la antena (rosca de 6 supuesta).
- **Topes sobre las celdas:** Ø6 en (±7, −12), de z 87.8 a la tapa (0.3 sobre las celdas).
  - No van sobre los ejes de las celdas: ahí caen los tornillos de la antena a 210° y 330°, que
    se aprietan desde abajo.
- Bolsillo de la OLED: x ±14.1, y 15.1–21.0, techo en z 97.3.
- **Antena:** el modelo y su conector **no están confirmados** ([hardware/bom.md](../../hardware/bom.md):
  "Helix; modelo exacto por confirmar"). La tapa es paramétrica (`antena` en parameters.json): si
  cambia la antena se reimprime solo la tapa.

**Chasis (04-chassis):**
- **Rieles en C**, z 9.5–81:
  - ranura de la placa a 0.15 por cara;
  - labio delantero desde |x| 17.1, dentro de la franja;
  - tope de la placa en z 80;
  - el riel +X se corta en z 18.2–46.3, frente a la funda del USB-C y a la tarjeta.
- **Paredes laterales** x ±19–20, hasta z 95.7, con un **tirador** arriba: lengüeta de 2 mm y
  agujero Ø2.5 en z 93.5.
- **Antena del WROOM (U201):** como en V2.3, sin plástico del chasis delante de ella.
  - La antena son los últimos 6 mm del módulo: x −15.15…−9.15, z 49.9–67.9.
  - En z 44.5–73 se quitan el riel −X (labio, dorso y pared) y la punta de la pared lateral: todo
    lo que quedaba a menos de 5 mm.
  - La placa sigue guiada por el resto del riel −X (z 9.5–44.5 y 73–81), el riel +X y los dos M2.
    No puede salir de lado: los tramos de riel de arriba y de abajo la retienen.
  - Dentro de los 5 mm solo queda el saliente M2 de la OLED del lado −X, detrás de la placa: no se
    puede mover.
- **Ranuras de la carrier** con las reglas de V2.3 para sus cantos (USB-C que sobresale, soldaduras
  del arnés, componentes junto a los cantos).
  - Topes en z 69.2–70.2 y labios de los ganchos en z 16.0–16.8: **0.2 de juego** arriba y abajo.
  - Ganchos: brazo de 0.8 × 1.1, ranuras de **0.6** a los lados (mínimo de MJF) y 1.3 libres
    detrás.
- **Salientes** Ø5 en x ±11.75, z 70.2, de y 8.0 a 13.8; piloto Ø1.6 × 5.
- **Puente** (y 2.0–5.9, z 72.3–84), detrás de la clavija SMA y delante de las celdas:
  - hueco y ≤ 5.0 en x −6.5…4.1 para la tuerca de la clavija, que gira con 9.2 entre esquinas:
    queda a 0.6;
  - **ventana** en z 75.5–80, x −10.5…8.5, para la llave fija de 8 girada ±30°. El puente queda en
    dos barras unidas por los lados.
- Todo en r ≤ 23.9, salvo las esquinas de los rieles (r 24.5, en las ranuras).

**Tecla (05-key-tpu):**
- Pestaña Ø8.8/6.4 × 0.6 pegada en el rebaje exterior, a ras.
- Membrana de 0.4 y cabeza Ø5 que asoma 1.0.
- Émbolo Ø3 hasta 0.35 de SW401, que en la placa real mide 1.55 de alto (recorrido del pulsador:
  0.25).

**Tapones (06, 07):**
- Cuerpo sin holgura nominal: el TPU entra a presión.
- Ala de 0.6 sobre la pared, 1.5 más grande que la abertura, y lengüeta de 4 × 3 para tirar.
- El de la microSD queda a 0.5 de la tarjeta puesta.

**Coaxial:**
- Clavija SMA recta: tuerca de 5/16" (7.94 entre caras, 9.2 entre esquinas, 5.5 de largo) en el
  cañón (z 74.5–80) y cuerpo Ø6.5 hasta z 89.5.
- Cable fino en S hasta el paso de la tapa y bucle de servicio (reserva: anillo de r 7 en z 92.4)
  sobre la placa.

## Conflictos con la especificación

Lo que no cabe como estaba pedido, con números y lo que se hizo. Nada se cambió en silencio.

1. **Clavija SMA de la carrier y placa.**
   - La tuerca de la clavija (9.2 entre esquinas, eje en y 10.2) llega a y 14.8, y el dorso de la
     placa está en y 13.8.
   - **Resuelto** con la muesca del canto de arriba de la placa (u 14.2–24.2, v 0–6.5), que según
     la coordinación ya está en la placa real (`placa.muesca_sma.activa`). La tuerca queda a 1.0
     del PCB y la placa sube a su sitio pasando la tuerca.
   - Hay que comprobarlo con el STEP real.
2. **El coaxial no puede curvarse con R ≥ 10.**
   - Del cuerpo de la clavija (z 89.5, a 10.27 del eje) al paso de la tapa (eje, z 100) la S sale
     de **R 5.25**. R 10 pide 17.5 mm de alto; hay 10.5.
   - Se pasa a un coaxial fino (RG178 de Ø1.8 o de 1.13 mm) con bucle de servicio. Hay que mirar en
     la hoja del cable que admita R 5.25 fijo.
   - El paso de la tapa se alargó 4 mm hacia el SMA.
3. **Retenes de la tuerca.**
   - Los M3 de V2.3 (hasta z 18.35) no caben: las celdas empiezan en z 17.5 y la carrier en z 17,
     alrededor de toda la tuerca salvo el frente.
   - Un solo M2 con arandela ancha de M3 a 270°, en r 14.5 (no en 14.1): ahí también libra la
     cabeza alomada de Ø4.
4. **La carrier no puede entrar por delante ni por arriba.**
   - Los salientes M2 de la OLED, detrás de la placa (y 8–13.8, z 67.7–72.7), le cierran el paso.
   - Barrido contra los salientes solos: por delante choca el canto de su PCB; por arriba, nueve de
     sus piezas; por abajo, nada.
   - Entra por abajo y la sostienen dos ganchos. Los labios delanteros de sus ranuras solo pueden
     ir en z 59.5–69.
5. **Base y tapa con tornillos radiales, no con bayoneta.** El collar de una bayoneta necesita unos
   3 mm dentro de r 24.2, y delante las clavijas (y 19.8) y la OLED (y 20.0) llegan a menos de
   0.6 de la cara plana.
6. **Rieles de la placa.** La esquina del canto de la placa está en r 23.69, a 0.5 del tubo: un
   riel en C con labios de 0.8 necesita las dos ranuras de 0.6 en la pared.
7. **Túnel del USB-C (y 12.4 hasta fuera, no 13.4–20.6).** Con y 13.4–20.6 desde x 14.7 quedaban
   dos cuñas:
   - sobre el túnel, de 0.85 a 0 mm (calculado; el sondeo de espesor mide 0.46 a 0.6 de su filo);
   - abajo, contra el lado de la ranura del riel a 31°, de 0.74 a 0.01 mm (calculado).
   
   Con el túnel desde y 12.4 y abierto hasta la cara exterior, la pared más fina alrededor mide
   0.84.
8. **Rebaje para la uña.** Centrado en el canto delantero con R2.5, bajaba la pared a 0.59 bajo la
   ranura. Con R1.9 y 1.2 de hondo deja 0.65.
9. **La tecla traba el chasis.** Su émbolo queda delante de la placa: con la tecla puesta, al subir
   el chasis los componentes chocan con él a los 12 mm. Se saca por fuera antes; sin ella, el
   chasis sale limpio.
10. **Guía de luz del LED.** Pide a la placa nada más que el LED en r 1.5 alrededor de D403
    (x −6, z 22). La placa real lo cumple: la guía queda a 0.345 de lo más cercano.

## Verificaciones

Hechas el 08-10-2026 con FreeCAD 1.1.3 sobre los archivos de esta carpeta
([generated/check.json](generated/check.json), [generated/exports.json](generated/exports.json)).
- **Placa real:** `hardware/main-board/cad/placa-principal.step` (PCB y 106 componentes, con sus
  muescas del USB-C y del SMA).
  - La última corrida de `check_v3_0.py` fue contra el STEP de las 06:36 del 08-10-2026, exportado
    después de las correcciones de la auditoría eléctrica: J403 con pads SMD, sin mover ninguna pieza.
  - Resultados: 0 choques, los 11 barridos limpios y la guarda de la pared sin faltantes. Las holguras
    de esta sección son de esa corrida.
- **Clavijas reales:** zonas de J102, J404 y J301 de `kicad/plugs.json` v0.3.
- El módulo OLED no está en el STEP: se dibuja desde sus medidas (separador de 1.3, vidrio hasta
  y 20.0).

> **Corregido el 08-10-2026.** La primera versión del tubo salía **sin la pared de la cara plana**
> en |x| < 9.79, en todo el alto: el hueco interior juntaba el círculo de r 24.2 entero con la cara
> plana. Ningún choque lo mostraba. Desde entonces `export_v3_0.py` y `check_v3_0.py` sondean la
> pared, y `check_v3_0.py` compara además su volumen y mide su espesor mínimo.

| Comprobación | Resultado |
| --- | --- |
| Piezas | 7 piezas, un sólido válido cada una. Mallas STL cerradas, sin no-manifold ni autointersecciones. Triángulos: base 5436, tubo 5302, tapa 6110, chasis 1928, tecla 812, tapones 124 y 100. Volúmenes en cm³: base 8.37, tubo 27.78, tapa 7.71, chasis 4.76, tecla 0.08, tapones 0.51 y 0.11 |
| Pared del tubo: sondas a media pared cada 0.5 mm | Cara plana: 10 120 puntos, 1 793 en las aberturas, **0 sin material**. Anillo: 48 371 puntos, 3 042 en las aberturas, **0 sin material** |
| Pared del tubo: volumen | 27 780.5 mm³; esperado 27 779.4 (+0.004 %, tolerancia 0.5 %). Pared intencionada hecha aparte con polígonos: 25 856.1 |
| Pared del tubo: espesor mínimo (pedido 0.6) | Túnel del USB-C 0.88; ranura de la microSD y rebaje 0.65; ventana de la OLED 0.72 (en el chaflán; 0.8 en el resto del bolsillo); tecla y LED 1.2; uniones 0.9; pared normal 1.2 en la sección (radial: 1.8) |
| Choques en posición final | 0 entre piezas, 0 de las piezas con las 154 referencias y 0 entre referencias. El tapón del USB-C y la funda de la clavija son alternativos y no se cuentan |
| Barridos (pasos de 0.5 mm) | 0 choques en los once (lista de abajo) |
| Llave fija de 8 en la tuerca SMA, sin la placa | Holgura al chasis 1.03 recta y 0.5 girada ±30° |
| Chasis armado con la tecla puesta | Bloqueado: J102 choca con el émbolo a los 10 mm de subida. Sin la tecla sale limpio |
| Chasis armado (chasis, placa real, OLED, carrier, clavija SMA) | Radio máximo 24.5 (esquinas de los rieles, en las ranuras de r 24.8); fuera de ellas 24.05 (vidrio de la OLED, dentro de la cara plana). Holgura al tubo por encima de las repisas: 0.27 |
| Holguras del chasis | Tubo 0.27; celdas 0.6; componentes 0.294 (U302 y U303; luego R115 0.4); carrier 0.15; base 0.3; tapa 0.3; tuerca SMA 0.6 (pedido ≥ 0.5) |
| Holguras del tubo | Celdas 0.3; PCB 0.3; componentes y OLED 0.3 (componentes reales: J401 0.354, U303 0.51); funda USB-C 0.3; tarjeta 0.52 |
| Holguras de la tapa y de la base | Tapa: OLED 0.3, celdas 0.3 (topes), coaxial 2.04. Base: clavijas reales 0.58, PCB 0.3, carrier 1.1, celdas 1.6; componentes más cercanos (C114, J102, J301) a 1.9 |
| Holguras a la cara plana | Vidrio de la OLED 0.33; PCB, cinta y tornillos de la OLED 0.73; componentes 0.67; clavijas 0.58; chasis 5.27. La pestaña de la tecla va a ras en su rebaje (contacto) |
| Tecla y guía de luz contra la placa real | Émbolo–SW401 (1.55 de alto) 0.355; tecla–otros componentes 1.8; guía de luz–D403 (0.71 de alto) 0.345 |
| Otras holguras | Tuerca SMA–PCB 1.0; perno de 15.5–soldaduras de la carrier 1.2; perno–celdas 2.0; retén–celdas 0.27; tapones–chasis 0.35; tapón–tarjeta 0.5; bucle del coaxial–piezas 2.7 |
| Cables (reservas a J102, J404 y J301 reales) | Al resto de piezas: + y NTC 0.91 (base), − 0.73 (base), arnés de J301 0.1 (pared lateral del chasis) y 0.3 (base). A los componentes, 3.1 o más |
| Antena del WROOM (U201: x −15.15…−9.15, z 49.9–67.9, delante de la placa) | Plástico del chasis a menos de 5 mm: **204.8 → 45.1 mm³** al quitar el riel −X y la punta de la pared lateral en z 44.5–73. Lo que queda es el saliente M2 de la OLED del lado −X, a 1.6 por detrás de la placa. La pared del tubo queda a 0.29 de la esquina del módulo |
| Nada de la placa por detrás de su dorso delante del SMA de la carrier (x −6…3, y < 13.8, z 60–80) | Cumple con el STEP de las 06:36 del 08-10-2026. J403 no tiene modelo 3D: sus pines se cortan a la altura del separador y se sueldan sobre pads SMD de la cara, sin agujeros, así que acaban en y 15.4 |
| Contactos intencionados (holgura 0) | Pie de los rieles en sus repisas; placa contra los salientes (y 13.8) y el tope (z 80); celdas en sus repisas; base, tapa, tecla y tapones contra el tubo |
| Coaxial | R disponible 5.25; pedido 10: **no cumple** ([conflicto 2](#conflictos-con-la-especificacion)) |

Los once barridos:
- celdas por arriba (85 mm) contra el tubo y la base;
- carrier al chasis por abajo (60 mm; sin los labios de los ganchos, que se apartan);
- clavija SMA por arriba con la carrier en el chasis y sin la placa (25 mm; tuerca con su barrido
  de 9.2);
- llave fija de 8 por delante (30 mm);
- placa real con la OLED por los rieles, por abajo (92 mm), con la carrier y la clavija SMA
  puestas;
- chasis armado por arriba (92 mm), con las celdas y sus cables, sin la tecla;
- base por abajo (20 mm) contra todo lo de dentro, con las clavijas y cables reales;
- tapa con la antena por arriba (20 mm);
- tecla por fuera (12 mm);
- tarjeta microSD por el costado (15 mm);
- tapones por fuera (12 mm).

Con la envolvente de la especificación en vez de la placa real (`--envelope`), el mismo día:
- 0 choques de la carcasa;
- once barridos limpios;
- holgura más justa: la del labio del riel a la franja (0.1).

Lo único que marca es referencia contra referencia: las zonas de clavija reales entran 0.35–0.46 mm
en sus conectores, que la envolvente rellena (5 a 15 mm³).

**No verificado:**
- **El módulo OLED real** (no está en el STEP), con su separador de 1.3 y el vidrio hasta y 20.0.
- **La carrier:** modelo sacado de una foto (±1 mm). **Medirla con calibre antes de imprimir** el
  chasis; los topes y ganchos tienen 0.2 de juego.
- **Cables:** reservas de Ø1.5 (pack y NTC) y Ø3 (arnés) por recorridos supuestos. No se sabe por
  dónde salen los del pack real.
- **Antena y coaxial:** modelo y conector sin confirmar; radio de curva admisible del cable fino;
  rosca de 6 de la antena.
- **Antena del WROOM:** cuánto la desafinan el saliente M2 de la OLED (1.6 mm detrás de la placa) y la
  pared del tubo (0.29 de la esquina del módulo).
- **Perno del bastón:** el largo real de la rosca. Con más de 15.5 mm toca la carrier.
- **Impresión:**
  - tolerancias de MJF (±0.3) frente a holguras de 0.15 a 0.3;
  - flexión de los ganchos;
  - paredes de 0.65 a 0.9 junto a las aberturas y de 1.2 en las ranuras;
  - agarre de los M2.5 radiales (2.9 mm de rosca) y del retén M2;
  - ajuste a presión de los tapones de TPU;
  - la membrana de la tecla;
  - el pegado de la lámina y de la guía de luz;
  - la estanqueidad de las uniones en escalón.
- **Llave:** la envolvente es la de una llave fija de 8 genérica (bocas hasta 3.4 detrás del eje,
  cabeza de 15 de ancho, 3.5 de grueso).
- **La unión base–tubo:** solo lleva tornillos atrás y a los lados. Delante hay escalón, pero no
  se sabe si el borde se abre al cargar el bastón.

## Impresión

Pensada para **MJF (PA12 o PA11)**, como V2.3. La tecla y los tapones, en TPU. Probar primero un
tramo de tubo y el chasis (rieles, ranuras y ganchos).

**En FDM, como plan B:**
- las repisas de las celdas y de los rieles, los nervios de la cuna y los topes de la tapa tienen
  voladizos planos sin chaflán: necesitan soportes, o un chaflán de 45° que habría que añadir;
- los redondeos R4 de la base y de la tapa quedan bien solo con esa cara contra la cama;
- los ganchos de la carrier (brazos de 0.8 con ranuras de 0.6), los labios de 0.8 de los rieles y
  la membrana de 0.4 de la tecla son demasiado finos para FDM con boquilla de 0.4. Habría que
  rediseñarlos;
- las paredes de 0.65 a 0.9 junto a las aberturas quedan en dos perímetros como mucho.

## Regenerar

Requisitos: FreeCAD 1.1 (su Python). `geom_v3_0.py` tiene la geometría común, las referencias y
las guardas de la pared. Usa `hardware/main-board/cad/carrier_bdlx.py` y, si están,
`hardware/main-board/cad/placa-principal.step` y `hardware/main-board/kicad/plugs.json` (v0.3).
Sin ellos, la envolvente y la zona de clavijas de respaldo de `parameters.json`.

```bash
cd mechanical/v3.0
export PYTHONPATH=/Applications/FreeCAD.app/Contents/Resources/lib
/Applications/FreeCAD.app/Contents/Resources/bin/python build_v3_0.py
/Applications/FreeCAD.app/Contents/Resources/bin/python export_v3_0.py
/Applications/FreeCAD.app/Contents/Resources/bin/python check_v3_0.py   # placa real; unos 11 minutos
# con la envolvente de la especificacion:
/Applications/FreeCAD.app/Contents/Resources/bin/python check_v3_0.py --envelope
```

- `build_v3_0.py` genera `generated/TresVizo-V3.0.FCStd` (piezas y referencias `ref_*`) y
  `model-index.json`.
- `export_v3_0.py` genera los STL y STEP de las piezas y comprueba las mallas, las interferencias
  entre piezas y la pared del tubo (sondas cada 1 mm). Si falta pared, termina con código 1.
- `check_v3_0.py` escribe `check.json`:
  - `guarda_pared_tubo`: sondas, volumen y espesor mínimo;
  - choques en posición final y barridos;
  - holguras, también a la cara plana, y holgura de la llave;
  - bloqueos al sacar el chasis con la tecla puesta;
  - radio del chasis armado.
