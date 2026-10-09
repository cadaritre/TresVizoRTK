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
CLR = HOL['ajuste_impresas']          # juego entre piezas impresas
CLR_BUY = HOL['compradas']           # aire a piezas compradas


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
    """Exterior completo z 0-H_TOTAL (111): R28, redondeos R4 arriba y abajo, cara plana en y 22.9."""
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

    En |x| <= X_FLAT (15.33) llega hasta la cara plana interior (y 20.5); fuera de esa franja sigue
    el circulo de r RI (25.6), que corta la cara plana justo en |x| 15.33. Al circulo se le quita
    antes el casquete delante de la cara plana: si no, el hueco pasa de la cara plana exterior
    (y 22.9) y el frente queda abierto (error de la primera version).
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
    """Alto maximo de componentes sobre la cara de la placa: 0.5 de aire a la cara plana interior
    (tope h_max) y 0.5 en radial a la pared redonda (circulo de RI - aire), no 0.5 en y: en los
    cantos la pared va inclinada y 0.5 en y dejaba solo ~0.37 de aire."""
    return min(PL['h_max'], math.sqrt(max((RI - PL['aire']) ** 2 - x * x, 0.0)) - PL['y_cara'])


BOARD_JSON = MB_CAD / 'placa-principal.json'


def board_json():
    try:
        return json.loads(BOARD_JSON.read_text(encoding='utf-8'))
    except Exception:
        return None


def sd_axis_z():
    """Eje de la tarjeta microSD: centro de J401 en la placa real (placa-principal.json) mas el
    corrimiento del canal de la tarjeta (0.9, de los pivotes de la huella TF-015). Si no esta, el
    valor de respaldo de parameters.json. Nunca sale de la ranura."""
    sd = P['costado']['microsd']
    bj = board_json()
    try:
        zz = bj['componentes']['J401']['caja']['z']
        return round((zz[0] + zz[1]) / 2.0 + sd['desplazamiento_canal'], 2), 'J401 (placa-principal.json)'
    except Exception:
        return sd['z_centro'], 'respaldo (parameters.json)'


SD_Z, SD_Z_SRC = sd_axis_z()


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
    zc = SD_Z - P['costado']['microsd']['desplazamiento_canal']
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


def usb_axis():
    """Eje de la clavija USB-C: centro de la caja de J101 en la placa real (placa-principal.json), en y
    y en z. Si no esta, el de respaldo de parameters.json (funda_usb.y_centro, usb_c.z)."""
    bj = board_json()
    try:
        bx_ = bj['componentes']['J101']['caja']
        return round(sum(bx_['y']) / 2.0, 3), round(sum(bx_['z']) / 2.0, 3), 'J101 (placa-principal.json)'
    except Exception:
        return PL['funda_usb']['y_centro'], PL['usb_c']['z'], 'respaldo (parameters.json)'


USB_Y, USB_Z, USB_SRC = usb_axis()


def rounded_rect_x(x0, x1, yc, zc, h, w, r):
    """Prisma a lo largo de X (x0 a x1) de seccion rectangulo redondeado: alto h (en y), ancho w (en z),
    radio de esquina r."""
    r = max(0.0, min(r, h / 2.0 - 1e-3, w / 2.0 - 1e-3))
    L = x1 - x0
    core = box(x0, x1, yc - h / 2.0 + r, yc + h / 2.0 - r, zc - w / 2.0, zc + w / 2.0)
    core = core.fuse(box(x0, x1, yc - h / 2.0, yc + h / 2.0, zc - w / 2.0 + r, zc + w / 2.0 - r))
    if r > 0:
        for sy in (-1, 1):
            for sz in (-1, 1):
                core = core.fuse(Part.makeCylinder(r, L, V(x0, yc + sy * (h / 2.0 - r), zc + sz * (w / 2.0 - r)), V(1, 0, 0)))
    return core.removeSplitter()


def rounded_rect_inside(y, z, yc, zc, h, w, r):
    """Si (y, z) cae dentro del rectangulo redondeado de rounded_rect_x (alto h en y, ancho w en z, radio r)."""
    dy, dz = abs(y - yc) - (h / 2.0 - r), abs(z - zc) - (w / 2.0 - r)
    if dy <= 0 or dz <= 0:
        return abs(y - yc) <= h / 2.0 and abs(z - zc) <= w / 2.0
    return dy * dy + dz * dz <= r * r


def usb_tunnel():
    """Tunel del USB-C: (x0 = boca de J101, yc, zc, alto en y, ancho en z, radio): funda + holgura por lado."""
    u, f, c = PL['usb_c'], PL['funda_usb'], P['costado']['usb_c']
    hh = c['holgura']
    return u['boca_x'], USB_Y, USB_Z, f['alto'] + 2 * hh, f['ancho'] + 2 * hh, c['radio_funda'] + hh


def sd_slot():
    """Ranura de la microSD: (x0, y0, y1, zc, ancho en z) = tarjeta + holgura por lado, en el eje de J401."""
    sd, t = P['costado']['microsd'], PL['tarjeta']
    hh = sd['holgura']
    return sd['x0'], t['y0'] - hh, t['y0'] + t['espesor'] + hh, SD_Z, t['ancho'] + 2 * hh


