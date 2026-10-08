"""Geometría de la placa principal v0.3 («compacta») y colocación de componentes (escribe kicad/board.json,
kicad/plugs.json y kicad/panel.json).

Coordenadas locales (u, v) en mm, vista desde la cara de componentes (la que mira a la cara plana del tubo):
u hacia la derecha, v hacia abajo, origen en la esquina superior izquierda. Posición en la carcasa v0.3
(research/v03-compacta.md): tubo de Ø52 con cara plana, placa en el plano y 13.8-15.4 con la cara de
componentes hacia el frente (+Y); u = 18 - x y v = 80 - z (x del equipo a la izquierda mirando el frente,
z hacia la antena). Detrás de la placa van la carrier BDLX y las dos 18650.

Todo cabe bajo el techo del tubo: alto máximo sobre la cara h(x) = min(4.63, sqrt(24.2² - x²) - 15.7), con
x = 18 - u en el |x| más grande de cada pieza (cad/check_heights.py lo comprueba sobre el STEP).
"""

import json
import math
import os

OX, OY = 100.0, 100.0  # origen de la placa en la hoja de KiCad
W, H = 36.0, 71.5
Z_TOP = 80.0            # z del canto superior en la carcasa: v = Z_TOP - z
X_U0 = 18.0             # x del canto u = 0: x = X_U0 - u
Y_BACK, Y_FACE = 13.8, 15.4   # dorso y cara de componentes en la carcasa (research/v03-compacta.md, pila)
CHAMFER = 0.5           # chaflanes de las esquinas
# Muesca del USB-C: la funda de la clavija (12.35 x 6.5 como máximo, centrada en el eje del conector) llega
# hasta el dorso de la placa; la placa se recorta frente a la boca (u 0-3.1, z 25 ± 6.5). La cara del conector
# queda en u 3.1 (x 14.9), 0.1 mm más adentro que en la especificación: con la cara en x 15.0, la caja del modelo
# STEP del conector (3.30 sobre la cara) quedaba 0.01 mm por encima del techo del tubo en cad/check_heights.py.
NOTCH = (0.0, 48.5, 3.1, 61.5)
# Muesca del canto de arriba para la clavija SMA de la carrier (revisión de la carcasa): el eje del jack está en
# x -1.2, y 10.2, con el cañón hasta z 79.5; la tuerca de la clavija (5/16", hasta ~9.2 mm entre vértices) llega a
# y 14.2-14.8, detrás del dorso (y 13.8), así que entra en la placa en x -6.2...+3.8, z 73.5-80. Abierta al canto
# de arriba, bajo la OLED (allí solo hay pistas), entre sus agujeros y por encima de su fila de pines; esquinas
# interiores con el radio de la fresa. Nada se rutea por ella (queda fuera de la placa).
SMA_NOTCH = (14.2, 0.0, 24.2, 6.5)
SMA_NOTCH_R = 1.0
EDGE_STRIP = 1.0        # franja sin componentes en los cantos laterales (ranuras o labios de la pared)
# Agujeros sin metalizar de Ø2.2 de la OLED (en su huella): M2 con tuerca por detrás; sin cobre en r 2.6
OLED_HOLE_FREE_R = 2.6
# Pulsador del equipo bajo la tecla de la cara plana: a menos de 5 mm de su centro solo piezas de 1 mm o menos
BUTTON_CENTER, BUTTON_LOW_R, BUTTON_LOW_H = (18.0, 58.0), 5.0, 1.0
# Guía de luz de Ø2 que baja sobre el LED de estado (D403): a menos de 1.5 mm de su centro no puede haber otra pieza
LIGHT_PIPE_R = 1.5


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
    # Piezas que terminan el abanico prerruteado de la fila de la derecha (PROG, BATP, SDRV) y REGN, en la misma
    # posición relativa que tenían en v0.2
    "R103": (7.6, -0.4, 0), "R107": (7.6, 1.2, 180), "Q101": (6.8, -5.8, 90), "C103": (-4.0, 1.9, 180),
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
    ("CHG_ILIM", "F.Cu", 0.2, [(2.2, 1.2), (2.45, 1.2), (2.85, 1.6)]),
    ("CHG_BATP", "F.Cu", 0.2, [(2.2, 0.8), (2.85, 0.8), (3.25, 1.2), (7.09, 1.2)]),
    ("CHG_BTST2", "F.Cu", 0.2, [(2.2, 0.4), (3.77, 0.4)]),
    ("CHG_SW2", "F.Cu", 0.4, [(5.775, 0.4), (6.7, 0.4)]),
    ("CHG_SW2", "B.Cu", 0.4, [(6.7, 0.4), (1.0, 0.4)]),
    ("CHG_PROG", "F.Cu", 0.2, [(2.2, 0.0), (2.85, 0.0), (3.25, -0.4), (7.12, -0.4)]),
    ("CHG_INT_N", "F.Cu", 0.2, [(2.2, -0.4), (2.45, -0.4), (2.85, -0.8), (4.6, -0.8), (5.0, -1.2)]),
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
    # Las GND de la fila de abajo (pines 10, 11 y 13) quedan cercadas por las salidas de VBUS, BTN_N e I2C: la de
    # los pines 10 y 11 baja a su vía (como en v0.2) y el 13 rodea por debajo a BTN_N hasta la misma vía
    ("GND", "F.Cu", 0.2, [(-1.0, 2.05), (-0.6, 2.05)]),
    ("GND", "F.Cu", 0.25, [(-0.8, 2.05), (-0.8, 2.75)]),
    ("GND", "F.Cu", 0.2, [(0.2, 2.1), (0.2, 2.55), (-0.2, 2.95), (-0.6, 2.95), (-0.8, 2.75)]),
    # v0.3: debajo del cargador está el divisor del regulador de 3.3 V; para que salgan juntos SCL, SDA y TS, BTN_N
    # sale hacia dentro, a una vía bajo el chip entre las columnas de vías de SW (la mitad del chip que no tiene pines
    # de potencia), SCL y SDA bajan a dos vías escalonadas y TS baja junto a su divisor (R104/R105, a la derecha)
    ("BTN_N", "F.Cu", 0.2, [(-0.2, 1.9), (-0.2, 0.95), (0.0, 0.75), (0.0, 0.5)]),
    ("I2C_SCL", "F.Cu", 0.2, [(0.6, 1.9), (0.6, 3.55)]),
    ("I2C_SDA", "F.Cu", 0.2, [(1.0, 1.9), (1.0, 2.8), (1.35, 3.15), (1.35, 4.35)]),
    ("CHG_TS", "F.Cu", 0.2, [(1.95, 2.2), (1.95, 2.6), (2.15, 2.8), (2.15, 3.05)]),
]
CHG_VIAS = [("CHG_SW1", -1.0, y) for y in (-0.55, 0.25, 1.1)] + \
    [("CHG_SW2", 1.0, y) for y in (-0.55, 0.25, 1.1)] + [
    ("CHG_SW1", -5.075, 0.45), ("CHG_SW2", 6.7, 0.4),
    ("CHG_SW1", -1.6, -8.4), ("CHG_SW1", -2.5, -8.4), ("CHG_SW2", 1.6, -8.4), ("CHG_SW2", 2.5, -8.4),
    ("GND", 0.0, -4.4), ("GND", 0.0, -5.3), ("GND", 0.0, -6.2),
    ("GND", -0.8, 2.75),
    ("BTN_N", 0.0, 0.5), ("I2C_SCL", 0.6, 3.55), ("I2C_SDA", 1.35, 4.35),
]
CHG_ORIGIN, CHG_ROT = (26.4, 51.4), 0

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
G5_ORIGIN, G5_ROT = (28.27, 33.72), 180   # 0.43 mm más arriba que su primer sitio: la serigrafía de L301 libra la de L101

# ------------------------------------------------------------- 3.3 V: TPS62903
# U105 en (0, 0), según su hoja de datos: SW a L102 por F.Cu sin vías (0.9 mm); C115 (entrada) a la derecha,
# entre VIN y GND, con EN saliendo entre sus pads; C118 y C119 (salida) bajo U105, entre la salida de L102 y
# GND; VOS toma la tensión en C118; FB con su divisor junto al pin. C111 es un 10 uF más de VSYS.
# (Mismas posiciones relativas que en v0.2, donde estaba en coordenadas absolutas.)
BUCK_PARTS = {
    "U105": (0.0, 0.0, 0), "L102": (-2.55, 1.51, 270), "C115": (2.1, 0.34, 270), "C116": (1.85, -2.05, 0),
    "R115": (4.0, -0.7, 270), "R116": (4.0, 1.3, 270), "R117": (-2.7, -2.2, 0), "R118": (-0.7, -2.2, 0),
    "C117": (3.8, 3.85, 270), "C118": (0.3, 3.1, 0), "C119": (0.9, 5.1, 0), "C120": (-4.7, 2.7, 90),
}
BUCK_TRACKS = [
    ("BUCK_SW", "F.Cu", 0.3, [(-0.85, 0.34), (-1.8, 0.34)]),
    ("VSYS", "F.Cu", 0.3, [(0.85, -0.16), (1.7, -0.16)]),
    ("GND", "F.Cu", 0.3, [(0.85, 0.84), (1.7, 0.84)]),
    ("BUCK_EN", "F.Cu", 0.2, [(0.85, 0.34), (4.0, 0.34)]),
    ("BUCK_EN", "F.Cu", 0.2, [(4.0, -0.19), (4.0, 0.79)]),
    ("BUCK_FB", "F.Cu", 0.2, [(-2.19, -2.2), (-1.21, -2.2)]),
    ("BUCK_FB", "F.Cu", 0.2, [(-1.21, -2.2), (-0.5, -1.49), (-0.5, -1.0)]),
    ("+3V3", "F.Cu", 0.2, [(-0.63, 0.9), (-0.65, 2.8)]),
    ("+3V3", "F.Cu", 0.6, [(-1.7, 3.1), (-1.1, 3.1)]),
    ("GND", "F.Cu", 0.4, [(0.7, 0.95), (1.0, 1.25), (1.0, 2.8)]),
    ("+3V3", "F.Cu", 0.6, [(-0.65, 3.4), (-0.05, 4.0), (-0.05, 4.85)]),
    ("GND", "F.Cu", 0.6, [(1.25, 3.4), (1.85, 4.0), (1.85, 4.85)]),
    ("+3V3", "F.Cu", 0.4, [(-4.5, 3.18), (-3.4, 3.18)]),
    # SS y el GND del pin 7: en v0.2 los ruteaba route_rest.py (SS por una vía junto al pin 8 y B.Cu hasta C117; el
    # pin 7 a una vía a su derecha); aquí el cargador queda justo encima y no siempre los encontraba, así que van
    # prerruteados con esas mismas vías
    ("BUCK_SS", "F.Cu", 0.2, [(0.0, -1.0), (0.0, -1.35), (0.15, -1.35), (0.6, -1.8)]),
    ("BUCK_SS", "B.Cu", 0.2, [(0.6, -1.8), (2.85, -1.8), (2.85, 3.0)]),
    ("BUCK_SS", "F.Cu", 0.2, [(2.85, 3.0), (3.5, 3.075)]),
    ("GND", "F.Cu", 0.2, [(0.5, -0.84), (0.6, -1.0), (0.9, -1.0)]),
    # VSYS de C116 a C115 (la vía de SS queda al lado y el fanout podía cerrar el paso)
    ("VSYS", "F.Cu", 0.3, [(1.37, -2.05), (1.37, -1.4), (1.85, -0.92)]),
]
BUCK_VIAS = [("GND", 1.0, 2.0), ("BUCK_SS", 0.6, -1.8), ("BUCK_SS", 2.85, 3.0), ("GND", 0.9, -1.0)]
BUCK_ORIGIN, BUCK_ROT = (30.45, 59.0), 0

