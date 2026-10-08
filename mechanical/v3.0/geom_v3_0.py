"""Geometria comun de la carcasa V3.0: parametros, utilidades y piezas de referencia.

La usan build_v3_0.py, export_v3_0.py y check_v3_0.py. Ejes de V2.x: z = eje del baston hacia
arriba, +Y al frente (cara plana), +X a la izquierda mirando el frente. Medidas en mm.
"""
import json, math, sys
from pathlib import Path

# Sin __pycache__: importa carrier_bdlx.py de hardware/main-board/cad, que no es de esta carpeta.
sys.dont_write_bytecode = True

import FreeCAD as App
import Part

ROOT = Path(__file__).resolve().parent
REPO = ROOT.parent.parent
MB_CAD = REPO / 'hardware' / 'main-board' / 'cad'
PLUGS_JSON = REPO / 'hardware' / 'main-board' / 'kicad' / 'plugs.json'
P = json.loads((ROOT / 'parameters.json').read_text(encoding='utf-8'))
V = App.Vector

TB, HOL = P['tubo'], P['holguras']
RO = TB['radio_exterior']
RI = RO - TB['pared']
Y_FLAT_O, Y_FLAT_I, X_FLAT = TB['plano_y_exterior'], TB['plano_y_interior'], TB['plano_x']
H_TOTAL, R_ROUND = TB['alto_total'], TB['redondeo']
Z_TUBE0, Z_TUBE1 = TB['z_base'], TB['z_tapa']
CLR = HOL['general']


# --- Primitivas ----------------------------------------------------------------
def box(x0, x1, y0, y1, z0, z1):
    x0, x1 = sorted((x0, x1))
    y0, y1 = sorted((y0, y1))
    z0, z1 = sorted((z0, z1))
    return Part.makeBox(x1 - x0, y1 - y0, z1 - z0, V(x0, y0, z0))


def cyl_z(r, x, y, z0, z1):
    return Part.makeCylinder(r, z1 - z0, V(x, y, z0), V(0, 0, 1))


def cyl_y(r, x, z, y0, y1):
    return Part.makeCylinder(r, y1 - y0, V(x, y0, z), V(0, 1, 0))


def cyl_x(r, y, z, x0, x1):
    return Part.makeCylinder(r, x1 - x0, V(x0, y, z), V(1, 0, 0))


def sector(r_out, r_in, z0, z1, a0, a1):
    """Sector anular entre los angulos a0 y a1 (grados, desde +X hacia +Y)."""
    sweep = (a1 - a0) % 360.0 or 360.0
    s = Part.makeCylinder(r_out, z1 - z0, V(0, 0, z0), V(0, 0, 1), sweep)
    if r_in > 0:
        s = s.cut(Part.makeCylinder(r_in, z1 - z0 + 2, V(0, 0, z0 - 1), V(0, 0, 1), sweep))
    s.rotate(V(), V(0, 0, 1), a0)
    return s


def fuse_all(shapes):
    shapes = [s for s in shapes if s is not None]
    if not shapes:
        return None
    if len(shapes) == 1:
        return shapes[0]
    return shapes[0].multiFuse(shapes[1:])


def clean(shape):
    shape = shape.removeSplitter()
    solids = [s for s in shape.Solids if s.Volume >= 0.05]
    if len(solids) > 1:
        return Part.makeCompound(solids)
    return solids[0] if solids else shape


def polar(r, a_deg):
    a = math.radians(a_deg)
    return r * math.cos(a), r * math.sin(a)


def tube_path(points, d):
    """Cable de diametro d por una poligonal: cilindros y esferas en los quiebres."""
    r = d / 2.0
    parts = [Part.makeSphere(r, V(*points[0]))]
    for a, b in zip(points[:-1], points[1:]):
        va, vb = V(*a), V(*b)
        L = (vb - va).Length
        if L > 1e-6:
            parts.append(Part.makeCylinder(r, L, va, vb - va))
        parts.append(Part.makeSphere(r, vb))
    return fuse_all(parts)


