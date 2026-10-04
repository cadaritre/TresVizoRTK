"""Geometría de la placa y colocación de componentes (escribe kicad/board.json).

Coordenadas locales (u, v) en mm, vista desde la cara de componentes (la que mira al
panel): u hacia la derecha, v hacia abajo, origen en la esquina superior izquierda.
Correspondencia con la carcasa V2.2 (constraints.md 1.4): z = 97 - v (eje del jalón,
hacia la antena) y x_equipo = 25 - u. El BMI088 va en u = 25 (sobre el eje).
"""

import json
import os

OX, OY = 100.0, 100.0  # origen de la placa en la hoja de KiCad
W, H = 50.0, 76.0

# ---------------------------------------------------------------- colocación
# ref: (u, v, rot)   rot en grados, antihorario visto desde arriba (convención de KiCad)
PLACE = {
    # ================================================= GNSS (franja superior)
    "U301": (25.0, 15.2, 270),   # UM980: ANT_IN a la izquierda; COM2 abajo; VCC a la derecha
    # Fila superior de resistencias (los pines 42-53 del UM980 miran al canto superior)
    "R315": (17.8, 2.1, 90), "R310": (19.1, 2.1, 90), "R305": (20.4, 2.1, 90), "R316": (21.7, 2.1, 90),
    "R311": (23.9, 2.1, 90), "R302": (25.3, 2.1, 90), "R314": (30.2, 2.1, 90), "R313": (31.6, 2.1, 90),
    # RF y alimentación de antena (franja izquierda)
    "J301": (8.6, 9.15, 180), "D302": (10.7, 9.47, 270), "L301": (12.0, 8.45, 270), "C310": (14.4, 9.15, 0),
    "C309": (10.4, 6.9, 0), "C308": (8.0, 6.0, 90), "D301": (5.0, 6.0, 90),
    "U302": (5.6, 12.2, 0), "C307": (5.6, 14.6, 0), "R312": (8.7, 13.2, 90),
    "J302": (12.7, 21.0, 90),    # UM980_AUX (SH5 vertical)
    "SW201": (4.6, 21.0, 90), "SW202": (8.2, 21.0, 90),   # RESET y BOOT, accesibles quitando la tapa
    # Franja derecha: riel del UM980, desacoplo y resistencias serie
    "U106": (42.0, 10.2, 0), "C122": (39.4, 10.2, 90), "R122": (44.6, 10.2, 90), "FB101": (45.0, 13.4, 90),
    "C304": (35.3, 16.3, 90), "C305": (36.5, 16.3, 90), "C301": (38.4, 16.3, 90), "C302": (40.7, 16.3, 90),
    "C303": (43.0, 16.3, 90), "R301": (35.6, 13.6, 0), "C306": (35.6, 12.3, 0),
    "R308": (35.6, 19.0, 0), "R309": (35.6, 20.5, 0), "R304": (37.9, 21.3, 0), "R303": (37.9, 22.6, 0),
    "TP301": (41.0, 22.2, 0), "TP302": (43.4, 22.2, 0), "TP306": (45.6, 19.4, 0),
    "R306": (28.9, 28.6, 90), "R307": (30.3, 28.6, 90),
    "TP303": (21.6, 29.4, 0), "TP304": (23.8, 29.4, 0), "TP305": (26.0, 29.4, 0),
    # ================================================= IMU en el eje
    "U401": (25.0, 36.5, 180), "C403": (28.0, 36.0, 90), "C404": (22.0, 37.0, 90),
    # ================================================= Panel (derecha, ventana)
    "J402": (39.0, 30.5, 0),     # PANEL_UI (SH9 vertical)
    "J403": (36.0, 38.5, 0),     # OLED (SH4 vertical)
    "R408": (30.4, 34.4, 90), "D402": (32.0, 33.8, 90), "D401": (35.4, 33.7, 90), "R412": (36.4, 34.1, 90),
    "Q402": (38.6, 34.3, 0), "R409": (40.6, 34.1, 90), "R410": (41.9, 34.1, 90), "R411": (43.2, 34.1, 90),
    "R111": (44.5, 34.1, 90), "R413": (40.8, 36.5, 0),
    # ================================================= USB del panel (izquierda, ventana)
    "J101": (12.5, 34.5, 270),   # PANEL_USB (PH6 vertical): VBUS abajo, D+/D- arriba
    "D101": (17.4, 40.8, 90), "U101": (18.8, 31.0, 90), "R101": (17.6, 35.0, 0), "R102": (17.6, 36.3, 0),
    "TP206": (5.0, 30.0, 0), "TP207": (5.0, 32.4, 0),
    # ================================================= Cargador BQ25798 (izquierda, girado 270°)
    "U102": (11.0, 52.0, 270), "L101": (17.0, 52.0, 90), "C104": (12.9, 44.0, 180), "C103": (10.2, 46.6, 90), "C105": (15.9, 43.6, 0),
    "C109": (13.9, 48.2, 90),
    "C106": (17.0, 46.2, 90), "C107": (19.3, 46.2, 90), "C108": (21.6, 46.2, 90), "C101": (8.2, 46.6, 90),
    "C113": (15.0, 56.4, 270), "C110": (17.2, 57.4, 270), "C111": (19.5, 57.4, 270), "C112": (21.8, 57.4, 270),
    "Q101": (12.6, 57.6, 90), "C114": (7.7, 58.0, 90), "C102": (20.6, 53.4, 90),
    # Divisores de TS/ILIM y PROG a 3.5 mm del BQ25798: deja canal para que salgan sus 8 pines de la izquierda
    "R106": (5.0, 50.4, 0), "R108": (5.0, 51.7, 0), "R107": (3.0, 51.8, 90),
    "R103": (5.0, 53.0, 0), "R104": (5.0, 54.3, 0), "R105": (3.0, 54.6, 90), "R109": (9.9, 56.2, 90),
    # Batería: polaridad inversa
    "J102": (8.6, 66.0, 0),
    "Q102": (10.6, 60.6, 0), "Q103": (13.4, 62.6, 0), "R112": (13.4, 59.9, 90), "R113": (14.8, 64.7, 0),
    "R114": (14.8, 66.0, 0),
    # ================================================= microSD (abajo, centro)
    "J401": (24.3, 66.35, 0), "C401": (14.6, 72.0, 90), "C402": (15.4, 60.2, 90),
    # ================================================= ESP32 (abajo a la derecha, antena al canto derecho)
    "U201": (34.6, 53.3, 270),
    "C202": (39.4, 44.6, 90), "C201": (42.6, 43.0, 0), "R202": (44.0, 39.6, 0), "R203": (44.0, 40.9, 0),
    "R204": (41.5, 39.6, 0), "R205": (41.5, 40.9, 0), "R110": (44.0, 37.0, 0), "R116": (44.0, 38.3, 0),
    # ================================================= Zona inferior derecha
    "R401": (32.8, 64.0, 90), "R402": (34.0, 64.0, 90), "R403": (35.2, 64.0, 90), "R404": (36.4, 64.0, 90),
    "R405": (37.6, 64.0, 90), "R406": (38.8, 64.0, 90), "Q401": (41.4, 64.0, 0),
    "R407": (43.6, 65.4, 90), "R201": (44.8, 65.4, 90), "C203": (46.0, 65.4, 90),
    # 3.3 V
    "C116": (33.2, 67.8, 90), "C117": (35.0, 66.2, 90), "U105": (36.4, 67.4, 0), "L102": (36.4, 70.4, 0),
    "R118": (39.8, 66.4, 0), "R119": (39.8, 67.7, 0), "R120": (39.8, 69.0, 0), "R121": (39.8, 70.3, 0),
    "C118": (41.8, 68.4, 90), "C119": (43.6, 68.6, 90), "C120": (45.9, 68.6, 90), "C121": (37.0, 73.0, 0),
    # Medidor de batería
    "U103": (41.0, 73.2, 0), "C115": (43.4, 73.2, 0), "R115": (45.4, 73.2, 90), "R117": (46.6, 73.2, 90),
    "TP201": (33.0, 74.6, 0), "TP202": (35.2, 74.6, 0), "TP203": (46.0, 40.0, 0), "TP204": (46.0, 42.2, 0),
    "TP205": (46.0, 44.4, 0),
    # Otros
    "J404": (5.0, 41.0, 90),     # NTC opcional (sin montar)
}

