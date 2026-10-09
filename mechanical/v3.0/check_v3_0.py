"""Comprueba la carcasa V3.0 contra la placa v0.3 y el resto de piezas compradas.

Mide, con las piezas de generated/TresVizo-V3.0.FCStd:
  - guardas de la pared del tubo (el material que falta no sale como choque): sondas en la mitad
    de la pared, en la cara plana y en un anillo, y volumen contra el de la pared intencionada;
  - choques entre piezas impresas y contra cada referencia en la posicion final: placa (envolvente
    de la especificacion o STEP real con --board), carrier con sus componentes, celdas, tuerca y
    reten, antena y sus tornillos, coaxial, clavijas y cables, OLED, funda del USB-C, tarjeta;
  - barridos del montaje: celdas por arriba, carrier y placa al chasis por abajo, chasis armado
    (con el marco del USB-C) por arriba con las celdas puestas, base por abajo, tapa por arriba, tecla
    y tarjeta por fuera, marco sobre el USB-C por fuera y funda del USB-C por el costado;
  - holguras minimas y radio maximo del chasis armado;
  - marco del USB-C: contactos, holguras, cuanto se mueve atrapado, espesores, y que se ve desde fuera
    por el USB-C y la ranura de la microSD (rayos rectos y oblicuos hasta 30 grados);
  - bandas de TPU: apriete contra el tubo, la base y la tapa (a proposito, no es choque), holguras de sus
    aberturas, barrido de cada banda al ponerla, base, tapa, tecla, tarjeta y funda con las bandas puestas,
    angulo maximo de la tapa de puertos con la banda, distintivo y rayas entre las bandas.

Uso:
  PYTHONPATH=/Applications/FreeCAD.app/Contents/Resources/lib \\
  /Applications/FreeCAD.app/Contents/Resources/bin/python check_v3_0.py [--board placa.step] [--envelope]
Por defecto usa la placa real (hardware/main-board/cad/placa-principal.step) si existe; si no, o con
--envelope, la envolvente de la especificacion.
Escribe generated/check.json. NO es una validacion: nada se ha impreso ni montado.
"""
import argparse, json, math, sys, time
from pathlib import Path

sys.dont_write_bytecode = True

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
import FreeCAD as App
import Part
import geom_v3_0 as G
from geom_v3_0 import P, V, box

ap = argparse.ArgumentParser(description=__doc__)
ap.add_argument('--output-dir', type=Path, default=ROOT / 'generated')
ap.add_argument('--board', type=Path, default=None,
                help='STEP de la placa v0.3 (por defecto hardware/main-board/cad/placa-principal.step si existe)')
ap.add_argument('--envelope', action='store_true', help='usar la envolvente de la especificacion aunque exista el STEP')
ap.add_argument('--step', type=float, default=0.5, help='paso de los barridos, mm')
args, _ = ap.parse_known_args()
OUT = args.output_dir.resolve()
T0 = time.time()
LIM = 0.05   # mm3: por debajo, contacto o redondeo de OCC


def log(*a):
    print('[%6.1f s]' % (time.time() - T0), *a, flush=True)


doc = App.openDocument(str(OUT / 'TresVizo-V3.0.FCStd'))
parts = {o.Name.lstrip('_').replace('_', '-'): o.Shape for o in doc.Objects
         if hasattr(o, 'Shape') and not o.Shape.isNull() and not o.Name.startswith('ref_')}
BASE, TUBE, CAP = parts['01-base'], parts['02-tube'], parts['03-antenna-cap']
CHS, KEY = parts['04-chassis'], parts['05-key-tpu']
COVER = parts['06-port-cover-tpu']
# Marco del USB-C: el resorte (dedo sobre el blindaje de J101, que lo aprieta a proposito) se separa de
# la parte rigida para los barridos y para medir cuanto se mueve.
BEZEL = parts['08-usb-bezel']
BEZEL_SPRING = BEZEL.common(G.bezel_spring_zone())
BEZEL_RIGID = BEZEL.cut(G.bezel_spring_zone())
# Bandas de TPU: en el documento, con su medida de impresion (el solape con el tubo, la base y la tapa es el
# apriete). Para los barridos y la tapa de puertos abierta, la banda ESTIRADA sobre el cuerpo (contorno interior
# = cuerpo + bandas.holgura_barrido, mismo espesor): asi esta montada.
BAND_B, BAND_T = parts[G.BAND_NAMES['abajo']], parts[G.BAND_NAMES['arriba']]
BAND_B_ST, BAND_T_ST = G.band('abajo', stretched=True), G.band('arriba', stretched=True)

# --- Referencias ------------------------------------------------------------------------
if args.board is None and not args.envelope and (G.MB_CAD / 'placa-principal.step').exists():
    args.board = G.MB_CAD / 'placa-principal.step'
if args.board and not args.envelope:
    board = G.load_board_step(args.board)
    board_src = str(args.board)
    if 'PCB' not in board:
        k = next((k for k in board if 'pcb' in k.lower()), None)
        if k is None:
            raise SystemExit('El STEP no trae un solido llamado PCB: no se puede comprobar.')
        board['PCB'] = board.pop(k)
    board.update(G.oled_stack())   # el modulo OLED no lo monta JLCPCB: se dibuja aparte
else:
    board = G.board_envelope()
    board_src = 'envolvente de la especificacion (no hay STEP de la placa v0.3)'
plug_refs, plug_src = G.plugs()
coax_refs, coax_R = G.coax()
groups = {'placa': board, 'carrier': G.carrier(), 'celdas': G.cells(), 'tuerca': G.nut_and_retainer(),
          'antena': G.antenna_and_screws(), 'coaxial': coax_refs, 'clavijas': plug_refs,
          'cables': G.cable_reserves(), 'tornillos': G.case_screws(),
          'usb': {'funda de la clavija': G.usb_overmold()}, 'microsd': {'tarjeta puesta': G.microsd_card()},
          'frente': {'guia de luz del LED': G.light_pipe(), 'lamina de la ventana (PC 1.0)': G.oled_window_sheet()}}
refs = {f'{g}: {k}': v for g, d in groups.items() for k, v in d.items()}
log('referencias:', len(refs), '| placa:', board_src, '| clavijas:', plug_src)

# Parejas que se tocan o se penetran a proposito (conector enchufado, cable que entra en su
# clavija...). Se comparan por el comienzo del nombre: con el STEP real, J401 es el zocalo.
MATES = [('carrier: SMA cañón', 'coaxial: clavija SMA de la carrier'),
         ('placa: J401', 'microsd: tarjeta puesta'),
         ('placa: componentes (envolvente h(x))', 'microsd: tarjeta puesta'),
         ('antena: antena HA-901A', 'coaxial: pasamuros SMA (fuera)'),
         ('antena: antena HA-901A', 'coaxial: clavija SMA del cable'),
         ('cables: cable NTC (cuerpo)', 'celdas:'),
         ('cables: cable hilos_ntc', 'celdas:'),
         ('cables: cable mazo_pack', 'celdas:'),
         ('cables: cable arnes_j301', 'carrier: arnés J301: cables por delante (8 agujeros)')]
MATE_GROUPS = [('cables', 'clavijas')]


def is_mate(a, b):
    for p, q in MATES:
        if (a.startswith(p) and b.startswith(q)) or (a.startswith(q) and b.startswith(p)):
            return True
    ga, gb = a.split(':')[0], b.split(':')[0]
    return (ga, gb) in MATE_GROUPS or (gb, ga) in MATE_GROUPS


def common_vol(a, b):
    if not a.BoundBox.intersect(b.BoundBox):
        return 0.0
    try:
        c = a.common(b)
        return c.Volume if c.Solids else 0.0
    except Exception:
        return -1.0


def gap(a, b):
    try:
        return round(a.distToShape(b)[0], 3)
    except Exception:
        return None


def min_gap(a, shapes):
    vals = [g for g in (gap(a, s) for s in shapes) if g is not None]
    return min(vals) if vals else None


report = {'placa_origen': board_src, 'clavijas_origen': plug_src, 'paso_barridos_mm': args.step}
REAL_BOARD = bool(args.board and not args.envelope)

# --- 0. Guardas de la pared del tubo ----------------------------------------------------
# El material que falta no aparece como choque: se comprueba aparte. (1) sondas en la mitad de la
# pared, cara plana y anillo; (2) volumen del tubo contra el de la pared intencionada (hecha con
# poligonos, sin interior()) menos las aberturas a proposito mas nervios, repisas y cuna.
import build_v3_0 as B
guard = {'sondas': G.wall_probes(TUBE, step=0.5)}
wall_ref = G.wall_reference()
rr_ = P['tubo']['ranuras_rieles']
groove_list = [G.sector(rr_['radio'], G.RI - 0.5, rr_['z'][0], G.Z_TUBE1 + 1, a0, a1) for a0, a1 in rr_['angulos']]
openings = G.fuse_all([s_ for s_ in (B.front_openings(), B.side_openings(), B.screw_holes(), B.rebates(),
                                     B.decorative_lines()) if s_ is not None])
expected = wall_ref.cut(G.fuse_all(groove_list)) if groove_list else wall_ref
expected = expected.fuse(B.rail_ledges()).fuse(B.cell_cradle()).cut(openings).cut(G.logo_engrave())
v_tube, v_exp = TUBE.Volume, expected.Volume
guard['volumen'] = {
    'tubo_mm3': round(v_tube, 1), 'esperado_mm3': round(v_exp, 1),
    'anillo_solido_mm3': round(wall_ref.Volume, 1),
    'diferencia_mm3': round(v_tube - v_exp, 1), 'diferencia_pct': round(100 * (v_tube - v_exp) / v_exp, 3),
    'tolerancia_pct': 0.5, 'ok': abs(v_tube - v_exp) <= 0.005 * v_exp,
    '_nota': (f'esperado = anillo solido (circulo R{G.RO:g} con la cara plana en y {G.Y_FLAT_O:g}, hueco R{G.RI:g} con la cara '
              f'plana interior en y {G.Y_FLAT_I:g} para |x| <= {G.X_FLAT:g}, z {G.Z_TUBE0:g}-{G.Z_TUBE1:g}) - rebajes de las uniones '
              '+ apoyos del chasis + cuna - ventana con su bolsillo, tecla con su rebaje, LED, tunel USB-C, ranura microSD, '
              'rebaje de la una, agujero del ancla de la tapa de puertos, tornillos, lineas decorativas y distintivo grabado.')}
# Espesor minimo de pared alrededor de las aberturas (rayos desde el contorno de secciones
# horizontales; se ignoran 0.6 mm alrededor de las esquinas vivas). Objetivo: 1.2 en general y no
# menos de 1.0 en lo local (holguras.pared_minima / pared_local_minima); se listan los que no llegan.
HOLG = P['holguras']
RR = G.RO + 1.0
side = (10.0, RR, 4.0, G.Y_FLAT_O + 1.0)
front = (-G.X_FLAT - 1.5, G.X_FLAT + 1.5, G.Y_FLAT_I - 1.0, G.Y_FLAT_O + 1.0)
whole = (-RR, RR, -RR, G.Y_FLAT_O + 1.0)
_zsd = [round(G.SD_Z + d_, 2) for d_ in (-6.5, -5.0, -3.0, -1.0, 0.0, 1.0, 3.0, 5.0, 6.5)]
# Solo la pared: se quitan los nervios, repisas y apoyos de dentro (no son pared; los nervios de la
# cuna miden 1.6 a proposito). La pared normal se mide en z 15, 70 (con las rayas) y 95: en z 60 ahora esta el
# distintivo grabado (frente.logo), donde el rayo mediria el ancho entre trazos del grabado, no la pared.
TUBE_WALL = TUBE.cut(G.interior(G.Z_TUBE0 - 1, G.Z_TUBE1 + 1, 0.05))
_za_list = G.anchor_zs()
_wz = P['frente']['ventana_oled']['z']
th = {'tunel USB-C': G.min_wall_thickness(TUBE_WALL, [18.6, 19.0, 22.0, 25.0, 28.0, 31.0, 31.4], side),
      'ranura microSD y rebaje': G.min_wall_thickness(TUBE_WALL, _zsd, side),
      'agujeros de las anclas de la tapa de puertos': G.min_wall_thickness(TUBE_WALL, [z_ + d_ for z_ in _za_list for d_ in (-0.7, 0.0, 0.7)], side),
      'ventana OLED (bolsillo y chaflan)': G.min_wall_thickness(TUBE_WALL, [_wz[0] - 0.5, _wz[0] + 1.0, 80.0, _wz[1] - 1.0, _wz[1] + 0.5], front),
      'tecla y LED': G.min_wall_thickness(TUBE_WALL, [18.0, 20.0, 22.0, 24.0, 26.0], (-10.0, 10.0, G.Y_FLAT_I - 1.0, G.Y_FLAT_O + 0.5)),
      'uniones (rebajes)': G.min_wall_thickness(TUBE_WALL, [G.Z_TUBE0 + 0.5, G.Z_TUBE0 + 1.2, G.Z_TUBE1 - 1.2, G.Z_TUBE1 - 0.5], whole),
      'tornillos radiales de base y tapa': G.min_wall_thickness(TUBE_WALL, [P['base']['tornillos']['z'], P['tapa']['tornillos_z']], whole),
      'pared normal y lineas decorativas (z 15, 70, 95)': G.min_wall_thickness(TUBE_WALL, [15.0, 70.0, 95.0], whole)}
guard['espesor_minimo'] = {k: {'mm': v[0], 'donde': v[1]} for k, v in th.items()}
guard['espesor_por_debajo_de_1.2'] = {k: v[0] for k, v in th.items() if v[0] < HOLG['pared_minima']}
guard['espesor_por_debajo_de_1.0'] = {k: v[0] for k, v in th.items() if v[0] < HOLG['pared_local_minima']}
guard['espesor_minimo_ok'] = all(v[0] >= HOLG['pared_local_minima'] for v in th.values())
# La guarda es la de pared que falta (sondas y volumen); el espesor se informa aparte.
guard['ok'] = guard['sondas']['cara_plana']['ok'] and guard['sondas']['anillo']['ok'] and guard['volumen']['ok']
report['guarda_pared_tubo'] = guard
log('guarda de la pared:', {k: guard['sondas'][k]['sin_material'] for k in ('cara_plana', 'anillo')},
    guard['volumen']['tubo_mm3'], 'vs', guard['volumen']['esperado_mm3'], 'ok' if guard['ok'] else 'FALLA',
    '| espesores:', {k: v['mm'] for k, v in guard['espesor_minimo'].items()})

