# Carcasa V2.3 (exploratoria): chasis deslizable para la placa principal v0.2

> **Estado:** geometría generada con scripts y comprobada en FreeCAD contra la placa v0.2 real
> (STEP con sus componentes), sus clavijas enchufadas y la placa panel-usb.
> **No se ha impreso ni montado nada.** Vive en la rama `hw/main-board-kicad`, fuera de `main`,
> igual que la placa principal. Resultado de la comprobación en [Verificaciones](#verificaciones).

Parte de la V2.2 de `main` (94f00f9: Ø64 × 130, tuerca 5/8 de latón, panel con OLED, botón de
12 mm y dos LEDs, plataforma del IMU en el cuello de la tapa, bandas de TPU). El exterior no
cambia. Cambian el interior y la tapa del panel, para la placa principal v0.2
([../../hardware/main-board](../../hardware/main-board/README.md)).

## Qué cambia frente a V2.2

| Pieza | Cambio |
| --- | --- |
| 02 Tubo | Fuera el respaldo de amarre y los toalleros. Dos pares de **nervios guía** (x ±23.6 hacia la pared, z 30–95) donde corren los rieles del chasis; dos **topes** sobre el collar inferior (z 15.95–17); **cuna de la 18650** en la pared trasera: dos nervios flexibles con labios y una repisa con hueco para el cable |
| 08 Chasis (nueva) | Marco que se arma **fuera del tubo**: la placa corre en sus rieles y se atornilla por H1/H2; la carrier del UM980 queda presa detrás; el conjunto entra por arriba entre los nervios |
| 01 Base | Ranura de 3 mm bajo J102 (x −21.5…−13.5, y 2.5…8.5) para el cable de la batería |
| 05 Tapa del panel | Hueco del USB-C de la placa panel-usb (12.8 × 7.0, R1.2, en z 93.2) y dos ménsulas donde se atornilla esa placa (M2 × 5 autorroscantes); fuera el bolsillo del JST-XH. El botón de 12 mm y los LEDs no cambian |

Base, tapa de antena, plataforma del IMU y bandas son las de V2.2.

## Cómo se arma (sin tornillos dentro del tubo)

1. **18650 en su cuna.** Con la tapa de antena quitada, la celda baja por el collar de arriba
   **corrida 3.2 mm hacia el frente** (eje en y −16.4). En su posición final no cabe: llega a
   r 28.9 y el collar deja r 26. Los nervios de la cuna, a todo lo alto, la guían sin tocarla.
   - Ya entera bajo el collar (fondo bajo z 42.9), se empuja hacia atrás y entra a presión en los
     labios, que solo van de z 26 a 42. Los nervios se abren ~1.5 mm.
   - El cable baja por el hueco de la repisa y sale por un **canal a ras del piso hacia −X**, que
     rodea el retén de la tuerca. De ahí sigue por el piso, sube junto al collar y pasa por fuera
     del riel −X, en x −27, z 24, hasta J102.
   - Con el chasis puesto, la carrier (0.4 mm delante) y la lengua (arriba) no la dejan salir.
2. **Carrier en el chasis, fuera del tubo.** Entra por el frente (sin la placa puesta) hasta los
   labios traseros de sus dos ranuras y apoya en sus dos pisos.
3. **Placa en el chasis, fuera del tubo: entra POR ABAJO.** Sube por los rieles y se atornilla
   desde el frente con dos **M2.5 × 8 autorroscantes** a los brazos de H1 y H2.
   - Por arriba no entra: el módulo ESP32 (U201) llega a x 22.19 y chocaría con la lengüeta +X
     de arriba; J102 también rozaría la −X.
   - Desde abajo U201 se detiene en z 69.9, antes de esa lengüeta.
   - La placa, delante, y dos topes arriba dejan la carrier presa.
4. **Cables** (con el chasis aún fuera): arnés de J301 a la carrier, coaxial al SMA de la carrier.
5. **Chasis al tubo.** Entra por arriba, con los rieles entre los nervios, hasta apoyar en los
   topes del collar inferior.
6. **Por abajo** (base quitada): batería a J102 (su cable pasa por fuera del riel −X; por debajo
   de z 30 no hay nervios), NTC opcional a J404. Base puesta.
7. **Arriba:** cable del IMU a J405 y coaxial a la plataforma. Al cerrar la tapa de antena, su
   cuello (z 99.41) queda 0.4 mm sobre el travesaño: el chasis no puede salir.
8. **Panel:** la placa panel-usb se atornilla a sus ménsulas, se enchufan OLED (J403), botón
   (J402), LEDs (J406) y USB (J502 ↔ J101) por la ventana, y se atornilla la tapa del panel.

## Geometría del chasis

Ejes de V2.2: z = eje del jalón hacia arriba, +Y = panel, +X a la izquierda mirando el panel.
Placa: x = 23 − u, z = 87.5 − v, dorso en y 1.5 y cara de componentes en y 3.1.

- **Rieles** en x ±23.3…25.2, z 17–99. Reciben los cantos de la placa con 0.15 mm por cara.
  - Lengüetas delanteras solo sobre las franjas sin componentes de la placa (u 0–2.5 y 43.5–46,
    v 0–48.5): en −X de z 39 a 87.5 y en +X solo de z 71 a 87.5, para que la placa entre por
    abajo sin que el módulo ESP32 las toque.
  - **El riel +X se corta en z 54–71, frente a la antena del ESP32.** Su tramo de abajo se une
    al brazo de H1 por detrás, con un enlace a 10 mm de la placa (x 9–16).
- **Travesaño** en z 95.8–99.0, y −2.4…1.2, bajo el cuello de la tapa. Su cara trasera deja pasar
  el coaxial (y −4.4).
- **Brazos de H1 (x 11.0, z 75.3) y H2 (−17.4, 83.8):** bajan del travesaño detrás de la placa.
  Llevan un saliente Ø6 con piloto Ø2.1 × 5.5.
- **Ranuras de la carrier** en sus cantos (x −21 y +11):
  - labios detrás de su PCB (y −10.6…−10.1);
  - pisos de 1 mm bajo su canto inferior (z 18);
  - topes sobre su canto superior: el de −X en el riel y el de +X bajo el brazo de H1.
  - La del lado +X va de z 17 a 50, lejos de la antena.
- **Lengua sobre la 18650** (x 3…9, z 92–99): no la deja subir si el equipo se pone de cabeza.
  Va a la derecha del SMA para no estorbar el coaxial.
- Todo el chasis queda en **r ≤ 25.5** para pasar el collar de r 26.

Los valores salen de [parameters.json](parameters.json) (bloques `chasis`, `cuna_18650` y
`panel.usb_c`); las posiciones de la placa, de la carrier y de la panel-usb, de
`hardware/main-board/cad/placement.json`.

## Supuestos que hay que medir antes de imprimir

- **Carrier BDLX:** 32 × 52 × 11 mm en todo su largo, componentes hacia la placa, SMA arriba.
  BDLX no publica plano.
  - Medir su espesor real (sin el SMA), la posición del SMA y la de sus conectores GH8 y GH5.
  - Con la carrier a 0.4 mm de la placa, si sus conectores quedan en la cara de componentes no se
    pueden enchufar.
  - Corregir `chasis.carrier` y regenerar.
- **18650 protegida:** Ø18.6 × 69 mm. El chasis pasa a 0.4 mm de ella al entrar (lo fija la
  envolvente supuesta de 11 mm de la carrier). Si la carrier real es más delgada, la holgura crece.
- **Cable de la 18650:** se supone que sale por su extremo de abajo. Si sale por arriba, baja por
  el costado −X de la cuna.

## Impresión

Pensada para **MJF (PA12 o PA11)**: el chasis tiene salientes en varias direcciones y la repisa
de la cuna tiene un voladizo plano de unos 8 mm sobre la espiga de la base. En FDM, chasis y tubo
necesitan soportes. Tolerancias de MJF: ±0.3 mm. Las holguras de deslizamiento son de 0.2 a
0.3 mm: imprimir primero el chasis y un tramo de tubo y probar el ajuste.

## Regenerar

Requisitos: FreeCAD 1.1 (su Python).

```bash
cd mechanical/v2.3
export PYTHONPATH=/Applications/FreeCAD.app/Contents/Resources/lib
/Applications/FreeCAD.app/Contents/Resources/bin/python build_v2_3.py
/Applications/FreeCAD.app/Contents/Resources/bin/python export_v2_3.py
/Applications/FreeCAD.app/Contents/Resources/bin/python check_v2_3.py
```

`build_v2_3.py` genera `generated/TresVizo-V2.3.FCStd` y `model-index.json`. `export_v2_3.py`
genera los STL y STEP de las piezas impresas y comprueba mallas e interferencias entre ellas.
`check_v2_3.py` compara contra los STEP de `hardware/main-board/cad/` (placa con componentes,
clavijas, panel-usb, envolventes supuestas) y escribe `generated/check.json`.

## Verificaciones

Hechas el 05-10-2026 con FreeCAD 1.1.3 sobre los archivos de esta carpeta
([generated/check.json](generated/check.json), [generated/exports.json](generated/exports.json)).

| Comprobación | Resultado |
| --- | --- |
| Piezas | 8 sólidos válidos, un sólido por pieza; mallas STL cerradas, sin no-manifold ni autointersecciones |
| Choques entre piezas impresas en su posición final | 0 (límite 1 mm³ por pareja) |
| Choques con la placa v0.2 real (PCB y 110 componentes del STEP), las clavijas enchufadas con sus cables, la panel-usb, la carrier y su SMA, la 18650 y el coaxial | 0 mm³ |
| Chasis armado (chasis, placa y carrier) en el collar Ø52 | radio máximo 25.5 mm (límite 25.65 con 0.35 de holgura) |
| Plástico del chasis junto a la antena del ESP32 (x 16.8–26, z 54.2–70.2) | 0 mm³ |
| Holguras | chasis–tapa 0.41 (al cerrar), chasis–plataforma del IMU 0.91, chasis–base 1.09, chasis–18650 1.0, chasis–coaxial 0.5; carrier–18650 0.4 (supuesta) |
| Montaje paso a paso (`hardware/main-board/cad/check_montaje_v2_3.py`, de la otra sesión; tramos de 0.5–1 mm contra lo ya puesto) | Sobre b33f44a encontró 3 problemas, corregidos en esta versión: la 18650 no entraba recta (labios hasta z 81), la placa no entraba en los rieles (U201 contra las lengüetas +X) y el cable de la 18650 no salía del hueco de la repisa. Sin problema: carrier al chasis, chasis al tubo con la 18650 puesta, clavijas de abajo sin base, tapa del panel con todo lo suyo, plataforma del IMU. **Pendiente re-correrlo sobre esta versión** |
| Contactos intencionados (holgura 0) | pie de los rieles sobre los topes del collar; carrier sobre sus pisos; 18650 tangente a los labios de su cuna (se imprime así; la retención es geométrica, no por interferencia) |

**No verificado:** tolerancias de impresión; el recorrido de montaje paso a paso (solo la posición
final y el paso por el collar); el paso real de los cables (sobre todo el de la 18650 a J102); la
rigidez del chasis y de los nervios de la cuna; la carrier real (envolvente supuesta); que el
travesaño aguante el apriete de la tapa.
