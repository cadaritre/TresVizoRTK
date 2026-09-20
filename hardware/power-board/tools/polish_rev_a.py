"""Planos, propiedades finales y archivos para revisión mecánica."""
from pathlib import Path
import pcbnew as k,json
B=Path(__file__).resolve().parents[1]/'rev-a';b=k.LoadBoard(str(B/'power-board.kicad_pcb'));D=json.loads((B/'circuit.json').read_text());parts={p['reference']:p for p in D['components']}
def mm(x):return k.FromMM(x)
for t in list(b.GetTracks()):
 if isinstance(t,k.PCB_VIA) and abs(k.ToMM(t.GetPosition().x)-14.15)<.001 and abs(k.ToMM(t.GetPosition().y)-8.25)<.001:b.RemoveNative(t)
for fp in b.GetFootprints():
 if fp.GetReference() in parts:fp.SetValue(parts[fp.GetReference()]['value'])
net=b.FindNet('GND')
for layer in [k.F_Cu,k.B_Cu]:
 if any(z.GetLayer()==layer for z in b.Zones()):continue
 z=k.ZONE(b);z.SetLayer(layer);z.SetNet(net);z.SetLocalClearance(mm(.15));z.SetMinThickness(mm(.127));z.SetPadConnection(k.ZONE_CONNECTION_FULL);z.SetIslandRemovalMode(k.ISLAND_REMOVAL_MODE_ALWAYS)
 poly=z.Outline();poly.NewOutline()
 for x,y in [(.25,.25),(44.75,.25),(44.75,39.75),(.25,39.75)]:poly.Append(mm(x),mm(y))
 b.Add(z)
b.BuildConnectivity();k.ZONE_FILLER(b).Fill(b.Zones());k.SaveBoard(str(B/'power-board.kicad_pcb'),b)
print('Ground pours filled; board metadata synchronized')