# --- 1. Posicion final ------------------------------------------------------------------
names = sorted(parts)
pp, band_grip = [], {}
for i, a in enumerate(names):
    for b in names[i + 1:]:
        v = common_vol(parts[a], parts[b])
        if G.band_grip_pair(a, b):
            band_grip[f'{a} / {b}'] = round(v, 3)      # apriete a proposito (0.3 por lado)
            continue
        if v > LIM or v < 0:
            pp.append({'a': a, 'b': b, 'mm3': round(v, 3)})
report['choques_entre_piezas'] = pp
pr = []
# Piezas que ocupan el sitio de una referencia a proposito y nunca a la vez: el tapon del USB-C
# va donde la funda de la clavija cuando no hay cable.
ALTERNATIVES = [('06-port-cover-tpu', 'usb: funda de la clavija')]
# Contactos con apriete a proposito: el resorte del marco aprieta el blindaje de J101 (se mide aparte).
INTENDED = {('08-usb-bezel', 'placa: J101'): 'resorte del marco sobre el techo del blindaje'}
intended_rep = {}
for pn in names:
    for rn, rs in refs.items():
        if (pn, rn) in ALTERNATIVES:
            continue
        if pn == '08-usb-bezel' and not REAL_BOARD and rn.startswith('placa:') and rn != 'placa: PCB':
            continue   # el marco solo se comprueba con la placa real: la envolvente llena la cara entera
        if (pn, rn) in INTENDED:
            intended_rep[f'{pn} / {rn}'] = {'mm3': round(common_vol(parts[pn], rs), 3), 'que_es': INTENDED[(pn, rn)]}
            continue
        v = common_vol(parts[pn], rs)
        if v > LIM or v < 0:
            pr.append({'pieza': pn, 'ref': rn, 'mm3': round(v, 3)})
report['choques_piezas_referencias'] = pr
report['contactos_con_apriete_a_proposito'] = intended_rep
rr, keys = [], sorted(refs)
for i, a in enumerate(keys):
    for b in keys[i + 1:]:
        if a.split(':')[0] == b.split(':')[0] or is_mate(a, b):
            continue
        v = common_vol(refs[a], refs[b])
        if v > LIM or v < 0:
            rr.append({'a': a, 'b': b, 'mm3': round(v, 3)})
report['choques_entre_referencias'] = rr
log('posicion final:', len(pp), 'entre piezas,', len(pr), 'pieza-referencia,', len(rr), 'entre referencias')


# --- 2. Barridos del montaje ------------------------------------------------------------
def slabs(shape, dz=10.0):
    """Parte un obstaculo grande en rebanadas de z: cada comun sale mas barato."""
    bb = shape.BoundBox
    out, z = [], math.floor(bb.ZMin)
    while z < bb.ZMax:
        s = shape.common(box(-60, 60, -60, 60, z, z + dz))
        if s.Solids:
            out.append(s)
        z += dz
    return out


FOOT = {}


def footprint_free(on, oshape, ms, vec):
    """Filtro exacto para barridos verticales: si en ninguna seccion del obstaculo dentro del
    tramo de z recorrido hay material que toque la caja XY de la pieza movil, no puede chocar."""
    if abs(vec.x) > 1e-9 or abs(vec.y) > 1e-9:
        return False
    import numpy as np
    from matplotlib.path import Path as MPath
    from matplotlib.transforms import Bbox
    if on not in FOOT:
        bb = oshape.BoundBox
        FOOT[on] = []
        for z in G._frange(math.floor(bb.ZMin), math.ceil(bb.ZMax), 0.5):
            polys = G.section_polygons(oshape, z, 0.1)
            FOOT[on].append((z, polys, [MPath(np.array(p_)) for p_ in polys if len(p_) > 2]))
    mb = ms.BoundBox
    zlo, zhi = min(mb.ZMin, mb.ZMin + vec.z), max(mb.ZMax, mb.ZMax + vec.z)
    box2 = Bbox([[mb.XMin - 0.05, mb.YMin - 0.05], [mb.XMax + 0.05, mb.YMax + 0.05]])
    center = np.array([[(mb.XMin + mb.XMax) / 2.0, (mb.YMin + mb.YMax) / 2.0]])
    for z, polys, paths in FOOT[on]:
        if not (zlo - 0.5 <= z <= zhi + 0.5):
            continue
        if any(pth.intersects_bbox(box2, filled=False) for pth in paths):
            return False
        if G.inside_material(polys, center)[0]:
            return False
    return True


def sweep(moving, obstacles, vec, step=None):
    """Lleva cada pieza movil de su sitio a sitio + vec en pasos y mide el choque maximo con
    cada obstaculo. moving / obstacles: {nombre: forma}. Devuelve la lista de choques."""
    step = step or args.step
    L = vec.Length
    n = max(1, int(math.ceil(L / step)))
    u = V(vec.x / L, vec.y / L, vec.z / L)
    found = []
    for on, oshape in obstacles.items():
        pieces = OBST_SLABS.get(on) or [oshape]
        for mn, ms in moving.items():
            if on in OBST_SLABS and footprint_free(on, oshape, ms, vec):
                continue
            sb = ms.BoundBox
            swept = App.BoundBox(sb)
            swept.add(V(sb.XMin, sb.YMin, sb.ZMin) + vec)
            swept.add(V(sb.XMax, sb.YMax, sb.ZMax) + vec)
            worst, at = 0.0, None
            for op in pieces:
                if not swept.intersect(op.BoundBox):
                    continue
                for i in range(n + 1):
                    t = min(L, i * step)
                    m = ms.translated(u * t)
                    if not m.BoundBox.intersect(op.BoundBox):
                        continue
                    v = common_vol(m, op)
                    if v > worst:
                        worst, at = v, t
            if worst > LIM:
                found.append({'movil': mn, 'obstaculo': on, 'mm3_max': round(worst, 3), 'a_mm': round(at, 2)})
    return found


# El distintivo va grabado por fuera de la cara plana (de y 22.9 - profundidad a 22.9) y nada de dentro
# llega a el: los barridos y las holguras usan el tubo con el grabado relleno (mucho mas rapido). Las
# guardas y la posicion final, el tubo entero.
lgp = P['frente']['logo']
TUBE_NL = TUBE.fuse(box(-lgp['ancho'] / 2 - 0.5, lgp['ancho'] / 2 + 0.5, G.Y_FLAT_O - lgp['profundidad'] - 0.05, G.Y_FLAT_O,
                        lgp['z_centro'] - 0.65 * lgp['ancho'], lgp['z_centro'] + 0.65 * lgp['ancho']))
OBST_SLABS = {'02-tube': slabs(TUBE_NL), '04-chassis': slabs(CHS)}
board_refs = {f'placa: {k}': v for k, v in board.items()}
carrier_refs = {f'carrier: {k}': v for k, v in groups['carrier'].items()}
cell_refs = {f'celdas: {k}': v for k, v in groups['celdas'].items()}
sweeps = {}

# a. Celdas por arriba (tapa quitada, chasis fuera, base puesta).
UP_CELLS = G.Z_TUBE1 - P['celdas']['z'][0] + 1.0
UP_CHS = G.Z_TUBE1 - P['chasis']['riel']['z'][0] + 1.0
sweeps['celdas_por_arriba'] = sweep(cell_refs, {'02-tube': TUBE_NL, '01-base': BASE}, V(0, 0, UP_CELLS))
log('celdas:', sweeps['celdas_por_arriba'])
# b. Carrier al chasis por abajo (los labios de los ganchos se apartan: no cuentan).
gk = P['chasis']['ganchos']
_ca, _hh = P['carrier'], P['chasis']['ranura_carrier']['holgura']
_lz = (_ca['z'][0] - _hh - 0.8, _ca['z'][0] - _hh)
hook_zone = box(-17.8, -14.8, gk['y'][0] - 0.5, gk['y'][1] + 0.5, _lz[0] - 0.5, _lz[1] + 0.01)
hook_zone = hook_zone.fuse(box(14.8, 17.8, gk['y'][0] - 0.5, gk['y'][1] + 0.5, _lz[0] - 0.5, _lz[1] + 0.01))
chs_no_hooks = CHS.cut(hook_zone)
OBST_SLABS['chasis sin labios de gancho'] = slabs(chs_no_hooks)
sweeps['carrier_al_chasis_por_abajo'] = sweep(carrier_refs, {'chasis sin labios de gancho': chs_no_hooks}, V(0, 0, -60))
log('carrier:', sweeps['carrier_al_chasis_por_abajo'])
# c. Clavija SMA del coaxial al SMA de la carrier, por arriba, con la carrier en el chasis y SIN
#    la placa (el frente del chasis esta abierto). La tuerca se dibuja con su barrido al girar.
plug_sh = coax_refs['clavija SMA de la carrier']
carrier_no_barrel = {k: v for k, v in carrier_refs.items() if 'SMA cañón' not in k}
obst = {'04-chassis': CHS}
obst.update(carrier_no_barrel)
sweeps['clavija_sma_por_arriba_sin_placa'] = sweep({'coaxial: clavija SMA (tuerca Ø9.2 y cuerpo)': plug_sh}, obst, V(0, 0, 25))
# c2. Llave fija de 8 por delante (+Y) hasta la tuerca, sin la placa: bocas a los lados de la
#     tuerca, que llegan 3.4 detras de su eje (las caras planas miden 2.3 a cada lado), y cabeza
#     delante, z 76-79.5. Se barre recta y se comprueba quieta girada +-30 grados (cambio de cara).
cxp = P['coaxial']['clavija']
nx, ny = cxp['x'], cxp['y']
jaw = cxp['tuerca']['entre_caras'] / 2.0 + 0.1
back = 3.4


def wrench_at(angle_deg):
    w = G.fuse_all([box(-7.5, -jaw, -back, 40, 76.0, 79.5), box(jaw, 7.5, -back, 40, 76.0, 79.5),
                    box(-7.5, 7.5, jaw, 40, 76.0, 79.5)])
    w.rotate(V(), V(0, 0, 1), angle_deg)
    w.translate(V(nx, ny, 0))
    return w


_ntz = cxp['tuerca']
obst = {'04-chassis': CHS, 'coaxial: cuerpo acodado de la clavija': coax_refs['clavija SMA de la carrier'].cut(
    box(-40, 40, -40, 40, _ntz['z0'] - 1, _ntz['z0'] + _ntz['largo']))}
obst.update(carrier_refs)
sweeps['llave_por_delante_sin_placa'] = sweep({'llave fija de 8 (envolvente)': wrench_at(0)}, obst, V(0, 30, 0))
for ang in (-30, 30):
    for on, ob in obst.items():
        v = common_vol(wrench_at(ang), ob)
        if v > LIM:
            sweeps['llave_por_delante_sin_placa'].append({'movil': f'llave girada {ang} grados', 'obstaculo': on, 'mm3_max': round(v, 3), 'a_mm': 0})
report['llave_holgura_chasis'] = {str(a): gap(wrench_at(a), CHS) for a in (-30, 0, 30)}
# d. Placa con la OLED soldada, por abajo, con la carrier y la clavija SMA ya puestas (la muesca
#    del canto de arriba pasa alrededor de la tuerca). Sin los tornillos M2.
board_mov = {k: v for k, v in board_refs.items() if 'tornillos' not in k}
obst = {'04-chassis': CHS, 'coaxial: clavija SMA (tuerca Ø9.2 y cuerpo)': plug_sh}
obst.update(carrier_refs)
sweeps['placa_al_chasis_por_abajo'] = sweep(board_mov, obst, V(0, 0, -92))
log('placa:', sweeps['placa_al_chasis_por_abajo'])
# e. Chasis armado (chasis, placa con OLED y tornillos, carrier, clavija SMA) por arriba, con las
#    celdas y sus cables puestos y SIN la tecla. e2: lo mismo con la tecla puesta.
assembly = {'04-chassis': CHS, 'coaxial: clavija SMA (tuerca Ø9.2 y cuerpo)': plug_sh, '08-usb-bezel': BEZEL}
assembly.update(board_refs)
assembly.update(carrier_refs)
# El arnes de J301 va de la carrier a la placa: entra y sale con el chasis armado.
assembly['cables: cable arnes_j301'] = groups['cables']['cable arnes_j301']
batt = {f'cables: {k}': v for k, v in groups['cables'].items() if 'arnes' not in k}   # los del pack, quietos con el
obst = {'02-tube': TUBE_NL, '01-base': BASE}
obst.update(cell_refs)
obst.update(batt)
obst['06-port-cover-tpu'] = COVER
sweeps['chasis_armado_por_arriba_sin_tecla'] = sweep(assembly, obst, V(0, 0, UP_CHS))
log('chasis armado sin tecla:', sweeps['chasis_armado_por_arriba_sin_tecla'])
obst_k = {'05-key-tpu': KEY}
sweeps['chasis_armado_con_tecla_puesta'] = sweep(assembly, obst_k, V(0, 0, UP_CHS))
log('chasis armado con tecla:', sweeps['chasis_armado_con_tecla_puesta'])
# f. Base por abajo (con la tuerca y el reten), con todo lo de dentro puesto.
base_mov = {'01-base': BASE}
base_mov.update({f'tuerca: {k}': v for k, v in groups['tuerca'].items() if 'perno' not in k})
obst = {'02-tube': TUBE_NL, '04-chassis': CHS}
obst.update(board_refs)
obst.update(carrier_refs)
obst.update(cell_refs)
obst.update({f'clavijas: {k}': v for k, v in plug_refs.items()})
obst.update({f'cables: {k}': v for k, v in groups['cables'].items()})
# Con la banda de abajo puesta (estirada): la base sale por abajo sin quitarla.
obst['09-band-bottom-tpu (estirada)'] = BAND_B_ST
sweeps['base_por_abajo'] = sweep(base_mov, obst, V(0, 0, -20))
log('base:', sweeps['base_por_abajo'])
# g. Tapa con la antena atornillada, por arriba (con sus topes de las celdas y su labio).
cap_mov = {'03-antenna-cap': CAP}
cap_mov.update({f'antena: {k}': v for k, v in groups['antena'].items()})
cap_mov.update({f'coaxial: {k}': v for k, v in coax_refs.items() if 'pasamuros' in k or 'antena hembra' in k})
obst = {'02-tube': TUBE_NL, '04-chassis': CHS, 'coaxial: clavija SMA (tuerca Ø9.2 y cuerpo)': plug_sh}
obst.update(board_refs)
obst.update(cell_refs)
obst.update(batt)
# Con la banda de arriba puesta (estirada): la tapa sale por arriba sin quitarla.
obst['10-band-top-tpu (estirada)'] = BAND_T_ST
sweeps['tapa_por_arriba'] = sweep(cap_mov, obst, V(0, 0, 20))
log('tapa:', sweeps['tapa_por_arriba'])
# h. Tecla entera por fuera (la pestana va en el rebaje exterior: entra y sale por fuera).
obst = {'02-tube': TUBE_NL, '09-band-bottom-tpu (estirada)': BAND_B_ST}      # por la ventana de la banda
obst.update(board_refs)
sweeps['tecla_por_fuera'] = sweep({'05-key-tpu': KEY}, obst, V(0, 12, 0))
# i. Tarjeta microSD por el costado +X.
sweeps['tarjeta_por_el_costado'] = sweep({'microsd: tarjeta': G.microsd_card()},
                                         {'02-tube': TUBE_NL, '04-chassis': CHS, 'placa: PCB': board['PCB'],
                                          '09-band-bottom-tpu (estirada)': BAND_B_ST}, V(15, 0, 0))
