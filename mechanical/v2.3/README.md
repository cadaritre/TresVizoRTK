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
| 05 Tapa del panel | Hueco con la **forma exacta del USB-C** de la placa panel-usb y, por dentro, **dos ménsulas** donde se atornilla por sus agujeros M2 (H501/H502) con autorroscantes M2×5. Fuera el bolsillo del JST-XH y **fuera los dos LEDs** (la OLED ya muestra el estado; J406 de la placa queda sin usar). El bolsillo de los pines de la OLED queda **abierto hacia arriba**, para no encerrar pines ni cables. El botón de 12 mm no cambia |
| 06 / 07 Bandas de TPU | Más altas para **tapar los tornillos de la tapa del panel** (z 29.0 y 102.9): la de abajo va de z 0 a 34 y la de arriba de 98.0 a 129.91, por encima del hueco del USB-C. Por dentro, ranura para la cabeza |
| 08 Chasis (nueva) | Se arma **fuera del tubo**: dos rieles donde corre la placa, una placa superior con ventana grande que los une y lleva H1/H2, ranuras de la carrier, lengua sobre la 18650 y zapatas bajo el cuello de la tapa. Entra por arriba entre los nervios |
| 09 Logo de TPU (nueva) | Incrustación **plana** del logo para imprimir en TPU, desenrollada de la curva del tubo para llenar su grabado |

El tubo lleva además **líneas verticales decorativas**, simétricas respecto al eje panel (90°)–logo (270°): 0–36° y 144–180° a los lados del panel, y 198–234° y 306–342° a los lados del logo (a 6° de él), en z 34–98, entre las bandas. Entre los grupos de cada costado quedan 18°.

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
   - **NTC de la celda** (obligatoria desde el 07-10-2026; la placa no carga sin ella): antes de
     meter la celda, pegarla con cinta kapton al **frente** de la celda (el lado que mira a la
     carrier), en x 0…+4 y z 25–35. Ahí hay ~3.2 mm hasta el dorso de la carrier; las patas del SMA
     y las soldaduras de la carrier quedan lejos (z 63–72, x −20 y fila de abajo en z ~19.6,
     x −11…−1). Sus dos hilos bajan por la celda y salen con el cable de la batería por el hueco de
     la repisa y el canal hasta J404, junto a J102.
   - Con el chasis puesto, la carrier (3.2 mm delante, salvo las patas del SMA) y la lengua
     (arriba) no la dejan salir.
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
   - La placa panel-usb se pone con el USB-C en su hueco y la lengüeta en su bolsillo, y se atornilla
     a las dos ménsulas con dos autorroscantes M2×5 por sus agujeros H501/H502.
   - Se enchufan OLED (J403), botón (J402) y USB (J502 ↔ J101) por la ventana, y se atornilla la
     tapa del panel.
   - Las bandas de TPU tapan sus tornillos. Para abrir la tapa del panel o una bayoneta hay que
     quitar antes su banda.

## Geometría

Ejes de V2.2: z = eje del jalón hacia arriba, +Y = panel, +X a la izquierda mirando el panel.

**Pila de adelante hacia atrás:** placa principal (dorso en y 2.5, cara en y 4.1), carrier
(y −7.4…1.6, con las patas del SMA hasta y −10.4) y 18650 (eje y −19.9, frente en y −10.6).
- Holguras: **0.9 mm** entre placa y carrier y **0.32 mm** entre las patas del SMA y la 18650,
  con las medidas de la carrier (sacadas de una foto) **más 1 mm** (9 mm de grueso, patas de 3 mm). Las patas
  no se cortan: el hueco lo deja la carcasa.
- La placa va 1.0 mm más hacia el panel que en `hardware/main-board/cad` (allí: dorso en y 1.5).
- Su cara queda a 1.5 mm de los terminales del botón de V2.2; el botón ultracorto deja más.

