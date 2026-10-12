"""Comprueba el MONTAJE de la carcasa V2.3 (mechanical/v2.3) paso a paso con la placa v0.2.

Cada paso mueve una pieza o un conjunto por su recorrido de montaje, en tramos cortos, y busca
choques con lo que ya está puesto en ese momento (orden de mechanical/v2.3/README.md):

  1. 18650 a su cuna: baja corrida hacia delante lo justo para pasar el collar, se empuja hacia
     atrás ya entera bajo el collar y baja recta a la repisa.
  2. Carrier al chasis por el frente (-Y), sin la placa: la envolvente medida de V2.3 y, aparte, la
     carrier aproximada con sus componentes (carrier_bdlx.py), que no tiene margen en los cantos.
  3. Placa al chasis por los rieles, desde arriba (-Z) y desde abajo (+Z), con la carrier puesta.
  4. Chasis armado (chasis, placa, carrier y la clavija de J301) al tubo desde arriba, con la 18650
     puesta.
  5. Clavijas de J102 y J404 desde abajo (+Z), sin la base.
  6. Tapa del panel hacia dentro (-Y) con OLED, botón, panel-usb y la clavija de J502.
  7. Plataforma del IMU y tapa de antena desde arriba (-Z), sin el giro final de la bayoneta.

Además dibuja cortes horizontales del fondo para buscar paso al cable de la 18650 hasta J102.

Uso:
    PYTHONPATH=/Applications/FreeCAD.app/Contents/Resources/lib \\
    /Applications/FreeCAD.app/Contents/Resources/bin/python check_montaje_v2_3.py

Lee mechanical/v2.3/generated/TresVizo-V2.3.FCStd y los STEP de esta carpeta. La placa y sus
clavijas se mueven chasis.desplazamiento_placa_y hacia el panel: en V2.3 la placa va más adelante que
en estos STEP (dorso en y 1.5). La plataforma y la tapa de antena se comprueban solo contra lo de
dentro (el encaje con el tubo es el de V2.2: uñas y bayoneta, que no bajan en línea recta). Escribe
montaje-v2.3/resultado.json y los cortes en montaje-v2.3/. Comprueba geometría, no tolerancias ni
rigidez.
"""

import json
import math
import sys
import time
from pathlib import Path

import FreeCAD as App
import Import
import Part

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
V23 = REPO / "mechanical" / "v2.3"
OUT = HERE / "montaje-v2.3"
OUT.mkdir(exist_ok=True)
T0 = time.time()
LIM = 0.05          # mm³: por debajo es contacto, no choque
V = App.Vector


def log(*a):
    print("[%6.1f s]" % (time.time() - T0), *a, flush=True)


# ---------------------------------------------------------------- piezas
doc = App.openDocument(str(V23 / "generated" / "TresVizo-V2.3.FCStd"))
P = {o.Name: o.Shape for o in doc.Objects if hasattr(o, "Shape") and not o.Shape.isNull()}
base, tube, cap = P["_01_threaded_base"], P["_02_logo_tube"], P["_03_antenna_cap"]
plat, cover, sled = P["_04_imu_platform"], P["_05_panel_cover"], P["_08_sled"]
carrier, battery = P["ref_carrier"], P["ref_battery"]
keepers = P["ref_nut_keepers"]
panel_refs = {"oled": P["ref_oled"], "boton": P["ref_button"]}
imu = {"imu_pcb": P["ref_imu_pcb"], "imu_chip": P["ref_imu_chip"], "sma_antena": P["ref_sma"]}
pm = json.loads((V23 / "parameters.json").read_text(encoding="utf-8"))
CH = pm["chasis"]
DY = CH.get("desplazamiento_placa_y", 0.0)
sys.path.insert(0, str(HERE))
import carrier_bdlx  # noqa: E402
carrier_parts = carrier_bdlx.build(CH["carrier"])


