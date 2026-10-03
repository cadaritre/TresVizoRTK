"""V2.2: carcasa TresVizo. Es V2.1 con 10 mm mas de diametro, 20 mm mas de
cuerpo, panel frontal grande con pantalla OLED y boton metalico de 12 mm, sin
trineo y con el IMU en una plataforma que se incrusta en la tapa de antena.

Seis piezas: base con rosca, tubo con logo grabado y respaldo de amarre, tapa de
antena, plataforma del IMU y las dos tapas de panel. Todas las cotas salen de
parameters.json; las de los componentes de referencia, de components.json.

Cambios frente a V2.1 (pedidos por el propietario el 02-10-2026):
  - diametro 69 -> 79 y cuerpo 20 mm mas alto;
  - panel frontal de 72 grados x 96 mm: pantalla OLED de 0.96 in en su marco,
    boton metalico de 12 mm con asiento plano por fuera y por dentro, USB-C con
    repisa y dos LEDs;
  - fuera el trineo: el boton, la pantalla y su cableado ocupan el frente. Todo
    se amarra con bridas a un respaldo ranurado que forma parte del tubo, en la
    cara trasera;
  - el IMU va en una plataforma que se incrusta en el cuello de la tapa con tres
    unas, con el CHIP en el eje y no la linea de los agujeros, que es lo que
    hacia V2.1 y dejaba el sensor unos 5 mm fuera.

Ejes: Z es el eje del jalon, hacia arriba. FRONT es +Y. Origen en la cara de
apoyo del jalon (Z=0). Mirando la cara +Y con Z arriba, X apunta a la izquierda.

Los objetos ref_* del documento son componentes comprados dibujados para ver y
comprobar el montaje. No se exportan ni se imprimen.

Uso:
  <freecad>/bin/python build_v2_2.py [--output-dir generated]
"""
from pathlib import Path
import argparse, json, math

import FreeCAD as App
import Part

ROOT = Path(__file__).resolve().parent
ap = argparse.ArgumentParser(description=__doc__)
ap.add_argument('--output-dir', type=Path, default=ROOT / 'generated')
# parse_known_args: freecadcmd anade su propio argumento al lanzar el script.
args, _ = ap.parse_known_args()
OUT = args.output_dir.resolve()
OUT.mkdir(parents=True, exist_ok=True)

P = json.loads((ROOT / 'parameters.json').read_text(encoding='utf-8'))
C = json.loads((ROOT / 'components.json').read_text(encoding='utf-8'))
V = App.Vector

TUBE, BODY, BACK = P['tubo'], P['cuerpo'], P['respaldo']
IMU, PLAT, ANT, INS = P['imu'], P['plataforma_imu'], P['antena'], P['inserto_jalon']
BAY, LOCK, PAN = P['bayoneta'], P['seguro'], P['panel']
AUX, ACC = P['panel_aux'], P['accesorios']
LOGO, PR = P['logo'], P['impresion']
OLED, BTN, USB, LED = PAN['pantalla'], PAN['boton'], PAN['usb_c'], PAN['leds']

RO = TUBE['diametro_exterior'] / 2.0
RI = RO - TUBE['pared']
CLR = PR['holgura_general']

# --- Plano de alturas -------------------------------------------------------
Z_FLANGE_TOP = INS['barril_altura'] + INS['brida_espesor']
Z_FLOOR = Z_FLANGE_TOP + 4.0
Z_CEIL = Z_FLOOR + BODY['largo_util']
Z_TUBE0 = 8.0
Z_TUBE1 = Z_CEIL + 2.0
# La antena se atornilla POR FUERA, sobre la cara superior de la tapa.
Z_TOP = Z_TUBE1 + ANT['espesor_tapa']

N_TEETH = BAY['numero_dientes']
TOOTH_H, TOOTH_A = BAY['diente_alto'], BAY['diente_largo_grados']
TRAVEL_A, BAY_CLR = BAY['tope_grados'], BAY['holgura']
COLLAR_T, COLLAR_H = BAY['collar_espesor'], BAY['collar_altura']
R_COLLAR = RI - COLLAR_T
R_SPIGOT = R_COLLAR - CLR
R_TOOTH = R_SPIGOT + TOOTH_H
R_GROOVE = R_TOOTH + BAY_CLR
NECK_RI = R_SPIGOT - TUBE['pared']
GROOVE_START = -(TOOTH_A + 4) / 2.0
GROOVE_SPAN = TOOTH_A + TRAVEL_A + 2 * BAY_CLR
# Giro real de cierre: 28.7 grados, no los 30 de `tope_grados`. Base y tapa se
# dibujan CERRADAS para que los seguros coincidan con los del tubo.
GIRO_CIERRE = GROOVE_START + GROOVE_SPAN - TOOTH_A / 2.0
# Cuanto muerde un refuerzo dentro de la pared antes de sobresalir. Tangente,
# OCC marca la pieza como "unorientable".
BOSS_BITE = 0.8

SIGN_BASE = 1
SIGN_CAP = -1 if BAY.get('tapa_cierra_horario', False) else 1

Z_LOCK_BASE = Z_FLANGE_TOP + LOCK.get('altura_sobre_brida', 1.2)
Z_LOCK_CAP = Z_TUBE1 - 5.0
Z_NECK_BOTTOM = Z_TUBE1 - COLLAR_H - BAY.get('cuello_extra', 0.0)

# --- Plataforma del IMU: cotas que comparten la tapa y la plataforma --------
# La tapa lleva las ventanas y la plataforma las unas. Las dos piezas leen
# estas cifras de aqui para que cada una caiga siempre en su ventana.
PLAT_R = NECK_RI - PLAT['holgura_radial']
Z_PLAT0 = Z_TUBE1 - PLAT['altura_total']
Z_PLAT1 = Z_PLAT0 + PLAT['espesor_disco']
NAIL = PLAT['unas']
TAN_RET = math.tan(math.radians(NAIL['angulo_retencion']))
NAIL_H = NAIL['saliente'] * TAN_RET + NAIL['plano_superior'] + NAIL['saliente']
Z_NAIL_TOP = Z_PLAT1 + NAIL['largo']
Z_NAIL = Z_NAIL_TOP - NAIL_H          # canto interior de la cara de retencion
# El canto inferior de la ventana va donde la cara inclinada de la una lo toca
# con la lengueta todavia doblada `precarga` mm. Ese resto de flexion empuja la
# plataforma contra la tapa: sin juego, aunque la impresion se desvie 0.2 mm.
Z_WIN0 = Z_NAIL + (PLAT['holgura_radial'] + NAIL['precarga']) * TAN_RET
Z_WIN1 = Z_NAIL_TOP + NAIL['holgura_ventana_arriba']

