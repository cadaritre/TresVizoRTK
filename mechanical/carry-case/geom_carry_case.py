"""Geometria del estuche del receptor (carry-case): parametros, utilidades y piezas.

La usan build_carry_case.py y check_carry_case.py. Ejes: origen en el centro de la huella, z 0 = apoyo
de la base, -Y = frente (cierres), +Y = atras (bisagra), +Z arriba. Medidas en mm. Para los perfiles
del frente se usa u = distancia hacia fuera desde la cara exterior (y = -63.5 - u) y v = z - z_union.
"""
import importlib.util, json, math, sys
from pathlib import Path

sys.dont_write_bytecode = True

import FreeCAD as App
import Part

ROOT = Path(__file__).resolve().parent
REPO = ROOT.parent.parent
P = json.loads((ROOT / 'parameters.json').read_text(encoding='utf-8'))
V = App.Vector

BX, BY, RC = P['box']['x'], P['box']['y'], P['box']['corner_radius']
T = P['box']['wall']
ZP = P['box']['z_parting']              # canto de la base
ZL = ZP + P['box']['parting_gap']       # canto de la tapa, cerrada
ZT = P['box']['z_top']
Z_CEIL = ZT - P['box']['top']           # techo por dentro
Z_FLOOR = P['box']['floor']
YF, YB = -BY / 2.0, BY / 2.0

RCV = P['receiver']
XB, YA, ZA = RCV['x_bottom'], RCV['y_axis'], RCV['z_axis']   # el eje del receptor va a lo largo de X
BAY_Y0 = YF + T
BAY_Y1 = BAY_Y0 + P['bay']['width']
BIN_Y0 = BAY_Y1 + P['divider']['thickness']
BIN_Y1 = YB - T
XIN = BX / 2.0 - T                      # cara de dentro de los costados


def rx(z):
    """x del estuche de un z del receptor (a lo largo de su eje)."""
    return XB + z

HG = P['hinge']
HY, HZ = YB + HG['axis_out'], ZP + HG['axis_dz']
LT = P['latch']


# --- Primitivas ----------------------------------------------------------------
def box(x0, x1, y0, y1, z0, z1):
    x0, x1 = sorted((x0, x1))
    y0, y1 = sorted((y0, y1))
    z0, z1 = sorted((z0, z1))
    return Part.makeBox(x1 - x0, y1 - y0, z1 - z0, V(x0, y0, z0))


def cyl_x(r, y, z, x0, x1):
    x0, x1 = sorted((x0, x1))
    return Part.makeCylinder(r, x1 - x0, V(x0, y, z), V(1, 0, 0))


def cyl_y(r, x, z, y0, y1):
    y0, y1 = sorted((y0, y1))
    return Part.makeCylinder(r, y1 - y0, V(x, y0, z), V(0, 1, 0))


def fuse_all(shapes):
    shapes = [s for s in shapes if s is not None]
    if not shapes:
        return None
    return shapes[0] if len(shapes) == 1 else shapes[0].multiFuse(shapes[1:])


def clean(shape):
    shape = shape.removeSplitter()
    solids = [s for s in shape.Solids if s.Volume >= 0.05]
    if len(solids) > 1:
        return Part.makeCompound(solids)
    return solids[0] if solids else shape


def rr_wire(u, z, r=None):
    """Rectangulo redondeado de la huella desplazado u hacia dentro (u < 0: hacia fuera), en z."""
    w, h = BX / 2.0 - u, BY / 2.0 - u
    r = RC - u if r is None else r
    cx, cy = w - r, h - r
    c = math.sqrt(0.5)
    e = [Part.LineSegment(V(-cx, -h, z), V(cx, -h, z)).toShape(),
         Part.Arc(V(cx, -h, z), V(cx + r * c, -cy - r * c, z), V(w, -cy, z)).toShape(),
         Part.LineSegment(V(w, -cy, z), V(w, cy, z)).toShape(),
         Part.Arc(V(w, cy, z), V(cx + r * c, cy + r * c, z), V(cx, h, z)).toShape(),
         Part.LineSegment(V(cx, h, z), V(-cx, h, z)).toShape(),
         Part.Arc(V(-cx, h, z), V(-cx - r * c, cy + r * c, z), V(-w, cy, z)).toShape(),
         Part.LineSegment(V(-w, cy, z), V(-w, -cy, z)).toShape(),
         Part.Arc(V(-w, -cy, z), V(-cx - r * c, -cy - r * c, z), V(-cx, -h, z)).toShape()]
    return Part.Wire(e)


def prism(u, z0, z1, r=None):
    return Part.Face(rr_wire(u, z0, r)).extrude(V(0, 0, z1 - z0))


def ring(u0, u1, z0, z1):
    """Anillo de la huella entre u0 (fuera) y u1 (dentro)."""
    return prism(u0, z0, z1).cut(prism(u1, z0 - 1, z1 + 1))


