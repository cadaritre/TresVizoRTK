"""Junta varias placas ya ruteadas en un solo PCB (panel) para un pedido de JLCPCB.

Se ejecuta con el Python de KiCad:
    <KiCad>/Contents/Frameworks/Python.framework/Versions/Current/bin/python3 panelize.py \
        <panel.json> <salida.kicad_pcb>

`panel.json` (mm, coordenadas absolutas de la hoja de KiCad):
    boards     [{"name", "file", "at": [x, y], "net_prefix"}]: "at" es donde queda la esquina superior
               izquierda del contorno de cada placa. Las redes de las placas que no son la primera
               llevan el prefijo (p. ej. «PUSB/»), para que GND de una placa no se una a la de otra.
    gap        ancho de la fresa alrededor de cada placa.
    rails      [izquierda, arriba, derecha, abajo]: ancho de cada riel por fuera de la fresa.
    tabs       [{"board", "edge": "top|bottom|left|right", "offset", "width"}]: puentes que cruzan la
               fresa, en el canto indicado de la placa, a "offset" mm de su esquina izquierda (cantos de
               arriba y abajo) o de arriba (cantos laterales). También se admite {"at": [x, y], "dir"}.
    cuts       [{"board", "edge", "offset", "width", "depth"}]: ensancha la fresa frente a un tramo del
               canto (donde una pieza sobresale): rectángulo de "width" mm, ubicado como los puentes, que
               llega a "depth" mm del canto, con esquinas de R1. El marco crece si hace falta para que los
               rieles conserven su ancho.
    mousebite  {"drill", "pitch", "offset"}: agujeros sin metalizar en el canto de la placa, dentro de
               cada puente ("offset" los saca hacia el puente).
    keepout    profundidad de la zona sin cobre que se deja dentro de la placa junto a cada puente.
    fiducials  [[x, y], ...] en los rieles (cobre 1 mm, máscara 2 mm).
    tooling    {"drill", "at": [[x, y], ...]}: agujeros de herramienta en los rieles.
    marks      {"tooling_drill", "tooling_inset": [dx, dy], "fiducial_inset": [dx, dy]}: en vez de dar
               posiciones, pone 4 agujeros de herramienta en las esquinas del marco y 3 fiduciales
               (arriba a la izquierda, arriba a la derecha y abajo a la izquierda), medidos desde cada
               esquina del marco hacia dentro.
    texts      [{"text", "layer", "at", "size"}].

Lo que hace: copia huellas, pistas, vías, zonas y dibujos de cada placa con su desplazamiento,
quita los contornos originales y dibuja el marco con la fresa (anillo alrededor de las placas menos
los puentes), los mouse bites, fiduciales, agujeros de herramienta y textos; rellena las zonas y
guarda. Las referencias no deben repetirse entre placas (el CPL sale de este archivo).
"""

import json
import os
import sys

import pcbnew

mm = pcbnew.FromMM
to_mm = pcbnew.ToMM


def V(x, y):
    return pcbnew.VECTOR2I(mm(x), mm(y))


def outline_poly(board):
    sps = pcbnew.SHAPE_POLY_SET()
    board.GetBoardPolygonOutlines(sps, False)
    return sps


def bbox_mm(sps):
    bb = sps.BBox()
    return to_mm(bb.GetLeft()), to_mm(bb.GetTop()), to_mm(bb.GetRight()), to_mm(bb.GetBottom())


def rect_poly(x1, y1, x2, y2):
    sps = pcbnew.SHAPE_POLY_SET()
    sps.NewOutline()
    for x, y in ((x1, y1), (x2, y1), (x2, y2), (x1, y2)):
        sps.Append(mm(x), mm(y))
    return sps


def add_poly_edges(board, sps, layer=pcbnew.Edge_Cuts, width=0.1):
    for o in range(sps.OutlineCount()):
        chains = [sps.Outline(o)] + [sps.Hole(o, h) for h in range(sps.HoleCount(o))]
        for ch in chains:
            n = ch.PointCount()
            for i in range(n):
                a, b = ch.CPoint(i), ch.CPoint((i + 1) % n)
                if a == b:
                    continue
                s = pcbnew.PCB_SHAPE(board)
                s.SetShape(pcbnew.SHAPE_T_SEGMENT)
                s.SetStart(a)
                s.SetEnd(b)
                s.SetLayer(layer)
                s.SetWidth(mm(width))
                board.Add(s)


