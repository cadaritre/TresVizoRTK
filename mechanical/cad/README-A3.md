# A3 — base imprimible para el jalón

La estructura del montaje se fabrica por impresión 3D. **Sólo se compran tornillos, tuercas y arandelas comerciales.** A3 elimina las tres placas, los ocho casquillos y el calce metálicos de A1/A2. Conserva la antena exterior y el recorrido coaxial de A2.

## Cómo se sujeta

1. La base impresa tiene un suelo de 4 mm y un alojamiento hexagonal integral de 24.25 mm entre caras. El hexágono impide que la tuerca 5/8-11 gire dentro de la base.
2. La tuerca comercial se introduce desde arriba. Un calce **impreso** completa el espacio sobre ella. Su espesor nominal es aproximadamente 0.5 mm; el generador permite adaptarlo a la altura de la tuerca comprada.
3. Una tapa impresa de 3.3 mm retiene la tuerca axialmente. Cuatro M4 × 30 avellanados atraviesan base, tapa y piso del bastidor; se cierran con arandelas y tuercas M4. Los apoyos están integrados en las piezas impresas y no necesitan casquillos.
4. Los cuatro M3 × 8 horizontales con tuercas cautivas sujetan carcasa y base. No presionan ni dañan la rosca del jalón.

La cara inferior Z=0 apoya sobre el hombro del jalón. El alojamiento hexagonal, la tapa y el suelo retienen la tuerca dentro del receptor. El apriete contra el hombro/collar del jalón fija el receptor al jalón; son uniones distintas. No se define aún un par de apriete o resistencia admisible del plástico.

## Rosca y espacio para la punta

Se adopta **5/8″-11 UNC**, la interfaz publicada por [Emlid para Reach RX](https://emlid.com/es/reachrx/). La denominación define diámetro y paso de rosca; no proporciona por sí sola una longitud saliente. El [plano general oficial del RX](https://files.emlid.com/docs/Reach%2BRX%2Bdrawing.pdf) no acota esa longitud. No se cambia la rosca ni se exige un adaptador especial.

La entrada tiene Ø17.2 de holgura y la tuerca comienza a Z=4. La cavidad continúa libre hasta **26.5 mm desde la cara de apoyo**, con un techo a Z=28 que separa la punta de la electrónica. Así no se utiliza el fondo como tope de apriete. Se comprobaron envolventes cilíndricas nominales Ø15.875 con salientes de 19, 20 y 25 mm; la mayor conserva 1.5 mm hasta el techo interior. Estas son comprobaciones geométricas, no una declaración de longitud universal ni ensayos de rosca o resistencia.

Como referencia externa concreta, [Goecke publica un adaptador topográfico de 5/8 con salientes roscados de 19 mm](https://goecke.de/index.php?cPath=174_92_114&cat=c114_Target-for-laser-scanning-Target-for-laser-scanning.html&language=en&page=2). La rosca efectiva disponible depende de la penetración en la tuerca; la geometría simplificada no incluye chaflanes de entrada ni filetes.

## Tornillería de la base

| Cantidad | Compra |
| --- | --- |
| 1 | Tuerca hexagonal estándar **5/8″-11 UNC**, acero; referencia dimensional [L.H. Dottie HN58](https://lhdottie.com/pdf/product-specification-sheet/HN58), no tuerca pesada ni acopladora. |
| 4 | Tornillos **M4 × 30 avellanados, 90°**, longitud total 30 mm; cabeza compatible con alojamiento Ø9. |
| 4 + 4 | Tuercas M4 y arandelas planas M4; envolventes del CAD AF7 × 3.2 y Ø9 × 0.8 respectivamente. |
| 4 + 4 | Tornillos M3 × 8 y tuercas M3 para las uniones horizontales heredadas. |

No hay piezas metálicas que mandar cortar, tornear o perforar. La lista corresponde al montaje inferior; no sustituye la futura tornillería de placas electrónicas o antena.

La HN58 publicada tiene AF 23.4188–23.8252 y altura 13.589–14.1986 mm. El calce impreso se calcula como `14.7 − altura real de la tuerca`; en ese intervalo mide aproximadamente 0.50–1.11 mm. El STL entregado representa el extremo de tuerca más alto. No forzar una pila demasiado alta apretando los M4.

## Archivos

- `TresVizo-case-A3.FCStd`: conjunto actual. Los grupos separan piezas impresas, tornillería y reservas electrónicas.
- `TresVizo-case-A3-MOUNT-SECTION.FCStd`: corte de revisión; no imprimir ese corte.
- `../exports/review-a3/`: STEP del conjunto y piezas; **13 STL de piezas impresas**. Los bloques electrónicos y los herrajes no se exportan como STL.
- `case-a3.json` y `build_case_a3.py`: cotas y generador, con A2 como origen. La hoja del FCStd es informativa y no dirige la geometría.
- `../exports/review-a3/printed-mount-a3.png`: corte y despiece del montaje.

Para la base, colocar la cara Z=0 en la cama; para tapa y calce, sus caras planas inferiores. El hueco del bastidor incorpora un techo con puente de 17.2 mm: revisar el laminado y el soporte/puente antes de imprimir. Ensayar primero el alojamiento de la tuerca y el montaje inferior con masa de prueba. La geometría no determina material, adhesión entre capas, resistencia a flexión, fluencia o par de apriete seguro.

## Verificación y límites

Se verifican sólidos individuales, intersecciones entre piezas, mallas cerradas, inserción vertical de la tuerca principal y de las cuatro tuercas radiales, paso de las tres envolventes de espárrago y conservación del espacio coaxial Ø5 de A2. Los resultados numéricos quedan en `cad-checks.json`; `reopen-checks.json` comprueba reapertura nativa/STEP. Las entradas de tuercas se ensayan geométricamente antes de cerrar la tapa y colocar el bastidor.

La estructura es un prototipo pendiente de prueba física de ajuste y carga. Conserva los pendientes de A2: patrones de algunas placas/antena, conectores y fijación/sellado del coaxial, batería y alimentación. **El encendido tampoco está resuelto:** `LatchReserve` sólo reserva espacio al módulo biestable; no hay un pulsador exterior ni circuito de alimentación verificado. No confundir la ausencia de botón de medición con la necesidad de resolver el encendido.

Regenerar desde la raíz del repositorio:

```sh
PYTHONPATH=/Applications/FreeCAD.app/Contents/Resources/lib \
  /Applications/FreeCAD.app/Contents/Resources/bin/python mechanical/cad/build_case_a3.py
PYTHONPATH=/Applications/FreeCAD.app/Contents/Resources/lib \
  /Applications/FreeCAD.app/Contents/Resources/bin/python mechanical/cad/render_case_a3.py
```
