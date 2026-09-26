"""Comprueba el reparto angular del tubo y recoloca el logo en el hueco libre.

Cada elemento exterior ocupa un sector. Este script los lista, detecta solapes
y deja el logo centrado y del mayor tamano que quepa. Asi mover un elemento no
obliga a recalcular el resto a mano.
"""
import json, math, pathlib

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


def añadir(nombre, centro, medio_ancho):
    zonas.append((nombre, norm(centro - medio_ancho), norm(centro + medio_ancho),
                  centro, medio_ancho))


añadir('panel principal', d['panel']['angulo'], d['panel']['arco_grados'] / 2)
añadir('panel auxiliar', d['panel_aux']['angulo'], d['panel_aux']['arco_grados'] / 2)
acc = d['accesorios']
for signo in (-1, 1):
    ang = acc['angulo'] + signo * acc['separacion_angular'] / 2
    añadir(f'accesorio {norm(ang):.0f}', ang,
           arco_grados(acc['refuerzo_diametro'] / 2, RI))
seg = d['seguro']
añadir('seguro', seg['angulo'], arco_grados(seg['cabeza_diametro'] / 2))
vert = d['tubo']['lineas_verticales']
añadir('lineas verticales A', (min(vert['angulos']) + 180) / 2 if False else
       (vert['angulos'][0] + vert['angulos'][6]) / 2,
       (vert['angulos'][6] - vert['angulos'][0]) / 2 + arco_grados(vert['ancho'] / 2))
añadir('lineas verticales B', (vert['angulos'][7] + vert['angulos'][11]) / 2,
       (vert['angulos'][11] - vert['angulos'][7]) / 2 + arco_grados(vert['ancho'] / 2))

zonas.sort(key=lambda z: z[3])
print(f'{"elemento":<22}{"centro":>8}{"desde":>8}{"hasta":>8}')
print('-' * 46)
for nombre, a, b, c, m in zonas:
    print(f'{nombre:<22}{c:>8.1f}{a:>8.1f}{b:>8.1f}')

# Huecos entre zonas consecutivas, en el orden angular.
bordes = sorted((norm(z[3] - z[4]), norm(z[3] + z[4]), z[0]) for z in zonas)
huecos = []
for i in range(len(bordes)):
    fin = bordes[i][1]
    inicio = bordes[(i + 1) % len(bordes)][0]
    ancho = norm(inicio - fin)
    if ancho > 1.0:
        huecos.append((ancho, fin, inicio, bordes[i][2], bordes[(i + 1) % len(bordes)][2]))
    elif ancho < 0.001 and norm(inicio - fin) != 0:
        pass

print('\nhuecos libres:')
for ancho, ini, fin, antes, despues in sorted(huecos, reverse=True):
    print(f'  {ini:6.1f} a {fin:6.1f}  ({ancho:5.1f} grados, '
          f'{ancho * math.pi * RO / 180:5.1f} mm)   entre {antes} y {despues}')

mayor = max(huecos)
ancho_g, ini, fin = mayor[0], mayor[1], mayor[2]
centro = norm(ini + ancho_g / 2)

lineas = sorted(d['tubo']['ranuras_decorativas_z'])
gw = d['tubo']['ranura_decorativa_ancho'] / 2
abajo = max(z for z in lineas if z < 50) + gw
arriba = min(z for z in lineas if z > 50) - gw

margen = 3.0
ancho_mm = min(ancho_g * math.pi * RO / 180 - 2 * margen,
               (arriba - abajo - 2 * margen) / 1.1513)

lg = d['logo']
lg['ancho_mm'] = round(ancho_mm, 1)
lg['angulo'] = round(centro, 1)
lg['z_centro'] = round((abajo + arriba) / 2, 1)
lg['_nota_posicion'] = (
    f'Colocado por layout_check.py en el mayor hueco libre: {ini:.0f} a {fin:.0f} '
    f'grados y {abajo:.0f} a {arriba:.0f} mm, con {margen} mm de margen por lado.')
p.write_text(json.dumps(d, indent=1, ensure_ascii=False), encoding='utf-8')
print(f'\nlogo -> ancho {lg["ancho_mm"]}  angulo {lg["angulo"]}  z {lg["z_centro"]}'
      f'  (alto {lg["ancho_mm"] * 1.1513:.1f})')
