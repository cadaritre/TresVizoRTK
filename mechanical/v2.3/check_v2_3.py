"""Comprueba V2.3 contra la placa principal v0.2 real (STEP con sus componentes),
las clavijas enchufadas, la placa panel-usb y las envolventes supuestas de la
carrier BDLX, la 18650 y el coaxial (hardware/main-board/cad/).

Mide:
  - choques entre piezas impresas (en su posicion final) y con cada referencia;
  - que el chasis armado (chasis + placa + carrier) pase el collar Ø52;
  - que no haya plastico del chasis junto a la antena del ESP32;
  - holguras minimas de las parejas que importan.

Uso:
  PYTHONPATH=<freecad>/lib <freecad>/bin/python check_v2_3.py [--output-dir generated]
Escribe <output-dir>/check.json. NO es una validacion: nada se ha impreso.
"""
import argparse, json, math
from pathlib import Path

import FreeCAD as App
import Part, Import

ROOT = Path(__file__).resolve().parent
CAD = ROOT.parent.parent / 'hardware' / 'main-board' / 'cad'
ap = argparse.ArgumentParser()
ap.add_argument('--output-dir', type=Path, default=ROOT / 'generated')
args, _ = ap.parse_known_args()
OUT = args.output_dir.resolve()
P = json.loads((ROOT / 'parameters.json').read_text(encoding='utf-8'))
CH = P['chasis']

doc = App.openDocument(str(OUT / 'TresVizo-V2.3.FCStd'))
parts = {o.Name.lstrip('_').replace('_', '-'): o.Shape for o in doc.Objects
         if hasattr(o, 'Shape') and not o.Shape.isNull() and not o.Name.startswith('ref_')}


def load_step(name):
    """Une todos los solidos de un STEP en un compuesto, con sus etiquetas."""
    path = CAD / name
    if not path.exists():
        return {}
    d = App.newDocument('tmp_' + name.split('.')[0].replace('-', '_'))
    Import.insert(str(path), d.Name)
    out = {}
    for o in d.Objects:
        if hasattr(o, 'Shape') and not o.Shape.isNull() and o.Shape.Solids:
            sh = o.Shape.copy()
            out[o.Label] = sh
    return out


refs = {}
board = load_step('placa-principal.step')
plugs = load_step('clavijas.step')
pusb = load_step('panel-usb.step')
env = load_step('envolventes-supuestas.step')
# Los objetos 'v02b_check' son los grupos que contienen todo: se ignoran. La
# carrier y su clavija SMA van donde las deja el chasis (su posicion la fija el
# chasis): la envolvente de hardware/main-board/cad se sube 1.6 mm, a donde la
# ponen los pisos del chasis. Los compuestos que agrupan varias piezas se ignoran.
for group, dct in (('placa', board), ('clavija', plugs), ('panel_usb', pusb), ('supuesto', env)):
    for k, v in dct.items():
        if 'v02b' in k or 'export_tmp' in k or len(v.Solids) > 1 and group == 'supuesto':
            continue
        lk = k.lower()
        if group == 'supuesto' and ('battery' in lk or 'pusb_heads' in lk or 'carrier' in lk):
            continue   # la 18650 y la carrier (medida, con su SMA y sus patas) se toman de este modelo; la panel-usb ya no lleva tornillos
        v = v.copy()
        if group in ('placa', 'clavija'):
            # La placa va CH['desplazamiento_placa_y'] mas hacia el panel que en cad/.
            v.translate(App.Vector(0, CH.get('desplazamiento_placa_y', 0.0), 0))
        if group == 'supuesto' and 'carrier' in lk:
            # La carrier y su clavija SMA van donde las pone el chasis (el coaxial se
            # deja como en cad/: es flexible y su recorrido se ajusta al montar).
            v.translate(App.Vector(0, CH['carrier']['y'][0] + 9.9, CH['carrier']['z'][0] - 16.4))
        refs[f'{group}:{k}'] = v
for o in doc.Objects:
    if o.Name in ('ref_battery', 'ref_button', 'ref_oled', 'ref_nut_keepers', 'ref_carrier'):
        refs['v23:' + o.Name] = o.Shape

print('referencias:', len(refs), {g: len(d) for g, d in (('placa', board), ('clavija', plugs), ('panel_usb', pusb), ('supuesto', env))})

LIM = 0.05  # mm3
report = {'choques_piezas': [], 'choques_referencias': [], 'holguras': {}}

