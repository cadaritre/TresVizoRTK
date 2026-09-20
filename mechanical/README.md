# Mecánica — A5 simplificado

**Resultado de integración posterior:** ver [INTEGRATION_REVIEW.md](../docs/INTEGRATION_REVIEW.md). El panel comercial se actualizó al `Chassis` actual en una [variante derivada](integration-review/README.md); el maestro A5 se conserva. Se detectó bloqueo del desplazamiento axial del cuerpo sobre el chasis/cuna, además de pendientes de power y retención del jalón. **No liberar la impresión del receptor completo con la secuencia anterior.** [BOM conjunta: 21 tornillos definidos, total final abierto](MECHANICAL_BOM.md).

Abrir [A5/TresVizo-A5.FCStd](A5/TresVizo-A5.FCStd). Es el **único maestro activo**, con geometría embebida; no necesita macros ni archivos de `legacy`.

La revisión del 20 de septiembre reduce el conjunto definido a **seis piezas impresas permanentes, una plantilla reutilizable y cero arandelas sueltas**. Se integraron base/bandeja y cuna/asiento IMU; guías impresas sustituyen dos tornillos de la cuna y la tapa usa dos cierres. Se conservaron la silueta, el símbolo 3 + hexágono y la antena externa HA-901A con su paso SMA y tres tornillos.

Para cierres, estructura e IMU: **15 tornillos y 12 tuercas comunes**. La comparación completa es 23→15 tornillos: el CAD anterior dibujaba 17 pero omitía los seis cierres de tapa/panel. Esta cuenta excluye fijaciones aún no definidas de otras PCBs e inserto del jalón.

- [Impresión, tornillería y montaje](A5/PRINT-AND-ASSEMBLY.md): cambios, BOM, orientación y soportes locales.
- [STL orientados para impresión](A5/print/): seis piezas permanentes y plantilla; exportaciones independientes del maestro.
- [Centrado del BMI088](A5/IMU-ALIGNMENT.md): ajuste, plantilla y límites.
- [Interfaz para integrar la PCB](A5/PCB-INTERFACE.md): marco de coordenadas y nombres nuevos.
- [Dimensiones investigadas](A5/COMPONENT-DIMENSIONS.md): fuentes y datos que siguen sin confirmarse.

Se comprobaron **44 sólidos válidos, siete mallas STL cerradas, interferencias, ajuste IMU e inserción de la cuna**. La revisión incluye superficies de apoyo y rampas para facilitar FDM; quedan soportes locales descritos en la guía. No se ha imprimido, laminado con una impresora específica ni probado la resistencia del conjunto.

La alimentación vigente utiliza módulos comerciales. El maestro conserva su panel provisional; las perforaciones de USB/botón/luces y los despejes se encuentran en la variante derivada de integración. El inserto del jalón y varias fijaciones de placas siguen pendientes. El modelo es un prototipo, **no una liberación final de fabricación ni una certificación IP**.

`legacy/`, excluido de Git, conserva revisiones y respaldos anteriores. Los scripts de trabajo no son dependencias del maestro. No se ejecutaron commits ni push.
