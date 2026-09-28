"""Pila de alturas y posiciones del Meridian3. Python puro, sin FreeCAD.

La altura del equipo NO es un parametro: sale de apilar, de abajo arriba, lo que
tiene que caber en el eje. La usan build_meridian3.py, bom.py, layout_check.py y
capacity_check.py, para que todos trabajen con las mismas cifras.

Ejes como en V2 y V2.1: Z es el eje del jalon, hacia arriba; FRONT es +Y (donde
esta el panel del USB-C); origen en la cara de apoyo del jalon.

Pila en el eje, de abajo arriba:
  inserto 5/8 (barril + brida) -> suelo de la base -> pie del trineo
  -> hueco del conector inferior del carrier (+ carrera de ajuste)
  -> carrier (52) -> SMA del carrier (11)
  -> clavija recta inferior del latiguillo -> tramo libre de cable (+ carrera)
  -> clavija recta superior -> SMA de la antena bajo la tapa -> tapa (5)

Ejecutarlo solo imprime la pila y compara con los 106.9 de V2.
"""
import json, math, pathlib

ROOT = pathlib.Path(__file__).resolve().parent
P = json.loads((ROOT / 'parameters.json').read_text(encoding='utf-8'))
C = json.loads((ROOT / 'components.json').read_text(encoding='utf-8'))

V2_ALTURA_TOTAL = 106.91      # model-index.json de V2: altura total con la tapa
V2_BORDE_TUBO = 101.91        # V2: borde superior del tubo = cara inferior de la tapa

TUBE, BAY, PR = P['tubo'], P['bayoneta'], P['impresion']
SLED, INS, ANT = P['trineo'], P['inserto_jalon'], P['antena']
CAR, COAX, TINY = C['carrier_um980'], C['latiguillo'], C['esp32_tiny']

# --- Radios ------------------------------------------------------------------
RO = TUBE['diametro_exterior'] / 2.0
RI = RO - TUBE['pared']
R_COLLAR = RI - BAY['collar_espesor']
R_SPIGOT = R_COLLAR - PR['holgura_general']
NECK_RI = R_SPIGOT - TUBE['pared']
R_PASO = R_COLLAR - SLED['holgura_lateral']        # todo lo del trineo cabe aqui

# --- Carrier en planta ---------------------------------------------------------
car_t, car_w, car_l = CAR['publicado']
SMA = CAR['sma']
CAR_X0 = P['disposicion']['carrier_desplazamiento_x'] - car_w / 2.0
CAR_X1 = CAR_X0 + car_w
# La cara trasera se fija para que el SMA quede en y=0, en el eje de la antena.
CAR_Y0 = -SMA['eje_sobre_cara_trasera']
CAR_Y1 = CAR_Y0 + car_t
CAR_PCB_TOP_Y = CAR_Y0 + 1.6
SMA_X = P['disposicion']['carrier_desplazamiento_x'] + SMA['eje_x_desde_centro']
SMA_Y = 0.0

# --- Placa del trineo en planta -------------------------------------------------
PLATE_Y1 = SLED['cara_delantera_y']
PLATE_Y0 = PLATE_Y1 - SLED['espesor']

# --- Alturas -------------------------------------------------------------------
Z_FLANGE_TOP = INS['barril_altura'] + INS['brida_espesor']
Z_FLOOR = Z_FLANGE_TOP + P['base']['suelo_sobre_brida']
Z_FOOT_TOP = Z_FLOOR + SLED['pie']['espesor']
AJUSTE = CAR['ajuste_vertical']
Z_CAR0 = Z_FOOT_TOP + CAR['conector_inferior']['hueco_necesario'] + AJUSTE
Z_CAR1 = Z_CAR0 + car_l
Z_SMA_TIP = Z_CAR1 + SMA['sobresale']
Z_PLUGC_TOP = Z_SMA_TIP + COAX['clavija_recta_mas_alla_de_la_punta']
Z_PLUGA_BOT = Z_PLUGC_TOP + COAX['tramo_libre']
Z_ANT_TIP = Z_PLUGA_BOT + COAX['clavija_recta_mas_alla_de_la_punta']
Z_TUBE1 = Z_ANT_TIP + C['antena']['sma_bajo_tapa']
Z_TOP = Z_TUBE1 + ANT['espesor_tapa']
Z_TUBE0 = 8.0

