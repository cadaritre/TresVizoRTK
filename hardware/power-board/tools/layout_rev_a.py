"""Placement reproducible. Ejecutar con Python incluido en KiCad 10."""
from pathlib import Path
from uuid import uuid5,NAMESPACE_URL
import json,math,random,collections,sys
import pcbnew as k
B=Path(__file__).resolve().parents[1]/'rev-a';D=json.loads((B/'circuit.json').read_text());parts=D['components'];P={p['reference']:p for p in parts}
if (B/'power-board.kicad_pcb').exists() and '--replace-board' not in sys.argv:
 raise SystemExit('PCB existente: este script elimina el ruteo. Usar export_rev_a.py para exportar. --replace-board sólo para regenerar intencionalmente desde cero.')
W,H=45.,40.;board=k.BOARD();board.SetCopperLayerCount(4)
def mm(x):return k.FromMM(x)
def vec(x,y):return k.VECTOR2I(mm(x),mm(y))
def uid(x):return str(uuid5(NAMESPACE_URL,'tresvizo-power-reva/'+x))
settings=board.GetDesignSettings();settings.m_TrackMinWidth=mm(.127);settings.m_MinClearance=mm(.127);settings.m_ViasMinSize=mm(.45);settings.m_MinThroughDrill=mm(.2);settings.m_CopperEdgeClearance=mm(.25);settings.m_SolderMaskExpansion=mm(.03)
nc=settings.m_NetSettings.GetDefaultNetclass();nc.SetClearance(mm(.127));nc.SetTrackWidth(mm(.2));nc.SetViaDiameter(mm(.45));nc.SetViaDrill(mm(.2))
names=sorted({n for p in parts for n in p['pins'].values() if n});nets={}
for name in names:
 n=k.NETINFO_ITEM(board,name);board.Add(n);nets[name]=n
fps={};bounds={}
for p in parts:
 lib,name=p['footprint'].split(':');fp=k.FootprintLoad(str(B/'lib'/(lib+'.pretty')),name)
 assert fp,p['footprint'];fp.SetReference(p['reference']);fp.SetValue(p['value']);fp.SetFPID(k.LIB_ID(lib,name));fp.SetUuid(k.KIID(uid('pcb/'+p['reference'])))
 fp.SetPath(k.KIID_PATH('/'+uid('root')+'/'+uid('sheet/'+p['section'])+'/'+uid(p['reference'])))
 fp.SetDNP(p['dnp']);fp.Reference().SetVisible(False);fp.Value().SetVisible(False)
 actual={pad.GetNumber() for pad in fp.Pads() if pad.GetNumber() and pad.GetNumber()!='MP'}
 assert actual==set(p['pins']),(p['reference'],actual,set(p['pins']))
 for pad in fp.Pads():
  n=p['pins'].get(pad.GetNumber())
  if n:pad.SetNet(nets[n])
 # Courtyard represented by footprint graphics rather than hidden field boxes.
 cs=[g.GetBoundingBox() for g in fp.GraphicalItems() if g.GetLayer()==k.F_CrtYd]
 xs=[k.ToMM(bb.GetLeft()) for bb in cs];ys=[k.ToMM(bb.GetTop()) for bb in cs];xe=[k.ToMM(bb.GetRight()) for bb in cs];ye=[k.ToMM(bb.GetBottom()) for bb in cs]
 bounds[p['reference']]=(min(xs),min(ys),max(xe),max(ye))
 board.Add(fp);fps[p['reference']]=fp
# Fixed high-current / USB component locations. Positive angles follow KiCad.
fixed={
 'J1':(22.5,3.8,180,'F'),'J2':(5.5,31,270,'F'),'J3':(3.8,19,270,'F'),'J4':(39.5,27,90,'F'),
 'J5':(36,35,0,'F'),'J6':(20,36.4,0,'F'),'SW1':(37,3.5,0,'F'),
 'LED1':(7,2,0,'F'),'LED2':(30.5,2,0,'F'),'LED3':(30.5,4,0,'F'),'LED4':(30.5,6,0,'F'),
 'U3':(8,6,0,'F'),'U4':(14,10,0,'F'),'U8':(9,11.5,0,'F'),'U9':(11,25,0,'F'),'U10':(15,20,0,'F'),
 'Q2':(12,29,180,'F'),'Q3':(15,29,0,'F'),'F2':(8.5,30.5,0,'B'),
 'U20':(29,19.5,0,'F'),'L1':(31.5,23,90,'F'),
 'U21':(22.5,11.5,90,'F'),'U25':(22.5,16,0,'F'),
 'U11':(5,10,0,'B'),'U12':(5,15,0,'B'),'U13':(9,5,0,'B'),'U14':(10,10,0,'B'),
 'U15':(15,10,0,'B'),'U16':(10,15,0,'B'),'U17':(15,15,0,'B'),'U18':(10,20,0,'B'),'U19':(18,23,0,'B'),
 'U22':(27,11.5,0,'B'),'U23':(33,10,0,'B'),'U24':(27,17,0,'B'),'U26':(33,16.5,0,'B'),
 'U27':(24,28,0,'F'),'U28':(24,28,0,'B'),'U29':(29,25,0,'B'),'U30':(32,30,0,'B'),'U31':(24,34,0,'B'),
 'U5':(5.5,23.5,0,'B'),'U6':(7,27,0,'B'),'U7':(13,25,0,'B'),
 'Q1':(14,13.8,0,'F'),'Q4':(33,3,0,'B'),'Q5':(38,17,0,'B'),'Q6':(39,11,0,'B'),
}
# Power bypass caps intentionally placed next to their converter pins.
for p in parts:
 if p['model']=='C' and p['section']=='04_5v_outputs':
  if p['value']=='10u':fixed[p['reference']]=(25,21,90,'F')
  elif 'SYSTEM_5V' in p['pins'].values():
   idx=sum(1 for ref in fixed if ref.startswith('C') and P[ref]['section']=='04_5v_outputs' and 'SYSTEM_5V' in P[ref]['pins'].values());fixed[p['reference']]=(32.5+idx*3,16.5,90,'F')
