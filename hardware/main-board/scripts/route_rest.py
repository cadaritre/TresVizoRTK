"""Rutea las conexiones pendientes con A* en rejilla y arranque y reruteo (rip-up and reroute).

    python3 route_rest.py <placa.kicad_pcb> <drc.json> [capas]

Lee los pares sin conectar del informe DRC (JSON de kicad-cli), rasteriza el cobre existente con
su margen y busca caminos por las capas indicadas (por omisión F.Cu,In2.Cu,B.Cu) con el ancho y
la vía de la clase de red (si no caben, con vía de 0.6/0.3 y pista más delgada; se informa).
Cuando una conexión no cabe, se buscan caminos que atraviesen pistas puestas por este mismo
programa, se arrancan las que estorban y se vuelven a encolar (con coste histórico para no
oscilar). El cobre que ya estaba en la placa (pads, prerruteos, fanout, zonas) no se toca.

En In2 (plano de +3V3) las pistas nuevas son válidas pero más caras: el relleno de la zona las
rodea al volver a rellenar. Se ejecuta con el Python de KiCad; no usa bibliotecas externas.

Variables de entorno: SKIP_NETS=GND,... omite redes (salvo las conexiones a pines de CI, U*);
ROUTE_REST_LIMIT=N solo intenta N pares;
ROUTE_REST_MINUTES=M tiempo máximo (por omisión 20).
"""

import heapq
import json
import math
import os
import sys
import time
from array import array
from collections import Counter, deque

import pcbnew

mm = pcbnew.FromMM
to_mm = pcbnew.ToMM
R = 0.1                     # resolución de la rejilla (mm)
MARGIN = 0.02               # margen sobre la separación de la clase de red (cubre la discretización)
SMALL_VIA = (0.6, 0.3)      # vía por omisión (diámetro, taladro)
HOLE_TO_HOLE = 0.5          # borde a borde entre agujeros
HOLE_CLEARANCE = 0.25       # cobre a borde de agujero
EDGE = 0.3                  # cobre al canto
ZONE_CLEARANCE = 0.2
VIA_COST = 30               # en celdas
INNER_COST = 1.8            # coste relativo de la capa interna (es el plano de +3V3)
RIP_PENALTY = 40            # coste por celda ocupada por otra ruta al buscar con arranque
HIST_STEP = 5.0             # coste histórico que se suma a cada celda disputada
MAX_RIPS = 60               # veces que una conexión puede arrancar a otras
ZONE_REACH = 3.0            # una zona se alcanza a menos de esto del punto que marca el DRC (mm)
INFL = 1.3                  # alcance máximo de una marca alrededor del eje o centro de su forma (mm)
BLOCK = -1
FLEX_NETS = ("GND", "+3V3")    # sus zonas no son obstáculo: al rellenar de nuevo rodean las pistas nuevas
NECK_W = 0.2                # ancho del cuello junto a pads de paso fino
NECK_R = 1.0                # el cuello solo se permite a menos de esto de los pads de los extremos (mm)
OUTER = ("F.Cu", "B.Cu")    # capas permitidas a las redes de potencia y de conmutación
OUTER_CLASSES = ("Power", "Switch")


def seg_dist(px, py, ax, ay, bx, by):
    dx, dy = bx - ax, by - ay
    L = dx * dx + dy * dy
    t = 0.0 if L == 0 else max(0.0, min(1.0, ((px - ax) * dx + (py - ay) * dy) / L))
    return math.hypot(px - (ax + t * dx), py - (ay + t * dy))


def _ccw(ax, ay, bx, by, cx, cy):
    return (cx - ax) * (by - ay) - (bx - ax) * (cy - ay)


def seg_seg_dist(a, b, c, d):
    d1, d2 = _ccw(*c, *d, *a), _ccw(*c, *d, *b)
    d3, d4 = _ccw(*a, *b, *c), _ccw(*a, *b, *d)
    if ((d1 > 0) != (d2 > 0)) and ((d3 > 0) != (d4 > 0)) and d1 and d2 and d3 and d4:
        return 0.0
    return min(seg_dist(*a, *c, *d), seg_dist(*b, *c, *d), seg_dist(*c, *a, *b), seg_dist(*d, *a, *b))


def inside_poly(pts, x, y):
    inside = False
    j = len(pts) - 1
    for i in range(len(pts)):
        xi, yi = pts[i]
        xj, yj = pts[j]
        if (yi > y) != (yj > y) and x < (xj - xi) * (y - yi) / (yj - yi) + xi:
            inside = not inside
        j = i
    return inside


def poly_dist(pts):
    n = len(pts)

    def f(x, y):
        if inside_poly(pts, x, y):
            return 0.0
        return min(seg_dist(x, y, *pts[i], *pts[(i + 1) % n]) for i in range(n))
    return f


def seg_shape(ax, ay, bx, by, hw):
    """Distancia al cobre de una pista y su caja (incluye el medio ancho)."""
    return (lambda x, y: max(0.0, seg_dist(x, y, ax, ay, bx, by) - hw)), \
        (min(ax, bx) - hw, min(ay, by) - hw, max(ax, bx) + hw, max(ay, by) + hw)


def disc_shape(cx, cy, r):
    """Distancia al cobre de un disco (vía o agujero) y su caja."""
    return (lambda x, y: max(0.0, math.hypot(x - cx, y - cy) - r)), (cx - r, cy - r, cx + r, cy + r)


