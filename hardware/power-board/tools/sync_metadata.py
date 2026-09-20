from pathlib import Path
import pcbnew as k,json,xml.etree.ElementTree as E
B=Path(__file__).resolve().parents[1]/'rev-a';b=k.LoadBoard(str(B/'power-board.kicad_pcb'));D=json.loads((B/'circuit.json').read_text());P={p['reference']:p for p in D['components']};F={fp.GetReference():fp for fp in b.GetFootprints()}
for ref,fp in F.items():
 if ref not in P:fp.SetAttributes(fp.GetAttributes()|k.FP_BOARD_ONLY);continue
 p=P[ref];fp.SetValue(p['value']);fp.SetExcludedFromBOM(p['model'] in ['TP','SJ'])
 for key,val in [('MPN',p['mpn']),('Design_Note',p['reason']),('Datasheet',p['datasheet'])]:
  fp.SetField(key,val);fp.GetField(key).SetVisible(False);fp.GetField(key).SetPosition(fp.GetPosition())
 for pad in fp.Pads():
  if p['model']=='SJ' and pad.GetNetname()=='GND':pad.SetLocalZoneConnection(k.ZONE_CONNECTION_FULL)
for n in E.parse(B/'review/netlist.xml').getroot().findall('nets/net'):
 name=n.attrib['name']
 if not name.startswith('unconnected-'):continue
 ni=b.FindNet(name)
 if not ni:ni=k.NETINFO_ITEM(b,name);b.Add(ni)
 for node in n.findall('node'):
  fp=F[node.attrib['ref']]
  for pad in fp.Pads():
   if pad.GetNumber()==node.attrib['pin']:pad.SetNet(ni)
b.BuildConnectivity();k.ZONE_FILLER(b).Fill(b.Zones());k.SaveBoard(str(B/'power-board.kicad_pcb'),b)
print('PCB fields, NC nets, copper jumpers and mechanical-only holes synchronized')
