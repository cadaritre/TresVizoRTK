"""Construye la carcasa V3.0 (tubo de 56 x 111 para la placa principal compacta v0.3).

Piezas: 01-base, 02-tube, 03-antenna-cap, 04-chassis, 05-key-tpu, 06-port-cover-tpu, 07-logo-inlay-tpu,
en su posicion final.
Ademas guarda las referencias (placa de la especificacion, carrier, celdas, tuerca, antena,
coaxial, clavijas y cables) como objetos ref_* que no se exportan.

Uso:
  PYTHONPATH=/Applications/FreeCAD.app/Contents/Resources/lib \\
  /Applications/FreeCAD.app/Contents/Resources/bin/python build_v3_0.py [--output-dir generated]
"""
import argparse, json, math, sys
from pathlib import Path

sys.dont_write_bytecode = True

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
import FreeCAD as App
import Part
import geom_v3_0 as G
from geom_v3_0 import P, V, box, cyl_z, cyl_y, cyl_x, sector, fuse_all, clean, polar

ap = argparse.ArgumentParser(description=__doc__)
ap.add_argument('--output-dir', type=Path, default=ROOT / 'generated')
args, _ = ap.parse_known_args()
OUT = args.output_dir.resolve()
OUT.mkdir(parents=True, exist_ok=True)

RO, RI, CLR = G.RO, G.RI, G.CLR
Z0, Z1 = G.Z_TUBE0, G.Z_TUBE1
BASE, CAP, TB = P['base'], P['tapa'], P['tubo']
NUT, RET = BASE['tuerca'], BASE['reten']
ENV = G.outer_envelope()


def slab(z0, z1):
    return box(-40, 40, -40, 40, z0, z1)


def radial_hole(angle, z, d, r_from=RO + 1.0, r_to=0.0):
    """Taladro radial desde r_from hacia dentro hasta r_to."""
    a = math.radians(angle)
    ux, uy = math.cos(a), math.sin(a)
    return Part.makeCylinder(d / 2.0, r_from - r_to, V(ux * r_from, uy * r_from, z), V(-ux, -uy, 0))


def countersink(angle, z, d_head, d_shank):
    """Avellanado a 90 grados desde la cara exterior (r 28) hacia dentro."""
    a = math.radians(angle)
    ux, uy = math.cos(a), math.sin(a)
    h = (d_head - d_shank) / 2.0
    cone = Part.makeCone(d_head / 2.0, d_shank / 2.0, h, V(ux * RO, uy * RO, z), V(-ux, -uy, 0))
    lead = Part.makeCylinder(d_head / 2.0, 2.0, V(ux * (RO + 2.0), uy * (RO + 2.0), z), V(-ux, -uy, 0))
    return cone.fuse(lead)


def tabs(cfg, pilot):
    """Lenguetas que suben/bajan por dentro de la pared, con el piloto del tornillo radial."""
    r0, r1 = cfg['r']
    z0, z1 = cfg['z']
    half = math.degrees(cfg['ancho'] / 2.0 / ((r0 + r1) / 2.0))
    out = []
    for a in cfg['angulos']:
        out.append(sector(r1, r0, z0, z1, a - half, a + half))
    return fuse_all(out)


# --- 01 Base ------------------------------------------------------------------------
def build_base():
    """Disco de 2 mm con la tuerca del baston, anillo del redondeo hasta z 4 y labio del
    escalon de la union; tres lenguetas para los tornillos radiales."""
    t_floor = BASE['espesor']
    lab = TB['laberinto']
    body = ENV.common(slab(-1, t_floor))
    body = body.fuse(ENV.common(slab(t_floor, Z0)).cut(G.interior(t_floor - 1, Z0 + 1)))
    body = body.fuse(G.wall_band(Z0 - 0.01, Z0 + lab['alto_base'], 0.0, lab['ancho']))
    sb = BASE['saliente_tuerca']
    boss = cyl_z(sb['radio'], 0, 0, t_floor - 0.01, sb['z_sup']).common(box(-30, 30, -30, sb['y_max'], 0, 30))
    x, y = polar(RET['radio'], RET['angulo'])
    z_ret = RET.get('refuerzo_z_sup', sb['z_sup'])
    boss = boss.fuse(cyl_z(RET['refuerzo_diametro'] / 2.0, x, y, t_floor - 0.01, z_ret))
    body = body.fuse(boss)
    tb = BASE['lenguetas']
    body = body.fuse(tabs(tb, None))
    nv = BASE['nervios']
    for a in nv['angulos']:
        rib = box(nv['r'][0], nv['r'][1], -nv['ancho'] / 2.0, nv['ancho'] / 2.0, nv['z'][0] - 0.01, nv['z'][1])
        rib.rotate(V(), V(0, 0, 1), a)
        body = body.fuse(rib)
    ring = NUT['anillo_asiento']
    apothem = (NUT['entre_caras'] + NUT['holgura_caras']) / 2.0
    body = body.cut(G.hex_prism(apothem, ring, 30))
    r_hole = NUT['paso_perno_diametro'] / 2.0
    c = NUT['chaflan_paso']
    body = body.cut(cyl_z(r_hole, 0, 0, -1, ring + 0.1))
    body = body.cut(Part.makeCone(r_hole + c + 0.1, r_hole, c + 0.1, V(0, 0, -0.1)))
    # Piloto del reten M2 detras de la tuerca.
    body = body.cut(cyl_z(RET['piloto'] / 2.0, x, y, z_ret - RET['profundidad'], z_ret + 1))
    # Pilotos de los tornillos radiales en las lenguetas.
    ts = BASE['tornillos']
    for a in tb['angulos']:
        body = body.cut(radial_hole(a, ts['z'], ts['piloto'], RO + 1, tb['r'][0] - 0.5))
    dr = BASE['desague']
    body = body.cut(cyl_z(dr['diametro'] / 2.0, dr['x'], dr['y'], -1, t_floor + 0.5))
    return clean(body)


