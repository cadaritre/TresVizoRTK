"""Remates después del ruteo: vías de cosido a GND en huecos libres y relleno final de zonas.

    python3 finish_pcb.py <placa.kicad_pcb> <board.json>
"""

import json
import math
import os
import sys

import pcbnew

mm = pcbnew.FromMM
to_mm = pcbnew.ToMM


def point_in_poly(x, y, pts):
    inside = False
    j = len(pts) - 1
    for i in range(len(pts)):
        xi, yi = pts[i]
        xj, yj = pts[j]
        if (yi > y) != (yj > y) and x < (xj - xi) * (y - yi) / (yj - yi + 1e-12) + xi:
            inside = not inside
        j = i
    return inside


def outline_points(spec, n=96):
    if spec["type"] == "circle":
        cx, cy = spec["center"]
        r = spec["radius"]
        return [(cx + r * math.cos(2 * math.pi * k / n), cy + r * math.sin(2 * math.pi * k / n)) for k in range(n)]
    return [tuple(p) for p in spec["points"]]


def dist_to_poly_edge(x, y, pts):
    best = 1e9
    for i in range(len(pts)):
        (x1, y1), (x2, y2) = pts[i], pts[(i + 1) % len(pts)]
        dx, dy = x2 - x1, y2 - y1
        L = dx * dx + dy * dy
        t = 0 if L == 0 else max(0, min(1, ((x - x1) * dx + (y - y1) * dy) / L))
        px, py = x1 + t * dx, y1 + t * dy
        best = min(best, math.hypot(x - px, y - py))
    return best


def seg_dist(px, py, ax, ay, bx, by):
    dx, dy = bx - ax, by - ay
    L = dx * dx + dy * dy
    t = 0 if L == 0 else max(0, min(1, ((px - ax) * dx + (py - ay) * dy) / L))
    return math.hypot(px - (ax + t * dx), py - (ay + t * dy))


def place_refs(board):
    """Pone cada referencia visible donde no pise pads, serigrafía ni el canto; si no cabe, la oculta
    (sigue en la capa de fabricación)."""
    fps = list(board.GetFootprints())
    obstacles = []
    for fp in fps:
        for pad in fp.Pads():
            if pad.IsOnLayer(pcbnew.F_Cu):
                obstacles.append(pad.GetBoundingBox())
        for g in fp.GraphicalItems():
            if g.GetLayer() == pcbnew.F_SilkS:
                obstacles.append(g.GetBoundingBox())
    for d in board.GetDrawings():
        if d.GetLayer() == pcbnew.F_SilkS:
            obstacles.append(d.GetBoundingBox())
    edge = board.GetBoardEdgesBoundingBox()
    m = mm(0.4)
    inner = pcbnew.BOX2I(pcbnew.VECTOR2I(edge.GetLeft() + m, edge.GetTop() + m),
                         pcbnew.VECTOR2I(edge.GetWidth() - 2 * m, edge.GetHeight() - 2 * m))
    gap = mm(0.1)

    def free(bb):
        if not (inner.Contains(bb.GetOrigin()) and inner.Contains(bb.GetEnd())):
            return False
        big = pcbnew.BOX2I(pcbnew.VECTOR2I(bb.GetLeft() - gap, bb.GetTop() - gap),
                           pcbnew.VECTOR2I(bb.GetWidth() + 2 * gap, bb.GetHeight() + 2 * gap))
        return not any(big.Intersects(o) for o in obstacles)
    hidden = []
    for fp in sorted(fps, key=lambda f: f.GetReference()):
        ref = fp.Reference()
        if not ref.IsVisible():
            continue
        body = fp.GetBoundingBox(False)
        tb = ref.GetBoundingBox()
        hw, hh = tb.GetWidth() // 2, tb.GetHeight() // 2
        c = body.GetCenter()
        cands = [(c.x, body.GetTop() - hh - mm(0.3)), (c.x, body.GetBottom() + hh + mm(0.3)),
                 (body.GetLeft() - hw - mm(0.3), c.y), (body.GetRight() + hw + mm(0.3), c.y),
                 ref.GetPosition()]
        for x, y in [(p.x, p.y) if hasattr(p, "x") else p for p in cands]:
            ref.SetPosition(pcbnew.VECTOR2I(int(x), int(y)))
            bb = ref.GetBoundingBox()
            if free(bb):
                obstacles.append(bb)
                break
        else:
            ref.SetVisible(False)
            hidden.append(fp.GetReference())
    print("referencias ocultas por falta de sitio:", ", ".join(hidden) or "ninguna")


