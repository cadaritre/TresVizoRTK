# TresVizo V1 — prototipo de taller

Abrir **[TresVizo-V1.FCStd](generated/TresVizo-V1.FCStd) con FreeCAD 1.0.2**. El archivo contiene geometría propia y tres carpetas: **Para imprimir**, **Tornillería para comprar** y **Componentes**. La plantilla del BMI088 es una herramienta oculta, no parte del conjunto instalado. Seleccionar una carpeta/pieza y pulsar espacio alterna su visibilidad.

Fuente de V1: `build_v1.py` + `parameters.json`, derivados del generador del panel y del A5 conservado en [sources](../sources/README.md). Este paquete sustituye las exportaciones anteriores para el primer prototipo completo. [Resultado breve y verificaciones](../../docs/INTEGRATION_REVIEW.md) · [Lista de compra](../MECHANICAL_BOM.md).

## Archivos para fabricar

- [STL](generated/stl/): diez piezas permanentes y una plantilla; una unidad de cada archivo, mm, orientadas sobre Z=0.
- [STEP completo](generated/TresVizo-V1-assembly.step): montaje con envolventes comerciales; estas no se fabrican.
- [STEP de piezas impresas](generated/TresVizo-V1-print-parts.step) y [STEP individuales](generated/step/).
- [Validación CAD](generated/validation.json), [validación de exportaciones](generated/exports.json).

Los dos difusores requieren material translúcido; los otros ocho elementos son estructurales. Punto de partida: PETG, boquilla 0.4 mm, capa 0.2 mm, cuatro perímetros y relleno reforzado en alojamientos. Usar el perfil comprobado de la impresora. No se incluye G-code ni se ha hecho laminado específico.

| Pieza | Orientación del STL y soportes a revisar |
| --- | --- |
| Cuerpo | Boca inferior sobre cama; brim y soporte local en puente frontal. |
| Chasis/base | Base sobre cama; soportes accesibles en ventana posterior del inserto, repisas y retenes de placas. |
| Cuna/IMU/power | Vertical, sobre el pie de bandeja inferior; brim y soportes bajo asiento IMU y repisas. No poner soportes dentro de pilotos/ranuras estrechas. |
| Tapa | Plano de apoyo de antena sobre cama; taladros de antena verticales. |
| Panel | Borde inferior sobre cama; brim, soporte local bajo cuna USB y cartucho. |
| Prensa IMU | Cara del asiento sobre cama, alojamientos de tuerca hacia arriba. |
| Actuador/cartucho/difusores | Respaldo sobre cama; revisar pequeñas pestañas. |
| Plantilla | Orientación heredada del A5; reutilizable y retirada antes del cierre. |

## Montaje validado en CAD

FRONT sigue siendo **+Y**; Z es el eje del jalón. Las direcciones siguientes son globales. Los movimientos se ensayaron en ambos sentidos por reversibilidad, a pasos de 1 mm; botón a 0.05 mm. Las bridas se cortan para servicio y se sustituyen.

