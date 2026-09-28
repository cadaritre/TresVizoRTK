"""Meridian3: carcasa del receptor sencillo (ESP32-S3-Tiny + carrier UM980 +
helice HA-901A, alimentado por un power bank externo por USB-C).

Derivado de build_v2_1.py. Se conserva de V2.1:
  - bayoneta dibujada CERRADA, ranura superior simetrica: base y tapa cierran
    girando la pieza de arriba en sentido horario visto desde arriba, y el
    seguro de las tres piezas cae en el mismo angulo;
  - trineo con pie atornillado, pestanas, perfil en U y un disco arriba que el
    cuello de la tapa recoge y centra (aqui un anillo: ya no hay IMU);
  - avellanado real en los tornillos del panel;
  - tornilleria elegida por bom.py con largos que no pasan de sus pilotos.

Cambia:
  - diametro de V2 (54);
  - sin bateria, IMU, microSD, radio, panel auxiliar ni barrenos de accesorios;
  - la tapa del panel solo lleva la abertura del USB-C y, por dentro, una
    repisa con cuatro torres M2 para la Tiny-Adapter, cuyo receptaculo queda
    alineado con la abertura por construccion;
  - la altura sale de stack.py, no de un parametro.

Piezas: 01 base, 02 tubo, 03 tapa de antena, 04 trineo, 05 tapa del panel.
Ademas guarda en el FCStd, con nombre ref_*, las envolventes de lo que va
dentro (carrier, Tiny, Tiny-Adapter, latiguillo). No se imprimen.

Uso:
  <python de FreeCAD> build_meridian3.py [--output-dir generated]
"""
from pathlib import Path
import argparse, json, math, sys

import FreeCAD as App
import Part

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
import stack as S  # noqa: E402

ap = argparse.ArgumentParser(description=__doc__)
ap.add_argument('--output-dir', type=Path, default=ROOT / 'generated')
# parse_known_args: freecadcmd anade su propio argumento al lanzar el script.
args, _ = ap.parse_known_args()
OUT = args.output_dir.resolve()
OUT.mkdir(parents=True, exist_ok=True)

P, C = S.P, S.C
V = App.Vector

TUBE, GRID, SLED = P['tubo'], P['rejilla_anclaje'], P['trineo']
ANT, INS = P['antena'], P['inserto_jalon']
BAY, LOCK, PAN = P['bayoneta'], P['seguro'], P['panel']
LOGO, PR = P['logo'], P['impresion']

RO, RI = S.RO, S.RI
CLR = PR['holgura_general']
R_COLLAR, R_SPIGOT = S.R_COLLAR, S.R_SPIGOT
Z_FLANGE_TOP, Z_FLOOR = S.Z_FLANGE_TOP, S.Z_FLOOR
Z_TUBE0, Z_TUBE1, Z_TOP = S.Z_TUBE0, S.Z_TUBE1, S.Z_TOP

N_TEETH = BAY['numero_dientes']
TOOTH_H, TOOTH_A = BAY['diente_alto'], BAY['diente_largo_grados']
TRAVEL_A, BAY_CLR = BAY['tope_grados'], BAY['holgura']
COLLAR_T, COLLAR_H = BAY['collar_espesor'], BAY['collar_altura']
R_TOOTH = R_SPIGOT + TOOTH_H
R_GROOVE = R_TOOTH + BAY_CLR
GROOVE_START = -(TOOTH_A + 4) / 2.0
GROOVE_SPAN = TOOTH_A + TRAVEL_A + 2 * BAY_CLR
# Giro real de cierre (28.7, no 30): la entrada tiene 2 grados de mas y la
# holgura suma 0.7. Base, trineo y tapa se dibujan CERRADOS, girados esto.
GIRO_CIERRE = GROOVE_START + GROOVE_SPAN - TOOTH_A / 2.0
BOSS_BITE = 0.8

SIGN_BASE = 1
SIGN_CAP = -1 if BAY.get('tapa_cierra_horario', False) else 1

Z_LOCK_BASE, Z_LOCK_CAP = S.Z_LOCK_BASE, S.Z_LOCK_CAP
Z_NECK_BOTTOM = S.Z_NECK_BOTTOM


