"""Comprueba lo que la geometria de V2.1 promete sobre el trineo y los tornillos.

1. Paso libre: todo el trineo debe caber en el radio del collar de bayoneta,
   porque el tubo baja por encima de el al montar.
2. Bateria 955565 y carrier UM980 en su sitio: que quepan por el collar y que
   no choquen con el trineo. Se prueban la cota nominal y el peor caso
   documentado, no una envolvente inventada.
3. Centrado: la repisa del IMU debe llegar al taladro del cuello de la tapa
   (a la holgura pedida) en un arco de mas de 180 grados, y el cuello debe
   bajar hasta rodearla.
4. Rigidez frente a V2: inercia de la seccion entre filas de ranuras y en una
   fila, y rigidez de punta de la placa en voladizo (I / L^3), que es la que se
   notaba en la mano. Cuentas sobre el CAD, no un ensayo.
5. Seguros: con el modelo cerrado, un tornillo recto debe atravesar el paso del
   tubo y entrar en el piloto de la base o de la tapa sin tocar pared, y su
   rosca debe morder plastico.
6. Paredes entre tornillos: entre las crestas de rosca de los tornillos que
   forman rosca en la base, y entre ellas y los huecos del inserto, al menos
   PARED_MIN.
7. Tornillos de los paneles: la punta no debe llegar a menos de 0.5 mm de la
   bateria (panel auxiliar) ni del carrier UM980 (panel principal).
8. Sitio sobre el IMU para el conector del coaxial de la antena.

Sale con codigo distinto de cero si algo falla.

Uso: <python de FreeCAD> capacity_check.py
"""
import json, math, sys
from pathlib import Path

import FreeCAD as App
import Part

ROOT = Path(__file__).resolve().parent
P = json.loads((ROOT / 'parameters.json').read_text(encoding='utf-8'))
C = json.loads((ROOT / 'components.json').read_text(encoding='utf-8'))
INDEX = json.loads((ROOT / 'generated' / 'model-index.json').read_text(encoding='utf-8'))
V = App.Vector

PARED_MIN = 1.2          # mm entre crestas de rosca o hasta un hueco
SMA_ACODADO_ALTO = 15.0  # mm que ocupa bajo la tapa un SMA macho acodado con su cable

RO = P['tubo']['diametro_exterior'] / 2
RI = RO - P['tubo']['pared']
R_COLLAR = RI - P['bayoneta']['collar_espesor']
R_SPIGOT = R_COLLAR - P['impresion']['holgura_general']
NECK_RI = R_SPIGOT - P['tubo']['pared']
S = P['trineo']
H = INDEX['plano_alturas']
Z_FLOOR = H['piso_interior']
Z_BATT_TOP = Z_FLOOR + S['zona_bateria']
y0 = S['desplazamiento_y'] - S['espesor'] / 2
y1 = S['desplazamiento_y'] + S['espesor'] / 2
z_base = Z_FLOOR + S['pie']['espesor']


def piece(name):
    return Part.read(str(ROOT / 'generated' / 'step' / f'{name}.step'))


sled = piece('04-universal-sled')
tube = piece('02-logo-tube')
base = piece('01-threaded-base')
cap = piece('03-antenna-cap')


def max_radius(shape):
    pts = []
    for e in shape.Edges:
        pts += e.discretize(Deflection=0.02)
    return max(math.hypot(p.x, p.y) for p in pts)


def corner_radius(box):
    bb = box.BoundBox
    return max(math.hypot(x, y) for x in (bb.XMin, bb.XMax) for y in (bb.YMin, bb.YMax))


fallos = []
res = {'radio_collar_mm': round(R_COLLAR, 2)}

# --- 1. Paso libre ------------------------------------------------------------
r_sled = max_radius(sled)
res['trineo_radio_max_mm'] = round(r_sled, 2)
res['trineo_holgura_collar_mm'] = round(R_COLLAR - r_sled, 2)
if r_sled >= R_COLLAR:
    fallos.append('el trineo no pasa por el collar')