def poly_points(sps):
    out = []
    for o in range(sps.OutlineCount()):
        ol = sps.Outline(o)
        out.append([(to_mm(ol.CPoint(i).x), to_mm(ol.CPoint(i).y)) for i in range(ol.PointCount())])
    return out


def bbox_of(pts):
    xs = [p[0] for p in pts]
    ys = [p[1] for p in pts]
    return min(xs), min(ys), max(xs), max(ys)


def describe(item):
    if item.Type() == pcbnew.PCB_PAD_T:
        return "%s:%s" % (item.GetParentFootprint().GetReference(), item.GetNumber())
    p = item.GetPosition()
    kind = {pcbnew.PCB_VIA_T: "vía", pcbnew.PCB_ZONE_T: "zona"}.get(item.Type(), "pista")
    return "%s(%.1f,%.1f)" % (kind, to_mm(p.x), to_mm(p.y))


class Grid:
    """Ocupación por capa para el eje de pista de cada ancho y para centros de vía.

    Valor de celda: 0 libre, código de red si solo esa red puede usarla, BLOCK si nadie.
    """

    def __init__(self, board, layer_names, widths, via_sizes):
        self.lids = [board.GetLayerID(n) for n in layer_names]
        self.widths = sorted(set(widths))
        self.via_sizes = sorted(set(via_sizes))
        ol = pcbnew.SHAPE_POLY_SET()
        board.GetBoardPolygonOutlines(ol, False)
        self.outline = poly_points(ol)[0]
        x0, y0, x1, y1 = bbox_of(self.outline)
        self.x0, self.y0 = x0, y0
        self.nx = int(math.ceil((x1 - x0) / R)) + 1
        self.ny = int(math.ceil((y1 - y0) / R)) + 1
        base = array("h", [0]) * (self.nx * self.ny)
        for j in range(self.ny):
            y = y0 + j * R
            for i in range(self.nx):
                if not inside_poly(self.outline, x0 + i * R, y):
                    base[j * self.nx + i] = BLOCK
        L = len(self.lids)
        self.trk = {w: [array("h", base) for _ in range(L)] for w in self.widths}
        self.via = {vs: array("h", base) for vs in self.via_sizes}   # las vías atraviesan todas las capas
        m = len(self.outline)
        for k in range(m):
            (ax, ay), (bx, by) = self.outline[k], self.outline[(k + 1) % m]
            f, bb = seg_shape(ax, ay, bx, by, 0.0)
            for w in self.widths:
                for li in range(L):
                    self.stamp(self.trk[w][li], BLOCK, f, bb, EDGE + w / 2 + MARGIN)
            for (d, _), arr in self.via.items():
                self.stamp(arr, BLOCK, f, bb, EDGE + d / 2 + MARGIN)

    def clone(self):
        g = Grid.__new__(Grid)
        g.__dict__.update(self.__dict__)
        g.trk = {w: [array("h", a) for a in arrs] for w, arrs in self.trk.items()}
        g.via = {vs: array("h", a) for vs, a in self.via.items()}
        return g

    def arrays(self):
        for arrs in self.trk.values():
            yield from arrs
        yield from self.via.values()

    def cell(self, x, y):
        return int(round((x - self.x0) / R)), int(round((y - self.y0) / R))

    def clip_of(self, bb, extra):
        i1, j1 = self.cell(bb[0] - extra, bb[1] - extra)
        i2, j2 = self.cell(bb[2] + extra, bb[3] + extra)
        return max(0, i1), max(0, j1), min(self.nx - 1, i2), min(self.ny - 1, j2)

    def restore_from(self, src, clip):
        """Copia de src la región clip (i1, j1, i2, j2)."""
        i1, j1, i2, j2 = clip
        for dst, s in zip(self.arrays(), src.arrays()):
            for j in range(j1, j2 + 1):
                a, b = j * self.nx + i1, j * self.nx + i2 + 1
                dst[a:b] = s[a:b]

    def stamp(self, arr, net, f, bb, radius, clip=None):
        x1, y1, x2, y2 = bb
        i1, j1 = self.cell(x1 - radius, y1 - radius)
        i2, j2 = self.cell(x2 + radius, y2 + radius)
        i1, j1, i2, j2 = max(0, i1), max(0, j1), min(self.nx - 1, i2), min(self.ny - 1, j2)
        if clip:
            i1, j1, i2, j2 = max(i1, clip[0]), max(j1, clip[1]), min(i2, clip[2]), min(j2, clip[3])
        nx = self.nx
        for j in range(j1, j2 + 1):
            y = self.y0 + j * R
            row = j * nx
            for i in range(i1, i2 + 1):
                if f(self.x0 + i * R, y) <= radius:
                    k = row + i
                    v = arr[k]
                    if v == 0:
                        arr[k] = net
                    elif v != net:
                        arr[k] = BLOCK

    def add_copper(self, li, net, clearance, f, bb, clip=None):
        """Cobre en la capa li: bloquea ejes de pista y centros de vía de otras redes."""
        for w in self.widths:
            self.stamp(self.trk[w][li], net, f, bb, w / 2 + clearance + MARGIN, clip)
        for (d, _), arr in self.via.items():
            self.stamp(arr, net, f, bb, d / 2 + clearance + MARGIN, clip)

    def add_hole(self, cx, cy, drill, net, clip=None):
        """Agujero: separación al cobre de otras redes y separación entre agujeros (cualquier red)."""
        f, bb = disc_shape(cx, cy, drill / 2)
        for w in self.widths:
            for li in range(len(self.lids)):
                self.stamp(self.trk[w][li], net, f, bb, w / 2 + HOLE_CLEARANCE + MARGIN, clip)
        for (_, dr), arr in self.via.items():
            self.stamp(arr, BLOCK, f, bb, dr / 2 + HOLE_TO_HOLE + MARGIN, clip)

    def block_vias(self, f, bb, extra):
        """Prohíbe centros de vía (cualquier red) a menos de taladro/2 + extra de la forma."""
        for (_, dr), arr in self.via.items():
            self.stamp(arr, BLOCK, f, bb, dr / 2 + extra)

    def free(self, arr, k, net):
        v = arr[k]
        return v == 0 or v == net