# j. Tapa de puertos por fuera: la parte de delante de la bisagra (ala, cuerpos y lengueta) sale
#    hacia +X; la seta queda en su agujero.
tpp = P['costado']['tapa_puertos']
# La cabeza de la seta (r < RI, de unos 15 a 23 grados) se queda en su sitio: la parte movil empieza
# en la bisagra y en r RI (los cuerpos de TPU estan en r >= 25.65).
_front_zone = G.sector(40, G.RI - 0.01, -1, 101, tpp['bisagra']['angulo'], 90)
COVER_FRONT = COVER.common(_front_zone)
COVER_ANCHOR = COVER.cut(_front_zone)
obst = {'02-tube': TUBE_NL, '04-chassis': CHS, 'microsd: tarjeta puesta': G.microsd_card(), '08-usb-bezel': BEZEL,
        '09-band-bottom-tpu (estirada)': BAND_B_ST}
obst.update(board_refs)
sweeps['tapa_de_puertos_por_fuera'] = sweep({'06-port-cover-tpu (delante de la bisagra)': COVER_FRONT}, obst, V(12, 0, 0))


def sweep_min_gaps(moving, obstacles, vec, step=None, near=3.0):
    """Holgura minima (distToShape) de `moving` a cada obstaculo a lo largo de su recorrido (paso
    `step`); solo obstaculos a menos de `near` del recorrido. {obstaculo: (mm, a_mm)}."""
    step = step or args.step
    L = vec.Length
    n = max(1, int(math.ceil(L / step)))
    u = V(vec.x / L, vec.y / L, vec.z / L)
    sb = moving.BoundBox
    swept = App.BoundBox(sb)
    swept.add(V(sb.XMin, sb.YMin, sb.ZMin) + vec)
    swept.add(V(sb.XMax, sb.YMax, sb.ZMax) + vec)
    swept.enlarge(near)
    out = {}
    for on, os_ in obstacles.items():
        if not swept.intersect(os_.BoundBox):
            continue
        best = None
        for i in range(n + 1):
            t = min(L, i * step)
            m = moving.translated(u * t)
            bb = App.BoundBox(m.BoundBox)
            bb.enlarge(near)
            if not bb.intersect(os_.BoundBox):
                continue
            g_ = gap(m, os_)
            if g_ is not None and (best is None or g_ < best[0]):
                best = (g_, round(t, 2))
        if best is not None and best[0] < near:
            out[on] = best
    return out


# k. Marco del USB-C por fuera (-X) sobre el receptaculo, con la placa y la carrier ya en el chasis (se
#    mide al reves: del sitio hacia +X hasta que sale). El resorte aprieta el blindaje de J101 a proposito
#    (se mide aparte); la parte rigida se barre contra todo, J101 incluido.
L_BZ = 15.0
bz_obst = {'04-chassis': CHS}
# Con la envolvente de la especificacion (que llena toda la cara de la placa) solo cuenta la PCB.
bz_obst.update(board_refs if REAL_BOARD else {'placa: PCB': board['PCB']})
bz_obst.update(carrier_refs)
sweeps['marco_sobre_el_usb_c_por_fuera'] = (
    sweep({'08-usb-bezel (parte rigida)': BEZEL_RIGID}, bz_obst, V(L_BZ, 0, 0))
    + sweep({'08-usb-bezel (resorte)': BEZEL_SPRING}, {k: v for k, v in bz_obst.items() if k != 'placa: J101'}, V(L_BZ, 0, 0)))
_spr = [common_vol(BEZEL_SPRING.translated(V(t_, 0, 0)), board['J101']) for t_ in G._frange(0.0, 7.0, 0.5)] if 'J101' in board else []
_bz_g = sweep_min_gaps(BEZEL_RIGID, {k: v for k, v in bz_obst.items() if k not in ('placa: PCB', 'placa: J101')}, V(L_BZ, 0, 0))
report['marco_al_montarlo'] = {
    'recorrido_mm': L_BZ,
    'holgura_minima_durante_el_recorrido_mm': {k: {'mm': v[0], 'a_mm_de_su_sitio': v[1]} for k, v in sorted(_bz_g.items(), key=lambda kv: kv[1][0])[:10]},
    'componentes_min_mm': min([v[0] for k, v in _bz_g.items() if k.startswith('placa:')], default=None),
    'carrier_min_mm': min([v[0] for k, v in _bz_g.items() if k.startswith('carrier:')], default=None),
    'chasis_min_mm': _bz_g.get('04-chassis', (None,))[0],
    'resorte_sobre_J101_mm3_max': round(max(_spr), 3) if _spr else None,
    '_nota': ('El marco entra por -X: el labio pasa bajo el dorso de la placa (contacto) y el collar por encima de la cara, '
              'hasta que el fondo de las ranuras toca el canto de la placa (x 18). El resorte sube por la boca de J101 y '
              'aprieta su techo (volumen a proposito, no es choque).')}
log('marco por fuera:', sweeps['marco_sobre_el_usb_c_por_fuera'], report['marco_al_montarlo'])
# l. Funda maxima de la clavija USB-C por el costado (+X hasta salir), con el marco puesto y la tapa de
#    puertos abierta: el tunel del tubo y el del marco la guian a 0.3 por lado.
fo_obst = {'02-tube': TUBE_NL, '08-usb-bezel': BEZEL, '04-chassis': CHS, '09-band-bottom-tpu (estirada)': BAND_B_ST}
fo_obst.update(board_refs)
fo_obst.update(carrier_refs)
sweeps['funda_usb_c_por_el_costado'] = sweep({'usb: funda de la clavija': groups['usb']['funda de la clavija']}, fo_obst, V(15, 0, 0))
log('funda por el costado:', sweeps['funda_usb_c_por_el_costado'])
# m, n. Bandas de TPU: la de abajo sube por abajo y la de arriba baja por arriba hasta su sitio. Se ponen sobre el
#    tubo con la tapa de puertos puesta y ANTES de los seis M2.5 radiales y de la tecla, que van despues por sus
#    agujeros y su ventana (como en el servicio): las cabezas avellanadas son planas sobre una pared curva y sus
#    cantos asoman 0.11 (diagnostico abajo), y la tecla asoma 1.0. La base y la tapa entran por dentro de las bandas
#    (barridos base_por_abajo y tapa_por_arriba, con las bandas). Se mide al reves (de su sitio hasta que sale).
#    Banda estirada (contorno interior = cuerpo + holgura_barrido): nada que quede dentro del contorno del cuerpo
#    + 0.01 la puede tocar, asi que se barre contra lo que sobresale de ese contorno de cada pieza y referencia
#    (exacto, y mucho mas rapido que contra las piezas enteras). Se comprueba que la banda estirada queda fuera.
BODY_OUT = G.body_prism(-60, 200, 0.01)


def protrusions(d):
    out = {}
    for k, v in d.items():
        bb = v.BoundBox
        if (math.hypot(max(abs(bb.XMin), abs(bb.XMax)), max(abs(bb.YMin), abs(bb.YMax))) < G.RO
                and bb.YMax < G.Y_FLAT_O):
            continue                       # su caja ya cae dentro del contorno del cuerpo
        try:
            c = v.cut(BODY_OUT)
        except Exception:
            out[k] = v                     # sin recorte: se barre entera
            continue
        if c.Solids and c.Volume > 1e-4:
            out[k + ' (lo que sobresale)'] = c
    return out


_case = {k: v for k, v in parts.items() if k not in ('05-key-tpu', G.BAND_NAMES['abajo'], G.BAND_NAMES['arriba'])}
_case.update({k: v for k, v in refs.items() if not k.startswith('tornillos:')})
BAND_OBST = protrusions(_case)
L_BB = G.band_z('abajo')[1] + 2.0                                                      # hasta salir por abajo
L_BT = G.H_TOTAL + P['antena']['altura'] - G.band_z('arriba')[0] + 2.0                  # hasta pasar la antena
sweeps['banda_de_abajo_por_abajo'] = sweep({'09-band-bottom-tpu (estirada)': BAND_B_ST}, BAND_OBST, V(0, 0, -L_BB))
sweeps['banda_de_arriba_por_arriba'] = sweep({'10-band-top-tpu (estirada)': BAND_T_ST}, BAND_OBST, V(0, 0, L_BT))
# o. Los seis M2.5 radiales por los agujeros de las bandas puestas (estiradas): cada uno, de su avellanado hacia fuera.
L_SC = 8.0
_scr_sw, _scr_gap = [], {}
for _cfg, _zs, _bs, _bn in ((P['base']['lenguetas'], P['base']['tornillos']['z'], BAND_B_ST, '09-band-bottom-tpu (estirada)'),
                            (P['tapa']['lenguetas'], P['tapa']['tornillos_z'], BAND_T_ST, '10-band-top-tpu (estirada)')):
    for _a in _cfg['angulos']:
        _sc = G.radial_screw(_a, _zs)
        _u = V(math.cos(math.radians(_a)), math.sin(math.radians(_a)), 0)
        _nm = f'M2.5 a {_a:g} grados, z {_zs:g}'
        _scr_sw += sweep({_nm: _sc}, {_bn: _bs}, _u * L_SC)
        _g = sweep_min_gaps(_sc, {_bn: _bs}, _u * L_SC, near=3.0)
        _scr_gap[_nm] = _g.get(_bn, (None, None))[0]
sweeps['tornillos_radiales_por_las_bandas'] = _scr_sw
_kp = protrusions({'05-key-tpu': KEY})
_sp = protrusions({k: v for k, v in refs.items() if k.startswith('tornillos:')})
band_sweep = {
    'metodo': ('Banda estirada (contorno interior = el del cuerpo + %g, espesor %g) barrida en pasos de %g mm contra lo '
               'que sobresale del contorno del cuerpo + 0.01 de cada pieza y referencia, sin la tecla ni los M2.5 radiales '
               '(van despues, por la ventana y los agujeros).' % (G.BD['holgura_barrido'], G.BD['espesor'], args.step)),
    'banda_estirada_dentro_del_contorno_mm3': {'abajo': round(common_vol(BAND_B_ST, BODY_OUT), 4),
                                               'arriba': round(common_vol(BAND_T_ST, BODY_OUT), 4)},
    'lo_que_sobresale': {k: round(v.Volume, 2) for k, v in BAND_OBST.items()},
    'recorrido_mm': {'abajo': L_BB, 'arriba': round(L_BT, 2), 'tornillos': L_SC},
    'holgura_minima_al_ponerla_mm': {
        'abajo': {k: {'mm': v[0], 'a_mm_de_su_sitio': v[1]} for k, v in sweep_min_gaps(BAND_B_ST, BAND_OBST, V(0, 0, -L_BB), near=5.0).items()},
        'arriba': {k: {'mm': v[0], 'a_mm_de_su_sitio': v[1]} for k, v in sweep_min_gaps(BAND_T_ST, BAND_OBST, V(0, 0, L_BT), near=5.0).items()}},
    'tornillos_por_los_agujeros_holgura_mm': _scr_gap,
    'cantos_de_las_cabezas_de_los_tornillos_sobre_la_pared_mm': round(math.hypot(G.RO, P['base']['tornillos']['avellanado_diametro'] / 2.0) - G.RO, 3),
    'con_la_tecla_puesta': sweep({'09-band-bottom-tpu (estirada)': BAND_B_ST}, _kp, V(0, 0, -L_BB)),
    'con_los_tornillos_radiales_puestos': (sweep({'09-band-bottom-tpu (estirada)': BAND_B_ST}, _sp, V(0, 0, -L_BB))
                                           + sweep({'10-band-top-tpu (estirada)': BAND_T_ST}, _sp, V(0, 0, L_BT))),
    '_nota': ('Orden: cada banda sobre el tubo (con la tapa de puertos ya puesta) antes de cerrar con la base o la tapa; la '
              'base y la tapa entran por dentro de ella y sus M2.5 radiales y la tecla van despues, por los agujeros y la '
              'ventana, como en el servicio. Con todo armado no pasaria limpia: la tecla asoma 1.0 y los cantos de las '
              'cabezas de los M2.5 (planas, sobre la pared curva de R28) asoman 0.11 (diagnosticos con_la_tecla_puesta y '
              'con_los_tornillos_radiales_puestos). El TPU pasaria por encima de 0.11 estirandose, pero el modelo no lo '
              'cuenta.')}
log('bandas al ponerlas:', sweeps['banda_de_abajo_por_abajo'], sweeps['banda_de_arriba_por_arriba'],
    sweeps['tornillos_radiales_por_las_bandas'], band_sweep)
report['barridos'] = sweeps
log('barridos:', {k: len(v) for k, v in sweeps.items()})


