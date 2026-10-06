"""V2.3: carcasa TresVizo para la placa principal v0.2 (rama hw/main-board-kicad).

Parte de V2.2 (main@94f00f9: Ø64 x 130, tuerca 5/8 de laton, panel con OLED,
boton de 12 mm y dos LEDs, plataforma del IMU en el cuello de la tapa, bandas de
TPU) y cambia solo el interior y el panel:

  - fuera el respaldo de amarre y los toalleros;
  - CHASIS DESLIZABLE (pieza nueva): la placa principal v0.2 corre en sus rieles
    y se atornilla por H1/H2 con el chasis FUERA del tubo; la carrier BDLX del
    UM980 entra por el frente antes que la placa y queda presa entre la placa,
    los labios traseros, los pisos y dos topes. Todo el chasis armado cabe en
    r 25.5 y entra por arriba (tapa de antena quitada) entre dos pares de
    nervios del tubo; apoya en dos topes sobre el collar inferior y la tapa,
    al cerrar, lo deja preso. No hay tornillos dentro del tubo;
  - cuna de la 18650 en la pared trasera (entra a presion antes que el chasis)
    con repisa y hueco para el cable;
  - ranura en la base bajo J102 para los cables de la bateria;
  - tapa del panel: hueco con la forma exacta del USB-C de la placa panel-usb y
    una cuna tipo cajon que la abraza sin tornillos, en lugar del JST-XH;
  - base con cuatro retenes en cruz sobre la tuerca; bandas de TPU que tapan
    los tornillos de la tapa del panel.

Ejes: Z es el eje del jalon, hacia arriba. FRONT es +Y. Origen en la cara de
apoyo del jalon (Z=0). Mirando la cara +Y con Z arriba, X apunta a la izquierda.

Los objetos ref_* del documento son componentes dibujados para ver y comprobar
el montaje. No se exportan ni se imprimen.

Uso:
  PYTHONPATH=<freecad>/lib <freecad>/bin/python build_v2_3.py [--output-dir generated]
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

TUBE, BODY = P['tubo'], P['cuerpo']
IMU, PLAT, ANT, NUT = P['imu'], P['plataforma_imu'], P['antena'], P['tuerca_jalon']
BAY, LOCK, PAN = P['bayoneta'], P['seguro'], P['panel']
ACC = P['accesorios']
CH, CUNA = P['chasis'], P['cuna_18650']
BANDS, FINISH = P['bandas'], P.get('acabados', {})
LOGO, PR = P['logo'], P['impresion']
OLED, BTN, USBP, LED = PAN['pantalla'], PAN['boton'], PAN['usb_c'], PAN['leds']

RO = TUBE['diametro_exterior'] / 2.0
RI = RO - TUBE['pared']
CLR = PR['holgura_general']

# --- Plano de alturas -------------------------------------------------------
Z_FLOOR = NUT['piso_z']
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
# dibujan CERRADAS para que los seguros coincidan con los del tubo. No depende
# del ancho del diente: el diente indice cierra igual que los otros.
GIRO_CIERRE = GROOVE_START + GROOVE_SPAN - TOOTH_A / 2.0
# Ancho de cada diente. El primero es el indice: mas ancho que las entradas de
# los otros, asi la pieza solo entra en una posicion.
TOOTH_WIDTHS = [BAY.get('diente_indice_grados', TOOTH_A)] + [TOOTH_A] * (N_TEETH - 1)
# Cuanto muerde un refuerzo dentro de la pared antes de sobresalir. Tangente,
# OCC marca la pieza como "unorientable".
BOSS_BITE = 0.8

SIGN_BASE = 1
SIGN_CAP = -1 if BAY.get('tapa_cierra_horario', False) else 1

Z_LOCK_BASE = Z_FLOOR - LOCK['bajo_piso_base']

# --- Tuerca del jalon -------------------------------------------------------
# Alojamiento hexagonal con las caras hacia 30, 90, 150... grados: los dos M3
# que la detienen, a 90 y 270, caen frente a una cara.
NUT_APOTHEM = (NUT['entre_caras'] + NUT['holgura_caras']) / 2.0
# Diametro menor de la rosca interior 5/8-11 (ASME B1.1, 0.527 in). Solo dibuja
# la tuerca de referencia.
THREAD_MINOR_5_8 = 13.4
# Cabeza de un M3 ISO 7380.
M3_BUTTON_HEAD = 5.7
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


def hex_prism(apothem, z0, h):
    """Prisma hexagonal sobre el eje Z: vertices a 0, 60, 120... grados, caras
    mirando a 30, 90, 150..."""
    rc = apothem / math.cos(math.radians(30))
    pts = [V(rc * math.cos(math.radians(60 * k)), rc * math.sin(math.radians(60 * k)), z0)
           for k in range(6)]
    return Part.Face(Part.makePolygon(pts + [pts[0]])).extrude(V(0, 0, h))


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
    simetrica, que cierra en sentido contrario. Cada ranura se hace a la medida
    de su diente: la del indice es mas ancha."""
    cuts = []
    for i in range(N_TEETH):
        a = i * 360.0 / N_TEETH
        w = TOOTH_WIDTHS[i]
        g_start = -(w + 4) / 2.0
        g_span = w + TRAVEL_A + 2 * BAY_CLR
        start = g_start if sign > 0 else -(g_start + g_span)
        cuts.append(sector(R_GROOVE, R_SPIGOT - 2, z_groove,
                           TOOTH_H + 2 * BAY_CLR, a + start, g_span))
        cuts.append(sector(R_GROOVE, R_SPIGOT - 2, z_entry, h_entry,
                           a - (w + 4) / 2.0, w + 4))
    shape = cuts[0]
    for c in cuts[1:]:
        shape = shape.fuse(c)
    return shape


