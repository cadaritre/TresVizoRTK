# Mecánica vigente — TresVizo V2.2

**Abrir [TresVizo-V2.2.FCStd](v2.2/generated/TresVizo-V2.2.FCStd) con FreeCAD**, o
`v2.2/view_v2_2.py` para verlo con colores. Generado y comprobado con FreeCAD 1.1.

| Carpeta / archivo | Uso |
| --- | --- |
| [v2.2](v2.2/README.md) | **Vigente.** Montaje, criterio de diseño, parámetros y límites. |
| [v2.2/generated/stl](v2.2/generated/stl/) | Imprimir: cinco piezas rígidas y dos bandas de TPU. |
| [v2.2/generated/step](v2.2/generated/step/) | STEP por pieza para otros CAD, en posición cerrada. |
| [v2.2/SCREW-BOM.md](v2.2/SCREW-BOM.md) | Compra: 15 tornillos, la tuerca de latón del jalón y el conector de carga JST-XH. Los dos del IMU, avellanados. |
| [AUDITORIA-V1.md](AUDITORIA-V1.md) | Por qué se rehízo la carcasa desde cero. |
| [referencias](referencias/) | Cotas de los componentes comprados y datum del BMI088. |

## Qué cambió de V2.1 a V2.2

| | V2.1 | V2.2 |
| ---: | ---: | ---: |
| Diámetro exterior | 69 mm | **64 mm** (67.4 con las bandas de TPU) |
| Altura, del asiento del jalón a la cara de la antena | 136.9 mm | **129.9 mm** |
| Batería | LiPo 955565 en el trineo | **18650 detrás del respaldo** |
| Panel frontal | 66° × 58 mm, con USB-C | **86° × 83 mm**, con OLED 0.96", botón metálico de 12 mm y conector de carga JST-XH |
| Rosca del jalón | inserto de McMaster con brida: solo entraba pausando la impresión | **tuerca hexagonal 5/8"-11 de latón**, metida por dentro de la base |
| Panel auxiliar | sí | **no** |
| Interior | trineo atornillado a la base | **respaldo ranurado en el tubo y cuatro toalleros**; todo se amarra con bridas |
| IMU | repisa del trineo, con los agujeros en el eje (el chip quedaba 5.65 mm fuera) | **plataforma incrustada en la tapa**, con el chip en el eje |
| Bayonetas | entraban en tres posiciones | **una sola posición** |
| Protección | — | **bandas de TPU** arriba y abajo |

Las versiones anteriores (V2, V2.1 y la opción del domo para V2.1) se quitaron
del repositorio el 04-10-2026. Siguen en el historial de git: la última vez que
están completas es el commit `94f00f9`.

## Regenerar

```sh
python3 mechanical/v2.2/regenerate.py
```

Localiza FreeCAD solo, también en macOS. Comprueba sólidos, mallas,
interferencias, el paquete y la 18650 en el respaldo, los toalleros, la entrada
de la tapa del panel con todo montado, los pilotos del IMU, las uñas de la
plataforma, las bayonetas indexadas, la alineación de los seguros, la tuerca
del jalón con sus retenes, el bolsillo del JST y los tornillos bajo las bandas,
y devuelve código distinto de cero si algo falla.

## Estado

**Nada de V2.2 se ha impreso ni ensayado.** La geometría es coherente en CAD; eso
no es validación. Antes de imprimir la plataforma del IMU hay que medir en la
placa real dónde está el chip (ver el README de V2.2), y medir la tuerca del
jalón y el header JST que se compren: el modelo usa las medidas de norma y del
plano de JST.