def sd_notch_x0():
    """x donde empieza la muesca. Ciega (con `pared_detras`): fondo plano en x0 = donde el techo de la
    ranura (y1) llega a r = RI + pared_detras, asi el fondo cae a 90 grados sobre el techo y detras quedan
    pared_detras o mas. Con un fondo curvo (r constante) el encuentro era un filo de ~50 grados (0.71)."""
    sx0, sy0, sy1, szc, sw = sd_slot()
    pw = P['costado']['microsd']['muesca'].get('pared_detras')
    return max(sx0, math.sqrt((RI + pw) ** 2 - sy1 ** 2)) if pw else sx0


def sd_notch(inset=0.0, x1=None):
    """Muesca para la una sobre la ranura de la microSD, encogida `inset` por lado, desde sd_notch_x0()."""
    sx0, sy0, sy1, szc, sw = sd_slot()
    mu = P['costado']['microsd']['muesca']
    x1 = RO + 2 if x1 is None else x1
    return box(sd_notch_x0() + inset, x1, sy0 + inset, mu['y_sup'] - inset,
               szc - mu['ancho'] / 2.0 + inset, szc + mu['ancho'] / 2.0 - inset)


def anchor_zs():
    z = P['costado']['tapa_puertos']['ancla']['z']
    return list(z) if isinstance(z, (list, tuple)) else [z]


def usb_overmold():
    """Funda maxima de la clavija USB-C (12.35 x 6.5, esquinas de radio funda_usb.radio) desde la boca
    de J101, centrada en su eje."""
    f, u = PL['funda_usb'], PL['usb_c']
    return rounded_rect_x(u['boca_x'], u['boca_x'] + f['largo'], USB_Y, USB_Z, f['alto'], f['ancho'], f.get('radio', 0.0))


# --- Marco del USB-C (pieza 08) -----------------------------------------------------------
def board_component_boxes(skip=('J101',)):
    """{ref: [[x0, x1, y0, y1, z0, z1], ...]} de placa-principal.json; para las piezas de
    costado.usb_c.marco.cajas_placa_real, las cajas de sus partes en el STEP real."""
    real = P['costado']['usb_c']['marco'].get('cajas_placa_real', {})
    out = {}
    for ref, v in ((board_json() or {}).get('componentes') or {}).items():
        if ref in skip:
            continue
        c = v['caja']
        out[ref] = [[c['x'][0], c['x'][1], c['y'][0], c['y'][1], c['z'][0], c['z'][1]]]
    for ref, bxs in real.items():
        if ref in out:
            out[ref] = [list(b) for b in bxs]
    return out


def bezel_frame():
    """Cotas del marco: tunel (x0, yc, zc, alto, ancho, radio), cara del collar xf, cara de atras xc,
    z0-z1 (con las paredes), zt0-zt1 (lados del tunel), y0 (bajo el suelo), ytop (paso del chasis)."""
    mc = P['costado']['usb_c']['marco']
    ux0, uyc, uzc, uh, uw, ur = usb_tunnel()
    return dict(mc=mc, ux0=ux0, uyc=uyc, uzc=uzc, uh=uh, uw=uw, ur=ur,
                xf=ux0 - mc['retranqueo_boca'], xc=mc['x_collar'],
                z0=uzc - uw / 2.0 - mc['pared'], z1=uzc + uw / 2.0 + mc['pared'],
                zt0=uzc - uw / 2.0, zt1=uzc + uw / 2.0,
                y0=uyc - uh / 2.0 - mc['suelo'], ytop=Y_FLAT_I - CLR,
                yb=PL['y_dorso'], yf=PL['y_cara'], y_shell=PL['y_cara'] + PL['usb_c']['alto'])


