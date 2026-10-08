"""Comprueba la carcasa V3.0 contra la placa v0.3 y el resto de piezas compradas.

Mide, con las piezas de generated/TresVizo-V3.0.FCStd:
  - guardas de la pared del tubo (el material que falta no sale como choque): sondas en la mitad
    de la pared, en la cara plana y en un anillo, y volumen contra el de la pared intencionada;
  - choques entre piezas impresas y contra cada referencia en la posicion final: placa (envolvente
    de la especificacion o STEP real con --board), carrier con sus componentes, celdas, tuerca y
    reten, antena y sus tornillos, coaxial, clavijas y cables, OLED, funda del USB-C, tarjeta;
  - barridos del montaje: celdas por arriba, carrier y placa al chasis por abajo, chasis armado
    por arriba con las celdas puestas, base por abajo, tapa por arriba, tecla y tarjeta por fuera;
  - holguras minimas y radio maximo del chasis armado.

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
PLUG_USB, PLUG_SD = parts['06-usb-plug-tpu'], parts['07-sd-plug-tpu']

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
         ('antena: antena HA-901A', 'coaxial: coaxial (curva en S)'),
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

# --- 0. Guardas de la pared del tubo ----------------------------------------------------
# El material que falta no aparece como choque: se comprueba aparte. (1) sondas en la mitad de la
# pared, cara plana y anillo; (2) volumen del tubo contra el de la pared intencionada (hecha con
# poligonos, sin interior()) menos las aberturas a proposito mas nervios, repisas y cuna.
import build_v3_0 as B
guard = {'sondas': G.wall_probes(TUBE, step=0.5)}
wall_ref = G.wall_reference()
rr_ = P['tubo']['ranuras_rieles']
grooves = G.fuse_all([G.sector(rr_['radio'], G.RI - 0.5, rr_['z'][0], G.Z_TUBE1 + 1, a0, a1) for a0, a1 in rr_['angulos']])
openings = G.fuse_all([B.front_openings(), B.side_openings(), B.screw_holes(), B.rebates()])
expected = wall_ref.cut(grooves).fuse(B.rail_ledges()).fuse(B.cell_cradle()).cut(openings)
v_tube, v_exp = TUBE.Volume, expected.Volume
guard['volumen'] = {
    'tubo_mm3': round(v_tube, 1), 'esperado_mm3': round(v_exp, 1),
    'anillo_solido_mm3': round(wall_ref.Volume, 1),
    'diferencia_mm3': round(v_tube - v_exp, 1), 'diferencia_pct': round(100 * (v_tube - v_exp) / v_exp, 3),
    'tolerancia_pct': 0.5, 'ok': abs(v_tube - v_exp) <= 0.005 * v_exp,
    '_nota': 'esperado = anillo solido (circulo R26 con la cara plana en y 22.13, hueco R24.2 con la cara plana interior en y 20.33 para |x| <= 13.65, z 4-96) - ranuras de los rieles - rebajes de las uniones + repisas + cuna - ventana con su bolsillo, tecla con su rebaje, LED, tunel USB-C, ranura microSD, rebaje de la una y tornillos.'}
# Espesor minimo de pared alrededor de las aberturas (rayos desde el contorno de secciones
# horizontales; se ignoran 0.6 mm alrededor de las esquinas vivas). Minimo pedido: 0.6.
side = (12.0, 27.0, 9.0, 23.0)
front = (-14.5, 14.5, 19.0, 23.0)
th = {'tunel USB-C': G.min_wall_thickness(TUBE, [19.0, 22.0, 25.0, 28.0, 31.0], side),
      'ranura microSD y rebaje': G.min_wall_thickness(TUBE, [39.5, 41.0, 42.0, 45.0, 48.0, 49.0, 50.5], side),
      'ventana OLED (bolsillo y chaflan)': G.min_wall_thickness(TUBE, [73.0, 75.0, 80.0, 86.0, 87.3], front),
      'tecla y LED': G.min_wall_thickness(TUBE, [18.0, 20.0, 22.0, 24.0, 26.0], (-10.0, 10.0, 19.0, 23.0)),
      'uniones (rebajes)': G.min_wall_thickness(TUBE, [4.5, 5.2, 94.8, 95.5], (-27, 27, -27, 23)),
      'pared normal (z 60)': G.min_wall_thickness(TUBE, [60.0], (-27, 27, -27, 23))}
guard['espesor_minimo'] = {k: {'mm': v[0], 'donde': v[1]} for k, v in th.items()}
guard['espesor_minimo_ok'] = all(v[0] >= 0.6 for v in th.values())
guard['ok'] = (guard['sondas']['cara_plana']['ok'] and guard['sondas']['anillo']['ok'] and guard['volumen']['ok']
               and guard['espesor_minimo_ok'])
report['guarda_pared_tubo'] = guard
log('guarda de la pared:', {k: guard['sondas'][k]['sin_material'] for k in ('cara_plana', 'anillo')},
    guard['volumen']['tubo_mm3'], 'vs', guard['volumen']['esperado_mm3'], 'ok' if guard['ok'] else 'FALLA')

# --- 1. Posicion final ------------------------------------------------------------------
names = sorted(parts)
pp = []
for i, a in enumerate(names):
    for b in names[i + 1:]:
        v = common_vol(parts[a], parts[b])
        if v > LIM or v < 0:
            pp.append({'a': a, 'b': b, 'mm3': round(v, 3)})
report['choques_entre_piezas'] = pp
pr = []
# Piezas que ocupan el sitio de una referencia a proposito y nunca a la vez: el tapon del USB-C
# va donde la funda de la clavija cuando no hay cable.
ALTERNATIVES = [('06-usb-plug-tpu', 'usb: funda de la clavija')]
for pn in names:
    for rn, rs in refs.items():
        if (pn, rn) in ALTERNATIVES:
            continue
        v = common_vol(parts[pn], rs)
        if v > LIM or v < 0:
            pr.append({'pieza': pn, 'ref': rn, 'mm3': round(v, 3)})
report['choques_piezas_referencias'] = pr
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


OBST_SLABS = {'02-tube': slabs(TUBE), '04-chassis': slabs(CHS)}
board_refs = {f'placa: {k}': v for k, v in board.items()}
carrier_refs = {f'carrier: {k}': v for k, v in groups['carrier'].items()}
cell_refs = {f'celdas: {k}': v for k, v in groups['celdas'].items()}
sweeps = {}

# a. Celdas por arriba (tapa quitada, chasis fuera, base puesta).
sweeps['celdas_por_arriba'] = sweep(cell_refs, {'02-tube': TUBE, '01-base': BASE}, V(0, 0, 85))
log('celdas:', sweeps['celdas_por_arriba'])
# b. Carrier al chasis por abajo (los labios de los ganchos se apartan: no cuentan).
gk = P['chasis']['ganchos']
hook_zone = box(-17.5, -15.0, gk['y'][0] - 0.5, gk['y'][1] + 0.5, gk['labio_z'][0] - 0.5, gk['labio_z'][1] + 0.01)
hook_zone = hook_zone.fuse(box(15.0, 17.5, gk['y'][0] - 0.5, gk['y'][1] + 0.5, gk['labio_z'][0] - 0.5, gk['labio_z'][1] + 0.01))
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


obst = {'04-chassis': CHS, 'coaxial: cuerpo de la clavija': G.cyl_z(cxp['cuerpo']['diametro'] / 2.0, nx, ny,
        cxp['tuerca']['z0'] + cxp['tuerca']['largo'], cxp['tuerca']['z0'] + cxp['tuerca']['largo'] + cxp['cuerpo']['largo'])}
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
assembly = {'04-chassis': CHS, 'coaxial: clavija SMA (tuerca Ø9.2 y cuerpo)': plug_sh}
assembly.update(board_refs)
assembly.update(carrier_refs)
batt = {f'cables: {k}': v for k, v in groups['cables'].items() if 'bateria' in k}
obst = {'02-tube': TUBE, '01-base': BASE}
obst.update(cell_refs)
obst.update(batt)
sweeps['chasis_armado_por_arriba_sin_tecla'] = sweep(assembly, obst, V(0, 0, 92))
log('chasis armado sin tecla:', sweeps['chasis_armado_por_arriba_sin_tecla'])
obst_k = {'05-key-tpu': KEY}
sweeps['chasis_armado_con_tecla_puesta'] = sweep(assembly, obst_k, V(0, 0, 92))
log('chasis armado con tecla:', sweeps['chasis_armado_con_tecla_puesta'])
# f. Base por abajo (con la tuerca y el reten), con todo lo de dentro puesto.
base_mov = {'01-base': BASE}
base_mov.update({f'tuerca: {k}': v for k, v in groups['tuerca'].items() if 'perno' not in k})
obst = {'02-tube': TUBE, '04-chassis': CHS}
obst.update(board_refs)
obst.update(carrier_refs)
obst.update(cell_refs)
obst.update({f'clavijas: {k}': v for k, v in plug_refs.items()})
obst.update({f'cables: {k}': v for k, v in groups['cables'].items()})
sweeps['base_por_abajo'] = sweep(base_mov, obst, V(0, 0, -20))
log('base:', sweeps['base_por_abajo'])
# g. Tapa con la antena atornillada, por arriba (con sus topes de las celdas y su labio).
cap_mov = {'03-antenna-cap': CAP}
cap_mov.update({f'antena: {k}': v for k, v in groups['antena'].items()})
obst = {'02-tube': TUBE, '04-chassis': CHS, 'coaxial: clavija SMA (tuerca Ø9.2 y cuerpo)': plug_sh}
obst.update(board_refs)
obst.update(cell_refs)
obst.update(batt)
sweeps['tapa_por_arriba'] = sweep(cap_mov, obst, V(0, 0, 20))
log('tapa:', sweeps['tapa_por_arriba'])
# h. Tecla entera por fuera (la pestana va en el rebaje exterior: entra y sale por fuera).
obst = {'02-tube': TUBE}
obst.update(board_refs)
sweeps['tecla_por_fuera'] = sweep({'05-key-tpu': KEY}, obst, V(0, 12, 0))
# i. Tarjeta microSD por el costado +X.
sweeps['tarjeta_por_el_costado'] = sweep({'microsd: tarjeta': G.microsd_card()},
                                         {'02-tube': TUBE, '04-chassis': CHS, 'placa: PCB': board['PCB']}, V(15, 0, 0))
# j. Tapones de TPU por fuera (hacia +X).
obst = {'02-tube': TUBE, '04-chassis': CHS, 'microsd: tarjeta puesta': G.microsd_card()}
obst.update(board_refs)
sweeps['tapones_por_fuera'] = sweep({'06-usb-plug-tpu': PLUG_USB, '07-sd-plug-tpu': PLUG_SD}, obst, V(12, 0, 0))
report['barridos'] = sweeps
log('barridos:', {k: len(v) for k, v in sweeps.items()})


# --- 3. Holguras y radio del chasis armado -------------------------------------------------
comp_shapes = [v for k, v in board.items() if k != 'PCB' and 'tornillos' not in k]
pairs = {
    'chasis-tubo (contacto: pie de los rieles en sus repisas, z 9.5)': gap(CHS, TUBE),
    'chasis-tubo por encima de las repisas (z > 9.6)': gap(CHS, TUBE.common(box(-60, 60, -60, 60, 9.6, 200))),
    'chasis-celdas': min_gap(CHS, cell_refs.values()),
    'chasis-PCB de la placa': gap(CHS, board['PCB']),
    'chasis-componentes de la placa y OLED': min_gap(CHS, comp_shapes),
    'chasis-carrier (contactos: topes z 69 y ganchos z 17)': min_gap(CHS, carrier_refs.values()),
    'chasis-base': gap(CHS, BASE),
    'chasis-tapa': gap(CHS, CAP),
    'tubo-celdas (contacto: repisas, z 17.5)': min_gap(TUBE, cell_refs.values()),
    'tubo-celdas por encima de las repisas (nervios)': min_gap(TUBE.common(box(-60, 60, -60, 60, 17.6, 200)), cell_refs.values()),
    'tubo-PCB de la placa': gap(TUBE, board['PCB']),
    'tubo-componentes de la placa y OLED': min_gap(TUBE, comp_shapes),
    'tubo-funda USB-C': gap(TUBE, groups['usb']['funda de la clavija']),
    'tubo-tarjeta microSD': gap(TUBE, groups['microsd']['tarjeta puesta']),
    'tapa-OLED': min_gap(CAP, [v for k, v in board.items() if 'OLED' in k]),
    'tapa-coaxial': gap(CAP, coax_refs['coaxial (curva en S)']),
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
    'cables (reservas)-piezas': min([gap(c, p) for c in groups['cables'].values() for p in (TUBE, CHS, BASE, CAP)]),
    'tuerca SMA (barrido Ø9.2)-chasis (pedido >= 0.5)': gap(CHS, coax_refs['clavija SMA de la carrier']),
    'tuerca SMA-PCB con la muesca': gap(coax_refs['clavija SMA de la carrier'], board['PCB']),
    'coaxial (bucle de servicio)-piezas': min(gap(coax_refs['coaxial: bucle de servicio'], p) for p in (TUBE, CHS, CAP)),
    'perno del baston (15.5)-soldaduras de la carrier': min_gap(groups['tuerca']['perno del baston (rosca maxima)'],
                                                              [v for k, v in groups['carrier'].items() if 'soldaduras' in k]),
    'perno del baston (15.5)-celdas': min_gap(groups['tuerca']['perno del baston (rosca maxima)'], cell_refs.values()),
    'guia de luz-componentes de la placa': min_gap(groups['frente']['guia de luz del LED'],
                                                   [v for k, v in board.items() if k != 'PCB' and 'OLED' not in k]),
    'tapones TPU-chasis': min(gap(PLUG_USB, CHS), gap(PLUG_SD, CHS)),
    'tapon microSD-tarjeta': gap(PLUG_SD, groups['microsd']['tarjeta puesta']),
}
report['holguras'] = pairs

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
    'tubo_a_la_antena_mm': gap(TUBE, ant),
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

# Holguras a la cara plana del tubo (pared de y 20.33 a 22.13 en |x| <= 13.65), pieza a pieza.
front_wall = TUBE.common(box(-G.X_FLAT, G.X_FLAT, G.Y_FLAT_I - 0.5, G.Y_FLAT_O + 1, 0, 100))
fw = {
    'vidrio OLED (y 20.0)': gap(front_wall, board['OLED vidrio']) if 'OLED vidrio' in board else None,
    'OLED: PCB, cinta y tornillos': min_gap(front_wall, [v for k, v in board.items() if 'OLED' in k and 'vidrio' not in k]),
    'componentes de la placa (envolvente o STEP)': min_gap(front_wall, [v for k, v in board.items() if 'OLED' not in k and k != 'PCB']),
    'clavijas (y 19.8)': min_gap(front_wall, plug_refs.values()),
    'tecla: pestana contra la cara interior (contacto)': gap(front_wall, KEY),
    'tecla: volumen dentro de la pared (mm3)': round(common_vol(front_wall, KEY), 3),
    'chasis (lo mas cercano: labio de un riel, |x| 17.1)': gap(front_wall, CHS),
}
report['holguras_cara_plana'] = fw
log('cara plana:', fw)

ring_angles = P['tubo']['ranuras_rieles']['angulos']


def in_groove(x, y):
    a = math.degrees(math.atan2(y, x)) % 360
    return any(a0 <= a <= a1 for a0, a1 in ring_angles)


r_all, r_out = 0.0, 0.0
for s in [CHS] + list(board.values()) + list(carrier_refs.values()):
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
    'holgura_minima_al_tubo_por_encima_de_las_repisas': min_gap(TUBE.common(box(-60, 60, -60, 60, 9.6, 200)),
                                                                [CHS] + list(board.values()) + list(carrier_refs.values())),
    '_nota': 'Radio sobre vertices y aristas discretizadas cada 0.5 mm. Dentro de las ranuras (31-47 y 133-149 grados) el limite es 24.8; en |x| <= 13.65 el interior llega a la cara plana (y 20.33), por eso el vidrio de la OLED (r 24.05) cabe.'}
report['coaxial'] = {'radio_curva_disponible': round(coax_R, 2), 'radio_curva_pedido': P['coaxial']['radio_curva_minimo'],
                     'cumple': coax_R >= P['coaxial']['radio_curva_minimo']}
# El barrido con la tecla puesta es un diagnostico: dice que bloquea si no se quita la tecla.
report['bloqueos_al_sacar_el_chasis_con_la_tecla_puesta'] = sweeps.pop('chasis_armado_con_tecla_puesta')
report['barridos'] = sweeps
report['total_choques'] = (len(report['choques_entre_piezas']) + len(report['choques_piezas_referencias'])
                           + sum(len(v) for v in sweeps.values()))
report['guarda_pared_ok'] = guard['ok']
(OUT / 'check.json').write_text(json.dumps(report, indent=1, ensure_ascii=False), encoding='utf-8')
log('escrito', OUT / 'check.json')
print(json.dumps({k: report.get(k) for k in ('guarda_pared_tubo', 'holguras', 'holguras_cara_plana', 'chasis_armado', 'coaxial', 'antena_wroom',
                                             'placa_detras_del_dorso_frente_al_SMA',
                                             'bloqueos_al_sacar_el_chasis_con_la_tecla_puesta', 'total_choques')}, indent=1, ensure_ascii=False))
