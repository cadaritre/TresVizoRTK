"""Carga de símbolos de bibliotecas .kicad_sym y geometría de sus pines."""

import copy
import math
import os

from sexpr import QStr, find, findall, loads


class Pin:
    __slots__ = ("number", "name", "etype", "x", "y", "angle", "length", "unit", "hidden")

    def __init__(self, number, name, etype, x, y, angle, length, unit, hidden):
        self.number = number
        self.name = name
        self.etype = etype
        self.x = x
        self.y = y
        self.angle = angle
        self.length = length
        self.unit = unit
        self.hidden = hidden

    def __repr__(self):
        return "Pin(%s %s %s @%g,%g a%g)" % (self.number, self.name, self.etype, self.x, self.y, self.angle)


class Symbol:
    """Símbolo aplanado listo para incrustarse en un esquemático."""

    def __init__(self, lib_id, node):
        self.lib_id = lib_id
        self.node = node
        self.base = lib_id.split(":", 1)[1]
        self.pins = _pins(node, self.base)
        self.units = sorted({p.unit for p in self.pins if p.unit} or {1})
        self.power = find(node, "power") is not None
        self.bbox = _bbox(node, self.pins)

    def pins_of_unit(self, unit):
        return [p for p in self.pins if p.unit in (0, unit)]

    def pin(self, key, unit=None):
        """Busca un pin por número o, si no existe, por nombre."""
        cands = [p for p in self.pins if p.number == key]
        if not cands:
            cands = [p for p in self.pins if p.name == key]
        if unit is not None:
            cands = [p for p in cands if p.unit in (0, unit)]
        if not cands:
            raise KeyError("%s: no hay pin %r" % (self.lib_id, key))
        return cands

    def embedded(self):
        n = copy.deepcopy(self.node)
        n[1] = QStr(self.lib_id)
        return n

    def property(self, name):
        for p in findall(self.node, "property"):
            if p[1] == name:
                return str(p[2])
        return None


def _is_hidden(node):
    if "hide" in node:
        return True
    h = find(node, "hide")
    return h is not None and (len(h) == 1 or h[1] == "yes")


def _pins(node, base):
    pins = []
    for sub in findall(node, "symbol"):
        name = str(sub[1])
        try:
            unit, style = name[len(base) + 1:].split("_")[-2:]
            unit, style = int(unit), int(style)
        except ValueError:
            unit, style = 0, 1
        if style == 2:
            continue
        for p in findall(sub, "pin"):
            at = find(p, "at")
            length = find(p, "length")
            pins.append(Pin(
                number=str(find(p, "number")[1]),
                name=str(find(p, "name")[1]),
                etype=str(p[1]),
                x=float(at[1]), y=float(at[2]),
                angle=float(at[3]) if len(at) > 3 else 0.0,
                length=float(length[1]) if length else 0.0,
                unit=unit,
                hidden=_is_hidden(p),
            ))
    return pins


def _bbox(node, pins):
    xs, ys = [], []
    for sub in findall(node, "symbol"):
        for g in sub[2:]:
            if not isinstance(g, list):
                continue
            if g[0] == "rectangle":
                s, e = find(g, "start"), find(g, "end")
                xs += [float(s[1]), float(e[1])]
                ys += [float(s[2]), float(e[2])]
            elif g[0] == "polyline":
                for xy in findall(find(g, "pts"), "xy"):
                    xs.append(float(xy[1]))
                    ys.append(float(xy[2]))
            elif g[0] == "circle":
                c, r = find(g, "center"), float(find(g, "radius")[1])
                xs += [float(c[1]) - r, float(c[1]) + r]
                ys += [float(c[2]) - r, float(c[2]) + r]
    for p in pins:
        xs.append(p.x)
        ys.append(p.y)
    if not xs:
        return (-1.27, -1.27, 1.27, 1.27)
    return (min(xs), min(ys), max(xs), max(ys))


class Library:
    def __init__(self, path, nickname=None):
        self.path = path
        self.nickname = nickname or os.path.splitext(os.path.basename(path))[0]
        tree = loads(open(path, encoding="utf-8").read())
        self.raw = {str(s[1]): s for s in findall(tree, "symbol")}
        self._cache = {}

    def get(self, name):
        if name not in self._cache:
            self._cache[name] = Symbol("%s:%s" % (self.nickname, name), self._flat(name))
        return self._cache[name]

    def _flat(self, name):
        sym = copy.deepcopy(self.raw[name])
        ext = find(sym, "extends")
        if ext is None:
            return sym
        parent = self._flat(str(ext[1]))
        pbase = str(parent[1])
        out = [parent[0], QStr(name)]
        child_props = {str(p[1]): p for p in findall(sym, "property")}
        for item in parent[2:]:
            if isinstance(item, list) and item[0] == "property" and str(item[1]) in child_props:
                out.append(child_props.pop(str(item[1])))
            elif isinstance(item, list) and item[0] == "symbol":
                sub = copy.deepcopy(item)
                sub[1] = QStr(name + str(sub[1])[len(pbase):])
                out.append(sub)
            else:
                out.append(item)
        # Propiedades nuevas del hijo, antes de los subsímbolos.
        idx = next(i for i, it in enumerate(out) if isinstance(it, list) and it[0] == "symbol")
        for p in child_props.values():
            out.insert(idx, p)
            idx += 1
        return out


class Libraries:
    """Registro de bibliotecas por apodo."""

    def __init__(self):
        self.libs = {}

    def add(self, path, nickname=None):
        lib = Library(path, nickname)
        self.libs[lib.nickname] = lib
        return lib

    def get(self, lib_id):
        nick, name = lib_id.split(":", 1)
        return self.libs[nick].get(name)


def transform(px, py, sx, sy, rot, mirror=None):
    """Punto de biblioteca (Y hacia arriba) a coordenadas del esquemático (Y hacia abajo)."""
    dx, dy = px, -py
    if mirror == "y":
        dx = -dx
    elif mirror == "x":
        dy = -dy
    r = math.radians(rot)
    c, s = round(math.cos(r)), round(math.sin(r))
    rx = c * dx + s * dy
    ry = -s * dx + c * dy
    return (round(sx + rx, 4), round(sy + ry, 4))


def outward(angle, rot, mirror=None):
    """Vector unitario desde el punto de conexión del pin hacia afuera del cuerpo."""
    a = math.radians(angle)
    dx, dy = round(math.cos(a)), -round(math.sin(a))  # hacia el cuerpo, Y abajo
    if mirror == "y":
        dx = -dx
    elif mirror == "x":
        dy = -dy
    r = math.radians(rot)
    c, s = round(math.cos(r)), round(math.sin(r))
    rx = c * dx + s * dy
    ry = -s * dx + c * dy
    return (-rx, -ry)