def edges_at_z(shape, z, tol=1e-6):
    return [e for e in shape.Edges if abs(e.BoundBox.ZMin - z) < tol and abs(e.BoundBox.ZMax - z) < tol]


def poly_face(pts):
    pts = [V(*p) for p in pts]
    return Part.Face(Part.makePolygon(pts + [pts[0]]))


def front_prism(uv, x0, x1):
    """Prisma de un perfil (u, v) del frente, de x0 a x1."""
    x0, x1 = sorted((x0, x1))
    return poly_face([(x0, YF - u, ZP + v) for u, v in uv]).extrude(V(x1 - x0, 0, 0))


def front_cyl(r, u, v, x0, x1):
    return cyl_x(r, YF - u, ZP + v, x0, x1)


def back_prism(yz, x0, x1):
    x0, x1 = sorted((x0, x1))
    return poly_face([(x0, y, z) for y, z in yz]).extrude(V(x1 - x0, 0, 0))


def left_prism(uz, y0, y1):
    """Prisma de un perfil (u, z) del costado izquierdo (x = -BX/2 - u), de y0 a y1."""
    y0, y1 = sorted((y0, y1))
    return poly_face([(-BX / 2.0 - u, y0, z) for u, z in uz]).extrude(V(0, y1 - y0, 0))


def right_prism(uz, y0, y1):
    """Prisma de un perfil (u, z) del costado derecho (x = BX/2 + u), de y0 a y1."""
    y0, y1 = sorted((y0, y1))
    return poly_face([(BX / 2.0 + u, y0, z) for u, z in uz]).extrude(V(0, y1 - y0, 0))


def corner_bumpers(z0, z1, proud, chamfer_bottom=False, chamfer_top=False):
    """Defensas de las cuatro esquinas verticales: la huella crecida `proud` solo en las esquinas
    redondeadas (mas 3 de cada lado), con chaflan de 45 grados abajo o arriba."""
    sh = prism(-proud, z0, z1)
    if chamfer_bottom:
        sh = sh.makeChamfer(proud - 0.05, edges_at_z(sh, z0))
    if chamfer_top:
        sh = sh.makeChamfer(proud - 0.05, edges_at_z(sh, z1))
    sh = sh.cut(prism(0.5, z0 - 1, z1 + 1))
    xs, ys = BX / 2.0 - RC - 3.0, BY / 2.0 - RC - 3.0
    keep = []
    for sx in (-1, 1):
        for sy in (-1, 1):
            keep.append(box(sx * xs, sx * (BX / 2.0 + 5), sy * ys, sy * (BY / 2.0 + 5), z0 - 1, z1 + 1))
    return sh.common(Part.makeCompound(keep))


def latch_pin_span(xl):
    """x de las caras de fuera de las dos costillas que flanquean el cierre centrado en xl."""
    h = LT['width'] / 2.0 + LT['side_gap'] + LT['ear_thickness']
    return xl - h, xl + h


def hull2d(pts):
    pts = sorted(set((round(x, 6), round(y, 6)) for x, y in pts))
    if len(pts) < 3:
        return pts

    def cross(o, a, b):
        return (a[0] - o[0]) * (b[1] - o[1]) - (a[1] - o[1]) * (b[0] - o[0])
    lo, up = [], []
    for p in pts:
        while len(lo) >= 2 and cross(lo[-2], lo[-1], p) <= 0:
            lo.pop()
        lo.append(p)
    for p in reversed(pts):
        while len(up) >= 2 and cross(up[-2], up[-1], p) <= 0:
            up.pop()
        up.append(p)
    return lo[:-1] + up[:-1]


def circle_pts(cx, cy, r, n=48):
    return [(cx + r * math.cos(2 * math.pi * i / n), cy + r * math.sin(2 * math.pi * i / n)) for i in range(n)]


# --- Receptor ------------------------------------------------------------------
def receiver_matrix():
    """Coordenadas del receptor (x, y, z) a las del estuche: X = x_bottom + z, Y = y_axis + x, Z = z_axis + y."""
    return App.Matrix(0, 0, 1, XB,
                      1, 0, 0, YA,
                      0, 1, 0, ZA,
                      0, 0, 0, 1)


def receiver_objects(include_refs=False):
    """[(nombre, etiqueta, forma en el estuche)] de las piezas de la carcasa V3.0 (01 a 10) y, si se pide,
    las de referencia (placa, OLED, etc.)."""
    path = REPO / RCV['fcstd']
    doc = App.openDocument(str(path))
    m = receiver_matrix()
    out = []
    for o in doc.Objects:
        if not hasattr(o, 'Shape') or o.Shape.isNull():
            continue
        name = o.Name.lstrip('_')
        is_part = name[:2].isdigit()
        if not is_part and not (include_refs and name.startswith('ref_')):
            continue
        s = o.Shape.copy()
        s.transformShape(m)
        out.append((name, o.Label, s))
    App.closeDocument(doc.Name)
    return out


