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

# El distintivo de TPU, ademas, acostado para imprimir: la cara que se ve (y 22.9) contra la cama
# (z 0), centrado en el origen. Gira -90 grados en X: z' = -y, y' = z.
for obj in doc.Objects:
    if obj.Name.lstrip('_') == '07_logo_inlay_tpu':
        sh = obj.Shape.copy()
        sh.rotate(App.Vector(0, 0, 0), App.Vector(1, 0, 0), -90)
        bb = sh.BoundBox
        sh.translate(App.Vector(-(bb.XMin + bb.XMax) / 2, -(bb.YMin + bb.YMax) / 2, -bb.ZMin))
        m = MeshPart.meshFromShape(Shape=sh, LinearDeflection=args.linear_deflection,
                                   AngularDeflection=args.angular_deflection, Relative=False)
        m.write(str(OUT / 'stl' / '07-logo-inlay-tpu-para-imprimir.stl'))

# Las bandas de TPU, ademas, de pie sobre su canto entero (sin soportes), centradas en el origen: la de abajo
# como esta (canto de z 0 contra la cama, la muesca arriba); la de arriba dada vuelta (canto de z 116 contra
# la cama, la muesca de la OLED arriba). Gira 180 grados en X.
for obj in doc.Objects:
    nm_ = obj.Name.lstrip('_')
    if nm_ in ('09_band_bottom_tpu', '10_band_top_tpu'):
        sh = obj.Shape.copy()
        if nm_.startswith('10'):
            sh.rotate(App.Vector(0, 0, 0), App.Vector(1, 0, 0), 180)
        bb = sh.BoundBox
        sh.translate(App.Vector(-(bb.XMin + bb.XMax) / 2, -(bb.YMin + bb.YMax) / 2, -bb.ZMin))
        m = MeshPart.meshFromShape(Shape=sh, LinearDeflection=args.linear_deflection,
                                   AngularDeflection=args.angular_deflection, Relative=False)
        m.write(str(OUT / 'stl' / (nm_.replace('_', '-') + '-para-imprimir.stl')))

# Interferencias entre piezas impresas en su posicion final. Las piezas comparten caras de
# contacto (volumen 0); se admite 0.05 mm3 por pareja por redondeos de OCC. Las bandas de TPU se dibujan
# con su medida de impresion: su solape con el tubo, la base y la tapa es el apriete (no cuenta; se informa
# aparte, como en V2.2). Contra el resto de piezas cuentan como cualquier otra.
LIMITE_MM3 = 0.05
overlaps, grip, names = [], [], [r['pieza'] for r in report]
for i in range(len(shapes)):
    for j in range(i + 1, len(shapes)):
        common = shapes[i].common(shapes[j])
        volume = common.Volume if common.Solids else 0.0
        if G.band_grip_pair(names[i], names[j]):
            grip.append({'a': names[i], 'b': names[j], 'mm3': round(volume, 3)})
        elif volume > LIMITE_MM3:
            overlaps.append({'a': names[i], 'b': names[j], 'mm3': round(volume, 3)})

# Guarda barata de la pared del tubo (sondas cada 1 mm): una pared que falta no es una
# interferencia. check_v3_0.py la repite cada 0.5 mm y compara el volumen.
tube = next((sh for nm, sh in zip(names, shapes) if nm == '02-tube'), None)
guard = G.wall_probes(tube, step=1.0) if tube is not None else None
guard_ok = bool(guard and guard['cara_plana']['ok'] and guard['anillo']['ok'])

result = {'piezas': report, 'todas_cerradas': all_closed, 'interferencias': overlaps,
          'sin_interferencias': not overlaps, 'limite_mm3': LIMITE_MM3,
          'apriete_de_las_bandas': grip,
          'guarda_pared_tubo': guard, 'guarda_pared_ok': guard_ok,
          'deflexion_lineal': args.linear_deflection, 'deflexion_angular': args.angular_deflection}
(OUT / 'exports.json').write_text(json.dumps(result, indent=1, ensure_ascii=False), encoding='utf-8')
print(json.dumps(result, indent=1, ensure_ascii=False))
if not guard_ok:
    print('FALLA: falta material en la pared del tubo (ver guarda_pared_tubo)', file=sys.stderr)
    sys.exit(1)