# ------------------------------------------------------------- medidor de la batería
# MAX17048 (U103) en (0, 0): CELL y VDD bajan directo a R112 (VPACK -> FG_VDD); VDD sigue a C114 y baja a
# R114, que va justo debajo de R112. (Mismas posiciones relativas que en v0.2.)
FG_PARTS = {"U103": (0.0, 0.0, 0), "R112": (0.0, 1.95, 0), "C114": (2.0, 1.95, 0), "R114": (0.0, 3.2, 0),
            "R113": (2.2, 0.0, 90)}
FG_TRACKS = [
    ("VPACK", "F.Cu", 0.2, [(-0.25, 1.0), (-0.25, 1.8)]),
    ("FG_VDD", "F.Cu", 0.2, [(0.25, 1.0), (0.25, 1.8)]),
    ("FG_VDD", "F.Cu", 0.25, [(0.48, 1.95), (1.52, 1.95)]),
    ("FG_VDD", "F.Cu", 0.25, [(0.51, 1.95), (0.51, 3.2)]),
]
FG_ORIGIN, FG_ROT = (18.4, 61.9), 0

# ------------------------------------------------------------------ USB-C (J101)
# Mismo receptáculo y mismas pistas junto a sus pads que en la placa panel-usb (../../panel-usb/scripts/layout.py),
# en coordenadas de la huella de J101: cruce de D+ (U alrededor de la vía de A7) y D- (por B.Cu), CC1 y CC2 a sus Rd,
# GND de los pads a las patas de la carcasa y VBUS a dos vías por cada pad. J101 va girado 270: boca hacia +X.
USBC_PARTS = {"J101": (0.0, 0.0, 0), "R119": (-3.6, -5.08, 180), "R120": (3.6, -5.08, 0)}
USBC_TRACKS = [
    ("USB_DP", "F.Cu", 0.2, [(0.75, -3.12), (0.75, -3.33), (0.95, -3.53), (0.95, -4.68), (-0.45, -4.68),
                             (-0.45, -3.53), (-0.25, -3.33), (-0.25, -3.12)]),
    ("USB_DN", "F.Cu", 0.2, [(0.25, -3.12), (0.25, -4.03)]),
    ("USB_DN", "F.Cu", 0.2, [(-0.75, -3.12), (-0.75, -3.23), (-1.05, -3.53), (-1.05, -4.08)]),
    ("USB_DN", "B.Cu", 0.25, [(0.25, -4.03), (-1.05, -4.08)]),
    ("USB_DN", "B.Cu", 0.25, [(0.25, -4.03), (0.25, -5.33)]),
    ("CC1", "F.Cu", 0.2, [(-1.25, -3.12), (-1.65, -3.63), (-1.65, -5.08), (-3.09, -5.08)]),
    ("CC2", "F.Cu", 0.2, [(1.75, -3.12), (1.75, -5.08), (3.09, -5.08)]),
    ("GND", "F.Cu", 0.3, [(4.11, -5.08), (4.2, -2.63)]),
    ("GND", "F.Cu", 0.4, [(3.2, -2.47), (4.33, -1.93)]),
    ("GND", "F.Cu", 0.4, [(-3.2, -2.47), (-4.33, -1.93)]),
    ("VBUS", "F.Cu", 0.6, [(2.4, -3.12), (2.4, -4.48)]),
    ("VBUS", "F.Cu", 0.6, [(-2.4, -3.12), (-2.4, -4.48)]),
]
USBC_VIAS = [("USB_DN", 0.25, -4.03), ("USB_DN", -1.05, -4.08), ("USB_DN", 0.25, -5.33),
             ("VBUS", 2.4, -3.58), ("VBUS", 2.4, -4.48), ("VBUS", -2.4, -3.58), ("VBUS", -2.4, -4.48)]
USBC_ORIGIN, USBC_ROT = (8.17, 55.0), 270

# ---------------------------------------------------------------- resto de la placa
# ESD del lado de la carrier, uno encima del otro en el rincón (3.23 mm entre centros: sus contornos no se tocan)
U302_V, U303_V = 66.55, 69.78
PLACE = {
    # ESP32-S3-WROOM-1 horizontal con la antena hacia el canto derecho (-X), lejos del SMA y del coaxial de la
    # carrier. Huella de LCSC con el origen a 3.6 mm del centro hacia los pines; girada 270: cuerpo en
    # u 7.65-33.15, v 12.1-30.1 (antena en u 26.65-33.15). Con 3.11 mm de alto, la caja entera tiene que quedar en
    # |x| <= 15.2 (cad/check_heights.py), así que la punta de la antena queda en u 33.15 (x -15.15).
    "U201": (16.75, 21.1, 270),
    # OLED soldada por sus 4 pines, girada 180° (pines abajo), sobresale por arriba hasta z ≈ 96
    "J403": (18.0, 10.4, 0),
    # microSD con la boca hacia +X (u 1.5); tarjeta centrada en v ≈ 38.4 (z ≈ 41.6)
    "J401": (10.875, 40.0, 270),
    # Botón bajo la tecla y LED de estado bajo su ventanita
    "SW401": (18.0, 58.0, 0), "D403": (24.0, 58.0, 180),
    # Canto inferior, boca hacia abajo: batería (GH 4), NTC (SH 2) y carrier GNSS (SH 8)
    "J102": (15.9, 68.2, 0), "J404": (9.1, 68.3, 0), "J301": (26.0, 68.2, 0),
    # ---- franja izquierda (entre el canto y la punta izquierda del WROOM): reset, arranque, IO3 y puntos de prueba
    "SW201": (2.95, 16.7, 90), "R201": (5.7, 15.8, 270), "C203": (5.7, 17.8, 90),
    "SW202": (2.95, 28.0, 90), "R202": (5.7, 27.7, 270),
    # IO3 sale del pin 15 directo a R203 (su pad de IO3 a la derecha); R308 (pull-down de EVENT) un poco a la
    # izquierda, para que quepa la vía de EVENT del bus del GNSS entre ella y el pin 19
    "R203": (5.7, 14.1, 180),
    "R308": (5.1, 19.4, 180),
    # ---- bolsillos junto a la OLED: pull-ups del I2C y puntos de prueba (izquierda), desacoplo del WROOM (derecha)
    "R204": (2.5, 2.2, 0), "R205": (2.5, 3.4, 0),
    "TP201": (2.4, 5.1, 0), "TP202": (2.4, 7.2, 0), "TP206": (2.4, 9.3, 0), "TP207": (2.4, 11.4, 0),
    "C201": (33.5, 3.0, 90), "C202": (33.5, 5.7, 0),
    # ---- entre el WROOM y la microSD: puntos de prueba de GPIO35-37 bajo sus pines
    "TP203": (9.3, 31.6, 0), "TP204": (11.3, 31.6, 0), "TP205": (13.3, 31.6, 0),
    # UART0 (U0TXD pin 37, U0RXD pin 36) bajo la fila de abajo del módulo, entre Q401 y el bloque del TPS63070; TP208
    # deja libre a su derecha el paso de GNSS_5V hacia R302 (el divisor del TPS63070)
    "TP208": (23.65, 31.5, 0), "TP209": (21.65, 31.5, 0),
    # ---- microSD: inversor de la detección arriba, pull-ups y desacoplo a la derecha de las vías del bus
    "Q401": (18.75, 32.45, 270),
    "R403": (18.75, 34.62, 180), "R402": (18.75, 35.72, 180), "C402": (18.75, 39.01, 0),
    "R401": (18.75, 40.11, 180), "R405": (18.75, 41.21, 180), "R404": (18.75, 42.30, 180),
    "R406": (21.3, 39.6, 90), "R407": (22.5, 39.6, 90), "C401": (18.9, 44.4, 0),
    # ---- USB: ESD y TVS de VBUS junto al conector
    "U101": (15.35, 51.4, 180), "D101": (12.6, 48.9, 0),
    # ---- botón y LED; el ESD (D401) junto al botón y el diodo hacia GPIO18 (D402) fuera de la zona baja
    "D401": (14.3, 54.9, 90), "D402": (17.6, 48.0, 90), "R408": (2.7, 12.95, 0), "R409": (21.95, 58.0, 90),
    # ---- cargador: ILIM, TS e INT (fuera del bloque); C111 (10 uF más de VSYS) en la subida de VSYS al TPS63070
    # El divisor de TS (R104/R105) junto a la vía de TS del cargador, a la derecha: fuera del círculo de la guía de
    # luz del LED
    "R101": (22.7, 54.55, 0), "R102": (22.7, 55.6, 0), "R104": (29.8, 54.15, 180), "R105": (29.8, 55.45, 0),
    "R108": (34.3, 42.5, 90), "C111": (32.15, 39.3, 0),
    # ---- batería: protección contra celda invertida (Q102, Q103 y su divisor) junto a J102
    "Q102": (11.1, 61.6, 180), "Q103": (7.2, 61.6, 180), "R109": (8.9, 63.5, 180), "R110": (10.9, 64.6, 0),
    "R111": (12.95, 64.6, 0),
    # ---- GNSS: resistencias serie en fila sobre J301 (cada una baja recto a su pin) y ESD en el rincón
    "R304": (24.5, 64.3, 270), "R305": (25.5, 64.3, 90), "R306": (26.5, 64.3, 90), "R307": (27.5, 64.3, 270),
    "R309": (28.5, 64.3, 270),
    "U302": (33.4, U302_V, 270), "U303": (33.4, U303_V, 270), "TP301": (22.4, 62.6, 0),
    # ---- IMU (BMI088) en la esquina de abajo a la izquierda, lejos de L101 y del botón; sus 100 nF debajo y las
    # pull-ups de su I2C encima (SCL a la izquierda, SDA a la derecha, junto a la llegada de cada línea)
    "U401": (4.0, 66.9, 0), "C403": (2.4, 70.3, 0), "C404": (5.4, 70.3, 0), "R411": (7.0, 63.75, 0),
    "R412": (2.0, 62.6, 0),
}
TRACKS = []
VIAS = []

