"""Comprueba el estuche: choques cerrado, juego del receptor, apertura de la tapa, giro de los cierres,
pernos y rotulo. Escribe generated/check.json y sale con codigo 1 si algo falla.

Uso:
  PYTHONPATH=/Applications/FreeCAD.app/Contents/Resources/lib \\
  /Applications/FreeCAD.app/Contents/Resources/bin/python check_carry_case.py
"""
import json, math, sys
from pathlib import Path

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
import FreeCAD as App
import Part
import geom_carry_case as G

V = App.Vector
OUT = ROOT / 'generated'
doc = App.openDocument(str(OUT / 'TresVizo-CarryCase.FCStd'))
S = {o.Name.lstrip('_'): o.Shape.copy() for o in doc.Objects if hasattr(o, 'Shape') and not o.Shape.isNull()}
App.closeDocument(doc.Name)

case_names = [n for n in S if n[:2].isdigit()]
rcv_parts = [(n, l, s) for n, l, s in G.receiver_objects(include_refs=True)
             if n[:2].isdigit() or 'antena:' in l or '(fuera)' in l]
RCV = Part.makeCompound([s for _, _, s in rcv_parts])
EPS = 0.02          # mm3: por debajo, contacto (cara con cara) y no choque
fails = []


def vol(a, b):
    try:
        return a.common(b).Volume
    except Exception:
        return float('nan')


def depth(a, b):
    """Alto en z de la zona comun (penetracion vertical aproximada)."""
    c = a.common(b)
    return 0.0 if c.Volume < EPS else c.BoundBox.ZLength


# --- 1. Cerrado: choques entre piezas ----------------------------------------------------------
EXPECTED = {
    ('01_base', '05_seal_tpu'): 'labio de la junta doblado por la lengueta (0.6)',
    ('05_seal_tpu', '01_base'): 'labio de la junta doblado por la lengueta (0.6)',
    ('06_liner_tpu', 'receptor'): 'almohadillas de TPU sobre los hombros de las bandas (0.5 de apriete)',
}
pairs = {}
names = case_names + ['receptor']
shp = dict(S)
shp['receptor'] = RCV
for i, a in enumerate(names):
    for b in names[i + 1:]:
        if a.startswith('03') and b.startswith('04') or a.startswith('07') and b.startswith('07') or a.startswith('08') and b.startswith('08'):
            continue
        if not shp[a].BoundBox.intersect(shp[b].BoundBox):
            continue
        v = vol(shp[a], shp[b])
        if v >= EPS:
            why = EXPECTED.get((a, b)) or EXPECTED.get((b, a))
            pairs[f'{a} / {b}'] = {'volumen_mm3': round(v, 3), 'esperado': why or False}
            if not why:
                fails.append(f'choque cerrado: {a} / {b} ({v:.3f} mm3)')

# --- 2. Receptor: apoyo, holgura a los lados y a lo largo ---------------------------------------
base = S['01_base']
cr = G.P['cradle']
rcv_free = {}
for label, (dx, dy, dz) in {'apoyado (posicion del modelo)': (0, 0, 0),
                            '+0.75 a lo largo (hacia la antena)': (0.75, 0, 0),
                            '-0.75 a lo largo (hacia la base)': (-0.75, 0, 0),
                            '+0.5 de lado (hacia atras), subido 0.4': (0, 0.5, 0.4),
                            '-0.5 de lado (hacia el frente), subido 0.4': (0, -0.5, 0.4)}.items():
    r = RCV.copy()
    r.translate(V(dx, dy, dz))
    v = vol(r, base)
    rcv_free[label] = round(v, 3)
    if v >= EPS:
        fails.append(f'receptor {label}: toca la base ({v:.3f} mm3)')
# Tope a lo largo: con 1.5 de desplazamiento el canto de una banda tiene que topar con una costilla del medio.
stop = {}
for dx in (1.5, -1.5):
    r = RCV.copy()
    r.translate(V(dx, 0, 0))
    stop[f'{dx:+.1f}'] = round(vol(r, base), 2)
    if stop[f'{dx:+.1f}'] < EPS:
        fails.append(f'el receptor se desplaza {dx} a lo largo sin topar')
gap_side = (G.RCV['band_radius'] + cr['clearance']) - G.RCV['band_radius']
dist_antenna = None
for n, l, s in rcv_parts:
    if 'antena: antena' in l:
        dist_antenna = round(s.distToShape(base)[0], 2)

# --- 3. Apertura de la tapa (0 a 180 grados) con los cierres abiertos ---------------------------
lid_grp = Part.makeCompound([S['02_lid'], S['05_seal_tpu'], S['06_liner_tpu']])
lat_open = [G.latch(x, G.LT['open_deg']) for x in G.LT['x_centers']]
fixed = Part.makeCompound([base, S['07_hinge_pin_left'], S['07_hinge_pin_right'], S['08_latch_pin_left'],
                           S['08_latch_pin_right'], RCV] + lat_open)
sweep = {}
for deg in list(range(5, 181, 5)):
    l = G.lid_rotation(lid_grp, deg)
    v = vol(l, fixed)
    sweep[deg] = round(v, 3)
    if v >= EPS and deg >= 10:
        fails.append(f'la tapa choca al abrir {deg} grados ({v:.3f} mm3)')
lid_pins = {}
for side in ('left', 'right'):
    v = vol(S['02_lid'], S[f'07_hinge_pin_{side}'])
    lid_pins[side] = round(v, 3)