# Placa del IMU. El CHIP queda en X=0, Y=0 y la placa se coloca por sus
# AGUJEROS a partir de el, no por sus cantos: el contorno real no coincide con
# el del plano y la relacion chip-agujeros si esta confirmada. Agujeros al
# frente (+Y), pines atras, selector IIC/SPI a +X: asi los ejes serigrafiados
# coinciden con los del equipo.
CHIP = IMU['chip']
HOLE_Y = CHIP['desde_linea_agujeros']
# El chip esta 0.25 mas cerca del agujero lejano al selector (-X): el punto
# medio de los agujeros queda 0.25 hacia +X.
HOLE_XM = CHIP['corrimiento_lejos_del_selector']
HALF_SPAN = IMU['agujeros_separacion'] / 2.0
HOLES = [(HOLE_XM - HALF_SPAN, HOLE_Y), (HOLE_XM + HALF_SPAN, HOLE_Y)]
PIN_Y = HOLE_Y - IMU['pines_desde_linea_agujeros']
BL, BW, BT = IMU['placa_largo'], IMU['placa_ancho'], IMU['placa_espesor']
HOLE_E = IMU['agujero_desde_borde']
# Contorno nominal del plano, solo para la referencia y para dejar sitio.
BX0 = HOLES[0][0] - HOLE_E
BY0 = HOLE_Y + HOLE_E - BW
Z_BOARD = Z_PLAT1 + PLAT['separadores_alto']


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


def box(x0, x1, y0, y1, z0, z1):
    return Part.makeBox(x1 - x0, y1 - y0, z1 - z0, V(x0, y0, z0))


def yz_prism(points_yz, x0, x1):
    """Perfil en el plano YZ extruido en X de x0 a x1."""
    pts = [V(x0, y, z) for y, z in points_yz]
    return Part.Face(Part.makePolygon(pts + [pts[0]])).extrude(V(x1 - x0, 0, 0))


def rect_y(x0, x1, z0, z1, y):
    return Part.makePolygon([V(x0, y, z0), V(x1, y, z0), V(x1, y, z1),
                             V(x0, y, z1), V(x0, y, z0)])


def undercut_chamfer(shape, r_outer, depth, z_base):
    """Rebaja a 45 grados la cara inferior de un saliente interior.

    Imprimiendo el tubo de pie, cualquier resalte hacia dentro deja su cara
    inferior colgando. A 45 grados se autosoporta.
    """
    if not TUBE.get('chaflan_voladizos', True) or depth <= 0:
        return shape
    void = Part.makeCone(r_outer, max(r_outer - depth, 0.01), depth, V(0, 0, z_base))
    return shape.cut(void)


def oblique_ramp(radius, z_base, height):
    """Disco de radio `radius` en z_base barrido a 45 grados hacia +Y.

    Lo que queda FUERA de este prisma por el lado -Y esta por encima de una
    rampa a 45 grados que nace en el collar: se imprime de pie sin soportes.
    """
    disk = Part.Face(Part.Wire(Part.makeCircle(radius, V(0, 0, z_base), V(0, 0, 1))))
    return disk.extrude(V(0, height, height))


def clean(shape):
    shape = shape.removeSplitter()
    solids = [s for s in shape.Solids if s.Volume >= 0.05]
    if len(solids) > 1:
        return Part.makeCompound(solids).removeSplitter()
    return solids[0] if solids else shape


def radial_tool(radius, depth, angle_deg, z, direction=1):
    """Cilindro radial para taladrar la pared desde fuera hacia dentro."""
    a = math.radians(angle_deg)
    ux, uy = math.cos(a), math.sin(a)
    start = RO + 2 if direction > 0 else 0
    return Part.makeCylinder(radius, depth,
                             V(ux * start, uy * start, z), V(-ux, -uy, 0))


# --- Bayoneta ---------------------------------------------------------------
def bayonet_groove(z_entry, h_entry, z_groove, sign=1):
    """Canales de entrada mas sectores de ranura. `sign` = -1 da la ranura
    simetrica, que cierra en sentido contrario."""
    cuts = []
    for i in range(N_TEETH):
        a = i * 360.0 / N_TEETH
        start = GROOVE_START if sign > 0 else -(GROOVE_START + GROOVE_SPAN)
        cuts.append(sector(R_GROOVE, R_SPIGOT - 2, z_groove,
                           TOOTH_H + 2 * BAY_CLR, a + start, GROOVE_SPAN))
        cuts.append(sector(R_GROOVE, R_SPIGOT - 2, z_entry, h_entry,
                           a - (TOOTH_A + 4) / 2.0, TOOTH_A + 4))
    shape = cuts[0]
    for c in cuts[1:]:
        shape = shape.fuse(c)
    return shape


def bayonet_teeth(z_tooth, sign=1):
    """Dientes en posicion CERRADA: contra el fondo de su ranura."""
    teeth = []
    for i in range(N_TEETH):
        a = i * 360.0 / N_TEETH + sign * GIRO_CIERRE
        teeth.append(sector(R_TOOTH, R_SPIGOT - 1, z_tooth, TOOTH_H,
                            a - TOOTH_A / 2.0, TOOTH_A))
    shape = teeth[0]
    for t in teeth[1:]:
        shape = shape.fuse(t)
    return shape


