"""Fanout de pads de GND y +3V3 hacia sus planos internos (vía + pista corta) antes del autorruteo.

    python3 fanout.py <placa.kicad_pcb> <board.json>

Para cada pad SMD de esas redes busca, alrededor del pad y hacia fuera de su huella, el primer
sitio libre para una vía de 0.6/0.3 mm que respete márgenes con cobre de otras redes, áreas sin
vías y el canto. Así el ruteador solo tiene que unir señales.
"""

import json
import math
import os
import sys

import pcbnew

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import kiid_seed  # noqa: E402

mm = pcbnew.FromMM
to_mm = pcbnew.ToMM
VIA_D, VIA_DRILL, TRACK_W, CLR, EDGE = 0.6, 0.3, 0.25, 0.17, 0.6
IC_ESCAPE = 0.8     # distancia mínima de una vía de fanout a los pads de los CI de otras huellas


def poly_contains(pts, x, y):
    inside = False
    j = len(pts) - 1
    for i in range(len(pts)):
        xi, yi = pts[i]
        xj, yj = pts[j]
        if (yi > y) != (yj > y) and x < (xj - xi) * (y - yi) / (yj - yi + 1e-12) + xi:
            inside = not inside
        j = i
    return inside


def seg_dist(px, py, ax, ay, bx, by):
    dx, dy = bx - ax, by - ay
    L = dx * dx + dy * dy
    t = 0 if L == 0 else max(0, min(1, ((px - ax) * dx + (py - ay) * dy) / L))
    return math.hypot(px - (ax + t * dx), py - (ay + t * dy))


def rect_dist(px, py, r):
    x1, y1, x2, y2 = r
    dx = max(x1 - px, 0, px - x2)
    dy = max(y1 - py, 0, py - y2)
    return math.hypot(dx, dy)


