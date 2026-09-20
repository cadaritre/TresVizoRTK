"""Ruteo fijado de potencia/USB, plano GND y exportación para ruteo de control."""
from pathlib import Path
import json,math
import pcbnew as k
B=Path(__file__).resolve().parents[1]/'rev-a';b=k.LoadBoard(str(B/'power-board.kicad_pcb'))
def mm(x):return k.FromMM(x)
def vec(x,y):return k.VECTOR2I(mm(x),mm(y))
nets={n.GetNetname():n for n in b.GetNetsByNetcode().values()};fps={f.GetReference():f for f in b.GetFootprints()}
def line(net,pts,width=.18,layer=k.F_Cu):
 for a,c in zip(pts,pts[1:]):
  if a==c:continue
  t=k.PCB_TRACK(b);t.SetStart(vec(*a));t.SetEnd(vec(*c));t.SetWidth(mm(width));t.SetLayer(layer);t.SetNet(nets[net]);t.SetLocked(True);b.Add(t)
def via(net,x,y,size=.45,drill=.2):
 v=k.PCB_VIA(b);v.SetPosition(vec(x,y));v.SetWidth(mm(size));v.SetDrill(mm(drill));v.SetViaType(k.VIATYPE_THROUGH);v.SetLayerPair(k.F_Cu,k.B_Cu);v.SetNet(nets[net]);v.SetFrontTentingMode(k.TENTING_MODE_TENTED);v.SetBackTentingMode(k.TENTING_MODE_TENTED);v.SetLocked(True);b.Add(v)
def pad(ref,pn):
 p=next(p for p in fps[ref].Pads() if p.GetNumber()==str(pn));return (k.ToMM(p.GetPosition().x),k.ToMM(p.GetPosition().y))
# Boost: short SW connection and local power loop, retained by autorouter.
line('BOOST_SW',[pad('U20',5),(30.4,19.5),(30.9,20)],.2)
line('BOOST_SW',[(30.9,20),(31.5,20.6),pad('L1',2)],.5)
line('SYSTEM_5V',[pad('U20',6),(30.2,19),(30.9,18.3)],.2)
line('SYSTEM_5V',[(30.9,18.3),(31.225,17.975),pad('C20',1),pad('C21',1)],.5)
line('SYSTEM_POWER',[pad('U20',3),(27.6,20)],.2)
line('SYSTEM_POWER',[(27.6,20),(27.6,21),(26.65,21.95),pad('C19',1)],.5)
line('SYSTEM_POWER',[pad('L1',1),(27.235,24.185),pad('C19',1)],.6)
# Charger rail escapes: narrow at 0.5 mm pitch, wider beyond body.
line('SYSTEM_POWER',[pad('U10',10),(17.25,20.25),(17.25,19.75),pad('U10',11)],.2)
line('SYSTEM_POWER',[(17.25,20.25),(18.475,21.475),pad('C8',1)],.5)
line('PACK_P',[pad('U10',2),(12.7,19.75),(12.7,20.25),pad('U10',3)],.2)
line('PACK_P',[(12.7,20.25),(12.7,20.95),pad('C7',1)],.4)
# USB-C: A/B mirrored pin pairs; D- crosses on L3 with 0.4/0.2 vias.
for pin in ['A6','B6']:line('HOST_USB_P',[pad('J1',pin),(pad('J1',pin)[0],9.1),(21.75,9.1)])
line('HOST_USB_P',[(21.75,9.1),(21.55,9.3),pad('U21',6),pad('U21',1)])
for pin in ['A7','B7']:
 x,y=pad('J1',pin);line('HOST_USB_N',[(x,y),(x,8.2)]);via('HOST_USB_N',x,8.2,.4)
line('HOST_USB_N',[(22.25,8.2),(22.25,8.85),(23.25,8.85),(23.25,8.2)],layer=k.In2_Cu)
line('HOST_USB_N',[(23.25,8.85),(23.45,9.05),(23.45,9.6)],layer=k.In2_Cu);via('HOST_USB_N',23.45,9.6,.4)
line('HOST_USB_N',[(23.45,9.6),pad('U21',4),pad('U21',3)])
line('HOST_USB_P',[pad('U21',1),(20.8,13.3875),(19.8,13.3875),(19.8,15.6),(20.7,16.5),pad('U25',3)])
line('HOST_USB_N',[pad('U21',3),(25,14.1875),(25,15.725),(24.225,16.5),pad('U25',5)])
# MCU side USB on L3 with uninterrupted adjacent L2 ground reference.
line('TINY_USB_P',[pad('U25',2),(21.15,16)]);via('TINY_USB_P',21.15,16,.4)
line('TINY_USB_N',[pad('U25',6),(23.85,16)]);via('TINY_USB_N',23.85,16,.4)
line('TINY_USB_P',[(21.15,16),(22.275,17.125),(22.275,29.5),(23.275,30.5),(35.75,30.5),(36.75,31.5),(36.75,32)],layer=k.In2_Cu)
line('TINY_USB_N',[(23.85,16),(22.725,17.125),(22.725,29.05),(23.725,30.05),(36.25,30.05),(37.25,31.05),(37.25,31.6)],layer=k.In2_Cu)
for n,x,pn in [('TINY_USB_P',36.75,6),('TINY_USB_N',37.25,7)]:
 end_y=32 if pn==6 else 31.6
 via(n,x,end_y,.4);line(n,[(x,end_y),pad('J5',pn)])