# --- Pieza 1: base con rosca ------------------------------------------------
def build_base():
    """Como V2.1 sin las ranuras ni los pilotos del trineo: el piso queda liso."""
    ch = TUBE['chaflan_inferior']
    body = Part.makeCone(RO - ch, RO, ch, V(0, 0, 0))
    body = body.fuse(Part.makeCylinder(RO, Z_TUBE0 - ch, V(0, 0, ch)))
    body = body.fuse(Part.makeCylinder(R_SPIGOT, Z_FLOOR - Z_TUBE0, V(0, 0, Z_TUBE0)))
    body = body.fuse(bayonet_teeth(Z_TUBE0 + 4.0))

    body = body.cut(Part.makeCylinder(INS['barril_diametro'] / 2 + INS['holgura'] / 2,
                                      INS['barril_altura'] + 0.2, V(0, 0, -0.1)))
    body = body.cut(Part.makeCylinder(INS['brida_diametro'] / 2 + INS['holgura'] / 2,
                                      INS['brida_espesor'] + 0.1,
                                      V(0, 0, INS['barril_altura'])))
    body = body.cut(Part.makeCylinder(INS['paso_libre_macho_radio'], Z_FLOOR + 1,
                                      V(0, 0, Z_FLANGE_TOP - 0.1)))

    r = INS['radio_pilotos']
    for i in range(3):
        a = math.radians(90 + i * 120)
        x, y = r * math.cos(a), r * math.sin(a)
        if INS['capturar_sin_tornillos']:
            body = body.fuse(Part.makeCylinder(INS['piloto_diametro'] / 2,
                                               INS['brida_espesor'] + 1.4,
                                               V(x, y, INS['barril_altura'])))
        else:
            body = body.cut(Part.makeCylinder(1.25, Z_FLOOR + 1,
                                              V(x, y, INS['barril_altura'])))

    # Piloto del seguro con profundidad real: el M3 rosca en el macizo de la
    # base.
    body = body.cut(radial_tool(LOCK['piloto'] / 2, LOCK['profundidad_base'],
                                LOCK['angulo'], Z_LOCK_BASE))
    return clean(body)


# --- Pieza 2: tubo ----------------------------------------------------------
def panel_frame(cfg):
    """Engrosamiento interior, rebaje de la tapa y ventana pasante.

    La pared mide 2.5 y la tapa tambien: rebajar 2.5 la borraria. Por eso la
    zona del panel se engrosa HACIA DENTRO. Asi el rebaje deja respaldo, la
    tapa queda a ras y los tornillos tienen donde roscar.
    """
    a0 = cfg['angulo'] - cfg['arco_grados'] / 2.0
    sweep = cfg['arco_grados']
    z0 = cfg['z_centro'] - cfg['alto'] / 2.0
    lip_z = cfg['reborde_z']
    dlip = math.degrees(cfg['reborde_arco'] / RI)
    pad_t = cfg.get('engrosamiento', cfg['espesor'])

    pad = sector(RI, RI - pad_t, z0 - lip_z, cfg['alto'] + 2 * lip_z,
                 a0 - dlip, sweep + 2 * dlip)
    pad = undercut_chamfer(pad, RI, pad_t, z0 - lip_z)
    rebate = sector(RO + 1, RO - cfg['espesor'], z0, cfg['alto'], a0, sweep)
    window = sector(RO + 1, RI - pad_t - 1,
                    z0 + lip_z, cfg['alto'] - 2 * lip_z,
                    a0 + dlip, sweep - 2 * dlip)
    return pad, rebate, window


def build_backrest():
    """Respaldo de amarre: placa ranurada en la cara trasera, unida a la pared
    por dos costillas, con un canal detras.

    Sustituye al trineo. Todo lo de dentro se amarra con bridas a esta placa y
    el frente queda libre para el boton, la pantalla y su cableado. Al ser parte
    del tubo no se dobla ni se descentra.

    La placa, las costillas y el piso del canal nacen de una rampa a 45 grados
    que arranca en el collar inferior, de modo que el tubo se sigue imprimiendo
    de pie sin soportes. El canal queda cerrado abajo y abierto arriba: por ahi
    bajan el coaxial y los cables del IMU desde la tapa.
    """
    b = BACK
    yf = -b['plano_frontal']
    yb = yf - b['espesor']
    half = b['ancho'] / 2.0
    z0 = Z_FLOOR + b['arranque_sobre_piso']
    z1 = Z_NECK_BOTTOM - b['margen_cuello']
    h = z1 - z0
    deep = RI + 2.0

    region = box(-half, half, -deep, yf, z0, z1)
    region = region.common(Part.makeCylinder(RI + BOSS_BITE, h + 2, V(0, 0, z0 - 1)))

    channel = box(-half - 1, half + 1, -deep - 1, yb, z0, z1 + 1)
    for rx in b['costillas_x']:
        ct = b['costilla_espesor']
        channel = channel.cut(box(rx - ct / 2, rx + ct / 2, -deep - 2, yf, z0 - 1, z1 + 2))

    # Las rampas nacen 0.5 mm dentro del collar: si arrancaran justo en su cara
    # interior la tocarian tangentes y la malla saldria con autointersecciones.
    ramp_lo = oblique_ramp(R_COLLAR + 0.5, z0, RI + h)
    ramp_hi = oblique_ramp(R_COLLAR + 0.5, z0 + b['piso_canal'], RI + h)
    body = region.cut(channel.cut(ramp_hi)).cut(ramp_lo)

    s = b['ranura']
    z = b['filas_inicio']
    while z + s / 2 <= z1 - 3.0:
        for x in b['columnas_x']:
            body = body.cut(box(x - s / 2, x + s / 2, yb - 2, yf + 2, z - s / 2, z + s / 2))
        z += b['filas_paso']
    return body