def bayonet_teeth(z_tooth, sign=1):
    """Dientes en posicion CERRADA: contra el fondo de su ranura."""
    teeth = []
    for i in range(N_TEETH):
        a = i * 360.0 / N_TEETH + sign * GIRO_CIERRE
        w = TOOTH_WIDTHS[i]
        teeth.append(sector(R_TOOTH, R_SPIGOT - 1, z_tooth, TOOTH_H, a - w / 2.0, w))
    shape = teeth[0]
    for t in teeth[1:]:
        shape = shape.fuse(t)
    return shape


# --- Pieza 1: base con rosca ------------------------------------------------
def build_base():
    """Base con la tuerca 5/8-11 del jalon.

    La tuerca entra por dentro, con el tubo quitado, en un alojamiento
    hexagonal que no la deja girar, y apoya en un anillo de 2 mm cuya cara de
    abajo es el asiento contra el baston. Al apretar, el perno jala la tuerca
    contra el anillo y el anillo contra el hombro del baston: todo a
    compresion. Dos M3 con arandela ancha la detienen por arriba. Se imprime
    sin pausa: nada queda encerrado.
    """
    ch = TUBE['chaflan_inferior']
    body = Part.makeCone(RO - ch, RO, ch, V(0, 0, 0))
    body = body.fuse(Part.makeCylinder(RO, Z_TUBE0 - ch, V(0, 0, ch)))
    body = body.fuse(Part.makeCylinder(R_SPIGOT, Z_FLOOR - Z_TUBE0, V(0, 0, Z_TUBE0)))
    body = body.fuse(bayonet_teeth(Z_TUBE0 + 4.0))

    ring = NUT['anillo_asiento']
    r_hole = NUT['paso_perno_diametro'] / 2.0
    c = NUT['chaflan_paso']
    body = body.cut(Part.makeCylinder(r_hole, ring + 0.2, V(0, 0, -0.1)))
    # Entrada a 45 grados: guia el perno y se come la pata de elefante.
    body = body.cut(Part.makeCone(r_hole + c + 0.1, r_hole, c + 0.1, V(0, 0, -0.1)))
    body = body.cut(hex_prism(NUT_APOTHEM, ring, Z_FLOOR - ring + 0.1))

    ret = NUT['retenes']
    for a, rr in zip(ret['angulos'], ret['radios']):
        x = rr * math.cos(math.radians(a))
        y = rr * math.sin(math.radians(a))
        body = body.cut(Part.makeCylinder(ret['piloto'] / 2.0, ret['profundidad'] + 0.1,
                                          V(x, y, Z_FLOOR - ret['profundidad'])))

    # Ranura bajo J102: la clavija PH de la bateria asoma 3.5 mm del canto
    # inferior de la placa y su cable necesita sitio para doblar.
    rj = CH['ranura_base_j102']
    body = body.cut(box(rj['x'][0], rj['x'][1], rj['y'][0], rj['y'][1],
                        Z_FLOOR - rj['hondo'], Z_FLOOR + 1.0))

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


