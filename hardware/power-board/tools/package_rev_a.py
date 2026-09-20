"""Mapas de inspección, manifiesto y ZIP del diseño vigente; no altera el PCB."""
from pathlib import Path
import csv, hashlib, html, json, zipfile
B=Path(__file__).resolve().parents[1];ROOT=B.parent.parent;R=B/'rev-a';M=B/'manufacturing'
D=json.loads((R/'circuit.json').read_text());P=json.loads((R/'placement.json').read_text())
for side,label in [('F','top'),('B','bottom')]:
    items=['<svg xmlns="http://www.w3.org/2000/svg" width="1200" height="1200" viewBox="-4 -6 53 53">','<rect x="-4" y="-6" width="53" height="53" fill="#f6f8fa"/>',f'<text x="22.5" y="-3.6" font-family="sans-serif" font-size="1.4" text-anchor="middle">TresVizo Rev A · {"SUPERIOR" if side=="F" else "INFERIOR"}</text>','<rect width="45" height="40" fill="#e5eee8" stroke="#243a34" stroke-width=".15"/>']
    for x,y in P['holes']:
        if side=='B':x=45-x
        items.append(f'<circle cx="{x}" cy="{y}" r="1.1" fill="white" stroke="#243a34" stroke-width=".15"/>')
    for c in D['components']:
        ref=c['reference'];x,y,angle,s=P['placements'][ref]
        if side!=s:continue
        a,b,z,d=P['courtyards'][ref]
        if side=='B':a,z=45-z,45-a;x=45-x
        fill='#d7e5f3' if ref.startswith('U') else '#b9d8c7' if ref.startswith('J') else '#f1d8b2' if ref.startswith(('L','F')) else '#fff'
        if c['dnp']:fill='#ffdfdf'
        title=html.escape(f'{ref}: {c["value"]} | {c["mpn"]} | giro KiCad {angle}°'+(' | DNP' if c['dnp'] else ''))
        fs=min(.72,(z-a)/max(len(ref)*.62,1),.72*(d-b))
        items.append(f'<g><title>{title}</title><rect x="{a}" y="{b}" width="{z-a}" height="{d-b}" rx=".12" fill="{fill}" stroke="#5e746b" stroke-width=".07"/><text x="{(a+z)/2}" y="{(b+d)/2}" font-family="sans-serif" font-size="{fs}" dominant-baseline="middle" text-anchor="middle">{ref}</text></g>')
    items.append('<text x="22.5" y="43" text-anchor="middle" font-family="sans-serif" font-size=".95">45 × 40 mm · recuadros = courtyard · consultar KiCad para pin 1 y pads</text></svg>')
    (R/f'review/assembly-{label}.svg').write_text(''.join(items))

erc=json.loads((R/'review/erc.json').read_text());drc=json.loads((R/'review/drc.json').read_text())
assert not drc['violations'] and not drc['unconnected_items'] and not drc['schematic_parity']
assert all(not sheet['violations'] for sheet in erc.get('sheets',[]))
assert json.loads((R/'review/static-checks.json').read_text())['status']=='PASS_STATIC_CHECKS'
assert json.loads((R/'review/mechanical-checks.json').read_text())['status']=='VALID_LOCAL_STEP'
with (M/'rev-a/assembly/bom.csv').open() as f:rows=list(csv.DictReader(f))
purchase=[r for r in rows if r['LCSC']=='TBD' or 'sin existencias' in r['Stock_observation'].lower() or 'no disponible' in r['Stock_observation'].lower()]
with (M/'rev-a/assembly/purchasing-review.csv').open('w',newline='') as f:
    w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(purchase)
sources=[]
for base in [R,B/'tools',M/'rev-a',B/'datasheets']:
    for p in base.rglob('*'):
        if p.is_file() and '__pycache__' not in p.parts and p.suffix not in ['.pyc','.kicad_prl','.dsn','.ses'] and not p.name.startswith('~') and 'logs' not in p.parts:
            sources.append(p)
sources += [M/'power-board.step',M/'README.md']+list(B.glob('*.md'))+list((ROOT/'mechanical/integration').glob('power_board*'))+[ROOT/'mechanical/integration/POWER_BOARD_INTEGRATION.md']
sources=sorted(set(sources));manifest=M/'rev-a/SHA256SUMS.txt'
sources=[p for p in sources if p!=manifest]
manifest.write_text(''.join(hashlib.sha256(p.read_bytes()).hexdigest()+'  '+p.relative_to(ROOT).as_posix()+'\n' for p in sources))
sources.append(manifest)
with zipfile.ZipFile(M/'power-board-rev-a.zip','w',zipfile.ZIP_DEFLATED) as z:
    for p in sources:z.write(p,p.relative_to(ROOT))
with zipfile.ZipFile(M/'power-board-rev-a-gerbers.zip','w',zipfile.ZIP_DEFLATED) as z:
    for p in sorted((M/'rev-a/gerbers').glob('*')):z.write(p,p.name)
with zipfile.ZipFile(M/'power-board-rev-a.zip') as z:assert z.testzip() is None
print(f'Paquete: {len(sources)} archivos; ZIP íntegro. {len(purchase)} filas para revisión de compra/consignación.')