def build_tube(logo_shape):
    body = tube_ring(RO, RI, Z_TUBE0, Z_TUBE1 - Z_TUBE0)
    # Collar inferior: su cara de abajo apoya en la cama, no cuelga.
    body = body.fuse(tube_ring(RI, R_COLLAR, Z_TUBE0, COLLAR_H))
    # Collar superior: su cara inferior si cuelga. Lleva chaflan a 45 grados.
    top_collar = tube_ring(RI, R_COLLAR, Z_TUBE1 - COLLAR_H, COLLAR_H)
    top_collar = undercut_chamfer(top_collar, RI, COLLAR_T, Z_TUBE1 - COLLAR_H)
    body = body.fuse(top_collar)
    body = body.fuse(build_backrest())
    body = body.cut(bayonet_groove(Z_TUBE0 - 1, 6.0, Z_TUBE0 + 4.0 - BAY_CLR))
    body = body.cut(bayonet_groove(Z_TUBE1 - 6.0, 7.0, Z_TUBE1 - 8.0 - BAY_CLR, SIGN_CAP))

    for cfg in (PAN, AUX):
        pad, rebate, window = panel_frame(cfg)
        body = body.fuse(pad)
        body = body.cut(rebate).cut(window)
        half = cfg['tornillo_separacion_z'] / 2
        for dz in (-half, half):
            body = body.cut(radial_tool(cfg['tornillo_piloto'] / 2, TUBE['pared'] + 12,
                                        cfg['angulo'], cfg['z_centro'] + dz))

    # Barrenos de accesorios: pasantes, sin refuerzo interior.
    for z in ACC['z']:
        for sign in (-1, 1):
            angle = ACC['angulo'] + sign * ACC['separacion_angular'] / 2.0
            body = body.cut(radial_tool(ACC['piloto'] / 2, TUBE['pared'] + 4, angle, z))

    # Seguros de bayoneta: el paso libre ATRAVIESA pared y collar.
    through = (RO + 2) - (R_COLLAR - 1.5)
    for z in (Z_LOCK_BASE, Z_LOCK_CAP):
        body = body.cut(radial_tool(LOCK['paso_libre'] / 2, through, LOCK['angulo'], z))
        body = body.cut(radial_tool(LOCK['cabeza_diametro'] / 2,
                                    LOCK['cabeza_profundidad'] + 2, LOCK['angulo'], z))

    gw, gd = TUBE['ranura_decorativa_ancho'], TUBE['ranura_decorativa_profundidad']
    for z in TUBE['ranuras_decorativas_z']:
        if Z_TUBE0 + 2 < z < Z_TUBE1 - 2:
            body = body.cut(tube_ring(RO + 1, RO - gd, z - gw / 2, gw))

    vert = TUBE.get('lineas_verticales')
    if vert:
        z0, z1 = vert['z']
        dsweep = math.degrees(vert['ancho'] / RO)
        for grupo in vert['grupos']:
            for angle in grupo:
                body = body.cut(sector(RO + 1, RO - vert['profundidad'],
                                       z0, z1 - z0, angle - dsweep / 2, dsweep))

    if logo_shape is not None:
        body = body.cut(logo_shape).removeSplitter()
    return clean(body)


# --- Pieza 3: tapa de antena ------------------------------------------------
def build_cap():
    """Placa superior con la antena atornillada encima. El cuello baja por
    debajo del collar y aloja la plataforma del IMU, que entra por abajo y se
    engancha con tres unas en tres ventanas del cuello."""
    z0 = Z_NECK_BOTTOM
    body = Part.makeCylinder(RO, Z_TOP - Z_TUBE1, V(0, 0, Z_TUBE1))
    body = body.fuse(tube_ring(R_SPIGOT, NECK_RI, z0, Z_TUBE1 - z0))
    body = body.fuse(bayonet_teeth(Z_TUBE1 - 8.0, SIGN_CAP))
    body = body.cut(tube_ring(RO + 1, RO - 1.2, Z_TOP - 1.2, 1.3))

    # Paso libre de los tornillos de antena: roscan en la antena.
    for i in range(ANT['numero_pernos']):
        a = math.radians(ANT['angulo_inicial'] + i * 360.0 / ANT['numero_pernos'])
        r = ANT['circulo_pernos'] / 2
        body = body.cut(Part.makeCylinder(ANT['perno_paso'] / 2, ANT['espesor_tapa'] + 2,
                                          V(r * math.cos(a), r * math.sin(a),
                                            Z_TOP - ANT['espesor_tapa'] - 1)))
    body = body.cut(Part.makeCylinder(ANT['paso_coaxial'] / 2, Z_TOP - z0 + 2,
                                      V(0, 0, z0 - 1)))
    # Chaflan de entrada al pie del cuello: guia la plataforma al meterla.
    lead = BAY.get('chaflan_entrada_cuello', 0.0)
    if lead > 0:
        body = body.cut(Part.makeCone(NECK_RI + lead, NECK_RI, lead, V(0, 0, z0 - 0.01)))

    # Refuerzo local para el seguro: en el cuello solo hay 2.5 mm de pared.
    a = math.radians(LOCK['angulo'])
    ux, uy = math.cos(a), math.sin(a)
    boss = Part.makeCylinder(3.5, LOCK.get('boss_largo', 5.0),
                             V(ux * (R_SPIGOT - BOSS_BITE), uy * (R_SPIGOT - BOSS_BITE),
                               Z_LOCK_CAP), V(-ux, -uy, 0))
    body = body.fuse(boss.cut(Part.makeCylinder(ANT['paso_coaxial'] / 2 + 0.5, 60,
                                                V(0, 0, z0 - 1))))
    body = body.cut(radial_tool(LOCK['piloto'] / 2, LOCK['profundidad_tapa'],
                                LOCK['angulo'], Z_LOCK_CAP))

    # Ventanas de las unas de la plataforma. Impresa boca abajo, el canto que
    # retiene la una es el techo de la ventana: un puente de 6 mm.
    win = math.degrees((NAIL['ancho'] + NAIL['holgura_ventana_ancho']) / NECK_RI)
    for a in NAIL['angulos']:
        body = body.cut(sector(R_SPIGOT + 1, NECK_RI - 1, Z_WIN0, Z_WIN1 - Z_WIN0,
                               a - win / 2, win))
    return clean(body)