**Chasis (08-sled):**
- **Rieles** en x ±23.3…25.2, z 17–99.2. Reciben los cantos de la placa con 0.15 mm por cara.
  - Lengüetas delanteras solo sobre las franjas sin componentes de la placa: en −X de z 39 a 87.5
    y en +X solo de z 72.4 a 87.5, para que la placa entre por abajo.
  - **El riel +X se corta en z 53.7–72.4, frente al ESP32-S3-WROOM-1** (módulo en x −2.75…22.75,
    z 53.8–71.8; antena en el canto +X). Su tramo de abajo se une a
    la placa superior por detrás, con un enlace a 10 mm de la placa (x 11.2–16).
- **Placa superior** (y −2.4…2.35, z 71.4–99.2).
  - Detrás de la placa principal y encima de la carrier. Une los rieles y lleva los salientes Ø6
    de H1 (x 11.0, z 77.9) y H2 (−17.4, 83.8), con piloto Ø2.1 × 5.5.
  - **Ventana grande** en x −14…7.5, z 70–95.6, abierta por abajo: por ahí pasan la clavija SMA de
    la carrier, el coaxial y el cable del IMU.
  - Dos topes hacia atrás sobre los cantos de la carrier.
  - Su esquina +X de abajo se recorta en x ≥ 16 hasta z 72.6: nada de plástico frente a la antena.
  - **¿Por qué no una placa entera?** Detrás de la placa principal solo hay 1 mm hasta la carrier,
    y otro hasta la pila: la placa solo cabe encima de la carrier. Abajo quedan los rieles con las
    ranuras.
- **Ranuras de la carrier:** labios detrás de su PCB (y −8.1…−7.6), pisos bajo su canto inferior
  (z 18–19). La de +X llega solo a z 50, lejos de la antena.
  - Con los componentes de la carrier modelados desde la foto (con 1 mm de más) aparecieron dos choques
    que la caja no veía, y se abrió la ranura:
    - **USB-C de la carrier**, que sobresale ~0.9 mm de su canto +X: rebaje del muro +X en
      x 11.1…13.3, z 21.5…34. Queda a 1.40 mm.
    - **Soldaduras del arnés de J301**, junto al canto −X: sin labio en z 22.5…43, y el muro se abre
      0.8 mm por detrás del PCB.
    - Además, el muro +X se retrasa 1 mm en z 34…50 frente a la placa del UM980, que queda a 0.86 mm.
  - Comprobado con `carrier_check.py` de la otra sesión: 0 choques en su sitio y en toda la entrada
    por el frente.
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
- **Dos ménsulas** en x ±5.9…10.2, desde y 22 hasta la tapa, con la cara de apoyo en z 90.17 (cara
  inferior del PCB) y la de abajo a 45°. Agujeros guía de Ø1.6 × 4.5 mm en (x ±7.9, y 25.0) para
  autorroscantes M2×5, bajo H501/H502 de la panel-usb.

**Logo de TPU (09-logo-inlay-tpu):**
- Seis piezas de 0.8 mm, el fondo del grabado.
- Cada punto se desenrolla a su arco sobre el radio medio del grabado (31.6 mm): pasa de 32.0 a
  33.55 mm de ancho.
- Contorno exacto, sin holgura: el TPU se comprime y entra a presión.
- Se imprime con la cara visible contra la cama.

Los valores salen de [parameters.json](parameters.json): bloques `chasis`, `cuna_18650`,
`panel.usb_c`, `tuerca_jalon.retenes`, `bandas` y `logo`.

## Medidas supuestas (con holgura; no hay que medir nada)

- **Carrier BDLX:** envolvente de 32 × 52 × 9 mm, componentes hacia la placa, SMA arriba. BDLX no
  publica plano. Medida en foto el 05-10-2026 (±1 mm, sin calibrador):
  - Mide ~8 mm de grueso (PCB 1.6 + SMA ~6.5). Por decisión del propietario se toma todo con
    **1 mm de más**: envolvente de 9 mm.
  - SMA acodado: cuerpo en x −10…−2.5 (la envolvente cubre x −11…0.5), eje del cañón en x ≈ −6.2,
    punta en z ≈ 81. Sus 4 patas asoman 1–2 mm por detrás, hacia la 18650; se reservan 3 mm
    (x −11…−1.5, z 63.5–72) y **no se cortan**: la carrier va 2.2 mm más cerca de la placa que
    con la envolvente supuesta de 11 mm para dejarles aire.
  - Sus conectores (GH5 vertical y el de 8 pines) no caben con clavija: el arnés de J301 va
    **soldado** a las filas de agujeros de la carrier, plano.
  - No se mide: la carrier es lo único sacado de una foto y ya lleva su milímetro de más. Si algún
    día se quiere ajustar, se cambia `chasis.carrier` y se regenera.