# --- 3. Holguras y radio del chasis armado -------------------------------------------------
comp_shapes = [v for k, v in board.items() if k != 'PCB' and 'tornillos' not in k]
pairs = {
    'chasis-tubo (contacto: pie de los rieles en sus repisas, z 9.5)': gap(CHS, TUBE_NL),
    'chasis-tubo por encima de las repisas (z > 9.6)': gap(CHS, TUBE_NL.common(box(-60, 60, -60, 60, 9.6, 200))),
    'chasis-celdas': min_gap(CHS, cell_refs.values()),
    'chasis-PCB de la placa': gap(CHS, board['PCB']),
    'chasis-componentes de la placa y OLED': min_gap(CHS, comp_shapes),
    'chasis-carrier (contactos: topes z 69 y ganchos z 17)': min_gap(CHS, carrier_refs.values()),
    'chasis-base': gap(CHS, BASE),
    'chasis-tapa': gap(CHS, CAP),
    'tubo-celdas (contacto: repisas, z 18.8)': min_gap(TUBE_NL, cell_refs.values()),
    'tubo-celdas por encima de las repisas (nervios)': min_gap(TUBE_NL.common(box(-60, 60, -60, 60, P['celdas']['z'][0] + 0.1, 200)), cell_refs.values()),
    'tubo-PCB de la placa': gap(TUBE_NL, board['PCB']),
    'tubo-componentes de la placa y OLED': min_gap(TUBE_NL, comp_shapes),
    'tubo-funda USB-C': gap(TUBE_NL, groups['usb']['funda de la clavija']),
    'tubo-tarjeta microSD': gap(TUBE_NL, groups['microsd']['tarjeta puesta']),
    'tapa-OLED': min_gap(CAP, [v for k, v in board.items() if 'OLED' in k]),
    'tapa-coaxial (recorrido)': gap(CAP, coax_refs['coaxial (recorrido)']),
    'tapa-celdas': min_gap(CAP, cell_refs.values()),
    'base-clavijas': min_gap(BASE, plug_refs.values()),
    'base-PCB de la placa': gap(BASE, board['PCB']),
    'base-celdas': min_gap(BASE, cell_refs.values()),
    'base-carrier': min_gap(BASE, carrier_refs.values()),
    'reten-celdas': min_gap(groups['tuerca']['reten M2 con arandela'], cell_refs.values()),
    'tecla-SW401 (juego del embolo)': gap(KEY, board.get('SW401', board['PCB'])) if 'SW401' in board else None,
    'tecla-componentes de la placa': min_gap(KEY, [v for k, v in board.items() if k not in ('SW401',)]),
    'carrier-PCB de la placa': min_gap(board['PCB'], carrier_refs.values()),
    'carrier (patas del SMA)-celdas': min_gap(groups['carrier']['patas del SMA (atrás)'], cell_refs.values()),
    'cables (reservas)-piezas': min([gap(c, p) for c in groups['cables'].values() for p in (TUBE_NL, CHS, BASE, CAP)]),
    'tuerca SMA-PCB con la muesca': gap(coax_refs['clavija SMA de la carrier'], board['PCB']),
    'coaxial (recorrido)-piezas': min(gap(coax_refs['coaxial (recorrido)'], p) for p in (TUBE_NL, CHS, CAP, BASE)),
    'coaxial (recorrido)-celdas': min_gap(coax_refs['coaxial (recorrido)'], cell_refs.values()),
    'coaxial (recorrido)-placa y OLED': min_gap(coax_refs['coaxial (recorrido)'], board.values()),
    'clavija SMA acodada-chasis (pedido >= 0.5)': gap(CHS, coax_refs['clavija SMA de la carrier']),
    'cables (reservas)-celdas': min_gap(G.fuse_all([v for k, v in groups['cables'].items() if 'NTC' not in k and 'ntc' not in k and 'mazo_pack' not in k]), cell_refs.values()),
    'cables (reservas)-placa y carrier': min_gap(G.fuse_all([v for k, v in groups['cables'].items() if 'arnes' not in k]),
                                                 [v for v in list(board.values()) + list(carrier_refs.values())]),
    'perno del baston (15.5)-soldaduras de la carrier': min_gap(groups['tuerca']['perno del baston (rosca maxima)'],
                                                              [v for k, v in groups['carrier'].items() if 'soldaduras' in k]),
    'perno del baston (15.5)-celdas': min_gap(groups['tuerca']['perno del baston (rosca maxima)'], cell_refs.values()),
    'guia de luz-componentes de la placa': min_gap(groups['frente']['guia de luz del LED'],
                                                   [v for k, v in board.items() if k != 'PCB' and 'OLED' not in k]),
    'tapa de puertos-chasis': gap(COVER, CHS),
    'tapa de puertos-tarjeta': gap(COVER, groups['microsd']['tarjeta puesta']),
}


def slab_gap(a, b, z0, z1):
    """Holgura entre las partes de a y b dentro de la rebanada z0-z1 (quita los apoyos de fuera)."""
    sl = box(-60, 60, -60, 60, z0, z1)
    try:
        aa, bb = a.common(sl), b.common(sl)
    except Exception:
        return None
    return gap(aa, bb) if aa.Solids and bb.Solids else None


_zt = P['placa']['z'][1]
RAIL_ZONE = box(15.5, 30, 11.5, 18.0, 9.0, _zt - 0.1).fuse(box(-30, -15.5, 11.5, 18.0, 9.0, _zt - 0.1))
RAILS = CHS.common(RAIL_ZONE)
_ant = P['antena']
_zc = G.Z_TUBE1 + _ant['avellanado_cabeza']
_kr = P['frente']['tecla']['rebaje']['hondo']
_cx_in = {k: v for k, v in coax_refs.items() if 'dentro' in k or 'antena hembra' in k}
pairs.update({
    'chasis-componentes de la carrier (sin su PCB)': min_gap(CHS, [v for k, v in carrier_refs.items() if not k.endswith('PCB')]),
    'rieles-PCB de la placa (sin el tope de z 80 ni los salientes)': gap(RAILS, board['PCB']),
    'tapa bajo el canto del tubo (labio y lenguetas)-tubo': slab_gap(CAP, TUBE_NL, G.Z_TUBE1 - 15, G.Z_TUBE1 - 0.02),
    'base sobre el canto del tubo (labio, lenguetas, saliente)-tubo': slab_gap(BASE, TUBE_NL, G.Z_TUBE0 + 0.02, 30),
    'tecla-tubo (sin la pestana pegada)': gap(KEY.common(box(-20, 20, -60, G.Y_FLAT_O - _kr - 0.05, 0, 200)), TUBE_NL),
    'tapa-tornillos de la antena (radial, en su rebaje)': slab_gap(CAP, groups['antena']['tornillos M2.5 de la antena'],
                                                                   G.Z_TUBE1 + 0.1, _zc - 0.1),
    'tapa-tuerca del pasamuros (radial, en su bolsillo)': (slab_gap(CAP, coax_refs['pasamuros SMA (dentro)'], G.Z_TUBE1 + 0.1,
                                                                    G.H_TOTAL - _ant['conector']['pasamuros']['panel'] - 0.1)
                                                           if 'pasamuros SMA (dentro)' in coax_refs else None),
    'conector de la tapa (dentro)-placa, OLED y celdas': min_gap(G.fuse_all(list(_cx_in.values())), list(board.values()) + list(cell_refs.values())),
    'coaxial (recorrido)-cables': min_gap(coax_refs['coaxial (recorrido)'], groups['cables'].values()),
    'clavija SMA acodada-celdas': min_gap(coax_refs['clavija SMA de la carrier'], cell_refs.values()),
    'clavija SMA acodada-placa y OLED (sin la muesca)': min_gap(coax_refs['clavija SMA de la carrier'],
                                                                [v for k, v in board.items() if k != 'PCB']),
    'tuerca del baston-placa y carrier': min_gap(groups['tuerca']['tuerca 5/8-11'], list(board.values()) + list(carrier_refs.values())),
})
# Marco del USB-C. Contactos a proposito: labio bajo el dorso de la placa y fondo de las ranuras en su
# canto (PCB) y resorte sobre el blindaje de J101. La funda va guiada a 0.3 por lado en el tunel del marco
# (de la boca hacia fuera); el collar y el labio quedan 0.2 detras de la boca (retranqueo).
_bbz = App.BoundBox(BEZEL.BoundBox)
_bbz.enlarge(4.0)
_near_board = [v for k, v in board.items() if k not in ('PCB', 'J101') and 'tornillos' not in k and v.BoundBox.intersect(_bbz)]
_ux0 = P['placa']['usb_c']['boca_x']
pairs.update({
    'marco-tubo': gap(BEZEL, TUBE_NL),
    'marco-chasis': gap(BEZEL, CHS),
    'marco-tapa de puertos': gap(BEZEL, COVER),
    'marco-componentes de la placa (sin J101)': (min_gap(BEZEL, _near_board) if REAL_BOARD else None),
    'marco-carrier': min_gap(BEZEL, carrier_refs.values()),
    'marco-celdas y cables': min_gap(BEZEL, list(cell_refs.values()) + list(groups['cables'].values())),
    'marco-PCB (contacto: labio bajo el dorso y fondo de las ranuras)': gap(BEZEL, board['PCB']),
    'marco sin resorte-J101 (abertura del collar)': gap(BEZEL_RIGID, board['J101']) if 'J101' in board else None,
    'marco-funda USB-C (tunel del marco, por lado)': gap(BEZEL.common(box(_ux0, 60, -60, 60, -60, 120)), groups['usb']['funda de la clavija']),
    'marco-funda USB-C (collar y labio detras de la boca, en x)': gap(BEZEL, groups['usb']['funda de la clavija']),
})
# Bandas de TPU (con su medida de impresion, como estan en el documento).
_scr = groups['tornillos']['tornillos M2.5 de base y tapa']
pairs.update({
    'banda de abajo-tapa de puertos (pedido >= 0.5)': gap(BAND_B, COVER),
    'banda de abajo-tecla (pedido >= 1.0)': gap(BAND_B, KEY),
    'banda de abajo-distintivo de TPU': gap(BAND_B, parts['07-logo-inlay-tpu']),
    'banda de arriba-distintivo de TPU': gap(BAND_T, parts['07-logo-inlay-tpu']),
    'banda de abajo-guia de luz del LED': gap(BAND_B, groups['frente']['guia de luz del LED']),
    'banda de abajo-tornillos de la base': gap(BAND_B, _scr),
    'banda de arriba-tornillos de la tapa': gap(BAND_T, _scr),
    'banda de arriba-lamina de la ventana': gap(BAND_T, groups['frente']['lamina de la ventana (PC 1.0)']),
    'banda de arriba-antena': gap(BAND_T, groups['antena']['antena HA-901A']),
})
report['holguras'] = pairs
log('holguras:', {k: v for k, v in pairs.items()})

# --- 3b. Holguras laterales durante los barridos verticales ---------------------------------
# En un barrido vertical cada seccion horizontal de la pieza movil (a z_m en su sitio) pasa por
# todas las alturas z_m + t del recorrido. La holgura lateral minima del barrido es la distancia 2D
# minima entre una seccion de la pieza y una del obstaculo (a z_o) con z_o - z_m dentro del
# recorrido. Secciones cada 0.5 mm, a mitad de paso (no caen en caras planas). Los choques los
# mide el barrido de arriba; aqui solo la holgura, y solo por debajo de SWEEP_CAP.
import numpy as np
SEC = {}
SWEEP_CAP = 2.0
PRINTED = ('01-base', '02-tube', '03-antenna-cap', '04-chassis', '05-key-tpu', '06-port-cover-tpu',
           '08-usb-bezel', 'chasis sin labios de gancho')


def sections(name, shape, dz=0.5, ds=0.05):
    """Secciones horizontales de una forma a mitad de cada paso dz: [(z, puntos del contorno cada ds)]."""
    if name in SEC:
        return SEC[name]
    bb = shape.BoundBox
    out = []
    pieces = OBST_SLABS.get(name) or [shape]       # rebanadas de 10 mm: cada corte sale mas barato
    z = math.floor(bb.ZMin / dz) * dz + dz / 2.0
    while z < bb.ZMax:
        src = next((q_ for q_ in pieces if q_.BoundBox.ZMin <= z <= q_.BoundBox.ZMax), None)
        try:
            polys = [np.array(p_) for p_ in G.section_polygons(src, z, ds) if len(p_) > 1] if src is not None else []
        except Exception:
            polys = []
        if polys:
            out.append((z, np.vstack(polys)))
        z += dz
    SEC[name] = out
    return out


TREES = {}


def lateral_sweep_gap(moving, obstacles, L, cap=SWEEP_CAP):
    """{(movil, obstaculo): holgura lateral minima} de las parejas que se acercan a menos de cap.
    Distancia entre puntos de los contornos (cada 0.05 mm: error de unas centesimas) con un KD-tree
    por seccion del obstaculo; cada seccion del obstaculo se compara con todas las de la pieza movil
    que pasan por su altura durante el recorrido."""
    from scipy.spatial import cKDTree
    lo, hi = (0.0, L) if L > 0 else (L, 0.0)
    res = {}
    for on, os_ in obstacles.items():
        ob = os_.BoundBox
        cand = {mn: ms for mn, ms in moving.items()
                if not (ms.BoundBox.XMin - cap > ob.XMax or ob.XMin - cap > ms.BoundBox.XMax
                        or ms.BoundBox.YMin - cap > ob.YMax or ob.YMin - cap > ms.BoundBox.YMax
                        or ms.BoundBox.ZMax + hi < ob.ZMin or ms.BoundBox.ZMin + lo > ob.ZMax)}
        if not cand:
            continue
        SO = sections(on, os_)
        if on not in TREES:
            TREES[on] = [cKDTree(pts) for _, pts in SO]
        trees = TREES[on]
        for mn, ms in cand.items():
            SM = sections(mn, ms)
            if not SM:
                continue
            zm = np.array([q_[0] for q_ in SM])
            pts_all = np.vstack([q_[1] for q_ in SM])
            offs = np.cumsum([0] + [len(q_[1]) for q_ in SM])
            best = None
            for j, (zo, opts) in enumerate(SO):
                i0_ = np.searchsorted(zm, zo - hi - 1e-9, side='left')
                i1_ = np.searchsorted(zm, zo - lo + 1e-9, side='right')
                if i1_ <= i0_:
                    continue
                P_ = pts_all[offs[i0_]:offs[i1_]]
                omin, omax = opts.min(0) - cap, opts.max(0) + cap
                sel = P_[(P_[:, 0] >= omin[0]) & (P_[:, 0] <= omax[0]) & (P_[:, 1] >= omin[1]) & (P_[:, 1] <= omax[1])]
                if not len(sel):
                    continue
                d = float(trees[j].query(sel, k=1, distance_upper_bound=cap)[0].min())
                if d < cap and (best is None or d < best):
                    best = d
            if best is not None:
                res[(mn, on)] = round(best, 3)
    return res


def category(mn, on):
    names = (mn, on)
    if mn.startswith(PRINTED) and on.startswith(PRINTED):
        return 'impresas'
    if 'placa: PCB' in names and any(n.startswith('04-chassis: salientes') for n in names):
        return 'contacto a proposito (placa contra los salientes)'
    if 'placa: PCB' in names and any(n.startswith('04-chassis: rieles') for n in names):
        return 'rieles'
    if 'carrier: PCB' in names and any(n.startswith(('chasis sin labios', '04-chassis')) for n in names):
        return 'carrier-ranuras'
    return 'compradas'


