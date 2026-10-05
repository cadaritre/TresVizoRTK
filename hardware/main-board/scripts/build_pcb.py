"""Construye el PCB a partir de la netlist exportada del esquemático y de `board.json`.

Se ejecuta con el Python que trae KiCad (módulo pcbnew):
    <KiCad>/Contents/Frameworks/Python.framework/Versions/Current/bin/python3 build_pcb.py \
        <kicad_dir> <netlist> <board.json> <salida.kicad_pcb> <dir_huellas_kicad>

`board.json` describe contorno, agujeros, colocación, zonas, áreas restringidas,
pistas fijadas a mano y clases de red. El ruteo general lo hace route_rest.py después.
"""

import json
import math
import os
import sys

import pcbnew

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from sexpr import find, findall, loads  # noqa: E402

mm = pcbnew.FromMM


def V(x, y):
    return pcbnew.VECTOR2I(mm(x), mm(y))


LAYERS = {
    "F.Cu": pcbnew.F_Cu, "In1.Cu": pcbnew.In1_Cu, "In2.Cu": pcbnew.In2_Cu, "B.Cu": pcbnew.B_Cu,
    "F.SilkS": pcbnew.F_SilkS, "B.SilkS": pcbnew.B_SilkS, "Edge.Cuts": pcbnew.Edge_Cuts,
    "F.Fab": pcbnew.F_Fab, "User.1": pcbnew.User_1, "Cmts.User": pcbnew.Cmts_User,
}


def read_netlist(path):
    t = loads(open(path, encoding="utf-8").read())
    comps = {}
    for c in findall(find(t, "components"), "comp"):
        ref = str(find(c, "ref")[1])
        fields = {}
        fs = find(c, "fields")
        if fs:
            for f in findall(fs, "field"):
                fields[str(find(f, "name")[1])] = str(f[2]) if len(f) > 2 else ""
        props = {}
        for p in findall(c, "property"):
            props[str(find(p, "name")[1])] = str(find(p, "value")[1]) if find(p, "value") else ""
        comps[ref] = {
            "footprint": str(find(c, "footprint")[1]) if find(c, "footprint") else "",
            "value": str(find(c, "value")[1]),
            "sheet": str(find(find(c, "sheetpath"), "tstamps")[1]),
            "tstamp": str(find(c, "tstamps")[1]),
            "fields": fields,
            "props": props,
        }
    nets = {}
    for n in findall(find(t, "nets"), "net"):
        nets[str(find(n, "name")[1])] = [(str(find(x, "ref")[1]), str(find(x, "pin")[1]))
                                         for x in findall(n, "node")]
    return comps, nets


def lib_path(nick, std_dir, extra):
    if nick in extra:
        return extra[nick]
    return os.path.join(std_dir, nick + ".pretty")


def add_outline(board, spec, width=0.1):
    if spec["type"] == "circle":
        s = pcbnew.PCB_SHAPE(board)
        s.SetShape(pcbnew.SHAPE_T_CIRCLE)
        cx, cy = spec["center"]
        s.SetCenter(V(cx, cy))
        s.SetEnd(V(cx + spec["radius"], cy))
        s.SetLayer(pcbnew.Edge_Cuts)
        s.SetWidth(mm(width))
        board.Add(s)
        return
    pts = spec["points"]
    for i in range(len(pts)):
        a, b = pts[i], pts[(i + 1) % len(pts)]
        s = pcbnew.PCB_SHAPE(board)
        s.SetShape(pcbnew.SHAPE_T_SEGMENT)
        s.SetStart(V(*a))
        s.SetEnd(V(*b))
        s.SetLayer(pcbnew.Edge_Cuts)
        s.SetWidth(mm(width))
        board.Add(s)


def outline_points(spec, n=72):
    if spec["type"] == "circle":
        cx, cy = spec["center"]
        r = spec["radius"]
        return [(cx + r * math.cos(2 * math.pi * k / n), cy + r * math.sin(2 * math.pi * k / n)) for k in range(n)]
    return [tuple(p) for p in spec["points"]]


def find_net(board, name):
    """Busca una red por su nombre corto: las redes locales llevan el prefijo de la hoja («/Hoja/RED»)."""
    n = board.FindNet(name)
    if n is not None and n.GetNetCode() > 0:
        return n
    hits = [ni for nm, ni in board.GetNetsByName().items() if str(nm).endswith("/" + name)]
    if len(hits) != 1:
        raise SystemExit("red %r: %d coincidencias" % (name, len(hits)))
    return hits[0]