# --- Envolventes del tubo --------------------------------------------------------
def outer_envelope():
    """Exterior completo z 0-100: R26, redondeos R4 arriba y abajo, cara plana en y 22.13."""
    rr, h, ro = R_ROUND, H_TOTAL, RO
    c = ro - rr
    s45 = math.sqrt(0.5)
    e = [Part.LineSegment(V(0, 0, 0), V(c, 0, 0)),
         Part.Arc(V(c, 0, 0), V(c + rr * s45, 0, rr - rr * s45), V(ro, 0, rr)),
         Part.LineSegment(V(ro, 0, rr), V(ro, 0, h - rr)),
         Part.Arc(V(ro, 0, h - rr), V(c + rr * s45, 0, h - rr + rr * s45), V(c, 0, h)),
         Part.LineSegment(V(c, 0, h), V(0, 0, h)),
         Part.LineSegment(V(0, 0, h), V(0, 0, 0))]
    face = Part.Face(Part.Wire([seg.toShape() for seg in e]))
    solid = face.revolve(V(0, 0, 0), V(0, 0, 1), 360)
    solid = Part.Solid(solid) if solid.ShapeType == 'Shell' else solid
    return solid.cut(box(-50, 50, Y_FLAT_O, 50, -1, h + 1)).Solids[0]


def interior(z0, z1, inset=0.0):
    """Hueco interior del tubo, reducido `inset` hacia dentro.

    En |x| <= 13.65 llega hasta la cara plana interior (y 20.33); fuera de esa franja sigue el
    circulo de r 24.2 (con el escalon de 0.35 en |x| 13.65 de la especificacion). Al circulo se le
    quita antes el casquete delante de la cara plana: si no, en |x| < 9.79 el hueco pasa de la cara
    plana exterior (y 22.13) y el frente queda abierto.
    """
    r = RI - inset
    xf, yf = X_FLAT - inset, Y_FLAT_I - inset
    c = cyl_z(r, 0, 0, z0, z1).cut(box(-xf, xf, yf, r + 1, z0 - 1, z1 + 1))
    flat = box(-xf, xf, 0, yf, z0, z1)
    return c.fuse(flat).removeSplitter()


def cavity_face(z=0.0):
    """Seccion del hueco interior en el plano z (la misma regla que interior())."""
    circle = Part.Face(Part.Wire(Part.makeCircle(RI, V(0, 0, z))))
    front = box(-X_FLAT, X_FLAT, Y_FLAT_I, RI + 1, z - 1, z + 1)
    flat = Part.Face(Part.makePolygon([V(-X_FLAT, 0, z), V(X_FLAT, 0, z), V(X_FLAT, Y_FLAT_I, z),
                                       V(-X_FLAT, Y_FLAT_I, z), V(-X_FLAT, 0, z)]))
    f = circle.cut(front).fuse(flat).removeSplitter()
    return f.Faces[0] if f.ShapeType != 'Face' else f


def cavity_offset(z0, z1, d):
    """Hueco interior agrandado d hacia fuera (offset 2D con arcos), de z0 a z1."""
    base = cavity_face(z0)
    f = base.makeOffset2D(d, 0) if d > 0 else base
    return f.extrude(V(0, 0, z1 - z0))


def wall_band(z0, z1, d0, d1):
    """Banda de la pared entre el hueco desplazado d0 y d1 hacia fuera."""
    return cavity_offset(z0, z1, d1).cut(cavity_offset(z0 - 1, z1 + 1, d0))


# --- Barrido ---------------------------------------------------------------------
def translated(shape, v):
    s = shape.copy()
    s.translate(v)
    return s


def sweep_clash(moving, obstacle, vec, step=0.5, tol=0.01):
    """Recorre `moving` desde su sitio hasta sitio + vec en pasos de `step` y devuelve
    (volumen maximo de choque, desplazamiento en que ocurre). Comprueba primero las cajas."""
    L = vec.Length
    n = max(1, int(math.ceil(L / step)))
    u = V(vec.x / L, vec.y / L, vec.z / L) if L > 0 else V()
    ob = obstacle.BoundBox
    worst, at = 0.0, None
    for i in range(n + 1):
        t = min(L, i * step)
        m = translated(moving, u * t)
        if not m.BoundBox.intersect(ob):
            continue
        for s in (m.Solids or [m]):
            if not s.BoundBox.intersect(ob):
                continue
            c = s.common(obstacle)
            vol = c.Volume if c.Solids else 0.0
            if vol > worst + tol:
                worst, at = vol, t
    return round(worst, 3), at


# --- Referencias (piezas compradas y reservas): no se imprimen ---------------------
PL, CA, CE = P['placa'], P['carrier'], P['celdas']
OL = PL['oled']


