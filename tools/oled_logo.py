#!/usr/bin/env python3
"""Vectoriza el logo existente y genera su versión monocroma de 128×64 para OLED.

Requiere Pillow. Conserva contornos y huecos; no usa fuentes ni imágenes en SVG.
"""
from pathlib import Path
from PIL import Image, ImageDraw
ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / 'firmware/esp32/web/assets/tresvizo-logo.png'
ASSETS = ROOT / 'firmware/esp32/assets'

def generate():
    source = Image.open(SOURCE).convert('RGBA')
    white = Image.new('RGBA', source.size, 'white')
    white.alpha_composite(source)
    mask = white.convert('L').point(lambda v: 255 if v < 180 else 0)
    w, h = mask.size
    pixels = mask.load()
    edges = {}
    def filled(x, y):
        return 0 <= x < w and 0 <= y < h and pixels[x, y] != 0
    def edge(a, b):
        edges.setdefault(a, []).append(b)
    for y in range(h):
        for x in range(w):
            if not filled(x,y): continue
            if not filled(x,y-1): edge((x,y),(x+1,y))
            if not filled(x+1,y): edge((x+1,y),(x+1,y+1))
            if not filled(x,y+1): edge((x+1,y+1),(x,y+1))
            if not filled(x-1,y): edge((x,y+1),(x,y))
    loops=[]
    while edges:
        start=next(iter(edges)); p=start; loop=[]
        while True:
            loop.append(p)
            q=edges[p].pop()
            if not edges[p]: del edges[p]
            p=q
            if p==start:break
        # Quitar únicamente puntos colineales: no altera el dibujo original.
        loop=[p for i,p in enumerate(loop)
              if (p[0]-loop[i-1][0],p[1]-loop[i-1][1]) !=
                 (loop[(i+1)%len(loop)][0]-p[0],loop[(i+1)%len(loop)][1]-p[1])]
        loops.append(loop)
    path=' '.join('M'+' L'.join(f'{x},{y}' for x,y in loop)+' Z' for loop in loops)
    ASSETS.mkdir(exist_ok=True)
    (ASSETS/'tresvizo-logo.svg').write_text(
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {w} {h}" role="img" aria-label="TresVizo">\n'
        f'<path fill="currentColor" fill-rule="evenodd" d="{path}"/>\n</svg>\n')
    # Rasterizar los mismos contornos del SVG; orientación negativa = hueco.
    def area(loop):
        return sum(a[0]*b[1]-b[0]*a[1] for a,b in zip(loop,loop[1:]+loop[:1]))
    rendered=Image.new('L',(w+1,h+1),0)
    draw=ImageDraw.Draw(rendered)
    for loop in sorted(loops,key=lambda points:abs(area(points)),reverse=True):
        draw.polygon(loop,fill=255 if area(loop)>0 else 0)
    small=rendered.resize((120,54),Image.Resampling.LANCZOS).point(lambda v:255 if v>=128 else 0)
    canvas=Image.new('1',(128,64),0);canvas.paste(small,(4,5))
    canvas.save(ASSETS/'tresvizo-oled.png')
    canvas.resize((768,384),Image.Resampling.NEAREST).save(ASSETS/'tresvizo-oled-preview.png')
    data=canvas.tobytes();assert len(data)==1024
    rows=['    '+','.join(f'0x{b:02x}' for b in data[i:i+16])+',' for i in range(0,len(data),16)]
    (ROOT/'firmware/esp32/include/boot_logo.h').write_text(
        '#pragma once\n#include <Arduino.h>\n\n// Logo monocromo de assets/tresvizo-logo.svg; regenerar con tools/oled_logo.py.\n'
        'namespace boot_logo {\nconstexpr uint32_t kDurationMs = 3000;\n'
        'constexpr uint8_t kWidth = 128, kHeight = 64;\n'
        'const uint8_t kBitmap[] PROGMEM = {\n'+'\n'.join(rows)+'\n};\n}\n')
if __name__=='__main__':generate()
