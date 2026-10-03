"""Genera la lista de tornilleria de V2.2 a partir de los parametros del modelo.

Las longitudes se calculan con la geometria real, no se estiman: para cada
tornillo se mide desde donde apoya la cabeza hasta donde termina su barreno, y
se elige la medida comercial que cabe.

Salida: SCREW-BOM.md, y generated/screws.json con los largos elegidos, que
capacity_check.py usa para comprobar paredes y distancias.
"""
import json, math, pathlib

ROOT = pathlib.Path(__file__).resolve().parent
P = json.loads((ROOT / 'parameters.json').read_text(encoding='utf-8'))

RO = P['tubo']['diametro_exterior'] / 2
RI = RO - P['tubo']['pared']
R_COLLAR = RI - P['bayoneta']['collar_espesor']
R_SPIGOT = R_COLLAR - P['impresion']['holgura_general']

# Medidas que se consiguen sin buscar. Se omiten 5, 7, 9 y 11: existen pero no
# se encuentran en cualquier ferreteria.
COMERCIALES = [4, 6, 8, 10, 12, 14, 16, 20, 25, 30]


def comercial_que_cabe(util, agarre_minimo):
    """Tornillo que rosca en un piloto ciego: el mas largo que NO pase del fondo
    del piloto (con 0.5 de margen)."""
    validos = [m for m in COMERCIALES if agarre_minimo <= m <= util - 0.5]
    if not validos:
        raise SystemExit(f'Ningun tornillo comercial cabe en {util:.1f} mm con '
                         f'{agarre_minimo} de agarre: revisar el piloto.')
    return max(validos)


filas = []
notas = []
largos = {}

# --- Seguros de bayoneta ---------------------------------------------------
seg = P['seguro']
cabeza = RO - seg['cabeza_profundidad']
# El tornillo cruza primero la pared del tubo sin rosca: el agarre minimo se
# cuenta desde ahi.
sin_rosca = cabeza - R_SPIGOT
for clave, donde, fondo in (('seguro_base', 'Seguro de la base. Rosca en el macizo de la base.',
                             seg['profundidad_base']),
                            ('seguro_tapa', 'Seguro de la tapa. Rosca en el refuerzo del cuello.',
                             seg['profundidad_tapa'])):
    util = cabeza - ((RO + 2) - fondo)
    largos[clave] = comercial_que_cabe(util, sin_rosca + 6)
    filas.append(('M3 cabeza boton ISO 7380', largos[clave], 1, donde,
                  f'piloto util {util:.1f} mm; rosca {largos[clave] - sin_rosca:.1f} mm'))

# --- Tornillos de los dos paneles ------------------------------------------
# El de arriba del panel principal queda 0.4 mm bajo el cuello de la tapa: su
# punta no puede salir del engrosamiento. Mismo largo para los dos de cada tapa.
for clave, nombre in (('panel', 'principal'),):
    cfg = P[clave]
    r_pad = RI - cfg['engrosamiento']
    asiento = RO - cfg.get('cabeza_profundidad', 1.6)
    util = asiento - r_pad
    largo = comercial_que_cabe(util + 0.5, asiento - RI + 1.5)
    largos[clave] = largo
    filas.append(('M3 cabeza boton ISO 7380', largo, 2,
                  f'Tapa del panel {nombre}. Rosca en el engrosamiento.',
                  f'rosca {largo - (asiento - RI):.1f} mm; la punta no sale del engrosamiento'))
notas.append(
    'Tornillos del panel: NO poner uno mas largo que el de la lista. El de '
    'arriba queda a menos de 1 mm del cuello de la tapa, que gira al cerrar la '
    'bayoneta: si asoma, la tapa no cierra.')

# --- Antena ----------------------------------------------------------------
ant = P['antena']
rosca_antena = ant.get('rosca_profundidad', 4.0)
largo_antena = comercial_que_cabe(ant['espesor_tapa'] + rosca_antena, ant['espesor_tapa'] + 3)
filas.append((f'{ant["metrica"]} cilindrica ISO 4762', largo_antena, 3,
              'Antena. Sube desde dentro y rosca en la antena.',
              f'tapa {ant["espesor_tapa"]:.0f} + {largo_antena - ant["espesor_tapa"]:.0f} '
              f'de {rosca_antena:.0f} de rosca en la antena'))
notas.append(
    'Los tres tornillos de la antena y los tres del hombro van ANTES que la '
    'plataforma del IMU: sus cabezas quedan dentro del cuello de la tapa.')

# --- Hombro de la antena ---------------------------------------------------
sh = P['hombro']
largos['hombro'] = comercial_que_cabe(ant['espesor_tapa'] + sh['piloto_profundidad'],
                                      ant['espesor_tapa'] + 3)
filas.append((f'{ant["metrica"]} cilindrica ISO 4762', largos['hombro'], 3,
              'Hombro de la antena. Sube desde dentro de la tapa y rosca en el hombro.',
              f'tapa {ant["espesor_tapa"]:.0f} + piloto {sh["piloto_profundidad"]} en el hombro'))

# --- IMU -------------------------------------------------------------------
imu = P['imu']
# Avellanado: el largo comercial incluye la cabeza, que queda `cabeza_sobre_placa`
# por encima de la placa porque asienta en el canto del agujero de 3.0.
sobre = imu['cabeza_sobre_placa']
largos['imu'] = comercial_que_cabe(sobre + imu['placa_espesor'] + imu['piloto_profundidad'],
                                   sobre + imu['placa_espesor'] + 3.0)
