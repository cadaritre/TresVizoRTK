"""Regenera la placa del USB-C del panel: esquemático, ERC, netlist, PCB ruteado, DRC y archivos de JLCPCB.

    python3 build.py [--fab-only]

--fab-only no regenera el PCB: parte de kicad/tresvizo-panel-usb.kicad_pcb tal como esté (por ejemplo,
retocado a mano en KiCad) y rehace el DRC y los archivos de fabricación.

Usa los scripts de la placa principal sin cambiarlos (../../main-board/scripts): build_pcb.py construye
el PCB desde la netlist y kicad/board.json, fanout.py baja los pads de GND a los planos, route_rest.py
rutea lo que no está prerruteado en layout.py (solo F.Cu y B.Cu: las capas internas son GND enteras),
finish_pcb.py pone los rellenos de GND con vías de cosido y export_jlc.py hace el BOM y el CPL.

La placa principal importa kicad/tresvizo-panel-usb.kicad_pcb y su .net para armar el panel del pedido.

Variables de entorno:
    KICAD_APP          ruta a KiCad.app (por omisión /Applications/KiCad/KiCad.app)
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
MAIN = os.path.join(os.path.dirname(ROOT), "main-board", "scripts")
PROJECT = "tresvizo-panel-usb"

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


def fab_outputs(pcb, net, env):
    """Gerbers y taladros en zip, posiciones, BOM y CPL de JLCPCB y vista superior de la placa sola."""
    gdir = os.path.join(FAB, "gerbers-" + PROJECT)
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
    run([sys.executable, os.path.join(MAIN, "export_jlc.py"), net, pos,
         os.path.join(FAB, PROJECT + "-bom-jlcpcb.csv"), os.path.join(FAB, PROJECT + "-cpl-jlcpcb.csv")], env=env)
    for side in ("top", "bottom"):
        run([KCLI, "pcb", "render", "--side", side, "--quality", "high", "--width", "1600", "--height", "1200",
             "--background", "opaque", "-o", os.path.join(FAB, "%s-%s.png" % (PROJECT, side)), pcb], env=env)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--fab-only", action="store_true", help="no tocar el PCB; solo DRC y fabricación")
    a = ap.parse_args()
    os.makedirs(FAB, exist_ok=True)
    tmp = tempfile.mkdtemp(prefix="tresvizo-pusb-")
    env = dict(os.environ)
    env.setdefault("KICAD10_3DMODEL_DIR", os.path.join(SHARED, "3dmodels"))
    env.setdefault("KICAD10_FOOTPRINT_DIR", os.path.join(SHARED, "footprints"))
    env.setdefault("KICAD10_SYMBOL_DIR", os.path.join(SHARED, "symbols"))
    env["PYTHONDONTWRITEBYTECODE"] = "1"   # sin cachés en ../../main-board/scripts

    # 1. Esquemático, proyecto y board.json; ERC, netlist y PDF
    if not a.fab_only:
        run([sys.executable, os.path.join(HERE, "circuit.py"), os.path.join(SHARED, "symbols"), KDIR], env=env)
    sch = os.path.join(KDIR, PROJECT + ".kicad_sch")
    run([KCLI, "sch", "erc", "--format", "report", "--severity-all", "-o", os.path.join(FAB, "erc.rpt"), sch],
        env=env)
    net = os.path.join(KDIR, PROJECT + ".net")
    run([KCLI, "sch", "export", "netlist", "-o", net, sch], env=env)
    run([KCLI, "sch", "export", "pdf", "-o", os.path.join(FAB, PROJECT + "-schematic.pdf"), sch], env=env)

    # 2. PCB con colocación, prerruteos y fanout de GND
    pcb = os.path.join(KDIR, PROJECT + ".kicad_pcb")
    spec = os.path.join(KDIR, "board.json")
    if not a.fab_only:
        pcb_unrouted = os.path.join(tmp, PROJECT + ".kicad_pcb")
        run([KPY, os.path.join(MAIN, "build_pcb.py"), KDIR, net, spec, pcb_unrouted,
             os.path.join(SHARED, "footprints")], env=env)
        run([KPY, os.path.join(MAIN, "fanout.py"), pcb_unrouted, spec], env=env)
        shutil.copy(pcb_unrouted, pcb)

        # 3. Lo que quede sin prerruteo (solo capas externas), rellenos de GND con cosido y remates
        def route(tag, skip=""):
            rep = os.path.join(tmp, "drc-%s.json" % tag)
            run([KCLI, "pcb", "drc", "--refill-zones", "--format", "json", "--severity-error", "-o", rep, pcb],
                env=env)
            run([KPY, os.path.join(MAIN, "route_rest.py"), pcb, rep, "F.Cu,B.Cu"], env=dict(env, SKIP_NETS=skip))
        route("1", skip="GND")
        run([KPY, os.path.join(MAIN, "finish_pcb.py"), pcb, spec], env=env)
        route("2")
        run([KPY, os.path.join(MAIN, "finish_pcb.py"), pcb, spec], env=env)

    # 4. DRC final con paridad de esquemático
    run([KCLI, "pcb", "drc", "--refill-zones", "--schematic-parity", "--severity-all", "--format", "report",
         "-o", os.path.join(FAB, "drc.rpt"), pcb], env=env)

    # 5. Fabricación de la placa sola y comprobación de la posición de los conectores en el modelo 3D
    fab_outputs(pcb, net, env)
    wrl = os.path.join(tmp, PROJECT + ".wrl")
    run([KCLI, "pcb", "export", "vrml", "--units", "mm", "-o", wrl, pcb], env=env)
    out = run([sys.executable, os.path.join(HERE, "check3d.py"), wrl, pcb], env=env)
    with open(os.path.join(FAB, "check3d.txt"), "w", encoding="utf-8") as f:
        f.write(out)
    shutil.rmtree(tmp, ignore_errors=True)
    print("listo:", FAB)


if __name__ == "__main__":
    main()
