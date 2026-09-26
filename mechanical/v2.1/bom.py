"""Genera la lista de tornilleria de V2.1 a partir de los parametros del modelo.

Las longitudes se calculan con la geometria real, no se estiman: para cada
tornillo se mide desde donde apoya la cabeza hasta donde termina su barreno, y
se redondea a la medida comercial inmediata superior.

Salida: SCREW-BOM.md, y generated/screws.json con los largos elegidos, que
capacity_check.py usa para comprobar paredes y distancias.
"""
import json, math, pathlib

ROOT = pathlib.Path(__file__).resolve().parent
P = json.loads((ROOT / 'parameters.json').read_text(encoding='utf-8'))
C = json.loads((ROOT / 'components.json').read_text(encoding='utf-8'))

RO = P['tubo']['diametro_exterior'] / 2
RI = RO - P['tubo']['pared']
R_COLLAR = RI - P['bayoneta']['collar_espesor']
R_SPIGOT = R_COLLAR - P['impresion']['holgura_general']

# Medidas que se consiguen sin buscar. Se omiten 5, 7, 9 y 11: existen pero no
# se encuentran en cualquier ferreteria.
COMERCIALES = [4, 6, 8, 10, 12, 14, 16, 20, 25, 30]


def comercial(minimo, sobrante=0.0):
    """Medida comercial inmediata. 'sobrante' es cuanto puede asomar el tornillo
    por dentro sin chocar con nada; permite subir a la medida que si se
    consigue en vez de forzar una rara."""
    for medida in COMERCIALES:
        if medida >= minimo + 0.5 and medida <= minimo + sobrante + 0.5:
            return medida
    for medida in COMERCIALES:
        if medida >= minimo + 0.5:
            return medida
    return COMERCIALES[-1]


def comercial_que_cabe(util, agarre_minimo):
    """Tornillo que rosca en un piloto ciego: el mas largo que NO pase del fondo
    del piloto (con 0.5 de margen). V2 usaba `comercial` aqui y elegia uno mas
    largo que el piloto, que se atoraba contra el plastico macizo."""
    validos = [m for m in COMERCIALES if agarre_minimo <= m <= util - 0.5]
    if not validos:
        raise SystemExit(f'Ningun tornillo comercial cabe en {util:.1f} mm con '
                         f'{agarre_minimo} de agarre: revisar el piloto.')
    return max(validos)


filas = []
notas = []

# --- Seguros de bayoneta ---------------------------------------------------
seg = P['seguro']
cabeza = RO - seg['cabeza_profundidad']
largos = {}
# El tornillo cruza primero la pared del tubo sin rosca (de la cabeza hasta el
# macizo de la base o de la tapa): el agarre minimo se cuenta desde ahi.
sin_rosca = cabeza - R_SPIGOT
fin_base = (RO + 2) - seg['profundidad_base']
util = cabeza - fin_base
largos['seguro_base'] = comercial_que_cabe(util, sin_rosca + 6)
filas.append(('M3 cabeza boton ISO 7380', largos['seguro_base'], 1,
              'Seguro de la base. Rosca en el macizo de la base.',
              f'piloto util {util:.1f} mm; rosca {largos["seguro_base"] - sin_rosca:.1f} mm'))

fin_tapa = (RO + 2) - seg['profundidad_tapa']
util = cabeza - fin_tapa
largos['seguro_tapa'] = comercial_que_cabe(util, sin_rosca + 6)
filas.append(('M3 cabeza boton ISO 7380', largos['seguro_tapa'], 1,
              'Seguro de la tapa. Rosca en el refuerzo del cuello de la tapa.',
              f'piloto util {util:.1f} mm; rosca {largos["seguro_tapa"] - sin_rosca:.1f} mm'))

# --- Pie del trineo --------------------------------------------------------
pie = P['trineo']['pie']
agarre_min = 6.0
util_max = pie['espesor'] + pie['tornillo_profundidad']
largo = comercial_que_cabe(util_max, pie['espesor'] + agarre_min)
largos['pie'] = largo
filas.append(('M3 cabeza boton ISO 7380', largo, len(pie['tornillos']),
              'Pie del trineo contra el piso de la base. Rosca en la base.',
              f'pie {pie["espesor"]:.0f} + piloto {pie["tornillo_profundidad"]:.0f}; '
              f'no pasar de {util_max:.0f}'))
notas.append(
    'Los dos tornillos del pie del trineo van ANTES que las placas: quedan debajo '
    'de ellas. Son los que quitan el juego que tenian las dos pestanas de V2; '
    'apretarlos con el trineo asentado en sus cuatro ranuras.')

# --- Tornillos de los dos paneles ------------------------------------------
# Detras de cada panel hay algo: el canto de la bateria tras el auxiliar y el
# carrier del UM980 tras el principal. La punta tiene que quedarse a 0.5 mm.
# En V2 esto decia "puede asomar 14 mm" y detras del auxiliar habia 1 mm.
bat_semiancho = C['bateria']['peor_caso_documentado'][1] / 2
um_cara = (P['trineo']['desplazamiento_y'] + P['trineo']['espesor'] / 2
           + C['carrier_um980']['publicado'][0])