def load_step(name):
    d = App.newDocument("tmp_" + name.split(".")[0].replace("-", "_"))
    Import.insert(str(HERE / name), d.Name)
    out = {}
    for o in d.Objects:
        if o.TypeId != "Part::Feature" or "v02b" in o.Label:
            continue
        if hasattr(o, "Shape") and not o.Shape.isNull() and o.Shape.Solids:
            out[o.Label] = o.Shape.copy()
    return out


board = load_step("placa-principal.step")
plugs = load_step("clavijas.step")
pusb = load_step("panel-usb.step")
# La placa y sus clavijas van DY mm más hacia el panel que en los STEP; J502 es de la panel-usb.
for _k, _s in list(board.items()) + [kv for kv in plugs.items() if not kv[0].startswith("J502")]:
    _s.translate(V(0, DY, 0))
log("placa:", len(board), "objetos; clavijas:", len(plugs), "; panel-usb:", len(pusb), "; placa movida", DY)
bb = board["PCB_principal"].BoundBox
log("PCB en x %.2f..%.2f y %.2f..%.2f z %.2f..%.2f" % (bb.XMin, bb.XMax, bb.YMin, bb.YMax, bb.ZMin, bb.ZMax))

# Tubo recortado a r 27: lo que puede tocar algo que pasa por el collar (nervios, topes, collares,
# cuna). El logo y la piel exterior quedan fuera y las booleanas van mucho más rápido.
tube_in = tube.common(Part.makeCylinder(27.0, 150.0, V(0, 0, -10)))
# Anillo de r >= 23.4 (nervios guía, topes, collares) y lo de dentro (cuna de la 18650), para filtrar
# por radio: lo que no pasa de r 23.4 no puede tocar el anillo.
tube_ring = tube_in.cut(Part.makeCylinder(23.4, 150.0, V(0, 0, -10)))
tube_core = tube_in.common(Part.makeCylinder(23.4, 150.0, V(0, 0, -10)))
# Para la tapa del panel hace falta la ventana del tubo entera, del lado +Y.
tube_front = tube.common(Part.makeBox(80, 40, 140, V(-40, 8, -5)))
log("tubo recortado")


def vol(a, b):
    try:
        c = a.common(b)
        return c.Volume if c.Solids else 0.0
    except Exception:
        return -1.0


def moved(shape, off):
    s = shape.copy()
    s.translate(off)
    return s


def rmax_of(shape):
    return max(math.hypot(v.X, v.Y) for v in shape.Vertexes)


def sweep(tag, moving, obstacles, direction, ts, rmin=None):
    """Mueve 'moving' a final + t·direction para cada t y busca choques con 'obstacles'.
    rmin: {obstáculo: radio} para saltar las piezas que no pasan de ese radio (solo si el recorrido
    es paralelo al eje z)."""
    hits = {}
    rmin = rmin or {}
    mbb = {k: v.BoundBox for k, v in moving.items()}
    mr = {k: rmax_of(v) for k, v in moving.items()} if rmin else {}
    obb = {k: v.BoundBox for k, v in obstacles.items()}
    for t in ts:
        off = V(direction[0] * t, direction[1] * t, direction[2] * t)
        for mk, ms in moving.items():
            b = App.BoundBox(mbb[mk])
            b.move(off)
            for ok, os_ in obstacles.items():
                if ok in rmin and mr[mk] < rmin[ok]:
                    continue
                if not b.intersect(obb[ok]):
                    continue
                v = vol(moved(ms, off), os_)
                if v > LIM or v < 0:
                    h = hits.setdefault(mk + " × " + ok, {"mm3_max": 0.0, "t_min": t, "t_max": t})
                    h["mm3_max"] = round(max(h["mm3_max"], v), 3)
                    h["t_min"] = min(h["t_min"], t)
                    h["t_max"] = max(h["t_max"], t)
    log(tag, "choques:", len(hits))
    for k, h in sorted(hits.items(), key=lambda kv: -kv[1]["mm3_max"])[:12]:
        log("   ", k, h)
    return hits


