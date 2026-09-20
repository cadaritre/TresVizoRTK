"""Vías de retorno locales y salida del pin de control BGA; comprobación geométrica."""
from pathlib import Path
import json,math,pcbnew as k
B=Path(__file__).resolve().parents[1]/'rev-a';b=k.LoadBoard(str(B/'power-board.kicad_pcb'));report=json.loads((B/'review/drc.json').read_text());net={n.GetNetname():n for n in b.GetNetsByNetcode().values()}
def mm(x):return k.FromMM(x)
def v(x,y):return k.VECTOR2I(mm(x),mm(y))
def xy(p):return [k.ToMM(p.x),k.ToMM(p.y)]
# Redundant fanout vias reported as dangling on already connected signals.
remove={i['uuid'] for e in report['violations'] if e['type']=='via_dangling' for i in e['items'] if 'USB_PATH_EN' not in i['description']}
for t in list(b.GetTracks()):
 if t.m_Uuid.AsString() in remove:b.RemoveNative(t)
items=list(b.GetTracks())+[p for f in b.GetFootprints() for p in f.Pads()]
lookup={t.m_Uuid.AsString():t for t in items}
def shape(item,layer=None):
 if isinstance(item,k.PAD):return item.GetEffectiveShape(layer if layer is not None else item.GetLayer())
 return item.GetEffectiveShape()
def clear_circle(netname,x,y):
 circle=k.SHAPE_CIRCLE(v(x,y),mm(.225))
 if not(.55<x<44.45 and .55<y<39.45):return False
 for o in items:
  if isinstance(o,k.PAD) and not o.GetLayerSet().Contains(k.F_Cu) and not o.GetLayerSet().Contains(k.B_Cu):continue
  same=o.GetNetname()==netname
  if same and not isinstance(o,k.PAD):continue
  if shape(o).Collide(circle,mm(.06 if same else .135)):return False
 return True
def clear_line(netname,a,c,layer):
 seg=k.SHAPE_SEGMENT(v(*a),v(*c),mm(.18))
 for o in items:
  if o.GetNetname()==netname or not o.IsOnLayer(layer):continue
  if shape(o,layer).Collide(seg,mm(.135)):return False
 return True
def add(netname,x,y,a,layer):
 vi=k.PCB_VIA(b);vi.SetPosition(v(x,y));vi.SetWidth(mm(.45));vi.SetDrill(mm(.2));vi.SetViaType(k.VIATYPE_THROUGH);vi.SetLayerPair(k.F_Cu,k.B_Cu);vi.SetNet(net[netname]);vi.SetFrontTentingMode(k.TENTING_MODE_TENTED);vi.SetBackTentingMode(k.TENTING_MODE_TENTED);vi.SetLocked(True);b.Add(vi);items.append(vi)
 tr=k.PCB_TRACK(b);tr.SetStart(v(*a));tr.SetEnd(v(x,y));tr.SetWidth(mm(.18));tr.SetLayer(layer);tr.SetNet(net[netname]);tr.SetLocked(True);b.Add(tr);items.append(tr)
 return [x,y]
def escape(netname,locations,layer):
 for radius in [.55,.7,.85,1.,1.2,1.4,1.7,2.0,2.5,3.]:
  for a in locations:
   for angle in range(0,360,15):
    x=round(a[0]+radius*math.cos(math.radians(angle)),4);y=round(a[1]+radius*math.sin(math.radians(angle)),4)
    if clear_circle(netname,x,y) and clear_line(netname,a,[x,y],layer):return add(netname,x,y,a,layer)
 return None
seen=set();added=[]
for e in report['unconnected_items']:
 for i in e['items']:
  if '[GND]' not in i['description'] or i['uuid'] in seen:continue
  seen.add(i['uuid']);o=lookup.get(i['uuid']);assert o,i
  if isinstance(o,k.PCB_VIA):continue
  points=[xy(o.GetPosition())] if isinstance(o,k.PAD) else [xy(o.GetStart()),xy(o.GetEnd())]
  result=escape('GND',points,o.GetLayer());print('GND escape',i['description'],result);added.append(result)
for e in report['violations']:
 if e['type']=='track_dangling' and '[GND]' in e['items'][0]['description']:
  o=lookup[e['items'][0]['uuid']];result=escape('GND',[xy(o.GetStart()),xy(o.GetEnd())],o.GetLayer());print('GND spur via',result)
pad=next(p for f in b.GetFootprints() if f.GetReference()=='U8' for p in f.Pads() if p.GetNumber()=='A1');end=escape('USB_PATH_EN',[xy(pad.GetPosition())],k.F_Cu);print('USB_PATH_EN escape',end)
(B/'review/last_route.json').write_text(json.dumps({'net':'USB_PATH_EN','end':end,'start':[14.9107,23.4146]},indent=2))
b.GetDesignSettings().m_HoleClearance=mm(.2);b.BuildConnectivity();k.ZONE_FILLER(b).Fill(b.Zones());k.SaveBoard(str(B/'power-board.kicad_pcb'),b)