obstaculos = {'panel': (um_cara, 'carrier UM980'), 'panel_aux': (bat_semiancho, 'bateria')}
for clave, nombre in (('panel', 'principal'), ('panel_aux', 'auxiliar')):
    cfg = P[clave]
    r_pad = RI - cfg['engrosamiento']
    asiento = RO - cfg.get('cabeza_profundidad', 1.6)
    obst, que = obstaculos[clave]
    util = asiento - (obst + 0.5)
    # El mas corto que atraviese todo el engrosamiento; si no cabe, el mas
    # largo que no llegue al obstaculo.
    enteros = [m for m in COMERCIALES if asiento - r_pad <= m <= util]
    largo = min(enteros) if enteros else comercial_que_cabe(util + 0.5, asiento - RI + 1.5)
    largos[clave] = largo
    filas.append(('M3 cabeza boton ISO 7380', largo, 2,
                  f'Tapa del panel {nombre}. Rosca en el engrosamiento.',
                  f'rosca {min(largo, asiento - r_pad) - (asiento - RI):.1f} mm; '
                  f'{que} detras: nunca mas largo'))
notas.append(
    'Tornillos de los paneles: NO poner uno mas largo que el de la lista. Detras '
    'del panel auxiliar esta el canto de la bateria a menos de 1 mm del '
    'engrosamiento, y un M3x8 ya la pincharia.')

# --- Antena ----------------------------------------------------------------
# La antena trae sus propias roscas: el tornillo sube desde dentro de la tapa.
ant = P['antena']
rosca_antena = ant.get('rosca_profundidad', 4.0)
largo_antena = comercial_que_cabe(ant['espesor_tapa'] + rosca_antena, ant['espesor_tapa'] + 3)
filas.append((f'{ant["metrica"]} cilindrica ISO 4762', largo_antena, 3,
              'Antena. Sube desde dentro y rosca en la antena.',
              f'tapa {ant["espesor_tapa"]:.0f} + {largo_antena - ant["espesor_tapa"]:.0f} '
              f'de {rosca_antena:.0f} de rosca en la antena'))
notas.append(
    f'Los {ant["metrica"]} de la antena los impone la ANTENA, no el diseno: la '
    'HA-901A trae tres roscas de esa metrica en su base. Es la unica pieza del '
    'equipo que no usa M3 o M2. Si la antena que llega usa otra, se cambian dos '
    'parametros y se reimprime SOLO la tapa.')
notas.append(
    f'La profundidad de las roscas de la antena se supone {rosca_antena:.0f} mm, '
    'de la referencia 3-M2.5x6. Medirla antes de comprar: un tornillo largo de '
    'mas toca fondo y no aprieta.')

# --- IMU -------------------------------------------------------------------
imu = P['imu']
pila = 1.6 + imu['pcb_separadores'] + imu['espesor_repisa']
filas.append((f'{imu["metrica"]} cilindrica ISO 4762', comercial(pila + 2.0), 2,
              'BMI088 sobre la repisa del trineo.',
              f'PCB 1.6 + separador {imu["pcb_separadores"]} + repisa '
              f'{imu["espesor_repisa"]} + tuerca'))
filas.append((f'Tuerca {imu["metrica"]} DIN 934', None, 2,
              'BMI088. Obligatoria: los agujeros son ranurados.',
              'una ranura no puede sujetar una rosca'))
filas.append((f'Arandela {imu["metrica"]}', None, 2,
              'BMI088. Reparte el apriete sobre el agujero de 3.0 del PCB.',
              f'{imu["metrica"]} en un agujero de '
              f'{imu["agujeros_diametro"]} deja holgura'))
notas.append(
    'El IMU es el unico punto donde la tuerca no es opcional. Sus agujeros son '
    f'ranuras de +-{imu["ajuste_lateral"]} mm para poder centrar el sensor, y '
    'una ranura no da rosca.')
notas.append(
    f'El IMU usa {imu["metrica"]} y no M2.5 porque se consigue en cualquier kit '
    f'de hobby. M3 no pasa: los agujeros del BMI088 son de '
    f'{imu["agujeros_diametro"]} y no dejan holgura.')

# --- Accesorios ------------------------------------------------------------
acc = P['accesorios']
filas.append(('M4 formando rosca, o M3 con tuerca', None, 2,
              f'Barrenos de accesorios, {acc["piloto"]} mm pasantes.',
              'a discrecion segun lo que montes'))
notas.append(
    f'Los barrenos de accesorios son pasantes de {acc["piloto"]} mm y sin '
    'refuerzo interior. Sirven como piloto de M4 formando rosca en los 2.5 mm '
    'de pared, o como paso holgado de M3 con tuerca y arandela por dentro. Para '
    'colgar peso, la tuerca es lo sensato.')