# --- 02 Tubo: pared y aberturas --------------------------------------------------------
def tube_shell():
    body = ENV.common(slab(Z0, Z1)).cut(G.interior(Z0 - 1, Z1 + 1))
    # Ranuras de los rieles del chasis.
    rr = TB['ranuras_rieles']
    for a0, a1 in rr['angulos']:
        body = body.cut(sector(rr['radio'], RI - 0.5, rr['z'][0], Z1 + 1, a0, a1))
    return body


def rebates():
    """Rebajes interiores de 1.2 (labio 0.8 + juego 0.4) en los dos extremos del tubo (uniones)."""
    lab = TB['laberinto']
    w = lab['ancho'] + lab['holgura']
    return fuse_all([G.cavity_offset(Z0 - 1, Z0 + lab['alto_base'] + lab['holgura'], w),
                     G.cavity_offset(Z1 - lab['alto_tapa'] - lab['holgura'], Z1 + 1, w)])


def front_openings():
    """Ventana de la OLED con bolsillo exterior para la lamina y chaflan de entrada por dentro,
    agujero y rebaje de la tecla, y agujero de la guia de luz del LED."""
    fr = P['frente']
    w = fr['ventana_oled']
    x, (za, zb) = w['x'], w['z']
    y_in, y_out = G.Y_FLAT_I, G.Y_FLAT_O
    win = box(-x, x, y_in - 1, y_out + 1, za, zb)
    pk = w['bolsillo']
    m = pk['margen']
    win = win.fuse(box(-x - m, x + m, y_out - pk['hondo'], y_out + 1, za - m, zb + m))
    c = w['chaflan_interior']
    ya, yb = y_in - 0.2, y_in + c
    ea = c + 0.2
    r_a = Part.makePolygon([V(-x - ea, ya, za - ea), V(x + ea, ya, za - ea), V(x + ea, ya, zb + ea),
                            V(-x - ea, ya, zb + ea), V(-x - ea, ya, za - ea)])
    r_b = Part.makePolygon([V(-x, yb, za), V(x, yb, za), V(x, yb, zb), V(-x, yb, zb), V(-x, yb, za)])
    win = win.fuse(Part.makeLoft([r_a, r_b], True))
    k, l = fr['tecla'], fr['led']
    key = cyl_y(k['agujero'] / 2.0, k['x'], k['z'], y_in - 1, y_out + 1)
    rb = k['rebaje']
    key = key.fuse(cyl_y(rb['diametro'] / 2.0, k['x'], k['z'], y_out - rb['hondo'], y_out + 1))
    led = cyl_y(l['agujero'] / 2.0, l['x'], l['z'], y_in - 1, y_out + 1)
    return fuse_all([win, key, led])


