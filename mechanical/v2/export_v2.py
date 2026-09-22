"""Exporta V2 a STL y STEP y comprueba que las mallas queden cerradas.

Una malla abierta no se puede laminar de forma fiable, asi que el resultado se
declara solo si todas cierran.
"""
import argparse, json
from pathlib import Path

import FreeCAD as App
import Mesh, MeshPart, Part

ROOT = Path(__file__).resolve().parent
ap = argparse.ArgumentParser(description=__doc__)
ap.add_argument('--output-dir', type=Path, default=ROOT / 'generated')
ap.add_argument('--linear-deflection', type=float, default=0.05)
ap.add_argument('--angular-deflection', type=float, default=0.25)
args = ap.parse_args()
OUT = args.output_dir.resolve()
(OUT / 'stl').mkdir(parents=True, exist_ok=True)
(OUT / 'step').mkdir(parents=True, exist_ok=True)

doc = App.openDocument(str(OUT / 'TresVizo-V2.FCStd'))
report, all_closed = [], True
shapes = []
for obj in doc.Objects:
    if not hasattr(obj, 'Shape') or obj.Shape.isNull():
        continue
    # FreeCAD antepone '_' a los nombres que empiezan con digito.
    name = obj.Name.lstrip('_').replace('_', '-')
    mesh = MeshPart.meshFromShape(Shape=obj.Shape,
                                  LinearDeflection=args.linear_deflection,
                                  AngularDeflection=args.angular_deflection,
                                  Relative=False)
    stl = OUT / 'stl' / f'{name}.stl'
    mesh.write(str(stl))
    step = OUT / 'step' / f'{name}.step'
    obj.Shape.exportStep(str(step))
    shapes.append(obj.Shape)
    closed = mesh.isSolid() and not mesh.hasNonManifolds() and not mesh.hasSelfIntersections()
    all_closed = all_closed and closed
    report.append({
        'pieza': name,
        'etiqueta': obj.Label,
        'triangulos': mesh.CountFacets,
        'cerrada': bool(mesh.isSolid()),
        'no_manifold': bool(mesh.hasNonManifolds()),
        'autointersecciones': bool(mesh.hasSelfIntersections()),
        'volumen_cm3': round(obj.Shape.Volume / 1000.0, 2),
        'stl': stl.name,
    })

# Interferencias entre piezas en su posicion final. Las piezas comparten planos
# de contacto, asi que se admite un volumen comun despreciable.
overlaps = []
names = [r['pieza'] for r in report]
for i in range(len(shapes)):
    for j in range(i + 1, len(shapes)):
        common = shapes[i].common(shapes[j])
        volume = common.Volume / 1000.0 if common.Solids else 0.0
        if volume > 0.01:
            overlaps.append({'a': names[i], 'b': names[j], 'cm3': round(volume, 3)})

result = {
    'piezas': report,
    'todas_cerradas': all_closed,
    'interferencias': overlaps,
    'sin_interferencias': not overlaps,
    'deflexion_lineal': args.linear_deflection,
}
(OUT / 'exports.json').write_text(json.dumps(result, indent=1, ensure_ascii=False),
                                  encoding='utf-8')
print(json.dumps(result, indent=1, ensure_ascii=False))
