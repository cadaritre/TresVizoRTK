# Mapa de pines generado desde la netlist

Generado por `scripts/doc_tables.py`; no editar a mano.

## ESP32-S3-MINI-1-N4R2 (U201)

| GPIO | Pin del módulo | Red | Uso |
| --- | --- | --- | --- |
| - | 45 (EN) | ESP_EN | EN (RC 10k/1uF y pulsador RESET) |
| 0 | 4 (IO0) | ESP_BOOT | BOOT (pulsador a GND, 10k a 3V3) |
| 1 | 5 (IO1) | GNSS_PPS_MCU | PPS del UM980 (100 ohm) |
| 2 | 6 (IO2) | CHG_INT_N | INT del BQ25798 (drenador abierto, 10k a 3V3) |
| 3 | 7 (IO3) | ESP_IO3 | Pin de arranque: 10k a GND |
| 4 | 8 (IO4) | GNSS_RESET_MCU | RESET_N del UM980 (usar en drenador abierto, pulso >= 5 ms) |
| 5 | 9 (IO5) | GNSS_TXD3_MCU | RX de UART1 <- TXD3 del UM980 |
| 6 | 10 (IO6) | ESP_TX1 | TX de UART1 -> RXD3 del UM980 (1k) |
| 7 | 11 (IO7) | LED_R | Cátodo rojo del LED del panel (1k) |
| 8 | 12 (IO8) | I2C_SDA | I2C: OLED 0x3C/0x3D, MAX17048 0x36, BQ25798 0x6B (4.7k) |
| 9 | 13 (IO9) | I2C_SCL | I2C |
| 10 | 14 (IO10) | BTN_SENSE_N | Botón del panel (activo bajo, por 1N4148W desde QON) |
| 11 | 15 (IO11) | IMU_MOSI | SPI del BMI088 (SDI) |
| 12 | 16 (IO12) | IMU_SCK | SPI del BMI088 (SCK, hasta 10 MHz) |
| 13 | 17 (IO13) | IMU_MISO | SPI del BMI088 (SDO1 + SDO2) |
| 14 | 18 (IO14) | ESP_IO14 | Libre (antes OFF del Mk2); punto de prueba |
| 15 | 19 (IO15) | IMU_CS_ACC_N | CSB1 del BMI088 (acelerómetro) |
| 16 | 20 (IO16) | IMU_CS_GYR_N | CSB2 del BMI088 (giróscopo) |
| 17 | 21 (IO17) | IMU_INT1 | INT1 del acelerómetro |
| 18 | 22 (IO18) | IMU_INT3 | INT3 del giróscopo |
| 19 | 23 (USB_D-) | USB_DN | USB nativo D- (panel) |
| 20 | 24 (USB_D+) | USB_DP | USB nativo D+ (panel) |
| 21 | 25 (IO21) | LED_G | Cátodo verde (100 ohm) |
| 33 | 28 (IO33) | SD_D3 | SD_MMC D3 (10k) |
| 34 | 29 (IO34) | SD_CMD | SD_MMC CMD (10k) |
| 35 | 31 (IO35) | FG_ALRT_N | ALRT del MAX17048 (10k) |
| 36 | 32 (IO36) | LED_B | Cátodo azul (100 ohm) |
| 37 | 33 (IO37) | BTN_LED_EN | Anillo LED del botón (MOSFET N, 100k a GND) |
| 38 | 34 (IO38) | SD_CLK | SD_MMC CLK |
| 39 | 35 (IO39) | SD_D0 | SD_MMC D0 (10k) |
| 40 | 36 (IO40) | SD_D1 | SD_MMC D1 (10k) |
| 41 | 37 (IO41) | ANT_FAULT_N | Falla de la alimentación de antena (OC del TPS22945) |
| 42 | 38 (IO42) | ESP_IO42 | Libre; punto de prueba |
| 43 | 39 (TXD0) | ESP_TX0 | U0TXD -> RXD2 del UM980 (1k); la ROM escribe aquí al arrancar |
| 44 | 40 (RXD0) | GNSS_TXD2_MCU | U0RXD <- TXD2 del UM980 (COM2, 115200) |
| 45 | 41 (IO45) | GNSS_PWR_EN | Habilita el riel del UM980 (TPS22919); 100k a GND (pin de arranque, LOW en reset) |
| 47 | 27 (IO47) | SD_D2 | SD_MMC D2 (10k) |
| 48 | 30 (IO48) | SD_DET | Detección de tarjeta: HIGH con tarjeta (inversor con AO3401A) |

## J101 PANEL_USB (JST PH 6 vertical)

| Pin | Red |
| --- | --- |
| 1 | VBUS |
| 2 | VBUS |
| 3 | GND |
| 4 | USB_DN |
| 5 | USB_DP |
| 6 | GND |
| MP | GND |

## J402 PANEL_UI (JST SH 9 vertical)

| Pin | Red |
| --- | --- |
| 1 | GND |
| 2 | BTN_N |
| 3 | BTN_LED_A |
| 4 | BTN_LED_K |
| 5 | +3V3 |
| 6 | LED_R_K |
| 7 | LED_G_K |
| 8 | LED_B_K |
| 9 | CHG_LED_K |
| MP | GND |

## J403 OLED (JST SH 4 vertical, orden Qwiic)

| Pin | Red |
| --- | --- |
| 1 | GND |
| 2 | +3V3 |
| 3 | I2C_SDA |
| 4 | I2C_SCL |
| MP | GND |

## J302 UM980_AUX (JST SH 5 vertical)

| Pin | Red |
| --- | --- |
| 1 | GND |
| 2 | AUX_TXD1 |
| 3 | AUX_RXD1 |
| 4 | AUX_PPS |
| 5 | AUX_EVENT |
| MP | GND |

## J102 BATTERY (JST PH 2 lateral)

| Pin | Red |
| --- | --- |
| 1 | GND |
| 2 | VBATT_IN |
| MP | GND |

## J404 NTC opcional (JST SH 2 vertical, sin montar)

| Pin | Red |
| --- | --- |
| 1 | CHG_TS |
| 2 | GND |
| MP | GND |
