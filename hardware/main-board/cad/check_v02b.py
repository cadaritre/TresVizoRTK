#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Comprobacion CAD v0.2b: placa principal TresVizo MeridianV v0.2 en la carcasa V2.2.

Placa principal en su posicion NUEVA (2.5 mm mas arriba que en el primer estudio):
canto inferior z = 23.5, canto superior z = 87.5; x = 23 - u, z = 87.5 - v; cara trasera
y = 1.5, cara de componentes y = 3.1. Con los modelos 3D reales de los componentes y todas
las clavijas puestas se comprueba:

  A. placa y componentes contra cada pieza de la carcasa (volumen de choque y distancia minima),
  B. clavijas (cuerpo y reserva de cables de plugs.json, mas la J502 de la panel-usb) contra la
     carcasa, los componentes y entre si; largo libre a lo largo del eje de las que salen por
     los cantos superior e inferior,
  C. paso por los collares de diametro 52 (radio maximo desde el eje del tubo),
  D. franjas de los rieles (2.5 mm desde x = +-23 para z >= 39, sin el tramo z 54-71 del lado +X)
     y los rieles propuestos como solidos,
  E. espacio detras de cada agujero M2.5 para los brazos nuevos,
  F. otras cosas (holgura delante de cada componente, datos de entrada, panel-usb real).

