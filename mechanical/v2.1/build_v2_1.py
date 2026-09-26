"""V2.1: carcasa TresVizo. Es V2 con 15 mm mas de diametro, 30 mm mas de
altura y un trineo que no se dobla ni se descentra.

Seis piezas: base con rosca, tubo con logo grabado, tapa de antena, trineo
universal y las dos tapas de panel. Todas las cotas salen de parameters.json.

Cambios del trineo frente a V2 (el propietario lo imprimio: se doblaba con la
mano y casi nunca quedaba centrado; solo lo sujetaban dos pestanas):
  - pie horizontal que apoya plano en la base y se atornilla con dos M3;
  - cuatro pestanas en vez de dos;
  - placa de 4 mm con dos alas en la cara +Y: perfil en U;
  - cartelas pie-placa en la cara -Y;
  - la repisa del IMU es un disco que entra en el cuello de la tapa con 0.3
    de holgura y chaflan; el cuello baja hasta ella y lleva chaflan de
    entrada: al cerrar, la tapa centra el extremo superior del trineo.

Tambien cambian la bayoneta, con base y tapa que cierran en el mismo sentido y
dibujadas cerradas para que los seguros coincidan, y el IMU, que baja 15 mm
para dejar sitio al conector del coaxial.

Ejes: Z es el eje del jalon, hacia arriba. FRONT es +Y. Origen en la cara de
apoyo del jalon (Z=0).

Criterio: solo antena, rosca 5/8 e IMU tienen posicion definida. El resto del
interior es rejilla de anclaje universal. Los tornillos de la carcasa roscan en
el plastico; el IMU lleva tuercas y los de la antena roscan en la antena.

Uso:
  <freecad>/bin/python build_v2_1.py [--output-dir generated]
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
V = App.Vector

TUBE, GRID, SLED = P['tubo'], P['rejilla_anclaje'], P['trineo']
IMU, ANT, INS = P['imu'], P['antena'], P['inserto_jalon']
BAY, LOCK, PAN = P['bayoneta'], P['seguro'], P['panel']
AUX, ACC = P['panel_aux'], P['accesorios']
LOGO, PR = P['logo'], P['impresion']

RO = TUBE['diametro_exterior'] / 2.0
RI = RO - TUBE['pared']
CLR = PR['holgura_general']

# --- Plano de alturas -------------------------------------------------------
Z_FLANGE_TOP = INS['barril_altura'] + INS['brida_espesor']
Z_FLOOR = Z_FLANGE_TOP + 4.0
Z_BATT_TOP = Z_FLOOR + SLED['zona_bateria']
Z_CEIL = Z_BATT_TOP + SLED['zona_imu']
Z_TUBE0 = 8.0
Z_TUBE1 = Z_CEIL + 2.0
# La antena se atornilla POR FUERA, sobre la cara superior de la tapa. La tapa
# no necesita cavidad: es una placa con tres pilotos y el paso del coaxial.
Z_TOP = Z_TUBE1 + ANT['espesor_tapa']

N_TEETH = BAY['numero_dientes']
TOOTH_H, TOOTH_A = BAY['diente_alto'], BAY['diente_largo_grados']
TRAVEL_A, BAY_CLR = BAY['tope_grados'], BAY['holgura']
COLLAR_T, COLLAR_H = BAY['collar_espesor'], BAY['collar_altura']
R_COLLAR = RI - COLLAR_T
R_SPIGOT = R_COLLAR - CLR
R_TOOTH = R_SPIGOT + TOOTH_H
R_GROOVE = R_TOOTH + BAY_CLR
# Ranura de bayoneta: empieza (TOOTH_A + 4)/2 antes del eje del diente y barre
# GROOVE_SPAN. Estas dos cifras las usan la ranura del tubo y el giro de cierre.
GROOVE_START = -(TOOTH_A + 4) / 2.0
GROOVE_SPAN = TOOTH_A + TRAVEL_A + 2 * BAY_CLR
# Giro real de cierre: lo que recorre el diente desde la entrada hasta tocar el
# fondo de la ranura. No son los 30 de `tope_grados`: la entrada tiene 2 grados
# de mas y la holgura suma 0.7. Da 28.7.
#
# V2 dibujaba base y tapa en la posicion de ENTRADA. Al cerrar giraban esos
# 28.7 grados y el barreno del seguro de cada una dejaba de coincidir con el
# del tubo: el tornillo no entraba. En V2.1 la base, el trineo y la tapa se
# dibujan CERRADOS, con el diente contra el fondo de la ranura: asi el seguro
# de las tres piezas cae en el mismo angulo, que es el del parametro.
GIRO_CIERRE = GROOVE_START + GROOVE_SPAN - TOOTH_A / 2.0
# Cuanto muerde un refuerzo dentro de la pared antes de sobresalir. Un refuerzo
# tangente a la superficie deja aristas degeneradas y OCC marca la pieza como
# "unorientable"; con mordida real la union es limpia.
BOSS_BITE = 0.8


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


def undercut_chamfer(shape, r_outer, depth, z_base):
    """Rebaja a 45 grados la cara inferior de un saliente interior.

    Imprimiendo el tubo de pie, cualquier resalte hacia dentro deja su cara
    inferior colgando. Un redondeo no lo arregla: arranca con tangente
    horizontal y el primer perimetro sigue en el aire. A 45 grados se
    autosoporta y no hacen falta soportes.
    """
    if not TUBE.get('chaflan_voladizos', True) or depth <= 0:
        return shape
    void = Part.makeCone(r_outer, max(r_outer - depth, 0.01), depth,
                         V(0, 0, z_base))
    return shape.cut(void)


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
# Sentido de cierre. Abajo el diente avanza hacia angulos positivos. Arriba, si
# `tapa_cierra_horario`, la ranura es la simetrica: la tapa cierra girando en
# sentido horario visto desde arriba, igual que la base respecto del tubo y que
# el equipo al enroscarse al jalon.
SIGN_BASE = 1
SIGN_CAP = -1 if BAY.get('tapa_cierra_horario', False) else 1


def bayonet_groove(z_entry, h_entry, z_groove, sign=1):
    """Canales de entrada mas sectores de ranura. Sectorial, no anillo: un
    anillo completo cortaba la pared y partia el tubo en dos. `sign` = -1 da
    la ranura simetrica, que cierra en sentido contrario."""
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


# Alturas de los seguros. La de la base cae entre la brida del inserto y el
# piso; a 1.8 sobre la brida su piloto ya no asoma al alojamiento de esta.
Z_LOCK_BASE = Z_FLANGE_TOP + LOCK.get('altura_sobre_brida', 1.2)
# Alto para librar la repisa del IMU, pero no tanto como para que el avellanado
# de 6 mm toque el borde superior del tubo: tangente ahi rompe la malla.
Z_LOCK_CAP = Z_TUBE1 - 5.0
# El cuello de la tapa baja `cuello_extra` por debajo del collar del tubo.
Z_NECK_BOTTOM = Z_TUBE1 - COLLAR_H - BAY.get('cuello_extra', 0.0)


# --- Pieza 1: base con rosca ------------------------------------------------
def build_base():
    ch = TUBE['chaflan_inferior']
    body = Part.makeCone(RO - ch, RO, ch, V(0, 0, 0))
    body = body.fuse(Part.makeCylinder(RO, Z_TUBE0 - ch, V(0, 0, ch)))
    body = body.fuse(tube_ring(R_SPIGOT, 0, Z_TUBE0, Z_FLOOR - Z_TUBE0))
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
    # base. Un barreno corto en la pared no sujeta nada.
    body = body.cut(radial_tool(LOCK['piloto'] / 2, LOCK['profundidad_base'],
                                LOCK['angulo'], Z_LOCK_BASE))

    # Ranuras de las cuatro pestanas del trineo. Holgura propia, mas justa que
    # la general: estas ranuras son las que ubican el trineo.
    tabs = SLED['pestanas']
    tw = tabs['ancho'] + tabs['holgura']
    tt = SLED['espesor'] + tabs['holgura']
    th = tabs['alto'] + 0.3
    ty = SLED['desplazamiento_y'] - tt / 2.0
    for tx in tabs['x']:
        body = body.cut(Part.makeBox(tw, tt, th, V(tx - tw / 2, ty, Z_FLOOR - th)))

    # Pilotos de los dos tornillos del pie: el M3 rosca en el macizo de la base.
    foot = SLED['pie']
    for fx, fy in foot['tornillos']:
        body = body.cut(Part.makeCylinder(foot['tornillo_piloto'] / 2,
                                          foot['tornillo_profundidad'] + 0.1,
                                          V(fx, fy,
                                            Z_FLOOR - foot['tornillo_profundidad'])))
    return clean(body)


# --- Pieza 2: tubo ----------------------------------------------------------
def panel_frame(cfg):
    """Engrosamiento interior, rebaje de la tapa y ventana pasante.

    La pared mide 2.5 y la tapa tambien: rebajar 2.5 la borraria. Por eso la
    zona del panel se engrosa HACIA DENTRO 2.5 mm mas. Asi el rebaje deja
    respaldo, la tapa queda a ras y los tornillos tienen donde roscar.
    """
    a0 = cfg['angulo'] - cfg['arco_grados'] / 2.0
    sweep = cfg['arco_grados']
    z0 = cfg['z_centro'] - cfg['alto'] / 2.0
    # Reborde distinto en vertical y en arco. Con un solo valor, 8 mm de arco a
    # este radio son 18.7 grados y se comian casi toda la ventana; en vertical
    # ese mismo valor es lo que necesita el tornillo para tener pared.
    lip_z = cfg['reborde_z']
    lip_a = cfg['reborde_arco']
    dlip = math.degrees(lip_a / RI)
    # El engrosamiento es lo que aporta la rosca ahora que no hay postes.
    pad_t = cfg.get('engrosamiento', cfg['espesor'])

    pad = sector(RI, RI - pad_t, z0 - lip_z, cfg['alto'] + 2 * lip_z,
                 a0 - dlip, sweep + 2 * dlip)
    # El engrosamiento tambien sobresale hacia dentro y su canto inferior
    # cuelga. Mismo criterio que el collar.
    pad = undercut_chamfer(pad, RI, pad_t, z0 - lip_z)
    rebate = sector(RO + 1, RO - cfg['espesor'], z0, cfg['alto'], a0, sweep)
    window = sector(RO + 1, RI - pad_t - 1,
                    z0 + lip_z, cfg['alto'] - 2 * lip_z,
                    a0 + dlip, sweep - 2 * dlip)
    return pad, rebate, window


def build_tube(logo_shape):
    body = tube_ring(RO, RI, Z_TUBE0, Z_TUBE1 - Z_TUBE0)
    # Collar inferior: su cara de abajo apoya en la cama, no cuelga.
    body = body.fuse(tube_ring(RI, R_COLLAR, Z_TUBE0, COLLAR_H))
    # Collar superior: su cara inferior si cuelga. Lleva chaflan a 45 grados.
    top_collar = tube_ring(RI, R_COLLAR, Z_TUBE1 - COLLAR_H, COLLAR_H)
    top_collar = undercut_chamfer(top_collar, RI, COLLAR_T, Z_TUBE1 - COLLAR_H)
    body = body.fuse(top_collar)
    body = body.cut(bayonet_groove(Z_TUBE0 - 1, 6.0, Z_TUBE0 + 4.0 - BAY_CLR))
    body = body.cut(bayonet_groove(Z_TUBE1 - 6.0, 7.0, Z_TUBE1 - 8.0 - BAY_CLR, SIGN_CAP))

    # Los dos paneles comparten construccion: ventana, engrosamiento y postes.
    for cfg in (PAN, AUX):
        pad, rebate, window = panel_frame(cfg)
        body = body.fuse(pad)
        half = cfg['tornillo_separacion_z'] / 2
        # Sin postes interiores: la rosca sale del engrosamiento de la pared.
        # Los postes quedaban al filo de la ventana y estorbaban.
        if cfg.get('postes', False):
            a = math.radians(cfg['angulo'])
            ux, uy = math.cos(a), math.sin(a)
            for dz in (-half, half):
                body = body.fuse(Part.makeCylinder(4.0, 7.0 + BOSS_BITE,
                                                   V(ux * (RI + BOSS_BITE),
                                                     uy * (RI + BOSS_BITE),
                                                     cfg['z_centro'] + dz),
                                                   V(-ux, -uy, 0)))
        body = body.cut(rebate).cut(window)
        for dz in (-half, half):
            body = body.cut(radial_tool(cfg['tornillo_piloto'] / 2, TUBE['pared'] + 12,
                                        cfg['angulo'], cfg['z_centro'] + dz))

    # Barrenos de accesorios: barreno pasante limpio, sin refuerzo interior.
    # El refuerzo estorbaba dentro del cuerpo; la sujecion se resuelve al
    # accesorizar, con tuerca o con lo que convenga entonces.
    for z in ACC['z']:
        for sign in (-1, 1):
            angle = ACC['angulo'] + sign * ACC['separacion_angular'] / 2.0
            if ACC.get('refuerzo', False):
                a = math.radians(angle)
                ux, uy = math.cos(a), math.sin(a)
                body = body.fuse(Part.makeCylinder(ACC['refuerzo_diametro'] / 2,
                                                   ACC['refuerzo_profundidad'] + BOSS_BITE,
                                                   V(ux * (RI + BOSS_BITE),
                                                     uy * (RI + BOSS_BITE), z),
                                                   V(-ux, -uy, 0)))
            body = body.cut(radial_tool(ACC['piloto'] / 2, TUBE['pared'] + 4,
                                        angle, z))

    # Seguros de bayoneta: el paso libre debe ATRAVESAR pared y collar; si se
    # queda dentro del collar el tornillo nunca alcanza la base ni la tapa.
    through = (RO + 2) - (R_COLLAR - 1.5)
    for z in (Z_LOCK_BASE, Z_LOCK_CAP):
        body = body.cut(radial_tool(LOCK['paso_libre'] / 2, through,
                                    LOCK['angulo'], z))
        body = body.cut(radial_tool(LOCK['cabeza_diametro'] / 2,
                                    LOCK['cabeza_profundidad'] + 2,
                                    LOCK['angulo'], z))

    # Lineas de diseno circunferenciales.
    gw, gd = TUBE['ranura_decorativa_ancho'], TUBE['ranura_decorativa_profundidad']
    for z in TUBE['ranuras_decorativas_z']:
        if Z_TUBE0 + 2 < z < Z_TUBE1 - 2:
            body = body.cut(tube_ring(RO + 1, RO - gd, z - gw / 2, gw))

    # Lineas verticales, en los sectores que no ocupa nada mas.
    vert = TUBE.get('lineas_verticales')
    if vert:
        z0, z1 = vert['z']
        dsweep = math.degrees(vert['ancho'] / RO)
        for angle in vert['angulos']:
            body = body.cut(sector(RO + 1, RO - vert['profundidad'],
                                   z0, z1 - z0, angle - dsweep / 2, dsweep))

    if logo_shape is not None:
        body = body.cut(logo_shape).removeSplitter()
    return clean(body)


# --- Pieza 3: tapa de antena ------------------------------------------------
def build_cap():
    """Placa superior. La antena va atornillada ENCIMA, no dentro: esta pieza
    solo aporta los tres pilotos, el paso del coaxial y el cierre del tubo.
    El cuello baja por debajo del collar para rodear la repisa del IMU."""
    z0 = Z_NECK_BOTTOM
    neck_ri = R_SPIGOT - TUBE['pared']
    body = Part.makeCylinder(RO, Z_TOP - Z_TUBE1, V(0, 0, Z_TUBE1))
    body = body.fuse(tube_ring(R_SPIGOT, neck_ri, z0, Z_TUBE1 - z0))
    body = body.fuse(bayonet_teeth(Z_TUBE1 - 8.0, SIGN_CAP))
    # Chaflan de coronacion en vez de canto vivo.
    body = body.cut(tube_ring(RO + 1, RO - 1.2, Z_TOP - 1.2, 1.3))

    # Paso libre de los tornillos de antena, no piloto: la antena trae sus
    # propias roscas. El tornillo sube desde dentro de la tapa y rosca en ella,
    # de modo que aqui solo hace falta que pase holgado.
    for i in range(ANT['numero_pernos']):
        a = math.radians(ANT['angulo_inicial'] + i * 360.0 / ANT['numero_pernos'])
        r = ANT['circulo_pernos'] / 2
        body = body.cut(Part.makeCylinder(ANT['perno_paso'] / 2,
                                          ANT['espesor_tapa'] + 2,
                                          V(r * math.cos(a), r * math.sin(a),
                                            Z_TOP - ANT['espesor_tapa'] - 1)))
    # Paso del coaxial hacia la antena exterior.
    body = body.cut(Part.makeCylinder(ANT['paso_coaxial'] / 2, Z_TOP - z0 + 2,
                                      V(0, 0, z0 - 1)))
    # Chaflan de entrada al pie del cuello: embudo que recoge la repisa del
    # IMU y la lleva al centro al bajar la tapa. Es un cono, no depende del
    # angulo: la tapa todavia gira 28.7 grados al cerrar la bayoneta.
    lead = BAY.get('chaflan_entrada_cuello', 0.0)
    if lead > 0:
        body = body.cut(Part.makeCone(neck_ri + lead, neck_ri, lead,
                                      V(0, 0, z0 - 0.01)))

    # Refuerzo local para el seguro: en el cuello solo hay 2.5 mm de pared.
    a = math.radians(LOCK['angulo'])
    ux, uy = math.cos(a), math.sin(a)
    # Muerde hacia DENTRO del cuello, nunca hacia fuera: sobresalir invadiria
    # el collar del tubo. Radio contenido para librar la repisa del IMU.
    boss = Part.makeCylinder(3.5, LOCK.get('boss_largo', 5.0),
                             V(ux * (R_SPIGOT - BOSS_BITE),
                               uy * (R_SPIGOT - BOSS_BITE), Z_LOCK_CAP),
                             V(-ux, -uy, 0))
    body = body.fuse(boss.cut(Part.makeCylinder(ANT['paso_coaxial'] / 2 + 0.5, 60,
                                                V(0, 0, z0 - 1))))
    body = body.cut(radial_tool(LOCK['piloto'] / 2, LOCK['profundidad_tapa'],
                                LOCK['angulo'], Z_LOCK_CAP))
    return clean(body)


# --- Pieza 4: trineo universal ----------------------------------------------
# Todo el trineo tiene que pasar por el collar de bayoneta del tubo, que baja
# por encima de el al montar: ese es el radio que manda.
R_PASO = R_COLLAR - SLED['holgura_lateral']


def build_sled():
    t, w = SLED['espesor'], SLED['ancho']
    off = SLED['desplazamiento_y']
    y0 = off - t / 2.0            # cara -Y, contra la bateria
    y1 = off + t / 2.0            # cara +Y, la de las placas
    foot = SLED['pie']
    ft = foot['espesor']
    z0, z1 = Z_FLOOR, Z_BATT_TOP
    envelope = Part.makeCylinder(R_PASO, z1 - z0 + 20, V(0, 0, z0 - 10))

    # Placa.
    body = Part.makeBox(w, t, z1 - z0, V(-w / 2, y0, z0))

    # Pie: apoya plano en el piso de la base. Es lo que hace el trineo
    # perpendicular y le quita el juego que tenian las dos pestanas de V2.
    fy0 = y0 - foot['vuelo']
    fy1 = y1 + foot['vuelo']
    body = body.fuse(Part.makeBox(w, fy1 - fy0, ft, V(-w / 2, fy0, z0)))

    # Alas en la cara +Y: con ellas la seccion es una U y no una hoja.
    wing = SLED['alas']
    wd, wt, wx = wing['profundidad'], wing['espesor'], wing['x_exterior']
    for sign in (-1, 1):
        x_in = sign * (wx - wt)
        x_out = sign * wx
        body = body.fuse(Part.makeBox(abs(x_out - x_in), wd, z1 - z0,
                                      V(min(x_in, x_out), y1, z0)))

    # Cartelas pie-placa en la cara -Y, donde no hay alas.
    gus = SLED['cartelas']
    for gx in gus['x']:
        tri = Part.makePolygon([V(gx - gus['espesor'] / 2, y0, z0 + ft),
                                V(gx - gus['espesor'] / 2, y0, z0 + ft + gus['alto']),
                                V(gx - gus['espesor'] / 2, y0 - gus['fondo'], z0 + ft),
                                V(gx - gus['espesor'] / 2, y0, z0 + ft)])
        body = body.fuse(Part.Face(tri).extrude(V(gus['espesor'], 0, 0)))

    # Recorte al paso del collar: el tubo baja por encima de todo esto.
    body = body.common(envelope)

    # Hueco central: el esparrago del jalon puede asomar por encima del
    # inserto. Ni el pie ni el canto de la placa deben tocarlo.
    body = body.cut(Part.makeCylinder(foot['radio_libre_centro'], ft + 4,
                                      V(0, 0, z0 - 1)))

    # Pasos de los dos tornillos del pie.
    for fx, fy in foot['tornillos']:
        body = body.cut(Part.makeCylinder(foot['tornillo_paso'] / 2, ft + 2,
                                          V(fx, fy, z0 - 1)))

    # Cuatro pestanas bajo la placa. Ubican; aprietan los tornillos.
    tabs = SLED['pestanas']
    for tx in tabs['x']:
        body = body.fuse(Part.makeBox(tabs['ancho'], t, tabs['alto'],
                                      V(tx - tabs['ancho'] / 2, y0, z0 - tabs['alto'])))

    # Rejilla de anclaje. Solo en la placa y entre las alas.
    sw, sh = GRID['ranura_ancho'], GRID['ranura_alto']
    rows = []
    z = z0 + ft + GRID.get('inicio', GRID['paso_longitudinal'])
    while z < z1 - GRID['paso_longitudinal'] / 2:
        rows.append(z)
        z += GRID['paso_longitudinal']
    # Fila extra junto al borde superior: por ella pasan las bridas que amarran
    # la bateria a lo largo, por encima de su extremo.
    if GRID.get('fila_superior'):
        top = z1 - GRID['fila_superior']
        if top - rows[-1] >= sh + 2.0:
            rows.append(top)
    for z in rows:
        for span in GRID['separacion_transversal']:
            for sign in (-1, 1):
                x = sign * span / 2
                if abs(x) + sw / 2 < wx - wt - GRID['borde_minimo']:
                    body = body.cut(Part.makeBox(sw, t + 4, sh,
                                                 V(x - sw / 2, y0 - 2, z - sh / 2)))

    pcb_w, pcb_d = 23.5, 18.0
    adj = IMU['ajuste_lateral']
    shelf_t = IMU['espesor_repisa']
    shelf_w = pcb_w + 2 * adj + 6.0
    shelf_z = Z_BATT_TOP + 2.0
    shelf_y0 = -(pcb_d / 2.0 + adj + 3.0)
    # Repisa en DISCO del radio del taladro del cuello menos la holgura: es lo
    # que centra el extremo superior del trineo cuando se cierra la tapa. En la
    # primera version de V2.1 era el rectangulo de V2 y no llegaba al cuello.
    r_neck = R_SPIGOT - TUBE['pared'] - IMU.get('holgura_cuello', 0.5)
    if IMU.get('repisa') == 'disco':
        shelf = Part.makeCylinder(r_neck, shelf_t, V(0, 0, shelf_z))
        notch = IMU.get('muesca_cables')
        if notch:
            a0, a1 = notch['angulos']
            shelf = shelf.cut(sector(r_neck + 1, notch['radio_interior'], shelf_z - 1,
                                     shelf_t + 2, a0, a1 - a0))
    else:
        shelf = Part.makeBox(shelf_w, y1 - shelf_y0, shelf_t,
                             V(-shelf_w / 2, shelf_y0, shelf_z))
        shelf = shelf.common(Part.makeCylinder(r_neck, shelf_t + 2,
                                               V(0, 0, shelf_z - 1)))
    # Chaflan en el canto superior de la repisa: con el del cuello, forma el
    # embudo que la mete en su sitio.
    cham = IMU.get('chaflan_repisa', 0.0)
    if cham > 0:
        ring = Part.makeCylinder(r_neck + 1, cham, V(0, 0, shelf_z + shelf_t - cham))
        ring = ring.cut(Part.makeCone(r_neck, r_neck - cham, cham,
                                      V(0, 0, shelf_z + shelf_t - cham)))
        shelf = shelf.cut(ring)
    body = body.fuse(shelf)
    body = body.fuse(Part.makeBox(shelf_w, t, 6.0,
                                  V(-shelf_w / 2, y0, shelf_z - 6.0)))

    # Separadores bajo los tornillos: elevan el PCB para que pase por encima de
    # la marca del eje y esta quede visible al montar.
    stand = IMU['pcb_separadores']
    s = IMU['agujeros_separacion'] / 2.0
    for sign in (-1, 1):
        x = sign * s
        pad = Part.makeBox(2 * adj + 5.0, 7.0, stand,
                           V(x - adj - 2.5, -3.5, shelf_z + shelf_t))
        body = body.fuse(pad)

    # Marca del eje: agujero pasante exactamente en X=0, Y=0.
    body = body.cut(Part.makeCylinder(IMU['marca_eje_diametro'] / 2,
                                      shelf_t + 4, V(0, 0, shelf_z - 2)))

    # Ranuras de paso libre del IMU.
    rt = IMU['tornillo_paso'] / 2.0
    for sign in (-1, 1):
        x = sign * s
        slot = Part.makeBox(2 * adj, 2 * rt, shelf_t + stand + 4,
                            V(x - adj, -rt, shelf_z - 2))
        for end in (-adj, adj):
            slot = slot.fuse(Part.makeCylinder(rt, shelf_t + stand + 4,
                                               V(x + end, 0, shelf_z - 2)))
        body = body.cut(slot)
    return clean(body)


# --- Pieza 5: tapa del panel ------------------------------------------------
def build_panel(cfg, features):
    """Tapa curva a ras. 'features' describe los huecos de cada panel."""
    gap = cfg['holgura']
    a0 = cfg['angulo'] - cfg['arco_grados'] / 2.0 + math.degrees(gap / RO)
    sweep = cfg['arco_grados'] - 2 * math.degrees(gap / RO)
    z0 = cfg['z_centro'] - cfg['alto'] / 2.0 + gap
    body = sector(RO, RO - cfg['espesor'], z0, cfg['alto'] - 2 * gap, a0, sweep)

    a = math.radians(cfg['angulo'])
    ux, uy = math.cos(a), math.sin(a)

    def radial_cut(radius, z, depth=cfg['espesor'] + 4, offset=0.0):
        return Part.makeCylinder(radius, depth,
                                 V(ux * (RO + 2) - uy * offset,
                                   uy * (RO + 2) + ux * offset, z), V(-ux, -uy, 0))

    def radial_obround(width, height, z):
        """Hueco con extremos redondeados. Un receptaculo USB-C no es un
        rectangulo: sus cantos cortos son semicirculos de radio medio alto."""
        depth = cfg['espesor'] + 6
        r = height / 2.0
        flat = max(width - height, 0.0)
        cut = Part.makeBox(flat, depth, height, V(-flat / 2, -3, z - r))
        for sign in (-1, 1):
            cut = cut.fuse(Part.makeCylinder(r, depth, V(sign * flat / 2, -3, z),
                                             V(0, 1, 0)))
        cut.rotate(V(), V(0, 0, 1), cfg['angulo'] - 90)
        cut.translate(V(ux * (RO - cfg['espesor'] - 1),
                        uy * (RO - cfg['espesor'] - 1), 0))
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
                body = body.cut(radial_cut(diameter / 2, z,
                                           offset=sign * spacing / 2))

    for dz in (-cfg['tornillo_separacion_z'] / 2, cfg['tornillo_separacion_z'] / 2):
        z = cfg['z_centro'] + dz
        body = body.cut(radial_cut(cfg['tornillo_paso_libre'] / 2, z))
        # Avellanado real: el corte empieza 2 mm fuera de la tapa. En V2 media
        # 1.6 desde ahi y no llegaba a tocarla.
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
    # Herramienta de grabado: se resta del tubo y deja la marca hundida.
    solid = face.extrude(V(0, RO + 4.0, 0))
    solid = solid.cut(Part.makeCylinder(RO - depth, 400, V(0, 0, -100)))
    solid.rotate(V(), V(0, 0, 1), LOGO['angulo'] - 90.0)
    return clean(solid)


# --- Ensamble ---------------------------------------------------------------
doc = App.newDocument('TresVizoV21')
logo = build_logo()
parts = [
    ('01-threaded-base', 'Base con rosca 5/8', build_base()),
    ('02-logo-tube', 'Tubo con logo grabado', build_tube(logo)),
    ('03-antenna-cap', 'Tapa de antena', build_cap()),
    ('04-universal-sled', 'Trineo universal', build_sled()),
    ('05-panel-cover', 'Tapa del panel principal', build_panel(PAN, [
        ('box', PAN['usb_ancho'], PAN['usb_alto'], PAN['usb_z']),
        ('hole', PAN['boton_diametro'], PAN['boton_z']),
        ('pair', PAN['led_diametro'], PAN['led_z'], PAN['led_separacion']),
    ])),
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
doc.recompute()
doc.saveAs(str(OUT / 'TresVizo-V2.1.FCStd'))

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
        'repisa_imu': round(Z_BATT_TOP + 2.0, 2),
        'seguro_base': round(Z_LOCK_BASE, 2),
        'seguro_tapa': round(Z_LOCK_CAP, 2),
    },
    'piezas': summary,
    'volumen_total_cm3': round(sum(s['volumen_cm3'] for s in summary), 2),
}
(OUT / 'model-index.json').write_text(json.dumps(resumen, indent=1), encoding='utf-8')
print(json.dumps(resumen, indent=1))
