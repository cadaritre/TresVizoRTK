# Presupuesto de alimentación inicial

**No hay medida de consumo del conjunto ni total verificable.** TBD no significa cero. La ficha BDLX respalda un rail de 5 V para su carrier; todavía debe cerrarse el punto físico de inyección.

| Carga | Tensión de entrada de placa | I típico | I máximo/pico | Fuente / estado | Margen |
| --- | --- | --- | --- | --- | --- |
| Carrier BDLX RTK_UM98_V1.0.1 UM980 | 4.0–5.5 V, nominal 5 V según BDLX; header pendiente | 160 mA a 5 V, ficha (condiciones no detalladas) | TBD | [Tabla oficial](https://www.bdlxgnss.com/static/upload/image/20250804/1754279536807539.png); falta pico medido | TBD |
| ESP32-S3-Tiny-N8R8 (declarada) | TBD para punto de inyección elegido | TBD | TBD | Serigrafía informada ESP32-S3-TINY; revisión FPC pendiente. Evidencia histórica 4/2 por reconciliar; ver USB_NATIVE_REVIEW.md | TBD |
| BMI088 breakout | TBD | TBD | TBD | Breakout no identificado eléctricamente | TBD |
| microSD + lector | TBD | TBD | TBD | Lector/tarjeta sin caracterización; incluir escritura/flush | TBD |
| Antena activa, si recibe bias de carrier | TBD | TBD | TBD | Evitar doble conteo con UM980; modelo/consumo de alimentación pendiente | TBD |
| USB nativo de Tiny | Incluido en la alimentación de Tiny | TBD | TBD | Evitar doble conteo; medir enumeración y Serial/JTAG activos | TBD |
| Detector VBUS + switch USB + protección | USB_VBUS / lógica según circuito definitivo | TBD | TBD | Nuevos auxiliares P1; comprobar OFF/Ioff y consumo pre-enumeración | TBD |
| RGB y CHG | Según rail/driver elegido | TBD | TBD | Duty y corriente LED por definir; CHG desde USB | TBD |
| Soft-power/gauge/protección | SYSTEM_POWER / PACK | TBD total | TBD | Registrar corrientes de reposo, pull-ups y fugas | TBD |
| Otros módulos/cables | TBD | TBD | TBD | Inventario pendiente | TBD |

## Batería de referencia

El propietario identifica la publicación **955565, 3.7 V, 5000 mAh, 18.5 Wh**. Son datos anunciados, no mediciones. Imagen con dos cables: NTC accesible no confirmado; prever evaluación de termistor externo. PCM, corrientes admisibles, conector y dimensiones reales TBD. Ver [evidencia y efecto en el diseño](BATTERY_REFERENCE.md).

## Cálculo reproducible cuando existan medidas

- `P_load = sum(V_rail * I_rail)`, sin duplicar cargas alimentadas por otra placa.
- `I_pack_peak >= sum(P_rail_peak / eta_rail_min) / V_pack_min + I_always_on`.
- Objetivo propuesto de margen continuo: 30% sobre máximo medido; además verificar picos de arranque, saturación de inductores, caída de conectores y temperatura. No convertirlo en corriente nominal hasta medir.
- `P_USB_available = VBUS_min * I_USB_authorized`; descontar lógica/pérdidas antes de asignar carga. Si no alcanza, reducir carga; si batería no puede suplementar, inhibir arranque o apagar de forma controlada.
- Para cargador lineal, primera estimación: `P_loss ≈ (VBUS - VBAT)*I_charge + (VBUS - VSYS)*I_system_from_USB`. No incluye todas las pérdidas. Ejemplo hipotético: sólo cargar a 0.5 A con batería a 3.2 V desde 5 V disipa ~0.9 W, antes del sistema. No demuestra que A4 lo tolere.
- 3.7 V × 5 Ah = 18.5 Wh **nominales**; autonomía = energía útil × eficiencia / potencia media. Energía útil, potencia y autonomía: TBD. Tiempo de carga requiere corriente efectiva y fase CV.

## Campaña de medida pendiente

Medir cada placa por su entrada documentada: reposo, arranque, GNSS activo con antena, Wi-Fi TX, escritura/flush SD y combinación simultánea. Registrar fuente, revisión, tensión mínima/máxima, duración y pico con osciloscopio; repetir en batería baja y USB limitado. Medir corte y corriente OFF con USB/FPC/sensing/I2C conectados. Después congelar rails, límites y calibre/conectores.

SYSTEM_3V3 externo se añadirá sólo si una placa lo requiere; no alimentar salidas de LDO existentes ni unir dos fuentes de 3.3 V. Una eventual lógica auxiliar de 3.3 V no implica distribuir esa tensión a todos los módulos.
