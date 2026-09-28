"""Reparto angular del tubo del Meridian3 y colocacion del logo.

Derivado del de V2.1. Cambios: no hay panel auxiliar ni barrenos de
accesorios, y las alturas salen de stack.py (el grupo superior de lineas sigue
al borde del tubo, que ya no esta en una cota fija).
"""
import json, math, pathlib, sys

ROOT = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
import stack as S  # noqa: E402

p = ROOT / 'parameters.json'
d = json.loads(p.read_text(encoding='utf-8'))
RO = S.RO


def norm(a):
    return a % 360.0


def arco_grados(mm, radio=RO):
    return math.degrees(mm / radio)


zonas = []


def anadir(nombre, centro, medio_ancho):
    zonas.append((nombre, centro, medio_ancho))


anadir('panel USB-C', d['panel']['angulo'], d['panel']['arco_grados'] / 2)
seg = d['seguro']
anadir('seguro', seg['angulo'], arco_grados(seg['cabeza_diametro'] / 2))
vert = d['tubo']['lineas_verticales']
ang = vert['angulos']
anadir('lineas verticales A', (ang[0] + ang[6]) / 2,
       (ang[6] - ang[0]) / 2 + arco_grados(vert['ancho'] / 2))
anadir('lineas verticales B', (ang[7] + ang[11]) / 2,
       (ang[11] - ang[7]) / 2 + arco_grados(vert['ancho'] / 2))

zonas.sort(key=lambda z: z[1])
print(f'{"elemento":<22}{"centro":>8}{"desde":>8}{"hasta":>8}')
print('-' * 46)
for nombre, c, m in zonas:
    print(f'{nombre:<22}{c:>8.1f}{norm(c - m):>8.1f}{norm(c + m):>8.1f}')

# Solapes entre zonas consecutivas.
solapes = []
for i in range(len(zonas)):
    a, b = zonas[i], zonas[(i + 1) % len(zonas)]
    hueco = norm((b[1] - b[2]) - (a[1] + a[2]))
    if hueco > 180:
        solapes.append((a[0], b[0]))
if solapes:
    sys.exit(f'Solapes en el tubo: {solapes}')

bordes = sorted((norm(c - m), norm(c + m), n) for n, c, m in zonas)
huecos = []
for i in range(len(bordes)):
    fin = bordes[i][1]
    inicio = bordes[(i + 1) % len(bordes)][0]
    ancho = norm(inicio - fin)
    if ancho > 1.0:
        huecos.append((ancho, fin, inicio, bordes[i][2], bordes[(i + 1) % len(bordes)][2]))

print('\nhuecos libres:')
for ancho, ini, fin, antes, despues in sorted(huecos, reverse=True):
    print(f'  {ini:6.1f} a {fin:6.1f}  ({ancho:5.1f} grados, '
          f'{ancho * math.pi * RO / 180:5.1f} mm)   entre {antes} y {despues}')

ancho_g, ini, fin = max(huecos)[:3]
centro = norm(ini + ancho_g / 2)
lg = d['logo']
pref = lg.get('angulo_preferido')
ancho_max = lg.get('ancho_maximo', 1e9)

gw = d['tubo']['ranura_decorativa_ancho'] / 2
abajo = max(d['tubo']['ranuras_decorativas_z']) + gw
arriba = S.Z_TUBE1 - max(d['tubo']['ranuras_decorativas_bajo_borde']) - gw

margen = 3.0
ancho_mm = min(ancho_g * math.pi * RO / 180 - 2 * margen,
               (arriba - abajo - 2 * margen) / 1.1513, ancho_max)
# Angulo preferido (de espaldas al panel), o el mas cercano a el dentro del
# hueco con su margen.
if pref is not None:
    medio = math.degrees((ancho_mm / 2 + margen) / RO)
    desde = norm(pref - ini)                 # posicion dentro del hueco
    desde = max(medio, min(ancho_g - medio, desde))
    centro = norm(ini + desde)
lg['ancho_mm'] = round(ancho_mm, 1)
lg['angulo'] = round(centro, 1)
lg['z_centro'] = round((abajo + arriba) / 2, 1)
lg['_nota_posicion'] = (
    f'Colocado por layout_check.py en el mayor hueco libre: {ini:.0f} a {fin:.0f} '
    f'grados y {abajo:.0f} a {arriba:.0f} mm, con {margen} mm de margen por lado.')
p.write_text(json.dumps(d, indent=1, ensure_ascii=False) + '\n', encoding='utf-8')
print(f'\nlogo -> ancho {lg["ancho_mm"]}  angulo {lg["angulo"]}  z {lg["z_centro"]}'
      f'  (alto {lg["ancho_mm"] * 1.1513:.1f})')
