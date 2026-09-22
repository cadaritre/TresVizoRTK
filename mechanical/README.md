# Mecánica vigente — TresVizo V2

**Abrir [TresVizo-V2.FCStd](v2/generated/TresVizo-V2.FCStd) con FreeCAD.** Generado
y comprobado con FreeCAD 1.1.

| Carpeta / archivo | Uso |
| --- | --- |
| [v2/generated/stl](v2/generated/stl/) | Imprimir: seis piezas del receptor. |
| [v2/generated/step](v2/generated/step/) | STEP por pieza para otros CAD. |
| [v2](v2/README.md) | Montaje, criterio de diseño, parámetros y límites. |
| [v2/BOM-TORNILLERIA.md](v2/BOM-TORNILLERIA.md) | Compra: 11 tornillos, 2 tuercas y el inserto del jalón. |
| [AUDITORIA-V1.md](AUDITORIA-V1.md) | Por qué se rehízo la carcasa desde cero. |
| [referencias](referencias/) | Cotas de los componentes comprados y datum del BMI088. |

## Qué cambió respecto de V1

| | V1 | V2 |
| --- | ---: | ---: |
| Diámetro exterior | 74 mm | **54 mm** |
| Altura del cuerpo | 164 mm | **106.9 mm** |
| Material | 231 cm³ | **101.5 cm³** |
| Piezas impresas | 10 + plantilla | **6** |
| Tornillos | 19 | **11** |
| Tuercas | 13 | **2** |

Menos de la mitad del plástico y 57 mm más corto. El interior dejó de tener
alojamientos con forma de cada componente: es una rejilla de anclaje universal,
de modo que cambiar un módulo no obliga a reimprimir nada. El razonamiento está
en [la auditoría](AUDITORIA-V1.md).

## Regenerar

```sh
python mechanical/v2/regenerate.py --dxf "ruta/al/LOGO.dxf"
```

Localiza FreeCAD solo. Comprueba que cada pieza sea un único sólido, que las
mallas cierren y que no haya interferencias, y devuelve código distinto de cero
si algo falla.

## Estado

**Nada de V2 se ha impreso ni ensayado.** La geometría es coherente en CAD; eso no
es validación. Los pendientes concretos están en [v2/README.md](v2/README.md), y
uno de ellos impide el montaje tal como está: **el inserto del jalón no cabe por
ninguna de las dos aberturas de su alojamiento**.
