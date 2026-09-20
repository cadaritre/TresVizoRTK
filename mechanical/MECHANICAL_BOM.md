# BOM mecánica de integración A5 + panel comercial

20 de septiembre de 2026. Alcance: piezas definidas en el CAD revisado de [integración](integration-review/README.md). **21 tornillos representados, 12 tuercas, cero arandelas y cero insertos heat-set definidos. El total del receptor completo sigue abierto.** No incluye compras ni disponibilidad. La BOM electrónica permanece en [power-modules](../hardware/power-modules/README.md).

## Tornillería definida

| Ubicación | Cantidad | Diámetro | Longitud bajo cabeza | Tipo | Función | Herramienta |
| --- | ---: | --- | --- | --- | --- | --- |
| Cuerpo ↔ base integrada | 4 | M3 | 8 mm | Cabeza botón ISO 7380-1 | Cierre inferior desmontable | Allen 2 mm |
| Tapa ↔ cuerpo | 2 | M3 | 8 mm | Cabeza botón ISO 7380-1 | Cierre superior | Allen 2 mm |
| Panel ↔ cuerpo | 2 | M3 | 8 mm | Cabeza botón ISO 7380-1, Ø5.7 nominal | Panel desmontable, asiento plano corregido | Allen 2 mm |
| Cuna/IMU ↔ chasis | 2 | M3 | 20 mm | Cabeza botón ISO 7380-1 | Bloqueo rígido de cuna contra sus guías | Allen 2 mm |
| Antena HA-901A ↔ tapa | 3 | M2.5 | 8 mm | Cabeza cilíndrica ISO 4762 | Rosca existente de antena; penetración CAD 4 mm | Allen 2 mm |
| BMI088 ↔ prensa cautiva | 2 | M2.5 | 12 mm | Cabeza cilíndrica ISO 4762 | Fijación de PCB y ajuste inicial XY | Allen 2 mm |
| Adafruit 5871 ↔ panel | 4 | M2 | 5 mm | Cabeza cilíndrica ISO 4762, Ø3.8 × 2 mm | Cuatro apoyos frente a inserción USB | Allen 1.5 mm |
| Cartucho de botón ↔ panel | 2 | M2 | 8 mm | Cabeza cilíndrica ISO 4762, Ø3.8 × 2 mm | Cartucho desmontable | Allen 1.5 mm |
| **Subtotal definido** | **21** | **3 diámetros** | **6 combinaciones diámetro/longitud** | **2 familias de cabeza** | **10 M3 + 5 M2.5 + 6 M2** | **2 llaves** |

Para comprar por referencia: 8 M3×8, 2 M3×20, 3 M2.5×8, 2 M2.5×12, 4 M2×5 y 2 M2×8. No se compra un M3 avellanado para este panel revisado. Los seis M2 roscan en pilotos impresos Ø1.7: validar roscado, par y ciclos; la representación de vástago liso intersecta intencionalmente el piloto. No significa una rosca de plástico ensayada.

M3 se conserva en todos los cierres y la cuna; son 10/21, **no la mayoría absoluta del subtotal completo**. Forzar mayoría sustituyendo M2 dañaría agujeros USB Ø2.5. M2.5 está impuesto por la antena y permite holgura en agujeros IMU Ø3; M3 no aporta ese ajuste. El cartucho mantiene M2 para conservar sus postes Ø5 y su pared disponible. No se añaden M4/M5.

Referencias de cabezas: [M3 ISO 7380-1 PTS](https://www.pts-uk.com/products/socket-screws/socket-button-screws/metric-a2/a73800308), [M2.5 ISO 4762 PTS](https://www.pts-uk.com/products/socket-screws/socket-cap-screws/metric-a2/a91202508), [dimensiones M2 ISO 4762 Accu](https://www.accu.co.uk/metric-cap-head-screws/1010017-NBK-SNSP-M2-8-R360). Esta última se consulta por geometría de cabeza/llave, no prescribe bronce ni fijador de rosca. Contrastar el tornillo comprado; no aplicar fijador químico a plástico sin compatibilidad documentada.

## Otros herrajes y elementos no impresos

| Elemento | Cantidad definida | Estado / función |
| --- | ---: | --- |
| Tuerca hexagonal M3 DIN 934 | 10 | 8 cierres y 2 cuna; alojamientos cautivos existentes. CAD AF5.5 nominal, bolsillos heredados AF5.8; probar ajuste sin adhesivo. |
| Tuerca hexagonal M2.5 DIN 934 | 2 | Prensa `IMUNutBar`; AF5 nominal, bolsillo AF5.2, techo 1.8 mm. |
| Inserto hembra metálico 5/8-11 UNC | 1 previsto | Candidato existente McMaster 90611A121; **selección/retención no cerradas**. No fabricar a partir del cilindro CAD. |
| Tornillos/tuercas/arandelas de brida del inserto | **TBD** | La base tiene tres ranuras; no equivale a tres fijaciones ya dimensionadas. Elegir con plano real y cálculo de apoyo/longitud. |
| Fijaciones UM980, microSD, Tiny-Adapter, PowerBoost y SparkFun | **TBD** | No están incluidas en 21. Conocer agujeros, espesor, zonas sin cobre y conectores antes de cerrar recuento. |
| Heat-set inserts | 0 | No se añaden al montaje definido; los cierres repetidos ya usan tuercas cautivas. |
| Arandelas | 0 definidas | No afirmar cero en el receptor final: la brida o placas pendientes podrían necesitarlas. |
| Cincha removible para batería / alivios de arnés | TBD | Medir trayecto y ancho de pasos; nunca comprimir la bolsa ni usarla como apoyo estructural. |
| Guía óptica de carga y difusores transparentes | 1 sistema / 2 difusores | Trayecto de carga sin resolver; los dos STL de lente son sólo forma nominal. |

## Antes / después de esta revisión

| Concepto comparable | Antes de integrar | Después |
| --- | ---: | ---: |
| A5 simplificado: tornillos definidos | 15 | 15 |
| Fijación USB + cartucho | 6 | 6 |
| **Subtotal combinado** | **21** | **21** |
| Tuercas definidas | 12 | 12 |
| Arandelas / heat-set definidos | 0 / 0 | 0 / 0 |
| Tipo de cierre M3 del panel | Conflicto: avellanado en panel / botón en A5 | M3×8 botón coherente con A5 |
| Cabeza M2 representada | Ø3.6, alturas 1.3/1.4 sin referencia cerrada | Ø3.8 × 2 de ISO 4762 |

No se atribuye a esta revisión la reducción anterior 23→15, ni se eliminan tornillos de IMU, cuna o USB sin ensayo de rigidez. Se simplifica el suministro del panel reutilizando la misma cabeza M3 de los otros cierres.

Las seis piezas permanentes A5 se convierten en ocho estructurales al reemplazar `ServiceCover` por panel + actuador + cartucho; se suman dos lentes y la plantilla reutilizable fuera del producto. Los soportes aún pendientes pueden alterar ese total. No usar los seis STL del A5 y los del panel como dos juegos completos para montar simultáneamente.
