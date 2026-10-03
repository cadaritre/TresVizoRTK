"""Comprueba lo que la geometria de V2.2 promete.

1. Paquete: bateria del peor caso, carrier UM980 y Thing Plus contra el
   respaldo, sin tocar el tubo; la brida que rodea la bateria no llega a la
   pared, y cada componente pasa por el collar al meterlo centrado.
2. Respaldo: detras de cada ranura hay hueco para que pase la brida.
3. Montaje de los paneles: cada tapa, con lo que lleva montado (pantalla con
   sus Dupont, boton con tuerca y cables), entra radialmente por su ventana sin
   tocar el tubo.
4. Pantalla: piel minima de la tapa sobre el bolsillo del vidrio y sobre los
   pilotos; ventana centrada en el area activa.
5. Boton: espesor del panel en su eje, con junta, frente al maximo que admite
   el boton mas restrictivo, y distancia de su parte trasera al paquete.
6. IMU: los pilotos donde tienen que estar los agujeros para que el chip caiga
   en el eje, a menos de 0.2 mm (calculado de las cotas del chip, no de la
   geometria construida; un error de 0.25 ya falla),
   sitio libre para la mayor placa publicada y sitio para el SMA acodado.
7. Plataforma: cada una cae en su ventana, solo hay una orientacion posible, y
   la flexion de la lengueta es razonable.
8. Seguros: con el modelo cerrado, un tornillo recto atraviesa el paso del tubo
   y entra en el piloto de la base o de la tapa sin tocar pared, y su rosca
   muerde plastico.
9. Paredes: entre la cresta del seguro de la base y los huecos del inserto, al
   menos PARED_MIN.
10. Tornillos de los paneles: la punta no llega a menos de 0.5 mm del cuello de
    la tapa ni del paquete.

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
BRIDA_ESPESOR = 1.1      # mm de una brida de 3.6 mm
PIEL_MIN = 0.8           # mm de tapa sobre un bolsillo o un piloto ciego
FLEXION_MAX = 0.02       # deformacion maxima de la lengueta al entrar
PASO_TORNILLO = 0.5      # mm minimos de la punta de un tornillo a lo que tenga detras

RO = P['tubo']['diametro_exterior'] / 2
RI = RO - P['tubo']['pared']
R_COLLAR = RI - P['bayoneta']['collar_espesor']
R_SPIGOT = R_COLLAR - P['impresion']['holgura_general']
NECK_RI = R_SPIGOT - P['tubo']['pared']
H = INDEX['plano_alturas']

doc = App.openDocument(str(ROOT / 'generated' / 'TresVizo-V2.2.FCStd'))
OBJ = {o.Name.lstrip('_'): o.Shape for o in doc.Objects if hasattr(o, 'Shape')}
base = OBJ['01_threaded_base']
tube = OBJ['02_logo_tube']
cap = OBJ['03_antenna_cap']
plat = OBJ['04_imu_platform']
cover = OBJ['05_panel_cover']
aux = OBJ['06_aux_panel_cover']


def corner_radius(shape):
    bb = shape.BoundBox
    return max(math.hypot(x, y) for x in (bb.XMin, bb.XMax) for y in (bb.YMin, bb.YMax))


def common_mm3(a, b):
    c = a.common(b)
    return c.Volume if c.Solids else 0.0


fallos = []
res = {'radio_collar_mm': round(R_COLLAR, 2), 'radio_interior_mm': round(RI, 2)}

# --- 1. Paquete -----------------------------------------------------------------
res['paquete'] = {}
for nombre in ('ref_battery', 'ref_um980', 'ref_thing_plus'):
    shape = OBJ[nombre]
    choque = common_mm3(shape, tube)
    r = corner_radius(shape)
    bb = shape.BoundBox
    centrado = math.hypot(bb.XLength / 2, bb.YLength / 2)
    ok = choque < 0.01 and r < RI and centrado < R_COLLAR
    res['paquete'][nombre] = {'radio_esquina_mm': round(r, 2),
                              'choque_con_tubo_mm3': round(choque, 2),
                              'radio_esquina_centrado_mm': round(centrado, 2),
                              'pasa_por_el_collar': centrado < R_COLLAR,
                              'cabe': ok}
    if not ok:
        fallos.append(f'{nombre} no cabe o no pasa por el collar')
bat = OBJ['ref_battery'].BoundBox
r_brida = math.hypot(bat.XMax + BRIDA_ESPESOR, -P['respaldo']['plano_frontal'] - 0.5)
res['paquete']['brida_en_la_esquina_de_la_bateria'] = {
    'radio_mm': round(r_brida, 2), 'holgura_a_pared_mm': round(RI - r_brida, 2)}
if RI - r_brida < 0.3:
    fallos.append('la brida que rodea la bateria toca la pared')

# --- 2. Respaldo: hueco detras de cada ranura ------------------------------------
b = P['respaldo']
yb = -b['plano_frontal'] - b['espesor']
z1 = H['fondo_cuello_tapa'] - b['margen_cuello']
s = b['ranura']
tapadas = []
z = b['filas_inicio']
n = 0
while z + s / 2 <= z1 - 3.0:
    for x in b['columnas_x']:
        detras = Part.makeBox(s - 0.4, 1.5, s - 0.4, V(x - s / 2 + 0.2, yb - 1.6, z - s / 2 + 0.2))
        if common_mm3(detras, tube) > 0.05:
            tapadas.append([x, z])
        n += 1
    z += b['filas_paso']
res['respaldo'] = {'ranuras': n, 'ranuras_sin_hueco_detras': tapadas}
if tapadas:
    fallos.append(f'{len(tapadas)} ranuras del respaldo no tienen hueco detras')

# --- 3. Montaje de los paneles ------------------------------------------------------
res['montaje_paneles'] = {}
for clave, tapa, extras in (('panel', cover, ('ref_oled', 'ref_button')), ('panel_aux', aux, ())):
    cfg = P[clave]
    a = math.radians(cfg['angulo'])
    conjunto = tapa
    for e in extras:
        conjunto = conjunto.fuse(OBJ[e])
    peor, peor_d = 0.0, 0.0
    for paso in range(1, 31):
        d = paso * 0.5
        movido = conjunto.copy()
        movido.translate(V(math.cos(a) * d, math.sin(a) * d, 0))
        v = common_mm3(movido, tube)
        if v > peor:
            peor, peor_d = v, d
    ok = peor < 1.0
    res['montaje_paneles'][clave] = {'con': list(extras), 'peor_choque_mm3': round(peor, 2),
                                     'a_mm_de_su_sitio': peor_d, 'entra': ok}
    if not ok:
        fallos.append(f'la tapa del {clave} no entra por su ventana')

# --- 4. Pantalla --------------------------------------------------------------------
d = P['panel']['pantalla']
W = d['pcb_ancho']
yf = d['plano_apoyo_y']
prof = d['vidrio']['espesor'] + d['mica_espesor']
gx = max(abs(d['vidrio']['u'][0] - W / 2), abs(d['vidrio']['u'][1] - W / 2)) + d['holgura_vidrio']
piel_bolsillo = RO - math.hypot(gx, yf + prof)
px = max(abs(u - W / 2) for u, _ in d['agujeros']) + d['piloto'] / 2
piel_piloto = RO - math.hypot(px, yf + d['piloto_profundidad'])
(u0, u1), (v0, v1) = d['area_activa']['u'], d['area_activa']['v']
res['pantalla'] = {
    'piel_sobre_bolsillo_mm': round(piel_bolsillo, 2),
    'piel_sobre_pilotos_mm': round(piel_piloto, 2),
    'centro_area_activa_z_mm': round(d['z_borde_superior'] - (v0 + v1) / 2, 2),
    'centro_area_activa_x_mm': round(-((u0 + u1) / 2 - W / 2), 2),
    'vidrio_frente_y_mm': round(yf + prof, 2),
    'fondo_ventana_en_el_centro_mm': round(RO - (yf + prof), 2),
}
if min(piel_bolsillo, piel_piloto) < PIEL_MIN:
    fallos.append('la tapa queda demasiado delgada sobre la pantalla')

# --- 5. Boton ------------------------------------------------------------------------
bt = P['panel']['boton']
r_sf = bt['asiento_exterior_diametro'] / 2
espesor = math.sqrt(RO ** 2 - r_sf ** 2) - bt['asiento_tuerca_y']
paquete = OBJ['ref_battery'].fuse(OBJ['ref_um980']).fuse(OBJ['ref_thing_plus'])
dist_boton = OBJ['ref_button'].distToShape(paquete)[0]
dist_oled = OBJ['ref_oled'].distToShape(paquete)[0]
res['boton'] = {'espesor_panel_en_el_eje_mm': round(espesor, 2),
                'con_junta_mm': round(espesor + bt['junta'], 2),
                'panel_maximo_mm': bt['panel_maximo'],
                'distancia_al_paquete_con_cables_mm': round(dist_boton, 2)}
res['pantalla']['distancia_al_paquete_con_dupont_mm'] = round(dist_oled, 2)
if espesor + bt['junta'] > bt['panel_maximo']:
    fallos.append('el panel es demasiado grueso para la rosca del boton')
if min(dist_boton, dist_oled) < 3.0:
    fallos.append('el boton o la pantalla quedan a menos de 3 mm del paquete')

# --- 6. IMU ------------------------------------------------------------------------
imu = P['imu']
pl = P['plataforma_imu']
ch = imu['chip']
z_pcb = H['pcb_imu_cara_inferior']
z_top_plat = H['plataforma_disco'][1] + pl['separadores_alto']
# Donde TIENEN que estar los agujeros para que el chip caiga en el eje, sacado
# de las cotas del chip y no de la geometria construida.
esperados = [(ch['corrimiento_lejos_del_selector'] + s * imu['agujeros_separacion'] / 2,
              ch['desde_linea_agujeros']) for s in (-1, 1)]
pilotos = []
for x, y in esperados:
    # El piloto existe ahi: un pasador de 0.2 menos de radio no toca plastico...
    dentro = Part.makeCylinder(imu['piloto'] / 2 - 0.2, 3.0, V(x, y, z_top_plat - 3.0))
    # ...y no esta corrido: el anillo de 0.4 alrededor del piloto si es plastico.
    anillo = (Part.makeCylinder(imu['piloto'] / 2 + 0.6, 3.0, V(x, y, z_top_plat - 3.0))
              .cut(Part.makeCylinder(imu['piloto'] / 2 + 0.2, 3.0, V(x, y, z_top_plat - 3.0))))
    lleno = common_mm3(anillo, plat) / anillo.Volume
    ok = common_mm3(dentro, plat) < 0.01 and lleno > 0.98
    pilotos.append({'xy_mm': [round(x, 3), round(y, 3)], 'piloto_en_su_sitio': ok})
    if not ok:
        fallos.append(f'el piloto del IMU no esta en ({x:.2f}, {y:.2f})')
# Sitio para la mayor placa publicada, con los componentes y la palanca del
# selector, sin tocar la plataforma.
ax, ay = pl['alojamiento_placa']
cx = ch['corrimiento_lejos_del_selector']
cy = ch['desde_linea_agujeros'] + imu['agujero_desde_borde'] - imu['placa_ancho'] / 2
sitio = Part.makeBox(ax + imu['selector_saliente'], ay,
                     imu['placa_espesor'] + imu['componentes_alto'],
                     V(cx - ax / 2, cy - ay / 2, z_pcb))
choque_sitio = common_mm3(sitio, plat)
cima = z_pcb + imu['placa_espesor'] + imu['componentes_alto']
libre = H['borde_superior_tubo'] - cima
chip = OBJ['ref_imu_chip'].CenterOfMass
res['imu'] = {
    'chip_centro_xy_mm': [round(chip.x, 3), round(chip.y, 3)],
    'pilotos': pilotos,
    'sitio_placa_mm': [ax + imu['selector_saliente'], ay],
    'choque_sitio_plataforma_mm3': round(choque_sitio, 3),
    'cima_componentes_z_mm': round(cima, 2),
    'libre_hasta_la_tapa_mm': round(libre, 2),
    'pide_sma_acodado_mm': pl['sma_libre_minimo'],
    'confianza_posicion_chip': ch['confianza'],
}
if math.hypot(chip.x, chip.y) > 0.01:
    fallos.append('el chip de referencia no esta en el eje')
if choque_sitio > 0.05:
    fallos.append('la placa del IMU no cabe sobre la plataforma')
if libre < pl['sma_libre_minimo']:
    fallos.append('no cabe el SMA acodado sobre el IMU')

# --- 7. Plataforma ---------------------------------------------------------------------
un = pl['unas']
ang = [a % 360 for a in un['angulos']]
tol = math.degrees(un['holgura_ventana_ancho'] / NECK_RI)
otras = []
for giro in range(1, 360):
    rot = [(a + giro) % 360 for a in ang]
    if all(min(abs(r - w), 360 - abs(r - w)) <= tol for r, w in zip(sorted(rot), sorted(ang))):
        otras.append(giro)
flexion = 1.5 * pl['falda_espesor'] * (un['saliente'] - pl['holgura_radial']) / un['largo'] ** 2
z_win0, z_win1 = H['ventanas_cuello']
z_n0, z_n1 = H['unas']
# Cada una dentro de su ventana: la parte de la una que choca con la tapa es
# solo la precarga.
choque_unas = common_mm3(plat, cap)
res['plataforma'] = {
    'orientaciones_posibles_ademas_de_la_buena': otras,
    'flexion_lengueta': round(flexion, 4),
    'ventana_z_mm': [z_win0, z_win1],
    'una_z_mm': [z_n0, z_n1],
    'una_cabe_en_la_ventana': z_n1 <= z_win1,
    'interferencia_por_precarga_mm3': round(choque_unas, 2),
}
if otras:
    fallos.append('la plataforma entra en mas de una orientacion')
if flexion > FLEXION_MAX:
    fallos.append('la lengueta de la una flexiona demasiado')
if z_n1 > z_win1 or choque_unas > 5.0:
    fallos.append('las unas no caben en sus ventanas')

# --- 8. Seguros --------------------------------------------------------------------------
screws = json.loads((ROOT / 'generated' / 'screws.json').read_text(encoding='utf-8'))
seg = P['seguro']
a = math.radians(seg['angulo'])
ux, uy = math.cos(a), math.sin(a)


def rod(radius, depth, z, start=RO + 2, vx=ux, vy=uy):
    return Part.makeCylinder(radius, depth, V(vx * start, vy * start, z), V(-vx, -vy, 0))


res['seguros'] = {}
for nombre, part, z, fondo in (('base', base, H['seguro_base'], seg['profundidad_base']),
                               ('tapa', cap, H['seguro_tapa'], seg['profundidad_tapa'])):
    nucleo = rod(seg['piloto'] / 2 - 0.1, fondo - 0.5, z)
    choque = common_mm3(nucleo, tube) + common_mm3(nucleo, part)
    rosca = common_mm3(rod(1.5, fondo - 0.5, z), part)
    ok = choque < 0.05 and rosca > 5.0
    res['seguros'][nombre] = {'angulo': seg['angulo'], 'z_mm': z,
                              'choque_del_nucleo_mm3': round(choque, 2),
                              'plastico_para_la_rosca_mm3': round(rosca, 1),
                              'alineado': ok}
    if not ok:
        fallos.append(f'seguro de la {nombre} desalineado o sin rosca')

# --- 9. Paredes en la base -----------------------------------------------------------------
ins = P['inserto_jalon']
z_floor = H['piso_interior']
cavidades = {
    'alojamiento_brida': Part.makeCylinder(ins['brida_diametro'] / 2 + ins['holgura'] / 2,
                                           ins['brida_espesor'] + 0.1, V(0, 0, ins['barril_altura'])),
    'barril': Part.makeCylinder(ins['barril_diametro'] / 2 + ins['holgura'] / 2,
                                ins['barril_altura'] + 0.2, V(0, 0, -0.1)),
    'paso_esparrago': Part.makeCylinder(ins['paso_libre_macho_radio'], z_floor + 1,
                                        V(0, 0, ins['barril_altura'])),
}
cresta = rod(1.5, screws['seguro_base'], H['seguro_base'], RO - seg['cabeza_profundidad'])
paredes = {f'seguro_base-{k}': cresta.distToShape(c)[0] for k, c in cavidades.items()}
res['paredes_mm'] = {k: round(v, 2) for k, v in paredes.items()}
for k, v in paredes.items():
    if v < PARED_MIN:
        fallos.append(f'pared de {v:.2f} mm entre {k}')

# --- 10. Tornillos de los paneles -----------------------------------------------------------
obstaculos = cap.fuse(plat).fuse(paquete)
res['tornillos_panel'] = {}
for clave in ('panel', 'panel_aux'):
    cfg = P[clave]
    largo = screws[clave]
    ang_p = math.radians(cfg['angulo'])
    vx, vy = math.cos(ang_p), math.sin(ang_p)
    seat = RO - cfg.get('cabeza_profundidad', 1.6)
    peor = 99.0
    for dz in (-cfg['tornillo_separacion_z'] / 2, cfg['tornillo_separacion_z'] / 2):
        body = rod(1.5, largo, cfg['z_centro'] + dz, seat, vx, vy)
        peor = min(peor, body.distToShape(obstaculos)[0])
    res['tornillos_panel'][clave] = {'largo_mm': largo, 'distancia_punta_mm': round(peor, 2)}
    if peor < PASO_TORNILLO:
        fallos.append(f'el tornillo del {clave} llega a {peor:.2f} mm de lo que tiene detras')

res['cabe_todo'] = not fallos
res['fallos'] = fallos
out = ROOT / 'generated' / 'capacity.json'
out.write_text(json.dumps(res, indent=1, ensure_ascii=False), encoding='utf-8')
print(json.dumps(res, indent=1, ensure_ascii=False))
sys.exit(1 if fallos else 0)