def receiver_envelope():
    """Envolvente simple del receptor: bandas (R 29.7 con la cara plana en 24.6), tubo de 28 entre ellas
    y antena de Ø43.5 encima de la tapa."""
    R, flat, rt = RCV['band_radius'], RCV['band_flat'], RCV['tube_radius']
    parts = []
    for z0, z1 in RCV['bands_z']:
        c = cyl_x(R, YA, ZA, rx(z0), rx(z1))
        parts.append(c.cut(box(rx(z0) - 1, rx(z1) + 1, YA - 40, YA + 40, ZA + flat, ZA + 40)))
    z0, z1 = RCV['bands_z'][0][1], RCV['bands_z'][1][0]
    c = cyl_x(rt, YA, ZA, rx(z0), rx(z1))
    parts.append(c.cut(box(rx(z0) - 1, rx(z1) + 1, YA - 40, YA + 40, ZA + 22.9, ZA + 40)))
    L = RCV['length']
    parts.append(cyl_x(RCV['antenna_radius'], YA, ZA, rx(L), rx(L + RCV['antenna_length'])))
    return fuse_all(parts)


# --- Rotulo: logo y letras -------------------------------------------------------
def _logo_module():
    spec = importlib.util.spec_from_file_location('tresvizo_logo', str(REPO / 'hardware' / 'main-board' / 'scripts' / 'logo.py'))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _dedupe(ring_pts, eps=0.02):
    out = []
    for p in ring_pts:
        if not out or math.hypot(p[0] - out[-1][0], p[1] - out[-1][1]) > eps:
            out.append(p)
    if len(out) > 1 and math.hypot(out[0][0] - out[-1][0], out[0][1] - out[-1][1]) <= eps:
        out.pop()
    return out


def text_polys(text, baseline, width=None, cap=None, cx=0.0):
    """Contornos de `text` en Ubuntu Bold, de `width` de ancho o con `cap` de alto de mayuscula,
    centrado en cx y con la linea base en `baseline` (x a la derecha, y hacia atras).
    Devuelve [(contorno, [huecos])]."""
    from matplotlib.textpath import TextPath
    from matplotlib.font_manager import FontProperties
    lb = P['label']
    fp = FontProperties(fname=str(Path(lb['font_dir']) / lb['font']))
    path = TextPath((0, 0), text, size=10.0, prop=fp)
    ext = path.get_extents()
    if width is not None:
        k = width / ext.width
    else:
        k = cap / TextPath((0, 0), 'H', size=10.0, prop=fp).get_extents().height
    xm = (ext.x0 + ext.x1) / 2.0
    rings = []
    for poly in path.to_polygons(closed_only=True):
        r = _dedupe([(cx + (x - xm) * k, baseline + y * k) for x, y in poly])
        if len(r) >= 3:
            rings.append(r)
    return _logo_module()._nest(rings)


def logo_polys():
    lb = P['label']
    lg = _logo_module()
    polys, w, h = lg.full_logo(lb['logo_width'], (0.0, 0.0))
    cx, cy = lb['logo_center']

    def tr(r):
        return _dedupe([(cx + u, cy - v) for u, v in r])     # v del SVG hacia abajo
    return [(tr(o), [tr(hh) for hh in hs]) for o, hs in polys]


def _nearest_on_ring(p, ring_pts):
    best = (1e9, None)
    n = len(ring_pts)
    for i in range(n):
        ax, ay = ring_pts[i]
        bx, by = ring_pts[(i + 1) % n]
        dx, dy = bx - ax, by - ay
        L2 = dx * dx + dy * dy
        t = 0.0 if L2 == 0 else max(0.0, min(1.0, ((p[0] - ax) * dx + (p[1] - ay) * dy) / L2))
        q = (ax + t * dx, ay + t * dy)
        d = math.hypot(p[0] - q[0], p[1] - q[1])
        if d < best[0]:
            best = (d, q)
    return best


def glyph_face(outer, holes):
    wires = []
    for r in [outer] + list(holes):
        pts = [V(x, y, 0) for x, y in r]
        wires.append(Part.makePolygon(pts + [pts[0]]))
    return Part.makeFace(wires, 'Part::FaceMakerBullseye')


def label_groups():
    """[(nombre, poligonos)] del rotulo de la tapa."""
    lb = P['label']
    out = [('logo', logo_polys()),
           ('nombre', text_polys(lb['name'], lb['name_baseline'], width=lb['name_width']))]
    for i, (line, base) in enumerate(zip(lb['subtitle'], lb['subtitle_baselines'])):
        out.append((f'subtitulo {i + 1}', text_polys(line, base, cap=lb['subtitle_cap'])))
    return out


def _offset(face, d):
    """Desplaza la letra d por lado y la vuelve a hacer con poligonos (el desplazamiento con arcos deja
    aristas de micras que luego abren la malla del STL)."""
    if abs(d) < 1e-9:
        return face
    of = face.makeOffset2D(d, 0, False, False, False)
    rings = []
    for w in of.Wires:
        pts = _dedupe([(p.x, p.y) for p in w.discretize(Deflection=0.005)])
        if len(pts) >= 3:
            rings.append(pts)
    outer = max(rings, key=lambda r: abs(sum(r[i - 1][0] * r[i][1] - r[i][0] * r[i - 1][1] for i in range(len(r)))))
    return glyph_face(outer, [r for r in rings if r is not outer])