# --- Pieza 4: plataforma del IMU -------------------------------------------
def nail(a_center, w_deg):
    """Una de la lengueta en el plano radial: cara de retencion inclinada abajo
    y entrada a 45 grados arriba, revolucionada sobre el ancho de la lengueta."""
    p, r = NAIL['saliente'], PLAT_R
    pts = [V(r - 0.5, 0, Z_NAIL), V(r, 0, Z_NAIL),
           V(r + p, 0, Z_NAIL + p * TAN_RET),
           V(r + p, 0, Z_NAIL + p * TAN_RET + NAIL['plano_superior']),
           V(r, 0, Z_NAIL_TOP), V(r - 0.5, 0, Z_NAIL_TOP)]
    solid = Part.Face(Part.makePolygon(pts + [pts[0]])).revolve(V(), V(0, 0, 1), w_deg)
    solid.rotate(V(), V(0, 0, 1), a_center - w_deg / 2)
    return solid


def build_platform():
    """Disco con falda. La falda centra la plataforma en el taladro del cuello
    (0.15 de holgura) y su borde superior asienta contra la tapa: eso fija la
    altura y la deja paralela a la antena. Tres unas la retienen y la empujan
    contra la tapa.

    El IMU va con su CHIP en el eje. Dos M2.5 de cabeza avellanada entran por
    los agujeros de la placa: el cono de la cabeza asienta en el canto del
    agujero de 3.0 y centra la placa sobre cada piloto. Los pilotos estan donde
    tienen que estar los agujeros para que el chip caiga en el eje.
    """
    r = PLAT_R
    st = PLAT['falda_espesor']
    zt = Z_PLAT1
    body = Part.makeCylinder(r, PLAT['espesor_disco'], V(0, 0, Z_PLAT0))
    body = body.fuse(tube_ring(r, r - st, Z_PLAT0, Z_TUBE1 - Z_PLAT0))

    # Lenguetas: dos ranuras verticales y una horizontal encima de cada una.
    w_deg = math.degrees(NAIL['ancho'] / r)
    s_deg = math.degrees(NAIL['ranura'] / r)
    for a in NAIL['angulos']:
        for a0 in (a - w_deg / 2 - s_deg, a + w_deg / 2):
            body = body.cut(sector(r + 1, r - st - 1, zt, Z_NAIL_TOP + NAIL['ranura'] - zt,
                                   a0, s_deg))
        body = body.cut(sector(r + 1, r - st - 1, Z_NAIL_TOP, NAIL['ranura'],
                               a - w_deg / 2 - s_deg, w_deg + 2 * s_deg))
        body = body.fuse(nail(a, w_deg))

    # Separadores con piloto ciego para M2.5 que forma rosca.
    so = PLAT['separadores_alto']
    for hx, hy in HOLES:
        body = body.fuse(Part.makeCylinder(PLAT['separadores_diametro'] / 2, so + 0.5,
                                           V(hx, hy, zt - 0.5)))
    # Apoyos entre el chip y la hilera de pines, bajo cada agujero: la placa no
    # queda en voladizo al soldar. El dorso de la placa no lleva componentes.
    if PLAT.get('apoyos_traseros', True):
        y_pad = HOLE_Y - PLAT['apoyos_desde_linea_agujeros']
        for hx, _ in HOLES:
            body = body.fuse(box(hx - 1.25, hx + 1.25, y_pad - 1.25, y_pad + 1.25,
                                 zt - 0.5, zt + so))

    for hx, hy in HOLES:
        depth = IMU['piloto_profundidad']
        body = body.cut(Part.makeCylinder(IMU['piloto'] / 2, depth + 0.1,
                                          V(hx, hy, zt + so - depth)))

    # Ranura bajo la hilera de pines: pines hacia abajo o cables.
    rp = PLAT['ranura_pines']
    body = body.cut(box(HOLE_XM - rp['medio_largo'], HOLE_XM + rp['medio_largo'],
                        PIN_Y - rp['medio_ancho'], PIN_Y + rp['medio_ancho'],
                        Z_PLAT0 - 1, zt + 1))

    # Cruz del eje grabada fuera de la placa y una flecha hacia el frente:
    # con una regla se comprueba el centrado del chip ya montado. Arranca fuera
    # del sitio reservado para la placa mayor y de la palanca del selector.
    cw, cd = PLAT['cruz']['ancho'], PLAT['cruz']['profundidad']
    r_end = r - st - 1.5
    pc = PLAT['paso_cables']
    ax, ay = PLAT['alojamiento_placa']
    cx, cy = HOLE_XM, HOLE_Y + HOLE_E - BW / 2
    x_pos = cx + ax / 2 + IMU['selector_saliente'] + 1.0
    x_neg = cx - ax / 2 - 1.0
    y_pos = cy + ay / 2 + 1.0
    y_neg = min(cy - ay / 2, PIN_Y - rp['medio_ancho']) - 1.0
    marks = [
        box(x_pos, r_end, -cw / 2, cw / 2, zt - cd, zt + 0.1),
        box(-r_end, x_neg, -cw / 2, cw / 2, zt - cd, zt + 0.1),
        box(-cw / 2, cw / 2, y_pos, r_end - 5.0, zt - cd, zt + 0.1),
        box(-cw / 2, cw / 2, -(pc['radio_interior'] - 1.0), y_neg, zt - cd, zt + 0.1),
    ]
    tip = r_end - 0.5
    arrow = [V(-2.2, tip - 4.0, zt - cd), V(2.2, tip - 4.0, zt - cd), V(0, tip, zt - cd)]
    marks.append(Part.Face(Part.makePolygon(arrow + [arrow[0]])).extrude(V(0, 0, cd + 0.1)))
    for m in marks:
        body = body.cut(m)

    # Hueco del refuerzo del seguro y paso de cables atras.
    hs = PLAT['hueco_seguro']
    a0, a1 = hs['angulos']
    body = body.cut(sector(r + 1, r - st - 1, Z_TUBE1 - hs['desde_bajo_tapa'],
                           hs['desde_bajo_tapa'] + 1, a0, a1 - a0))
    a0, a1 = pc['angulos']
    body = body.cut(sector(r + 1, pc['radio_interior'], Z_PLAT0 - 1,
                           Z_TUBE1 - Z_PLAT0 + 2, a0, a1 - a0))
    return clean(body)