for _org, _rot, _parts, _tracks, _vias in ((CHG_ORIGIN, CHG_ROT, CHG_PARTS, CHG_TRACKS, CHG_VIAS),
                                           (G5_ORIGIN, G5_ROT, G5_PARTS, G5_TRACKS, G5_VIAS),
                                           (BUCK_ORIGIN, BUCK_ROT, BUCK_PARTS, BUCK_TRACKS, BUCK_VIAS),
                                           (FG_ORIGIN, FG_ROT, FG_PARTS, FG_TRACKS, []),
                                           (USBC_ORIGIN, USBC_ROT, USBC_PARTS, USBC_TRACKS, USBC_VIAS)):
    _p, _t, _v = block(_org, _rot, _parts, _tracks, _vias)
    PLACE.update(_p)
    TRACKS += _t
    VIAS += _v


# ------------------------------------------------------------- IMU (columna izquierda)
# El BMI088 no admite pistas ni vías de la cara de arriba bajo el cuerpo, así que cada pad sale hacia fuera. La columna
# izquierda (pines 7-1: +3V3, GND, -, GND, +3V3, GND, -) da al canto: sus GND (6 y 4) se juntan por fuera y bajan a
# una vía, el 2 a otra, y cada +3V3 (7 y 3) a la suya; las cuatro vías en columna a 1.4 mm del canto. La columna
# derecha, el pin 8 (arriba) y el 16 (abajo) tienen sitio: los rutea el script.
IMU_LEFT_TRACKS = [
    ("+3V3", "F.Cu", 0.2, [(-1.2, -1.5), (-2.3, -1.5), (-2.6, -1.8)]),
    ("GND", "F.Cu", 0.2, [(-1.2, -1.0), (-2.0, -1.0), (-2.0, 0.0), (-1.2, 0.0)]),
    ("GND", "F.Cu", 0.2, [(-2.0, -0.5), (-2.6, -0.5)]),
    ("+3V3", "F.Cu", 0.2, [(-1.2, 0.5), (-2.6, 0.5)]),
    ("GND", "F.Cu", 0.2, [(-1.2, 1.0), (-2.1, 1.0), (-2.6, 1.5)]),
]
IMU_LEFT_VIAS = [("+3V3", -2.6, -1.8), ("GND", -2.6, -0.5), ("+3V3", -2.6, 0.5), ("GND", -2.6, 1.5)]
# Columna derecha (pines 9-15: SDA, GND, +3V3, INT3, -, +3V3, GND): SDA e INT3 van con el bus del IMU (más abajo); las
# alimentaciones salen en línea recta a vías escalonadas: el GND del 10 arriba, cerca; los +3V3 (11 y 14) se juntan
# por fuera y bajan a una vía más lejos, al otro lado de la llegada de INT3 por In2; el GND del 15 abajo, cerca, y a
# esa vía va también el GND del 100 nF de abajo a la derecha (C404).
IMU_RIGHT_TRACKS = [
    ("GND", "F.Cu", 0.2, [(1.2, -1.0), (2.3, -1.0), (2.65, -1.15)]),
    ("+3V3", "F.Cu", 0.2, [(1.2, -0.5), (3.6, -0.5), (3.75, -0.35)]),
    ("+3V3", "F.Cu", 0.2, [(1.2, 1.0), (3.75, 1.0), (3.75, -0.35)]),
    ("GND", "F.Cu", 0.2, [(1.2, 1.5), (2.0, 1.5), (2.4, 1.9)]),
    ("GND", "F.Cu", 0.25, [(1.88, 3.4), (2.4, 2.88), (2.4, 1.9)]),
]
IMU_RIGHT_VIAS = [("GND", 2.65, -1.15), ("+3V3", 3.75, -0.35), ("GND", 2.4, 1.9)]
_p, _t, _v = block(PLACE["U401"][:2], PLACE["U401"][2], None, IMU_LEFT_TRACKS + IMU_RIGHT_TRACKS,
                   IMU_LEFT_VIAS + IMU_RIGHT_VIAS)
TRACKS += _t
VIAS += _v

# ------------------------------------------------------------- potencia prerruteada
# VBUS (hasta ~2.2 A en 2S): el pad A4/B9 del USB-C sube por F.Cu (0.6 mm) al cátodo de la TVS (D101), y las dos
# vías de cada pad de VBUS bajan a B.Cu, donde una pista de 0.8 mm junta los dos pads (rodeando el cruce de D-) y
# va al 22 uF de entrada del cargador (C104), que sube por una vía de 0.8/0.4.
_UX = USBC_ORIGIN[0] + 3.58, USBC_ORIGIN[0] + 4.48    # columnas de las vías de VBUS junto a los pads del USB-C
POWER_TRACKS = [
    ("VBUS", "F.Cu", 0.6, [(_UX[0], 52.6), (_UX[0], 49.95), (11.2, 49.35)]),
    ("VBUS", "B.Cu", 0.8, [(_UX[1], 52.6), (17.9, 52.6), (19.4, 51.1)]),
    ("VBUS", "B.Cu", 0.8, [(_UX[1], 57.4), (14.5, 57.4), (14.5, 53.0), (14.1, 52.6)]),
    ("VBUS", "F.Cu", 0.8, [(19.4, 51.1), (19.4, 49.95)]),
]
POWER_TRACKS += [
    ("VBUS", "B.Cu", 0.8, [(_UX[0], 52.6), (_UX[1], 52.6)]),
    ("VBUS", "B.Cu", 0.8, [(_UX[0], 57.4), (_UX[1], 57.4)]),
]
POWER_VIAS = [("VBUS", 19.4, 51.1, 0.8, 0.4)]
# Batería (hasta 2 A): la celda entra por J102 (3-4) y sube por F.Cu (0.8 mm) al drenador de Q102 (protección contra
# inversión); VPACK sale de su fuente por B.Cu (1.0 mm) pegado al canto de abajo (bajo los conectores, que solo tienen
# pads arriba) y por el derecho hasta el FET de apagado (Q101) del cargador, con vías a R112 (medidor) y a R107 (BATP,
# Kelvin del cargador). Así la franja de B.Cu sobre J301 queda libre para el bus del GNSS. El tramo del canto de abajo
# va de 0.8 mm (más cerca del canto, deja sitio a la vía central de U303).
VPACK_V = 70.75
VPACK_U = 34.35   # columna del canto derecho: deja sitio a las vías de U302/U303
POWER_TRACKS += [
    ("VBATT_IN", "F.Cu", 0.6, [(17.77, 66.0), (16.52, 66.0)]),
    ("VBATT_IN", "F.Cu", 0.8, [(16.52, 66.0), (16.52, 65.3), (13.3, 62.1), (12.5, 61.6)]),
    ("VPACK", "F.Cu", 0.6, [(9.95, 62.55), (10.95, 63.25)]),
    ("VPACK", "B.Cu", 1.0, [(10.95, 63.25), (10.95, VPACK_V - 0.4)]),
    ("VPACK", "B.Cu", 0.8, [(10.95, VPACK_V - 0.4), (11.35, VPACK_V), (VPACK_U - 0.4, VPACK_V), (VPACK_U, VPACK_V - 0.4)]),
    # Cada cambio de capa con dos vías de 0.8/0.4 (auditoría del 08-10-2026). Junto a Q102, la segunda a la derecha
    # de la primera; junto a Q101 el canto derecho sube recto hasta la derecha de su drenador (pin 3), entre el pin 1 y
    # C113, con las dos vías ahí (antes bajaba en diagonal bajo C113 hasta una sola vía a la izquierda del pin 3)
    ("VPACK", "F.Cu", 0.6, [(10.95, 63.25), (11.85, 63.45)]),
    ("VPACK", "B.Cu", 1.0, [(10.95, 63.25), (11.85, 63.45)]),
    ("VPACK", "B.Cu", 1.0, [(VPACK_U, VPACK_V - 0.4), (VPACK_U, 46.25)]),
    ("VPACK", "B.Cu", 0.8, [(VPACK_U, 46.25), (35.2, 45.7)]),
    ("VPACK", "F.Cu", 0.8, [(35.2, 45.7), (VPACK_U, 46.25), (33.2, 46.6)]),
    ("VPACK", "B.Cu", 0.3, [(17.0, VPACK_V), (17.0, 63.6)]),
    ("VPACK", "F.Cu", 0.3, [(17.0, 63.6), (17.75, 63.85)]),
    ("VPACK", "F.Cu", 0.3, [(34.48, 53.5), (34.48, 52.6)]),
    # GND de C113 (22 uF de BAT del cargador): la columna de VPACK pasa por debajo, así que su vía va prerruteada
    # hacia el canto (el fanout no le encuentra sitio)
    ("GND", "F.Cu", 0.4, [(34.25, 48.1), (35.35, 48.1)]),
]
POWER_VIAS += [("VPACK", 10.95, 63.25, 0.8, 0.4), ("VPACK", 11.85, 63.45, 0.8, 0.4),
               ("VPACK", VPACK_U, 46.25, 0.8, 0.4), ("VPACK", 35.2, 45.7, 0.8, 0.4),
               ("VPACK", 17.0, 63.6, 0.6, 0.3), ("VPACK", 34.48, 53.5, 0.6, 0.3),
               ("GND", 35.35, 48.1, 0.6, 0.3)]