def build_grid(board, layer_names, widths, via_sizes):
    g = Grid(board, layer_names, widths, via_sizes)
    lids = g.lids
    for fp in board.GetFootprints():
        for pad in fp.Pads():
            net = pad.GetNetCode() or BLOCK
            for li, lid in enumerate(lids):
                if not pad.IsOnLayer(lid) or not pad.FlashLayer(lid):
                    continue
                clr = to_mm(pad.GetOwnClearance(lid))
                for pts in poly_points(pad.GetEffectivePolygon(lid, pcbnew.ERROR_OUTSIDE)):
                    f, bb = poly_dist(pts), bbox_of(pts)
                    g.add_copper(li, net, clr, f, bb)
                    if not pad.HasHole():   # sin vías en pads SMD (la soldadura se escurre)
                        g.block_vias(f, bb, 0.1)
            if pad.HasHole():
                p = pad.GetPosition()
                g.add_hole(to_mm(p.x), to_mm(p.y), to_mm(max(pad.GetDrillSizeX(), pad.GetDrillSizeY())), net)
    for t in board.GetTracks():
        net = t.GetNetCode() or BLOCK
        if t.Type() == pcbnew.PCB_VIA_T:
            p = t.GetPosition()
            cx, cy = to_mm(p.x), to_mm(p.y)
            f, bb = disc_shape(cx, cy, to_mm(t.GetWidth(pcbnew.F_Cu)) / 2)
            for li, lid in enumerate(lids):
                g.add_copper(li, net, to_mm(t.GetOwnClearance(lid)), f, bb)
            g.add_hole(cx, cy, to_mm(t.GetDrillValue()), net)
            continue
        if t.GetLayer() not in lids:
            continue
        li = lids.index(t.GetLayer())
        a, b = t.GetStart(), t.GetEnd()
        f, bb = seg_shape(to_mm(a.x), to_mm(a.y), to_mm(b.x), to_mm(b.y), to_mm(t.GetWidth()) / 2)
        g.add_copper(li, net, to_mm(t.GetOwnClearance(t.GetLayer())), f, bb)
    for z in board.Zones():
        if z.GetIsRuleArea():
            for pts in poly_points(z.Outline()):
                f, bb = poly_dist(pts), bbox_of(pts)
                for li, lid in enumerate(lids):
                    if z.IsOnLayer(lid) and z.GetDoNotAllowTracks():
                        for w in g.widths:
                            g.stamp(g.trk[w][li], BLOCK, f, bb, w / 2)
                if z.GetDoNotAllowVias() and any(z.IsOnLayer(l) for l in lids):
                    for (d, _), arr in g.via.items():
                        g.stamp(arr, BLOCK, f, bb, d / 2)
            continue
        for li, lid in enumerate(lids):
            if not z.IsOnLayer(lid):
                continue
            if z.GetNetname() in FLEX_NETS:
                continue      # planos y rellenos de GND/+3V3: se vuelven a rellenar alrededor de lo nuevo
            net = z.GetNetCode() or BLOCK
            for pts in poly_points(z.GetFilledPolysList(lid)):
                g.add_copper(li, net, ZONE_CLEARANCE, poly_dist(pts), bbox_of(pts))
    return g


def endpoints(g, item, pos=None):
    """Extremos de una conexión: celdas (capa, i, j) donde puede terminar la pista y celdas donde
    tiene que terminar con una vía (zonas en capas que no se rutean, como el plano de GND de L2)."""
    cells, via_cells = [], []
    if item.Type() == pcbnew.PCB_PAD_T:
        for li, lid in enumerate(g.lids):
            if not item.IsOnLayer(lid) or not item.FlashLayer(lid):
                continue
            for pts in poly_points(item.GetEffectivePolygon(lid, pcbnew.ERROR_INSIDE)):
                x1, y1, x2, y2 = bbox_of(pts)
                i1, j1 = g.cell(x1, y1)
                i2, j2 = g.cell(x2, y2)
                for j in range(j1, j2 + 1):
                    for i in range(i1, i2 + 1):
                        if inside_poly(pts, g.x0 + i * R, g.y0 + j * R):
                            cells.append((li, i, j))
            p = item.GetPosition()
            cells.append((li,) + g.cell(to_mm(p.x), to_mm(p.y)))
    elif item.Type() == pcbnew.PCB_VIA_T:
        p = item.GetPosition()
        i, j = g.cell(to_mm(p.x), to_mm(p.y))
        cells += [(li, i, j) for li in range(len(g.lids))]
    elif item.Type() in (pcbnew.PCB_TRACE_T, pcbnew.PCB_ARC_T) and item.GetLayer() in g.lids:
        li = g.lids.index(item.GetLayer())
        a, b = item.GetStart(), item.GetEnd()
        n = max(1, int(to_mm(item.GetLength()) / R))
        for k in range(n + 1):
            x = to_mm(a.x) + (to_mm(b.x) - to_mm(a.x)) * k / n
            y = to_mm(a.y) + (to_mm(b.y) - to_mm(a.y)) * k / n
            cells.append((li,) + g.cell(x, y))
    elif item.Type() == pcbnew.PCB_ZONE_T:
        if pos is None:
            c = item.GetBoundingBox().GetCenter()
            pos = (to_mm(c.x), to_mm(c.y))
        for lid in item.GetLayerSet().Seq():
            if not pcbnew.IsCopperLayer(lid):
                continue
            fill = item.GetFilledPolysList(lid)
            ax, ay = zone_anchor(fill, pos)
            i1, j1, i2, j2 = g.clip_of((ax, ay, ax, ay), ZONE_REACH)
            inside = [(i, j) for j in range(j1, j2 + 1) for i in range(i1, i2 + 1)
                      if fill.Contains(pcbnew.VECTOR2I(mm(g.x0 + i * R), mm(g.y0 + j * R)))]
            if lid in g.lids:
                li = g.lids.index(lid)
                cells += [(li, i, j) for i, j in inside]
            else:
                via_cells += [(li, i, j) for li in range(len(g.lids)) for i, j in inside]
    return cells, via_cells