# --- Piezas 5 y 6: tapas de panel ------------------------------------------
def display_features():
    """Marco de la pantalla por dentro de la tapa (a 90 grados).

    El PCB apoya por la cara del vidrio en un plano; el vidrio y la mica entran
    en un bolsillo y la ventana, del tamano del area activa, se abre hacia fuera
    a 45 grados. Cuatro M2 sujetan el PCB por sus agujeros.
    """
    d = OLED
    W, H = d['pcb_ancho'], d['pcb_alto']
    zt, yf = d['z_borde_superior'], d['plano_apoyo_y']

    def xu(u):
        # Mirando la pantalla de frente, u crece a la derecha, que es -X.
        return -(u - W / 2.0)

    def xr(us):
        return min(xu(us[0]), xu(us[1])), max(xu(us[0]), xu(us[1]))

    def zr(vs):
        return zt - vs[1], zt - vs[0]

    m = d['marco_margen']
    z_lo, z_hi = zt - H - m, zt + m
    # Marco: bloque con su cara trasera plana y la de abajo a 45 grados, que
    # nace en la cara interior de la tapa.
    frame = yz_prism([(yf, z_lo + (RI - yf)), (yf, z_hi), (RO, z_hi), (RO, z_lo - (RO - RI))],
                     -(W / 2 + m), W / 2 + m)
    adds, cuts = [frame], []

    g = d['holgura_vidrio']
    depth = d['vidrio']['espesor'] + d['mica_espesor']
    x0, x1 = xr(d['vidrio']['u'])
    z0, z1 = zr(d['vidrio']['v'])
    cuts.append(box(x0 - g, x1 + g, yf - 1, yf + depth, z0 - g, z1 + g))
    for key in ('pines', 'flex'):
        x0, x1 = xr(d[key]['u'])
        z0, z1 = zr(d[key]['v'])
        cuts.append(box(x0, x1, yf - 1, yf + d[key]['relieve'], z0, z1))
    for u, v in d['agujeros']:
        cuts.append(Part.makeCylinder(d['piloto'] / 2, d['piloto_profundidad'] + 1,
                                      V(xu(u), yf - 1, zt - v), V(0, 1, 0)))

    # Ventana del area VISIBLE: el desfase del area activa no es igual en todas
    # las fuentes. Chaflan de 45 grados arriba y abajo, porque la pantalla se
    # mira desde abajo, y menor a los lados, para no comerse el labio que sujeta
    # la mica sobre la tapa curva.
    mg = d['margen_ventana']
    x0, x1 = xr(d['area_visible']['u'])
    z0, z1 = zr(d['area_visible']['v'])
    y_start, y_end = yf + depth - 0.3, RO + 2.0
    gz = (y_end - y_start) * math.tan(math.radians(d['chaflan_ventana']))
    gx = (y_end - y_start) * math.tan(math.radians(d['chaflan_ventana_lados']))
    cuts.append(Part.makeLoft([rect_y(x0 - mg, x1 + mg, z0 - mg, z1 + mg, y_start),
                               rect_y(x0 - mg - gx, x1 + mg + gx,
                                      z0 - mg - gz, z1 + mg + gz, y_end)], True))
    return adds, cuts


def button_features():
    """Boton de 12 mm: rebaje plano por fuera para la ceja y asiento plano por
    dentro para la tuerca. Sobre la tapa curva, sin ellos la ceja y la tuerca
    apoyarian en dos lineas y el boton bailaria."""
    b = BTN
    z = b['z']
    r_sf = b['asiento_exterior_diametro'] / 2
    y_sf = math.sqrt(RO ** 2 - r_sf ** 2)
    y_nut = b['asiento_tuerca_y']
    adds = [Part.makeCylinder(b['boss_diametro'] / 2, RI + 0.5 - y_nut,
                              V(0, y_nut, z), V(0, 1, 0))]
    cuts = [Part.makeCylinder(r_sf, 3.0, V(0, y_sf, z), V(0, 1, 0)),
            Part.makeCylinder(b['barreno'] / 2, RO + 3 - y_nut, V(0, y_nut - 1, z), V(0, 1, 0))]
    return adds, cuts


def usb_features():
    """Repisa con dos costillas detras del USB-C. La placa del receptaculo
    entra entre las costillas, apoya en la repisa y una brida rodea las dos."""
    u = USB
    if not u.get('soporte', True):
        return [], []
    z_lt = u['z'] - u['eje_sobre_cara_inferior_placa']
    t, yi, ct = u['repisa_espesor'], u['repisa_fondo_y'], u['costilla_espesor']
    half_in = u['placa_ancho'] / 2 + u['holgura_lateral']
    adds = [box(-half_in - ct, half_in + ct, yi, RI + 0.5, z_lt - t, z_lt)]
    # Costillas hasta la cara superior de la placa: la brida pasa por encima
    # de ellas y aprieta la placa contra la repisa.
    z_rib = z_lt + u['placa_espesor']
    z_b = z_lt - u['costilla_bajada']
    profile = [(yi, z_b + (RI - yi)), (yi, z_rib), (RO, z_rib), (RO, z_b - (RO - RI))]
    for x0 in (half_in, -half_in - ct):
        adds.append(yz_prism(profile, x0, x0 + ct))
    return adds, []


