"""Estimación del costo de montaje en JLCPCB: panel único de las dos placas frente a pedidos separados.

    python3 cost_jlc.py <salida.md> <placas> <bom_principal.csv> <pcb_principal> [<bom_usb.csv> <pcb_usb>]

Consulta precio, existencias, clase y rayos X de cada pieza en la API pública de JLCPCB (con caché en
fab/jlc_parts_cache.json). Tarifas de la página «PCB assembly price» de JLCPCB (actualizada el
09-09-2026, consultada el 04-10-2026); conviene confirmarlas en el cotizador antes de pedir. El PCB
desnudo no entra: su precio de 4 capas con dos diseños no está publicado y solo lo da el cotizador.
"""

import csv
import json
import os
import re
import subprocess
import sys
import time
import urllib.request

API = "https://cart.jlcpcb.com/shoppingCart/smtGood/getComponentDetail?componentCode=%s"
STD = {"setup": 25.56, "stencil": 8.21, "feeder": 1.53, "panel": 8.21}      # PCBA Standard, una cara
ECO = {"setup": 8.18, "stencil": 1.53, "feeder_ext": 3.07}                   # PCBA Economic, una cara
JOINT = 0.0016


def xray_fee(n):
    """Rayos X por componente según cuántos se inspeccionan en el pedido."""
    for top, fee in ((10, 1.64), (50, 0.82), (200, 0.49), (500, 0.33), (1000, 0.25), (5000, 0.16)):
        if n <= top:
            return fee
    return 0.082


def fetch(code, cache):
    if code in cache and cache[code].get("mpn"):
        return cache[code]
    req = urllib.request.Request(API % code, headers={"User-Agent": "Mozilla/5.0"})
    data = {}
    for attempt in range(3):
        try:
            data = json.load(urllib.request.urlopen(req, timeout=20)).get("data") or {}
            break
        except Exception:
            # Python de python.org sin certificados instalados: curl usa los del sistema
            try:
                out = subprocess.run(["curl", "-s", "-m", "20", "-A", "Mozilla/5.0", API % code],
                                     capture_output=True, text=True).stdout
                data = json.loads(out).get("data") or {}
                break
            except Exception:
                time.sleep(2)
    info = {
        "mpn": data.get("componentModelEn"),
        "stock": data.get("stockCount"),
        "type": data.get("componentLibraryType"),
        "preferred": data.get("preferredComponentFlag"),
        "xray": data.get("xrayFlag"),
        "least": data.get("leastNumber") or 1,
        "prices": [(p.get("startNumber"), p.get("productPrice")) for p in (data.get("prices") or [])],
    }
    if info["mpn"]:            # una consulta fallida no se guarda: se reintenta en la próxima pasada
        cache[code] = info
    else:
        print("sin datos de JLCPCB para", code)
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
    """Pads SMD/THT de las piezas que se montan (aproximado leyendo el .kicad_pcb)."""
    text = open(pcb_path, encoding="utf-8").read()
    total = 0
    for m in re.finditer(r'\(footprint "[^"]*".*?\(property "Reference" "([^"]+)"(.*?)\n\t\)\n', text, re.S):
        if m.group(1) in refs:
            total += len(re.findall(r'\(pad "[^"]*" (?:smd|thru_hole)', m.group(0)))
    return total


def read_bom(path):
    rows = []
    for r in csv.DictReader(open(path, encoding="utf-8")):
        rows.append((r["LCSC Part #"], r["Comment"], [d for d in r["Designator"].split(",") if d]))
    return rows


def parts_cost(lines, boards, cache):
    """lines: [(code, comment, n_por_placa)] -> (total, filas, extended distintas, piezas con rayos X)."""
    total, rows, ext, xray = 0.0, [], 0, 0
    for code, comment, n in lines:
        info = fetch(code, cache)
        buy = max(n * boards, info["least"])
        up = unit_price(info, buy)
        total += up * buy
        if info["type"] != "base":
            ext += 1
        if info.get("xray"):
            xray += n * boards
        rows.append((code, comment, n, info, up, buy, up * buy))
    return total, rows, ext, xray