fixed.update({'C6':(16.5,16.5,0,'F'),'C7':(11.3,20,90,'F'),'C8':(19.2,20,90,'F'),'R25':(27,14,0,'F'),'R26':(26.5,17,0,'F')})
# Semantic centers for remaining small parts.
centers={'01_usb_power':(10,9,'F'),'02_battery_charger':(12,20,'F'),'03_power_control':(12,13,'B'),'04_5v_outputs':(27,19,'F'),'05_usb_native':(27,18,'B'),'06_gauge':(24,25,'B'),'07_interfaces':(31,11,'B')}
# Roundish placement restrictions reserve mechanical hole keepouts.
holes=[(2.5,2.5),(2.5,37.5)]; placed={};rects={}
def rect(ref,x,y,ang,side):
 a,b,c,d=bounds[ref];pts=[(a,b),(a,d),(c,b),(c,d)]
 if side=='B':pts=[(-px,py) for px,py in pts]
 co=round(math.cos(math.radians(ang)));si=round(math.sin(math.radians(ang)))
 pts=[(x+px*co+py*si,y-px*si+py*co) for px,py in pts]
 return (min(p[0] for p in pts),min(p[1] for p in pts),max(p[0] for p in pts),max(p[1] for p in pts))
def valid(ref,x,y,a,side,extra=.04):
 r=rect(ref,x,y,a,side)
 # Connectors intentionally approach the outline; all auto-placed items fully inside.
 if r[0]<.45 or r[1]<.45 or r[2]>W-.45 or r[3]>H-.45:return False
 if side=='F':
  for t in [(24.1,13.5,34,26.5),(19.5,9.2,25.4,17.5)]:
   if r[0]<t[2] and r[2]>t[0] and r[1]<t[3] and r[3]>t[1]:return False
 if side=='B':
  for vx,vy in [(22.25,8.2),(23.25,8.2),(23.45,9.6),(21.15,16),(23.85,16),(36.75,32),(37.25,31.6),(14.55,19.55),(15.45,19.55),(14.55,20.45),(15.45,20.45)]:
   if r[0]<vx+.5 and r[2]>vx-.5 and r[1]<vy+.5 and r[3]>vy-.5:return False
 for hx,hy in holes:
  if r[0]<hx+1.6 and r[2]>hx-1.6 and r[1]<hy+1.6 and r[3]>hy-1.6:return False
 for o,t in rects.items():
  if placed[o][3]==side or o=='J1':
   if r[0]<t[2]+extra and r[2]>t[0]-extra and r[1]<t[3]+extra and r[3]>t[1]-extra:return False
 return True
def put(ref,x,y,a,side):
 placed[ref]=(x,y,a,side);rects[ref]=rect(ref,x,y,a,side)
for ref,loc in fixed.items():put(ref,*loc)
rails={'GND','AON_3V0','TINY_3V3','SYSTEM_POWER','SYSTEM_5V','USB_3V3','PACK_P','CELL_N'}
netparts=collections.defaultdict(list)
for p in parts:
 for n in set(p['pins'].values())-{None}:netparts[n].append(p['reference'])
def links(ref):
 out={}
 for n in P[ref]['pins'].values():
  if not n:continue
  weight=.03 if n in rails else 1/max(1,len(netparts[n])-1)
  for o in netparts[n]:
   if o!=ref and o in placed:out[o]=out.get(o,0)+weight
 return out
