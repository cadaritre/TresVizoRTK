"""Geometría de la placa del USB-C del panel: contorno, colocación, pistas fijadas y zonas (kicad/board.json).

Coordenadas locales (u, v) en mm vistas desde la cara de componentes con el USB-C arriba: u hacia la
derecha, v hacia abajo. Correspondencia con la carcasa V2.2 (estudio CAD; z = eje del jalón, +Y hacia
el panel, +X a la izquierda mirando el panel):  u = x + 10.4,  v = 31.3 - y.  La placa es horizontal:
cara inferior en z = 90.17 y cara de componentes en z = 91.77, hacia arriba.

Reglas y clases de red: las de la placa principal (las dos placas van en un mismo panel de JLCPCB).
"""

import importlib.util
import json
import math
import os

HERE = os.path.dirname(os.path.abspath(__file__))
_main = importlib.util.spec_from_file_location(
    "main_layout", os.path.join(os.path.dirname(os.path.dirname(HERE)), "main-board", "scripts", "layout.py"))
main_layout = importlib.util.module_from_spec(_main)
_main.loader.exec_module(main_layout)
NETCLASSES = main_layout.NETCLASSES

OX, OY = 100.0, 100.0          # origen de la placa en la hoja de KiCad
W = 20.8                       # ancho del cuerpo (u 0-20.8)
V_BODY, V_REAR = 4.7, 19.8     # el cuerpo empieza en v 4.7; canto trasero
TONGUE = (5.2, 15.6)           # lengüeta frontal bajo el USB-C
# Canto frontal de la lengüeta: el plano de HRO pone el canto de la placa 5.79 mm por delante de los
# postes de centrado y la cara del receptáculo 6.28 mm por delante (sobresale 0.49 mm). La cara queda en
# v = -0.40 (y = 31.70, a ras de la tapa curva) y los postes en v = 5.88. A pedido del propietario el
# canto retrocede a v = 0.89 (y = 30.41) para que el receptáculo sobresalga 1.29 mm y sea más fácil de
# montar en la tapa; el cobre de las ranuras delanteras del blindaje queda a 0.41 mm del canto (>= 0.3).
V_FRONT = 0.89
R_CORNER = 0.5

RULES = {"min_clearance": 0.127, "min_track": 0.127, "min_via_dia": 0.5, "min_drill": 0.3, "min_annular": 0.1,
         "hole_to_hole": 0.5, "edge_clearance": 0.3, "hole_clearance": 0.25, "min_resolved_spokes": 1}

# ---------------------------------------------------------------- colocación
# ref: (u, v, rot)   rot en grados, antihorario visto desde arriba (convención de KiCad)
PLACE = {
    # USB-C con la boca hacia el panel (-v): cara en v = -0.40 (1.29 mm por delante del canto), u = 10.4 (x = 0)
    "J501": (10.4, 4.67, 180),
    # GH 8 lateral con la boca hacia el canto trasero (+v, -Y). Los anclajes llegan a v = 19.48 (0.32 mm del
    # canto: cobre a >= 0.3 mm). El plano de XUNPU pone el frente del cuerpo a ras de los anclajes y el modelo
    # 3D de LCSC 0.09 mm más afuera: la boca queda 0.23-0.32 mm dentro del canto. Pines 1-8 de izquierda a
    # derecha (u 6.02-14.77).
    "J502": (10.4, 16.5, 0),
    "R501": (14.0, 9.75, 0),     # CC1 entra por la izquierda; GND sale a la pata trasera derecha del USB-C
    "R502": (6.8, 9.75, 180),    # CC2, simétrica
    "U501": (17.1, 13.4, 0),     # D+ la atraviesa (pines 6 y 1) camino de J502.8; D- por debajo (3 y 4)
    "D501": (3.4, 13.0, 180),    # cátodo junto a J502.1 (VBUS)
}

