"""Opcion de diseno sobre V2.1: antena de topografia dentro de un domo.

Dos piezas nuevas, el resto es V2.1 sin tocar:
  - tapa-plato: el mismo cuello, bayoneta y seguro que la tapa de V2.1; encima,
    un cuenco a 35 grados que se abre hasta un aro de 136 mm donde se atornilla
    la antena ArduSimple OEM por sus seis barrenos;
  - domo: casquete eliptico sobre falda recta que baja sobre el aro hasta un
    escalon, con junta torica y tres tornillos radiales por debajo del plano
    de la antena.

El propietario acepto soportes donde la estetica lo justifique: el cono
interior del cuenco y el interior del casquete los llevan. Por fuera del domo
no hace falta ninguno; en la tapa-plato quedan tres voladizos cortos que se
imprimen sin soporte y quedan tapados al montar.

Las cotas de la antena salen de su STEP oficial (ver parameters.json). Si se
pasa ese STEP con --antena-step, las comprobaciones se hacen contra la antena
real; si no, contra la envolvente medida.

El ensamble se guarda CERRADO, en el marco de V2.1: tubo de referencia, y
tapa-plato con sus dientes contra el fondo de la ranura.

Uso:
  <python de FreeCAD> build_dome.py [--antena-step ruta.step] [--output-dir generated]
"""
from pathlib import Path
import argparse, json, math, sys

import FreeCAD as App
import Part, MeshPart

ROOT = Path(__file__).resolve().parent
V21 = ROOT.parent / 'v2.1'
ap = argparse.ArgumentParser(description=__doc__)
ap.add_argument('--output-dir', type=Path, default=ROOT / 'generated')
ap.add_argument('--antena-step', type=Path,
                help='STEP oficial de la antena para comprobar contra la real')
# parse_known_args: freecadcmd anade su propio argumento al lanzar el script.
args, _ = ap.parse_known_args()
OUT = args.output_dir.resolve()
for sub in ('', 'stl', 'step'):
    (OUT / sub).mkdir(parents=True, exist_ok=True)

P = json.loads((V21 / 'parameters.json').read_text(encoding='utf-8'))
IDX = json.loads((V21 / 'generated' / 'model-index.json').read_text(encoding='utf-8'))
O = json.loads((ROOT / 'parameters.json').read_text(encoding='utf-8'))
V = App.Vector

TUBE, BAY, LOCK, PR = P['tubo'], P['bayoneta'], P['seguro'], P['impresion']
A, T, D, J, S = O['antena'], O['tapa'], O['domo'], O['junta'], O['tornillos_domo']

RO = TUBE['diametro_exterior'] / 2.0
RI = RO - TUBE['pared']
CLR = PR['holgura_general']
COLLAR_T, COLLAR_H = BAY['collar_espesor'], BAY['collar_altura']
R_COLLAR = RI - COLLAR_T
R_SPIGOT = R_COLLAR - CLR
TOOTH_H, TOOTH_A = BAY['diente_alto'], BAY['diente_largo_grados']
R_TOOTH = R_SPIGOT + TOOTH_H
N_TEETH = BAY['numero_dientes']
BOSS_BITE = 0.8
# Mismo giro de cierre y mismas alturas que V2.1: la tapa-plato sustituye a su
# tapa y tiene que cerrar igual y con el seguro en el mismo sitio.
GIRO_CIERRE = IDX['giro_cierre_grados']
Z1 = IDX['plano_alturas']['borde_superior_tubo']
Z_LOCK_CAP = IDX['plano_alturas']['seguro_tapa']
Z_NECK_BOTTOM = IDX['plano_alturas']['fondo_cuello_tapa']
SIGN_CAP = -1 if IDX.get('tapa_cierra_horario') else 1
NECK_RI = R_SPIGOT - TUBE['pared']