def steps(a, b, d):
    n = int(round((b - a) / d))
    return [round(a + i * d, 3) for i in range(n + 1)]


R = {"nota": "Recorridos de montaje de V2.3 con la placa v0.2 de cad/ (movida desplazamiento_placa_y). t = "
             "distancia a la posición final a lo largo del recorrido; los choques dan el volumen máximo y "
             "el tramo de t."}

# ---------------------------------------------------------------- 1. 18650
# Recorrido: (a) baja corrida hacia delante lo justo para pasar el collar (0.3 mm de holgura) hasta
# quedar entera bajo él; (b) ahí se empuja hacia atrás hasta su eje; (c) baja recta a la repisa.
r_bat = 9.3
c_y = -19.6
r_collar = 26.0
dy_min = (abs(c_y) + r_bat) - (r_collar - 0.3)
t_s = 111.91 - 91.0 - 0.4          # tope de la celda 0.4 mm bajo el collar al empujarla
tube_back = tube.common(Part.makeBox(80, 40, 150, V(-40, -35, -10)))   # y < 5: lo que puede tocar la celda
bat_fwd = moved(battery, V(0, dy_min, 0))
bat_obst = {"tubo": tube_back, "retenes_tuerca": keepers}
R["1_bateria"] = {
    "corrimiento_para_el_collar_mm": round(dy_min, 2),
    "eje_y_al_pasar": round(c_y + dy_min, 2),
    "altura_del_empuje_t": round(t_s, 2),
    "a_baja_corrida": sweep("1a 18650 baja corrida", {"18650": bat_fwd}, bat_obst, (0, 0, 1),
                            steps(t_s, 110.0, 1.0)),
    "b_hacia_atras": sweep("1b 18650 hacia atrás", {"18650": moved(battery, V(0, 0, t_s))}, bat_obst, (0, 1, 0),
                           steps(0.0, dy_min, 0.2)),
    "c_baja_a_la_repisa": sweep("1c 18650 baja a la repisa", {"18650": battery}, bat_obst, (0, 0, 1),
                                steps(0.0, t_s, 0.5)),
}

# ---------------------------------------------------------------- 2. carrier al chasis
R["2_carrier_al_chasis"] = sweep("2 carrier -> chasis (-Y)", {"carrier": carrier}, {"chasis": sled},
                                 (0, 1, 0), steps(0.0, 30.0, 0.5))
R["2b_carrier_con_componentes"] = {
    "choques": sweep("2b carrier con componentes -> chasis (-Y)", carrier_parts, {"chasis": sled},
                     (0, 1, 0), steps(0.0, 16.0, 0.25)),
    "holguras_finales": {k: {"chasis": round(v.distToShape(sled)[0], 2),
                             "18650": round(v.distToShape(battery)[0], 2)} for k, v in carrier_parts.items()},
}
log("2b holguras finales", R["2b_carrier_con_componentes"]["holguras_finales"])

# ---------------------------------------------------------------- 3. placa al chasis
sled_front = sled.common(Part.makeBox(80, 20, 120, V(-40, 3.1 + DY, 0)))   # delante de la cara de la placa
board_obst = {"chasis_frente_%d" % i: s for i, s in enumerate(sled_front.Solids)}
board_obst["carrier"] = carrier
board_obst.update({"carrier: " + k: v for k, v in carrier_parts.items()})
log("chasis por delante de la placa:", ["x %.1f..%.1f z %.1f..%.1f" % (s.BoundBox.XMin, s.BoundBox.XMax,
                                         s.BoundBox.ZMin, s.BoundBox.ZMax) for s in sled_front.Solids])