def sector(r_out, r_in, z, h, a0, sweep):
    outer = Part.makeCylinder(r_out, h, V(0, 0, z), V(0, 0, 1), sweep)
    outer.rotate(V(), V(0, 0, 1), a0)
    if r_in <= 0:
        return outer
    inner = Part.makeCylinder(r_in, h + 2, V(0, 0, z - 1), V(0, 0, 1), sweep)
    inner.rotate(V(), V(0, 0, 1), a0)
    return outer.cut(inner)


def tube_ring(r_out, r_in, z, h):
    ring = Part.makeCylinder(r_out, h, V(0, 0, z))
    if r_in <= 0:
        return ring
    return ring.cut(Part.makeCylinder(r_in, h + 2, V(0, 0, z - 1)))


def undercut_chamfer(shape, r_outer, depth, z_base):
    """Chaflan a 45 grados bajo un saliente interior: imprimiendo el tubo de
    pie, su cara inferior cuelga; a 45 grados se autosoporta."""
    if not TUBE.get('chaflan_voladizos', True) or depth <= 0:
        return shape
    void = Part.makeCone(r_outer, max(r_outer - depth, 0.01), depth, V(0, 0, z_base))
    return shape.cut(void)


def clean(shape):
    shape = shape.removeSplitter()
    solids = [s for s in shape.Solids if s.Volume >= 0.05]
    if len(solids) > 1:
        return Part.makeCompound(solids).removeSplitter()
    return solids[0] if solids else shape


def radial_tool(radius, depth, angle_deg, z):
    """Cilindro radial que entra desde 2 mm fuera de la pared."""
    a = math.radians(angle_deg)
    ux, uy = math.cos(a), math.sin(a)
    start = RO + 2
    return Part.makeCylinder(radius, depth, V(ux * start, uy * start, z), V(-ux, -uy, 0))


def box(x0, x1, y0, y1, z0, z1):
    return Part.makeBox(x1 - x0, y1 - y0, z1 - z0, V(x0, y0, z0))


def rounded_rect_prism(width, height, radius, y0, y1, zc, xc=0.0):
    """Prisma de seccion rectangular con esquinas redondeadas, a lo largo de Y."""
    r = min(radius, width / 2, height / 2)
    core = box(xc - width / 2 + r, xc + width / 2 - r, y0, y1, zc - height / 2, zc + height / 2)
    core = core.fuse(box(xc - width / 2, xc + width / 2, y0, y1, zc - height / 2 + r, zc + height / 2 - r))
    for sx in (-1, 1):
        for sz in (-1, 1):
            core = core.fuse(Part.makeCylinder(r, y1 - y0,
                                               V(xc + sx * (width / 2 - r), y0, zc + sz * (height / 2 - r)),
                                               V(0, 1, 0)))
    return core.removeSplitter()


# --- Bayoneta -------------------------------------------------------------------
def bayonet_groove(z_entry, h_entry, z_groove, sign=1):
    cuts = []
    for i in range(N_TEETH):
        a = i * 360.0 / N_TEETH
        start = GROOVE_START if sign > 0 else -(GROOVE_START + GROOVE_SPAN)
        cuts.append(sector(R_GROOVE, R_SPIGOT - 2, z_groove, TOOTH_H + 2 * BAY_CLR,
                           a + start, GROOVE_SPAN))
        cuts.append(sector(R_GROOVE, R_SPIGOT - 2, z_entry, h_entry,
                           a - (TOOTH_A + 4) / 2.0, TOOTH_A + 4))
    shape = cuts[0]
    for c in cuts[1:]:
        shape = shape.fuse(c)
    return shape


def bayonet_teeth(z_tooth, sign=1):
    """Dientes en posicion CERRADA: contra el fondo de su ranura."""
    teeth = []
    for i in range(N_TEETH):
        a = i * 360.0 / N_TEETH + sign * GIRO_CIERRE
        teeth.append(sector(R_TOOTH, R_SPIGOT - 1, z_tooth, TOOTH_H,
                            a - TOOTH_A / 2.0, TOOTH_A))
    shape = teeth[0]
    for t in teeth[1:]:
        shape = shape.fuse(t)
    return shape


