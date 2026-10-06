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

# JST GH de entrada lateral (SMxxB-GHS-TB, paso 1.25): huella importada de LCSC y código, por número de pines
# El SM08B-GHS-TB de JST está agotado en LCSC (04-10-2026): se monta el clon XUNPU de huella idéntica.
GH_FP = {8: "CONN-SMD_8P-P1.25_XUNPU-WAFER-GH1.25-8PWB"}
GH_LCSC = {8: "C3029383"}
GH_MPN = {8: "WAFER-GH1.25-8PWB"}
USBLC6_LCSC = "C2687116"


def gnss_5v(d, s, group, R, C):
    """5 V para la carrier GNSS desde VSYS con un buck-boost TPS63070 (sirve en 1S y en 2S).

    En apagado desconecta la carga (hoja SLVSC58B, p. 1): con GPIO45 bajo la carrier queda sin tensión.
    Salida 0.8 V x (1 + 5.1k / 1k) = 4.88 V (la carrier BDLX pide 4.0-5.5 V). Bobina de 1 uH con
    3 x 22 uF de salida: combinación de la tabla 3 de la hoja (valores nominales, ya con la caída por
    tensión). PS/SYNC a GND = PWM fijo de 2.4 MHz; VSEL a GND y FB2 al aire (no se usa); PG sin usar.
    """
    d.add("U301", "tresvizo:TPS63070", "TPS63070RNMR", s, group,
          {"VIN": "VSYS", "EN": "GNSS_PWR_EN", "PS/SYNC": "GND", "VSEL": "GND", "VAUX": "GNSS_VAUX",
           "L1": "GNSS_L1", "L2": "GNSS_L2", "VOUT": "GNSS_5V", "FB": "GNSS_FB", "FB2": None, "PG": None,
           "GND": "GND", "PGND": "GND"},
          lcsc="C109322", mpn="TPS63070RNMR", datasheet="https://www.ti.com/lit/ds/symlink/tps63070.pdf",
          description="Buck-boost 2-16 V a 4.88 V para la carrier GNSS; desconecta la carga apagado")
    d.add("L301", "Device:L", "1uH", s, group, {"1": "GNSS_L1", "2": "GNSS_L2"}, rot=90,
          footprint=LC + "L2520", lcsc="C435392", mpn="DFE252012F-1R0M=P2",
          description="1 uH 2520 (la misma que L102)")
    for _ in range(2):
        C(s, group, "10uF", "VSYS")
    C(s, group, "100nF", "VSYS")
    C(s, group, "100nF", "GNSS_VAUX")
    for _ in range(3):
        C(s, group, "22uF", "GNSS_5V")
    R(s, group, "5.1k", "GNSS_5V", "GNSS_FB", note="FB: 0.8 V x (1 + 5.1k/1k) = 4.88 V")
    R(s, group, "1k", "GNSS_FB", "GND")


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
    d = Design(libs, PROJECT, "TresVizo MeridianV — placa principal", "0.2", "2026-10-04", "TresVizo",
               comments=["Exploratorio: no fabricado ni probado",
                         "ESP32-S3-WROOM-1-N16R2 + BQ25798 (1S; 2S por variante); GNSS e IMU por conector",
                         "JLCPCB 4 capas JLC04161H-7628"])
    d.sheet("power", "power.kicad_sch", "Alimentación, carga y batería")
    d.sheet("mcu", "mcu.kicad_sch", "ESP32-S3")
    d.sheet("gnss", "gnss.kicad_sch", "GNSS: carrier UM980 por conector y su 5 V")
    d.sheet("io", "io.kicad_sch", "microSD, IMU por conector y panel")
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
    d.group(s, "flags", "Banderas de alimentación (ERC)", 120)

    # Enlace con la placa del USB-C del panel (pinout del propietario): 3 contactos por lado porque el GH
    # admite ~1 A por contacto con AWG26 (JST, eGH.pdf) y el peor caso (2S cargando) pide ~2.2 A.
    d.add("J101", "Connector_Generic_MountingPin:Conn_01x08_MountingPin", "PANEL_USB", s, "usb",
          {"1": "VBUS", "2": "VBUS", "3": "VBUS", "4": "GND", "5": "GND", "6": "GND", "7": "USB_DN", "8": "USB_DP",
           "MP": "GND"},
          footprint=LC + GH_FP[8], lcsc=GH_LCSC[8], mpn=GH_MPN[8],
          description="GH 8 lateral a la placa del USB-C del panel: VBUS x3, GND x3, D-, D+ (cable 1 a 1)")
    d.add("D101", "Device:D_Zener", "SMF15A", s, "usb", {"1": "VBUS", "2": "GND"}, rot=90,
          footprint=LC + "SOD-123FL_L2.7-W1.8-LS3.8-RD", lcsc="C19077509", mpn="SMF15A",
          description="TVS de VBUS: 15 V de trabajo, limita a 24.4 V a 8.2 A (VBUS del BQ25798: 30 V máx.)")
    d.add("U101", "Power_Protection:USBLC6-2SC6", "USBLC6-2SC6", s, "usb",
          {"1": "USB_DN", "6": "USB_DN", "3": "USB_DP", "4": "USB_DP", "5": "+3V3", "2": "GND"},
          footprint=LC + "SOT-23-6_L2.9-W1.6-P0.95-LS2.8-BL", lcsc="C2687116", mpn="USBLC6-2SC6",
          description="ESD de D+/D-; pin 5 a +3V3 (rompe a 6 V, no va a VBUS)")

    d.add("U102", "Battery_Management:BQ25798", "BQ25798RQMR", s, "chg",
          {"VBUS": "VBUS", "VAC1": "VBUS", "VAC2": "VBUS", "ACDRV1": "GND", "ACDRV2": "GND",
           "PMID": "PMID", "SW1": "CHG_SW1", "SW2": "CHG_SW2", "BTST1": "CHG_BTST1", "BTST2": "CHG_BTST2",
           "REGN": "REGN", "D+": None, "D-": None, "~{QON}": "BTN_N", "~{CE}": "GND",
           "SCL": "I2C_SCL", "SDA": "I2C_SDA", "TS": "CHG_TS", "ILIM_HIZ": "CHG_ILIM", "BATP": "CHG_BATP",
           "PROG": "CHG_PROG", "~{INT}": "CHG_INT_N", "BAT": "VBAT_CHG", "SDRV": "CHG_SDRV", "SYS": "VSYS",
           "GND": "GND", "STAT": None},
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
    # PMID: 2 x 22 uF/25 V (~10 uF efectivos cada uno a 5 V) en vez de 3 x 10 uF: más capacidad con una pieza
    # menos y el mismo número de parte que VBUS y SYS. D+/D- del cargador sin conectar (sin detección BC1.2).
    for _ in range(2):
        C(s, "chg", "22uF", "PMID")
    C(s, "chg", "100nF", "PMID")
    # SYS: TI pide >= 6 uF efectivos; 2 x 22 uF + 10 uF (25 V) superan el valor de 5 x 10 uF con menos piezas.
    C(s, "chg", "22uF", "VSYS")
    C(s, "chg", "22uF", "VSYS")
    C(s, "chg", "10uF", "VSYS")
    C(s, "chg", "100nF", "VSYS")
    # BAT: TI pide >= 3 uF efectivos (2 x 10 uF); un 22 uF/25 V da ~10 uF efectivos a 4.2 V.
    C(s, "chg", "22uF", "VBAT_CHG")
    R(s, "chg", "10k", "REGN", "CHG_ILIM", note="ILIM_HIZ: con 8.2k da ~1.45 A de techo de entrada (1S); 22k da ~2.9 A (2S)")
    R(s, "chg", "8.2k", "CHG_ILIM", "GND")
    v2s = d.variant2s = {}
    v2s["prog"] = R(s, "chg", "4.7k", "CHG_PROG", "GND", note="PROG: 4.7k = 1S a 750 kHz; 2S: 8.2k")
    R(s, "chg", "5.1k", "REGN", "CHG_TS")
    R(s, "chg", "30k", "CHG_TS", "GND")
    # 10k fijo en lugar de la NTC (el cargador ve ~25 C) mientras JP101 esté cerrado. JP101 es un puente de
    # cobre cerrado de fábrica: al conectar una NTC 10k B3435 en J404 se corta con un cúter (se vuelve a
    # cerrar con estaño), sin desoldar nada.
    R(s, "chg", "10k", "CHG_TS", "CHG_TS_FIJA", note="Sustituye a la NTC (~25 C) con JP101 cerrado")
    d.add("JP101", "Jumper:SolderJumper_2_Bridged", "NTC_CORTAR", s, "chg", {"1": "CHG_TS_FIJA", "2": "GND"},
          footprint=LC + "SolderJumper-2_P1.3mm_Bridged_RoundedPad1.0x1.5mm", in_bom=False,
          description="Puente cerrado de fábrica: cortarlo si se conecta una NTC en J404")
    R(s, "chg", "100", "VPACK", "CHG_BATP", note="BATP: 100 ohm en serie, Kelvin a VPACK")
    R(s, "chg", "10k", "+3V3", "CHG_INT_N")

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

    for net in ("VBUS", "VBATT_IN", "VPACK", "FG_VDD", "+3V3", "GND"):
        FLAG(s, "flags", net)

    # ===================================================================== MCU
    s = "mcu"
    d.group(s, "mod", "ESP32-S3-WROOM-1-N16R2 (16 MB de flash, 2 MB de PSRAM quad)", 230)
    d.group(s, "boot", "Arranque, reset y pines de configuración", 160)
    d.group(s, "i2c", "Bus I2C (OLED 0x3C, MAX17048 0x36, BQ25798 0x6B)", 120)
    d.group(s, "tps", "Puntos de prueba", 200)
    # Mapa de GPIO para el WROOM-1 (05-10-2026): cada grupo sale por el lado del módulo que mira a su
    # destino. Orilla de abajo -> microSD y botón; punta derecha -> GNSS, I2C del cargador y medidor;
    # orilla de arriba -> IMU. En el S3 la SD_MMC, las UART y el I2C van por la matriz de GPIO.
    esp = {
        "GND": "GND", "3V3": "+3V3", "EN": "ESP_EN",
        "IO0": "ESP_BOOT", "IO1": "IMU_INT3", "IO2": "IMU_INT1", "IO3": "ESP_IO3",
        "IO4": "SD_D1", "IO5": "SD_D0", "IO6": "SD_CLK", "IO7": "SD_CMD",
        "IO15": "SD_D3", "IO16": "SD_D2", "IO17": "SD_DET", "IO18": "BTN_SENSE_N",
        "IO8": "GNSS_TX_MCU", "USB_D-": "USB_DN", "USB_D+": "USB_DP",
        "IO46": None, "IO9": "GNSS_TXD2_MCU", "IO10": "GNSS_PPS_MCU", "IO11": "GNSS_EVENT_MCU",
        "IO12": "GNSS_RESET_MCU", "IO13": "I2C_SDA", "IO14": "I2C_SCL", "IO21": "CHG_INT_N",
        "IO47": "FG_ALRT_N", "IO48": "BTN_LED_EN", "IO45": "GNSS_PWR_EN",
        "IO35": "ESP_IO35", "IO36": "ESP_IO36", "IO37": "ESP_IO37", "IO38": None, "IO39": None, "IO40": None,
        "IO41": "IMU_SDA", "IO42": "IMU_SCL", "RXD0": None, "TXD0": None,
    }
    sym = libs.get("RF_Module:ESP32-S3-WROOM-1")
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
    d.add("U201", "RF_Module:ESP32-S3-WROOM-1", "ESP32-S3-WROOM-1-N16R2", s, "mod", pins,
          footprint=LC + "WIRELM-SMD_ESP32-S3-WROOM-1", lcsc="C2913205", mpn="ESP32-S3-WROOM-1-N16R2",
          description="16 MB flash, 2 MB PSRAM quad (GPIO35-37 libres); SD_MMC CMD/D3 en GPIO15/16 (el WROOM-1 no saca GPIO33/34)")
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
    for net, name in (("+3V3", "3V3"), ("GND", "GND"), ("ESP_IO35", "IO35"), ("ESP_IO36", "IO36"),
                      ("ESP_IO37", "IO37"), ("USB_DP", "D+"), ("USB_DN", "D-")):
        TPt(s, "tps", net, name)

    # ==================================================================== GNSS
    s = "gnss"
    d.group(s, "pwr", "5 V de la carrier GNSS desde VSYS, encendido por GPIO45 (modo «solo carga»: apagado)", 230)
    d.group(s, "conn", "Conector GH de 8 pines a la carrier BDLX (COM2, PPS, EVENT, RESET_N)", 260)
    R(s, "pwr", "100k", "GNSS_PWR_EN", "GND", note="GPIO45 bajo en reset (pin de arranque) = GNSS apagado")
    gnss_5v(d, s, "pwr", R, C)
    # Pinout pedido por el propietario. La carrier BDLX reparte esas señales en sus dos conectores
    # (GH de 5: 5V_IN, GND, PPS_OUT; GH de 8: TTL_TXD2, TTL_RXD2, GND, EVENT): mazo en Y, ver README.
    d.add("J301", "Connector_Generic_MountingPin:Conn_01x08_MountingPin", "GNSS", s, "conn",
          {"1": "GNSS_5V", "2": "GND", "3": "GNSS_RXD2", "4": "GNSS_TXD2", "5": "GNSS_PPS", "6": "GNSS_EVENT",
           "7": "GNSS_RESET_N", "8": "GND", "MP": "GND"},
          footprint=LC + "CONN-TH_SM08B-SRSS-TB-LF-SN", lcsc="C160407", mpn="SM08B-SRSS-TB(LF)(SN)",
          description="SH 8 lateral (JST SM08B-SRSS-TB): 5V, GND, RXD2, TXD2, PPS, EVENT, RESET_N, GND. "
                      "SH y no GH, para que no se pueda cruzar con J101 (GH 8 con VBUS)")
    # ESD junto al conector (la carrier va por cable); el pin 5 a +3V3 como en U101
    for k, (a_net, b_net) in enumerate((("GNSS_RXD2", "GNSS_TXD2"), ("GNSS_PPS", "GNSS_EVENT"))):
        d.add("U%d" % (302 + k), "Power_Protection:USBLC6-2SC6", "USBLC6-2SC6", s, "conn",
              {"1": a_net, "6": a_net, "3": b_net, "4": b_net, "5": "+3V3", "2": "GND"},
              footprint=LC + "SOT-23-6_L2.9-W1.6-P0.95-LS2.8-BL", lcsc=USBLC6_LCSC, mpn="USBLC6-2SC6",
              description="ESD de las señales del GNSS (cable a la carrier)")
    # Hacia la carrier 1 k: con la carrier apagada limita a ~3 mA lo que el ESP32 le mete por sus entradas
    # (la UART del GNSS va en GPIO8/9 por la matriz; GPIO43/44 quedan libres). Desde la carrier 100 ohm.
    R(s, "conn", "1k", "GNSS_TX_MCU", "GNSS_RXD2", note="GPIO8 (TX de la UART del GNSS) -> RXD2 de la carrier")
    R(s, "conn", "100", "GNSS_TXD2", "GNSS_TXD2_MCU", note="TXD2 de la carrier -> GPIO9 (RX de la UART del GNSS)")
    R(s, "conn", "100", "GNSS_PPS", "GNSS_PPS_MCU", note="PPS -> GPIO10")
    R(s, "conn", "1k", "GNSS_EVENT_MCU", "GNSS_EVENT", note="GPIO11 -> EVENT")
    R(s, "conn", "100k", "GNSS_EVENT_MCU", "GND", note="EVENT en bajo mientras el ESP32 arranca")
    R(s, "conn", "1k", "GNSS_RESET_MCU", "GNSS_RESET_N", note="GPIO12 en drenador abierto; la BDLX no saca RESET_N")
    TPt(s, "pwr", "GNSS_5V", "5V_GNSS")

    # ====================================================================== IO
    s = "io"
    d.group(s, "sd", "microSD (SD_MMC 4 bits, mismos GPIO que la Thing Plus)", 200)
    d.group(s, "imu", "IMU: breakout BMI088 V1.0 de la tapa por cable (I2C)", 200)
    d.group(s, "ui", "Panel: botón, LEDs y OLED", 300)
    d.add("J401", "tresvizo:TF-015", "TF-015", s, "sd",
          {"VDD": "+3V3", "CLK": "SD_CLK", "CMD": "SD_CMD", "DAT0": "SD_D0", "DAT1": "SD_D1", "DAT2": "SD_D2",
           "DAT3": "SD_D3", "CD": "SD_CD_N", "VSS": "GND", "SHIELD": "GND"}, lcsc="C113206", mpn="TF-015")
    for net in ("SD_CMD", "SD_D0", "SD_D1", "SD_D2", "SD_D3", "SD_CD_N"):
        R(s, "sd", "10k", "+3V3", net)
    C(s, "sd", "10uF", "+3V3")
    C(s, "sd", "100nF", "+3V3")
    d.add("Q401", "Transistor_FET:AO3401A", "AO3401A", s, "sd", {"G": "SD_CD_N", "S": "+3V3", "D": "SD_DET"},
          footprint=LC + "SOT-23_L2.9-W1.3-P1.90-LS2.4-BR", lcsc="C15127", mpn="AO3401A",
          description="Invierte la detección: GPIO17 HIGH con tarjeta")
    R(s, "sd", "100k", "SD_DET", "GND")

    # Panel en dos conectores de 8 pines o menos (kit de cables GH/SH del propietario); familias y números de
    # pines distintos de la OLED (SH4) para que no se puedan cruzar.
    d.add("J402", "Connector_Generic_MountingPin:Conn_01x04_MountingPin", "BOTON", s, "ui",
          {"1": "GND", "2": "BTN_N", "3": "BTN_LED_A", "4": "BTN_LED_K", "MP": "GND"},
          footprint=LC + "CONN-SMD_4P-P1.25_SM04B-GHS-TB-LF-SN", lcsc="C189895", mpn="SM04B-GHS-TB(LF)(SN)",
          description="GH 4 lateral al botón del panel: GND, contacto, anillo LED ánodo y cátodo")
    d.add("D401", "Device:D_TVS", "PESD5V0F1BL", s, "ui", {"1": "BTN_N", "2": "GND"}, rot=90,
          footprint=LC + "SOD-882_L1.0-W0.6-BI", lcsc="C3001950", mpn="PESD5V0F1BL",
          description="ESD del botón metálico, UMW (fuga < 1 nA: QON tiene un pull-up de 200 kohm)")
    d.add("D402", "Device:D", "1N4148W", s, "ui", {"1": "BTN_N", "2": "BTN_SENSE_N"}, rot=90,
          footprint=LC + "SOD-123F_L2.7-W1.6-LS3.8-RD", lcsc="C81598", mpn="1N4148W",
          description="Aísla QON (pull-up interno a 3.2-3.8 V) del GPIO18; silicio, no Schottky")
    R(s, "ui", "10k", "+3V3", "BTN_SENSE_N")
    R(s, "ui", "100", "VSYS", "BTN_LED_A", note="Anillo del botón: usar la versión de 3-6 V (la de 12 V no enciende)")
    d.add("Q402", "Transistor_FET:AO3400A", "AO3400A", s, "ui", {"G": "BTN_LED_EN", "S": "GND", "D": "BTN_LED_K"},
          footprint=LC + "SOT-23-3_L2.9-W1.3-P1.90-LS2.4-BR", lcsc="C20917", mpn="AO3400A")
    R(s, "ui", "100k", "BTN_LED_EN", "GND")
    d.add("J403", "Connector_Generic_MountingPin:Conn_01x04_MountingPin", "OLED", s, "ui",
          {"1": "GND", "2": "+3V3", "3": "I2C_SDA", "4": "I2C_SCL", "MP": "GND"},
          footprint=LC + "CONN-SMD_4P-P1.00_SM04B-SRSS-TB-LF-SN", lcsc="C160404", mpn="SM04B-SRSS-TB(LF)(SN)",
          description="JST SH 4 lateral con el orden Qwiic: GND, 3V3, SDA, SCL")
    d.add("J404", "Connector_Generic_MountingPin:Conn_01x02_MountingPin", "NTC", s, "ui",
          {"1": "CHG_TS", "2": "GND", "MP": "GND"}, footprint=LC + "CONN-SMD_2P-P1.00_SM02B-SRSS-TB-LF-SN",
          lcsc="C160402", mpn="SM02B-SRSS-TB(LF)(SN)",
          description="NTC 10k B3435 opcional, pegada a la celda: al conectarla, cortar JP101")
    # IMU de la tapa por I2C en un segundo bus (GPIO11 SDA, GPIO12 SCL) con sus dos interrupciones. El GH7 sigue
    # el orden del header de 9 pines del breakout BMI088 V1.0 (research/constraints.md §4) sin CSB1/CSB2:
    # cable n -> pin [1, 2, 3, 4, 5, 8, 9][n-1] del breakout. El pin 3 (SDO1/SDO2) a GND fija las direcciones
    # 0x18 (acelerómetro) y 0x68 (giróscopo); el selector del breakout va en IIC.
    d.add("J405", "Connector_Generic_MountingPin:Conn_01x07_MountingPin", "IMU", s, "imu",
          {"1": "+3V3", "2": "GND", "3": "GND", "4": "IMU_SDA", "5": "IMU_SCL", "6": "IMU_INT1", "7": "IMU_INT3",
           "MP": "GND"},
          footprint=LC + "CONN-SMD_SM7B-GHS-TB-LF-SN", lcsc="C495552", mpn="SM07B-GHS-TB(LF)(SN)",
          description="GH 7 lateral al BMI088 de la tapa (I2C): 3V3, GND, SDO a GND, SDA, SCL, INT1, INT3")
    R(s, "imu", "4.7k", "+3V3", "IMU_SDA", note="Pull-ups del bus del IMU (400 kHz por ~15 cm de cable)")
    R(s, "imu", "4.7k", "+3V3", "IMU_SCL")
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
                '  (lib (name "tresvizo_lcsc")(type "KiCad")(uri "${KIPRJMOD}/lib/lcsc.pretty")(options "")'
                '(descr "Huellas de LCSC/EasyEDA (orientación de JLCPCB)"))\n)\n')


def main():
    sym_dir, kicad_dir = sys.argv[1:3]
    libs = Libraries()
    for n in ("Device", "power", "Connector", "Connector_Generic_MountingPin", "Battery_Management", "Switch",
              "Sensor_Motion", "Power_Management", "Power_Protection", "Transistor_FET", "Regulator_Linear",
              "Jumper", "RF_Module"):
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