def add_zone(board, z, outline):
    zone = pcbnew.ZONE(board)
    layers = z["layers"] if "layers" in z else [z["layer"]]
    if len(layers) == 1:
        zone.SetLayer(LAYERS[layers[0]])
    else:
        ls = pcbnew.LSET()
        for l in layers:
            ls.AddLayer(LAYERS[l])
        zone.SetLayerSet(ls)
    poly = z.get("polygon", "outline")
    pts = outline if poly == "outline" else poly
    ol = zone.Outline()
    ol.NewOutline()
    for x, y in pts:
        ol.Append(mm(x), mm(y))
    if z.get("rule_area"):
        zone.SetIsRuleArea(True)
        zone.SetDoNotAllowTracks(z.get("no_tracks", True))
        zone.SetDoNotAllowVias(z.get("no_vias", True))
        zone.SetDoNotAllowZoneFills(z.get("no_pour", True))
        zone.SetDoNotAllowPads(z.get("no_pads", False))
        zone.SetDoNotAllowFootprints(z.get("no_footprints", False))
        if z.get("name"):
            zone.SetZoneName(z["name"])
    else:
        zone.SetNet(find_net(board, z["net"]))
        zone.SetAssignedPriority(z.get("priority", 0))
        zone.SetLocalClearance(mm(z.get("clearance", 0.2)))
        zone.SetMinThickness(mm(z.get("min_width", 0.2)))
        zone.SetThermalReliefGap(mm(z.get("thermal_gap", 0.3)))
        zone.SetThermalReliefSpokeWidth(mm(z.get("spoke", 0.3)))
        if z.get("solid_pads"):
            zone.SetPadConnection(pcbnew.ZONE_CONNECTION_FULL)
        if z.get("name"):
            zone.SetZoneName(z["name"])
    board.Add(zone)
    return zone


