# Integración resuelta — TresVizo V1

**READY FOR FIRST FULL PROTOTYPE PRINT: YES.** `scope_ready_for_first_full_prototype_print = true`.

Paquete de trabajo: [FreeCAD V1](../mechanical/v1/generated/TresVizo-V1.FCStd), [STEP completo](../mechanical/v1/generated/TresVizo-V1-assembly.step), [STL](../mechanical/v1/generated/stl/), [montaje e impresión](../mechanical/v1/README.md). Abrir con **FreeCAD 1.0.2**. Fuente reproducible: Python/FreeCAD y parámetros en `mechanical/v1/`; A5 original conservado byte a byte.

| Problema | Solución | Cambio geométrico | Validación |
| --- | --- | --- | --- |
| El cuerpo no podía atravesar el conjunto | Paso axial desde arriba | Alesado interior Ø61.9 hasta Z57 y recorte periférico del núcleo a Ø61; sin cambiar exterior | Extracción +Z 180 mm con núcleo cargado, panel y tapa retirados |
| Inserto libre, sin retención real | McMaster 90611A121, brida atornillada, barril hacia abajo | Asiento a Z9.525; 3 M3×8, 3 tuercas cautivas, ranuras radiales, ventana posterior y pozo de llave | Entrada posterior a Z+16, descenso, acceso a tres cabezas; bloqueo axial y de giro con fijaciones |
| Módulos power sin montaje | Dos bandejas abiertas integradas en la cuna | Respaldo aislante, tope inferior y dos bridas por módulo; sin patrón de PCB | Envolventes nominales y alternativas; extracción hacia −Y |
| Placas auxiliares sin retención práctica | Apoyos de borde y bridas | Soportes UM980/Tiny-Adapter, ranuras microSD/Tiny; microSD +3 mm Z, Tiny inmóvil | Entrada/salida de cada placa; Tiny hacia +Z |
| Exceso de fijaciones | 2 cierres inferiores, 2 USB diagonales, lengüeta + 1 M3 en botón | Postes, pilotos y lengüeta locales; cuatro apoyos USB conservados | Cabezas sin interferencia y llave Ø3×35 mm en los 19 tornillos |
| Cableado invadía volumen útil | Corredores laterales y salida superior de batería | Canales power/datos/USB/luz; alivio del coaxial R10 heredado | Posición final comprobada; arnés flexible se tiende después del cuerpo y se retira antes del servicio |
| Plantilla IMU chocaba con cuna/soporte power | Recuperar alojamientos y paso de plantilla | Dos guías Ø2.9 en coordenadas originales y rebaje local de respaldo; asiento rígido conservado | Plantilla entra/sale en +Z; datum, PCB, prensa y tornillos conservados |

La silueta, altura, logo/FRONT +Y, BMI088, antena centrada y posición exterior de USB/botón se mantienen. El alivio inferior deja pared local mínima de aproximadamente 1.25 mm, respaldada por el collar de base. Batería nominal 56×12×69 mm sin compresión ni puntas de tornillo en su volumen. La secuencia completa está en la guía; la batería se cambia retirando cuerpo y cuna.

**Power:** referencia PowerBoost 1000C sin USB-A, 23×10×45 mm; alternativa comprobada 26×8×47. SparkFun Soft Power Switch Mk2, 25.4×10×25.4; alternativa 27×8×27. Son combinaciones ancho/fondo/alto, no máximos independientes. USB conserva setback 1.2 mm y paso del sobremolde compacto 13×5.5×25 mm. Botón conserva su cara exterior, 0.1 mm de juego inicial y 0.4 mm hasta tope.

**Jalón:** 5/8"-11 UNC hembra metálica, eje X=Y=0; barril de 9.525 mm y brida de 2.38125 mm. Paso axial libre Ø17.2 hasta Z30 para evitar fondo prematuro. Los tres M3 proporcionan retención positiva; el plástico no constituye la rosca del jalón. El radio de taladros CAD 13.5 mm es nominal de montaje, no una cota publicada por McMaster; ranuras absorben la variación radial, con radio útil de centros de aproximadamente 12.6–15.5 mm considerando las tuercas. **Verificar físicamente antes de uso topográfico.** [Dimensiones del inserto 90611A121](https://www.mcmaster.com/products/screw-mount-nuts/thread-size~5-8-11-2/).

## Tornillería final

**19 tornillos:** 10 M3×8, 2 M3×20, 3 M2.5×8, 2 M2.5×12 y 2 M2×5. **13 tuercas:** 11 M3 y 2 M2.5. Un inserto McMaster y diez bridas de 2.5 mm. Dos llaves: Allen 2 y 1.5 mm. [BOM por ubicación](../mechanical/MECHANICAL_BOM.md).

Frente a **21 tornillos / 12 tuercas / 6 combinaciones**, V1 queda en **19 / 13 / 5**. Se eliminan cinco tornillos del alcance previo y se añaden tres para el inserto antes sin sujeción. Las tuercas aumentan una; no se disimula como reducción. M3 domina con 12/19. M2/M2.5 se mantienen únicamente por USB comercial, antena y fijación/ajuste del BMI088.

## Evidencia y alcance

Resultado: **70 sólidos válidos, 18 recorridos (1162 posiciones), 19 accesos de herramienta, cero interferencias no previstas, 11 STL cerrados y STEP completo reimportado con 60 sólidos válidos**. Resultado cuantitativo final en [validation.json](../mechanical/v1/generated/validation.json) y [exports.json](../mechanical/v1/generated/exports.json). Se comprueba regeneración desde A5+panel, sólidos, pares en posición final, secuencia de montaje/remoción, plantilla, USB/botón, herramientas, retención del inserto y exportaciones. Las intersecciones permitidas se limitan a pilotos de rosca, roscas de antena simplificadas y unión de corredores del mismo arnés; las cabezas se prueban aparte.

Muestreo de traslación a 1 mm y botón a 0.05 mm, no barrido continuo certificado. El coaxial se conecta con el cuerpo ya colocado; no se simula como una varilla rígida atravesando el cuello. No se ha impreso ni probado resistencia, temperatura, estanqueidad o precisión topográfica. El cableado sigue la arquitectura comercial de [WIRING](../hardware/power-modules/WIRING.md); esta entrega no cambia firmware ni declara conformidad USB.

## Siete comprobaciones físicas al armar

1. Jalón e inserto: rosca útil, apoyo del hombro antes de fondo, centrado y ausencia de giro tras apretar.
2. BMI088: encaje de plantilla, alineación con FRONT/eje y bloqueo rígido sin flexionar PCB.
3. Batería: pack protegido, polaridad, ausencia de presión/puntas y cable libre de pellizcos.
4. Cuerpo/cuna: guías y tuercas sin forzar, apriete de dos cierres y rigidez del borde inferior impreso.
5. USB/botón: enchufe completo, placa sin palanca y retorno del botón sin quedar presionado.
6. Módulos/arnés: bridas firmes fuera de componentes, cabezas dentro del paso, coaxial sin tirones y lazos de servicio libres.
7. Encendido/carga: primera alimentación limitada, separación de VBUS y alimentación interna según WIRING, apagado y temperatura inicial de módulos.