T3 = time.time()
lat = {}
lat['celdas_por_arriba'] = lateral_sweep_gap(cell_refs, {'02-tube': TUBE_NL, '01-base': BASE}, UP_CELLS)
lat['carrier_al_chasis_por_abajo'] = lateral_sweep_gap(carrier_refs, {'chasis sin labios de gancho': chs_no_hooks}, -60)
_o = {'04-chassis': CHS}
_o.update(carrier_no_barrel)
lat['clavija_sma_por_arriba_sin_placa'] = lateral_sweep_gap({'coaxial: clavija SMA (tuerca Ø9.2 y cuerpo)': plug_sh}, _o, 25)
_sx, _sz = P['chasis']['salientes']['x'], P['chasis']['salientes']['z']
_bz = G.fuse_all([box(sg_ * _sx - 3.0, sg_ * _sx + 3.0, 7.5, 13.9, _sz - 3.0, _sz + 3.0) for sg_ in (-1, 1)])
_o = {'04-chassis: rieles': RAILS, '04-chassis: salientes M2': CHS.common(_bz), '04-chassis: resto': CHS.cut(RAIL_ZONE).cut(_bz),
      'coaxial: clavija SMA (tuerca Ø9.2 y cuerpo)': plug_sh}
_o.update(carrier_refs)
lat['placa_al_chasis_por_abajo'] = lateral_sweep_gap(board_mov, _o, -92)
_o = {'02-tube': TUBE_NL, '01-base': BASE, '06-port-cover-tpu': COVER}
_o.update(cell_refs)
_o.update(batt)
lat['chasis_armado_por_arriba_sin_tecla'] = lateral_sweep_gap(assembly, _o, UP_CHS)
_o = {'02-tube': TUBE_NL, '04-chassis': CHS}
for _g in (board_refs, carrier_refs, cell_refs, {f'clavijas: {k}': v for k, v in plug_refs.items()},
           {f'cables: {k}': v for k, v in groups['cables'].items()}):
    _o.update(_g)
lat['base_por_abajo'] = lateral_sweep_gap(base_mov, _o, -20)
_o = {'02-tube': TUBE_NL, '04-chassis': CHS, 'coaxial: clavija SMA (tuerca Ø9.2 y cuerpo)': plug_sh}
for _g in (board_refs, cell_refs, batt):
    _o.update(_g)
lat['tapa_por_arriba'] = lateral_sweep_gap(cap_mov, _o, 20)
lat_min = {}
for sw, dd in lat.items():
    for (mn, on), v in dd.items():
        c = category(mn, on)
        if c not in lat_min or v < lat_min[c]['mm']:
            lat_min[c] = {'mm': v, 'barrido': sw, 'movil': mn, 'obstaculo': on}
report['holguras_laterales_en_barridos'] = {
    'minimos_por_categoria': lat_min,
    'por_barrido': {sw: [{'movil': mn, 'obstaculo': on, 'mm': v} for (mn, on), v in sorted(dd.items(), key=lambda kv: kv[1])[:12]]
                    for sw, dd in lat.items()},
    '_nota': (f'Holgura lateral minima de cada barrido vertical (secciones cada 0.5 mm); solo parejas a menos de {SWEEP_CAP} mm, '
              'las 12 mas justas por barrido. Contactos a proposito: placa contra los salientes (y 13.8).')}
log('holguras laterales en barridos (%.0f s):' % (time.time() - T3), lat_min)

# Tapa de puertos: holguras de la cabeza de la seta por dentro (en su sitio y al bajar o subir el
# chasis: columna vertical de la cabeza contra el chasis armado) y tapa abierta en la bisagra.
an = tpp['ancla']
heads = COVER_ANCHOR.common(G.cyl_z(G.RI - 0.01, 0, 0, 0, 100))
asm_parts = {'04-chassis': CHS, 'coaxial: clavija SMA': coax_refs['clavija SMA de la carrier']}
asm_parts.update(board_refs)
asm_parts.update(carrier_refs)
asm_parts['cables: cable arnes_j301'] = groups['cables']['cable arnes_j301']
fixed = dict(cell_refs)
fixed.update(batt)
fixed['01-base'] = BASE
ux0_, uyc_, uzc_, uh_, uw_, ur_ = G.usb_tunnel()
sx0_, sy0_, sy1_, szc_, sw_ = G.sd_slot()
mu_ = P['costado']['microsd']['muesca']
usb_open = G.rounded_rect_x(ux0_, 40, uyc_, uzc_, uh_, uw_, ur_)
sd_open = box(sx0_, 40, sy0_, sy1_, szc_ - sw_ / 2, szc_ + sw_ / 2).fuse(G.sd_notch(x1=40))
anchors_rep = {}
for za in G.anchor_zs():
    # Cabeza de esta seta y su planta (seccion por el plano de su eje, extruida a todo lo alto): lo
    # que barre el chasis al subir o bajar.
    head = heads.common(box(-60, 60, -60, 60, za - 3, za + 3))
    _hw = head.slice(V(0, 0, 1), za)
    _hf = Part.Face(Part.Wire(_hw[0].Edges)) if len(_hw) == 1 else Part.makeFace(_hw, 'Part::FaceMakerBullseye')
    _hf.translate(V(0, 0, -10 - za))
    column = _hf.extrude(V(0, 0, 130))
    fx = dict(fixed)
    fx['02-tube (sin la pared del agujero)'] = TUBE_NL.cut(G.cyl_z(G.RO + 1, 0, 0, za - 4, za + 4).cut(G.cyl_z(G.RI - 0.3, 0, 0, za - 5, za + 5)))
    hole = B.radial_hole(an['angulo'], za, an['agujero'], G.RO + 1.0, G.RI - 0.5)
    anchors_rep[f'z {za:g}'] = {
        'cabeza_en_su_sitio_mm': {k: gap(head, v) for k, v in fx.items()},
        'cabeza_al_barrer_el_chasis_mm': min_gap(column, asm_parts.values()),
        'pared_entre_el_agujero_y_otras_aberturas_mm': {'tunel USB-C': gap(hole, usb_open), 'ranura microSD y muesca': gap(hole, sd_open),
                                                        'lineas decorativas': gap(hole, B.decorative_lines())}}
ha = math.radians(tpp['bisagra']['angulo'])
Hh = V(G.RO * math.cos(ha), G.RO * math.sin(ha), 0)
plb = P['placa']
over_path = G.rounded_rect_x(plb['usb_c']['boca_x'], 60, G.USB_Y, G.USB_Z, plb['funda_usb']['alto'], plb['funda_usb']['ancho'],
                             plb['funda_usb'].get('radio', 0.0))
tj = plb['tarjeta']
zc_sd = G.SD_Z
card_path = box(tj['x_fuera'] - tj['largo'], 60, tj['y0'], tj['y0'] + tj['espesor'], zc_sd - tj['ancho'] / 2, zc_sd + tj['ancho'] / 2)


def cover_open(ang):
    fr_ = COVER_FRONT.copy()
    fr_.rotate(Hh, V(0, 0, 1), -ang)
    return fr_


def cover_max_angle(band_shape, step=1.0, tol=0.05):
    """Angulo hasta el que gira la tapa (solido rigido, en la bisagra) sin que su volumen comun con la banda pase
    de LIM. Pasos de `step` grados y biseccion hasta `tol`. (angulo, angulo en que ya choca o None)."""
    lo, a = 0.0, step
    while a <= 180.0 + 1e-9:
        if common_vol(cover_open(a), band_shape) > LIM:
            hi = a
            while hi - lo > tol:
                m_ = (lo + hi) / 2.0
                if common_vol(cover_open(m_), band_shape) > LIM:
                    hi = m_
                else:
                    lo = m_
            return round(lo, 2), round(hi, 2)
        lo, a = a, a + step
    return 180.0, None


opened = {}
for ang in (135, 180):
    fr = cover_open(ang)
    opened[str(ang)] = {'funda_mm3': round(common_vol(fr, over_path), 3), 'funda_holgura': gap(fr, over_path),
                        'tarjeta_mm3': round(common_vol(fr, card_path), 3), 'tarjeta_holgura': gap(fr, card_path),
                        'banda_de_abajo_estirada_mm3': round(common_vol(fr, BAND_B_ST), 3)}
# Con la banda de abajo puesta: angulo maximo (banda estirada, la de verdad; y con la medida de impresion, informativo)
# y holguras a la funda y a la tarjeta en ese angulo.
_amax, _ahit = cover_max_angle(BAND_B_ST)
_amax_p, _ahit_p = cover_max_angle(BAND_B)
_fr = cover_open(_amax)
cover_band = {'angulo_maximo_grados': _amax, 'choca_a_los_grados': _ahit,
              'funda_holgura': gap(_fr, over_path), 'funda_mm3': round(common_vol(_fr, over_path), 3),
              'tarjeta_holgura': gap(_fr, card_path), 'tarjeta_mm3': round(common_vol(_fr, card_path), 3),
              'banda_holgura': gap(_fr, BAND_B_ST), 'cerrada_a_la_banda_impresa_mm': gap(COVER, BAND_B),
              'cerrada_a_la_banda_estirada_mm': gap(COVER, BAND_B_ST),
              'angulo_maximo_con_la_banda_impresa_grados': _amax_p, 'objetivo_grados': 135.0,
              'cumple': bool(_amax >= 135.0 - 1e-6),
              '_nota': ('Parte de delante de la bisagra girada como solido rigido contra la banda de abajo ESTIRADA (como esta '
                        'montada: por fuera llega a r %g); con la medida de impresion (por fuera r %g) llega algo mas. Pasos de 1 '
                        'grado y biseccion. Lo que la para es el canto de atras de la muesca de la banda.'
                        % (G.RO + G.BD['holgura_barrido'] + G.BD['espesor'], G.RO - G.BD['apriete'] + G.BD['espesor']))}
report['tapa_de_puertos'] = {
    'ancla': {'angulo': an['angulo'], 'z': G.anchor_zs(), 'agujero': an['agujero']},
    'anclas': anchors_rep,
    'cabeza_al_barrer_el_chasis_mm': min(v['cabeza_al_barrer_el_chasis_mm'] for v in anchors_rep.values()),
    'cabeza_en_su_sitio_min_mm': min(min(v['cabeza_en_su_sitio_mm'].values()) for v in anchors_rep.values()),
    'pared_agujeros_min_mm': min(min(v['pared_entre_el_agujero_y_otras_aberturas_mm'].values()) for v in anchors_rep.values()),
    'abierta_girada_en_la_bisagra': opened,
    'abierta_con_la_banda_puesta': cover_band,
    '_nota': ('Tres anclas. Abierta: la parte de delante de la bisagra girada como solido rigido; en la realidad el TPU se dobla '
              '(su duracion y el sellado hay que probarlos impresos). Con 135 grados o mas deja libres la funda del USB-C y la tarjeta.')}
log('tapa de puertos:', report['tapa_de_puertos']['cabeza_al_barrer_el_chasis_mm'], opened, cover_band)

# Antena del ESP32-S3-WROOM-1 (U201): los ultimos 6 mm del modulo, en el canto -X. Como en V2.3,
# nada de plastico del chasis a menos de 5 mm (zona = caja de la antena desplazada 5 mm).
aw = P['chasis']['antena_wroom']
ant = box(aw['x'][0], aw['x'][1], aw['y'][0], aw['y'][1], aw['z'][0], aw['z'][1])
zone5 = ant.makeOffsetShape(aw['margen'], 1e-3, join=0)
c5 = CHS.common(zone5)
report['antena_wroom'] = {
    'zona_antena': {'x': aw['x'], 'y': aw['y'], 'z': aw['z']},
    'chasis_a_menos_de_5_mm_mm3': round(c5.Volume, 1) if c5.Solids else 0.0,
    'piezas_dentro': [[round(v, 2) for v in (q.BoundBox.XMin, q.BoundBox.XMax, q.BoundBox.YMin, q.BoundBox.YMax,
                                              q.BoundBox.ZMin, q.BoundBox.ZMax)] + [round(q.Volume, 1)] for q in (c5.Solids if c5.Solids else [])],
    'chasis_a_la_antena_mm': gap(CHS, ant),
    'tubo_a_la_antena_mm': gap(TUBE_NL, ant),
    'U201_en_el_STEP': [round(v, 2) for v in (board['U201'].BoundBox.XMin, board['U201'].BoundBox.XMax,
                                            board['U201'].BoundBox.ZMin, board['U201'].BoundBox.ZMax)] if 'U201' in board else None,
    '_nota': 'Lo que queda dentro de los 5 mm es el saliente M2 de la OLED del lado -X, detras de la placa (y 8-13.8, z 67.7-72.7): no se puede mover. El tubo (la pared) no cuenta.'}
log('antena WROOM:', report['antena_wroom']['chasis_a_menos_de_5_mm_mm3'], 'mm3 a menos de 5 mm')

# Nada de la placa por detras de su dorso (y 13.8) delante del SMA de la carrier (cuerpo y canon).
db = P['coaxial']['detras_placa']
behind = box(db['x'][0], db['x'][1], db['y'][0], db['y'][1], db['z'][0], db['z'][1])
bh = []
for k, v in board.items():
    vol = common_vol(v, behind)
    if vol > 0.001:
        bh.append({'pieza': k, 'mm3': round(vol, 3), 'y_min': round(v.BoundBox.YMin, 2)})
report['placa_detras_del_dorso_frente_al_SMA'] = {'zona': db, 'piezas': bh, 'ok': not bh,
                                                 'step': str(args.board) if args.board and not args.envelope else 'envolvente',
                                                 'step_fecha': (__import__('time').strftime('%Y-%m-%d %H:%M', __import__('time').localtime(args.board.stat().st_mtime))
                                                                if args.board and not args.envelope else None)}
log('detras del dorso frente al SMA:', bh if bh else 'nada')

