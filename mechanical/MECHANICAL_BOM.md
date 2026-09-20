# Tornillería y compra mecánica — V1

Paquete vigente: [V1](v1/README.md). **19 tornillos, 13 tuercas y un inserto metálico 5/8"-11 UNC.** Cinco combinaciones diámetro/longitud; 12 de los 19 tornillos son M3. Cantidades instaladas, sin repuestos ni compra ejecutada.

| Comprar | Cantidad | Uso |
| --- | ---: | --- |
| M3×8, cabeza botón ISO 7380-1, Allen 2 mm | **10** | 2 cuerpo, 2 tapa, 2 panel, 1 cartucho, 3 inserto del jalón. |
| M3×20, cabeza botón ISO 7380-1, Allen 2 mm | **2** | Cuna/IMU al chasis; conserva su unión rígida. |
| M2.5×8, cabeza cilíndrica ISO 4762, Allen 2 mm | **3** | Roscas comerciales de HA-901A; 4 mm de penetración nominal. |
| M2.5×12, cabeza cilíndrica ISO 4762, Allen 2 mm | **2** | BMI088, conserva agujeros y ajuste del datum. |
| M2×5, cabeza cilíndrica ISO 4762, Allen 1.5 mm | **2** | Adafruit 5871, dos diagonales; sus agujeros Ø2.5 no admiten holgura para M3. |
| Tuerca M3 DIN 934, AF5.5 | **11** | 6 cierres, 2 cuna, 3 inserto; alojamientos cautivos. |
| Tuerca M2.5 DIN 934, AF5 | **2** | Prensa IMU. |
| McMaster **90611A121**, acero, **5/8"-11 UNC hembra** | **1** | Brida y barril comerciales; usar la pieza metálica, no imprimir su referencia CAD. |
| Brida 2.5 mm, longitud 100–150 mm | **10** | 2 PowerBoost, 2 soft-power, 2 UM980, 2 microSD, 1 Tiny y 1 Tiny-Adapter. Cortar sobrantes y sustituir al desmontar. |
| Arandelas / insertos heat-set | **0 / 0** | No necesarios en la solución nominal. |

Los dos M2 y el M3 del cartucho roscan en pilotos impresos; sólo se abren ocasionalmente. Los cierres de servicio y la cuna usan tuercas metálicas. Las tres tuercas del inserto se colocan por abajo y se sostienen al iniciar rosca; una vez apretadas quedan encerradas y no giran. Cabeza M3 Ø5.7×1.65 y M2 Ø3.8×2 mm representadas.

| Comparación con revisión anterior | Antes | V1 |
| --- | ---: | ---: |
| Tornillos, incluidos los nuevos del jalón | 21 | **19 (−2)** |
| Tornillos en el alcance que ya estaba definido | 21 | **16 (−5)** |
| Fijación del inserto antes omitida | 0 | **3 M3×8** |
| Tuercas | 12 | **13 (+1)** |
| Combinaciones diámetro/longitud | 6 | **5** |
| Tornillos M3 | 10 | **12** |

La reducción viene de 4→2 cierres inferiores, 4→2 tornillos USB y 2 M2×8→1 M3×8 más lengüeta en cartucho. Se añaden tres tornillos y tres tuercas para resolver el inserto, y se eliminan dos tuercas de los cierres. **Las tuercas no disminuyen**; el incremento cierra una retención que antes faltaba. No se reducen las fijaciones de IMU, antena ni cuna.

Los componentes eléctricos vigentes están en [power-modules](../hardware/power-modules/README.md). El modelo agrega bandejas para PowerBoost 1000C sin USB-A y SparkFun Soft Power Switch Mk2, y retenciones para placas existentes. Complementos de montaje: lámina aislante fina en apoyos, guía óptica flexible Ø2 mm para CHG, silicona neutra removible para difusores, protección y alivios del arnés según WIRING. No comprar una segunda alimentación personalizada.

Fuente dimensional del inserto: [catálogo McMaster, 90611A121](https://www.mcmaster.com/products/screw-mount-nuts/thread-size~5-8-11-2/). Para cabezas: [M3 ISO 7380-1](https://www.pts-uk.com/products/socket-screws/socket-button-screws/metric-a2/a73800308), [M2.5 ISO 4762](https://www.pts-uk.com/products/socket-screws/socket-cap-screws/metric-a2/a91202508). La disponibilidad y el par de apriete no se han ensayado.