# --- 2. Bateria y carrier -------------------------------------------------------
bat = C['bateria']
z_bat = z_base + S['cartelas']['alto'] + 0.5
res['bateria'] = {}
bat_boxes = {}
for caso, dims in (('nominal', bat['publicado']), ('peor_caso', bat['peor_caso_documentado'])):
    esp, ancho, largo = dims
    box = Part.makeBox(ancho, esp, largo, V(-ancho / 2, y0 - esp - 0.05, z_bat))
    bat_boxes[caso] = box
    choque = box.common(sled).Volume
    r = corner_radius(box)
    arriba = z_bat + largo
    ok = r < R_COLLAR and choque < 0.01 and arriba <= Z_BATT_TOP
    res['bateria'][caso] = {
        'cota_mm': dims, 'radio_esquina_mm': round(r, 2),
        'holgura_collar_mm': round(R_COLLAR - r, 2),
        'choque_con_trineo_mm3': round(choque, 2),
        'z_mm': [round(z_bat, 1), round(arriba, 1)],
        'cabe': ok,
    }
    if not ok:
        fallos.append(f'bateria {caso} no cabe')
env = bat['envolvente_diseno']
res['bateria']['envolvente_diseno'] = {
    'cota_mm': env,
    'radio_esquina_si_centrada_mm': round(math.hypot(env[1] / 2, env[0] / 2), 2),
    'nota': 'Informativa: la envolvente con margen de hinchazon no pasa por el collar.',
}

um = C['carrier_um980']['publicado']            # espesor, ancho, largo
w_in = S['alas']['x_exterior'] - S['alas']['espesor']
um_box = Part.makeBox(um[1], um[0], um[2], V(-um[1] / 2, y1 + 0.05, z_bat))
choque = um_box.common(sled).Volume
r = corner_radius(um_box)
ok = r < R_COLLAR and choque < 0.01 and z_bat + um[2] <= Z_BATT_TOP
res['carrier_um980'] = {
    'cota_mm': um, 'hueco_entre_alas_mm': round(2 * w_in, 1),
    'radio_esquina_mm': round(r, 2), 'holgura_collar_mm': round(R_COLLAR - r, 2),
    'choque_con_trineo_mm3': round(choque, 2), 'cabe': ok,
}
if not ok:
    fallos.append('carrier UM980 no cabe')

# --- 3. Centrado de la repisa en el cuello -----------------------------------
z_shelf = H['repisa_imu'] + P['imu']['espesor_repisa'] / 2
r_target = NECK_RI - P['imu']['holgura_cuello']
cut = sled.slice(V(0, 0, 1), z_shelf)
pts = []
for w in cut:
    pts += w.discretize(Distance=0.2)
