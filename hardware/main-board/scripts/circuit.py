"""Descripción del circuito de la placa principal TresVizo (MeridianV) y generación del esquemático.

    python3 circuit.py <dir_simbolos_kicad> <kicad_dir>

Escribe las hojas .kicad_sch, el proyecto .kicad_pro, las tablas de bibliotecas y board.json.
Los valores y las decisiones están justificados en ../research/*.md y en ../README.md.
Variante por defecto: batería 1S. Las piezas de la variante 2S van sin montar (DNP) y se
listan en la documentación.
"""

import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from schgen import Design  # noqa: E402
from symlib import Libraries  # noqa: E402

PROJECT = "tresvizo-main"

# --------------------------------------------------------------- piezas comunes
R0402 = "Resistor_SMD:R_0402_1005Metric"
R0603 = "Resistor_SMD:R_0603_1608Metric"
C0402 = "Capacitor_SMD:C_0402_1005Metric"
C0603 = "Capacitor_SMD:C_0603_1608Metric"
C0805 = "Capacitor_SMD:C_0805_2012Metric"
LC = "tresvizo_lcsc:"
TP = "TestPoint:TestPoint_Pad_D1.0mm"

# valor -> (huella, LCSC, MPN)
RES = {
    "0": (R0402, "C17168", "0402WGF0000TCE"),
    "100": (R0402, "C25076", "0402WGF1000TCE"),
    "1k": (R0402, "C11702", "0402WGF1001TCE"),
    "4.7k": (R0402, "C25900", "0402WGF4701TCE"),
    "5.1k": (R0402, "C25905", "0402WGF5101TCE"),
    "10k": (R0402, "C25744", "0402WGF1002TCE"),
    "22k": (R0402, "C25768", "0402WGF2202TCE"),
    "30k": (R0603, "C22984", "0603WAF3002T5E"),
    "100k": (R0402, "C25741", "0402WGF1003TCE"),
    "1M": (R0402, "C26083", "0402WGF1004TCE"),
    # Solo variante 2S
    "8.2k": (R0402, "C25924", "0402WGF8201TCE"),
    "3.9k": (R0402, "C51721", "0402WGF3901TCE"),
}
CAP = {
    "100pF": (C0402, "C1546", "0402CG101J500NT", "100pF 50V C0G"),
    "47nF": (C0603, "C1622", "CL10B473KB8NNNC", "47nF 50V X7R"),
    "100nF": (C0402, "C307331", "CL05B104KB54PNC", "100nF 50V X7R"),
    "1uF": (C0402, "C52923", "CL05A105KA5NQNC", "1uF 25V X5R"),
    "4.7uF": (C0603, "C19666", "CL10A475KO8NNNC", "4.7uF 16V X5R"),
    "10uF": (C0805, "C15850", "CL21A106KAYNNNE", "10uF 25V X5R"),
    "22uF": (C0805, "C45783", "CL21A226MAQNNNE", "22uF 25V X5R"),
}


