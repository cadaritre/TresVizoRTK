"""Carrier BDLX RTK_UM98_V1.0.1 aproximada, con sus componentes, para las comprobaciones en FreeCAD.

BDLX no publica plano. Las medidas salen de una foto rectificada del propietario (05-10-2026, cinta
métrica, sin calibrador): ±1 mm. Coordenadas de foto: mm desde la esquina superior izquierda de la cara
de componentes, con el SMA arriba. En la carcasa la cara de componentes mira a la placa (+Y), así que
x = x_der - px y z = z_sup - py, con x_der, z_sup e y del dorso tomados de chasis.carrier en
mechanical/v2.3/parameters.json.

Lo que importa para las ranuras son los cantos, porque la carrier no tiene margen libre en ellos:
  - el USB-C sobresale ~0.9 mm del canto +X (foto: canto izquierdo);
  - la columna de 8 agujeros junto al conector de 8 pines está pegada al canto -X. Ahí y en la fila de
    5 junto a CON1 se suelda el arnés de J301: sus soldaduras asoman por detrás del PCB.
"""

import FreeCAD as App
import Part

V = App.Vector

# Cara de componentes: (nombre, px0, px1, py0, py1, alto sobre la cara)
FRONT = [
    ("USB-C (sobresale del canto +X)", -0.9, 6.3, 38.6, 48.0, 3.3),
    ("UM980 y su placa azul", 0.5, 23.5, 10.0, 27.8, 2.8),
    ("LEDs RTK/PVT", 1.4, 7.2, 5.8, 7.6, 0.8),
    ("pasivos C12-C14/L1", 8.4, 11.2, 1.4, 9.0, 1.0),
    ("SMA cuerpo", 13.8, 20.6, -0.6, 6.8, 6.5),
    ("u.FL P3", 23.8, 26.8, 2.8, 5.8, 1.3),
    ("IC de 8 pines", 23.6, 29.2, 19.2, 26.8, 1.6),
    ("pasivos del canto -X", 29.3, 31.3, 17.8, 28.0, 1.0),
    ("D6/R4", 23.5, 27.8, 28.8, 32.2, 1.2),
    ("GH8 vertical", 26.6, 30.8, 33.3, 47.4, 4.3),
    ("CON1 GH5 lateral", 11.6, 21.6, 46.0, 51.2, 4.3),
    ("electrónica central", 6.5, 24.0, 29.0, 45.5, 3.0),
    ("IC izquierdo y pasivos", 1.5, 9.0, 30.5, 37.0, 1.2),
]
SMA_AXIS = (17.2, 3.3)              # px del eje del cañón y su altura sobre la cara
SMA_BARREL = (6.4, 10.5)            # diámetro y largo por encima del canto superior
COIN = (27.5, 13.3, 7.0, 2.3)       # pila de botón: centro, diámetro y alto
HOLES_8 = [(31.3, 29.6 + i * 2.47) for i in range(8)]   # columna junto al conector de 8 pines
HOLES_5 = [(11.9 + i * 2.5, 51.4) for i in range(5)]    # fila junto a CON1
JOINT = (1.8, 1.0)                  # soldadura del arnés: diámetro y cuánto asoma por detrás
WIRE = (1.0, 3.0)                   # cable del arnés por delante: diámetro y tramo recto


def build(carrier):
    """Piezas de la carrier en la carcasa: {nombre: sólido}. 'carrier' es chasis.carrier."""
    x1, z1 = carrier["x"][1], carrier["z"][1]
    yb = carrier["y"][0]
    yf = yb + carrier["pcb"]

    def box(px0, px1, py0, py1, y0, dy):
        x0, xx = sorted((x1 - px0, x1 - px1))
        z0, zz = sorted((z1 - py0, z1 - py1))
        return Part.makeBox(xx - x0, dy, zz - z0, V(x0, y0, z0))

    def cyl(px, py, dia, y0, dy):
        return Part.makeCylinder(dia / 2.0, dy, V(x1 - px, y0, z1 - py), V(0, 1, 0))

    def fuse(shapes):
        s = shapes[0]
        for t in shapes[1:]:
            s = s.fuse(t)
        return s

    w = carrier["x"][1] - carrier["x"][0]
    h = carrier["z"][1] - carrier["z"][0]
    out = {"PCB": Part.makeBox(w, carrier["pcb"], h, V(carrier["x"][0], yb, carrier["z"][0]))}
    for name, px0, px1, py0, py1, hh in FRONT:
        out[name] = box(px0, px1, py0, py1, yf, hh)
    out["SMA cañón"] = Part.makeCylinder(SMA_BARREL[0] / 2.0, SMA_BARREL[1],
                                         V(x1 - SMA_AXIS[0], yf + SMA_AXIS[1], z1), V(0, 0, 1))
    out["pila de botón"] = fuse([cyl(COIN[0], COIN[1], COIN[2], yf, COIN[3]),
                                 box(27.8, 29.0, 13.0, 18.5, yf, 1.0)])
    legs = carrier["sma"].get("patas")
    if legs:
        out["patas del SMA (atrás)"] = Part.makeBox(legs["x"][1] - legs["x"][0], legs["atras"],
                                                    legs["z"][1] - legs["z"][0],
                                                    V(legs["x"][0], yb - legs["atras"], legs["z"][0]))
    out["arnés J301: soldaduras atrás (8 agujeros)"] = fuse(
        [cyl(px, py, JOINT[0], yb - JOINT[1], JOINT[1]) for px, py in HOLES_8])
    out["arnés J301: cables por delante (8 agujeros)"] = fuse(
        [cyl(px, py, WIRE[0], yf, WIRE[1]) for px, py in HOLES_8])
    out["arnés J301: soldaduras atrás (5 agujeros)"] = fuse(
        [cyl(px, py, JOINT[0], yb - JOINT[1], JOINT[1]) for px, py in HOLES_5])
    return out
