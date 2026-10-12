"""Convierte el logo vectorial en DXF a los mismos contornos que consume el
generador, sin depender del importador de ningun CAD.

Evalua las SPLINE con de Boor y desarrolla las LWPOLYLINE, incluidos sus bulges.
Despues encadena los tramos sueltos en lazos cerrados y clasifica el anidamiento
por profundidad, igual que trace_logo.py, de modo que el glifo no se borre al
reconstruir.

Salida: logo.json, compatible con build_v2.py.
"""
import argparse, json, math, pathlib

# --- Lectura del DXF --------------------------------------------------------

def read_pairs(path):
    lines = path.read_text(encoding='utf-8', errors='replace').splitlines()
    pairs, i = [], 0
    while i < len(lines) - 1:
        code = lines[i].strip()
        if code.lstrip('-').isdigit():
            pairs.append((int(code), lines[i + 1].rstrip('\r')))
            i += 2
        else:
            i += 1
    return pairs


def entities(pairs):
    """Trocea la seccion ENTITIES en entidades con sus pares de grupo."""
    start = end = None
    for index, (code, value) in enumerate(pairs):
        if code == 2 and value.strip() == 'ENTITIES' and start is None:
            start = index
        elif start is not None and code == 0 and value.strip() == 'ENDSEC':
            end = index
            break
    out, current = [], None
    for code, value in pairs[start:end]:
        if code == 0:
            if current:
                out.append(current)
            current = {'type': value.strip(), 'pairs': []}
        elif current:
            current['pairs'].append((code, value))
    if current:
        out.append(current)
    return [e for e in out if e['type'] in ('SPLINE', 'LWPOLYLINE', 'LINE', 'ARC', 'CIRCLE')]


def grouped(entity, *codes):
    return [v for c, v in entity['pairs'] if c in codes]


# --- Evaluacion de curvas ---------------------------------------------------

def de_boor(t, degree, knots, points, weights):
    """Punto de una B-spline racional en el parametro t."""
    n = len(points)
    span = degree
    while span < n - 1 and knots[span + 1] <= t:
        span += 1
    d = [(points[span - degree + j][0] * weights[span - degree + j],
          points[span - degree + j][1] * weights[span - degree + j],
          weights[span - degree + j]) for j in range(degree + 1)]
    for r in range(1, degree + 1):
        for j in range(degree, r - 1, -1):
            i = span - degree + j
            denom = knots[i + degree - r + 1] - knots[i]
            a = 0.0 if abs(denom) < 1e-12 else (t - knots[i]) / denom
            d[j] = tuple(d[j - 1][k] * (1 - a) + d[j][k] * a for k in range(3))
    x, y, w = d[degree]
    return (x / w, y / w) if abs(w) > 1e-12 else (x, y)


def spline_points(entity, samples_per_span):
    degree = int(float(grouped(entity, 71)[0])) if grouped(entity, 71) else 3
    knots = [float(v) for v in grouped(entity, 40)]
    weights = [float(v) for v in grouped(entity, 41)]
    xs = [float(v) for v in grouped(entity, 10)]
    ys = [float(v) for v in grouped(entity, 20)]
    ctrl = list(zip(xs, ys))
    if not ctrl:
        # Sin puntos de control: usar los de ajuste tal cual.
        fx = [float(v) for v in grouped(entity, 11)]
        fy = [float(v) for v in grouped(entity, 21)]
        return list(zip(fx, fy))
    if len(weights) != len(ctrl):
        weights = [1.0] * len(ctrl)
    if len(knots) != len(ctrl) + degree + 1:
        # Nudos uniformes sujetos si el archivo no los trae completos.
        inner = len(ctrl) - degree - 1
        knots = ([0.0] * (degree + 1) +
                 [(k + 1) / (inner + 1) for k in range(inner)] +
                 [1.0] * (degree + 1))
    t0, t1 = knots[degree], knots[len(ctrl)]
    total = max(samples_per_span * max(1, len(ctrl) - degree), 8)
    return [de_boor(t0 + (t1 - t0) * i / total, degree, knots, ctrl, weights)
            for i in range(total + 1)]


def polyline_points(entity, arc_step_deg):
    xs = [float(v) for c, v in entity['pairs'] if c == 10]
    ys = [float(v) for c, v in entity['pairs'] if c == 20]
    bulges = {}
    index = -1
    for code, value in entity['pairs']:
        if code == 10:
            index += 1
        elif code == 42:
            bulges[index] = float(value)
    closed = any(c == 70 and int(float(v)) & 1 for c, v in entity['pairs'])
    verts = list(zip(xs, ys))
    out = []
    count = len(verts)
    for i in range(count if closed else count - 1):
        a, b = verts[i], verts[(i + 1) % count]
        out.append(a)
        bulge = bulges.get(i, 0.0)
        if abs(bulge) > 1e-9:
            # Bulge es tan(theta/4); desarrollar el arco entre a y b.
            theta = 4 * math.atan(bulge)
            chord = math.hypot(b[0] - a[0], b[1] - a[1])
            if chord > 1e-9 and abs(math.sin(theta / 2)) > 1e-9:
                radius = chord / (2 * math.sin(theta / 2))
                mx, my = (a[0] + b[0]) / 2, (a[1] + b[1]) / 2
                dx, dy = (b[0] - a[0]) / chord, (b[1] - a[1]) / chord
                h = math.sqrt(max(radius * radius - (chord / 2) ** 2, 0.0))
                sign = 1 if theta > 0 else -1
                cx, cy = mx - dy * h * sign, my + dx * h * sign
                a0 = math.atan2(a[1] - cy, a[0] - cx)
                steps = max(2, int(abs(math.degrees(theta)) / arc_step_deg))
                for s in range(1, steps):
                    ang = a0 + theta * s / steps
                    out.append((cx + abs(radius) * math.cos(ang),
                                cy + abs(radius) * math.sin(ang)))
    if not closed:
        out.append(verts[-1])
    return out, closed