def zone_anchor(fill, pos):
    """Punto del relleno más cercano a pos (pos mismo si cae dentro)."""
    if fill.OutlineCount() == 0 or fill.Contains(pcbnew.VECTOR2I(mm(pos[0]), mm(pos[1]))):
        return pos
    best, bp = 1e18, pos
    for o in range(fill.OutlineCount()):
        ol = fill.Outline(o)
        n = ol.PointCount()
        pts = [(to_mm(ol.CPoint(i).x), to_mm(ol.CPoint(i).y)) for i in range(n)]
        for i in range(n):
            (x1, y1), (x2, y2) = pts[i], pts[(i + 1) % n]
            dx, dy = x2 - x1, y2 - y1
            L = dx * dx + dy * dy
            t = 0.0 if L == 0 else max(0.0, min(1.0, ((pos[0] - x1) * dx + (pos[1] - y1) * dy) / L))
            qx, qy = x1 + t * dx, y1 + t * dy
            d = (qx - pos[0]) ** 2 + (qy - pos[1]) ** 2
            if d < best:
                best, bp = d, (qx, qy)
    return bp


def island_ends(g, za, zb):
    """Extremos para unir islas de zonas: de las islas pequeñas de za a la mayor de zb (o de za si son
    la misma zona), buscando la mayor solo cerca de las pequeñas."""
    def cells_in(fill, i, box, stride):
        i1, j1, i2, j2 = box
        return [(ii, jj) for jj in range(j1, j2 + 1, stride) for ii in range(i1, i2 + 1, stride)
                if fill.Contains(pcbnew.VECTOR2I(mm(g.x0 + ii * R), mm(g.y0 + jj * R)), i)]

    def bbox_cells(bb, extra):
        return g.clip_of((to_mm(bb.GetLeft()), to_mm(bb.GetTop()), to_mm(bb.GetRight()), to_mm(bb.GetBottom())),
                         extra)
    ea, eb = ([], []), ([], [])
    for lid in za.GetLayerSet().Seq():
        if not pcbnew.IsCopperLayer(lid) or not zb.IsOnLayer(lid):
            continue
        fa, fb = za.GetFilledPolysList(lid), zb.GetFilledPolysList(lid)
        if fa.OutlineCount() == 0 or fb.OutlineCount() == 0:
            continue
        area = [abs(fb.Outline(i).Area()) for i in range(fb.OutlineCount())]
        main = max(range(len(area)), key=lambda i: area[i])
        small = [i for i in range(fa.OutlineCount()) if za.m_Uuid.AsString() != zb.m_Uuid.AsString() or i != main]
        ca, cb = [], []
        for i in small:
            bb = fa.Outline(i).BBox()
            ca += cells_in(fa, i, bbox_cells(bb, 0.0), 1)
            cb += cells_in(fb, main, bbox_cells(bb, ZONE_REACH), 1)
        if lid in g.lids:
            li = g.lids.index(lid)
            ea[0].extend((li, i, j) for i, j in ca)
            eb[0].extend((li, i, j) for i, j in set(cb))
        else:
            ea[1].extend((li, i, j) for li in range(len(g.lids)) for i, j in ca)
            eb[1].extend((li, i, j) for li in range(len(g.lids)) for i, j in set(cb))
    return ea, eb


def usable(g, w, vs, net, ends):
    """Extremos donde el eje de la pista (y la vía final, si hace falta) respeta la separación.
    Si no queda ninguno, ese ancho no cabe en el pad y se prueba el siguiente."""
    cells, via_cells = ends
    ok = [c for c in cells if g.trk[w][c[0]][c[2] * g.nx + c[1]] in (0, net)]
    ok += [c for c in via_cells if g.trk[w][c[0]][c[2] * g.nx + c[1]] in (0, net)
           and g.via[vs][c[2] * g.nx + c[1]] in (0, net)]
    return ok


MOVES = [(1, 0, 1.0), (-1, 0, 1.0), (0, 1, 1.0), (0, -1, 1.0),
         (1, 1, 1.4142), (1, -1, 1.4142), (-1, 1, 1.4142), (-1, -1, 1.4142)]


