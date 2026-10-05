"""Geometría de la placa principal v0.2 y colocación de componentes (escribe kicad/board.json y kicad/panel.json).

Coordenadas locales (u, v) en mm, vista desde la cara de componentes (la que mira al panel):
u hacia la derecha, v hacia abajo, origen en la esquina superior izquierda.
Posición en la carcasa V2.2 según el estudio mecánico de v0.2: plano axial con rieles, cara de
componentes en y = 3.1 mirando al panel, u = 23 - x, v = Z_TOP - z (x del equipo a la izquierda mirando
el panel, z hacia la antena). Detrás de la placa van la carrier BDLX y la 18650 (README, Mecánica).

La placa va 2.5 mm más arriba que en el primer estudio (z 23.5-87.5 en vez de 21-85): bajo el canto
inferior quedan 7.6 mm hasta la base para las clavijas enchufadas y el doblez de sus cables.
"""

import json
import math
import os

OX, OY = 100.0, 100.0  # origen de la placa en la hoja de KiCad
W, H = 46.0, 64.0
Z_TOP = 87.5            # z del canto superior en la carcasa: v = Z_TOP - z
# M2.5 sin metalizar Ø2.7, sin cobre en Ø5.2; se atornillan a dos brazos impresos detrás de la placa
# (|x| >= 10 para no tocar el SMA de la carrier). H2 en la esquina superior derecha; H1 bajo el IMU.
HOLES = [("H1", 12.0, 12.2), ("H2", 40.4, 3.7)]
HOLE_FREE_R = 2.6
# Rieles de la carcasa: 2.5 mm libres en cada canto lateral desde arriba hasta v 48.5 (rieles en z 39-90);
# el de la izquierda (+X) se corta frente a la antena del ESP32 (v 16.5-33.5, z 54-71). Por debajo de z 39
# no hay riel: ahí llegan al canto la microSD y la batería.
RAIL_FREE, RAIL_V_END, RAIL_CUT = 2.5, 48.5, (16.5, 33.5)
# Botón del panel: nada frente a él (z 38-49, x ±5.5); su cuerpo (x ±8.1, z 35.4-51.6) deja 2.5 mm
BUTTON_KEEPOUT = (17.5, Z_TOP - 49.0, 28.5, Z_TOP - 38.0)


def rot_pt(x, y, rot):
    """Giro de KiCad (antihorario en pantalla, v hacia abajo)."""
    a = math.radians(rot)
    return (x * math.cos(a) + y * math.sin(a), -x * math.sin(a) + y * math.cos(a))


def block(origin, rot, parts=None, tracks=None, vias=None):
    """Pasa un bloque en coordenadas propias (x, y, giro) a coordenadas de placa."""
    u0, v0 = origin
    out_p, out_t, out_v = {}, [], []
    for ref, (x, y, r) in (parts or {}).items():
        dx, dy = rot_pt(x, y, rot)
        out_p[ref] = (round(u0 + dx, 3), round(v0 + dy, 3), (r + rot) % 360)
    for net, layer, w, pts in tracks or []:
        out_t.append((net, layer, w, [tuple(round(c, 3) for c in (u0 + rot_pt(x, y, rot)[0],
                                                                       v0 + rot_pt(x, y, rot)[1])) for x, y in pts]))
    for net, x, y in vias or []:
        dx, dy = rot_pt(x, y, rot)
        out_v.append((net, round(u0 + dx, 3), round(v0 + dy, 3)))
    return out_p, out_t, out_v


