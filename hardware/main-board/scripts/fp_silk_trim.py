"""Quita de las huellas de LCSC la serigrafía que pisa sus propios pads (KiCad la recortaría igual al
sacar los Gerber y el DRC la marca como «serigrafía sobre cobre»). Se ejecuta una vez sobre la
biblioteca y deja la huella guardada; build.py no lo necesita.

    python3 fp_silk_trim.py <biblioteca.pretty> <huella> [<huella> ...]
(con el Python de KiCad)
"""

import math
import sys

import pcbnew

CLEAR = 0.1   # mm entre la serigrafía y el borde de la máscara del pad


def pad_boxes(fp):
    out = []
    for p in fp.Pads():
        bb = p.GetBoundingBox()
        m = pcbnew.FromMM(CLEAR) + p.GetSolderMaskExpansion(pcbnew.F_Mask)
        out.append((bb.GetLeft() - m, bb.GetTop() - m, bb.GetRight() + m, bb.GetBottom() + m))
    return out


def seg_hits_box(ax, ay, bx, by, w, box):
    x1, y1, x2, y2 = box
    x1, y1, x2, y2 = x1 - w / 2, y1 - w / 2, x2 + w / 2, y2 + w / 2
    for k in range(41):
        t = k / 40.0
        x, y = ax + (bx - ax) * t, ay + (by - ay) * t
        if x1 <= x <= x2 and y1 <= y <= y2:
            return True
    return False


def hits(g, boxes):
    w = g.GetWidth()
    s = g.GetShape()
    if s == pcbnew.SHAPE_T_SEGMENT:
        a, b = g.GetStart(), g.GetEnd()
        return any(seg_hits_box(a.x, a.y, b.x, b.y, w, bx) for bx in boxes)
    if s in (pcbnew.SHAPE_T_CIRCLE, pcbnew.SHAPE_T_ARC):
        c = g.GetCenter()
        r = g.GetRadius()
        pts = []
        for k in range(72):
            ang = 2 * math.pi * k / 72
            pts.append((c.x + r * math.cos(ang), c.y + r * math.sin(ang)))
        if s == pcbnew.SHAPE_T_CIRCLE and g.IsSolidFill():
            pts.append((c.x, c.y))
        return any(seg_hits_box(x, y, x, y, w, bx) for x, y in pts for bx in boxes)
    bb = g.GetBoundingBox()
    return any(not (bb.GetRight() < x1 or bb.GetLeft() > x2 or bb.GetBottom() < y1 or bb.GetTop() > y2)
               for x1, y1, x2, y2 in boxes)


def main():
    lib, names = sys.argv[1], sys.argv[2:]
    for name in names:
        fp = pcbnew.FootprintLoad(lib, name)
        boxes = pad_boxes(fp)
        drop = [g for g in fp.GraphicalItems()
                if g.GetLayer() == pcbnew.F_SilkS and isinstance(g, pcbnew.PCB_SHAPE) and hits(g, boxes)]
        for g in drop:
            fp.Remove(g)
        pcbnew.FootprintSave(lib, fp)
        print("%s: %d trazos de serigrafía quitados" % (name, len(drop)))


if __name__ == "__main__":
    main()
