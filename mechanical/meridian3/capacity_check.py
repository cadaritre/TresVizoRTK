"""Comprueba sobre el modelo cerrado lo que el Meridian3 promete.

 1. Paso del trineo: todo lo que va en el trineo cabe por el collar (r=21).
 2. Componentes: carrier, SMA, clavijas, cable, Tiny y Tiny-Adapter no tocan
    ninguna pieza impresa ni se tocan entre si; distancias minimas.
 3. Conectores del carrier: hueco lateral y hueco inferior para clavija y cables.
 4. Coaxial: curva en S del tramo libre con el radio de curvatura pedido, paso de
    la clavija por el anillo al cerrar, tuerca de la clavija inferior al alcance
    por la ventana del panel, largo del latiguillo.
 5. USB-C: el sobremolde maximo cabe por la abertura alineado con el eje del
    receptaculo, con cuanto margen, y cuanto entra.
 6. Montaje de la tapa del panel: la Tiny-Adapter y la repisa pasan por la
    ventana al meter la tapa.
 7. Centrado: el anillo del trineo entra en el cuello de la tapa.
 8. Bayoneta: sentido de cierre medido en la geometria (dientes frente a los
    canales de entrada), recorrido libre del diente y seguros alineados.
 9. Paredes entre tornillos y cavidades de la base, y entre tornillos de antena
    y el refuerzo del seguro de la tapa.
10. Tornillos del panel: su punta no llega a nada.
11. Rigidez del trineo frente al de V2 (cuentas sobre el CAD, no ensayo).
12. Altura: que falta para los 106.9 de V2 y cuanto daria enroscar la antena
    directa al carrier.

Sale con codigo distinto de cero si algo falla.
Uso: <python de FreeCAD> capacity_check.py
"""
import json, math, sys
from pathlib import Path

import FreeCAD as App
import Part

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
import stack as S  # noqa: E402

P, C = S.P, S.C
V = App.Vector
GEN = ROOT / 'generated'
INDEX = json.loads((GEN / 'model-index.json').read_text(encoding='utf-8'))
SCREWS = json.loads((GEN / 'screws.json').read_text(encoding='utf-8'))
doc = App.openDocument(str(GEN / 'Meridian3.FCStd'))
OBJ = {o.Name.lstrip('_'): o.Shape for o in doc.Objects if hasattr(o, 'Shape')}

base, tube, cap = OBJ['01_threaded_base'], OBJ['02_logo_tube'], OBJ['03_antenna_cap']
sled, cover = OBJ['04_sled'], OBJ['05_usb_panel_cover']
IMPRESAS = {'base': base, 'tubo': tube, 'tapa': cap, 'trineo': sled, 'tapa_panel': cover}
REFS = {k[4:]: v for k, v in OBJ.items() if k.startswith('ref_')}

PARED_MIN = 1.2          # mm entre crestas de rosca, o de rosca a hueco
HOLGURA_MIN = 0.5        # mm entre un componente y cualquier pieza

fallos, res = [], {}


def falla(texto):
    fallos.append(texto)


def vol(a, b):
    c = a.common(b)
    return c.Volume if c.Solids else 0.0


def dist(a, b):
    return a.distToShape(b)[0]


def max_radius(shape):
    pts = []
    for e in shape.Edges:
        pts += e.discretize(Deflection=0.02)
    return max(math.hypot(p.x, p.y) for p in pts)


def box(x0, x1, y0, y1, z0, z1):
    return Part.makeBox(x1 - x0, y1 - y0, z1 - z0, V(x0, y0, z0))


# --- 1. Paso del trineo ---------------------------------------------------------------
r_sled = max_radius(sled)
res['paso_trineo'] = {'radio_collar_mm': S.R_COLLAR, 'radio_max_trineo_mm': round(r_sled, 2),
                      'holgura_mm': round(S.R_COLLAR - r_sled, 2)}
if r_sled >= S.R_COLLAR:
    falla('el trineo no pasa por el collar')
