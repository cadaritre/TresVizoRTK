# Carcasa V2.3 (exploratoria): chasis deslizable para la placa principal v0.2

> **Estado:** geometría generada con scripts y comprobada en FreeCAD contra la placa v0.2 real
> (STEP con sus componentes), sus clavijas enchufadas y la placa panel-usb, en posición final y
> en el montaje paso a paso. **No se ha impreso ni montado nada.** Vive en la rama
> `hw/main-board-kicad`, fuera de `main`, igual que la placa principal. Resultados en
> [Verificaciones](#verificaciones).

Parte de la V2.2 de `main` (94f00f9: Ø64 × 130, tuerca 5/8 de latón, panel con OLED, botón de
12 mm y dos LEDs, plataforma del IMU en el cuello de la tapa, bandas de TPU). El exterior no
cambia; cambian el interior, la base, la tapa del panel y las bandas, para la placa principal v0.2
([../../hardware/main-board](../../hardware/main-board/README.md)).

## Qué cambia frente a V2.2

| Pieza | Cambio |
| --- | --- |
| 01 Base | **Cuatro retenes M3 en cruz** sobre la tuerca del jalón (antes dos). Ranura de 3 mm bajo J102 (x −21.5…−13.5, y 3.5…9.5) para el cable de la batería |
| 02 Tubo | Fuera el respaldo de amarre y los toalleros. Dos pares de **nervios guía** (desde x ±23.6, z 30–95) donde corren los rieles del chasis; dos **topes** sobre el collar inferior (z 15.95–17); **cuna de la 18650** en la pared trasera: nervios guía a todo lo alto, labios abajo y repisa con hueco y canal para el cable |
| 05 Tapa del panel | Hueco con la **forma exacta del USB-C** de la placa panel-usb y, por dentro, una **cuna tipo cajón** que la abraza sin tornillos. Fuera el bolsillo del JST-XH y **fuera los dos LEDs** (la OLED ya muestra el estado; J406 de la placa queda sin usar). El bolsillo de los pines de la OLED queda **abierto hacia arriba**, para no encerrar pines ni cables. El botón de 12 mm no cambia |
| 06 / 07 Bandas de TPU | Más altas para **tapar los tornillos de la tapa del panel** (z 29.0 y 102.9): la de abajo va de z 0 a 34 y la de arriba de 98.0 a 129.91, por encima del hueco del USB-C. Por dentro, ranura para la cabeza |
| 08 Chasis (nueva) | Se arma **fuera del tubo**: dos rieles donde corre la placa, una placa superior con ventana grande que los une y lleva H1/H2, ranuras de la carrier, lengua sobre la 18650 y zapatas bajo el cuello de la tapa. Entra por arriba entre los nervios |
| 09 Logo de TPU (nueva) | Incrustación **plana** del logo para imprimir en TPU, desenrollada de la curva del tubo para llenar su grabado |

El tubo lleva además **líneas verticales decorativas en los dos costados del panel**: además de 144–180° y 205–241°, ahora 0–36° y 312–348° (espejo respecto al panel, hasta 5.5° del logo), en z 34–98, entre las bandas.

Tapa de antena y plataforma del IMU son las de V2.2.

## Cómo se arma (sin tornillos dentro del tubo)

1. **18650 en su cuna.** Con la tapa de antena quitada, la celda baja por el collar de arriba
   **corrida 3.5 mm hacia el frente** (eje en y −16.4). En su posición final no cabe: llega a
   r 29.2 y el collar deja r 26. Los nervios de la cuna la guían sin tocarla.
   - Ya entera bajo el collar (fondo bajo z 42.9), se empuja hacia atrás hasta su eje en y −19.9,
     a 0.3 mm de la pared, y entra a presión en los labios (z 26–42). Los nervios se abren ~1.5 mm.
   - El cable baja por el hueco de la repisa y sale por un **canal a ras del piso hacia −X** que
     rodea el retén de la tuerca. Sigue por el piso, sube junto al collar, pasa por fuera del riel
     −X (x −27, z 24; ahí no hay nervios) y por delante del riel baja a J102.
   - Con el chasis puesto, la carrier (1.0 mm delante) y la lengua (arriba) no la dejan salir.
2. **Carrier en el chasis, fuera del tubo.** Entra por el frente, sin la placa puesta, hasta los
   labios traseros de sus dos ranuras, y apoya en sus dos pisos (z 18–19).
3. **Placa en el chasis, fuera del tubo: entra POR ABAJO.** Sube por los rieles y se atornilla
   desde el frente con dos **M2.5 × 8 autorroscantes** a los salientes de H1 y H2 de la placa
   superior.
   - Por arriba no entra: el módulo ESP32 (U201) llega a x 22.19 y chocaría con la lengüeta +X;
     J102 rozaría la −X.
   - La placa delante y dos topes de la placa superior dejan la carrier presa.
4. **Cables**, con el chasis aún fuera: arnés de J301 a la carrier y coaxial al SMA de la carrier.
5. **Chasis al tubo.** Entra por arriba, con los rieles entre los nervios, hasta apoyar en los
   topes del collar inferior.
6. **Por abajo**, con la base quitada: batería a J102 y NTC opcional a J404. Se pone la base.
7. **Arriba:** cable del IMU a J405 por la ventana de la placa superior y coaxial a la plataforma.
   Al cerrar la tapa de antena, su cuello (z 99.41) queda 0.21 mm sobre las zapatas del chasis:
   el chasis no puede subir.
8. **Panel:**
   - La placa panel-usb entra en su cuna deslizando hacia la tapa hasta que el USB-C asoma por el
     hueco; los dos dedos de atrás la retienen.
   - Se enchufan OLED (J403), botón (J402) y USB (J502 ↔ J101) por la ventana, y se atornilla la
     tapa del panel.
   - Las bandas de TPU tapan sus tornillos. Para abrir la tapa del panel o una bayoneta hay que
     quitar antes su banda.

## Geometría

Ejes de V2.2: z = eje del jalón hacia arriba, +Y = panel, +X a la izquierda mirando el panel.

**Pila de adelante hacia atrás:** placa principal (dorso en y 2.5, cara en y 4.1), carrier
(y −9.6…1.4) y 18650 (eje y −19.9, frente en y −10.6).
- Holguras: **1.1 mm** entre placa y carrier, y **1.0 mm** entre carrier y 18650, con la carrier
  supuesta de 11 mm.
- La placa va 1.0 mm más hacia el panel que en `hardware/main-board/cad` (allí: dorso en y 1.5).
- Su cara queda a 1.5 mm de los terminales del botón de V2.2; el botón ultracorto deja más.

**Chasis (08-sled):**
- **Rieles** en x ±23.3…25.2, z 17–99.2. Reciben los cantos de la placa con 0.15 mm por cara.
  - Lengüetas delanteras solo sobre las franjas sin componentes de la placa: en −X de z 39 a 87.5
    y en +X solo de z 71 a 87.5, para que la placa entre por abajo.
  - **El riel +X se corta en z 54–71, frente a la antena del ESP32.** Su tramo de abajo se une a
    la placa superior por detrás, con un enlace a 10 mm de la placa (x 11.2–16).
- **Placa superior** (y −2.4…2.35, z 71.4–99.2).
  - Detrás de la placa principal y encima de la carrier. Une los rieles y lleva los salientes Ø6
    de H1 (x 11.0, z 75.3) y H2 (−17.4, 83.8), con piloto Ø2.1 × 5.5.
  - **Ventana grande** en x −14…7.5, z 70–95.6, abierta por abajo: por ahí pasan la clavija SMA de
    la carrier, el coaxial y el cable del IMU.
  - Dos topes hacia atrás sobre los cantos de la carrier.
  - **¿Por qué no una placa entera?** Detrás de la placa principal solo hay 1 mm hasta la carrier,
    y otro hasta la pila: la placa solo cabe encima de la carrier. Abajo quedan los rieles con las
    ranuras.
- **Ranuras de la carrier:** labios detrás de su PCB (y −10.3…−9.8), pisos bajo su canto inferior
  (z 18–19). La de +X llega solo a z 50, lejos de la antena.
- **Zapatas** sobre cada riel, bajo el cuello de la tapa: r 24.2–25.5, ±14° (12 mm de arco por
  lado), z 97.0–99.2.
  - Apoyan en la cara plana del cuello; por dentro de r 24.4 está su chaflán de entrada.
  - Juego de 0.21 mm con la tapa cerrada.
- **Lengua sobre la 18650** (x 3…9, z 92–99.2), a la derecha del SMA para no estorbar el coaxial.
- Muescas alrededor de los retenes de la tuerca.
- Todo el chasis queda en **r ≤ 25.5** para pasar el collar de r 26.

**Tuerca del jalón:**
- Cuatro M3 cabeza botón en cruz:
  - a 90° y 270°, frente a una cara del hexágono: r 15, arandela ancha Ø9;
  - a 0° y 180°, frente a una esquina: r 16, para que el piloto deje 0.8 mm al alojamiento, y
    arandela normal Ø7, que pisa 1.25 mm de la esquina.
- La carrier sube a z 19 para librar la cabeza de 180°.

**USB-C del panel (05-panel-cover):**
- Hueco de 9.1 × 3.36 mm, esquinas R1.1, más 0.12 mm por lado. Es la envolvente de la carcasa del
  HRO TYPE-C-31-M-12 medida en el STEP de la panel-usb.
- Bolsillo de la lengüeta del PCB en la cara interior de la tapa.
- Cuna: piso de 1.2 mm bajo el PCB, paredes laterales en x ±10.55…11.3 con labios sobre sus cantos,
  y dos dedos flexibles (x ±7.2…9.6, a los lados de J502) con un diente en rampa que detiene el
  canto trasero del PCB.

**Logo de TPU (09-logo-inlay-tpu):**
- Seis piezas de 0.8 mm, el fondo del grabado.
- Cada punto se desenrolla a su arco sobre el radio medio del grabado (31.6 mm): pasa de 32.0 a
  33.55 mm de ancho.
- Contorno exacto, sin holgura: el TPU se comprime y entra a presión.
- Se imprime con la cara visible contra la cama.

Los valores salen de [parameters.json](parameters.json): bloques `chasis`, `cuna_18650`,
`panel.usb_c`, `tuerca_jalon.retenes`, `bandas` y `logo`.

## Supuestos que hay que medir antes de imprimir

- **Carrier BDLX:** 32 × 52 × 11 mm en todo su largo, componentes hacia la placa, SMA arriba.
  BDLX no publica plano.
  - Medir su espesor real sin el SMA, y la posición del SMA y de sus conectores GH8 y GH5.
  - Si sus conectores quedan en la cara que mira a la placa, no se pueden enchufar.
  - Corregir `chasis.carrier` y regenerar. Si es más delgada, las holguras crecen.
- **18650 protegida:** Ø18.6 × 69 mm.
- **Cable de la 18650:** se supone que sale por su extremo de abajo, de Ø2.6 como máximo y de
  ~70 mm o más hasta J102. Si sale por arriba, baja por el costado −X de la cuna.
- **Botón:** se mantiene la reserva del de V2.2 (19.5 mm detrás del panel y 6 de cables); el
  ultracorto ocupa menos.

## Impresión

Pensada para **MJF (PA12 o PA11)**: el chasis y la cuna de la tapa del panel tienen salientes en
varias direcciones, y la repisa de la batería tiene un voladizo plano de unos 8 mm. En FDM
necesitan soportes. Tolerancias de MJF: ±0.3 mm. Las holguras de deslizamiento son de 0.2 a
0.3 mm: imprimir primero el chasis y un tramo de tubo y probar el ajuste. Bandas y logo, en TPU.

## Regenerar

Requisitos: FreeCAD 1.1 (su Python).

```bash
cd mechanical/v2.3
export PYTHONPATH=/Applications/FreeCAD.app/Contents/Resources/lib
/Applications/FreeCAD.app/Contents/Resources/bin/python build_v2_3.py
/Applications/FreeCAD.app/Contents/Resources/bin/python export_v2_3.py
/Applications/FreeCAD.app/Contents/Resources/bin/python check_v2_3.py
/Applications/FreeCAD.app/Contents/Resources/bin/python logo_inlay.py
```

- `build_v2_3.py` genera `generated/TresVizo-V2.3.FCStd` y `model-index.json`.
- `export_v2_3.py` genera los STL y STEP de las piezas impresas y comprueba mallas e
  interferencias entre ellas.
- `check_v2_3.py` compara contra los STEP de `hardware/main-board/cad/` (placa con componentes,
  clavijas, panel-usb, envolventes supuestas) y escribe `generated/check.json`.
- `logo_inlay.py` genera la incrustación plana del logo (`generated/stl/09-logo-inlay-tpu.stl`).

## Verificaciones

Hechas el 05-10-2026 con FreeCAD 1.1.3 sobre los archivos de esta carpeta
([generated/check.json](generated/check.json), [generated/exports.json](generated/exports.json),
[generated/logo-inlay.json](generated/logo-inlay.json)).

| Comprobación | Resultado |
| --- | --- |
| Piezas | 8 piezas, un sólido válido cada una; mallas STL cerradas, sin no-manifold ni autointersecciones. Logo: 6 piezas, mallas cerradas |
| Choques entre piezas impresas en su posición final | 0 (límite 1 mm³ por pareja) |
| Choques con la placa v0.2 real (PCB y 110 componentes, movida 1 mm hacia el panel), clavijas enchufadas con sus cables, panel-usb real, carrier y su clavija SMA, 18650, coaxial, OLED, botón y retenes de la tuerca | 0 mm³ |
| Chasis armado en el collar Ø52 | radio máximo 25.5 mm (límite 25.65 con 0.35 de holgura) |
| Plástico del chasis junto a la antena del ESP32 (x 16.8–26, z 54.2–70.2) | 0 mm³ |
| Chasis contra la placa y sus 111 objetos del STEP (PCB y componentes) | PCB a 0.15 mm por cara (riel); componente más cercano a 1.1 mm (U201), luego L101 1.2, C307 1.5, J401 1.6, J405 1.6. Lo único delante de la cara de la placa son las lengüetas de los rieles, dentro de las franjas sin componentes de KiCad: +X en u 0–1.5, v 0–16.5 (franja u 0–2.55, v 0–16.55) y −X en u 44.3–46, v 0–48.5 (franja u 43.55–46, v 0–48.55) |
| Holguras | chasis–tapa 0.21 (zapatas, al cerrar), chasis–plataforma del IMU 0.71, chasis–base 1.09, chasis–18650 1.0, chasis–clavija SMA 0.6, chasis–coaxial 0.5; placa–carrier 1.1 y carrier–18650 1.0 (supuestas) |
| Montaje paso a paso (`hardware/main-board/cad/check_montaje_v2_3.py`, de la otra sesión, corrido sobre esta versión con la placa movida 1 mm) | 0 choques: 18650 en sus tres tramos, carrier al chasis, placa al chasis desde abajo (PCB y componentes), chasis armado al tubo con la 18650 puesta, clavijas de J102 y J404 desde abajo, plataforma del IMU. Lo que marca y no es real: la placa desde arriba (no se mete por ahí), las reservas de cable de J101/J502 (son el mismo cable) y la tapa de antena bajando recta (en la realidad gira con la bayoneta) |
| Cable de la 18650 a J102 (Ø2.6, 66.7 mm) | 0 choques con el recorrido corregido por delante del riel −X; holguras 0.17 al tubo, 0.18 a los retenes, 0.29 a la base, 0.52 al chasis |
| Contactos intencionados (holgura 0) | pie de los rieles sobre los topes del collar; carrier sobre sus pisos; 18650 tangente a los labios de su cuna (la retención es geométrica, no por interferencia) |

**No verificado:** tolerancias de impresión; rigidez del chasis, de los nervios de la cuna y de los
dedos de la cuna del USB-C; el giro de la bayoneta de la tapa de antena (sin cambio desde V2.2);
la carrier real (envolvente supuesta); el cable real de la pila; el ajuste del logo de TPU en su
grabado.