HOLES = [("H501", 2.5, 6.3), ("H502", 18.3, 6.3)]   # x = -7.9 / +7.9, y = 25.0
HOLE_KEEPOUT_R = 2.2                                # sin cobre en Ø4.4
# Puentes del panel (mouse bites de 5 mm): uno en cada canto lateral, centrados en v = 16.0. Sin cobre
# a menos de 1 mm del canto en v 13.0-19.0 (el puente más 0.5 mm por lado, como deja panelize.py).
TABS = [("left", 16.0), ("right", 16.0)]
TAB_W, TAB_DEPTH = 5.0, 1.0

# Pistas fijadas: (red, capa, ancho, [(u, v), ...])
TRACKS = [
    # ------------------------------------------------ VBUS (>= 0.6 mm; baja a B.Cu junto a cada pad del USB-C)
    ("VBUS", "F.Cu", 0.6, [(8.0, 7.79), (8.0, 9.15)]),              # B4/A9 -> vías L1, L2
    ("VBUS", "F.Cu", 0.6, [(12.8, 7.79), (12.8, 9.15)]),            # A4/B9 -> vías R1, R2
    ("VBUS", "B.Cu", 0.8, [(8.0, 8.25), (8.0, 13.4)]),
    ("VBUS", "B.Cu", 0.8, [(12.8, 8.25), (12.8, 11.1), (8.0, 11.1)]),
    ("VBUS", "B.Cu", 0.8, [(6.02, 13.4), (8.52, 13.4)]),
    ("VBUS", "F.Cu", 0.6, [(6.02, 13.4), (8.52, 13.4)]),            # J502 pines 1-3
    ("VBUS", "F.Cu", 0.6, [(6.02, 13.4), (6.02, 14.3)]),
    ("VBUS", "F.Cu", 0.6, [(7.27, 13.4), (7.27, 14.3)]),
    ("VBUS", "F.Cu", 0.6, [(8.52, 13.4), (8.52, 14.3)]),
    ("VBUS", "F.Cu", 0.6, [(5.03, 13.0), (5.6, 13.0), (6.02, 13.4)]),   # cátodo de D501
    ("VBUS", "B.Cu", 0.6, [(12.8, 11.1), (17.1, 11.1), (17.1, 11.25)]),  # pin 5 de U501
    ("VBUS", "F.Cu", 0.6, [(17.1, 11.25), (17.1, 12.25)]),
    # ------------------------------------------------ D+/D-: cruce de los contactos A y B del USB-C
    # D+ (B6 9.65 y A6 10.65) se unen por F.Cu con una U que rodea la vía de A7 (D-); D- (A7 10.15 y
    # B7 11.15) se une por B.Cu y vuelve a F.Cu debajo de la U.
    ("USB_DP", "F.Cu", 0.2, [(9.65, 7.79), (9.65, 8.0), (9.45, 8.2), (9.45, 9.35), (10.85, 9.35), (10.85, 8.2),
                             (10.65, 8.0), (10.65, 7.79)]),
    ("USB_DN", "F.Cu", 0.2, [(10.15, 7.79), (10.15, 8.7)]),
    ("USB_DN", "F.Cu", 0.2, [(11.15, 7.79), (11.15, 7.9), (11.45, 8.2), (11.45, 8.75)]),
    ("USB_DN", "B.Cu", 0.25, [(10.15, 8.7), (11.45, 8.75)]),
    ("USB_DN", "B.Cu", 0.25, [(10.15, 8.7), (10.15, 10.0)]),
    # Par hacia J502 (7 = D-, 8 = D+), 0.25 mm con 0.2 mm entre pistas
    ("USB_DP", "F.Cu", 0.25, [(10.85, 9.35), (10.85, 12.0), (11.1, 12.25), (16.15, 12.25)]),
    ("USB_DN", "F.Cu", 0.25, [(10.15, 10.0), (10.15, 12.45), (10.4, 12.7), (13.52, 12.7), (13.52, 14.3)]),
    # D+ atraviesa U501 (pin 6 -> pin 1, bajo el cuerpo) y entra a J502.8; D- llega a U501 por B.Cu
    ("USB_DP", "F.Cu", 0.25, [(16.15, 12.25), (16.15, 14.55), (14.77, 14.55)]),
    ("USB_DN", "B.Cu", 0.25, [(13.52, 13.35), (18.05, 13.35)]),
    ("USB_DN", "F.Cu", 0.25, [(18.05, 12.25), (18.05, 14.55)]),
    # ------------------------------------------------ CC: 5.1 kΩ a GND junto a las patas traseras del USB-C
    ("CC1", "F.Cu", 0.2, [(11.65, 7.79), (12.05, 8.3), (12.05, 9.75), (13.49, 9.75)]),
    ("CC2", "F.Cu", 0.2, [(8.65, 7.79), (8.65, 9.75), (7.31, 9.75)]),
    ("GND", "F.Cu", 0.3, [(14.51, 9.75), (14.6, 7.3)]),
    ("GND", "F.Cu", 0.3, [(6.29, 9.75), (6.2, 7.3)]),
    # ------------------------------------------------ GND de los pads del USB-C a las patas de la carcasa
    ("GND", "F.Cu", 0.4, [(7.2, 7.14), (6.07, 6.6)]),
    ("GND", "F.Cu", 0.4, [(13.6, 7.14), (14.73, 6.6)]),
    ("GND", "F.Cu", 0.3, [(17.1, 14.55), (17.1, 15.3), (16.62, 16.9)]),   # U501.2 -> anclaje derecho de J502
]
VIAS = [
    ("VBUS", 8.0, 8.25), ("VBUS", 8.0, 9.15), ("VBUS", 12.8, 8.25), ("VBUS", 12.8, 9.15),
    ("VBUS", 6.02, 13.4), ("VBUS", 7.27, 13.4), ("VBUS", 8.52, 13.4), ("VBUS", 17.1, 11.25),
    ("USB_DN", 10.15, 8.7), ("USB_DN", 11.45, 8.75), ("USB_DN", 10.15, 10.0),
    ("USB_DN", 13.52, 13.35), ("USB_DN", 18.05, 13.35),
]
# Textos: (texto, capa, u, v, tamaño, ángulo)
TEXTS = [
    ("TresVizo USB-C panel v0.1", "B.SilkS", 10.4, 14.6, 0.8, 0),
    ("J502: 1-3 VBUS 4-6 GND", "B.SilkS", 10.4, 15.9, 0.8, 0),
    ("7 D-  8 D+  cable 1:1", "B.SilkS", 10.4, 17.2, 0.8, 0),
]