for nombre in ('carrier_um980', 'tiny'):
    r = max_radius(REFS[nombre])
    res['paso_trineo'][f'radio_max_{nombre}_mm'] = round(r, 2)
    if r >= S.R_COLLAR - 0.3:
        falla(f'{nombre} no pasa por el collar con 0.3 de holgura')

# --- 2. Componentes contra piezas y entre si --------------------------------------------
res['componentes'] = {}
for nombre, forma in REFS.items():
    fila = {}
    for pieza, sp in IMPRESAS.items():
        v = vol(forma, sp)
        d = dist(forma, sp)
        fila[pieza] = round(d, 2) if v < 0.01 else f'CHOCA {v:.2f} mm3'
        if v >= 0.01:
            falla(f'{nombre} choca con {pieza}')
    res['componentes'][nombre] = fila
# Entre componentes: solo parejas que no se tocan por diseno.
parejas = [('tiny_adapter', 'clavija_inferior'), ('tiny_adapter', 'cable'),
           ('tiny_adapter', 'carrier_um980'), ('tiny', 'carrier_um980'),
           ('tiny', 'clavija_inferior')]
res['entre_componentes_mm'] = {}
for a, b in parejas:
    d = dist(REFS[a], REFS[b])
    res['entre_componentes_mm'][f'{a}-{b}'] = round(d, 2)
    if d < HOLGURA_MIN:
        falla(f'{a} a {d:.2f} mm de {b}')
# Holgura minima componente-pieza impresa (salvo apoyo del carrier en su lamina).
for nombre, fila in res['componentes'].items():
    for pieza, d in fila.items():
        if isinstance(d, float) and d < HOLGURA_MIN and not (
                nombre == 'carrier_um980' and pieza == 'trineo') and not (
                nombre == 'tiny' and pieza == 'trineo') and not (
                nombre == 'tiny_adapter' and pieza == 'tapa_panel'):
            falla(f'{nombre} a {d:.2f} mm de {pieza}')

# --- 3. Conectores del carrier -----------------------------------------------------------
CAR = C['carrier_um980']
lat = CAR['conector_lateral']
y_lat = (S.CAR_PCB_TOP_Y, S.CAR_PCB_TOP_Y + lat['alto_cuerpo'])
y_peor = max(abs(y) for y in y_lat)
hueco_lat = math.sqrt(S.R_COLLAR ** 2 - y_peor ** 2) - abs(S.CAR_X0)
zona_lat = box(S.CAR_X0 - lat['hueco_necesario'], S.CAR_X0, y_lat[0], y_lat[1],
               S.Z_CAR0 - CAR['ajuste_vertical'], S.Z_CAR0 + lat['tramo_desde_abajo'] + CAR['ajuste_vertical'])
choque_lat = sum(vol(zona_lat, sp) for sp in IMPRESAS.values())
res['conector_lateral'] = {'hueco_hasta_collar_mm': round(hueco_lat, 2),
                           'hace_falta_mm': lat['hueco_necesario'],
                           'choque_con_piezas_mm3': round(choque_lat, 2),
                           'nota': 'El collar del tubo pasa por encima al montar: la clavija enchufada no puede salir de r=21.'}
if hueco_lat < lat['hueco_necesario'] or choque_lat > 0.01:
    falla('no cabe la clavija del conector lateral del carrier')
inf = CAR['conector_inferior']
cx = (S.CAR_X0 + S.CAR_X1) / 2
z_inf1 = S.Z_CAR0 - CAR['ajuste_vertical']            # carrier en su posicion mas baja
zona_inf = box(cx - inf['ancho_zona'] / 2, cx + inf['ancho_zona'] / 2, S.CAR_Y0, S.CAR_Y1,
               S.Z_FOOT_TOP, z_inf1)
cabezas = [Part.makeCylinder(2.85, 1.65, V(x, y, S.Z_FOOT_TOP)) for x, y in P['trineo']['pie']['tornillos']]
choque_inf = sum(vol(zona_inf, sp) for sp in list(IMPRESAS.values()) + cabezas)
res['conector_inferior'] = {'alto_libre_con_carrier_abajo_mm': round(z_inf1 - S.Z_FOOT_TOP, 2),
                            'hace_falta_mm': inf['hueco_necesario'],
                            'choque_mm3': round(choque_inf, 2)}
