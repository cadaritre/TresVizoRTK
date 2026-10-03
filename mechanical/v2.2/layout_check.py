"""Comprueba el reparto angular del tubo y recoloca el logo en el hueco libre.

Cada elemento exterior ocupa un sector. Este script los lista, detecta solapes
y deja el logo centrado y del mayor tamano que quepa, sin pasar de
`logo.ancho_max_mm`. Los paneles cuentan con su reborde interior: por dentro
del tubo es el engrosamiento, no la tapa, lo que ocupa sitio.
"""
import json, math, pathlib, sys

ROOT = pathlib.Path(__file__).resolve().parent
p = ROOT / 'parameters.json'
d = json.loads(p.read_text(encoding='utf-8'))
RO = d['tubo']['diametro_exterior'] / 2
RI = RO - d['tubo']['pared']


def norm(a):
    return a % 360.0


def arco_grados(mm, radio=RO):
    return math.degrees(mm / radio)


zonas = []


def anadir(nombre, centro, medio_ancho):
    zonas.append((nombre, norm(centro - medio_ancho), norm(centro + medio_ancho),
                  centro, medio_ancho))


for clave, nombre in (('panel', 'panel principal'), ('panel_aux', 'panel auxiliar')):
    cfg = d[clave]
    anadir(nombre, cfg['angulo'], cfg['arco_grados'] / 2 + arco_grados(cfg['reborde_arco'], RI))
acc = d['accesorios']
for signo in (-1, 1):
    ang = acc['angulo'] + signo * acc['separacion_angular'] / 2
    anadir(f'accesorio {norm(ang):.0f}', ang, arco_grados(acc['refuerzo_diametro'] / 2, RI))
seg = d['seguro']
anadir('seguro', seg['angulo'], arco_grados(seg['cabeza_diametro'] / 2))
vert = d['tubo']['lineas_verticales']
for i, grupo in enumerate(vert['grupos']):
    anadir(f'lineas verticales {"AB"[i]}', (grupo[0] + grupo[-1]) / 2,
           (grupo[-1] - grupo[0]) / 2 + arco_grados(vert['ancho'] / 2))

zonas.sort(key=lambda z: z[3])
print(f'{"elemento":<22}{"centro":>8}{"desde":>8}{"hasta":>8}')
print('-' * 46)
for nombre, a, b, c, m in zonas:
    print(f'{nombre:<22}{c:>8.1f}{a:>8.1f}{b:>8.1f}')

bordes = sorted((norm(z[3] - z[4]), norm(z[3] + z[4]), z[0]) for z in zonas)
huecos, solapes = [], []
for i in range(len(bordes)):
    fin = bordes[i][1]
    inicio = bordes[(i + 1) % len(bordes)][0]
    ancho = norm(inicio - fin)
    if ancho > 180:
        solapes.append((bordes[i][2], bordes[(i + 1) % len(bordes)][2], 360 - ancho))
    elif ancho > 1.0:
        huecos.append((ancho, fin, inicio, bordes[i][2], bordes[(i + 1) % len(bordes)][2]))

print('\nhuecos libres:')
for ancho, ini, fin, antes, despues in sorted(huecos, reverse=True):
    print(f'  {ini:6.1f} a {fin:6.1f}  ({ancho:5.1f} grados, '
          f'{ancho * math.pi * RO / 180:5.1f} mm)   entre {antes} y {despues}')
if solapes:
    for a, b, g in solapes:
        print(f'SOLAPE: {a} y {b} se pisan {g:.1f} grados')
    sys.exit(1)

mayor = max(huecos)
ancho_g, ini, fin = mayor[0], mayor[1], mayor[2]
centro = norm(ini + ancho_g / 2)

lineas = sorted(d['tubo']['ranuras_decorativas_z'])
gw = d['tubo']['ranura_decorativa_ancho'] / 2
medio = (min(lineas) + max(lineas)) / 2
abajo = max(z for z in lineas if z < medio) + gw
arriba = min(z for z in lineas if z > medio) - gw

margen = 3.0
lg = d['logo']
ancho_mm = min(ancho_g * math.pi * RO / 180 - 2 * margen,
               (arriba - abajo - 2 * margen) / 1.1513,
               lg.get('ancho_max_mm', 1e9))
lg['ancho_mm'] = round(ancho_mm, 1)
lg['angulo'] = round(centro, 1)
lg['z_centro'] = round((abajo + arriba) / 2, 1)
lg['_nota_posicion'] = (
    f'Colocado por layout_check.py en el mayor hueco libre: {ini:.0f} a {fin:.0f} '
    f'grados y {abajo:.0f} a {arriba:.0f} mm, con {margen} mm de margen por lado.')
p.write_text(json.dumps(d, indent=1, ensure_ascii=False) + '\n', encoding='utf-8')
print(f'\nlogo -> ancho {lg["ancho_mm"]}  angulo {lg["angulo"]}  z {lg["z_centro"]}'
      f'  (alto {lg["ancho_mm"] * 1.1513:.1f})')