def usb_bezel(split=False):
    """Marco del USB-C (ver costado.usb_c.marco). Con split=True devuelve (marco, parte rigida, resorte)."""
    f = bezel_frame()
    mc, xf, xc, z0, z1 = f['mc'], f['xf'], f['xc'], f['z0'], f['z1']
    zt0, zt1, y0, ytop, yb, yf, ysh = f['zt0'], f['zt1'], f['y0'], f['ytop'], f['yb'], f['yf'], f['y_shell']
    u = PL['usb_c']
    body = box(xc, RO, y0, ytop, z0, z1)
    clip = cyl_z(P['chasis']['r_max'], 0, 0, z0 - 1, z1 + 1).common(box(-40, 40, -40, ytop, z0 - 1, z1 + 1))
    body = body.common(clip)
    # Tunel (funda + holgura por lado) desde la cara del collar hacia fuera.
    body = body.cut(rounded_rect_x(xf, RO + 2, f['uyc'], f['uzc'], f['uh'], f['uw'], f['ur']))
    # El techo del tunel (y 20.15) queda por encima del paso del chasis (y 20.1): sus esquinas redondeadas
    # dejarian cunas en lo alto de las paredes de los lados. Por encima del centro de esas esquinas, los
    # lados del tunel siguen rectos.
    body = body.cut(box(xf, RO + 2, f['uyc'] + f['uh'] / 2.0 - f['ur'], ytop + 1, zt0, zt1))
    # Ranura de la placa: del dorso (el labio apoya) a la cara + juego, hasta el canto de la placa.
    body = body.cut(box(xc - 1, PL['x'], yb, yf + mc['holgura_cara'], z0 - 1, z1 + 1))
    # Abertura del collar: blindaje de J101 + holgura.
    cu = mc['cuerpo_usb']
    c = cu['holgura']
    body = body.cut(rounded_rect_x(xc - 1, xf + 0.01, (yf + ysh) / 2.0, f['uzc'], ysh - yf + 2 * c,
                                   u['ancho'] + 2 * c, cu['radio'] + c))
    # Chaflan de entrada en el canto de atras de arriba del labio (entra bajo el dorso de la placa).
    ch = mc['chaflan_labio']
    tri = Part.Face(Part.makePolygon([V(xc - 0.01, yb - ch, z0 - 1), V(xc + ch, yb + 0.01, z0 - 1),
                                      V(xc - 0.01, yb + 0.01, z0 - 1), V(xc - 0.01, yb - ch, z0 - 1)]))
    body = body.cut(tri.extrude(V(0, 0, z1 - z0 + 2)))
    # Resorte: dedo sobre el techo del blindaje con un tope cilindrico que lo aprieta.
    rs = mc['resorte']
    y_under = ysh + c
    finger = box(rs['x0'], xc + 0.01, y_under, y_under + rs['espesor'], rs['z'][0], rs['z'][1])
    tp = rs['tope']
    yb_bump = ysh - rs['interferencia']
    bump = Part.makeCylinder(tp['radio'], tp['z'][1] - tp['z'][0], V(tp['x'], yb_bump + tp['radio'], tp['z'][0]), V(0, 0, 1))
    bump = bump.common(box(tp['x'] - 2, tp['x'] + 2, yb_bump - 1, y_under + 0.01, tp['z'][0] - 1, tp['z'][1] + 1))
    spring = finger.fuse(bump).removeSplitter()
    # Zonas prohibidas: cada componente salvo J101 crecido el aire a compradas y alargado hacia -X
    # (el marco entra por -X y pasa por encima). Si entre la zona y el tunel quedaria una pared de
    # lado mas fina que la local minima, se quita hasta el tunel (solo delante del collar).
    air, wmin = HOL['compradas'], HOL['pared_local_minima']
    cuts = []
    for ref, bxs in board_component_boxes().items():
        for bx0, bx1, by0, by1, bz0, bz1 in bxs:
            k = [-50.0, bx1 + air, by0 - air, by1 + air, bz0 - air, bz1 + air]
            if k[1] < rs['x0'] or k[5] < z0 or k[4] > z1 or k[3] < y0 or k[2] > ytop:
                continue
            cuts.append(box(*k))
            for side, thin in (((z0 - 1, zt0 + 0.01), k[4] < zt0 and 0 < zt0 - k[5] < wmin),
                               ((zt1 - 0.01, z1 + 1), k[5] > zt1 and 0 < k[4] - zt1 < wmin)):
                if not thin:
                    continue
                cuts.append(box(xf, k[1], k[2], k[3], *side))
                # Si la esquina de arriba de la zona queda a menos de wmin del paso del chasis (r_max), entre
                # las dos quedaria un cuello fino: se quita la pared de esa esquina hacia fuera, dejando wmin
                # de alto por encima de la zona y wmin entre la zona y lo que queda por debajo.
                rmax_ = P['chasis']['r_max']
                if rmax_ - math.hypot(k[1], k[3]) < wmin and k[3] + wmin < rmax_:
                    xa = math.sqrt(rmax_ ** 2 - (k[3] + wmin) ** 2)
                    cuts.append(box(xa, RO + 2, k[3] - wmin, ytop + 1, *side))
    if cuts:
        allc = fuse_all(cuts)
        body, spring = body.cut(allc), spring.cut(allc)
    out = clean(body.fuse(spring))
    if split:
        return out, clean(body), spring
    return out


def bezel_spring_zone():
    """Caja que contiene el resorte del marco (detras del collar, sobre el blindaje)."""
    f = bezel_frame()
    rs = f['mc']['resorte']
    return box(rs['x0'] - 1, f['xc'], f['y_shell'] - 1.0, f['ytop'] + 1, rs['z'][0] - 1, rs['z'][1] + 1)


def microsd_card(dx=0.0):
    t = PL['tarjeta']
    zc = SD_Z
    x1 = t['x_fuera'] + dx
    return box(x1 - t['largo'], x1, t['y0'], t['y0'] + t['espesor'],
               zc - t['ancho'] / 2, zc + t['ancho'] / 2)


def carrier():
    sys.path.insert(0, str(MB_CAD))
    import carrier_bdlx
    return carrier_bdlx.build(CA)


def cells():
    z0, z1 = CE['z']
    return {'pack 1S2P (envolvente)': pack_solid(z0, z1)}


def pack_solid(z0, z1, off=0.0):
    """Envolvente del pack 1S2P: estadio (dos cilindros de diametro grueso con los valles puenteados por
    la funda) de ancho x grueso, entre z0 y z1, crecido off por todos lados en planta."""
    pk = CE['pack']
    cx, cy = pk['centro']
    a = (pk['ancho'] - pk['grueso']) / 2.0
    r = pk['grueso'] / 2.0 + off
    s = box(cx - a, cx + a, cy - r, cy + r, z0, z1)
    for sx in (-1, 1):
        s = s.fuse(cyl_z(r, cx + sx * a, cy, z0, z1))
    return s.removeSplitter()


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


