"""Auditoría de conectividad real y márgenes estáticos; ejecutar con pcbnew de KiCad."""
from pathlib import Path
import collections, itertools, json, math, xml.etree.ElementTree as ET
import pcbnew as k

B=Path(__file__).resolve().parents[1]/'rev-a'
parts=json.loads((B/'circuit.json').read_text())['components']
p={x['reference']:x for x in parts}
b=k.LoadBoard(str(B/'power-board.kicad_pcb'))
fps={fp.GetReference():fp for fp in b.GetFootprints()}
placements=json.loads((B/'placement.json').read_text())['placements']
x=ET.parse(B/'review/netlist.xml').getroot()
netlist={}
for net in x.findall('nets/net'):
    for n in net.findall('node'):netlist[n.attrib['ref'],n.attrib['pin']]=net.attrib['name']
checked=0
for part in parts:
    ref=part['reference'];fp=fps[ref]
    assert fp.GetValue()==part['value'],ref
    assert fp.IsDNP()==part['dnp'],ref
    assert fp.GetFieldText('MPN')==part['mpn'],(ref,'MPN')
    px,py,angle,side=placements[ref]
    assert abs(k.ToMM(fp.GetPosition().x)-px)<1e-5 and abs(k.ToMM(fp.GetPosition().y)-py)<1e-5,(ref,'position')
    assert abs((fp.GetOrientationDegrees()-angle+180)%360-180)<1e-5,(ref,'orientation')
    assert fp.GetLayer()==(k.F_Cu if side=='F' else k.B_Cu),(ref,'side')
    for pin,net in part['pins'].items():
        if net is None:continue
        assert netlist[ref,pin]==net,(ref,pin,'schematic')
        pads=[pad for pad in fp.Pads() if pad.GetNumber()==pin]
        assert pads and all(pad.GetNetname()==net for pad in pads),(ref,pin,'board')
        checked+=1
assert p['J1']['pins']['A4']=='USB_VBUS' and p['J4']['pins']['1']=='SYSTEM_5V'
assert b.FindNet('USB_VBUS').GetNetCode()!=b.FindNet('SYSTEM_5V').GetNetCode()
assert p['U8']['pins']['B1']=='USB_FUSED' and p['U8']['pins']['B2']=='USB_INPUT_PROTECTED'
assert p['U25']['pins']['2']=='TINY_USB_P' and p['U25']['pins']['3']=='HOST_USB_P'
assert p['U25']['pins']['5']=='HOST_USB_N' and p['U25']['pins']['6']=='TINY_USB_N'
assert p['J6']['pins']['2']=='TINY_3V3' and p['J5']['dnp']
assert p['J2']['pins']['2']=='CELL_N' and p['U9']['pins']['4']=='CELL_N'
assert not any('CP2102' in c['mpn'] or c['model'].startswith('ESP32') for c in parts)
for ref in ['U1','U2']:
    assert p[ref]['pins']['2']=='GND'
for ref in ['LED1','LED2','LED3','LED4']:
    assert 'LED' in p[ref]['pins']['2'] # pad 2 = ánodo en huella KiCad

def resistor(a,z):
    matches=[c for c in parts if c['model']=='R' and list(c['pins'].values())==[a,z]]
    assert len(matches)==1,(a,z)
    c=matches[0];s=c['value'].split()[0]
    value=float(s.rstrip('kM'))*(1e6 if s.endswith('M') else 1e3 if s.endswith('k') else 1)
    return c,value

def threshold(rail,sense):
    hi,rt=resistor(rail,sense);lo,rb=resistor(sense,'GND')
    # TPS3808G01: ±2% VIT, 3% histéresis máx., ±25 nA. Resistores independientes.
    # Incluye TCR hasta 100 °C respecto a 25 °C, envolviendo -40…+125 °C.
    tol=.001+(10e-6 if '10ppm' in hi['value'] else 25e-6)*100
    assert '0.1%' in hi['value'] and '0.1%' in lo['value']
    fall_min=.405*.98*(1+rt*(1-tol)/(rb*(1+tol)))-25e-9*rt*(1+tol)
    rise_max=.405*1.02*1.03*(1+rt*(1+tol)/(rb*(1-tol)))+25e-9*rt*(1+tol)
    return dict(resistors=[hi['reference'],lo['reference']],nominal_falling_v=.405*(1+rt/rb),min_falling_v=fall_min,max_rising_v=rise_max,resistor_total_tolerance=tol)
usb=threshold('USB_VBUS','VBUS_SENSE');tiny=threshold('TINY_3V3','TINY_SENSE')
assert usb['min_falling_v']>4.35 and usb['max_rising_v']<4.75,usb
assert tiny['max_rising_v']<3.3*.98,tiny
# JP1 cerrado: pull-up 10k ±1%, pull-down 100k ±1%, AON -2%, carga de entrada 15uA.
hold_min=(2.94/(10000*1.01)-15e-6)/(1/(10000*1.01)+1/(100000*.99))
assert hold_min>2.,hold_min
_,rhi=resistor('SYSTEM_5V','BOOST_FB');_,rlo=resistor('BOOST_FB','GND')
vout=.6*(1+rhi/rlo)
layers=collections.Counter(b.GetLayerName(t.GetLayer()) for t in b.GetTracks() if type(t)==k.PCB_TRACK)
assert layers['In1.Cu']==0,'Plano GND debe permanecer sin ruteo de señales'
lengths={net:sum(k.ToMM(t.GetLength()) for t in b.GetTracks() if type(t)==k.PCB_TRACK and t.GetNetname()==net) for net in ['HOST_USB_P','HOST_USB_N','TINY_USB_P','TINY_USB_N']}
truth=[dict(sys_ok=s,boot_window=w,hold=h,program=m,kill_safe=int(s and (w or h or m))) for s,w,h,m in itertools.product([0,1],repeat=4)]
report=dict(status='PASS_STATIC_CHECKS',connected_pin_checks=checked,schematic_components=len(parts),pcb_footprints=len(fps),populated_bom_components=sum(not c['dnp'] and c['model'] not in ['TP','SJ'] for c in parts),tracks_per_layer=dict(layers),vias=sum(type(t)==k.PCB_VIA for t in b.GetTracks()),board_mm=[45,40,k.ToMM(b.GetDesignSettings().GetBoardThickness())],usb_sensing=usb,tiny_sensing=tiny,program_hold_min_v=hold_min,boost_nominal_v=vout,usb_total_track_lengths_mm=lengths,kill_truth_table=truth,limits='No simulación de transitorios ni medición física. Longitudes suman ramas/testpoints; no son longitud de vuelo ni certificación USB. Margen de detección no incluye envejecimiento ni fugas de placa contaminada.')
(B/'review/static-checks.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps({q:report[q] for q in ['status','connected_pin_checks','schematic_components','populated_bom_components','tracks_per_layer','vias','usb_sensing','tiny_sensing']},indent=2))