def build(libs):
    d = Design(libs, PROJECT, "TresVizo MeridianV — placa principal", "0.1", "2026-10-04", "TresVizo",
               comments=["Exploratorio: no fabricado ni probado",
                         "UM980 + ESP32-S3-MINI-1-N4R2 + BMI088 + BQ25798 (1S; 2S por variante)",
                         "JLCPCB 4 capas JLC04161H-7628, 50 x 76 mm"])
    d.sheet("power", "power.kicad_sch", "Alimentación, carga y batería")
    d.sheet("mcu", "mcu.kicad_sch", "ESP32-S3")
    d.sheet("gnss", "gnss.kicad_sch", "GNSS UM980 y antena")
    d.sheet("io", "io.kicad_sch", "microSD, IMU y panel")
    count = {}

    def ref(prefix, sheet):
        base = {"power": 100, "mcu": 200, "gnss": 300, "io": 400}[sheet]
        k = (prefix, sheet)
        count[k] = count.get(k, 0) + 1
        return "%s%d" % (prefix, base + count[k])

    def R(sheet, group, value, a, b, rot=90, dnp=False, note=None):
        fp, lcsc, mpn = RES[value]
        return d.add(ref("R", sheet), "Device:R", value, sheet, group, {"1": a, "2": b}, footprint=fp,
                     rot=rot, lcsc=lcsc, mpn=mpn, dnp=dnp, description=note)

    def C(sheet, group, value, a, b="GND", rot=0, dnp=False):
        fp, lcsc, mpn, desc = CAP[value]
        return d.add(ref("C", sheet), "Device:C", value, sheet, group, {"1": a, "2": b}, footprint=fp,
                     rot=rot, lcsc=lcsc, mpn=mpn, dnp=dnp, description=desc)

    def TPt(sheet, group, net, name):
        return d.add(ref("TP", sheet), "Connector:TestPoint", name, sheet, group, {"1": net}, footprint=TP,
                     in_bom=False)

    def FLAG(sheet, group, net):
        n = sum(1 for p in d.parts if p.ref.startswith("#FLG")) + 1
        return d.add("#FLG%02d" % n, "power:PWR_FLAG", "PWR_FLAG", sheet, group, {"1": net}, in_bom=False)

    # =================================================================== POWER
    s = "power"
    d.group(s, "usb", "Entrada USB-C del panel (5 V, datos al ESP32)", 150)
    d.group(s, "chg", "Cargador BQ25798 (buck-boost NVDC, 1S por defecto; 2S por PROG)", 230)
    d.group(s, "bat", "Batería: polaridad inversa, FET de apagado (ship) y medidor", 200)
    d.group(s, "buck", "3.3 V: TPS62903 (3-17 V, 3 A, modo 100 %)", 170)
    d.group(s, "gsw", "Riel conmutado del UM980", 120)
    d.group(s, "flags", "Banderas de alimentación (ERC)", 120)

    d.add("J101", "Connector_Generic_MountingPin:Conn_01x06_MountingPin", "PANEL_USB", s, "usb",
          {"1": "VBUS", "2": "VBUS", "3": "GND", "4": "USB_DN", "5": "USB_DP", "6": "GND", "MP": "GND"},
          footprint=LC + "CONN-SMD_6P-P2.00_B6B-PH-SM4-TB-LF-SN", lcsc="C471518", mpn="B6B-PH-SM4-TB(LF)(SN)",
          description="JST PH 6 vertical: VBUS x2, GND, D-, D+, GND al breakout USB-C del panel (con 5.1k en CC)")
    d.add("D101", "Device:D_Zener", "SMF20A", s, "usb", {"1": "VBUS", "2": "GND"}, rot=90,
          footprint=LC + "SOD-123F_L2.8-W1.8-LS3.7-RD", lcsc="C123788", mpn="SMF20A",
          description="TVS de VBUS, 20 V de trabajo (el BQ25798 admite hasta 30 V)")
    d.add("U101", "Power_Protection:USBLC6-2SC6", "USBLC6-2SC6", s, "usb",
          {"1": "USB_DN", "6": "USB_DN", "3": "USB_DP", "4": "USB_DP", "5": "+3V3", "2": "GND"},
          footprint=LC + "SOT-23-6_L2.9-W1.6-P0.95-LS2.8-BL", lcsc="C2687116", mpn="USBLC6-2SC6",
          description="ESD de D+/D-; pin 5 a +3V3 (rompe a 6 V, no va a VBUS)")
    R(s, "usb", "0", "USB_DP", "CHG_DP", dnp=True, note="Opcional: D+ al BQ25798 para BC1.2 (sin montar)")
    R(s, "usb", "0", "USB_DN", "CHG_DN", dnp=True, note="Opcional: D- al BQ25798 para BC1.2 (sin montar)")

    d.add("U102", "Battery_Management:BQ25798", "BQ25798RQMR", s, "chg",
          {"VBUS": "VBUS", "VAC1": "VBUS", "VAC2": "VBUS", "ACDRV1": "GND", "ACDRV2": "GND",
           "PMID": "PMID", "SW1": "CHG_SW1", "SW2": "CHG_SW2", "BTST1": "CHG_BTST1", "BTST2": "CHG_BTST2",
           "REGN": "REGN", "D+": "CHG_DP", "D-": "CHG_DN", "~{QON}": "BTN_N", "~{CE}": "GND",
           "SCL": "I2C_SCL", "SDA": "I2C_SDA", "TS": "CHG_TS", "ILIM_HIZ": "CHG_ILIM", "BATP": "CHG_BATP",
           "PROG": "CHG_PROG", "~{INT}": "CHG_INT_N", "BAT": "VBAT_CHG", "SDRV": "CHG_SDRV", "SYS": "VSYS",
           "GND": "GND", "STAT": "CHG_STAT"},
          footprint="Package_DFN_QFN:Texas_RQM0029A_VQFN-29_4x4mm_P0.4mm", lcsc="C2876593", mpn="BQ25798RQMR",
          datasheet="https://www.ti.com/lit/ds/symlink/bq25798.pdf",
          description="Cargador I2C 0x6B; compatible pin a pin con BQ25792 (ICHG por defecto 1 A en el 98)")
    d.add("L101", "Device:L", "2.2uH", s, "chg", {"1": "CHG_SW1", "2": "CHG_SW2"}, rot=90,
          footprint=LC + "IND-SMD_L5.4-W5.2", lcsc="C408408", mpn="MWSA0503S-2R2MT",
          description="2.2 uH, 29 mOhm, Isat 5.6 A (750 kHz); alternativa compacta de la MWSA0603S")
    C(s, "chg", "47nF", "CHG_BTST1", "CHG_SW1")
    C(s, "chg", "47nF", "CHG_BTST2", "CHG_SW2")
    C(s, "chg", "4.7uF", "REGN")
    # VBUS: TI pide >= 2 uF efectivos (2 x 10 uF); un 22 uF/25 V da ~10 uF efectivos a 5 V.
    C(s, "chg", "22uF", "VBUS")
    C(s, "chg", "100nF", "VBUS")
    for _ in range(3):
        C(s, "chg", "10uF", "PMID")
    C(s, "chg", "100nF", "PMID")
    # SYS: TI pide >= 6 uF efectivos; 2 x 22 uF + 10 uF (25 V) superan el valor de 5 x 10 uF con menos piezas.
    C(s, "chg", "22uF", "VSYS")
    C(s, "chg", "22uF", "VSYS")
    C(s, "chg", "10uF", "VSYS")
    C(s, "chg", "100nF", "VSYS")
    # BAT: TI pide >= 3 uF efectivos (2 x 10 uF); un 22 uF/25 V da ~10 uF efectivos a 4.2 V.
    C(s, "chg", "22uF", "VBAT_CHG")
    R(s, "chg", "10k", "REGN", "CHG_ILIM", note="ILIM_HIZ: con 22k da ~2.9 A de techo de entrada")
    R(s, "chg", "22k", "CHG_ILIM", "GND")
    v2s = d.variant2s = {}
    v2s["prog"] = R(s, "chg", "4.7k", "CHG_PROG", "GND", note="PROG: 4.7k = 1S a 750 kHz; 2S: 8.2k")
    R(s, "chg", "5.1k", "REGN", "CHG_TS")
    R(s, "chg", "30k", "CHG_TS", "GND")
    R(s, "chg", "10k", "CHG_TS", "GND", note="Sustituye a la NTC (~25 C). Sin montar si se usa NTC en J403")
    R(s, "chg", "100", "VPACK", "CHG_BATP", note="BATP: 100 ohm en serie, Kelvin a VPACK")
    R(s, "chg", "10k", "+3V3", "CHG_INT_N")
    R(s, "chg", "1k", "CHG_STAT", "CHG_LED_K", note="LED de carga del panel (ánodo a +3V3)")

    d.add("Q101", "Transistor_FET:AO3400A", "AO3400A", s, "bat",
          {"G": "CHG_SDRV", "S": "VBAT_CHG", "D": "VPACK"}, footprint=LC + "SOT-23-3_L2.9-W1.3-P1.90-LS2.4-BR",
          lcsc="C20917", mpn="AO3400A", description="FET de apagado (ship): obligatorio en BQ2579x rev D")
    d.add("Q102", "Transistor_FET:AO3401A", "AO3401A", s, "bat",
          {"G": "BATREV_G", "S": "VPACK", "D": "VBATT_IN"}, footprint=LC + "SOT-23_L2.9-W1.3-P1.90-LS2.4-BR",
          lcsc="C15127", mpn="AO3401A", description="Protección contra celda invertida (lado positivo)")
    R(s, "bat", "1M", "VPACK", "BATREV_G")
    d.add("Q103", "Transistor_FET:AO3400A", "AO3400A", s, "bat",
          {"G": "BATREV_SENSE", "S": "GND", "D": "BATREV_G"}, footprint=LC + "SOT-23-3_L2.9-W1.3-P1.90-LS2.4-BR",
          lcsc="C20917", mpn="AO3400A", description="Enciende Q102 solo si el borne de la celda es positivo")
    R(s, "bat", "100k", "VBATT_IN", "BATREV_SENSE")
    R(s, "bat", "1M", "BATREV_SENSE", "GND")
    d.add("J102", "Connector_Generic_MountingPin:Conn_01x02_MountingPin", "BATTERY", s, "bat",
          {"1": "GND", "2": "VBATT_IN", "MP": "GND"}, footprint=LC + "CONN-SMD_P2.00_S2B-PH-SM4-TB-LF-SN",
          lcsc="C295747", mpn="S2B-PH-SM4-TB(LF)(SN)", description="JST PH 2: 1 = BAT-, 2 = BAT+ (medir el pack)")
    v2s["fg"] = d.add("U103", "tresvizo:MAX17048", "MAX17048G+T10", s, "bat",
          {"VDD": "FG_VDD", "CELL": "VPACK", "CTG": "GND", "QSTRT": "GND", "SDA": "I2C_SDA", "SCL": "I2C_SCL",
           "~{ALRT}": "FG_ALRT_N", "GND": "GND", "EP": "GND"},
          footprint=LC + "TDFN-8_L2.0-W2.0-P0.50-BL-EP1.2", lcsc="C2682616", mpn="MAX17048G+T10",
          description="Medidor I2C 0x36 (2S: MAX17049G+T10 C18185545, VDD regulado)")
    C(s, "bat", "100nF", "FG_VDD")
    v2s["fgv1"] = R(s, "bat", "0", "VPACK", "FG_VDD", note="1S: VDD del medidor desde VPACK (2S: sin montar)")
    R(s, "bat", "10k", "+3V3", "FG_ALRT_N")
    v2s["fgv2"] = R(s, "bat", "0", "+3V3", "FG_VDD", dnp=True,
                    note="Solo 2S: VDD del MAX17049 desde +3V3 (pierde el estado en cada apagado)")

    d.add("U105", "tresvizo:TPS62903", "TPS62903RPJR", s, "buck",
          {"VIN": "VSYS", "EN": "BUCK_EN", "MODE": "GND", "SS/TR": "BUCK_SS", "SW": "BUCK_SW", "VOS": "+3V3",
           "FB": "BUCK_FB", "PG": None, "GND": "GND"}, lcsc="C2866502", mpn="TPS62903RPJR")
    C(s, "buck", "10uF", "VSYS")
    C(s, "buck", "100nF", "VSYS")
    R(s, "buck", "22k", "VSYS", "BUCK_EN", note="EN: enciende ~3.24 V, apaga ~2.88 V (1S). 2S: 3.9k abajo")
    v2s["en_bot"] = R(s, "buck", "10k", "BUCK_EN", "GND")
    C(s, "buck", "47nF", "BUCK_SS")
    d.add("L102", "Device:L", "1uH", s, "buck", {"1": "BUCK_SW", "2": "+3V3"}, rot=90,
          footprint=LC + "L2520", lcsc="C435392", mpn="DFE252012F-1R0M=P2", description="1 uH 2520")
    R(s, "buck", "100k", "+3V3", "BUCK_FB", note="FB: 0.6 V x (1 + 100k/22k) = 3.33 V")
    R(s, "buck", "22k", "BUCK_FB", "GND")
    for _ in range(2):
        C(s, "buck", "22uF", "+3V3")
    C(s, "buck", "100nF", "+3V3")

    d.add("U106", "tresvizo:TPS22919DCK_QOD", "TPS22919DCKR", s, "gsw",
          {"IN": "+3V3", "ON": "GNSS_PWR_EN", "QOD": "GNSS_SW", "OUT": "GNSS_SW", "GND": "GND"},
          footprint=LC + "SC-70-6_L2.2-W1.3-P0.65-LS2.1-BR", lcsc="C2149796", mpn="TPS22919DCKR",
          description="Riel del UM980: rampa ~1 ms y descarga rápida; apagado en reset")
    C(s, "gsw", "1uF", "+3V3")
    R(s, "gsw", "100k", "GNSS_PWR_EN", "GND", note="GPIO45 bajo en reset (pin de arranque) = UM980 apagado")
    d.add("FB101", "Device:FerriteBead_Small", "BLM18PG121SN1D", s, "gsw", {"1": "GNSS_SW", "2": "+3V3_GNSS"},
          rot=90, footprint=LC + "L0603", lcsc="C14709", mpn="BLM18PG121SN1D")

    for net in ("VBUS", "VBATT_IN", "VPACK", "FG_VDD", "+3V3", "+3V3_GNSS", "GND"):
        FLAG(s, "flags", net)

    # ===================================================================== MCU
    s = "mcu"
    d.group(s, "mod", "ESP32-S3-MINI-1-N4R2 (mismo módulo que la Thing Plus)", 230)
    d.group(s, "boot", "Arranque, reset y pines de configuración", 160)
    d.group(s, "i2c", "Bus I2C (OLED 0x3C, MAX17048 0x36, BQ25798 0x6B)", 120)
    d.group(s, "tps", "Puntos de prueba", 200)
    esp = {
        "GND": "GND", "3V3": "+3V3", "EN": "ESP_EN",
        "IO0": "ESP_BOOT", "IO1": "GNSS_PPS_MCU", "IO2": "CHG_INT_N", "IO3": "ESP_IO3",
        "IO4": "GNSS_RESET_MCU", "IO5": "GNSS_TXD3_MCU", "IO6": "ESP_TX1", "IO7": "LED_R",
        "IO8": "I2C_SDA", "IO9": "I2C_SCL", "IO10": "BTN_SENSE_N", "IO11": "IMU_MOSI", "IO12": "IMU_SCK",
        "IO13": "IMU_MISO", "IO14": "ESP_IO14", "IO15": "IMU_CS_ACC_N", "IO16": "IMU_CS_GYR_N",
        "IO17": "IMU_INT1", "IO18": "IMU_INT3", "USB_D-": "USB_DN", "USB_D+": "USB_DP", "IO21": "LED_G",
        "IO26": None, "IO33": "SD_D3", "IO34": "SD_CMD", "IO35": "FG_ALRT_N", "IO36": "LED_B",
        "IO37": "BTN_LED_EN", "IO38": "SD_CLK", "IO39": "SD_D0", "IO40": "SD_D1", "IO41": "ANT_FAULT_N",
        "IO42": "ESP_IO42", "TXD0": "ESP_TX0", "RXD0": "GNSS_TXD2_MCU", "IO45": "GNSS_PWR_EN",
        "IO46": None, "IO47": "SD_D2", "IO48": "SD_DET",
    }
    sym = libs.get("tresvizo:ESP32-S3-MINI-1_LCSC")
    pins = {}
    for p in sym.pins:
        if p.name in esp:
            pins[p.number] = esp[p.name]
        elif p.name == "GND":
            pins[p.number] = "GND"
    missing = [p.name for p in sym.pins if p.number not in pins and p.etype != "no_connect"]
    for p in sym.pins:
        if p.number not in pins and p.etype == "no_connect":
            pass
    if missing:
        raise SystemExit("ESP32 sin asignar: %s" % missing)
    d.add("U201", "tresvizo:ESP32-S3-MINI-1_LCSC", "ESP32-S3-MINI-1-N4R2", s, "mod", pins,
          footprint=LC + "BULETM-SMD_ESP32-S3-MINI-1-N8", lcsc="C3013941", mpn="ESP32-S3-MINI-1-N4R2",
          description="4 MB flash, 2 MB PSRAM quad; mismos GPIO que la Thing Plus")
    C(s, "mod", "22uF", "+3V3")
    C(s, "mod", "100nF", "+3V3")
    R(s, "boot", "10k", "+3V3", "ESP_EN")
    C(s, "boot", "1uF", "ESP_EN")
    d.add("SW201", "Switch:SW_Push", "RESET", s, "boot", {"1": "ESP_EN", "2": "GND"}, rot=90,
          footprint=LC + "SW-SMD_L3.9-W3.0-P4.45", lcsc="C720477", mpn="TS-1088-AR02016")
    R(s, "boot", "10k", "+3V3", "ESP_BOOT")
    d.add("SW202", "Switch:SW_Push", "BOOT", s, "boot", {"1": "ESP_BOOT", "2": "GND"}, rot=90,
          footprint=LC + "SW-SMD_L3.9-W3.0-P4.45", lcsc="C720477", mpn="TS-1088-AR02016")
    R(s, "boot", "10k", "ESP_IO3", "GND", note="GPIO3 (pin de arranque) sin dejar al aire")
    R(s, "i2c", "4.7k", "+3V3", "I2C_SDA")
    R(s, "i2c", "4.7k", "+3V3", "I2C_SCL")
    for net, name in (("+3V3", "3V3"), ("GND", "GND"), ("ESP_IO14", "IO14"), ("ESP_IO42", "IO42"),
                      ("ESP_TX0", "TXD0"), ("USB_DP", "D+"), ("USB_DN", "D-")):
        TPt(s, "tps", net, name)

    # ==================================================================== GNSS
    s = "gnss"
    d.group(s, "um", "Unicore UM980 (LGA soldado; COM2 y COM3 al ESP32, COM1 al conector auxiliar)", 260)
    d.group(s, "ser", "Resistencias serie (100 ohm desde el UM980, 1 k hacia el UM980)", 220)
    d.group(s, "ant", "Antena activa: límite de corriente, bias-T y u.FL (manual Unicore, fig. 3-2)", 220)
    d.group(s, "aux", "Puerto auxiliar UM980 (UPrecise, PPS, EVENT)", 140)
    d.add("U301", "tresvizo:UM980", "UM980", s, "um",
          {"VCC": "+3V3_GNSS", "V_BCKP": "GNSS_VBCKP", "RESET_N": "GNSS_RESET_N",
           "RXD1": "GNSS_RXD1", "RXD2": "GNSS_RXD2", "RXD3": "GNSS_RXD3", "EVENT": "GNSS_EVENT",
           "BIF1": "GNSS_BIF1", "BIF2": "GNSS_BIF2", "ANT_IN": "GNSS_ANT_IN", "ANT_DETECT": None,
           "ANT_SHORT_N": None, "ANT_OFF": None, "VCC_RF": None, "TXD1": "GNSS_TXD1", "TXD2": "GNSS_TXD2",
           "TXD3": "GNSS_TXD3", "PPS": "GNSS_PPS", "PVT_STAT": "GNSS_PVT", "RTK_STAT": "GNSS_RTK",
           "ERR_STAT": "GNSS_ERR", "SPIS_CSN": None, "SPIS_MOSI": None, "SPIS_CLK": None, "SPIS_MISO": None,
           "SDA": None, "SCL": None, "GND": "GND"},
          mpn="UM980", description="No lo vende LCSC: se consigna a JLCPCB o se suelda aparte (MSL 3)")
    for v in ("22uF", "22uF", "10uF", "100nF", "100pF"):
        C(s, "um", v, "+3V3_GNSS")
    R(s, "um", "0", "+3V3", "GNSS_VBCKP", note="V_BCKP desde +3V3: arranque en caliente si solo se apaga el UM980")
    C(s, "um", "1uF", "GNSS_VBCKP")
    FLAG(s, "um", "GNSS_VBCKP")
    R(s, "um", "10k", "+3V3_GNSS", "GNSS_RESET_N")
    R(s, "um", "10k", "+3V3_GNSS", "GNSS_BIF1", note="BIF: 10k a VCC y punto de prueba (Unicore)")
    R(s, "um", "10k", "+3V3_GNSS", "GNSS_BIF2")
    R(s, "um", "100k", "GNSS_EVENT", "GND")
    for net, name in (("GNSS_BIF1", "BIF1"), ("GNSS_BIF2", "BIF2"), ("GNSS_PVT", "PVT"), ("GNSS_RTK", "RTK"),
                      ("GNSS_ERR", "ERR"), ("+3V3_GNSS", "3V3_GNSS")):
        TPt(s, "um", net, name)
    # Serie hacia/desde el ESP32
    R(s, "ser", "1k", "ESP_TX0", "GNSS_RXD2", note="GPIO43 (U0TXD) -> RXD2: limita la alimentación parásita")
    R(s, "ser", "100", "GNSS_TXD2", "GNSS_TXD2_MCU")
    R(s, "ser", "1k", "ESP_TX1", "GNSS_RXD3")
    R(s, "ser", "100", "GNSS_TXD3", "GNSS_TXD3_MCU")
    R(s, "ser", "100", "GNSS_PPS", "GNSS_PPS_MCU")
    R(s, "ser", "100", "GNSS_RESET_MCU", "GNSS_RESET_N", note="GPIO4 en drenador abierto, pulso >= 5 ms")
    # Antena
    d.add("U302", "tresvizo:TPS22945", "TPS22945DCKR", s, "ant",
          {"VIN": "+3V3_GNSS", "ON": "+3V3_GNSS", "VOUT": "ANT_BIAS", "OC": "ANT_FAULT_N", "GND": "GND"},
          lcsc="C47507", mpn="TPS22945DCKR", description="ANT_BIAS propio con límite de 100-200 mA y aviso OC")
    C(s, "ant", "1uF", "+3V3_GNSS")
    R(s, "ant", "10k", "+3V3", "ANT_FAULT_N")
    d.add("D301", "Device:D_Zener", "SMF5.0A", s, "ant", {"1": "ANT_BIAS", "2": "GND"}, rot=90,
          footprint=LC + "SOD-123FL_L2.7-W1.8-LS3.8-RD", lcsc="C19077497", mpn="SMF5.0A")
    C(s, "ant", "100nF", "ANT_BIAS")
    C(s, "ant", "100pF", "ANT_BIAS")
    d.add("L301", "Device:L", "68nH", s, "ant", {"1": "ANT_BIAS", "2": "ANT_RF"}, rot=90,
          footprint=LC + "L0603", lcsc="C86135", mpn="LQW18AN68NG00D", description="Choke RF 0603, SRF > 2.2 GHz")
    d.add("D302", "Device:D_TVS", "PESD5V0F1BL", s, "ant", {"1": "ANT_RF", "2": "GND"}, rot=90,
          footprint=LC + "SOD-882_L1.0-W0.6-BI", lcsc="C45961", mpn="PESD5V0F1BL,315",
          description="ESD de RF, 0.4 pF")
    C(s, "ant", "100pF", "ANT_RF", "GNSS_ANT_IN", rot=90)
    d.add("J301", "tresvizo:U.FL", "U.FL", s, "ant", {"1": "ANT_RF", "2": "GND", "3": "GND"},
          lcsc="C5137195", mpn="BWU.FL-IPEX1", description="Coaxial a la antena helix (latiguillo u.FL-SMA)")
    # Auxiliar
    d.add("J302", "Connector_Generic_MountingPin:Conn_01x05_MountingPin", "UM980_AUX", s, "aux",
          {"1": "GND", "2": "AUX_TXD1", "3": "AUX_RXD1", "4": "AUX_PPS", "5": "AUX_EVENT", "MP": "GND"},
          footprint=LC + "CONN-SMD_5P-P1.00_BM05B-SRSS-TB", lcsc="C160391", mpn="BM05B-SRSS-TB(LF)(SN)",
          description="JST SH 5: GND, TXD1, RXD1, PPS, EVENT (adaptador USB-UART de 3.3 V)")
    R(s, "aux", "100", "GNSS_TXD1", "AUX_TXD1")
    R(s, "aux", "1k", "AUX_RXD1", "GNSS_RXD1")
    R(s, "aux", "1k", "GNSS_PPS", "AUX_PPS")
    R(s, "aux", "1k", "AUX_EVENT", "GNSS_EVENT")

    # ====================================================================== IO
    s = "io"
    d.group(s, "sd", "microSD (SD_MMC 4 bits, mismos GPIO que la Thing Plus)", 200)
    d.group(s, "imu", "IMU BMI088 en el eje del jalón (SPI)", 200)
    d.group(s, "ui", "Panel: botón, LEDs y OLED", 260)
    d.add("J401", "tresvizo:TF-015", "TF-015", s, "sd",
          {"VDD": "+3V3", "CLK": "SD_CLK", "CMD": "SD_CMD", "DAT0": "SD_D0", "DAT1": "SD_D1", "DAT2": "SD_D2",
           "DAT3": "SD_D3", "CD": "SD_CD_N", "VSS": "GND", "SHIELD": "GND"}, lcsc="C113206", mpn="TF-015")
    for net in ("SD_CMD", "SD_D0", "SD_D1", "SD_D2", "SD_D3", "SD_CD_N"):
        R(s, "sd", "10k", "+3V3", net)
    C(s, "sd", "10uF", "+3V3")
    C(s, "sd", "100nF", "+3V3")
    d.add("Q401", "Transistor_FET:AO3401A", "AO3401A", s, "sd", {"G": "SD_CD_N", "S": "+3V3", "D": "SD_DET"},
          footprint=LC + "SOT-23_L2.9-W1.3-P1.90-LS2.4-BR", lcsc="C15127", mpn="AO3401A",
          description="Invierte la detección: GPIO48 HIGH con tarjeta, como espera el firmware")
    R(s, "sd", "100k", "SD_DET", "GND")

    d.add("U401", "tresvizo:BMI088_SPI", "BMI088", s, "imu",
          {"VDD": "+3V3", "VDDIO": "+3V3", "GNDA": "GND", "GNDIO": "GND", "PS": "GND", "SCK/SCL": "IMU_SCK",
           "SDI/SDA": "IMU_MOSI", "SDO1": "IMU_MISO", "SDO2": "IMU_MISO", "~{CSB1}": "IMU_CS_ACC_N",
           "~{CSB2}": "IMU_CS_GYR_N", "INT1": "IMU_INT1", "INT3": "IMU_INT3", "INT2": None, "INT4": None},
          footprint=LC + "LGA-16_L4.5-W3.0-P0.50-BL", lcsc="C194919", mpn="BMI088",
          description="Acelerómetro + giróscopo; PS a GND = SPI; centro sobre el eje del jalón")
    C(s, "imu", "100nF", "+3V3")
    C(s, "imu", "100nF", "+3V3")

    d.add("J402", "Connector_Generic_MountingPin:Conn_01x09_MountingPin", "PANEL_UI", s, "ui",
          {"1": "GND", "2": "BTN_N", "3": "BTN_LED_A", "4": "BTN_LED_K", "5": "+3V3", "6": "LED_R_K",
           "7": "LED_G_K", "8": "LED_B_K", "9": "CHG_LED_K", "MP": "GND"},
          footprint=LC + "CONN-SMD_9P-P1.00_BM09B-SRSS-TB", lcsc="C160395", mpn="BM09B-SRSS-TB(LF)(SN)",
          description="JST SH 9: GND, botón, anillo LED A/K, ánodo LEDs (3V3), R, G, B, carga")
    d.add("D401", "Device:D_TVS", "PESD5V0F1BL", s, "ui", {"1": "BTN_N", "2": "GND"}, rot=90,
          footprint=LC + "SOD-882_L1.0-W0.6-BI", lcsc="C45961", mpn="PESD5V0F1BL,315",
          description="ESD del botón metálico")
    d.add("D402", "Device:D", "1N4148W", s, "ui", {"1": "BTN_N", "2": "BTN_SENSE_N"}, rot=90,
          footprint=LC + "SOD-123F_L2.7-W1.6-LS3.8-RD", lcsc="C81598", mpn="1N4148W",
          description="Aísla QON (pull-up interno a 3.2-3.8 V) del GPIO10; silicio, no Schottky")
    R(s, "ui", "10k", "+3V3", "BTN_SENSE_N")
    R(s, "ui", "1k", "LED_R", "LED_R_K")
    R(s, "ui", "100", "LED_G", "LED_G_K")
    R(s, "ui", "100", "LED_B", "LED_B_K")
    R(s, "ui", "100", "VSYS", "BTN_LED_A", note="Anillo del botón: usar la versión de 3-6 V (la de 12 V no enciende)")
    d.add("Q402", "Transistor_FET:AO3400A", "AO3400A", s, "ui", {"G": "BTN_LED_EN", "S": "GND", "D": "BTN_LED_K"},
          footprint=LC + "SOT-23-3_L2.9-W1.3-P1.90-LS2.4-BR", lcsc="C20917", mpn="AO3400A")
    R(s, "ui", "100k", "BTN_LED_EN", "GND")
    d.add("J403", "Connector_Generic_MountingPin:Conn_01x04_MountingPin", "OLED", s, "ui",
          {"1": "GND", "2": "+3V3", "3": "I2C_SDA", "4": "I2C_SCL", "MP": "GND"},
          footprint=LC + "CONN-SMD_BM04B-SRSS-TB", lcsc="C160390", mpn="BM04B-SRSS-TB(LF)(SN)",
          description="JST SH 4 con el orden Qwiic: GND, 3V3, SDA, SCL")
    d.add("J404", "Connector_Generic_MountingPin:Conn_01x02_MountingPin", "NTC", s, "ui",
          {"1": "CHG_TS", "2": "GND", "MP": "GND"}, footprint=LC + "CONN-TH_BM02B-SRSS-TB-LF-SN",
          lcsc="C160388", mpn="BM02B-SRSS-TB(LF)(SN)", dnp=True,
          description="Opcional: NTC 10k B3435 pegada a la celda (quitar el 10k fijo de TS)")
    return d