def astar(g, w, vs, net, starts, goals, layer_cost, soft=None, hist=None, max_expand=500000, neck=None):
    """A* en la rejilla g. Con soft, las celdas que soft bloquea se permiten con penalización.
    layer_cost[l] None prohíbe la capa. neck = (celdas (i, j)) permite pasar con NECK_W donde el
    ancho w no cabe, solo en esas celdas (junto a los pads de los extremos)."""
    starts = [c for c in starts if layer_cost[c[0]] is not None]
    goals = [c for c in goals if layer_cost[c[0]] is not None]
    goal_set = set(goals)
    if not starts or not goal_set:
        return None
    gx = [c[1] for c in goal_set]
    gy = [c[2] for c in goal_set]
    bx1, bx2, by1, by2 = min(gx), max(gx), min(gy), max(gy)

    def h(i, j):
        dx = bx1 - i if i < bx1 else (i - bx2 if i > bx2 else 0)
        dy = by1 - j if j < by1 else (j - by2 if j > by2 else 0)
        return math.hypot(dx, dy)

    nx, ny = g.nx, g.ny
    N = nx * ny
    trk = g.trk[w]
    via = g.via[vs]
    ncells = neck if neck and w > NECK_W else None
    ntrk = g.trk[NECK_W] if ncells else None

    def ok(li, i2, j2, k2):
        v = trk[li][k2]
        if v == 0 or v == net:
            return True
        if ncells is not None and (i2, j2) in ncells:
            v = ntrk[li][k2]
            return v == 0 or v == net
        return False
    strk = soft.trk[w] if soft else None
    svia = soft.via[vs] if soft else None
    L = len(g.lids)
    best = {}
    heap = []
    parent = {}
    for s in starts:
        best[s] = 0.0
        parent[s] = None
        heapq.heappush(heap, (h(s[1], s[2]), 0.0, s))
    done = set()

    def penalty(li, k):
        v = strk[li][k]
        if v == 0 or v == net:
            return 0.0
        return RIP_PENALTY + hist[li * N + k]

    min_via = (vs[1] + HOLE_TO_HOLE + MARGIN) / R      # celdas entre centros de vías del mismo camino

    def near_own_via(st):
        """True si el camino que llega a st cambió de capa (puso una vía) a menos de min_via celdas."""
        cur = st
        for _ in range(16):
            par = parent.get(cur)
            if par is None:
                return False
            if par[0] != cur[0] and math.hypot(cur[1] - st[1], cur[2] - st[2]) < min_via:
                return True
            cur = par
        return False

    while heap:
        _, cost, s = heapq.heappop(heap)
        if s in done:
            continue
        done.add(s)
        if s in goal_set:
            path = [s]
            while parent[path[-1]] is not None:
                path.append(parent[path[-1]])
            return path[::-1]
        if len(done) > max_expand:
            return None
        li, i, j = s
        lc = layer_cost[li]
        for di, dj, step in MOVES:
            ni, nj = i + di, j + dj
            if not (0 <= ni < nx and 0 <= nj < ny):
                continue
            k2 = nj * nx + ni
            ns = (li, ni, nj)
            if not ok(li, ni, nj, k2) and ns not in goal_set:
                continue
            if di and dj:   # diagonal: las dos celdas ortogonales deben estar libres
                if not ok(li, ni, j, j * nx + ni) or not ok(li, i, nj, nj * nx + i):
                    continue
            nc = cost + step * lc
            if soft:
                nc += penalty(li, k2)
                if di and dj:
                    nc += penalty(li, j * nx + ni) + penalty(li, nj * nx + i)
            if nc < best.get(ns, 1e18):
                best[ns] = nc
                parent[ns] = s
                heapq.heappush(heap, (nc + h(ni, nj), nc, ns))
        k = j * nx + i
        vv = via[k]
        if (vv == 0 or vv == net) and not near_own_via(s):
            extra = 0.0
            if soft:
                sv = svia[k]
                if sv != 0 and sv != net:
                    extra = RIP_PENALTY + hist[li * N + k]
            for l2 in range(L):
                if l2 == li or layer_cost[l2] is None:
                    continue
                ns = (l2, i, j)
                if not ok(l2, i, j, k) and ns not in goal_set:
                    continue
                nc = cost + VIA_COST + extra
                if soft:
                    nc += penalty(l2, k)
                if nc < best.get(ns, 1e18):
                    best[ns] = nc
                    parent[ns] = s
                    heapq.heappush(heap, (nc + h(i, j), nc, ns))
    return None


def path_shapes(g, path, w, vs, net, clr, via_start=False, via_end=False, widths=None):
    """Convierte el camino de celdas en formas: ("seg", capa, ax, ay, bx, by, ancho, red, sep) y
    ("via", None, x, y, diámetro, taladro, red, sep). via_start/via_end añaden la vía a un plano.
    widths da el ancho que admite cada celda (cuellos); un tramo usa el menor de sus dos extremos."""
    wc = widths or [w] * len(path)
    segs, vias = [], []
    if via_start:
        vias.append((path[0][1], path[0][2]))
    if via_end and (len(path) > 1 or not via_start):
        vias.append((path[-1][1], path[-1][2]))
    start = prev = path[0]
    direction, run_w = None, None
    for n in range(1, len(path)):
        c = path[n]
        if c[0] != prev[0]:
            if prev != start:
                segs.append((prev[0], start, prev, run_w))
            vias.append((prev[1], prev[2]))
            start, direction, run_w = c, None, None
        else:
            d = (c[1] - prev[1], c[2] - prev[2])
            sw = min(wc[n], wc[n - 1])
            if direction is not None and (d != direction or sw != run_w):
                segs.append((prev[0], start, prev, run_w))
                start = prev
            direction, run_w = d, sw
        prev = c
    if prev != start:
        segs.append((prev[0], start, prev, run_w))
    vias = list(dict.fromkeys(vias))
    shapes = []
    for li, a, b, sw in segs:
        shapes.append(("seg", li, g.x0 + a[1] * R, g.y0 + a[2] * R, g.x0 + b[1] * R, g.y0 + b[2] * R, sw or w, net,
                       clr))
    for i, j in vias:
        shapes.append(("via", None, g.x0 + i * R, g.y0 + j * R, vs[0], vs[1], net, clr))
    return shapes


