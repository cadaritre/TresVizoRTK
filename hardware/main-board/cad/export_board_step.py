#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""STEP de la placa principal en los ejes de la carcasa, con un sólido por componente.

1. Exporta el PCB con kicad-cli (--subst-models: cada .wrl de LCSC se cambia por el .step del mismo
   nombre) en una carpeta temporal.
2. Corrige cada modelo de LCSC a la posición de su .wrl: los .step de LCSC/EasyEDA no tienen el mismo
   origen que los .wrl con los que se diseñaron y comprobaron las huellas. Para cada modelo se mide
   el desplazamiento (centro de las cajas) y se valida que una traslación pura los hace coincidir
   (distancia de los puntos del .wrl a la superficie del .step trasladado).
3. Si a una huella con modelo le falta su instancia en el STEP (p. ej. no está el .step de LCSC), la
   sustituye por la caja de su .wrl, y lo dice.
4. Rehace el PCB con 1.6 mm (el STEP trae solo el dieléctrico) y lo lleva todo a la carcasa con los
   datos de kicad/plugs.json:

       x = x_u0 - u,   y = y_back + h,   z = z_top - v

   u y v: coordenadas de la placa (mm desde la esquina de arriba a la izquierda, mirando la cara de
   componentes); h: altura sobre el dorso. x_u0 es la x del canto u = 0 (si plugs.json no lo trae,
   size[0] / 2: placa centrada).

Salidas (en --out, por defecto esta carpeta):
  <nombre>.step  PCB ("PCB") y un sólido por componente con su referencia. Con un solo sólido por
                 pieza, FreeCAD conserva el nombre al importarla.
  <nombre>.json  transformación, caja de cada pieza en la carcasa y en la placa, correcciones.

Uso, desde hardware/main-board:
  PYTHONPATH=/Applications/FreeCAD.app/Contents/Resources/lib \\
  /Applications/FreeCAD.app/Contents/Resources/bin/python cad/export_board_step.py