filas.append(('M2.5 cabeza avellanada ISO 10642 o DIN 965', largos['imu'], 2,
              'BMI088 sobre la plataforma. Rosca en el separador.',
              f'cabeza {sobre} sobre la placa + PCB {imu["placa_espesor"]} + '
              f'piloto {imu["piloto_profundidad"]}'))
notas.append(
    'Los dos M2.5 del IMU tienen que ser de cabeza AVELLANADA: el cono asienta en '
    'el canto del agujero de 3.0 y centra la placa sobre el piloto. Con cabeza '
    'cilindrica quedan 0.25 mm de juego por lado y el chip ya no cae en el eje. '
    'Sin tuercas ni arandelas.')

# --- Pantalla --------------------------------------------------------------
d = P['panel']['pantalla']
largos['pantalla'] = comercial_que_cabe(d['pcb_espesor'] + d['piloto_profundidad'],
                                        d['pcb_espesor'] + 2.0)
filas.append(('M2 cilindrica ISO 4762 o cabeza plana', largos['pantalla'], 4,
              'Pantalla OLED contra su marco. Rosca en el marco.',
              f'PCB {d["pcb_espesor"]} + piloto {d["piloto_profundidad"]}'))
notas.append(
    'Los agujeros de la pantalla son de 2.0 segun el plano del vendedor y el M2 '
    'entra justo. Si no pasa, repasar el agujero con broca de 2.2 o usar M1.6x4.')

# --- Boton -----------------------------------------------------------------
bt = P['panel']['boton']
r_sf = bt['asiento_exterior_diametro'] / 2
espesor_boton = math.sqrt(RO ** 2 - r_sf ** 2) - bt['asiento_tuerca_y']
filas.append(('Tuerca M12x0.75 del boton', None, 1,
              'Viene con el boton. Asienta en el plano interior de la tapa.',
              f'panel de {espesor_boton:.1f} mm en el eje del boton'))
notas.append(
    'La tuerca del boton queda a unos 10 mm del marco de la pantalla: apretarla '
    'con pinzas o con una llave de 14 delgada, antes de montar la pantalla.')

# --- Accesorios ------------------------------------------------------------
acc = P['accesorios']
if acc.get('activo', True):
    filas.append(('M4 formando rosca, o M3 con tuerca', None, 2,
                  f'Barrenos de accesorios, {acc["piloto"]} mm pasantes.',
                  'a discrecion segun lo que montes'))

# --- Inserto ---------------------------------------------------------------
filas.append(('McMaster 90611A121', None, 1, 'Rosca 5/8-11 UNC hembra del jalon.',
              'capturado en la base; ver el pendiente del README'))

lineas = ['# Tornilleria de V2.2', '',
          'Generado por `bom.py` desde `parameters.json` (lo ejecuta `regenerate.py`). Las longitudes salen de',
          'la geometria del modelo, no de una estimacion: se mide desde el asiento',
          'de la cabeza hasta el fondo del barreno y se elige la medida comercial que cabe.',
          '',
          '**Nada de esto se ha montado ni ensayado.**', '',
          '## Carcasa', '',
          '| Pieza | Largo | Cant. | Donde | Calculo |',
          '| --- | ---: | ---: | --- | --- |']
for nombre, largo, cant, donde, calculo in filas:
    largo_txt = f'{largo} mm' if largo else '—'
    lineas.append(f'| {nombre} | {largo_txt} | **{cant}** | {donde} | {calculo} |')

tornillos = sum(c for _, l, c, _, _ in filas if l)
lineas += ['',
           f'**{tornillos} tornillos con longitud definida.** Sin tuercas sueltas: '
           'todos roscan en el plastico o en la antena.', '']

lineas += ['## Lo de dentro', '',
           'Nada de lo de dentro se atornilla: bateria, carrier UM980, Thing Plus y',
           'lo demas se amarran con bridas al respaldo del tubo o a los cuatro',
           'toalleros. Varias de esas placas no tienen patron de agujeros publicado.', '']

if notas:
    lineas += ['## Advertencias', '']
    lineas += [f'- {n}' for n in notas]
    lineas.append('')

lineas += ['## Consumibles',
           '',
           '| Consumible | Cantidad | Uso |',
           '| --- | ---: | --- |',
           '| Brida de 2.5 a 3.6 mm, 150-200 mm | 10-15 | Paquete contra el respaldo |',
           '| Brida de 2.5 mm, 100 mm | 2 | Placa del USB-C a su repisa |',
           '| Brida de 2.5 mm, 100-150 mm | 4-8 | Componentes extra en los toalleros |',
           '| Lamina transparente de 1 mm (acrilico o PETG), 26.7 x 19.3 | 1 | Mica de la pantalla |',
           '| Filamento TPU 95A | ~25 g | Las dos bandas de proteccion |',
           '| Cinta de espuma o fieltro adhesivo | segun bateria | Entre bateria y respaldo |',
           '| Llave Allen 2 mm | 1 | M3 cabeza boton y M2.5 cilindrica de la antena |',
           '| Llave Allen 1.5 mm o desarmador Phillips 0 | 1 | M2 de la pantalla y M2.5 avellanado del IMU |',
           '| Llave de 14 mm o pinzas | 1 | Tuerca del boton |',
           '']

(ROOT / 'generated').mkdir(exist_ok=True)
(ROOT / 'generated' / 'screws.json').write_text(json.dumps(largos, indent=1), encoding='utf-8')
destino = ROOT / 'SCREW-BOM.md'
destino.write_text('\n'.join(lineas), encoding='utf-8')
print('\n'.join(lineas[:30]))
print(f'\nescrito: {destino}')