def h_max(x):
    """Alto maximo de componentes sobre la cara de la placa (especificacion v0.3)."""
    return min(PL['h_max'], math.sqrt(max(RI ** 2 - x * x, 0.0)) - 15.7)


def board_envelope():
    """Placa v0.3 de la especificacion: PCB, envolvente h(x) de componentes y piezas fijas."""
    yb, yf, (z0, z1), xe = PL['y_dorso'], PL['y_cara'], PL['z'], PL['x']
    out = {}
    pcb = box(-xe, xe, yb, yf, z0, z1)
    mu = PL['muesca_usb']
    pcb = pcb.cut(box(mu['x'][0], mu['x'][1] + 1, yb - 1, yf + 1, mu['z'][0], mu['z'][1]))
    ms = PL['muesca_sma']
    if ms.get('activa'):
        pcb = pcb.cut(box(ms['x'][0], ms['x'][1], yb - 1, yf + 1, ms['z'][0], z1 + 1))
    out['PCB'] = pcb
    # Envolvente de componentes: perfil h(x) fuera de las franjas, de z0 a la OLED.
    xs = PL['x'] - PL['franja']
    n = 68
    pts = [V(-xs + 2 * xs * i / n, yf, z0) for i in range(n + 1)]
    pts += [V(x.x, yf + h_max(x.x), z0) for x in reversed(pts)]
    prof = Part.Face(Part.makePolygon(pts + [pts[0]]))
    env = prof.extrude(V(0, 0, OL['z0'] - z0))
    env = env.cut(box(mu['x'][0], 30, yb, 30, mu['z'][0], mu['z'][1]))
    b = PL['boton']
    low = cyl_y(b['radio_bajo'], b['x'], b['z'], yf + b['alto_bajo'], 30)
    ld = PL['led']
    low = low.fuse(cyl_y(ld['radio_bajo'], ld['x'], ld['z'], yf + ld['alto_bajo'], 30))
    out['componentes (envolvente h(x))'] = env.cut(low)
    hs = b['lado'] / 2
    out['SW401'] = box(b['x'] - hs, b['x'] + hs, yf, yf + b['alto'], b['z'] - hs, b['z'] + hs)
    u = PL['usb_c']
    out['J101 USB-C'] = box(u['boca_x'] - u['fondo'], u['boca_x'], yf, yf + u['alto'],
                            u['z'] - u['ancho'] / 2, u['z'] + u['ancho'] / 2)
    sd = PL['microsd']
    zc = P['costado']['microsd']['z_centro']
    out['J401 microSD'] = box(sd['boca_x'] - sd['fondo'], sd['boca_x'], yf, yf + sd['alto'],
                              zc - sd['ancho'] / 2, zc + sd['ancho'] / 2)
    out.update(oled_stack())
    return out


def oled_stack():
    W, H, T = OL['pcb']
    z0, yp = OL['z0'], OL['y_pcb']
    yb, yf = PL['y_dorso'], PL['y_cara']
    out = {'OLED PCB': box(-W / 2, W / 2, yp, yp + T, z0, z0 + H),
           'OLED separador y componentes de atras': box(-W / 2, W / 2, yf, yp, z0, z0 + H)}
    g = OL['vidrio']
    out['OLED vidrio'] = box(-g['x'], g['x'], yp + T, yp + T + g['espesor'], g['z'][0], g['z'][1])
    f = OL['flex']
    out['OLED cinta flexible'] = box(-f['x'], f['x'], yp - 0.5, yp + T + 1.0, g['z'][1] - 0.2, f['z_max'])
    pn = OL['pines']
    out['OLED pines'] = box(-pn['x'], pn['x'], yf, yp + T + 0.5, pn['z'][0], pn['z'][1])   # pads SMD
    t = OL['tornillo']
    scr = []
    for sx in (-1, 1):
        x, z = sx * OL['agujeros']['x'], OL['agujeros']['z']
        y_head = yp + T
        scr.append(cyl_y(t['cabeza_diametro'] / 2, x, z, y_head, y_head + t['cabeza_alto']))
        scr.append(cyl_y(t['diametro'] / 2 - 0.2, x, z, y_head - t['largo'], y_head))
    out['OLED tornillos M2'] = fuse_all(scr)
    return out


def usb_overmold():
    f, u, c = PL['funda_usb'], PL['usb_c'], P['costado']['usb_c']
    return box(u['boca_x'], u['boca_x'] + f['largo'], f['y_centro'] - f['alto'] / 2,
               f['y_centro'] + f['alto'] / 2, u['z'] - f['ancho'] / 2, u['z'] + f['ancho'] / 2)