def _rr_wire(x, yb, yt, zc, w, r):
    """Contorno (en el plano x) de un rectangulo redondeado de y yb a yt y ancho w en z, radio r."""
    r = max(0.0, min(r, (yt - yb) / 2.0 - 1e-3, w / 2.0 - 1e-3))
    z0, z1 = zc - w / 2.0, zc + w / 2.0
    if r <= 0:
        pts = [V(x, yb, z0), V(x, yb, z1), V(x, yt, z1), V(x, yt, z0), V(x, yb, z0)]
        return Part.makePolygon(pts)
    e = []
    def arc(cy, cz, a0):
        import math as _m
        ps = [V(x, cy + r * _m.sin(_m.radians(a0 + 45 * k)), cz + r * _m.cos(_m.radians(a0 + 45 * k))) for k in range(3)]
        return Part.Arc(ps[0], ps[1], ps[2]).toShape()
    e.append(Part.LineSegment(V(x, yb, z0 + r), V(x, yb, z1 - r)).toShape())
    e.append(arc(yb + r, z1 - r, -90))
    e.append(Part.LineSegment(V(x, yb + r, z1), V(x, yt - r, z1)).toShape())
    e.append(arc(yt - r, z1 - r, 0))
    e.append(Part.LineSegment(V(x, yt, z1 - r), V(x, yt, z0 + r)).toShape())
    e.append(arc(yt - r, z0 + r, 90))
    e.append(Part.LineSegment(V(x, yt - r, z0), V(x, yb + r, z0)).toShape())
    e.append(arc(yb + r, z0 + r, 180))
    return Part.Wire(Part.__sortEdges__(e))


def outer_top_chamfer(yb, yt, zc, w, r, c):
    """Chaflan a 45 grados del canto de fuera de arriba de una abertura del costado +X (techo plano en
    y = yt): el techo salia por la cara exterior en cuna de ~44 grados. Solido reglado entre el contorno
    de la abertura, c por dentro del canto, y el mismo contorno con el techo subido otro tanto fuera."""
    xe = math.sqrt(RO ** 2 - yt ** 2)
    x1, x2 = xe - c, RO + 2.0
    return Part.makeLoft([_rr_wire(x1, yb, yt, zc, w, r), _rr_wire(x2, yb, yt + (x2 - x1), zc, w, r)], True, True)


def inner_bottom_chamfer(yb, yt, zc, w, r, c):
    """Chaflan a 45 grados del canto de dentro de abajo de una abertura con contorno redondeado (el
    suelo corta la cara interior en cuna, tambien en las esquinas redondeadas). Solido reglado entre el
    contorno, c por fuera del canto, y el mismo contorno con el suelo bajado otro tanto ya en el hueco
    interior. No se ve desde fuera."""
    xi = math.sqrt(RI ** 2 - yb ** 2)
    x1, x2 = xi + c, xi - 3.0
    d = x1 - x2
    return Part.makeLoft([_rr_wire(x1, yb, yt, zc, w, r), _rr_wire(x2, yb - d, yt, zc, w, r)], True, True)


def inner_edge_chamfer(y0, z0, z1, c):
    """Chaflan del canto donde el suelo plano (y = y0) de una abertura del costado +X corta la cara
    interior del tubo: ahi queda una cuna de ~53 grados. Quita el triangulo de c de lado (no se ve desde
    fuera)."""
    xe = math.sqrt(RI ** 2 - y0 ** 2)
    ya = y0 - c
    xa = math.sqrt(RI ** 2 - ya ** 2)
    pts = [V(xe + c, y0 + 0.01, z0), V(xa, ya, z0), V(xa - 0.6, ya, z0), V(xe - 0.6, y0 + 0.01, z0)]
    return Part.Face(Part.makePolygon(pts + [pts[0]])).extrude(V(0, 0, z1 - z0))


def side_openings():
    """Costado +X: tunel cerrado de la funda del USB-C (rectangulo redondeado, de la cara exterior a la
    boca de J101), ranura justa de la microSD con su muesca para la una, chaflanes de los cantos de fuera
    de arriba y agujeros de las anclas de la tapa de puertos."""
    cs = P['costado']
    ux0, uyc, uzc, uh, uw, ur = G.usb_tunnel()
    usb = G.rounded_rect_x(ux0, RO + 2, uyc, uzc, uh, uw, ur)
    usb = usb.fuse(outer_top_chamfer(uyc - uh / 2.0, uyc + uh / 2.0, uzc, uw, ur, cs['usb_c']['chaflan_entrada']))
    ci = cs['usb_c'].get('chaflan_interior', 0.0)
    if ci > 0:
        usb = usb.fuse(inner_bottom_chamfer(uyc - uh / 2.0, uyc + uh / 2.0, uzc, uw, ur, ci))
    sx0, sy0, sy1, szc, sw = G.sd_slot()
    mu = cs['microsd']['muesca']
    ch = cs['microsd']['chaflan_entrada']
    slot = box(sx0, RO + 2, sy0, sy1, szc - sw / 2.0, szc + sw / 2.0)
    notch = box(sx0, RO + 2, sy0, mu['y_sup'], szc - mu['ancho'] / 2.0, szc + mu['ancho'] / 2.0)
    cuts = [usb, slot, notch, outer_top_chamfer(sy0, sy1, szc, sw, 0.0, ch), outer_top_chamfer(sy0, mu['y_sup'], szc, mu['ancho'], 0.0, ch)]
    ci = cs['microsd'].get('chaflan_interior', 0.0)
    if ci > 0:
        cuts.append(inner_edge_chamfer(sy0, szc - sw / 2.0, szc + sw / 2.0, ci))
    an = cs['tapa_puertos']['ancla']
    cuts += [radial_hole(an['angulo'], za, an['agujero'], RO + 1.0, RI - 0.5) for za in G.anchor_zs()]
    return fuse_all(cuts)