def label_solids(z0, z1, grow):
    """Prismas del rotulo entre z0 y z1, una pieza por isla (letra, punto de la i, raya del logo),
    desplazados `grow` por lado. Devuelve un compuesto."""
    solids = []
    for name, polys in label_groups():
        for outer, holes in polys:
            f = _offset(glyph_face(outer, holes), grow)
            s = f.extrude(V(0, 0, z1 - z0))
            s.translate(V(0, 0, z0))
            solids.append(s)
    return Part.makeCompound(solids)


def label_face_z():
    """z de la cara del panel rebajado de la tapa, donde van las letras."""
    return ZT - P['label']['panel']['depth']


# --- Base ------------------------------------------------------------------------
def knuckle_ranges(xc):
    """[(x0, x1, 'b' o 't')] de un tramo de bisagra centrado en xc, de fuera hacia dentro (el primero
    lleva la cabeza del perno; el ultimo, la punta partida)."""
    S, n, g = HG['segment_length'], HG['knuckles'], HG['knuckle_gap']
    kl = (S - (n - 1) * g) / n
    out = []
    for i in range(n):
        owner = 'b' if i % 2 == 0 else 't'
        if xc < 0:
            x0 = xc - S / 2.0 + i * (kl + g)
            out.append((x0, x0 + kl, owner))
        else:
            x1 = xc + S / 2.0 - i * (kl + g)
            out.append((x1 - kl, x1, owner))
    return out


def hinge_outer_x(xc):
    return xc - HG['segment_length'] / 2.0 if xc < 0 else xc + HG['segment_length'] / 2.0


def _web_base():
    y0 = YB - 1.0
    zb = HZ - HG['knuckle_radius'] - (HY - y0)
    return [(y0, zb), (y0, ZP), (HY, ZP), (HY, HZ - HG['knuckle_radius'])]


def _web_lid():
    y0 = YB - 1.0
    zt = HZ + HG['knuckle_radius'] + (HY - y0)
    return [(y0, ZL), (HY, ZL), (HY, HZ + HG['knuckle_radius']), (y0, zt)]