Z_TOOTH_BASE = Z_TUBE0 + 4.0
Z_TOOTH_CAP = Z_TUBE1 - 8.0


# --- Trineo: formas compartidas por la base (ranuras) y el trineo (pestanas) ----
def tab_boxes(grow=0.0, extra_h=0.0):
    """Pestanas bajo el trineo. grow/extra_h dan las ranuras de la base."""
    tabs = SLED['pestanas']
    t = SLED['espesor']
    out = []
    y0, y1 = S.PLATE_Y0 - grow / 2, S.PLATE_Y1 + grow / 2
    for tx in tabs['placa_x']:
        w = tabs['ancho'] + grow
        out.append(box(tx - w / 2, tx + w / 2, y0, y1,
                       S.Z_FLOOR - tabs['alto'] - extra_h, S.Z_FLOOR))
    if tabs.get('bajo_alas'):
        wing = SLED['alas']
        for sign in (-1, 1):
            xa = sign * wing['x_interior']
            xb = sign * (wing['x_interior'] + wing['espesor'])
            x0, x1 = min(xa, xb) - grow / 2, max(xa, xb) + grow / 2
            out.append(box(x0, x1, S.PLATE_Y0 - wing['profundidad'] - grow / 2,
                           S.PLATE_Y0 + grow / 2,
                           S.Z_FLOOR - tabs['alto'] - extra_h, S.Z_FLOOR))
    return out


# --- Pieza 1: base con rosca -------------------------------------------------------
def build_base():
    ch = TUBE['chaflan_inferior']
    body = Part.makeCone(RO - ch, RO, ch, V(0, 0, 0))
    body = body.fuse(Part.makeCylinder(RO, Z_TUBE0 - ch, V(0, 0, ch)))
    body = body.fuse(tube_ring(R_SPIGOT, 0, Z_TUBE0, Z_FLOOR - Z_TUBE0))
    body = body.fuse(bayonet_teeth(Z_TOOTH_BASE, SIGN_BASE))

    body = body.cut(Part.makeCylinder(INS['barril_diametro'] / 2 + INS['holgura'] / 2,
                                      INS['barril_altura'] + 0.2, V(0, 0, -0.1)))
    body = body.cut(Part.makeCylinder(INS['brida_diametro'] / 2 + INS['holgura'] / 2,
                                      INS['brida_espesor'] + 0.1,
                                      V(0, 0, INS['barril_altura'])))
    body = body.cut(Part.makeCylinder(INS['paso_libre_macho_radio'], Z_FLOOR + 1,
                                      V(0, 0, Z_FLANGE_TOP - 0.1)))
    r = INS['radio_pilotos']
    for i in range(3):
        a = math.radians(90 + i * 120)
        x, y = r * math.cos(a), r * math.sin(a)
        if INS['capturar_sin_tornillos']:
            body = body.fuse(Part.makeCylinder(INS['piloto_diametro'] / 2,
                                               INS['brida_espesor'] + 1.4,
                                               V(x, y, INS['barril_altura'])))
        else:
            body = body.cut(Part.makeCylinder(1.25, Z_FLOOR + 1,
                                              V(x, y, INS['barril_altura'])))

    body = body.cut(radial_tool(LOCK['piloto'] / 2, LOCK['profundidad_base'],
                                LOCK['angulo'], Z_LOCK_BASE))
    tabs = SLED['pestanas']
    for b in tab_boxes(grow=tabs['holgura'], extra_h=0.3):
        body = body.cut(b)
    foot = SLED['pie']
    for fx, fy in foot['tornillos']:
        body = body.cut(Part.makeCylinder(foot['tornillo_piloto'] / 2,
                                          foot['tornillo_profundidad'] + 0.1,
                                          V(fx, fy, Z_FLOOR - foot['tornillo_profundidad'])))
    return clean(body)


# --- Pieza 2: tubo -------------------------------------------------------------------
def panel_angles(cfg):
    a0 = cfg['angulo'] - cfg['arco_grados'] / 2.0
    return a0, cfg['arco_grados']


