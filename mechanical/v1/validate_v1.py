"""Validacion nominal reproducible de V1; no sustituye la primera impresion."""
from pathlib import Path
import FreeCAD as A, Part, json, itertools, hashlib, math
ROOT=Path(__file__).resolve().parent; OUT=ROOT/'generated'
P=json.loads((ROOT/'parameters.json').read_text()); EPS=P['collision_threshold_mm3'];V=A.Vector
D=A.openDocument(str(OUT/'TresVizo-V1.FCStd'))
I=json.loads((OUT/'model-index.json').read_text())
S={o.Name:o.Shape for o in D.Objects if hasattr(o,'Shape') and not hasattr(o,'Group')}
R={'freecad_version':A.Version(),'limits':'Geometria nominal; movimientos discretos cada 1 mm (boton 0.05 mm). Cables flexibles desconectados/retirados para servicio. No ensayo fisico ni barrido continuo certificado.'}
def write(): (OUT/'validation.json').write_text(json.dumps(R,indent=2,ensure_ascii=False),encoding='utf-8')
def bbox(s):return [round(getattr(s.BoundBox,k),5) for k in ['XMin','YMin','ZMin','XMax','YMax','ZMax']]
def hits(s,obs):
 out=[]
 for n,t in obs.items():
  if s.BoundBox.intersect(t.BoundBox):
   c=s.common(t)
   if c.Volume>EPS:out.append({'against':n,'volume_mm3':round(c.Volume,5),'box':bbox(c)})
 return out
def moved(s,v):s=s.copy();s.translate(V(*v));return s
def motion(name,moving,obstacles,axis,distance,origin=(0,0,0),step=1):
 print('MOVIMIENTO',name,flush=True); failures=[]
 for i in range(round(distance/step)+1):
  t=i*step
  for n in moving:
   failures.extend(dict(offset_mm=t,part=n,**h) for h in hits(moved(S[n],[a+t*b for a,b in zip(origin,axis)]),{k:S[k] for k in obstacles}))
 return {'name':name,'moving':moving,'obstacles':obstacles,'axis':axis,'origin':origin,'distance_mm':distance,'step_mm':step,'samples':round(distance/step)+1,'hits':failures}
R['solids']=[{'name':n,'valid':s.isValid(),'solids':len(s.Solids)} for n,s in S.items()]
R['pair_intersections']=[]
intent={frozenset(['ModulePanel',n]):'Vastago liso dentro de piloto para roscar plastico' for n in ['USBScrew1','USBScrew4','ButtonM3']}
intent.update({frozenset(['A5_HA901Reserve','A5_AntennaBolt'+str(i)]):'Rosca comercial de antena representada sin vaciado' for i in range(1,4)})
intent[frozenset(['TinyUSBPlugReserve','UsbHarness'])]='Continuidad plug/arnes'
for a,b in itertools.combinations(['BatteryToPower','RearPowerBus','PowerToGNSS'],2):intent[frozenset([a,b])]='Corredores de un mismo arnes compartido; no solidos de cables individuales'
for (n,s),(m,t) in itertools.combinations(S.items(),2):
 if any(k in (n,m) for k in ['A5_IMUTarget']+I.get('tools',[])):continue
 for h in hits(s,{m:t}):R['pair_intersections'].append(dict(part=n,classification=intent.get(frozenset([n,m]),'UNEXPECTED'),**h))
