"""Genera la biblioteca propia del proyecto: símbolos (tresvizo.kicad_sym) y la huella del UM980.

    python3 mklib.py <dir_simbolos_kicad> <kicad_dir>

Los símbolos son rectángulos con los pines agrupados por función. Los números de pin
coinciden con los pads de las huellas importadas de LCSC (lib/lcsc.pretty) o con la
huella propia del UM980, generada a partir de las cotas del manual de Unicore (R1.10,
tabla 2-6 y figuras 2-1/3-4) recogidas en research/um980_footprint.json.
"""

import copy
import json
import math
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from sexpr import QStr, dumps, find, findall, loads  # noqa: E402
from symlib import Libraries  # noqa: E402

G = 2.54


def font(size=1.27, hide=False, justify=None):
    e = ["effects", ["font", ["size", size, size]]]
    if justify:
        e.append(["justify"] + justify.split())
    if hide:
        e.append(["hide", "yes"])
    return e


def prop(name, value, x=0.0, y=0.0, hide=False, justify=None):
    return ["property", QStr(name), QStr(value), ["at", x, y, 0], font(hide=hide, justify=justify)]


def pin(num, name, etype, x, y, angle, hidden=False, length=G):
    p = ["pin", etype, "line", ["at", x, y, angle], ["length", length]]
    if hidden:
        p.append(["hide", "yes"])
    p.append(["name", QStr(name), font()])
    p.append(["number", QStr(num), font()])
    return p


def ic(name, left, right, top=(), bottom=(), ref="U", footprint="", description="", datasheet="",
       hidden=(), min_w=10.16):
    """left/right/top/bottom: listas de (número, nombre, tipo) o None para un hueco.
    hidden: pines ocultos apilados (número, nombre, tipo, número_visible_al_que_se_apilan)."""
    cw = 0.85
    lw = max([len(p[1]) for p in left if p] + [0]) * cw
    rw = max([len(p[1]) for p in right if p] + [0]) * cw
    tw = max(len(top), len(bottom)) * G + G
    w = max(min_w, lw + rw + 3.0, tw)
    w = math.ceil(w / (2 * G)) * 2 * G
    n = max(len(left), len(right), 1)
    h = (n + 1) * G
    tb = max(len(top), len(bottom))
    if tb:
        h = max(h, 4 * G)
    h = math.ceil(h / (2 * G)) * 2 * G
    x0, x1 = -w / 2, w / 2
    y1, y0 = h / 2, -h / 2  # arriba, abajo (Y hacia arriba)
    pins = []
    pos = {}

    def col(items, x, angle):
        start = (len(items) - 1) * G / 2
        start = math.floor(start / 1.27) * 1.27 if (len(items) - 1) % 2 else start
        for i, it in enumerate(items):
            if it is None:
                continue
            y = round(start - i * G, 4)
            pins.append(pin(it[0], it[1], it[2], x, y, angle))
            pos[it[0]] = (x, y, angle)

    col(left, x0 - G, 0)
    col(right, x1 + G, 180)

    def row(items, y, angle):
        start = -(len(items) - 1) * G / 2
        for i, it in enumerate(items):
            if it is None:
                continue
            x = round(start + i * G, 4)
            pins.append(pin(it[0], it[1], it[2], x, y, angle))
            pos[it[0]] = (x, y, angle)

    row(top, y1 + G, 270)
    row(bottom, y0 - G, 90)
    for num, nm, et, base in hidden:
        x, y, a = pos[base]
        # Los pines ocultos apilados van como pasivos: un pin de alimentación oculto
        # crearía en KiCad una conexión implícita a una red global con su nombre.
        pins.append(pin(num, nm, et if et == NC else P, x, y, a, hidden=True))
    body = ["symbol", QStr(name + "_0_1"),
            ["rectangle", ["start", x0, y1], ["end", x1, y0],
             ["stroke", ["width", 0.254], ["type", "default"]], ["fill", ["type", "background"]]]]
    sym = ["symbol", QStr(name), ["pin_names", ["offset", 0.508]], ["exclude_from_sim", "no"],
           ["in_bom", "yes"], ["on_board", "yes"],
           prop("Reference", ref, x0, y1 + 1.27, justify="left"),
           prop("Value", name, x0, y0 - 1.27, justify="left"),
           prop("Footprint", footprint, hide=True),
           prop("Datasheet", datasheet, hide=True),
           prop("Description", description, hide=True),
           body, ["symbol", QStr(name + "_1_1")] + pins, ["embedded_fonts", "no"]]
    return sym