def microsd_card(dx=0.0):
    t = PL['tarjeta']
    zc = P['costado']['microsd']['z_centro']
    x1 = t['x_fuera'] + dx
    return box(x1 - t['largo'], x1, t['y0'], t['y0'] + t['espesor'],
               zc - t['ancho'] / 2, zc + t['ancho'] / 2)


def carrier():
    sys.path.insert(0, str(MB_CAD))
    import carrier_bdlx
    return carrier_bdlx.build(CA)


def cells():
    r = CE['diametro'] / 2
    z0, z1 = CE['z']
    return {f'celda {i + 1}': cyl_z(r, x, y, z0, z1) for i, (x, y) in enumerate(CE['ejes'])}


NUTP = P['base']['tuerca']
RET = P['base']['reten']


def hex_prism(apothem, z0, h):
    """Prisma hexagonal en el eje Z: vertices a 0, 60... grados; caras hacia 30, 90... (+-Y)."""
    rc = apothem / math.cos(math.radians(30))
    pts = [V(rc * math.cos(math.radians(60 * k)), rc * math.sin(math.radians(60 * k)), z0)
           for k in range(6)]
    return Part.Face(Part.makePolygon(pts + [pts[0]])).extrude(V(0, 0, h))


def nut_and_retainer():
    z0 = NUTP['anillo_asiento']
    nut = hex_prism(NUTP['entre_caras'] / 2, z0, NUTP['alto']).cut(cyl_z(6.7, 0, 0, -1, 30))
    x, y = polar(RET['radio'], RET['angulo'])
    zt = z0 + NUTP['alto'] + 0.01
    w = cyl_z(RET['arandela_diametro'] / 2, x, y, zt, zt + RET['arandela_espesor'])
    zh = zt + RET['arandela_espesor']
    head = cyl_z(RET['cabeza_diametro'] / 2, x, y, zh, zh + RET['cabeza_alto'])
    shank = cyl_z(RET['piloto'] / 2, x, y, zh - 8.0, zh)
    return {'tuerca 5/8-11': nut, 'reten M2 con arandela': fuse_all([w, head, shank]),
            'perno del baston (rosca maxima)': stud_max()}


ANT = P['antena']


def antenna_and_screws():
    out = {'antena HA-901A': cyl_z(ANT['diametro'] / 2, 0, 0, H_TOTAL, H_TOTAL + ANT['altura'])}
    scr = []
    z_ceil = Z_TUBE1 + ANT['avellanado_cabeza']          # techo del rebaje de la cabeza
    zw = z_ceil - ANT['arandela_espesor']
    for i in range(ANT['numero_pernos']):
        x, y = polar(ANT['circulo_pernos'] / 2, ANT['angulo_inicial'] + i * 360.0 / ANT['numero_pernos'])
        scr.append(cyl_z(ANT['cabeza_diametro'] / 2, x, y, zw, z_ceil))                       # arandela ISO 7089
        scr.append(cyl_z(ANT['cabeza_diametro'] / 2, x, y, zw - ANT['cabeza_alto'], zw))       # cabeza ISO 7045
        scr.append(cyl_z(1.05, x, y, zw, zw + 6.0))
    out['tornillos M2.5 de la antena'] = fuse_all(scr)
    return out


CX = P['coaxial']


def s_bend(a, b, n=16):
    """Curva en S de a (subiendo) a b (subiendo) en el plano vertical que los une.
    Devuelve (puntos, radio)."""
    dx, dy, h = b[0] - a[0], b[1] - a[1], b[2] - a[2]
    d = math.hypot(dx, dy)
    if d < 1e-6:
        return [a, b], float('inf')
    ux, uy = dx / d, dy / d
    R = (d * d + h * h) / (4 * d)
    alpha = math.asin(min(1.0, h / (2 * R)))
    pts = []
    for i in range(n + 1):
        t = alpha * i / n
        lat, up = R - R * math.cos(t), R * math.sin(t)
        pts.append((a[0] + ux * lat, a[1] + uy * lat, a[2] + up))
    for i in range(n - 1, -1, -1):
        t = alpha * i / n
        lat, up = d - (R - R * math.cos(t)), h - R * math.sin(t)
        pts.append((a[0] + ux * lat, a[1] + uy * lat, a[2] + up))
    return pts, R