def panel_frame(cfg):
    a0, sweep = panel_angles(cfg)
    z0 = S.PANEL_Z - cfg['alto'] / 2.0
    lip_z, lip_a = cfg['reborde_z'], cfg['reborde_arco']
    dlip = math.degrees(lip_a / RI)
    pad_t = cfg['engrosamiento']
    pad = sector(RI, RI - pad_t, z0 - lip_z, cfg['alto'] + 2 * lip_z,
                 a0 - dlip, sweep + 2 * dlip)
    pad = undercut_chamfer(pad, RI, pad_t, z0 - lip_z)
    rebate = sector(RO + 1, RO - cfg['espesor'], z0, cfg['alto'], a0, sweep)
    window = sector(RO + 1, RI - pad_t - 1, z0 + lip_z, cfg['alto'] - 2 * lip_z,
                    a0 + dlip, sweep - 2 * dlip)
    return pad, rebate, window


def build_tube(logo_shape):
    body = tube_ring(RO, RI, Z_TUBE0, Z_TUBE1 - Z_TUBE0)
    body = body.fuse(tube_ring(RI, R_COLLAR, Z_TUBE0, COLLAR_H))
    top_collar = tube_ring(RI, R_COLLAR, Z_TUBE1 - COLLAR_H, COLLAR_H)
    top_collar = undercut_chamfer(top_collar, RI, COLLAR_T, Z_TUBE1 - COLLAR_H)
    body = body.fuse(top_collar)
    body = body.cut(bayonet_groove(Z_TUBE0 - 1, 6.0, Z_TOOTH_BASE - BAY_CLR, SIGN_BASE))
    body = body.cut(bayonet_groove(Z_TUBE1 - 6.0, 7.0, Z_TOOTH_CAP - BAY_CLR, SIGN_CAP))

    pad, rebate, window = panel_frame(PAN)
    body = body.fuse(pad)
    body = body.cut(rebate).cut(window)
    half = PAN['tornillo_separacion_z'] / 2
    for dz in (-half, half):
        body = body.cut(radial_tool(PAN['tornillo_piloto'] / 2, TUBE['pared'] + 12,
                                    PAN['angulo'], S.PANEL_Z + dz))

    through = (RO + 2) - (R_COLLAR - 1.5)
    for z in (Z_LOCK_BASE, Z_LOCK_CAP):
        body = body.cut(radial_tool(LOCK['paso_libre'] / 2, through, LOCK['angulo'], z))
        body = body.cut(radial_tool(LOCK['cabeza_diametro'] / 2,
                                    LOCK['cabeza_profundidad'] + 2, LOCK['angulo'], z))

    gw, gd = TUBE['ranura_decorativa_ancho'], TUBE['ranura_decorativa_profundidad']
    zs = list(TUBE['ranuras_decorativas_z'])
    zs += [Z_TUBE1 - d for d in TUBE['ranuras_decorativas_bajo_borde']]
    for z in zs:
        if Z_TUBE0 + 2 < z < Z_TUBE1 - 2:
            body = body.cut(tube_ring(RO + 1, RO - gd, z - gw / 2, gw))

    vert = TUBE['lineas_verticales']
    z0, z1 = vert['z_desde'], Z_TUBE1 - vert['z_hasta_bajo_borde']
    dsweep = math.degrees(vert['ancho'] / RO)
    for angle in vert['angulos']:
        body = body.cut(sector(RO + 1, RO - vert['profundidad'], z0, z1 - z0,
                               angle - dsweep / 2, dsweep))
    if logo_shape is not None:
        body = body.cut(logo_shape).removeSplitter()
    return clean(body)