def screw_holes():
    """Pasos y avellanados de los tornillos radiales de la base y de la tapa."""
    out = []
    for cfg, z in ((BASE['lenguetas'], BASE['tornillos']['z']), (CAP['lenguetas'], CAP['tornillos_z'])):
        ts = BASE['tornillos']
        for a in cfg['angulos']:
            out.append(radial_hole(a, z, ts['paso'], RO + 1, RI - 0.2))
            out.append(countersink(a, z, ts['avellanado_diametro'], ts['paso']))
    return fuse_all(out)


# --- 02 Tubo: interior ----------------------------------------------------------------
def rail_ledges():
    """Repisas bajo las paredes laterales del chasis: su pie (z 9.5) apoya aqui. Nacen de la pared."""
    ap = TB['apoyos_chasis']
    out = [sector(RI + 0.8, ap['r0'], ap['z'][0], ap['z'][1], a0, a1) for a0, a1 in ap['angulos']]
    return fuse_all(out)


def cell_cradle():
    """Cuna del pack 1S2P: tres nervios por extremo redondo (de la pared al pack: costado, atras y un
    labio delante-fuera) que acaban a la holgura de su envolvente, y repisas bajo su parte de fuera."""
    cu, ce = P['cuna'], P['celdas']
    pk = ce['pack']
    nv = cu['nervios']
    t = nv['espesor']
    z0, z1 = nv['z']
    cx0, cy0 = pk['centro']
    a_end = (pk['ancho'] - pk['grueso']) / 2.0
    parts = []
    for sx in (-1.0, 1.0):
        cx, cy = cx0 + sx * a_end, cy0
        for rel in nv['angulos_rel']:
            a = math.radians(rel)
            dx, dy = sx * math.cos(a), math.sin(a)
            rib = box(0, 30.0, -t / 2.0, t / 2.0, z0, nv.get('z_labio', z1) if rel > 0 else z1)
            rib.rotate(V(), V(0, 0, 1), math.degrees(math.atan2(dy, dx)))
            rib.translate(V(cx, cy, 0))
            parts.append(rib)
    rp = cu['repisas']
    for a0, a1 in rp['angulos']:
        parts.append(sector(RI + 0.8, rp['r0'], rp['z'][0], rp['z'][1], a0, a1))
    body = fuse_all(parts).common(cyl_z(RI + 0.8, 0, 0, 0, 100))
    return body.cut(G.pack_solid(ce['z'][0], 200, pk['holgura']))


def decorative_lines():
    """Rayas verticales como las de V2.3: grupos de 5 a 9 grados, simetricos frente-atras."""
    lv = TB.get('lineas_verticales')
    if not lv:
        return None
    half = math.degrees(lv['ancho'] / 2.0 / RO)
    cuts = [sector(RO + 1.0, RO - lv['profundidad'], lv['z'][0], lv['z'][1], a - half, a + half)
            for grupo in lv['grupos'] for a in grupo]
    return fuse_all(cuts)


def build_tube():
    body = tube_shell().cut(rebates())
    body = body.fuse(rail_ledges()).fuse(cell_cradle())
    body = body.cut(front_openings()).cut(side_openings()).cut(screw_holes())
    dl = decorative_lines()
    if dl is not None:
        body = body.cut(dl)
    body = body.cut(G.logo_engrave())
    return clean(body)