def shape_bbox(s):
    if s[0] == "seg":
        return min(s[2], s[4]), min(s[3], s[5]), max(s[2], s[4]), max(s[3], s[5])
    return s[2], s[3], s[2], s[3]


def stamp_shape(g, s, clip=None):
    if s[0] == "seg":
        _, li, ax, ay, bx, by, w, net, clr = s
        f, bb = seg_shape(ax, ay, bx, by, w / 2)
        g.add_copper(li, net, clr, f, bb, clip)
    else:
        _, _, x, y, d, dr, net, clr = s
        f, bb = disc_shape(x, y, d / 2)
        for li in range(len(g.lids)):
            g.add_copper(li, net, clr, f, bb, clip)
        g.add_hole(x, y, dr, net, clip)


def shapes_conflict(p, q):
    """True si dos formas violan separación (p y q con el formato de path_shapes)."""
    same = p[-2] == q[-2]
    clr = max(p[-1], q[-1]) + MARGIN
    if p[0] == "seg" and q[0] == "seg":
        if same or p[1] != q[1]:
            return False
        return seg_seg_dist((p[2], p[3]), (p[4], p[5]), (q[2], q[3]), (q[4], q[5])) <= p[6] / 2 + q[6] / 2 + clr
    if p[0] == "via" and q[0] == "via":
        dist = math.hypot(p[2] - q[2], p[3] - q[3])
        if dist <= p[5] / 2 + q[5] / 2 + HOLE_TO_HOLE + MARGIN:
            return True
        return not same and dist <= p[4] / 2 + q[4] / 2 + clr
    v, s = (p, q) if p[0] == "via" else (q, p)
    if same:
        return False
    dist = seg_dist(v[2], v[3], s[2], s[3], s[4], s[5])
    return dist <= v[4] / 2 + s[6] / 2 + clr or dist <= v[5] / 2 + s[6] / 2 + HOLE_CLEARANCE + MARGIN


