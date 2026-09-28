# Mecánica vigente — TresVizo V2.1

**Abrir [TresVizo-V2.1.FCStd](v2.1/generated/TresVizo-V2.1.FCStd) con FreeCAD.**
Generado y comprobado con FreeCAD 1.1.

| Carpeta / archivo | Uso |
| --- | --- |
| [v2.1](v2.1/README.md) | **Vigente.** Montaje, criterio de diseño, parámetros y límites. |
| [v2.1/generated/stl](v2.1/generated/stl/) | Imprimir: seis piezas del receptor. |
| [v2.1/generated/step](v2.1/generated/step/) | STEP por pieza para otros CAD, en posición cerrada. |
| [v2.1/SCREW-BOM.md](v2.1/SCREW-BOM.md) | Compra: 13 tornillos, 2 tuercas y el inserto del jalón. |
| [option-oem-dome](option-oem-dome/README.md) | **Otra posibilidad, no una V3:** antena de topografía ArduSimple dentro de un domo, sobre V2.1. |
| [meridian3](meridian3/README.md) | **Otro producto, no una revisión del MeridianV:** receptor sencillo (ESP32-S3-Tiny + UM980 + HA-901A, power bank externo por USB-C). Ø54 con los arreglos de V2.1. |
| [v2](v2/README.md) | Anterior. Se conserva como estaba; sus fallos están corregidos en V2.1. |
| [AUDITORIA-V1.md](AUDITORIA-V1.md) | Por qué se rehízo la carcasa desde cero. |
| [referencias](referencias/) | Cotas de los componentes comprados y datum del BMI088. |

## Qué cambió de V2 a V2.1

| | V2 | V2.1 |
| ---: | ---: | ---: |
| Diámetro exterior | 54 mm | **69 mm** |
| Altura del cuerpo | 106.9 mm | **136.9 mm** |
| Trineo | hoja de 3 mm, dos pestañas, arriba libre | **pie atornillado, cuatro pestañas, perfil en U, centrado por la tapa** |
| Seguros de la bayoneta | desalineados al cerrar | **alineados**; lo comprueba `capacity_check.py` |
| Sentido de cierre | tapa al revés que la base | **las dos en sentido horario** |
| Sitio sobre el IMU para el coaxial | 4.9 mm | **18.4 mm** |
| Tornillos con largo definido | 11 | 13 |

**Fallos de V2 que siguen en su carpeta:**

- Base y tapa se dibujaron en la posición de entrada de la bayoneta. Al cerrar
  giran 28.7° y el tornillo del seguro ya no entra.
- El trineo se dobla y no queda centrado.
- El conector del coaxial de la antena no cabe sobre el IMU.
- Los tornillos de los paneles no tenían avellanado real y la lista permitía uno que pinchaba la batería.
- La lista de tornillería elegía tornillos más largos que sus pilotos.

V2 no se modificó para no perder la referencia; imprimir V2.1.

## Meridian3

Receptor aparte, más sencillo que el MeridianV: sin batería, IMU, microSD,
radio ni puerto auxiliar, y alimentado por un power bank externo por el USB-C
de la Tiny-Adapter. Tiene el diámetro de V2 (54) con los arreglos de V2.1:
bayoneta dibujada cerrada, las dos uniones en sentido horario, seguros
alineados, trineo con pie atornillado y anillo centrado por la tapa,
avellanados reales y tornillos que no pasan de sus pilotos.

**No cabe en la altura de V2 con un latiguillo coaxial: mide 150.6 mm.** Si
la antena trae SMA macho y se enrosca directa al carrier, se estima que
cabría en unos 105.6 mm, pero eso no está modelado. Todo el detalle está en
[meridian3/README.md](meridian3/README.md).

```sh
python3 mechanical/meridian3/regenerate.py
```

Nada del Meridian3 se ha impreso ni montado.

## Regenerar

```sh
python3 mechanical/v2.1/regenerate.py
```

Localiza FreeCAD solo, también en macOS. Comprueba sólidos, mallas,
interferencias, capacidad del trineo y alineación de los seguros, y devuelve
código distinto de cero si algo falla. La opción del domo se regenera aparte;
ver su README.

## Estado

**Nada de V2.1 ni de la opción del domo se ha impreso ni ensayado.** La
geometría es coherente en CAD; eso no es validación. Sigue un pendiente que
impide el montaje tal como está, heredado de V2: **el inserto del jalón no cabe
por ninguna de las dos aberturas de su alojamiento**.