# ------------------------------------------------------------------------ cargador
# BQ25798 en (0, 0) con los pines de potencia arriba (girado 0), como en el ejemplo de TI (hoja, 8.4):
# - 100 nF de PMID (C108) sobre los pines 29 (PMID) y 27 (GND) y 100 nF de SYS (C112) junto al 25,
#   con GND en T al pin 27; los 22 uF de PMID y de SYS en columnas a cada lado.
# - SW1 y SW2 bajan por 3 vías cada uno bajo el chip y suben por B.Cu (1 mm) a la bobina, arriba.
# - Bootstrap (C101 y C102) en la cara superior junto a sus pines (no hay cara inferior): su lado de
#   SW baja por una vía y llega por B.Cu a la columna de vías de SW bajo el chip.
CHG_PARTS = {
    "U102": (0.0, 0.0, 0),
    "C108": (-0.45, -2.95, 0),
    "C112": (0.95, -3.4, 90),
    "C106": (-3.3, -3.75, 180), "C107": (-3.3, -5.75, 180),
    "C109": (3.3, -3.75, 0), "C110": (3.3, -5.75, 0),
    "L101": (0.0, -10.2, 180),
    "C105": (-3.7, -2.25, 180),
    "C104": (-7.0, -2.6, 90),
    "C101": (-4.3, -0.4, 180),
    "C102": (5.0, 0.4, 0),
    "C113": (6.9, -3.3, 0),
}
CHG_TRACKS = [
    ("PMID", "F.Cu", 0.2, [(-0.9, -2.2), (-0.93, -2.64)]),
    ("GND", "F.Cu", 0.2, [(0.0, -2.2), (0.03, -2.64)]),
    ("VSYS", "F.Cu", 0.2, [(0.9, -2.2), (0.95, -2.92)]),
    ("GND", "F.Cu", 0.4, [(0.95, -3.88), (0.4, -3.88), (0.03, -3.26)]),
    ("PMID", "F.Cu", 0.5, [(-1.21, -2.95), (-2.35, -2.95), (-2.35, -5.75)]),
    ("VSYS", "F.Cu", 0.5, [(1.26, -2.92), (1.6, -2.92), (2.35, -3.3), (2.35, -5.75)]),
    # SW1 / SW2: del extremo interior del pad a una columna de 3 vías bajo el chip (x = -1.0 / +1.0)
    ("CHG_SW1", "F.Cu", 0.2, [(-0.45, -1.2), (-0.45, -0.55)]),
    ("CHG_SW1", "F.Cu", 0.4, [(-0.45, -0.55), (-1.0, -0.55), (-1.0, 1.1)]),
    ("CHG_SW2", "F.Cu", 0.2, [(0.45, -1.2), (0.45, -0.55)]),
    ("CHG_SW2", "F.Cu", 0.4, [(0.45, -0.55), (1.0, -0.55), (1.0, 1.1)]),
    ("CHG_SW1", "B.Cu", 1.0, [(-1.0, 1.1), (-1.0, -7.9), (-1.6, -8.4), (-2.5, -8.4)]),
    ("CHG_SW2", "B.Cu", 1.0, [(1.0, 1.1), (1.0, -7.9), (1.6, -8.4), (2.5, -8.4)]),
    ("CHG_SW1", "F.Cu", 0.8, [(-1.6, -8.4), (-2.5, -8.4)]),
    ("CHG_SW1", "F.Cu", 0.8, [(-2.05, -8.4), (-2.05, -9.3)]),
    ("CHG_SW2", "F.Cu", 0.8, [(1.6, -8.4), (2.5, -8.4)]),
    ("CHG_SW2", "F.Cu", 0.8, [(2.05, -8.4), (2.05, -9.3)]),
    ("CHG_BTST1", "F.Cu", 0.2, [(-2.2, -0.4), (-3.075, -0.4)]),
    ("CHG_SW1", "F.Cu", 0.4, [(-5.075, 0.45), (-5.075, -0.4)]),
    ("CHG_SW1", "B.Cu", 0.4, [(-5.075, 0.45), (-1.0, 0.45), (-1.0, 0.25)]),
    # Fila inferior (pines 17-24, paso 0.4): cada pin sale recto y se abre en abanico escalonado; el
    # bootstrap 2 baja recto a C102 y su lado SW sube por B.Cu a la columna de vías de SW2.
    ("CHG_ILIM", "F.Cu", 0.2, [(2.2, 1.2), (2.45, 1.2), (2.85, 1.6), (3.6, 1.6)]),
    ("CHG_BATP", "F.Cu", 0.2, [(2.2, 0.8), (2.85, 0.8), (3.25, 1.2), (7.09, 1.2)]),
    ("CHG_BTST2", "F.Cu", 0.2, [(2.2, 0.4), (3.77, 0.4)]),
    ("CHG_SW2", "F.Cu", 0.4, [(5.775, 0.4), (6.7, 0.4)]),
    ("CHG_SW2", "B.Cu", 0.4, [(6.7, 0.4), (1.0, 0.4)]),
    ("CHG_PROG", "F.Cu", 0.2, [(2.2, 0.0), (2.85, 0.0), (3.25, -0.4), (7.12, -0.4)]),
    ("CHG_INT_N", "F.Cu", 0.2, [(2.2, -0.4), (2.45, -0.4), (2.85, -0.8), (4.6, -0.8), (5.0, -1.2), (6.2, -1.2)]),
    ("CHG_SDRV", "F.Cu", 0.2, [(2.2, -1.6), (2.7, -1.6), (3.15, -2.05), (3.45, -2.05)]),
    # VBUS: los pines 2 y 3 se juntan fuera del chip y van al 100 nF y al 22 uF
    ("VBUS", "F.Cu", 0.2, [(-2.2, -1.2), (-2.6, -1.2)]),
    ("VBUS", "F.Cu", 0.2, [(-2.2, -0.8), (-2.45, -0.8), (-2.75, -1.1)]),
    ("VBUS", "F.Cu", 0.5, [(-2.6, -1.2), (-2.75, -1.1), (-2.95, -1.42), (-7.0, -1.42), (-7.0, -1.65)]),
    ("VBUS", "F.Cu", 0.3, [(-3.22, -2.25), (-3.22, -1.42)]),
    ("GND", "F.Cu", 0.3, [(-4.18, -2.25), (-4.2, -3.3)]),
    # BAT: pines 22 y 23 unidos entre sí; baja por el 23 y va en diagonal al 22 uF (C113), abajo a la derecha
    ("VBAT_CHG", "F.Cu", 0.2, [(1.9, -0.8), (1.9, -1.2)]),
    ("VBAT_CHG", "F.Cu", 0.25, [(2.2, -1.2), (4.1, -1.2)]),
    ("VBAT_CHG", "F.Cu", 0.25, [(4.1, -1.2), (5.3, -2.4)]),
    ("VBAT_CHG", "F.Cu", 0.5, [(5.3, -2.4), (5.3, -3.3), (5.5, -3.3)]),
]
CHG_VIAS = [("CHG_SW1", -1.0, y) for y in (-0.55, 0.25, 1.1)] + \
    [("CHG_SW2", 1.0, y) for y in (-0.55, 0.25, 1.1)] + [
    ("CHG_SW1", -5.075, 0.45), ("CHG_SW2", 6.7, 0.4),
    ("CHG_SW1", -1.6, -8.4), ("CHG_SW1", -2.5, -8.4), ("CHG_SW2", 1.6, -8.4), ("CHG_SW2", 2.5, -8.4),
    ("GND", 0.0, -4.4), ("GND", 0.0, -5.3), ("GND", 0.0, -6.2),
]
CHG_ORIGIN, CHG_ROT = (30.5, 22.4), 270   # VBUS hacia arriba (J101), BAT hacia abajo, I2C hacia el ESP32