def coax():
    """Clavija SMA recta en el SMA de la carrier: tuerca hexagonal de 5/16 (se dibuja su barrido
    al girar, Ø9.2) sobre el canon y cuerpo encima. Coaxial fino en S hasta el paso de la tapa
    y bucle de servicio sobre la placa. Devuelve ({nombre: solido}, radio de la S)."""
    c = CX['clavija']
    nt, bd = c['tuerca'], c['cuerpo']
    z0 = nt['z0']
    z1 = z0 + nt['largo']
    nut = cyl_z(nt['entre_esquinas'] / 2.0, c['x'], c['y'], z0, z1)
    body = cyl_z(bd['diametro'] / 2.0, c['x'], c['y'], z1, z1 + bd['largo'])
    pts, R = s_bend((c['x'], c['y'], z1 + bd['largo']), (0.0, 0.0, H_TOTAL))
    lp = CX['bucle']
    rc = CX['cable_diametro'] / 2.0
    loop = Part.makeTorus(lp['radio'], rc, V(lp['centro'][0], lp['centro'][1], lp['z']), V(0, 0, 1))
    return {'clavija SMA de la carrier': nut.fuse(body),
            'coaxial (curva en S)': tube_path(pts, CX['cable_diametro']),
            'coaxial: bucle de servicio': loop}, R


def nut_hex():
    """Hexagono real de la tuerca de la clavija (5/16), con una cara hacia +Y."""
    c = CX['clavija']
    nt = c['tuerca']
    h = hex_prism(nt['entre_caras'] / 2.0, nt['z0'], nt['largo'])
    h.rotate(V(), V(0, 0, 1), 30)
    h.translate(V(c['x'], c['y'], 0))
    return h


def stud_max():
    """Perno 5/8 del baston con la rosca maxima admitida desde el asiento (z 0)."""
    return cyl_z(15.875 / 2.0, 0, 0, 0.0, NUTP['perno_max'])


def light_pipe():
    lp = P['frente']['led']
    g = lp['guia_luz']
    return cyl_y(g['diametro'] / 2.0, lp['x'], lp['z'], g['y0'], Y_FLAT_O)


def oled_window_sheet():
    """Lamina de PC o acrilico pegada en el bolsillo exterior de la ventana."""
    w = P['frente']['ventana_oled']
    m, mi = w['bolsillo']['margen'], w['mica']
    e = m - mi['holgura']
    return box(-(w['x'] + e), w['x'] + e, Y_FLAT_O - mi['espesor'], Y_FLAT_O, w['z'][0] - e, w['z'][1] + e)


def plugs():
    """Zonas de clavijas y cables del canto de abajo. Lee kicad/plugs.json si ya es el de v0.3;
    si no, usa la zona de respaldo de parameters.json. Devuelve (dict, origen)."""
    zp = PL['clavijas']
    try:
        pj = json.loads(PLUGS_JSON.read_text(encoding='utf-8'))
    except Exception:
        pj = None
    if pj and abs(pj.get('z_top', 0) - PL['z'][1]) < 0.01 and 'x_u0' in pj:
        out = {}
        x0, zt, yfa = pj['x_u0'], pj['z_top'], pj['y_face']
        for q in pj['plugs']:
            us = [p[0] for p in q['zone']]
            vs = [p[1] for p in q['zone']]
            out['clavija ' + q['ref']] = box(x0 - max(us), x0 - min(us), yfa, yfa + q['h'],
                                              zt - max(vs), zt - min(vs))
        return out, 'kicad/plugs.json (v0.3)'
    out = {}
    y0, y1 = zp['zona_y']
    for i, (xa, xb) in enumerate(zp['x_respaldo']):
        # Perfil h(x) de la placa, con el alto de la clavija como tope.
        n = 40
        xs = [xa + (xb - xa) * k / n for k in range(n + 1)]
        pts = [V(x, y0, zp['z_min']) for x in xs]
        pts += [V(x, min(y1, y0 + h_max(x)), zp['z_min']) for x in reversed(xs)]
        face = Part.Face(Part.makePolygon(pts + [pts[0]]))
        out[f'clavijas de respaldo {i + 1}'] = face.extrude(V(0, 0, PL['z'][0] - zp['z_min']))
    src = 'respaldo (plugs.json es v0.2)' if pj else 'respaldo (sin plugs.json)'
    return out, src