# --- 03 Tapa de antena ------------------------------------------------------------------
def build_cap():
    ANT = P['antena']
    body = ENV.common(slab(Z1, G.H_TOTAL + 1))
    lab = TB['laberinto']
    body = body.fuse(G.wall_band(Z1 - lab['alto_tapa'], Z1 + 0.01, 0.0, lab['ancho']))
    tc = CAP['lenguetas']
    body = body.fuse(tabs(tc, None))
    # Topes sobre las celdas: no las dejan subir (0.3 de juego).
    tp = CAP['topes_celdas']
    z_cells = P['celdas']['z'][1]
    for bx_, by_ in tp['puntos']:
        body = body.fuse(cyl_z(tp['diametro'] / 2.0, bx_, by_, z_cells + tp['holgura'], Z1 + 0.01))
    ts = BASE['tornillos']
    for a in tc['angulos']:
        body = body.cut(radial_hole(a, CAP['tornillos_z'], ts['piloto'], RO + 1, tc['r'][0] - 0.5))
    for i in range(ANT['numero_pernos']):
        x, y = polar(ANT['circulo_pernos'] / 2.0, ANT['angulo_inicial'] + i * 360.0 / ANT['numero_pernos'])
        body = body.cut(cyl_z(ANT['perno_paso'] / 2.0, x, y, Z1 - 1, G.H_TOTAL + 1))
        body = body.cut(cyl_z(ANT['avellanado_diametro'] / 2.0, x, y, Z1 - 1, Z1 + ANT['avellanado_cabeza']))
    # Paso del coaxial: Ø12 en el eje, alargado hacia el SMA de la carrier (ranura con dos arcos).
    cn = ANT['conector']
    pm = cn['pasamuros']
    if cn['tipo'] == 'macho':
        # Pasamuros SMA hembra: agujero de 6.5 con cara plana antigiro y rebaje por dentro para la
        # tuerca de 8, que deja el panel en su espesor.
        hole = cyl_z(pm['agujero'] / 2.0, 0, 0, Z1 - 1, G.H_TOTAL + 1)
        flat_y = pm['plano'] - pm['agujero'] / 2.0
        hole = hole.cut(box(-5, 5, flat_y, 5, Z1 - 2, G.H_TOTAL + 2))
        body = body.cut(hole)
        body = body.cut(cyl_z(pm['bolsillo_tuerca'] / 2.0, 0, 0, Z1 - 1, G.H_TOTAL - pm['panel']))
    else:
        body = body.cut(cyl_z(cn['paso_hembra'] / 2.0, 0, 0, Z1 - 1, G.H_TOTAL + 1))
    return clean(body)


# --- 04 Chasis -------------------------------------------------------------------------
def spans_minus(z0, z1, cuts):
    out = [(z0, z1)]
    for ca, cb in cuts:
        nxt = []
        for a, b in out:
            if cb <= a or ca >= b:
                nxt.append((a, b))
                continue
            if ca > a:
                nxt.append((a, ca))
            if cb < b:
                nxt.append((cb, b))
        out = nxt
    return out


def chassis_clip():
    """Paso del chasis: r <= chasis.r_max (25.2, 0.4 al tubo) e y <= cara plana interior - 0.4."""
    CH = P['chasis']
    clip = cyl_z(CH['r_max'], 0, 0, -10, 200)
    for a0, a1 in TB['ranuras_rieles']['angulos']:
        clip = clip.fuse(sector(CH['r_max_ranura'], 0, -10, 200, a0 + 0.6, a1 - 0.6))
    return clip.common(box(-40, 40, -40, G.Y_FLAT_I - CLR, -10, 200))