def base():
    pb, rim, sl = P['parting_band'], P['rim'], P['seal']
    b = prism(0, 0, ZP)
    b = b.makeFillet(P['box']['bottom_fillet'], edges_at_z(b, 0.0))
    b = b.cut(prism(T, Z_FLOOR, ZP + 1))
    br = P['bottom_recess']
    b = b.cut(prism(br['border'], -1, br['depth'], r=br['radius']))
    for yc in br['skids_y']:
        b = b.fuse(box(br['skid_x'][0], br['skid_x'][1], yc - br['skid_width'] / 2.0, yc + br['skid_width'] / 2.0, 0, br['depth'] + 0.5))
    sp = P['side_panels']
    for sgn in (-1, 1):
        x_out = sgn * BX / 2.0
        pnl = box(x_out - sgn * sp['depth'], x_out + sgn * 2, sp['y'][0], sp['y'][1], sp['z'][0], sp['z'][1])
        pnl = pnl.makeFillet(sp['radius'], [e for e in pnl.Edges if e.BoundBox.XLength > 0.1 and e.BoundBox.YLength < 1e-6 and e.BoundBox.ZLength < 1e-6])
        b = b.cut(pnl)
    band = prism(-pb['proud'], ZP - pb['height'], ZP)
    band = band.makeChamfer(pb['chamfer'], edges_at_z(band, ZP - pb['height']))
    band = band.cut(prism(0.5, ZP - pb['height'] - 1, ZP + 1))
    feats = [band, ring(rim['base_ledge'][0], rim['base_ledge'][1], ZP - rim['base_ledge_height'], ZP)]
    t0, t1 = sl['tongue']
    th = sl['tongue_height']
    feats += [ring(t0, t1, ZP - 0.5, ZP + th - 0.3), ring(t0 + 0.3, t1 - 0.3, ZP + th - 0.31, ZP + th)]

    # Cuna: costillas en U bajo las bandas, contra el tubo entre las bandas y bajo la antena
    cr = P['cradle']
    t = cr['rib_thickness']

    def rib(x0, x1, R, lift):
        """Costilla en U con el circulo de radio R centrado `lift` por encima del eje del receptor."""
        zc = ZA + lift
        r = box(x0, x1, BAY_Y0 - 0.5, BAY_Y1 + 0.5, Z_FLOOR - 0.5, zc + cr['above_axis'])
        return r.cut(cyl_x(R, YA, zc, x0 - 1, x1 + 1))
    c = cr['clearance']
    for z in cr['band_rib_z']:              # la banda apoya en el fondo: centro c mas alto
        feats.append(rib(rx(z) - t / 2.0, rx(z) + t / 2.0, RCV['band_radius'] + c, c))
    c = cr['tube_clearance']
    for z0, z1 in cr['stop_rib_z']:
        feats.append(rib(rx(z0), rx(z1), RCV['tube_radius'] + c, c / 2.0))
    c = cr['antenna_clearance']
    za_ = cr['antenna_rib_z']
    feats.append(rib(rx(za_) - t / 2.0, rx(za_) + t / 2.0, RCV['antenna_radius'] + c, c / 2.0))

    # Tabique entre el receptor y el compartimento de extras, con muesca para los dedos
    dv = P['divider']
    div = box(-XIN - 0.5, XIN + 0.5, BAY_Y1, BIN_Y0, Z_FLOOR - 0.5, ZP)
    nx0, nx1 = rx(dv['notch_z_rcv'][0]), rx(dv['notch_z_rcv'][1])
    nz, nr = dv['notch_z'], dv['notch_radius']
    notch = fuse_all([box(nx0 + nr, nx1 - nr, BAY_Y1 - 1, BIN_Y0 + 1, nz, ZP + 1),
                      box(nx0, nx1, BAY_Y1 - 1, BIN_Y0 + 1, nz + nr, ZP + 1),
                      cyl_y(nr, nx0 + nr, nz + nr, BAY_Y1 - 1, BIN_Y0 + 1),
                      cyl_y(nr, nx1 - nr, nz + nr, BAY_Y1 - 1, BIN_Y0 + 1)])
    feats.append(div.cut(notch))

    # Tabique bajo del compartimento de extras con las ranuras de las microSD
    ex = P['extras']
    ct = ex['cross_thickness'] / 2.0
    ztop = Z_FLOOR + ex['cross_height']
    xc = ex['cross_x']
    cross = box(xc - ct, xc + ct, BIN_Y0 - 0.5, BIN_Y1 + 0.5, Z_FLOOR - 0.5, ztop)
    ym = (BIN_Y0 + BIN_Y1) / 2.0
    n = ex['microsd_count']
    for i in range(n):
        yc = ym + (i - (n - 1) / 2.0) * ex['microsd_pitch']
        cross = cross.cut(box(xc - ex['microsd_slot'] / 2.0, xc + ex['microsd_slot'] / 2.0,
                              yc - ex['microsd_width'] / 2.0, yc + ex['microsd_width'] / 2.0,
                              ztop - ex['microsd_depth'], ztop + 1))
    feats.append(cross)

    # Bisagra: nudillos de la base con sus almas
    rk = HG['knuckle_radius']
    for xc in HG['segment_x']:
        for x0, x1, owner in knuckle_ranges(xc):
            if owner == 'b':
                feats += [cyl_x(rk, HY, HZ, x0, x1), back_prism(_web_base(), x0, x1)]

    # Costillas: las de los cierres (sus orejas), costados, atras (bajo las bisagras) y bajo el candado
    rb = P['ribs']
    rw, rp = rb['width'], rb['proud']
    zb0 = 3.0 - ZP                                     # v del pie de las costillas
    pu, pv, R = LT['pivot_u'], LT['pivot_v'], LT['barrel_radius']
    ear_uv = [(-0.8, zb0), (rp + 0.5, zb0), (pu + 4.5, pv - 9.0), (pu + 4.5, pv + 4.0), (pu + 1.0, -P['parting_band']['height']),
              (-0.8, -P['parting_band']['height'])]
    for xl in LT['x_centers']:
        for side in (-1, 1):
            xin = xl + side * (LT['width'] / 2.0 + LT['side_gap'])
            feats.append(front_prism(ear_uv, xin, xin + side * LT['ear_thickness']))
    plain = [(-0.8, zb0), (rp, zb0), (rp, -P['parting_band']['height'] - rp), (-0.8, -P['parting_band']['height'])]
    pl = P['padlock']
    xpc = sum(pl['tab_x_base']) / 2.0
    feats.append(front_prism(plain, xpc - rw / 2.0, xpc + rw / 2.0))
    for yc in rb['side_y']:
        for sgn in (-1, 1):
            uz = [(u, ZP + v) for u, v in plain]
            if sgn < 0:
                feats.append(left_prism(uz, yc - rw / 2.0, yc + rw / 2.0))
            else:
                feats.append(right_prism(uz, yc - rw / 2.0, yc + rw / 2.0))
    yw = YB - 0.8
    for xc in rb['back_x']:
        zw = HZ - HG['knuckle_radius'] - (HY - (YB + rp)) + 0.6
        feats.append(back_prism([(yw, 3.0), (YB + rp, 3.0), (YB + rp, zw), (yw, zw - rp - 0.8)], xc - rw / 2.0, xc + rw / 2.0))
    feats.append(corner_bumpers(4.0, ZP - P['parting_band']['height'], rb['corner_proud'], chamfer_bottom=True))

    # Oreja del candado
    x0, x1 = pl['tab_x_base']
    feats.append(front_prism([(-0.8, -11.0), (-0.8, 0.0), (2.0, 0.0), (2.0, 7.5), (pl['u'], 7.5),
                              (pl['u'], -7.0), (3.2, -7.0)], x0, x1))

    b = b.fuse(feats)

    # Argolla del costado (despues de los paneles rebajados)
    ly = P['lanyard']
    lu, lzb = ly['u'], ly['z_below_parting']
    loop = left_prism([(-0.9, ZP - lzb - 0.1), (-0.9, ZP), (lu, ZP), (lu, ZP - lzb + lu + 0.9)], ly['y'][0], ly['y'][1])
    su0, su1 = ly['slot_u']
    loop = loop.cut(box(-BX / 2.0 - su1, -BX / 2.0 - su0, ly['slot_y'][0], ly['slot_y'][1], ZP - lzb - 5, ZP + 1))
    b = b.fuse(loop)

    # Agujeros: pernos de la bisagra (con el rebaje de la cabeza y el de la punta), de los cierres y candado
    holes = []
    for xc in HG['segment_x']:
        kr = knuckle_ranges(xc)
        xo = hinge_outer_x(xc)
        sgn = 1 if xc < 0 else -1          # hacia dentro
        xi = xo + sgn * HG['segment_length']
        for i, (x0, x1, owner) in enumerate(kr):
            if owner == 'b':
                holes.append(cyl_x(HG['bore_base'] / 2.0, HY, HZ, x0 - 0.01, x1 + 0.01))
        hp = HG['pin_head_h'] + HG['head_pocket_clear']
        holes.append(cyl_x(HG['pin_head_d'] / 2.0 + HG['head_pocket_clear'], HY, HZ, xo - sgn * 1, xo + sgn * hp))
        holes.append(cyl_x(HG['barb_pocket_d'] / 2.0, HY, HZ, xi - sgn * HG['barb_pocket_h'], xi + sgn * 1))
    for xl in LT['x_centers']:
        x0l, x1l = latch_pin_span(xl)
        holes.append(front_cyl(LT['bore'] / 2.0, pu, pv, x0l - 1, x1l + 1))
    holes.append(front_cyl(pl['hole'] / 2.0, pl['hole_u'], P['box']['parting_gap'] / 2.0, x0 - 1, x1 + 1))
    b = b.cut(Part.makeCompound(holes))
    return clean(b)