comp = {k: v for k, v in board.items() if k != "PCB_principal"}
pcb = {"PCB_principal": board["PCB_principal"]}
R["3a_placa_desde_arriba"] = {
    "pcb": sweep("3a PCB por los rieles desde arriba", pcb, {"chasis": sled, "carrier": carrier}, (0, 0, 1),
                 steps(0.0, 82.0, 1.0)),
    "componentes": sweep("3a componentes desde arriba", comp, board_obst, (0, 0, 1), steps(0.0, 82.0, 1.0)),
}
R["3b_placa_desde_abajo"] = {
    "pcb": sweep("3b PCB por los rieles desde abajo", pcb, {"chasis": sled, "carrier": carrier}, (0, 0, -1),
                 steps(0.0, 82.0, 1.0)),
    "componentes": sweep("3b componentes desde abajo", comp, board_obst, (0, 0, -1), steps(0.0, 82.0, 1.0)),
}

# ---------------------------------------------------------------- 4. chasis armado al tubo
j301 = {k: v for k, v in plugs.items() if k.startswith("J301")}
assembly = {"chasis": sled, "carrier": carrier, "PCB_principal": board["PCB_principal"]}
assembly.update(comp)
assembly.update(j301)
rmax = 0.0
for k, s in assembly.items():
    for vx in s.Vertexes:
        rmax = max(rmax, math.hypot(vx.X, vx.Y))
R["4_chasis_al_tubo"] = {
    "radio_max_conjunto": round(rmax, 3),
    "choques": sweep("4 chasis armado -> tubo (-Z)", assembly,
                     {"tubo_anillo": tube_ring, "tubo_cuna": tube_core, "18650": battery,
                      "retenes_tuerca": keepers}, (0, 0, 1), steps(0.0, 112.0, 1.0),
                     rmin={"tubo_anillo": 23.35}),
}
gaps = {}
for k in ("chasis", "carrier"):
    try:
        gaps[k + "-tubo"] = round(assembly[k].distToShape(tube_in)[0], 3)
        gaps[k + "-18650"] = round(assembly[k].distToShape(battery)[0], 3)
    except Exception:
        pass
R["4_chasis_al_tubo"]["holguras_finales"] = gaps
log("4 holguras finales", gaps)

# ---------------------------------------------------------------- 5. clavijas de abajo
fixed_after = {"tubo_anillo": tube_ring, "tubo_cuna": tube_core, "chasis": sled, "carrier": carrier, "18650": battery, "retenes_tuerca": keepers,
               "PCB_principal": board["PCB_principal"]}
fixed_after.update({"comp_" + k: v for k, v in comp.items() if v.BoundBox.ZMin < 40})
for ref in ("J102", "J404"):
    mv = {k: v for k, v in plugs.items() if k.startswith(ref)}
    R["5_" + ref + "_desde_abajo"] = sweep("5 %s desde abajo (+Z)" % ref, mv, fixed_after, (0, 0, -1),
                                           steps(0.0, 26.0, 0.5), rmin={"tubo_anillo": 23.35})

# ---------------------------------------------------------------- 6. tapa del panel
cover_set = {"tapa_panel": cover}
cover_set.update(panel_refs)
cover_set.update({"pusb_" + k: v for k, v in pusb.items()})
cover_set.update({k: v for k, v in plugs.items() if k.startswith("J502")})
fixed_panel = {"tubo_frente": tube_front, "chasis": sled, "PCB_principal": board["PCB_principal"]}
fixed_panel.update({"comp_" + k: v for k, v in comp.items()})
fixed_panel.update({k: v for k, v in plugs.items() if not k.startswith("J502") and not k.startswith("J102")
                    and not k.startswith("J404") and not k.startswith("J301")})
R["6_tapa_del_panel"] = sweep("6 tapa del panel (-Y)", cover_set, fixed_panel, (0, 1, 0), steps(0.0, 25.0, 0.5))