# --- Inserto ---------------------------------------------------------------
ins = P['inserto_jalon']
filas.append((f'McMaster 90611A121', None, 1,
              'Rosca 5/8-11 UNC hembra del jalon.',
              'capturado entre base y tubo; sin tornillos'))

lineas = ['# Tornilleria de V2.1', '',
          'Generado por `bom.py` desde `parameters.json` (lo ejecuta `regenerate.py`). Las longitudes salen de',
          'la geometria del modelo, no de una estimacion: se mide desde el asiento',
          'de la cabeza hasta el fondo del barreno y se redondea a medida comercial.',
          '',
          '**Nada de esto se ha montado ni ensayado.**', '',
          '## Carcasa', '',
          '| Pieza | Largo | Cant. | Donde | Calculo |',
          '| --- | ---: | ---: | --- | --- |']
for nombre, largo, cant, donde, calculo in filas:
    largo_txt = f'{largo} mm' if largo else '—'
    lineas.append(f'| {nombre} | {largo_txt} | **{cant}** | {donde} | {calculo} |')

tornillos = sum(c for _, l, c, _, _ in filas if l)
tuercas = sum(c for n, _, c, _, _ in filas if 'Tuerca' in n)
lineas += ['',
           f'**{tornillos} tornillos con longitud definida y {tuercas} tuercas.** '
           'El resto queda a criterio al accesorizar.', '']

lineas += ['## Tornilleria de las placas interiores', '',
           'El diseno **no necesita tornillos para las placas**: la rejilla del',
           'trineo las sujeta con brida contra un plano de apoyo. Esto es',
           'deliberado, porque el repositorio declara no conocer el patron de',
           'agujeros de varias de ellas.', '',
           'Si aun asi quieres atornillar alguna, esto es lo que admite cada una',
           'segun su ficha. **Confirmar midiendo la placa real antes de comprar.**', '',
           '| Placa | Metrica | Patron | Confianza del dato |',
           '| --- | --- | --- | --- |']

placas = [
    ('bmi088', 'M2.5', 'dos agujeros de 3.0, separacion 18.5'),
    ('microsd', 'M2', '38 x 20 segun la familia'),
    ('tiny_adapter', 'M2', '14 x 14'),
    ('esp32_tiny', '—', 'sus pads no son agujeros de montaje'),
    ('carrier_um980', '—', 'cuatro agujeros sin cotas publicadas'),
    ('powerboost', 'M2.5', 'sin plano acotado localizado'),
    ('soft_switch', 'M2.5', 'sin plano acotado localizado'),
]
for clave, metrica, patron in placas:
    comp = C.get(clave, {})
    lineas.append(f'| {comp.get("descripcion", clave)} | {metrica} | {patron} | '
                  f'{comp.get("confianza", "?")} |')

lineas += ['',
           'Solo el BMI088 tiene plano publicado, y por eso es el unico que el',
           'modelo atornilla. Para el resto, atornillar a un patron supuesto es',
           'exactamente el error que se corrigio de V1.', '',
           'Si decides atornillar alguna, lo necesario seria:', '',
           '| Consumible | Uso previsto |',
           '| --- | --- |',
           '| M2 x 6 cilindrica + tuerca M2 | microSD y Tiny-Adapter, cuatro por placa |',
           '| M2.5 x 6 cilindrica + tuerca M2.5 | PowerBoost y Soft Power Switch |',
           '| Separadores nylon M2 y M2.5, 3 a 5 mm | separar la placa del plano de apoyo |',
           '',
           'Las tuercas son necesarias porque el trineo no lleva torres roscadas:',
           'su cara es plana a proposito, para que sirva con cualquier placa.', '']

if notas:
    lineas += ['## Advertencias', '']
    lineas += [f'- {n}' for n in notas]
    lineas.append('')

lineas += ['## Consumibles',
           '',
           '| Consumible | Cantidad | Uso |',
           '| --- | ---: | --- |',
           '| Brida de 2.5 mm, 100-150 mm | 6-10 | Sujecion de placas y bateria en la rejilla |',
           '| Lamina aislante fina | segun placas | Entre placa y plano de apoyo |',
           '| Llave Allen 2 mm | 1 | M3 cabeza boton |',
           '| Llave Allen 2 mm | 1 | M2.5 cilindrica |',
           '| Llave Allen 1.5 mm | 1 | M2 cilindrica del IMU |',
           '']

(ROOT / 'generated').mkdir(exist_ok=True)
(ROOT / 'generated' / 'screws.json').write_text(json.dumps(largos, indent=1), encoding='utf-8')
destino = ROOT / 'SCREW-BOM.md'
destino.write_text('\n'.join(lineas), encoding='utf-8')
print('\n'.join(lineas[:40]))
print(f'\nescrito: {destino}')