# --- Tapa ----------------------------------------------------------------------------
def lid():
    pb, rim, sl, lc = P['parting_band'], P['rim'], P['seal'], P['liner']
    t = prism(0, ZL, ZT)
    t = t.makeFillet(P['box']['top_fillet'], edges_at_z(t, ZT))
    t = t.cut(prism(T, ZL - 1, Z_CEIL))
    band = prism(-pb['proud'], ZL, ZL + pb['height'])
    band = band.makeChamfer(pb['chamfer'], edges_at_z(band, ZL + pb['height']))
    band = band.cut(prism(0.5, ZL - 1, ZL + pb['height'] + 1))
    feats = [band, ring(rim['lid_ledge'][0], rim['lid_ledge'][1], ZL, ZL + rim['lid_ledge_height'])]

    # Topes de los cierres
    ku, (kv0, kv1), kc = LT['keeper_u'], LT['keeper_v'], LT['keeper_corner']
    keeper = [(-0.8, kv0), (ku - 0.3, kv0), (ku, kv0 + 0.3), (ku, kv1 - kc), (ku - kc, kv1), (-0.8, LT['keeper_inner_top_v'])]
    for xl in LT['x_centers']:
        feats.append(front_prism(keeper, xl - LT['keeper_width'] / 2.0, xl + LT['keeper_width'] / 2.0))

    # Bisagra: nudillos de la tapa
    rk = HG['knuckle_radius']
    for xc in HG['segment_x']:
        for x0, x1, owner in knuckle_ranges(xc):
            if owner == 't':
                feats += [cyl_x(rk, HY, HZ, x0, x1), back_prism(_web_lid(), x0, x1)]

    # Oreja del candado (simetrica a la de la base respecto al eje del agujero)
    pl = P['padlock']
    x0, x1 = pl['tab_x_lid']
    g = P['box']['parting_gap']
    feats.append(front_prism([(-0.8, g + 11.0), (-0.8, g), (2.0, g), (2.0, g - 7.5), (pl['u'], g - 7.5),
                              (pl['u'], g + 7.0), (3.2, g + 7.0)], x0, x1))

    # Costillas de la tapa (alineadas con las de la base) y defensas de las esquinas
    rb = P['ribs']
    rw, lp = rb['width'], rb['lid_proud']
    z0r, z1r = ZL + pb['height'] - 0.5, ZT - P['box']['top_fillet'] - 1.0
    rib_uz = [(-0.8, z0r), (lp, z0r), (lp, z1r - lp), (-0.8, z1r + 0.8)]
    rib_uv = [(u, z - ZP) for u, z in rib_uz]
    for xl in LT['x_centers']:
        for side in (-1, 1):
            xin = xl + side * (LT['width'] / 2.0 + LT['side_gap'])
            feats.append(front_prism(rib_uv, xin, xin + side * LT['ear_thickness']))
    for yc in rb['lid_side_y']:
        feats.append(left_prism(rib_uz, yc - rw / 2.0, yc + rw / 2.0))
        feats.append(right_prism(rib_uz, yc - rw / 2.0, yc + rw / 2.0))
    for xc in rb['lid_back_x']:
        feats.append(back_prism([(YB - 0.8, z0r), (YB + lp, z0r), (YB + lp, z1r - lp), (YB - 0.8, z1r + 0.8)], xc - rw / 2.0, xc + rw / 2.0))
    feats.append(corner_bumpers(ZL + pb['height'] - 0.5, ZT - P['box']['top_fillet'] - 0.5, rb['corner_proud'], chamfer_top=True))

    # Topes que sujetan el forro de TPU
    nr, nl = lc['nub_radius'], lc['nub_length']
    nz = Z_CEIL - lc['thickness'] - nr - 0.1
    for xc in lc['nub_x']:
        for yw in (YF + T, YB - T):
            feats.append(cyl_x(nr, yw, nz, xc - nl / 2.0, xc + nl / 2.0))
    for xw in (-BX / 2.0 + T, BX / 2.0 - T):
        feats.append(cyl_y(nr, xw, nz, -nl / 2.0, nl / 2.0))

    t = t.fuse(feats)
    holes = [ring(sl['groove'][0], sl['groove'][1], ZL - 1, ZL + sl['groove_depth'])]
    for xc in HG['segment_x']:
        for x0, x1, owner in knuckle_ranges(xc):
            if owner == 't':
                holes.append(cyl_x(HG['bore_lid'] / 2.0, HY, HZ, x0 - 0.01, x1 + 0.01))
    holes.append(front_cyl(pl['hole'] / 2.0, pl['hole_u'], g / 2.0, x0 - 1, x1 + 1))
    pn = P['label']['panel']
    (pw, ph), (pcx, pcy) = pn['size'], pn['center']
    panel = box(pcx - pw / 2.0, pcx + pw / 2.0, pcy - ph / 2.0, pcy + ph / 2.0, ZT - pn['depth'], ZT + 1)
    panel = panel.makeFillet(pn['radius'], [e for e in panel.Edges if e.BoundBox.ZLength > 0.1 and e.BoundBox.XLength < 1e-6 and e.BoundBox.YLength < 1e-6])
    holes.append(panel)
    lb = P['label']
    zf = label_face_z()
    holes.append(label_solids(zf - lb['pocket_depth'], ZT + 0.5, lb['pocket_clearance']))
    t = t.cut(Part.makeCompound(holes))
    return clean(t)