def npth_footprint(board, ref, holes, drill):
    """Huella sin componente con agujeros sin metalizar (mouse bites o agujeros de herramienta)."""
    fp = pcbnew.FOOTPRINT(board)
    fp.SetReference(ref)
    fp.Reference().SetVisible(False)
    fp.SetValue(ref)
    fp.Value().SetVisible(False)
    fp.SetBoardOnly(True)
    fp.SetExcludedFromBOM(True)
    fp.SetExcludedFromPosFiles(True)
    x0, y0 = holes[0]
    fp.SetPosition(V(x0, y0))
    for i, (x, y) in enumerate(holes):
        pad = pcbnew.PAD(fp)
        pad.SetAttribute(pcbnew.PAD_ATTRIB_NPTH)
        pad.SetShape(pcbnew.PAD_SHAPE_CIRCLE)
        pad.SetSize(V(drill, drill))
        pad.SetDrillSize(V(drill, drill))
        ls = pcbnew.LSET()
        ls.AddLayer(pcbnew.F_Mask)
        ls.AddLayer(pcbnew.B_Mask)
        pad.SetLayerSet(ls)
        pad.SetNumber("")
        fp.Add(pad)
        pad.SetPosition(V(x, y))
    board.Add(fp)
    return fp


def dup(item):
    """Copia de un elemento (la firma de Duplicate cambia según el tipo en KiCad 10)."""
    try:
        return item.Duplicate(False).Cast()
    except TypeError:
        return item.Duplicate().Cast()


def copy_board(dst, src, dv, prefix, skip_edges=True):
    """Copia los elementos de `src` en `dst` desplazados `dv` (VECTOR2I), con las redes renombradas."""
    nets = {}

    def net_for(item):
        name = item.GetNetname()
        if not name:
            return None
        new = prefix + name
        if new not in nets:
            ni = dst.FindNet(new)
            if ni is None:
                ni = pcbnew.NETINFO_ITEM(dst, new)
                dst.Add(ni)
            nets[new] = ni
        return nets[new]

    for fp in list(src.GetFootprints()):
        n = dup(fp)
        n.Move(dv)
        dst.Add(n)
        for pad in n.Pads():
            ni = net_for(pad)
            if ni is not None:
                pad.SetNet(ni)
    for t in list(src.GetTracks()):
        n = dup(t)
        n.Move(dv)
        ni = net_for(t)
        dst.Add(n)
        if ni is not None:
            n.SetNet(ni)
    for z in list(src.Zones()):
        n = dup(z)
        n.Move(dv)
        ni = net_for(z) if not z.GetIsRuleArea() else None
        dst.Add(n)
        if ni is not None:
            n.SetNet(ni)
    for d in list(src.GetDrawings()):
        if skip_edges and d.GetLayer() == pcbnew.Edge_Cuts:
            continue
        n = dup(d)
        n.Move(dv)
        dst.Add(n)