def cable_reserves():
    return {f'cable {k}': tube_path([tuple(p) for p in v['puntos']], v['diametro'])
            for k, v in P['cables'].items()}


def radial_screw(angle, z, head_d=5.0, shank_d=2.1, length=6.0):
    """M2.5 avellanado radial desde fuera (cabeza a ras de la pared r 26)."""
    a = math.radians(angle)
    ux, uy = math.cos(a), math.sin(a)
    cone = Part.makeCone(head_d / 2, shank_d / 2, (head_d - shank_d) / 2,
                         V(ux * RO, uy * RO, z), V(-ux, -uy, 0))
    shank = Part.makeCylinder(shank_d / 2, length, V(ux * RO, uy * RO, z), V(-ux, -uy, 0))
    return cone.fuse(shank)


def case_screws():
    b, t = P['base'], P['tapa']
    s = [radial_screw(a, b['tornillos']['z']) for a in b['lenguetas']['angulos']]
    s += [radial_screw(a, t['tornillos_z']) for a in t['lenguetas']['angulos']]
    return {'tornillos M2.5 de base y tapa': fuse_all(s)}


def load_board_step(path):
    """Placa real: un solido por pieza con su referencia y 'PCB' (cad/export_board_step.py)."""
    import Import
    d = App.newDocument('board_step')
    Import.insert(str(path), d.Name)
    out = {}
    for o in d.Objects:
        if hasattr(o, 'Shape') and not o.Shape.isNull() and o.Shape.Solids and not o.OutList:
            key = o.Label
            while key in out:
                key += '_'
            out[key] = o.Shape.copy()
    App.closeDocument(d.Name)
    return out


# --- Guardas de pared: el material que falta no sale como choque -------------------------
def _frange(a, b, step):
    n = int(round((b - a) / step))
    return [a + i * step for i in range(n + 1)]


def section_polygons(shape, z, dist=0.05):
    """Contornos de la seccion horizontal de `shape` en z, como poligonos (x, y)."""
    return [[(p.x, p.y) for p in w.discretize(Distance=dist)] for w in shape.slice(V(0, 0, 1), z)]


def inside_material(polys, pts2d):
    """Regla par-impar con los contornos de la seccion: dentro del material si cae dentro de un
    numero impar de contornos (exterior y huecos)."""
    import numpy as np
    from matplotlib.path import Path as MPath
    cnt = np.zeros(len(pts2d), dtype=int)
    for poly in polys:
        if len(poly) > 2:
            cnt += MPath(poly).contains_points(pts2d).astype(int)
    return cnt % 2 == 1


def _openings_front(x, z, y, m=0.1):
    """Aberturas a proposito en la cara plana a la profundidad y, ensanchadas `m`."""
    fr = P['frente']
    w = fr['ventana_oled']
    pk = w['bolsillo']
    if y >= Y_FLAT_O - pk['hondo'] - m:
        e = pk['margen'] + m
    elif y <= Y_FLAT_I + w['chaflan_interior'] + m:
        e = w['chaflan_interior'] + m
    else:
        e = m
    if abs(x) <= w['x'] + e and w['z'][0] - e <= z <= w['z'][1] + e:
        return 'ventana OLED'
    k = fr['tecla']
    r_k = k['agujero'] / 2.0
    if y >= Y_FLAT_O - k['rebaje']['hondo'] - m:
        r_k = k['rebaje']['diametro'] / 2.0
    if math.hypot(x - k['x'], z - k['z']) <= r_k + m:
        return 'tecla'
    l = fr['led']
    if math.hypot(x - l['x'], z - l['z']) <= l['agujero'] / 2.0 + m:
        return 'led'
    return None


