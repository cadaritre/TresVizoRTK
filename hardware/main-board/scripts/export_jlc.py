"""Convierte las salidas de kicad-cli a los formatos de BOM y CPL de JLCPCB.

    python3 export_jlc.py <netlist.net> <pos.csv> <bom_salida.csv> <cpl_salida.csv> [rotaciones.json] \
        [--net <otra_netlist.net> ...]

- BOM: Comment, Designator, Footprint, LCSC Part #  (agrupado por pieza LCSC)
- CPL: Designator, Mid X, Mid Y, Layer, Rotation
Las piezas marcadas DNP o sin campo LCSC no se mandan a ensamblar y se listan aparte.
`rotaciones.json` permite corregir la orientación por referencia o por prefijo de huella.
Con `--net` se suman las piezas de otras placas del mismo panel (las referencias no se repiten
entre placas); el CPL sale entonces del archivo de posiciones del panel.
"""

import csv
import json
import os
import re
import sys
from collections import OrderedDict

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from sexpr import find, findall, loads  # noqa: E402


def comps_from_netlist(path):
    t = loads(open(path, encoding="utf-8").read())
    out = OrderedDict()
    for c in findall(find(t, "components"), "comp"):
        ref = str(find(c, "ref")[1])
        fields = {}
        fs = find(c, "fields")
        if fs:
            for f in findall(fs, "field"):
                fields[str(find(f, "name")[1])] = str(f[2]) if len(f) > 2 else ""
        props = {str(find(p, "name")[1]): (str(find(p, "value")[1]) if find(p, "value") else "")
                 for p in findall(c, "property")}
        out[ref] = {
            "value": str(find(c, "value")[1]),
            "footprint": str(find(c, "footprint")[1]) if find(c, "footprint") else "",
            "lcsc": fields.get("LCSC", ""),
            "mpn": fields.get("MPN", ""),
            "dnp": "dnp" in props,
            "exclude_bom": "exclude_from_bom" in props,
        }
    return out


def natural(ref):
    m = re.match(r"([A-Za-z#]+)(\d+)", ref)
    return (m.group(1), int(m.group(2))) if m else (ref, 0)


def main():
    args, extra = [], []
    argv = sys.argv[1:]
    while argv:
        a = argv.pop(0)
        if a == "--net":
            extra.append(argv.pop(0))
        else:
            args.append(a)
    net, pos, bom_out, cpl_out = args[:4]
    rot_fix = json.load(open(args[4])) if len(args) > 4 and os.path.exists(args[4]) else {}
    comps = comps_from_netlist(net)
    for path in extra:
        for ref, c in comps_from_netlist(path).items():
            if ref in comps and not ref.startswith("#"):
                raise SystemExit("referencia repetida entre placas: %s" % ref)
            comps[ref] = c
    groups = OrderedDict()
    skipped = []
    for ref, c in comps.items():
        if ref.startswith("#") or c["exclude_bom"]:
            continue
        if c["dnp"] or not c["lcsc"]:
            skipped.append((ref, c["value"], c["mpn"], "DNP" if c["dnp"] else "sin LCSC"))
            continue
        # Una línea por pieza LCSC: JLCPCB cobra el alimentador por pieza distinta, no por valor
        key = (c["lcsc"], c["footprint"])
        groups.setdefault(key, []).append(ref)
    with open(bom_out, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["Comment", "Designator", "Footprint", "LCSC Part #"])
        for (lcsc, fpn), refs in groups.items():
            refs.sort(key=natural)
            value = "/".join(sorted({comps[r]["value"] for r in refs}))
            w.writerow([value, ",".join(refs), fpn.split(":")[-1], lcsc])
    placed = {r for refs in groups.values() for r in refs}
    rows = []
    with open(pos, encoding="utf-8") as f:
        for r in csv.DictReader(f):
            ref = r["Ref"]
            if ref not in placed:
                continue
            fpn = comps[ref]["footprint"].split(":")[-1]
            rot = float(r["Rot"])
            fix = rot_fix.get("refs", {}).get(ref)
            if fix is None:
                for pat, val in rot_fix.get("footprints", {}).items():
                    if re.search(pat, fpn):
                        fix = val
                        break
            rot = (rot + (fix or 0)) % 360
            side = "Top" if r["Side"].lower().startswith("top") else "Bottom"
            rows.append([ref, "%.4fmm" % float(r["PosX"]), "%.4fmm" % float(r["PosY"]), side, "%g" % rot])
    rows.sort(key=lambda x: natural(x[0]))
    with open(cpl_out, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["Designator", "Mid X", "Mid Y", "Layer", "Rotation"])
        w.writerows(rows)
    print("BOM: %d líneas, %d piezas; CPL: %d; fuera de ensamble: %d" % (
        len(groups), len(placed), len(rows), len(skipped)))
    for s in skipped:
        print("  fuera:", *s)


if __name__ == "__main__":
    main()