def build_panel(cfg, features, extra=None):
    """Tapa curva a ras. 'features' son los huecos simples de V2.1 y 'extra'
    devuelve lo que se suma y se resta dibujado a 90 grados."""
    gap = cfg['holgura']
    a0 = cfg['angulo'] - cfg['arco_grados'] / 2.0 + math.degrees(gap / RO)
    sweep = cfg['arco_grados'] - 2 * math.degrees(gap / RO)
    z0 = cfg['z_centro'] - cfg['alto'] / 2.0 + gap
    body = sector(RO, RO - cfg['espesor'], z0, cfg['alto'] - 2 * gap, a0, sweep)

    a = math.radians(cfg['angulo'])
    ux, uy = math.cos(a), math.sin(a)
    turn = cfg['angulo'] - 90.0

    if extra:
        envelope = Part.makeCylinder(RO - 0.01, 400, V(0, 0, -100))
        adds, cuts = [], []
        for fn in extra:
            a_list, c_list = fn()
            adds += a_list
            cuts += c_list
        for shape in adds:
            shape = shape.common(envelope)
            shape.rotate(V(), V(0, 0, 1), turn)
            body = body.fuse(shape)
        for shape in cuts:
            shape.rotate(V(), V(0, 0, 1), turn)
            body = body.cut(shape)

    def radial_cut(radius, z, depth=cfg['espesor'] + 4, offset=0.0):
        return Part.makeCylinder(radius, depth,
                                 V(ux * (RO + 2) - uy * offset,
                                   uy * (RO + 2) + ux * offset, z), V(-ux, -uy, 0))

    def radial_obround(width, height, z):
        """Hueco con extremos redondeados: un receptaculo USB-C no es un
        rectangulo."""
        depth = cfg['espesor'] + 6
        r = height / 2.0
        flat = max(width - height, 0.0)
        cut = Part.makeBox(flat, depth, height, V(-flat / 2, -3, z - r))
        for sign in (-1, 1):
            cut = cut.fuse(Part.makeCylinder(r, depth, V(sign * flat / 2, -3, z), V(0, 1, 0)))
        cut.rotate(V(), V(0, 0, 1), cfg['angulo'] - 90)
        cut.translate(V(ux * (RO - cfg['espesor'] - 1), uy * (RO - cfg['espesor'] - 1), 0))
        return cut

    for kind, *rest in features:
        if kind == 'box':
            width, height, z = rest
            body = body.cut(radial_obround(width, height, z))
        elif kind == 'hole':
            diameter, z = rest
            body = body.cut(radial_cut(diameter / 2, z))
        elif kind == 'pair':
            diameter, z, spacing = rest
            for sign in (-1, 1):
                body = body.cut(radial_cut(diameter / 2, z, offset=sign * spacing / 2))

    for dz in (-cfg['tornillo_separacion_z'] / 2, cfg['tornillo_separacion_z'] / 2):
        z = cfg['z_centro'] + dz
        body = body.cut(radial_cut(cfg['tornillo_paso_libre'] / 2, z))
        body = body.cut(radial_cut(cfg['tornillo_cabeza'] / 2, z,
                                   2.0 + cfg.get('cabeza_profundidad', 1.6)))
    return clean(body)


# --- Logo -------------------------------------------------------------------
def build_logo():
    path = ROOT / 'logo.json'
    if not path.exists():
        print('AVISO: falta logo.json; ejecuta dxf_logo.py. Se omite el grabado.')
        return None
    data = json.loads(path.read_text(encoding='utf-8'))
    width, depth = LOGO['ancho_mm'], LOGO['profundidad_grabado']
    faces = []
    for shape in sorted(data['shapes'], key=lambda s: s.get('depth', int(s['hole']))):
        # X negado: mirando la cara +Y con Z arriba, el eje X apunta a la
        # izquierda. Sin esto la marca sale espejeada en la pieza real.
        pts = [V(-p[0] * width, 0, p[1] * width + LOGO['z_centro'])
               for p in shape['points']]
        if len(pts) < 3:
            continue
        faces.append((shape.get('depth', int(shape['hole'])),
                      Part.Face(Part.makePolygon(pts + [pts[0]]))))
    if not faces:
        return None
    face = None
    for level, f in faces:
        if face is None:
            face = f
        elif level % 2:
            face = face.cut(f)
        else:
            face = face.fuse(f)
    solid = face.extrude(V(0, RO + 4.0, 0))
    solid = solid.cut(Part.makeCylinder(RO - depth, 400, V(0, 0, -100)))
    solid.rotate(V(), V(0, 0, 1), LOGO['angulo'] - 90.0)
    return clean(solid)


# --- Referencias: componentes comprados ------------------------------------
def build_references():
    """Componentes dibujados en su sitio para ver el montaje y comprobar
    choques. No se exportan."""
    refs = []

    board = box(BX0, BX0 + BL, BY0, BY0 + BW, Z_BOARD, Z_BOARD + BT)
    for hx, hy in HOLES:
        board = board.cut(Part.makeCylinder(IMU['agujero_diametro'] / 2, BT + 2,
                                            V(hx, hy, Z_BOARD - 1)))
    refs.append(('ref_imu_pcb', 'Ref: PCB del BMI088', board))
    chip = box(-CHIP['largo_x'] / 2, CHIP['largo_x'] / 2, -CHIP['ancho_y'] / 2,
               CHIP['ancho_y'] / 2, Z_BOARD + BT, Z_BOARD + BT + CHIP['alto'])
    refs.append(('ref_imu_chip', 'Ref: chip BMI088, centrado en el eje', chip))

    sh = PLAT['sma_alto']
    sma = Part.makeCylinder(4.5, sh, V(0, 0, Z_TUBE1 - sh))
    sma = sma.fuse(Part.makeCylinder(1.5, PLAT_R - 4.0, V(0, 0, Z_TUBE1 - sh + 4.0),
                                     V(0, -1, 0)))
    refs.append(('ref_sma', 'Ref: SMA macho acodado y coaxial', sma))
    refs.append(('ref_antenna', 'Ref: antena HA-901A',
                 Part.makeCylinder(ANT['diametro'] / 2, ANT['altura'], V(0, 0, Z_TOP))))

    d = OLED
    W, H, zt, yf = d['pcb_ancho'], d['pcb_alto'], d['z_borde_superior'], d['plano_apoyo_y']
    pcb = box(-W / 2, W / 2, yf - d['pcb_espesor'], yf, zt - H, zt)
    (u0, u1), (v0, v1) = d['vidrio']['u'], d['vidrio']['v']
    glass = box(-(u1 - W / 2), -(u0 - W / 2), yf, yf + d['vidrio']['espesor'],
                zt - v1, zt - v0)
    (u0, u1), (v0, v1) = d['pines']['u'], d['pines']['v']
    dupont = box(-(u1 - W / 2), -(u0 - W / 2), yf - d['pcb_espesor'] - C['oled']['dupont_detras'],
                 yf - d['pcb_espesor'], zt - v1, zt - v0 + 0.5)
    refs.append(('ref_oled', 'Ref: OLED 0.96 in con pines y Dupont', pcb.fuse(glass).fuse(dupont)))

    b = BTN
    r_sf = b['asiento_exterior_diametro'] / 2
    y_sf = math.sqrt(RO ** 2 - r_sf ** 2)
    zb = b['z']
    behind = b['largo_detras_panel']
    head = Part.makeCylinder(b['cabeza_diametro'] / 2, b['cabeza_alto_sobre_panel'],
                             V(0, y_sf, zb), V(0, 1, 0))
    thread = Part.makeCylinder(6.0, behind - b['terminales_largo'],
                               V(0, y_sf - (behind - b['terminales_largo']), zb), V(0, 1, 0))
    ac = b['tuerca_entre_caras'] / math.cos(math.radians(30))
    nut = Part.makeCylinder(ac / 2, b['tuerca_espesor'],
                            V(0, b['asiento_tuerca_y'] - b['tuerca_espesor'], zb), V(0, 1, 0))
    wires = C['boton']['cables_detras']
    lugs = box(-3.5, 3.5, y_sf - behind - wires, y_sf - behind + b['terminales_largo'],
               zb - 3.5, zb + 3.5)
    refs.append(('ref_button', 'Ref: boton 12 mm con tuerca y cables',
                 head.fuse(thread).fuse(nut).fuse(lugs)))

    pk = C['paquete']
    zp = pk['z_inferior']
    yf = -BACK['plano_frontal']
    bt, bw, bl = C['bateria']['peor_caso_documentado']
    battery = box(-bw / 2, bw / 2, yf, yf + bt, zp, zp + bl)
    refs.append(('ref_battery', 'Ref: bateria 955565, peor caso', battery))
    ut, uw, ul = C['carrier_um980']['publicado']
    y1 = yf + bt
    refs.append(('ref_um980', 'Ref: carrier UM980',
                 box(-bw / 2, -bw / 2 + uw, y1, y1 + ut, zp, zp + ul)))
    tt, tw, tl = C['thing_plus']['publicado']
    refs.append(('ref_thing_plus', 'Ref: Thing Plus ESP32-S3',
                 box(bw / 2 - tw, bw / 2, y1, y1 + tt, zp, zp + tl)))
    return refs