HOLES = [("H1", 12.0, 3.0), ("H2", 38.0, 3.0)]

# Pistas fijadas antes del autorruteo: (red, capa, ancho, [(u, v), ...])
TRACKS = [
    # Línea de 50 ohm (CPWG 0.30 / 0.20 sobre GND de L2, JLC04161H-7628): u.FL -> ESD/choke -> C de bloqueo -> ANT_IN
    ("ANT_RF", "F.Cu", 0.30, [(9.36, 9.15), (13.92, 9.15)]),
    ("GNSS_ANT_IN", "F.Cu", 0.30, [(14.88, 9.15), (17.55, 9.15)]),
    # BQ25798 girado 270°: PMID, SW1, GND, SW2 y SYS salen por la derecha hacia la bobina
    ("CHG_SW1", "F.Cu", 0.25, [(12.72, 51.55), (14.4, 51.55), (15.9, 50.55)]),
    ("CHG_SW1", "F.Cu", 0.60, [(15.9, 50.55), (16.6, 50.2)]),
    ("CHG_SW2", "F.Cu", 0.25, [(12.72, 52.45), (14.4, 52.45), (15.9, 53.45)]),
    ("CHG_SW2", "F.Cu", 0.60, [(15.9, 53.45), (16.6, 53.8)]),
    ("GND", "F.Cu", 0.25, [(12.72, 52.0), (16.6, 52.0)]),
    ("PMID", "F.Cu", 0.25, [(12.75, 51.1), (13.9, 51.1), (13.9, 48.68)]),
    ("VSYS", "F.Cu", 0.25, [(12.72, 52.9), (13.95, 52.9), (13.95, 55.6), (14.6, 55.6)]),
    ("CHG_SDRV", "F.Cu", 0.20, [(12.87, 53.78), (13.35, 54.3), (13.35, 56.0), (13.55, 56.3)]),
    ("VBAT_CHG", "F.Cu", 0.20, [(11.82, 53.95), (12.22, 53.95)]),
    ("VBAT_CHG", "F.Cu", 0.40, [(12.02, 54.2), (12.02, 56.6), (11.65, 56.6)]),
    ("VPACK", "F.Cu", 0.50, [(12.6, 58.6), (12.6, 59.2), (11.75, 59.65)]),
    ("VBATT_IN", "F.Cu", 0.60, [(9.45, 60.6), (9.6, 61.4), (9.6, 63.07)]),
    # VBUS (hasta ~2.2 A cargando 2S): J101 -> TVS / 22 uF / 100 nF -> pines 2 y 3 del BQ25798
    ("VBUS", "F.Cu", 0.80, [(14.6, 39.6), (14.6, 43.2), (13.85, 44.0)]),
    ("VBUS", "F.Cu", 0.40, [(14.6, 43.2), (15.42, 43.6)]),
    ("VBUS", "F.Cu", 0.50, [(14.6, 42.53), (17.4, 42.53)]),
    ("VBUS", "F.Cu", 0.60, [(13.85, 44.0), (13.85, 44.8), (12.0, 46.65), (12.0, 49.55)]),
    ("VBUS", "F.Cu", 0.25, [(12.0, 49.55), (12.2, 49.85)]),
    ("VBUS", "F.Cu", 0.25, [(12.0, 49.55), (11.8, 49.85)]),
]
VIAS = [
    ("GND", 15.3, 52.0), ("GND", 16.6, 52.0),                          # GND del BQ bajo la bobina
    ("GND", 10.7, 10.45), ("GND", 13.0, 9.95), ("GND", 13.0, 8.35),    # cerca de la línea RF
    ("GND", 15.7, 9.95), ("GND", 15.7, 8.35), ("GND", 6.6, 7.2), ("GND", 7.9, 11.8),
] + [("GND", 25.0 - y, 15.2 + x) for x in (0.0, 2.1, -2.1, 4.2, -4.2, 6.3, -6.3) for y in (0.0, 2.1, -2.1, 4.2, -4.2)]
# 35 vías de GND entre los pads interiores del UM980 (pads de 1.1 mm a paso 2.1; manual Unicore 3.4)
# Textos: (texto, capa, u, v, tamaño, ángulo)
TEXTS = [
    ("ANT", "F.SilkS", 4.6, 9.3, 0.8, 0),
    ("AUX", "F.SilkS", 12.7, 25.7, 0.8, 0),
    ("RST", "F.SilkS", 4.6, 25.0, 0.8, 0),
    ("BOOT", "F.SilkS", 8.4, 25.0, 0.8, 0),
    ("USB", "F.SilkS", 9.5, 34.5, 0.8, 90),
    ("PANEL", "F.SilkS", 39.0, 27.4, 0.8, 0),
    ("OLED", "F.SilkS", 36.0, 41.4, 0.8, 0),
    ("BAT 1- 2+", "F.SilkS", 8.6, 72.2, 0.8, 0),
    ("microSD", "F.SilkS", 24.3, 74.6, 0.8, 0),
    ("TresVizo v0.1", "F.SilkS", 45.6, 26.0, 0.8, 90),
    ("IMU BMI088", "F.Fab", 25.0, 32.6, 0.6, 0),
    ("Ejes (verificar con Bosch fig. 12): X sensor -> derecha, Y sensor -> arriba (antena)", "F.Fab", 25.0, 31.6, 0.5, 0),
    ("TresVizo MeridianV - placa principal v0.1 (2026-10)", "B.SilkS", 25.0, 30.0, 1.0, 0),
    ("1S: R105=4.7k R119=10k U103=MAX17048", "B.SilkS", 25.0, 33.0, 0.8, 0),
    ("2S: R105=8.2k R119=3.9k U103=MAX17049 R115 NC R117 0R", "B.SilkS", 25.0, 34.6, 0.8, 0),
    ("JLCJLCJLCJLC", "B.SilkS", 25.0, 40.0, 1.0, 0),
]

