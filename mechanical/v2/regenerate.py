"""Regenera V2 completa. Portable: localiza FreeCAD en vez de tener su ruta
quemada, que es lo que impide hoy regenerar V1 fuera de la maquina del autor.

Uso:
  python regenerate.py [--freecad <ruta a su python>] [--dxf <logo.dxf>]
"""
import argparse, os, pathlib, shutil, subprocess, sys

ROOT = pathlib.Path(__file__).resolve().parent

CANDIDATES = [
    'C:/Program Files/FreeCAD 1.1/bin/python.exe',
    'C:/Program Files/FreeCAD 1.0/bin/python.exe',
    'C:/Program Files/FreeCAD/bin/python.exe',
    '/Applications/FreeCAD.app/Contents/Resources/bin/python',
    '~/Applications/FreeCAD-1.0.2.app/Contents/Resources/bin/python',
    '/usr/lib/freecad/bin/python',
    '/usr/bin/freecadcmd',
]


def find_freecad(explicit):
    if explicit:
        return pathlib.Path(explicit)
    for name in ('freecadcmd', 'FreeCADCmd'):
        found = shutil.which(name)
        if found:
            return pathlib.Path(found)
    for candidate in CANDIDATES:
        path = pathlib.Path(os.path.expanduser(candidate))
        if path.exists():
            return path
    for base in (pathlib.Path('C:/Program Files'), pathlib.Path('C:/Program Files (x86)')):
        if base.exists():
            for folder in sorted(base.glob('FreeCAD*'), reverse=True):
                python = folder / 'bin' / 'python.exe'
                if python.exists():
                    return python
    return None


ap = argparse.ArgumentParser(description=__doc__)
ap.add_argument('--freecad', help='python de FreeCAD; se busca solo si se omite')
ap.add_argument('--dxf', type=pathlib.Path, help='logo vectorial; si se omite se conserva logo.json')
args = ap.parse_args()

freecad = find_freecad(args.freecad)
if not freecad:
    sys.exit('No se encontro FreeCAD. Indicalo con --freecad <ruta a su python>.')
print('FreeCAD:', freecad)

if args.dxf:
    # El trazado del logo no necesita FreeCAD: solo numpy.
    subprocess.run([sys.executable, str(ROOT / 'dxf_logo.py'), str(args.dxf)], check=True)
elif not (ROOT / 'logo.json').exists():
    sys.exit('Falta logo.json. Pasa --dxf con el logo vectorial.')

# Reparto angular: detecta solapes y recoloca el logo en el hueco libre. No
# necesita FreeCAD.
print('\n--- layout_check.py ---')
subprocess.run([sys.executable, str(ROOT / 'layout_check.py')], check=True)

for script in ('build_v2.py', 'export_v2.py'):
    print(f'\n--- {script} ---')
    subprocess.run([str(freecad), str(ROOT / script)], check=True)

import json
exports = json.loads((ROOT / 'generated' / 'exports.json').read_text(encoding='utf-8'))
index = json.loads((ROOT / 'generated' / 'model-index.json').read_text(encoding='utf-8'))
solidos_ok = all(p['solidos'] == 1 and p['valido'] for p in index['piezas'])
listo = exports['todas_cerradas'] and exports['sin_interferencias'] and solidos_ok
print(f"\naltura {index['altura_total_mm']} mm   diametro {index['diametro_exterior_mm']} mm"
      f"   material {index['volumen_total_cm3']} cm3")
print('un solido por pieza :', solidos_ok)
print('mallas cerradas     :', exports['todas_cerradas'])
print('sin interferencias  :', exports['sin_interferencias'])
print('\nGEOMETRIA COHERENTE:', 'SI' if listo else 'NO')
print('Esto NO significa validado: nada se ha impreso ni ensayado.')
sys.exit(0 if listo else 1)