def main():
    kicad_dir, netlist, spec_path, out, std_fp = sys.argv[1:6]
    spec = json.load(open(spec_path, encoding="utf-8"))
    comps, nets = read_netlist(netlist)
    extra_libs = {k: os.path.join(kicad_dir, v) for k, v in spec.get("libs", {}).items()}

    board = pcbnew.CreateEmptyBoard()
    ds = board.GetDesignSettings()
    board.SetCopperLayerCount(spec["board"]["layers"])
    ds.SetBoardThickness(mm(spec["board"].get("thickness", 1.6)))
    r = spec["rules"]
    ds.m_MinClearance = mm(r["min_clearance"])
    ds.m_TrackMinWidth = mm(r["min_track"])
    ds.m_ViasMinSize = mm(r["min_via_dia"])
    ds.m_MinThroughDrill = mm(r["min_drill"])
    ds.m_ViasMinAnnularWidth = mm(r["min_annular"])
    ds.m_HoleToHoleMin = mm(r["hole_to_hole"])
    ds.m_CopperEdgeClearance = mm(r["edge_clearance"])
    ds.m_HoleClearance = mm(r.get("hole_clearance", 0.2))
    ds.m_SolderMaskMinWidth = mm(r.get("mask_min_web", 0.1))
    ds.m_MinResolvedSpokes = r.get("min_resolved_spokes", 2)

    ns = ds.m_NetSettings
    dflt = ns.GetDefaultNetclass()
    d = spec["netclasses"]["Default"]
    dflt.SetTrackWidth(mm(d["track"]))
    dflt.SetClearance(mm(d["clearance"]))
    dflt.SetViaDiameter(mm(d["via_dia"]))
    dflt.SetViaDrill(mm(d["via_drill"]))
    for name, c in spec["netclasses"].items():
        if name == "Default":
            continue
        nc = pcbnew.NETCLASS(name)
        nc.SetTrackWidth(mm(c["track"]))
        nc.SetClearance(mm(c["clearance"]))
        nc.SetViaDiameter(mm(c["via_dia"]))
        nc.SetViaDrill(mm(c["via_drill"]))
        nc.SetPriority(c.get("priority", 10))
        ns.SetNetclass(name, nc)
        for pat in c["nets"]:
            ns.SetNetclassPatternAssignment(pat, name)
            ns.SetNetclassPatternAssignment("*/" + pat, name)

    netinfo = {}
    for name in nets:
        ni = pcbnew.NETINFO_ITEM(board, name)
        board.Add(ni)
        netinfo[name] = ni
    pad_net = {}
    for name, nodes in nets.items():
        for ref, pin in nodes:
            pad_net[(ref, pin)] = name

    placement = spec["placement"]
    missing = [r for r in comps if r not in placement]
    if missing:
        print("SIN COLOCACIÓN:", ", ".join(sorted(missing)))
    for ref, c in sorted(comps.items()):
        nick, name = c["footprint"].split(":", 1)
        fp = pcbnew.FootprintLoad(lib_path(nick, std_fp, extra_libs), name)
        if fp is None:
            raise SystemExit("no se encontró la huella %s para %s" % (c["footprint"], ref))
        fp.SetFPIDAsString(c["footprint"])
        # Modelos 3D que la biblioteca de KiCad no trae: se sustituyen por uno del mismo cuerpo
        models = fp.Models()
        for i in range(len(models)):   # por índice: al iterar, SWIG entrega copias
            name = os.path.basename(models[i].m_Filename)
            if name in spec.get("model_substitutes", {}):
                models[i].m_Filename = spec["model_substitutes"][name]
        fp.SetReference(ref)
        fp.SetValue(c["value"])
        for k, v in c["fields"].items():
            if k == "Footprint" or not v:
                continue
            fp.SetField(k, v)
            for f in fp.GetFields():
                if f.GetName() == k:
                    f.SetVisible(False)
                    f.SetLayer(pcbnew.F_Fab)
        fp.SetPath(pcbnew.KIID_PATH(c["sheet"] + c["tstamp"]))
        p = placement.get(ref, {"x": 0, "y": 0, "rot": 0, "side": "F"})
        board.Add(fp)
        if p.get("side", "F") == "B":
            fp.Flip(fp.GetPosition(), pcbnew.FLIP_DIRECTION_LEFT_RIGHT)
        fp.SetOrientationDegrees(p.get("rot", 0))
        fp.SetPosition(V(p["x"], p["y"]))
        if p.get("dnp") or "dnp" in c["props"]:
            fp.SetDNP(True)
        if "exclude_from_bom" in c["props"]:
            fp.SetExcludedFromBOM(True)
        for pad in fp.Pads():
            n = pad_net.get((ref, pad.GetNumber()))
            if n:
                pad.SetNet(netinfo[n])
        fp.Reference().SetVisible(p.get("show_ref", True))
        if "ref_offset" in p:
            fp.Reference().SetPosition(V(p["x"] + p["ref_offset"][0], p["y"] + p["ref_offset"][1]))

    add_outline(board, spec["board"]["outline"])
    outline = outline_points(spec["board"]["outline"])
    for h in spec["board"].get("holes", []):
        fp = pcbnew.FootprintLoad(os.path.join(std_fp, "MountingHole.pretty"), h["footprint"])
        fp.SetReference(h["ref"])
        fp.Reference().SetVisible(False)
        fp.SetPosition(V(h["x"], h["y"]))
        fp.SetBoardOnly(True)
        board.Add(fp)
        if h.get("net"):
            for pad in fp.Pads():
                pad.SetNet(board.FindNet(h["net"]))
    for z in spec.get("zones", []):
        if not z.get("post"):
            add_zone(board, z, outline)
    for t in spec.get("tracks", []):
        pts = t["points"]
        for a, b in zip(pts, pts[1:]):
            tr = pcbnew.PCB_TRACK(board)
            tr.SetStart(V(*a))
            tr.SetEnd(V(*b))
            tr.SetWidth(mm(t["width"]))
            tr.SetLayer(LAYERS[t["layer"]])
            tr.SetNet(find_net(board, t["net"]))
            tr.SetLocked(True)
            board.Add(tr)
    for v in spec.get("vias", []):
        via = pcbnew.PCB_VIA(board)
        via.SetPosition(V(v["x"], v["y"]))
        via.SetWidth(mm(v.get("dia", 0.6)))
        via.SetDrill(mm(v.get("drill", 0.3)))
        via.SetNet(find_net(board, v["net"]))
        via.SetLocked(True)
        board.Add(via)
    for t in spec.get("texts", []):
        tx = pcbnew.PCB_TEXT(board)
        tx.SetText(t["text"])
        tx.SetPosition(V(t["x"], t["y"]))
        tx.SetLayer(LAYERS[t.get("layer", "F.SilkS")])
        tx.SetTextSize(V(t.get("size", 1.0), t.get("size", 1.0)))
        tx.SetTextThickness(mm(t.get("thickness", 0.15)))
        if t.get("layer", "F.SilkS").startswith("B."):
            tx.SetMirrored(True)
        if t.get("angle"):
            tx.SetTextAngleDegrees(t["angle"])
        board.Add(tx)
    # Gráficos rellenos (logotipo): contorno con huecos, partido en polígonos simples (el formato de
    # KiCad guarda un solo contorno por polígono)
    for g in spec.get("graphics", []):
        ps = pcbnew.SHAPE_POLY_SET()
        ps.NewOutline()
        for x, y in g["outline"]:
            ps.Append(mm(x), mm(y))
        for hole in g.get("holes", []):
            ps.NewHole()
            for x, y in hole:
                ps.Append(mm(x), mm(y), -1, -1)
        ps.Fracture()
        for i in range(ps.OutlineCount()):
            one = pcbnew.SHAPE_POLY_SET()
            one.AddOutline(ps.Outline(i))
            sh = pcbnew.PCB_SHAPE(board)
            sh.SetShape(pcbnew.SHAPE_T_POLY)
            sh.SetPolyShape(one)
            sh.SetFilled(True)
            sh.SetWidth(0)
            sh.SetLayer(LAYERS[g.get("layer", "F.SilkS")])
            board.Add(sh)
    pcbnew.SaveBoard(out, board)
    print("guardado", out, "huellas:", len(comps), "redes:", len(nets))


if __name__ == "__main__":
    main()