def _openings_side(x, y, z, m=0.1):
    """Aberturas a proposito en la pared redonda, ensanchadas `m`."""
    cs = P['costado']
    u = cs['usb_c']
    if x >= u['x0'] - m and y >= u['y'][0] - m and abs(z - u['z_centro']) <= u['medio_alto'] + m:
        return 'tunel USB-C'
    sd = cs['microsd']
    if x >= 15.5 - m and sd['y'][0] - m <= y <= sd['y'][1] + m and abs(z - sd['z_centro']) <= sd['ancho'] / 2 + m:
        return 'ranura microSD'
    nl = sd['una']
    ye = sd['y'][1]
    xo = math.sqrt(RO ** 2 - ye ** 2)
    if math.hypot(x - (xo + nl['radio'] - nl['hondo']), y - ye) <= nl['radio'] + m and \
            abs(z - sd['z_centro']) <= nl['alto'] / 2 + m:
        return 'rebaje de la una'
    r = math.hypot(x, y)
    a = math.atan2(y, x)
    head = P['base']['tornillos']['avellanado_diametro'] / 2.0
    for cfg, zs in ((P['base']['lenguetas'], P['base']['tornillos']['z']), (P['tapa']['lenguetas'], P['tapa']['tornillos_z'])):
        for ang in cfg['angulos']:
            da = math.atan2(math.sin(a - math.radians(ang)), math.cos(a - math.radians(ang)))
            if abs(da) < math.pi / 2 and math.hypot(r * math.sin(da), z - zs) <= head + m:
                return 'tornillo radial'
    return None


def probe_zones():
    """(z0, z1, y de la sonda delantera, r del anillo, r en las ranuras). En los extremos, donde el
    tubo tiene el rebaje de 0.9 por dentro, las sondas van en la mitad de lo que queda."""
    lab = P['tubo']['laberinto']
    zb = Z_TUBE0 + lab['alto_base'] + lab['holgura']
    zt = Z_TUBE1 - lab['alto_tapa'] - lab['holgura']
    y_mid = (Y_FLAT_I + Y_FLAT_O) / 2.0
    y_out = (Y_FLAT_I + lab['ancho'] + lab['holgura'] + Y_FLAT_O) / 2.0
    r_out = (RI + lab['ancho'] + lab['holgura'] + RO) / 2.0
    return [(math.ceil(zb + 0.4), math.floor(zt - 0.4), y_mid, (RI + RO) / 2.0, 25.6),
            (Z_TUBE0 + 0.2, zb - 0.1, y_out, r_out, r_out),
            (zt + 0.1, Z_TUBE1 - 0.5, y_out, r_out, r_out)]


def wall_probes(tube, step=0.5):
    """Sondas en la mitad de la pared: cara plana (x -13.5...13.5) y anillo (fuera de la cara
    plana). Todo punto fuera de las aberturas a proposito tiene que ser material."""
    import numpy as np
    grooves = P['tubo']['ranuras_rieles']['angulos']
    front_x = _frange(-13.5, 13.5, step)
    da = step / 25.1
    res = {'cara_plana': {'puntos': 0, 'en_aberturas': 0, 'sin_material': 0, 'ejemplos': []},
           'anillo': {'puntos': 0, 'en_aberturas': 0, 'sin_material': 0, 'ejemplos': []}}
    zones = probe_zones()
    for z0, z1, y_f, r_ring, r_groove in zones:
        ring = []
        for i in range(int(2 * math.pi / da)):
            a = i * da
            deg = math.degrees(a)
            r = r_groove if any(a0 <= deg <= a1 for a0, a1 in grooves) else r_ring
            x, y = r * math.cos(a), r * math.sin(a)
            if y > Y_FLAT_O - 0.3:      # zona de la cara plana: la cubre la sonda delantera
                continue
            ring.append((x, y))
        n = max(1, int(round((z1 - z0) / step)))
        for z in [z0 + (z1 - z0) * i / n for i in range(n + 1)]:
            polys = section_polygons(tube, z)
            for key, pts, opening in (('cara_plana', [(x, y_f) for x in front_x], lambda x, y: _openings_front(x, z, y)),
                                      ('anillo', ring, lambda x, y: _openings_side(x, y, z)
                                       or (_openings_front(x, z, y) if abs(x) <= X_FLAT else None))):
                inside = inside_material(polys, np.array(pts))
                r_ = res[key]
                for (x, y), ok in zip(pts, inside):
                    r_['puntos'] += 1
                    if opening(x, y):
                        r_['en_aberturas'] += 1
                    elif not ok:
                        r_['sin_material'] += 1
                        if len(r_['ejemplos']) < 10:
                            r_['ejemplos'].append([round(x, 2), round(y, 2), round(z, 2)])
    for r_ in res.values():
        r_['ok'] = r_['sin_material'] == 0
    res['paso_mm'] = step
    res['zonas'] = [[round(v, 2) for v in zz] for zz in zones]
    return res