# --- Pieza 3: tapa de antena -----------------------------------------------------------
def build_cap():
    z0 = Z_NECK_BOTTOM
    neck_ri = S.NECK_RI
    body = Part.makeCylinder(RO, Z_TOP - Z_TUBE1, V(0, 0, Z_TUBE1))
    body = body.fuse(tube_ring(R_SPIGOT, neck_ri, z0, Z_TUBE1 - z0))
    body = body.fuse(bayonet_teeth(Z_TOOTH_CAP, SIGN_CAP))
    body = body.cut(tube_ring(RO + 1, RO - 1.2, Z_TOP - 1.2, 1.3))

    for i in range(ANT['numero_pernos']):
        a = math.radians(ANT['angulo_inicial'] + i * 360.0 / ANT['numero_pernos'])
        r = ANT['circulo_pernos'] / 2
        body = body.cut(Part.makeCylinder(ANT['perno_paso'] / 2, ANT['espesor_tapa'] + 2,
                                          V(r * math.cos(a), r * math.sin(a),
                                            Z_TOP - ANT['espesor_tapa'] - 1)))
    body = body.cut(Part.makeCylinder(ANT['paso_coaxial'] / 2, Z_TOP - z0 + 2,
                                      V(0, 0, z0 - 1)))
    lead = BAY.get('chaflan_entrada_cuello', 0.0)
    if lead > 0:
        body = body.cut(Part.makeCone(neck_ri + lead, neck_ri, lead, V(0, 0, z0 - 0.01)))

    a = math.radians(LOCK['angulo'])
    ux, uy = math.cos(a), math.sin(a)
    boss = Part.makeCylinder(3.5, LOCK['boss_largo'],
                             V(ux * (R_SPIGOT - BOSS_BITE), uy * (R_SPIGOT - BOSS_BITE),
                               Z_LOCK_CAP), V(-ux, -uy, 0))
    # No puede subir por encima de la cara inferior de la tapa ni bajar al
    # paso del coaxial.
    boss = boss.common(Part.makeCylinder(R_SPIGOT, Z_TUBE1 - z0, V(0, 0, z0)))
    body = body.fuse(boss.cut(Part.makeCylinder(ANT['paso_coaxial'] / 2 + 0.5, 80,
                                                V(0, 0, z0 - 1))))
    body = body.cut(radial_tool(LOCK['piloto'] / 2, LOCK['profundidad_tapa'],
                                LOCK['angulo'], Z_LOCK_CAP))
    return clean(body)


# --- Pieza 4: trineo -----------------------------------------------------------------
def grid_rows():
    rows = []
    z = S.Z_FOOT_TOP + GRID['inicio']
    while z < S.Z_PLATE_TOP - GRID['ranura_alto'] / 2 - 1.5:
        rows.append(z)
        z += GRID['paso_longitudinal']
    return rows


def ffc_slot_z():
    return S.Z_CAR1 + SLED['paso_ffc']['z_sobre_carrier']


def build_sled():
    t = SLED['espesor']
    y0, y1 = S.PLATE_Y0, S.PLATE_Y1
    foot = SLED['pie']
    ft = foot['espesor']
    z0, z1 = Z_FLOOR, S.Z_PLATE_TOP
    envelope = Part.makeCylinder(S.R_PASO, z1 - z0 + 40, V(0, 0, z0 - 10))
    w = SLED['ancho']

    body = box(-w / 2, w / 2, y0, y1, z0, z1)
    body = body.fuse(box(-w / 2, w / 2, y0 - foot['vuelo_detras'],
                         y1 + foot['vuelo_delante'], z0, z0 + ft))

    wing = SLED['alas']
    for sign in (-1, 1):
        xa = sign * wing['x_interior']
        xb = sign * (wing['x_interior'] + wing['espesor'])
        body = body.fuse(box(min(xa, xb), max(xa, xb), y0 - wing['profundidad'], y0,
                             z0, z1))

    gus = SLED['cartelas']
    for gx in gus['x']:
        xg = gx - gus['espesor'] / 2
        tri = Part.makePolygon([V(xg, y1, z0 + ft), V(xg, y1, z0 + ft + gus['alto']),
                                V(xg, y1 + gus['fondo'], z0 + ft), V(xg, y1, z0 + ft)])
        body = body.fuse(Part.Face(tri).extrude(V(gus['espesor'], 0, 0)))

    body = body.common(envelope)
    body = body.cut(Part.makeCylinder(foot['radio_libre_centro'], ft + 4, V(0, 0, z0 - 1)))
    for fx, fy in foot['tornillos']:
        body = body.cut(Part.makeCylinder(foot['tornillo_paso'] / 2, ft + 2,
                                          V(fx, fy, z0 - 1)))
    for b in tab_boxes():
        body = body.fuse(b)

    sw, sh = GRID['ranura_ancho'], GRID['ranura_alto']
    for z in grid_rows():
        for x in GRID['columnas_x']:
            body = body.cut(box(x - sw / 2, x + sw / 2, y0 - 1, y1 + 1, z - sh / 2, z + sh / 2))
    ffc = SLED['paso_ffc']
    zf = ffc_slot_z()
    body = body.cut(box(-ffc['ancho'] / 2, ffc['ancho'] / 2, y0 - 1, y1 + 1,
                        zf - ffc['alto'] / 2, zf + ffc['alto'] / 2))

    # Anillo de centrado y puente desde la placa. El anillo entra en el cuello
    # de la tapa con la holgura pedida; el agujero deja pasar la clavija.
    ring = SLED['anillo']
    r_out = S.NECK_RI - ring['holgura_cuello']
    ann = tube_ring(r_out, ring['radio_interior'], S.Z_RING0, ring['espesor'])
    cham = ring['chaflan']
    if cham > 0:
        top = S.Z_RING1 - cham
        cut = Part.makeCylinder(r_out + 1, cham + 0.01, V(0, 0, top))
        cut = cut.cut(Part.makeCone(r_out, r_out - cham, cham + 0.01, V(0, 0, top)))
        ann = ann.cut(cut)
        # Embudo en el agujero: guia la clavija al cerrar la tapa.
        ann = ann.cut(Part.makeCone(ring['radio_interior'], ring['radio_interior'] + cham,
                                    cham + 0.01, V(0, 0, top)))
    body = body.fuse(ann)
    bw = ring['puente_ancho']
    bridge = box(-bw / 2, bw / 2, y0, y1, z1 - 1.0, S.Z_RING0 + 0.5)
    bridge = bridge.common(Part.makeCylinder(r_out, 40, V(0, 0, z1 - 5)))
    body = body.fuse(bridge)
    return clean(body)