# Holguras a la cara plana del tubo (pared de y 20.5 a 22.9 en |x| <= 15.33), pieza a pieza.
front_wall = TUBE_NL.common(box(-G.X_FLAT, G.X_FLAT, G.Y_FLAT_I - 0.5, G.Y_FLAT_O + 1, 0, G.Z_TUBE1 + 1))   # sin el logo (por fuera): mucho mas rapido
fw = {
    'vidrio OLED (y 20.0)': gap(front_wall, board['OLED vidrio']) if 'OLED vidrio' in board else None,
    'OLED: PCB, cinta y tornillos': min_gap(front_wall, [v for k, v in board.items() if 'OLED' in k and 'vidrio' not in k]),
    'componentes de la placa (envolvente o STEP)': min_gap(front_wall, [v for k, v in board.items() if 'OLED' not in k and k != 'PCB']),
    'clavijas (y 19.8)': min_gap(front_wall, plug_refs.values()),
    'tecla: pestana contra la cara interior (contacto)': gap(front_wall, KEY),
    'tecla: volumen dentro de la pared (mm3)': round(common_vol(front_wall, KEY), 3),
    'chasis (lo mas cercano)': gap(front_wall, CHS),
}
report['holguras_cara_plana'] = fw
log('cara plana:', fw)

ring_angles = P['tubo']['ranuras_rieles']['angulos']


def in_groove(x, y):
    a = math.degrees(math.atan2(y, x)) % 360
    return any(a0 <= a <= a1 for a0, a1 in ring_angles)


r_all, r_out = 0.0, 0.0
for s in [CHS, BEZEL] + list(board.values()) + list(carrier_refs.values()):
    pts = [v.Point for v in s.Vertexes]
    for e in s.Edges:
        try:
            pts += e.discretize(Distance=0.5)
        except Exception:
            pass
    for p in pts:
        r = math.hypot(p.x, p.y)
        r_all = max(r_all, r)
        if not in_groove(p.x, p.y):
            r_out = max(r_out, r)
report['chasis_armado'] = {
    'radio_max': round(r_all, 3), 'radio_max_fuera_de_ranuras': round(r_out, 3),
    'radio_interior_tubo': G.RI, 'radio_fondo_ranuras': P['tubo']['ranuras_rieles']['radio'],
    'holgura_minima_al_tubo_por_encima_de_las_repisas': min_gap(TUBE_NL.common(box(-60, 60, -60, 60, 9.6, 200)),
                                                                [CHS, BEZEL] + list(board.values()) + list(carrier_refs.values())),
    '_nota': (f'Chasis con la placa, la carrier y el marco del USB-C. Radio sobre vertices y aristas discretizadas cada 0.5 mm. Tubo sin ranuras: interior R{G.RI:g}; en '
              f'|x| <= {G.X_FLAT:g} el interior llega a la cara plana (y {G.Y_FLAT_I:g}).')}
_rc = P['coaxial']['radio_curva']
_cp = G.coax_route()
report['coaxial'] = {'cable': P['coaxial']['cable'], 'radio_curva_disponible': round(coax_R, 2),
                     'radio_curva_objetivo': _rc['objetivo'], 'radio_curva_preferido': _rc['preferido'],
                     # 1e-6: los arcos son de R exacto; la poligonal da 9.99999999999 por redondeo.
                     'cumple_objetivo': coax_R >= _rc['objetivo'] - 1e-6, 'cumple_preferido': coax_R >= _rc['preferido'] - 1e-6,
                     'largo_del_recorrido_mm': round(sum(math.dist(a_, b_) for a_, b_ in zip(_cp[:-1], _cp[1:])), 1),
                     'radio_max_del_eje_del_cable': round(max(math.hypot(q_[0], q_[1]) for q_ in _cp), 2),
                     'z_del_recorrido': [round(min(q_[2] for q_ in _cp), 2), round(max(q_[2] for q_ in _cp), 2)]}


# --- 3c. Marco del USB-C: atrapado, espesores, una sola pieza -----------------------------------
def free_travel(shape, obstacles, u, t_max=2.0, coarse=0.1, tol=0.005, lim=0.002):
    """Recorrido libre de `shape` en la direccion u hasta que su volumen comun con un obstaculo pasa de
    `lim` mm3. Devuelve (mm, obstaculo que lo para); (None, None) si pasa de t_max."""
    def hits(t):
        m = shape.translated(u * t)
        bb = m.BoundBox
        for on, os_ in obstacles.items():
            if bb.intersect(os_.BoundBox) and common_vol(m, os_) > lim:
                return on
        return None
    prev, t = 0.0, coarse
    while t <= t_max + 1e-9:
        h = hits(t)
        if h:
            lo, hi = prev, t
            while hi - lo > tol:
                mid = (lo + hi) / 2.0
                if hits(mid):
                    hi = mid
                else:
                    lo = mid
            return round(lo, 3), hits(hi)
        prev, t = t, t + coarse
    return None, None


def min_thickness_axes(shape, step=0.5, limits=None):
    """Espesor minimo de `shape` en secciones normales a z, a x y a y (G.min_wall_thickness, que ignora
    0.6 mm alrededor de las esquinas vivas). limits = {eje: (min, max)}: niveles de seccion a usar en ese
    eje. {eje: (mm, [x, y, z])}."""
    res = {}
    limits = limits or {}
    for ax, rot in (('z', None), ('x', (V(0, 1, 0), 90)), ('y', (V(1, 0, 0), -90))):
        s_ = shape.copy()
        if rot:
            s_.rotate(V(), rot[0], rot[1])
        bb = s_.BoundBox
        zs = G._frange(bb.ZMin + 0.13, bb.ZMax - 0.13, step)
        lo_, hi_ = limits.get(ax, (None, None))
        real = (lambda zz: zz) if ax == 'z' else (lambda zz: -zz)      # nivel en la pieza sin girar
        zs = [zz for zz in zs if (lo_ is None or real(zz) >= lo_) and (hi_ is None or real(zz) <= hi_)]
        th, w = G.min_wall_thickness(s_, zs, (bb.XMin - 1, bb.XMax + 1, bb.YMin - 1, bb.YMax + 1))
        if w is not None:
            a, b, c = w
            w = {'z': [a, b, c], 'x': [-c, b, a], 'y': [a, -c, b]}[ax]
        res[ax] = (th, w)
    return res


T3c = time.time()
tr_obst = {'02-tube': TUBE_NL, '04-chassis': CHS, '06-port-cover-tpu': COVER}
tr_obst.update({k: v for k, v in board_refs.items() if v.BoundBox.intersect(_bbz)})
tr_obst.update(carrier_refs)
travel = {}
for nm_, u_ in (('+x (hacia el tubo)', V(1, 0, 0)), ('-x (hacia dentro)', V(-1, 0, 0)), ('+y (hacia la cara plana)', V(0, 1, 0)),
                ('-y (hacia atras)', V(0, -1, 0)), ('+z', V(0, 0, 1)), ('-z', V(0, 0, -1))):
    t_, by_ = free_travel(BEZEL_RIGID, tr_obst, u_)
    travel[nm_] = {'mm': t_, 'lo_para': by_}
# Sin el tope cilindrico del resorte (sus secciones cerca del fondo son tiras finas: no es pared) y, en las
# secciones normales a x, sin el extremo de fuera (r 25.2: corta en sesgo el canto del suelo).
_bf = G.bezel_frame()
_rs = _bf['mc']['resorte']
_bump_box = box(_rs['x0'] - 1, _bf['xc'], _bf['y_shell'] - 1.0, _bf['y_shell'] + _bf['mc']['cuerpo_usb']['holgura'], _rs['z'][0] - 1, _rs['z'][1] + 1)
_x_end = math.sqrt(P['chasis']['r_max'] ** 2 - (_bf['uyc'] - _bf['uh'] / 2.0) ** 2) - 0.05
th_bz = min_thickness_axes(BEZEL.cut(_bump_box), limits={'x': (None, _x_end)})
th_rig = min_thickness_axes(BEZEL_RIGID, limits={'x': (None, _x_end)})
_wmin = min(v[0] for v in th_bz.values())
_wrig = min(v[0] for v in th_rig.values())
_mc = P['costado']['usb_c']['marco']
_ov = BEZEL_SPRING.common(board['J101']) if 'J101' in board else None
_pen = round(_ov.optimalBoundingBox().YLength, 3) if _ov is not None and _ov.Solids else None   # tope contra el techo real
report['marco_usb_c'] = {
    'volumen_cm3': round(BEZEL.Volume / 1000.0, 3), 'solidos': len(BEZEL.Solids), 'cascaras': len(BEZEL.Shells),
    'valido': BEZEL.isValid(), 'una_pieza_sin_huecos_cerrados': len(BEZEL.Solids) == 1 and len(BEZEL.Shells) == 1,
    'caja': [round(v, 2) for v in (BEZEL.BoundBox.XMin, BEZEL.BoundBox.XMax, BEZEL.BoundBox.YMin, BEZEL.BoundBox.YMax,
                                   BEZEL.BoundBox.ZMin, BEZEL.BoundBox.ZMax)],
    'recorrido_libre_con_el_chasis_en_el_tubo_mm': travel,
    'espesor_minimo_mm': {k: {'mm': v[0], 'donde': v[1]} for k, v in th_bz.items()},
    'espesor_minimo_sin_el_resorte_mm': {k: {'mm': v[0], 'donde': v[1]} for k, v in th_rig.items()},
    'espesor_objetivo_mm': {'paredes': _bf['mc']['pared_minima'], 'local': _bf['mc']['pared_local_minima']},
    'espesor_minimo_cumple': bool(_wmin >= _bf['mc']['pared_local_minima'] - 1e-3 and _wrig >= _bf['mc']['pared_minima'] - 1e-3),
    'resorte_J101_mm3': intended_rep.get('08-usb-bezel / placa: J101', {}).get('mm3'),
    'resorte_J101_penetracion_mm': _pen,
    '_nota': ('Parte rigida (sin el resorte) movida en cada sentido hasta tocar el tubo, el chasis, la tapa de puertos, la '
              'placa (PCB y componentes, J101 incluido) o la carrier. Espesor: secciones cada 0.5 mm normales a cada eje; el '
              'dedo del resorte mide 0.8 a proposito (local minima de esta pieza); sin el resorte, objetivo 1.0. Penetracion del resorte: tope nominal contra el '
              'techo del blindaje en el STEP real.')}
log('marco (%.0f s):' % (time.time() - T3c), report['marco_usb_c'])


# --- 3d. Que se ve desde fuera por el USB-C y por la ranura de la microSD -------------------------
# Rayos desde la piel exterior del tubo, dentro de cada abertura, hacia -X: de frente y oblicuos hasta
# 30 grados en y y en z (rejilla de 7 x 7 direcciones). Se anota lo primero que toca cada rayo. Trazado
# propio (Moller-Trumbore con numpy) sobre la teselacion: Mesh.nearestFacetOnRay de FreeCAD toma la recta
# en los dos sentidos.
def tri_scene(objs, clip, near, defl=0.04, far_defl=0.15):
    tris, lab, names = [], [], []
    for nm_, s_ in objs.items():
        if s_ is None or s_.isNull() or not s_.BoundBox.intersect(clip.BoundBox):
            continue
        if s_.BoundBox.XLength > 40 or s_.BoundBox.ZLength > 60:
            try:
                s_ = s_.common(clip)
            except Exception:
                pass
        if not s_.Faces:
            continue
        pts_, fac_ = s_.tessellate(defl if s_.BoundBox.intersect(near.BoundBox) else far_defl)
        if not fac_:
            continue
        Pn = np.array([[q_.x, q_.y, q_.z] for q_ in pts_], float)
        tris.append(Pn[np.array(fac_, int)])
        lab.append(np.full(len(fac_), len(names)))
        names.append(nm_)
    return np.concatenate(tris), np.concatenate(lab), names


def trace(scene, origins, d, cell=0.5):
    """Primer choque hacia delante (t > 0) de cada rayo origen + t d: [(etiqueta, punto)]."""
    tris, lab, names = scene
    O = np.asarray(origins, float)
    d = np.asarray(d, float) / np.linalg.norm(d)
    a_ = np.array([0.0, 0.0, 1.0]) if abs(d[2]) < 0.9 else np.array([1.0, 0.0, 0.0])
    u_ = np.cross(d, a_)
    u_ /= np.linalg.norm(u_)
    Bm = np.stack([u_, np.cross(d, u_)], 1)
    O2, T2 = O @ Bm, tris @ Bm
    lo, hi = T2.min(1), T2.max(1)
    rlo, rhi = O2.min(0) - 1e-6, O2.max(0) + 1e-6
    keep = (hi[:, 0] >= rlo[0]) & (lo[:, 0] <= rhi[0]) & (hi[:, 1] >= rlo[1]) & (lo[:, 1] <= rhi[1])
    keep &= (tris @ d).max(1) > (O @ d).min() - 1e-6
    T, L, lo, hi = tris[keep], lab[keep], lo[keep], hi[keep]
    v0 = T[:, 0]
    e1, e2 = T[:, 1] - v0, T[:, 2] - v0
    pv = np.cross(d, e2)
    det = np.einsum('ij,ij->i', e1, pv)
    ok = np.abs(det) > 1e-12
    inv = np.where(ok, 1.0 / np.where(ok, det, 1.0), 0.0)
    out = [(None, None)] * len(O)
    cells = {}
    for k_, ij in enumerate(map(tuple, np.floor((O2 - rlo) / cell).astype(int))):
        cells.setdefault(ij, []).append(k_)
    for (i_, j_), ks in cells.items():
        c0 = rlo + np.array([i_, j_]) * cell
        c1 = c0 + cell
        idx = np.nonzero(ok & (hi[:, 0] >= c0[0]) & (lo[:, 0] <= c1[0]) & (hi[:, 1] >= c0[1]) & (lo[:, 1] <= c1[1]))[0]
        if not len(idx):
            continue
        tv = O[ks][:, None, :] - v0[idx][None]
        uu = np.einsum('kcj,cj->kc', tv, pv[idx]) * inv[idx]
        qv = np.cross(tv, e1[idx][None])
        vv = np.einsum('kcj,j->kc', qv, d) * inv[idx]
        tt = np.einsum('kcj,cj->kc', qv, e2[idx]) * inv[idx]
        tt = np.where((uu >= -1e-9) & (vv >= -1e-9) & (uu + vv <= 1 + 1e-9) & (tt > 1e-6), tt, np.inf)
        best = tt.argmin(1)
        for r_, k_ in enumerate(ks):
            tb = tt[r_, best[r_]]
            if np.isfinite(tb):
                out[k_] = (names[L[idx[best[r_]]]], tuple(O[k_] + tb * d))
    return out


VIS_ANG = (-30, -20, -10, 0, 10, 20, 30)
VIS_OK = ('marco', 'tubo', 'tapa de puertos', 'J101', 'J401', 'tarjeta', 'canto de la PCB bajo J101 (permitido)')
_mu = P['placa']['muesca_usb']