class Router:
    def __init__(self, board, layer_names, pairs, netclass, positions):
        self.removed = []
        self.board = board
        self.pairs = pairs
        self.positions = positions
        self.netclass = netclass
        widths, vias = {0.2}, {SMALL_VIA}
        for a, _ in pairs:
            for w, vs in self.options(a):
                widths.add(w)
                vias.add(vs)
        t0 = time.time()
        self.fixed = build_grid(board, layer_names, widths, vias)
        self.g = self.fixed.clone()
        print("rejilla %d x %d x %d, anchos %s, vías %s (%.0f s)" % (
            self.fixed.nx, self.fixed.ny, len(self.fixed.lids), self.fixed.widths, self.fixed.via_sizes,
            time.time() - t0))
        self.layer_cost = [1.0 if n in OUTER else INNER_COST for n in layer_names]
        self.layer_cost_power = [1.0 if n in OUTER else None for n in layer_names]
        self.neck_cache = {}
        self.hist = array("f", [0.0]) * (len(layer_names) * self.fixed.nx * self.fixed.ny)
        self.routes = {}          # índice de par -> (formas, objetos de la placa)
        self.used = {}            # índice de par -> (ancho, vía)
        self.end_cache = {}

    def outer_only(self, item):
        return any(c in OUTER_CLASSES for c in self.netclass(item).GetName().split(","))

    def options(self, item):
        """Ancho y vía de la clase (con cuello de NECK_W junto a los pads finos); si aun así no cabe, vía
        pequeña y después pista más delgada (se informa como «reducida»)."""
        nc = self.netclass(item)
        w = round(to_mm(nc.GetTrackWidth()), 3)
        vs = (round(to_mm(nc.GetViaDiameter()), 3), round(to_mm(nc.GetViaDrill()), 3))
        out = []
        for o in ((w, vs), (w, SMALL_VIA), (min(w, 0.3), SMALL_VIA), (0.2, SMALL_VIA)):
            if o not in out:
                out.append(o)
        return out

    def costs(self, item):
        """Las redes de potencia y de conmutación no pasan por la capa interna (plano de +3V3)."""
        return self.layer_cost_power if self.outer_only(item) else self.layer_cost

    def neck(self, idx):
        """Celdas (i, j) a menos de NECK_R de los pads de los extremos del par."""
        if idx not in self.neck_cache:
            ea, eb = self.end_cache[idx]
            r = int(round(NECK_R / R))
            disc = [(di, dj) for di in range(-r, r + 1) for dj in range(-r, r + 1) if di * di + dj * dj <= r * r]
            cells = set()
            for item, e in zip(self.pairs[idx], (ea, eb)):
                if item.Type() != pcbnew.PCB_PAD_T:
                    continue
                for _, i, j in set(e[0]):
                    for di, dj in disc:
                        cells.add((i + di, j + dj))
            self.neck_cache[idx] = cells
        return self.neck_cache[idx]

    def widths_for(self, g, p, w, net):
        """Ancho que admite cada celda del camino: w o, en un cuello, NECK_W."""
        if w <= NECK_W:
            return None
        out = []
        for li, i, j in p:
            v = g.trk[w][li][j * g.nx + i]
            out.append(w if v in (0, net) else NECK_W)
        return out

    def ends(self, g, idx, w, vs, net):
        if idx not in self.end_cache:
            (a, b), (pa, pb) = self.pairs[idx], self.positions[idx]
            if pa is None and pb is None:
                self.end_cache[idx] = island_ends(self.fixed, a, b)
            else:
                self.end_cache[idx] = (endpoints(self.fixed, a, pa), endpoints(self.fixed, b, pb))
        ea, eb = self.end_cache[idx]
        we = min(w, NECK_W)     # los extremos en un pad pueden ser de cuello
        return usable(g, we, vs, net, ea), usable(g, we, vs, net, eb)

    def shapes_for(self, idx, p, w, vs, net, clr, g):
        ea, eb = self.end_cache[idx]
        via_start = p[0] in set(ea[1]) and p[0] not in set(ea[0])
        via_end = p[-1] in set(eb[1]) and p[-1] not in set(eb[0])
        return path_shapes(self.fixed, p, w, vs, net, clr, via_start, via_end, self.widths_for(g, p, w, net))

    def commit(self, idx, shapes):
        a = self.pairs[idx][0]
        netinfo = a.GetNet()
        items = []
        for s in shapes:
            if s[0] == "seg":
                _, li, ax, ay, bx, by, w, _, _ = s
                tr = pcbnew.PCB_TRACK(self.board)
                tr.SetStart(pcbnew.VECTOR2I(mm(ax), mm(ay)))
                tr.SetEnd(pcbnew.VECTOR2I(mm(bx), mm(by)))
                tr.SetWidth(mm(w))
                tr.SetLayer(self.g.lids[li])
            else:
                _, _, x, y, d, dr, _, _ = s
                tr = pcbnew.PCB_VIA(self.board)
                tr.SetPosition(pcbnew.VECTOR2I(mm(x), mm(y)))
                tr.SetWidth(mm(d))
                tr.SetDrill(mm(dr))
            tr.SetNet(netinfo)
            self.board.Add(tr)
            items.append(tr)
            stamp_shape(self.g, s)
        self.routes[idx] = (shapes, items)

    def ripup(self, idx):
        shapes, items = self.routes.pop(idx)
        self.used.pop(idx, None)
        for it in items:
            self.board.Remove(it)
            # Que Python no libere las pistas y vías quitadas mientras KiCad pueda guardar punteros a
            # ellas (conectividad, caché por KIID): con muchos arranques, Fill se caía con -11.
            self.removed.append(it)
        xs1, ys1, xs2, ys2 = zip(*[shape_bbox(s) for s in shapes])
        bb = (min(xs1), min(ys1), max(xs2), max(ys2))
        clip = self.g.clip_of(bb, INFL)
        self.g.restore_from(self.fixed, clip)
        cx1, cy1 = self.g.x0 + clip[0] * R - INFL, self.g.y0 + clip[1] * R - INFL
        cx2, cy2 = self.g.x0 + clip[2] * R + INFL, self.g.y0 + clip[3] * R + INFL
        for other, _ in self.routes.values():
            for s in other:
                sb = shape_bbox(s)
                if sb[2] >= cx1 and sb[0] <= cx2 and sb[3] >= cy1 and sb[1] <= cy2:
                    stamp_shape(self.g, s, clip)

    def conflicts(self, shapes):
        out = set()
        for idx, (other, _) in self.routes.items():
            for s in shapes:
                if any(shapes_conflict(s, q) for q in other):
                    out.add(idx)
                    break
        return out

    def try_route(self, idx):
        a, _ = self.pairs[idx]
        net = a.GetNetCode()
        clr = to_mm(self.netclass(a).GetClearance())
        for w, vs in self.options(a):
            sa, sb = self.ends(self.g, idx, w, vs, net)
            p = astar(self.g, w, vs, net, sa, sb, self.costs(a), neck=self.neck(idx))
            if p is not None:
                shapes = self.shapes_for(idx, p, w, vs, net, clr, self.g)
                if not shapes:
                    return False
                self.commit(idx, shapes)
                self.used[idx] = (w, vs)
                return True
        return False

    def try_ripup(self, idx):
        """Busca un camino ignorando (con coste) las rutas de este programa y arranca las que estorban."""
        a, _ = self.pairs[idx]
        net = a.GetNetCode()
        clr = to_mm(self.netclass(a).GetClearance())
        for w, vs in self.options(a):
            sa, sb = self.ends(self.fixed, idx, w, vs, net)
            p = astar(self.fixed, w, vs, net, sa, sb, self.costs(a), soft=self.g, hist=self.hist,
                      max_expand=2500000, neck=self.neck(idx))
            if p is None:
                continue
            shapes = self.shapes_for(idx, p, w, vs, net, clr, self.fixed)
            if not shapes:
                continue
            victims = self.conflicts(shapes)
            N = self.fixed.nx * self.fixed.ny
            for li, i, j in p:
                k = j * self.fixed.nx + i
                if not self.g.free(self.g.trk[w][li], k, net):
                    self.hist[li * N + k] += HIST_STEP
            for v in victims:
                self.ripup(v)
            self.commit(idx, shapes)
            self.used[idx] = (w, vs)
            return victims
        return None