# ---------------------------------------------------------------- 7. plataforma y tapa de antena
top_fixed = {"chasis": sled, "carrier": carrier, "18650": battery, "tapa_panel": cover}
top_fixed.update({k: v for k, v in plugs.items() if k[:4] in ("J101", "J405", "J502")})
top_fixed.update({"pusb_" + k: v for k, v in pusb.items()})
plat_set = {"plataforma": plat}
plat_set.update(imu)
R["7a_plataforma"] = sweep("7a plataforma del IMU (-Z)", {"plataforma": plat, "imu_pcb": imu["imu_pcb"],
                                                          "imu_chip": imu["imu_chip"]},
                           top_fixed, (0, 0, 1), steps(0.0, 30.0, 0.5))
top_fixed.update({"plataforma": plat, "imu_pcb": imu["imu_pcb"]})
R["7b_tapa_antena"] = sweep("7b tapa de antena (-Z)", {"tapa_antena": cap, "sma_antena": imu["sma_antena"]},
                            top_fixed, (0, 0, 1), steps(0.0, 30.0, 0.5))

# ---------------------------------------------------------------- 8. cable de la 18650 a J102
# Recorrido (Ø2.6, dos hilos AWG24-26 juntos), sacado de los cortes. Sale de debajo de la celda por el
# hueco de la repisa, pasa por encima de la arandela del retén de la tuerca (r 4.5 hasta z 16.7) por la
# esquina delantera izquierda del hueco, entra en el canal bajo la repisa (techo en z 19.0), sale hacia
# delante, va por el piso hacia -X entre la cuna y la carrier, sube por dentro del collar inferior en
# x -20.5, rodea por detrás la ranura -X de la carrier, pasa por fuera del riel -X por encima del collar
# (z > 21; aquí aún no hay nervios), entra por delante del riel y baja junto a J102 hasta la salida de
# su clavija. En la esquina del hueco el cable tiene que ir por encima de la arandela (centro en z >= 18.0)
# y por debajo de la repisa (z <= 17.7): con el techo del canal en z 19.0 no pasa; con un rebaje hasta
# z 20.0 en x -7...-3, y -18.6...-15.6 sí (comprobado aparte quitando ese volumen). Desde que la placa va
# 1 mm más adelante (desplazamiento_placa_y), el tramo que rodea el riel -X y baja a J102 va 1 mm más adelante.
CABLE_R = 1.3
ROUTE = [(0.0, -19.6, 21.0), (-2.6, -18.9, 19.9), (-3.8, -17.5, 18.3), (-6.0, -16.9, 17.6), (-7.8, -13.0, 17.5),
         (-20.5, -12.8, 17.5), (-20.5, -12.8, 22.8), (-24.5, -12.6, 23.5), (-25.6, -9.0, 24.0), (-27.2, -3.5, 24.3), (-27.2, 5.0, 24.5),
         (-23.1, 6.9, 24.6), (-23.1, 6.9, 18.0), (-20.0, 6.9, 17.3)]
pieces = []
for (a1, a2) in zip(ROUTE, ROUTE[1:]):
    p1, p2 = V(*a1), V(*a2)
    d = p2.sub(p1)
    if d.Length > 1e-6:
        pieces.append(Part.makeCylinder(CABLE_R, d.Length, p1, d))
for q in ROUTE[1:-1]:
    pieces.append(Part.makeSphere(CABLE_R, V(*q)))
cable = pieces[0].multiFuse(pieces[1:])
length = sum(V(*b_).sub(V(*a_)).Length for a_, b_ in zip(ROUTE, ROUTE[1:]))
cable_obst = {"tubo": tube, "base": base, "chasis": sled, "carrier": carrier, "18650": battery,
              "retenes_tuerca": keepers, "PCB_principal": board["PCB_principal"]}
