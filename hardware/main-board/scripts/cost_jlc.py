"""Estimación del costo de montaje en JLCPCB a partir del BOM generado.

    python3 cost_jlc.py <bom_jlcpcb.csv> <placa.kicad_pcb> <salida.md> [placas=5]

Consulta precio, existencias y clase de cada pieza en la API pública de JLCPCB (con caché en
fab/jlc_parts_cache.json). Las tarifas de montaje Standard son las publicadas por JLCPCB y
recogidas en research/constraints.md (6.1); conviene confirmarlas en el cotizador antes de pedir.
"""

import csv
import json
import os
import re
import sys
import time
import urllib.request

API = "https://cart.jlcpcb.com/shoppingCart/smtGood/getComponentDetail?componentCode=%s"
SETUP, STENCIL, FEEDER, JOINT, XRAY_EACH = 25.56, 8.21, 1.53, 0.0016, 0.82


def fetch(code, cache):
    if code in cache:
        return cache[code]
    req = urllib.request.Request(API % code, headers={"User-Agent": "Mozilla/5.0"})
    for attempt in range(3):
        try:
            data = json.load(urllib.request.urlopen(req, timeout=20)).get("data") or {}
            break
        except Exception:
            time.sleep(2)
    else:
        data = {}
    info = {
        "mpn": data.get("componentModelEn"),
        "stock": data.get("stockCount"),
        "type": data.get("componentLibraryType"),
        "preferred": data.get("preferredComponentFlag"),
        "xray": data.get("xrayFlag"),
        "least": data.get("leastNumber") or 1,
        "prices": [(p.get("startNumber"), p.get("productPrice")) for p in (data.get("prices") or [])],
    }
    cache[code] = info
    time.sleep(0.4)
    return info


def unit_price(info, qty):
    best = None
    for start, price in sorted(info["prices"], key=lambda x: x[0] or 0):
        if start is not None and qty >= start:
            best = price
    if best is None and info["prices"]:
        best = info["prices"][0][1]
    return best or 0.0


def count_joints(pcb_path, refs):
    """Cuenta pads SMD/THT de las piezas que se montan (aproximado por el archivo .kicad_pcb)."""
    text = open(pcb_path, encoding="utf-8").read()
    total = 0
    for m in re.finditer(r'\(footprint "[^"]*".*?\(property "Reference" "([^"]+)"(.*?)\n\t\)\n', text, re.S):
        if m.group(1) in refs:
            total += len(re.findall(r'\(pad "[^"]*" (?:smd|thru_hole)', m.group(0)))
    return total


def main():
    bom, pcb, out = sys.argv[1:4]
    boards = int(sys.argv[4]) if len(sys.argv) > 4 else 5
    cache_path = os.path.join(os.path.dirname(out), "jlc_parts_cache.json")
    cache = json.load(open(cache_path)) if os.path.exists(cache_path) else {}
    rows = list(csv.DictReader(open(bom, encoding="utf-8")))
    lines = []
    parts_total = 0.0
    refs = set()
    xray = 0
    for r in rows:
        code = r["LCSC Part #"]
        des = [d for d in r["Designator"].split(",") if d]
        refs.update(des)
        info = fetch(code, cache)
        qty = len(des) * boards
        buy = max(qty, info["least"])
        up = unit_price(info, buy)
        cost = up * buy
        parts_total += cost
        if info.get("xray"):
            xray += len(des)
        lines.append((code, r["Comment"], len(des), info["type"] or "?", info["stock"], up, buy, cost, info["mpn"]))
    json.dump(cache, open(cache_path, "w"), indent=1)
    joints = count_joints(pcb, refs) * boards
    unique = len(rows)
    feeders = unique * FEEDER
    asm = SETUP + STENCIL + feeders + joints * JOINT + xray * boards * XRAY_EACH
    with open(out, "w", encoding="utf-8") as f:
        f.write("# Estimación de costo en JLCPCB (%d placas)\n\n" % boards)
        f.write("Precios y existencias de la API pública de JLCPCB consultada al generar este archivo. "
                "No es una cotización: confirmar en https://cart.jlcpcb.com/quote antes de pedir.\n\n")
        f.write("| LCSC | Pieza | Por placa | Clase | Existencias | USD/u | Compra | USD |\n")
        f.write("| --- | --- | ---: | --- | ---: | ---: | ---: | ---: |\n")
        for code, comment, n, typ, stock, up, buy, cost, mpn in lines:
            f.write("| %s | %s (%s) | %d | %s | %s | %.4f | %d | %.2f |\n" % (
                code, comment, mpn or "?", n, typ, stock, up, buy, cost))
        f.write("\n| Concepto | USD |\n| --- | ---: |\n")
        f.write("| Piezas (sin UM980) | %.2f |\n" % parts_total)
        f.write("| Preparación Standard + plantilla | %.2f |\n" % (SETUP + STENCIL))
        f.write("| Alimentadores: %d piezas distintas x %.2f | %.2f |\n" % (unique, FEEDER, feeders))
        f.write("| Juntas: %d x %.4f | %.2f |\n" % (joints, JOINT, joints * JOINT))
        f.write("| Rayos X: %d componentes x %.2f | %.2f |\n" % (xray * boards, XRAY_EACH, xray * boards * XRAY_EACH))
        f.write("| **Montaje + piezas** | **%.2f** |\n" % (asm + parts_total))
        f.write("| Por placa | %.2f |\n" % ((asm + parts_total) / boards))
    print("piezas %.2f, montaje %.2f, total %.2f USD (%d placas, %d piezas distintas)" % (
        parts_total, asm, parts_total + asm, boards, unique))


if __name__ == "__main__":
    main()
