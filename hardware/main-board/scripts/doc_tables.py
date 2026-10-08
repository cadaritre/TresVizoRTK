"""Genera las tablas de GPIO y de conectores directamente desde la netlist (sin transcribir a mano).

    python3 doc_tables.py <netlist.net> <salida.md>
"""

import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from sexpr import find, findall, loads  # noqa: E402

GPIO_NOTES = {
    "GNSS_PPS_MCU": "PPS de la carrier GNSS (100 ohm desde J301.5)",
    "CHG_INT_N": "INT del BQ25798 (drenador abierto, 10k a 3V3)",
    "ESP_IO3": "Pin de arranque: 10k a GND",
    "GNSS_RESET_MCU": "RESET_N de la carrier (J301.7, 1k; usar en drenador abierto, pulso >= 5 ms). La BDLX no lo saca",
    "GNSS_EVENT_MCU": "EVENT de la carrier (J301.6, 1k; 100k a GND)",
    "I2C_SDA": "I2C: OLED 0x3C/0x3D, MAX17048 0x36, BQ25798 0x6B (4.7k)",
    "I2C_SCL": "I2C",
    "BTN_SENSE_N": "Botón del equipo (SW401; activo bajo, por 1N4148W desde QON; 10k a 3V3)",
    "IMU_SDA": "I2C del BMI088 (U401) en la placa, segundo bus: SDA (4.7k). Acelerómetro 0x18, giróscopo 0x68",
    "IMU_SCL": "I2C del BMI088: SCL (4.7k), 400 kHz",
    "IMU_INT1": "INT1 del acelerómetro (U401.16)",
    "IMU_INT3": "INT3 del giróscopo (U401.12)",
    "USB_DN": "USB nativo D- (USB-C J101, A7/B7, por el ESD U101)",
    "USB_DP": "USB nativo D+ (USB-C J101, A6/B6, por el ESD U101)",
    "SD_D3": "SD_MMC D3 (10k)",
    "SD_CMD": "SD_MMC CMD (10k)",
    "FG_ALRT_N": "ALRT del MAX17048 (10k)",
    "LED_STATUS": "LED de estado rojo D403 (330 ohm, ~4.4 mA; activo alto, sin pull en el reset)",
    "SD_CLK": "SD_MMC CLK",
    "SD_D0": "SD_MMC D0 (10k)",
    "SD_D1": "SD_MMC D1 (10k)",
    "GNSS_TX_MCU": "TX de la UART del GNSS -> RXD2 de la carrier (1k, J301.3)",
    "GNSS_TXD2_MCU": "RX de la UART del GNSS <- TXD2 de la carrier (100 ohm, J301.4; COM2, 115200)",
    "ESP_IO35": "Libre; punto de prueba",
    "ESP_IO36": "Libre; punto de prueba",
    "ESP_IO37": "Libre; punto de prueba",
    "GNSS_PWR_EN": "Enciende el 5 V de la carrier GNSS; 100k a GND (pin de arranque, LOW en reset = GNSS apagado)",
    "SD_D2": "SD_MMC D2 (10k)",
    "SD_DET": "Detección de tarjeta: HIGH con tarjeta (inversor con AO3401A)",
    "ESP_BOOT": "BOOT (pulsador a GND, 10k a 3V3)",
    "ESP_EN": "EN (RC 10k/1uF y pulsador RESET)",
    "ESP_TXD0": "U0TXD: mensajes de la ROM al arrancar; punto de prueba TP208",
    "ESP_RXD0": "U0RXD; punto de prueba TP209",
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
    comp_info = {}
    for c in findall(find(t, "components"), "comp"):
        ls = find(c, "libsource")
        ref = str(find(c, "ref")[1])
        comp_lib[ref] = str(find(ls, "lib")[1]) + ":" + str(find(ls, "part")[1])
        fields = {str(find(f, "name")[1]): (str(f[2]) if len(f) > 2 else "")
                  for f in findall(find(c, "fields") or [], "field")}
        props = {str(find(p, "name")[1]) for p in findall(c, "property")}
        comp_info[ref] = {"value": str(find(c, "value")[1]), "mpn": fields.get("MPN", ""),
                          "lcsc": fields.get("LCSC", ""), "desc": fields.get("Description", ""),
                          "dnp": "dnp" in props}
    for n in findall(find(t, "nets"), "net"):
        name = str(find(n, "name")[1]).split("/")[-1]
        for x in findall(n, "node"):
            pins.setdefault(str(find(x, "ref")[1]), {})[str(find(x, "pin")[1])] = name
    lines = ["# Mapa de pines generado desde la netlist", "",
             "Generado por `scripts/doc_tables.py`; no editar a mano.", "", "## ESP32-S3-WROOM-1-N16R2 (U201)", "",
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
    for ref in sorted((r for r in pins if r.startswith("J")), key=lambda r: int(re.sub(r"\D", "", r) or 0)):
        info = comp_info.get(ref, {})
        lines += ["", "## %s %s" % (ref, info.get("value", "")), ""]
        if info.get("mpn"):
            lines.append("%s (LCSC %s)%s. %s" % (info["mpn"], info.get("lcsc", "-"),
                                                 ", sin montar" if info.get("dnp") else "", info.get("desc", "")))
            lines.append("")
        lines += ["| Pin | Red |", "| --- | --- |"]
        for num in sorted(pins.get(ref, {}), key=lambda k: (not k.isdigit(), int(k) if k.isdigit() else 0, k)):
            lines.append("| %s | %s |" % (num, pins[ref][num]))
    with open(out, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")
    print("tablas:", out)


if __name__ == "__main__":
    main()