# --- Encadenado en lazos ----------------------------------------------------

def chain(segments, tolerance):
    """Une tramos sueltos en lazos cerrados por proximidad de extremos."""
    remaining = [list(s) for s in segments if len(s) >= 2]
    loops = []
    while remaining:
        loop = remaining.pop(0)
        changed = True
        while changed:
            changed = False
            if math.dist(loop[0], loop[-1]) <= tolerance and len(loop) > 2:
                break
            for index, candidate in enumerate(remaining):
                for cand in (candidate, candidate[::-1]):
                    if math.dist(loop[-1], cand[0]) <= tolerance:
                        loop.extend(cand[1:])
                        remaining.pop(index)
                        changed = True
                        break
                if changed:
                    break
        loops.append(loop)
    return loops


def area(points):
    return 0.5 * sum(points[i][0] * points[(i + 1) % len(points)][1] -
                     points[(i + 1) % len(points)][0] * points[i][1]
                     for i in range(len(points)))


def inside(point, polygon):
    x, y = point
    result = False
    for k in range(len(polygon)):
        x0, y0 = polygon[k]
        x1, y1 = polygon[(k + 1) % len(polygon)]
        if (y0 > y) != (y1 > y) and x < (x1 - x0) * (y - y0) / (y1 - y0) + x0:
            result = not result
    return result


def simplify(points, epsilon):
    """Ramer-Douglas-Peucker iterativo."""
    if len(points) < 3 or epsilon <= 0:
        return points
    keep = [False] * len(points)
    keep[0] = keep[-1] = True
    stack = [(0, len(points) - 1)]
    while stack:
        a, b = stack.pop()
        if b <= a + 1:
            continue
        x0, y0 = points[a]
        x1, y1 = points[b]
        dx, dy = x1 - x0, y1 - y0
        norm = math.hypot(dx, dy)
        best, best_d = -1, epsilon
        for i in range(a + 1, b):
            px, py = points[i]
            d = (abs(dx * (y0 - py) - (x0 - px) * dy) / norm) if norm > 1e-12 \
                else math.hypot(px - x0, py - y0)
            if d > best_d:
                best, best_d = i, d
        if best > 0:
            keep[best] = True
            stack.extend([(a, best), (best, b)])
    return [p for p, k in zip(points, keep) if k]


ap = argparse.ArgumentParser(description=__doc__)
ap.add_argument('dxf', type=pathlib.Path)
ap.add_argument('--out', type=pathlib.Path,
                default=pathlib.Path(__file__).parent / 'logo.json')
ap.add_argument('--samples-per-span', type=int, default=12)
ap.add_argument('--arc-step-deg', type=float, default=6.0)
# Tolerancia relativa al ancho del dibujo; 0.0015 sobre 69 mm es ~0.1 mm.
ap.add_argument('--simplify-rel', type=float, default=0.0015)
ap.add_argument('--join-rel', type=float, default=0.004)
args = ap.parse_args()

ents = entities(read_pairs(args.dxf))
segments, closed_loops = [], []
for e in ents:
    if e['type'] == 'SPLINE':
        pts = spline_points(e, args.samples_per_span)
        if len(pts) >= 2:
            (closed_loops if math.dist(pts[0], pts[-1]) < 1e-6 else segments).append(pts)
    elif e['type'] == 'LWPOLYLINE':
        pts, closed = polyline_points(e, args.arc_step_deg)
        if len(pts) >= 2:
            (closed_loops if closed else segments).append(pts)

xs = [p[0] for s in segments + closed_loops for p in s]
ys = [p[1] for s in segments + closed_loops for p in s]
width_dxf = max(xs) - min(xs)
loops = closed_loops + chain(segments, args.join_rel * width_dxf)
loops = [simplify(l, args.simplify_rel * width_dxf) for l in loops]
loops = [l for l in loops if len(l) >= 3 and abs(area(l)) > (0.0005 * width_dxf ** 2)]
loops.sort(key=lambda l: -abs(area(l)))

xs = [p[0] for l in loops for p in l]
ys = [p[1] for l in loops for p in l]
width = max(xs) - min(xs)
height = max(ys) - min(ys)
cx, cy = (max(xs) + min(xs)) / 2, (max(ys) + min(ys)) / 2

shapes = []
for index, loop in enumerate(loops):
    depth = sum(1 for other in loops[:index] if inside(loop[0], other))
    shapes.append({
        'depth': depth,
        'hole': bool(depth % 2),
        'points': [[round((x - cx) / width, 6), round((y - cy) / width, 6)]
                   for x, y in loop],
    })
shapes.sort(key=lambda s: s['depth'])

data = {
    'source': str(args.dxf).replace('\\', '/'),
    'units': 'normalizado; multiplicar por el ancho deseado del distintivo en mm',
    'aspect_h_over_w': round(height / width, 6),
    'badge_px': [round(width, 3), round(height, 3)],
    'tolerance_px': args.simplify_rel * width_dxf,
    'shapes': shapes,
}
args.out.write_text(json.dumps(data, indent=1), encoding='utf-8')

levels = {}
for s in shapes:
    levels[s['depth']] = levels.get(s['depth'], 0) + 1
print(f'entidades leidas: {len(ents)}  ({sum(1 for e in ents if e["type"]=="SPLINE")} splines)')
print(f'distintivo: {width:.3f} x {height:.3f} unidades, relacion h/w {height/width:.4f}')
print('contornos por profundidad:', dict(sorted(levels.items())),
      f'({sum(len(s["points"]) for s in shapes)} vertices)')
print('escrito:', args.out)