# --- Plano de alturas de la opcion -------------------------------------------
R_BAND, R_IN, H_BAND = T['aro_radio_exterior'], T['aro_radio_interior'], T['aro_alto']
C0 = T['collar_inicial']
R_DOME_O = R_BAND + D['holgura_radial'] + D['pared']   # radio exterior del domo
STEP_H = T['escalon_recto']
SLOPE = math.tan(math.radians(T['pendiente_cuenco']))  # vertical por horizontal
# El cuenco sube desde el tubo hasta el escalon, al radio exterior del domo.
FLARE_H = (R_DOME_O - RO) * SLOPE
Z_SEAT = Z1 + C0 + FLARE_H + STEP_H + H_BAND           # cara inferior del plato
# Cono interior paralelo al exterior, con la pared perpendicular pedida.
INNER_OFFSET = T['pared_cuenco'] / math.sin(math.radians(T['pendiente_cuenco']))
Z_STEP = Z_SEAT - H_BAND                               # escalon: apoyo del domo
Z_FLARE_TOP = Z_STEP - STEP_H


def r_inner(z):
    """Radio del cono interior a la altura z."""
    return R_DOME_O - INNER_OFFSET + (z - Z_FLARE_TOP) / SLOPE


def z_inner(r):
    return Z_FLARE_TOP + (r - R_DOME_O + INNER_OFFSET) * SLOPE


Z_BAND_IN_BOTTOM = z_inner(R_IN)          # donde el aro interior se vuelve cono
Z_NECK_MEET = z_inner(NECK_RI)            # donde el cono interior llega al cuello
assert Z_NECK_MEET >= Z1, 'el cono interior cortaria el cuello'
ROT = A['rotacion']


# --- Utilidades (las mismas que V2.1) ----------------------------------------
def sector(r_out, r_in, z, h, a0, sweep):
    outer = Part.makeCylinder(r_out, h, V(0, 0, z), V(0, 0, 1), sweep)
    outer.rotate(V(), V(0, 0, 1), a0)
    if r_in <= 0:
        return outer
    inner = Part.makeCylinder(r_in, h + 2, V(0, 0, z - 1), V(0, 0, 1), sweep)
    inner.rotate(V(), V(0, 0, 1), a0)
    return outer.cut(inner)


def tube_ring(r_out, r_in, z, h):
    return (Part.makeCylinder(r_out, h, V(0, 0, z))
            .cut(Part.makeCylinder(r_in, h + 2, V(0, 0, z - 1))))


def clean(shape):
    shape = shape.removeSplitter()
    solids = [s for s in shape.Solids if s.Volume >= 0.05]
    if len(solids) > 1:
        return Part.makeCompound(solids).removeSplitter()
    return solids[0] if solids else shape


def radial_tool(radius, depth, angle_deg, z, start):
    a = math.radians(angle_deg)
    ux, uy = math.cos(a), math.sin(a)
    return Part.makeCylinder(radius, depth, V(ux * start, uy * start, z), V(-ux, -uy, 0))


def revolve(points):
    """Solido de revolucion de un perfil (r, z) cerrado."""
    pts = [V(r, 0, z) for r, z in points]
    face = Part.Face(Part.makePolygon(pts + [pts[0]]))
    return face.revolve(V(0, 0, 0), V(0, 0, 1), 360)


def bayonet_teeth(z_tooth):
    """Dientes en posicion CERRADA y con el sentido de cierre de la tapa de V2.1."""
    teeth = None
    for i in range(N_TEETH):
        a = i * 360.0 / N_TEETH + SIGN_CAP * GIRO_CIERRE
        tooth = sector(R_TOOTH, R_SPIGOT - 1, z_tooth, TOOTH_H, a - TOOTH_A / 2.0, TOOTH_A)
        teeth = tooth if teeth is None else teeth.fuse(tooth)
    return teeth


def polar(r, angle_deg):
    a = math.radians(angle_deg)
    return r * math.cos(a), r * math.sin(a)