def build_tube_interior():
    """Nervios guia del chasis, topes sobre el collar inferior y cuna de la 18650.

    Los nervios van en pares, delante y detras de cada riel del chasis, de la
    pared hacia dentro hasta x = 23.6: guian el riel sin entrar en el paso del
    collar que usa el resto. Por debajo de z 30 no hay nervios: por ahi pasa el
    cable de la 18650 hacia J102, por fuera del riel -X. Los topes son dos
    dientes sobre el collar inferior, por encima de la espiga de la base, donde
    apoya el pie de cada riel. La cuna son dos nervios flexibles con labios y una
    repisa con hueco para el cable. Todo nace de la pared y se imprime de pie: lo
    que mira hacia abajo lleva rampa.
    """
    nv, tp, cu = CH['nervios_tubo'], CH['topes'], CUNA
    wall = RI + BOSS_BITE
    clip = Part.makeCylinder(wall, 400, V(0, 0, -100))
    out = None

    def add(shape):
        nonlocal out
        shape = shape.common(clip)
        out = shape if out is None else out.fuse(shape)

    z0, z1 = nv['z']
    for sx in (-1, 1):
        for (y0, y1) in (nv['delantero_y'], nv['trasero_y']):
            xa, xb = nv['x_interior'], RI + 1
            rib = box(min(sx * xa, sx * xb), max(sx * xa, sx * xb), y0, y1, z0, z1)
            # Pie a 45 grados: el nervio nace en la pared.
            dx = xb - xa
            pts = [(sx * xa, z0), (sx * xb, z0), (sx * xb, z0 - dx)]
            ramp = Part.Face(Part.makePolygon([V(x, y0, z) for x, z in pts] + [V(pts[0][0], y0, pts[0][1])])).extrude(V(0, y1 - y0, 0))
            add(rib.fuse(ramp))
        # Tope del riel sobre el collar inferior.
        r0, r1 = tp['r']
        ry0, ry1 = CH['riel']['y']
        za, zb = tp['z']
        stop = box(min(sx * r0, sx * (RI + 1)), max(sx * r0, sx * (RI + 1)), ry0, ry1, za, zb)
        add(stop)

    # Cuna de la 18650.
    ex, ey = cu['eje']
    rc = cu['diametro'] / 2.0
    zc0 = cu['z_inferior']
    zc1 = zc0 + cu['largo']
    nx0, nx1 = cu['nervio_x']
    ly0, ly1 = cu['labio_y']
    lx = cu['labio_x']
    for sx in (-1, 1):
        rib = box(min(sx * nx0, sx * nx1), max(sx * nx0, sx * nx1), -RI - 1, ly1, zc0 - 1.5, zc1 - 6)
        # Labio hacia el eje, delante del eje de la celda: la retiene.
        lip = box(min(sx * lx, sx * nx0), max(sx * lx, sx * nx0), ly0, ly1, cu['labio_z'][0], cu['labio_z'][1])
        add(rib.fuse(lip))
    rz0, rz1 = cu['repisa_z']
    shelf = box(-nx1, nx1, -RI - 1, ly1, rz0, rz1)
    shelf = shelf.cut(Part.makeCylinder(cu['repisa_hueco'] / 2.0, 10, V(ex, ey, rz0 - 2)))
    # Rampa bajo la repisa, desde la pared.
    ramp = yz_prism([(-RI - 1, rz0), (ly1, rz0), (-RI - 1, rz0 - (RI - abs(ly1)))], -nx1, nx1)
    ramp = ramp.cut(Part.makeCylinder(cu['repisa_hueco'] / 2.0, 40, V(ex, ey, rz0 - 30)))
    # Por encima de la espiga de la base (z 15.906).
    ramp = ramp.common(box(-50, 50, -50, 50, Z_FLOOR + 0.05, 200))
    cradle_block = shelf.fuse(ramp)
    # Canal del cable a ras del piso: del hueco hacia -X, por fuera del reten de la tuerca.
    cc = cu['canal_cable']
    za, zb = cc['z']
    cradle_block = cradle_block.cut(box(cc['x'][0], cc['x'][1], cc['y'][0], cc['y'][1], za - 1, zb))
    cradle_block = cradle_block.cut(box(cc['salida_x'][0], cc['salida_x'][1], cc['y'][0], cc['salida_y_frente'], za - 1, zb))
    es = cc['esquina']
    cradle_block = cradle_block.cut(box(es['x'][0], es['x'][1], es['y'][0], es['y'][1], za - 1, es['z_techo']))
    add(cradle_block)
    # La celda no debe tocar nada: hueco de la celda a traves de nervios y labios.
    cell = Part.makeCylinder(rc, cu['largo'], V(ex, ey, zc0))
    return out.cut(cell)