def build_chassis():
    CH = P['chasis']
    rl, pw, rc = CH['riel'], CH['pared_lateral'], CH['ranura_carrier']
    gk, sb, br, pu = CH['ganchos'], CH['salientes'], CH['brazos'], CH['puente']
    parts, cuts, hook_parts = [], [], []
    for sx in (-1, 1):
        def bx(x0, x1, y0, y1, z0, z1):
            return box(sx * x0, sx * x1, y0, y1, z0, z1)
        z0, z1 = rl['z']
        cut_list = rl['cortes_mas_x'] if sx > 0 else []
        for za, zb in spans_minus(z0, z1, cut_list):
            parts.append(bx(rl['x_dorso'], 26, rl['y_dorso'][0], rl['y_dorso'][1], za, zb))
            parts.append(bx(rl['x_fondo'], 26, rl['y_dorso'][0], rl['y_labio'][1], za, zb))
            parts.append(bx(rl['x_labio'], 26, rl['y_labio'][0], rl['y_labio'][1], za, zb))
        # Tope de la placa sobre el canto de arriba (franja), sin tocar la OLED (|x| <= 13.75).
        parts.append(bx(rl['x_labio'], 26, rl['y_dorso'][0], rl['y_labio'][1], rl['z_tope'], z1))
        # Pared lateral; la de -X acaba en z 83: por encima pasa el coaxial.
        z_top_wall = pw['z'][1] if sx > 0 else pw['corte_coax_menos_x']['z0']
        parts.append(bx(pw['x'][0], pw['x'][1], pw['y'][0], pw['y'][1], pw['z'][0], z_top_wall))
        # Ranura de la carrier, sacada de sus medidas (carrier.x, .z) y del juego (ranura_carrier.holgura).
        ca = P['carrier']
        hh = rc['holgura']
        edge = ca['x'][1] if sx > 0 else -ca['x'][0]
        yb, yf = ca['y'][0], ca['y'][0] + ca['pcb']
        cz0, cz1 = ca['z']
        wx0, wx1 = edge + hh, edge + hh + 1.15
        sy0, sy1 = yb - hh - 0.65, yf + hh + 0.65
        za, zb = cz0 - hh - 0.8, cz1 + hh + 1.0
        parts.append(bx(wx0, pw['x'][0] + 0.01, sy0, sy1, za, zb))
        lz0 = za if sx > 0 else rc['labio_atras_menos_x_desde_z']
        parts.append(bx(edge - rc['labio_atras_solape'], wx0 + 0.01, sy0, yb - hh, lz0, zb))
        parts.append(bx(edge - rc['labio_delante_solape'], wx0 + 0.01, yf + hh, sy1, rc['labio_delante_z'][0], rc['labio_delante_z'][1]))
        parts.append(bx(edge - 1.0, wx0 + 0.01, yb, yf, cz1 + hh, cz1 + hh + 1.0))
        if sx > 0:
            cuts.append(bx(wx0 - 0.3, wx1 + 0.3, rc['sin_pared_delante_mas_x_y'], 12.0, 0, rc['sin_pared_delante_mas_x_hasta_z']))
        else:
            cuts.append(bx(wx0 - 0.3, rc['pared_atras_menos_x'], sy0 - 1, yb + rc['corte_atras_menos_x_y'], 0, rc['labio_atras_menos_x_desde_z']))
        # Gancho flexible al pie de la ranura: brazo separado de la pared y labio bajo el PCB.
        gx0, gx1 = edge - 0.7, wx0 + 0.8
        gy0, gy1 = gk['y']
        hx = gx1 + gk['hueco_detras']
        sl = gk['ranura']
        lip_z = (cz0 - hh - 0.8, cz0 - hh)
        zh0, zh1 = lip_z[0], lip_z[0] + gk['largo']
        hook_cuts = [bx(wx0 - 0.05, hx, gy0 - sl, gy0, zh0 - 1, zh1 + sl),
                     bx(wx0 - 0.05, hx, gy1, gy1 + sl, zh0 - 1, zh1 + sl),
                     bx(gx1, hx, gy0 - sl, gy1 + sl, zh0 - 1, zh1 + sl)]
        cuts.extend(hook_cuts)
        arm = bx(wx0, gx1, gy0, gy1, zh0, zh1 + sl + 0.1)
        lip = bx(gx0, wx0 + 0.01, gy0, gy1, lip_z[0], lip_z[1])
        # Rampa de entrada bajo el labio (la carrier llega desde abajo).
        ramp = Part.Face(Part.makePolygon([V(sx * gx0, gy0, lip_z[1]), V(sx * wx0, gy0, lip_z[0]),
                                           V(sx * gx0, gy0, lip_z[0]), V(sx * gx0, gy0, lip_z[1])]))
        lip = lip.cut(ramp.extrude(V(0, gy1 - gy0, 0)))
        hook_parts.append(arm.fuse(lip).cut(fuse_all(hook_cuts)))
        # Tirador en lo alto de cada pared lateral: lengueta engrosada con agujero para un gancho.
        tr = CH['tirador']
        tz0, tz1 = tr['z'] if sx > 0 else tr['z_menos_x']
        parts.append(bx(tr['x'][0], tr['x'][1], pw['y'][0], pw['y'][1], tz0, tz1))
        cuts.append(cyl_x(tr['agujero'] / 2.0, tr['y_agujero'], (tz0 + tz1) / 2.0, *sorted((sx * 15.0, sx * 30.0))))
        # Saliente M2 de la OLED, detras de la placa, y brazo hasta el puente.
        boss = cyl_y(sb['diametro'] / 2.0, sx * sb['x'], sb['z'], sb['y'][0], sb['y'][1])
        parts.append(boss)
        cuts.append(cyl_y(sb['piloto'] / 2.0, sx * sb['x'], sb['z'], sb['y'][1] - sb['piloto_hondo'], sb['y'][1] + 1))
        parts.append(bx(br['x'][0], br['x'][1], br['y'][0], br['y'][1], br['z'][0], br['z'][1]))
    bridge = box(-pu['x'], pu['x'], pu['y'][0], pu['y'][1], pu['z'][0], pu['z'][1])
    # Esquinas de fuera quitadas: ahi pasan los labios delante-fuera de la cuna de las celdas.
    for sx in (-1, 1):
        bridge = bridge.cut(box(*sorted((sx * pu['esquinas_x'], sx * 30.0)), pu['y'][0] - 1, pw['y'][0], pu['z'][0] - 1, pu['z'][1] + 1))
    mq = pu['muesca']
    bridge = bridge.cut(box(mq['x'][0], mq['x'][1], mq['y_max'], pu['y'][1] + 1, pu['z'][0] - 1, pu['z'][1] + 1))
    vl = pu['ventana_llave']
    bridge = bridge.cut(box(vl['x'][0], vl['x'][1], pu['y'][0] - 1, pu['y'][1] + 1, vl['z'][0], vl['z'][1]))
    parts.append(bridge)
    body = fuse_all(parts).cut(fuse_all(cuts))
    # Los ganchos se suman despues de los cortes de las ranuras (que no se los coman), ya con sus
    # propias ranuras de 0.6 alrededor del brazo.
    body = body.fuse(fuse_all(hook_parts))
    # Sin plastico a menos de 5 mm de la antena del WROOM (riel -X y punta de la pared lateral).
    ct = CH['antena_wroom']['corte']
    body = body.cut(box(ct['x'][0], ct['x'][1], ct['y'][0], ct['y'][1], ct['z'][0], ct['z'][1]))
    return clean(body.common(chassis_clip()))


