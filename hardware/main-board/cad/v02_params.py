"""Parametros de la propuesta mecanica v0.2 (placa principal + carrier BDLX +
18650 + placa panel-usb) dentro de la carcasa V2.2.

Ejes del CAD de V2.2: Z = eje del jalon hacia arriba (origen en el asiento del
jalon), +Y = frente (panel), +X a la IZQUIERDA mirando el panel. mm.

Todo lo que no sale de parameters.json de V2.2 esta aqui, con su origen.
"""

# --- Placa panel-usb (opcion b: receptaculo horizontal, PCB horizontal) -------
PANEL_USB = {
    # Boca del receptaculo: centro en el eje del antiguo JST-XH (x = 0, z = 93.5)
    'z_axis': 93.5,
    # Cara frontal del receptaculo. 31.69 es donde sus esquinas (x = +-4.47)
    # tocan el cilindro exterior r = 32; en el centro queda 0.30 bajo la cara.
    'y_face': 31.70,
    # GCT USB4105-GF-A (plano B4, 18-12-2023): eje de la boca 1.73 sobre la
    # cara superior del PCB, alto total 3.31, ancho 8.94, largo 7.35; borde del
    # PCB recomendado = cara frontal del receptaculo; patas delanteras a 2.60
    # y traseras a 6.78 de la cara; pads de senal 1.15 de largo centrados a 6.78.
    'hc': 1.73, 'shell_w': 8.94, 'shell_h': 3.31, 'shell_l': 7.35,
    'footprint_half': 4.82,          # pads de las patas: +-4.32 +- 0.50
    'overhang': 0.40,                # receptaculo que asoma del canto del PCB
    'pcb_t': 1.6,
    'tongue_half': 5.2,              # lengua del PCB bajo el receptaculo
    'body_half': 10.4,               # medio ancho del cuerpo del PCB
    'body_front_y': 26.6,            # canto delantero del cuerpo (fuera de la lengua)
    'rear_y': 11.5,                  # canto trasero = cara de acople del PH 6P
    'corner_r': 0.5,
    # Orejas: tornillo M2 formando rosca desde arriba, a una mensula de la tapa
    'ear_x': 7.9, 'ear_y': 25.0,
    'ear_hole': 2.2,                 # NPTH en el PCB para M2
    'head_d': 4.0, 'head_h': 1.6,    # cabeza M2 (ISO 14583/7045 hasta 4.0)
    'pilot_d': 1.6, 'pilot_depth': 4.5,   # como el piloto M2 de la OLED en V2.2
    'bracket_x': (5.9, 10.2), 'bracket_y0': 22.6, 'bracket_front': 29.6,
    # JST S6B-PH-SM4-TB (catalogo JST ePH): ancho 15.9, cuerpo 6.0 de fondo +
    # 2.6 de patas detras, 5.5 de alto. Carcasa PHR-6: 13.8 x 4.5 x 6.85.
    'ph_half': 7.95, 'ph_depth': 6.0, 'ph_leads': 2.6, 'ph_h': 5.5,
    'plug_half': 6.9, 'plug_out': 3.5, 'plug_h': 4.5,   # PHR-6 asomando (estimado)
    'wire_bend': 4.0,                # reserva para doblar los 6 cables (estimado)
    # Hueco en la tapa. Variante "sobremolde" (pedida): 12.8 x 7.0 R1.2,
    # bajada 0.3 para que entre la lengua del PCB. Variante ajustada: 11.2 x 5.7.
    'opening': {'half_w': 6.4, 'z0': 89.7, 'z1': 96.7, 'r': 1.2},
    'opening_tight': {'half_w': 5.6, 'z0': 89.8, 'z1': 95.5, 'r': 0.8},
    'opening_cut_from_y': 28.6,
}

# LEDs de 3 mm: reserva supuesta (como en constraints.md 1.3): cilindro de 4 mm
# hacia dentro, para patas soldadas y termofit.
LEDS = {'x': 13.5, 'z': 93.5, 'd': 4.0, 'y_in': 11.2, 'y_out': 25.0}