# --- Pieza A: tapa-plato ------------------------------------------------------
def build_lid():
    # Cuello, dientes, seguro y chaflan de entrada: copia literal de la tapa de
    # V2.1 para que cierre igual sobre el mismo tubo.
    z0 = Z_NECK_BOTTOM          # el cuello baja hasta rodear la repisa del IMU
    body = tube_ring(R_SPIGOT, NECK_RI, z0, Z1 - z0)
    body = body.fuse(bayonet_teeth(Z1 - 8.0))

    # Cuenco: pared paralela por fuera y por dentro, escalon plano donde apoya
    # el domo y aro recto arriba.
    outer = [(RO, Z1), (RO, Z1 + C0), (R_DOME_O, Z_FLARE_TOP), (R_DOME_O, Z_STEP),
             (R_BAND, Z_STEP), (R_BAND, Z_SEAT)]
    bowl = revolve(outer + [(R_IN, Z_SEAT), (R_IN, Z_BAND_IN_BOTTOM),
                            (NECK_RI, Z_NECK_MEET), (NECK_RI, Z1)])
    body = body.fuse(bowl)
    # Envolvente exterior: ninguna torre interior debe asomar por fuera.
    hull = revolve([(0, Z1)] + outer + [(0, Z_SEAT)])

    # Seis torres bajo los barrenos del plato de la antena.
    r_bc = A['barrenos_circulo'] / 2.0
    tower_h = Z_SEAT - Z1
    for k in range(A['barrenos_numero']):
        x, y = polar(r_bc, ROT + k * 360.0 / A['barrenos_numero'])
        tower = Part.makeCylinder(T['torres_diametro'] / 2, tower_h, V(x, y, Z1))
        tower = tower.common(hull).cut(Part.makeCylinder(r_bc - T['torres_diametro'], 100,
                                                           V(0, 0, Z1 - 1)))
        # Solo lo que queda por encima del cono interior mas un poco de mordida.
        low = z_inner(r_bc - T['torres_diametro'] / 2) - 1.5
        body = body.fuse(tower.common(Part.makeCylinder(R_DOME_O, Z_SEAT - low,
                                                        V(0, 0, low))))

    # Torres interiores para los tornillos del domo: el piloto es ciego y el
    # agua no encuentra camino al interior.
    tw = S['torre_ancho']
    for k in range(S['numero']):
        ang = ROT + S['angulo_inicial'] + k * 360.0 / S['numero']
        dsweep = math.degrees(tw / R_IN)
        low = z_inner(R_IN - 5.0) - 1.5
        block = sector(R_IN + BOSS_BITE, R_IN - 5.0, low, Z_SEAT - low,
                       ang - dsweep / 2, dsweep)
        body = body.fuse(block.common(hull))

    # Refuerzo y piloto del seguro, como en V2.1.
    a = math.radians(LOCK['angulo'])
    ux, uy = math.cos(a), math.sin(a)
    boss = Part.makeCylinder(3.5, LOCK.get('boss_largo', 5.0), V(ux * (R_SPIGOT - BOSS_BITE),
                                         uy * (R_SPIGOT - BOSS_BITE), Z_LOCK_CAP),
                             V(-ux, -uy, 0))
    body = body.fuse(boss)
    body = body.cut(radial_tool(LOCK['piloto'] / 2, LOCK['profundidad_tapa'],
                                LOCK['angulo'], Z_LOCK_CAP, RO + 2))
    lead = BAY.get('chaflan_entrada_cuello', 0.0)
    if lead > 0:
        body = body.cut(Part.makeCone(NECK_RI + lead, NECK_RI, lead, V(0, 0, z0 - 0.01)))

    # Pilotos de las torres de la antena: M3 desde arriba, rosca en plastico.
    for k in range(A['barrenos_numero']):
        x, y = polar(r_bc, ROT + k * 360.0 / A['barrenos_numero'])
        body = body.cut(Part.makeCylinder(T['torres_piloto'] / 2, T['torres_profundidad'] + 0.1,
                                          V(x, y, Z_SEAT - T['torres_profundidad'])))

    # Pilotos ciegos de los tornillos del domo.
    for k in range(S['numero']):
        ang = ROT + S['angulo_inicial'] + k * 360.0 / S['numero']
        body = body.cut(radial_tool(S['piloto'] / 2, S['profundidad'] + 2, ang,
                                    Z_SEAT + S['z_desde_asiento'], R_BAND + 2))

    # Ranura de la junta torica en el aro.
    r_groove = (R_BAND + D['holgura_radial']) - (J['seccion'] - J['prensado'])
    zc = Z_SEAT + J['z_desde_asiento']
    body = body.cut(tube_ring(R_BAND + 1, r_groove, zc - J['ranura_ancho'] / 2,
                              J['ranura_ancho']))

    return clean(body), r_groove


# --- Pieza B: domo ------------------------------------------------------------
# Casquete eliptico con el ecuador en el plano del asiento. La altura interior
# se calcula para que cada escalon del elemento quede a la holgura pedida.
R_SK_I = R_BAND + D['holgura_radial']


