"""BOM agrupada por MPN y CPL derivado de posiciones KiCad, sin inventar códigos de compra."""
from pathlib import Path
import collections, csv, json, re
B=Path(__file__).resolve().parents[1];R=B/'rev-a';M=B/'manufacturing/rev-a/assembly';M.mkdir(parents=True,exist_ok=True)
parts=json.loads((R/'circuit.json').read_text())['components']
catalog=json.loads((R/'procurement.json').read_text())
def mfr(c):
    m=c['mpn']
    for prefix,name in [('RC','Yageo'),('RT','Yageo'),('CC','Yageo'),('GRM','Murata'),('GCM','Murata'),('WSL','Vishay'),('LTST','Lite-On'),('LTC','Analog Devices'),('MAX','Analog Devices'),('TYPE-C','HRO'),('FH12','Hirose'),('S2B','JST'),('SM0','JST'),('SM14','JST'),('TL3305','E-Switch'),('XAL','Coilcraft'),('0466','Littelfuse'),('PESD','Nexperia'),('AO3400','Alpha & Omega Semiconductor'),('USBLC','STMicroelectronics')]:
        if m.startswith(prefix):return name
    return 'Texas Instruments'
def refs(cs):return ','.join(sorted([c['reference'] for c in cs],key=lambda s:(re.sub(r'\d','',s),int(re.search(r'\d+',s)[0]))))
groups=collections.defaultdict(list)
for c in parts:
    if c['model'] not in ['TP','SJ']:groups[c['mpn'],c['dnp']].append(c)
rows=[]
for (mpn,dnp),cs in groups.items():
    c=cs[0];cat=catalog.get(mpn,{})
    rows.append(dict(Designator=refs(cs),Quantity=len(cs),Value=' / '.join(sorted({x['value'] for x in cs})),Manufacturer=mfr(c),MPN=mpn,Footprint=c['footprint'],DNP='yes' if dnp else 'no',LCSC=cat.get('lcsc','TBD'),JLC_class=cat.get('jlc_class','TBD; comprobar al cotizar'),Stock_observation=cat.get('stock','No confirmado'),USD_unit_observed=cat.get('usd',''),Price_tier=cat.get('tier',''),Source=cat.get('source','https://www.lcsc.com/search?q='+mpn.replace('#','%23')),Datasheet=c['datasheet'],Alternative=cat.get('alternative','Mismo MPN de distribuidor autorizado; no sustitución automática'),Notes='; '.join(sorted({x['reason'] for x in cs if x['reason']}))))
with (M/'bom.csv').open('w',newline='') as f:
    w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
with (M/'bom-jlcpcb.csv').open('w',newline='') as f:
    w=csv.writer(f);w.writerow(['Comment','Designator','Footprint','LCSC Part #'])
    for r in rows:
        if r['DNP']=='no':w.writerow([r['MPN'],r['Designator'],r['Footprint'].split(':')[1],r['LCSC'] if r['LCSC']!='TBD' else ''])
valid={c['reference'] for c in parts if not c['dnp'] and c['model'] not in ['TP','SJ']}
with (M/'positions-kicad.csv').open() as f:positions=list(csv.DictReader(f))
out=[p for p in positions if p['Ref'] in valid]
assert {p['Ref'] for p in out}==valid
with (M/'cpl-jlcpcb.csv').open('w',newline='') as f:
    w=csv.writer(f);w.writerow(['Designator','Mid X','Mid Y','Layer','Rotation'])
    for p in out:w.writerow([p['Ref'],p['PosX']+'mm',p['PosY']+'mm','Top' if p['Side']=='top' else 'Bottom',p['Rot']])
(M/'dnp.txt').write_text('J5: no montar. Huella/cable candidatos sin comprobación física de la Tiny del usuario.\nJP1, JP2 y JP3: dejar abiertos, no son componentes.\nTP1–TP10: cobre, sin compra. H1/H2: taladros NPTH, sin compra.\n')
print(f'{len(rows)} filas BOM; {len(out)} componentes a montar; {sum(r["LCSC"]=="TBD" for r in rows)} MPN sin código LCSC confirmado.')
