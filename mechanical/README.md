# Mecánica — TresVizo V1

Paquete vigente para el prototipo completo: **[V1 / FreeCAD 1.0.2](v1/README.md)**. Conserva exterior, FRONT +Y, datum del BMI088 y ejes de antena/jalón. Resuelve paso del cuerpo, inserto metálico 5/8"-11, soportes power y servicio de los módulos.

- [Abrir TresVizo-V1.FCStd](v1/generated/TresVizo-V1.FCStd): carpetas para imprimir, tornillería y componentes.
- [STL para imprimir](v1/generated/stl/): diez piezas permanentes y una plantilla.
- [STEP completo](v1/generated/TresVizo-V1-assembly.step).
- [Montaje, orientación de impresión y regeneración](v1/README.md).
- [Resultado de integración](../docs/INTEGRATION_REVIEW.md) y [BOM: 19 tornillos, 13 tuercas](MECHANICAL_BOM.md).

La fuente de V1 es Python/FreeCAD en `v1/`, derivada del generador de `panel-modules/` y del [A5 original](A5/TresVizo-A5.FCStd), conservado byte a byte. Usar las exportaciones de V1 como juego completo; no mezclarlas con las del A5 o de la auditoría anterior.

El A5 y su documentación quedan como antecedente de forma exterior, arquitectura y referencias. La [revisión anterior](integration-review/README.md) documenta problemas que V1 resuelve. Ni esos archivos ni el generador actual dependen de `legacy/`.

Prototipo nominal comprobado en CAD; impresión física, resistencia y calibración topográfica posteriores. El resultado de las verificaciones y las siete comprobaciones físicas están en el informe de integración.
