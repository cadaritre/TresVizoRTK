"""Dibuja cortes del Meridian3 cerrado en PNG, con las piezas impresas en gris
y las envolventes de referencia en color. Sirve para revisar el encaje a ojo;
las cifras las da capacity_check.py.

Salida: generated/cortes/*.png
Uso: <python de FreeCAD> sections.py
"""
import json, math
from pathlib import Path

import FreeCAD as App
from PIL import Image, ImageChops, ImageDraw

ROOT = Path(__file__).resolve().parent
OUT = ROOT / 'generated' / 'cortes'
OUT.mkdir(parents=True, exist_ok=True)
V = App.Vector
ESCALA = 8.0            # pixeles por mm

doc = App.openDocument(str(ROOT / 'generated' / 'Meridian3.FCStd'))
IMPRESAS = (200, 200, 200)
COLORES = {
    'ref_carrier_um980': (40, 140, 60), 'ref_sma_carrier': (200, 160, 30),
    'ref_clavija_inferior': (220, 120, 30), 'ref_clavija_superior': (220, 120, 30),
    'ref_cable': (30, 30, 30), 'ref_tiny': (30, 90, 200), 'ref_tiny_adapter': (0, 138, 252),
}


def planar(p, plane):
    kind, _ = plane
    if kind == 'xz':
        return p.x, p.z
    if kind == 'yz':
        return p.y, p.z
    return p.x, p.y


def section_mask(shape, plane, size, origin):
    kind, value = plane
    normal = {'xz': V(0, 1, 0), 'yz': V(1, 0, 0), 'xy': V(0, 0, 1)}[kind]
    mask = Image.new('1', size, 0)
    try:
        wires = shape.slice(normal, value)
    except Exception:
        return mask
    for w in wires:
        pts = w.discretize(Distance=0.3)
        if len(pts) < 3:
            continue
        poly = []
        for p in pts:
            u, v = planar(p, plane)
            poly.append(((u - origin[0]) * ESCALA, size[1] - (v - origin[1]) * ESCALA))
        tmp = Image.new('1', size, 0)
        ImageDraw.Draw(tmp).polygon(poly, fill=1)
        mask = ImageChops.logical_xor(mask, tmp)
    return mask


def render(name, plane, u_range, v_range, titulo):
    size = (int((u_range[1] - u_range[0]) * ESCALA), int((v_range[1] - v_range[0]) * ESCALA))
    img = Image.new('RGB', size, (255, 255, 255))
    origin = (u_range[0], v_range[0])
    for obj in doc.Objects:
        if not hasattr(obj, 'Shape') or obj.Shape.isNull():
            continue
        color = COLORES.get(obj.Name, IMPRESAS)
        mask = section_mask(obj.Shape, plane, size, origin)
        img.paste(Image.new('RGB', size, color), (0, 0), mask)
    d = ImageDraw.Draw(img)
    # Rejilla cada 10 mm.
    for u in range(int(math.ceil(u_range[0] / 10)) * 10, int(u_range[1]) + 1, 10):
        x = (u - origin[0]) * ESCALA
        d.line([(x, 0), (x, size[1])], fill=(235, 235, 235) if u else (255, 150, 150))
    for v in range(int(math.ceil(v_range[0] / 10)) * 10, int(v_range[1]) + 1, 10):
        y = size[1] - (v - origin[1]) * ESCALA
        d.line([(0, y), (size[0], y)], fill=(235, 235, 235))
        d.text((2, y - 10), f'{v}', fill=(120, 120, 120))
    d.text((4, 4), titulo, fill=(0, 0, 0))
    img.save(OUT / f'{name}.png')
    return name


hechos = []
hechos.append(render('corte-xz-eje', ('xz', 0.0), (-30, 30), (-2, 155),
                     'Corte XZ por el eje (y=0), visto desde -Y (+X a la derecha). Gris: impreso. Color: referencias.'))
hechos.append(render('corte-yz-eje', ('yz', 0.7), (-30, 30), (-2, 155),
                     'Corte YZ por el SMA (x=0.7). +Y a la derecha: panel USB-C.'))
index = json.loads((ROOT / 'generated' / 'model-index.json').read_text(encoding='utf-8'))
H = index['plano_alturas']
for etiqueta, z in (('carrier', (H['carrier_abajo'] + H['carrier_arriba']) / 2),
                    ('usb', H['eje_usb']), ('anillo', sum(H['anillo']) / 2),
                    ('seguro-base', H['seguro_base']), ('pie', H['suelo_base'] + 1.5)):
    hechos.append(render(f'corte-xy-{etiqueta}', ('xy', z), (-30, 30), (-30, 30),
                         f'Corte XY a z={z:.1f} ({etiqueta}). +Y arriba: panel USB-C.'))
print('\n'.join(str(OUT / f'{h}.png') for h in hechos))