Entradas (solo lectura):
  main-placed.step, main-placed.kicad_pcb, plugs.json (esta carpeta),
  ../mech/cad_out/*.brep y ../mech/v22_copy + ../mech/v02_params.py (carcasa del primer estudio),
  ../kd/lib/lcsc.3dshapes (modelos .wrl/.step de LCSC de la placa principal),
  la placa panel-usb del repositorio: se COPIA a tmp/pusb_src y se exporta panel-usb.step aqui.

Correccion de modelos: kicad-cli con --subst-models sustituye cada .wrl de LCSC por el .step del
mismo nombre, pero los .step de LCSC/EasyEDA no tienen el mismo origen que los .wrl con los que
se diseno (y se comprobo) cada huella. Para cada modelo se mide el desplazamiento entre los dos
(centro de las cajas envolventes), se comprueba que una traslacion pura los hace coincidir
(distancia de puntos del .wrl a la superficie del .step) y se corrige cada instancia.

Salidas: results_v02b.json, v02b_check.FCStd, img/*.png.

Uso:
  PYTHONPATH=/Applications/FreeCAD.app/Contents/Resources/lib \\
  /Applications/FreeCAD.app/Contents/Resources/bin/python check_v02b.py
"""
import sys
sys.dont_write_bytecode = True
import json, math, re, shutil, subprocess, time, types
from pathlib import Path

T0 = time.time()
HERE = Path(__file__).resolve().parent
SCR = HERE.parent
MECH = SCR / 'mech'
CAD = MECH / 'cad_out'
COPY = MECH / 'v22_copy'
LIB_MAIN = SCR / 'kd' / 'lib' / 'lcsc.3dshapes'
REPO_PUSB = Path('/Users/cadaritre/Documents/TresVizo RTK/TresVizoRTK-hw-kicad/hardware/panel-usb/kicad')
TMP = HERE / 'tmp'
IMG = HERE / 'img'
PUSB_SRC = TMP / 'pusb_src'
LIB_PUSB = PUSB_SRC / 'lib' / 'lcsc.3dshapes'
KICAD_CLI = '/Applications/KiCad/KiCad.app/Contents/MacOS/kicad-cli'
for d in (TMP, IMG):
    d.mkdir(exist_ok=True)

import FreeCAD as App
import Part
import Import
V = App.Vector


def log(*a):
    print('[%6.1f s]' % (time.time() - T0), *a, flush=True)


def r2(x):
    return None if x is None else round(float(x), 2)


def r3(x):
    return None if x is None else round(float(x), 3)


# ============================================================================
# Posicion nueva de la placa principal (plugs.json)
# ============================================================================
PL = json.loads((HERE / 'plugs.json').read_text(encoding='utf-8'))
Z_TOP = PL['z_top']                 # 87.5
Y_FACE = PL['y_face']               # 3.1
Y_BACK = PL['y_back']               # 1.5
W_B, H_B = PL['size']               # 46 x 64
Z_BOT = Z_TOP - H_B                 # 23.5
XH = W_B / 2                        # 23
T_PCB = Y_FACE - Y_BACK             # 1.6

# STEP de kicad-cli con --user-origin 100x100mm: X = u, Y = -v, Z desde la cara trasera.
# Carcasa: x = 23 - X, y = 1.5 + Z, z = 87.5 + Y  (rotacion propia, det +1)
MAT_MAIN = App.Matrix(-1, 0, 0, XH,
                      0, 0, 1, Y_BACK,
                      0, 1, 0, Z_TOP,
                      0, 0, 0, 1)
# Placa panel-usb (README y scripts/layout.py): u = x + 10.4, v = 31.3 - y, cara inferior
# z = 90.17, cara de componentes z = 91.77 hacia arriba -> x = X - 10.4, y = 31.3 + Y, z = 90.17 + Z
PU_U0, PU_V0, PU_ZB = 10.4, 31.3, 90.17
PU_ZT = PU_ZB + 1.6
MAT_PUSB = App.Matrix(1, 0, 0, -PU_U0,
                      0, 1, 0, PU_V0,
                      0, 0, 1, PU_ZB,
                      0, 0, 0, 1)


def to_uv(x, y, z):
    """Carcasa -> placa principal: (u, v, altura sobre la cara de componentes)."""
    return XH - x, Z_TOP - z, y - Y_FACE


def bb_case(b):
    return {'x': [r2(b.XMin), r2(b.XMax)], 'y': [r2(b.YMin), r2(b.YMax)], 'z': [r2(b.ZMin), r2(b.ZMax)]}


def bb_board(b):
    return {'u': [r2(XH - b.XMax), r2(XH - b.XMin)], 'v': [r2(Z_TOP - b.ZMax), r2(Z_TOP - b.ZMin)],
            'h_sobre_cara': [r2(b.YMin - Y_FACE), r2(b.YMax - Y_FACE)]}


def bb_pusb(b):
    return {'u_pusb': [r2(b.XMin + PU_U0), r2(b.XMax + PU_U0)],
            'v_pusb': [r2(PU_V0 - b.YMax), r2(PU_V0 - b.YMin)],
            'h_sobre_cara_pusb': [r2(b.ZMin - PU_ZT), r2(b.ZMax - PU_ZT)]}


def pt_case(p):
    return [r2(p.x), r2(p.y), r2(p.z)]


def pt_board(p):
    u, v, h = to_uv(p.x, p.y, p.z)
    return {'u': r2(u), 'v': r2(v), 'h': r2(h)}


def xform(shape, mat):
    s = shape.copy()
    s.transformShape(mat)
    return s


def box(x0, x1, y0, y1, z0, z1):
    return Part.makeBox(x1 - x0, y1 - y0, z1 - z0, V(x0, y0, z0))


def cyl_y(r, x, z, y0, y1):
    return Part.makeCylinder(r, y1 - y0, V(x, y0, z), V(0, 1, 0))


def cyl_z(r, x, y, z0, z1):
    return Part.makeCylinder(r, z1 - z0, V(x, y, z0), V(0, 0, 1))


def fuse_all(shapes):
    out = shapes[0]
    for s in shapes[1:]:
        out = out.fuse(s)
    return out


def bbdist(b1, b2):
    dx = max(0.0, b1.XMin - b2.XMax, b2.XMin - b1.XMax)
    dy = max(0.0, b1.YMin - b2.YMax, b2.YMin - b1.YMax)
    dz = max(0.0, b1.ZMin - b2.ZMax, b2.ZMin - b1.ZMax)
    return math.sqrt(dx * dx + dy * dy + dz * dz)


def common_vol(a, b):
    """Volumen de la interseccion (sin contar dos veces solidos solapados) y su caja."""
    try:
        c = a.common(b)
    except Exception as e:                       # pragma: no cover
        return None, None
    sols = [s for s in c.Solids if s.Volume > 1e-9]
    if not sols:
        return 0.0, None
    if len(sols) > 1:
        try:
            f = sols[0].multiFuse(sols[1:])
            return f.Volume, f.BoundBox
        except Exception:
            pass
    comp = Part.makeCompound(sols)
    return sum(s.Volume for s in sols), comp.BoundBox


N_RECALC = []


def _on(shape, p, tol=1e-3):
    return shape.distToShape(Part.Vertex(p))[0] < tol


def robust_dist(a, b, k=200):
    """Distancia por muestreo: puntos del teselado de cada forma (los k mas cercanos a la caja de la
    otra) contra la otra forma. Cota superior, ajustada al teselado (0.02)."""
    import numpy as np
    best = (1e9, None, None)
    for src, dst, a_side in ((a, b, True), (b, a, False)):
        vs = src.tessellate(0.02)[0]
        if not vs:
            continue
        arr = np.array([[p.x, p.y, p.z] for p in vs])
        bb = dst.BoundBox
        dx = np.maximum(0, np.maximum(bb.XMin - arr[:, 0], arr[:, 0] - bb.XMax))
        dy = np.maximum(0, np.maximum(bb.YMin - arr[:, 1], arr[:, 1] - bb.YMax))
        dz = np.maximum(0, np.maximum(bb.ZMin - arr[:, 2], arr[:, 2] - bb.ZMax))
        for i in np.argsort(dx * dx + dy * dy + dz * dz)[:k]:
            p = V(*arr[i])
            d, pts, _ = dst.distToShape(Part.Vertex(p))
            if d < best[0]:
                q = pts[0][1]
                best = (d, p, q) if a_side else (d, q, p)
    return best


def pair(a, b, need_vol=True):
    d, pts, _ = a.distToShape(b)
    res = {'d': d, 'pa': pts[0][0], 'pb': pts[0][1], 'vol': 0.0, 'bb': None}
    if need_vol and d < 1e-4:
        v, bb = common_vol(a, b)
        res['vol'], res['bb'] = (v if v is not None else -1.0), bb
        if v is not None and v > 1e-9:
            return res
    # Comprobacion: cada punto devuelto tiene que estar sobre su forma. distToShape de OCC da a veces
    # resultados falsos (p. ej. 0) con aristas degeneradas de algunos modelos de LCSC (Q401: arista de
    # un empalme de 0.01 mm frente al cilindro de la bateria). Si no se cumple, se mide por muestreo.
    if not (_on(a, res['pa']) and _on(b, res['pb'])):
        d2, p2a, p2b = robust_dist(a, b)
        N_RECALC.append([round(res['d'], 3), round(d2, 3)])
        res.update(d=d2, pa=p2a, pb=p2b, recalculada=True)
    return res


def solids_of(shape):
    sols = list(shape.Solids)
    if not sols:
        for sh in shape.Shells:
            try:
                s = Part.makeSolid(sh)
                if abs(s.Volume) > 1e-9:
                    sols.append(s)
            except Exception:
                pass
    return sols


# ============================================================================
# Carcasa: funciones del generador de V2.2 (copia) y del primer estudio
# ============================================================================
def load_ns(path):
    ns = {'__file__': str(path), '__name__': path.stem}
    exec(compile(path.read_text(encoding='utf-8'), str(path), 'exec'), ns)
    return ns


Q = types.SimpleNamespace(**{k: v for k, v in load_ns(MECH / 'v02_params.py').items()
                             if not k.startswith('__')})
_src = (COPY / 'build_v2_2.py').read_text(encoding='utf-8')
_head = _src[:_src.index("doc = App.newDocument")]
ns = {'__file__': str(COPY / 'build_v2_2.py'), '__name__': 'v22'}
_argv = sys.argv
sys.argv = [str(COPY / 'build_v2_2.py'), '--output-dir', str(TMP / 'gen_tmp')]
exec(compile(_head, str(COPY / 'build_v2_2.py'), 'exec'), ns)
sys.argv = _argv
tube_ring, yz_prism = ns['tube_ring'], ns['yz_prism']
RO, RI, R_COLLAR, BOSS_BITE = ns['RO'], ns['RI'], ns['R_COLLAR'], ns['BOSS_BITE']
Z_FLOOR, Z_TUBE0, Z_TUBE1 = ns['Z_FLOOR'], ns['Z_TUBE0'], ns['Z_TUBE1']
Z_NECK_BOTTOM, COLLAR_H, COLLAR_T = ns['Z_NECK_BOTTOM'], ns['COLLAR_H'], ns['COLLAR_T']
PAN, TUBE, BACK, LOCK = ns['PAN'], ns['TUBE'], ns['BACK'], ns['LOCK']
MOLD, CARR = Q.MAIN, Q.CARRIER     # parametros del primer estudio (placa en z 21-85)


# --- copiado de ../mech/v02_check.py (sin cambios de geometria) ----------------
def build_ribs():
    z0 = Z_FLOOR + BACK['arranque_sobre_piso']
    z1 = Z_NECK_BOTTOM - BACK['margen_cuello']
    h = z1 - z0
    ct = Q.RIBS['t']
    clip = Part.makeCylinder(RI + BOSS_BITE, h + 2, V(0, 0, z0 - 1))
    ribs = [box(rx - ct / 2, rx + ct / 2, -(RI + 2), Q.RIBS['y_front'], z0, z1).common(clip)
            for rx in Q.RIBS['x']]
    body = fuse_all(ribs)
    return body.cut(ns['oblique_ramp'](R_COLLAR + 0.5, z0, RI + h))


def rail_geometry(yb=None, t=None):
    yb = MOLD['y_back'] if yb is None else yb
    t = MOLD['t'] if t is None else t
    ymid = yb + t / 2
    gw, lt = Q.RAILS['groove_w'], Q.RAILS['lip_t']
    return ymid, ymid - gw / 2 - lt, ymid + gw / 2 + lt


def build_rails_old():
    ymid, y0, y1 = rail_geometry()
    z0, z1 = Q.RAILS['z']
    xe = MOLD['x'][1]
    lip = xe - Q.RAILS['lip_in']
    shapes = []
    for s in (-1, 1):
        fin = box(min(s * lip, s * (RI + 1)), max(s * lip, s * (RI + 1)), y0, y1, 15.0, z1)
        fin = fin.common(Part.makeCylinder(RI + BOSS_BITE, 200, V(0, 0, 0)))
        groove = box(min(s * lip, s * (xe + Q.RAILS['groove_clear'])),
                     max(s * lip, s * (xe + Q.RAILS['groove_clear'])),
                     ymid - Q.RAILS['groove_w'] / 2, ymid + Q.RAILS['groove_w'] / 2, 0, z1 + 1)
        shapes.append(fin.cut(groove))
    rails = fuse_all(shapes)
    z_c = Z_TUBE0 + COLLAR_H
    cone = Part.makeCone(R_COLLAR + z_c, R_COLLAR - (z0 - z_c), z0, V(0, 0, 0))
    return rails.cut(cone)


def build_arms_old():
    A = Q.ARMS
    lip = MOLD['x'][1] - Q.RAILS['lip_in']
    shapes = []
    for s in (-1, 1):
        x_in, x_fin = A['x_in'], lip + 1.0
        zu_fin = A['z_under_at_fin']
        pts = [(x_in, A['z_top']), (x_fin, A['z_top']), (x_fin, zu_fin - 1.0),
               (lip, zu_fin), (x_in, zu_fin + (lip - x_in))]
        vs = [V(s * px, A['y'][0], pz) for px, pz in pts]
        prof = Part.Face(Part.makePolygon(vs + [vs[0]]))
        arm = prof.extrude(V(0, A['y'][1] - A['y'][0], 0))
        u, v = MOLD['holes_uv'][0 if s > 0 else 1]
        hx, hz = MOLD['x'][1] - u, MOLD['z'][1] - v
        arm = arm.cut(cyl_y(1.05, hx, hz, A['y'][1] - 6.0, A['y'][1] + 1.0))
        shapes.append(arm)
    return fuse_all(shapes)


def build_carrier_stops():
    xl, xr = CARR['x']
    yl0, yl1 = CARR['y'][0] - 0.5, CARR['y'][1] - 1.5
    left = box(-(RI + 1), xl - 0.3, yl0, yl1, 15.0, 68.0)
    left = left.common(Part.makeCylinder(RI + BOSS_BITE, 200, V(0, 0, 0)))
    ct = Q.RIBS['t']
    right = box(xr + 0.3, Q.RIBS['x'][1] + ct / 2, Q.RIBS['y_front'] - 1.0, -2.0, 30.0, 68.0)
    stops = left.fuse(right)
    z_c = Z_TUBE0 + COLLAR_H
    cone = Part.makeCone(R_COLLAR + z_c, 1.0, z_c + R_COLLAR - 1.0, V(0, 0, 0))
    return stops.cut(cone)


def build_tube_v02(features=('ribs', 'rails', 'arms', 'stops')):
    body = tube_ring(RO, RI, Z_TUBE0, Z_TUBE1 - Z_TUBE0)
    body = body.fuse(tube_ring(RI, R_COLLAR, Z_TUBE0, COLLAR_H))
    top_collar = tube_ring(RI, R_COLLAR, Z_TUBE1 - COLLAR_H, COLLAR_H)
    top_collar = ns['undercut_chamfer'](top_collar, RI, COLLAR_T, Z_TUBE1 - COLLAR_H)
    body = body.fuse(top_collar)
    if 'ribs' in features:
        body = body.fuse(build_ribs())
    if 'rails' in features:
        body = body.fuse(build_rails_old())
    if 'arms' in features:
        body = body.fuse(build_arms_old())
    if 'stops' in features:
        body = body.fuse(build_carrier_stops())
    BAY_CLR, SIGN_CAP = ns['BAY_CLR'], ns['SIGN_CAP']
    body = body.cut(ns['bayonet_groove'](Z_TUBE0 - 1, 6.0, Z_TUBE0 + 4.0 - BAY_CLR))
    body = body.cut(ns['bayonet_groove'](Z_TUBE1 - 6.0, 7.0, Z_TUBE1 - 8.0 - BAY_CLR, SIGN_CAP))
    pad, rebate, window = ns['panel_frame'](PAN)
    body = body.fuse(pad).cut(rebate).cut(window)
    half = PAN['tornillo_separacion_z'] / 2
    for dz in (-half, half):
        body = body.cut(ns['radial_tool'](PAN['tornillo_piloto'] / 2, TUBE['pared'] + 12,
                                          PAN['angulo'], PAN['z_centro'] + dz))
    through = (RO + 2) - (R_COLLAR - 1.5)
    for z in (ns['Z_LOCK_BASE'], ns['Z_LOCK_CAP']):
        body = body.cut(ns['radial_tool'](LOCK['paso_libre'] / 2, through, LOCK['angulo'], z))
        body = body.cut(ns['radial_tool'](LOCK['cabeza_diametro'] / 2,
                                          LOCK['cabeza_profundidad'] + 2, LOCK['angulo'], z))
    return ns['clean'](body)
# --- fin de lo copiado ---------------------------------------------------------


# Rieles NUEVOS propuestos (solo para medir): misma seccion que los del primer estudio
# (labio de 1.5 sobre cada cara de la placa, ranura 0.3 mas alla del canto, ranura de 2.0 en y,
# labios de 1.0), de z 39 a z 90; el riel +X (lado u = 0) cortado en z 54-71 por la antena.
NEW_RAILS = {'z': (39.0, 90.0), 'corte_+X_z': (54.0, 71.0), 'labio_sobre_cara': 1.5,
             'holgura_ranura_canto': 0.3, 'ranura_y': 2.0, 'labio_t': 1.0}


def build_rails_new():
    ymid, y0, y1 = rail_geometry(Y_BACK, T_PCB)
    z0, z1 = NEW_RAILS['z']
    lip = XH - NEW_RAILS['labio_sobre_cara']
    out = {}
    for s, tag in ((-1, '-X (u = 46)'), (1, '+X (u = 0)')):
        fin = box(min(s * lip, s * (RI + 1)), max(s * lip, s * (RI + 1)), y0, y1, z0, z1)
        fin = fin.common(Part.makeCylinder(RI + BOSS_BITE, 200, V(0, 0, 0)))
        groove = box(min(s * lip, s * (XH + NEW_RAILS['holgura_ranura_canto'])),
                     max(s * lip, s * (XH + NEW_RAILS['holgura_ranura_canto'])),
                     ymid - NEW_RAILS['ranura_y'] / 2, ymid + NEW_RAILS['ranura_y'] / 2, 0, z1 + 1)
        fin = fin.cut(groove)
        if s > 0:
            c0, c1 = NEW_RAILS['corte_+X_z']
            fin = fin.cut(box(0, RI + 2, -5, 10, c0, c1))
        out[tag] = fin
    return out


# ============================================================================
# KiCad: huellas, STEP y correccion de los modelos de LCSC
# ============================================================================
def footprints(pcb_path, ox=100.0, oy=100.0):
    t = Path(pcb_path).read_text(encoding='utf-8')
    starts = [m.start() for m in re.finditer(r'\n\t\(footprint "', t)]
    out = {}
    for i, s in enumerate(starts):
        blk = t[s:starts[i + 1] if i + 1 < len(starts) else len(t)]
        ref = re.search(r'\(property "Reference" "([^"]+)"', blk).group(1)
        at = re.search(r'\(at ([-\d.]+) ([-\d.]+)(?: ([-\d.]+))?\)', blk)
        rec = {'fp': re.search(r'\(footprint "([^"]+)"', blk).group(1),
               'layer': re.search(r'\(layer "([^"]+)"\)', blk).group(1),
               'u': float(at.group(1)) - ox, 'v': float(at.group(2)) - oy,
               'rot': float(at.group(3) or 0.0)}
        m = re.search(r'\(model "([^"]+)"\s*\(offset\s*\(xyz ([^)]*)\)\s*\)\s*\(scale\s*\(xyz ([^)]*)\)'
                      r'\s*\)\s*\(rotate\s*\(xyz ([^)]*)\)', blk)
        if m:
            rec['model'] = m.group(1)
            rec['offset'] = [float(a) for a in m.group(2).split()]
            rec['model_rot'] = [float(a) for a in m.group(4).split()]
        out[ref] = rec
    return out


def import_step(path):
    doc = App.newDocument('imp_' + re.sub(r'\W', '_', path.stem))
    Import.insert(str(path), doc.Name)
    parts = [o for o in doc.Objects if o.TypeId == 'App::Part']
    roots = [o for o in parts if not [p for p in o.InList if p.TypeId == 'App::Part']]
    assert len(roots) == 1, roots
    root = roots[0]
    assert root.Placement.Base.Length < 1e-9 and abs(root.Placement.Rotation.Angle) < 1e-9
    comps, board = [], None
    for k in root.Group:
        if k.TypeId == 'App::Part':
            comps.append({'label': k.Label, 'pl': App.Placement(k.Placement), 'shape': k.Shape.copy()})
        elif k.TypeId == 'Part::Feature':
            assert board is None
            board = k.Shape.copy()
    App.closeDocument(doc.Name)
    return comps, board


def match_footprints(comps, fps):
    cand = {ref: f for ref, f in fps.items() if 'model' in f}
    used = set()
    for c in comps:
        b = c['pl'].Base
        best = None
        for ref, f in cand.items():
            a = math.radians(f['rot'])
            ox, oy = f['offset'][0], f['offset'][1]
            ex = f['u'] + ox * math.cos(a) - oy * math.sin(a)
            ey = -f['v'] + ox * math.sin(a) + oy * math.cos(a)
            d = math.hypot(b.x - ex, b.y - ey)
            if best is None or d < best[0]:
                best = (d, ref)
        assert best[0] < 0.05, (c['label'], best)
        assert best[1] not in used, best
        used.add(best[1])
        c['ref'] = best[1]
        c['fp'] = cand[best[1]]
    missing = sorted(set(cand) - used)
    return missing


NUM = r'[-+]?\d*\.?\d+(?:[eE][-+]?\d+)?'


def wrl_points(path):
    """Vertices de un .wrl de easyeda2kicad (sin Transform), en mm (unidad VRML = 0.1 in)."""
    t = path.read_text(encoding='utf-8', errors='ignore')
    if 'Transform' in t:
        raise RuntimeError('wrl con Transform: no soportado ' + str(path))
    pts = []
    for blk in re.findall(r'point\s*\[(.*?)\]', t, re.S):
        v = [float(a) for a in re.findall(NUM, blk)]
        pts += [(v[i] * 2.54, v[i + 1] * 2.54, v[i + 2] * 2.54) for i in range(0, len(v) - 2, 3)]
    return pts


_models = {}


def lcsc_model(libdir, stem):
    """Desplazamiento .step -> .wrl de un modelo de LCSC (en el sistema del modelo) y validacion."""
    key = (str(libdir), stem)
    if key in _models:
        return _models[key]
    pts = wrl_points(libdir / (stem + '.wrl'))
    sh = Part.read(str(libdir / (stem + '.step')))
    xs, ys, zs = zip(*pts)
    wb = (min(xs), max(xs), min(ys), max(ys), min(zs), max(zs))
    sb = sh.BoundBox
    wc = ((wb[0] + wb[1]) / 2, (wb[2] + wb[3]) / 2, (wb[4] + wb[5]) / 2)
    delta = (wc[0] - sb.Center.x, wc[1] - sb.Center.y, wc[2] - sb.Center.z)
    moved = sh.copy()
    moved.translate(V(*delta))
    step = max(1, len(pts) // 48)
    ds = sorted(moved.distToShape(Part.Vertex(V(*p)))[0] for p in pts[::step])
    rec = {'delta_mm': [r3(a) for a in delta],
           'wrl_caja': [r2(a) for a in wb],
           'step_caja': [r2(sb.XMin), r2(sb.XMax), r2(sb.YMin), r2(sb.YMax), r2(sb.ZMin), r2(sb.ZMax)],
           'validacion_puntos_wrl_a_step_trasladado_mm': {
               'n': len(ds), 'mediana': r3(ds[len(ds) // 2]),
               'p90': r3(ds[int(0.9 * (len(ds) - 1))]), 'max': r3(ds[-1])},
           '_step_bb': sb}
    _models[key] = rec
    return rec


def load_board(step_path, pcb_path, libdir, mat, name):
    """Importa el STEP de kicad-cli, identifica cada instancia por su huella, corrige los modelos de
    LCSC a la posicion de su .wrl y lleva todo a la carcasa. Devuelve placa (1.6 mm) y componentes."""
    fps = footprints(pcb_path)
    comps, board_raw = import_step(step_path)
    missing = match_footprints(comps, fps)
    corr = {}
    for c in comps:
        f = c['fp']
        model = f['model']
        c['model'] = Path(model).name
        c['raw'] = c['shape'].copy()
        if 'lcsc.3dshapes' in model and model.endswith('.wrl'):
            stem = Path(model).stem
            rec = lcsc_model(libdir, stem)
            # comprobacion: la geometria nativa de la instancia es el .step de la biblioteca
            nat = c['shape'].copy()
            nat.transformShape(c['pl'].inverse().toMatrix())
            nb, sb = nat.BoundBox, rec['_step_bb']
            err = max(abs(nb.XMin - sb.XMin), abs(nb.XMax - sb.XMax), abs(nb.YMin - sb.YMin),
                      abs(nb.YMax - sb.YMax), abs(nb.ZMin - sb.ZMin), abs(nb.ZMax - sb.ZMax))
            shift = c['pl'].Rotation.multVec(V(*rec['delta_mm']))
            c['shape'].translate(shift)
            c['shift_step'] = shift
            c['native_check_err'] = err
            corr.setdefault(stem, {k: v for k, v in rec.items() if not k.startswith('_')})
            corr[stem].setdefault('instancias', []).append(c['ref'])
        else:
            c['shift_step'] = V(0, 0, 0)
            c['native_check_err'] = None
    # Placa: el STEP trae solo el dielectrico (Z 0-1.51); se rehace con 1.6 desde la cara inferior
    faces = [f for f in board_raw.Faces
             if abs(f.BoundBox.ZMin) < 1e-6 and abs(f.BoundBox.ZMax) < 1e-6]
    bottom = max(faces, key=lambda f: f.Area)
    board16 = bottom.extrude(V(0, 0, 1.6))
    out = {'board_raw_case': xform(board_raw, mat), 'board': xform(board16, mat),
           'board_raw_step_bb': board_raw.BoundBox, 'missing': missing, 'corr': corr, 'comps': []}
    for c in comps:
        sols = solids_of(c['shape'])
        fallback = False
        if not sols:
            sols = [box(*[getattr(c['shape'].BoundBox, k) for k in
                          ('XMin', 'XMax', 'YMin', 'YMax', 'ZMin', 'ZMax')])]
            fallback = True
        sh = xform(Part.makeCompound(sols), mat)
        raw = xform(Part.makeCompound(solids_of(c['raw']) or sols), mat)
        out['comps'].append({'ref': c['ref'], 'model': c['model'], 'shape': sh, 'raw': raw,
                             'shift_step': c['shift_step'], 'native_check_err': c['native_check_err'],
                             'fallback_caja': fallback, 'n_solidos': len(sols)})
    out['comps'].sort(key=lambda c: c['ref'])
    log(name, ':', len(out['comps']), 'componentes con modelo;', 'sin instancia:', missing)
    return out


# ============================================================================
# 1. Carcasa
# ============================================================================
log('carcasa: breps del primer estudio')
CASE_NAMES = ['base', 'battery_1s', 'button', 'cap', 'carrier', 'carrier_sma_plug', 'coax', 'cover',
              'imu', 'leds_assumed', 'nut_keepers', 'oled', 'platform', 'sma_antenna', 'tube',
              'pusb_heads', 'pusb_pcb', 'pusb_ph6', 'pusb_plug_wires', 'pusb_receptacle']
BR = {}
for n in CASE_NAMES:
    s = Part.Shape()
    s.importBrep(str(CAD / f'{n}.brep'))
    BR[n] = s

# Tuerca 5/8-11 de laton del jalon (no esta en los breps; su alojamiento hexagonal de la base esta
# vacio): 23.8125 entre caras, 13.89 de alto como maximo, apoyada en el anillo de 2.0 -> cara superior
# en z 15.89 (0.016 bajo el piso de la base). Misma orientacion que el alojamiento.
NUTP = ns['NUT']
NUT_REF = ns['hex_prism'](NUTP['entre_caras'] / 2.0, NUTP['anillo_asiento'], NUTP['alto'])
log('carcasa: tubo rehecho (completo, sin rieles ni brazos viejos)')
tube_full = build_tube_v02()
tube_base = build_tube_v02(features=('ribs', 'stops'))
old_rails = build_rails_old()
old_arms = build_arms_old()
xor = tube_full.cut(BR['tube']).Volume + BR['tube'].cut(tube_full).Volume
rebuild = {'volumen_tube_brep_mm3': r2(BR['tube'].Volume), 'volumen_rehecho_mm3': r2(tube_full.Volume),
           'diferencia_simetrica_mm3': r3(xor),
           'volumen_tubo_sin_rieles_ni_brazos_mm3': r2(tube_base.Volume),
           'volumen_rieles_viejos_mm3': r2(old_rails.Volume),
           'volumen_brazos_viejos_mm3': r2(old_arms.Volume),
           'tube_brep_menos_base_menos_rieles_y_brazos_mm3': r3(BR['tube'].cut(tube_base).cut(old_rails)
                                                                 .cut(old_arms).Volume)}
log('  tubo rehecho:', rebuild)
new_rails = build_rails_new()

# ============================================================================
# 2. Placa principal y panel-usb
# ============================================================================
log('placa principal: importar main-placed.step')
MB = load_board(HERE / 'main-placed.step', HERE / 'main-placed.kicad_pcb', LIB_MAIN, MAT_MAIN,
                'placa principal')

PUSB_STEP = HERE / 'panel-usb.step'
if not PUSB_STEP.exists():
    log('panel-usb: copia del proyecto a tmp/pusb_src y exportacion STEP con kicad-cli')
    PUSB_SRC.mkdir(parents=True, exist_ok=True)
    for f in ('tresvizo-panel-usb.kicad_pcb', 'tresvizo-panel-usb.kicad_pro', 'fp-lib-table'):
        shutil.copy2(REPO_PUSB / f, PUSB_SRC / f)
    if not (PUSB_SRC / 'lib').exists():
        shutil.copytree(REPO_PUSB / 'lib', PUSB_SRC / 'lib')
    subprocess.run([KICAD_CLI, 'pcb', 'export', 'step', '--subst-models', '--user-origin',
                    '100x100mm', '-f', '-o', str(PUSB_STEP),
                    str(PUSB_SRC / 'tresvizo-panel-usb.kicad_pcb')], check=True)
log('panel-usb: importar panel-usb.step')
PU = load_board(PUSB_STEP, PUSB_SRC / 'tresvizo-panel-usb.kicad_pcb', LIB_PUSB, MAT_PUSB, 'panel-usb')

# Comprobacion de la transformacion
bbr = MB['board_raw_case'].BoundBox
bb16 = MB['board'].BoundBox
pbr = PU['board_raw_case'].BoundBox
pb16 = PU['board'].BoundBox
R = {'notas': [
    'Placa principal en la posicion nueva: x = 23 - u, z = 87.5 - v, cara trasera y = 1.5, '
    'cara de componentes y = 3.1 (canto inferior z 23.5, superior z 87.5).',
    'Los modelos .step de LCSC del STEP exportado se corrigieron a la posicion de sus .wrl '
    '(ver correccion_modelos).',
    'tube = tubo del primer estudio rehecho sin rieles ni brazos (los viejos se dan aparte); '
    'los pusb_* viejos se sustituyen por la panel-usb real (panel-usb.step) salvo las cabezas '
    'de los M2 (pusb_heads), que van en los mismos agujeros.']}
R['transformacion'] = {
    'step_placa_principal_caja_XYZ': {'X': [r3(MB['board_raw_step_bb'].XMin), r3(MB['board_raw_step_bb'].XMax)],
                                      'Y': [r3(MB['board_raw_step_bb'].YMin), r3(MB['board_raw_step_bb'].YMax)],
                                      'Z': [r3(MB['board_raw_step_bb'].ZMin), r3(MB['board_raw_step_bb'].ZMax)]},
    'placa_principal_del_step_en_carcasa': bb_case(bbr),
    'placa_principal_1_6_en_carcasa': bb_case(bb16),
    'determinante': r3(MAT_MAIN.determinant()),
    'placa_principal_ok': (abs(bb16.XMin + 23) < 1e-3 and abs(bb16.XMax - 23) < 1e-3 and
                           abs(bb16.YMin - 1.5) < 1e-3 and abs(bb16.YMax - 3.1) < 1e-3 and
                           abs(bb16.ZMin - 23.5) < 1e-3 and abs(bb16.ZMax - 87.5) < 1e-3),
    'nota_espesor': 'El cuerpo de placa del STEP es solo el dielectrico (Z 0-1.51) y los modelos se apoyan '
                    'en Z = 1.595; para las comprobaciones la placa se rehizo con 1.6 mm (y 1.5-3.1).',
    'panel_usb_del_step_en_carcasa': bb_case(pbr),
    'panel_usb_1_6_en_carcasa': bb_case(pb16),
}
log('transformacion:', R['transformacion']['placa_principal_1_6_en_carcasa'],
    R['transformacion']['panel_usb_1_6_en_carcasa'])

# Componentes: tabla y correcciones
comp_by_ref = {c['ref']: c for c in MB['comps']}
pu_by_ref = {c['ref']: c for c in PU['comps']}
R['correccion_modelos'] = {
    'motivo': 'kicad-cli --subst-models pone el .step de LCSC en lugar del .wrl referenciado en la huella; '
              'los .step de LCSC/EasyEDA tienen otro origen. Se mide el desplazamiento (centro de las cajas) '
              'y se valida que una traslacion pura los hace coincidir.',
    'placa_principal': MB['corr'], 'panel_usb': PU['corr'],
    'instancias_sin_modelo_en_step': {'placa_principal': MB['missing'], 'panel_usb': PU['missing']},
}
shift_tab = {}
for c in MB['comps'] + PU['comps']:
    s = c['shift_step']
    if s.Length > 0.05:
        # desplazamiento en la carcasa (lo que se movio el componente respecto del STEP exportado)
        b0, b1 = c['raw'].BoundBox, c['shape'].BoundBox
        shift_tab[c['ref']] = {'modelo': c['model'],
                               'movido_en_carcasa_xyz_mm': [r2(b1.Center.x - b0.Center.x),
                                                            r2(b1.Center.y - b0.Center.y),
                                                            r2(b1.Center.z - b0.Center.z)],
                               'caja_step_crudo': bb_case(b0), 'caja_corregida': bb_case(b1)}
R['correccion_modelos']['instancias_movidas'] = shift_tab
R['correccion_modelos']['error_max_geometria_nativa_vs_biblioteca_mm'] = r3(max(
    [c['native_check_err'] for c in MB['comps'] + PU['comps'] if c['native_check_err'] is not None]))

comp_table = {}
for c in MB['comps']:
    b = c['shape'].BoundBox
    comp_table[c['ref']] = {'modelo': c['model'], 'caja': bb_case(b), 'placa': bb_board(b),
                            'alto_sobre_cara_mm': r2(b.YMax - Y_FACE)}
R['componentes_placa_principal'] = comp_table
ymin_all = min(c['shape'].BoundBox.YMin for c in MB['comps'])
R['nada_detras_de_la_placa'] = {'y_min_componentes_mm': r3(ymin_all), 'ok': ymin_all >= Y_BACK - 1e-6}

# Coherencia con plugs.json: boca de cada conector frente a donde empieza su clavija
mouths = {}
for p in PL['plugs']:
    c = comp_by_ref[p['ref']]
    for tag, shp in (('corregido', c['shape']), ('step_crudo', c['raw'])):
        b = shp.BoundBox
        us, vs = [q[0] for q in p['plug']], [q[1] for q in p['plug']]
        rec = mouths.setdefault(p['ref'], {})
        if min(vs) < 0.01 and max(vs) < 2:          # sale por el canto superior (v < 0)
            rec['clavija_empieza_v'] = r2(max(vs))
            rec['boca_v_' + tag] = r2(Z_TOP - b.ZMax)
        elif max(vs) > H_B - 2:                     # canto inferior
            rec['clavija_empieza_v'] = r2(min(vs))
            rec['boca_v_' + tag] = r2(Z_TOP - b.ZMin)
        else:                                        # entra por un lado en el plano de la placa
            uu = [q[0] for q in p['plug']]
            wu = [q[0] for q in p['wires']]
            if sum(wu) / len(wu) < sum(uu) / len(uu):    # cables hacia u menor: boca en u max de la clavija
                rec['clavija_empieza_u'] = r2(max(uu))
                rec['boca_u_' + tag] = r2(XH - b.XMax)
            else:
                rec['clavija_empieza_u'] = r2(min(uu))
                rec['boca_u_' + tag] = r2(XH - b.XMin)
        rec['alto_' + tag] = r2(b.YMax - Y_FACE)
R['bocas_conectores_vs_plugs_json'] = mouths

# ============================================================================
# 3. Clavijas
# ============================================================================
def prism_uv(poly, h):
    pts = [V(XH - u, Y_FACE, Z_TOP - v) for u, v in poly]
    s = Part.Face(Part.makePolygon(pts + [pts[0]])).extrude(V(0, h, 0))
    return s


PLUGS = {}
for p in PL['plugs']:
    PLUGS[p['ref']] = {'family': p['family'], 'h': p['h'], 'plug': prism_uv(p['plug'], p['h']),
                       'wires': prism_uv(p['wires'], p['h']), 'own': [p['ref']], 'src': p}
# J502 (GH 8 de la panel-usb): mismas reglas que la J101 de plugs.json (clavija 11.25 de ancho que
# asoma 3.1 de la boca, 3.0 de reserva para doblar los cables, 4.35 de alto sobre la cara)
j502 = pu_by_ref['J502']['shape'].BoundBox
GH_OUT, GH_WIRES, GH_W, GH_H = 3.1, 3.0, 11.25, 4.35
y_m = j502.YMin
xc = (j502.XMin + j502.XMax) / 2
PLUGS['J502'] = {'family': 'GH', 'h': GH_H, 'own': ['J502'],
                 'plug': box(xc - GH_W / 2, xc + GH_W / 2, y_m - GH_OUT, y_m, PU_ZT, PU_ZT + GH_H),
                 'wires': box(xc - GH_W / 2, xc + GH_W / 2, y_m - GH_OUT - GH_WIRES, y_m - GH_OUT,
                              PU_ZT, PU_ZT + GH_H),
                 'src': {'boca_y': r2(y_m), 'boca_v_pusb': r2(PU_V0 - y_m), 'x_centro': r2(xc)}}
R['clavijas'] = {}
for ref, P in PLUGS.items():
    R['clavijas'][ref] = {'familia': P['family'], 'alto_mm': P['h'],
                          'clavija': bb_case(P['plug'].BoundBox), 'cables': bb_case(P['wires'].BoundBox)}
    if ref != 'J502':
        R['clavijas'][ref]['clavija_placa'] = bb_board(P['plug'].BoundBox)
        R['clavijas'][ref]['cables_placa'] = bb_board(P['wires'].BoundBox)
    else:
        R['clavijas'][ref].update(P['src'])

# ============================================================================
# Piezas contra las que se mide
# ============================================================================
pu_comp_shape = Part.makeCompound([c['shape'] for c in PU['comps']])
PARTS = {   # nombre -> lista de solidos (la caja de cada uno sirve de prefiltro)
    'button': [BR['button']], 'oled': [BR['oled']], 'cover': [BR['cover']],
    'leds_assumed': list(BR['leds_assumed'].Solids),
    'panel_usb_pcb': [PU['board']],
    'panel_usb_componentes': [c['shape'] for c in PU['comps']],
    'panel_usb_cabezas_M2': list(BR['pusb_heads'].Solids),
    'J502_clavija': [PLUGS['J502']['plug']], 'J502_cables': [PLUGS['J502']['wires']],
    'tube_sin_rieles_ni_brazos': [tube_base],
    'rieles_viejos_tube': list(old_rails.Solids), 'brazos_viejos_tube': list(old_arms.Solids),
    'rieles_nuevos_propuestos': list(new_rails.values()),
    'carrier': [BR['carrier']], 'carrier_sma_plug': [BR['carrier_sma_plug']],
    'battery_1s': [BR['battery_1s']], 'base': [BR['base']], 'nut_keepers': list(BR['nut_keepers'].Solids),
    'tuerca_5_8_ref': [NUT_REF],
    'coax': [BR['coax']], 'cap': [BR['cap']], 'platform': [BR['platform']], 'imu': [BR['imu']],
    'sma_antenna': [BR['sma_antenna']],
}
PANEL_SIDE = ['button', 'oled', 'cover', 'leds_assumed', 'panel_usb_pcb', 'panel_usb_componentes',
              'panel_usb_cabezas_M2', 'J502_clavija', 'J502_cables']


def check_items_vs_parts(items, parts, near=3.0, kmin=4, skip=None):
    """items: [(nombre, forma)]; parts: {nombre: [solidos]}. Distancia exacta para los pares cuya
    caja este a menos de `near` mm y, como minimo, los `kmin` mas cercanos por caja."""
    out = {}
    LB[id(parts)] = lbs = {}
    for pname, sols in parts.items():
        rows = []
        lb = 1e9          # cota inferior (por caja) de los pares no calculados
        for sol in sols:
            pb = sol.BoundBox
            order = sorted(((bbdist(s.BoundBox, pb), n, s) for n, s in items
                            if not (skip and skip(n, pname))), key=lambda t: t[0])
            for i, (bd, n, s) in enumerate(order):
                if bd > near and i >= kmin:
                    lb = min(lb, bd)
                    break
                r = pair(s, sol)
                r.update(item=n, bbd=bd)
                rows.append(r)
        lbs[pname] = lb
        # combinar por item (si la pieza tiene varios solidos)
        best = {}
        for r in rows:
            b = best.get(r['item'])
            if b is None:
                best[r['item']] = dict(r)
            else:
                if r['d'] < b['d']:
                    vol = b['vol'] + r['vol']
                    bb = b['bb']
                    b.update(r)
                    b['vol'], b['bb'] = vol, (r['bb'] or bb)
                else:
                    b['vol'] += r['vol']
                    b['bb'] = b['bb'] or r['bb']
        out[pname] = sorted(best.values(), key=lambda r: (r['d'], -r['vol']))
    return out


LB = {}


def summarize(res, parts, board_coords=True, contact_vol=0.01):
    S = {}
    lbs = LB.get(id(parts), {})
    for pname, rows in res.items():
        if not rows:
            S[pname] = {'sin_pares_cercanos': True}
            continue
        coll = [r for r in rows if r['vol'] >= contact_vol]
        cont = [r for r in rows if r['d'] < 1e-3 and r['vol'] < contact_vol]
        m = rows[0]
        e = {'choque_total_mm3': r2(sum(r['vol'] for r in coll)),
             'minimo_exacto': bool(m['d'] <= lbs.get(pname, 1e9) + 1e-9),
             'choques': [{'item': r['item'], 'mm3': r2(r['vol']), 'caja_choque': bb_case(r['bb']),
                          **({'caja_choque_placa': bb_board(r['bb'])} if board_coords and r['bb'] else {})}
                         for r in coll],
             'contactos_<0.01mm3': sorted(r['item'] for r in cont),
             'distancia_min_mm': r2(m['d']), 'mas_cercano': m['item'],
             'punto_item': pt_case(m['pa']), 'punto_pieza': pt_case(m['pb']),
             'cercanos_<3mm': [[r['item'], r2(r['d'])] for r in rows if r['d'] < 3.0][:12]}
        if board_coords:
            e['punto_item_placa'] = pt_board(m['pa'])
        S[pname] = e
    return S


# ============================================================================
# A. Placa y componentes contra la carcasa
# ============================================================================
log('A: placa + componentes contra la carcasa')
items_A = [('PCB', MB['board'])] + [(c['ref'], c['shape']) for c in MB['comps']]
resA = check_items_vs_parts(items_A, PARTS)
R['A_placa_y_componentes_vs_carcasa'] = summarize(resA, PARTS)
for k, v in R['A_placa_y_componentes_vs_carcasa'].items():
    log('  %-28s choque %8s  dmin %6s (%s)' % (k, v.get('choque_total_mm3'), v.get('distancia_min_mm'),
                                                v.get('mas_cercano')))

# ============================================================================
# B. Clavijas
# ============================================================================
log('B: clavijas')
items_B = []
for ref, P in PLUGS.items():
    items_B += [(ref + ':clavija', P['plug']), (ref + ':cables', P['wires'])]
PARTS_B = {k: v for k, v in PARTS.items() if k not in ('J502_clavija', 'J502_cables', 'panel_usb_componentes')}
PARTS_B['panel_usb_componentes_sin_J502'] = [c['shape'] for c in PU['comps'] if c['ref'] != 'J502']
PARTS_B['panel_usb_J502_cuerpo'] = [pu_by_ref['J502']['shape']]
resB_case = check_items_vs_parts(items_B, PARTS_B,
                                 skip=lambda n, p: n.startswith('J502') and p in ('panel_usb_pcb',
                                                                                  'panel_usb_J502_cuerpo'))
R['B_clavijas_vs_carcasa'] = summarize(resB_case, PARTS_B, board_coords=False)

# contra los componentes de la placa principal (menos el propio conector) y de la panel-usb
comp_parts = {c['ref']: [c['shape']] for c in MB['comps']}
comp_parts.update({'pusb:' + c['ref']: [c['shape']] for c in PU['comps']})
comp_parts['PCB'] = [MB['board']]
comp_parts['pusb:PCB'] = [PU['board']]


def own(item, part):
    ref = item.split(':')[0]
    return part == ref or part == 'pusb:' + ref


resB_comp = check_items_vs_parts(items_B, comp_parts, near=1.0, kmin=0, skip=own)
# componente ajeno mas cercano de cada clavija (sin su placa, sobre la que apoya)
near_foreign = {}
for n, s in items_B:
    cands = sorted(((bbdist(s.BoundBox, sh[0].BoundBox), pn, sh[0]) for pn, sh in comp_parts.items()
                    if pn not in ('PCB', 'pusb:PCB') and not own(n, pn)), key=lambda t: t[0])[:4]
    best = None
    for bd, pn, sh in cands:
        r = pair(s, sh)
        if best is None or r['d'] < best[1]:
            best = (pn, r['d'], r['vol'])
    near_foreign[n] = {'componente': best[0], 'distancia_mm': r3(best[1]), 'choque_mm3': r3(best[2])}
coll_comp = []
for pname, rows in resB_comp.items():
    for r in rows:
        if pname in ('PCB', 'pusb:PCB') and r['vol'] <= 1e-4 and r['d'] < 1e-3:
            continue      # la clavija apoya sobre la cara de su placa (contacto sin volumen)
        if r['vol'] > 1e-4 or r['d'] < 0.3:
            coll_comp.append({'clavija': r['item'], 'componente': pname, 'mm3': r2(r['vol']),
                              'distancia_mm': r3(r['d']),
                              'caja_choque': bb_case(r['bb']) if r['bb'] else None,
                              'caja_choque_placa': bb_board(r['bb']) if r['bb'] else None})
R['B_clavijas_vs_componentes'] = sorted(coll_comp, key=lambda e: (-(e['mm3'] or 0), e['distancia_mm']))
# minimo por clavija contra componentes ajenos
mins = {}
for pname, rows in resB_comp.items():
    for r in rows:
        k = r['item']
        if k not in mins or r['d'] < mins[k][1]:
            mins[k] = (pname, r['d'])
R['B_clavijas_componente_ajeno_mas_cercano'] = near_foreign
R['B_clavijas_vs_su_placa_mm3'] = {}
for n, s in items_B:
    brd = PU['board'] if n.startswith('J502') else MB['board']
    v_, _ = common_vol(s, brd)
    R['B_clavijas_vs_su_placa_mm3'][n] = r3(v_ or 0.0)

# entre clavijas
pp = {}
names = list(PLUGS)
for i, a in enumerate(names):
    for b in names[i + 1:]:
        for ta in ('plug', 'wires'):
            for tb in ('plug', 'wires'):
                A_, B_ = PLUGS[a][ta], PLUGS[b][tb]
                bd = bbdist(A_.BoundBox, B_.BoundBox)
                if bd > 3.0:
                    continue
                r = pair(A_, B_)
                pp[f'{a}:{ta} x {b}:{tb}'] = {'mm3': r2(r['vol']), 'distancia_mm': r3(r['d']),
                                              'caja_choque': bb_case(r['bb']) if r['bb'] else None}
R['B_clavijas_entre_si_<3mm'] = pp


# Largo libre a lo largo del eje de las clavijas de los cantos
def free_axis(ref, direction, obstacles, length=45.0):
    P = PLUGS[ref]
    src = P['src']
    us = [q[0] for q in src['plug']] + [q[0] for q in src['wires']]
    vs_plug = [q[1] for q in src['plug']]
    vs_all = vs_plug + [q[1] for q in src['wires']]
    x0, x1 = XH - max(us), XH - min(us)
    y0, y1 = Y_FACE, Y_FACE + P['h']
    if direction > 0:      # canto superior: hacia +z
        z_m = Z_TOP - max(vs_plug)
        probe = box(x0, x1, y0, y1, z_m, z_m + length)
        need_edge = (Z_TOP - min(vs_all)) - Z_TOP
        edge = Z_TOP
    else:
        z_m = Z_TOP - min(vs_plug)
        probe = box(x0, x1, y0, y1, z_m - length, z_m)
        need_edge = Z_BOT - (Z_TOP - max(vs_all))
        edge = Z_BOT
    hits = []
    for oname, sols in obstacles.items():
        for sol in sols:
            if bbdist(sol.BoundBox, probe.BoundBox) > 0:
                continue
            v, bb = common_vol(probe, sol)
            if v and v > 1e-6:
                zh = bb.ZMin if direction > 0 else bb.ZMax
                hits.append((abs(zh - z_m), oname, zh))
    hits.sort()
    res = {'direccion': '+z (canto superior)' if direction > 0 else '-z (canto inferior)',
           'seccion_x': [r2(x0), r2(x1)], 'seccion_y': [r2(y0), r2(y1)], 'boca_z': r2(z_m),
           'necesario_desde_el_canto_mm (clavija + cables)': r2(need_edge)}
    seen, lst = set(), []
    for d, o, zh in hits:
        if o in seen:
            continue
        seen.add(o)
        lst.append({'obstaculo': o, 'z': r2(zh), 'libre_desde_boca_mm': r2(d),
                    'libre_desde_canto_mm': r2(abs(zh - edge))})
    res['obstaculos_en_orden'] = lst[:6]
    if lst:
        res['libre_desde_canto_mm'] = lst[0]['libre_desde_canto_mm']
        res['margen_mm'] = r2(lst[0]['libre_desde_canto_mm'] - need_edge)
    return res


obst_axis = {k: v for k, v in PARTS.items()}
for ref2, P2 in PLUGS.items():
    obst_axis[ref2 + ':reserva'] = [P2['plug'], P2['wires']]
obst_axis['componentes_pusb'] = [c['shape'] for c in PU['comps']]
R['B_largo_libre_eje'] = {}
for ref, d in (('J101', 1), ('J405', 1), ('J406', 1), ('J102', -1), ('J301', -1), ('J404', -1)):
    ob = {k: v for k, v in obst_axis.items() if k != ref + ':reserva'}
    R['B_largo_libre_eje'][ref] = free_axis(ref, d, ob)
    # sin contar la reserva de la J502 (es el mismo cable J101-J502)
    if ref == 'J101':
        ob2 = {k: v for k, v in ob.items() if k not in ('J502:reserva', 'J502_clavija', 'J502_cables')}
        R['B_largo_libre_eje']['J101_sin_contar_el_cable_J502'] = free_axis(ref, d, ob2)
    log('  largo libre', ref, R['B_largo_libre_eje'][ref].get('libre_desde_canto_mm'),
        R['B_largo_libre_eje'][ref].get('obstaculos_en_orden', [{}])[0:1])

# J502 hacia atras (-y), por si acaso
probe = box(PLUGS['J502']['plug'].BoundBox.XMin, PLUGS['J502']['plug'].BoundBox.XMax, y_m - 40, y_m,
            PU_ZT, PU_ZT + GH_H)
hits = []
for oname, sols in {**PARTS, 'J101:reserva': [PLUGS['J101']['plug'], PLUGS['J101']['wires']],
                    'componentes_placa_principal': [c['shape'] for c in MB['comps']],
                    'PCB_placa_principal': [MB['board']]}.items():
    if oname.startswith('J502') or oname.startswith('panel_usb'):
        continue
    for sol in sols:
        if bbdist(sol.BoundBox, probe.BoundBox) > 0:
            continue
        v, bb = common_vol(probe, sol)
        if v and v > 1e-6:
            hits.append((y_m - bb.YMax, oname, bb.YMax))
hits.sort()
R['B_largo_libre_eje']['J502_hacia_-y'] = {
    'boca_y': r2(y_m), 'necesario_mm (clavija + cables)': GH_OUT + GH_WIRES,
    'obstaculos_en_orden': [{'obstaculo': o, 'y': r2(yh), 'libre_desde_boca_mm': r2(d)}
                            for d, o, yh in hits[:6]]}

# J101 frente a la J502 y la panel-usb, en detalle
j = {}
for ta in ('plug', 'wires'):
    for tb in ('plug', 'wires'):
        r = pair(PLUGS['J101'][ta], PLUGS['J502'][tb])
        j[f'J101:{ta} x J502:{tb}'] = {'mm3': r2(r['vol']), 'distancia_mm': r3(r['d']),
                                       'caja_choque': bb_case(r['bb']) if r['bb'] else None}
for ta in ('plug', 'wires'):
    for nm, shp in (('PCB panel-usb', PU['board']), ('J502 (cuerpo)', pu_by_ref['J502']['shape']),
                    ('J501', pu_by_ref['J501']['shape'])):
        r = pair(PLUGS['J101'][ta], shp)
        j[f'J101:{ta} x {nm}'] = {'mm3': r2(r['vol']), 'distancia_mm': r3(r['d'])}
r = pair(comp_by_ref['J101']['shape'], PLUGS['J502']['wires'])
j['J101 (cuerpo) x J502:cables'] = {'mm3': r2(r['vol']), 'distancia_mm': r3(r['d'])}
# Caras de salida de las dos clavijas (extremos del mismo cable J101-J502)
pb1, pb2 = PLUGS['J101']['plug'].BoundBox, PLUGS['J502']['plug'].BoundBox
c1 = V((pb1.XMin + pb1.XMax) / 2, (pb1.YMin + pb1.YMax) / 2, pb1.ZMax)     # sale hacia +z
c2 = V((pb2.XMin + pb2.XMax) / 2, pb2.YMin, (pb2.ZMin + pb2.ZMax) / 2)     # sale hacia -y
j['caras_de_salida'] = {'J101_centro': pt_case(c1), 'J101_sale_hacia': '+z',
                        'J502_centro': pt_case(c2), 'J502_sale_hacia': '-y',
                        'distancia_entre_centros_mm': r2((c2 - c1).Length),
                        'separacion_y_mm': r2(c2.y - c1.y), 'separacion_z_mm': r2(c2.z - c1.z)}
R['B_J101_vs_J502'] = j

# ============================================================================
# C. Paso por el collar (r 26)
# ============================================================================
log('C: radio maximo')


def max_r_pt(shape):
    best = (0.0, None)
    for e in shape.Edges:
        try:
            pts = e.discretize(Deflection=0.01)
        except Exception:
            continue
        for p in pts:
            rr = math.hypot(p.x, p.y)
            if rr > best[0]:
                best = (rr, p)
    try:
        vs, _ = shape.tessellate(0.05)
        for p in vs:
            rr = math.hypot(p.x, p.y)
            if rr > best[0]:
                best = (rr, p)
    except Exception:
        pass
    return best


rr = [(max_r_pt(c['shape']), c['ref']) for c in MB['comps']]
prof = {}
for c in [{'shape': MB['board'], 'ref': 'PCB'}] + MB['comps']:
    vs, _ = c['shape'].tessellate(0.05)
    for p in vs:
        k = min(int((p.z - Z_BOT) // 8.0), 7)
        rv = math.hypot(p.x, p.y)
        if rv > prof.get(k, (0, ''))[0]:
            prof[k] = (rv, c['ref'])
rr.sort(key=lambda t: -t[0][0])
rb = max_r_pt(MB['board'])
R['C_collar'] = {
    'radio_collar_mm': r2(R_COLLAR),
    'placa_sola_radio_max_mm': r3(rb[0]), 'placa_sola_punto': pt_case(rb[1]),
    'placa_y_componentes_radio_max_mm': r3(max(rb[0], rr[0][0][0])),
    'margen_mm': r3(R_COLLAR - max(rb[0], rr[0][0][0])),
    'pasa': max(rb[0], rr[0][0][0]) < R_COLLAR,
    'componentes_mas_alejados': [{'ref': ref, 'r_mm': r3(m[0]), 'punto': pt_case(m[1]),
                                  'punto_placa': pt_board(m[1])} for m, ref in rr[:6]],
}
rp = []
for ref, P in PLUGS.items():
    if ref == 'J502':
        continue
    for t in ('plug', 'wires'):
        m = max_r_pt(P[t])
        rp.append((m[0], ref + ':' + t))
rp.sort(reverse=True)
R['C_collar']['clavijas_puestas_radio_max (referencia)'] = [[n, r3(v)] for v, n in rp[:4]]
R['C_collar']['perfil_por_tramos_de_z (teselado 0.05)'] = {
    'z %.1f-%.1f' % (Z_BOT + 8 * k, Z_BOT + 8 * (k + 1)): [r3(v[0]), v[1]] for k, v in sorted(prof.items())}

# ============================================================================
# D. Franjas de los rieles
# ============================================================================
log('D: franjas de los rieles')
STRIP = 2.5
strips = {
    '-X (u 43.5-46), z 39-90': box(-30, -(XH - STRIP), Y_BACK - 0.5, 30, 39.0, 90.0),
    '+X (u 0-2.5), z 39-54': box(XH - STRIP, 30, Y_BACK - 0.5, 30, 39.0, 54.0),
    '+X (u 0-2.5), z 71-90': box(XH - STRIP, 30, Y_BACK - 0.5, 30, 71.0, 90.0),
}
items_D = items_A[1:] + items_B
D = {'franja_mm': STRIP, 'en_franja': [], 'cerca_de_franja_<1mm': []}
for sname, sb in strips.items():
    for n, s in items_D:
        if n.startswith('J502'):
            continue
        bd = bbdist(s.BoundBox, sb.BoundBox)
        if bd > 1.0:
            continue
        v, bb = common_vol(s, sb)
        if v and v > 1e-6:
            xe = bb.XMax if sb.BoundBox.XMin > 0 else bb.XMin
            D['en_franja'].append({'franja': sname, 'item': n, 'mm3': r3(v), 'caja': bb_case(bb),
                                   'caja_placa': bb_board(bb),
                                   'llega_a_x': r2(xe), 'llega_a_u': r2(XH - xe),
                                   'dentro_de_la_franja_mm': r2(abs(xe) - (XH - STRIP)),
                                   'dentro_del_labio_1.5_mm': r2(max(0.0, abs(xe) - (XH - 1.5)))})
        else:
            d = pair(s, sb, need_vol=False)['d']
            if d < 1.0:
                D['cerca_de_franja_<1mm'].append({'franja': sname, 'item': n, 'distancia_mm': r3(d)})
# Rieles propuestos como solidos
resD = check_items_vs_parts(items_A + [x for x in items_B if not x[0].startswith('J502')],
                            {('riel nuevo ' + k): [v] for k, v in new_rails.items()}, near=2.0, kmin=3)
D['rieles_nuevos_solidos'] = {k: {'choque_total_mm3': r2(sum(r['vol'] for r in rows if r['vol'] >= 1e-4)),
                                  'choques': [[r['item'], r3(r['vol']), bb_case(r['bb'])]
                                              for r in rows if r['vol'] >= 1e-4],
                                  'distancias_<2mm': [[r['item'], r3(r['d'])] for r in rows if r['d'] < 2.0][:10]}
                              for k, rows in resD.items()}
D['rieles_nuevos_definicion'] = NEW_RAILS
R['D_rieles'] = D

# ============================================================================
# E. Brazos traseros
# ============================================================================
log('E: brazos')
behind = {'carrier': [BR['carrier']], 'carrier_sma_plug': [BR['carrier_sma_plug']], 'coax': [BR['coax']],
          'battery_1s': [BR['battery_1s']], 'tube_sin_rieles_ni_brazos': [tube_base],
          'rieles_viejos_tube': list(old_rails.Solids), 'brazos_viejos_tube': list(old_arms.Solids),
          'rieles_nuevos_propuestos': list(new_rails.values())}
E = {}
for hrec in PL['holes']:
    u, v = hrec['u'], hrec['v']
    x, z = XH - u, Z_TOP - v
    e = {'u': u, 'v': v, 'x': r2(x), 'z': r2(z)}
    # 1) profundidad libre detras de la placa para un saliente de diametro 6 (eje del agujero, -y)
    probe = cyl_y(3.0, x, z, -RI - 1, Y_BACK)
    hits = []
    for on, sols in behind.items():
        for sol in sols:
            if bbdist(sol.BoundBox, probe.BoundBox) > 0:
                continue
            vv, bb = common_vol(probe, sol)
            if vv and vv > 1e-6:
                hits.append((Y_BACK - bb.YMax, on, bb.YMax))
    hits.sort()
    e['diametro_6_hacia_-y'] = [{'obstaculo': o, 'y': r2(yh), 'libre_desde_cara_trasera_mm': r2(d)}
                                for d, o, yh in hits[:5]]
    # 2) saliente de diametro 6 de y -5 a 1.3 (como los brazos viejos): distancias
    boss = cyl_y(3.0, x, z, -5.0, Y_BACK - 0.2)
    dd = {}
    for on, sols in behind.items():
        best = None
        for sol in sols:
            rr_ = pair(boss, sol)
            if best is None or rr_['d'] < best['d']:
                best = rr_
        dd[on] = {'distancia_mm': r2(best['d']), 'choque_mm3': r2(best['vol']), 'punto': pt_case(best['pb'])}
    e['saliente_d6_y_-5_a_1.3'] = dd
    # 3) brazo lateral recto desde la pared del mismo lado, a la altura del agujero (6 de alto, y -5..1.3)
    s = 1 if x > 0 else -1
    arm = box(min(x, s * (RI + 1)), max(x, s * (RI + 1)), -5.0, Y_BACK - 0.2, z - 3.0, z + 3.0)
    arm = arm.common(Part.makeCylinder(RI + BOSS_BITE, 200, V(0, 0, 0)))
    da = {}
    for on, sols in behind.items():
        if on == 'tube_sin_rieles_ni_brazos':
            continue
        best = None
        for sol in sols:
            rr_ = pair(arm, sol)
            if best is None or rr_['d'] < best['d']:
                best = rr_
        da[on] = {'distancia_mm': r2(best['d']), 'choque_mm3': r2(best['vol'])}
    e['brazo_lateral_desde_la_pared_6x6.3'] = {'largo_desde_pared_mm (en y = -1.85)':
                                               r2(math.sqrt(RI ** 2 - 1.85 ** 2) - abs(x)),
                                               'distancias': da}
    # 4) delante: cabeza del tornillo M2.5 (diametro 5, 2 de alto) contra componentes y panel
    head = cyl_y(2.5, x, z, Y_FACE, Y_FACE + 2.0)
    hd = []
    for c in MB['comps']:
        if bbdist(c['shape'].BoundBox, head.BoundBox) < 1.5:
            rr_ = pair(head, c['shape'])
            hd.append([c['ref'], r3(rr_['d']), r3(rr_['vol'])])
    hd.sort(key=lambda t: t[1])
    e['cabeza_M2.5_d5x2_delante_vs_componentes'] = hd[:4]
    hp = {}
    for on in ('button', 'oled', 'cover', 'leds_assumed'):
        rr_ = pair(head, PARTS[on][0])
        hp[on] = r2(rr_['d'])
    e['cabeza_M2.5_vs_panel_mm'] = hp
    # 5) agujero frente a los brazos viejos: tramo de z que ocupa el brazo viejo en la x del agujero
    e['brazos_viejos_pilotos_xz'] = [[r2(MOLD['x'][1] - uu), r2(MOLD['z'][1] - vv)] for uu, vv in MOLD['holes_uv']]
    line = box(x - 0.01, x + 0.01, -1.01, -0.99, 40.0, 100.0)
    vv_, bb_ = common_vol(line, old_arms)
    if vv_ and bb_:
        e['brazo_viejo_en_x_del_agujero_z'] = [r2(bb_.ZMin), r2(bb_.ZMax)]
        e['agujero_respecto_al_brazo_viejo'] = (
            'dentro (%.1f bajo su cara superior, %.1f sobre la inferior)' % (bb_.ZMax - z, z - bb_.ZMin)
            if bb_.ZMin <= z <= bb_.ZMax else
            ('%.1f mm por debajo de su cara inferior' % (bb_.ZMin - z) if z < bb_.ZMin else
             '%.1f mm por encima de su cara superior' % (z - bb_.ZMax)))
    else:
        e['brazo_viejo_en_x_del_agujero_z'] = None
    E[hrec['ref']] = e
R['E_brazos'] = E

# ============================================================================
# F. Otras comprobaciones
# ============================================================================
log('F: otras')
F = {}
# holgura delante de cada componente hasta lo del panel (boton, OLED, tapa, LEDs, panel-usb, J502)
fr = []
for c in MB['comps']:
    best = (99.0, None)
    for pn in PANEL_SIDE:
        for row in resA.get(pn, []):
            if row['item'] == c['ref'] and row['d'] < best[0]:
                best = (row['d'], pn)
    if best[1] is not None:
        fr.append((best[0], c['ref'], best[1]))
fr.sort()
F['componentes_mas_cerca_del_panel'] = [{'ref': ref, 'distancia_mm': r2(d), 'a': pn,
                                         'alto_sobre_cara_mm': comp_table[ref]['alto_sobre_cara_mm']}
                                        for d, ref, pn in fr[:10]]
tall = sorted(((c['shape'].BoundBox.YMax - Y_FACE, c['ref']) for c in MB['comps']), reverse=True)
F['componentes_mas_altos_mm'] = [[ref, r2(h)] for h, ref in tall[:8]]
# zona del boton en la placa (keepout 'boton' u 17.5-28.5, v 38.5-49.5)
bz = box(-5.5, 5.5, Y_FACE, Y_FACE + 20, 38.0, 49.0)
inz = []
for c in MB['comps']:
    v_, bb_ = common_vol(c['shape'], bz)
    if v_ and v_ > 1e-6:
        inz.append([c['ref'], r3(v_)])
F['componentes_en_la_zona_del_boton_x+-5.5_z38-49'] = inz
# panel-usb real contra la tapa, el tubo y las piezas del panel (comprobacion de su colocacion)
pu_items = [('pusb:PCB', PU['board'])] + [('pusb:' + c['ref'], c['shape']) for c in PU['comps']]
PARTS_F = {k: PARTS[k] for k in ('cover', 'tube_sin_rieles_ni_brazos', 'oled', 'leds_assumed', 'cap',
                                  'platform', 'coax', 'carrier_sma_plug', 'battery_1s')}
resF = check_items_vs_parts(pu_items, PARTS_F)
F['panel_usb_real_vs_carcasa'] = summarize(resF, PARTS_F, board_coords=False)
F['panel_usb_real_posiciones'] = {
    'J501_cara_y': r2(pu_by_ref['J501']['shape'].BoundBox.YMax),
    'J501_caja': bb_case(pu_by_ref['J501']['shape'].BoundBox),
    'J502_caja': bb_case(pu_by_ref['J502']['shape'].BoundBox),
    'J502_boca_y': r2(y_m), 'J502_alto_z': r2(pu_by_ref['J502']['shape'].BoundBox.ZMax)}
# placa frente al carrier y brazos viejos (lo que hay justo detras)
F['placa_cara_trasera'] = {k: r3(pair(MB['board'], PARTS[k][0] if len(PARTS[k]) == 1 else
                                          Part.makeCompound(PARTS[k]), need_vol=False)['d'])
                           for k in ('carrier', 'carrier_sma_plug', 'brazos_viejos_tube', 'rieles_viejos_tube')}
u201 = comp_by_ref['U201']['shape']
ub = u201.BoundBox
ant = box(ub.XMax - 6.0, ub.XMax + 0.01, ub.YMin - 0.01, ub.YMax + 0.01, ub.ZMin - 0.01, ub.ZMax + 0.01)
ant_sh = u201.common(ant)
F['antena_ESP32_ultimos_6mm_del_modulo'] = {
    'caja': bb_case(ant_sh.BoundBox), 'caja_placa': bb_board(ant_sh.BoundBox),
    'distancias_mm': {k: r2(pair(ant_sh, PARTS[k][0], need_vol=False)['d']) for k in
                      ('carrier', 'carrier_sma_plug', 'battery_1s', 'coax')}}
F['distancias_recalculadas_por_muestreo [distToShape falso, muestreo]'] = N_RECALC
R['F_otras'] = F
R['tubo_rehecho'] = rebuild

# ============================================================================
# Guardar
# ============================================================================
def clean_json(o):
    if isinstance(o, dict):
        return {str(k): clean_json(v) for k, v in o.items() if not str(k).startswith('_')}
    if isinstance(o, (list, tuple)):
        return [clean_json(v) for v in o]
    if isinstance(o, float):
        return round(o, 4)
    if isinstance(o, App.Vector):
        return [r3(o.x), r3(o.y), r3(o.z)]
    return o


R['tiempo_s'] = round(time.time() - T0, 1)
(HERE / 'results_v02b.json').write_text(json.dumps(clean_json(R), indent=1, ensure_ascii=False),
                                       encoding='utf-8')
log('results_v02b.json escrito')

# Documento FreeCAD
doc = App.newDocument('TresVizoV02b')


def add(name, shape, group=None):
    o = doc.addObject('Part::Feature', re.sub(r'\W', '_', name))
    o.Label = name
    o.Shape = shape
    if group is not None:
        group.addObject(o)
    return o


g_case = doc.addObject('App::DocumentObjectGroup', 'carcasa')
for n in ('base', 'cap', 'platform', 'cover', 'oled', 'button', 'leds_assumed', 'imu', 'sma_antenna',
          'nut_keepers', 'carrier', 'carrier_sma_plug', 'battery_1s', 'coax', 'pusb_heads'):
    add(n, BR[n], g_case)
add('tube_sin_rieles_ni_brazos', tube_base, g_case)
add('tuerca_5_8_ref', NUT_REF, g_case)
add('rieles_viejos', old_rails, g_case)
add('brazos_viejos', old_arms, g_case)
g_new = doc.addObject('App::DocumentObjectGroup', 'propuesta_nueva')
for k, v in new_rails.items():
    add('riel_nuevo_' + k, v, g_new)
for hrec in PL['holes']:
    x, z = XH - hrec['u'], Z_TOP - hrec['v']
    add('saliente_d6_' + hrec['ref'], cyl_y(3.0, x, z, -5.0, Y_BACK - 0.2), g_new)
g_mb = doc.addObject('App::DocumentObjectGroup', 'placa_principal')
add('PCB_principal', MB['board'], g_mb)
for c in MB['comps']:
    add(c['ref'], c['shape'], g_mb)
g_pl = doc.addObject('App::DocumentObjectGroup', 'clavijas')
for ref, P in PLUGS.items():
    add(ref + '_clavija', P['plug'], g_pl)
    add(ref + '_cables', P['wires'], g_pl)
g_pu = doc.addObject('App::DocumentObjectGroup', 'panel_usb_real')
add('PCB_panel_usb', PU['board'], g_pu)
for c in PU['comps']:
    add('pusb_' + c['ref'], c['shape'], g_pu)
doc.recompute()
doc.saveAs(str(HERE / 'v02b_check.FCStd'))
log('v02b_check.FCStd guardado')

# Formas para los cortes
SHAPES = {'tube': tube_base, 'old_rails': old_rails, 'old_arms': old_arms,
          'new_rails': Part.makeCompound(list(new_rails.values())),
          'main_pcb': MB['board'], 'main_comps': Part.makeCompound([c['shape'] for c in MB['comps']]),
          'plugs': Part.makeCompound([P['plug'] for r_, P in PLUGS.items() if r_ != 'J502']),
          'wires': Part.makeCompound([P['wires'] for r_, P in PLUGS.items() if r_ != 'J502']),
          'j502_plug': PLUGS['J502']['plug'], 'j502_wires': PLUGS['J502']['wires'],
          'pusb_pcb': PU['board'], 'pusb_comps': pu_comp_shape, 'nut': NUT_REF}
for n in ('base', 'cap', 'platform', 'cover', 'oled', 'button', 'leds_assumed', 'imu', 'sma_antenna',
          'nut_keepers', 'carrier', 'carrier_sma_plug', 'battery_1s', 'coax', 'pusb_heads'):
    SHAPES[n] = BR[n]
(TMP / 'shapes').mkdir(exist_ok=True)
for k, s in SHAPES.items():
    s.exportBrep(str(TMP / 'shapes' / f'{k}.brep'))
(TMP / 'shapes' / 'index.json').write_text(json.dumps(sorted(SHAPES)), encoding='utf-8')
log('fin')