def main():
    path, spec_path = sys.argv[1:3]
    spec = json.load(open(spec_path, encoding="utf-8"))
    st = spec.get("stitching")
    board = pcbnew.LoadBoard(path)
    # Rellenos que no se exportan al autorruteador
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    import build_pcb
    outline = outline_points(spec["board"]["outline"])
    names = {z.GetZoneName() for z in board.Zones()}
    for z in spec.get("zones", []):
        if z.get("post") and z.get("name") not in names:
            build_pcb.add_zone(board, z, outline)
    if st:
        gnd = board.FindNet("GND")
        outline = outline_points(spec["board"]["outline"])
        keepouts = [z["polygon"] for z in spec.get("zones", []) if z.get("rule_area") and z.get("no_vias", True)]
        # Ni dentro de los rellenos de potencia de otras redes (PMID, VSYS)
        keepouts += [z["polygon"] for z in spec.get("zones", [])
                     if not z.get("rule_area") and z.get("net") != "GND" and "polygon" in z]
        avoid = [tuple(a) + (r,) for a, r in st.get("avoid_circles", [])]
        obstacles = []  # (tipo, geometría, holgura)
        under_modules = []
        for t in board.GetTracks():
            if t.GetNetname() == "GND" and t.Type() == pcbnew.PCB_VIA_T:
                p = t.GetPosition()
                obstacles.append(("pt", (to_mm(p.x), to_mm(p.y)), to_mm(t.GetWidth(pcbnew.F_Cu)) / 2 + 0.6))
                continue
            if t.Type() == pcbnew.PCB_VIA_T:
                p = t.GetPosition()
                obstacles.append(("pt", (to_mm(p.x), to_mm(p.y)), to_mm(t.GetWidth(pcbnew.F_Cu)) / 2))
            else:
                a, b = t.GetStart(), t.GetEnd()
                obstacles.append(("seg", (to_mm(a.x), to_mm(a.y), to_mm(b.x), to_mm(b.y)), to_mm(t.GetWidth()) / 2))
        for fp in board.GetFootprints():
            for pad in fp.Pads():
                bb = pad.GetBoundingBox()
                cx, cy = to_mm(bb.GetCenter().x), to_mm(bb.GetCenter().y)
                r = max(to_mm(bb.GetWidth()), to_mm(bb.GetHeight())) / 2
                obstacles.append(("pt", (cx, cy), r))
            # Bajo los módulos (antena, LGA) no se cosen vías.
            if fp.GetReference() in st.get("no_vias_under", []):
                bb = fp.GetBoundingBox(False)
                x1, y1 = to_mm(bb.GetLeft()), to_mm(bb.GetTop())
                x2, y2 = to_mm(bb.GetRight()), to_mm(bb.GetBottom())
                under_modules.append([(x1, y1), (x2, y1), (x2, y2), (x1, y2)])
        clearance = st.get("clearance", 0.25)
        vr = st.get("dia", 0.6) / 2
        step = st.get("pitch", 4.0)
        xs = [p[0] for p in outline]
        ys = [p[1] for p in outline]

        def spot_ok(x, y, areas):
            if not point_in_poly(x, y, outline) or dist_to_poly_edge(x, y, outline) <= st.get("edge", 1.0):
                return False
            if any(point_in_poly(x, y, k) or dist_to_poly_edge(x, y, k) < vr + 0.05 for k in areas):
                return False
            if any(math.hypot(x - ax, y - ay) < ar for ax, ay, ar in avoid):
                return False
            for kind, g, r in obstacles:
                d = math.hypot(x - g[0], y - g[1]) if kind == "pt" else seg_dist(x, y, *g)
                if d < r + vr + clearance:
                    return False
            return True

        def add_via(x, y):
            v = pcbnew.PCB_VIA(board)
            v.SetPosition(pcbnew.VECTOR2I(mm(x), mm(y)))
            v.SetWidth(mm(2 * vr))
            v.SetDrill(mm(st.get("drill", 0.3)))
            v.SetNet(gnd)
            board.Add(v)
            obstacles.append(("pt", (x, y), vr + 0.6))
        added = 0
        y = min(ys) + step / 2
        while y < max(ys):
            x = min(xs) + step / 2
            while x < max(xs):
                if spot_ok(x, y, keepouts + under_modules):
                    add_via(x, y)
                    added += 1
                x += step
            y += step
        print("vías de cosido:", added)
        # Islas de los rellenos de GND sin ninguna vía: una vía dentro las une al plano de L2.
        # (Aquí sí se permiten bajo los módulos, lejos de sus pads.)
        pcbnew.ZONE_FILLER(board).Fill(board.Zones())
        gpts = [(t.GetPosition(), t) for t in board.GetTracks()
                if t.Type() == pcbnew.PCB_VIA_T and t.GetNetname() == "GND"]
        gpts = [p for p, _ in gpts]
        gpts += [pad.GetPosition() for fp in board.GetFootprints() for pad in fp.Pads()
                 if pad.GetNetname() == "GND" and pad.GetAttribute() == pcbnew.PAD_ATTRIB_PTH]
        islands, fixed = 0, 0
        for z in board.Zones():
            if z.GetIsRuleArea() or z.GetNetname() != "GND":
                continue
            for lid in (pcbnew.F_Cu, pcbnew.B_Cu):
                if not z.IsOnLayer(lid):
                    continue
                fill = z.GetFilledPolysList(lid)
                for i in range(fill.OutlineCount()):
                    if any(fill.Contains(p, i) for p in gpts):
                        continue
                    islands += 1
                    bb = fill.Outline(i).BBox()
                    cx, cy = to_mm(bb.GetCenter().x), to_mm(bb.GetCenter().y)
                    cands = []
                    yy = to_mm(bb.GetTop())
                    while yy <= to_mm(bb.GetBottom()):
                        xx = to_mm(bb.GetLeft())
                        while xx <= to_mm(bb.GetRight()):
                            cands.append((math.hypot(xx - cx, yy - cy), xx, yy))
                            xx += 0.2
                        yy += 0.2
                    for _, xx, yy in sorted(cands):
                        ring = [(xx + (vr + 0.05) * math.cos(k * math.pi / 4), yy + (vr + 0.05) * math.sin(k * math.pi / 4))
                                for k in range(8)]
                        if all(fill.Contains(pcbnew.VECTOR2I(mm(px), mm(py)), i) for px, py in [(xx, yy)] + ring) \
                                and spot_ok(xx, yy, keepouts):
                            add_via(xx, yy)
                            gpts.append(pcbnew.VECTOR2I(mm(xx), mm(yy)))
                            fixed += 1
                            break
        print("islas de GND sin vía: %d, con vía nueva: %d" % (islands, fixed))
    place_refs(board)
    filler = pcbnew.ZONE_FILLER(board)
    filler.Fill(board.Zones())
    pcbnew.SaveBoard(path, board)


if __name__ == "__main__":
    main()
