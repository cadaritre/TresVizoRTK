"""Importar pistas de SES en modo headless, conservando las pistas fijadas."""
from pathlib import Path
import json,sys,re,pcbnew as k
B=Path(__file__).resolve().parents[1]/'rev-a';b=k.LoadBoard(str(B/'power-board.kicad_pcb'))
# KiCad's legacy ImportSpecctraSES requires a PCB_EDIT_FRAME; parse the public SES interchange instead.
source=B/'review'/('power-board.ses' if len(sys.argv)<2 else sys.argv[1]);tokens=re.findall(r'\(|\)|"(?:\\.|[^"\\])*"|[^\s()]+',source.read_text());stack=[];root=None
for token in tokens:
 if token=='(':a=[];stack.append(a)
 elif token==')':
  a=stack.pop()
  if stack:stack[-1].append(a)
  else:root=a
 else:stack[-1].append(json.loads(token) if token.startswith('"') else token)
def child(node,key):return next(x for x in node if isinstance(x,list) and x[0]==key)
routes=child(root,'routes');res=child(routes,'resolution');assert res[1:] == ['um','10'],res
network=child(routes,'network_out');nets={n.GetNetname():n for n in b.GetNetsByNetcode().values()};layers={n:b.GetLayerID(n) for n in ['F.Cu','In1.Cu','In2.Cu','B.Cu']}
def val(x):return round(float(x)*100) # 0.1 um SES units -> KiCad nm
for t in list(b.GetTracks()):
 if not t.IsLocked():b.RemoveNative(t)
count=0
for net in network[1:]:
 assert net[0]=='net';name=net[1];ni=nets[name]
 for item in net[2:]:
  if item[0]=='wire':
   p=child(item,'path');layer,width=p[1:3];pts=[k.VECTOR2I(val(x),-val(y)) for x,y in zip(p[3::2],p[4::2])]
   for start,end in zip(pts,pts[1:]):
    if start==end:continue
    t=k.PCB_TRACK(b);t.SetStart(start);t.SetEnd(end);t.SetWidth(val(width));t.SetLayer(layers[layer]);t.SetNet(ni);b.Add(t);count+=1
  elif item[0]=='via':
   typ,x,y=item[1:4];m=re.search(r'_(\d+):(\d+)_um',typ);assert m,typ
   v=k.PCB_VIA(b);v.SetPosition(k.VECTOR2I(val(x),-val(y)));v.SetWidth(int(m[1])*1000);v.SetDrill(int(m[2])*1000);v.SetViaType(k.VIATYPE_THROUGH);v.SetLayerPair(k.F_Cu,k.B_Cu);v.SetNet(ni);v.SetFrontTentingMode(k.TENTING_MODE_TENTED);v.SetBackTentingMode(k.TENTING_MODE_TENTED);b.Add(v);count+=1
  else:raise ValueError(item[0])
b.BuildConnectivity();k.ZONE_FILLER(b).Fill(b.Zones());k.SaveBoard(str(B/'power-board.kicad_pcb'),b)
print('Imported',count,'routing objects; preserved fixed tracks')