def _dist_to_ellipse(r, z, a, b, n=4000):
    return min(math.hypot(r - a * math.cos(t), z - b * math.sin(t))
               for t in (math.pi / 2 * i / n for i in range(n + 1)))


def _cap_height():
    """Altura interior del casquete. Holgura medida en perpendicular a la curva,
    no en vertical: en los flancos del elemento la vertical engana."""
    corners = [(dia / 2.0, zb) for dia, _za, zb in A['elemento']]
    b = A['elemento_cima'] + D['holgura_sobre_antena']
    while min(_dist_to_ellipse(r, z, R_SK_I, b) for r, z in corners) < D['holgura_lateral_minima']:
        b += 0.1
    return b


H_TOP_I = _cap_height()


def ellipse_points(a, b, n=120):
    """Cuarto de elipse del ecuador (a, 0) a la cima (0, b)."""
    return [(a * math.cos(math.pi / 2 * i / n), b * math.sin(math.pi / 2 * i / n))
            for i in range(n + 1)]


def build_dome():
    t = D['pared']
    r_sk_o = R_SK_I + t
    zb = -H_BAND
    e = D['entrada_falda']
    # Entrada suave para la junta: e en radial a lo largo de entrada_alto (unos
    # 16 grados). Un chaflan a 45 grados puede pellizcarla al bajar el domo.
    eh = D.get('entrada_alto', e)
    inner = ellipse_points(R_SK_I, H_TOP_I)          # de (a,0) a (0,b)
    outer = ellipse_points(r_sk_o, H_TOP_I + t)
    prof = ([(r_sk_o, zb), (r_sk_o, 0.0)] + outer[1:]
            + list(reversed(inner))[:-1] + [(R_SK_I, 0.0), (R_SK_I, zb + eh), (R_SK_I + e, zb)])
    body = revolve([(max(r, 0.0), Z_SEAT + z) for r, z in prof])
    for k in range(S['numero']):
        ang = ROT + S['angulo_inicial'] + k * 360.0 / S['numero']
        z = Z_SEAT + S['z_desde_asiento']
        body = body.cut(radial_tool(S['paso'] / 2, t + 4, ang, z, r_sk_o + 2))
        # Canto interior del paso matado: la junta pasa por encima al montar.
        ch = S.get('chaflan_interior', 0.0)
        if ch > 0:
            a = math.radians(ang)
            ux, uy = math.cos(a), math.sin(a)
            body = body.cut(Part.makeCone(S['paso'] / 2, S['paso'] / 2 + ch, ch,
                                          V(ux * (R_SK_I + ch), uy * (R_SK_I + ch), z),
                                          V(-ux, -uy, 0)))
    return clean(body)


# --- Antena: envolvente medida y, si se pasa, la real -------------------------
def antenna_proxy():
    plate = Part.makeCylinder(A['plato_diametro'] / 2, A['plato_espesor'], V(0, 0, Z_SEAT))
    r_bc = A['barrenos_circulo'] / 2
    for k in range(A['barrenos_numero']):
        x, y = polar(r_bc, ROT + k * 360.0 / A['barrenos_numero'])
        plate = plate.cut(Part.makeCylinder(A['barrenos_diametro'] / 2, 3, V(x, y, Z_SEAT - 1)))
    element = None
    for dia, za, zb in A['elemento']:
        c = Part.makeCylinder(dia / 2, zb - za, V(0, 0, Z_SEAT + za))
        element = c if element is None else element.fuse(c)
    last_top = A['elemento'][-1][2]
    element = element.fuse(Part.makeCylinder(8.0, A['elemento_cima'] - last_top,
                                             V(0, 0, Z_SEAT + last_top)))
    h, ch = A['caja_inferior_ancho'] / 2, A['caja_inferior_chaflan']
    octo = [V(h - ch, -h, 0), V(h, -h + ch, 0), V(h, h - ch, 0), V(h - ch, h, 0),
            V(-h + ch, h, 0), V(-h, h - ch, 0), V(-h, -h + ch, 0), V(-h + ch, -h, 0)]
    box = Part.Face(Part.makePolygon(octo + [octo[0]])).extrude(V(0, 0, A['caja_inferior_profundidad']))
    box.translate(V(0, 0, Z_SEAT - A['caja_inferior_profundidad']))
    box.rotate(V(), V(0, 0, 1), ROT)
    element.rotate(V(), V(0, 0, 1), ROT)
    return plate, element, box


