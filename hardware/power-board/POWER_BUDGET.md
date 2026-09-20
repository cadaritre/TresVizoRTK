# Presupuesto de potencia — Rev A

Datos publicados, cálculos y medidas se distinguen expresamente. El prototipo todavía no está medido.

| Carga / rail | Tensión | Consumo típico | Máximo | Fuente / margen |
| --- | --- | --- | --- | --- |
| Carrier UM980 BDLX externa | 4.0–5.5 V; alimentar a 5 V | 160 mA publicado | TBD, antena/configuración incluidas | [Tabla de carrier](https://www.bdlxgnss.com/static/upload/image/20250804/1754279536807539.png); no confundir con módulo desnudo |
| Tiny N8R8 externa | 5 V por entrada documentada | TBD con firmware real | TBD, picos radio/SD | [Waveshare](https://docs.waveshare.com/ESP32-S3-Tiny); comprobar revisión/diodo/LDO |
| IMU, SD y periféricos existentes | Según cableado externo | TBD | TBD | Fuera de esta placa; deben entrar en medición total |
| LEDs de estado | SYSTEM_5V; 1 kΩ/canal | ~2–3 mA/canal ON | <15 mA total | Cálculo de resistencias, brillo por medir |
| OFF a batería | SYSTEM_POWER → AON_3V0 | Orden 0.4–0.5 mA | TBD con temperatura | Estimación de ICs y pull-ups |
| Gauge MAX17048 | PACK_P | Según hibernación/lectura | Ver hoja técnica/medir | SOC requiere caracterización de celda |
| Salida total de ensayo | 4.992 V nominal | Punto de diseño 0.6 A, 3 W | No medido | TPS61023, L=1 µH, CIN=10 µF, COUT=44 µF nominal |
| Carga de celda | CC/CV 4.2 V | 500 mA nominal | ~548 mA por tolerancia ISET antes de regulación | Límite real de la batería pendiente |

A 3 W, eficiencia supuesta 85% y batería 3.1 V: `Ibat ≈ 3/(0.85×3.1) = 1.14 A`, más consumos auxiliares. Los 18.5 Wh anunciados darían `18.5×0.85/3 ≈ 5.2 h` ideales. UVLO, temperatura, envejecimiento y capacidad real reducen energía útil: no es autonomía garantizada.

Fuente C-C con anuncio ≥1.5 A habilita ~1 A en la rama power-path. Un receptor de 3 W puede consumir ~0.65–0.8 A de entrada; no queda margen para cargar siempre a 500 mA. DPPM reduce carga y la batería puede suplementar. Puerto legacy limita esa rama a ~50 mA nominales: debug con batería y carga lenta, sin garantía de funcionamiento completo desde USB solo.

CC ideal de 5000 mAh/500 mA dura 10 h, más CV/precharge. El sistema encendido prolonga ese tiempo. TMR desactivado explícitamente; consultar DESIGN.md. No se afirma tiempo máximo de carga.

Charger con celda a 3 V y carga 0.5 A: `(5−3)×0.5 ≈ 1 W`, más pérdidas de alimentar el sistema. Debe ensayarse con carcasa y NTC real; puede regular térmicamente. Planos de GND y lazo switching corto no certifican ruido GNSS aceptable.