1. **Base e inserto, antes de electrónica.** Colocar tres tuercas M3 en bolsillos inferiores, sujetándolas durante el primer roscado. Introducir McMaster 90611A121 desde atrás (−Y), elevado 16 mm; centrar y bajar. Barril hacia abajo, brida arriba. Atornillar tres M3×8 desde arriba; hay paso de llave Ø3×35 mm. El barril termina a ras de Z0. Las tuercas quedan encerradas al apretar, no son clips a presión.
2. **IMU con cuna fuera.** Introducir prensa con dos tuercas M2.5 desde +Y hacia −Y; colocar BMI088, alinear con plantilla y apretar los dos M2.5×12 alternadamente. Retirar plantilla hacia +Z. Conservar el [procedimiento de datum A5](../sources/a5/IMU-ALIGNMENT.md). No usar espuma ni bridas en el IMU.
3. **Batería y placas de la cuna.** Introducir batería desde +Y sin comprimirla; sacar su cable por el canal superior lateral. Montar microSD y ambos módulos power desde atrás. PowerBoost sin USB-A, dos bridas por bandeja; microSD, dos bridas. Mantener cabezas de brida junto a las placas de soporte y dentro del cilindro de paso Ø61 mm; cortar sobrantes.
4. **Placas del chasis.** UM980 entra desde +Y, sobre dos apoyos de borde y con dos bridas. Tiny entra desde arriba por sus guías, con una brida por ranuras; conserva posición original. Tiny-Adapter entra desde +Y, con una brida, FPC original y conexión accesible. No apretar bridas sobre conectores o componentes altos; usar lámina aislante fina en apoyos de placas expuestas.
5. **Cuna cargada.** Presentarla desde −Y y deslizar hacia +Y hasta las guías; cerrar con dos M3×20. Montar las tuercas cautivas de cierres. Comprobar que el pack queda libre de puntas de tornillo.
6. **Cuerpo.** Panel y tapa fuera; arnés/coaxial flexibles recogidos fuera del recorrido. Bajar el cuerpo desde arriba: el paso interior Ø61.9 mm atraviesa el núcleo recortado a Ø61 mm. Fijar con dos M3×8 laterales opuestos en X. Los dos orificios heredados sin tornillo pueden sellarse con silicona neutra removible.
7. **Arneses y panel.** Con cuerpo colocado y aberturas superior/frontal libres, tender coaxial y corredores power/datos/USB según CAD y [WIRING](../../hardware/power-modules/WIRING.md). El coaxial se alimenta flexible después del cuerpo; su reserva curva R10 no debe intentar atravesar rígida el cuello. Montar USB con dos M2×5 diagonales sobre cuatro apoyos; actuador desde atrás, cartucho con lengüeta izquierda y un M3×8 derecho. Colocar LED/difusores; retener difusores con silicona neutra removible. Guiar luz CHG con fibra/guía óptica flexible Ø2 mm. Conectar dejando lazo de servicio, presentar panel desde +Y y cerrar dos M3×8.
8. **Tapa/antena.** Con tapa fuera, fijar antena con tres M2.5×8 desde abajo; pasar coaxial por Ø16 y conectar sin torsión. Colocar desde arriba y cerrar dos M3×8. Antena e inserto siguen centrados en X=Y=0.

Para servicio: quitar panel y tapa, desconectar y retirar arneses flexibles del paso, quitar los dos cierres laterales y subir el cuerpo. Sacar los M3×20 y retirar la cuna hacia −Y; batería hacia +Y, power hacia −Y. Cambiar batería requiere abrir el cuerpo y retirar cuna: no se fuerza por la ventana del panel. Para extraer el inserto, vaciar el chasis y revertir el paso 1.

## Bandejas universales

No utilizan un patrón fijo de agujeros de PCB. Apoyo plano aislante, tope inferior y dos bridas por módulo; abiertas lateralmente para variaciones.

| Zona | Envolvente nominal ancho × fondo × alto | Alternativa comprobada, a menor fondo |
| --- | --- | --- |
| PowerBoost 1000C sin USB-A | 23 × 10 × 45 mm | 26 × 8 × 47 mm |
| SparkFun Soft Power Switch Mk2 | 25.4 × 10 × 25.4 mm | 27 × 8 × 27 mm |

Son combinaciones de volumen comprobadas, no dimensiones máximas independientes que se puedan sumar. La holgura nominal a la placa de respaldo es 0.4 mm. El recorrido USB exterior conserva setback de 1.2 mm y admite el sobremolde compacto comprobado de 13 × 5.5 mm; no equivale a cualquier sobremolde de mercado.

## Reproducción

Desde la raíz del repositorio:

```sh
zsh mechanical/v1/regenerate.sh
```

Usa el Python instalado de FreeCAD **1.0.2**, regenera primero A5+panel en `.cache/mechanical-v1/baseline/` (raíz del repositorio), construye V1, exporta y valida. Finaliza con error si la geometría o exportaciones fallan. No escribe el A5 original. Para guardar colores y subcarpetas nativos, ejecutar `present_v1.py` en la consola Python de esa misma versión, usando `exec(compile(...), {'__file__': ruta})`; no inyectar un `GuiDocument.xml` de otra versión.

Las envolventes comerciales son referencias simplificadas y la rosca se representa sin hélice. La simulación es nominal y discreta, no una prueba física de resistencia. Las comprobaciones físicas están limitadas a siete en el informe breve.
