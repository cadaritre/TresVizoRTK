"""Genera el estuche del receptor: modelo de FreeCAD, STEP y STL de cada pieza e indice del modelo.

Piezas: 01-base, 02-lid, 03-latch-left, 04-latch-right, 07-hinge-pin-left/right y 08-latch-pin-left/right
(PA12-HP); 05-seal-tpu y 06-liner-tpu (TPU). Sin tornilleria: los pernos son impresos.
Referencias (no se imprimen): el receptor V3.0 en su sitio.

Uso:
  PYTHONPATH=/Applications/FreeCAD.app/Contents/Resources/lib \\
  /Applications/FreeCAD.app/Contents/Resources/bin/python build_carry_case.py [--output-dir generated]
"""
import argparse, json, sys, time
from pathlib import Path

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
import FreeCAD as App
import Mesh, MeshPart, Part
import geom_carry_case as G

ap = argparse.ArgumentParser(description=__doc__)
ap.add_argument('--output-dir', type=Path, default=ROOT / 'generated')
ap.add_argument('--linear-deflection', type=float, default=0.03)
ap.add_argument('--angular-deflection', type=float, default=0.2)
args, _ = ap.parse_known_args()
OUT = args.output_dir.resolve()
(OUT / 'stl').mkdir(parents=True, exist_ok=True)
(OUT / 'step').mkdir(parents=True, exist_ok=True)

t0 = time.time()


def log(msg):
    print(f'[{time.time() - t0:6.1f} s] {msg}', flush=True)


parts = []
log('base')
parts.append(('01_base', 'Base', G.base(), 'PA12-HP negro'))
log('tapa')
parts.append(('02_lid', 'Tapa', G.lid(), 'PA12-HP negro'))
log('cierres')
parts.append(('03_latch_left', 'Cierre izquierdo', G.latch(G.LT['x_centers'][0]), 'PA12-HP negro'))
parts.append(('04_latch_right', 'Cierre derecho', G.latch(G.LT['x_centers'][1]), 'PA12-HP negro'))
log('junta')
parts.append(('05_seal_tpu', 'Junta de labio de TPU', G.seal(), 'TPU'))
log('forro')
parts.append(('06_liner_tpu', 'Forro de la tapa con las letras (TPU azul)', G.liner(), 'TPU azul #008AFC'))
log('pernos')
for xc, side in zip(G.HG['segment_x'], ('left', 'right')):
    parts.append((f'07_hinge_pin_{side}', f'Perno de bisagra impreso ({side})', G.hinge_pin(xc), 'PA12-HP negro'))
for xl, side in zip(G.LT['x_centers'], ('left', 'right')):
    parts.append((f'08_latch_pin_{side}', f'Perno de cierre impreso ({side})', G.latch_pin(xl), 'PA12-HP negro'))

doc = App.newDocument('CarryCase')
for name, label, shape, _ in parts:
    o = doc.addObject('Part::Feature', name)
    o.Label = label
    o.Shape = shape
log('referencias')
for name, label, s in G.receiver_objects():
    o = doc.addObject('Part::Feature', f'ref_receiver_{name}')
    o.Label = f'ref: receptor {label}'
    o.Shape = s
doc.recompute()
fc = OUT / 'TresVizo-CarryCase.FCStd'
if fc.exists():
    fc.unlink()                     # si no, FreeCAD deja una copia .FCBak al guardar encima
doc.saveAs(str(fc))
log('guardado el FCStd')

# STEP y STL de las piezas, y copias acostadas para imprimir en FDM las de TPU.
index = []
for name, label, shape, mat in parts:
    fname = name.replace('_', '-')
    mesh = MeshPart.meshFromShape(Shape=shape, LinearDeflection=args.linear_deflection,
                                  AngularDeflection=args.angular_deflection, Relative=False)
    mesh.write(str(OUT / 'stl' / f'{fname}.stl'))
    shape.exportStep(str(OUT / 'step' / f'{fname}.step'))
    bb = shape.BoundBox
    index.append({'pieza': fname, 'etiqueta': label, 'material': mat, 'valida': shape.isValid(),
                  'solidos': len(shape.Solids), 'volumen_cm3': round(shape.Volume / 1000.0, 2),
                  'caja': [round(v, 2) for v in (bb.XMin, bb.XMax, bb.YMin, bb.YMax, bb.ZMin, bb.ZMax)],
                  'malla_cerrada': bool(mesh.isSolid()), 'no_manifold': bool(mesh.hasNonManifolds()),
                  'triangulos': mesh.CountFacets})
    log(f'exportada {fname}')


def write_flat(shape, fname, flip):
    s = shape.copy()
    if flip:
        s.rotate(App.Vector(0, 0, 0), App.Vector(1, 0, 0), 180)
    bb = s.BoundBox
    s.translate(App.Vector(-(bb.XMin + bb.XMax) / 2, -(bb.YMin + bb.YMax) / 2, -bb.ZMin))
    m = MeshPart.meshFromShape(Shape=s, LinearDeflection=args.linear_deflection,
                               AngularDeflection=args.angular_deflection, Relative=False)
    m.write(str(OUT / 'stl' / fname))


# Junta: la tira contra la cama y el labio hacia arriba. Forro para FDM: placa contra la cama y letras
# hacia arriba, sin las almohadillas (van aparte, para no imprimir soportes de TPU).
write_flat(parts[4][2], '05-seal-tpu-para-imprimir.stl', True)
write_flat(G.liner(with_pads=False), '06-liner-tpu-sin-almohadillas-fdm.stl', False)
write_flat(G.liner_pads(), '06b-liner-pads-tpu-fdm.stl', True)

(OUT / 'model-index.json').write_text(json.dumps({'piezas': index, 'tornilleria': 'ninguna: pernos impresos (07 y 08)'}, indent=1, ensure_ascii=False) + '\n',
                                      encoding='utf-8')
log('listo')