- **18650 protegida:** Ø18.6 × 69 mm.
- **Cable de la 18650:** se supone que sale por su extremo de abajo, de Ø2.6 como máximo y de
  ~70 mm o más hasta J102. Si sale por arriba, baja por el costado −X de la cuna.
- **Botón:** se mantiene la reserva del de V2.2 (19.5 mm detrás del panel y 6 de cables); el
  ultracorto ocupa menos.

## Impresión

Pensada para **MJF (PA12 o PA11)**: el chasis y las ménsulas de la tapa del panel tienen salientes en
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
| Choques con la placa v0.2 real (PCB y 110 componentes, movida 1 mm hacia el panel), clavijas enchufadas con sus cables, panel-usb real, carrier medida (con su SMA y sus patas, + 1 mm), 18650, coaxial, OLED, botón y retenes de la tuerca | 0 mm³ |
| Chasis armado en el collar Ø52 | radio máximo 25.5 mm (límite 25.65 con 0.35 de holgura) |
| Plástico del chasis junto a la antena del ESP32 (antena del WROOM-1: x 16.3–23, z 54.2–72.2) | 0 mm³ |
| Placa con el ESP32-S3-WROOM-1 (06-10-2026; STEP de `kicad-cli` con el modelo del WROOM corrido a su `.wrl`, fuera de `check_v2_3.py`, que aún usa el STEP de `hardware/main-board/cad` con el MINI) contra las 8 piezas | 0 mm³; radio máximo de la placa 23.35 |
| Chasis contra la placa y sus 111 objetos del STEP (PCB y componentes) | PCB a 0.15 mm por cara (riel); componente más cercano a 1.1 mm (U201), luego L101 1.2, C307 1.5, J401 1.6, J405 1.6. Lo único delante de la cara de la placa son las lengüetas de los rieles, dentro de las franjas sin componentes de KiCad: +X en u 0–1.5, v 0–16.5 (franja u 0–2.55, v 0–16.55) y −X en u 44.3–46, v 0–48.5 (franja u 43.55–46, v 0–48.55) |
| Holguras | chasis–tapa 0.21 (zapatas, al cerrar), chasis–plataforma del IMU 0.71, chasis–base 1.09, chasis–18650 1.0, chasis–coaxial 0.5; placa–carrier 0.9 y patas del SMA–18650 0.32 (carrier medida en foto + 1 mm) |
| Montaje paso a paso (`hardware/main-board/cad/check_montaje_v2_3.py`, de la otra sesión, corrido sobre esta versión con la placa movida 1 mm) | 0 choques: 18650 en sus tres tramos, carrier al chasis, placa al chasis desde abajo (PCB y componentes), chasis armado al tubo con la 18650 puesta, clavijas de J102 y J404 desde abajo, plataforma del IMU. Lo que marca y no es real: la placa desde arriba (no se mete por ahí), las reservas de cable de J101/J502 (son el mismo cable) y la tapa de antena bajando recta (en la realidad gira con la bayoneta) |
| Cable de la 18650 a J102 (Ø2.6, 66.7 mm) | 0 choques con el recorrido corregido por delante del riel −X; holguras 0.17 al tubo, 0.18 a los retenes, 0.29 a la base, 0.52 al chasis |
| Contactos intencionados (holgura 0) | pie de los rieles sobre los topes del collar; carrier sobre sus pisos; 18650 tangente a los labios de su cuna (la retención es geométrica, no por interferencia) |

**No verificado:** tolerancias de impresión; rigidez del chasis, de los nervios de la cuna y de los
agarre de los autorroscantes M2 en las ménsulas del USB-C; el giro de la bayoneta de la tapa de antena (sin cambio desde V2.2);
la carrier real (envolvente supuesta); el cable real de la pila; el ajuste del logo de TPU en su
grabado.