def _bspline(ctrl, k, u):
    """Punto de un B-spline de grado k con nodos uniformes sujetos (como scipy BSpline), por de Boor."""
    n = len(ctrl)
    t = [0.0] * k + [i / float(n - k) for i in range(n - k + 1)] + [1.0] * k
    u = min(max(u, 0.0), 1.0 - 1e-12)
    j = max(i for i in range(k, n) if t[i] <= u)
    d = [list(ctrl[j - k + i]) for i in range(k + 1)]
    for r in range(1, k + 1):
        for i in range(k, r - 1, -1):
            a = (u - t[j - k + i]) / (t[i + 1 + j - r] - t[j - k + i])
            d[i] = [(1 - a) * d[i - 1][c] + a * d[i][c] for c in range(3)]
    return tuple(d[k])


def coax_route(n=800):
    """Recorrido del latiguillo, del SMA acodado de la carrier al pasamuros del eje: B-spline cubico
    de coaxial.ruta.puntos_control (optimizado para R >= 12 con holgura a todo), con 2 mm de cable
    dentro de la clavija acodada delante. Empieza en la salida de la clavija hacia -X y acaba vertical
    en la cara de dentro del pasamuros."""
    c, rt = CX['clavija'], CX['ruta']
    ac = c['acodada']
    dx, dy = ac['direccion']
    ctrl = rt['puntos_control']
    pts = [(c['x'] + dx * (ac['largo'] - 2.0), c['y'] + dy * (ac['largo'] - 2.0), ac['z_cable'])]
    pts += [_bspline(ctrl, rt.get('grado', 3), i / float(n)) for i in range(n + 1)]
    return pts


def coax_solid():
    """Cable del latiguillo como barrido de un circulo por el B-spline exacto de coaxial.ruta (mas los
    2 mm dentro de la clavija acodada). Un solo barrido liso: fundir cientos de cilindros cortos daba
    distancias falsas en distToShape de OCC."""
    c, rt = CX['clavija'], CX['ruta']
    ac = c['acodada']
    r = CX['cable']['diametro'] / 2.0
    ctrl = rt['puntos_control']
    k = rt.get('grado', 3)
    n = len(ctrl)
    knots = [i / float(n - k) for i in range(n - k + 1)]
    mults = [k + 1] + [1] * (n - k - 1) + [k + 1]
    bs = Part.BSplineCurve()
    bs.buildFromPolesMultsKnots([V(*p) for p in ctrl], mults, knots, False, k)
    t0 = bs.tangent(bs.FirstParameter)[0]
    circ = Part.Wire(Part.makeCircle(r, bs.value(bs.FirstParameter), t0))
    pipe = Part.Wire(bs.toShape()).makePipeShell([circ], True, True)
    dx, dy = ac['direccion']
    p0 = V(c['x'] + dx * (ac['largo'] - 2.0), c['y'] + dy * (ac['largo'] - 2.0), ac['z_cable'])
    stub = Part.makeCylinder(r, 2.0, p0, V(dx, dy, 0))
    return pipe.fuse(stub).removeSplitter()


def min_bend_radius(pts):
    """Radio de curva minimo de una poligonal fina (circunradio de cada terna de puntos)."""
    best = float('inf')
    for a, b, c in zip(pts[:-2], pts[1:-1], pts[2:]):
        A, B, C = V(*a), V(*b), V(*c)
        ab, bc, ca = (B - A).Length, (C - B).Length, (A - C).Length
        area2 = (B - A).cross(C - A).Length
        if area2 > 1e-9:
            best = min(best, ab * bc * ca / (2.0 * area2))
    return best


def coax():
    """Clavija SMA acodada en el SMA de la carrier, recorrido del cable y conector de la tapa
    (pasamuros SMA hembra si la antena es macho; clavija recta por el paso de 12 si es hembra).
    Devuelve ({nombre: solido}, radio de curva minimo)."""
    c = CX['clavija']
    nt, ac = c['tuerca'], c['acodada']
    z1 = nt['z0'] + nt['largo']
    nut = cyl_z(nt['entre_esquinas'] / 2.0, c['x'], c['y'], nt['z0'], z1)
    dx = ac['direccion'][0]
    xa, xb = sorted((c['x'] - dx * 3.5, c['x'] + dx * (ac['largo'] - 2.0)))
    housing = box(xa, xb, c['y'] - ac['ancho'] / 2.0, c['y'] + ac['ancho'] / 2.0, ac['z'][0], ac['z'][1])
    boot = cyl_x(1.5, c['y'], ac['z_cable'], *sorted((c['x'] + dx * (ac['largo'] - 2.0), c['x'] + dx * ac['largo'])))
    plug = [nut, housing, boot]
    if ac['z'][0] > z1:                                 # cuello entre la tuerca y el cuerpo acodado
        plug.append(cyl_z(ac.get('cuello_diametro', 5.0) / 2.0, c['x'], c['y'], z1 - 0.01, ac['z'][0] + 0.01))
    pts = coax_route()
    out = {'clavija SMA de la carrier': fuse_all(plug), 'coaxial (recorrido)': coax_solid()}
    cn = ANT['conector']
    z_in = H_TOTAL - cn['pasamuros']['panel']          # cara de dentro del panel de la tapa
    if cn['tipo'] == 'macho':
        pm = cn['pasamuros']
        tnut = hex_prism(pm['tuerca_entre_caras'] / 2.0, z_in - pm['tuerca_alto'], pm['tuerca_alto'])
        body = cyl_z(3.0, 0, 0, z_in - pm['largo_dentro'] + 3.0, z_in - pm['tuerca_alto'])
        bt = cyl_z(1.75, 0, 0, z_in - pm['largo_dentro'], z_in - pm['largo_dentro'] + 3.0)
        out['pasamuros SMA (dentro)'] = fuse_all([tnut, body, bt])
        flat_y = pm['plano'] - pm['agujero'] / 2.0 - 0.05      # el cuerpo roscado lleva la misma cara plana
        out['pasamuros SMA (fuera)'] = cyl_z(pm['rosca'] / 2.0, 0, 0, z_in, H_TOTAL + pm['largo_fuera']).cut(
            box(-5, 5, flat_y, 5, z_in - 1, H_TOTAL + pm['largo_fuera'] + 1))
    else:
        out['clavija SMA del cable (antena hembra)'] = cyl_z(4.0, 0, 0, z_in - cn['pasamuros']['largo_dentro'], H_TOTAL + 2.0)
    return out, min_bend_radius(pts)


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
    """Manojos de cables (reservas) y la NTC pegada en la cara de atras del pack."""
    cb = P['cables']
    out = {f'cable {k}': tube_path([tuple(p) for p in v['puntos']], v['diametro'])
           for k, v in cb.items() if isinstance(v, dict) and 'puntos' in v}
    if 'ntc' in cb:
        c = cb['ntc']['caja']
        out['cable NTC (cuerpo)'] = box(c['x'][0], c['x'][1], c['y'][0], c['y'][1], c['z'][0], c['z'][1])
    return out


