"""Ayuda de colocación: imprime posiciones de pads y cajas de huellas en coordenadas (u, v).

    python3 probe_pcb.py <placa.kicad_pcb> REF[:pin,pin...] ...
    python3 probe_pcb.py <placa.kicad_pcb> --overlaps
"""

import sys

import pcbnew

OX, OY = 100.0, 100.0


def uv(p):
    return (round(pcbnew.ToMM(p.x) - OX, 2), round(pcbnew.ToMM(p.y) - OY, 2))


def courtyard_box(fp):
    cy = fp.GetCourtyard(pcbnew.F_CrtYd)
    if cy.OutlineCount():
        b = cy.BBox()
        return (pcbnew.ToMM(b.GetLeft()) - OX, pcbnew.ToMM(b.GetTop()) - OY,
                pcbnew.ToMM(b.GetRight()) - OX, pcbnew.ToMM(b.GetBottom()) - OY)
    b = fp.GetBoundingBox(False)
    return (pcbnew.ToMM(b.GetLeft()) - OX, pcbnew.ToMM(b.GetTop()) - OY,
            pcbnew.ToMM(b.GetRight()) - OX, pcbnew.ToMM(b.GetBottom()) - OY)


def main():
    board = pcbnew.LoadBoard(sys.argv[1])
    fps = {fp.GetReference(): fp for fp in board.GetFootprints()}
    if "--pads" in sys.argv:
        # Choques reales entre pads de huellas distintas (y con vías), con 0.15 mm de margen.
        m = 0.15
        items = []
        for fp in board.GetFootprints():
            for pad in fp.Pads():
                bb = pad.GetBoundingBox()
                items.append((fp.GetReference() + ":" + pad.GetNumber(), pad.GetNetname(),
                              pcbnew.ToMM(bb.GetLeft()) - OX, pcbnew.ToMM(bb.GetTop()) - OY,
                              pcbnew.ToMM(bb.GetRight()) - OX, pcbnew.ToMM(bb.GetBottom()) - OY))
        for t in board.GetTracks():
            if t.Type() == pcbnew.PCB_VIA_T:
                p = t.GetPosition()
                r = pcbnew.ToMM(t.GetWidth(pcbnew.F_Cu)) / 2
                x, y = pcbnew.ToMM(p.x) - OX, pcbnew.ToMM(p.y) - OY
                items.append(("via@%.2f,%.2f" % (x, y), t.GetNetname(), x - r, y - r, x + r, y + r))
        for i, a in enumerate(items):
            for b in items[i + 1:]:
                if a[0].split(":")[0] == b[0].split(":")[0]:
                    continue
                if a[1] and a[1] == b[1]:
                    continue
                if a[2] - m < b[4] and b[2] - m < a[4] and a[3] - m < b[5] and b[3] - m < a[5]:
                    print("PADS", a[0], a[1].split("/")[-1], "<->", b[0], b[1].split("/")[-1])
        return
    if "--overlaps" in sys.argv:
        boxes = {r: courtyard_box(f) for r, f in fps.items() if not r.startswith("H")}
        inside = {r: b for r, b in boxes.items() if b[0] > -5 and b[2] < 55}
        refs = sorted(inside)
        for i, a in enumerate(refs):
            for b in refs[i + 1:]:
                A, B = inside[a], inside[b]
                if A[0] < B[2] and B[0] < A[2] and A[1] < B[3] and B[1] < A[3]:
                    print("SOLAPE", a, b, [round(x, 2) for x in A], [round(x, 2) for x in B])
        for r, b in sorted(inside.items()):
            if b[0] < 0 or b[2] > 50 or b[1] < 0 or b[3] > 76:
                print("FUERA", r, [round(x, 2) for x in b])
        return
    for arg in sys.argv[2:]:
        ref, _, pins = arg.partition(":")
        fp = fps[ref]
        box = [round(x, 2) for x in courtyard_box(fp)]
        print(ref, fp.GetValue(), "pos", uv(fp.GetPosition()), "rot", fp.GetOrientationDegrees(), "caja", box)
        want = set(pins.split(",")) if pins else None
        for pad in fp.Pads():
            if want is None or pad.GetNumber() in want or pad.GetNetname() in want:
                print("   ", pad.GetNumber(), pad.GetNetname(), uv(pad.GetPosition()),
                      "tam", round(pcbnew.ToMM(pad.GetBoundingBox().GetWidth()), 2),
                      round(pcbnew.ToMM(pad.GetBoundingBox().GetHeight()), 2))


if __name__ == "__main__":
    main()
