"""Circuito de la placa del USB-C del panel (TresVizo MeridianV) y generación del esquemático.

    python3 circuit.py <dir_simbolos_kicad> <kicad_dir>

Escribe el esquemático, el proyecto .kicad_pro, la tabla de huellas y board.json. Usa los
generadores de la placa principal (../../main-board/scripts: schgen, symlib, sexpr) sin cambiarlos.

Receptáculo USB-C 2.0 con 5.1 kΩ en CC1/CC2 (sumidero de 5 V, sin PD), ESD en D+/D−, TVS en VBUS y
un conector JST GH de 8 pines lateral hacia J101 de la placa principal, con el mismo orden de pines
en las dos placas: 1-3 VBUS, 4-6 GND, 7 D−, 8 D+.
"""

import json
import os
import sys

sys.dont_write_bytecode = True   # sin cachés en ../../main-board/scripts, que edita otra persona
HERE = os.path.dirname(os.path.abspath(__file__))
MAIN_SCRIPTS = os.path.join(os.path.dirname(os.path.dirname(HERE)), "main-board", "scripts")
sys.path.insert(0, HERE)
sys.path.insert(1, MAIN_SCRIPTS)
from schgen import Design  # noqa: E402
from symlib import Libraries  # noqa: E402

import layout  # noqa: E402  (el de esta placa)

PROJECT = "tresvizo-panel-usb"
LC = "tresvizo_lcsc:"
R0402 = "Resistor_SMD:R_0402_1005Metric"

class PanelDesign(Design):
    """Una sola hoja, pero con etiquetas globales: así las redes se llaman VBUS, USB_DP, CC1... sin el
    prefijo de la hoja, y la placa principal las encuentra igual al armar el panel. VBUS va con etiqueta
    global y no con símbolo de alimentación para que las tres de J502 se lean."""

    def net_sheets(self):
        return {n: s | {"(global)"} for n, s in Design.net_sheets(self).items()}


def build(libs):
    d = PanelDesign(libs, PROJECT, "TresVizo MeridianV — USB-C del panel", "0.1", "2026-10-04", "TresVizo",
                    comments=["Exploratorio: no fabricado ni probado",
                              "USB-C 2.0 al ras de la tapa del panel; cable JST GH 8 a J101 de la placa principal",
                              "JLCPCB 4 capas JLC04161H-7628, montaje por una cara"])
    s = "usb"
    d.sheet(s, "usb.kicad_sch", "USB-C del panel y conector a la placa principal")
    d.group(s, "rx", "USB-C 2.0: 5 V sin PD (Rd 5.1 kΩ)", 210)
    d.group(s, "esd", "ESD y TVS", 150)
    d.group(s, "link", "Cable a J101 (GH 8)", 170)
    d.group(s, "flags", "ERC", 90)

    usb = {"A1": "GND", "A12": "GND", "B1": "GND", "B12": "GND", "SH": "GND",
           "A4": "VBUS", "A9": "VBUS", "B4": "VBUS", "B9": "VBUS",
           "A5": "CC1", "B5": "CC2", "A6": "USB_DP", "B6": "USB_DP", "A7": "USB_DN", "B7": "USB_DN",
           "A8": None, "B8": None}
    d.add("J501", "Connector:USB_C_Receptacle_USB2.0_16P", "USB_C", s, "rx", usb,
          footprint=LC + "USB-C_SMD-TYPE-C-31-M-12", lcsc="C165948", mpn="TYPE-C-31-M-12",
          datasheet="https://www.lcsc.com/datasheet/lcsc_datasheet_2205251630_Korean-Hroparts-Elec-TYPE-C-31-M-12_C165948.pdf",
          description="HRO TYPE-C-31-M-12: USB-C 16 contactos horizontal; cara 1.29 mm por delante del canto, "
                      "eje a ~1.65 mm de la placa; carcasa a GND")
    for ref, net in (("R501", "CC1"), ("R502", "CC2")):
        d.add(ref, "Device:R", "5.1k", s, "rx", {"1": net, "2": "GND"}, footprint=R0402, rot=90,
              lcsc="C25905", mpn="0402WGF5101TCE",
              description="Rd de %s: el cargador ve un sumidero y entrega 5 V (sin PD ni HVDCP)" % net)

    # I/O1 (pines 1 y 6) = D+ e I/O2 (3 y 4) = D− por cómo queda la pieza en la placa; es simétrica.
    d.add("U501", "Power_Protection:USBLC6-2SC6", "USBLC6-2SC6", s, "esd",
          {"1": "USB_DP", "6": "USB_DP", "3": "USB_DN", "4": "USB_DN", "5": "VBUS", "2": "GND"},
          footprint=LC + "SOT-23-6_L2.9-W1.6-P0.95-LS2.8-BL", lcsc="C2687116", mpn="USBLC6-2SC6",
          datasheet="https://www.st.com/resource/en/datasheet/usblc6-2.pdf",
          description="ESD de D+/D-; pin 5 a VBUS (5 V fijos: solo Rd, sin PD)")
    d.add("D501", "Device:D_Zener", "SMF15A", s, "esd", {"1": "VBUS", "2": "GND"}, rot=270,
          footprint=LC + "SOD-123FL_L2.7-W1.8-LS3.8-RD", lcsc="C19077509", mpn="SMF15A",
          datasheet="https://wmsc.lcsc.com/wmsc/upload/file/pdf/v2/lcsc/2312041000_hongjiacheng-SMF15A_C19077509.pdf",
          description="TVS unidireccional de VBUS, 15 V de trabajo (la misma de la placa principal)")

    d.add("J502", "Connector_Generic_MountingPin:Conn_01x08_MountingPin", "PANEL_USB", s, "link",
          {"1": "VBUS", "2": "VBUS", "3": "VBUS", "4": "GND", "5": "GND", "6": "GND", "7": "USB_DN",
           "8": "USB_DP", "MP": "GND"},
          footprint=LC + "CONN-SMD_8P-P1.25_XUNPU-WAFER-GH1.25-8PWB", lcsc="C3029383", mpn="WAFER-GH1.25-8PWB",
          datasheet="https://www.jst-mfg.com/product/pdf/eng/eGH.pdf",
          description="GH 8 lateral (XUNPU, huella de JST SM08B-GHS-TB): 1-3 VBUS, 4-6 GND, 7 D-, 8 D+; "
                      "tres contactos por lado (GH ~1 A por contacto con AWG26)")

    for k, net in enumerate(("VBUS", "GND"), start=1):
        d.add("#FLG%02d" % k, "power:PWR_FLAG", "PWR_FLAG", s, "flags", {"1": net}, in_bom=False)
    return d