# Zonas de potencia en la capa superior (prioridad sobre el relleno de GND)
POWER_ZONES = [
    ("PMID", [(13.6, 46.6), (22.8, 46.6), (22.8, 48.9), (13.6, 48.9)]),
    ("VSYS", [(14.4, 55.25), (23.0, 55.25), (23.0, 57.0), (14.4, 57.0)]),
]


def to_abs(u, v):
    return (round(OX + u, 4), round(OY + v, 4))


def rect(u1, v1, u2, v2):
    return [to_abs(u1, v1), to_abs(u2, v1), to_abs(u2, v2), to_abs(u1, v2)]


def circle_poly(u, v, r, n=24):
    import math
    return [to_abs(u + r * math.cos(2 * math.pi * k / n), v + r * math.sin(2 * math.pi * k / n)) for k in range(n)]


def outline():
    c = 1.0  # chaflanes de 1 x 1 para entrar en los rieles
    pts = [(c, 0), (W - c, 0), (W, c), (W, H - c), (W - c, H), (c, H), (0, H - c), (0, c)]
    return [to_abs(u, v) for u, v in pts]


# Clases de red: las usan la placa (board.json) y el archivo de proyecto (circuit.py)
NETCLASSES = {
    "Default": {"track": 0.2, "clearance": 0.15, "via_dia": 0.6, "via_drill": 0.3, "nets": []},
    "Power": {"track": 0.4, "clearance": 0.15, "via_dia": 0.8, "via_drill": 0.4, "priority": 1,
              "nets": ["VBUS", "VSYS", "PMID", "VBAT_CHG", "VPACK", "VBATT_IN", "CHG_SW1", "CHG_SW2",
                       "BUCK_SW", "GNSS_SW", "+3V3_GNSS"]},
    "RF": {"track": 0.3, "clearance": 0.2, "via_dia": 0.6, "via_drill": 0.3, "priority": 0,
           "nets": ["ANT_RF", "GNSS_ANT_IN"]},
    "USB": {"track": 0.25, "clearance": 0.15, "via_dia": 0.6, "via_drill": 0.3, "priority": 2,
            "nets": ["USB_DP", "USB_DN"]},
}