names = sorted(parts)
for i, a in enumerate(names):
    for b in names[i + 1:]:
        if 'bumper' in a or 'bumper' in b:
            continue
        c = parts[a].common(parts[b])
        v = c.Volume if c.Solids else 0.0
        if v > 1.0:
            report['choques_piezas'].append({'a': a, 'b': b, 'mm3': round(v, 2)})

# Piezas impresas contra referencias. Las bandas de TPU no cuentan.
for pn in names:
    if 'bumper' in pn:
        continue
    pbb = parts[pn].BoundBox
    for rn, rs in refs.items():
        if not pbb.intersect(rs.BoundBox):
            continue
        try:
            c = parts[pn].common(rs)
            v = c.Volume if c.Solids else 0.0
        except Exception as e:
            v = -1
        if v > LIM or v < 0:
            report['choques_referencias'].append({'pieza': pn, 'ref': rn, 'mm3': round(v, 3)})

# Referencias entre si (placa contra carrier, clavijas contra carrier, etc.)
keys = sorted(refs)
rr = []
for i, a in enumerate(keys):
    for b in keys[i + 1:]:
        ga, gb = a.split(':')[0], b.split(':')[0]
        if ga == gb == 'placa' or ga == gb == 'v23':
            continue
        if not refs[a].BoundBox.intersect(refs[b].BoundBox):
            continue
        try:
            c = refs[a].common(refs[b])
            v = c.Volume if c.Solids else 0.0
        except Exception:
            v = -1
        if v > LIM:
            rr.append({'a': a, 'b': b, 'mm3': round(v, 3)})
report['choques_entre_referencias'] = rr

# Collar: chasis + placa + carrier deben caber en r 26 - 0.35.
r_lim = 26.0 - 0.35
ring = Part.makeCylinder(60, 300, App.Vector(0, 0, -50)).cut(Part.makeCylinder(r_lim, 300, App.Vector(0, 0, -50)))
over = []
assembly = [('sled', parts['08-sled'])] + [(k, v) for k, v in refs.items()
                                           if k.startswith('placa:') or 'carrier' in k.lower() or 'sma' in k.lower()]
rmax = 0.0
for k, sh in assembly:
    for vtx in sh.Vertexes:
        rmax = max(rmax, math.hypot(vtx.X, vtx.Y))
    c = sh.common(ring)
    if c.Solids and c.Volume > 0.01:
        over.append({'objeto': k, 'mm3_fuera': round(c.Volume, 3)})
report['collar'] = {'radio_limite': r_lim, 'radio_max_vertices': round(rmax, 3), 'fuera': over}

# Antena del ESP32: nada del chasis en la zona de chasis.antena_esp32 (y su prolongacion hasta el riel), y -6..12.
_az = CH.get('antena_esp32', {'x': [16.8, 23.0], 'z': [54.2, 70.2]})
ant = Part.makeBox(26.0 - _az['x'][0], 18, _az['z'][1] - _az['z'][0], App.Vector(_az['x'][0], -6, _az['z'][0]))
c = parts['08-sled'].common(ant)
report['antena_plastico_mm3'] = round(c.Volume, 3) if c.Solids else 0.0

# Holguras minimas.
def gap(a, b):
    try:
        return round(a.distToShape(b)[0], 3)
    except Exception:
        return None

sled = parts['08-sled']
tube = parts['02-logo-tube']
pairs = {
    'chasis-tubo': (sled, tube),
    'chasis-tapa': (sled, parts['03-antenna-cap']),
    'chasis-plataforma': (sled, parts['04-imu-platform']),
    'chasis-base': (sled, parts['01-threaded-base']),
}
for k, v in refs.items():
    lk = k.lower()
    if 'battery' in lk or 'bater' in lk or '18650' in lk:
        pairs['chasis-18650'] = (sled, v)
        pairs['tubo-18650'] = (tube, v)
    if lk.endswith(':carrier') or lk.endswith('ref_carrier'):
        pairs['chasis-carrier'] = (sled, v)
        pairs['carrier-18650'] = (v, refs.get('v23:ref_battery'))
        pairs['placa-carrier'] = (v, next((s for n, s in refs.items() if n.startswith('placa:') and 'PCB' in n), None))
    if 'sma' in lk:
        pairs['chasis-clavija_sma'] = (sled, v)
    if 'coax' in lk:
        pairs['chasis-coaxial'] = (sled, v)
for k, (a, b) in pairs.items():
    report['holguras'][k] = gap(a, b)

(OUT / 'check.json').write_text(json.dumps(report, indent=1, ensure_ascii=False), encoding='utf-8')
print(json.dumps(report, indent=1, ensure_ascii=False))