# GND de la batería (J102.1 y J102.2, hasta 2 A entre los dos): un relleno propio de F.Cu, con los pads unidos sin
# alivios térmicos, que toma los dos pines, el hueco entre ellos y los dos pads de anclaje, y cuatro vías de 0.6/0.3
# (dos por pin): tres bajo el cuerpo del conector, entre la fila de pines y los anclajes, y una entre J102.1 y R111.
# Antes cada pin salía por una pista de 0.25 mm a una sola vía del fanout (J102 queda fuera del fanout).
J102_GND_ZONE = [(11.55, 65.25), (15.85, 65.25), (15.85, 67.7), (20.25, 67.7), (20.25, 71.2), (11.55, 71.2)]
POWER_VIAS += [("GND", 13.25, 65.6, 0.6, 0.3), ("GND", 13.1, 67.95, 0.6, 0.3), ("GND", 14.65, 67.95, 0.6, 0.3),
               ("GND", 15.9, 67.95, 0.6, 0.3)]
# 5 V de la carrier (GNSS_5V, ~160 mA): de los 22 uF de salida del TPS63070 (C307) baja por In2 (0.4 mm, unos 12 mV
# de caída) a lo largo de u 20.5, entre las piezas de la microSD y las del cargador, pasa bajo el botón hasta una vía
# junto al LED y por F.Cu llega al punto de prueba TP301 y a J301.1. Por B.Cu partía en dos el centro de la placa
# (VBUS y VSYS no pueden ir por capas internas en el ruteo automático); si lo ruteaba el script, iba por el hueco del
# USB-C, bajo su cuerpo.
_g5u, _g5v = G5_ORIGIN[0] - 6.95, G5_ORIGIN[1] + 1.65        # pad de GNSS_5V de C307
POWER_TRACKS += [
    ("GNSS_5V", "F.Cu", 0.4, [(_g5u, _g5v), (20.5, _g5v + 0.95)]),
    ("GNSS_5V", "In2.Cu", 0.4, [(20.5, _g5v + 0.95), (20.5, 58.9), (21.0, 59.4), (22.7, 59.4), (23.3, 60.0), (23.3, 60.3)]),
    ("GNSS_5V", "F.Cu", 0.4, [(23.3, 60.3), (23.3, 61.6), (22.4, 62.5), (22.4, 62.6)]),
    ("GNSS_5V", "F.Cu", 0.4, [(22.4, 62.6), (22.5, 66.26)]),
]
POWER_VIAS += [("GNSS_5V", 20.5, _g5v + 0.95, 0.6, 0.3), ("GNSS_5V", 23.3, 60.3, 0.6, 0.3)]
# Rama de GNSS_5V al divisor de realimentación (R302.1, menos de 1 mA): desde el pin 7 del TPS63070 (donde el bloque
# deja un tramo para ella), por una vía, B.Cu bajo C305 y otra vía a la izquierda de R302. La rutaba route_rest.py
# por el mismo camino (la primera vía y su tramo son los suyos), pero con la segunda vía donde ahora está TP208.
_gx, _gy = G5_ORIGIN
POWER_TRACKS += [
    ("GNSS_5V", "F.Cu", 0.4, [(_gx - 1.67, _gy + 0.58), (_gx - 1.87, _gy + 0.58), (_gx - 2.07, _gy + 0.78)]),
    ("GNSS_5V", "B.Cu", 0.25, [(_gx - 2.07, _gy + 0.78), (_gx - 3.97, _gy - 1.17)]),
    ("GNSS_5V", "F.Cu", 0.25, [(_gx - 3.97, _gy - 1.17), (_gx - 3.21, _gy - 1.55)]),
]
POWER_VIAS += [("GNSS_5V", _gx - 2.07, _gy + 0.78, 0.8, 0.4), ("GNSS_5V", _gx - 3.97, _gy - 1.17, 0.6, 0.3)]
# GND del pin 15 del TPS63070 a su vía de siempre (la que le daba el fanout): con la zona de la antena bajada hasta
# v 30.6, la vía de C304 se corre a un lado y el fanout, que va por orden de referencia, se la quitaba
POWER_TRACKS += [("GND", "F.Cu", 0.25, [(_gx + 1.4, _gy - 0.54), (_gx + 0.791, _gy - 2.395)])]
POWER_VIAS += [("GND", _gx + 0.791, _gy - 2.395, 0.6, 0.3)]
# VSYS (salida del cargador): del relleno de VSYS junto a C109/C110 sube por F.Cu a la entrada del TPS63070 (C301-C303),
# pasando por el 10 uF de C111; al TPS62903, abajo, no hay paso por las capas externas (el abanico de la derecha del
# cargador por F.Cu y el retorno de bootstrap de SW2 por B.Cu lo cierran), así que va por In2 (0.6 mm, menos de
# 0.6 A en 1S) desde una vía en el relleno hasta otra junto a C116.
POWER_TRACKS += [
    ("VSYS", "F.Cu", 0.4, [(30.0, 43.2), (30.9, 42.3), (30.9, G5_ORIGIN[1] + 2.45), (31.4, G5_ORIGIN[1] + 1.95)]),
    ("VSYS", "In2.Cu", 0.6, [(30.0, 44.0), (31.0, 45.0), (31.0, 55.55), (31.6, 56.15)]),
    ("VSYS", "F.Cu", 0.4, [(31.6, 56.15), (31.82, 56.95)]),
]
POWER_VIAS += [("VSYS", 30.0, 44.0, 0.6, 0.3), ("VSYS", 31.6, 56.15, 0.6, 0.3)]
# ILIM (techo de entrada): sale por la derecha del cargador y su divisor (R101/R102) va a la izquierda, junto a REGN;
# cruza bajo la fila de abajo del BQ25798 por B.Cu, entre las vías de SW y las de GND de los pines 10, 11 y 13.
POWER_TRACKS += [
    ("CHG_ILIM", "B.Cu", 0.2, [(29.35, 53.25), (29.18, 53.42), (24.4, 53.42), (23.95, 53.87), (23.95, 54.2)]),
    ("CHG_ILIM", "F.Cu", 0.2, [(29.25, 53.0), (29.35, 53.25)]),
    ("CHG_ILIM", "F.Cu", 0.2, [(23.95, 54.2), (23.46, 54.55)]),
]
POWER_VIAS += [("CHG_ILIM", 29.35, 53.25, 0.6, 0.3), ("CHG_ILIM", 23.95, 54.2, 0.6, 0.3)]
TRACKS += POWER_TRACKS


def wroom_pad(n, place=None):
    """Centro del pad n (1-40) del ESP32-S3-WROOM-1 en coordenadas de placa (huella de LCSC)."""
    u0, v0, rot = (place or PLACE)["U201"]
    if n <= 14:
        x, y = -8.75, -8.89 + (n - 1) * 1.27
    elif n <= 26:
        x, y = -6.99 + (n - 15) * 1.27, 8.89
    else:
        x, y = 8.75, 7.62 - (n - 27) * 1.27
    dx, dy = rot_pt(x, y, rot)
    return (round(u0 + dx, 3), round(v0 + dy, 3))


def sd_pad(n, place=None):
    """Centro del pad n (1-9) de la microSD (TF-015) en coordenadas de placa."""
    xs = {1: 2.30, 2: 1.21, 3: 0.11, 4: -0.99, 5: -2.09, 6: -3.18, 7: -4.28, 8: -5.38, 9: -6.48}
    u0, v0, rot = (place or PLACE)["J401"]
    dx, dy = rot_pt(xs[n], -5.09, rot)
    return (round(u0 + dx, 3), round(v0 + dy, 3))


# ------------------------------------------------------------- bus de la microSD (prerruteado)
# Los pines de la microSD salen por la orilla de arriba del WROOM (girado 270, frente a la OLED) y la fila de pads
# del zócalo mira a +u, debajo del módulo. Visto desde arriba, el orden de los pines (D2 ... D1, de izquierda a
# derecha) llega al revés que el de los pads (D1 arriba ... D2 abajo) si se baja por la derecha de la fila; por
# eso el bus baja por B.Cu bajo el módulo en diagonal hacia la izquierda, corre bajo el cuerpo del zócalo y cada
# pista dobla a la derecha a la altura de su pad, sin cruces: vía junto al pin (dentro del módulo), diagonales
# paralelas a 1.27 mm, columna de pistas a 0.45 mm bajo el zócalo y una vía a la derecha de cada pad (fuera del
# cuerpo), con un tramo corto de F.Cu hasta el pad. La detección (pin 10, SD_DET) cruza el bus por F.Cu bajo el
# módulo y baja por B.Cu a la derecha del bus hasta el drenador de Q401.
SD_BUS = [("SD_D2", 9, 1), ("SD_D3", 8, 2), ("SD_CMD", 7, 3), ("SD_CLK", 6, 5), ("SD_D0", 5, 7), ("SD_D1", 4, 8)]
SD_VIA_DV = 0.65      # vía del pin: 0.65 mm por debajo del canto interior del pad
SD_BUS_U0, SD_BUS_PITCH = 11.95, 0.45   # columna bajo el zócalo
SD_PAD_VIA_U = 17.6   # vías a la derecha de la fila de pads del zócalo