if z_inf1 - S.Z_FOOT_TOP < inf['hueco_necesario'] - 0.01 or choque_inf > 0.01:
    falla('no cabe la clavija del conector inferior del carrier')

# --- 4. Coaxial ------------------------------------------------------------------------------
CX = C['latiguillo']
R_curva = CX['radio_curvatura_por_diametro'] * CX['diametro']
d_lat = math.hypot(S.SMA_X, S.SMA_Y)
aj = CAR['ajuste_vertical']
tramo_min = CX['tramo_libre'] - aj
h_s = 2 * math.sqrt(max(R_curva ** 2 - (R_curva - d_lat / 2) ** 2, 0.0))
ring = P['trineo']['anillo']
r_clavija_max = d_lat + CX['radio_clavija']
nut = (S.Z_SMA_TIP - CX['rosca_cubierta'] - aj, S.Z_SMA_TIP + 3 + aj)
res['coaxial'] = {
    'radio_curvatura_mm': round(R_curva, 1),
    'desfase_ejes_sma_mm': round(d_lat, 2),
    'curva_en_s_pide_mm': round(h_s, 1),
    'tramo_libre_mm': [tramo_min, CX['tramo_libre'] + aj],
    'clavija_por_anillo': {'radio_clavija_mm': round(r_clavija_max, 2),
                           'radio_agujero_anillo_mm': ring['radio_interior']},
    'tuerca_clavija_inferior_mm': [round(nut[0], 1), round(nut[1], 1)],
    'ventana_panel_mm': [round(S.WINDOW_Z[0], 1), round(S.WINDOW_Z[1], 1)],
    'fondo_cuello_mm': round(S.Z_NECK_BOTTOM, 1),
    'latiguillo_entre_puntas_sma_mm': [round(S.Z_ANT_TIP - S.Z_SMA_TIP - aj, 1),
                                       round(S.Z_ANT_TIP - S.Z_SMA_TIP + aj, 1)],
    'nota': ('Latiguillo recto entre el SMA de la antena y el del carrier. El carrier se sube o baja '
             f'{aj:.0f} mm con sus bridas para que el cable quede recto; la tuerca de abajo se aprieta '
             'por la ventana del panel con la tapa ya cerrada.'),
}
if h_s > tramo_min:
    falla('el tramo libre no alcanza para la curva en S del coaxial')
if r_clavija_max >= ring['radio_interior'] - 0.5:
    falla('la clavija inferior no pasa por el anillo')
if not (S.WINDOW_Z[0] <= nut[0] and nut[1] <= S.WINDOW_Z[1] and nut[1] < S.Z_NECK_BOTTOM):
    falla('la tuerca de la clavija inferior no queda al alcance por la ventana')

# --- 5. USB-C ------------------------------------------------------------------------------
PAN = P['panel']
REP = PAN['repisa']
om_w, om_h = C['usb_c_clavija']['sobremolde_maximo']


def sobremolde(dx=0.0, dz=0.0, r=1.0):
    """Sobremolde maximo con esquinas de r=1, desde la cara del receptaculo hacia fuera."""
    y0, y1 = REP['cara_receptaculo_y'], S.RO + 30
    core = box(dx - om_w / 2 + r, dx + om_w / 2 - r, y0, y1, S.USB_Z + dz - om_h / 2, S.USB_Z + dz + om_h / 2)
    core = core.fuse(box(dx - om_w / 2, dx + om_w / 2, y0, y1, S.USB_Z + dz - om_h / 2 + r, S.USB_Z + dz + om_h / 2 - r))
    for sx in (-1, 1):
        for sz in (-1, 1):
            core = core.fuse(Part.makeCylinder(r, y1 - y0, V(dx + sx * (om_w / 2 - r), y0,
                                                             S.USB_Z + dz + sz * (om_h / 2 - r)), V(0, 1, 0)))
    return core


def libre(dx, dz):
    s = sobremolde(dx, dz)
    return vol(s, cover) + vol(s, tube) < 0.01