# ------------------------------------------------------------- 5 V de la carrier GNSS
# TPS63070 en (0, 0): VIN a la izquierda con 100 nF + 2 x 10 uF, VOUT a la derecha con 3 x 22 uF,
# bobina sobre L1/L2 y PGND al pin 4 (GND) por debajo del chip; VAUX, EN y FB con sus piezas al lado.
G5_PARTS = {
    "U301": (0.0, 0.0, 0), "L301": (0.0, -3.3, 0),
    "C303": (-2.2, -1.0, 270), "C301": (-3.75, -0.7, 270), "C302": (-5.75, -0.7, 270),
    "C305": (2.95, -0.7, 270), "C306": (4.95, -0.7, 270), "C307": (6.95, -0.7, 270),
    "C304": (0.0, 2.2, 270), "R301": (-2.6, 2.2, 270), "R302": (2.7, 1.55, 180), "R303": (2.7, 2.65, 0),
}
G5_TRACKS = [
    ("GNSS_L1", "F.Cu", 0.25, [(-0.5, -1.635), (-0.5, -2.45)]),
    ("GNSS_L2", "F.Cu", 0.25, [(0.5, -1.635), (0.5, -2.45)]),
    # PGND sube entre los pads de la bobina hasta su vía al plano de GND
    ("GND", "F.Cu", 0.35, [(0.0, -1.63), (0.0, -4.75)]),
    ("VSYS", "F.Cu", 0.4, [(-1.4, -0.96), (-2.2, -1.48), (-3.75, -1.65), (-5.75, -1.65)]),
    ("GNSS_PWR_EN", "F.Cu", 0.2, [(-1.4, 0.04), (-1.7, 0.04), (-2.1, 0.44), (-2.6, 0.44), (-2.6, 1.69)]),
    # GND de C303 (entre VSYS y EN) al GND de C301, que tiene su vía
    ("GND", "F.Cu", 0.3, [(-2.45, -0.35), (-3.25, 0.0)]),
    ("VSYS", "F.Cu", 0.25, [(-1.4, -0.46), (-1.4, -0.96)]),
    ("GNSS_5V", "F.Cu", 0.4, [(1.4, -0.96), (2.95, -1.65), (6.95, -1.65)]),
    ("GNSS_5V", "F.Cu", 0.25, [(1.4, -0.46), (1.7, -0.71)]),
]
G5_VIAS = [("GND", 0.0, -5.0)]
G5_ORIGIN = (35.4, 43.6)