def main():
    out, boards = sys.argv[1], int(sys.argv[2])
    pairs = [(sys.argv[i], sys.argv[i + 1]) for i in range(3, len(sys.argv) - 1, 2)]
    cache_path = os.path.join(os.path.dirname(out), "jlc_parts_cache.json")
    cache = json.load(open(cache_path)) if os.path.exists(cache_path) else {}
    boms = [read_bom(b) for b, _ in pairs]
    joints = [count_joints(p, {d for _, _, ds in bom for d in ds}) for (b, p), bom in zip(pairs, boms)]

    def merge(bom_list):
        acc = {}
        for bom in bom_list:
            for code, comment, ds in bom:
                c, n = acc.get(code, (comment, 0))
                acc[code] = (c, n + len(ds))
        return [(code, c, n) for code, (c, n) in acc.items()]

    # (A) Panel único con las dos placas, PCBA Standard
    lines_a = merge(boms)
    parts_a, rows_a, ext_a, xray_a = parts_cost(lines_a, boards, cache)
    j_a = sum(joints) * boards
    asm_a = {"Preparación Standard": STD["setup"], "Plantilla": STD["stencil"],
             "Panel con %d diseños" % len(pairs): STD["panel"] if len(pairs) > 1 else 0.0,
             "Alimentadores: %d piezas distintas x %.2f" % (len(lines_a), STD["feeder"]): len(lines_a) * STD["feeder"],
             "Juntas: %d x %.4f" % (j_a, JOINT): j_a * JOINT,
             "Rayos X: %d componentes" % xray_a: xray_a * xray_fee(xray_a)}
    total_a = parts_a + sum(asm_a.values())
    # (B) Pedidos separados: principal en Standard, placa del USB-C en Economic
    res_b = []
    for k, (bom, (bpath, _)) in enumerate(zip(boms, pairs)):
        lines = merge([bom])
        parts, rows, ext, xray = parts_cost(lines, boards, cache)
        j = joints[k] * boards
        if k == 0:
            asm = STD["setup"] + STD["stencil"] + len(lines) * STD["feeder"] + j * JOINT + xray * xray_fee(xray)
            kind = "Standard"
        else:
            asm = ECO["setup"] + ECO["stencil"] + ext * ECO["feeder_ext"] + j * JOINT + xray * xray_fee(xray)
            kind = "Economic (%d piezas Extended distintas)" % ext
        res_b.append((os.path.basename(bpath), kind, parts, asm))
    total_b = sum(p + a for _, _, p, a in res_b)

    with open(out, "w", encoding="utf-8") as f:
        f.write("# Estimación de costo en JLCPCB (%d juegos de placas)\n\n" % boards)
        f.write("Precios, existencias y clase de la API pública de JLCPCB consultada al generar este archivo; "
                "tarifas de montaje de su página de precios (09-09-2026). No es una cotización: confirmar en "
                "https://cart.jlcpcb.com/quote antes de pedir. **No incluye el PCB desnudo** (4 capas, panel con "
                "dos diseños: su precio y el cargo por diseño distinto solo los da el cotizador) ni el envío.\n\n")
        f.write("| LCSC | Pieza | Por juego | Clase | Rayos X | Existencias | USD/u | Compra | USD |\n")
        f.write("| --- | --- | ---: | --- | --- | ---: | ---: | ---: | ---: |\n")
        for code, comment, n, info, up, buy, cost in sorted(rows_a, key=lambda r: -r[6]):
            f.write("| %s | %s (%s) | %d | %s | %s | %s | %.4f | %d | %.2f |\n" % (
                code, comment, info["mpn"] or "?", n, info["type"] or "?", "sí" if info.get("xray") else "no",
                info["stock"], up, buy, cost))
        f.write("\n## (A) Un solo pedido: panel con las dos placas, PCBA Standard\n\n| Concepto | USD |\n| --- | ---: |\n")
        f.write("| Piezas | %.2f |\n" % parts_a)
        for k, v in asm_a.items():
            f.write("| %s | %.2f |\n" % (k, v))
        f.write("| **Montaje + piezas** | **%.2f** |\n| Por juego | %.2f |\n" % (total_a, total_a / boards))
        if len(pairs) > 1:
            f.write("\n## (B) Dos pedidos: principal en Standard y placa del USB-C en Economic\n\n")
            f.write("| Pedido | Montaje | Piezas | Montaje + piezas |\n| --- | --- | ---: | ---: |\n")
            for name, kind, parts, asm in res_b:
                f.write("| %s | %s | %.2f | %.2f |\n" % (name, kind, parts, parts + asm))
            f.write("| **Total** | | | **%.2f** |\n\n" % total_b)
            f.write("Diferencia (B) − (A): **%.2f USD** a favor del panel único, sin contar el PCB desnudo: en (B) "
                    "hay dos PCB y dos envíos; en (A) un solo PCB más grande con cargo por diseño distinto.\n"
                    % (total_b - total_a))
    json.dump(cache, open(cache_path, "w"), indent=1)
    print("panel único %.2f USD; separados %.2f USD (%d juegos, sin PCB desnudo)" % (total_a, total_b, boards))


if __name__ == "__main__":
    main()