def main():
    path, spec_path = sys.argv[1:3]
    kiid_seed.seed("fanout", path, spec_path)
    spec = json.load(open(spec_path, encoding="utf-8"))
    fo = spec.get("fanout", {})
    nets = set(fo.get("nets", ["GND", "+3V3"]))
    skip = set(fo.get("skip_refs", []))
    board = pcbnew.LoadBoard(path)
    outline = [tuple(p) for p in spec["board"]["outline"]["points"]]

    pads = []  # (ref, num, net, rect)
    # Orden fijo (referencia, pad): KiCad no garantiza el orden de las huellas entre ejecuciones
    for fp in sorted(board.GetFootprints(), key=lambda f: f.GetReference()):
        for pad in sorted(fp.Pads(), key=lambda p: p.GetNumber()):
            bb = pad.GetBoundingBox()
            pads.append((fp.GetReference(), pad.GetNumber(), pad.GetNetname(),
                         (to_mm(bb.GetLeft()), to_mm(bb.GetTop()), to_mm(bb.GetRight()), to_mm(bb.GetBottom())),
                         pad, fp))
    tracks, vias = [], []
    for t in board.GetTracks():
        if t.Type() == pcbnew.PCB_VIA_T:
            p = t.GetPosition()
            vias.append((t.GetNetname(), to_mm(p.x), to_mm(p.y), to_mm(t.GetWidth(pcbnew.F_Cu)) / 2))
        else:
            a, b = t.GetStart(), t.GetEnd()
            tracks.append((t.GetNetname(), to_mm(a.x), to_mm(a.y), to_mm(b.x), to_mm(b.y), to_mm(t.GetWidth()) / 2,
                           t.GetLayer()))
    no_via = []
    for z in board.Zones():
        if z.GetIsRuleArea() and z.GetDoNotAllowVias():
            ol = z.Outline()
            no_via.append([(to_mm(ol.CVertex(i).x), to_mm(ol.CVertex(i).y)) for i in range(ol.TotalVertices())])

    def via_ok(x, y, net, own_pad):
        r = VIA_D / 2
        if not poly_contains(outline, x, y):
            return False
        for i in range(len(outline)):
            (x1, y1), (x2, y2) = outline[i], outline[(i + 1) % len(outline)]
            if seg_dist(x, y, x1, y1, x2, y2) < r + EDGE:
                return False
        for poly in no_via:
            if poly_contains(poly, x, y):
                return False
            for i in range(len(poly)):
                (x1, y1), (x2, y2) = poly[i], poly[(i + 1) % len(poly)]
                if seg_dist(x, y, x1, y1, x2, y2) < r:
                    return False
        own_fp = own_pad.GetParentFootprint()
        for ref, num, pnet, rect, pad, fp in pads:
            d = rect_dist(x, y, rect)
            if pad is own_pad:
                if d < r + 0.05:
                    return False
                continue
            # Pads de la misma red de otra huella: tampoco rozarlos (un roce deja una unión de ancho casi 0)
            need = r + (0.05 if pnet == net and fp is own_fp else 0.1 if pnet == net else CLR)
            if ref.startswith("U") and fp is not own_fp:
                need = max(need, r + IC_ESCAPE)   # deja sitio para que salgan las pistas del CI
            if d < need:
                return False
        for tnet, x1, y1, x2, y2, hw, layer in tracks:
            if seg_dist(x, y, x1, y1, x2, y2) < r + hw + (0.05 if tnet == net else CLR):
                return False
        for vnet, vx, vy, vr in vias:
            if math.hypot(x - vx, y - vy) < max(r + vr + CLR, VIA_DRILL + 0.5):
                return False
        return True

    def track_ok(x1, y1, x2, y2, net, own_pad):
        hw = TRACK_W / 2
        n = max(2, int(math.hypot(x2 - x1, y2 - y1) / 0.05))
        for k in range(n + 1):
            px, py = x1 + (x2 - x1) * k / n, y1 + (y2 - y1) * k / n
            for ref, num, pnet, rect, pad, fp in pads:
                if pad is own_pad or (pnet == net and fp is own_pad.GetParentFootprint()):
                    continue
                if rect_dist(px, py, rect) < hw + (0.1 if pnet == net else CLR):
                    return False
            for tnet, a, b, c, d, thw, layer in tracks:
                if tnet != net and layer == pcbnew.F_Cu and seg_dist(px, py, a, b, c, d) < hw + thw + CLR:
                    return False
        return True

    added = 0
    failed = []
    for ref, num, net, rect, pad, fp in pads:
        if net not in nets or ref in skip or not pad.IsOnLayer(pcbnew.F_Cu):
            continue
        if pad.GetAttribute() not in (pcbnew.PAD_ATTRIB_SMD,):
            continue
        cx, cy = (rect[0] + rect[2]) / 2, (rect[1] + rect[3]) / 2
        fc = fp.GetBoundingBox(False).GetCenter()
        ox, oy = cx - to_mm(fc.x), cy - to_mm(fc.y)
        base = math.atan2(oy, ox) if math.hypot(ox, oy) > 0.05 else 0.0
        hx, hy = (rect[2] - rect[0]) / 2, (rect[3] - rect[1]) / 2
        found = None
        for step in range(0, 14):
            for k in (0, 1, -1, 2, -2, 3, -3, 4):
                a = base + k * math.pi / 4
                ca, sa = math.cos(a), math.sin(a)
                reach = abs(ca) * hx + abs(sa) * hy
                d = reach + VIA_D / 2 + 0.12 + step * 0.12
                x, y = cx + ca * d, cy + sa * d
                if via_ok(x, y, net, pad) and track_ok(cx, cy, x, y, net, pad):
                    found = (x, y)
                    break
            if found:
                break
        if not found:
            failed.append("%s:%s" % (ref, num))
            continue
        x, y = found
        tr = pcbnew.PCB_TRACK(board)
        tr.SetStart(pcbnew.VECTOR2I(mm(cx), mm(cy)))
        tr.SetEnd(pcbnew.VECTOR2I(mm(x), mm(y)))
        tr.SetWidth(mm(TRACK_W))
        tr.SetLayer(pcbnew.F_Cu)
        tr.SetNet(pad.GetNet())
        tr.SetLocked(True)
        board.Add(tr)
        v = pcbnew.PCB_VIA(board)
        v.SetPosition(pcbnew.VECTOR2I(mm(x), mm(y)))
        v.SetWidth(mm(VIA_D))
        v.SetDrill(mm(VIA_DRILL))
        v.SetNet(pad.GetNet())
        v.SetLocked(True)
        board.Add(v)
        tracks.append((net, cx, cy, x, y, TRACK_W / 2, pcbnew.F_Cu))
        vias.append((net, x, y, VIA_D / 2))
        added += 1
    pcbnew.SaveBoard(path, board)
    print("fanout: %d vías; sin sitio: %s" % (added, ", ".join(failed) or "ninguno"))


if __name__ == "__main__":
    main()