def write_board_json(design, kicad_dir, place=None):
    place = place or PLACE
    placement = {}
    staging_u, staging_v = W + 10.0, 0.0
    for p in design.parts:
        if p.ref.startswith("#"):
            continue
        if p.ref in place:
            u, v, rot = place[p.ref]
            x, y = to_abs(u, v)
            placement[p.ref] = {"x": x, "y": y, "rot": rot, "side": "F",
                                "show_ref": p.ref[0] in "UJL" and not p.ref.startswith("L3")}
        else:
            x, y = to_abs(staging_u, staging_v)
            placement[p.ref] = {"x": x, "y": y, "rot": 0, "side": "F"}
            staging_v += 3.0
            if staging_v > 90:
                staging_v = 0.0
                staging_u += 6.0
    zones = [{"net": n, "layer": "F.Cu", "priority": 2, "name": n + "_pour", "polygon": [to_abs(u, v) for u, v in poly],
              "clearance": 0.2, "solid_pads": True} for n, poly in POWER_ZONES]
    zones += [
        {"net": "GND", "layer": "In1.Cu", "priority": 0, "name": "GND_L2"},
        {"net": "+3V3", "layer": "In2.Cu", "priority": 0, "name": "3V3_L3"},
        {"net": "GND", "layer": "F.Cu", "priority": 0, "name": "GND_TOP", "post": True},
        {"net": "GND", "layer": "B.Cu", "priority": 0, "name": "GND_BOT", "post": True},
    ]
    keepouts = []
    for name, u, v in HOLES:
        keepouts.append({"rule_area": True, "name": "hole_" + name, "polygon": circle_poly(u, v, 3.0),
                         "layers": ["F.Cu", "In1.Cu", "In2.Cu", "B.Cu"], "no_tracks": True, "no_vias": True,
                         "no_pour": True})
    # Antena del ESP32-S3-MINI-1 en el canto derecho: sin cobre en ninguna capa (guía de Espressif).
    keepouts.append({"rule_area": True, "name": "esp32_antena", "polygon": rect(42.0, 45.0, W, 61.5),
                     "layers": ["F.Cu", "In1.Cu", "In2.Cu", "B.Cu"], "no_tracks": True, "no_vias": True,
                     "no_pour": True})
    # BMI088: nada de cobre de la capa superior bajo el encapsulado (Bosch) ni vías bajo él.
    keepouts.append({"rule_area": True, "name": "imu_top", "polygon": rect(24.3, 35.6, 25.7, 37.4),
                     "layers": ["F.Cu"], "no_tracks": True, "no_vias": True, "no_pour": True})
    # BQ25798 (VQFN sin pad expuesto): bajo la mitad del encapsulado que da a SW1/SW2/PMID/SYS no pasan
    # pistas ni vías; la otra mitad queda libre para que salgan sus pines (TI también usa ese hueco).
    keepouts.append({"rule_area": True, "name": "u102_conmutacion", "polygon": rect(11.0, 50.75, 12.25, 53.25),
                     "layers": ["F.Cu"], "no_tracks": True, "no_vias": True, "no_pour": True})
    keepouts.append({"rule_area": True, "name": "imu_vias", "polygon": rect(23.4, 34.2, 26.6, 38.8),
                     "layers": ["F.Cu", "In1.Cu", "In2.Cu", "B.Cu"], "no_tracks": False, "no_vias": True,
                     "no_pour": False})
    spec = {
        "libs": {"tresvizo": "lib/tresvizo.pretty", "tresvizo_lcsc": "lib/lcsc.pretty"},
        "board": {"layers": 4, "thickness": 1.6, "outline": {"type": "polygon", "points": outline()},
                  "holes": [{"ref": n, "x": to_abs(u, v)[0], "y": to_abs(u, v)[1],
                             "footprint": "MountingHole_2.7mm"} for n, u, v in HOLES]},
        "rules": {"min_clearance": 0.127, "min_track": 0.127, "min_via_dia": 0.5, "min_drill": 0.3,
                  "min_annular": 0.1, "hole_to_hole": 0.5, "edge_clearance": 0.3, "hole_clearance": 0.25,
                  # Un radio térmico basta (pads de GND del UM980 y de 0402 rodeados de pistas)
                  "min_resolved_spokes": 1},
        "netclasses": NETCLASSES,
        # El BQ25798 (RQM0029A) no tiene modelo 3D en KiCad 10: se usa un VQFN de 4 x 4 x 1 mm
        "model_substitutes": {
            "Texas_RQM0029A_VQFN-29_4x4mm_P0.4mm.step":
                "${KICAD10_3DMODEL_DIR}/Package_DFN_QFN.3dshapes/Texas_RGE0024C_VQFN-24-1EP_4x4mm_P0.5mm_EP2.1x2.1mm.step"},
        "placement": placement,
        "fanout": {"nets": ["GND", "+3V3"], "skip_refs": ["U301", "U201"]},
        # Vías de cosido entre los rellenos de GND de F.Cu/B.Cu y el plano de L2, en rejilla de 3 mm
        "stitching": {"pitch": 3.0, "dia": 0.6, "drill": 0.3, "clearance": 0.25, "edge": 0.8,
                      "no_vias_under": ["U301", "U201", "U401", "J401", "U102", "U105"]},
        "zones": zones + keepouts,
        "tracks": [{"net": n, "layer": l, "width": w, "points": [to_abs(u, v) for u, v in pts]}
                   for n, l, w, pts in TRACKS],
        "vias": [{"net": n, "x": to_abs(u, v)[0], "y": to_abs(u, v)[1]} for n, u, v in VIAS],
        "texts": [{"text": t, "layer": l, "x": to_abs(u, v)[0], "y": to_abs(u, v)[1], "size": sz, "angle": a}
                  for t, l, u, v, sz, a in TEXTS],
    }
    with open(os.path.join(kicad_dir, "board.json"), "w", encoding="utf-8") as f:
        json.dump(spec, f, indent=1)