# ---------------------------------------------------------------- resto de la placa
PLACE = {
    # ESP32-S3-MINI-1 con la antena en el canto izquierdo (+X del equipo), fuera de la sombra de la carrier
    "U201": (13.6, 25.3, 90),
    # ---- conectores de cable (todos de entrada lateral; ver SIDE_ENTRY y las zonas de clavija)
    # Canto superior, boca hacia arriba (la clavija sale por encima del canto): IMU, USB del panel (justo
    # bajo el conector de la placa panel-usb) y LEDs del panel.
    "J405": (9.1, 3.45, 180), "J101": (22.7, 3.45, 180), "J406": (33.6, 3.45, 180),
    # OLED: dentro de la placa, boca hacia la izquierda sobre una zona libre bajo los pines de la OLED
    "J403": (27.6, 11.0, 270),
    # Botón: a la izquierda del botón del panel, boca hacia la izquierda sobre una zona libre
    "J402": (12.0, 40.8, 270),
    # Canto inferior, boca hacia abajo: microSD, carrier GNSS, NTC (opcional) y batería
    "J401": (9.26, 54.4, 0), "J301": (24.57, 60.6, 0), "J404": (33.89, 60.8, 0), "J102": (40.59, 59.0, 0),
    # ---- entrada USB: ESD de D+/D- en el camino al ESP32 y TVS de VBUS junto al 22 uF de entrada
    "U101": (23.4, 16.1, 90), "D101": (33.0, 12.8, 0),
    "TP206": (17.6, 9.0, 0), "TP207": (17.6, 13.4, 0),
    # ---- alrededor del cargador (U102 en 30.5, 22.4; VBUS arriba, BAT abajo, I2C a la izquierda)
    "C103": (28.6, 18.4, 90),                       # REGN
    "R101": (27.6, 26.6, 90), "R102": (26.5, 26.6, 90),   # ILIM
    "R104": (25.4, 26.6, 90), "R105": (24.2, 26.8, 90),   # TS
    # 10k fijo de TS y su puente (cortar para usar NTC) junto a J404
    "R106": (32.1, 56.8, 0), "JP101": (34.9, 56.8, 0),
    "R103": (30.9, 30.0, 270),                      # PROG (1S 4.7k; 2S 8.2k), bajo su pin
    "R107": (29.3, 30.0, 90),                       # BATP, bajo su pin
    "R108": (21.0, 37.4, 90),                       # INT pull-up, bajo el ESP32
    "Q101": (36.3, 29.2, 0),                        # FET de apagado (ship)
    # ---- 3.3 V: TPS62903 (bloque de v0.1 compactado); C111 es un 10 uF más de VSYS
    "U105": (33.0, 32.6, 0), "L102": (33.0, 35.6, 0), "C115": (29.8, 33.0, 90), "C116": (34.7, 32.2, 90),
    "R116": (36.4, 31.6, 0), "R117": (36.4, 32.9, 0), "R118": (36.4, 34.2, 0), "R119": (36.4, 35.5, 0),
    "C117": (38.4, 33.6, 90), "C118": (40.2, 33.8, 90), "C119": (42.2, 33.8, 90), "C120": (33.6, 38.2, 0),
    "C111": (41.2, 29.4, 0),
    # ---- medidor y protección de polaridad junto a la batería
    "U103": (32.4, 49.4, 0), "R113": (32.4, 51.35, 0), "C114": (34.4, 51.35, 0), "R115": (32.4, 52.6, 0),
    "R114": (34.6, 49.4, 90),
    "Q102": (39.6, 48.3, 0), "Q103": (39.6, 51.8, 0), "R110": (42.4, 48.6, 90), "R111": (36.8, 51.8, 90),
    "R112": (42.4, 51.8, 90),
    # ---- GNSS: ESD y resistencias serie sobre J301
    "U302": (22.2, 54.6, 0), "U303": (26.6, 54.6, 0),
    "R304": (20.0, 50.8, 90), "R305": (21.2, 50.8, 90), "R306": (22.4, 50.8, 90), "R307": (23.6, 50.8, 90),
    "R308": (24.8, 50.8, 90), "R309": (26.0, 50.8, 90), "TP301": (28.4, 51.0, 0),
    # ---- ESP32: reset y arranque arriba a la izquierda (lejos del botón y de los conectores), desacoplo
    # bajo el pin de 3V3, pull-ups y puntos de prueba
    "SW201": (5.6, 9.2, 0), "SW202": (5.6, 13.4, 0), "R202": (15.6, 11.8, 90),
    "R201": (8.0, 16.2, 90), "C203": (9.2, 16.2, 90),
    "C201": (9.5, 34.8, 0), "C202": (6.0, 34.4, 0), "R203": (13.2, 34.6, 90),
    # Pull-ups del bus I2C junto a la OLED (en el canal entre el ESP32 y el cargador el plano de 3V3
    # queda partido por las vías)
    "R204": (32.7, 11.3, 180), "R205": (32.7, 10.2, 180),
    # Pull-ups bajo el ESP32, en la franja sobre el botón (bajas; el plano de 3V3 está entero ahí)
    "R414": (18.6, 37.4, 90), "R415": (19.8, 37.4, 90),
    "TP201": (3.6, 16.1, 0), "TP202": (5.8, 16.1, 0), "TP203": (22.6, 29.8, 0),
    "TP204": (14.8, 16.3, 0), "TP205": (12.4, 16.3, 0),
    # ---- panel: resistencias de los LEDs y de la luz de carga bajo su conector; anillo del botón (Q402)
    # junto al ESP32; ESD y aislamiento del botón junto a J402
    "R109": (32.3, 8.6, 90), "R411": (33.5, 8.6, 90), "R410": (34.7, 8.6, 90), "R409": (35.9, 8.6, 90),
    "Q402": (23.0, 19.6, 0), "R413": (24.7, 19.6, 0),
    "D402": (15.8, 38.6, 90), "D401": (15.6, 41.6, 0), "R408": (16.2, 42.5, 0), "R412": (16.2, 43.5, 0),
    # ---- microSD: pull-ups, inversor de la detección y desacoplo, entre J402 y el zócalo
    "R401": (3.07, 46.4, 90), "R402": (4.2, 46.4, 90), "R403": (5.33, 46.4, 90), "C402": (6.46, 46.4, 90),
    "C401": (8.82, 46.3, 0), "R404": (11.18, 46.4, 90), "R405": (12.31, 46.4, 90), "R406": (13.44, 46.4, 90),
    "R407": (16.0, 47.9, 0), "Q401": (16.2, 45.7, 0),
}
TRACKS = []
VIAS = []