def two_pin(name, ref, pins, footprint, description, graphic):
    """Símbolo de dos terminales (pines arriba y abajo) con un gráfico simple."""
    body = ["symbol", QStr(name + "_0_1")] + graphic
    plist = [pin(n, nm, et, 0, y, a) for (n, nm, et, y, a) in pins]
    return ["symbol", QStr(name), ["pin_numbers", ["hide", "yes"]], ["pin_names", ["offset", 0], ["hide", "yes"]],
            ["exclude_from_sim", "no"], ["in_bom", "yes"], ["on_board", "yes"],
            prop("Reference", ref, 2.54, 0.6, justify="left"), prop("Value", name, 2.54, -1.6, justify="left"),
            prop("Footprint", footprint, hide=True), prop("Datasheet", "", hide=True),
            prop("Description", description, hide=True), body,
            ["symbol", QStr(name + "_1_1")] + plist, ["embedded_fonts", "no"]]


def stroke(w=0.254):
    return ["stroke", ["width", w], ["type", "default"]]


def poly(points, fill="none", w=0.254):
    return ["polyline", ["pts"] + [["xy", x, y] for x, y in points], stroke(w), ["fill", ["type", fill]]]


# ----------------------------------------------------------------------- símbolos
P, I, O, B, PW, PO, OC, NC = ("passive", "input", "output", "bidirectional", "power_in", "power_out",
                              "open_collector", "no_connect")

LCSC_FP = "tresvizo_lcsc:"