def main():
    path, drc_json = sys.argv[1:3]
    layer_names = (sys.argv[3] if len(sys.argv) > 3 else "F.Cu,In2.Cu,B.Cu").split(",")
    skip = {n for n in os.environ.get("SKIP_NETS", "").split(",") if n}
    minutes = float(os.environ.get("ROUTE_REST_MINUTES", "30"))
    board = pcbnew.LoadBoard(path)
    pcbnew.ZONE_FILLER(board).Fill(board.Zones())   # las zonas sirven de extremo y de obstáculo
    rep = json.load(open(drc_json))
    pairs = []
    for u in rep.get("unconnected_items", []):
        its = u.get("items", [])
        items = [board.ResolveItem(pcbnew.KIID(it["uuid"])) for it in its]
        if len(its) != 2 or any(x is None for x in items):
            continue
        items = [x.Cast() for x in items]
        # Las redes omitidas (GND) sí se rutean cuando tocan un pin de un CI: si no, sus pines quedan
        # encerrados por las señales antes de que existan los rellenos.
        ic = any(x.Type() == pcbnew.PCB_PAD_T and x.GetParentFootprint().GetReference().startswith("U")
                 for x in items)
        # ...salvo de pin a pin del mismo CI: esa unión rodea a los pines de en medio y los encierra;
        # la hacen los rellenos de GND en la segunda pasada.
        if ic and all(x.Type() == pcbnew.PCB_PAD_T for x in items) and \
                items[0].GetParentFootprint().GetReference() == items[1].GetParentFootprint().GetReference():
            ic = False
        if items[0].GetNetname().split("/")[-1] not in skip or ic:
            # El DRC da como posición de una zona su primer vértice, no el punto más cercano: se usa la
            # posición del otro extremo.
            pos = [(it["pos"]["x"], it["pos"]["y"]) for it in its]
            zone = [x.Type() == pcbnew.PCB_ZONE_T for x in items]
            if zone[0] and not zone[1]:
                pos[0] = pos[1]
            elif zone[1] and not zone[0]:
                pos[1] = pos[0]
            elif zone[0] and zone[1]:
                pos = [None, None]
            pairs.append((items, pos))
    print("pendientes:", len(pairs), "(omitidas: %s)" % ",".join(sorted(skip)) if skip else "")
    nsets = board.GetDesignSettings().m_NetSettings

    def netclass(item):
        return nsets.GetEffectiveNetClass(item.GetNetname())

    def plen(p):
        # longitud y, para desempatar siempre igual, red y posiciones (las uniones de islas, al final)
        if p[1][0] is None or p[1][1] is None:
            return (1e9, p[0][0].GetNetname(), (0, 0))
        (ax, ay), (bx, by) = p[1]
        return (round(math.hypot(ax - bx, ay - by), 4), p[0][0].GetNetname(), p[1])
    pairs.sort(key=plen)
    limit = int(os.environ.get("ROUTE_REST_LIMIT", "0")) or None
    pairs = pairs[:limit]
    positions = [pp for _, pp in pairs]
    pairs = [items for items, _ in pairs]
    rt = Router(board, layer_names, pairs, netclass, positions)

    def label(idx):
        a, b = pairs[idx]
        return "%s: %s -> %s" % (a.GetNetname(), describe(a), describe(b))
    t0 = time.time()
    queue = deque(range(len(pairs)))
    rips = Counter()
    failed = set()
    tries = 0
    while queue and time.time() - t0 < minutes * 60:
        idx = queue.popleft()
        if idx in rt.routes:
            continue
        tries += 1
        if rt.try_route(idx):
            continue
        if rips[idx] >= MAX_RIPS:
            failed.add(idx)
            continue
        rips[idx] += 1
        victims = rt.try_ripup(idx)
        if victims is None:
            failed.add(idx)          # no cabe ni arrancando rutas (o se agotó la búsqueda)
            print("  sin camino aun arrancando rutas:", label(idx))
            continue
        for v in sorted(victims):
            queue.append(v)
        if victims:
            print("  %s arranca %d" % (label(idx), len(victims)))
    pending = [i for i in range(len(pairs)) if i not in rt.routes]
    filler = pcbnew.ZONE_FILLER(board)
    filler.Fill(board.Zones())
    pcbnew.SaveBoard(path, board)
    for idx in sorted(rt.routes):
        w, vs = rt.used[idx]
        if (w, vs) != rt.options(pairs[idx][0])[0]:
            print("  reducida: %s (%.2f mm, vía %.1f/%.1f)" % (label(idx), w, vs[0], vs[1]))
        neck = sum(math.hypot(s[4] - s[2], s[5] - s[3]) for s in rt.routes[idx][0] if s[0] == "seg" and s[6] < w)
        if neck > 0:
            print("  cuello: %s (%.1f mm a %.2f mm junto a pads; el resto a %.2f mm)" % (label(idx), neck, NECK_W, w))
    for idx in pending:
        print("  sin ruta:", label(idx))
    inner = sum(1 for shapes, _ in rt.routes.values() for s in shapes
                if s[0] == "seg" and layer_names[s[1]] not in ("F.Cu", "B.Cu"))
    print("ruteadas %d de %d, sin ruta %d, intentos %d, tramos internos %d (%.0f s)" % (
        len(rt.routes), len(pairs), len(pending), tries, inner, time.time() - t0))


if __name__ == "__main__":
    main()
