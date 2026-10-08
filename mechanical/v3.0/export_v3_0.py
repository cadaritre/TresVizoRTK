"""Exporta las piezas de V3.0 a STEP y STL y comprueba sus mallas e interferencias.

Una malla abierta no se puede laminar de forma fiable: se declara el resultado solo si todas
cierran (sin aristas no-manifold ni autointersecciones). Ademas sondea la pared del tubo: el
material que falta no aparece como interferencia (sale con codigo 1 si falta). Los objetos ref_* son piezas compradas o
reservas dibujadas para comprobar el montaje: no se exportan.

Uso:
  PYTHONPATH=/Applications/FreeCAD.app/Contents/Resources/lib \\
  /Applications/FreeCAD.app/Contents/Resources/bin/python export_v3_0.py [--output-dir generated]
Escribe <output-dir>/exports.json.
"""
import argparse, json, sys
from pathlib import Path

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
import FreeCAD as App
import Mesh, MeshPart, Part
import geom_v3_0 as G

ap = argparse.ArgumentParser(description=__doc__)
ap.add_argument('--output-dir', type=Path, default=ROOT / 'generated')
ap.add_argument('--linear-deflection', type=float, default=0.05)
ap.add_argument('--angular-deflection', type=float, default=0.25)
args, _ = ap.parse_known_args()
OUT = args.output_dir.resolve()
(OUT / 'stl').mkdir(parents=True, exist_ok=True)
(OUT / 'step').mkdir(parents=True, exist_ok=True)

doc = App.openDocument(str(OUT / 'TresVizo-V3.0.FCStd'))
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
    step = OUT / 'step' / f'{name}.step'
    obj.Shape.exportStep(str(step))
    shapes.append(obj.Shape)
    closed = mesh.isSolid() and not mesh.hasNonManifolds() and not mesh.hasSelfIntersections()
    all_closed = all_closed and closed
    report.append({'pieza': name, 'etiqueta': obj.Label, 'solido_valido': obj.Shape.isValid(),
                   'solidos': len(obj.Shape.Solids), 'triangulos': mesh.CountFacets,
                   'cerrada': bool(mesh.isSolid()), 'no_manifold': bool(mesh.hasNonManifolds()),
                   'autointersecciones': bool(mesh.hasSelfIntersections()),
                   'volumen_cm3': round(obj.Shape.Volume / 1000.0, 2), 'stl': stl.name, 'step': step.name})

# Interferencias entre piezas impresas en su posicion final. Las piezas comparten caras de
# contacto (volumen 0); se admite 0.05 mm3 por pareja por redondeos de OCC.
LIMITE_MM3 = 0.05
overlaps, names = [], [r['pieza'] for r in report]
for i in range(len(shapes)):
    for j in range(i + 1, len(shapes)):
        common = shapes[i].common(shapes[j])
        volume = common.Volume if common.Solids else 0.0
        if volume > LIMITE_MM3:
            overlaps.append({'a': names[i], 'b': names[j], 'mm3': round(volume, 3)})

# Guarda barata de la pared del tubo (sondas cada 1 mm): una pared que falta no es una
# interferencia. check_v3_0.py la repite cada 0.5 mm y compara el volumen.
tube = next((sh for nm, sh in zip(names, shapes) if nm == '02-tube'), None)
guard = G.wall_probes(tube, step=1.0) if tube is not None else None
guard_ok = bool(guard and guard['cara_plana']['ok'] and guard['anillo']['ok'])

result = {'piezas': report, 'todas_cerradas': all_closed, 'interferencias': overlaps,
          'sin_interferencias': not overlaps, 'limite_mm3': LIMITE_MM3,
          'guarda_pared_tubo': guard, 'guarda_pared_ok': guard_ok,
          'deflexion_lineal': args.linear_deflection, 'deflexion_angular': args.angular_deflection}
(OUT / 'exports.json').write_text(json.dumps(result, indent=1, ensure_ascii=False), encoding='utf-8')
print(json.dumps(result, indent=1, ensure_ascii=False))
if not guard_ok:
    print('FALLA: falta material en la pared del tubo (ver guarda_pared_tubo)', file=sys.stderr)
    sys.exit(1)