# --- Ensamble ---------------------------------------------------------------
doc = App.newDocument('TresVizoV22')
logo = build_logo()
parts = [
    ('01-threaded-base', 'Base con rosca 5/8', build_base()),
    ('02-logo-tube', 'Tubo con logo y respaldo de amarre', build_tube(logo)),
    ('03-antenna-cap', 'Tapa de antena', build_cap()),
    ('04-imu-platform', 'Plataforma del IMU', build_platform()),
    ('05-panel-cover', 'Tapa del panel principal', build_panel(PAN, [
        ('box', USB['ancho'], USB['alto'], USB['z']),
        ('pair', LED['diametro'], LED['z'], LED['separacion']),
    ], extra=(display_features, button_features, usb_features))),
    ('06-aux-panel-cover', 'Tapa del panel auxiliar', build_panel(AUX, [
        ('box', AUX['usbc_ancho'], AUX['usbc_alto'], AUX['usbc_z']),
    ])),
]
summary = []
for name, label, shape in parts:
    obj = doc.addObject('Part::Feature', name.replace('-', '_'))
    obj.Label = label
    obj.Shape = shape
    bb = shape.BoundBox
    summary.append({
        'pieza': name, 'etiqueta': label,
        'solidos': len(shape.Solids), 'valido': bool(shape.isValid()),
        'volumen_cm3': round(shape.Volume / 1000.0, 2),
        'caja': [round(bb.XLength, 2), round(bb.YLength, 2), round(bb.ZLength, 2)],
        'z': [round(bb.ZMin, 2), round(bb.ZMax, 2)],
    })
for name, label, shape in build_references():
    obj = doc.addObject('Part::Feature', name)
    obj.Label = label
    obj.Shape = shape
doc.recompute()
doc.saveAs(str(OUT / 'TresVizo-V2.2.FCStd'))

resumen = {
    'posicion': 'cerrada: dientes de base y tapa contra el fondo de su ranura',
    'giro_cierre_grados': round(GIRO_CIERRE, 2),
    'tapa_cierra_horario': SIGN_CAP < 0,
    'altura_total_mm': round(Z_TOP, 2),
    'diametro_exterior_mm': round(2 * RO, 2),
    'plano_alturas': {
        'piso_interior': round(Z_FLOOR, 2),
        'techo_interior': round(Z_CEIL, 2),
        'largo_util_mm': round(Z_CEIL - Z_FLOOR, 2),
        'cara_montaje_antena': round(Z_TOP, 2),
        'borde_superior_tubo': round(Z_TUBE1, 2),
        'fondo_cuello_tapa': round(Z_NECK_BOTTOM, 2),
        'seguro_base': round(Z_LOCK_BASE, 2),
        'seguro_tapa': round(Z_LOCK_CAP, 2),
        'plataforma_disco': [round(Z_PLAT0, 2), round(Z_PLAT1, 2)],
        'pcb_imu_cara_inferior': round(Z_BOARD, 2),
        'unas': [round(Z_NAIL, 3), round(Z_NAIL_TOP, 3)],
        'ventanas_cuello': [round(Z_WIN0, 3), round(Z_WIN1, 3)],
    },
    'imu': {
        'chip_xy_mm': [0.0, 0.0],
        'agujeros_xy_mm': [[round(x, 3), round(y, 3)] for x, y in HOLES],
        'placa_x_mm': [round(BX0, 3), round(BX0 + BL, 3)],
        'placa_y_mm': [round(BY0, 3), round(BY0 + BW, 3)],
    },
    'piezas': summary,
    'volumen_total_cm3': round(sum(s['volumen_cm3'] for s in summary), 2),
}
(OUT / 'model-index.json').write_text(json.dumps(resumen, indent=1), encoding='utf-8')
print(json.dumps(resumen, indent=1))
