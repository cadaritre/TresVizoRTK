#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Altos de los componentes de la placa v0.3 contra el tubo de la carcasa V3.0 (cara plana al frente).

Lee el JSON de export_board_step.py (caja de cada pieza en los ejes de la carcasa) y comprueba que la
esquina de arriba de cada pieza, en el |x| más grande que ocupa, quede con el aire pedido bajo el techo
del tubo:

    cara plana:  y_plana - y_max >= aire
    círculo:     r_int - hypot(|x|max, y_max) >= aire      (aire medido en radio)

Es conservador: toma la cara de arriba de la pieza tan ancha como su caja. También comprueba la franja sin
componentes de los cantos laterales.

Por omisión toma el tubo de mechanical/v3.0/parameters.json (radio interior = radio_exterior - pared,
cara plana interior en plano_y_interior) y 0.5 mm de aire, el objetivo de la carcasa para las piezas
compradas. Se puede forzar con las opciones.

Uso (con cualquier python 3):
  python3 cad/check_heights.py [placa-principal.json] [--r-int R] [--y-plana Y] [--aire 0.5]
                               [--franja 1.0] [--ancho 36]
Sale con 1 si alguna pieza no cabe.
"""
import argparse
import json
import math
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
CASE_PARAMS = HERE.parents[2] / 'mechanical' / 'v3.0' / 'parameters.json'


def case_tube():
    """(radio interior, y de la cara plana interior) del tubo de V3.0, o None si no está."""
    try:
        t = json.loads(CASE_PARAMS.read_text(encoding='utf-8'))['tubo']
        return t['radio_exterior'] - t['pared'], t['plano_y_interior']
    except (OSError, KeyError, ValueError):
        return None


def main():
    tube = case_tube() or (25.6, 20.5)
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    ap.add_argument('json', nargs='?', default=str(HERE / 'placa-principal.json'))
    ap.add_argument('--r-int', type=float, default=tube[0], help='radio interior del tubo')
    ap.add_argument('--y-plana', type=float, default=tube[1], help='y de la cara plana por dentro')
    ap.add_argument('--aire', type=float, default=0.5, help='aire mínimo sobre cada pieza')
    ap.add_argument('--franja', type=float, default=1.0, help='franja sin componentes en los cantos laterales')
    ap.add_argument('--ancho', type=float, default=36.0, help='ancho de la placa (cantos en x = ±ancho/2)')
    a = ap.parse_args()
    d = json.loads(Path(a.json).read_text(encoding='utf-8'))
    print('Tubo: radio interior %.2f, cara plana interior en y %.2f, aire %.2f%s'
          % (a.r_int, a.y_plana, a.aire, '' if case_tube() else ' (sin mechanical/v3.0: valores por omisión)'))

    def margin_of(xm, y1):
        return min(a.y_plana - y1, a.r_int - math.hypot(xm, y1)) - a.aire

    x_edge = a.ancho / 2 - a.franja
    rows, bad = [], []
    for ref, c in sorted(d['componentes'].items()):
        (x0, x1), (y0, y1) = c['caja']['x'], c['caja']['y']
        xm = max(abs(x0), abs(x1))
        margin = margin_of(xm, y1)
        fuera_franja = xm <= x_edge + 1e-6
        rows.append((margin, ref, c['modelo'], xm, y1))
        if margin < -1e-3 or not fuera_franja:
            bad.append({'ref': ref, 'modelo': c['modelo'], 'x_max_abs': round(xm, 2), 'y_max': round(y1, 2),
                        'margen': round(margin, 2), 'en_la_franja_de_los_cantos': not fuera_franja})
    rows.sort()
    print('Piezas con menos margen (mm, además del aire):')
    for margin, ref, model, xm, y1 in rows[:12]:
        print('  %-6s %6.2f   |x| hasta %5.2f, y hasta %5.2f   %s' % (ref, margin, xm, y1, model))
    if bad:
        print('NO CABEN o pisan la franja de %.1f mm de los cantos:' % a.franja)
        for b in bad:
            print('  ', json.dumps(b, ensure_ascii=False))
        return 1
    print('Todas las piezas (%d) caben con %.1f mm de aire y fuera de la franja de %.1f mm.'
          % (len(rows), a.aire, a.franja))
    return 0


if __name__ == '__main__':
    sys.exit(main())
