"""Comprueba en el modelo 3D de la placa dónde quedan el USB-C y el GH (exportación VRML de kicad-cli).

    python3 check3d.py <placa.wrl> <placa.kicad_pcb>

Evalúa las transformaciones del VRML y mide, sobre los modelos 3D de los conectores, la cara del
receptáculo USB-C, la altura de su eje (centro de la carcasa) sobre la cara de componentes y la boca
del GH, en coordenadas de la placa (u, v) y de la carcasa V2.2 (x = u - 10.4, y = 31.3 - v, z = 91.77 + h).
Es una medida sobre los modelos de LCSC, no sobre piezas reales.
"""

import math
import os
import re
import sys

sys.dont_write_bytecode = True
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import layout  # noqa: E402

U0, V0, Z_TOP = 10.4, 31.3, 91.77   # x = u - U0, y = V0 - v, z = Z_TOP + altura sobre la cara superior


def tokens(text):
    return re.findall(r'[{}\[\]]|"[^"]*"|[^\s{}\[\],]+', text)


def parse(toks):
    i = 0

    def is_node(k):
        return toks[k] == "DEF" or (k + 1 < len(toks) and toks[k + 1] == "{")

    def node():
        nonlocal i
        name = None
        if toks[i] == "DEF":
            name = toks[i + 1]
            i += 2
        if toks[i] == "USE":
            i += 2
            return None
        typ = toks[i]
        i += 2  # tipo y «{»
        fields = {}
        while toks[i] != "}":
            key = toks[i]
            i += 1
            if toks[i] == "[":
                i += 1
                items = []
                while toks[i] != "]":
                    if is_node(i):
                        items.append(node())
                    else:
                        items.append(toks[i])
                        i += 1
                i += 1
                fields[key] = items
            elif is_node(i):
                fields[key] = node()
            else:
                vals = []
                while toks[i] != "}" and (not re.match(r"^[a-zA-Z_]", toks[i]) or toks[i] in ("TRUE", "FALSE")):
                    vals.append(toks[i])
                    i += 1
                fields[key] = vals
        i += 1
        return (typ, name, fields)

    roots = []
    while i < len(toks):
        if is_node(i):
            roots.append(node())
        else:
            i += 1
    return roots


def rotmat(ax, ay, az, ang):
    n = math.sqrt(ax * ax + ay * ay + az * az) or 1.0
    x, y, z = ax / n, ay / n, az / n
    c, s, k = math.cos(ang), math.sin(ang), 1 - math.cos(ang)
    return [[c + x * x * k, x * y * k - z * s, x * z * k + y * s],
            [y * x * k + z * s, c + y * y * k, y * z * k - x * s],
            [z * x * k - y * s, z * y * k + x * s, c + z * z * k]]


def walk(n, xf, shapes):
    if not isinstance(n, tuple):
        return
    typ, name, f = n
    if typ == "Transform":
        t = [float(v) for v in f.get("translation", ["0", "0", "0"])]
        r = [float(v) for v in f.get("rotation", ["0", "0", "1", "0"])]
        s = [float(v) for v in f.get("scale", ["1", "1", "1"])]
        m = rotmat(*r)

        def child_xf(p, xf=xf, t=t, m=m, s=s):
            q = (p[0] * s[0], p[1] * s[1], p[2] * s[2])
            q = tuple(sum(m[a][b] * q[b] for b in range(3)) for a in range(3))
            return xf((q[0] + t[0], q[1] + t[1], q[2] + t[2]))
        for c in f.get("children", []):
            walk(c, child_xf, shapes)
    elif typ == "Shape":
        g = f.get("geometry")
        if g and g[0] == "IndexedFaceSet" and g[2].get("coord"):
            pts = [float(v) for v in g[2]["coord"][2].get("point", [])]
            shapes.append([xf((pts[k], pts[k + 1], pts[k + 2])) for k in range(0, len(pts) - 2, 3)])


def box(pts):
    xs, ys, zs = zip(*pts)
    return min(xs), max(xs), min(ys), max(ys), min(zs), max(zs)


def main():
    wrl, pcb = sys.argv[1:3]
    shapes = []
    for r in parse(tokens(open(wrl, encoding="utf-8").read())):
        walk(r, lambda p: p, shapes)
    thick = float(re.search(r"\(thickness ([\d.]+)\)", open(pcb, encoding="utf-8").read()).group(1))
    top = thick / 2
    # Cuerpo de la placa: la forma plana más grande con el espesor de la placa
    boards = [b for b in map(box, shapes) if b[4] > -top - 0.05 and b[5] < top + 0.05 and b[5] - b[4] > thick * 0.8]
    bx = max(boards, key=lambda b: (b[1] - b[0]) * (b[3] - b[2]))
    v_front = layout.V_FRONT

    def uv(x, y):
        return x - bx[0], v_front + (bx[3] - y)

    def model(region):
        """Formas de un modelo 3D (las que sobresalen más de 1 mm de la placa y cuyo centro cae en
        region = (u1, v1, u2, v2)); devuelve todas y la de más puntos (carcasa o cuerpo)."""
        found = []
        for pts in shapes:
            b = box(pts)
            if b[5] < top + 1.0:
                continue
            cu, cv = uv((b[0] + b[1]) / 2, (b[2] + b[3]) / 2)
            if region[0] <= cu <= region[2] and region[1] <= cv <= region[3]:
                found.append(pts)
        return found, (max(found, key=len) if found else None)

    usb_all, shell = model((8.0, -1.0, 13.0, 8.0))
    gh_all, _ = model((6.0, 14.0, 15.0, 20.0))
    if shell:
        b = box([p for pts in usb_all for p in pts])
        u1, v_face = uv(b[0], b[3])
        u2, v_back = uv(b[1], b[2])
        uc = (u1 + u2) / 2
        # Cuerpo de la carcasa sin las patas (que van por los costados y atraviesan la placa)
        body = [p for p in shell if abs(uv(p[0], p[1])[0] - uc) < 3.5]
        bb = box(body)
        h_bot, h_top = bb[4] - top, bb[5] - top
        axis = (h_bot + h_top) / 2
        print("USB-C (modelo 3D de LCSC):")
        print("  ancho u %.2f-%.2f (centro %.2f, x = %.2f)" % (u1, u2, uc, uc - U0))
        print("  cara v = %.2f (y = %.2f), extremo de las colas SMD v = %.2f" % (v_face, V0 - v_face, v_back))
        print("  sobresale del canto frontal (v = %.2f): %.2f mm" % (v_front, v_front - v_face))
        print("  carcasa de %.2f a %.2f mm sobre la cara de componentes; eje a %.2f mm (z = %.2f)"
              % (h_bot, h_top, axis, Z_TOP + axis))
    if gh_all:
        b = box([p for pts in gh_all for p in pts])
        _, v_mouth = uv(b[0], b[2])
        _, v_back = uv(b[0], b[3])
        print("GH 8 (modelo 3D de LCSC):")
        print("  boca v = %.2f (y = %.2f, %.2f mm dentro del canto), extremo de las patas v = %.2f; "
              "alto %.2f mm sobre la placa" % (v_mouth, V0 - v_mouth, layout.V_REAR - v_mouth, v_back, b[5] - top))


if __name__ == "__main__":
    main()