def margen(eje):
    lo, hi = 0.0, 3.0
    for _ in range(12):
        mid = (lo + hi) / 2
        ok = libre(mid, 0) and libre(-mid, 0) if eje == 'x' else libre(0, mid) and libre(0, -mid)
        lo, hi = (mid, hi) if ok else (lo, mid)
    return lo


centrado = libre(0, 0)
mx, mz = (margen('x'), margen('z')) if centrado else (0.0, 0.0)
rec = C['tiny_adapter']['receptaculo']
res['usb_c'] = {'eje_receptaculo': {'x': 0.0, 'z_mm': round(S.USB_Z, 2)},
                'sobremolde_maximo_mm': [om_w, om_h],
                'cabe_centrado': centrado,
                'margen_lateral_mm': round(mx, 2), 'margen_vertical_mm': round(mz, 2),
                'receptaculo_hundido_bajo_superficie_mm': round(S.RO - REP['cara_receptaculo_y'], 2),
                'nota': ('El margen vertical cubre la duda entre receptaculo de montaje superior '
                         f'(eje a {rec["eje_sobre_pcb"]} sobre el PCB) e intermedio. El sobremolde tiene '
                         'que entrar recto lo que el receptaculo esta hundido; los acodados, igual.')}
if not centrado or mz < 0.5:
    falla('el sobremolde USB-C no entra por la abertura con margen')

# --- 6. La tapa del panel entra con la Tiny-Adapter puesta ----------------------------------
adp = REFS['tiny_adapter']
bb = adp.BoundBox
shelf_z0 = bb.ZMin - REP['torre_alto'] - REP['espesor']
barrido = box(bb.XMin, bb.XMax, bb.YMin, S.RO + 20, shelf_z0, bb.ZMax + C['tiny_adapter']['alto_componentes'])
choque_barrido = vol(barrido, tube)
res['montaje_tapa_panel'] = {'choque_del_barrido_con_el_tubo_mm3': round(choque_barrido, 3),
                             'nota': 'Caja que envuelve repisa, torres y placa, barrida hacia fuera por la ventana.'}
if choque_barrido > 0.01:
    falla('la Tiny-Adapter no pasa por la ventana con la tapa del panel')

# --- 7. Centrado -------------------------------------------------------------------------------
z_ring = (S.Z_RING0 + S.Z_RING1) / 2 - 0.5
pts = []
for w in sled.slice(V(0, 0, 1), z_ring):
    pts += w.discretize(Distance=0.2)
r_ring = max(math.hypot(p.x, p.y) for p in pts)
bins = {int(math.degrees(math.atan2(p.y, p.x)) % 360) // 2 for p in pts
        if math.hypot(p.x, p.y) >= r_ring - 0.1}
neck_ok = S.Z_NECK_BOTTOM <= S.Z_RING0
res['centrado'] = {'radio_anillo_mm': round(r_ring, 2), 'radio_taladro_cuello_mm': round(S.NECK_RI, 2),
                   'holgura_radial_mm': round(S.NECK_RI - r_ring, 2),
                   'arco_en_contacto_grados': min(360, len(bins) * 2), 'cuello_baja_hasta_el_anillo': neck_ok}
if not (neck_ok and len(bins) * 2 > 180 and S.NECK_RI - r_ring > 0):
    falla('el anillo del trineo no queda centrado por el cuello')

# --- 8. Bayoneta ------------------------------------------------------------------------------
BAY = P['bayoneta']