# --- Pieza 5: tapa del panel ---------------------------------------------------------
ADP = C['tiny_adapter']
REP = PAN['repisa']


def adapter_frame():
    """Posicion de la Tiny-Adapter: PCB horizontal, canto del receptaculo en
    y = cara_receptaculo_y, eje del receptaculo a la altura de la abertura."""
    pcb_t, pcb_w, pcb_l = ADP['pcb']
    rec = ADP['receptaculo']
    y_out = REP['cara_receptaculo_y']
    y_in = y_out - pcb_l
    z_top = S.USB_Z - rec['eje_sobre_pcb']
    z_bot = z_top - pcb_t
    holes = []
    e = ADP['agujeros_desde_borde']
    for hx in (-pcb_w / 2 + e, pcb_w / 2 - e):
        for hy in (y_in + e, y_out - e):
            holes.append((hx, hy))
    return {'x': (-pcb_w / 2, pcb_w / 2), 'y': (y_in, y_out), 'z': (z_bot, z_top),
            'holes': holes}


def build_panel(cfg):
    gap = cfg['holgura']
    a0 = cfg['angulo'] - cfg['arco_grados'] / 2.0 + math.degrees(gap / RO)
    sweep = cfg['arco_grados'] - 2 * math.degrees(gap / RO)
    z0 = S.PANEL_Z - cfg['alto'] / 2.0 + gap
    body = sector(RO, RO - cfg['espesor'], z0, cfg['alto'] - 2 * gap, a0, sweep)

    a = math.radians(cfg['angulo'])
    ux, uy = math.cos(a), math.sin(a)

    def radial_cut(radius, z, depth=cfg['espesor'] + 4):
        return Part.makeCylinder(radius, depth, V(ux * (RO + 2), uy * (RO + 2), z),
                                 V(-ux, -uy, 0))

    # Repisa y torres de la Tiny-Adapter. Van unidas a la cara interior.
    fr = adapter_frame()
    z_rep1 = fr['z'][0] - REP['torre_alto']
    z_rep0 = z_rep1 - REP['espesor']
    shelf = box(fr['x'][0], fr['x'][1], fr['y'][0], RO - 0.8, z_rep0, z_rep1)
    shelf = shelf.common(Part.makeCylinder(RO - 0.8, 200, V(0, 0, 0)))
    for hx, hy in fr['holes']:
        shelf = shelf.fuse(Part.makeCylinder(REP['torre_diametro'] / 2, REP['torre_alto'],
                                             V(hx, hy, z_rep1)))
    body = body.fuse(shelf)
    for hx, hy in fr['holes']:
        body = body.cut(Part.makeCylinder(REP['piloto'] / 2, REP['torre_alto'] + REP['espesor'] + 1,
                                          V(hx, hy, z_rep0 - 0.5)))
    # Rebaje para las esquinas del PCB y el cuerpo de la placa, que tocan la
    # cara interior curva de la tapa.
    # Empieza en la cara inferior del PCB: no toca las torres.
    body = body.cut(box(fr['x'][0] - 0.3, fr['x'][1] + 0.3, fr['y'][0], fr['y'][1] + 0.3,
                        fr['z'][0], fr['z'][1] + ADP['alto_componentes'] + 0.3))

    # Abertura del USB-C: rectangulo con esquinas redondeadas del tamano del
    # sobremolde, centrado en el eje del receptaculo. Solo atraviesa la tapa:
    # mas adentro estan las torres de la repisa.
    y_start = RO - cfg['espesor'] - 1.5
    cut = rounded_rect_prism(cfg['usb_ancho'], cfg['usb_alto'], cfg['usb_radio_esquina'],
                             y_start, RO + 2, S.USB_Z)
    cut.rotate(V(), V(0, 0, 1), cfg['angulo'] - 90)
    body = body.cut(cut)

    for dz in (-cfg['tornillo_separacion_z'] / 2, cfg['tornillo_separacion_z'] / 2):
        z = S.PANEL_Z + dz
        body = body.cut(radial_cut(cfg['tornillo_paso_libre'] / 2, z))
        body = body.cut(radial_cut(cfg['tornillo_cabeza'] / 2, z, 2.0 + cfg['cabeza_profundidad']))
    return clean(body)


