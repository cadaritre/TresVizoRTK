"""Regenera el Meridian3 completo y lo comprueba. Localiza FreeCAD solo.

Uso:
  python3 regenerate.py [--freecad <ruta a su python>] [--dxf <logo.dxf>]

Orden: pila de alturas, logo, tornilleria, piezas, exportacion (mallas e
interferencias), comprobaciones de capacidad y bayoneta, y cortes en PNG.
Sale con codigo distinto de cero si algo falla.
"""
import argparse, json, os, pathlib, shutil, subprocess, sys

ROOT = pathlib.Path(__file__).resolve().parent

CANDIDATES = [
    'C:/Program Files/FreeCAD 1.1/bin/python.exe',
    'C:/Program Files/FreeCAD 1.0/bin/python.exe',
    'C:/Program Files/FreeCAD/bin/python.exe',
    '/Applications/FreeCAD.app/Contents/Resources/bin/python',
    '/Applications/FreeCAD.app/Contents/Resources/bin/freecadcmd',
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
    subprocess.run([sys.executable, str(ROOT / 'dxf_logo.py'), str(args.dxf)], check=True)
elif not (ROOT / 'logo.json').exists():
    sys.exit('Falta logo.json. Pasa --dxf con el logo vectorial.')

for script in ('stack.py', 'layout_check.py', 'bom.py'):
    print(f'\n--- {script} ---')
    subprocess.run([sys.executable, str(ROOT / script)], check=True)

# El python de FreeCAD en macOS no encuentra sus modulos sin PYTHONPATH a su lib.
env = dict(os.environ)
lib = freecad.resolve().parent.parent / 'lib'
if freecad.name.startswith('python') and (lib / 'FreeCAD.so').exists():
    env['PYTHONPATH'] = str(lib) + os.pathsep + env.get('PYTHONPATH', '')

cap_ok = True
for script in ('build_meridian3.py', 'export_meridian3.py', 'capacity_check.py', 'sections.py'):
    print(f'\n--- {script} ---')
    r = subprocess.run([str(freecad), str(ROOT / script)], env=env)
    if script == 'capacity_check.py':
        cap_ok = r.returncode == 0
    elif r.returncode != 0:
        sys.exit(f'{script} fallo')

gen = ROOT / 'generated'
exports = json.loads((gen / 'exports.json').read_text(encoding='utf-8'))
index = json.loads((gen / 'model-index.json').read_text(encoding='utf-8'))
cap = json.loads((gen / 'capacity.json').read_text(encoding='utf-8'))
solidos_ok = all(p['solidos'] == 1 and p['valido'] for p in index['piezas'])
listo = exports['todas_cerradas'] and exports['sin_interferencias'] and solidos_ok and cap_ok
print(f"\naltura {index['altura_total_mm']} mm   diametro {index['diametro_exterior_mm']} mm"
      f"   material {index['volumen_total_cm3']} cm3")
print('un solido por pieza :', solidos_ok)
print('mallas cerradas     :', exports['todas_cerradas'])
print('sin interferencias  :', exports['sin_interferencias'])
print('cabe y bayoneta     :', cap['cabe_todo'], cap['fallos'] or '')
print('\nGEOMETRIA COHERENTE:', 'SI' if listo else 'NO')
print('Esto NO significa validado: nada se ha impreso ni montado.')
sys.exit(0 if listo else 1)
