#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Altos de los componentes de la placa v0.3 contra el tubo de Ø52 con cara plana.

Lee el JSON de export_board_step.py (caja de cada pieza en los ejes de la carcasa) y comprueba que
la cara de arriba de cada pieza, más el aire, quede bajo el techo del tubo en el |x| más grande que
ocupa (research/v03-compacta.md):

    techo(x) = min(y_plana, sqrt(r_int² - x²))
    y_max + aire <= techo(max |x|)

Es conservador: toma la cara de arriba de la pieza tan ancha como su caja.
También comprueba la franja sin componentes de los cantos laterales.

Uso (con cualquier python 3):
  python3 cad/check_heights.py [placa-principal.json] [--r-int 24.2] [--y-plana 20.33] [--aire 0.3]
                               [--franja 1.0] [--ancho 36]
Sale con 1 si alguna pieza no cabe.
"""
import argparse
import json
import math
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent


def main():
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    ap.add_argument('json', nargs='?', default=str(HERE / 'placa-principal.json'))
    ap.add_argument('--r-int', type=float, default=24.2, help='radio interior del tubo')
    ap.add_argument('--y-plana', type=float, default=20.33, help='y de la cara plana por dentro')
    ap.add_argument('--aire', type=float, default=0.3, help='aire mínimo sobre cada pieza')
    ap.add_argument('--franja', type=float, default=1.0, help='franja sin componentes en los cantos laterales')
    ap.add_argument('--ancho', type=float, default=36.0, help='ancho de la placa (cantos en x = ±ancho/2)')
    a = ap.parse_args()
    d = json.loads(Path(a.json).read_text(encoding='utf-8'))

    def techo(x):
        return min(a.y_plana, math.sqrt(max(0.0, a.r_int ** 2 - x * x)))

    x_edge = a.ancho / 2 - a.franja
    rows, bad = [], []
    for ref, c in sorted(d['componentes'].items()):
        (x0, x1), (y0, y1) = c['caja']['x'], c['caja']['y']
        xm = max(abs(x0), abs(x1))
        margin = techo(xm) - a.aire - y1
        fuera_franja = xm <= x_edge + 1e-6
        rows.append((margin, ref, c['modelo'], xm, y1))
        if margin < -1e-3 or not fuera_franja:
            bad.append({'ref': ref, 'modelo': c['modelo'], 'x_max_abs': round(xm, 2), 'y_max': round(y1, 2),
                        'techo_menos_aire': round(techo(xm) - a.aire, 2), 'margen': round(margin, 2),
                        'en_la_franja_de_los_cantos': not fuera_franja})
    rows.sort()
    print('Piezas con menos margen (techo - aire - y_max, mm):')
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