def sd_bus_routes(place=None):
    tracks, vias = [], []
    for k, (net, pin, pad) in enumerate(SD_BUS):
        pu, pv = wroom_pad(pin, place)
        v_via = round(pv + 0.75 + SD_VIA_DV, 3)          # canto interior del pad (+0.75) y margen
        tu, tv = sd_pad(pad, place)
        ub = round(SD_BUS_U0 + k * SD_BUS_PITCH, 3)
        c = pu + v_via + 0.3                               # recta u + v = c (diagonal a 45°)
        tracks.append((net, "F.Cu", 0.2, [(pu, pv), (pu, v_via)]))
        tracks.append((net, "B.Cu", 0.2, [(pu, v_via), (pu, round(v_via + 0.3, 3)), (ub, round(c - ub, 3)),
                                          (ub, tv), (SD_PAD_VIA_U, tv)]))
        tracks.append((net, "F.Cu", 0.2, [(SD_PAD_VIA_U, tv), (round(tu + 0.6, 3), tv)]))
        vias += [(net, pu, v_via), (net, SD_PAD_VIA_U, tv)]
    return tracks, vias


_t, _v = sd_bus_routes()
TRACKS += _t
VIAS += _v
# GND del pin 6 de la microSD (entre CLK y D0): a una vía en la columna de las del bus, a la derecha de los pads
_gu, _gv = sd_pad(6)
TRACKS += [("GND", "F.Cu", 0.25, [(_gu, _gv), (SD_PAD_VIA_U, _gv)])]
VIAS += [("GND", SD_PAD_VIA_U, _gv)]


# ------------------------------------------------------------- pad central del WROOM-1 (pin 41, GND)
# 3 x 3 pads de 0.9 mm a 1.4 mm. El fanout no toca U201 y la vía de GND más cercana quedaba a 11.8 mm (auditoría del
# 08-10-2026). Cuatro vías de 0.6/0.3 en los cruces de los huecos entre pads (no dentro de los pads: la pasta no se va
# por los agujeros), cada una unida por F.Cu a los pads de alrededor. El cruce de arriba a la izquierda cae sobre el
# bus de la microSD (B.Cu, en diagonal bajo el módulo): la cuarta va en el hueco de la derecha de la columna de pads
# más cercana a la antena.
WROOM_EP = (-1.5, -1.17)          # centro del pad central, en coordenadas de la huella (LCSC)
WROOM_EP_VIAS = [(-0.7, -0.7), (0.7, 0.7), (0.7, -0.7), (-0.7, -2.2)]


def wroom_ep_routes(place=None):
    u0, v0, rot = (place or PLACE)["U201"]

    def to_uv(x, y):
        dx, dy = rot_pt(x, y, rot)
        return (round(u0 + dx, 3), round(v0 + dy, 3))

    cx, cy = WROOM_EP
    pads = [(cx + i * 1.4, cy + j * 1.4) for i in (-1, 0, 1) for j in (-1, 0, 1)]
    tracks, vias = [], []
    for a, b in WROOM_EP_VIAS:
        x, y = cx + a, cy + b
        vias.append(("GND",) + to_uv(x, y))
        for px, py in pads:
            if math.hypot(px - x, py - y) < 1.2:
                tracks.append(("GND", "F.Cu", 0.3, [to_uv(x, y), to_uv(px, py)]))
    return tracks, vias


_t, _v = wroom_ep_routes()
TRACKS += _t
VIAS += _v

# Bajo la fila de abajo del módulo, entre Q401 y el bloque del TPS63070: U0RXD (pin 36) y U0TXD (pin 37) bajan en
# diagonal a sus puntos de prueba, y SD_DET llega a Q401.3 por la derecha, desde una vía bajo el módulo (el mismo
# camino que tomaba route_rest.py antes de los puntos de prueba). Si SD_DET entra por la izquierda, encierra el
# relleno de GND del ancla J401.10, que queda suelto: por eso además J401.10 va unido por F.Cu a J401.6, que tiene
# su vía (por la izquierda de la fila de pads del zócalo; las filas del bus del IMU por In2 no dejan poner una vía
# junto a J401.10).
_r36, _r37 = wroom_pad(36), wroom_pad(37)
_tp8, _tp9 = PLACE["TP208"][:2], PLACE["TP209"][:2]
TRACKS += [
    ("ESP_RXD0", "F.Cu", 0.2, [_r36, (_r36[0], round(_r36[1] + 0.6, 3)), _tp9]),
    ("ESP_TXD0", "F.Cu", 0.2, [_r37, (_r37[0], round(_r37[1] + 0.6, 3)), (round(_tp8[0] - 0.77, 3), _tp8[1]), _tp8]),
    ("SD_DET", "B.Cu", 0.2, [(17.4, 27.9), (20.55, 31.3)]),
    ("SD_DET", "F.Cu", 0.2, [(20.55, 31.3), (18.75, 31.3)]),
]
VIAS += [("SD_DET", 17.4, 27.9), ("SD_DET", 20.55, 31.3)]
_g10, _g6 = (15.435, 32.24), sd_pad(6)
TRACKS += [("GND", "F.Cu", 0.25, [_g10, (14.6, 32.9), (14.6, _g6[1]), _g6])]


# ------------------------------------------------------------- bus del GNSS (prerruteado)
# Las cinco líneas del lado del micro (TX por el pin 12 y TXD2, PPS, EVENT y RESET por los pines 17-20, en la orilla
# izquierda del módulo) van a la fila de resistencias serie sobre J301, en el otro extremo de la placa. Bajan juntas
# por B.Cu: TX cruza bajo la fila de arriba del módulo hasta la franja izquierda; los pines 17-20 salen por F.Cu a
# una vía a su izquierda; las cinco bajan en columna por la franja (bajo los pulsadores), pasan a la derecha de la
# guía izquierda de la microSD, bajan por el hueco entre las patas de la carcasa del USB-C, doblan a la derecha
# bajo J101 y corren hacia J301; cada una baja en escalera a una vía sobre su resistencia y llega a su pad por un
# tramo corto de F.Cu. El orden de las columnas (de izquierda a derecha TX, TXD2, PPS, EVENT, RESET) es el de las
# resistencias, así que no hay cruces.
GNSS_BUS = [("GNSS_TX_MCU", 12, "R304"), ("GNSS_TXD2_MCU", 17, "R305"), ("GNSS_PPS_MCU", 18, "R306"),
            ("GNSS_EVENT_MCU", 19, "R307"), ("GNSS_RESET_MCU", 20, "R309")]
GNSS_PITCH = 0.4
GNSS_STRIP_U = 3.6        # columnas en la franja izquierda (la de TX)
GNSS_PIN_VIA_U = 6.65     # vías de los pines 17-20, a la izquierda de sus pads
GNSS_TX_VIA_V = 13.75     # vía de TX bajo su pad (fila de arriba del módulo)
GNSS_SD_U = 6.25          # columnas bajo la microSD, a la derecha de su guía (Ø1 en u 4.87-5.87)
GNSS_JOG1_V = 30.9        # primer desvío (franja -> microSD)
GNSS_GAP_U = 6.9          # columnas entre las patas del USB-C (u 6.6 y 8.83)
GNSS_JOG2_V = 45.0        # segundo desvío (microSD -> hueco del USB-C)
GNSS_ROW_V = 62.5         # fila de TX bajo J101; las demás, 0.4 mm más arriba cada una
GNSS_LAND_V = 63.0        # vías de llegada sobre las resistencias
_D45 = GNSS_PITCH * (math.sqrt(2) - 1)   # escalonado de los dobleces a 45° para mantener 0.4 mm entre pistas


def gnss_bus_routes(place=None):
    place = place or PLACE
    tracks, vias = [], []
    n = len(GNSS_BUS)
    for j, (net, pin, rref) in enumerate(GNSS_BUS):
        pu, pv = wroom_pad(pin, place)
        uL = round(GNSS_STRIP_U + j * GNSS_PITCH, 3)
        uM = round(GNSS_SD_U + j * GNSS_PITCH, 3)
        uG = round(GNSS_GAP_U + j * GNSS_PITCH, 3)
        h = round(GNSS_ROW_V - j * GNSS_PITCH, 3)
        ru, rv, _ = place[rref]
        pts = []
        if pin == 12:
            # TX: vía bajo el pad y por B.Cu hacia la izquierda, bajo la fila de arriba
            tracks.append((net, "F.Cu", 0.2, [(pu, pv), (pu, GNSS_TX_VIA_V)]))
            vias.append((net, pu, GNSS_TX_VIA_V))
            pts += [(pu, GNSS_TX_VIA_V), (uL + 0.3, GNSS_TX_VIA_V), (uL, GNSS_TX_VIA_V + 0.3)]
        else:
            tracks.append((net, "F.Cu", 0.2, [(pu, pv), (GNSS_PIN_VIA_U, pv)]))
            vias.append((net, GNSS_PIN_VIA_U, pv))
            pts += [(GNSS_PIN_VIA_U, pv), (uL + 0.3, pv), (uL, round(pv + 0.3, 3))]
        # primer desvío: los de la derecha empiezan antes (diagonales paralelas a 0.4 mm)
        s1 = round(GNSS_JOG1_V + (n - 1 - j) * _D45, 3)
        d1 = uM - uL
        pts += [(uL, s1), (uM, round(s1 + d1, 3))]
        s2 = round(GNSS_JOG2_V + (n - 1 - j) * _D45, 3)
        d2 = uG - uM
        pts += [(uM, s2), (uG, round(s2 + d2, 3))]
        # doblez a la derecha bajo J101: el de más a la derecha (fila más alta) dobla primero
        e = round(0.5 + (n - 1 - j) * (2 * GNSS_PITCH - GNSS_PITCH * math.sqrt(2)), 3)
        pts += [(uG, round(h - e, 3)), (round(uG + e, 3), h)]
        # escalera hasta la vía sobre la resistencia
        dv = round(GNSS_LAND_V - h, 3)
        c = min(0.5, dv)
        pts += [(round(ru - c, 3), h), (ru, round(h + c, 3)), (ru, GNSS_LAND_V)]
        clean = [pts[0]]
        for q in pts[1:]:
            if abs(q[0] - clean[-1][0]) > 1e-6 or abs(q[1] - clean[-1][1]) > 1e-6:
                clean.append(q)
        tracks.append((net, "B.Cu", 0.2, [(round(a, 3), round(b, 3)) for a, b in clean]))
        vias.append((net, ru, GNSS_LAND_V))
        tracks.append((net, "F.Cu", 0.2, [(ru, GNSS_LAND_V), (ru, round(rv - 0.51, 3))]))
    return tracks, vias