def to_abs(u, v):
    return (round(OX + u, 4), round(OY + v, 4))


def rect(u1, v1, u2, v2):
    return [to_abs(u1, v1), to_abs(u2, v1), to_abs(u2, v2), to_abs(u1, v2)]


def circle_poly(u, v, r, n=32):
    return [to_abs(u + r * math.cos(2 * math.pi * k / n), v + r * math.sin(2 * math.pi * k / n)) for k in range(n)]


def fillet(pts, r, seg=6):
    """Redondea cada vértice de un polígono de ángulos rectos con radio r (convexos y cóncavos)."""
    out = []
    n = len(pts)
    for i in range(n):
        p, a, b = pts[i], pts[i - 1], pts[(i + 1) % n]
        d1 = ((a[0] - p[0]) / math.dist(a, p), (a[1] - p[1]) / math.dist(a, p))
        d2 = ((b[0] - p[0]) / math.dist(b, p), (b[1] - p[1]) / math.dist(b, p))
        c = (p[0] + (d1[0] + d2[0]) * r, p[1] + (d1[1] + d2[1]) * r)   # centro (esquina de 90°)
        t1 = (p[0] + d1[0] * r, p[1] + d1[1] * r)
        t2 = (p[0] + d2[0] * r, p[1] + d2[1] * r)
        a1 = math.atan2(t1[1] - c[1], t1[0] - c[0])
        a2 = math.atan2(t2[1] - c[1], t2[0] - c[0])
        da = (a2 - a1 + math.pi) % (2 * math.pi) - math.pi
        for k in range(seg + 1):
            ang = a1 + da * k / seg
            out.append((round(c[0] + r * math.cos(ang), 4), round(c[1] + r * math.sin(ang), 4)))
    return out