print('PARES',len(R['pair_intersections']),flush=True);write()
refs=I['routes']+I.get('tools',[])+['A5_IMUTarget','A5_CoaxRouteReserve','TinyUSBPlugReserve']
physical=[n for n in S if n not in refs]
panel=[n for n in physical if not n.startswith('A5_') and n not in ['TinyAdapterPosition','PowerBoost','SoftPower'] and not n.startswith('Insert')]
cap=['A5_AntennaCap','A5_HA901Reserve','A5_AntennaBolt1','A5_AntennaBolt2','A5_AntennaBolt3']
carrier=['A5_BatteryIMUCarrier','A5_BatteryReserve','A5_IMUReserve','A5_IMUNutBar','A5_IMUPcbBolt1','A5_IMUPcbBolt2','A5_IMUPcbNut1','A5_IMUPcbNut2','A5_SDReference','A5_ModuleNut12','A5_ModuleNut22','PowerBoost','SoftPower']
removed=panel+cap+['A5_MainShell']+[n for n in physical if n.startswith(('A5_RadialBolt','A5_CapClosure','A5_PanelBolt','A5_ModuleBolt'))]
ops=[
('panel',panel,[n for n in physical if n not in panel and not n.startswith('A5_PanelBolt')],(0,1,0),60),
('cap',cap,[n for n in physical if n not in cap and not n.startswith('A5_CapClosureBolt')],(0,0,1),170),
('shell',['A5_MainShell'],[n for n in physical if n not in panel+cap+['A5_MainShell'] and not n.startswith(('A5_RadialBolt','A5_CapClosure','A5_Panel'))],(0,0,1),180),
('loaded_carrier',carrier,[n for n in physical if n not in carrier+removed],(0,-1,0),80),
('battery',['A5_BatteryReserve'],['A5_BatteryIMUCarrier','A5_IMUReserve','A5_IMUNutBar','PowerBoost','SoftPower','A5_SDReference'],(0,1,0),60),
('powerboost',['PowerBoost'],['A5_BatteryIMUCarrier','A5_BatteryReserve','A5_IMUReserve','A5_SDReference','SoftPower'],(0,-1,0),60),
('soft_power',['SoftPower'],['A5_BatteryIMUCarrier','A5_BatteryReserve','A5_SDReference','PowerBoost'],(0,-1,0),60),
('insert_lift',['A5_FlangedInsert'],['A5_Chassis'],(0,0,1),16),
('insert_rear',['A5_FlangedInsert'],['A5_Chassis'],(0,-1,0),60,(0,0,16)),
('imu_nutbar',['A5_IMUNutBar','A5_IMUPcbNut1','A5_IMUPcbNut2'],['A5_BatteryIMUCarrier'],(0,1,0),50),
('imu_board',['A5_IMUReserve'],['A5_BatteryIMUCarrier','A5_IMUNutBar'],(0,0,1),40),
('gnss',['A5_GNSSReserve'],['A5_Chassis','A5_BatteryIMUCarrier'],(0,1,0),60),
('sd',['A5_SDReference'],['A5_BatteryIMUCarrier','PowerBoost','SoftPower'],(0,-1,0),60),
('tiny',['A5_ESPReference'],['A5_Chassis','TinyAdapterPosition'],(0,0,1),40),
('adapter',['TinyAdapterPosition'],['A5_Chassis','A5_ESPReference'],(0,1,0),60),
('button_cartridge',['ButtonCartridge','TactileBody','TactileStem'],['ModulePanel','ButtonCap'],(0,-1,0),40),
('button_stroke',['ButtonCap'],['ModulePanel','ButtonCartridge','A5_Chassis','A5_MainShell'],(0,-1,0),.4,(0,0,0),.05)]
R['motions']=[]
for op in ops:R['motions'].append(motion(*op));write()
# Herramienta axial a las 19 cabezas, con el subconjunto accesible indicado.
R['tools']=[]; R['head_intersections']=[]
for n in [k for k in physical if 'Bolt' in k or 'Screw' in k or k=='ButtonM3']:
 s=S[n]; faces=[f for f in s.Faces if isinstance(f.Surface,Part.Cylinder)]
 f=max(faces,key=lambda f:f.Surface.Radius); a=f.Surface.Axis
 if (f.CenterOfMass-sum((sol.CenterOfMass*sol.Volume for sol in s.Solids),V())/s.Volume).dot(a)<0:a=-a
 c=f.CenterOfMass;limit=max(v.Point.dot(a) for v in f.Vertexes)
 start=c+a*(limit-c.dot(a)+.01);tool=Part.makeCylinder(1.5,35,start,a)
 if n.startswith('Insert'):obs=['A5_Chassis','A5_FlangedInsert']+[k for k in physical if k.startswith('Insert') and k!=n];stage='base desnuda'
 elif n.startswith('USB') or n=='ButtonM3':obs=[k for k in panel if k!=n];stage='panel fuera'
 elif n.startswith('A5_IMUPcbBolt'):obs=[k for k in carrier if k!=n];stage='cuna fuera'
 elif n.startswith('A5_AntennaBolt'):obs=[k for k in cap if k!=n];stage='tapa fuera'
 elif n.startswith('A5_ModuleBolt'):obs=[k for k in physical if k not in panel+cap+['A5_MainShell',n]];stage='cuerpo fuera'
 else:obs=[k for k in physical if k!=n];stage='conjunto cerrado'
 R['tools'].append({'screw':n,'stage':stage,'tool_diameter_mm':3,'length_mm':35,'hits':hits(tool,{k:S[k] for k in obs})})
 low=min(v.Point.dot(a) for v in f.Vertexes);head=Part.makeCylinder(f.Surface.Radius,limit-low,c+a*(low-c.dot(a)),a)
 R['head_intersections'].append({'screw':n,'hits':hits(head,{k:S[k] for k in I['printed']})})
print('HERRAMIENTAS',len(R['tools']),flush=True);write()
# Sobremolde USB-C compacto 13 x 5.5 mm, longitud 25; reversible 180 grados.
uy=37.1+(132-100)/88-1.2
plug=Part.makeBox(10,25,5.5,V(-5,uy,129.25)).fuse(Part.makeBox(13,25,2.5,V(-6.5,uy,130.75)))
for x in [-5,5]:
 for z in [130.75,133.25]:plug=plug.fuse(Part.makeCylinder(1.5,25,V(x,uy,z),V(0,1,0)))
