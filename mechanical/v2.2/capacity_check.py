"""Comprueba lo que la geometria de V2.2 promete.

1. Paquete: bateria del peor caso, carrier UM980 y Thing Plus contra el
   respaldo, sin tocar el tubo; la brida que rodea la bateria no llega a la
   pared, y cada componente pasa por el collar al meterlo centrado.
2. Respaldo: detras de cada ranura hay hueco para la brida, y por cada hueco
   de las costillas pasa una brida de una celda del canal a la otra.
3. Toalleros: detras de cada barra hay sitio para una brida y quedan a mas de
   2 mm del paquete.
4. Montaje del panel: la tapa, con la pantalla y sus Dupont y el boton con su
   tuerca y cables, entra radialmente por su ventana sin tocar el tubo en los
   35 mm de recorrido que pide la Dupont.
5. Pantalla: piel minima de la tapa sobre el bolsillo del vidrio y sobre los
   pilotos.
6. Boton: espesor del panel en su eje, con junta, frente al maximo que admite
   el boton mas restrictivo, y distancia de su parte trasera al paquete.
7. IMU: los pilotos estan a 9.0 del eje hacia -X y a 9.5 hacia +X, el lado del
   selector, sobre la recta y = 5.65. Se comprueba con las distancias de las
   fuentes y no con la formula del generador, para que un signo cambiado falle.
   Ademas, sitio libre para la mayor placa publicada y para el SMA acodado.
8. Plataforma: cada una esta en su ventana (se compara una por una), solo hay
   una orientacion posible, la flexion de la lengueta es razonable, el margen
   de error de la ventana es suficiente y la una no se autobloquea.
9. Bayonetas: girada 120 o 240 grados, ni la base ni la tapa pasan por las
   entradas: el diente indice lo impide. En su posicion, si pasan.
10. Seguros: con el modelo cerrado, un tornillo recto atraviesa el paso del
    tubo y entra en el piloto de la base o de la tapa sin tocar pared, y su
    rosca muerde plastico.
11. Paredes: entre la cresta del seguro de la base y los huecos del inserto, al
    menos PARED_MIN.
12. Tornillos del panel: la punta no llega a menos de 0.5 mm del cuello de la
    tapa, de la plataforma ni del paquete.
13. Bandas de TPU: no tapan la tapa del panel, y la cabeza de cada seguro cae
    dentro de su ranura.
14. Hombro: no toca la antena y deja su holgura alrededor.

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
BRIDA_ANCHO = 3.6        # mm de la brida mas ancha que se usa
PIEL_MIN = P['impresion']['pared_minima']   # mm de tapa sobre un bolsillo o un piloto ciego
FLEXION_MAX = 0.02       # deformacion maxima de la lengueta al entrar
PASO_TORNILLO = 0.5      # mm minimos de la punta de un tornillo a lo que tenga detras
RECORRIDO_PANEL = 35     # mm que recorre la tapa del panel al meterla; la Dupont pide 29.6
MARGEN_VENTANA = 0.3     # mm de error en la altura de la ventana que debe absorber la una
MU_MAX = 0.8             # rozamiento por debajo del cual la una no debe autobloquearse
UNA_MAX_MM3 = 1.0        # solape de una una con la tapa: la precarga son ~0.3

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
shoulder = OBJ['06_antenna_shoulder']


def corner_radius(shape):
    bb = shape.BoundBox
    return max(math.hypot(x, y) for x in (bb.XMin, bb.XMax) for y in (bb.YMin, bb.YMax))


def common_mm3(a, b):
    c = a.common(b)
    return c.Volume if c.Solids else 0.0


def rotated(shape, deg):
    s = shape.copy()
    s.rotate(V(), V(0, 0, 1), deg)
    return s


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
paquete = OBJ['ref_battery'].fuse(OBJ['ref_um980']).fuse(OBJ['ref_thing_plus'])

# --- 2. Respaldo -------------------------------------------------------------------
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
# Una brida de 3.6 x 1.1 atraviesa cada costilla por su hueco, en x.
cerrados = []
hc = b['huecos_costillas']
for rx in b['costillas_x']:
    y_wall = -math.sqrt(RI ** 2 - rx ** 2)
    yc = ((yb - 1.5) + (y_wall + 2.0)) / 2.0
    for zc in hc['z']:
        brida = Part.makeBox(8.0, BRIDA_ESPESOR + 0.4, BRIDA_ANCHO + 0.4,
                             V(rx - 4.0, yc - (BRIDA_ESPESOR + 0.4) / 2, zc - (BRIDA_ANCHO + 0.4) / 2))
        if common_mm3(brida, tube) > 0.05:
            cerrados.append([rx, zc])
res['respaldo'] = {'ranuras': n, 'ranuras_sin_hueco_detras': tapadas,
                   'huecos_costillas': len(b['costillas_x']) * len(hc['z']),
                   'huecos_por_los_que_no_pasa_una_brida': cerrados}
if tapadas:
    fallos.append(f'{len(tapadas)} ranuras del respaldo no tienen hueco detras')
if cerrados:
    fallos.append(f'{len(cerrados)} huecos de las costillas no dejan pasar una brida')

# --- 3. Toalleros --------------------------------------------------------------------
t = P['toalleros']
res['toalleros'] = []
for tipo, lista in (('vertical', t['verticales']), ('horizontal', t['horizontales'])):
    for bar in lista:
        ang = bar['angulo']
        if tipo == 'vertical':
            z0, z1b = bar['z']
            zc, largo = (z0 + z1b) / 2, (z1b - z0) - 2 * t['poste'] - 2.0
            r_out = RI - t['separacion_pared']
            # Hueco detras de la barra, en su tramo libre: ahi va la brida.
            probe = Part.makeBox(t['separacion_pared'] - 0.6, BRIDA_ANCHO, largo,
                                 V(r_out + 0.3, -BRIDA_ANCHO / 2, zc - largo / 2))
        else:
            zc, half = bar['z'], bar['largo'] / 2
            x_out = math.sqrt((RI - t['separacion_pared']) ** 2 - half ** 2)
            libre = bar['largo'] - 2 * t['poste'] - 2.0
            probe = Part.makeBox(t['separacion_pared'] - 0.6, libre, BRIDA_ANCHO,
                                 V(x_out + 0.3, -libre / 2, zc - BRIDA_ANCHO / 2))
        probe = rotated(probe, ang)
        hueco = common_mm3(probe, tube) < 0.05
        barra = rotated(Part.makeBox(4.0, 4.0, 4.0, V(RI - t['separacion_pared'] - 4.0, -2.0, zc - 2.0)), ang)
        dist = barra.distToShape(paquete)[0]
        res['toalleros'].append({'tipo': tipo, 'angulo': ang, 'z_mm': zc,
                                 'hueco_para_brida': hueco, 'distancia_al_paquete_mm': round(dist, 2)})
        if not hueco:
            fallos.append(f'el toallero {tipo} de {ang} grados no deja pasar una brida')
        if dist < 2.0:
            fallos.append(f'el toallero {tipo} de {ang} grados queda a {dist:.1f} mm del paquete')

# --- 4. Montaje del panel --------------------------------------------------------------
cfg = P['panel']
a = math.radians(cfg['angulo'])
conjunto = cover.fuse(OBJ['ref_oled']).fuse(OBJ['ref_button'])
peor, peor_d = 0.0, 0.0
for paso in range(1, RECORRIDO_PANEL + 1):
    movido = conjunto.copy()
    movido.translate(V(math.cos(a) * paso, math.sin(a) * paso, 0))
    v = common_mm3(movido, tube)
    if v > peor:
        peor, peor_d = v, paso
ok = peor < 1.0
res['montaje_panel'] = {'con': ['ref_oled', 'ref_button'], 'recorrido_mm': RECORRIDO_PANEL,
                        'peor_choque_mm3': round(peor, 2), 'a_mm_de_su_sitio': peor_d, 'entra': ok}
if not ok:
    fallos.append('la tapa del panel no entra por su ventana')

# --- 5. Pantalla --------------------------------------------------------------------
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
    'piel_minima_mm': PIEL_MIN,
    'centro_area_activa_z_mm': round(d['z_borde_superior'] - (v0 + v1) / 2, 2),
    'vidrio_frente_y_mm': round(yf + prof, 2),
    'fondo_ventana_en_el_centro_mm': round(RO - (yf + prof), 2),
}
if min(piel_bolsillo, piel_piloto) < PIEL_MIN:
    fallos.append('la tapa queda demasiado delgada sobre la pantalla')

# --- 6. Boton ------------------------------------------------------------------------
bt = P['panel']['boton']
r_sf = bt['asiento_exterior_diametro'] / 2
espesor = math.sqrt(RO ** 2 - r_sf ** 2) - bt['asiento_tuerca_y']
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

# --- 7. IMU ------------------------------------------------------------------------
imu = P['imu']
pl = P['plataforma_imu']
ch = imu['chip']
z_pcb = H['pcb_imu_cara_inferior']
z_top_plat = H['plataforma_disco'][1] + pl['separadores_alto']
lado = 1 if imu.get('selector_lado', '+X') == '+X' else -1
esperados = [(-lado * ch['distancia_al_agujero_lejano'], ch['desde_linea_agujeros']),
             (lado * ch['distancia_al_agujero_del_selector'], ch['desde_linea_agujeros'])]
coherente = abs(ch['distancia_al_agujero_lejano'] + ch['distancia_al_agujero_del_selector']
                - imu['agujeros_separacion']) < 0.01
pilotos = []
for x, y in esperados:
    # El piloto existe ahi: un pasador de 0.2 menos de radio no toca plastico...
    dentro = Part.makeCylinder(imu['piloto'] / 2 - 0.2, 3.0, V(x, y, z_top_plat - 3.0))
    # ...y no esta corrido: el anillo alrededor del piloto si es plastico.
    anillo = (Part.makeCylinder(imu['piloto'] / 2 + 0.6, 3.0, V(x, y, z_top_plat - 3.0))
              .cut(Part.makeCylinder(imu['piloto'] / 2 + 0.2, 3.0, V(x, y, z_top_plat - 3.0))))
    lleno = common_mm3(anillo, plat) / anillo.Volume
    ok = common_mm3(dentro, plat) < 0.01 and lleno > 0.98
    pilotos.append({'xy_mm': [round(x, 3), round(y, 3)], 'piloto_en_su_sitio': ok})
    if not ok:
        fallos.append(f'el piloto del IMU no esta en ({x:.2f}, {y:.2f})')
if not coherente:
    fallos.append('las distancias del chip a los agujeros no suman la separacion')
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

# --- 8. Plataforma ---------------------------------------------------------------------
un = pl['unas']
ang = [a % 360 for a in un['angulos']]
tol = math.degrees(un['holgura_ventana_ancho'] / NECK_RI)
otras = []
for giro in range(1, 360):
    rot = [(a + giro) % 360 for a in ang]
    if all(min(abs(r - w), 360 - abs(r - w)) <= tol for r, w in zip(sorted(rot), sorted(ang))):
        otras.append(giro)
holgura = pl['holgura_radial']
flexion = 1.5 * pl['falda_espesor'] * (un['saliente'] - holgura) / un['largo'] ** 2
tan_b = math.tan(math.radians(un['angulo_retencion']))
# Error admisible en la altura de la ventana: hacia abajo hasta perder la
# precarga; hacia arriba hasta que la una ya no entre en la ventana.
e_min = -un['precarga'] * tan_b
e_max = (un['saliente'] - holgura - un['precarga']) * tan_b
z_n0, z_n1 = H['unas']
plat_r = NECK_RI - holgura
por_una = []
w_deg = math.degrees(un['ancho'] / plat_r)
for a in un['angulos']:
    zona = Part.makeCylinder(plat_r + un['saliente'] + 0.2, z_n1 - z_n0 + 0.4,
                             V(0, 0, z_n0 - 0.2), V(0, 0, 1), w_deg + 1.0)
    zona = zona.cut(Part.makeCylinder(plat_r - 0.6, z_n1 - z_n0 + 2, V(0, 0, z_n0 - 1)))
    zona.rotate(V(), V(0, 0, 1), a - (w_deg + 1.0) / 2)
    v = common_mm3(plat.common(zona), cap)
    por_una.append({'angulo': a, 'solape_con_la_tapa_mm3': round(v, 3)})
    if v > UNA_MAX_MM3:
        fallos.append(f'la una de {a} grados no esta en su ventana ({v:.2f} mm3 de choque)')
res['plataforma'] = {
    'orientaciones_posibles_ademas_de_la_buena': otras,
    'flexion_lengueta': round(flexion, 4),
    'angulo_retencion': un['angulo_retencion'],
    'error_ventana_admisible_mm': [round(e_min, 2), round(e_max, 2)],
    'se_autobloquea_con_rozamiento_mayor_que': round(tan_b, 2),
    'unas': por_una,
}
if otras:
    fallos.append('la plataforma entra en mas de una orientacion')
if flexion > FLEXION_MAX:
    fallos.append('la lengueta de la una flexiona demasiado')
if e_max < MARGEN_VENTANA or -e_min < MARGEN_VENTANA - 0.1:
    fallos.append('la una absorbe poco error en la altura de la ventana')
if tan_b < MU_MAX:
    fallos.append('la una se autobloquea con rozamientos normales')

# --- 9. Bayonetas indexadas --------------------------------------------------------------
giro = INDEX['giro_cierre_grados']
abrir_tapa = giro if INDEX['tapa_cierra_horario'] else -giro
res['bayonetas'] = {}
for nombre, pieza, abrir in (('base', base, -giro), ('tapa', cap, abrir_tapa)):
    en_entrada = common_mm3(rotated(pieza, abrir), tube)
    girada = [round(common_mm3(rotated(pieza, abrir + k * 120.0), tube), 1) for k in (1, 2)]
    ok = en_entrada < 1.0 and min(girada) > 2.0
    res['bayonetas'][nombre] = {'choque_en_su_entrada_mm3': round(en_entrada, 2),
                                'choque_girada_120_y_240_mm3': girada,
                                'una_sola_posicion': ok}
    if not ok:
        fallos.append(f'la bayoneta de la {nombre} no queda indexada')

# --- 10. Seguros --------------------------------------------------------------------------
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

# --- 11. Paredes en la base -----------------------------------------------------------------
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

# --- 12. Tornillos del panel -----------------------------------------------------------------
obstaculos = cap.fuse(plat).fuse(paquete)
largo = screws['panel']
ang_p = math.radians(cfg['angulo'])
vx, vy = math.cos(ang_p), math.sin(ang_p)
seat = RO - cfg.get('cabeza_profundidad', 1.6)
peor = 99.0
for dz in (-cfg['tornillo_separacion_z'] / 2, cfg['tornillo_separacion_z'] / 2):
    body = rod(1.5, largo, cfg['z_centro'] + dz, seat, vx, vy)
    peor = min(peor, body.distToShape(obstaculos)[0])
res['tornillos_panel'] = {'largo_mm': largo, 'distancia_punta_mm': round(peor, 2)}
if peor < PASO_TORNILLO:
    fallos.append(f'el tornillo del panel llega a {peor:.2f} mm de lo que tiene detras')

# --- 13. Bandas de TPU ------------------------------------------------------------------------
bd = P['bandas']
bandas = [tuple(H['banda_abajo']), tuple(H['banda_arriba'])]
cz0, cz1 = cover.BoundBox.ZMin, cover.BoundBox.ZMax
tapan_panel = any(z0 < cz1 and cz0 < z1 for z0, z1 in bandas)
cabezas = []
for z_seg, (z0, z1) in ((H['seguro_base'], bandas[0]), (H['seguro_tapa'], bandas[1])):
    r_cab = seg['cabeza_diametro'] / 2
    dentro = (z0 <= z_seg - bd['ranura_alto'] / 2 and z_seg + bd['ranura_alto'] / 2 <= z1
              and bd['ranura_alto'] / 2 >= r_cab + 0.5)
    cabezas.append({'seguro_z_mm': z_seg, 'banda_mm': [z0, z1], 'en_su_ranura': dentro})
    if not dentro:
        fallos.append(f'la cabeza del seguro de z = {z_seg} no cae en la ranura de su banda')
res['bandas'] = {'tapan_la_tapa_del_panel': tapan_panel, 'tapa_del_panel_z_mm': [round(cz0, 2), round(cz1, 2)],
                 'seguros': cabezas}
if tapan_panel:
    fallos.append('una banda de TPU tapa la tapa del panel')

# --- 14. Hombro ----------------------------------------------------------------------------
ant = OBJ['ref_antenna']
choque_ant = common_mm3(shoulder, ant)
holgura_ant = shoulder.distToShape(ant)[0]
res['hombro'] = {'choque_con_la_antena_mm3': round(choque_ant, 3),
                 'holgura_a_la_antena_mm': round(holgura_ant, 2),
                 'cima_z_mm': H['hombro_cima']}
if choque_ant > 0.01 or holgura_ant < 0.2:
    fallos.append('el hombro toca la antena')

res['cabe_todo'] = not fallos
res['fallos'] = fallos
out = ROOT / 'generated' / 'capacity.json'
out.write_text(json.dumps(res, indent=1, ensure_ascii=False), encoding='utf-8')
print(json.dumps(res, indent=1, ensure_ascii=False))
sys.exit(1 if fallos else 0)