near={'C2':'U3','C3':'U3','C4':'U4','C5':'U9','C9':'U11','C10':'U11','C12':'U12','C13':'U13','C17':'U14','C22':'U22','C23':'U23','C24':'U25','C25':'U27','C26':'U28','C27':'U30'}
logic_refs=[p['reference'] for p in parts if p['model'] in ['AND','OR','NAND','NOT','BUF']]
near.update({f'C{28+i}':ref for i,ref in enumerate(logic_refs)})
random.seed(8)
remaining=[p['reference'] for p in parts if p['reference'] not in placed]
remaining.sort(key=lambda r: (-1 if r in near else 0, -((bounds[r][2]-bounds[r][0])*(bounds[r][3]-bounds[r][1]))))
# Large parts first, then passives pulled toward their signal's IC.
for ref in remaining:
 p=P[ref];cx,cy,side=centers[p['section']];adj=links(ref)
 if ref in near:adj={near[ref]:30.0}
 if adj:
  den=sum(adj.values());cx=sum(placed[o][0]*v for o,v in adj.items())/den;cy=sum(placed[o][1]*v for o,v in adj.items())/den
  strong=max(adj,key=adj.get)
  if adj[strong]>.1:side=placed[strong][3]
 if p['model']=='TP':side='B'
 best=None
 for chosen_side in [side, 'B' if side=='F' else 'F']:
  candidates=sorted(((round(x*.5,2),round(y*.5,2)) for x in range(2,int(W*2-1)) for y in range(2,int(H*2-1))),key=lambda pos:(pos[0]-cx)**2+(pos[1]-cy)**2)
  found=0
  for x,y in candidates:
   for a in [0,90]:
    if valid(ref,x,y,a,chosen_side):
     score=sum(v*(abs(x-placed[o][0])+abs(y-placed[o][1])) for o,v in adj.items())+.15*(abs(x-cx)+abs(y-cy))+(2 if chosen_side!=side else 0)
     if best is None or score<best[0]:best=(score,x,y,a,chosen_side)
     found+=1
   if found>80:break
  if best is not None:break
 if best is None:raise RuntimeError('No room for '+ref)
 put(ref,*best[1:])
# Log explicit overlap check for fixed locations; no silent acceptance.
collisions=[]
for a,r in rects.items():
 for o,t in rects.items():
  if o<=a:continue
  if placed[a][3]==placed[o][3]:
   if r[0]<t[2] and r[2]>t[0] and r[1]<t[3] and r[3]>t[1]:collisions.append([a,o])
print('Fixed courtyard overlaps:',collisions)
for ref,(x,y,a,side) in placed.items():
 fp=fps[ref];fp.SetPosition(vec(x,y))
 if side=='B':fp.Flip(fp.GetPosition(),k.FLIP_DIRECTION_LEFT_RIGHT)
 fp.SetOrientationDegrees(a)
# Outline and mounting holes.
for i,(x,y) in enumerate([(0,0),(W,0),(W,H),(0,H)]):
 end=[(W,0),(W,H),(0,H),(0,0)][i];e=k.PCB_SHAPE();e.SetShape(k.SHAPE_T_SEGMENT);e.SetStart(vec(x,y));e.SetEnd(vec(*end));e.SetLayer(k.Edge_Cuts);e.SetWidth(mm(.05));board.Add(e)
for i,(x,y) in enumerate(holes):
 fp=k.FOOTPRINT(board);fp.SetReference('H'+str(i+1));fp.SetValue('M2 NPTH');fp.Reference().SetVisible(False);fp.Value().SetVisible(False)
 pad=k.PAD(fp);pad.SetAttribute(k.PAD_ATTRIB_NPTH);pad.SetShape(k.PAD_SHAPE_CIRCLE);pad.SetSize(vec(2.2,2.2));pad.SetDrillSize(vec(2.2,2.2));pad.SetLayerSet(k.LSET.AllCuMask());pad.SetPosition(vec(0,0));fp.Add(pad);board.Add(fp);fp.SetPosition(vec(x,y));fp.SetExcludedFromBOM(True);fp.SetExcludedFromPosFiles(True)
board.GetTitleBlock().SetTitle('TresVizo Power Board — Rev A prototype');board.GetTitleBlock().SetRevision('A');board.GetTitleBlock().SetDate('2026-09-20')
for fp in board.GetFootprints():
 if fp.GetReference()=='J1':
  for g in list(fp.GraphicalItems()):
   if g.GetLayer()==k.F_SilkS and g.GetBoundingBox().GetTop()<mm(.15):fp.Remove(g)
board.BuildConnectivity();k.SaveBoard(str(B/'power-board.kicad_pcb'),board)
(B/'placement.json').write_text(json.dumps({'width_mm':W,'height_mm':H,'holes':holes,'placements':placed,'courtyards':rects,'collisions':collisions},indent=2)+'\n')
print('Placed',len(fps),'components on',W,'x',H,'mm')
