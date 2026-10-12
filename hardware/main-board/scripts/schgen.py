"""Generación de esquemáticos jerárquicos de KiCad a partir de una descripción en Python.

Cada pin se une a su red con un tramo corto de cable y una etiqueta (local si la
red vive en una sola hoja, global si cruza hojas) o un símbolo de alimentación.
Así la conectividad queda explícita y el ERC de KiCad la puede comprobar.
"""

import uuid as _uuid

from sexpr import QStr, dumps
from symlib import outward, transform

SCH_VERSION = 20250114
GEN_VERSION = "9.0"
GRID = 1.27
STUB = 2.54
NS = _uuid.UUID("6f1c7a52-3b1e-4c9e-9d55-2a8c4f0b7e11")


def uid(*key):
    return QStr(str(_uuid.uuid5(NS, "/".join(str(k) for k in key))))


def snap(v):
    return round(round(v / GRID) * GRID, 4)


def font(size=1.27, hide=False, justify=None, bold=False):
    f = ["font", ["size", size, size]]
    if bold:
        f.append(["bold", "yes"])
    e = ["effects", f]
    if justify:
        e.append(["justify"] + justify.split())
    if hide:
        e.append(["hide", "yes"])
    return e


POWER_SYMBOLS = {
    "GND": ("power:GND", (0, 1)),
    "+3V3": ("power:+3V3", (0, -1)),
}


def _rot_for(direction, default):
    """Rotación que lleva el vector `default` (a 0°) al vector `direction`."""
    for rot in (0, 90, 180, 270):
        if rot == 0:
            v = default
        else:
            import math
            r = math.radians(rot)
            c, s = round(math.cos(r)), round(math.sin(r))
            v = (c * default[0] + s * default[1], -s * default[0] + c * default[1])
        if tuple(v) == tuple(direction):
            return rot
    return 0


class Part:
    def __init__(self, design, ref, lib_id, value, footprint, sheet, group, pins,
                 rot=0, fields=None, dnp=False, in_bom=True, unit=1):
        self.design = design
        self.ref = ref
        self.lib_id = lib_id
        self.sym = design.libs.get(lib_id)
        self.value = value
        self.footprint = footprint if footprint is not None else (self.sym.property("Footprint") or "")
        self.sheet = sheet
        self.group = group
        self.rot = rot
        self.fields = fields or {}
        self.dnp = dnp
        self.in_bom = in_bom
        self.unit = unit
        self.conns = {}  # número de pin -> red (None = sin conexión)
        for key, net in pins.items():
            for p in self.sym.pin(str(key), unit):
                if p.number in self.conns and self.conns[p.number] != net:
                    raise ValueError("%s pin %s asignado dos veces" % (ref, p.number))
                self.conns[p.number] = net
        missing = [p for p in self.sym.pins_of_unit(unit) if p.number not in self.conns
                   and p.etype != "no_connect"]
        if missing:
            raise ValueError("%s (%s): pines sin asignar: %s" % (
                ref, lib_id, ", ".join("%s/%s" % (p.number, p.name) for p in missing)))
        self.at = (0.0, 0.0)

    def nets(self):
        return {n for n in self.conns.values() if n}


