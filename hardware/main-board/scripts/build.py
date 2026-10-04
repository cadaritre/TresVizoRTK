"""Regenera el proyecto completo: esquemático, PCB, ruteo, comprobaciones y archivos para JLCPCB.

    python3 build.py [--no-route | --fab-only]

--fab-only no regenera ni rutea el PCB: parte de kicad/tresvizo-main.kicad_pcb tal como esté
(por ejemplo, después de retocarlo a mano en KiCad) y rehace DRC y archivos de fabricación.

Variables de entorno:
    KICAD_APP          ruta a KiCad.app (por omisión /Applications/KiCad/KiCad.app)

El costo (cost_jlc.py) consulta la API pública de JLCPCB y se ejecuta aparte.
"""

import argparse
import os
import shutil
import subprocess
import sys
import tempfile
import zipfile

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
KDIR = os.path.join(ROOT, "kicad")
FAB = os.path.join(ROOT, "fab")
PROJECT = "tresvizo-main"

KICAD_APP = os.environ.get("KICAD_APP", "/Applications/KiCad/KiCad.app")
KCLI = os.path.join(KICAD_APP, "Contents/MacOS/kicad-cli")
KPY = os.path.join(KICAD_APP, "Contents/Frameworks/Python.framework/Versions/Current/bin/python3")
SHARED = os.path.join(KICAD_APP, "Contents/SharedSupport")


def run(cmd, **kw):
    print("$", " ".join(str(c) for c in cmd))
    r = subprocess.run(cmd, text=True, capture_output=True, **kw)
    out = (r.stdout or "") + (r.stderr or "")
    tail = "\n".join(line for line in out.strip().splitlines()[-30:] if "wxApp" not in line)
    if tail:
        print(tail)
    if r.returncode not in (0, 5):  # 5 = kicad-cli con violaciones
        raise SystemExit("falló: %s (código %d)" % (cmd[0], r.returncode))
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--no-route", action="store_true", help="solo prerruteos y fanout")
    ap.add_argument("--fab-only", action="store_true", help="no tocar el PCB; solo DRC y fabricación")
    a = ap.parse_args()
    os.makedirs(FAB, exist_ok=True)
    tmp = tempfile.mkdtemp(prefix="tresvizo-")
    env = dict(os.environ)
    env.setdefault("KICAD10_3DMODEL_DIR", os.path.join(SHARED, "3dmodels"))
    env.setdefault("KICAD10_FOOTPRINT_DIR", os.path.join(SHARED, "footprints"))
    env.setdefault("KICAD10_SYMBOL_DIR", os.path.join(SHARED, "symbols"))

    # 1. Esquemático, proyecto y board.json
    if not a.fab_only:
        run([sys.executable, os.path.join(HERE, "circuit.py"), os.path.join(SHARED, "symbols"), KDIR], env=env)
    sch = os.path.join(KDIR, PROJECT + ".kicad_sch")
    run([KCLI, "sch", "erc", "--format", "report", "--severity-all", "-o",
         os.path.join(FAB, "erc.rpt"), sch], env=env)
    net = os.path.join(KDIR, PROJECT + ".net")
    run([KCLI, "sch", "export", "netlist", "-o", net, sch], env=env)
    run([KCLI, "sch", "export", "pdf", "-o", os.path.join(FAB, PROJECT + "-schematic.pdf"), sch], env=env)
    run([sys.executable, os.path.join(HERE, "doc_tables.py"), net, os.path.join(FAB, "pinout.md")], env=env)

    # 2. PCB con colocación, prerruteos y fanout
    pcb_unrouted = os.path.join(tmp, PROJECT + "-unrouted.kicad_pcb")
    pcb = os.path.join(KDIR, PROJECT + ".kicad_pcb")
    spec = os.path.join(KDIR, "board.json")
    if not a.fab_only:
        run([KPY, os.path.join(HERE, "build_pcb.py"), KDIR, net, spec, pcb_unrouted,
             os.path.join(SHARED, "footprints")], env=env)
        run([KPY, os.path.join(HERE, "fanout.py"), pcb_unrouted, spec], env=env)
        shutil.copy(pcb_unrouted, pcb)

    # 3. Ruteo: señales y potencia (GND va por fanout y rellenos), rellenos de GND con cosido y lo que quede
    def route(tag, skip=""):
        rep = os.path.join(tmp, "drc-%s.json" % tag)
        run([KCLI, "pcb", "drc", "--refill-zones", "--format", "json", "--severity-error", "-o", rep, pcb],
            env=env)
        run([KPY, os.path.join(HERE, "route_rest.py"), pcb, rep], env=dict(env, SKIP_NETS=skip))
    if not (a.no_route or a.fab_only):
        route("1", skip="GND")
    if not a.fab_only:
        run([KPY, os.path.join(HERE, "finish_pcb.py"), pcb, spec], env=env)
    if not (a.no_route or a.fab_only):
        route("2")
        # Las pistas nuevas pueden partir los rellenos: otra vez cosido e islas
        run([KPY, os.path.join(HERE, "finish_pcb.py"), pcb, spec], env=env)

    # 4. DRC final con paridad de esquemático
    run([KCLI, "pcb", "drc", "--refill-zones", "--schematic-parity", "--severity-all", "--format", "report",
         "-o", os.path.join(FAB, "drc.rpt"), pcb], env=env)

    # 5. Fabricación
    gdir = os.path.join(FAB, "gerbers")
    shutil.rmtree(gdir, ignore_errors=True)
    os.makedirs(gdir)
    layers = "F.Cu,In1.Cu,In2.Cu,B.Cu,F.Paste,B.Paste,F.Silkscreen,B.Silkscreen,F.Mask,B.Mask,Edge.Cuts"
    run([KCLI, "pcb", "export", "gerbers", "--layers", layers, "--subtract-soldermask",
         "--no-protel-ext", "-o", gdir + "/", pcb], env=env)
    run([KCLI, "pcb", "export", "drill", "--format", "excellon", "--excellon-separate-th",
         "--generate-map", "--map-format", "gerberx2", "-o", gdir + "/", pcb], env=env)
    zpath = os.path.join(FAB, PROJECT + "-gerbers-jlcpcb.zip")
    with zipfile.ZipFile(zpath, "w", zipfile.ZIP_DEFLATED) as z:
        for fn in sorted(os.listdir(gdir)):
            z.write(os.path.join(gdir, fn), fn)
    pos = os.path.join(FAB, PROJECT + "-pos.csv")
    run([KCLI, "pcb", "export", "pos", "--format", "csv", "--units", "mm", "--side", "both",
         "--exclude-dnp", "-o", pos, pcb], env=env)
    run([sys.executable, os.path.join(HERE, "export_jlc.py"), net, pos,
         os.path.join(FAB, PROJECT + "-bom-jlcpcb.csv"), os.path.join(FAB, PROJECT + "-cpl-jlcpcb.csv"),
         os.path.join(KDIR, "jlc_rotations.json")], env=env)
    for side in ("top", "bottom"):
        run([KCLI, "pcb", "render", "--side", side, "--quality", "high", "--width", "1600", "--height", "1200",
             "--background", "opaque", "-o", os.path.join(FAB, "%s-%s.png" % (PROJECT, side)), pcb], env=env)
    run([KCLI, "pcb", "export", "step", "--subst-models", "-f", "-o",
         os.path.join(FAB, PROJECT + ".step"), pcb], env=env)
    shutil.rmtree(tmp, ignore_errors=True)
    print("listo:", FAB)


if __name__ == "__main__":
    main()