def radial_screw(angle, z, head_d=5.0, shank_d=2.1, length=6.0):
    """M2.5 avellanado radial desde fuera (cabeza a ras de la pared exterior, r 28)."""
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
    ux0, uyc, uzc, uh, uw, ur = usb_tunnel()
    if abs(z - uzc) <= uw / 2 + m and abs(y - uyc) <= uh / 2 + m and x >= ux0 - m:
        return 'tunel USB-C'
    ch = cs['usb_c']['chaflan_entrada'] + 0.3
    if abs(z - uzc) <= uw / 2 + m and uyc + uh / 2 - m <= y <= uyc + uh / 2 + ch and math.hypot(x, y) >= RO - 2 * ch:
        return 'chaflan del tunel'
    sx0, sy0, sy1, szc, sw = sd_slot()
    if x >= sx0 - m and sy0 - m <= y <= sy1 + m and abs(z - szc) <= sw / 2 + m:
        return 'ranura microSD'
    mu = cs['microsd']['muesca']
    if (x >= sx0 - m and sy0 - m <= y <= mu['y_sup'] + m and abs(z - szc) <= mu['ancho'] / 2 + m
            and x >= sd_notch_x0() - m):
        return 'muesca de la una'
    ch = cs['microsd']['chaflan_entrada'] + 0.3
    if math.hypot(x, y) >= RO - 2 * ch and ((sy1 - m <= y <= sy1 + ch and abs(z - szc) <= sw / 2 + m) or
                                            (mu['y_sup'] - m <= y <= mu['y_sup'] + ch and abs(z - szc) <= mu['ancho'] / 2 + m)):
        return 'chaflan de la ranura'
    r = math.hypot(x, y)
    a = math.atan2(y, x)
    an = cs['tapa_puertos']['ancla']
    da = math.atan2(math.sin(a - math.radians(an['angulo'])), math.cos(a - math.radians(an['angulo'])))
    for za in anchor_zs():
        if abs(da) < math.pi / 2 and math.hypot(r * math.sin(da), z - za) <= an['agujero'] / 2.0 + m:
            return 'ancla de la tapa de puertos'
    head = P['base']['tornillos']['avellanado_diametro'] / 2.0
    for cfg, zs in ((P['base']['lenguetas'], P['base']['tornillos']['z']), (P['tapa']['lenguetas'], P['tapa']['tornillos_z'])):
        for ang in cfg['angulos']:
            da = math.atan2(math.sin(a - math.radians(ang)), math.cos(a - math.radians(ang)))
            if abs(da) < math.pi / 2 and math.hypot(r * math.sin(da), z - zs) <= head + m:
                return 'tornillo radial'
    return None


def probe_zones():
    """(z0, z1, y de la sonda delantera, r del anillo, r en las ranuras). En los extremos, donde el
    tubo tiene el rebaje de 1.2 por dentro, las sondas van en la mitad de lo que queda."""
    lab = P['tubo']['laberinto']
    zb = Z_TUBE0 + lab['alto_base'] + lab['holgura']
    zt = Z_TUBE1 - lab['alto_tapa'] - lab['holgura']
    y_mid = (Y_FLAT_I + Y_FLAT_O) / 2.0
    y_out = (Y_FLAT_I + lab['ancho'] + lab['holgura'] + Y_FLAT_O) / 2.0
    r_out = (RI + lab['ancho'] + lab['holgura'] + RO) / 2.0
    return [(math.ceil(zb + 0.4), math.floor(zt - 0.4), y_mid, (RI + RO) / 2.0, (P['tubo']['ranuras_rieles']['radio'] + RO) / 2.0),
            (Z_TUBE0 + 0.2, zb - 0.1, y_out, r_out, r_out),
            (zt + 0.1, Z_TUBE1 - 0.5, y_out, r_out, r_out)]