"""
import sys
sys.dont_write_bytecode = True
import argparse, json, math, re, subprocess, tempfile, time
from pathlib import Path

HERE = Path(__file__).resolve().parent
MB = HERE.parent
KICAD_CLI = '/Applications/KiCad/KiCad.app/Contents/MacOS/kicad-cli'
T_PCB = 1.6

import FreeCAD as App
import Part
import Import
V = App.Vector
T0 = time.time()


def log(*a):
    print('[%6.1f s]' % (time.time() - T0), *a, flush=True)


def r2(x):
    return None if x is None else round(float(x), 2)


def r3(x):
    return None if x is None else round(float(x), 3)


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


def box(x0, x1, y0, y1, z0, z1):
    return Part.makeBox(x1 - x0, y1 - y0, z1 - z0, V(x0, y0, z0))


def xform(shape, mat):
    s = shape.copy()
    s.transformShape(mat)
    return s


# ============================================================================
# KiCad: huellas y STEP
# ============================================================================
def footprints(pcb_path, ox=100.0, oy=100.0):
    """Huellas del PCB: posición (u, v), giro, capa y su primer modelo 3D."""
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
        m = re.search(r'\(model "([^"]+)"(.*?)\n\t\t\)', blk, re.S)
        if m:
            body = m.group(2)

            def xyz(key, default):
                q = re.search(r'\(' + key + r'\s*\(xyz ([^)]*)\)', body)
                return [float(a) for a in q.group(1).split()] if q else default
            rec['model'] = m.group(1)
            rec['offset'] = xyz('offset', [0.0, 0.0, 0.0])
            rec['scale'] = xyz('scale', [1.0, 1.0, 1.0])
            rec['model_rot'] = xyz('rotate', [0.0, 0.0, 0.0])
        out[ref] = rec
    return out


def export_step(pcb, out_step):
    subprocess.run([KICAD_CLI, 'pcb', 'export', 'step', '--subst-models', '--user-origin', '100x100mm',
                    '-f', '-o', str(out_step), str(pcb)], check=True)


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
    """Cada instancia del STEP es la huella cuyo origen del modelo cae en su sitio (< 0.05 mm)."""
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
    return sorted(set(cand) - used)


# ============================================================================
# Modelos de LCSC: .wrl (con el que se diseñó la huella) contra .step
# ============================================================================
NUM = r'[-+]?\d*\.?\d+(?:[eE][-+]?\d+)?'


def wrl_points(path):
    """Vértices de un .wrl de easyeda2kicad (sin Transform), en mm (unidad VRML = 0.1 in)."""
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
    """Desplazamiento .step -> .wrl de un modelo de LCSC (en el sistema del modelo) y validación."""
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


def wrl_box_instance(f, libdir):
    """Caja del .wrl de una huella de la cara de arriba, en el sistema del STEP de kicad-cli."""
    pts = wrl_points(libdir / (Path(f['model']).stem + '.wrl'))
    xs, ys, zs = zip(*pts)
    s = box(min(xs), max(xs), min(ys), max(ys), min(zs), max(zs))
    s.translate(V(*f['offset']))
    s.rotate(V(0, 0, 0), V(0, 0, 1), f['rot'])
    s.translate(V(f['u'], -f['v'], T_PCB))
    return s


def single(shape):
    """Una pieza = un sólido, para que el STEP conserve su nombre al importarlo."""
    sols = solids_of(shape)
    if len(sols) == 1:
        return sols[0], 'ok'
    try:
        f = sols[0].multiFuse(sols[1:]).removeSplitter()
        if len(f.Solids) == 1 and f.isValid():
            return f.Solids[0], 'fundido'
        return f, 'compuesto'
    except Exception:
        return Part.makeCompound(sols), 'compuesto'


# ============================================================================
# Principal
# ============================================================================
def main():
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    ap.add_argument('--pcb', default=str(MB / 'kicad' / 'tresvizo-main.kicad_pcb'))
    ap.add_argument('--plugs', default=str(MB / 'kicad' / 'plugs.json'))
    ap.add_argument('--lib', default=str(MB / 'kicad' / 'lib' / 'lcsc.3dshapes'))
    ap.add_argument('--out', default=str(HERE))
    ap.add_argument('--name', default='placa-principal')
    args = ap.parse_args()
    pcb, libdir, out = Path(args.pcb), Path(args.lib), Path(args.out)
    out.mkdir(parents=True, exist_ok=True)

    PL = json.loads(Path(args.plugs).read_text(encoding='utf-8'))
    W, H = PL['size']
    X0 = PL.get('x_u0', W / 2.0)
    Z_TOP, Y_BACK, Y_FACE = PL['z_top'], PL['y_back'], PL['y_face']
    assert abs(Y_FACE - Y_BACK - T_PCB) < 1e-6, (Y_BACK, Y_FACE)
    # STEP de kicad-cli con --user-origin 100x100mm: X = u, Y = -v, Z desde el dorso.
    # Carcasa: x = X0 - X, y = Y_BACK + Z, z = Z_TOP + Y (rotación propia, det +1)
    MAT = App.Matrix(-1, 0, 0, X0,
                     0, 0, 1, Y_BACK,
                     0, 1, 0, Z_TOP,
                     0, 0, 0, 1)

    def bb_case(b):
        return {'x': [r2(b.XMin), r2(b.XMax)], 'y': [r2(b.YMin), r2(b.YMax)], 'z': [r2(b.ZMin), r2(b.ZMax)]}

    def bb_board(b):
        return {'u': [r2(X0 - b.XMax), r2(X0 - b.XMin)], 'v': [r2(Z_TOP - b.ZMax), r2(Z_TOP - b.ZMin)],
                'h_sobre_cara': [r2(b.YMin - Y_FACE), r2(b.YMax - Y_FACE)]}

    fps = footprints(pcb)
    with tempfile.TemporaryDirectory() as td:
        raw_step = Path(td) / 'board.step'
        log('kicad-cli: STEP de', pcb.name)
        export_step(pcb, raw_step)
        log('importar STEP')
        comps, board_raw = import_step(raw_step)
    missing = match_footprints(comps, fps)

    # Modelos de LCSC a la posición de su .wrl
    corr, worst = {}, 0.0
    for c in comps:
        f = c['fp']
        model = f['model']
        c['model'] = Path(model).name
        c['raw'] = c['shape'].copy()
        c['shift_step'] = V(0, 0, 0)
        c['native_check_err'] = None
        if 'lcsc.3dshapes' in model and model.endswith('.wrl'):
            stem = Path(model).stem
            rec = lcsc_model(libdir, stem)
            nat = c['shape'].copy()
            nat.transformShape(c['pl'].inverse().toMatrix())
            nb, sb = nat.BoundBox, rec['_step_bb']
            err = max(abs(nb.XMin - sb.XMin), abs(nb.XMax - sb.XMax), abs(nb.YMin - sb.YMin),
                      abs(nb.YMax - sb.YMax), abs(nb.ZMin - sb.ZMin), abs(nb.ZMax - sb.ZMax))
            shift = c['pl'].Rotation.multVec(V(*rec['delta_mm']))
            c['shape'].translate(shift)
            c['shift_step'] = shift
            c['native_check_err'] = err
            worst = max(worst, err)
            corr.setdefault(stem, {k: v for k, v in rec.items() if not k.startswith('_')})
            corr[stem].setdefault('instancias', []).append(c['ref'])

    # Huellas con modelo y sin instancia en el STEP: caja de su .wrl
    fallback = {}
    for ref in missing:
        f = fps[ref]
        model = f['model']
        why = None
        if not model.endswith('.wrl') or 'lcsc.3dshapes' not in model:
            why = 'modelo que kicad-cli no exportó y no es un .wrl de LCSC'
        elif f['layer'] != 'F.Cu':
            why = 'huella en ' + f['layer']
        elif any(abs(a) > 1e-9 for a in f['model_rot']) or any(abs(a - 1) > 1e-9 for a in f['scale']):
            why = 'modelo con giro o escala propios'
        if why:
            fallback[ref] = {'modelo': Path(model).name, 'sin_pieza': why}
            continue
        sh = wrl_box_instance(f, libdir)
        comps.append({'ref': ref, 'fp': f, 'model': Path(model).name, 'shape': sh, 'raw': sh.copy(),
                      'shift_step': V(0, 0, 0), 'native_check_err': None})
        fallback[ref] = {'modelo': Path(model).name, 'caja_del_wrl': True,
                         'motivo': 'kicad-cli no la exportó (¿falta el .step de LCSC?)'}

    # PCB: el STEP trae solo el dieléctrico (Z 0-1.51); se rehace con 1.6 desde el dorso
    faces = [fc for fc in board_raw.Faces
             if abs(fc.BoundBox.ZMin) < 1e-6 and abs(fc.BoundBox.ZMax) < 1e-6]
    bottom = max(faces, key=lambda fc: fc.Area)
    pcb_case = xform(bottom.extrude(V(0, 0, T_PCB)), MAT)

    tmp = App.newDocument('export_board')
    objs, table, how_n = [], {}, {}
    o = tmp.addObject('Part::Feature', 'PCB')
    o.Label = 'PCB'
    o.Shape = pcb_case
    objs.append(o)
    for c in sorted(comps, key=lambda c: c['ref']):
        sols = solids_of(c['shape'])
        caja = False
        if not sols:
            b = c['shape'].BoundBox
            sols = [box(b.XMin, b.XMax, b.YMin, b.YMax, b.ZMin, b.ZMax)]
            caja = True
        sh, how = single(xform(Part.makeCompound(sols), MAT))
        how_n[how] = how_n.get(how, 0) + 1
        o = tmp.addObject('Part::Feature', re.sub(r'\W', '_', c['ref']))
        o.Label = c['ref']
        o.Shape = sh
        objs.append(o)
        b = sh.BoundBox
        rec = {'modelo': c['model'], 'caja': bb_case(b), 'placa': bb_board(b),
               'alto_sobre_cara_mm': r2(b.YMax - Y_FACE), 'solidos': how}
        if c['shift_step'].Length > 0.05:
            b0 = xform(c['raw'], MAT).BoundBox
            rec['movido_respecto_de_kicad_cli_mm'] = [r2(b.Center.x - b0.Center.x), r2(b.Center.y - b0.Center.y),
                                                      r2(b.Center.z - b0.Center.z)]
        if caja:
            rec['caja_por_falta_de_solidos'] = True
        if c['ref'] in fallback:
            rec['caja_del_wrl'] = True
        table[c['ref']] = rec

    step_path = out / (args.name + '.step')
    Import.export(objs, str(step_path))
    App.closeDocument(tmp.Name)

    bp = pcb_case.BoundBox
    ok = (abs(bp.XMin - (X0 - W)) < 1e-3 and abs(bp.XMax - X0) < 1e-3 and abs(bp.YMin - Y_BACK) < 1e-3 and
          abs(bp.YMax - Y_FACE) < 1e-3 and abs(bp.ZMin - (Z_TOP - H)) < 1e-3 and abs(bp.ZMax - Z_TOP) < 1e-3)
    bad_val = {s: r['validacion_puntos_wrl_a_step_trasladado_mm'] for s, r in corr.items()
               if r['validacion_puntos_wrl_a_step_trasladado_mm']['max'] > 0.2}
    sin_modelo = sorted(ref for ref, f in fps.items() if 'model' not in f)
    res = {
        'pcb': str(pcb.relative_to(MB)) if pcb.is_relative_to(MB) else str(pcb),
        'transformacion': {'formula': 'x = %g - u, y = %g + h, z = %g - v' % (X0, Y_BACK, Z_TOP),
                           'determinante': r3(MAT.determinant()),
                           'pcb_en_carcasa': bb_case(bp), 'pcb_donde_debe': ok},
        'piezas': len(objs), 'solidos_por_pieza': how_n,
        'huellas_sin_modelo': sin_modelo,
        'sustituidas_o_sin_pieza': fallback,
        'correccion_lcsc': {'motivo': 'kicad-cli --subst-models pone el .step de LCSC en lugar del .wrl de la '
                                      'huella; los .step de LCSC/EasyEDA tienen otro origen. Se mide el '
                                      'desplazamiento (centro de las cajas) y se valida que una traslación pura '
                                      'los hace coincidir.',
                            'error_max_geometria_nativa_vs_biblioteca_mm': r3(worst),
                            'validacion_mala_max_mayor_0_2_mm': bad_val,
                            'modelos': corr},
        'componentes': table,
    }
    (out / (args.name + '.json')).write_text(json.dumps(res, indent=1, ensure_ascii=False) + '\n',
                                             encoding='utf-8')
    log('STEP:', step_path, '-', len(objs), 'piezas', how_n)
    log('PCB en la carcasa:', bb_case(bp), 'ok' if ok else 'FUERA DE SU SITIO')
    if fallback:
        log('sustituidas o sin pieza:', fallback)
    if bad_val:
        log('modelos de LCSC que no coinciden con su .wrl:', bad_val)
    if sin_modelo:
        log('huellas sin modelo 3D:', ' '.join(sin_modelo))
    return 0 if ok and not bad_val else 1


if __name__ == '__main__':
    sys.exit(main())