bins = set()
for p in pts:
    if math.hypot(p.x, p.y) >= r_target - 0.1:
        bins.add(int(math.degrees(math.atan2(p.y, p.x)) % 360) // 2)
covered = sorted(bins)
gaps = [((covered[(i + 1) % len(covered)] - covered[i]) % 180) * 2 for i in range(len(covered))] if covered else [360]
max_gap = max(gaps) if covered else 360
neck_ok = H['fondo_cuello_tapa'] <= H['repisa_imu']
centrado_ok = covered and max_gap < 180 and neck_ok
res['centrado'] = {
    'radio_repisa_mm': round(max(math.hypot(p.x, p.y) for p in pts), 2),
    'radio_taladro_cuello_mm': round(NECK_RI, 2),
    'holgura_radial_mm': round(NECK_RI - max(math.hypot(p.x, p.y) for p in pts), 2),
    'arco_en_contacto_grados': len(covered) * 2,
    'mayor_hueco_grados': max_gap,
    'cuello_baja_hasta_la_repisa': neck_ok,
    'centra': bool(centrado_ok),
}
if not centrado_ok:
    fallos.append('la repisa del IMU no queda centrada por el cuello')

# --- 4. Rigidez ---------------------------------------------------------------
def section_inertia(shape, z):
    faces = [Part.Face(w) for w in shape.slice(V(0, 0, 1), z) if w.isClosed()]
    area = sum(f.Area for f in faces)
    yc = sum(f.CenterOfMass.y * f.Area for f in faces) / area
    return sum(f.MatrixOfInertia.A11 + f.Area * (f.CenterOfMass.y - yc) ** 2 for f in faces)


grid = P['rejilla_anclaje']
row0 = z_base + grid.get('inicio', grid['paso_longitudinal'])
mid = (Z_FLOOR + Z_BATT_TOP) / 2
k = round((mid - row0) / grid['paso_longitudinal'])
z_row = row0 + k * grid['paso_longitudinal']
z_gap = z_row + grid['paso_longitudinal'] / 2
i_gap, i_row = section_inertia(sled, z_gap), section_inertia(sled, z_row)
L21 = Z_BATT_TOP - Z_FLOOR
res['rigidez'] = {'v2_1': {'largo_placa_mm': round(L21, 1),
                           'inercia_entre_filas_mm4': round(i_gap), 'inercia_en_fila_mm4': round(i_row),
                           'z_mm': [round(z_row, 1), round(z_gap, 1)]}}
v2_step = ROOT.parent / 'v2' / 'generated' / 'step' / '04-trineo-universal.step'
if v2_step.exists():
    old = Part.read(str(v2_step))
    ip2 = json.loads((ROOT.parent / 'v2' / 'parameters.json').read_text(encoding='utf-8'))
    ix2 = json.loads((ROOT.parent / 'v2' / 'generated' / 'model-index.json').read_text(encoding='utf-8'))
    zf2 = ix2['plano_alturas']['piso_interior']
    L2 = ip2['trineo']['zona_bateria']
    g2 = ip2['rejilla_anclaje']['paso_longitudinal']
    mid2 = zf2 + L2 / 2
    z_row2 = zf2 + g2 * round((mid2 - zf2) / g2)
    i2_gap, i2_row = section_inertia(old, z_row2 + g2 / 2), section_inertia(old, z_row2)
    res['rigidez']['v2'] = {'largo_placa_mm': L2, 'inercia_entre_filas_mm4': round(i2_gap),
                            'inercia_en_fila_mm4': round(i2_row)}
    f_sec = (i_gap / i2_gap, i_row / i2_row)
    f_tip = tuple(f * (L2 / L21) ** 3 for f in f_sec)
    res['rigidez']['factor_seccion'] = [round(min(f_sec), 1), round(max(f_sec), 1)]
    res['rigidez']['factor_punta_en_voladizo'] = [round(min(f_tip), 1), round(max(f_tip), 1)]
    res['rigidez']['nota'] = ('Flexion fuera del plano de la placa. factor_punta compara la placa como '
                              'voladizo libre (I/L^3, mismo material). En V2.1, con la tapa puesta, el '
                              'cuello sujeta ademas el extremo superior.')

# --- 5. Seguros -----------------------------------------------------------------
seg = P['seguro']
a = math.radians(seg['angulo'])
ux, uy = math.cos(a), math.sin(a)


def rod(radius, depth, z, start=RO + 2):
    return Part.makeCylinder(radius, depth, V(ux * start, uy * start, z), V(-ux, -uy, 0))


res['seguros'] = {}
for nombre, part, z, fondo in (('base', base, H['seguro_base'], seg['profundidad_base']),
                               ('tapa', cap, H['seguro_tapa'], seg['profundidad_tapa'])):
    nucleo = rod(seg['piloto'] / 2 - 0.1, fondo - 0.5, z)
    choque = nucleo.common(tube).Volume + nucleo.common(part).Volume
    rosca = rod(1.5, fondo - 0.5, z).common(part).Volume
    ok = choque < 0.05 and rosca > 5.0
    res['seguros'][nombre] = {'angulo': seg['angulo'], 'z_mm': z,
                              'choque_del_nucleo_mm3': round(choque, 2),
                              'plastico_para_la_rosca_mm3': round(rosca, 1),
                              'alineado': ok}
    if not ok:
        fallos.append(f'seguro de la {nombre} desalineado o sin rosca')

# --- 6. Paredes entre tornillos de la base ------------------------------------
screws = json.loads((ROOT / 'generated' / 'screws.json').read_text(encoding='utf-8'))
ins = P['inserto_jalon']
pocket = Part.makeCylinder(ins['brida_diametro'] / 2 + ins['holgura'] / 2, ins['brida_espesor'] + 0.1,
                           V(0, 0, ins['barril_altura']))
barrel = Part.makeCylinder(ins['barril_diametro'] / 2 + ins['holgura'] / 2, ins['barril_altura'] + 0.2,
                           V(0, 0, -0.1))
stud = Part.makeCylinder(ins['paso_libre_macho_radio'], Z_FLOOR + 1, V(0, 0, ins['barril_altura']))
cavidades = {'alojamiento_brida': pocket, 'barril': barrel, 'paso_esparrago': stud}
crestas = {}
pie = S['pie']
for i, (fx, fy) in enumerate(pie['tornillos']):
    largo = screws['pie']
    crestas[f'pie_{i}'] = Part.makeCylinder(1.5, largo - pie['espesor'],
                                            V(fx, fy, Z_FLOOR - (largo - pie['espesor'])))
seat = RO - seg['cabeza_profundidad']
crestas['seguro_base'] = rod(1.5, screws['seguro_base'], H['seguro_base'], seat)
paredes = {}
names = list(crestas)
for i, na in enumerate(names):
    for nb in names[i + 1:]:
        paredes[f'{na}-{nb}'] = crestas[na].distToShape(crestas[nb])[0]
    for nc, cav in cavidades.items():
        paredes[f'{na}-{nc}'] = crestas[na].distToShape(cav)[0]
res['paredes_mm'] = {k: round(v, 2) for k, v in paredes.items()}
for k, v in paredes.items():
    if v < PARED_MIN:
        fallos.append(f'pared de {v:.2f} mm entre {k}')

# --- 7. Tornillos de los paneles contra lo que hay detras ------------------------
res['tornillos_panel'] = {}
for clave, obstaculo, nombre in (('panel_aux', bat_boxes['peor_caso'], 'bateria'),
                                 ('panel', um_box, 'carrier UM980')):
    cfg = P[clave]
    largo = screws[clave]
    ang = math.radians(cfg['angulo'])
    vx, vy = math.cos(ang), math.sin(ang)
    seat_p = RO - cfg.get('cabeza_profundidad', 1.6)
    peor = 99.0
    for dz in (-cfg['tornillo_separacion_z'] / 2, cfg['tornillo_separacion_z'] / 2):
        body = Part.makeCylinder(1.5, largo, V(vx * seat_p, vy * seat_p, cfg['z_centro'] + dz),
                                 V(-vx, -vy, 0))
        peor = min(peor, body.distToShape(obstaculo)[0])
    res['tornillos_panel'][clave] = {'largo_mm': largo, 'obstaculo': nombre,
                                     'distancia_punta_mm': round(peor, 2)}
    if peor < 0.5:
        fallos.append(f'el tornillo del {clave} llega a {peor:.2f} mm de la {nombre}')

# --- 8. Sitio sobre el IMU ------------------------------------------------------
imu = P['imu']
imu_top = H['repisa_imu'] + imu['espesor_repisa'] + imu['pcb_separadores'] + 1.6 + 1.5
libre = H['borde_superior_tubo'] - imu_top
res['sobre_imu'] = {'cara_inferior_tapa_mm': H['borde_superior_tubo'],
                    'cima_imu_estimada_mm': round(imu_top, 1),
                    'libre_mm': round(libre, 1),
                    'pide_sma_acodado_mm': SMA_ACODADO_ALTO}
if libre < SMA_ACODADO_ALTO:
    fallos.append('no cabe el conector del coaxial sobre el IMU')

res['cabe_todo'] = not fallos
res['fallos'] = fallos
out = ROOT / 'generated' / 'capacity.json'
out.write_text(json.dumps(res, indent=1, ensure_ascii=False), encoding='utf-8')
print(json.dumps(res, indent=1, ensure_ascii=False))
sys.exit(1 if fallos else 0)