def outline_uv():
    t1, t2 = TONGUE
    corners = [(t1, V_FRONT), (t2, V_FRONT), (t2, V_BODY), (W, V_BODY), (W, V_REAR), (0.0, V_REAR), (0.0, V_BODY),
               (t1, V_BODY)]
    return fillet(corners, R_CORNER)


def outline():
    return [to_abs(u, v) for u, v in outline_uv()]


def tab_keepouts():
    out = []
    for edge, vc in TABS:
        v1, v2 = vc - TAB_W / 2 - 0.5, vc + TAB_W / 2 + 0.5
        u1, u2 = (0.0, TAB_DEPTH) if edge == "left" else (W - TAB_DEPTH, W)
        out.append((edge, rect(u1 - 0.5 if edge == "left" else u1, v1, u2 + 0.5 if edge == "right" else u2, v2)))
    return out


def write_board_json(design, kicad_dir, place=None):
    place = place or PLACE
    placement = {}
    for p in design.parts:
        if p.ref.startswith("#"):
            continue
        u, v, rot = place[p.ref]
        x, y = to_abs(u, v)
        placement[p.ref] = {"x": x, "y": y, "rot": rot, "side": "F", "show_ref": True}
    zones = [
        {"net": "GND", "layer": "In1.Cu", "priority": 0, "name": "PUSB_GND_L2"},
        {"net": "GND", "layer": "In2.Cu", "priority": 0, "name": "PUSB_GND_L3"},
        {"net": "GND", "layer": "F.Cu", "priority": 0, "name": "PUSB_GND_TOP", "post": True},
        {"net": "GND", "layer": "B.Cu", "priority": 0, "name": "PUSB_GND_BOT", "post": True},
    ]
    cu = ["F.Cu", "In1.Cu", "In2.Cu", "B.Cu"]
    keepouts = [{"rule_area": True, "name": "pusb_agujero_" + name, "polygon": circle_poly(u, v, HOLE_KEEPOUT_R),
                 "layers": cu, "no_tracks": True, "no_vias": True, "no_pour": True} for name, u, v in HOLES]
    keepouts += [{"rule_area": True, "name": "pusb_puente_" + edge, "polygon": poly, "layers": cu, "no_tracks": True,
                  "no_vias": True, "no_pour": True} for edge, poly in tab_keepouts()]
    spec = {
        "libs": {"tresvizo_lcsc": "lib/lcsc.pretty"},
        "board": {"layers": 4, "thickness": 1.6, "outline": {"type": "polygon", "points": outline()},
                  "holes": [{"ref": n, "x": to_abs(u, v)[0], "y": to_abs(u, v)[1],
                             "footprint": "MountingHole_2.2mm_M2"} for n, u, v in HOLES]},
        "rules": RULES,
        "netclasses": NETCLASSES,
        "placement": placement,
        "fanout": {"nets": ["GND"], "skip_refs": ["J501"]},
        # Vías de cosido de GND en rejilla de 2 mm donde queden libres
        "stitching": {"pitch": 2.0, "dia": 0.6, "drill": 0.3, "clearance": 0.25, "edge": 0.8,
                      "no_vias_under": ["U501", "J502", "D501"]},
        "zones": zones + keepouts,
        "tracks": [{"net": n, "layer": l, "width": w, "points": [to_abs(u, v) for u, v in pts]}
                   for n, l, w, pts in TRACKS],
        "vias": [{"net": n, "x": to_abs(u, v)[0], "y": to_abs(u, v)[1]} for n, u, v in VIAS],
        "texts": [{"text": t, "layer": l, "x": to_abs(u, v)[0], "y": to_abs(u, v)[1], "size": sz, "angle": a}
                  for t, l, u, v, sz, a in TEXTS],
    }
    with open(os.path.join(kicad_dir, "board.json"), "w", encoding="utf-8") as f:
        json.dump(spec, f, indent=1)
