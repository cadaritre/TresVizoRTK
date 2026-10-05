"""Biblioteca de huellas y modelos 3D de la placa del USB-C del panel (kicad/lib/).

    python3 mklib.py <dir_easyeda2kicad>

<dir_easyeda2kicad> es donde easyeda2kicad dejó lcsc.pretty/ y lcsc.3dshapes/ de las piezas de LCSC:

    easyeda2kicad --footprint --3d --lcsc_id=C165948 --output <dir>/lcsc     # USB-C HRO TYPE-C-31-M-12
    easyeda2kicad --footprint --3d --lcsc_id=C2687116 --output <dir>/lcsc    # USBLC6-2SC6
    easyeda2kicad --footprint --3d --lcsc_id=C19077509 --output <dir>/lcsc   # SMF15A

El GH de 8 pines lateral (C3029383) se copia de la biblioteca de la placa principal, que ya tiene sus
anclajes renombrados a MP. Las huellas de LCSC conservan su origen y su orientación (las de JLCPCB).

Cambios a la huella del USB-C (sin mover el origen ni girarla):
- Los pads dobles de EasyEDA (A1B12, A4B9, B4A9, B1A12) pasan a dos pads superpuestos con el número
  de cada contacto, como en la huella de KiCad, para usar el símbolo USB_C_Receptacle_USB2.0_16P.
- Las cuatro patas de la carcasa pasan a «SH», con las ranuras del plano de HRO (0.6 x 1.7 atrás,
  0.6 x 1.4 adelante) y anillo de 0.2 mm (EasyEDA usa ranuras de 0.8 mm de ancho), y llevan pasta en
  F.Paste: JLCPCB suelda estas patas en el mismo reflujo (pasta en el agujero).
- Los dos postes de centrado pasan a agujeros sin metalizar.
- Serigrafía solo a los lados del cuerpo (la frontal quedaba fuera de la placa) y patio que cubre
  los pads.
- Modelo 3D desplazado 2.22 mm: el de EasyEDA quedaba con las patas fuera de sus ranuras (comprobado
  con la exportación VRML de la placa, ver build.py).
"""

import os
import shutil
import sys

sys.dont_write_bytecode = True   # sin cachés en ../../main-board/scripts
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
MAIN = os.path.join(os.path.dirname(ROOT), "main-board")
sys.path.insert(0, os.path.join(MAIN, "scripts"))
from sexpr import QStr, dumps, find, findall, loads  # noqa: E402

LIB = os.path.join(ROOT, "kicad", "lib")
PRETTY = os.path.join(LIB, "lcsc.pretty")
SHAPES = os.path.join(LIB, "lcsc.3dshapes")
MODEL_DIR = "${KIPRJMOD}/lib/lcsc.3dshapes/"

USB_SRC = "USB-C_SMD-TYPE-C-31-M-12_1"
USB_NAME = "USB-C_SMD-TYPE-C-31-M-12"
# Desplazamiento del modelo 3D del USB-C en el eje Y del visor 3D (hacia arriba = -y de la huella)
USB_MODEL_OFFSET_Y = -2.22
GH8 = "CONN-SMD_8P-P1.25_XUNPU-WAFER-GH1.25-8PWB"
COPY = {  # huella -> modelo (sin extensión), tal como los deja easyeda2kicad
    "SOT-23-6_L2.9-W1.6-P0.95-LS2.8-BL": "SOT-23-6_L2.9-W1.6-H1.5-LS2.8-P0.95",
    "SOD-123FL_L2.7-W1.8-LS3.8-RD": "SOD-123FL_L2.8-W1.8-H1.1-LS3.6",
}


def model_node(name, offset=(0, 0, 0), rotate=(0, 0, 0)):
    return ["model", QStr(MODEL_DIR + name + ".wrl"), ["offset", ["xyz"] + list(offset)],
            ["scale", ["xyz", 1, 1, 1]], ["rotate", ["xyz"] + list(rotate)]]


def line(x1, y1, x2, y2, layer, w):
    return ["fp_line", ["start", x1, y1], ["end", x2, y2], ["layer", layer], ["width", w]]


def rect_pad(num, x, y, w, h):
    return ["pad", QStr(num), "smd", "rect", ["at", x, y, 0], ["size", w, h],
            ["layers", "F.Cu", "F.Paste", "F.Mask"]]


def copy_models(src_dir, name):
    for ext in (".wrl", ".step"):
        src = os.path.join(src_dir, name + ext)
        if os.path.exists(src):
            shutil.copy(src, os.path.join(SHAPES, name + ext))