def build_sled():
    """Chasis deslizable: dos rieles, una placa superior con ventana grande que
    los une y lleva H1/H2, ranuras de la carrier, lengua sobre la 18650 y
    zapatas bajo el cuello de la tapa. Se recorta a r 25.5 para pasar el collar.

    No es una placa entera porque detras de la placa principal no hay sitio: la
    carrier va a 0.4 mm de ella y la 18650 a 0.4 mm de la carrier. La placa solo
    cabe encima de la carrier; abajo quedan los rieles con sus ranuras.
    """
    rl, cr, rc = CH['riel'], CH['carrier'], CH['ranuras_carrier']
    pl = CH['placa']
    xi, xe = rl['x_interior'], rl['x_exterior']
    ry0, ry1 = rl['y']
    rz0, rz1 = rl['z']
    yb, yf = pl['y_dorso'], pl['y_cara']
    parts = []
    for sx in (-1, 1):
        def bx(x0, x1, *rest):
            return box(min(sx * x0, sx * x1), max(sx * x0, sx * x1), *rest)
        # Riel: macizo fuera del canto de la placa y apoyo detras de la franja.
        # El de +X se corta frente a la antena del ESP32 (z 54-71).
        spans = [(rz0, rl['corte_antena_z'][0]), (rl['corte_antena_z'][1], rz1)] if sx > 0 else [(rz0, rz1)]
        for za, zb in spans:
            parts.append(bx(xi, xe, ry0, ry1, za, zb))
            parts.append(bx(rl['lengueta_x'], xi + 0.01, ry0, yb - 0.15, za, min(zb, rz1 - 3.2)))
        zones = rl['lengueta_z_mas_x'] if sx > 0 else rl['lengueta_z_menos_x']
        for za, zb in zones:
            parts.append(bx(rl['lengueta_x'], xi, rl['lengueta_y'][0], rl['lengueta_y'][1], za, zb))
            parts.append(bx(xi - 0.01, xe, ry1 - 0.01, rl['lengueta_y'][1], za, zb))
        # Ranura de la carrier en el canto de este lado.
        y0, y1 = rc['y']
        ly0, ly1 = rc['labio_y']
        edge = cr['x'][1] if sx > 0 else -cr['x'][0]
        cz0, cz1 = cr['z']
        zlim = rc['z_mas_x'] if sx > 0 else [rz0, cz1 + 0.5]
        parts.append(bx(edge + 0.2, xi, y0, ry0 + 0.5, zlim[0], zlim[1]))
        parts.append(bx(edge - rc['labio_ancho'], edge + 0.2, ly0, ly1, cz0, zlim[1]))
        parts.append(bx(edge - rc['labio_ancho'] - 1.0, edge + 0.2, y0, cr['y'][0] + cr['pcb'] + 0.2,
                        cz0 - rc['piso_alto'], cz0))

    # Placa superior: une los rieles, lleva H1 y H2 y deja una ventana grande.
    ps = CH['placa_superior']
    py0, py1 = ps['y']
    pz0, pz1 = ps['z']
    plate = box(-xe, xe, py0, py1, pz0, pz1)
    wx, wz = ps['ventana']['x'], ps['ventana']['z']
    plate = plate.cut(box(wx[0], wx[1], py0 - 1, py1 + 1, wz[0], wz[1]))
    # Sin plastico frente a la antena del ESP32: la esquina +X de abajo de la placa superior se recorta.
    az = CH.get('antena_esp32')
    if az:
        plate = plate.cut(box(az['x'][0] - 0.3, xe + 1, py0 - 1, py1 + 1, pz0 - 1, az['z'][1] + 0.4))
    parts.append(plate)
    rb = ps['boss_diametro'] / 2.0
    pilots = []
    for (hx, hz) in pl['agujeros']:
        parts.append(Part.makeCylinder(rb, py1 - ps['boss_y0'], V(hx, ps['boss_y0'], hz), V(0, 1, 0)))
        pilots.append(Part.makeCylinder(ps['piloto'] / 2.0, ps['piloto_hondo'],
                                        V(hx, yb - ps['piloto_hondo'], hz), V(0, 1, 0)))
    # Topes sobre los cantos de la carrier (por detras, sobre su PCB).
    for tx0, tx1 in ps['topes_carrier']:
        parts.append(box(tx0, tx1, ps['topes_y0'], py0 + 0.5, pz0, pz0 + ps['topes_alto']))
    # Enlace del tramo bajo del riel +X con la placa superior, por detras y lejos
    # de la antena (a ~10 mm de la placa principal).
    lk = CH['enlace_mas_x']
    parts.append(box(lk['x'][0], lk['x'][1], lk['y'][0], lk['y'][1], lk['z'][0], lk['z'][1]))
    # Lengua sobre la 18650.
    lb = CH['lengua_bateria']
    parts.append(box(lb['x'][0], lb['x'][1], lb['y'][0], py0 + 0.5, lb['z'][0], lb['z'][1]))
    # Zapatas bajo el cuello de la tapa, sobre cada riel.
    zp = CH['zapatas']
    for a0 in (0.0, 180.0):
        parts.append(sector(zp['r'][1], zp['r'][0], zp['z'][0], zp['z'][1] - zp['z'][0],
                            a0 - zp['medio_arco_grados'], 2 * zp['medio_arco_grados']))

    body = parts[0]
    for p in parts[1:]:
        body = body.fuse(p)
    for p in pilots:
        body = body.cut(p)
    # Muesca alrededor de los retenes de la tuerca del jalon.
    mr = CH['muesca_retenes']
    nr = NUT['retenes']
    for a, rr in zip(nr['angulos'], nr['radios']):
        body = body.cut(Part.makeCylinder(mr['radio'], mr['z_techo'] - 10,
                                          V(rr * math.cos(math.radians(a)), rr * math.sin(math.radians(a)), 10)))
    # Hueco de la placa: los rieles la reciben con 0.15 mm por cara.
    body = body.cut(box(-pl['x'][1] - 0.3, pl['x'][1] + 0.3, yb - 0.15, yf + 0.2, pl['z'][0], pl['z'][1] + 5))
    # Componentes de la carrier que salen de su envolvente de caja (medidos en foto, revisados con
    # su modelo por componentes): USB-C y placa del UM980 en el canto +X, soldaduras del arnes en el -X.
    rc = CH['ranuras_carrier']
    face = cr['y'][0] + cr['pcb']
    if 'rebaje_usb_mas_x' in rc:
        r = rc['rebaje_usb_mas_x']
        body = body.cut(box(r['x'][0], r['x'][1], rc['labio_y'][1], rl['y'][0] + 0.6, r['z'][0], r['z'][1]))
    if 'alivio_um980_mas_x' in rc:
        r = rc['alivio_um980_mas_x']
        body = body.cut(box(r['x'][0], r['x'][1], face - 0.5, rl['y'][0] + 0.6, r['z'][0], r['z'][1]))
    if 'corte_labio_menos_x' in rc:
        r = rc['corte_labio_menos_x']
        body = body.cut(box(cr['x'][0] - 1.0, cr['x'][0] + rc['labio_ancho'] + 0.1, rc['labio_y'][0] - 0.01,
                            cr['y'][0], r['z'][0], r['z'][1]))
    body = body.common(Part.makeCylinder(CH['radio_paso'], 400, V(0, 0, -100)))
    return clean(body)