def antenna_real(path, box_clip):
    """Coloca el STEP oficial en el asiento. Devuelve (rigido, elemento, cable).

    El plato se reconoce por ser el solido de 130 x 130 x 1. El cable y el SMA
    del STEP estan dibujados rectos y fuera del equipo: se separan, porque en la
    realidad el coaxial es flexible y baja por el cuenco."""
    shape = Part.read(str(path))
    plate = max(shape.Solids, key=lambda s: (abs(s.BoundBox.XLength - 130) < 1
                                             and s.BoundBox.ZLength < 1.5, s.Volume))
    bb = plate.BoundBox
    shape.translate(V(-bb.Center.x, -bb.Center.y, Z_SEAT - bb.ZMin))
    shape.rotate(V(), V(0, 0, 1), ROT)
    rigid, cable, element = [], [], []
    clip = box_clip
    for so in shape.Solids:
        if so.BoundBox.ZMin < Z_SEAT - 0.5:          # caja, cable y conector
            inside = so.common(clip)
            rigid.append(inside)
            rest = so.cut(clip)
            if rest.Volume > 1:
                cable.append(rest)
        else:
            rigid.append(so)
            if so.BoundBox.ZMax > Z_SEAT + 2:
                element.append(so)
    return (Part.makeCompound(rigid), Part.makeCompound(element),
            Part.makeCompound(cable) if cable else None)


# --- Imprimibilidad -----------------------------------------------------------
def overhangs(shape, build_dir, limit_deg=45.0, bed_tol=0.05):
    """Caras que cuelgan mas de `limit_deg` desde la vertical en la orientacion
    de impresion. build_dir es el 'arriba' de la impresora en coordenadas del
    modelo. Se ignoran las caras apoyadas en la cama."""
    b = build_dir.normalize() if hasattr(build_dir, 'normalize') else build_dir
    heights = [v.Point.dot(b) for v in shape.Vertexes]
    bed = min(heights)
    lim = math.cos(math.radians(90 - limit_deg)) + 1e-3   # componente hacia abajo
    found = []
    for f in shape.Faces:
        if f.Area < 0.5:
            continue
        if isinstance(f.Surface, Part.Plane):
            # Normal constante: no hace falta muestrear (y un anillo estrecho se
            # escapaba del muestreo).
            n = f.normalAt(0, 0)
            p = f.CenterOfMass
            if -n.dot(b) > lim and abs(p.dot(b) - bed) > bed_tol:
                found.append({'area_mm2': round(f.Area, 1),
                              'altura_mm': round(p.dot(b) - bed, 1), 'tipo': 'Plane'})
            continue
        u0, u1, v0, v1 = f.ParameterRange
        hits = total = 0
        for i in range(8):
            for j in range(8):
                u = u0 + (u1 - u0) * (i + 0.5) / 8
                v = v0 + (v1 - v0) * (j + 0.5) / 8
                try:
                    p = f.valueAt(u, v)
                    if not f.isInside(p, 0.01, True):
                        continue
                    n = f.normalAt(u, v)
                except Exception:
                    continue
                total += 1
                if -n.dot(b) > lim and abs(p.dot(b) - bed) > bed_tol:
                    hits += 1
        if total and hits / total > 0.5:
            found.append({'area_mm2': round(f.Area, 1),
                          'altura_mm': round(f.CenterOfMass.dot(b) - bed, 1),
                          'tipo': type(f.Surface).__name__})
    found.sort(key=lambda x: -x['area_mm2'])
    return found


# --- Construccion ---------------------------------------------------------------
lid, r_groove = build_lid()
dome = build_dome()
plate, element, box = antenna_proxy()
proxy = Part.makeCompound([plate, element, box])

# Clip para separar la caja del cable en el STEP real: la envolvente de la caja
# con medio milimetro de margen.
h, ch = A['caja_inferior_ancho'] / 2 + 0.5, A['caja_inferior_chaflan']
octo = [V(h - ch, -h, 0), V(h, -h + ch, 0), V(h, h - ch, 0), V(h - ch, h, 0),
        V(-h + ch, h, 0), V(-h, h - ch, 0), V(-h, -h + ch, 0), V(-h + ch, -h, 0)]
