# Mapa de pines generado desde la netlist

Generado por `scripts/doc_tables.py`; no editar a mano.

## ESP32-S3-WROOM-1-N16R2 (U201)

| GPIO | Pin del módulo | Red | Uso |
| --- | --- | --- | --- |
| - | 3 (EN) | ESP_EN | EN (RC 10k/1uF y pulsador RESET) |
| 0 | 27 (IO0) | ESP_BOOT | BOOT (pulsador a GND, 10k a 3V3) |
| 1 | 39 (IO1) | IMU_INT3 | INT3 del giróscopo (U401.12) |
| 2 | 38 (IO2) | IMU_INT1 | INT1 del acelerómetro (U401.16) |
| 3 | 15 (IO3) | ESP_IO3 | Pin de arranque: 10k a GND |
| 4 | 4 (IO4) | SD_D1 | SD_MMC D1 (10k) |
| 5 | 5 (IO5) | SD_D0 | SD_MMC D0 (10k) |
| 6 | 6 (IO6) | SD_CLK | SD_MMC CLK |
| 7 | 7 (IO7) | SD_CMD | SD_MMC CMD (10k) |
| 8 | 12 (IO8) | GNSS_TX_MCU | TX de la UART del GNSS -> RXD2 de la carrier (1k, J301.3) |
| 9 | 17 (IO9) | GNSS_TXD2_MCU | RX de la UART del GNSS <- TXD2 de la carrier (100 ohm, J301.4; COM2, 115200) |
| 10 | 18 (IO10) | GNSS_PPS_MCU | PPS de la carrier GNSS (100 ohm desde J301.5) |
| 11 | 19 (IO11) | GNSS_EVENT_MCU | EVENT de la carrier (J301.6, 1k; 100k a GND) |
| 12 | 20 (IO12) | GNSS_RESET_MCU | RESET_N de la carrier (J301.7, 1k; usar en drenador abierto, pulso >= 5 ms). La BDLX no lo saca |
| 13 | 21 (IO13) | I2C_SDA | I2C: OLED 0x3C/0x3D, MAX17048 0x36, BQ25798 0x6B (4.7k) |
| 14 | 22 (IO14) | I2C_SCL | I2C |
| 15 | 8 (IO15) | SD_D3 | SD_MMC D3 (10k) |
| 16 | 9 (IO16) | SD_D2 | SD_MMC D2 (10k) |
| 17 | 10 (IO17) | SD_DET | Detección de tarjeta: HIGH con tarjeta (inversor con AO3401A) |
| 18 | 11 (IO18) | BTN_SENSE_N | Botón del equipo (SW401; activo bajo, por 1N4148W desde QON; 10k a 3V3) |
| 19 | 13 (USB_D-) | USB_DN | USB nativo D- (USB-C J101, A7/B7, por el ESD U101) |
| 20 | 14 (USB_D+) | USB_DP | USB nativo D+ (USB-C J101, A6/B6, por el ESD U101) |
| 21 | 23 (IO21) | CHG_INT_N | INT del BQ25798 (drenador abierto, 10k a 3V3) |
| 35 | 28 (IO35) | ESP_IO35 | Libre; punto de prueba |
| 36 | 29 (IO36) | ESP_IO36 | Libre; punto de prueba |
| 37 | 30 (IO37) | ESP_IO37 | Libre; punto de prueba |
| 41 | 34 (IO41) | IMU_SDA | I2C del BMI088 (U401) en la placa, segundo bus: SDA (4.7k). Acelerómetro 0x18, giróscopo 0x68 |
| 42 | 35 (IO42) | IMU_SCL | I2C del BMI088: SCL (4.7k), 400 kHz |
| 43 | 37 (TXD0) | ESP_TXD0 | U0TXD: mensajes de la ROM al arrancar; punto de prueba TP208 |
| 44 | 36 (RXD0) | ESP_RXD0 | U0RXD; punto de prueba TP209 |
| 45 | 26 (IO45) | GNSS_PWR_EN | Enciende el 5 V de la carrier GNSS; 100k a GND (pin de arranque, LOW en reset = GNSS apagado) |
| 47 | 24 (IO47) | FG_ALRT_N | ALRT del MAX17048 (10k) |
| 48 | 25 (IO48) | LED_STATUS | LED de estado rojo D403 (330 ohm, ~4.4 mA; activo alto, sin pull en el reset) |

## J101 USB_C

TYPE-C-31-M-12 (LCSC C165948). HRO TYPE-C-31-M-12: USB-C 16 contactos horizontal (huella y modelo de la panel-usb); carcasa a GND; cara 1.29 mm por delante del canto en la panel-usb, eje a ~1.65 mm de la placa

| Pin | Red |
| --- | --- |
| A1 | GND |
| A12 | GND |
| A4 | VBUS |
| A5 | CC1 |
| A6 | USB_DP |
| A7 | USB_DN |
| A8 | unconnected-(J101-SBU1-PadA8) |
| A9 | VBUS |
| B1 | GND |
| B12 | GND |
| B4 | VBUS |
| B5 | CC2 |
| B6 | USB_DP |
| B7 | USB_DN |
| B8 | unconnected-(J101-SBU2-PadB8) |
| B9 | VBUS |
| SH | GND |

## J102 BATTERY

SM04B-GHS-TB(LF)(SN) (LCSC C189895). JST GH 4 lateral al pack 1S2P: 1-2 = BAT-, 3-4 = BAT+ (dos contactos por polo, ~1 A cada uno). El pack necesita cable GH de 4 hilos AWG 26; ICHG del BQ25798 <= 1.5 A. Medir el pack antes de enchufar

| Pin | Red |
| --- | --- |
| 1 | GND |
| 2 | GND |
| 3 | VBATT_IN |
| 4 | VBATT_IN |
| MP | GND |

## J301 GNSS

SM08B-SRSS-TB(LF)(SN) (LCSC C160407). SH 8 lateral (JST SM08B-SRSS-TB): 5V, GND, RXD2, TXD2, PPS, EVENT, RESET_N, GND. SH y no GH, para que no se pueda cruzar con J102 (GH 4 de la batería)

| Pin | Red |
| --- | --- |
| 1 | GNSS_5V |
| 2 | GND |
| 3 | GNSS_RXD2 |
| 4 | GNSS_TXD2 |
| 5 | GNSS_PPS |
| 6 | GNSS_EVENT |
| 7 | GNSS_RESET_N |
| 8 | GND |
| MP | GND |

## J401 TF-015

TF-015 (LCSC C113206). 

| Pin | Red |
| --- | --- |
| 1 | SD_D2 |
| 2 | SD_D3 |
| 3 | SD_CMD |
| 4 | +3V3 |
| 5 | SD_CLK |
| 6 | GND |
| 7 | SD_D0 |
| 8 | SD_D1 |
| 9 | SD_CD_N |
| 10 | GND |
| 11 | GND |
| 12 | GND |
| 13 | GND |

## J403 OLED

| Pin | Red |
| --- | --- |
| 1 | +3V3 |
| 2 | GND |
| 3 | I2C_SCL |
| 4 | I2C_SDA |

## J404 NTC

SM02B-SRSS-TB(LF)(SN) (LCSC C160402). NTC 10k B3435 (103AT) obligatoria, pegada a la celda: sin ella el cargador no carga

| Pin | Red |
| --- | --- |
| 1 | CHG_TS |
| 2 | GND |
| MP | GND |