# --- 05 Tecla de TPU -------------------------------------------------------------------
def build_key():
    """Tecla de TPU que se pone por fuera: pestana pegada (o a presion) en el rebaje exterior,
    membrana de 0.4, cabeza que asoma 1.0 y embolo hasta 0.5 de SW401. Sella el agujero y se saca
    por fuera."""
    tk, fr, pl = P['tecla'], P['frente']['tecla'], P['placa']
    x, z = fr['x'], fr['z']
    y_out = G.Y_FLAT_O
    pe = tk['pestana']
    y_floor = y_out - fr['rebaje']['hondo']
    flange = cyl_y(pe['diametro'] / 2.0, x, z, y_floor, y_out).cut(cyl_y(pe['agujero'] / 2.0, x, z, y_floor - 1, y_out + 1))
    membrane = cyl_y(pe['agujero'] / 2.0 + 0.01, x, z, y_out - tk['membrana'], y_out)
    head = cyl_y(tk['cabeza_diametro'] / 2.0, x, z, y_out - 0.01, y_out + tk['sobresale'])
    y_sw = pl['y_cara'] + pl['boton']['alto']
    plunger = cyl_y(tk['embolo_diametro'] / 2.0, x, z, y_sw + tk['juego_boton'], y_out - tk['membrana'] + 0.01)
    return clean(fuse_all([flange, membrane, head, plunger]))


def build_port_cover():
    """Tapa de TPU atada de los puertos del costado +X: ala curva sobre la pared que tapa el tunel
    del USB-C y la ranura de la microSD, con sus cuerpos a presion por dentro (la forma de las
    aberturas), lengueta delante, bisagra fina y setas de anclaje por agujeros de 2 en la pared."""
    cs = P['costado']
    tp = cs['tapa_puertos']
    e = tp['espesor']
    a0, a1 = tp['angulos']
    za, zb = tp['z']
    parts = [sector(RO + e, RO, za, zb, a0, a1),
             box(tp['x_frente_plano'], math.sqrt(RO ** 2 - G.Y_FLAT_O ** 2) + 0.3, G.Y_FLAT_O, G.Y_FLAT_O + e, za, zb)]
    lg = tp['lengueta']
    parts.append(box(lg['x0'], tp['x_frente_plano'] + 0.01, G.Y_FLAT_O, G.Y_FLAT_O + e + lg['alto'], lg['z'][0], lg['z'][1]))
    ring_usb = cyl_z(RO, 0, 0, 0, 100).cut(cyl_z(tp['cuerpos']['usb_r0'], 0, 0, -1, 101))
    ring_sd = cyl_z(RO, 0, 0, 0, 100).cut(cyl_z(tp['cuerpos']['sd_r0'], 0, 0, -1, 101))
    m = 0.05
    ux0, uyc, uzc, uh, uw, ur = G.usb_tunnel()
    parts.append(G.rounded_rect_x(ux0 + m, RO + 1, uyc, uzc, uh - 2 * m, uw - 2 * m, ur - m).common(ring_usb))
    sx0, sy0, sy1, szc, sw = G.sd_slot()
    mu = cs['microsd']['muesca']
    sdb = box(sx0 + m, RO + 1, sy0 + m, sy1 - m, szc - sw / 2.0 + m, szc + sw / 2.0 - m).fuse(
        box(sx0 + m, RO + 1, sy0 + m, mu['y_sup'] - m, szc - mu['ancho'] / 2.0 + m, szc + mu['ancho'] / 2.0 - m))
    parts.append(sdb.common(ring_sd))
    # Setas de anclaje (una por agujero): vastago por la pared y cabeza con cono de entrada por dentro.
    an = tp['ancla']
    a = math.radians(an['angulo'])
    ux, uy = math.cos(a), math.sin(a)
    inward = V(-ux, -uy, 0)
    # La cara de apoyo de la cabeza es plana y la pared curva: se mete 0.07 para que sus bordes no
    # entren en la pared (a 1.7 del eje la pared esta 0.06 mas lejos).
    r_seat = RI - 0.07
    r_head = r_seat - an['cabeza_alto']
    for za_ in G.anchor_zs():
        def at(r, zz=za_):
            return V(ux * r, uy * r, zz)
        parts.append(Part.makeCylinder(an['vastago'] / 2.0, RO + 0.2 - r_seat, at(RO + 0.2), inward))
        parts.append(Part.makeCylinder(an['cabeza_diametro'] / 2.0, an['cabeza_alto'], at(r_seat), inward))
        parts.append(Part.makeCone(an['cabeza_diametro'] / 2.0, an['vastago'] / 2.0, an['cono'], at(r_head), inward))
    body = fuse_all(parts)
    bz = tp['bisagra']
    body = body.cut(sector(RO + e + 1, RO + bz['espesor'], za - 1, zb + 1,
                           bz['angulo'] - bz['ancho_grados'] / 2.0, bz['angulo'] + bz['ancho_grados'] / 2.0))
    return clean(body)