_t, _v = gnss_bus_routes()
TRACKS += _t
VIAS += _v


# ------------------------------------------------------------- bus del IMU (prerruteado)
# Las cuatro líneas del BMI088 (SDA, SCL, INT1 e INT3: pines 34, 35, 38 y 39, en la orilla de abajo del módulo) van al
# rincón de abajo a la izquierda. Bajan por vías justo dentro del módulo y corren juntas por In2 (el plano de +3V3
# queda cortado a lo largo del haz, pero unido por sus dos extremos): bajo la fila de pines, hacia la izquierda entre
# el módulo y la microSD y hacia abajo por el hueco entre las patas del USB-C, encima del bus del GNSS (que va por
# B.Cu). Al pie del hueco cada una sigue por In2 hasta una vía junto a su pin del IMU (SCL arriba, SDA arriba a la
# derecha, INT3 a la derecha entre los pines de alimentación e INT1 abajo) y llega a él por un tramo corto de
# F.Cu; las alimentaciones del IMU y las pull-ups las rutea route_rest.py. Para que el orden del haz (de izquierda a
# derecha SCL, SDA, INT3, INT1) sea el de los pines del IMU, SDA e INT3 cruzan a SCL e INT1 por F.Cu bajo el módulo.
IMU_BUS = [("IMU_SCL", 35, 0.0), ("IMU_SDA", 34, 0.7), ("IMU_INT3", 39, 0.7), ("IMU_INT1", 38, 0.0)]
IMU_VIA_V = 28.45          # vías dentro del módulo, 0.65 mm sobre el canto interior de los pads de abajo
IMU_CROSS_V = 27.75        # tramo de F.Cu de SDA e INT3 por encima de las vías de SCL e INT1
IMU_ROW_V = 31.4           # filas del tramo horizontal (SCL arriba), cada 0.4 mm
IMU_GAP_U = 7.1            # columnas en el hueco del USB-C (sobre las del GNSS), cada 0.4 mm
IMU_END_V = 59.4
_IU, _IV = 4.0, 66.9      # centro de U401 (PLACE)
IMU_END = {
    # SCL: baja en diagonal bajo Q103 a una vía sobre el pin 8 (arriba, al centro)
    "IMU_SCL": {"in2": [(7.1, 60.6), (5.2, 62.5)], "via": (_IU, 63.7), "fcu": [(_IU, _IV - 1.91)]},
    # SDA: a una vía arriba a la derecha (con su pull-up R411 al lado); al pin 9 sube por fuera de la columna
    "IMU_SDA": {"in2": [(7.5, 63.15)], "via": (6.1, 64.55),
                "fcu": [(5.85, 64.8), (5.85, 65.15), (_IU + 1.6, _IV - 1.5), (_IU + 1.2, _IV - 1.5)]},
    # INT3: a una vía justo a la derecha del pin 12, entre las salidas de +3V3 de los pines 11 y 14
    "IMU_INT3": {"in2": [(7.9, 65.4)], "via": (6.15, 67.15),
                 "fcu": [(5.9, 66.9), (_IU + 1.2, _IV)]},
    # INT1: por debajo del IMU, entre sus dos 100 nF, al pin 16 (abajo, al centro)
    "IMU_INT1": {"in2": [(8.3, 69.9), (7.85, 70.35)], "via": (_IU, 70.35), "fcu": [(_IU, _IV + 1.91)]},
}


def imu_bus_routes(place=None):
    place = place or PLACE
    tracks, vias = [], []
    n = len(IMU_BUS)
    for j, (net, pin, cross) in enumerate(IMU_BUS):
        pu, pv = wroom_pad(pin, place)
        if cross:
            # cruza por F.Cu a una vía al otro lado del vecino (SDA a la derecha de SCL, INT3 a la izquierda de INT1)
            vu = round(pu + (1.27 + 0.66) if pin == 34 else pu - (1.27 + 0.65), 3)
            tracks.append((net, "F.Cu", 0.2, [(pu, pv), (pu, IMU_CROSS_V), (vu, IMU_CROSS_V)]))
            vv = IMU_CROSS_V
        else:
            vu, vv = pu, IMU_VIA_V
            tracks.append((net, "F.Cu", 0.2, [(pu, pv), (pu, vv)]))
        vias.append((net, vu, vv))
        row = round(IMU_ROW_V + j * 0.4, 3)
        ug = round(IMU_GAP_U + j * 0.4, 3)
        e = round(0.5 + (n - 1 - j) * (2 * 0.4 - 0.4 * math.sqrt(2)), 3)   # doblez escalonado: 0.4 mm entre pistas
        pts = [(vu, vv), (vu, round(row - 0.4, 3)), (round(vu - 0.4, 3), row), (round(ug + e, 3), row),
               (ug, round(row + e, 3)), (ug, IMU_END_V)]
        # llegada al IMU: In2 hasta su vía y F.Cu hasta el pad
        ex, ey = IMU_END[net]["via"]
        pts += [(round(a, 3), round(b, 3)) for a, b in IMU_END[net]["in2"]] + [(ex, ey)]
        tracks.append((net, "In2.Cu", 0.2, pts))
        vias.append((net, ex, ey))
        tracks.append((net, "F.Cu", 0.2, [(ex, ey)] + IMU_END[net]["fcu"]))
    return tracks, vias


_t, _v = imu_bus_routes()
TRACKS += _t
VIAS += _v

# TS: el divisor (R104 a REGN y R105 a GND) va junto a la salida de TS de la fila de abajo del cargador
_tu, _tv = CHG_ORIGIN[0] + 2.15, CHG_ORIGIN[1] + 3.05
TRACKS += [("CHG_TS", "F.Cu", 0.2, [(_tu, _tv), (round(PLACE["R104"][0] - 0.51, 3), PLACE["R104"][1])]),
           ("CHG_TS", "F.Cu", 0.2, [(_tu, _tv), (round(PLACE["R105"][0] - 0.825, 3), PLACE["R105"][1])])]

# BTN_N (QON del cargador): sale hacia dentro del BQ25798 a una vía bajo el chip (ver CHG_TRACKS), va por In2 (GND bajo
# el cargador, se rellena alrededor) hasta una vía bajo C103, cruza el 5 V de la carrier por B.Cu y sube por otra vía
# junto a D402, que lo lleva al botón y a su ESD.
_bu, _bv = CHG_ORIGIN[0] + 0.0, CHG_ORIGIN[1] + 0.5
TRACKS += [("BTN_N", "In2.Cu", 0.2, [(_bu, _bv), (_bu, 53.2), (22.55, 53.2), (21.25, 54.5)]),
           ("BTN_N", "B.Cu", 0.2, [(21.25, 54.5), (20.0, 54.5), (18.75, 53.25), (18.75, 53.2)]),
           ("BTN_N", "F.Cu", 0.2, [(18.75, 53.2), (PLACE["D402"][0], PLACE["D402"][1] + 1.73)])]
VIAS += [("BTN_N", 21.25, 54.5), ("BTN_N", 18.75, 53.2)]

# ------------------------------------------------------------- ESD del lado de la carrier (U302/U303)
# Cada SRV05-4 protege dos líneas con dos canales unidos por debajo del cuerpo (1-6 y 3-4). Girados 270: GND a la
# izquierda (U303 la toma del pad de anclaje de J301; U302, de una vía en su centro) y +3V3 a la derecha (los dos
# unidos por el canto, con una vía arriba). Las cuatro líneas salen de J301: TXD2 por F.Cu bajo el cuerpo del
# conector; RXD2, PPS y EVENT bajan a una vía bajo su pin y corren por B.Cu (EVENT llega a la vía del centro de
# U303, la única forma de alcanzar su par de abajo).
_a, _b = U302_V, U303_V
GNSS_ESD_TRACKS = [
    ("GNSS_RXD2", "F.Cu", 0.2, [(32.25, _a - 0.95), (34.55, _a - 0.95)]),
    ("GNSS_TXD2", "F.Cu", 0.2, [(32.25, _a + 0.95), (34.55, _a + 0.95)]),
    ("GNSS_PPS", "F.Cu", 0.2, [(32.25, _b - 0.95), (34.55, _b - 0.95)]),
    ("GNSS_EVENT", "F.Cu", 0.2, [(32.25, _b + 0.95), (34.55, _b + 0.95)]),
    ("GND", "F.Cu", 0.3, [(32.25, _a), (33.3, _a)]),
    ("GND", "F.Cu", 0.3, [(32.25, _b), (31.2, _b)]),
    ("+3V3", "F.Cu", 0.3, [(34.55, _b), (35.4, _b), (35.4, _a), (34.55, _a)]),
    ("+3V3", "F.Cu", 0.3, [(35.4, _a), (35.4, 64.65)]),
    ("GNSS_RXD2", "F.Cu", 0.2, [(24.5, 66.26), (24.5, 67.5)]),
    ("GNSS_RXD2", "B.Cu", 0.2, [(24.5, 67.5), (24.5, 66.8), (24.9, 66.4), (30.35, 66.4), (30.75, 66.0), (30.75, 65.4)]),
    ("GNSS_RXD2", "F.Cu", 0.2, [(30.75, 65.4), (32.25, _a - 0.95)]),
    ("GNSS_TXD2", "F.Cu", 0.2, [(25.5, 66.26), (25.5, 68.1), (30.0, 68.1), (30.0, _a + 0.95), (32.25, _a + 0.95)]),
    ("GNSS_PPS", "F.Cu", 0.2, [(26.5, 66.26), (26.5, 67.5)]),
    ("GNSS_PPS", "B.Cu", 0.2, [(26.5, 67.5), (26.5, 67.9), (26.9, 68.3), (30.55, 68.3), (30.9, 68.65)]),
    ("GNSS_PPS", "F.Cu", 0.2, [(30.9, 68.65), (32.25, _b - 0.95)]),
    ("GNSS_EVENT", "F.Cu", 0.2, [(27.5, 66.26), (27.5, 67.5)]),
    ("GNSS_EVENT", "B.Cu", 0.2, [(27.5, 67.5), (32.4, 67.5), (33.3, 68.4), (33.3, _b)]),
    ("GNSS_EVENT", "F.Cu", 0.2, [(33.3, _b), (33.3, _b + 0.95)]),
]
GNSS_ESD_VIAS = [("GND", 33.3, _a), ("+3V3", 35.4, 64.65), ("GNSS_RXD2", 24.5, 67.5), ("GNSS_RXD2", 30.75, 65.4),
                 ("GNSS_PPS", 26.5, 67.5), ("GNSS_PPS", 30.9, 68.65), ("GNSS_EVENT", 27.5, 67.5),
                 ("GNSS_EVENT", 33.3, _b)]