# --- Logo -------------------------------------------------------------------------
def build_logo():
    path = ROOT / 'logo.json'
    if not path.exists():
        print('AVISO: falta logo.json; se omite el grabado.')
        return None
    data = json.loads(path.read_text(encoding='utf-8'))
    width, depth = LOGO['ancho_mm'], LOGO['profundidad_grabado']
    faces = []
    for shp in sorted(data['shapes'], key=lambda s: s.get('depth', int(s['hole']))):
        # X negado: mirando la cara +Y con Z arriba, X apunta a la izquierda.
        pts = [V(-p[0] * width, 0, p[1] * width + LOGO['z_centro']) for p in shp['points']]
        if len(pts) < 3:
            continue
        faces.append((shp.get('depth', int(shp['hole'])),
                      Part.Face(Part.makePolygon(pts + [pts[0]]))))
    if not faces:
        return None
    face = None
    for level, f in faces:
        if face is None:
            face = f
        elif level % 2:
            face = face.cut(f)
        else:
            face = face.fuse(f)
    solid = face.extrude(V(0, RO + 4.0, 0))
    solid = solid.cut(Part.makeCylinder(RO - depth, 400, V(0, 0, -100)))
    solid.rotate(V(), V(0, 0, 1), LOGO['angulo'] - 90.0)
    return clean(solid)


# --- Envolventes de referencia (no se imprimen) ---------------------------------------
CAR, COAX = C['carrier_um980'], C['latiguillo']