def wall_reference(n=720):
    """Pared intencionada del tubo, hecha aparte (poligonos, sin interior()): circulo R26 con la
    cara plana en y 22.13 por fuera; por dentro circulo R24.2, salvo en |x| <= 13.65, donde manda
    la cara plana en y 20.33."""
    out, inn = [], []
    for i in range(n):
        a = 2 * math.pi * i / n
        x, y = RO * math.cos(a), RO * math.sin(a)
        out.append(V(x, min(y, Y_FLAT_O), 0))
        x, y = RI * math.cos(a), RI * math.sin(a)
        inn.append(V(x, y, 0))
    of = Part.Face(Part.makePolygon(out + [out[0]]))
    circle = Part.Face(Part.makePolygon(inn + [inn[0]]))
    front = box(-X_FLAT, X_FLAT, Y_FLAT_I, RI + 1, -1, 1)          # casquete delante de la cara plana
    flat = Part.Face(Part.makePolygon([V(-X_FLAT, 0, 0), V(X_FLAT, 0, 0), V(X_FLAT, Y_FLAT_I, 0),
                                       V(-X_FLAT, Y_FLAT_I, 0), V(-X_FLAT, 0, 0)]))
    inner = circle.cut(front).fuse(flat).removeSplitter()
    ring = of.cut(inner)
    prism = ring.extrude(V(0, 0, Z_TUBE1 - Z_TUBE0))
    prism.translate(V(0, 0, Z_TUBE0))
    return prism.common(outer_envelope())


def min_wall_thickness(shape, zs, region, dist=0.05):
    """Espesor minimo de pared en secciones horizontales: desde el punto medio de cada tramo del
    contorno, rayo hacia dentro del material hasta el siguiente contorno. Solo tramos dentro de
    region = (x0, x1, y0, y1). Detecta cunas: el espesor cae a cero en su filo.
    Devuelve (espesor minimo, [x, y, z])."""
    import numpy as np
    best, where = float('inf'), None
    x0, x1, y0, y1 = region
    for z in zs:
        polys = [np.array(p) for p in section_polygons(shape, z, dist) if len(p) > 2]
        if not polys:
            continue
        segs = np.vstack([np.hstack([p[:-1], p[1:]]) for p in polys])   # (n, 4): ax ay bx by
        A, B = segs[:, :2], segs[:, 2:]
        # Esquinas vivas (giro > 20 grados): cerca de su vertice el espesor del rayo tiende a
        # cero aunque no haya pared fina; se ignoran los tramos a menos de 0.6 de ellas.
        sharp = []
        for p in polys:
            q = p[:-1] if np.allclose(p[0], p[-1]) else p
            n = len(q)
            for k in range(n):
                u1 = q[k] - q[k - 1]
                u2 = q[(k + 1) % n] - q[k]
                l1, l2 = np.linalg.norm(u1), np.linalg.norm(u2)
                if l1 < 1e-9 or l2 < 1e-9:
                    continue
                if np.dot(u1, u2) / (l1 * l2) < math.cos(math.radians(20)):
                    sharp.append(q[k])
        sharp = np.array(sharp) if sharp else np.zeros((0, 2))
        for (ax, ay, bx, by) in segs:
            mx, my = (ax + bx) / 2.0, (ay + by) / 2.0
            if not (x0 <= mx <= x1 and y0 <= my <= y1):
                continue
            if len(sharp) and np.min(np.hypot(sharp[:, 0] - mx, sharp[:, 1] - my)) < 0.6:
                continue
            ex, ey = bx - ax, by - ay
            L = math.hypot(ex, ey)
            if L < 1e-9:
                continue
            nx, ny = -ey / L, ex / L
            probe = np.array([[mx + nx * 0.01, my + ny * 0.01]])
            if not inside_material([p.tolist() for p in polys], probe)[0]:
                nx, ny = -nx, -ny
            # Interseccion del rayo (m + t n) con todos los tramos.
            d = B - A
            den = nx * d[:, 1] - ny * d[:, 0]
            ok = np.abs(den) > 1e-12
            qx, qy = A[:, 0] - mx, A[:, 1] - my
            t = np.where(ok, (qx * d[:, 1] - qy * d[:, 0]) / np.where(ok, den, 1), np.inf)
            u = np.where(ok, (qx * ny - qy * nx) / np.where(ok, den, 1), -1)
            hit = ok & (t > 1e-4) & (u >= 0) & (u <= 1)
            if hit.any():
                th = t[hit].min()
                if th < best:
                    best, where = th, [round(mx, 2), round(my, 2), round(z, 2)]
    return round(best, 3), where