cable_obst.update({"comp_" + k: v for k, v in comp.items() if v.BoundBox.ZMin < 40})
cable_obst.update({k: v for k, v in plugs.items() if k[:4] in ("J404", "J301")})
res = {"diametro_mm": 2 * CABLE_R, "puntos": ROUTE, "largo_mm": round(length, 1), "choques": {}, "holguras": {}}
# El primer punto está bajo la celda: su contacto con ella (holgura 0) es el extremo del cable.
for k, o in cable_obst.items():
    if not cable.BoundBox.intersect(o.BoundBox):
        continue
    v = vol(cable, o)
    if v > LIM or v < 0:
        res["choques"][k] = round(v, 3)
    try:
        dist = cable.distToShape(o)[0]
        if dist < 1.0:
            res["holguras"][k] = round(dist, 3)
    except Exception:
        pass
R["8_cable_18650_J102"] = res
log("8 cable 18650 -> J102: largo", res["largo_mm"], "choques", res["choques"], "holguras < 1 mm", res["holguras"])

# ---------------------------------------------------------------- cortes del fondo
def section_paths(shape, normal, d, to2d):
    """Corte plano de 'shape' como trayectorias de matplotlib: contorno antihorario y huecos horarios."""
    from matplotlib.path import Path as MPath
    verts, codes = [], []
    for w in shape.slice(normal, d):
        pts = [to2d(p) for p in w.discretize(Deflection=0.05)]
        if len(pts) < 3:
            continue
        verts += pts + [pts[0]]
        codes += [MPath.MOVETO] + [MPath.LINETO] * (len(pts) - 1) + [MPath.CLOSEPOLY]
    return MPath(verts, codes) if verts else None


try:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.patches import Circle, PathPatch

    layers = [("tubo", tube_in, "#909090"), ("chasis", sled, "#3070c0"), ("carrier", carrier, "#c08030"),
              ("18650", battery, "#30a050"), ("retenes", keepers, "#806040"),
              ("PCB", board["PCB_principal"], "#207020")]
    layers += [("clavijas", s, "#c03030") for k, s in plugs.items() if k[:4] in ("J102", "J404", "J301")]
    layers += [("comp", s, "#60a060") for k, s in comp.items() if s.BoundBox.ZMin < 40]
    layers += [("cable", cable, "#e000e0")]

    def draw(fname, title, normal, d, to2d, xlim, ylim, extra=None):
        fig, ax = plt.subplots(figsize=(7, 7))
        if extra:
            extra(ax)
        for name, s, col in layers:
            try:
                path = section_paths(s, normal, d, to2d)
            except Exception:
                path = None
            if path is not None:
                ax.add_patch(PathPatch(path, facecolor=col, alpha=0.55, lw=0.3, edgecolor=col))
        ax.set_xlim(*xlim)
        ax.set_ylim(*ylim)
        ax.set_aspect("equal")
        ax.grid(True, lw=0.3)
        ax.set_title(title, fontsize=9)
        fig.savefig(OUT / fname, dpi=110)
        plt.close(fig)

    def rings(ax):
        ax.add_patch(Circle((0, 0), 26.0, fill=False, ls="--", color="k", lw=0.6))
        ax.add_patch(Circle((0, 0), 29.5, fill=False, color="k", lw=0.6))

    for z in (16.5, 18.5, 20.0, 21.0, 23.0, 25.0, 28.0):
        draw("corte_z%04.1f.png" % z, "Corte horizontal en z = %.1f (vista desde arriba; +Y = panel)" % z,
             V(0, 0, 1), z, lambda p: (p.x, p.y), (-31, 31), (-31, 31), rings)
    for x in (0.0, -17.6, -22.2, -27.0):
        draw("corte_x%+05.1f.png" % x, "Corte vertical en x = %.1f (horizontal: y, +Y = panel; vertical: z)" % x,
             V(1, 0, 0), x, lambda p: (p.y, p.z), (-31, 31), (8, 40))
    log("cortes dibujados")
except Exception as e:
    log("sin cortes:", e)

(OUT / "resultado.json").write_text(json.dumps(R, indent=1, ensure_ascii=False), encoding="utf-8")
log("fin")
