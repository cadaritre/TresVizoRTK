"""Genera la biblioteca propia del proyecto: símbolos (tresvizo.kicad_sym) y ajustes de las huellas de LCSC.

    python3 mklib.py <dir_simbolos_kicad> <kicad_dir>

Los símbolos son rectángulos con los pines agrupados por función. Los números de pin
coinciden con los pads de las huellas importadas de LCSC (lib/lcsc.pretty).
(La v0.1 generaba aquí también la huella del UM980; la v0.2 lo lleva en su carrier, fuera de la placa.)
"""

import copy
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
    syms.append(ic(
        "TPS62903", left=[("6", "VIN", PW), ("5", "EN", I), ("7", "MODE", I), ("8", "SS/TR", P)],
        right=[("2", "SW", PO), ("3", "VOS", I), ("9", "FB", I), ("1", "PG", OC)], bottom=[("4", "GND", PW)],
        footprint=LCSC_FP + "VQFN-HR-9_L2.0-W1.5-P0.50-TL",
        datasheet="https://www.ti.com/lit/ds/symlink/tps62903.pdf",
        description="TI TPS62903 buck síncrono 3-17 V, 3 A, modo 100 %"))
    # Huella de LCSC: los pads de VIN (12 y 13) llevan el número 12 y los de VOUT (7 y 8) el 7.
    syms.append(ic(
        "TPS63070", left=[("12", "VIN", PW), ("14", "EN", I), ("1", "PS/SYNC", I), ("15", "VSEL", I),
                          ("3", "VAUX", P)],
        right=[("11", "L1", P), ("9", "L2", P), ("7", "VOUT", PO), ("5", "FB", I), ("6", "FB2", P),
               ("2", "PG", OC)],
        bottom=[("4", "GND", PW), ("10", "PGND", PW)],
        footprint=LCSC_FP + "VQFN-15_L3.0-W2.5-P0.50-BL",
        datasheet="https://www.ti.com/lit/ds/symlink/tps63070.pdf",
        description="TI TPS63070 buck-boost 2-16 V a 2.5-9 V, 2 A, desconecta la carga en apagado"))
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

    return syms


def write_symbols(path, syms):
    lib = ["kicad_symbol_lib", ["version", 20241209], ["generator", QStr("kicad_symbol_editor")],
           ["generator_version", QStr("9.0")]] + syms
    with open(path, "w", encoding="utf-8") as f:
        f.write(dumps(lib) + "\n")


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
    print("biblioteca escrita en", lib)


if __name__ == "__main__":
    main()