R['usb']={'envelope_mm':[13,5.5,25],'setback_mm':1.2,'hits':hits(plug,{k:S[k] for k in ['ModulePanel','A5_MainShell']}),'minimum_gap_mm':min(plug.distToShape(S[k])[0] for k in ['ModulePanel','A5_MainShell'])}
# Variaciones de ancho admitidas con altura de componentes reducida: no afirmar caja maxima unica.
R['universal_tray_options']=[]
for n,key in [('PowerBoost','powerboost'),('SoftPower','soft_switch')]:
 boxes=[P[key]['box'],P[key]['alternative_box']]
 for b in boxes:
  sh=Part.makeBox(*b[3:],V(*b[:3]));obs={k:s for k,s in S.items() if k not in [n,'A5_IMUTarget']+I['routes']+I.get('tools',[])}
  R['universal_tray_options'].append({'module':n,'box':b,'hits':hits(sh,obs)})
# Datums y superficies criticas conservadas respecto de A5 / panel.
B=A.openDocument(str(ROOT.parents[1]/'.cache/mechanical-v1/baseline/TresVizo-panel-modules.FCStd'));old={o.Name:o.Shape for o in B.Objects if hasattr(o,'Shape') and not hasattr(o,'Group')}
critical=['A5_IMUReserve','A5_IMUTarget','A5_IMUNutBar','A5_AntennaCap','A5_HA901Reserve','A5_BatteryReserve','A5_ESPReference','USBModule','USBReceptacle','ButtonCap']
R['preserved']=[{'name':n,'symmetric_difference_mm3':S[n].cut(old[n]).Volume+old[n].cut(S[n]).Volume} for n in critical]
region=Part.makeBox(35,22,13,V(-17.5,-11,113))
R['imu_datum_removed_mm3']=old['A5_BatteryIMUCarrier'].common(region).cut(S['A5_BatteryIMUCarrier']).Volume
logo=Part.makeBox(50,20,40,V(-25,20,40))
R['front_logo_removed_mm3']=old['A5_MainShell'].common(logo).cut(S['A5_MainShell']).Volume
original_doc=A.openDocument(str(ROOT.parent/'sources/a5/TresVizo-A5.FCStd'))
S['IMUAlignmentGauge']=original_doc.IMUAlignmentGauge.Shape
R['motions'].append(motion('imu_alignment_gauge',['IMUAlignmentGauge'],['A5_BatteryIMUCarrier','A5_IMUReserve','A5_IMUNutBar','A5_IMUPcbBolt1','A5_IMUPcbBolt2'],(0,0,1),40))
R['shell_bbox_before']=bbox(old['A5_MainShell']);R['shell_bbox_after']=bbox(S['A5_MainShell'])
# Antigiro positivo y retencion axial: colision ante giro/desplazamiento sin retirar tornillos.
poleobs={k:S[k] for k in ['A5_Chassis','InsertBolt1','InsertBolt2','InsertBolt3']}
R['insert_retention']=[]
for angle in [-5,5]:
 s=S['A5_FlangedInsert'].copy();s.rotate(V(),V(0,0,1),angle)
 R['insert_retention'].append({'rotation_deg':angle,'hits':hits(s,poleobs)})
for z in [-.5,.5]:R['insert_retention'].append({'translation_z_mm':z,'hits':hits(moved(S['A5_FlangedInsert'],[0,0,z]),poleobs)})
R['pole_clear_bore']={'diameter_mm':15.875,'free_height_mm':30,'hits':hits(Part.makeCylinder(7.9375,30,V()),{'chassis':S['A5_Chassis']})}
source=ROOT.parent/'sources/a5/TresVizo-A5.FCStd';initial=json.loads((ROOT/'evidence/inputs.json').read_text())['sha256']['mechanical/A5/TresVizo-A5.FCStd']
R['original_a5_unchanged']=hashlib.sha256(source.read_bytes()).hexdigest()==initial
R['counts']={'printed':len(I['printed']),'screws':len(R['tools']),'nuts':len([n for n in I['hardware'] if 'Nut' in n]),'fastener_diameter_length_combinations':5}
fail=[]
if any(not o['valid'] or o['solids']!=1 for o in R['solids']):fail.append('solid')
if any(h['classification']=='UNEXPECTED' for h in R['pair_intersections']):fail.append('final_collision')
for k in ['motions','tools','head_intersections','universal_tray_options']:
 if any(o['hits'] for o in R[k]):fail.append(k)
if R['usb']['hits'] or R['pole_clear_bore']['hits']:fail.append('interface_access')
if any(o['symmetric_difference_mm3']>EPS for o in R['preserved']) or R['imu_datum_removed_mm3']>EPS or R['front_logo_removed_mm3']>EPS or not R['original_a5_unchanged']:fail.append('datum')
if any(not o['hits'] for o in R['insert_retention']):fail.append('insert_retention')
R['failures']=fail;R['scope_ready_for_first_full_prototype_print']=not fail;write()
print('RESULT',R['scope_ready_for_first_full_prototype_print'],fail,flush=True)
