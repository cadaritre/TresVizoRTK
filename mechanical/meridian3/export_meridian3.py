"""Exporta las piezas del Meridian3 a STL y STEP y comprueba que las mallas
cierren y que las piezas no se interfieran en la posicion cerrada.

Las envolventes de referencia (objetos ref_*) no se exportan: no se imprimen.
"""
import argparse, json
from pathlib import Path

import FreeCAD as App
import MeshPart

ROOT = Path(__file__).resolve().parent
ap = argparse.ArgumentParser(description=__doc__)
ap.add_argument('--output-dir', type=Path, default=ROOT / 'generated')
ap.add_argument('--linear-deflection', type=float, default=0.05)
ap.add_argument('--angular-deflection', type=float, default=0.25)
args, _ = ap.parse_known_args()
OUT = args.output_dir.resolve()
(OUT / 'stl').mkdir(parents=True, exist_ok=True)
(OUT / 'step').mkdir(parents=True, exist_ok=True)

doc = App.openDocument(str(OUT / 'Meridian3.FCStd'))
report, all_closed, shapes = [], True, []
for obj in doc.Objects:
    if not hasattr(obj, 'Shape') or obj.Shape.isNull() or obj.Name.startswith('ref_'):
        continue
    # FreeCAD antepone '_' a los nombres que empiezan con digito.
    name = obj.Name.lstrip('_').replace('_', '-')
    mesh = MeshPart.meshFromShape(Shape=obj.Shape, LinearDeflection=args.linear_deflection,
                                  AngularDeflection=args.angular_deflection, Relative=False)
    stl = OUT / 'stl' / f'{name}.stl'
    mesh.write(str(stl))
    obj.Shape.exportStep(str(OUT / 'step' / f'{name}.step'))
    shapes.append(obj.Shape)
    closed = mesh.isSolid() and not mesh.hasNonManifolds() and not mesh.hasSelfIntersections()
    all_closed = all_closed and closed
    report.append({'pieza': name, 'etiqueta': obj.Label, 'triangulos': mesh.CountFacets,
                   'cerrada': bool(mesh.isSolid()), 'no_manifold': bool(mesh.hasNonManifolds()),
                   'autointersecciones': bool(mesh.hasSelfIntersections()),
                   'volumen_cm3': round(obj.Shape.Volume / 1000.0, 2), 'stl': stl.name})

overlaps = []
names = [r['pieza'] for r in report]
for i in range(len(shapes)):
    for j in range(i + 1, len(shapes)):
        common = shapes[i].common(shapes[j])
        volume = common.Volume / 1000.0 if common.Solids else 0.0
        if volume > 0.01:
            overlaps.append({'a': names[i], 'b': names[j], 'cm3': round(volume, 3)})

result = {'piezas': report, 'todas_cerradas': all_closed, 'interferencias': overlaps,
          'sin_interferencias': not overlaps, 'deflexion_lineal': args.linear_deflection}
(OUT / 'exports.json').write_text(json.dumps(result, indent=1, ensure_ascii=False), encoding='utf-8')
print(json.dumps(result, indent=1, ensure_ascii=False))