def vis_class(lab_, p):
    if lab_ is None:
        return 'nada (sale)'
    if lab_ == 'placa: PCB':
        x_, y_, z_ = p
        if abs(x_ - _mu['x'][0]) < 0.03 and G.PL['y_dorso'] - 0.02 <= y_ <= G.PL['y_cara'] + 0.02 and _mu['z'][0] <= z_ <= _mu['z'][1]:
            return 'canto de la PCB bajo J101 (permitido)'
        if abs(z_ - _mu['z'][0]) < 0.03 or abs(z_ - _mu['z'][1]) < 0.03:
            return 'PCB: lados de la muesca del USB-C'
        if abs(x_ - G.PL['x']) < 0.03:
            return 'PCB: canto exterior (x 18)'
        if abs(y_ - G.PL['y_cara']) < 0.03:
            return 'PCB: cara de componentes'
        if abs(y_ - G.PL['y_dorso']) < 0.03:
            return 'PCB: dorso'
        return 'PCB: agujeros y cantos'
    for k_, n_ in (('08-usb-bezel', 'marco'), ('02-tube', 'tubo'), ('06-port-cover', 'tapa de puertos'),
                   ('placa: J101', 'J101'), ('placa: J401', 'J401'), ('microsd: tarjeta', 'tarjeta')):
        if lab_.startswith(k_):
            return n_
    return lab_


def skin_origins(rects, step, jitter=None):
    """Origenes en la piel exterior (r 28) dentro de las aberturas: rects = [(y0, y1, z0, z1, dentro(y, z))]."""
    out = []
    for y0_, y1_, z0_, z1_, inside in rects:
        for y_ in np.arange(y0_ + step / 2, y1_, step):
            for z_ in np.arange(z0_ + step / 2, z1_, step):
                yy, zz = (y_, z_) if jitter is None else (y_ + jitter.uniform(-step / 2, step / 2), z_ + jitter.uniform(-step / 2, step / 2))
                if inside(yy, zz):
                    out.append((math.sqrt(G.RO ** 2 - yy * yy) + 0.05, yy, zz))
    return out


def visibility(scene, rects, label):
    rng = np.random.default_rng(1)
    cnt, cnt_ang, other = {}, {}, {}
    n_tot = 0
    for ay in VIS_ANG:
        for az in VIS_ANG:
            d = np.array([-1.0, math.tan(math.radians(ay)), math.tan(math.radians(az))])
            org = skin_origins(rects, 0.2, rng)
            amax = str(max(abs(ay), abs(az)))
            for (lab_, p), o in zip(trace(scene, org, d), org):
                c_ = vis_class(lab_, p)
                cnt[c_] = cnt.get(c_, 0) + 1
                ca = cnt_ang.setdefault(amax, [0, 0])
                ca[0] += 1
                n_tot += 1
                if c_ not in VIS_OK:
                    ca[1] += 1
                    other.setdefault(c_, []).append((ay, az, o, p))
    org0 = skin_origins(rects, 0.05)
    c0 = {}
    for (lab_, p), o in zip(trace(scene, org0, (-1.0, 0.0, 0.0)), org0):
        c_ = vis_class(lab_, p)
        c0[c_] = c0.get(c_, 0) + 1
    pct = lambda k, n: round(100.0 * k / n, 2)
    n_other = sum(v for k, v in cnt.items() if k not in VIS_OK)
    det = []
    for c_, l_ in sorted(other.items(), key=lambda kv: -len(kv[1])):
        P_ = np.array([q[3] for q in l_ if q[3] is not None]) if any(q[3] is not None for q in l_) else None
        O_ = np.array([q[2] for q in l_])
        det.append({'que': c_, 'rayos': len(l_), 'pct': pct(len(l_), n_tot),
                    'choques_x_y_z': [[round(P_[:, i].min(), 2), round(P_[:, i].max(), 2)] for i in range(3)] if P_ is not None else None,
                    'entran_por_y_z': [[round(O_[:, i].min(), 2), round(O_[:, i].max(), 2)] for i in (1, 2)],
                    'direcciones_ay_az': sorted(set((q[0], q[1]) for q in l_))})
    n0 = sum(c0.values())
    return {'abertura': label, 'rayos': n_tot, 'direcciones': len(VIS_ANG) ** 2, 'angulos_grados': list(VIS_ANG),
            'otro_pct': pct(n_other, n_tot), 'permitido_pct': pct(n_tot - n_other, n_tot),
            'por_categoria_pct': {k: pct(v, n_tot) for k, v in sorted(cnt.items(), key=lambda kv: -kv[1])},
            'otro_pct_por_angulo_max': {k: pct(v[1], v[0]) for k, v in sorted(cnt_ang.items(), key=lambda kv: int(kv[0]))},
            'de_frente': {'rayos': n0, 'rejilla_mm': 0.05, 'otro_pct': pct(sum(v for k, v in c0.items() if k not in VIS_OK), n0),
                          'por_categoria_pct': {k: pct(v, n0) for k, v in sorted(c0.items(), key=lambda kv: -kv[1])}},
            'lo_que_se_ve_ademas': det}


T3d = time.time()
ha_ = math.radians(tpp['bisagra']['angulo'])
cov_open = COVER_FRONT.copy()
cov_open.rotate(V(G.RO * math.cos(ha_), G.RO * math.sin(ha_), 0), V(0, 0, 1), -150)
vis_objs = {'02-tube': TUBE_NL, '04-chassis': CHS, '08-usb-bezel': BEZEL, '06-port-cover-tpu (abierta 150)': cov_open,
            '06-port-cover-tpu (anclas)': COVER_ANCHOR, '05-key-tpu': KEY, '01-base': BASE, '03-antenna-cap': CAP,
            G.BAND_NAMES['abajo']: BAND_B, G.BAND_NAMES['arriba']: BAND_T}
vis_objs.update({k: v for k, v in refs.items() if not k.startswith(('usb:', 'microsd:'))})
vis_clip, vis_near = box(-30, 32, -30, 30, 0, 62), box(5, 30, 5, 23, 12, 50)
scene0 = tri_scene(vis_objs, vis_clip, vis_near)
vis_objs['microsd: tarjeta puesta'] = groups['microsd']['tarjeta puesta']
scene1 = tri_scene(vis_objs, vis_clip, vis_near)
ux0_v, uyc_v, uzc_v, uh_v, uw_v, ur_v = G.usb_tunnel()
sx0_v, sy0_v, sy1_v, szc_v, sw_v = G.sd_slot()
mu_v = P['costado']['microsd']['muesca']
usb_rect = [(uyc_v - uh_v / 2, uyc_v + uh_v / 2, uzc_v - uw_v / 2, uzc_v + uw_v / 2,
             lambda y, z: G.rounded_rect_inside(y, z, uyc_v, uzc_v, uh_v - 0.01, uw_v - 0.01, ur_v))]
sd_rects = [(sy0_v, sy1_v, szc_v - sw_v / 2, szc_v + sw_v / 2, lambda y, z: True),
            (sy1_v, mu_v['y_sup'], szc_v - mu_v['ancho'] / 2, szc_v + mu_v['ancho'] / 2, lambda y, z: True)]
report['visibilidad'] = {
    'usb_c': visibility(scene0, usb_rect, 'tunel del USB-C (12.95 x 7.1)'),
    'microsd_sin_tarjeta': visibility(scene0, sd_rects, 'ranura de la microSD (11.6 x 1.6) y muesca'),
    'microsd_con_la_tarjeta_trabada': visibility(scene1, sd_rects, 'ranura de la microSD (11.6 x 1.6) y muesca'),
    'permitido': list(VIS_OK),
    '_nota': ('Origenes en la piel exterior del tubo (r 28) dentro de cada abertura, en rejilla de 0.2 mm con desplazamiento '
              'aleatorio (semilla fija) para cada una de las 49 direcciones (-X inclinado de -30 a 30 grados en y y en z); '
              'de_frente: rejilla fija de 0.05 mm, rayos paralelos a -X. Tapa de puertos abierta 150 grados. "otro" es todo lo '
              'que no es J101, J401, la tarjeta, el tubo, el marco, la tapa de puertos o el canto de la PCB bajo J101 '
              '(x 14.9, y 13.8-15.4, z 18.5-31.5). Teselacion de 0.04 mm cerca de las aberturas.')}
log('visibilidad (%.0f s):' % (time.time() - T3d), {k: (v['otro_pct'], v['de_frente']['otro_pct']) for k, v in report['visibilidad'].items() if isinstance(v, dict) and 'otro_pct' in v})


# --- 3e. Bandas de TPU: apriete, aberturas, anillo completo, distintivo y rayas entre las bandas ----------------
def tess_box(shape, tol=0.01):
    """Caja de la teselacion fina: la de OCC sobre los redondeos (B-spline) sale algo mas grande."""
    pts = shape.tessellate(tol)[0]
    return App.BoundBox(min(p.x for p in pts), min(p.y for p in pts), min(p.z for p in pts),
                        max(p.x for p in pts), max(p.y for p in pts), max(p.z for p in pts))


_bd = G.band_dims()
_bz_b, _bz_t = G.band_z('abajo'), G.band_z('arriba')
_lgz = [z_ for o_, hs_ in G.logo_polygons()[0] for x_, z_ in o_]
_wo = P['frente']['ventana_oled']
_pk_m = _wo['bolsillo']['margen']
_pocket = box(-_wo['x'] - _pk_m, _wo['x'] + _pk_m, G.Y_FLAT_O - _wo['bolsillo']['hondo'], G.Y_FLAT_O, _wo['z'][0] - _pk_m, _wo['z'][1] + _pk_m)
_lvz = P['tubo']['lineas_verticales']['z']
_kk, _vt = P['frente']['tecla'], G.BD['abajo']['ventana_tecla']
_ring_top = min(_bd['tapa_puertos']['z_fondo'], _kk['z'] - _vt['diametro_tecla'] / 2.0)
_dr = P['base']['desague']
_drain = G.cyl_z(_dr['diametro'] / 2.0, _dr['x'], _dr['y'], -1.0, P['base']['espesor'] + 0.5)
# Que la banda de arriba no tape la cara de arriba de la tapa: nada por encima de z 116 ni por dentro de su contorno de
# apriete (cuerpo - apriete - 0.02) en el ultimo mm.
_inside_grip = G.body_prism(G.H_TOTAL - 1.0, G.H_TOTAL + 5.0, -G.BD['apriete'] - 0.02)
_tpp = P['costado']['tapa_puertos']
_tab = COVER.common(box(_tpp['lengueta']['x0'] - 0.01, _tpp['x_frente_plano'] + 0.01, G.Y_FLAT_O - 0.01, 40,
                        _tpp['lengueta']['z'][0] - 0.01, _tpp['lengueta']['z'][1] + 0.01))
_bt_ok = {
    'tapa de puertos >= 0.5': (pairs['banda de abajo-tapa de puertos (pedido >= 0.5)'] or 0) >= G.BD['abajo']['muesca_tapa_puertos']['holgura'] - 1e-3,
    'tecla >= 1.0': (pairs['banda de abajo-tecla (pedido >= 1.0)'] or 0) >= 1.0 - 1e-3,
    'anillo completo >= 12': _ring_top >= 12.0,
    'tapa de puertos abre >= 135': cover_band['cumple'],
    'distintivo >= 2 a la banda y al bolsillo': min(_lgz) - _bz_b[1] >= 2.0 and _pocket.BoundBox.ZMin - max(_lgz) >= 2.0,
    'rayas >= 1.5 a las bandas': _lvz[0] - _bz_b[1] >= 1.5 - 1e-6 and _bz_t[0] - _lvz[1] >= 1.5 - 1e-6,
    'nada sobre la cara de arriba de la tapa': (common_vol(BAND_T, box(-60, 60, -60, 60, G.H_TOTAL, G.H_TOTAL + 50)) <= 1e-3
                                                and common_vol(BAND_T, _inside_grip) <= 1e-3),
    'barridos de las bandas limpios': (not sweeps['banda_de_abajo_por_abajo'] and not sweeps['banda_de_arriba_por_arriba']
                                       and not sweeps['tornillos_radiales_por_las_bandas']),
}
report['bandas'] = {
    'piezas': {G.BAND_NAMES[w_]: {'z': list(G.band_z(w_)), 'volumen_cm3': round(sh_.Volume / 1000.0, 2), 'solidos': len(sh_.Solids),
                                  'valida': sh_.isValid(), 'caja': [round(v_, 2) for v_ in (bb_.XMin, bb_.XMax, bb_.YMin, bb_.YMax,
                                                                                            bb_.ZMin, bb_.ZMax)]}
               for w_, sh_, bb_ in (('abajo', BAND_B, tess_box(BAND_B)), ('arriba', BAND_T, tess_box(BAND_T)))},
    'espesor_mm': G.BD['espesor'], 'apriete_por_lado_mm': G.BD['apriete'],
    'por_fuera_del_cuerpo_mm': round(G.BD['espesor'] - G.BD['apriete'], 3),
    'apriete_mm3': band_grip,
    'aberturas': {
        'agujeros de los tornillos de la base': {'diametro': G.BD['abajo']['tornillos_diametro'], 'z': P['base']['tornillos']['z'],
                                                 'angulos': P['base']['lenguetas']['angulos'],
                                                 'holgura_a_la_cabeza_mm': pairs['banda de abajo-tornillos de la base']},
        'ventana de la tecla y el LED': {'diametro_tecla': _vt['diametro_tecla'], 'diametro_led': _vt['diametro_led'],
                                         'holgura_a_la_tecla_mm': pairs['banda de abajo-tecla (pedido >= 1.0)'],
                                         'holgura_a_la_guia_de_luz_mm': pairs['banda de abajo-guia de luz del LED']},
        'muesca de la tapa de puertos': dict({k_: round(v_, 3) for k_, v_ in _bd['tapa_puertos'].items()},
                                             holgura_a_la_tapa_cerrada_mm=pairs['banda de abajo-tapa de puertos (pedido >= 0.5)'],
                                             sitio_para_la_una_delante_de_la_lengueta_mm=gap(BAND_B, _tab)),
        'desague (holgura al agujero)': gap(BAND_B, _drain),
        'agujeros de los tornillos de la tapa': {'diametro': G.BD['arriba']['tornillos_diametro'], 'z': P['tapa']['tornillos_z'],
                                                 'angulos': P['tapa']['lenguetas']['angulos'],
                                                 'holgura_a_la_cabeza_mm': pairs['banda de arriba-tornillos de la tapa']},
        'muesca de la OLED': dict({k_: round(v_, 3) for k_, v_ in _bd['oled'].items()},
                                  holgura_al_bolsillo_mm=gap(BAND_T, _pocket),
                                  holgura_a_la_lamina_mm=pairs['banda de arriba-lamina de la ventana'])},
    'anillo_completo_banda_de_abajo': {'z': [_bz_b[0], round(_ring_top, 3)], 'alto_mm': round(_ring_top - _bz_b[0], 3),
                                       'objetivo_mm': 12.0, '_nota': 'Sin muesca ni ventana; solo los tres agujeros de los tornillos de la base.'},
    'cara_de_arriba_de_la_tapa': {'banda_por_encima_de_z_%g_mm3' % G.H_TOTAL: round(common_vol(BAND_T, box(-60, 60, -60, 60, G.H_TOTAL, G.H_TOTAL + 50)), 4),
                                  'banda_por_dentro_de_su_contorno_de_apriete_mm3': round(common_vol(BAND_T, _inside_grip), 4),
                                  'holgura_a_la_antena_mm': pairs['banda de arriba-antena'],
                                  'holgura_a_los_tornillos_de_la_antena_mm': gap(BAND_T, groups['antena']['tornillos M2.5 de la antena'])},
    'tapa_de_puertos_abierta': cover_band,
    'al_ponerlas': band_sweep,
    'distintivo_entre_las_bandas': {'z': [round(min(_lgz), 2), round(max(_lgz), 2)], 'a_la_banda_de_abajo_mm': round(min(_lgz) - _bz_b[1], 2),
                                    'al_bolsillo_de_la_lamina_mm': round(_pocket.BoundBox.ZMin - max(_lgz), 2), 'objetivo_mm': 2.0},
    'rayas_entre_las_bandas': {'z': _lvz, 'a_la_banda_de_abajo_mm': round(_lvz[0] - _bz_b[1], 2),
                               'a_la_banda_de_arriba_mm': round(_bz_t[0] - _lvz[1], 2), 'objetivo_mm': 1.5},
    'cumple': _bt_ok, 'todo_cumple': all(_bt_ok.values()),
    '_nota': ('Bandas con su medida de impresion (como en el documento): el solape con el tubo, la base y la tapa es el apriete '
              '(no cuenta como choque). Barridos y tapa de puertos abierta, con la banda estirada (ver al_ponerlas.metodo).')}
