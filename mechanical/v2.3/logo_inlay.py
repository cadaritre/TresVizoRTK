"""Incrustacion PLANA del logo para imprimir en TPU, del tamano exacto de su
grabado en el tubo.

El grabado del tubo es la proyeccion del logo plano sobre el cilindro: un punto
a x del eje del logo cae a un arco R * asin(x / R) sobre la superficie. Para que
la pieza plana de TPU, al doblarse sobre el tubo, llene el hueco, cada punto se
desenrolla a ese arco con R = radio medio del grabado. El espesor es el fondo
del grabado (queda a ras). Por omision el contorno es exacto: el TPU se comprime y
entra a presion. Con --holgura se puede reducir por lado (el desplazamiento 2D de
OCC deja autointersecciones en las esquinas concavas: revisar la malla).

Se dibuja como se ve desde fuera (cara visible hacia +Z). Para imprimir, la cara
visible va contra la cama (queda lisa).

Uso:
  PYTHONPATH=<freecad>/lib <freecad>/bin/python logo_inlay.py [--output-dir generated]
"""
import argparse, json, math
from pathlib import Path

import FreeCAD as App
import Part, MeshPart

ROOT = Path(__file__).resolve().parent
ap = argparse.ArgumentParser()
ap.add_argument('--output-dir', type=Path, default=ROOT / 'generated')
ap.add_argument('--holgura', type=float, default=0.0)
args, _ = ap.parse_known_args()
OUT = args.output_dir.resolve()
(OUT / 'stl').mkdir(parents=True, exist_ok=True)
(OUT / 'step').mkdir(parents=True, exist_ok=True)

P = json.loads((ROOT / 'parameters.json').read_text(encoding='utf-8'))
LOGO = P['logo']
RO = P['tubo']['diametro_exterior'] / 2.0
width, depth = LOGO['ancho_mm'], LOGO['profundidad_grabado']
R = RO - depth / 2.0
V = App.Vector


def densify(pts, step=0.6):
    out = []
    for (x0, y0), (x1, y1) in zip(pts, pts[1:] + pts[:1]):
        n = max(1, int(math.hypot(x1 - x0, y1 - y0) / step))
        out += [(x0 + (x1 - x0) * k / n, y0 + (y1 - y0) * k / n) for k in range(n)]
    return out


data = json.loads((ROOT / 'logo.json').read_text(encoding='utf-8'))
faces = []
for shape in sorted(data['shapes'], key=lambda s: s.get('depth', int(s['hole']))):
    pts = [(p[0] * width, p[1] * width) for p in shape['points']]
    if pts[0] == pts[-1]:
        pts = pts[:-1]
    if len(pts) < 3:
        continue
    pts = [(R * math.asin(max(-1.0, min(1.0, x / R))), y) for x, y in densify(pts)]
    vs = [V(x, y, 0) for x, y in pts]
    faces.append((shape.get('depth', int(shape['hole'])), Part.Face(Part.makePolygon(vs + [vs[0]]))))

face = None
for level, f in faces:
    if face is None:
        face = f
    elif level % 2:
        face = face.cut(f)
    else:
        face = face.fuse(f)
face = Part.makeCompound(face.removeSplitter().Faces)
if args.holgura > 0:
    face = Part.makeCompound([f.makeOffset2D(-args.holgura, join=0) for f in face.Faces])
solid = Part.makeCompound([f.extrude(V(0, 0, depth)) for f in face.Faces])
bb = solid.BoundBox
mesh = MeshPart.meshFromShape(Shape=solid, LinearDeflection=0.02, AngularDeflection=0.2, Relative=False)
mesh.write(str(OUT / 'stl' / '09-logo-inlay-tpu.stl'))
solid.exportStep(str(OUT / 'step' / '09-logo-inlay-tpu.step'))
info = {
    'pieza': '09-logo-inlay-tpu',
    'material': 'TPU',
    'piezas_sueltas': len(solid.Solids),
    'ancho_desenrollado_mm': round(bb.XLength, 3),
    'ancho_plano_original_mm': width,
    'alto_mm': round(bb.YLength, 3),
    'espesor_mm': depth,
    'radio_desenrollado_mm': R,
    'holgura_por_lado_mm': args.holgura,
    'solidos_validos': all(x.isValid() for x in solid.Solids),
    'mallas_cerradas_por_pieza': all((lambda m: m.isSolid() and not m.hasSelfIntersections() and not m.hasNonManifolds())(
        MeshPart.meshFromShape(Shape=x, LinearDeflection=0.02, AngularDeflection=0.2, Relative=False)) for x in solid.Solids),
}
(OUT / 'logo-inlay.json').write_text(json.dumps(info, indent=1, ensure_ascii=False), encoding='utf-8')
print(json.dumps(info, indent=1, ensure_ascii=False))