clip = Part.Face(Part.makePolygon(octo + [octo[0]])).extrude(V(0, 0, 40))
clip.translate(V(0, 0, Z_SEAT - 20))
clip.rotate(V(), V(0, 0, 1), ROT)

real = None
if args.antena_step and args.antena_step.exists():
    real = antenna_real(args.antena_step, clip)
ant_rigid, ant_element = (real[0], real[1]) if real else (proxy, element)

# Piezas de V2.1 que se conservan, en su posicion cerrada.
v21_parts = {}
for name in ('01-threaded-base', '02-logo-tube', '04-universal-sled',
             '05-panel-cover', '06-aux-panel-cover'):
    v21_parts[name] = Part.read(str(V21 / 'generated' / 'step' / f'{name}.step'))

# --- Comprobaciones -------------------------------------------------------------
checks, fallos = {}, []


def vol(a, b):
    c = a.common(b)
    return c.Volume if c.Solids else 0.0


for name, piece in (('tapa_plato', lid), ('domo', dome)):
    checks[name] = {'solidos': len(piece.Solids), 'valido': bool(piece.isValid()),
                    'volumen_cm3': round(piece.Volume / 1000, 2)}
    if len(piece.Solids) != 1 or not piece.isValid():
        fallos.append(f'{name}: no es un solido valido')

inter = {
    'tapa_plato-tubo': vol(lid, v21_parts['02-logo-tube']),
    'tapa_plato-trineo': vol(lid, v21_parts['04-universal-sled']),
    'domo-tapa_plato': vol(dome, lid),
    'domo-tubo': vol(dome, v21_parts['02-logo-tube']),
    'antena-tapa_plato': vol(ant_rigid, lid),
    'antena-domo': vol(ant_rigid, dome),
}
checks['interferencias_mm3'] = {k: round(v, 2) for k, v in inter.items()}
for k, v in inter.items():
    if v > 10.0:   # 0.01 cm3, el mismo criterio de V2.1
        fallos.append(f'interferencia {k}: {v:.1f} mm3')

d_elem = ant_element.distToShape(dome)[0]
d_plate = ant_rigid.distToShape(dome)[0]
# Caja del LNA sola (lo que cuelga bajo el plato), contra la tapa-plato.
if real:
    under = [so for so in real[0].Solids if so.BoundBox.ZMax <= Z_SEAT + 0.05]
    lna = Part.makeCompound(under) if under else box
else:
    lna = box
d_box = lna.distToShape(lid)[0]
checks['holguras_mm'] = {
    'elemento_a_domo': round(d_elem, 2),
    'antena_completa_a_domo': round(d_plate, 2),
    'caja_lna_a_tapa_plato': round(d_box, 2),
}
if d_box < 1.5:
    fallos.append('la caja del LNA queda a menos de 1.5 mm de la tapa-plato')
if d_elem < D['holgura_lateral_minima'] - 0.2:
    fallos.append('el elemento de la antena queda demasiado cerca del domo')

# Recorrido del coaxial: se barre un cable del diametro del STEP desde su
# salida, con el radio de curvatura pedido, hasta el tubo por el lado +Y, y se
# exige que no toque tapa-plato, antena, tubo ni trineo. La curva en U va
# inclinada: en el plano vertical no cabe un radio de 13 (lo encontro la
# revision del 25-09-2026).
CB = O['cable']


class CablePath:
    def __init__(self, p, t):
        self.p, self.t, self.edges, self.length = V(p), V(t).normalize(), [], 0.0

    def line(self, length):
        if length > 1e-6:
            q = self.p + self.t * length
            self.edges.append(Part.makeLine(self.p, q))
            self.p, self.length = q, self.length + length
        return self

    def arc(self, r, ang_deg, n):
        n = V(n) - self.t * V(n).dot(self.t)
        n.normalize()
        a = math.radians(ang_deg)
        c = self.p + n * r

        def pt(th):
            return c - n * (r * math.cos(th)) + self.t * (r * math.sin(th))
        end = pt(a)
        self.edges.append(Part.Arc(self.p, pt(a / 2), end).toShape())
        self.t = (n * math.sin(a) + self.t * math.cos(a)).normalize()
        self.p, self.length = end, self.length + r * a
        return self

    def pipe(self, radius, skip=0):
        edges = self.edges[skip:]
        e0 = edges[0]
        circ = Part.Wire(Part.makeCircle(radius, e0.valueAt(e0.FirstParameter),
                                         e0.tangentAt(e0.FirstParameter)))
        return Part.Wire(edges).makePipeShell([circ], True, True)


