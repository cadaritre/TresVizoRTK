# Presupuesto de alimentación inicial

**No hay medida de consumo del conjunto ni total verificable.** TBD no significa cero. Los 5 V son una hipótesis de arquitectura, no una instrucción de cableado.

| Carga | Tensión de entrada de placa | I típico | I máximo/pico | Fuente / estado | Margen |
| --- | --- | --- | --- | --- | --- |
| Carrier BDLX RTK_UM98_V1.0.1 UM980 | TBD (USB sugiere entrada 5 V, no confirma header) | TBD | TBD | hardware/identification.md y ficha BDLX; falta esquema de carrier y medida | TBD |
| ESP32-S3-Tiny 4 MB/2 MB | TBD para punto de inyección elegido | TBD | TBD | Identificada por USB; revisión física/esquema pendiente; el consumo del SoC no es el de la placa | TBD |
| BMI088 breakout | TBD | TBD | TBD | Breakout no identificado eléctricamente | TBD |
| microSD + lector | TBD | TBD | TBD | Lector/tarjeta sin caracterización; incluir escritura/flush | TBD |
| Antena activa, si recibe bias de carrier | TBD | TBD | TBD | Evitar doble conteo con UM980; modelo/consumo de alimentación pendiente | TBD |
| USB-UART CP2102N | Dominio USB, según circuito de fabricante | TBD modo final | TBD | Datasheet en datasheets/README.md; enumeración, TX y suspensión difieren | TBD |
| RGB y CHG | Según rail/driver elegido | TBD | TBD | Duty y corriente LED por definir; CHG desde USB | TBD |
| Soft-power/gauge/protección | SYSTEM_POWER / PACK | TBD total | TBD | Registrar corrientes de reposo, pull-ups y fugas | TBD |
| Otros módulos/cables | TBD | TBD | TBD | Inventario pendiente | TBD |

## Cálculo reproducible cuando existan medidas

- `P_load = sum(V_rail * I_rail)`, sin duplicar cargas alimentadas por otra placa.
- `I_pack_peak >= sum(P_rail_peak / eta_rail_min) / V_pack_min + I_always_on`.
- Objetivo propuesto de margen continuo: 30% sobre máximo medido; además verificar picos de arranque, saturación de inductores, caída de conectores y temperatura. No convertirlo en corriente nominal hasta medir.
- `P_USB_available = VBUS_min * I_USB_authorized`; descontar bridge/lógica/pérdidas antes de asignar carga. Si no alcanza, reducir carga; si batería no puede suplementar, inhibir arranque o apagar de forma controlada.
- Para cargador lineal, primera estimación: `P_loss ≈ (VBUS - VBAT)*I_charge + (VBUS - VSYS)*I_system_from_USB`. No incluye todas las pérdidas. Ejemplo hipotético: sólo cargar a 0.5 A con batería a 3.2 V desde 5 V disipa ~0.9 W, antes del sistema. No demuestra que A4 lo tolere.
- 3.7 V × 5 Ah = 18.5 Wh **nominales**; autonomía = energía útil × eficiencia / potencia media. Energía útil, potencia y autonomía: TBD. Tiempo de carga requiere corriente efectiva y fase CV.

## Campaña de medida pendiente

Medir cada placa por su entrada documentada: reposo, arranque, GNSS activo con antena, Wi-Fi TX, escritura/flush SD y combinación simultánea. Registrar fuente, revisión, tensión mínima/máxima, duración y pico con osciloscopio; repetir en batería baja y USB limitado. Medir corte y corriente OFF con UART/I2C conectados. Después congelar rails, límites y calibre/conectores.

SYSTEM_3V3 externo se añadirá sólo si una placa lo requiere; no alimentar salidas de LDO existentes ni unir dos fuentes de 3.3 V. Una eventual lógica auxiliar de 3.3 V no implica distribuir esa tensión a todos los módulos.