class Design:
    def __init__(self, libs, project, title, rev, date, company, comments=()):
        self.libs = libs
        self.project = project
        self.title = title
        self.rev = rev
        self.date = date
        self.company = company
        self.comments = list(comments)
        self.parts = []
        self.sheets = []  # (nombre, archivo, título)
        self.groups = {}  # hoja -> lista ordenada de (grupo, título)
        self.notes = {}  # hoja -> lista de textos libres

    def sheet(self, name, filename, title):
        self.sheets.append((name, filename, title))
        self.groups[name] = []
        self.notes[name] = []

    def group(self, sheet, name, title, width=None):
        self.groups[sheet].append((name, title, width))

    def note(self, sheet, text):
        self.notes.setdefault(sheet, []).append(text)

    def add(self, ref, lib_id, value, sheet, group, pins, footprint=None, rot=0,
            lcsc=None, mpn=None, dnp=False, in_bom=True, description=None, datasheet=None, **extra):
        fields = {}
        if mpn:
            fields["MPN"] = mpn
        if lcsc:
            fields["LCSC"] = lcsc
        if description:
            fields["Description"] = description
        if datasheet:
            fields["Datasheet"] = datasheet
        fields.update(extra)
        if any(p.ref == ref for p in self.parts):
            raise ValueError("referencia repetida " + ref)
        p = Part(self, ref, lib_id, value, footprint, sheet, group, pins, rot, fields, dnp, in_bom)
        self.parts.append(p)
        return p

    # ------------------------------------------------------------------ redes
    def net_sheets(self):
        m = {}
        for p in self.parts:
            for n in p.nets():
                m.setdefault(n, set()).add(p.sheet)
        return m

    def netlist(self):
        """Red -> lista de (ref, pin)."""
        m = {}
        for p in self.parts:
            for num, n in p.conns.items():
                if n:
                    m.setdefault(n, []).append((p.ref, num))
        return m

    def check(self):
        problems = []
        for n, pins in self.netlist().items():
            if len(pins) < 2:
                problems.append("red %s con un solo pin: %s" % (n, pins))
        return problems

    # ------------------------------------------------------------- escritura
    def write(self, outdir):
        import os
        root_uuid = uid(self.project, "root")
        sheet_uuids = {name: uid(self.project, "sheet", name) for name, _, _ in self.sheets}
        net_sheets = self.net_sheets()
        files = {}
        self._pwr_base = {name: 1000 * i for i, (name, _, _) in enumerate(self.sheets, start=1)}
        for page, (name, filename, title) in enumerate(self.sheets, start=2):
            files[filename] = self._sheet_file(name, title, page, root_uuid, sheet_uuids[name], net_sheets)
        files[self.project + ".kicad_sch"] = self._root_file(root_uuid, sheet_uuids)
        for fn, tree in files.items():
            with open(os.path.join(outdir, fn), "w", encoding="utf-8") as f:
                f.write(dumps(tree) + "\n")
        return files

    def _title_block(self, title):
        tb = ["title_block", ["title", QStr(title)], ["date", QStr(self.date)],
              ["rev", QStr(self.rev)], ["company", QStr(self.company)]]
        for i, c in enumerate(self.comments, start=1):
            tb.append(["comment", i, QStr(c)])
        return tb

    def _root_file(self, root_uuid, sheet_uuids):
        t = ["kicad_sch", ["version", SCH_VERSION], ["generator", QStr("eeschema")],
             ["generator_version", QStr(GEN_VERSION)], ["uuid", root_uuid], ["paper", QStr("A4")],
             self._title_block(self.title), ["lib_symbols"]]
        x0, y0 = 30.48, 50.8
        for i, (name, filename, title) in enumerate(self.sheets):
            col, row = i % 2, i // 2
            x, y = x0 + col * 127.0, y0 + row * 63.5
            w, h = 101.6, 38.1
            t.append(["sheet", ["at", x, y], ["size", w, h],
                      ["exclude_from_sim", "no"], ["in_bom", "yes"], ["on_board", "yes"], ["dnp", "no"],
                      ["fields_autoplaced", "yes"],
                      ["stroke", ["width", 0.1524], ["type", "solid"]],
                      ["fill", ["color", 0, 0, 0, 0.0]],
                      ["uuid", sheet_uuids[name]],
                      ["property", QStr("Sheetname"), QStr(title), ["at", x, y - 0.7, 0],
                       font(1.8, justify="left bottom")],
                      ["property", QStr("Sheetfile"), QStr(filename), ["at", x, y + h + 0.6, 0],
                       font(1.27, justify="left top")],
                      ["instances", ["project", QStr(self.project),
                                     ["path", QStr("/" + root_uuid), ["page", QStr(str(i + 2))]]]]])
        y = y0 + ((len(self.sheets) + 1) // 2) * 63.5 + 5
        for k, text in enumerate(self.notes.get("_root", [])):
            t.append(["text", QStr(text), ["exclude_from_sim", "no"], ["at", x0, y + k * 6, 0],
                      font(1.6, justify="left top"), ["uuid", uid(self.project, "rootnote", k)]])
        t.append(["sheet_instances", ["path", QStr("/"), ["page", QStr("1")]]])
        t.append(["embedded_fonts", "no"])
        return t

    def _sheet_file(self, name, title, page, root_uuid, sheet_uuid, net_sheets):
        parts = [p for p in self.parts if p.sheet == name]
        path = "/%s/%s" % (root_uuid, sheet_uuid)
        items = []
        lib_ids = []
        self._layout(name, parts)

        def use(lib_id):
            if lib_id not in lib_ids:
                lib_ids.append(lib_id)

        pwr_count = [self._pwr_base.get(name, 0)]

        for p in parts:
            use(p.lib_id)
            items.append(self._symbol_instance(p, path))
            done_points = set()
            for pin in p.sym.pins_of_unit(p.unit):
                net = p.conns.get(pin.number)
                pt = transform(pin.x, pin.y, p.at[0], p.at[1], p.rot)
                if pt in done_points:
                    continue
                done_points.add(pt)
                key = (p.ref, pin.number)
                if pin.etype == "no_connect":
                    continue
                if net is None:
                    items.append(["no_connect", ["at", pt[0], pt[1]], ["uuid", uid(self.project, "nc", *key)]])
                    continue
                o = outward(pin.angle, p.rot)
                end = (round(pt[0] + o[0] * STUB, 4), round(pt[1] + o[1] * STUB, 4))
                items.append(["wire", ["pts", ["xy", pt[0], pt[1]], ["xy", end[0], end[1]]],
                              ["stroke", ["width", 0], ["type", "default"]],
                              ["uuid", uid(self.project, "w", *key)]])
                angle = {(1, 0): 0, (0, -1): 90, (-1, 0): 180, (0, 1): 270}[tuple(o)]
                if net in POWER_SYMBOLS:
                    lib_id, default_dir = POWER_SYMBOLS[net]
                    use(lib_id)
                    pwr_count[0] += 1
                    items.append(self._power_instance(lib_id, net, end, _rot_for(o, default_dir), path,
                                                      "%s-%s" % key, "#PWR%04d" % pwr_count[0]))
                elif len(net_sheets.get(net, ())) > 1:
                    items.append(["global_label", QStr(net), ["shape", "bidirectional"],
                                  ["at", end[0], end[1], angle], ["fields_autoplaced", "yes"],
                                  font(1.0, justify="left" if angle in (0, 90) else "right"),
                                  ["uuid", uid(self.project, "gl", *key)],
                                  ["property", QStr("Intersheetrefs"), QStr("${INTERSHEET_REFS}"),
                                   ["at", end[0], end[1], 0], font(1.0, hide=True)]])
                else:
                    items.append(["label", QStr(net), ["at", end[0], end[1], angle],
                                  ["fields_autoplaced", "yes"],
                                  font(1.0, justify=("left bottom" if angle in (0, 90) else "right bottom")),
                                  ["uuid", uid(self.project, "lb", *key)]])

        # Títulos y marcos de grupo.
        for gname, (x1, y1, x2, y2, gtitle) in self._group_boxes.items():
            items.append(["rectangle", ["start", x1, y1], ["end", x2, y2],
                          ["stroke", ["width", 0.1524], ["type", "dash"]], ["fill", ["type", "none"]],
                          ["uuid", uid(self.project, "box", name, gname)]])
            items.append(["text", QStr(gtitle), ["exclude_from_sim", "no"], ["at", x1 + 1.27, y1 + 1.27, 0],
                          font(1.8, justify="left top", bold=True), ["uuid", uid(self.project, "gt", name, gname)]])
        for k, text in enumerate(self.notes[name]):
            items.append(["text", QStr(text), ["exclude_from_sim", "no"],
                          ["at", self._notes_origin[0], self._notes_origin[1] + k * 4.0, 0],
                          font(1.27, justify="left top"), ["uuid", uid(self.project, "note", name, k)]])

        libsyms = ["lib_symbols"] + [self.libs.get(l).embedded() for l in lib_ids]
        t = ["kicad_sch", ["version", SCH_VERSION], ["generator", QStr("eeschema")],
             ["generator_version", QStr(GEN_VERSION)], ["uuid", uid(self.project, "file", name)],
             ["paper", QStr(self._paper)], self._title_block(title), libsyms]
        t += items
        t.append(["embedded_fonts", "no"])
        return t

    def _symbol_instance(self, p, path):
        x, y = p.at
        bb = self._bbox_sch(p)
        props = []
        vertical2 = self._vertical2(p)
        fa = (360 - p.rot) % 360
        if vertical2:
            rpos, rjust = (bb[2] + 0.6, y - 1.0), "left"
            vpos, vjust = (bb[2] + 0.6, y + 1.6), "left"
        else:
            rpos, rjust = (bb[0], bb[1] - 2.0), "left bottom"
            vpos, vjust = (bb[0], bb[1] - 0.4), "left bottom"
        hide_rv = p.ref.startswith("#")
        props.append(["property", QStr("Reference"), QStr(p.ref), ["at", rpos[0], rpos[1], fa],
                      font(1.27, justify=rjust, hide=hide_rv)])
        props.append(["property", QStr("Value"), QStr(p.value), ["at", vpos[0], vpos[1], fa],
                      font(1.0, justify=vjust, hide=hide_rv)])
        props.append(["property", QStr("Footprint"), QStr(p.footprint), ["at", x, y, 0], font(1.27, hide=True)])
        props.append(["property", QStr("Datasheet"), QStr(p.fields.get("Datasheet", "")), ["at", x, y, 0], font(1.27, hide=True)])
        props.append(["property", QStr("Description"), QStr(p.fields.get("Description", "")), ["at", x, y, 0], font(1.27, hide=True)])
        for k, v in p.fields.items():
            if k in ("Datasheet", "Description"):
                continue
            props.append(["property", QStr(k), QStr(v), ["at", x, y, 0], font(1.27, hide=True)])
        node = ["symbol", ["lib_id", QStr(p.lib_id)], ["at", x, y, p.rot], ["unit", p.unit],
                ["exclude_from_sim", "no"], ["in_bom", "yes" if p.in_bom else "no"], ["on_board", "yes"],
                ["dnp", "yes" if p.dnp else "no"], ["uuid", uid(self.project, "sym", p.ref)]]
        node += props
        for pin in p.sym.pins_of_unit(p.unit):
            node.append(["pin", QStr(pin.number), ["uuid", uid(self.project, "pin", p.ref, pin.number)]])
        node.append(["instances", ["project", QStr(self.project),
                                   ["path", QStr(path), ["reference", QStr(p.ref)], ["unit", p.unit]]]])
        return node

    def _power_instance(self, lib_id, net, at, rot, path, key, ref):
        sym = self.libs.get(lib_id)
        node = ["symbol", ["lib_id", QStr(lib_id)], ["at", at[0], at[1], rot], ["unit", 1],
                ["exclude_from_sim", "no"], ["in_bom", "yes"], ["on_board", "yes"], ["dnp", "no"],
                ["uuid", uid(self.project, "pwr", key)],
                ["property", QStr("Reference"), QStr(ref), ["at", at[0], at[1], 0], font(1.27, hide=True)],
                ["property", QStr("Value"), QStr(net), ["at", at[0], at[1] + (3.2 if net == "GND" else -3.2),
                                                       (360 - rot) % 360],
                 font(1.0, hide=(net == "GND"))],
                ["property", QStr("Footprint"), QStr(""), ["at", at[0], at[1], 0], font(1.27, hide=True)],
                ["property", QStr("Datasheet"), QStr(""), ["at", at[0], at[1], 0], font(1.27, hide=True)],
                ["property", QStr("Description"), QStr(""), ["at", at[0], at[1], 0], font(1.27, hide=True)]]
        for pin in sym.pins:
            node.append(["pin", QStr(pin.number), ["uuid", uid(self.project, "pwrpin", key)]])
        node.append(["instances", ["project", QStr(self.project),
                                   ["path", QStr(path), ["reference", QStr(ref)], ["unit", 1]]]])
        return node

    # ---------------------------------------------------------------- layout
    def _bbox_sch(self, p):
        x1, y1, x2, y2 = p.sym.bbox
        pts = [transform(a, b, p.at[0], p.at[1], p.rot) for a in (x1, x2) for b in (y1, y2)]
        xs = [q[0] for q in pts]
        ys = [q[1] for q in pts]
        return (min(xs), min(ys), max(xs), max(ys))

    def _extent(self, p):
        """Caja del símbolo más cables y etiquetas, relativa a su origen."""
        saved = p.at
        p.at = (0.0, 0.0)
        bx1, by1, bx2, by2 = self._bbox_sch(p)
        x1, y1, x2, y2 = bx1, by1 - 4.0, bx2, by2 + 1.5
        for pin in p.sym.pins_of_unit(p.unit):
            net = p.conns.get(pin.number)
            if not net:
                continue
            px, py = transform(pin.x, pin.y, 0, 0, p.rot)
            o = outward(pin.angle, p.rot)
            if net in POWER_SYMBOLS:
                L = STUB + 3.5
                tw = 1.5
            else:
                L = STUB + 2.5 + len(net) * 1.05
                tw = 1.5
            ex, ey = px + o[0] * L, py + o[1] * L
            x1, x2 = min(x1, ex, px - tw), max(x2, ex, px + tw)
            y1, y2 = min(y1, ey, py - tw), max(y2, ey, py + tw)
        tw = 0 if p.ref.startswith("#") else max(len(p.ref) * 1.1, len(p.value) * 0.9)
        if self._vertical2(p):
            x2 = max(x2, bx2 + 1.0 + tw)
        else:
            x2 = max(x2, bx1 + tw)
        p.at = saved
        return (x1, y1, x2, y2)

    def _vertical2(self, p):
        pins = p.sym.pins_of_unit(p.unit)
        if len({(q.x, q.y) for q in pins}) != 2:
            return False
        return all(outward(q.angle, p.rot)[0] == 0 for q in pins)

    PAPERS = (("A3", 420.0, 297.0), ("A2", 594.0, 420.0), ("A1", 841.0, 594.0))

    def _layout(self, sheet, parts):
        """Elige la hoja más pequeña en la que caben los grupos y los coloca en filas."""
        for name, W, H in self.PAPERS:
            if self._try_layout(sheet, parts, W, H) or name == "A1":
                self._paper = name
                return

    def _try_layout(self, sheet, parts, W, H):
        self._group_boxes = {}
        margin = 12.7
        page_w = W - margin
        x_cursor, y_cursor, row_h = margin, margin + 5.0, 0.0
        max_y = 0.0
        for gname, gtitle, gwidth in self.groups[sheet]:
            gparts = [p for p in parts if p.group == gname]
            if not gparts:
                continue
            ext = [self._extent(p) for p in gparts]
            widest = max(e[2] - e[0] for e in ext) + 9.0
            max_w = min(max(gwidth or 180.0, widest), page_w - margin)
            rows, cur, cur_w = [], [], 0.0
            for p, e in zip(gparts, ext):
                w = e[2] - e[0] + 3.0
                if cur and cur_w + w > max_w - 6.0:
                    rows.append(cur)
                    cur, cur_w = [], 0.0
                cur.append((p, e))
                cur_w += w
            rows.append(cur)
            gw = max(sum(e[2] - e[0] + 3.0 for _, e in r) for r in rows) + 6.0
            gh = sum(max(e[3] - e[1] for _, e in r) + 3.0 for r in rows) + 10.0
            if x_cursor + gw > page_w and x_cursor > margin:
                x_cursor = margin
                y_cursor += row_h + 6.0
                row_h = 0.0
            gx, gy = x_cursor, y_cursor
            yy = gy + 8.0
            for r in rows:
                xx = gx + 3.0
                rh = max(e[3] - e[1] for _, e in r)
                for p, e in r:
                    p.at = (snap(xx - e[0]), snap(yy - e[1]))
                    xx += e[2] - e[0] + 3.0
                yy += rh + 3.0
            self._group_boxes[gname] = (snap(gx), snap(gy), snap(gx + gw), snap(gy + gh), gtitle)
            x_cursor += gw + 6.0
            row_h = max(row_h, gh)
            max_y = max(max_y, gy + gh)
        notes_h = 4.0 * len(self.notes.get(sheet, []))
        self._notes_origin = (margin, snap(y_cursor + row_h + 8.0))
        # Se reserva la franja del cajetín (abajo a la derecha) sumando ~40 mm al alto ocupado.
        return max_y + notes_h + 8.0 <= H - margin - 40.0