# --- Cierre ----------------------------------------------------------------------------
def latch(xc, angle=0.0):
    """Cierre centrado en xc; angle > 0 lo abre (la parte de arriba hacia fuera)."""
    pu, pv, R = LT['pivot_u'], LT['pivot_v'], LT['barrel_radius']
    hv, ht, tu, ch = LT['hook_v'], LT['hook_thickness'], LT['hook_tip_u'], LT['hook_chamfer']
    p0, pt, pv0 = LT['plate_u'], LT['plate_thickness'], LT['plate_v0']
    top = hv + ht
    x0, x1 = xc - LT['width'] / 2.0, xc + LT['width'] / 2.0
    parts = [front_cyl(R, pu, pv, x0, x1),
             front_prism([(p0, pv0), (p0 + pt, pv0), (p0 + pt, top), (p0, top)], x0, x1),
             front_prism([(tu + ch, hv), (p0 + pt, hv), (p0 + pt, top), (tu, top), (tu, hv + ch)], x0, x1),
             front_prism([(p0, top - 0.1), (p0, top + LT['lip_height']), (LT['lip_u'] - 0.5, top + LT['lip_height']),
                          (LT['lip_u'], top + LT['lip_height'] - 0.5), (LT['lip_u'], top - 0.1), (p0 + pt, top - 1.6)], x0, x1),
             front_prism(hull2d(circle_pts(pu, pv, R) + [(p0, pv0), (p0 + pt, pv0), (p0, pv0 + 3), (p0 + pt, pv0 + 3)]), x0, x1)]
    s = fuse_all(parts).cut(front_cyl(LT['bore'] / 2.0, pu, pv, x0 - 1, x1 + 1))
    s = clean(s)
    if angle:
        s.rotate(V(0, YF - pu, ZP + pv), V(1, 0, 0), angle)
    return s