# VBUS ancho de J101 al cargador (en 2S pide ~2.2 A de entrada): barra bajo los tres pines de VBUS,
# bajada de 1 mm bajo el cuerpo de J403 (entre sus pads de anclaje y los de señal) y tramo de 0.8 mm
# entre la TVS (D101) y el 22 uF de entrada (C104), donde arranca el abanico del cargador.
TRACKS += [
    ("VBUS", "F.Cu", 0.8, [(24.6, 6.0), (27.65, 6.0)]),
    ("VBUS", "F.Cu", 1.0, [(27.65, 6.0), (27.65, 13.2)]),
    ("VBUS", "F.Cu", 0.8, [(27.65, 13.2), (28.45, 14.0), (32.15, 14.0)]),
    ("VBUS", "F.Cu", 0.8, [(31.37, 14.0), (31.37, 13.0)]),
    ("VBUS", "F.Cu", 0.8, [(32.15, 14.0), (32.15, 15.0)]),
]
# Cargador: las GND de la columna izquierda (pines 10, 11 y 13) quedan cercadas por las salidas de VBUS,
# BTN_N e I2C; cada grupo lleva su vía al plano de GND.
TRACKS += [
    ("GND", "F.Cu", 0.2, [(28.45, 21.4), (28.45, 21.8)]),
    ("GND", "F.Cu", 0.25, [(28.45, 21.6), (27.75, 21.6)]),
    ("GND", "F.Cu", 0.2, [(28.4, 22.6), (26.6, 22.6)]),
]
VIAS += [("GND", 27.75, 21.6), ("GND", 26.6, 22.6)]
# Medidor: CELL y VDD bajan directo a R113 (VPACK -> FG_VDD); VDD sigue a C114 y baja a R115, que va justo
# debajo de R113 para dejar libre la línea de serigrafía de JP101
TRACKS += [
    ("VPACK", "F.Cu", 0.2, [(32.15, 50.4), (32.15, 51.2)]),
    ("FG_VDD", "F.Cu", 0.2, [(32.65, 50.4), (32.65, 51.2)]),
    ("FG_VDD", "F.Cu", 0.25, [(32.88, 51.35), (33.92, 51.35)]),
    ("FG_VDD", "F.Cu", 0.25, [(32.91, 51.35), (32.91, 52.6)]),
]

for _org, _rot, _parts, _tracks, _vias in ((CHG_ORIGIN, CHG_ROT, CHG_PARTS, CHG_TRACKS, CHG_VIAS),
                                           (G5_ORIGIN, 0, G5_PARTS, G5_TRACKS, G5_VIAS)):
    _p, _t, _v = block(_org, _rot, _parts, _tracks, _vias)
    PLACE.update(_p)
    TRACKS += _t
    VIAS += _v

# Textos: (texto, capa, u, v, tamaño, ángulo). Cada conector lleva su función junto a él; la cara
# trasera (sin componentes) lleva el logotipo, el sitio y las notas de variante.
TEXTS = [
    ("IMU J405", "F.SilkS", 10.0, 6.9, 0.8, 0),
    ("USB J101", "F.SilkS", 22.7, 6.9, 0.8, 0),
    ("LED J406", "F.SilkS", 33.6, 7.0, 0.8, 0),
    ("OLED", "F.SilkS", 21.8, 10.3, 0.8, 0),
    ("J403", "F.SilkS", 21.8, 11.7, 0.8, 0),
    ("BTN", "F.SilkS", 6.0, 40.1, 0.8, 0),
    ("J402", "F.SilkS", 6.0, 41.5, 0.8, 0),
    ("GNSS J301", "F.SilkS", 24.57, 57.0, 0.8, 0),
    ("cortar JP101", "F.SilkS", 33.6, 53.75, 0.8, 0),
    ("NTC J404", "F.SilkS", 33.6, 54.95, 0.8, 0),
    ("BAT", "F.SilkS", 44.2, 54.0, 0.8, 0),
    ("J102", "F.SilkS", 44.2, 55.0, 0.8, 0),
    ("-", "F.SilkS", 38.2, 56.4, 1.0, 0),
    ("+", "F.SilkS", 42.8, 56.4, 1.0, 0),
    ("v0.2", "F.SilkS", 23.0, 48.4, 0.8, 0),
    ("www.tresvizo.com", "B.SilkS", 23.0, 31.0, 1.6, 0),
    ("TresVizo MeridianV - placa principal v0.2", "B.SilkS", 23.0, 35.0, 1.0, 0),
    ("2026-10 - 4 capas JLC04161H-7628", "B.SilkS", 23.0, 36.8, 0.8, 0),
    ("1S: R103=4.7k R117=10k U103=MAX17048", "B.SilkS", 23.0, 40.0, 0.8, 0),
    ("2S: R103=8.2k R117=3.9k U103=MAX17049 R113 NC R115 0R", "B.SilkS", 23.0, 41.6, 0.8, 0),
]

# Logotipo (scripts/logo.py, de los archivos del repositorio): completo atrás y el distintivo al frente,
# en el hueco frente al botón del panel (allí no hay componentes, solo pistas).
LOGOS = [
    {"kind": "full", "layer": "B.SilkS", "width": 30.0, "center": (23.0, 21.5)},
    {"kind": "badge", "layer": "F.SilkS", "width": 7.0, "center": (23.0, 43.0)},
]

# ------------------------------------------------------------- clavijas enchufadas
# Conectores de cable de entrada lateral: familia, pines y borde de la boca en coordenadas de la huella
# (+y local: borde exterior de los pads de anclaje o del patio, el mayor). Cada uno apunta a un canto o a
# una zona libre: delante de la boca se reserva, sin componentes, lo que asoma la clavija enchufada y el
# doblez de sus cables, con 1 mm a cada lado para tomarla (DRC: áreas «clavija_*»; CAD: kicad/plugs.json).
SIDE_ENTRY = {"J101": ("GH", 8, 3.10), "J301": ("GH", 8, 3.10), "J402": ("GH", 4, 2.95), "J405": ("GH", 7, 3.00),
              "J403": ("SH", 4, 2.84), "J404": ("SH", 2, 2.84), "J406": ("SH", 5, 2.84), "J102": ("PH", 2, 4.63)}