def rot(v):
    v = V(v)
    a = math.radians(ROT)
    return V(v.x * math.cos(a) - v.y * math.sin(a), v.x * math.sin(a) + v.y * math.cos(a), v.z)


sx, sy, sz = A['salida_cable']
R_B = CB['radio_curvatura']
tilt = math.radians(CB['inclinacion_curva'])
exit_point = rot(V(sx, sy, Z_SEAT + sz))
path = CablePath(exit_point, rot(V(0, -1, 0)))
path.arc(R_B, 180, rot(V(-math.sin(tilt), 0, -math.cos(tilt))))
# Cruza bajo la caja hacia +Y y baja por la muesca de la repisa del IMU.
path.line(max(0.0, (CB['y_bajada'] - R_B) - path.p.y))
path.arc(R_B, 90, V(0, 0, -1)).line(CB['tramo_final'])
cable = path.pipe(CB['diametro'] / 2)
cable_hits = {
    'tapa_plato': vol(cable, lid),
    # Junto a la salida el STEP ya dibuja el arranque del cable: se excluye
    # una esfera de 1.6 mm alrededor de ese punto.
    'antena': vol(cable, ant_rigid.cut(Part.makeSphere(1.6, exit_point))),
    'tubo': vol(cable, v21_parts['02-logo-tube']),
    'trineo': vol(cable, v21_parts['04-universal-sled']),
}
checks['cable'] = {
    'diametro_mm': CB['diametro'], 'radio_curvatura_mm': R_B,
    'largo_recorrido_mm': round(path.length, 1), 'largo_cable_mm': CB['largo'],
    'choques_mm3': {k: round(v, 2) for k, v in cable_hits.items()},
    'pasa': all(v < 0.05 for v in cable_hits.values()) and path.length < CB['largo'],
}
if not checks['cable']['pasa']:
    fallos.append('el coaxial no pasa con el radio de curvatura pedido')

# Seguro: un tornillo recto por el tubo y la tapa-plato, como en V2.1.
a = math.radians(LOCK['angulo'])
ux, uy = math.cos(a), math.sin(a)
core = Part.makeCylinder(LOCK['piloto'] / 2 - 0.1, LOCK['profundidad_tapa'] - 0.5,
                         V(ux * (RO + 2), uy * (RO + 2), Z_LOCK_CAP), V(-ux, -uy, 0))
thread = Part.makeCylinder(1.5, LOCK['profundidad_tapa'] - 0.5,
                           V(ux * (RO + 2), uy * (RO + 2), Z_LOCK_CAP), V(-ux, -uy, 0))
hit = vol(core, lid) + vol(core, v21_parts['02-logo-tube'])
bite = vol(thread, lid)
checks['seguro'] = {'angulo': LOCK['angulo'], 'choque_del_nucleo_mm3': round(hit, 2),
                    'plastico_para_la_rosca_mm3': round(bite, 1),
                    'alineado': hit < 0.05 and bite > 5}
if not checks['seguro']['alineado']:
    fallos.append('seguro de la tapa-plato desalineado')

# Imprimibilidad. Tapa-plato boca abajo; domo de pie. Se listan las caras que
# necesitan soporte para decidir donde se aceptan (solo por dentro).
def resumen_voladizos(lista):
    return {'area_con_soporte_mm2': round(sum(x['area_mm2'] for x in lista), 0),
            'caras': lista[:6]}


checks['voladizos'] = {'tapa_plato_boca_abajo': resumen_voladizos(overhangs(lid, V(0, 0, -1))),
                       'domo_de_pie': resumen_voladizos(overhangs(dome, V(0, 0, 1)))}
# En el domo, ninguna cara EXTERIOR debe pedir soporte: se comprueba que todo lo
# que cuelga esta mas cerca del casquete interior que del exterior.
ext = 0.0
for f in dome.Faces:
    if f.Area < 0.5:
        continue
    c = f.CenterOfMass
    r, zr = math.hypot(c.x, c.y), c.z - Z_SEAT
    if zr <= 0.5:
        continue
    d_in = abs((r / R_SK_I) ** 2 + (zr / H_TOP_I) ** 2 - 1)
    d_out = abs((r / (R_SK_I + D['pared'])) ** 2 + (zr / (H_TOP_I + D['pared'])) ** 2 - 1)
    n = f.normalAt(*f.Surface.parameter(c)) if not isinstance(f.Surface, Part.Plane) else f.normalAt(0, 0)
    if d_out < d_in and n.z < -0.72:
        ext += f.Area