def write_project(kicad_dir, design):
    import layout
    style = {"wire_width": 6, "bus_width": 12, "line_style": 0, "pcb_color": "rgba(0, 0, 0, 0.000)",
             "schematic_color": "rgba(0, 0, 0, 0.000)"}
    classes = []
    for name, c in layout.NETCLASSES.items():
        nc = {"name": name, "clearance": c["clearance"], "track_width": c["track"], "via_diameter": c["via_dia"],
              "via_drill": c["via_drill"], "priority": c.get("priority", 2147483647)}
        if name == "USB":
            nc.update({"diff_pair_gap": 0.15, "diff_pair_width": c["track"]})
        nc.update(style)
        classes.append(nc)
    nets = {name: c["nets"] for name, c in layout.NETCLASSES.items() if c["nets"]}
    pro = {
        "board": {"design_settings": {
            "defaults": {"board_outline_line_width": 0.1, "copper_line_width": 0.2, "copper_text_size_h": 1.5,
                         "copper_text_size_v": 1.5, "silk_line_width": 0.15, "silk_text_size_h": 1.0,
                         "silk_text_size_v": 1.0, "silk_text_thickness": 0.15},
            "rules": {"min_clearance": 0.127, "min_connection": 0.127, "min_copper_edge_clearance": 0.3,
                      "min_hole_clearance": 0.25, "min_hole_to_hole": 0.5, "min_microvia_diameter": 0.2,
                      "min_microvia_drill": 0.1, "min_through_hole_diameter": 0.3, "min_track_width": 0.127,
                      "min_via_annular_width": 0.1, "min_via_diameter": 0.5, "min_text_height": 0.8,
                      "min_text_thickness": 0.12, "solder_mask_min_width": 0.1,
                      "min_resolved_spokes": 1},
            "track_widths": [0.0, 0.15, 0.2, 0.3, 0.5, 0.8, 1.0],
            "via_dimensions": [{"diameter": 0.0, "drill": 0.0}, {"diameter": 0.6, "drill": 0.3},
                               {"diameter": 0.8, "drill": 0.4}],
        }},
        "meta": {"filename": PROJECT + ".kicad_pro", "version": 3},
        "net_settings": {
            "classes": classes,
            "meta": {"version": 4},
            "netclass_patterns": [{"netclass": cls, "pattern": pat} for cls, ns in nets.items() for n in ns
                                  for pat in (n, "*/" + n)],
        },
        "schematic": {"drawing": {"default_line_thickness": 6.0, "default_text_size": 50.0}},
        "text_variables": {},
    }
    with open(os.path.join(kicad_dir, PROJECT + ".kicad_pro"), "w", encoding="utf-8") as f:
        json.dump(pro, f, indent=2)
    with open(os.path.join(kicad_dir, "sym-lib-table"), "w", encoding="utf-8") as f:
        f.write('(sym_lib_table\n  (version 7)\n'
                '  (lib (name "tresvizo")(type "KiCad")(uri "${KIPRJMOD}/lib/tresvizo.kicad_sym")(options "")'
                '(descr "Símbolos propios"))\n'
                '  (lib (name "tresvizo_lcsc")(type "KiCad")(uri "${KIPRJMOD}/lib/lcsc.kicad_sym")(options "")'
                '(descr "Símbolos importados de LCSC/EasyEDA"))\n)\n')
    with open(os.path.join(kicad_dir, "fp-lib-table"), "w", encoding="utf-8") as f:
        f.write('(fp_lib_table\n  (version 7)\n'
                '  (lib (name "tresvizo")(type "KiCad")(uri "${KIPRJMOD}/lib/tresvizo.pretty")(options "")'
                '(descr "Huellas propias"))\n'
                '  (lib (name "tresvizo_lcsc")(type "KiCad")(uri "${KIPRJMOD}/lib/lcsc.pretty")(options "")'
                '(descr "Huellas de LCSC/EasyEDA (orientación de JLCPCB)"))\n)\n')