def main():
    spec_path, out = sys.argv[1:3]
    spec = json.load(open(spec_path, encoding="utf-8"))
    base_dir = os.path.dirname(os.path.abspath(spec_path))
    boards = spec["boards"]
    # Todas las placas se cargan antes de tocar ninguna (si no, pcbnew devuelve objetos sin tipo)
    srcs = [pcbnew.LoadBoard(os.path.join(base_dir, b["file"])) for b in boards]
    panel = srcs[0]
    outlines = pcbnew.SHAPE_POLY_SET()
    placed = []
    for i, b in enumerate(boards):
        src = srcs[i]
        poly = outline_poly(src)
        x1, y1, x2, y2 = bbox_mm(poly)
        dx, dy = b["at"][0] - x1, b["at"][1] - y1
        dv = V(dx, dy)
        if i == 0:
            # La primera placa es la base del panel: se mueve todo lo suyo
            for item in list(panel.GetFootprints()) + list(panel.GetTracks()) + list(panel.Zones()) + \
                    list(panel.GetDrawings()):
                item.Move(dv)
            # Los contornos originales pasan a Cmts.User: borrarlos con Remove() deja a pcbnew
            # devolviendo objetos sin tipo en las llamadas siguientes
            for d in [d for d in panel.GetDrawings() if d.GetLayer() == pcbnew.Edge_Cuts]:
                d.SetLayer(pcbnew.Cmts_User)
        else:
            copy_board(panel, src, dv, b.get("net_prefix", ""))
        poly.Move(dv)
        outlines.BooleanAdd(poly)
        placed.append((b["name"], x1 + dx, y1 + dy, x2 + dx, y2 + dy))
        print("placa %s: %.2f x %.2f mm en (%.2f, %.2f)" % (b["name"], x2 - x1, y2 - y1, x1 + dx, y1 + dy))

    gap = spec.get("gap", 2.0)
    grown = pcbnew.SHAPE_POLY_SET(outlines)
    grown.Inflate(mm(gap), pcbnew.CORNER_STRATEGY_ROUND_ALL_CORNERS, mm(0.01))
    boxes = {name: (x1, y1, x2, y2) for name, x1, y1, x2, y2 in placed}
    for c in spec.get("cuts", []):
        bx1, by1, bx2, by2 = boxes[c["board"]]
        off, w, dep = c["offset"], c["width"], c["depth"]
        x1, y1, x2, y2 = {"top": (bx1 + off, by1 - dep, bx1 + off + w, by1),
                          "bottom": (bx1 + off, by2, bx1 + off + w, by2 + dep),
                          "left": (bx1 - dep, by1 + off, bx1, by1 + off + w),
                          "right": (bx2, by1 + off, bx2 + dep, by1 + off + w)}[c["edge"]]
        cut = rect_poly(x1 + 1.0, y1 + 1.0, x2 - 1.0, y2 - 1.0)
        cut.Inflate(mm(1.0), pcbnew.CORNER_STRATEGY_ROUND_ALL_CORNERS, mm(0.01))
        grown.BooleanAdd(cut)
        print("fresa ensanchada en %s (%s): %.1f mm de fondo" % (c["board"], c["edge"], dep))
    ring = pcbnew.SHAPE_POLY_SET(grown)
    ring.BooleanSubtract(outlines)
    keepouts = []
    mb = spec.get("mousebite", {"drill": 0.5, "pitch": 0.8, "offset": 0.0})
    for k, t in enumerate(spec.get("tabs", [])):
        w = t.get("width", 5.0)
        if "board" in t:
            bx1, by1, bx2, by2 = boxes[t["board"]]
            e, off = t["edge"], t["offset"]
            x, y = {"top": (bx1 + off, by1), "bottom": (bx1 + off, by2),
                    "left": (bx1, by1 + off), "right": (bx2, by1 + off)}[e]
            d = {"top": "up", "bottom": "down", "left": "left", "right": "right"}[e]
        else:
            x, y = t["at"]
            d = t["dir"]
        far = gap + 1.0
        if d == "up":
            r = (x - w / 2, y - far, x + w / 2, y + 0.05)
            holes_line = [(x - w / 2 + mb["drill"] / 2 + j * mb["pitch"], y - mb.get("offset", 0.0))
                          for j in range(int((w - mb["drill"]) / mb["pitch"]) + 1)]
            ko = (x - w / 2 - 0.5, y, x + w / 2 + 0.5, y + spec.get("keepout", 1.0))
        elif d == "down":
            r = (x - w / 2, y - 0.05, x + w / 2, y + far)
            holes_line = [(x - w / 2 + mb["drill"] / 2 + j * mb["pitch"], y + mb.get("offset", 0.0))
                          for j in range(int((w - mb["drill"]) / mb["pitch"]) + 1)]
            ko = (x - w / 2 - 0.5, y - spec.get("keepout", 1.0), x + w / 2 + 0.5, y)
        elif d == "left":
            r = (x - far, y - w / 2, x + 0.05, y + w / 2)
            holes_line = [(x - mb.get("offset", 0.0), y - w / 2 + mb["drill"] / 2 + j * mb["pitch"])
                          for j in range(int((w - mb["drill"]) / mb["pitch"]) + 1)]
            ko = (x, y - w / 2 - 0.5, x + spec.get("keepout", 1.0), y + w / 2 + 0.5)
        else:
            r = (x - 0.05, y - w / 2, x + far, y + w / 2)
            holes_line = [(x + mb.get("offset", 0.0), y - w / 2 + mb["drill"] / 2 + j * mb["pitch"])
                          for j in range(int((w - mb["drill"]) / mb["pitch"]) + 1)]
            ko = (x - spec.get("keepout", 1.0), y - w / 2 - 0.5, x, y + w / 2 + 0.5)
        ring.BooleanSubtract(rect_poly(*r))
        npth_footprint(panel, "MB%d" % (k + 1), holes_line, mb["drill"])
        keepouts.append(ko)
    # Junto a cada puente, nada de cobre dentro de la placa (el corte deja el canto a la vista)
    for k, (x1, y1, x2, y2) in enumerate(keepouts):
        z = pcbnew.ZONE(panel)
        ls = pcbnew.LSET()
        for l in (pcbnew.F_Cu, pcbnew.In1_Cu, pcbnew.In2_Cu, pcbnew.B_Cu):
            ls.AddLayer(l)
        z.SetLayerSet(ls)
        ol = z.Outline()
        ol.NewOutline()
        for px, py in ((x1, y1), (x2, y1), (x2, y2), (x1, y2)):
            ol.Append(mm(px), mm(py))
        z.SetIsRuleArea(True)
        z.SetDoNotAllowTracks(True)
        z.SetDoNotAllowVias(True)
        z.SetDoNotAllowZoneFills(True)
        z.SetDoNotAllowPads(False)
        z.SetDoNotAllowFootprints(False)
        z.SetZoneName("puente_%d" % (k + 1))
        panel.Add(z)

    gx1, gy1, gx2, gy2 = bbox_mm(grown)
    rl, rt, rr, rb = spec.get("rails", [5.0, 5.0, 5.0, 5.0])
    fx1, fy1, fx2, fy2 = gx1 - rl, gy1 - rt, gx2 + rr, gy2 + rb
    min_w, min_h = spec.get("min_size", [0, 0])
    if fx2 - fx1 < min_w:
        fx2 = fx1 + min_w
    if fy2 - fy1 < min_h:
        fy2 = fy1 + min_h
    frame = rect_poly(fx1, fy1, fx2, fy2)
    add_poly_edges(panel, frame)
    ring.Simplify()
    add_poly_edges(panel, ring)
    print("panel: %.2f x %.2f mm" % (fx2 - fx1, fy2 - fy1))

    fids = list(spec.get("fiducials", []))
    tool = spec.get("tooling")
    marks = spec.get("marks")
    if marks:
        tx, ty = marks["tooling_inset"]
        tool = {"drill": marks["tooling_drill"],
                "at": [[fx1 + tx, fy1 + ty], [fx2 - tx, fy1 + ty], [fx1 + tx, fy2 - ty], [fx2 - tx, fy2 - ty]]}
        dx, dy = marks["fiducial_inset"]
        fids += [[fx1 + dx, fy1 + dy], [fx2 - dx, fy1 + dy], [fx1 + dx, fy2 - dy]]
    lib = os.path.join(os.environ.get("KICAD10_FOOTPRINT_DIR", ""), "Fiducial.pretty")
    for k, (x, y) in enumerate(fids):
        fp = pcbnew.FootprintLoad(lib, "Fiducial_1mm_Mask2mm")
        fp.SetReference("FID%d" % (k + 1))
        fp.Reference().SetVisible(False)   # en el riel la referencia tocaría el canto
        fp.SetPosition(V(x, y))
        fp.SetExcludedFromBOM(True)
        fp.SetExcludedFromPosFiles(True)
        panel.Add(fp)
    if tool:
        for k, (x, y) in enumerate(tool["at"]):
            npth_footprint(panel, "TH%d" % (k + 1), [(x, y)], tool["drill"])
    for t in spec.get("texts", []):
        tx = pcbnew.PCB_TEXT(panel)
        tx.SetText(t["text"])
        tx.SetPosition(V(*t["at"]))
        layer = {"F.SilkS": pcbnew.F_SilkS, "B.SilkS": pcbnew.B_SilkS}[t.get("layer", "F.SilkS")]
        tx.SetLayer(layer)
        tx.SetTextSize(V(t.get("size", 1.0), t.get("size", 1.0)))
        tx.SetTextThickness(mm(t.get("thickness", 0.15)))
        if layer == pcbnew.B_SilkS:
            tx.SetMirrored(True)
        panel.Add(tx)
    pcbnew.ZONE_FILLER(panel).Fill(panel.Zones())
    pcbnew.SaveBoard(out, panel)
    # Los mouse bites van a 0.3 mm entre bordes (JLCPCB: grupos de agujeros de 0.6 mm con 0.3-0.4 mm);
    # la regla general de agujero a agujero (0.5 mm) es para vías y no se les aplica.
    with open(os.path.splitext(out)[0] + ".kicad_dru", "w", encoding="utf-8") as f:
        f.write('(version 1)\n(rule "mouse_bites"\n  (condition "A.memberOfFootprint(\'MB*\') && '
                'B.memberOfFootprint(\'MB*\')")\n  (constraint hole_to_hole (min 0.25mm)))\n')
    print("guardado", out)


if __name__ == "__main__":
    main()
