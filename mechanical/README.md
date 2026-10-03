# Mecánica vigente — TresVizo V2.2

**Abrir [TresVizo-V2.2.FCStd](v2.2/generated/TresVizo-V2.2.FCStd) con FreeCAD**, o
`v2.2/view_v2_2.py` para verlo con colores. Generado y comprobado con FreeCAD 1.1.

| Carpeta / archivo | Uso |
| --- | --- |
| [v2.2](v2.2/README.md) | **Vigente.** Montaje, criterio de diseño, parámetros y límites. |
| [v2.2/generated/stl](v2.2/generated/stl/) | Imprimir: seis piezas del receptor. |
| [v2.2/generated/step](v2.2/generated/step/) | STEP por pieza para otros CAD, en posición cerrada. |
| [v2.2/SCREW-BOM.md](v2.2/SCREW-BOM.md) | Compra: 15 tornillos y el inserto del jalón. Los dos del IMU, avellanados. |
| [v2.1](v2.1/README.md) | Anterior. Se conserva como estaba. |
| [option-oem-dome](option-oem-dome/README.md) | **Otra posibilidad, no una V3:** antena de topografía ArduSimple dentro de un domo. Es para V2.1 (Ø69): no está adaptada a V2.2. |
| [v2](v2/README.md) | Anterior a V2.1. |
| [AUDITORIA-V1.md](AUDITORIA-V1.md) | Por qué se rehízo la carcasa desde cero. |
| [referencias](referencias/) | Cotas de los componentes comprados y datum del BMI088. |

## Qué cambió de V2.1 a V2.2

| | V2.1 | V2.2 |
| ---: | ---: | ---: |
| Diámetro exterior | 69 mm | **79 mm** |
| Altura, del asiento del jalón a la cara de la antena | 136.9 mm | **156.9 mm** |
| Panel frontal | 66° × 58 mm | **72° × 96 mm**, con OLED 0.96" y botón metálico de 12 mm |
| Interior | trineo atornillado a la base | **respaldo ranurado en el tubo**; todo se amarra con bridas |
| IMU | repisa del trineo, con los agujeros en el eje (el chip quedaba ~5 mm fuera) | **plataforma incrustada en la tapa**, con el chip en el eje |

V2.1 no se modificó, para no perder la referencia; imprimir V2.2.

## Regenerar

```sh
python3 mechanical/v2.2/regenerate.py
```

Localiza FreeCAD solo, también en macOS. Comprueba sólidos, mallas,
interferencias, el paquete contra el respaldo, la entrada de las tapas de panel
con todo montado, el chip del IMU en el eje, las uñas de la plataforma y la
alineación de los seguros, y devuelve código distinto de cero si algo falla.

## Estado

**Nada de V2.2 se ha impreso ni ensayado.** La geometría es coherente en CAD; eso
no es validación. Antes de imprimir la plataforma del IMU hay que medir en la
placa real dónde está el chip (ver el README de V2.2). Sigue un pendiente heredado
de V2: **el inserto del jalón no cabe por ninguna de las dos aberturas de su
alojamiento**; el README de V2.2 propone pausar la impresión de la base para
meterlo.
