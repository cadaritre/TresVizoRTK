"""Genera las tablas de GPIO y de conectores directamente desde la netlist (sin transcribir a mano).

    python3 doc_tables.py <netlist.net> <salida.md>
"""

import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from sexpr import find, findall, loads  # noqa: E402

GPIO_NOTES = {
    "GNSS_PPS_MCU": "PPS del UM980 (100 ohm)",
    "CHG_INT_N": "INT del BQ25798 (drenador abierto, 10k a 3V3)",
    "ESP_IO3": "Pin de arranque: 10k a GND",
    "GNSS_RESET_MCU": "RESET_N del UM980 (usar en drenador abierto, pulso >= 5 ms)",
    "GNSS_TXD3_MCU": "RX de UART1 <- TXD3 del UM980",
    "ESP_TX1": "TX de UART1 -> RXD3 del UM980 (1k)",
    "LED_R": "Cátodo rojo del LED del panel (1k)",
    "I2C_SDA": "I2C: OLED 0x3C/0x3D, MAX17048 0x36, BQ25798 0x6B (4.7k)",
    "I2C_SCL": "I2C",
    "BTN_SENSE_N": "Botón del panel (activo bajo, por 1N4148W desde QON)",
    "IMU_MOSI": "SPI del BMI088 (SDI)",
    "IMU_SCK": "SPI del BMI088 (SCK, hasta 10 MHz)",
    "IMU_MISO": "SPI del BMI088 (SDO1 + SDO2)",
    "ESP_IO14": "Libre (antes OFF del Mk2); punto de prueba",
    "IMU_CS_ACC_N": "CSB1 del BMI088 (acelerómetro)",
    "IMU_CS_GYR_N": "CSB2 del BMI088 (giróscopo)",
    "IMU_INT1": "INT1 del acelerómetro",
    "IMU_INT3": "INT3 del giróscopo",
    "USB_DN": "USB nativo D- (panel)",
    "USB_DP": "USB nativo D+ (panel)",
    "LED_G": "Cátodo verde (100 ohm)",
    "SD_D3": "SD_MMC D3 (10k)",
    "SD_CMD": "SD_MMC CMD (10k)",
    "FG_ALRT_N": "ALRT del MAX17048 (10k)",
    "LED_B": "Cátodo azul (100 ohm)",
    "BTN_LED_EN": "Anillo LED del botón (MOSFET N, 100k a GND)",
    "SD_CLK": "SD_MMC CLK",
    "SD_D0": "SD_MMC D0 (10k)",
    "SD_D1": "SD_MMC D1 (10k)",
    "ANT_FAULT_N": "Falla de la alimentación de antena (OC del TPS22945)",
    "ESP_IO42": "Libre; punto de prueba",
    "ESP_TX0": "U0TXD -> RXD2 del UM980 (1k); la ROM escribe aquí al arrancar",
    "GNSS_TXD2_MCU": "U0RXD <- TXD2 del UM980 (COM2, 115200)",
    "GNSS_PWR_EN": "Habilita el riel del UM980 (TPS22919); 100k a GND (pin de arranque, LOW en reset)",
    "SD_D2": "SD_MMC D2 (10k)",
    "SD_DET": "Detección de tarjeta: HIGH con tarjeta (inversor con AO3401A)",
    "ESP_BOOT": "BOOT (pulsador a GND, 10k a 3V3)",
    "ESP_EN": "EN (RC 10k/1uF y pulsador RESET)",
}


def main():
    net, out = sys.argv[1:3]
    t = loads(open(net, encoding="utf-8").read())
    pins = {}
    names = {}
    for c in findall(find(t, "libparts"), "libpart"):
        lib = str(find(c, "lib")[1]) + ":" + str(find(c, "part")[1])
        names[lib] = {str(find(p, "num")[1]): str(find(p, "name")[1]) for p in findall(find(c, "pins") or [], "pin")}
    comp_lib = {}
    for c in findall(find(t, "components"), "comp"):
        ls = find(c, "libsource")
        comp_lib[str(find(c, "ref")[1])] = str(find(ls, "lib")[1]) + ":" + str(find(ls, "part")[1])
    for n in findall(find(t, "nets"), "net"):
        name = str(find(n, "name")[1]).split("/")[-1]
        for x in findall(n, "node"):
            pins.setdefault(str(find(x, "ref")[1]), {})[str(find(x, "pin")[1])] = name
    lines = ["# Mapa de pines generado desde la netlist", "",
             "Generado por `scripts/doc_tables.py`; no editar a mano.", "", "## ESP32-S3-MINI-1-N4R2 (U201)", "",
             "| GPIO | Pin del módulo | Red | Uso |", "| --- | --- | --- | --- |"]
    pn = names.get(comp_lib.get("U201"), {})
    rows = []
    for num, netname in pins.get("U201", {}).items():
        pname = pn.get(num, "")
        if netname in ("GND", "+3V3") or netname.startswith("unconnected"):
            continue
        m = re.match(r"IO(\d+)", pname)
        g = int(m.group(1)) if m else {"TXD0": 43, "RXD0": 44, "USB_D-": 19, "USB_D+": 20}.get(pname, -1)
        rows.append((g, num, pname, netname))
    for g, num, pname, netname in sorted(rows):
        lines.append("| %s | %s (%s) | %s | %s |" % (g if g >= 0 else "-", num, pname, netname,
                                                     GPIO_NOTES.get(netname, "")))
    for ref, title in (("J101", "PANEL_USB (JST PH 6 vertical)"), ("J402", "PANEL_UI (JST SH 9 vertical)"),
                       ("J403", "OLED (JST SH 4 vertical, orden Qwiic)"), ("J302", "UM980_AUX (JST SH 5 vertical)"),
                       ("J102", "BATTERY (JST PH 2 lateral)"), ("J404", "NTC opcional (JST SH 2 vertical, sin montar)")):
        lines += ["", "## %s %s" % (ref, title), "", "| Pin | Red |", "| --- | --- |"]
        for num in sorted(pins.get(ref, {}), key=lambda k: (not k.isdigit(), int(k) if k.isdigit() else 0, k)):
            lines.append("| %s | %s |" % (num, pins[ref][num]))
    with open(out, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")
    print("tablas:", out)


if __name__ == "__main__":
    main()
