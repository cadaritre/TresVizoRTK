# TresVizo V2.1 — más grande, trineo rígido y centrado, seguros que sí coinciden

Revisión de [V2](../v2/README.md) pedida por el propietario después de probarla:
15 mm más ancha, 30 mm más alta, un trineo que no se dobla ni se descentra y
los seguros de la bayoneta alineados de verdad.

**Nada de V2.1 se ha impreso ni ensayado.** La geometría es coherente en CAD y
pasa las comprobaciones automáticas; eso no es validación.

## Qué cambió frente a V2

| | V2 | V2.1 |
| --- | ---: | ---: |
| Diámetro exterior | 54 mm | **69 mm** |
| Altura del cuerpo | 106.9 mm | **136.9 mm** |
| Largo útil interior | 84 mm | **114 mm** |
| Trineo | hoja de 3 mm, dos pestañas, arriba libre | **pie atornillado, cuatro pestañas, perfil en U, arriba centrado por la tapa** |
| Seguros de la bayoneta | desalineados al cerrar | **alineados** |
| Sentido de cierre | la tapa cerraba al revés que la base | **las dos en sentido horario** visto desde arriba |
| Sitio sobre el IMU para el coaxial | 4.9 mm | **18.4 mm** |
| Material | 101 cm³ | 187 cm³ |

## El trineo

En V2 el trineo era una hoja de 3 mm llena de ranuras, sujeta solo por **dos
pestañas** con juego y libre por arriba. Se doblaba con la mano y quedaba donde
cayera.

| Problema | Solución en V2.1 |
| --- | --- |
| Dos pestañas con juego | **Pie horizontal** que apoya plano en el piso de la base y se **atornilla con dos M3**, por la cara +Y entre las alas. Además, **cuatro pestañas** en sus ranuras. |
| Hoja de 3 mm | Placa de **4 mm** con **dos alas** en la cara +Y (sección en U) y **cartelas** entre pie y placa por la cara −Y. |
| Arriba quedaba libre | La repisa del IMU es un **disco** del diámetro del cuello de la tapa menos **0.3 mm**, con chaflán. El **cuello de la tapa baja 15 mm** hasta rodearla y lleva chaflán de entrada. Al cerrar, la tapa centra el extremo superior del trineo. El centrado es un cono, así que no depende del ángulo. El disco tiene una **muesca en +Y** para el coaxial y los cables del IMU. |
| El espárrago del jalón podía tocar el trineo | Hueco libre de radio 10.5 en el pie y en el canto de la placa. |

Rigidez fuera del plano, calculada sobre el CAD con el mismo material:

- **Inercia de la sección:** de 11.8× (entre filas de ranuras) a 33× (en una
  fila).
- **Punta de la placa como voladizo libre:** de 6.7× a 18.7×. Ya cuenta que la
  placa de V2.1 es más larga.
- Con la tapa puesta, además, el extremo superior queda sujeto.

Son cuentas, no un ensayo.

**La placa sigue desplazada del eje a propósito.** La batería va contra la cara
−Y y queda centrada, porque es lo único que pasa por el collar de la bayoneta.
Lo que tiene que quedar en el eje es el IMU, y ahí está, con su marca pasante y
±1.5 mm de ajuste.

## El IMU bajó 15 mm

El coaxial de la HA-901A baja por el eje, justo encima del IMU. En V2 quedaban
4.9 mm para el conector y era imposible meterlo. En V2.1 la zona de batería mide
87 mm (la batería ocupa hasta 68 mm más su apoyo) y la del IMU 27 mm, con la
misma altura total. Sobre el IMU quedan **18.4 mm**, sitio para un SMA macho
acodado. De ahí el cable va a la muesca +Y de la repisa y baja al UM980.

## Bayoneta y seguros

**Fallo de V2:** base y tapa se dibujaban en la posición de **entrada**. Al cerrar
giran **28.7°**, no 30: la entrada de la ranura tiene 2° de más y la holgura
suma 0.7. El barreno del seguro de cada una acababa a 28.7° del que tiene el
tubo y el tornillo no entraba. Lo confirmé sobre los STEP de V2.

**En V2.1:**

- Base, trineo y tapa se dibujan **cerrados**, con los dientes contra el fondo
  de su ranura. El seguro de las tres piezas cae a 193°, donde está el del tubo.
- La ranura de arriba es la **simétrica** de la de abajo. Las dos uniones cierran
  girando la pieza de arriba **en sentido horario** visto desde arriba, el mismo
  sentido en que el equipo se enrosca al jalón. Enroscarlo sujetándolo por la
  tapa aprieta la bayoneta en vez de abrirla.