log('bandas:', {k: v for k, v in report['bandas'].items() if k not in ('al_ponerlas', 'tapa_de_puertos_abierta')})

# --- 4. Objetivos de la revision: minimo conseguido por categoria ------------------------------
# B1 ajustes entre impresas >= 0.4; B2 rieles de la placa >= 0.25 por cara; B3 aire a compradas
# >= 0.5; B4 carrier en sus ranuras (juego y suplementos); B5 paredes >= 1.2 (local >= 1.0);
# B6 radio de curva del coaxial >= 12 en todas las curvas; B7 mazos entre si >= 0.3. Posicion final
# y barridos. La funda del USB-C y la tarjeta van guiadas a 0.3 por lado (pedido del propietario).
def _summary(items, target):
    vals = [(k, v) for k, v in items if v is not None]
    if not vals:
        return None
    k, v = min(vals, key=lambda kv: kv[1])
    return {'objetivo_mm': target, 'minimo_mm': v, 'donde': k, 'cumple': v >= target - 1e-3,
            'por_debajo': {k_: v_ for k_, v_ in vals if v_ < target - 1e-3}}


def _lat(cat):
    d = lat_min.get(cat)
    return [] if d is None else [(f"barrido {d['barrido']}: {d['movil']} / {d['obstaculo']}", d['mm'])]


B1_KEYS = ('chasis-tubo por encima de las repisas (z > 9.6)', 'chasis-base', 'chasis-tapa',
           'tapa bajo el canto del tubo (labio y lenguetas)-tubo', 'base sobre el canto del tubo (labio, lenguetas, saliente)-tubo',
           'tecla-tubo (sin la pestana pegada)', 'tapa de puertos-chasis', 'marco-tubo', 'marco-chasis',
           'marco-tapa de puertos', 'banda de abajo-tapa de puertos (pedido >= 0.5)', 'banda de abajo-tecla (pedido >= 1.0)',
           'banda de abajo-distintivo de TPU', 'banda de arriba-distintivo de TPU')
B3_KEYS = ('chasis-celdas', 'chasis-componentes de la placa y OLED', 'chasis-componentes de la carrier (sin su PCB)',
           'tubo-celdas por encima de las repisas (nervios)', 'tubo-PCB de la placa', 'tubo-componentes de la placa y OLED',
           'tapa-OLED', 'tapa-coaxial (recorrido)', 'tapa-celdas',
           'base-clavijas', 'base-PCB de la placa', 'base-celdas', 'base-carrier', 'reten-celdas',
           'tecla-SW401 (juego del embolo)', 'tecla-componentes de la placa', 'carrier (patas del SMA)-celdas',
           'cables (reservas)-piezas', 'cables (reservas)-celdas', 'cables (reservas)-placa y carrier',
           'tuerca SMA-PCB con la muesca', 'coaxial (recorrido)-piezas', 'coaxial (recorrido)-celdas',
           'coaxial (recorrido)-placa y OLED', 'coaxial (recorrido)-cables', 'clavija SMA acodada-chasis (pedido >= 0.5)',
           'clavija SMA acodada-celdas', 'clavija SMA acodada-placa y OLED (sin la muesca)',
           'perno del baston (15.5)-soldaduras de la carrier', 'perno del baston (15.5)-celdas',
           'guia de luz-componentes de la placa', 'tapa de puertos-tarjeta', 'tapa-tornillos de la antena (radial, en su rebaje)',
           'tapa-tuerca del pasamuros (radial, en su bolsillo)', 'conector de la tapa (dentro)-placa, OLED y celdas',
           'tuerca del baston-placa y carrier', 'carrier-PCB de la placa', 'marco-componentes de la placa (sin J101)',
           'marco-carrier', 'marco-celdas y cables', 'banda de abajo-guia de luz del LED', 'banda de abajo-tornillos de la base',
           'banda de arriba-tornillos de la tapa', 'banda de arriba-lamina de la ventana', 'banda de arriba-antena')
tp_rep = report['tapa_de_puertos']
_head = []
for an_k, an_v in tp_rep['anclas'].items():
    _head += [(f'cabeza de la seta ({an_k}) en su sitio-{k}', v) for k, v in an_v['cabeza_en_su_sitio_mm'].items()]
    _head.append((f'cabeza de la seta ({an_k}) al barrer el chasis armado', an_v['cabeza_al_barrer_el_chasis_mm']))
# Mazos entre si (cables y coaxial): mismo grupo, que la seccion de choques no compara.
BUNDLES = {'mazo del pack (rojo, negro y NTC)': groups['cables']['cable mazo_pack'],
           'hilos de la NTC': groups['cables']['cable hilos_ntc'],
           'arnes de J301': groups['cables']['cable arnes_j301'], 'coaxial': coax_refs['coaxial (recorrido)']}
_bk = list(BUNDLES)
# Los hilos de la NTC se juntan con el mazo del pack abajo: esa pareja no cuenta.
mazos = {f'{a} / {b}': gap(BUNDLES[a], BUNDLES[b]) for i, a in enumerate(_bk) for b in _bk[i + 1:]
         if {a, b} != {'mazo del pack (rojo, negro y NTC)', 'hilos de la NTC'}}
mazos['cuerpo de la NTC / coaxial'] = gap(groups['cables']['cable NTC (cuerpo)'], BUNDLES['coaxial'])
report['distancias_entre_mazos'] = mazos
for ang, d in tp_rep['abierta_girada_en_la_bisagra'].items():
    _head += [(f'tapa abierta {ang} grados-funda USB-C', d['funda_holgura']), (f'tapa abierta {ang} grados-tarjeta', d['tarjeta_holgura'])]
_cb = tp_rep['abierta_con_la_banda_puesta']
_head += [(f"tapa abierta al maximo con la banda ({_cb['angulo_maximo_grados']:g} grados)-funda USB-C", _cb['funda_holgura']),
          (f"tapa abierta al maximo con la banda ({_cb['angulo_maximo_grados']:g} grados)-tarjeta", _cb['tarjeta_holgura'])]
HOL = P['holguras']
objetivos = {
    'B1_ajustes_entre_impresas': _summary([(k, pairs.get(k)) for k in B1_KEYS] + _lat('impresas'), HOL['ajuste_impresas']),
    'B2_rieles_de_la_placa': _summary([('rieles-PCB de la placa (sin el tope de z 80 ni los salientes)',
                                        pairs['rieles-PCB de la placa (sin el tope de z 80 ni los salientes)'])] + _lat('rieles'),
                                      HOL['riel_placa']),
    'B3_aire_a_compradas': _summary([(k, pairs.get(k)) for k in B3_KEYS] + _lat('compradas') + _head, HOL['compradas']),
    'B4_carrier': {'juego_por_cara_mm': P['chasis']['ranura_carrier']['holgura'],
                   'medido_en_su_sitio_mm': gap(chs_no_hooks, carrier_refs['carrier: PCB']),
                   'medido_al_subirla_mm': lat_min.get('carrier-ranuras', {}).get('mm'),
                   '_nota': 'Ajuste de posicion, no aire: la carrier va guiada. Medidas de la foto (+-1 mm): medir y '
                            'ajustar chasis.ranura_carrier y carrier.x/z antes de imprimir; suplementos en README.'},
    'B5_paredes_del_tubo': {'objetivo_mm': HOL['pared_minima'], 'local_minimo_mm': HOL['pared_local_minima'],
                            'espesores_mm': {k: v['mm'] for k, v in guard['espesor_minimo'].items()},
                            'por_debajo_de_1.2': guard['espesor_por_debajo_de_1.2'],
                            'por_debajo_de_1.0': guard['espesor_por_debajo_de_1.0']},
    'B6_coaxial': {k: report['coaxial'][k] for k in ('radio_curva_disponible', 'radio_curva_objetivo', 'radio_curva_preferido',
                                                     'cumple_objetivo', 'cumple_preferido')},
    'B7_mazos_entre_si': _summary(list(mazos.items()), 0.3),
    'bandas_de_tpu': {'cumple': report['bandas']['cumple'], 'todo_cumple': report['bandas']['todo_cumple'],
                      'apriete_mm3': report['bandas']['apriete_mm3'],
                      'angulo_maximo_de_la_tapa_de_puertos_grados': _cb['angulo_maximo_grados'],
                      'anillo_completo_mm': report['bandas']['anillo_completo_banda_de_abajo']['alto_mm']},
    # La tarjeta trabada asoma 2.5 de la boca de J401 (hoja del TF-015): queda dentro de su ranura, guiada.
    'ajustes_guiados': {'funda USB-C en el tunel (por lado)': pairs.get('tubo-funda USB-C'),
                        'tarjeta trabada en la ranura (por lado)': pairs.get('tubo-tarjeta microSD'),
                        'funda USB-C en el tunel del marco (por lado)': pairs.get('marco-funda USB-C (tunel del marco, por lado)'),
                        'objetivo_mm': P['costado']['usb_c']['holgura'],
                        'cumple': all(v_ is not None and v_ >= P['costado']['usb_c']['holgura'] - 1e-3 for v_ in (
                            pairs.get('tubo-funda USB-C'), pairs.get('tubo-tarjeta microSD'),
                            pairs.get('marco-funda USB-C (tunel del marco, por lado)'))),
                        '_nota': 'Pedido del propietario: aberturas justas, funda y tarjeta a 0.3 por lado; no es aire de 0.5.'},
    '_nota': ('Contactos a proposito (no cuentan): pie de los rieles en sus apoyos (z 9.5), placa contra los salientes '
              '(y 13.8) y el tope (z 80), celdas en sus repisas, base y tapa contra los cantos del tubo, tornillos en sus '
              'avellanados y arandelas en sus asientos, tecla pegada en su rebaje, tapa de puertos sobre el tubo, seta en su '
              'agujero, cuerpos de TPU en las aberturas, tuerca del baston en su hexagono (0.3 por cara), pasamuros en su '
              'agujero en D, marco del USB-C con el labio bajo el dorso de la placa y el fondo de sus ranuras en el canto, '
              'resorte del marco sobre el blindaje de J101 (apriete a proposito), bandas de TPU sobre el tubo, la base y la tapa '
              '(apriete de 0.3 por lado, ver bandas). Ajustes de posicion aparte: rieles (B2) y carrier (B4).')}
report['objetivos'] = objetivos
log('objetivos:', {k: (v.get('minimo_mm'), v.get('cumple')) if isinstance(v, dict) and 'minimo_mm' in v else None
                   for k, v in objetivos.items() if k.startswith('B')})

# El barrido con la tecla puesta es un diagnostico: dice que bloquea si no se quita la tecla.
report['bloqueos_al_sacar_el_chasis_con_la_tecla_puesta'] = sweeps.pop('chasis_armado_con_tecla_puesta')
report['barridos'] = sweeps
report['total_choques'] = (len(report['choques_entre_piezas']) + len(report['choques_piezas_referencias'])
                           + sum(len(v) for v in sweeps.values()))
report['guarda_pared_ok'] = guard['ok']
report['numero_de_barridos'] = len(sweeps)
(OUT / 'check.json').write_text(json.dumps(report, indent=1, ensure_ascii=False, default=lambda o: o.item() if hasattr(o, 'item') else str(o)),
                               encoding='utf-8')
log('escrito', OUT / 'check.json')
print(json.dumps({k: report.get(k) for k in ('guarda_pared_tubo', 'objetivos', 'bandas', 'holguras_cara_plana', 'chasis_armado', 'coaxial', 'antena_wroom',
                                             'placa_detras_del_dorso_frente_al_SMA', 'marco_usb_c', 'marco_al_montarlo',
                                             'bloqueos_al_sacar_el_chasis_con_la_tecla_puesta', 'numero_de_barridos', 'total_choques')},
                 indent=1, ensure_ascii=False, default=lambda o: o.item() if hasattr(o, 'item') else str(o)))
print(json.dumps({k: {kk: v.get(kk) for kk in ('otro_pct', 'de_frente', 'lo_que_se_ve_ademas')} for k, v in report['visibilidad'].items()
                  if isinstance(v, dict) and 'otro_pct' in v}, indent=1, ensure_ascii=False, default=lambda o: o.item() if hasattr(o, 'item') else str(o)))