def references():
    refs = {}
    refs['ref_carrier_um980'] = box(S.CAR_X0, S.CAR_X1, S.CAR_Y0, S.CAR_Y1, S.Z_CAR0, S.Z_CAR1)
    sma = CAR['sma']
    refs['ref_sma_carrier'] = Part.makeCylinder(sma['radio_hexagono'], sma['sobresale'] + 6,
                                                V(S.SMA_X, S.SMA_Y, S.Z_CAR1 - 6))
    rc = COAX['radio_clavija']
    cov = COAX['rosca_cubierta']
    refs['ref_clavija_inferior'] = Part.makeCylinder(rc, S.Z_PLUGC_TOP - (S.Z_SMA_TIP - cov),
                                                     V(S.SMA_X, S.SMA_Y, S.Z_SMA_TIP - cov))
    refs['ref_clavija_superior'] = Part.makeCylinder(rc, S.Z_ANT_TIP + cov - S.Z_PLUGA_BOT,
                                                     V(0, 0, S.Z_PLUGA_BOT))
    # Cable del tramo libre, recto entre los dos ejes (0.7 mm de desfase).
    a, b = V(S.SMA_X, S.SMA_Y, S.Z_PLUGC_TOP), V(0, 0, S.Z_PLUGA_BOT)
    refs['ref_cable'] = Part.makeCylinder(COAX['diametro'] / 2, (b - a).Length, a, b - a)
    refs['ref_tiny'] = box(-9.0, 9.0, S.TINY_Y0, S.TINY_Y1, S.TINY_Z0, S.TINY_Z1)
    fr = adapter_frame()
    rec = ADP['receptaculo']
    adp = box(fr['x'][0], fr['x'][1], fr['y'][0], fr['y'][1], fr['z'][0], fr['z'][1])
    adp = adp.fuse(box(-rec['ancho'] / 2, rec['ancho'] / 2, fr['y'][1] - rec['largo'],
                       fr['y'][1], S.USB_Z - rec['alto'] / 2, S.USB_Z + rec['alto'] / 2))
    refs['ref_tiny_adapter'] = adp
    return refs


# --- Ensamble ---------------------------------------------------------------------
if __name__ == '__main__':
    doc = App.newDocument('Meridian3')
    logo = build_logo()
    parts = [
        ('01-threaded-base', 'Meridian3 base con rosca 5/8', build_base()),
        ('02-logo-tube', 'Meridian3 tubo con logo grabado', build_tube(logo)),
        ('03-antenna-cap', 'Meridian3 tapa de antena', build_cap()),
        ('04-sled', 'Meridian3 trineo', build_sled()),
        ('05-usb-panel-cover', 'Meridian3 tapa del panel USB-C', build_panel(PAN)),
    ]
    summary = []
    for name, label, shape in parts:
        obj = doc.addObject('Part::Feature', name.replace('-', '_'))
        obj.Label = label
        obj.Shape = shape
        bb = shape.BoundBox
        summary.append({
            'pieza': name, 'etiqueta': label,
            'solidos': len(shape.Solids), 'valido': bool(shape.isValid()),
            'volumen_cm3': round(shape.Volume / 1000.0, 2),
            'caja': [round(bb.XLength, 2), round(bb.YLength, 2), round(bb.ZLength, 2)],
            'z': [round(bb.ZMin, 2), round(bb.ZMax, 2)],
        })
    for name, shape in references().items():
        obj = doc.addObject('Part::Feature', name)
        obj.Label = name.replace('ref_', 'Referencia (no se imprime): ')
        obj.Shape = shape
    doc.recompute()
    doc.saveAs(str(OUT / 'Meridian3.FCStd'))

    resumen = {
        'posicion': 'cerrada: dientes de base y tapa contra el fondo de su ranura',
        'giro_cierre_grados': round(GIRO_CIERRE, 2),
        'tapa_cierra_horario': SIGN_CAP < 0,
        'altura_total_mm': round(Z_TOP, 2),
        'diametro_exterior_mm': round(2 * RO, 2),
        'plano_alturas': dict(S.resumen()['pila_mm'],
                              fondo_cuello_tapa=round(Z_NECK_BOTTOM, 2),
                              anillo=[round(S.Z_RING0, 2), round(S.Z_RING1, 2)],
                              placa_arriba=round(S.Z_PLATE_TOP, 2),
                              panel_centro=round(S.PANEL_Z, 2),
                              eje_usb=round(S.USB_Z, 2),
                              seguro_base=round(Z_LOCK_BASE, 2),
                              seguro_tapa=round(Z_LOCK_CAP, 2),
                              ranura_ffc=round(ffc_slot_z(), 2)),
        'filas_rejilla': [round(z, 2) for z in grid_rows()],
        'piezas': summary,
        'volumen_total_cm3': round(sum(s['volumen_cm3'] for s in summary), 2),
    }
    (OUT / 'model-index.json').write_text(json.dumps(resumen, indent=1, ensure_ascii=False),
                                          encoding='utf-8')
    print(json.dumps(resumen, indent=1, ensure_ascii=False))