def usb_c(ee):
    t = loads(open(os.path.join(ee, "lcsc.pretty", USB_SRC + ".kicad_mod"), encoding="utf-8").read())
    out = [t[0], QStr(USB_NAME)]
    pads = []
    for item in t[2:]:
        if not isinstance(item, list):
            out.append(item)
            continue
        head = item[0]
        if head == "pad":
            num, kind = str(item[1]), str(item[2])
            x, y = float(find(item, "at")[1]), float(find(item, "at")[2])
            if kind == "smd" and str(item[3]) == "custom":
                # Pad doble (p. ej. A1B12): dos pads de 0.6 x 1.3 superpuestos, uno por contacto
                a, b = num[:2], num[2:]
                pads += [rect_pad(a, x, y, 0.6, 1.3), rect_pad(b, x, y, 0.6, 1.3)]
            elif kind == "smd":
                pads.append(rect_pad(num, x, y, 0.3, 1.3))
            elif num == "":
                d = float(find(item, "drill")[1])
                pads.append(["pad", QStr(""), "np_thru_hole", "circle", ["at", x, y], ["size", d, d],
                             ["drill", d], ["layers", "*.Cu", "*.Mask"]])
            else:
                # Patas de la carcasa: ranuras del plano de HRO, anillo de 0.2 mm
                slot = 1.7 if y < 0 else 1.4
                pads.append(["pad", QStr("SH"), "thru_hole", "oval", ["at", x, y], ["size", 1.0, slot + 0.4],
                             ["drill", "oval", 0.6, slot], ["layers", "*.Cu", "*.Mask", "F.Paste"]])
            continue
        if head in ("fp_line", "fp_circle", "model", "property"):
            continue
        if head == "fp_text" and str(item[1]) == "value":
            item[2] = USB_NAME
        out.append(item)
    # Serigrafía a los lados del cuerpo, entre las ranuras; cuerpo en F.Fab (frente en y = 5.07,
    # 6.28 mm por delante de los postes de centrado, según el plano de HRO)
    for sx in (-1, 1):
        out.append(line(sx * 4.47, -0.45, sx * 4.47, 1.35, "F.SilkS", 0.15))
    body = [(-4.47, -2.23), (4.47, -2.23), (4.47, 5.07), (-4.47, 5.07)]
    for i in range(4):
        (x1, y1), (x2, y2) = body[i], body[(i + 1) % 4]
        out.append(line(x1, y1, x2, y2, "F.Fab", 0.1))
    crt = [(-5.1, -3.4), (5.1, -3.4), (5.1, 5.35), (-5.1, 5.35)]
    for i in range(4):
        (x1, y1), (x2, y2) = crt[i], crt[(i + 1) % 4]
        out.append(line(x1, y1, x2, y2, "F.CrtYd", 0.05))
    out += pads
    out.append(["property", QStr("LCSC Part"), QStr("C165948")])
    out.append(model_node(USB_NAME, (0, USB_MODEL_OFFSET_Y, 0), (0, 0, 180)))
    with open(os.path.join(PRETTY, USB_NAME + ".kicad_mod"), "w", encoding="utf-8") as f:
        f.write(dumps(out) + "\n")
    for ext in (".wrl", ".step"):
        src = os.path.join(ee, "lcsc.3dshapes", USB_SRC + ext)
        if os.path.exists(src):
            shutil.copy(src, os.path.join(SHAPES, USB_NAME + ext))


def copy_easyeda(ee, fp_name, model):
    t = loads(open(os.path.join(ee, "lcsc.pretty", fp_name + ".kicad_mod"), encoding="utf-8").read())
    for m in findall(t, "model"):
        m[1] = QStr(MODEL_DIR + model + ".wrl")
    with open(os.path.join(PRETTY, fp_name + ".kicad_mod"), "w", encoding="utf-8") as f:
        f.write(dumps(t) + "\n")
    copy_models(os.path.join(ee, "lcsc.3dshapes"), model)


def main():
    ee = sys.argv[1]
    os.makedirs(PRETTY, exist_ok=True)
    os.makedirs(SHAPES, exist_ok=True)
    usb_c(ee)
    for fp_name, model in COPY.items():
        copy_easyeda(ee, fp_name, model)
    main_lib = os.path.join(MAIN, "kicad", "lib")
    shutil.copy(os.path.join(main_lib, "lcsc.pretty", GH8 + ".kicad_mod"), os.path.join(PRETTY, GH8 + ".kicad_mod"))
    copy_models(os.path.join(main_lib, "lcsc.3dshapes"), GH8)
    print("biblioteca escrita en", LIB)


if __name__ == "__main__":
    main()