- Los pilotos de los seguros son ciegos y el refuerzo de la tapa crece a 7.5 mm.
  Los dos seguros son **M3×12**, con 7.4 mm de rosca.

## Qué cabe

Todo lo que va en el trineo tiene que pasar por el collar de la bayoneta
(radio 28.5), porque el tubo baja por encima al montar.

| | Cota | Holgura en el collar |
| --- | --- | ---: |
| Trineo | radio máximo 27.9 | 0.6 mm |
| Batería 955565 nominal | 9.5 × 55 × 65 | **0.56 mm** en las esquinas |
| Batería, peor caso documentado | 10 × 55.5 × 68 | **0.29 mm** |
| Carrier UM980, entre las alas | 11 × 32 × 52 | 2.85 mm (hueco entre alas 41.8) |

La batería **cabe, pero justa**:

- Se amarra **a lo largo**, con bridas por las ranuras de ±6 o ±13 de la fila de
  debajo y de la fila superior. **Nunca rodeando su ancho**: en los cantos no
  queda sitio para una brida.
- Si la bolsa se hincha, no sale sin desmontar. Medir la batería real antes de
  imprimir.

## Montaje

1. Inserto del jalón en la base (ver el pendiente de abajo).
2. Trineo sobre la base: cuatro pestañas en sus ranuras y los **dos M3×10 del pie**,
   por la cara +Y. Van antes que las placas.
3. Batería contra la cara −Y, con bridas a lo largo. Placas en la cara +Y entre
   las alas.
4. Tubo desde arriba: dientes por las entradas, **girar en sentido horario visto
   desde arriba** hasta el tope y M3×12 del seguro de la base.
5. Tapa: el cuello recoge la repisa del IMU. Girar en sentido horario hasta el
   tope y M3×12 del seguro de la tapa.

Tornillos de los paneles: **M3×6 en el principal y M3×4 en el auxiliar, nunca más
largos.** Detrás del auxiliar está el canto de la batería. La lista completa
está en [SCREW-BOM.md](SCREW-BOM.md).

## Pendiente que sigue impidiendo el montaje

Viene de V2 y **no se tocó**: la brida del inserto del jalón (Ø36.5) no pasa por
ninguna de las dos aberturas de su alojamiento (Ø18). Hay que decidir cómo se
mete antes de imprimir la base.

## Piezas

| Archivo | Qué es |
| --- | --- |
| `01-threaded-base.stl` | Base: inserto 5/8", ranuras de las pestañas y pilotos del pie. |
| `02-logo-tube.stl` | Tubo: logo grabado, dos paneles, accesorios, líneas de diseño. |
| `03-antenna-cap.stl` | Tapa: HA-901A por fuera, cuello largo con chaflán de entrada. |
| `04-universal-sled.stl` | Trineo: pie, placa en U, rejilla y repisa en disco. |
| `05-panel-cover.stl` | Panel principal: USB, botón y dos LEDs. |
| `06-aux-panel-cover.stl` | Panel auxiliar: USB-C hembra. |

## Regenerar

```sh
python3 mechanical/v2.1/regenerate.py
```

Localiza FreeCAD y funciona también en macOS. Hace, en este orden:

1. Recoloca el logo.
2. Elige la tornillería.
3. Construye y exporta las piezas.
4. Comprueba sólidos, mallas e interferencias.
5. Ejecuta `capacity_check.py`: capacidad, centrado, rigidez, seguros, paredes
   entre tornillos (mínimo 1.2 mm), tornillos de panel y sitio sobre el IMU.

Si algo falla, sale con código distinto de cero. Los resultados quedan en
[`generated/capacity.json`](generated/capacity.json).

Para verlo con colores: abrir `view_v2_1.py` desde FreeCAD.

## Límites

- **Sin imprimir ni ensayar.** Sin datos de resistencia, ajuste, temperatura ni
  estanqueidad.
- Las holguras de 0.3 (pestañas y repisa) suponen una impresora que saca las
  cotas a ±0.1. Si la tuya cierra los huecos, sube `pestanas.holgura` e
  `imu.holgura_cuello`.
- La captura del inserto sin tornillos, la bayoneta impresa y el roscado en
  plástico siguen sin ensayo, igual que en V2.
- La antena sigue siendo la HA-901A atornillada por fuera. La opción con antena
  de topografía dentro de un domo está en
  [`../option-oem-dome`](../option-oem-dome/README.md).