def build_symbols(kicad_sym_dir):
    syms = []
    um_nc = ["13", "15", "16", "17", "18", "22", "23", "24", "25", "35", "38", "39", "40", "46", "47", "50", "52", "54"]
    um_gnd = ["1", "3", "12", "14", "32", "37", "41", "48"]
    syms.append(ic(
        "UM980",
        left=[("33", "VCC", PW), ("36", "V_BCKP", PW), None, ("49", "RESET_N", I), None,
              ("43", "RXD1", I), ("26", "RXD2", I), ("31", "RXD3", I), None, ("51", "EVENT", I), None,
              ("28", "BIF1", P), ("29", "BIF2", P), None, ("2", "ANT_IN", I), ("4", "ANT_DETECT", I),
              ("6", "ANT_SHORT_N", I), ("5", "ANT_OFF", O), ("7", "VCC_RF", PO)],
        right=[("42", "TXD1", O), ("27", "TXD2", O), ("30", "TXD3", O), None, ("53", "PPS", O), None,
               ("19", "PVT_STAT", O), ("20", "RTK_STAT", O), ("21", "ERR_STAT", O), None,
               ("8", "SPIS_CSN", I), ("9", "SPIS_MOSI", I), ("10", "SPIS_CLK", I), ("11", "SPIS_MISO", O),
               ("44", "SDA", B), ("45", "SCL", B)],
        bottom=[("55", "GND", PW)],
        hidden=[("34", "VCC", PW, "33")] + [(n, "GND", PW, "55") for n in um_gnd]
               + [(n, "NC", NC, "55") for n in um_nc],
        footprint="tresvizo:UM980", datasheet="https://en.unicore.com/uploads/file/UM980_User%20Manual_EN_R1.10.pdf",
        description="Unicore UM980 GNSS RTK multibanda, LGA 22x17 mm (54 pads + 48 pads de GND)"))
    # Los pines NC ocultos del UM980 no deben aparecer como «apilados» sobre GND: se mueven fuera.
    um = syms[-1]
    for sub in findall(um, "symbol"):
        for p in findall(sub, "pin"):
            if p[1] == "no_connect":
                at = find(p, "at")
                at[1], at[2] = 0.0, 0.0
    syms.append(ic(
        "TPS62903", left=[("6", "VIN", PW), ("5", "EN", I), ("7", "MODE", I), ("8", "SS/TR", P)],
        right=[("2", "SW", PO), ("3", "VOS", I), ("9", "FB", I), ("1", "PG", OC)], bottom=[("4", "GND", PW)],
        footprint=LCSC_FP + "VQFN-HR-9_L2.0-W1.5-P0.50-TL",
        datasheet="https://www.ti.com/lit/ds/symlink/tps62903.pdf",
        description="TI TPS62903 buck síncrono 3-17 V, 3 A, modo 100 %"))
    syms.append(ic(
        "TPS22945", left=[("5", "VIN", PW), ("4", "ON", I)], right=[("1", "VOUT", PO), ("3", "OC", OC)],
        bottom=[("2", "GND", PW)], footprint=LCSC_FP + "SC-70-5_L2.1-W1.3-P0.65-LS2.1-BL",
        datasheet="https://www.ti.com/lit/ds/symlink/tps22945.pdf",
        description="TI TPS22945 interruptor de carga con límite de corriente (alimentación de antena)"))
    syms.append(ic(
        "MAX17048", left=[("3", "VDD", PW), ("2", "CELL", I), ("1", "CTG", I), ("6", "QSTRT", I)],
        right=[("8", "SDA", B), ("7", "SCL", I), ("5", "~{ALRT}", OC)], bottom=[("4", "GND", PW), ("9", "EP", P)],
        footprint=LCSC_FP + "TDFN-8_L2.0-W2.0-P0.50-BL-EP1.2",
        datasheet="https://www.analog.com/media/en/technical-documentation/data-sheets/MAX17048-MAX17049.pdf",
        description="Medidor de batería ModelGauge I2C 0x36 (MAX17048 1S / MAX17049 2S, misma huella)"))
    syms.append(ic(
        "TF-015", left=[("4", "VDD", PW), ("5", "CLK", I), ("3", "CMD", B), ("7", "DAT0", B), ("8", "DAT1", B),
                        ("1", "DAT2", B), ("2", "DAT3", B), None, ("9", "CD", P)],
        right=[], bottom=[("6", "VSS", PW), ("10", "SHIELD", P)],
        hidden=[("11", "SHIELD", P, "10"), ("12", "SHIELD", P, "10"), ("13", "SHIELD", P, "10")],
        ref="J", footprint=LCSC_FP + "TF-SMD_TF-015", min_w=7.62,
        datasheet="https://www.lcsc.com/datasheet/C113206.pdf",
        description="Zócalo microSD push-push SOFNG TF-015; CD cierra contra la carcasa con tarjeta"))
    syms.append(ic(
        "U.FL", left=[("1", "RF", P)], right=[], bottom=[("2", "GND", P)], hidden=[("3", "GND", P, "2")],
        ref="J", footprint=LCSC_FP + "IPEX-SMD_BWIPX-1-001E", min_w=5.08,
        datasheet="https://www.lcsc.com/datasheet/C5137195.pdf", description="Receptáculo u.FL (IPEX MHF I)"))
    # Pulsador de 4 pads: se usan dos pads en diagonal (1 y 4), que nunca están unidos por dentro.
    sw = two_pin("SW_TACT", "SW",
                 [("1", "A", P, 5.08, 270), ("4", "B", P, -5.08, 90)],
                 LCSC_FP + "SW-SMD_4P-L5.1-W5.1-P3.70-LS6.5-TL_H1.5",
                 "Pulsador táctil SMD de 4 pads; se conectan los pads diagonales 1 y 4",
                 [poly([(0, 2.54), (0, 1.27)]), poly([(0, -2.54), (0, -1.27)]),
                  poly([(-1.27, 1.6), (1.27, 1.6)]), poly([(-0.9, -1.27), (0.9, 0.9)]),
                  ["circle", ["center", 0, -1.27], ["radius", 0.3], stroke(), ["fill", ["type", "none"]]],
                  ["circle", ["center", 0, 1.27], ["radius", 0.3], stroke(), ["fill", ["type", "none"]]]])
    sw[-2].append(pin("2", "NC", NC, 2.54, 0, 180, hidden=True))
    sw[-2].append(pin("3", "NC", NC, 2.54, 0, 180, hidden=True))
    syms.append(sw)
    # ESP32-S3-MINI-1 con la numeración de la huella de LCSC (pads de GND con número «GND»).
    libs = Libraries()
    rf = libs.add(os.path.join(kicad_sym_dir, "RF_Module.kicad_sym"))
    esp = copy.deepcopy(rf.get("ESP32-S3-MINI-1").node)
    esp[1] = QStr("ESP32-S3-MINI-1_LCSC")
    for sub in findall(esp, "symbol"):
        sub[1] = QStr(str(sub[1]).replace("ESP32-S3-MINI-1", "ESP32-S3-MINI-1_LCSC"))
        keep = []
        for item in sub:
            if isinstance(item, list) and item[0] == "pin":
                num = str(find(item, "number")[1])
                if num in ("62", "63", "64", "65"):
                    continue
                if num == "61":
                    find(item, "number")[1] = QStr("GND")
            keep.append(item)
        sub[:] = keep
    for p in findall(esp, "property"):
        if p[1] == "Footprint":
            p[2] = QStr(LCSC_FP + "BULETM-SMD_ESP32-S3-MINI-1-N8")
    syms.append(esp)

    # Copias de símbolos de KiCad con tipos de pin ajustados a cómo se usan aquí (para el ERC):
    # SDO1/SDO2 del BMI088 se unen en el bus SPI (salidas de tres estados) y QOD del TPS22919
    # se une a OUT, como indica su hoja de datos.
    def derive(libname, symname, newname, types):
        lib = libs.add(os.path.join(kicad_sym_dir, libname + ".kicad_sym"))
        node = copy.deepcopy(lib.get(symname).node)
        node[1] = QStr(newname)
        for sub in findall(node, "symbol"):
            sub[1] = QStr(str(sub[1]).replace(symname, newname, 1))
            for item in findall(sub, "pin"):
                num = str(find(item, "number")[1])
                if num in types:
                    item[1] = types[num]
        return node

    syms.append(derive("Sensor_Motion", "BMI088", "BMI088_SPI", {"10": "tri_state", "15": "tri_state"}))
    syms.append(derive("Power_Management", "TPS22919DCK", "TPS22919DCK_QOD", {"5": "passive"}))
    return syms


