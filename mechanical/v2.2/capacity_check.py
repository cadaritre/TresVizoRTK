"""Comprueba lo que la geometria de V2.2 promete.

1. Paquete: la 18650 del peor caso detras del respaldo, y el carrier UM980 y
   la Thing Plus delante, sin tocar el tubo; la 18650 deja holgura a la pared
   y a las costillas, y cada componente pasa por el collar al meterlo
   centrado.
2. Respaldo: detras de cada ranura hay hueco para la brida, y por cada hueco
   de las costillas pasa una brida de una celda del canal a la otra.
3. Toalleros: detras de cada barra hay sitio para una brida y quedan a mas de
   2 mm del paquete.
4. Montaje del panel: la tapa, con la pantalla y sus cables, el boton con su
   tuerca y cables y el header JST con los suyos, entra radialmente por su
   ventana sin tocar el tubo en 35 mm de recorrido.
5. Pantalla: piel minima de la tapa sobre el bolsillo del vidrio y sobre los
   pilotos.
6. Boton: espesor del panel en su eje, con junta, frente al maximo que admite
   el boton mas restrictivo; y el boton y la pantalla, con sus cables, a mas de
   HOLGURA_CABLES del paquete.
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
11. Tuerca del jalon: al menos PARED_MIN del alojamiento hexagonal y de los
    pilotos de sus retenes a la cresta del seguro de la base, y de cada piloto
    al alojamiento; la tuerca de referencia cabe sin tocar la base y no
    sobresale de su cara; cada arandela pisa al menos 1 mm de tuerca sin tapar
    el paso del perno, y arandelas y cabezas no tocan el tubo ni nada de dentro.
12. Tornillos del panel: la punta no llega a menos de 0.5 mm del cuello de la
    tapa, de la plataforma ni del paquete.
13. Bandas de TPU: cada banda tapa entera la cabeza de los tornillos que
    tiene debajo, con borde_minimo hasta su canto, y sobre cada uno hay una
    caja redonda mayor que la cabeza; sus cantos libres no pisan el boton ni el
    hueco del JST.
14. Conector de carga: el header JST con sus cables cabe en su bolsillo sin
    tocar la tapa, su cara no sobresale, y el bolsillo deja PIEL_MIN al
    piloto de arriba de la tapa.

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
HOLGURA_CABLES = 2.0     # mm entre los cables flexibles del boton o la pantalla y una placa
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


def max_radius(shape):
    pts = []
    for e in shape.Edges:
        pts += e.discretize(Deflection=0.02)
    return max(math.hypot(p.x, p.y) for p in pts)


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
    r = max_radius(shape)
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
# La 18650 en el canal: holgura a la pared, por donde pasa la brida que la
# rodea, y a las costillas.
bat = OBJ['ref_battery']
a_pared = RI - max_radius(bat)
costillas = [Part.makeBox(P['respaldo']['costilla_espesor'], 40, 200,
                          V(rx - P['respaldo']['costilla_espesor'] / 2, -RI - 5, -50))
             for rx in P['respaldo']['costillas_x']]
a_costilla = min(bat.distToShape(c)[0] for c in costillas)
res['paquete']['18650_en_el_canal'] = {'holgura_a_pared_mm': round(a_pared, 2),
                                       'holgura_a_costillas_mm': round(a_costilla, 2)}
if a_pared < 0.3 or a_costilla < 0.5:
    fallos.append('la 18650 no cabe holgada en el canal del respaldo')
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
conjunto = cover.fuse(OBJ['ref_oled']).fuse(OBJ['ref_button']).fuse(OBJ['ref_jst'])
peor, peor_d = 0.0, 0.0
for paso in range(1, RECORRIDO_PANEL + 1):
    movido = conjunto.copy()
    movido.translate(V(math.cos(a) * paso, math.sin(a) * paso, 0))
    v = common_mm3(movido, tube)
    if v > peor:
        peor, peor_d = v, paso
ok = peor < 1.0
res['montaje_panel'] = {'con': ['ref_oled', 'ref_button', 'ref_jst'], 'recorrido_mm': RECORRIDO_PANEL,
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
res['pantalla']['distancia_al_paquete_con_cables_mm'] = round(dist_oled, 2)
if espesor + bt['junta'] > bt['panel_maximo']:
    fallos.append('el panel es demasiado grueso para la rosca del boton')
if min(dist_boton, dist_oled) < HOLGURA_CABLES:
    fallos.append(f'el boton o la pantalla quedan a menos de {HOLGURA_CABLES} mm del paquete')

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

# --- 11. Tuerca del jalon -------------------------------------------------------------------
tj = P['tuerca_jalon']
ret = tj['retenes']
z_floor = H['piso_interior']
PERNO_5_8 = 15.875       # mm, diametro mayor del perno del baston


def hexagono(apotema, z0, h):
    rc = apotema / math.cos(math.radians(30))
    pts = [V(rc * math.cos(math.radians(60 * k)), rc * math.sin(math.radians(60 * k)), z0)
           for k in range(6)]
    return Part.Face(Part.makePolygon(pts + [pts[0]])).extrude(V(0, 0, h))


alojamiento = hexagono((tj['entre_caras'] + tj['holgura_caras']) / 2, tj['anillo_asiento'],
                       z_floor - tj['anillo_asiento'])
cresta = rod(1.5, screws['seguro_base'], H['seguro_base'], RO - seg['cabeza_profundidad'])
paredes = {'seguro_base-alojamiento': cresta.distToShape(alojamiento)[0]}
pisa = []
for k, ang in enumerate(ret['angulos'], start=1):
    x = ret['radio'] * math.cos(math.radians(ang))
    y = ret['radio'] * math.sin(math.radians(ang))
    reten = Part.makeCylinder(1.5, ret['profundidad'], V(x, y, z_floor - ret['profundidad']))
    paredes[f'reten_{k}-alojamiento'] = reten.distToShape(alojamiento)[0]
    paredes[f'seguro_base-reten_{k}'] = cresta.distToShape(reten)[0]
    pisa.append(tj['entre_caras'] / 2 - (ret['radio'] - ret['arandela_diametro'] / 2))
libre_perno = ret['radio'] - ret['arandela_diametro'] / 2 - PERNO_5_8 / 2
tuerca = OBJ['ref_nut']
choque_tuerca = common_mm3(tuerca, base)
sobresale = tuerca.BoundBox.ZMax - z_floor
dentro = cap.fuse(plat).fuse(paquete).fuse(cover)
choque_retenes = common_mm3(OBJ['ref_nut_keepers'], tube) + common_mm3(OBJ['ref_nut_keepers'], dentro)
res['tuerca_jalon'] = {
    'paredes_mm': {k: round(v, 2) for k, v in paredes.items()},
    'arandela_pisa_tuerca_mm': [round(p, 2) for p in pisa],
    'arandela_a_perno_mm': round(libre_perno, 2),
    'holgura_perno_en_anillo_mm': round((tj['paso_perno_diametro'] - PERNO_5_8) / 2, 2),
    'choque_tuerca_con_base_mm3': round(choque_tuerca, 2),
    'tuerca_sobre_cara_de_la_base_mm': round(sobresale, 2),
    'choque_retenes_mm3': round(choque_retenes, 2),
}
for k, v in paredes.items():
    if v < PARED_MIN:
        fallos.append(f'pared de {v:.2f} mm entre {k}')
if min(pisa) < 1.0:
    fallos.append(f'la arandela solo pisa {min(pisa):.2f} mm de la tuerca')
if libre_perno < 0.5:
    fallos.append('la arandela tapa el paso del perno')
if choque_tuerca > 0.01 or sobresale > 0.0:
    fallos.append('la tuerca no cabe en su alojamiento')
if choque_retenes > 0.01:
    fallos.append('las arandelas o las cabezas de los retenes tocan algo')

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
ri_banda = RO - bd['apriete_diametral'] / 2
bandas = {'abajo': (tuple(H['banda_abajo']), OBJ['06_bumper_bottom']),
          'arriba': (tuple(H['banda_arriba']), OBJ['07_bumper_top'])}
half = cfg['tornillo_separacion_z'] / 2
cabezas = [('seguro de la base', seg['angulo'], H['seguro_base'], seg['cabeza_diametro']),
           ('seguro de la tapa', seg['angulo'], H['seguro_tapa'], seg['cabeza_diametro']),
           ('tapa del panel, abajo', cfg['angulo'], cfg['z_centro'] - half, cfg['tornillo_cabeza']),
           ('tapa del panel, arriba', cfg['angulo'], cfg['z_centro'] + half, cfg['tornillo_cabeza'])]
res['bandas'] = {}
for nombre_b, ((z0, z1), banda) in bandas.items():
    debajo = []
    for nombre, ang, z, dia in cabezas:
        if z + dia / 2 <= z0 or z - dia / 2 >= z1:
            continue
        r_caja = dia / 2 + bd['caja_holgura_diametro'] / 2
        borde = min(z - r_caja - z0, z1 - (z + r_caja))
        # La caja esta en su sitio: un disco de la cabeza mas 0.5 por lado,
        # metido en la banda hasta 0.2 antes del fondo de la caja, no toca TPU.
        a = math.radians(ang)
        ux, uy = math.cos(a), math.sin(a)
        r0 = ri_banda - 0.5
        sonda = Part.makeCylinder(dia / 2 + 0.5, bd['caja_profundidad'] + 0.3,
                                  V(ux * r0, uy * r0, z), V(ux, uy, 0))
        en_caja = common_mm3(sonda, banda) < 0.01
        debajo.append({'tornillo': nombre, 'z_mm': round(z, 2), 'en_su_caja': en_caja,
                       'borde_hasta_el_canto_mm': round(borde, 2)})
        if not en_caja:
            fallos.append(f'la cabeza del {nombre} queda bajo la banda de {nombre_b} sin su caja')
        if borde < bd['borde_minimo']:
            fallos.append(f'la banda de {nombre_b} no tapa entera la cabeza del {nombre}')
    res['bandas'][nombre_b] = {'z_mm': [z0, z1], 'alto_mm': round(z1 - z0, 2),
                               'tornillos_debajo': debajo}
# La muesca de alineacion, en el canto libre sobre el panel, no se cruza con la
# caja del tornillo del panel: por fuera y por dentro a la vez dejaria 0.3 de TPU.
mk = bd['marca']
for nombre_b, (z0, z1), libre_arriba in (('abajo', tuple(H['banda_abajo']), True),
                                         ('arriba', tuple(H['banda_arriba']), False)):
    muesca = (z1 - mk['largo'], z1) if libre_arriba else (z0, z0 + mk['largo'])
    for nombre, ang, z, dia in cabezas:
        r_caja = dia / 2 + bd['caja_holgura_diametro'] / 2
        if abs(ang - cfg['angulo']) < 1e-6 and z0 < z < z1:
            hueco = max(muesca[0] - (z + r_caja), (z - r_caja) - muesca[1])
            res['bandas'][nombre_b]['muesca_a_caja_mm'] = round(hueco, 2)
            if hueco < 0.3:
                fallos.append(f'la muesca de la banda de {nombre_b} se cruza con la caja del {nombre}')
# Los cantos libres no pisan el boton ni el hueco del JST.
bt_p = cfg['boton']
jx_p = cfg['jst_xh']
a_boton = bt_p['z'] - bt_p['asiento_exterior_diametro'] / 2 - H['banda_abajo'][1]
a_jst = H['banda_arriba'][0] - (jx_p['z'] + jx_p['fondo'] / 2 + jx_p['holgura'])
res['bandas']['canto_de_abajo_al_boton_mm'] = round(a_boton, 2)
res['bandas']['canto_de_arriba_al_jst_mm'] = round(a_jst, 2)
if min(a_boton, a_jst) < 0.5:
    fallos.append('el canto de una banda queda encima del boton o del JST')

# --- 14. Conector de carga --------------------------------------------------------------------
jx = cfg['jst_xh']
jst = OBJ['ref_jst']
choque_jst = common_mm3(jst, cover)
cara = jst.BoundBox.YMax
x_borde = jx['ancho'] / 2
saliente_centro = cara - RO
saliente_borde = cara - math.sqrt(RO ** 2 - x_borde ** 2)
# El bolsillo tiene que pasar por la ventana del tubo: por encima de su borde
# empieza el engrosamiento donde apoya el reborde de la tapa.
borde_ventana = cfg['z_centro'] + cfg['alto'] / 2 - cfg['reborde_z']
techo_bolsillo = jx['z'] + jx['fondo'] / 2 + jx['holgura'] + jx['pared']
res['conector_carga'] = {
    'choque_con_la_tapa_mm3': round(choque_jst, 2),
    'cara_sobre_la_superficie_en_el_centro_mm': round(saliente_centro, 2),
    'cara_sobre_la_superficie_en_los_extremos_mm': round(saliente_borde, 2),
    'bolsillo_bajo_el_borde_de_la_ventana_mm': round(borde_ventana - techo_bolsillo, 2),
}
if choque_jst > 0.01:
    fallos.append('el header JST no cabe en su bolsillo')
if saliente_centro > 0.0 or saliente_borde > 0.05:
    fallos.append('la cara del header JST sobresale del panel')
if borde_ventana - techo_bolsillo < 0.3:
    fallos.append('el bolsillo del JST no pasa por la ventana del tubo')

res['cabe_todo'] = not fallos
res['fallos'] = fallos
out = ROOT / 'generated' / 'capacity.json'
out.write_text(json.dumps(res, indent=1, ensure_ascii=False), encoding='utf-8')
print(json.dumps(res, indent=1, ensure_ascii=False))
sys.exit(1 if fallos else 0)
