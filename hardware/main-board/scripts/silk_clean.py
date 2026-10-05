"""Deja la serigrafía sin solapes: lo que el DRC de KiCad marca como serigrafía encimada a otra
serigrafía, a pads o fuera de la placa se corrige aquí, en ese orden de preferencia:

- referencia de una huella: se oculta (sigue en la capa de fabricación y en el plano de montaje);
- trazo del dibujo de una huella (contorno, marca de pin 1...): pasa a la capa de fabricación;
- texto o gráfico propio de la placa (etiquetas, logotipo): no se toca; se informa para moverlo en
  layout.py.

Repite DRC y corrección hasta que no quede nada o no haya avance.

    python3 silk_clean.py <placa.kicad_pcb> <kicad-cli>
(con el Python de KiCad)
"""

import json
import os
import subprocess
import sys
import tempfile

import pcbnew

SILK_TYPES = {"silk_overlap", "silk_over_copper", "silk_edge_clearance"}


def drc(kcli, path):
    out = tempfile.mktemp(suffix=".json")
    subprocess.run([kcli, "pcb", "drc", "--severity-all", "--format", "json", "-o", out, path],
                   capture_output=True, text=True)
    data = json.load(open(out, encoding="utf-8"))
    os.remove(out)
    return [v for v in data["violations"] if v["type"] in SILK_TYPES]


def index(board):
    """uuid -> (tipo, objeto, huella o None)"""
    idx = {}
    for fp in board.GetFootprints():
        idx[fp.Reference().m_Uuid.AsString()] = ("ref", fp.Reference(), fp)
        idx[fp.Value().m_Uuid.AsString()] = ("value", fp.Value(), fp)
        for g in fp.GraphicalItems():
            idx[g.m_Uuid.AsString()] = ("fpgfx", g, fp)
    for d in board.GetDrawings():
        idx[d.m_Uuid.AsString()] = ("board", d, None)
    return idx


def is_silk(item):
    return item.GetLayer() in (pcbnew.F_SilkS, pcbnew.B_SilkS)


def pick(items, idx):
    """De los objetos de una violación, cuál se corrige."""
    cands = []
    for it in items:
        k = idx.get(it.get("uuid"))
        if k and is_silk(k[1]):
            cands.append(k)
    # Prioridad: referencias, luego trazos de huellas (el de la huella más pequeña); nunca lo propio de la placa
    refs = [c for c in cands if c[0] in ("ref", "value")]
    if refs:
        return refs[0]
    gfx = [c for c in cands if c[0] == "fpgfx"]
    if gfx:
        return min(gfx, key=lambda c: c[2].GetBoundingBox(False).GetArea())
    return cands[0] if cands else None


def main():
    path, kcli = sys.argv[1:3]
    pending = []
    for rnd in range(8):
        viol = drc(kcli, path)
        if not viol:
            print("serigrafía: sin solapes (ronda %d)" % rnd)
            return
        board = pcbnew.LoadBoard(path)
        idx = index(board)
        hidden, deleted, pending = set(), 0, []
        for v in viol:
            k = pick(v["items"], idx)
            if k is None:
                continue
            kind, item, fp = k
            uid = item.m_Uuid.AsString()
            if uid in hidden:
                continue
            if kind in ("ref", "value"):
                item.SetVisible(False)
                hidden.add(uid)
            elif kind == "fpgfx":
                item.SetLayer(pcbnew.F_Fab if item.GetLayer() == pcbnew.F_SilkS else pcbnew.B_Fab)
                hidden.add(uid)
                deleted += 1
            else:
                pending.append("%s: %s" % (v["type"], " / ".join(i["description"] for i in v["items"])))
        if not hidden:
            break
        pcbnew.SaveBoard(path, board)
        print("ronda %d: %d violaciones, %d objetos corregidos (%d trazos a fabricación)" % (rnd, len(viol), len(hidden), deleted))
    for p in sorted(set(pending)):
        print("  AVISO, queda (mover en layout.py):", p)


if __name__ == "__main__":
    main()