RING = SLED['anillo']
Z_RING0 = Z_PLUGC_TOP + RING['sobre_clavija']
Z_RING1 = Z_RING0 + RING['espesor']
Z_NECK_BOTTOM = Z_RING0 - 1.0
Z_PLATE_TOP = Z_NECK_BOTTOM - 0.5      # la placa no entra en el cuello; el puente si
CUELLO_EXTRA = Z_TUBE1 - BAY['collar_altura'] - Z_NECK_BOTTOM

# --- Panel -----------------------------------------------------------------------
PAN = P['panel']
PANEL_Z = Z_NECK_BOTTOM - PAN['bajo_cuello'] - PAN['tornillo_separacion_z'] / 2.0
WINDOW_Z = (PANEL_Z - PAN['alto'] / 2.0 + PAN['reborde_z'],
            PANEL_Z + PAN['alto'] / 2.0 - PAN['reborde_z'])
USB_Z = PANEL_Z + PAN['usb_sobre_centro']

# --- Tiny detras de la placa -------------------------------------------------------
tiny_env = TINY['envolvente']
TINY_Y1 = PLATE_Y0 - P['disposicion']['tiny_separacion_placa']
TINY_Y0 = TINY_Y1 - tiny_env[0]
TINY_Z0 = Z_CAR1 + P['disposicion']['tiny_sobre_carrier']
TINY_Z1 = TINY_Z0 + tiny_env[2]

# --- Seguros -----------------------------------------------------------------------
LOCK = P['seguro']
Z_LOCK_BASE = Z_FLANGE_TOP + LOCK['altura_sobre_brida']
Z_LOCK_CAP = Z_TUBE1 - 5.0


def resumen():
    return {
        'radios': {'exterior': RO, 'interior_tubo': RI, 'collar': R_COLLAR,
                   'espigon': round(R_SPIGOT, 2), 'taladro_cuello': round(NECK_RI, 2),
                   'paso_trineo': round(R_PASO, 2)},
        'pila_mm': {
            'cara_superior_brida_inserto': round(Z_FLANGE_TOP, 2),
            'suelo_base': round(Z_FLOOR, 2),
            'cara_superior_pie': round(Z_FOOT_TOP, 2),
            'carrier_abajo': round(Z_CAR0, 2),
            'carrier_arriba': round(Z_CAR1, 2),
            'punta_sma_carrier': round(Z_SMA_TIP, 2),
            'fin_clavija_inferior': round(Z_PLUGC_TOP, 2),
            'inicio_clavija_superior': round(Z_PLUGA_BOT, 2),
            'punta_sma_antena': round(Z_ANT_TIP, 2),
            'borde_superior_tubo': round(Z_TUBE1, 2),
            'cara_montaje_antena': round(Z_TOP, 2),
        },
        'anillo_mm': [round(Z_RING0, 2), round(Z_RING1, 2)],
        'fondo_cuello_tapa_mm': round(Z_NECK_BOTTOM, 2),
        'cuello_bajo_collar_mm': round(CUELLO_EXTRA, 2),
        'panel_centro_mm': round(PANEL_Z, 2),
        'ventana_mm': [round(WINDOW_Z[0], 2), round(WINDOW_Z[1], 2)],
        'eje_usb_mm': round(USB_Z, 2),
        'altura_total_mm': round(Z_TOP, 2),
        'frente_a_v2_mm': round(Z_TOP - V2_ALTURA_TOTAL, 2),
    }


if __name__ == '__main__':
    print(json.dumps(resumen(), indent=1, ensure_ascii=False))
