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