def write_symbols(path, syms):
    lib = ["kicad_symbol_lib", ["version", 20241209], ["generator", QStr("kicad_symbol_editor")],
           ["generator_version", QStr("9.0")]] + syms
    with open(path, "w", encoding="utf-8") as f:
        f.write(dumps(lib) + "\n")


# ------------------------------------------------------------------- huella UM980
def um980_footprint(json_path, out_path):
    d = json.load(open(json_path, encoding="utf-8"))
    W, H = d["outline"]["width_mm"], d["outline"]["height_mm"]
    items = ["footprint", QStr("UM980"), ["version", 20241229], ["generator", QStr("pcbnew")],
             ["generator_version", QStr("9.0")], ["layer", QStr("F.Cu")],
             ["descr", QStr("Unicore UM980, LGA 22.0 x 17.0 mm, 54 pads perimetrales de 0.8 x 1.5 mm (paso 1.1) "
                            "y 48 pads interiores de GND de 1.1 mm (paso 2.1). Cotas del manual Unicore UM980 "
                            "R1.10, tabla 2-6 y figuras 2-1/3-4, vista superior.")],
             ["tags", QStr("UM980 GNSS RTK LGA")],
             ["property", QStr("Reference"), QStr("REF**"), ["at", 0, -H / 2 - 1.6, 0], ["layer", QStr("F.SilkS")],
              ["uuid", QStr("6d0c7d5c-0000-4000-8000-000000000001")], font(1.0)],
             ["property", QStr("Value"), QStr("UM980"), ["at", 0, H / 2 + 1.6, 0], ["layer", QStr("F.Fab")],
              ["uuid", QStr("6d0c7d5c-0000-4000-8000-000000000002")], font(1.0)],
             ["attr", "smd"]]

    def line(x1, y1, x2, y2, layer, w):
        items.append(["fp_line", ["start", x1, y1], ["end", x2, y2],
                      ["stroke", ["width", w], ["type", "solid"]], ["layer", QStr(layer)]])

    def rect(x1, y1, x2, y2, layer, w):
        line(x1, y1, x2, y1, layer, w)
        line(x2, y1, x2, y2, layer, w)
        line(x2, y2, x1, y2, layer, w)
        line(x1, y2, x1, y1, layer, w)

    rect(-W / 2, -H / 2, W / 2, H / 2, "F.Fab", 0.1)
    cy = 0.5
    rect(-11.25 - cy, -8.75 - cy, 11.25 + cy, 8.75 + cy, "F.CrtYd", 0.05)
    s = 0.15
    o = 0.25
    # Serigrafía: solo esquinas, fuera del cuerpo.
    for sx in (-1, 1):
        for sy in (-1, 1):
            x, y = sx * (W / 2 + o), sy * (H / 2 + o)
            line(x, y, x - sx * 2.0, y, "F.SilkS", s)
            line(x, y, x, y - sy * 2.0, "F.SilkS", s)
    # Marca del pin 1 (abajo a la izquierda en vista superior).
    items.append(["fp_circle", ["center", -W / 2 - 0.9, H / 2 + 0.9], ["end", -W / 2 - 0.6, H / 2 + 0.9],
                  ["stroke", ["width", 0.3], ["type", "solid"]], ["fill", "yes"], ["layer", QStr("F.SilkS")]])
    for p in d["pads"]:
        num = p["pin"]
        if int(num) > 54:
            num = "55"  # todos los pads interiores son GND: un único número
        shape = "circle" if p.get("shape") == "circle" or p.get("shape") == "round" else "rect"
        pad = ["pad", QStr(num), "smd", shape, ["at", p["x_mm"], p["y_mm"]], ["size", p["w_mm"], p["h_mm"]],
               ["layers", QStr("F.Cu"), QStr("F.Paste"), QStr("F.Mask")]]
        items.append(pad)
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(dumps(items) + "\n")