TRACKS += GNSS_ESD_TRACKS
VIAS += GNSS_ESD_VIAS

# Textos: (texto, capa, u, v, tamaño, ángulo). La cara de componentes no tiene sitio para rótulos: la función de
# cada conector del canto de abajo, el logotipo, el sitio y las notas de variante van en la cara trasera (sin
# componentes; queda frente a la carrier).
TEXTS = [
    ("v0.3", "F.SilkS", 33.5, 9.6, 0.8, 0),
    ("www.tresvizo.com", "B.SilkS", 18.0, 26.9, 1.6, 0),
    ("TresVizo MeridianV - placa principal v0.3", "B.SilkS", 18.0, 29.0, 1.0, 0),
    ("2026-10 - 4 capas JLC04161H-7628", "B.SilkS", 18.0, 30.6, 0.8, 0),
    ("1S: R103=4.7k R116=10k U103=MAX17048", "B.SilkS", 18.0, 32.0, 0.8, 0),
    ("2S: R103=8.2k R116=3.9k U103=MAX17049", "B.SilkS", 18.0, 33.3, 0.8, 0),
    ("2S: R112 NC  R114 0R", "B.SilkS", 18.0, 34.6, 0.8, 0),
    # rótulos de los conectores del canto de abajo, detrás de cada uno (sus pads son de la cara de arriba)
    ("NTC J404", "B.SilkS", 9.1, 67.2, 0.8, 0),
    ("BAT J102", "B.SilkS", 15.9, 67.2, 0.8, 0),
    ("1-2 BAT-  3-4 BAT+", "B.SilkS", 15.9, 68.6, 0.8, 0),
    ("GNSS J301", "B.SilkS", 26.0, 67.2, 0.8, 0),
]

# Logotipo (scripts/logo.py, de los archivos del repositorio): completo en la cara trasera, detrás del WROOM (detrás
# de la OLED están la muesca de la SMA y los pines de la OLED), con las notas debajo. En la cara de componentes no
# cabe el distintivo.
LOGOS = [
    {"kind": "full", "layer": "B.SilkS", "width": 26.0, "center": (18.0, 19.3)},
]

# ------------------------------------------------------------- clavijas enchufadas
# Conectores de cable de entrada lateral: familia, pines y borde de la boca en coordenadas de la huella
# (+y local: borde exterior de los pads de anclaje o del patio, el mayor). Cada uno apunta al canto de abajo:
# delante de la boca se reserva, sin componentes, lo que asoma la clavija enchufada y el doblez de sus cables,
# con 1 mm a cada lado para tomarla (DRC: áreas «clavija_*»; CAD: kicad/plugs.json).
SIDE_ENTRY = {"J301": ("SH", 8, 2.84), "J404": ("SH", 2, 2.84), "J102": ("GH", 4, 2.95)}
# JST: GH enchufado asoma 7.15 - 4.05 = 3.1 mm de la boca y mide 4.35 de alto (eGH, «Assembly layout»);
# carcasa GHR de (n-1)·1.25 + 2.5 de ancho. SH: carcasa SHR de 5.0 de largo, (n-1) + 2.0 de ancho y 2.8 de
# alto (eSH); se toma 3.0 de asomo. Reserva para doblar los cables: 3 mm.
PLUG = {"GH": {"out": 3.1, "wires": 3.0, "h": 4.35, "pitch": 1.25, "extra": 2.5},
        "SH": {"out": 3.0, "wires": 3.0, "h": 2.95, "pitch": 1.0, "extra": 2.0}}
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


def outline_uv():
    c = CHAMFER
    n1, nv1, n2, nv2 = NOTCH
    s1, sv1, s2, sv2 = SMA_NOTCH
    r = SMA_NOTCH_R
    # Esquinas interiores de la muesca de la SMA: cuartos de círculo de radio r (6 tramos de 15°)
    arc1 = [(round(s1 + r + r * math.cos(math.radians(a)), 4), round(sv2 - r + r * math.sin(math.radians(a)), 4))
            for a in range(180, 89, -15)]
    arc2 = [(round(s2 - r + r * math.cos(math.radians(a)), 4), round(sv2 - r + r * math.sin(math.radians(a)), 4))
            for a in range(90, -1, -15)]
    return [(c, 0), (s1, sv1)] + arc1 + arc2 + [(s2, sv1), (W - c, 0), (W, c), (W, H - c), (W - c, H), (c, H),
                                                (0, H - c), (0, nv2), (n2, nv2), (n2, nv1), (0, nv1), (0, c)]


def outline():
    return [to_abs(u, v) for u, v in outline_uv()]


def oled_holes(place=None):
    """Agujeros sin metalizar de la OLED (en su huella, a (±11.75, -0.6) del centro de la fila de pines)."""
    u0, v0, rot = (place or PLACE)["J403"]
    return [(u0 + rot_pt(x, -0.6, rot)[0], v0 + rot_pt(x, -0.6, rot)[1]) for x in (-11.75, 11.75)]


def antenna_area(place=None):
    """Zona de la antena del WROOM-1 (los 6.5 mm de la punta de la huella) prolongada hasta el canto derecho."""
    u0, v0, rot = (place or PLACE)["U201"]
    assert rot == 270
    return (u0 + 16.39 - 6.5, v0 - 9.0, W, v0 + 9.0)


# Zona sin cobre de la antena, más ancha que la antena (auditoría del 08-10-2026): por arriba sube hasta v 9 (bajo la
# OLED solo había una vía de cosido) y por abajo baja hasta v 32 a la derecha de R301, sobre C301 y C302. Entre u 26.64
# y 32 baja solo hasta v 30.6, justo encima de los pads de R301 y C304 (la fila de arriba del bloque del TPS63070, en
# v 30.77): el bloque no puede bajar (L301 queda a 0.6 mm de L101) y sus vías de GND se van a los lados.
ANT_TOP_V, ANT_MID_V, ANT_LOW_V, ANT_LOW_U = 9.0, 30.6, 32.0, 32.0


def antenna_keepout(place=None):
    """Polígono (u, v) de la zona sin cobre de la antena."""
    u1, v1, u2, v2 = antenna_area(place)
    return [(u1, ANT_TOP_V), (u2, ANT_TOP_V), (u2, ANT_LOW_V), (ANT_LOW_U, ANT_LOW_V), (ANT_LOW_U, ANT_MID_V),
            (u1, ANT_MID_V)]


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

# Panel para el pedido (panelize.py): la placa principal sola, con rieles de 5 mm, marcas de JLCPCB y cuatro
# puentes de 5 mm con mouse bites, dos por canto lateral. Ninguno a menos de 5 mm del BMI088 (U401) ni de los
# condensadores de potencia (0805 de 10 y 22 uF), que se pueden rajar al separar la placa (auditoría del
# 08-10-2026; antes había uno junto a U401 y otro junto a C113). A la izquierda, arriba (v 4-9, junto a
# resistencias y puntos de prueba) y junto a la carcasa metálica de la microSD (v 38.5-43.5); a la derecha, los
# dos en la franja de la antena (v 10.5-15.5 y 21.5-26.5), sin piezas ni cobre: los agujeros caen dentro de su
# zona sin cobre. Sin puentes en la muesca del USB-C ni en el canto de abajo (bocas de los conectores, U401,
# U302/U303) ni en el de arriba (tope de la carcasa en z 80). Los cuatro quedan en los 45 mm de arriba: la parte
# de abajo cuelga unos 30 mm. Los puentes caen en las ranuras de la pared: lijar la rebaba.
PANEL = {
    "boards": [{"name": "main", "file": "tresvizo-main.kicad_pcb", "at": [107.0, 107.0]}],
    "gap": 2.0,
    "rails": [5.0, 5.0, 5.0, 5.0],
    "tabs": [
        {"board": "main", "edge": "left", "offset": 6.5, "width": 5.0},
        {"board": "main", "edge": "left", "offset": 41.0, "width": 5.0},
        {"board": "main", "edge": "right", "offset": 13.0, "width": 5.0},
        {"board": "main", "edge": "right", "offset": 24.0, "width": 5.0},
    ],
    "mousebite": {"drill": 0.6, "pitch": 0.9, "offset": 0.0},
    "keepout": 1.0,
    "marks": {"tooling_drill": 2.0, "tooling_inset": [2.5, 2.5], "fiducial_inset": [6.0, 3.85]},
    "texts": [{"text": "JLCJLCJLCJLC", "layer": "B.SilkS", "at": [125.0, 182.5], "size": 1.0}],
}