# --- Junta de TPU -------------------------------------------------------------------------
def seal():
    sl = P['seal']
    g0, g1 = sl['groove']
    zs1 = ZL + sl['groove_depth']
    zs0 = zs1 - sl['strip_thickness']
    strip = ring(g0, g1, zs0, zs1)
    a = math.radians(sl['lip_tilt_deg'])
    L = sl['lip_length']
    tip_u = sl['lip_tip_u']
    z_tip = zs0 - L * math.cos(a)
    th = sl['lip_thickness'] / math.cos(a) / 2.0      # medio espesor en horizontal

    def u_at(z):
        return tip_u + (z - z_tip) * math.tan(a)
    zr = zs0 + 0.3
    outer = Part.makeLoft([rr_wire(u_at(zr) - th, zr), rr_wire(tip_u - th, z_tip)], True, True)
    inner = Part.makeLoft([rr_wire(u_at(zr) + th, zr + 0.01), rr_wire(tip_u + th, z_tip - 0.01)], True, True)
    return clean(strip.fuse(outer.cut(inner)))


# --- Forro de TPU con las letras ------------------------------------------------------------
def liner_pads():
    lc = P['liner']
    R = RCV['band_radius'] - lc['pad_squeeze']
    zb = Z_CEIL - lc['thickness']
    pads = []
    for z0, z1 in lc['pad_z_rcv']:
        x0, x1 = rx(z0), rx(z1)
        pad = box(x0, x1, YA - 27.0, YA + 27.0, lc['pad_z_min'], zb + 0.2)
        pad = pad.cut(cyl_x(R, YA, ZA, x0 - 1, x1 + 1))
        pad = pad.cut(box(x0 - 1, x1 + 1, YA - lc['pad_x_clear'], YA + lc['pad_x_clear'], 0, 100))
        pads.append(pad)
    return fuse_all(pads)


def liner(with_pads=True):
    lc = P['liner']
    s = prism(T + lc['clearance'], Z_CEIL - lc['thickness'], Z_CEIL)
    if with_pads:
        s = s.fuse(liner_pads())
    return clean(s)


def letters():
    """Letras y logo de TPU para meter en los huecos de la tapa: tantos solidos como islas tiene el
    rotulo, a ras de la cara del panel."""
    lb = P['label']
    zf = label_face_z()
    return label_solids(zf - lb['pocket_depth'], zf, -lb['inlay_clearance'])


# --- Pernos impresos (PA12) ------------------------------------------------------------------
def snap_pin(y, z, x_head, sgn, d, length, head_d, head_h, barb_d, barb_len, slot_w, slot_len):
    """Perno a lo largo de X: cabeza desde x_head hacia sgn, cana de `length` desde la cabeza con la
    punta partida por una ranura y una uña conica que se cierra al pasar por los agujeros y se abre al
    salir."""
    xh1 = x_head + sgn * head_h
    xt = xh1 + sgn * length
    xl = xt - sgn * barb_len
    pin = cyl_x(head_d / 2.0, y, z, x_head, xh1).fuse([
        cyl_x(d / 2.0, y, z, xh1 - sgn * 0.1, xl + sgn * 0.01),
        Part.makeCone(barb_d / 2.0, d / 2.0 - 0.3, barb_len, V(xl, y, z), V(sgn, 0, 0))])
    slot = box(xt - sgn * slot_len, xt + sgn * 1.0, y - slot_w / 2.0, y + slot_w / 2.0, z - barb_d, z + barb_d)
    return clean(pin.cut(slot))


def hinge_pin(xc):
    """Perno de la bisagra del tramo centrado en xc, puesto: cabeza en el rebaje del nudillo de fuera,
    uña 0.2 pasada del escalon del rebaje del nudillo de dentro."""
    xo = hinge_outer_x(xc)
    sgn = 1 if xc < 0 else -1
    hp = HG['pin_head_h'] + HG['head_pocket_clear']
    length = HG['segment_length'] - 0.3 - hp
    return snap_pin(HY, HZ, xo + sgn * HG['head_pocket_clear'], sgn, HG['pin_d'], length, HG['pin_head_d'],
                    HG['pin_head_h'], HG['barb_d'], HG['barb_len'], HG['slot_w'], HG['slot_len'])


def latch_pin(xl):
    """Perno del cierre centrado en xl, puesto: cabeza contra la costilla del lado del centro del
    estuche, uña 0.2 pasada de la cara de fuera de la otra costilla."""
    x0, x1 = latch_pin_span(xl)
    pu, pv = LT['pivot_u'], LT['pivot_v']
    if xl < 0:
        xh, sgn, span = x1, -1, x1 - x0
    else:
        xh, sgn, span = x0, 1, x1 - x0
    xh -= sgn * LT['pin_head_h']
    return snap_pin(YF - pu, ZP + pv, xh, sgn, LT['pin_d'], span + 0.2 + LT['barb_len'], LT['pin_head_d'],
                    LT['pin_head_h'], LT['barb_d'], LT['barb_len'], LT['slot_w'], LT['slot_len'])


def lid_rotation(shape, deg):
    """Gira una pieza de la tapa `deg` grados sobre el eje de la bisagra (deg > 0 abre)."""
    s = shape.copy()
    s.rotate(V(0, HY, HZ), V(1, 0, 0), -deg)
    return s