def build_tube(logo_shape):
    body = tube_ring(RO, RI, Z_TUBE0, Z_TUBE1 - Z_TUBE0)
    # Collar inferior: su cara de abajo apoya en la cama, no cuelga.
    body = body.fuse(tube_ring(RI, R_COLLAR, Z_TUBE0, COLLAR_H))
    # Collar superior: su cara inferior si cuelga. Lleva chaflan a 45 grados.
    top_collar = tube_ring(RI, R_COLLAR, Z_TUBE1 - COLLAR_H, COLLAR_H)
    top_collar = undercut_chamfer(top_collar, RI, COLLAR_T, Z_TUBE1 - COLLAR_H)
    body = body.fuse(top_collar)
    body = body.fuse(build_tube_interior())
    body = body.cut(bayonet_groove(Z_TUBE0 - 1, 6.0, Z_TUBE0 + 4.0 - BAY_CLR))
    body = body.cut(bayonet_groove(Z_TUBE1 - 6.0, 7.0, Z_TUBE1 - 8.0 - BAY_CLR, SIGN_CAP))

    # Un solo panel: el auxiliar se quito.
    pad, rebate, window = panel_frame(PAN)
    body = body.fuse(pad)
    body = body.cut(rebate).cut(window)
    half = PAN['tornillo_separacion_z'] / 2
    for dz in (-half, half):
        body = body.cut(radial_tool(PAN['tornillo_piloto'] / 2, TUBE['pared'] + 12,
                                    PAN['angulo'], PAN['z_centro'] + dz))

    # Barrenos de accesorios: pasantes, sin refuerzo interior. Desactivados
    # mientras el de 324 grados apunte a la bateria.
    if ACC.get('activo', True):
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
    # Chaflan a 45 grados en el canto superior. Impresa boca abajo, ese canto
    # va en la cama y a 45 grados no cuelga; el escalon de V2.1 dejaba un
    # voladizo de 1.2 en un canto visto.
    c = 1.2
    body = body.cut(Part.makeCylinder(RO + 1, c + 1, V(0, 0, Z_TOP - c))
                    .cut(Part.makeCone(RO, RO - c - 1, c + 1, V(0, 0, Z_TOP - c))))

    # Paso libre de los tornillos de antena: roscan en la antena.
    for i in range(ANT['numero_pernos']):
        a = math.radians(ANT['angulo_inicial'] + i * 360.0 / ANT['numero_pernos'])
        r = ANT['circulo_pernos'] / 2
        body = body.cut(Part.makeCylinder(ANT['perno_paso'] / 2, ANT['espesor_tapa'] + 2,
                                          V(r * math.cos(a), r * math.sin(a),
                                            Z_TOP - ANT['espesor_tapa'] - 1)))
    # Ranura fina alrededor de la antena: enmarca su base. Impresa boca abajo
    # es un puente de 0.8 en la primera capa.
    ring = FINISH.get('anillo_antena')
    if ring:
        r_mid = ring['diametro'] / 2
        body = body.cut(tube_ring(r_mid + ring['ancho'] / 2, r_mid - ring['ancho'] / 2,
                                  Z_TOP - ring['profundidad'], ring['profundidad'] + 1))
    body = body.cut(Part.makeCylinder(ANT['paso_coaxial'] / 2, Z_TOP - z0 + 2,
                                      V(0, 0, z0 - 1)))
    # Chaflan de entrada al pie del cuello: guia la plataforma al meterla.
    lead = BAY.get('chaflan_entrada_cuello', 0.0)
    if lead > 0:
        body = body.cut(Part.makeCone(NECK_RI + lead, NECK_RI, lead, V(0, 0, z0 - 0.01)))

    # Refuerzo local para el seguro: en el cuello solo hay 2.5 mm de pared. Un
    # alma lo une a la placa: impresa boca abajo, el refuerzo solo quedaba en
    # mensula a 1.5 mm de la placa, justo donde va el piloto del M3. El alma cae
    # en el hueco de 181-205 grados de la falda de la plataforma.
    boss_len = LOCK.get('boss_largo', 5.0)
    r_boss = R_SPIGOT - BOSS_BITE
    boss = Part.makeCylinder(3.5, boss_len, V(r_boss, 0, Z_LOCK_CAP), V(-1, 0, 0))
    boss = boss.fuse(box(r_boss - boss_len, r_boss, -3.5, 3.5, Z_LOCK_CAP, Z_TUBE1 + 0.5))
    boss.rotate(V(), V(0, 0, 1), LOCK['angulo'])
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
    en un bolsillo y la ventana, del tamano del area visible, se abre hacia
    fuera: 45 grados arriba y abajo, 20 a los lados. Cuatro M2 sujetan el PCB
    por sus agujeros.
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
    # Marco: bloque con su cara trasera plana en toda la altura del PCB y la de
    # abajo a 45 grados hacia la tapa. Si el chaflan arrancara en la tapa, la
    # cara plana empezaria por encima de los dos agujeros de abajo y esos M2
    # apretarian contra el chaflan, doblando el canto del PCB.
    frame = yz_prism([(yf, z_lo), (yf, z_hi), (RO, z_hi), (RO, z_lo - (RO - yf))],
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
        if key == 'pines' and d['pines'].get('abierto_arriba', False):
            # Abierto hacia arriba: los pines y sus cables no quedan encerrados.
            z1 = z_hi + 1.0
        cuts.append(box(x0, x1, yf - 1, yf + d[key]['relieve'], z0, z1))
    for u, v in d['agujeros']:
        cuts.append(Part.makeCylinder(d['piloto'] / 2, d['piloto_profundidad'] + 1,
                                      V(xu(u), yf - 1, zt - v), V(0, 1, 0)))

    # Ventana del area VISIBLE: el desfase del area activa no es igual en todas
    # las fuentes. Chaflan de 45 grados arriba y abajo, porque la pantalla se
    # mira desde abajo, y menor a los lados, para no comerse el labio que sujeta
    # la mica sobre la tapa curva.
    # Arriba sin margen: el labio que sujeta la mica por arriba queda mas ancho.
    mg = d['margen_ventana']
    mg_top = d.get('margen_ventana_arriba', mg)
    x0, x1 = xr(d['area_visible']['u'])
    z0, z1 = zr(d['area_visible']['v'])
    y_start, y_end = yf + depth - 0.3, RO + 2.0
    gz = (y_end - y_start) * math.tan(math.radians(d['chaflan_ventana']))
    gx = (y_end - y_start) * math.tan(math.radians(d['chaflan_ventana_lados']))
    cuts.append(Part.makeLoft([rect_y(x0 - mg, x1 + mg, z0 - mg, z1 + mg_top, y_start),
                               rect_y(x0 - mg - gx, x1 + mg + gx,
                                      z0 - mg - gz, z1 + mg_top + gz, y_end)], True))
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
    """Placa panel-usb sin tornillos (ver panel.usb_c en parameters.json).

    - Hueco de la tapa con la forma exacta del receptaculo USB-C (estadio de
      8.94 x 3.2 mas holgura): por fuera solo se ve el conector, a ras.
    - Bolsillo de la lengueta del PCB en la cara interior de la tapa.
    - Cuna tipo cajon: piso bajo el PCB, paredes laterales con labios sobre sus
      cantos y un dedo flexible a cada lado de J502 que la retiene por su canto
      trasero. La placa entra deslizando hacia la tapa (+Y)."""
    u = USBP
    rc, pc, fl, wl, rt = u['receptaculo'], u['pcb'], u['piso'], u['pared'], u['reten']
    g = rc['holgura']
    hw = rc['ancho'] / 2.0 + g
    r = rc['alto'] / 2.0 + g
    zc = rc['z_eje']
    hole = box(-hw, hw, 26.0, RO + 3, zc - r, zc + r)
    ys = [e for e in hole.Edges if abs(e.Vertexes[0].Point.y - e.Vertexes[-1].Point.y) > 1.0]
    hole = hole.makeFillet(rc['radio_esquina'] + g, ys)
    hp = pc['holgura']
    z0, z1 = pc['z']
    tab = box(pc['lengueta_x'][0] - hp, pc['lengueta_x'][1] + hp, pc['y'][1] - 1.0,
              pc['lengueta_y'][1] + hp, z0 - hp, z1 + hp)
    # Cuna.
    xin = pc['x'][1] + hp
    y0 = fl['y0']
    zf0 = z0 - fl['espesor']
    floor = box(-wl['x'][1], wl['x'][1], y0, RO, zf0, z0)
    adds = [floor]
    zw1 = z1 + wl['alto_sobre_pcb']
    for sx in (-1, 1):
        x0, x1 = sorted((sx * wl['x'][0], sx * wl['x'][1]))
        adds.append(box(x0, x1, y0, RO, zf0, zw1))
        lx0, lx1 = sorted((sx * wl['labio_x'], sx * wl['x'][1]))
        adds.append(box(lx0, lx1, y0, RO, zw1 - wl['labio_espesor'], zw1))
    cuts = [hole, tab,
            box(-xin, xin, pc['y'][0] - hp, pc['y'][1] + 0.01, z0 - 0.01, z1 + hp)]
    # Retenes: dedo del piso (dos ranuras a sus lados, libre en el canto de atras
    # del piso) con un diente en rampa: la placa lo dobla hacia abajo al entrar y
    # su cara vertical detiene el canto trasero del PCB.
    yb = pc['y'][0] - hp
    for sx in (-1, 1):
        x0, x1 = sorted((sx * rt['x'][0], sx * rt['x'][1]))
        for xa, xb in ((x0 - 0.5, x0), (x1, x1 + 0.5)):
            cuts.append(box(xa, xb, y0 - 1, yb + rt['largo'], zf0 - 1, z0 + 0.01))
        adds.append(yz_prism([(y0 + 0.3, z0), (yb, z0), (yb, z0 + rt['diente'])], x0, x1))
    return adds, cuts


def build_panel_usb_ref():
    """Placa panel-usb con su contorno real (cuerpo + lengueta), USB-C y J502."""
    pc, rc = USBP['pcb'], USBP['receptaculo']
    z0, z1 = pc['z']
    ref = box(pc['x'][0], pc['x'][1], pc['y'][0], pc['y'][1], z0, z1)
    ref = ref.fuse(box(pc['lengueta_x'][0], pc['lengueta_x'][1], pc['lengueta_y'][0], pc['lengueta_y'][1], z0, z1))
    shell = box(-rc['ancho'] / 2.0, rc['ancho'] / 2.0, 23.8, rc['cara_y'],
                rc['z_eje'] - rc['alto'] / 2.0, rc['z_eje'] + rc['alto'] / 2.0)
    ys = [e for e in shell.Edges if abs(e.Vertexes[0].Point.y - e.Vertexes[-1].Point.y) > 1.0]
    shell = shell.makeFillet(rc['radio_esquina'], ys)
    ref = ref.fuse(shell)
    ref = ref.fuse(box(-6.63, 6.63, 11.73, 16.73, z1, 96.12))
    return ref


def build_panel(cfg, features, extra=None):
    """Tapa curva a ras. 'features' son los huecos simples de V2.1 y 'extra'
    devuelve lo que se suma y se resta dibujado a 90 grados."""
    gap = cfg['holgura']
    a0 = cfg['angulo'] - cfg['arco_grados'] / 2.0 + math.degrees(gap / RO)
    sweep = cfg['arco_grados'] - 2 * math.degrees(gap / RO)
    z0 = cfg['z_centro'] - cfg['alto'] / 2.0 + gap
    body = sector(RO, RO - cfg['espesor'], z0, cfg['alto'] - 2 * gap, a0, sweep)
    # Chaflan leve en el canto exterior: la junta con el tubo queda como una
    # linea en V intencionada y no como una rendija.
    ch = FINISH.get('chaflan_canto_tapa_panel', 0.0)
    if ch > 0:
        outer = [e for e in body.Edges
                 if all(abs(math.hypot(v.X, v.Y) - RO) < 0.01 for v in e.Vertexes)]
        try:
            body = body.makeChamfer(ch, outer)
        except Exception as error:
            print(f'AVISO: no se achaflano el canto de la tapa del panel ({error})')

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


# --- Piezas 6 y 7: bandas de TPU -------------------------------------------
def build_band(z0, z_screws):
    """Banda de proteccion para imprimir en TPU. Diametro interior menor que el
    cuerpo: el TPU se estira y aprieta. Por dentro, una ranura corrida a la
    altura de cada seguro de bayoneta, por si la cabeza del M3 asoma; corrida
    para que la banda entre en cualquier giro. Tambien en los tornillos de la
    tapa del panel que quedan debajo."""
    b = BANDS
    ri = RO - b['apriete_diametral'] / 2
    ro = ri + b['espesor']
    alto = b['alto_abajo'] if z0 < 1.0 else b['alto_arriba']
    body = tube_ring(ro, ri, z0, alto)
    edges = [e for e in body.Edges
             if hasattr(e.Curve, 'Radius') and abs(e.Curve.Radius - ro) < 0.01]
    if edges and b.get('redondeo', 0) > 0:
        try:
            body = body.makeFillet(b['redondeo'], edges)
        except Exception as error:
            print(f'AVISO: no se redondearon los cantos de la banda ({error})')
    for z in z_screws:
        body = body.cut(tube_ring(ri + b['ranura_profundidad'], ri - 1,
                                  z - b['ranura_alto'] / 2, b['ranura_alto']))
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
    wires = box(-(u1 - W / 2), -(u0 - W / 2), yf - d['pcb_espesor'] - C['oled']['cables_detras'],
                yf - d['pcb_espesor'], zt - v1, zt - v0 + 0.5)
    refs.append(('ref_oled', 'Ref: OLED 0.96 in con pines y cables soldados', pcb.fuse(glass).fuse(wires)))

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

    # Placa principal v0.2, carrier, 18650 y panel-usb (hardware/main-board/cad).
    pl, cr, cu = CH['placa'], CH['carrier'], CUNA
    refs.append(('ref_main_board', 'Ref: PCB de la placa principal v0.2',
                 box(pl['x'][0], pl['x'][1], pl['y_dorso'], pl['y_cara'], pl['z'][0], pl['z'][1])))
    carrier = box(cr['x'][0], cr['x'][1], cr['y'][0], cr['y'][1], cr['z'][0], cr['z'][1])
    sx0, sx1 = cr['sma']['x']
    carrier = carrier.fuse(box(sx0, sx1, cr['y'][0], cr['y'][1], cr['z'][1], cr['z'][1] + cr['sma']['alto']))
    pt = cr['sma'].get('patas')
    if pt:   # patas del SMA que asoman por detras de la carrier, hacia la 18650
        carrier = carrier.fuse(box(pt['x'][0], pt['x'][1], cr['y'][0] - pt['atras'], cr['y'][0], pt['z'][0], pt['z'][1]))
    refs.append(('ref_carrier', 'Ref: carrier BDLX (envolvente medida en foto) con SMA y sus patas', carrier))
    ex, ey = cu['eje']
    refs.append(('ref_battery', 'Ref: 18650 en su cuna',
                 Part.makeCylinder(cu['diametro'] / 2.0, cu['largo'], V(ex, ey, cu['z_inferior']))))
    pusb = build_panel_usb_ref()
    refs.append(('ref_panel_usb', 'Ref: placa panel-usb con USB-C y J502', pusb))
    # Clavijas enchufadas y reserva de sus cables (hardware/main-board/kicad/plugs.json).
    plugs_path = ROOT.parent.parent / 'hardware' / 'main-board' / 'kicad' / 'plugs.json'
    if plugs_path.exists():
        pj = json.loads(plugs_path.read_text(encoding='utf-8'))
        zt, yfc = pj['z_top'], pj['y_face'] + CH.get('desplazamiento_placa_y', 0.0)
        shapes = []
        for pg in pj['plugs']:
            for key in ('plug', 'wires'):
                us = [u for u, v in pg[key]]
                vs = [v for u, v in pg[key]]
                shapes.append(box(23 - max(us), 23 - min(us), yfc, yfc + pg['h'], zt - max(vs), zt - min(vs)))
        plugs = shapes[0]
        for sh in shapes[1:]:
            plugs = plugs.fuse(sh)
        refs.append(('ref_plugs', 'Ref: clavijas enchufadas y doblez de sus cables', plugs))

    # Tuerca del jalon sobre su anillo, con el diametro menor de su rosca.
    ring = NUT['anillo_asiento']
    nut = hex_prism(NUT['entre_caras'] / 2.0, ring, NUT['alto'])
    nut = nut.cut(Part.makeCylinder(THREAD_MINOR_5_8 / 2, NUT['alto'] + 2, V(0, 0, ring - 1)))
    refs.append(('ref_nut', 'Ref: tuerca 5/8-11 de laton', nut))
    ret = NUT['retenes']
    keepers = []
    for a, rr, dw in zip(ret['angulos'], ret['radios'], ret['arandela_diametros']):
        x = rr * math.cos(math.radians(a))
        y = rr * math.sin(math.radians(a))
        washer = Part.makeCylinder(dw / 2, ret['arandela_espesor'],
                                   V(x, y, Z_FLOOR))
        head = Part.makeCylinder(M3_BUTTON_HEAD / 2, ret['cabeza_alto'],
                                 V(x, y, Z_FLOOR + ret['arandela_espesor']))
        keepers.append(washer.fuse(head))
    refs.append(('ref_nut_keepers', 'Ref: arandelas y cabezas de los M3 que detienen la tuerca',
                 keepers[0].fuse(keepers[1:])))

    return refs

# --- Ensamble ---------------------------------------------------------------
def band_screws(z0):
    """Alturas de los tornillos exteriores cuya cabeza queda bajo una banda que
    empieza en z0: los dos seguros de bayoneta y los de la tapa del panel."""
    half = PAN['tornillo_separacion_z'] / 2
    heads = [(Z_LOCK_BASE, LOCK['cabeza_diametro']), (Z_LOCK_CAP, LOCK['cabeza_diametro']),
             (PAN['z_centro'] - half, PAN['tornillo_cabeza']),
             (PAN['z_centro'] + half, PAN['tornillo_cabeza'])]
    z1 = z0 + (BANDS['alto_abajo'] if z0 < 1.0 else BANDS['alto_arriba'])
    return [z for z, d in heads if z + d / 2 > z0 and z - d / 2 < z1]


doc = App.newDocument('TresVizoV23')
logo = build_logo()
parts = [
    ('01-threaded-base', 'Base con rosca 5/8', build_base()),
    ('02-logo-tube', 'Tubo con logo, nervios guia y cuna de la 18650', build_tube(logo)),
    ('03-antenna-cap', 'Tapa de antena', build_cap()),
    ('04-imu-platform', 'Plataforma del IMU', build_platform()),
    ('05-panel-cover', 'Tapa del panel principal', build_panel(PAN, (
        [('pair', LED['diametro'], LED['z'], LED['separacion'])] if LED.get('activo', True) else []
    ), extra=(display_features, button_features, usb_features))),
    ('08-sled', 'Chasis deslizable de la placa principal y la carrier', build_sled()),
    ('06-bumper-bottom', 'Banda de TPU de abajo', build_band(0.0, band_screws(0.0))),
    ('07-bumper-top', 'Banda de TPU de arriba',
     build_band(Z_TOP - BANDS['alto_arriba'], band_screws(Z_TOP - BANDS['alto_arriba']))),
]
summary = []
for name, label, shape in parts:
    obj = doc.addObject('Part::Feature', name.replace('-', '_'))
    obj.Label = label
    obj.Shape = shape
    # optimalBoundingBox: la caja normal de OCC sale holgada en los redondeos.
    bb = shape.optimalBoundingBox()
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
doc.saveAs(str(OUT / 'TresVizo-V2.3.FCStd'))

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
        'banda_abajo': [0.0, BANDS['alto_abajo']],
        'banda_arriba': [round(Z_TOP - BANDS['alto_arriba'], 2), round(Z_TOP, 2)],
        'ranuras_banda_abajo': [round(z, 2) for z in band_screws(0.0)],
        'ranuras_banda_arriba': [round(z, 2) for z in band_screws(Z_TOP - BANDS['alto_arriba'])],
    },
    'arp_sobre_asiento_jalon_mm': round(Z_TOP, 2),
    '_nota_arp': 'Del asiento del jalon (cara inferior de la base) a la cara de la tapa donde apoya la antena.',
    'tuerca_jalon': {
        'alojamiento_entre_caras_mm': round(2 * NUT_APOTHEM, 3),
        'alojamiento_z_mm': [NUT['anillo_asiento'], round(Z_FLOOR, 3)],
        'paso_perno_diametro_mm': NUT['paso_perno_diametro'],
        'retenes_xy_mm': [[round(rr * math.cos(math.radians(a)), 3), round(rr * math.sin(math.radians(a)), 3)]
                          for a, rr in zip(NUT['retenes']['angulos'], NUT['retenes']['radios'])],
    },
    'usb_c_panel': {
        'receptaculo_mm': [USBP['receptaculo']['ancho'], USBP['receptaculo']['alto']],
        'z_eje_mm': USBP['receptaculo']['z_eje'],
        'holgura_mm': USBP['receptaculo']['holgura'],
    },
    'chasis': {
        'riel_x_mm': [CH['riel']['x_interior'], CH['riel']['x_exterior']],
        'riel_z_mm': CH['riel']['z'],
        'placa_superior_z_mm': CH['placa_superior']['z'],
        'radio_paso_mm': CH['radio_paso'],
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
