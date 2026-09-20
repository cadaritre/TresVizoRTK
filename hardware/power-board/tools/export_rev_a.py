"""Verifica y exporta la placa ruteada; no regenera ni modifica su placement."""
from pathlib import Path
import argparse, concurrent.futures, json, os, shutil, subprocess

B = Path(__file__).resolve().parents[1]
R = B / 'rev-a'
M = B / 'manufacturing/rev-a'
parser = argparse.ArgumentParser()
parser.add_argument('--cli', default=os.environ.get('KICAD_CLI') or shutil.which('kicad-cli') or '/Volumes/KiCad/KiCad/KiCad.app/Contents/MacOS/kicad-cli')
parser.add_argument('--render', action='store_true')
args = parser.parse_args()
pcb, sch = R/'power-board.kicad_pcb', R/'power-board.kicad_sch'
for p in [M/'gerbers', M/'assembly', R/'review/schematic', R/'review/logs', R/'output/pdf']:
    p.mkdir(parents=True, exist_ok=True)

def run(name, command):
    result = subprocess.run([args.cli, *map(str, command)], capture_output=True, text=True)
    (R/'review/logs'/f'{name}.txt').write_text(result.stdout + result.stderr)
    if result.returncode:
        raise RuntimeError(f'{name}: exit {result.returncode}; consultar review/logs/{name}.txt')
    print(name + ': OK', flush=True)

# La exportación depende de ambas comprobaciones. No se continúa con incidencias.
run('erc', ['sch','erc',sch,'-o',R/'review/erc.json','--format','json','--exit-code-violations'])
run('drc', ['pcb','drc',pcb,'-o',R/'review/drc.json','--format','json','--schematic-parity','--exit-code-violations'])
jobs = [
 ('netlist',['sch','export','netlist',sch,'-o',R/'review/netlist.xml','--format','kicadxml']),
 ('schematic-svg',['sch','export','svg',sch,'-o',R/'review/schematic']),
 ('schematic-pdf',['sch','export','pdf',sch,'-o',R/'output/pdf/power-board.pdf','--no-background-color']),
 ('gerbers',['pcb','export','gerbers',pcb,'-o',M/'gerbers','-l','F.Cu,In1.Cu,In2.Cu,B.Cu,F.Mask,B.Mask,F.SilkS,B.SilkS,F.Paste,B.Paste,Edge.Cuts','--subtract-soldermask']),
 ('drill',['pcb','export','drill',pcb,'-o',M/'gerbers','--format','excellon','--excellon-separate-th','--generate-map','--map-format','svg','--generate-report','--report-path',M/'drill-report.txt']),
 ('positions',['pcb','export','pos',pcb,'-o',M/'assembly/positions-kicad.csv','--side','both','--format','csv','--units','mm','--exclude-dnp']),
 ('step-reference',['pcb','export','step',pcb,'-o',M/'power-board-kicad.step','--user-origin','22.5x20mm','--force']),
 ('step-board',['pcb','export','step',pcb,'-o',M/'board-only-kicad.step','--user-origin','22.5x20mm','--board-only','--force']),
]
for name,layers in [('top','F.Cu,F.SilkS,Edge.Cuts'),('bottom','B.Cu,B.SilkS,Edge.Cuts'),('ground-plane','In1.Cu,Edge.Cuts'),('inner-signals','In2.Cu,Edge.Cuts')]:
    jobs.append((name,['pcb','export','svg',pcb,'-o',R/f'review/{name}.svg','--layers',layers,'--mode-single','--fit-page-to-board','--exclude-drawing-sheet']))
if args.render:
    jobs += [
      ('render-3d',['pcb','render',pcb,'-o',R/'review/power-board-3d.png','--rotate','325,0,25','--zoom','0.76','--width','1600','--height','1200','--quality','high','--background','opaque']),
      ('render-bottom',['pcb','render',pcb,'-o',R/'review/power-board-bottom.png','--side','bottom','--zoom','0.78','--width','1600','--height','1200','--quality','high','--background','opaque'])]
with concurrent.futures.ThreadPoolExecutor(max_workers=3) as pool:
    futures=[pool.submit(run,*job) for job in jobs]
    for f in futures: f.result()
print('Exportación completa. STEP local e interfaz mecánica: ejecutar mechanical_rev_a.py con FreeCAD Python.')