def wall_probes(tube, step=0.5):
    """Sondas en la mitad de la pared: cara plana (x -13.5...13.5) y anillo (fuera de la cara
    plana). Todo punto fuera de las aberturas a proposito tiene que ser material."""
    import numpy as np
    grooves = P['tubo']['ranuras_rieles']['angulos']
    front_x = _frange(-13.5, 13.5, step)
    da = step / ((RI + RO) / 2.0)
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
        # Corridas 0.013 de los multiplos de 0.5: una seccion justo en la tangente de un agujero
        # horizontal (el del ancla acaba en z 33.5) sale degenerada y falla entera.
        for z in [z0 + 0.013 + (z1 - z0 - 0.026) * i / n for i in range(n + 1)]:
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
    """Pared intencionada del tubo, hecha aparte (poligonos, sin interior()): circulo RO (28) con
    la cara plana en y 22.9 por fuera; por dentro circulo RI (25.6), salvo en |x| <= 15.33, donde
    manda la cara plana en y 20.5."""
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


# --- Logo ------------------------------------------------------------------------------
LOGO_PY = REPO / 'hardware' / 'main-board' / 'scripts' / 'logo.py'


def logo_polygons():
    """Distintivo de TresVizo (hexágono con el 3, el de las carcasas V2.x) de
    hardware/main-board/scripts/logo.py, badge() (contornos de mechanical/v2.2/logo.json), sin
    modificarlo, en la cara plana: mirando el frente desde +Y, +X queda a la izquierda, así que x = -u y
    z = z_c - v (se lee bien desde delante, sin espejo). Devuelve [(contorno, [huecos])] en (x, z), ancho
    y alto."""
    import importlib.util
    spec = importlib.util.spec_from_file_location('tresvizo_logo', str(LOGO_PY))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    lg = P['frente']['logo']
    polys, w, h = mod.badge(lg['ancho'], (0.0, 0.0), mirror=False)
    tr = lambda ring: [(-u, lg['z_centro'] - v) for u, v in ring]
    return [(tr(o), [tr(hh) for hh in hs]) for o, hs in polys], w, h


def logo_solid(y0, y1):
    """Prisma del distintivo entre y0 e y1 (y1 > y0)."""
    polys, _, _ = logo_polygons()
    solids = []
    for o, hs in polys:
        f = Part.Face(Part.makePolygon([V(x, y0, z) for x, z in o] + [V(o[0][0], y0, o[0][1])]))
        for hh in hs:
            fh = Part.Face(Part.makePolygon([V(x, y0, z) for x, z in hh] + [V(hh[0][0], y0, hh[0][1])]))
            f = f.cut(fh)
        for face in f.Faces:
            solids.append(face.extrude(V(0, y1 - y0, 0)))
    return fuse_all(solids)


def logo_engrave():
    """Grabado del distintivo en la cara plana exterior: de y 22.9 - profundidad hacia fuera."""
    d = P['frente']['logo']['profundidad']
    return logo_solid(Y_FLAT_O - d, Y_FLAT_O + 1.0)


def logo_inlay():
    """Incrustación del distintivo para imprimir aparte en TPU y pegar en el grabado: los mismos
    contornos, reducidos `holgura` por lado, del fondo del grabado (y 22.9 - profundidad) hasta la cara
    plana (queda a ras). En su posición final; export_v3_0.py la escribe también acostada para
    imprimir. Son tantos sólidos como islas tiene el distintivo (el hexágono, el 3 y sus rayas)."""
    lg = P['frente']['logo']
    d, c = lg['profundidad'], lg['incrustacion']['holgura']
    y0 = Y_FLAT_O - d
    polys, _, _ = logo_polygons()
    solids = []
    for o, hs in polys:
        f = Part.Face(Part.makePolygon([V(x, y0, z) for x, z in o] + [V(o[0][0], y0, o[0][1])]))
        for hh in hs:
            fh = Part.Face(Part.makePolygon([V(x, y0, z) for x, z in hh] + [V(hh[0][0], y0, hh[0][1])]))
            f = f.cut(fh)
        for face in f.Faces:
            if c > 0:
                face = face.makeOffset2D(-c, join=0)
            for ff in face.Faces:
                solids.append(ff.extrude(V(0, lg['incrustacion']['espesor'], 0)))
    return Part.makeCompound(solids)


# --- Bandas de TPU (piezas 09 y 10) ----------------------------------------------------------
BD = P['bandas']
BAND_NAMES = {'abajo': '09-band-bottom-tpu', 'arriba': '10-band-top-tpu'}
# Contactos con apriete a proposito: cada banda abraza estas piezas (0.3 por lado). No son choques.
BAND_GRIP = {('09-band-bottom-tpu', '01-base'), ('09-band-bottom-tpu', '02-tube'),
             ('10-band-top-tpu', '02-tube'), ('10-band-top-tpu', '03-antenna-cap')}


def band_grip_pair(a, b):
    return (a, b) in BAND_GRIP or (b, a) in BAND_GRIP


def body_section(z=0.0):
    """Seccion exterior del cuerpo en el plano z: circulo RO cortado por la cara plana (y Y_FLAT_O)."""
    c = Part.Face(Part.Wire(Part.makeCircle(RO, V(0, 0, z))))
    return c.cut(box(-RO - 1, RO + 1, Y_FLAT_O, RO + 1, z - 1, z + 1)).Faces[0]


def body_prism(z0, z1, d=0.0):
    """Prisma del contorno del cuerpo desplazado d (con arcos), de z0 a z1. Todo el cuerpo (base, tubo y
    tapa, con sus redondeos R4) queda dentro del de d = 0."""
    s = body_section(z0)
    return (s.makeOffset2D(d, 0) if abs(d) > 1e-9 else s).extrude(V(0, 0, z1 - z0))