# JST: GH enchufado asoma 7.15 - 4.05 = 3.1 mm de la boca y mide 4.35 de alto (eGH, «Assembly layout»);
# carcasa GHR de (n-1)·1.25 + 2.5 de ancho. SH: carcasa SHR de 5.0 de largo, (n-1) + 2.0 de ancho y 2.8 de
# alto (eSH); se toma 3.0 de asomo. PH: PHR de (n-1)·2.0 + 3.9 de ancho y 4.5 de alto; 3.5 de asomo
# (estimado, como en la placa panel-usb). Reserva para doblar los cables: 3 mm (GH, SH) y 4 mm (PH).
PLUG = {"GH": {"out": 3.1, "wires": 3.0, "h": 4.35, "pitch": 1.25, "extra": 2.5},
        "SH": {"out": 3.0, "wires": 3.0, "h": 2.95, "pitch": 1.0, "extra": 2.0},
        "PH": {"out": 3.5, "wires": 4.0, "h": 4.5, "pitch": 2.0, "extra": 3.9}}
GRIP = 1.0


def plug_boxes(ref, place=None):
    """Clavija enchufada de `ref`: polígonos (u, v) de la clavija, del doblez de los cables y de la zona sin
    componentes (las dos más 1 mm a cada lado), y su alto sobre la cara de componentes."""
    fam, n, mouth = SIDE_ENTRY[ref]
    p = PLUG[fam]
    w = (n - 1) * p["pitch"] + p["extra"]
    u0, v0, rot = (place or PLACE)[ref]

    def poly(x0, x1, y0, y1):
        return [(round(u0 + rot_pt(x, y, rot)[0], 3), round(v0 + rot_pt(x, y, rot)[1], 3))
                for x, y in ((x0, y0), (x1, y0), (x1, y1), (x0, y1))]
    end = mouth + p["out"] + p["wires"]
    return {"family": fam, "pins": n, "h": p["h"], "width": w,
            "plug": poly(-w / 2, w / 2, mouth, mouth + p["out"]),
            "wires": poly(-w / 2, w / 2, mouth + p["out"], end),
            "zone": poly(-w / 2 - GRIP, w / 2 + GRIP, mouth, end)}


# Zonas de potencia en la capa superior (prioridad sobre el relleno de GND), en coordenadas del bloque
CHG_POWER_ZONES = [
    ("PMID", [(-1.25, -2.6), (-2.9, -2.6), (-2.9, -6.6), (-1.75, -6.6), (-1.75, -3.3), (-1.25, -3.3)]),
    ("VSYS", [(1.25, -2.45), (2.9, -2.45), (2.9, -6.6), (3.1, -6.6), (3.1, -8.6), (4.1, -8.6), (4.1, -6.95),
              (1.75, -6.95), (1.75, -3.6), (1.25, -3.6)]),
]
POWER_ZONES = [(n, [rot_pt(x, y, CHG_ROT) for x, y in poly]) for n, poly in CHG_POWER_ZONES]
POWER_ZONES = [(n, [(CHG_ORIGIN[0] + x, CHG_ORIGIN[1] + y) for x, y in poly]) for n, poly in POWER_ZONES]


def to_abs(u, v):
    return (round(OX + u, 4), round(OY + v, 4))


def rect(u1, v1, u2, v2):
    return [to_abs(u1, v1), to_abs(u2, v1), to_abs(u2, v2), to_abs(u1, v2)]


def circle_poly(u, v, r, n=24):
    return [to_abs(u + r * math.cos(2 * math.pi * k / n), v + r * math.sin(2 * math.pi * k / n)) for k in range(n)]


def outline():
    c = 1.0  # chaflanes de 1 x 1 para entrar en los rieles
    pts = [(c, 0), (W - c, 0), (W, c), (W, H - c), (W - c, H), (c, H), (0, H - c), (0, c)]
    return [to_abs(u, v) for u, v in pts]


# Clases de red: las usan la placa (board.json) y el archivo de proyecto (circuit.py)
NETCLASSES = {
    "Default": {"track": 0.2, "clearance": 0.15, "via_dia": 0.6, "via_drill": 0.3, "nets": []},
    "Power": {"track": 0.4, "clearance": 0.15, "via_dia": 0.8, "via_drill": 0.4, "priority": 1,
              "nets": ["VBUS", "VSYS", "PMID", "VBAT_CHG", "VPACK", "VBATT_IN", "BUCK_SW", "GNSS_5V",
                       "GNSS_L1", "GNSS_L2"]},
    # Nodos de conmutación del cargador: su camino de potencia está prerruteado; lo que rutea el script
    # son ramas cortas (bootstrap), solo por capas externas.
    "Switch": {"track": 0.25, "clearance": 0.15, "via_dia": 0.6, "via_drill": 0.3, "priority": 1,
               "nets": ["CHG_SW1", "CHG_SW2", "CHG_BTST1", "CHG_BTST2"]},
    "USB": {"track": 0.25, "clearance": 0.15, "via_dia": 0.6, "via_drill": 0.3, "priority": 2,
            "nets": ["USB_DP", "USB_DN"]},
}