def tooth_angles(shape, z):
    """Angulo medio de cada diente: corte a la altura del diente, puntos fuera
    del espigon, agrupados en sectores de 120 grados."""
    ang = []
    for w in shape.slice(V(0, 0, 1), z):
        for p in w.discretize(Distance=0.2):
            if math.hypot(p.x, p.y) > S.R_SPIGOT + 0.5:
                ang.append(math.degrees(math.atan2(p.y, p.x)) % 360)
    grupos = {}
    for a in ang:
        grupos.setdefault(int(((a + 60) % 360) // 120), []).append(a)
    out = []
    for g in grupos.values():
        s = sum(math.sin(math.radians(a)) for a in g)
        c = sum(math.cos(math.radians(a)) for a in g)
        out.append(math.degrees(math.atan2(s, c)))
    return sorted(out)


groove_start = -(BAY['diente_largo_grados'] + 4) / 2
giro = groove_start + BAY['diente_largo_grados'] + BAY['tope_grados'] + 2 * BAY['holgura'] - BAY['diente_largo_grados'] / 2
z_tb = S.Z_TUBE0 + 4 + BAY['diente_alto'] / 2
z_tc = S.Z_TUBE1 - 8 + BAY['diente_alto'] / 2
a_base = tooth_angles(base, z_tb)
a_cap = tooth_angles(cap, z_tc)


def offset(angles):
    """Desfase medio de los dientes respecto de los canales de entrada (0, 120, 240)."""
    return sum(((a + 60) % 120) - 60 for a in angles) / len(angles)


off_b, off_c = offset(a_base), offset(a_cap)
# Visto desde arriba, angulos crecientes = antihorario. La pieza de ABAJO con el
# diente en +giro respecto al canal equivale a que la de ARRIBA giro -giro:
# horario. En la tapa el diente es de la pieza de arriba: horario si esta en -giro.
base_horario = off_b > 0
tapa_horario = off_c < 0


def barrido_diente(shape_teeth_z, desde, hasta, z):
    """Sector que recorre un diente desde su canal de entrada hasta cerrado."""
    a0, a1 = min(desde, hasta), max(desde, hasta)
    r0 = S.R_SPIGOT
    r1 = S.R_SPIGOT + BAY['diente_alto']
    out = []
    for i in range(BAY['numero_dientes']):
        c = i * 120
        sec = Part.makeCylinder(r1, BAY['diente_alto'], V(0, 0, z), V(0, 0, 1),
                                a1 - a0 + BAY['diente_largo_grados'])
        sec.rotate(V(), V(0, 0, 1), c + a0 - BAY['diente_largo_grados'] / 2)
        sec = sec.cut(Part.makeCylinder(r0, BAY['diente_alto'] + 2, V(0, 0, z - 1)))
        out.append(sec)
    s = out[0]
    for o in out[1:]:
        s = s.fuse(o)
    return s


# Recorrido de giro hasta 0.1 grados antes del tope (en el tope el diente toca
# el fondo de la ranura a proposito) y recorrido vertical por el canal de entrada.
sw_b = barrido_diente(None, 0, math.copysign(giro - 0.1, off_b), S.Z_TUBE0 + 4)
sw_c = barrido_diente(None, 0, math.copysign(giro - 0.1, off_c), S.Z_TUBE1 - 8)


def entrada(z_desde, z_hasta):
    out = None
    for i in range(BAY['numero_dientes']):
        sec = Part.makeCylinder(S.R_SPIGOT + BAY['diente_alto'], abs(z_hasta - z_desde),
                                V(0, 0, min(z_desde, z_hasta)), V(0, 0, 1), BAY['diente_largo_grados'] - 0.2)
        sec.rotate(V(), V(0, 0, 1), i * 120 - (BAY['diente_largo_grados'] - 0.2) / 2)
        sec = sec.cut(Part.makeCylinder(S.R_SPIGOT, 400, V(0, 0, -100)))
        out = sec if out is None else out.fuse(sec)
    return out


ent_b = entrada(S.Z_TUBE0 - 3, S.Z_TUBE0 + 4 + BAY['diente_alto'])
ent_c = entrada(S.Z_TUBE1 - 8, S.Z_TUBE1 + 3)
res['bayoneta'] = {
    'giro_de_cierre_grados': round(giro, 2),
    'dientes_base_respecto_canal_grados': round(off_b, 2),
    'dientes_tapa_respecto_canal_grados': round(off_c, 2),
    'tubo_cierra_sobre_base_horario': base_horario,
    'tapa_cierra_horario': tapa_horario,
    'choque_al_girar_base_mm3': round(vol(sw_b, tube), 3),
    'choque_al_girar_tapa_mm3': round(vol(sw_c, tube), 3),
    'choque_al_entrar_base_mm3': round(vol(ent_b, tube), 3),
    'choque_al_entrar_tapa_mm3': round(vol(ent_c, tube), 3),
    'nota': 'Visto desde arriba. Cierra la pieza de arriba girando en sentido horario, como el equipo al enroscarse al jalon.',
}
if not (base_horario and tapa_horario):
    falla('las dos uniones no cierran en sentido horario')
if abs(abs(off_b) - giro) > 0.3 or abs(abs(off_c) - giro) > 0.3:
    falla('los dientes no estan dibujados en la posicion cerrada')
if max(vol(sw_b, tube), vol(sw_c, tube), vol(ent_b, tube), vol(ent_c, tube)) > 0.05:
    falla('el diente no recorre libre su canal de entrada o su ranura')

seg = P['seguro']
a = math.radians(seg['angulo'])
ux, uy = math.cos(a), math.sin(a)


def rod(radius, depth, z, start=S.RO + 2):
    return Part.makeCylinder(radius, depth, V(ux * start, uy * start, z), V(-ux, -uy, 0))


res['seguros'] = {}
for nombre, part, z, fondo in (('base', base, S.Z_LOCK_BASE, seg['profundidad_base']),
                               ('tapa', cap, S.Z_LOCK_CAP, seg['profundidad_tapa'])):
    nucleo = rod(seg['piloto'] / 2 - 0.1, fondo - 0.5, z)
    choque = vol(nucleo, tube) + vol(nucleo, part)
    rosca = vol(rod(1.5, fondo - 0.5, z), part)
    ok = choque < 0.05 and rosca > 5.0
    res['seguros'][nombre] = {'angulo': seg['angulo'], 'z_mm': round(z, 2),
                              'choque_del_nucleo_mm3': round(choque, 2),
                              'plastico_para_la_rosca_mm3': round(rosca, 1), 'alineado': ok}
    if not ok:
        falla(f'seguro de la {nombre} desalineado o sin rosca')

# --- 9. Paredes -------------------------------------------------------------------------------
ins = P['inserto_jalon']
cav = {
    'alojamiento_brida': Part.makeCylinder(ins['brida_diametro'] / 2 + ins['holgura'] / 2,
                                           ins['brida_espesor'] + 0.1, V(0, 0, ins['barril_altura'])),
    'barril': Part.makeCylinder(ins['barril_diametro'] / 2 + ins['holgura'] / 2,
                                ins['barril_altura'] + 0.2, V(0, 0, -0.1)),
    'paso_esparrago': Part.makeCylinder(ins['paso_libre_macho_radio'], S.Z_FLOOR + 1,
                                        V(0, 0, S.Z_FLANGE_TOP - 0.1)),
    'superficie_espigon': Part.makeCylinder(S.R_SPIGOT + 5, S.Z_FLOOR - S.Z_TUBE0, V(0, 0, S.Z_TUBE0)).cut(
        Part.makeCylinder(S.R_SPIGOT, S.Z_FLOOR, V(0, 0, S.Z_TUBE0 - 1))),
}
tabs = P['trineo']['pestanas']
pie = P['trineo']['pie']
# Ranuras de las pestanas en el suelo de la base (mismas cotas que build_meridian3.py).
g = tabs['holgura']
for k, tx in enumerate(tabs['placa_x']):
    w = tabs['ancho'] + g
    cav[f'ranura_pestana_{k}'] = box(tx - w / 2, tx + w / 2, S.PLATE_Y0 - g / 2, S.PLATE_Y1 + g / 2,
                                     S.Z_FLOOR - tabs['alto'] - 0.3, S.Z_FLOOR)
if tabs.get('bajo_alas'):
    wing = P['trineo']['alas']
    for sgn in (-1, 1):
        xa, xb = sgn * wing['x_interior'], sgn * (wing['x_interior'] + wing['espesor'])
        cav[f'ranura_ala_{sgn:+d}'] = box(min(xa, xb) - g / 2, max(xa, xb) + g / 2,
                                          S.PLATE_Y0 - wing['profundidad'] - g / 2, S.PLATE_Y0 + g / 2,
                                          S.Z_FLOOR - tabs['alto'] - 0.3, S.Z_FLOOR)
cr = {}
for i, (fx, fy) in enumerate(pie['tornillos']):
    largo = SCREWS['pie'] - pie['espesor']
    cr[f'pie_{i}'] = Part.makeCylinder(1.5, largo, V(fx, fy, S.Z_FLOOR - largo))
cr['seguro_base'] = rod(1.5, SCREWS['seguro_base'], S.Z_LOCK_BASE, S.RO - seg['cabeza_profundidad'])
paredes = {}
names = list(cr)
for i, na in enumerate(names):
    for nb in names[i + 1:]:
        paredes[f'{na}-{nb}'] = dist(cr[na], cr[nb])
    for nc, c in cav.items():
        if na == 'seguro_base' and nc == 'superficie_espigon':
            continue            # el seguro entra por ahi a proposito
        paredes[f'{na}-{nc}'] = dist(cr[na], c)
res['paredes_base_mm'] = {k: round(v, 2) for k, v in paredes.items()}
for k, v in paredes.items():
    if v < PARED_MIN:
        falla(f'pared de {v:.2f} mm entre {k}')
# Tornillos de antena: la cabeza apoya en la cara inferior de la tapa y no debe
# tocar el cuello ni el refuerzo del seguro, que bajan por debajo de esa cara.
ant = P['antena']
bajo_placa = cap.common(Part.makeCylinder(S.RO + 1, S.Z_TUBE1 - 0.05 - (S.Z_NECK_BOTTOM - 2),
                                          V(0, 0, S.Z_NECK_BOTTOM - 2)))
res['tornillos_antena_mm'] = {'nota': 'distancia de la cabeza (DIN 912, 4.5 x 2.5) al cuello y al refuerzo del seguro'}
for i in range(ant['numero_pernos']):
    aa = math.radians(ant['angulo_inicial'] + i * 360.0 / ant['numero_pernos'])
    r = ant['circulo_pernos'] / 2
    cabeza = Part.makeCylinder(2.25, 2.5, V(r * math.cos(aa), r * math.sin(aa), S.Z_TUBE1 - 2.5))
    d = dist(cabeza, bajo_placa)
    res['tornillos_antena_mm'][f'{math.degrees(aa) % 360:.0f}_grados'] = round(d, 2)
    if d < 0.5:
        falla('la cabeza de un tornillo de antena toca el cuello o el refuerzo del seguro')

# --- 10. Tornillos del panel --------------------------------------------------------------------
neck = Part.makeCylinder(S.R_SPIGOT, S.Z_TUBE1 - S.Z_NECK_BOTTOM, V(0, 0, S.Z_NECK_BOTTOM)).cut(
    Part.makeCylinder(S.NECK_RI, 200, V(0, 0, 0)))
obst = {'cuello_tapa': neck, 'trineo': sled, 'carrier': REFS['carrier_um980'],
        'tiny_adapter': adp, 'clavija_inferior': REFS['clavija_inferior']}
pa = math.radians(PAN['angulo'])
vx, vy = math.cos(pa), math.sin(pa)
seat = S.RO - PAN['cabeza_profundidad']
res['tornillos_panel'] = {'largo_mm': SCREWS['panel']}
peor = 99.0
for dz in (-PAN['tornillo_separacion_z'] / 2, PAN['tornillo_separacion_z'] / 2):
    body = Part.makeCylinder(1.5, SCREWS['panel'], V(vx * seat, vy * seat, S.PANEL_Z + dz), V(-vx, -vy, 0))
    for n, o in obst.items():
        peor = min(peor, dist(body, o))
res['tornillos_panel']['distancia_punta_mm'] = round(peor, 2)
if peor < 0.5:
    falla('un tornillo del panel llega a menos de 0.5 mm de algo')

# --- 11. Rigidez ---------------------------------------------------------------------------------
def section_inertia(shape, z):
    faces = [Part.Face(w) for w in shape.slice(V(0, 0, 1), z) if w.isClosed()]
    area = sum(f.Area for f in faces)
    yc = sum(f.CenterOfMass.y * f.Area for f in faces) / area
    return sum(f.MatrixOfInertia.A11 + f.Area * (f.CenterOfMass.y - yc) ** 2 for f in faces)


rows = INDEX['filas_rejilla']
z_row = rows[len(rows) // 2]
z_gap = z_row + P['rejilla_anclaje']['paso_longitudinal'] / 2
i_gap, i_row = section_inertia(sled, z_gap), section_inertia(sled, z_row)
L3 = S.Z_PLATE_TOP - S.Z_FLOOR
res['rigidez'] = {'meridian3': {'largo_placa_mm': round(L3, 1), 'inercia_entre_filas_mm4': round(i_gap),
                                'inercia_en_fila_mm4': round(i_row)}}
v2_step = ROOT.parent / 'v2' / 'generated' / 'step' / '04-trineo-universal.step'
if v2_step.exists():
    old = Part.read(str(v2_step))
    ip2 = json.loads((ROOT.parent / 'v2' / 'parameters.json').read_text(encoding='utf-8'))
    ix2 = json.loads((ROOT.parent / 'v2' / 'generated' / 'model-index.json').read_text(encoding='utf-8'))
    zf2 = ix2['plano_alturas']['piso_interior']
    L2 = ip2['trineo']['zona_bateria']
    g2 = ip2['rejilla_anclaje']['paso_longitudinal']
    z_row2 = zf2 + g2 * round((L2 / 2) / g2)
    i2_gap, i2_row = section_inertia(old, z_row2 + g2 / 2), section_inertia(old, z_row2)
    f_sec = (i_gap / i2_gap, i_row / i2_row)
    f_tip = tuple(f * (L2 / L3) ** 3 for f in f_sec)
    res['rigidez']['v2'] = {'largo_placa_mm': L2, 'inercia_entre_filas_mm4': round(i2_gap),
                            'inercia_en_fila_mm4': round(i2_row)}
    res['rigidez']['factor_seccion'] = [round(min(f_sec), 1), round(max(f_sec), 1)]
    res['rigidez']['factor_punta_en_voladizo'] = [round(min(f_tip), 1), round(max(f_tip), 1)]
    res['rigidez']['nota'] = ('Flexion fuera del plano de la placa, mismo material. factor_punta toma la placa '
                              'como voladizo libre (I/L^3). Con la tapa puesta el anillo sujeta ademas el extremo.')
    if min(f_tip) < 1.0:
        falla('el trineo queda menos rigido que el de V2')

# --- 12. Altura ----------------------------------------------------------------------------------
directo = (S.Z_CAR1 + C['carrier_um980']['sma']['sobresale'] + P['antena']['espesor_tapa'] + 4.0)
res['altura'] = {
    'total_mm': round(S.Z_TOP, 2), 'v2_mm': S.V2_ALTURA_TOTAL,
    'de_mas_frente_a_v2_mm': round(S.Z_TOP - S.V2_ALTURA_TOTAL, 2),
    'reparto_sobre_carrier_mm': {
        'sma_carrier': C['carrier_um980']['sma']['sobresale'],
        'clavijas_rectas': 2 * CX['clavija_recta_mas_alla_de_la_punta'],
        'tramo_libre': CX['tramo_libre'],
        'sma_antena_bajo_tapa': C['antena']['sma_bajo_tapa'],
    },
    'estimacion_antena_enroscada_al_carrier_mm': round(directo, 1),
    'nota_estimacion': ('Si la antena trae SMA macho y se enrosca directamente en el SMA del carrier: '
                        'carrier arriba + SMA 11 + tapa 5 + ~4 de tuerca. Exige que el carrier vaya con la '
                        'tapa (no con el trineo de la base). No esta modelado.'),
}

res['cabe_todo'] = not fallos
res['fallos'] = fallos
(GEN / 'capacity.json').write_text(json.dumps(res, indent=1, ensure_ascii=False), encoding='utf-8')
print(json.dumps(res, indent=1, ensure_ascii=False))
sys.exit(1 if fallos else 0)