def tab_keepouts():
    """Zona sin cobre junto a cada puente del panel (la misma que deja panelize.py), en coordenadas de placa."""
    out = []
    k = PANEL["keepout"]
    for t in PANEL["tabs"]:
        w, off = t["width"], t["offset"]
        e = t["edge"]
        if e == "left":
            box = (0.0, off - w / 2 - 0.5, k, off + w / 2 + 0.5)
        elif e == "right":
            box = (W - k, off - w / 2 - 0.5, W, off + w / 2 + 0.5)
        elif e == "top":
            box = (off - w / 2 - 0.5, 0.0, off + w / 2 + 0.5, k)
        else:
            box = (off - w / 2 - 0.5, H - k, off + w / 2 + 0.5, H)
        out.append((e, box))
    return out


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
    zones.append({"net": "GND", "layer": "F.Cu", "priority": 2, "name": "GND_J102",
                  "polygon": [to_abs(u, v) for u, v in J102_GND_ZONE], "clearance": 0.2, "solid_pads": True})
    # Bajo la etapa de potencia del cargador, la capa interna 3 es GND (no +3V3): las pistas de SW1/SW2 por B.Cu
    # (y sus retornos de bootstrap) quedan entre dos planos de GND. v0.3: solo bajo la bobina, las pistas de SW y el
    # chip; en v0.2 era todo el bloque, pero aquí hay piezas de +3V3 alrededor (pull-ups de la microSD, C402...) y
    # sus vías quedaban sin plano.
    chg_box = [(-3.3, -12.0), (3.3, -12.0), (3.3, -0.2), (7.2, -0.2), (7.2, 1.2), (3.3, 1.2), (3.3, 2.6),
               (-3.3, 2.6), (-3.3, 1.2), (-5.6, 1.2), (-5.6, -0.2), (-3.3, -0.2)]
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
    cu = ["F.Cu", "In1.Cu", "In2.Cu", "B.Cu"]
    keepouts = []
    # Agujeros de la OLED: M2 con tuerca por detrás, sin cobre alrededor en ninguna capa
    for k, (u, v) in enumerate(oled_holes(place)):
        keepouts.append({"rule_area": True, "name": "oled_agujero_%d" % (k + 1),
                         "polygon": circle_poly(u, v, OLED_HOLE_FREE_R), "layers": cu,
                         "no_tracks": True, "no_vias": True, "no_pour": True})
    # Antena del ESP32-S3-WROOM-1 en el canto derecho: sin cobre en ninguna capa (guía de Espressif)
    keepouts.append({"rule_area": True, "name": "esp32_antena",
                     "polygon": [to_abs(u, v) for u, v in antenna_keepout(place)],
                     "layers": cu, "no_tracks": True, "no_vias": True, "no_pour": True})
    # Puentes del panel: sin cobre a menos de 1 mm del canto (el corte deja el canto a la vista)
    for k, (e, box) in enumerate(tab_keepouts()):
        keepouts.append({"rule_area": True, "name": "puente_%d" % (k + 1), "polygon": rect(*box), "layers": cu,
                         "no_tracks": True, "no_vias": True, "no_pour": True})
    # BMI088: sin pistas, vías ni relleno en F.Cu bajo el cuerpo, entre sus pads (hoja de Bosch, recomendaciones de
    # montaje)
    iu, iv, irot = place["U401"]
    hx, hy = (1.35, 0.65) if irot % 180 == 90 else (0.65, 1.35)
    keepouts.append({"rule_area": True, "name": "imu_bajo_cuerpo", "polygon": rect(iu - hx, iv - hy, iu + hx, iv + hy),
                     "layers": ["F.Cu"], "no_tracks": True, "no_vias": True, "no_pour": True})
    # USB-C: sin pistas ni vías de la cara de arriba bajo el cuerpo (su carcasa metálica apoya sobre la máscara);
    # por debajo pasan el bus del GNSS (B.Cu) y el del IMU (In2)
    ju, jv, _ = place["J101"]
    keepouts.append({"rule_area": True, "name": "usb_bajo_cuerpo", "polygon": rect(ju - 4.77, jv - 4.6, ju + 1.45, jv + 4.6),
                     "layers": ["F.Cu"], "no_tracks": True, "no_vias": True, "no_pour": False})
    # Guía de luz sobre D403: anillo sin huellas entre 1.25 y 1.5 mm de su centro (dentro solo cabe el propio D403;
    # otra pieza ahí chocaría con su patio). Polígono en C con una ranura de 4° para no tener agujero.
    du, dv, _ = place["D403"]
    ring = [(du + LIGHT_PIPE_R * math.cos(math.radians(a)), dv + LIGHT_PIPE_R * math.sin(math.radians(a)))
            for a in range(2, 359, 4)]
    ring += [(du + 1.25 * math.cos(math.radians(a)), dv + 1.25 * math.sin(math.radians(a))) for a in range(358, 1, -4)]
    keepouts.append({"rule_area": True, "name": "guia_de_luz_D403", "polygon": [to_abs(u, v) for u, v in ring],
                     "layers": ["F.Cu"], "no_tracks": False, "no_vias": False, "no_pour": False,
                     "no_footprints": True})
    # Franjas de los cantos laterales (sin componentes)
    for k, (u1, u2) in enumerate(((0.0, EDGE_STRIP), (W - EDGE_STRIP, W))):
        keepouts.append({"rule_area": True, "name": "canto_%d" % (k + 1), "polygon": rect(u1, 0.0, u2, H),
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
        cu_, cv = lg["center"]
        logo_boxes.append(rect(cu_ - w / 2 - 0.4, cv - h / 2 - 0.4, cu_ + w / 2 + 0.4, cv + h / 2 + 0.4))
    spec = {
        "libs": {"tresvizo_lcsc": "lib/lcsc.pretty"},
        "board": {"layers": 4, "thickness": 1.6, "outline": {"type": "polygon", "points": outline()}, "holes": []},
        "rules": {"min_clearance": 0.127, "min_track": 0.127, "min_via_dia": 0.5, "min_drill": 0.3,
                  "min_annular": 0.1, "hole_to_hole": 0.5, "edge_clearance": 0.3, "hole_clearance": 0.25,
                  "min_resolved_spokes": 1},
        "netclasses": NETCLASSES,
        # El BQ25798 (RQM0029A) no tiene modelo 3D en KiCad 10: se usa un VQFN de 4 x 4 x 1 mm
        "model_substitutes": {
            "Texas_RQM0029A_VQFN-29_4x4mm_P0.4mm.step":
                "${KICAD10_3DMODEL_DIR}/Package_DFN_QFN.3dshapes/Texas_RGE0024C_VQFN-24-1EP_4x4mm_P0.5mm_EP2.1x2.1mm.step"},
        "placement": placement,
        "fanout": {"nets": ["GND", "+3V3"], "skip_refs": ["U201", "J102"]},
        "stitching": {"pitch": 3.0, "dia": 0.6, "drill": 0.3, "clearance": 0.25, "edge": 0.8,
                      "no_vias_under": ["U201", "J401", "U102", "U105", "U301", "U401", "J101", "SW401"],
                      "avoid_polys": logo_boxes},
        "zones": zones + keepouts,
        "tracks": [{"net": n, "layer": l, "width": w, "points": [to_abs(u, v) for u, v in pts]}
                   for n, l, w, pts in TRACKS],
        "vias": [{"net": n, "x": to_abs(u, v)[0], "y": to_abs(u, v)[1]} for n, u, v in VIAS] +
                [{"net": n, "x": to_abs(u, v)[0], "y": to_abs(u, v)[1], "dia": d, "drill": dr}
                 for n, u, v, d, dr in POWER_VIAS],
        "texts": [{"text": t, "layer": l, "x": to_abs(u, v)[0], "y": to_abs(u, v)[1], "size": sz, "angle": a}
                  for t, l, u, v, sz, a in TEXTS],
        "graphics": graphics,
    }
    with open(os.path.join(kicad_dir, "board.json"), "w", encoding="utf-8") as f:
        json.dump(spec, f, indent=1)
    # Para la carcasa (cad/export_board_step.py): clavijas en coordenadas de placa y su paso a la carcasa
    with open(os.path.join(kicad_dir, "plugs.json"), "w", encoding="utf-8") as f:
        json.dump({"note": "Coordenadas de placa (u, v) en mm; carcasa v0.3 (tubo de Ø52 con cara plana): "
                           "x = x_u0 - u, z = z_top - v, dorso en y = y_back y cara de componentes en y = y_face "
                           "(las clavijas van de y_face a y_face + h).",
                   "z_top": Z_TOP, "y_face": Y_FACE, "y_back": Y_BACK, "size": [W, H], "x_u0": X_U0,
                   "cutouts": [
                       {"name": "usb_c", "note": "muesca frente a la boca del USB-C (J101), abierta al canto u = 0",
                        "u": [NOTCH[0], NOTCH[2]], "v": [NOTCH[1], NOTCH[3]],
                        "x": [X_U0 - NOTCH[2], X_U0 - NOTCH[0]], "z": [Z_TOP - NOTCH[3], Z_TOP - NOTCH[1]]},
                       {"name": "sma_carrier", "note": "muesca del canto de arriba para la clavija SMA de la carrier "
                                                       "(eje en x -1.2, y 10.2; tuerca hasta y 14.8); esquinas "
                                                       "interiores con radio r",
                        "u": [SMA_NOTCH[0], SMA_NOTCH[2]], "v": [SMA_NOTCH[1], SMA_NOTCH[3]], "r": SMA_NOTCH_R,
                        "x": [round(X_U0 - SMA_NOTCH[2], 3), round(X_U0 - SMA_NOTCH[0], 3)],
                        "z": [Z_TOP - SMA_NOTCH[3], Z_TOP - SMA_NOTCH[1]]}],
                   "plugs": [dict(ref=r, **b) for r, b in sorted(plugs.items())]}, f, indent=1)
    with open(os.path.join(kicad_dir, "panel.json"), "w", encoding="utf-8") as f:
        json.dump(PANEL, f, indent=1)