def main():
    sym_dir, kicad_dir = sys.argv[1:3]
    libs = Libraries()
    for n in ("Device", "power", "Connector", "Connector_Generic_MountingPin", "Battery_Management", "Switch",
              "Sensor_Motion", "Power_Management", "Power_Protection", "Transistor_FET", "Regulator_Linear"):
        libs.add(os.path.join(sym_dir, n + ".kicad_sym"))
    libs.add(os.path.join(kicad_dir, "lib", "tresvizo.kicad_sym"), "tresvizo")
    d = build(libs)
    problems = d.check()
    for p in problems:
        print("AVISO:", p)
    d.note("_root", "Placa principal exploratoria de TresVizo MeridianV. Nada de esto se ha fabricado ni probado.")
    v = d.variant2s
    d.note("_root", "Variante 1S por defecto. Variante 2S: %s = 8.2k (PROG), %s = MAX17049G+T10, %s sin montar,"
           % (v["prog"].ref, v["fg"].ref, v["fgv1"].ref))
    d.note("_root", "%s montado (VDD del medidor desde +3V3) y %s (EN del buck, abajo) = 3.9k."
           % (v["fgv2"].ref, v["en_bot"].ref))
    d.write(kicad_dir)
    write_project(kicad_dir, d)
    try:
        import layout
    except ImportError:
        layout = None
    if layout:
        layout.write_board_json(d, kicad_dir)
    print("esquemático:", len([p for p in d.parts if not p.ref.startswith("#")]), "piezas,",
          len(d.netlist()), "redes")


if __name__ == "__main__":
    main()