def band_z(which):
    h = BD['alto']
    return (0.0, h) if which == 'abajo' else (H_TOTAL - h, H_TOTAL)


def band_inner_offset(stretched=False):
    """Contorno interior de la banda respecto al del cuerpo: -apriete impresa; + holgura_barrido estirada."""
    return BD['holgura_barrido'] if stretched else -BD['apriete']


def side_offset(c, R):
    """Holgura en los lados rectos de una muesca de esquinas de radio R para que en la esquina (con la
    esquina viva del obstaculo dentro del arco) quede c."""
    return c if R <= c else R - (R - c) / math.sqrt(2.0)


def _radial_cyl(angle, z, d, r0=24.0, r1=34.0):
    a = math.radians(angle)
    u = V(math.cos(a), math.sin(a), 0)
    return Part.makeCylinder(d / 2.0, r1 - r0, V(u.x * r0, u.y * r0, z), u)


def _hull2(c1, r1, c2, r2, y0, y1):
    """Envolvente convexa de dos circulos del plano xz (centro (x, z), radio), extruida de y0 a y1."""
    (x1, z1), (x2, z2) = c1, c2
    d = math.hypot(x2 - x1, z2 - z1)
    ux, uz = (x2 - x1) / d, (z2 - z1) / d
    nx, nz = -uz, ux
    cb = (r1 - r2) / d
    sb = math.sqrt(1.0 - cb * cb)
    q = []
    for s in (1, -1):
        ex, ez = ux * cb + s * nx * sb, uz * cb + s * nz * sb
        q.append(((x1 + r1 * ex, z1 + r1 * ez), (x2 + r2 * ex, z2 + r2 * ez)))
    (a1, a2), (b1, b2) = q
    poly = [V(a1[0], y0, a1[1]), V(a2[0], y0, a2[1]), V(b2[0], y0, b2[1]), V(b1[0], y0, b1[1])]
    quad = Part.Face(Part.makePolygon(poly + [poly[0]])).extrude(V(0, y1 - y0, 0))
    return fuse_all([cyl_y(r1, x1, z1, y0, y1), cyl_y(r2, x2, z2, y0, y1), quad]).removeSplitter()


def band_dims():
    """Cotas de las aberturas de las bandas que salen de los parametros (para el modelo y el informe)."""
    tp, R = P['costado']['tapa_puertos'], BD['radio_esquinas']
    mt, mo = BD['abajo']['muesca_tapa_puertos'], BD['arriba']['muesca_oled']
    s_tp = side_offset(mt['holgura'], R)
    w = P['frente']['ventana_oled']
    s_o = side_offset(mo['holgura'], R)
    hx = w['x'] + w['bolsillo']['margen'] + s_o
    return {'tapa_puertos': {'angulo_ala': tp['angulos'][0], 'atras': s_tp, 'z_fondo': tp['z'][0] - s_tp,
                             'x_delante': tp['lengueta']['x0'] - mt['una'], 'radio': R},
            'oled': {'x': hx, 'z_arriba': w['z'][1] + w['bolsillo']['margen'] + s_o, 'lados': s_o, 'radio': R}}


def _cover_notch(z_top):
    """Muesca de la banda de abajo alrededor de la tapa de puertos, abierta hacia arriba: detras, un plano
    paralelo al canto de atras del ala (radial a angulo_ala) desplazado `atras`; delante, x >= x_delante
    (sitio para la una); abajo, z >= z_fondo; esquinas de abajo de radio R."""
    d = band_dims()['tapa_puertos']
    a0, s, zb, xf, R = d['angulo_ala'], d['atras'], d['z_fondo'], d['x_delante'], d['radio']
    zt = z_top + 1.0

    def behind(v0, z0):            # p . n0 >= v0, con n0 normal al radio de a0 hacia el frente
        b = box(-60, 60, v0, 60, z0, zt)
        b.rotate(V(), V(0, 0, 1), a0)
        return b
    A = behind(-s, zb + R).common(box(xf, 60, -5, 60, zb + R, zt))
    B = behind(-s + R, zb).common(box(xf + R, 60, -5, 60, zb, zt))
    au = math.radians(a0)
    u0, n0 = V(math.cos(au), math.sin(au), 0), V(-math.sin(au), math.cos(au), 0)
    org = n0 * (-s + R) + u0 * 20.0
    corner_back = Part.makeCylinder(R, 15.0, V(org.x, org.y, zb + R), u0)
    corner_front = cyl_y(R, xf + R, zb + R, 15.0, 35.0)
    return fuse_all([A, B, corner_back, corner_front]).removeSplitter()


def _oled_notch(z_bot):
    """Muesca de la banda de arriba alrededor de la ventana de la OLED y su bolsillo, abierta hacia abajo;
    esquinas de arriba de radio R. Solo corta la parte plana de la banda (|x| < 16.11)."""
    d = band_dims()['oled']
    hx, zt, R = d['x'], d['z_arriba'], d['radio']
    y0, y1 = Y_FLAT_O - 3.0, Y_FLAT_O + 6.0
    return fuse_all([box(-hx, hx, y0, y1, z_bot - 1, zt - R), box(-hx + R, hx - R, y0, y1, z_bot - 1, zt),
                     cyl_y(R, -hx + R, zt - R, y0, y1), cyl_y(R, hx - R, zt - R, y0, y1)]).removeSplitter()