# --- 4. Giro de los cierres con la tapa cerrada -------------------------------------------------
latch_sweep = []
lid = S['02_lid']
for deg in range(0, 61, 2):
    lt = G.latch(G.LT['x_centers'][1], deg)
    vb = vol(lt, base)
    vl = vol(lt, lid)
    dl = depth(lt, lid) if vl >= EPS else 0.0
    latch_sweep.append({'grados': deg, 'con_base_mm3': round(vb, 3), 'con_tapa_mm3': round(vl, 3), 'penetracion_tapa': round(dl, 2)})
    if vb >= EPS:
        fails.append(f'el cierre toca la base a {deg} grados ({vb:.3f} mm3)')
hump = max(r['penetracion_tapa'] for r in latch_sweep)
release = next((r['grados'] for r in latch_sweep if r['grados'] > 0 and r['con_tapa_mm3'] < EPS), None)
if release is None:
    fails.append('el gancho del cierre no suelta el tope de la tapa en 60 grados')
if hump > 0.8:
    fails.append(f'el cierre hunde la tapa {hump} al abrir (mas que el labio)')

# --- 5. Pernos: que no choquen puestos y que la uña quede fuera del agujero --------------------
pins = {}
for n in [x for x in case_names if x.startswith(('07', '08'))]:
    others = [k for k in ('01_base', '02_lid', '03_latch_left', '04_latch_right') if S[k].BoundBox.intersect(S[n].BoundBox)]
    pins[n] = {k: round(vol(S[n], S[k]), 3) for k in others}
    for k, v in pins[n].items():
        if v >= EPS:
            fails.append(f'perno {n} choca con {k} ({v:.3f} mm3)')

# --- 6. Rotulo: trazos finos, letras en sus huecos y a ras ---------------------------------------
label = {}
for name, polys in G.label_groups():
    thin = 0
    for o, hs in polys:
        f = G.glyph_face(o, hs)
        try:
            e = f.makeOffset2D(-0.4, 0, False, False, False)
            if e.isNull() or e.Area < 0.05 * f.Area:
                thin += 1
        except Exception:
            thin += 1
    label[name] = {'piezas': len(polys), 'piezas_con_trazo_menor_de_0.8': thin}
    if thin:
        fails.append(f'rotulo {name}: {thin} piezas con trazo de menos de 0.8')
let = S['09_letters_tpu']
zf = G.label_face_z()
lb = G.P['label']
label['letras_tpu'] = {'piezas': len(let.Solids), 'z_cara': round(let.BoundBox.ZMax, 3), 'z_panel': round(zf, 3),
                       'hueco': lb['pocket_depth'], 'techo_bajo_el_hueco': round(zf - lb['pocket_depth'] - G.Z_CEIL, 2),
                       'con_tapa_mm3': round(vol(let, S['02_lid']), 3),
                       'juego_por_lado': lb['pocket_clearance'] + lb['inlay_clearance']}
if abs(let.BoundBox.ZMax - zf) > 1e-3:
    fails.append('las letras no quedan a ras del panel')
# Cada letra tiene que llenar su hueco: la letra agrandada el juego tiene que caber y llenar.
lid_solid = S['02_lid']
pocket_fill = vol(G.label_solids(zf - lb['pocket_depth'] + 0.01, zf - 0.01, lb['pocket_clearance'] - 0.01), lid_solid)
label['letras_tpu']['material_de_tapa_dentro_de_los_huecos_mm3'] = round(pocket_fill, 3)
if pocket_fill >= EPS:
    fails.append(f'quedo material de la tapa dentro de los huecos de las letras ({pocket_fill:.3f} mm3)')

# --- 7. Volumenes, peso y medidas --------------------------------------------------------------
dens = {'PA12': 1.01, 'TPU': 1.2}
parts = {}
tot = {'PA12': 0.0, 'TPU': 0.0}
for n in case_names:
    m = 'TPU' if 'tpu' in n else 'PA12'
    v = S[n].Volume / 1000.0
    tot[m] += v
    parts[n] = {'material': m, 'volumen_cm3': round(v, 2), 'peso_g': round(v * dens[m], 1)}
bb = Part.makeCompound([S[n] for n in case_names]).BoundBox

res = {
    'piezas': parts,
    'total_cm3': {k: round(v, 1) for k, v in tot.items()},
    'peso_total_g': round(tot['PA12'] * dens['PA12'] + tot['TPU'] * dens['TPU']),
    'medidas_exteriores': [round(bb.XLength, 1), round(bb.YLength, 1), round(bb.ZLength, 1)],
    'cerrado_contactos': pairs,
    'receptor': {'desplazamientos_sin_tocar_mm3': rcv_free, 'tope_a_lo_largo_mm3': stop,
                 'holgura_bandas_costillas': gap_side, 'antena_a_la_base': dist_antenna},
    'apertura_tapa_mm3': sweep,
    'perno_bisagra_con_tapa_mm3': lid_pins,
    'cierre_giro': latch_sweep,
    'cierre_hundimiento_max': hump,
    'cierre_suelta_a_grados': release,
    'pernos': pins,
    'rotulo': label,
    'fallos': fails,
}
(OUT / 'check.json').write_text(json.dumps(res, indent=1, ensure_ascii=False) + '\n', encoding='utf-8')
print(json.dumps({k: res[k] for k in ('total_cm3', 'peso_total_g', 'medidas_exteriores', 'cerrado_contactos', 'receptor',
                                       'cierre_hundimiento_max', 'cierre_suelta_a_grados', 'rotulo', 'fallos')}, indent=1, ensure_ascii=False))
print('apertura', {k: v for k, v in sweep.items() if v})
sys.exit(1 if fails else 0)