def connector_mount_pads(pretty):
    """En las huellas JST importadas, los pads de anclaje (los dos de mayor número) pasan a «MP»,
    como en los símbolos Conn_01xNN_MountingPin de KiCad."""
    for fn in sorted(os.listdir(pretty)):
        if not fn.startswith(("CONN-SMD_", "CONN-TH_")):
            continue
        path = os.path.join(pretty, fn)
        t = loads(open(path, encoding="utf-8").read())
        pads = findall(t, "pad")
        if any(str(p[1]) == "MP" for p in pads):
            continue  # ya convertida
        if any(str(p[1]) == "0" for p in pads):
            # Algunas huellas numeran los anclajes como «0».
            for p in pads:
                if str(p[1]) == "0":
                    p[1] = QStr("MP")
            with open(path, "w", encoding="utf-8") as f:
                f.write(dumps(t) + "\n")
            continue
        nums = sorted({int(str(p[1])) for p in pads if str(p[1]).isdigit()})
        if len(nums) < 3:
            continue
        mount = nums[-2:]
        changed = False
        for p in pads:
            if str(p[1]).isdigit() and int(str(p[1])) in mount:
                p[1] = QStr("MP")
                changed = True
        if changed:
            with open(path, "w", encoding="utf-8") as f:
                f.write(dumps(t) + "\n")


def npth_alignment_holes(pretty):
    """Los agujeros de centrado sin número que EasyEDA exporta como «thru_hole» sin anillo pasan a NPTH."""
    for fn in sorted(os.listdir(pretty)):
        path = os.path.join(pretty, fn)
        t = loads(open(path, encoding="utf-8").read())
        changed = False
        for p in findall(t, "pad"):
            if str(p[1]) == "" and str(p[2]) == "thru_hole":
                drill, size = find(p, "drill"), find(p, "size")
                if drill and size and abs(float(drill[1]) - float(size[1])) < 0.01:
                    p[2] = "np_thru_hole"
                    lay = find(p, "layers")
                    lay[1:] = [QStr("*.Cu"), QStr("*.Mask")]
                    changed = True
        if changed:
            with open(path, "w", encoding="utf-8") as f:
                f.write(dumps(t) + "\n")


def main():
    kicad_sym_dir, kicad_dir = sys.argv[1:3]
    connector_mount_pads(os.path.join(kicad_dir, "lib", "lcsc.pretty"))
    npth_alignment_holes(os.path.join(kicad_dir, "lib", "lcsc.pretty"))
    lib = os.path.join(kicad_dir, "lib")
    write_symbols(os.path.join(lib, "tresvizo.kicad_sym"), build_symbols(kicad_sym_dir))
    os.makedirs(os.path.join(lib, "tresvizo.pretty"), exist_ok=True)
    um980_footprint(os.path.join(os.path.dirname(kicad_dir), "research", "um980_footprint.json"),
                    os.path.join(lib, "tresvizo.pretty", "UM980.kicad_mod"))
    print("biblioteca escrita en", lib)


if __name__ == "__main__":
    main()