def band_openings(which):
    z0, z1 = band_z(which)
    if which == 'abajo':
        ab = BD['abajo']
        cuts = []
        k, l, vt = P['frente']['tecla'], P['frente']['led'], ab['ventana_tecla']
        cuts.append(_hull2((k['x'], k['z']), vt['diametro_tecla'] / 2.0, (l['x'], l['z']), vt['diametro_led'] / 2.0,
                           Y_FLAT_O - 3.0, Y_FLAT_O + 6.0))
        cuts.append(_cover_notch(z1))
    else:
        cuts = [_oled_notch(z0)]
    return fuse_all(cuts)


def band_screws(which):
    """[(angulo, z)] de los M2.5 radiales que tapa la banda (los de la base o los de la tapa)."""
    if which == 'abajo':
        return [(a, P['base']['tornillos']['z']) for a in P['base']['lenguetas']['angulos']]
    return [(a, P['tapa']['tornillos_z']) for a in P['tapa']['lenguetas']['angulos']]


def screw_head_out():
    """Cuanto asoman sobre la pared curva (R28) los cantos de la cabeza plana de los M2.5 radiales, con su centro a
    ras: hypot(RO, d/2) - RO (0.11 con el avellanado de 5)."""
    return math.hypot(RO, P['base']['tornillos']['avellanado_diametro'] / 2.0) - RO


def band_pockets(which, d_in):
    """Bolsillos ciegos por dentro de la banda sobre cada M2.5 radial: cilindro radial de bolsillos_tornillos.diametro
    hasta un fondo curvo, concentrico con la banda, a `hondo` de su cara de dentro (r RO + d_in): queda espesor - hondo
    de TPU por fuera. Ningun tornillo cae en la cara plana."""
    bt = BD['bolsillos_tornillos']
    r_bottom = RO + d_in + bt['hondo']
    z0, z1 = band_z(which)
    keep = cyl_z(r_bottom, 0, 0, z0 - 1, z1 + 1)
    return fuse_all([_radial_cyl(a, z, bt['diametro'], r0=RO - 3.0, r1=r_bottom + 1.0).common(keep)
                     for a, z in band_screws(which)])


def _on_offset_surface(face, d, tol=2e-3):
    """La cara esta en la superficie lateral a distancia |d| del contorno del cuerpo (tres puntos)."""
    wire = body_section(0.0).OuterWire
    try:
        u0, u1, v0, v1 = face.ParameterRange
        pts = [face.valueAt(u0 + (u1 - u0) * a, v0 + (v1 - v0) * b) for a, b in ((0.25, 0.25), (0.5, 0.5), (0.75, 0.6))]
    except Exception:
        return False
    return all(abs(wire.distToShape(Part.Vertex(V(p.x, p.y, 0)))[0] - abs(d)) < tol for p in pts)


def _edges_on_surface(body, d, z_only=None):
    """Aristas vivas del borde de la superficie lateral a distancia d: las que separan una cara de esa
    superficie de otra que no lo es (cantos libres y bordes de las aberturas). Con z_only, solo las de ese z."""
    ids = set(f.hashCode() for f in body.Faces if _on_offset_surface(f, d))
    out = []
    for e in body.Edges:
        anc = body.ancestorsOfType(e, Part.Face)
        if len(anc) != 2 or sum(1 for f in anc if f.hashCode() in ids) != 1:
            continue
        if z_only is not None:
            bb = e.BoundBox
            if abs(bb.ZMin - z_only) > 1e-4 or abs(bb.ZMax - z_only) > 1e-4:
                continue
        out.append(e)
    return out


def band(which, stretched=False, info=None):
    """Banda de TPU ('abajo' o 'arriba'). Anillo entre el contorno del cuerpo desplazado -apriete (dentro) y
    -apriete + espesor (fuera, con la esquina de la cara plana en arco), recto por dentro en todo su alto (no
    abraza los redondeos R4), menos las aberturas y con bolsillos ciegos por dentro que tapan los M2.5 radiales. Cantos de fuera
    redondeados `redondeo` y canto de dentro que entra primero redondeado `entrada`. Con stretched=True, la
    banda estirada sobre el cuerpo (contorno interior = cuerpo + holgura_barrido, mismo espesor), para los
    barridos. `info` (dict) recibe los redondeos conseguidos."""
    z0, z1 = band_z(which)
    d_in = band_inner_offset(stretched)
    d_out = d_in + BD['espesor']
    ring = body_prism(z0, z1, d_out).cut(body_prism(z0 - 1, z1 + 1, d_in))
    body = clean(ring.cut(band_openings(which)).cut(band_pockets(which, d_in)))
    info = {} if info is None else info
    for key, d, r, z_only in (('fuera', d_out, BD['redondeo'], None),
                              ('dentro_entrada', d_in, BD['entrada'], z1 if which == 'abajo' else z0)):
        edges = _edges_on_surface(body, d, z_only)
        info[key] = {'aristas': len(edges), 'radio_pedido': r, 'radio': None}
        for rr in (r, 0.8 * r, 0.6 * r):
            try:
                f = body.makeFillet(rr, edges)
                if f.isValid() and len(f.Solids) == 1:
                    body = f
                    info[key]['radio'] = round(rr, 3)
                    break
            except Exception as ex:
                info[key]['error'] = str(ex)[:120]
    return clean(body)
