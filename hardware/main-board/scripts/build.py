"""Regenera el proyecto completo: esquemático, PCB, ruteo, comprobaciones y archivos para JLCPCB.

    python3 build.py [--no-route | --fab-only]

--fab-only no regenera ni rutea el PCB: parte de kicad/tresvizo-main.kicad_pcb tal como esté
(por ejemplo, después de retocarlo a mano en KiCad) y rehace DRC y archivos de fabricación.

v0.3: el USB-C, la OLED, el botón y el LED van en la placa principal; ya no hay placa panel-usb. El panel
del pedido (panelize.py con kicad/panel.json) lleva solo la placa principal, con rieles, marcas de JLCPCB y
puentes con mouse bites, y saca su propio juego de archivos: fab/tresvizo-panel-*.

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
PANEL = "tresvizo-panel"

KICAD_APP = os.environ.get("KICAD_APP", "/Applications/KiCad/KiCad.app")
# Redes que route_rest.py rutea antes que el resto (prefijos): las que pasan por los pasos más estrechos
ROUTE_FIRST = "SD_,USB_"
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
        what = os.path.basename(str(cmd[1] if len(cmd) > 1 and str(cmd[1]).endswith(".py") else cmd[0]))
        if r.returncode < 0:
            raise SystemExit("falló: %s, se cayó con la señal %d" % (what, -r.returncode))
        raise SystemExit("falló: %s (código %d)" % (what, r.returncode))
    return out


def fab_outputs(name, pcb, nets, env, renders=False, step=True):
    """Gerbers y taladros en zip, posiciones, BOM y CPL de JLCPCB, vistas y STEP de un PCB."""
    gdir = os.path.join(FAB, "gerbers-" + name)
    shutil.rmtree(gdir, ignore_errors=True)
    os.makedirs(gdir)
    layers = "F.Cu,In1.Cu,In2.Cu,B.Cu,F.Paste,B.Paste,F.Silkscreen,B.Silkscreen,F.Mask,B.Mask,Edge.Cuts"
    run([KCLI, "pcb", "export", "gerbers", "--layers", layers, "--subtract-soldermask",
         "--no-protel-ext", "-o", gdir + "/", pcb], env=env)
    run([KCLI, "pcb", "export", "drill", "--format", "excellon", "--excellon-separate-th",
         "--generate-map", "--map-format", "gerberx2", "-o", gdir + "/", pcb], env=env)
    zpath = os.path.join(FAB, name + "-gerbers-jlcpcb.zip")
    with zipfile.ZipFile(zpath, "w", zipfile.ZIP_DEFLATED) as z:
        for fn in sorted(os.listdir(gdir)):
            z.write(os.path.join(gdir, fn), fn)
    pos = os.path.join(FAB, name + "-pos.csv")
    run([KCLI, "pcb", "export", "pos", "--format", "csv", "--units", "mm", "--side", "both",
         "--exclude-dnp", "-o", pos, pcb], env=env)
    cmd = [sys.executable, os.path.join(HERE, "export_jlc.py"), nets[0], pos,
           os.path.join(FAB, name + "-bom-jlcpcb.csv"), os.path.join(FAB, name + "-cpl-jlcpcb.csv"),
           os.path.join(KDIR, "jlc_rotations.json")]
    for extra in nets[1:]:
        cmd += ["--net", extra]
    run(cmd, env=env)
    if renders:
        for side in ("top", "bottom"):
            run([KCLI, "pcb", "render", "--side", side, "--quality", "high", "--width", "1600", "--height",
                 "1200", "--background", "opaque", "-o", os.path.join(FAB, "%s-%s.png" % (name, side)), pcb],
                env=env)
    if step:
        run([KCLI, "pcb", "export", "step", "--subst-models", "-f", "-o", os.path.join(FAB, name + ".step"),
             pcb], env=env)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--no-route", action="store_true", help="solo prerruteos y fanout")
    ap.add_argument("--fab-only", action="store_true", help="no tocar el PCB; solo DRC y fabricación")
    a = ap.parse_args()
    os.makedirs(FAB, exist_ok=True)
    tmp = tempfile.mkdtemp(prefix="tresvizo-")
    env = dict(os.environ)
    env["PYTHONUNBUFFERED"] = "1"   # si un paso se cae, sus últimas líneas igual salen
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
        # Primero lo que queda de la microSD y el USB (el bus de datos de la microSD va prerruteado en
        # layout.py): pasan bajo el WROOM y el zócalo, donde no queda más que su paso
        run([KPY, os.path.join(HERE, "route_rest.py"), pcb, rep],
            env=dict(env, SKIP_NETS=skip, ROUTE_FIRST=ROUTE_FIRST))
    if not (a.no_route or a.fab_only):
        route("1", skip="GND")
    if not a.fab_only:
        run([KPY, os.path.join(HERE, "finish_pcb.py"), pcb, spec], env=env)
    if not (a.no_route or a.fab_only):
        route("2")
        # Las pistas nuevas pueden partir los rellenos: otra vez cosido e islas; y fuera las vías que quedaron sin uso
        run([KPY, os.path.join(HERE, "finish_pcb.py"), pcb, spec, "--final"], env=env)
    if not a.fab_only:
        # Serigrafía sin solapes (referencias y trazos de huellas que pisan pads u otra serigrafía)
        run([KPY, os.path.join(HERE, "silk_clean.py"), pcb, KCLI], env=env)

    # 4. DRC final con paridad de esquemático
    run([KCLI, "pcb", "drc", "--refill-zones", "--schematic-parity", "--severity-all", "--format", "report",
         "-o", os.path.join(FAB, "drc.rpt"), pcb], env=env)

    # 5. Fabricación de la placa sola (referencia y comparación de costo)
    fab_outputs(PROJECT, pcb, [net], env, renders=True)

    # 6. Panel del pedido: la placa principal con rieles, marcas de JLCPCB y puentes con mouse bites
    ppcb = os.path.join(KDIR, PANEL + ".kicad_pcb")
    shutil.copy(os.path.join(KDIR, PROJECT + ".kicad_pro"), os.path.join(KDIR, PANEL + ".kicad_pro"))
    run([KPY, os.path.join(HERE, "panelize.py"), os.path.join(KDIR, "panel.json"), ppcb], env=env)
    run([KCLI, "pcb", "drc", "--refill-zones", "--severity-all", "--format", "report",
         "-o", os.path.join(FAB, "drc-panel.rpt"), ppcb], env=env)
    fab_outputs(PANEL, ppcb, [net], env, renders=True, step=False)
    shutil.rmtree(tmp, ignore_errors=True)
    print("listo:", FAB)


if __name__ == "__main__":
    main()