# Thermal vias inside charger EP require filled/capped via-in-pad assembly.
for x in [14.55,15.45]:
 for y in [19.55,20.45]:via('GND',x,y,.4)
# Solid reference plane. No signal tracks will be autorouted on In1.Cu.
z=k.ZONE(b);z.SetLayer(k.In1_Cu);z.SetNet(nets['GND']);z.SetLocalClearance(mm(.18));z.SetMinThickness(mm(.127));z.SetPadConnection(k.ZONE_CONNECTION_FULL)
p=z.Outline();p.NewOutline()
for x,y in [(.25,.25),(44.75,.25),(44.75,39.75),(.25,39.75)]:p.Append(mm(x),mm(y))
b.Add(z)
b.BuildConnectivity();k.ZONE_FILLER(b).Fill(b.Zones());k.SaveBoard(str(B/'power-board.kicad_pcb'),b)
# Configure project net classes after save; subsequent loads read these definitions.
pro=B/'power-board.kicad_pro';j=json.loads(pro.read_text());base=j['net_settings']['classes'][0];base.update(clearance=.127,track_width=.2,via_diameter=.45,via_drill=.2)
power=dict(base,name='Power',track_width=.3,via_diameter=.6,via_drill=.3);usb=dict(base,name='USB',track_width=.18,via_diameter=.4,via_drill=.2)
powernets=['USB_VBUS','USB_FUSED','USB_INPUT_PROTECTED','CELL_P','CELL_N','PACK_P','BAT_FET_MID','BAT_SHUNT_N','SYSTEM_POWER','SYSTEM_5V'];usbnet=['HOST_USB_P','HOST_USB_N','TINY_USB_P','TINY_USB_N']
j['net_settings']['classes']=[base,power,usb];j['net_settings']['netclass_patterns']=[{'pattern':n,'netclass':'Power'} for n in powernets]+[{'pattern':n,'netclass':'USB'} for n in usbnet];j['board']['design_settings']['rules']['min_via_diameter']=.4
pro.write_text(json.dumps(j,indent=2)+'\n')
b=k.LoadBoard(str(B/'power-board.kicad_pcb'))
classes={}
for name,width in [('Power',.3),('USB',.18)]:
 nc=k.NETCLASS(name);nc.SetClearance(mm(.127));nc.SetTrackWidth(mm(width));nc.SetViaDiameter(mm(.45 if name=='Power' else .4));nc.SetViaDrill(mm(.2));classes[name]=nc
for n in b.GetNetsByNetcode().values():
 if n.GetNetname() in powernets:n.SetNetClass(classes['Power'])
 elif n.GetNetname() in usbnet:n.SetNetClass(classes['USB'])
print('DSN',k.ExportSpecctraDSN(b,str(B/'review/power-board.dsn')))
print('Manual copper:',len(list(b.GetTracks())),'segments/vias')
# Exporter exposes only the default project class in standalone Python; assign DSN classes explicitly.
dsn=B/'review/power-board.dsn';s=dsn.read_text();start=s.index('(class kicad_default ');depth=0;end=None
for i in range(start,len(s)):
 if s[i]=='(':depth+=1
 elif s[i]==')':
  depth-=1
  if depth==0:end=i+1;break
allnets=sorted({n.GetNetname() for n in b.GetNetsByNetcode().values() if n.GetNetname()});rest=[n for n in allnets if n not in powernets+usbnet]
def dclass(name,ns,width):return '(class '+name+' '+' '.join(ns)+' (circuit (use_via "Via[0-3]_450:200_um")) (rule (width '+str(width)+') (clearance 127)))'
s=s[:start]+dclass('kicad_default',rest,200)+'\n'+dclass('Power',powernets,300)+'\n'+dclass('USB',usbnet,180)+s[end:];dsn.write_text(s)