# Panel para el pedido (panelize.py): placa principal y placa del USB-C del panel, con rieles de 5 mm
PANEL = {
    "boards": [
        {"name": "main", "file": "tresvizo-main.kicad_pcb", "at": [107.0, 107.0]},
        {"name": "usb", "file": "../../panel-usb/kicad/tresvizo-panel-usb.kicad_pcb", "at": [155.0, 107.0],
         "net_prefix": "PUSB/"},
    ],
    "gap": 2.0,
    "rails": [5.0, 5.0, 5.0, 5.0],
    # Puentes con mouse bites. Arriba y abajo de la placa principal no hay sitio (conectores en los dos
    # cantos): dos puentes en cada canto lateral, sin cobre a 1 mm. Los de v 10.5 y 15.11 caen en la zona
    # de los rieles: lijar la rebaba. El de la derecha a v 15.11 une la principal con la panel-usb, cuyos
    # puentes van a esa misma altura: v 16.0 de esa placa, 15.11 por debajo del canto de su lengüeta (sin
    # cobre en v 13-19 de esa placa).
    "tabs": [
        {"board": "main", "edge": "left", "offset": 10.5, "width": 5.0},
        {"board": "main", "edge": "left", "offset": 54.5, "width": 5.0},
        {"board": "main", "edge": "right", "offset": 15.11, "width": 5.0},
        {"board": "main", "edge": "right", "offset": 52.0, "width": 5.0},
        {"board": "usb", "edge": "left", "offset": 15.11, "width": 5.0},
        {"board": "usb", "edge": "right", "offset": 15.11, "width": 5.0},
    ],
    # El USB-C de la panel-usb sobresale 1.29 mm del canto de su lengüeta (u 5.2-15.6 de esa placa): con
    # la fresa de 2 mm quedaría a 0.71 mm del marco. Frente a la lengüeta la fresa llega a 3 mm (1.71 mm
    # libres) y el marco sube 1 mm para que el riel de arriba siga teniendo 5 mm.
    "cuts": [{"board": "usb", "edge": "top", "offset": 3.2, "width": 14.4, "depth": 3.0}],
    "mousebite": {"drill": 0.6, "pitch": 0.9, "offset": 0.0},
    "keepout": 1.0,
    "marks": {"tooling_drill": 2.0, "tooling_inset": [2.5, 2.5], "fiducial_inset": [6.0, 2.5]},
    "texts": [{"text": "JLCJLCJLCJLC", "layer": "B.SilkS", "at": [140.0, 175.5], "size": 1.0}],
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
            placement[p.ref] = {"x": x, "y": y, "rot": rot, "side": "F", "show_ref": p.ref[0] in "UJL"}
        else:
            x, y = to_abs(staging_u, staging_v)
            placement[p.ref] = {"x": x, "y": y, "rot": 0, "side": "F"}
            staging_v += 3.0
            if staging_v > 90:
                staging_v = 0.0
                staging_u += 6.0
    zones = [{"net": n, "layer": "F.Cu", "priority": 2, "name": n + "_pour", "polygon": [to_abs(u, v) for u, v in poly],
              "clearance": 0.2, "solid_pads": True} for n, poly in POWER_ZONES]
    # Bajo la etapa de potencia del cargador, la capa interna 3 es GND (no +3V3): las pistas de SW1/SW2
    # por B.Cu quedan entre dos planos de GND.
    chg_box = [(-8.0, -13.4), (8.0, -13.4), (8.0, 3.0), (-8.0, 3.0)]
    chg_box = [rot_pt(x, y, CHG_ROT) for x, y in chg_box]
    chg_box = [to_abs(CHG_ORIGIN[0] + x, CHG_ORIGIN[1] + y) for x, y in chg_box]
    # Planos internos con 0.12 mm de margen (JLC admite 0.09 en capas internas): con más, las vías dejan
    # tiras y cuellos finos en el plano de 3V3
    zones += [
        {"net": "GND", "layer": "In1.Cu", "priority": 0, "name": "GND_L2", "clearance": 0.12},
        {"net": "+3V3", "layer": "In2.Cu", "priority": 0, "name": "3V3_L3", "clearance": 0.12},
        {"net": "GND", "layer": "In2.Cu", "priority": 1, "name": "GND_L3_cargador", "polygon": chg_box,
         "clearance": 0.12},
        {"net": "GND", "layer": "F.Cu", "priority": 0, "name": "GND_TOP", "post": True},
        {"net": "GND", "layer": "B.Cu", "priority": 0, "name": "GND_BOT", "post": True},
    ]
    keepouts = []
    for name, u, v in HOLES:
        keepouts.append({"rule_area": True, "name": "hole_" + name, "polygon": circle_poly(u, v, HOLE_FREE_R),
                         "layers": ["F.Cu", "In1.Cu", "In2.Cu", "B.Cu"], "no_tracks": True, "no_vias": True,
                         "no_pour": True})
    # Antena del ESP32-S3-MINI-1 en el canto izquierdo: sin cobre en ninguna capa (guía de Espressif)
    keepouts.append({"rule_area": True, "name": "esp32_antena", "polygon": rect(0.0, 17.3, 6.2, 33.3),
                     "layers": ["F.Cu", "In1.Cu", "In2.Cu", "B.Cu"], "no_tracks": True, "no_vias": True,
                     "no_pour": True})
    # Frente al botón del panel no caben componentes (sus terminales con cables quedan a 2.5 mm de la
    # cara de componentes): solo pistas.
    keepouts.append({"rule_area": True, "name": "boton", "polygon": rect(*BUTTON_KEEPOUT),
                     "layers": ["F.Cu"], "no_tracks": False, "no_vias": False, "no_pour": False,
                     "no_footprints": True})
    # Franjas de los rieles (sin componentes); la izquierda se corta frente a la antena
    strips = [(0.0, 0.0, RAIL_FREE, RAIL_CUT[0]), (0.0, RAIL_CUT[1], RAIL_FREE, RAIL_V_END),
              (W - RAIL_FREE, 0.0, W, RAIL_V_END)]
    for k, (u1, v1, u2, v2) in enumerate(strips):
        keepouts.append({"rule_area": True, "name": "riel_%d" % (k + 1), "polygon": rect(u1, v1, u2, v2),
                         "layers": ["F.Cu"], "no_tracks": False, "no_vias": False, "no_pour": False,
                         "no_footprints": True})
    # Clavijas enchufadas y el doblez de sus cables: sin componentes delante de cada conector lateral
    plugs = {}
    for ref in sorted(SIDE_ENTRY):
        b = plug_boxes(ref, place)
        plugs[ref] = b
        keepouts.append({"rule_area": True, "name": "clavija_" + ref, "polygon": [to_abs(u, v) for u, v in b["zone"]],
                         "layers": ["F.Cu"], "no_tracks": False, "no_vias": False, "no_pour": False,
                         "no_footprints": True})
    import logo
    graphics, logo_boxes = [], []
    for lg in LOGOS:
        polys, w, h = (logo.full_logo if lg["kind"] == "full" else logo.badge)(
            lg["width"], lg["center"], mirror=lg["layer"].startswith("B."))
        graphics += [{"layer": lg["layer"], "outline": [to_abs(u, v) for u, v in o],
                      "holes": [[to_abs(u, v) for u, v in hh] for hh in hs]} for o, hs in polys]
        cu, cv = lg["center"]
        logo_boxes.append(rect(cu - w / 2 - 0.4, cv - h / 2 - 0.4, cu + w / 2 + 0.4, cv + h / 2 + 0.4))
    spec = {
        "libs": {"tresvizo_lcsc": "lib/lcsc.pretty"},
        "board": {"layers": 4, "thickness": 1.6, "outline": {"type": "polygon", "points": outline()},
                  "holes": [{"ref": n, "x": to_abs(u, v)[0], "y": to_abs(u, v)[1],
                             "footprint": "MountingHole_2.7mm"} for n, u, v in HOLES]},
        "rules": {"min_clearance": 0.127, "min_track": 0.127, "min_via_dia": 0.5, "min_drill": 0.3,
                  "min_annular": 0.1, "hole_to_hole": 0.5, "edge_clearance": 0.3, "hole_clearance": 0.25,
                  "min_resolved_spokes": 1},
        "netclasses": NETCLASSES,
        # El BQ25798 (RQM0029A) no tiene modelo 3D en KiCad 10: se usa un VQFN de 4 x 4 x 1 mm
        "model_substitutes": {
            "Texas_RQM0029A_VQFN-29_4x4mm_P0.4mm.step":
                "${KICAD10_3DMODEL_DIR}/Package_DFN_QFN.3dshapes/Texas_RGE0024C_VQFN-24-1EP_4x4mm_P0.5mm_EP2.1x2.1mm.step"},
        "placement": placement,
        "fanout": {"nets": ["GND", "+3V3"], "skip_refs": ["U201"]},
        "stitching": {"pitch": 3.0, "dia": 0.6, "drill": 0.3, "clearance": 0.25, "edge": 0.8,
                      "no_vias_under": ["U201", "J401", "U102", "U105", "U301"], "avoid_polys": logo_boxes},
        "zones": zones + keepouts,
        "tracks": [{"net": n, "layer": l, "width": w, "points": [to_abs(u, v) for u, v in pts]}
                   for n, l, w, pts in TRACKS],
        "vias": [{"net": n, "x": to_abs(u, v)[0], "y": to_abs(u, v)[1]} for n, u, v in VIAS],
        "texts": [{"text": t, "layer": l, "x": to_abs(u, v)[0], "y": to_abs(u, v)[1], "size": sz, "angle": a}
                  for t, l, u, v, sz, a in TEXTS],
        "graphics": graphics,
    }
    with open(os.path.join(kicad_dir, "board.json"), "w", encoding="utf-8") as f:
        json.dump(spec, f, indent=1)
    # Para la comprobación en CAD: clavijas y agujeros en coordenadas de placa y su paso a la carcasa
    with open(os.path.join(kicad_dir, "plugs.json"), "w", encoding="utf-8") as f:
        json.dump({"note": "Coordenadas de placa (u, v) en mm; carcasa V2.2: x = 23 - u, z = z_top - v, "
                           "cara de componentes en y = y_face (las clavijas van de y_face a y_face + h).",
                   "z_top": Z_TOP, "y_face": 3.1, "y_back": 1.5, "size": [W, H],
                   "holes": [{"ref": n, "u": u, "v": v, "d": 2.7} for n, u, v in HOLES],
                   "plugs": [dict(ref=r, **b) for r, b in sorted(plugs.items())]}, f, indent=1)
    with open(os.path.join(kicad_dir, "panel.json"), "w", encoding="utf-8") as f:
        json.dump(PANEL, f, indent=1)