def write_project(kicad_dir):
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
    r = layout.RULES
    pro = {
        "board": {"design_settings": {
            "defaults": {"board_outline_line_width": 0.1, "copper_line_width": 0.2, "copper_text_size_h": 1.5,
                         "copper_text_size_v": 1.5, "silk_line_width": 0.15, "silk_text_size_h": 1.0,
                         "silk_text_size_v": 1.0, "silk_text_thickness": 0.15},
            "rules": {"min_clearance": r["min_clearance"], "min_connection": 0.127,
                      "min_copper_edge_clearance": r["edge_clearance"], "min_hole_clearance": r["hole_clearance"],
                      "min_hole_to_hole": r["hole_to_hole"], "min_microvia_diameter": 0.2,
                      "min_microvia_drill": 0.1, "min_through_hole_diameter": r["min_drill"],
                      "min_track_width": r["min_track"], "min_via_annular_width": r["min_annular"],
                      "min_via_diameter": r["min_via_dia"], "min_text_height": 0.8, "min_text_thickness": 0.12,
                      "solder_mask_min_width": 0.1, "min_resolved_spokes": r["min_resolved_spokes"]},
            "track_widths": [0.0, 0.2, 0.25, 0.3, 0.6, 0.8],
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
    with open(os.path.join(kicad_dir, "fp-lib-table"), "w", encoding="utf-8") as f:
        f.write('(fp_lib_table\n  (version 7)\n'
                '  (lib (name "tresvizo_lcsc")(type "KiCad")(uri "${KIPRJMOD}/lib/lcsc.pretty")(options "")'
                '(descr "Huellas de LCSC/EasyEDA (orientación de JLCPCB)"))\n)\n')


def main():
    sym_dir, kicad_dir = sys.argv[1:3]
    libs = Libraries()
    for n in ("Device", "power", "Connector", "Connector_Generic_MountingPin", "Power_Protection"):
        libs.add(os.path.join(sym_dir, n + ".kicad_sym"))
    d = build(libs)
    for p in d.check():
        print("AVISO:", p)
    d.note("_root", "Placa del USB-C del panel de TresVizo MeridianV. Nada de esto se ha fabricado ni probado.")
    d.note("_root", "J502 (GH 8) va con un cable 1 a 1 (pin 1 con pin 1) a J101 de la placa principal. "
                    "Un cable en espejo pone VBUS contra GND: medirlo pin a pin antes de conectar.")
    d.write(kicad_dir)
    write_project(kicad_dir)
    layout.write_board_json(d, kicad_dir)
    print("esquemático:", len([p for p in d.parts if not p.ref.startswith("#")]), "piezas,",
          len(d.netlist()), "redes")


if __name__ == "__main__":
    main()