checks['voladizos']['domo_exterior_con_soporte_mm2'] = round(ext, 1)
# Tapa-plato: todo lo que cuelga fuera del cono interior son voladizos cortos
# que se imprimen sin soporte y quedan tapados al montar.
checks['voladizos']['tapa_plato_exteriores'] = (
    'escalon del domo (2.8 mm), flanco de la ranura de la junta (1.25 mm) y cara '
    'superior de los tres dientes (2.5 mm): voladizos cortos, sin soporte; '
    'quedan tapados por el domo o dentro del tubo')
if ext > 1.0:
    fallos.append('el domo pide soporte por fuera')

checks['junta'] = {
    'fondo_ranura_diametro_mm': round(2 * r_groove, 2),
    'falda_interior_diametro_mm': round(2 * R_SK_I, 2),
    'prensado_nominal_pct': round(100 * J['prensado'] / J['seccion'], 1),
}
checks['cotas'] = {
    'asiento_antena_z_mm': round(Z_SEAT, 2),
    'cima_domo_z_mm': round(Z_SEAT + H_TOP_I + D['pared'], 2),
    'altura_interior_casquete_mm': round(H_TOP_I, 2),
    'cabeza_sobre_el_tubo_mm': round(Z_SEAT + H_TOP_I + D['pared'] - Z1, 1),
    'diametro_exterior_mm': round(2 * R_DOME_O, 1),
    'sobre_la_tapa_de_v2_1_mm': round(Z_SEAT + H_TOP_I + D['pared'] - IDX['altura_total_mm'], 1),
    'altura_total_mm': round(Z_SEAT + H_TOP_I + D['pared'], 1),
}
checks['antena_comprobada_con'] = 'STEP oficial' if real else 'envolvente medida'
checks['cable_del_step_fuera_de_la_caja_mm3'] = round(real[2].Volume, 1) if real and real[2] else None
checks['fallos'] = fallos
checks['geometria_coherente'] = not fallos

# --- Guardar --------------------------------------------------------------------
doc = App.newDocument('TresVizoDomeOption')
for name, shape in v21_parts.items():
    obj = doc.addObject('Part::Feature', 'V21_' + name.replace('-', '_'))
    obj.Label = f'V2.1 {name}'
    obj.Shape = shape
for name, label, shape in (('07_tapa_plato', 'Tapa-plato antena OEM', lid),
                           ('08_domo', 'Domo', dome),
                           ('Antena_envolvente', 'Antena ArduSimple OEM (envolvente, no se imprime)', proxy)):
    obj = doc.addObject('Part::Feature', name)
    obj.Label = label
    obj.Shape = shape
doc.recompute()
doc.saveAs(str(OUT / 'TresVizo-DomeOption.FCStd'))

exports = []
for fname, shape in (('07-oem-antenna-lid', lid), ('08-oem-dome', dome)):
    shape.exportStep(str(OUT / 'step' / f'{fname}.step'))
    # Malla desde el STEP releido: la teselacion del solido en memoria dejaba
    # triangulos degenerados en los chaflanes pequenos del domo.
    mesh = MeshPart.meshFromShape(Shape=Part.read(str(OUT / 'step' / f'{fname}.step')),
                                  LinearDeflection=0.05, AngularDeflection=0.25,
                                  Relative=False)
    mesh.write(str(OUT / 'stl' / f'{fname}.stl'))
    closed = mesh.isSolid() and not mesh.hasNonManifolds() and not mesh.hasSelfIntersections()
    exports.append({'pieza': fname, 'triangulos': mesh.CountFacets, 'cerrada': bool(closed)})
    if not closed:
        fallos.append(f'{fname}: malla abierta')
checks['exportes'] = exports
checks['geometria_coherente'] = not fallos

(OUT / 'checks.json').write_text(json.dumps(checks, indent=1, ensure_ascii=False), encoding='utf-8')
print(json.dumps(checks, indent=1, ensure_ascii=False))
sys.exit(0 if not fallos else 1)
