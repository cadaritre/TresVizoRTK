"""Logotipo de TresVizo para la serigrafía.

Fuentes del propio repositorio (no se descarga nada):
- logo completo (distintivo + «VIZO», el del sitio www.tresvizo.com y del firmware):
  firmware/esp32/assets/tresvizo-logo.svg, contornos M/L/Z con relleno par-impar;
- distintivo solo (hexágono con el 3), en vectores: mechanical/v2.2/logo.json.

Devuelve polígonos [(contorno, [huecos])] en mm de placa (v hacia abajo) listos para board.json.
"""

import json
import math
import os
import re

REPO = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", ".."))
SVG = os.path.join(REPO, "firmware", "esp32", "assets", "tresvizo-logo.svg")
BADGE = os.path.join(REPO, "mechanical", "v2.2", "logo.json")


def _rdp(pts, eps):
    """Douglas-Peucker sobre una polilínea abierta."""
    if len(pts) < 3:
        return pts
    (ax, ay), (bx, by) = pts[0], pts[-1]
    dx, dy = bx - ax, by - ay
    L = math.hypot(dx, dy)
    best, idx = -1.0, 0
    for i in range(1, len(pts) - 1):
        px, py = pts[i]
        d = abs(dy * (px - ax) - dx * (py - ay)) / L if L else math.hypot(px - ax, py - ay)
        if d > best:
            best, idx = d, i
    if best <= eps:
        return [pts[0], pts[-1]]
    return _rdp(pts[:idx + 1], eps)[:-1] + _rdp(pts[idx:], eps)


def _simplify_ring(ring, eps):
    # Se parte el anillo por el punto más lejano al primero para que el RDP no colapse el lazo
    far = max(range(len(ring)), key=lambda i: math.hypot(ring[i][0] - ring[0][0], ring[i][1] - ring[0][1]))
    a = _rdp(ring[:far + 1], eps)
    b = _rdp(ring[far:] + [ring[0]], eps)
    return a[:-1] + b[:-1]


def _inside(pt, poly):
    x, y = pt
    c = False
    j = len(poly) - 1
    for i in range(len(poly)):
        xi, yi = poly[i]
        xj, yj = poly[j]
        if (yi > y) != (yj > y) and x < (xj - xi) * (y - yi) / (yj - yi + 1e-12) + xi:
            c = not c
        j = i
    return c


def _nest(rings):
    """Anillos con regla par-impar -> [(contorno, [huecos])]."""
    depth = [sum(1 for j, o in enumerate(rings) if j != i and _inside(r[0], o)) for i, r in enumerate(rings)]
    out = []
    for i, r in enumerate(rings):
        if depth[i] % 2:
            continue
        holes = [h for j, h in enumerate(rings) if depth[j] == depth[i] + 1 and _inside(h[0], r)]
        out.append((r, holes))
    return out


def _place(polys, width, center, mirror):
    xs = [x for o, hs in polys for ring in [o] + hs for x, _ in ring]
    ys = [y for o, hs in polys for ring in [o] + hs for _, y in ring]
    x0, x1, y0, y1 = min(xs), max(xs), min(ys), max(ys)
    k = width / (x1 - x0)
    cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
    sgn = -1 if mirror else 1

    def tr(ring):
        return [(round(center[0] + sgn * (x - cx) * k, 4), round(center[1] + (y - cy) * k, 4)) for x, y in ring]
    return [(tr(o), [tr(h) for h in hs]) for o, hs in polys], (x1 - x0) * k, (y1 - y0) * k


def full_logo(width, center, mirror=False, eps_px=0.6):
    """Logo completo (distintivo + VIZO) de `width` mm de ancho, centrado en `center` (u, v).
    `mirror` para la cara trasera (se lee desde atrás). Devuelve (polígonos, ancho, alto)."""
    s = open(SVG, encoding="utf-8").read()
    d = re.search(r' d="([^"]+)"', s).group(1)
    rings = []
    for sub in re.findall(r"M([^Z]+)Z", d):
        pts = [tuple(float(c) for c in p.split(",")) for p in re.findall(r"(-?[\d.]+,-?[\d.]+)", sub)]
        rings.append(_simplify_ring(pts, eps_px))
    return _place(_nest(rings), width, center, mirror)


def badge(width, center, mirror=False):
    """Distintivo solo (hexágono con el 3), de los contornos vectoriales del CAD de la carcasa."""
    data = json.load(open(BADGE, encoding="utf-8"))
    rings = [[(x, -y) for x, y in sh["points"][:-1]] for sh in data["shapes"]]   # y del CAD hacia arriba
    return _place(_nest(rings), width, center, mirror)