# --- Placa principal (sandwich: bateria | carrier | placa | panel) -----------
MAIN = {
    'x': (-23.0, 23.0),              # 46 de ancho
    'y_back': 1.5, 't': 1.6,         # cara de componentes en y = 3.1, hacia el panel
    'z': (21.0, 85.0),               # 64 de alto
    'h_max': 10.0,                   # altura maxima general de componentes
    'edge_free': 2.5,                # cantos laterales libres (rieles)
    'button_keepout': {'x': 5.5, 'z': (38.0, 49.0), 'h': 0.0},
    'oled_zone': {'x': 7.25, 'z': (78.5, 85.0), 'h': 8.15},
    # Agujeros M2.5 (u, v) desde la esquina superior izquierda mirando la cara
    # de componentes; u = 23 - x, v = 85 - z.
    'holes_uv': [(10.0, 3.5), (36.0, 3.5)],
    'hole_d': 2.7,
    # Modulo ESP32-S3-MINI-1 con la antena en el canto +X (izquierda vista de frente)
    'esp_antenna': {'x': (17.5, 23.0), 'z': (52.0, 67.4), 'y_top': 5.5},
}

# Rieles de la placa principal en el tubo (aletas desde la pared)
RAILS = {'lip_in': 1.5, 'groove_clear': 0.3, 'groove_w': 2.0, 'lip_t': 1.0,
         'z': (25.5, 90.0)}
# Brazos traseros para los 2 M2.5 (detras de la placa, encima del carrier)
# Mensula a 45 grados en X desde la aleta del riel: su cara inferior sube de
# z = 69.5 en la aleta (|x| = 21.5) a z = 79 en |x| = 12 (encima del carrier).
ARMS = {'x_in': 10.0, 'y': (-5.0, 1.3), 'z_top': 85.0, 'z_under_at_fin': 69.5}

# --- Carrier BDLX RTK_UM98_V1.0.1 -------------------------------------------
# 32 x 52 x 11 publicado (envolvente). SMA hembra en un extremo corto (foto:
# ~13 mm fuera del PCB, a ~2.4 del centro). Se toma 11 en todo el largo.
CARRIER = {
    'x': (-21.0, 11.0), 'y': (-9.9, 1.1), 'z': (16.4, 68.4),
    'sma_x': -2.6, 'sma_y': -4.4, 'sma_d': 9.2, 'sma_len': 13.0,
    'plug_box': (9.0, 9.0, 11.0),    # SMA macho acodado (estimado)
}

# --- 18650 -------------------------------------------------------------------
BATTERY_1S = {'c': (0.0, -19.6), 'r': 9.3, 'z': (22.0, 91.0)}
BATTERY_2S = {'c': [(9.5, -17.14), (-9.5, -17.14)], 'r': 9.3, 'z': (22.0, 91.0)}

# Nervios del canal de la bateria (los de V2.2 en x = +-12, recortados)
RIBS = {'x': (-12.0, 12.0), 't': 2.5, 'y_front': -10.5}

# Coaxial carrier -> SMA de la antena (Ø3, RG178/RG316), trazado aproximado
# Pasa bajo el disco de la plataforma (z 99.91) y sube por su paso trasero
# (235-305 grados, desde r = 15) hasta el SMA acodado de la antena (z 113.9).
COAX_PATH = [(-2.6, -4.4, 92.4), (-2.6, -4.4, 96.0), (0.0, -17.5, 97.5),
             (0.0, -17.5, 113.9)]

# --- Alternativa T5: carrier contra la pared trasera, placa en medio, celdas
# delante a los lados (permite 2S) --------------------------------------------
T5 = {
    # Por encima del collar inferior: en su sitio sus esquinas quedan a r = 29.1
    'carrier': {'x': (-16.0, 16.0), 'y': (-24.3, -13.3), 'z': (21.5, 73.5),
                'sma_x': 2.4, 'sma_y': -18.8},
    # Las celdas delante a los lados quedan dentro de r = 25.3: pueden bajar al
    # collar; arriba tienen que quedar bajo la placa panel-usb (z 90.17).
    'cells_z': (18.0, 87.0),
    'main_y_back': -12.9,
    'cells_1s': [(15.5, 4.0)],
    'cells_2s': [(15.5, 4.0), (-15.5, 4.0)],
}
