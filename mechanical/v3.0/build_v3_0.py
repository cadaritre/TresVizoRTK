"""Construye la carcasa V3.0 (tubo de 52 x 100 para la placa principal compacta v0.3).

Piezas: 01-base, 02-tube, 03-antenna-cap, 04-chassis, 05-key-tpu, en su posicion final.
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
    """Avellanado a 90 grados desde la cara exterior (r 26) hacia dentro."""
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
    boss = boss.fuse(cyl_z(RET['refuerzo_diametro'] / 2.0, x, y, t_floor - 0.01, sb['z_sup']))
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
    body = body.cut(cyl_z(RET['piloto'] / 2.0, x, y, sb['z_sup'] - RET['profundidad'], sb['z_sup'] + 1))
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
    """Rebajes interiores de 0.9 en los dos extremos del tubo (escalon de las uniones)."""
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


def side_openings():
    """Tunel de la funda del USB-C y ranura de la microSD con rebaje para la una (+X)."""
    cs = P['costado']
    u = cs['usb_c']
    usb = box(u['x0'], RO + 2, u['y'][0], u['y'][1], u['z_centro'] - u['medio_alto'],
              u['z_centro'] + u['medio_alto'])
    sd = cs['microsd']
    zc, w = sd['z_centro'], sd['ancho']
    slot = box(15.5, RO + 2, sd['y'][0], sd['y'][1], zc - w / 2.0, zc + w / 2.0)
    nl = sd['una']
    y_e = sd['y'][1]
    x_out = math.sqrt(RO ** 2 - y_e ** 2)
    nail = cyl_z(nl['radio'], x_out + nl['radio'] - nl['hondo'], y_e, zc - nl['alto'] / 2.0, zc + nl['alto'] / 2.0)
    return fuse_all([usb, slot, nail])


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
    """Repisa en el fondo de cada ranura: el pie del riel del chasis apoya aqui."""
    rr, rp = TB['ranuras_rieles'], TB['repisas_rieles']
    pl = P['placa']
    out = []
    for a0, a1 in rr['angulos']:
        out.append(sector(rp['r'][1], rp['r'][0], rp['z'][0], rp['z'][1], a0, a1))
    led = fuse_all(out)
    m = CLR
    led = led.cut(box(-pl['x'] - m, pl['x'] + m, pl['y_dorso'] - m, pl['y_cara'] + m, 0, 100))
    # Delante de la placa, fuera de la envolvente de componentes y de las clavijas.
    xs = pl['x'] - pl['franja'] + m
    return led.cut(box(-xs, xs, pl['y_cara'] - m, 30, 0, 100))


def cell_cradle():
    """Nervios de la cuna (tres por celda, de la pared a la celda) y repisas bajo las celdas."""
    cu, ce = P['cuna'], P['celdas']
    rc = ce['diametro'] / 2.0 + ce['holgura']
    nv = cu['nervios']
    t = nv['espesor']
    z0, z1 = nv['z']
    parts = []
    for cx, cy in ce['ejes']:
        sx = 1.0 if cx > 0 else -1.0
        for rel in nv['angulos_rel']:
            a = math.radians(rel)
            dx, dy = sx * math.cos(a), math.sin(a)
            L = 30.0
            # Caja a lo largo de la direccion (dx, dy) desde el eje de la celda.
            rib = box(0, L, -t / 2.0, t / 2.0, z0, z1)
            rib.rotate(V(), V(0, 0, 1), math.degrees(math.atan2(dy, dx)))
            rib.translate(V(cx, cy, 0))
            parts.append(rib)
    rp = cu['repisas']
    for a0, a1 in rp['angulos']:
        parts.append(sector(RI + 0.8, rp['r0'], rp['z'][0], rp['z'][1], a0, a1))
    body = fuse_all(parts).common(cyl_z(RI + 0.8, 0, 0, 0, 100))
    for cx, cy in ce['ejes']:
        body = body.cut(cyl_z(rc, cx, cy, ce['z'][0], 200))
    return body


def build_tube():
    body = tube_shell().cut(rebates())
    body = body.fuse(rail_ledges()).fuse(cell_cradle())
    body = body.cut(front_openings()).cut(side_openings()).cut(screw_holes())
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
    rp = ANT['paso_coaxial'] / 2.0
    c = P['coaxial']['clavija']
    ext = ANT.get('paso_coaxial_alargado', 0.0)
    ang = math.atan2(c['y'], c['x'])
    ux, uy = math.cos(ang), math.sin(ang)
    nx, ny = -uy, ux
    a0, a1 = V(0, 0, Z1 - 1), V(ux * ext, uy * ext, Z1 - 1)
    e = [Part.Arc(a0 + V(nx, ny, 0) * rp, a0 - V(ux, uy, 0) * rp, a0 - V(nx, ny, 0) * rp),
         Part.LineSegment(a0 - V(nx, ny, 0) * rp, a1 - V(nx, ny, 0) * rp),
         Part.Arc(a1 - V(nx, ny, 0) * rp, a1 + V(ux, uy, 0) * rp, a1 + V(nx, ny, 0) * rp),
         Part.LineSegment(a1 + V(nx, ny, 0) * rp, a0 + V(nx, ny, 0) * rp)]
    stadium = Part.Face(Part.Wire([g.toShape() for g in e])).extrude(V(0, 0, G.H_TOTAL - Z1 + 2))
    body = body.cut(stadium)
    bo = CAP['bolsillo_oled']
    body = body.cut(box(-bo['x'], bo['x'], bo['y'][0], bo['y'][1], Z1 - 1, bo['z_techo']))
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
    """Paso del chasis: r 23.9, y r 24.5 dentro de las ranuras del tubo (con 0.5 grados de holgura)."""
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
        parts.append(bx(pw['x'][0], pw['x'][1], pw['y'][0], pw['y'][1], pw['z'][0], pw['z'][1]))
        # Ranura de la carrier.
        za, zb = rc['z']
        wx0, wx1 = rc['x_pared']
        parts.append(bx(wx0, pw['x'][0] + 0.01, rc['y'][0], rc['y'][1], za, zb))
        lz0 = za if sx > 0 else rc['labio_atras_menos_x_desde_z']
        parts.append(bx(rc['labio_atras_x'], wx0 + 0.01, rc['labio_atras_y'][0], rc['labio_atras_y'][1], lz0, zb))
        parts.append(bx(rc['labio_delante_x'], wx0 + 0.01, rc['labio_delante_y'][0], rc['labio_delante_y'][1],
                        rc['labio_delante_z'][0], rc['labio_delante_z'][1]))
        ca = P['carrier']
        yb, yf = ca['y'][0], ca['y'][0] + ca['pcb']
        parts.append(bx(rc['labio_delante_x'], wx0 + 0.01, yb, yf, rc['tope_z'][0], rc['tope_z'][1]))
        if sx > 0:
            cuts.append(bx(wx0 - 0.3, wx1 + 0.3, rc['sin_pared_delante_mas_x_y'], 12.0, 0, rc['sin_pared_delante_mas_x_hasta_z']))
        else:
            cuts.append(bx(wx0 - 0.3, rc['pared_atras_menos_x'], rc['y'][0] - 1, yb + 0.15, 0, rc['labio_atras_menos_x_desde_z']))
        # Gancho flexible al pie de la ranura: brazo separado de la pared y labio bajo el PCB.
        gx0, gx1 = gk['x']
        gy0, gy1 = gk['y']
        hx = gx1 + gk['hueco_detras']
        sl = gk['ranura']
        zh0, zh1 = gk['labio_z'][0], gk['z'][1]
        hook_cuts = [bx(wx0 - 0.05, hx, gy0 - sl, gy0, zh0 - 1, zh1 + sl),
                     bx(wx0 - 0.05, hx, gy1, gy1 + sl, zh0 - 1, zh1 + sl),
                     bx(gx1, hx, gy0 - sl, gy1 + sl, zh0 - 1, zh1 + sl)]
        cuts.extend(hook_cuts)
        arm = bx(wx0, gx1, gy0, gy1, zh0, zh1 + sl + 0.1)
        lip = bx(gx0, wx0 + 0.01, gy0, gy1, gk['labio_z'][0], gk['labio_z'][1])
        # Rampa de entrada bajo el labio (la carrier llega desde abajo).
        ramp = Part.Face(Part.makePolygon([V(sx * gx0, gy0, gk['labio_z'][1]), V(sx * wx0, gy0, gk['labio_z'][0]),
                                           V(sx * gx0, gy0, gk['labio_z'][0]), V(sx * gx0, gy0, gk['labio_z'][1])]))
        lip = lip.cut(ramp.extrude(V(0, gy1 - gy0, 0)))
        hook_parts.append(arm.fuse(lip).cut(fuse_all(hook_cuts)))
        # Tirador en lo alto de la pared lateral: lengueta engrosada con agujero.
        tr = CH['tirador']
        tab = bx(tr['x'][0], tr['x'][1], pw['y'][0], pw['y'][1], tr['z'][0], tr['z'][1])
        parts.append(tab)
        cuts.append(cyl_x(tr['agujero'] / 2.0, tr['y_agujero'], tr['z_agujero'], -30, 30))
        # Saliente M2 de la OLED, detras de la placa, y brazo hasta el puente.
        boss = cyl_y(sb['diametro'] / 2.0, sx * sb['x'], sb['z'], sb['y'][0], sb['y'][1])
        parts.append(boss)
        cuts.append(cyl_y(sb['piloto'] / 2.0, sx * sb['x'], sb['z'], sb['y'][1] - sb['piloto_hondo'], sb['y'][1] + 1))
        parts.append(bx(br['x'][0], br['x'][1], br['y'][0], br['y'][1], br['z'][0], br['z'][1]))
    bridge = box(-pu['x'], pu['x'], pu['y'][0], pu['y'][1], pu['z'][0], pu['z'][1])
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
    membrana de 0.4, cabeza que asoma 1.0 y embolo hasta 0.35 de SW401. Sella el agujero y se saca
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


def build_plug(kind):
    """Tapon de TPU: cuerpo que llena la abertura (sin holgura nominal: ajuste a presion del TPU),
    ala curva sobre la pared y lengueta para tirar. kind = 'usb_c' o 'microsd'."""
    cs = P['costado']
    tp = cs['tapones_tpu']
    ea, m = tp['espesor_ala'], tp['margen_ala']
    if kind == 'usb_c':
        u = cs['usb_c']
        tpn = u['tapon']
        za, zb = u['z_centro'] - u['medio_alto'] + 0.1, u['z_centro'] + u['medio_alto'] - 0.1
        body = box(tpn['x0'], RO + 1, tpn['y'][0], tpn['y'][1], za, zb)
        a0 = math.degrees(math.asin(u['y'][0] / RO))
        a1 = math.degrees(math.asin(G.Y_FLAT_O / RO)) - 1.0
    else:
        sd = cs['microsd']
        za, zb = sd['z_centro'] - sd['ancho'] / 2.0 + 0.05, sd['z_centro'] + sd['ancho'] / 2.0 - 0.05
        body = box(sd['tapon']['x0'], RO + 1, sd['y'][0] + 0.05, sd['y'][1] - 0.05, za, zb)
        a0 = math.degrees(math.asin(sd['y'][0] / RO))
        a1 = math.degrees(math.asin((sd['y'][1] + sd['una']['radio']) / RO)) + 1.0
    body = body.common(cyl_z(RO, 0, 0, 0, 100))
    dm = math.degrees(m / RO)
    wing = sector(RO + ea, RO, za - m, zb + m, a0 - dm, a1)
    L, Wt, T = tp['lengueta']
    am = (a0 + a1) / 2.0
    dw = math.degrees(Wt / 2.0 / RO)
    if kind == 'usb_c':
        tab = sector(RO + T, RO, za - m - L, za - m + 0.01, am - dw, am + dw)
    else:
        tab = sector(RO + T, RO, zb + m - 0.01, zb + m + L, am - dw, am + dw)
    return clean(fuse_all([body, wing, tab]))


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
              ('06_usb_plug_tpu', 'Tapon de TPU del USB-C', build_plug('usb_c')),
              ('07_sd_plug_tpu', 'Tapon de TPU de la microSD', build_plug('microsd'))]
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