# --- Documento -------------------------------------------------------------------------
def references():
    refs = {}
    for g, d in (('placa', G.board_envelope()), ('carrier', G.carrier()), ('celdas', G.cells()),
                 ('tuerca', G.nut_and_retainer()), ('antena', G.antenna_and_screws()),
                 ('coaxial', G.coax()[0]), ('clavijas', G.plugs()[0]), ('cables', G.cable_reserves()),
                 ('tornillos', G.case_screws())):
        for k, v in d.items():
            refs[f'{g}: {k}'] = v
    refs['usb: funda de la clavija'] = G.usb_overmold()
    refs['microsd: tarjeta puesta'] = G.microsd_card()
    return refs


def main():
    pieces = [('01_base', 'Base con la tuerca del baston', build_base()),
              ('02_tube', 'Tubo', build_tube()),
              ('03_antenna_cap', 'Tapa de antena', build_cap()),
              ('04_chassis', 'Chasis', build_chassis()),
              ('05_key_tpu', 'Tecla de TPU', build_key()),
              ('06_port_cover_tpu', 'Tapa de puertos de TPU', build_port_cover()),
              ('07_logo_inlay_tpu', 'Distintivo de TPU para el grabado', G.logo_inlay())]
    doc = App.newDocument('TresVizo_V3_0')
    index = {'piezas': [], 'referencias': []}
    for name, label, shape in pieces:
        o = doc.addObject('Part::Feature', name)
        o.Label, o.Shape = label, shape
        try:
            bb = shape.optimalBoundingBox()
        except Exception:
            bb = shape.BoundBox
        index['piezas'].append({'nombre': name.replace('_', '-'), 'etiqueta': label, 'valida': shape.isValid(),
                                'solidos': len(shape.Solids), 'volumen_cm3': round(shape.Volume / 1000, 2),
                                'caja': [round(v, 2) for v in (bb.XMin, bb.XMax, bb.YMin, bb.YMax, bb.ZMin, bb.ZMax)]})
        print(name, shape.isValid(), len(shape.Solids), round(shape.Volume, 1))
    for i, (k, v) in enumerate(references().items()):
        o = doc.addObject('Part::Feature', f'ref_{i:02d}')
        o.Label, o.Shape = 'Ref: ' + k, v
        index['referencias'].append(k)
    _, R = G.coax()
    index['coaxial_radio_curva'] = round(R, 2)
    index['clavijas_origen'] = G.plugs()[1]
    doc.recompute()
    target = OUT / 'TresVizo-V3.0.FCStd'
    if target.exists():
        target.unlink()   # sin copia .FCBak
    doc.saveAs(str(target))
    (OUT / 'model-index.json').write_text(json.dumps(index, indent=1, ensure_ascii=False), encoding='utf-8')
    print('guardado', OUT / 'TresVizo-V3.0.FCStd')


if __name__ == '__main__':
    main()
