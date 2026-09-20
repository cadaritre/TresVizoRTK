"""Esquema jerárquico editable y biblioteca local a partir del modelo Rev A."""
from pathlib import Path
from uuid import uuid5,NAMESPACE_URL
import json,math,collections
BASE=Path(__file__).resolve().parents[1]/'rev-a'
data=json.loads((BASE/'circuit.json').read_text());parts=data['components'];models=data['models']
def uid(x):return str(uuid5(NAMESPACE_URL,'tresvizo-power-reva/'+x))
def q(x):return json.dumps(str(x),ensure_ascii=False)
def f(size=1.0):return f'(effects (font (size {size} {size})))'
def grid(x):return round(round(x/1.27)*1.27,4)
def box(x,y,w,h):return f'(rectangle (start {x} {y}) (end {x+w} {y+h}) (stroke (width 0.254) (type default)) (fill (type background)))'
def poly(points):return '(polyline (pts '+''.join(f'(xy {x} {y})' for x,y in points)+') (stroke (width 0.254) (type default)) (fill (type none)))'
lib=[];coord={};half={}
for name,m in models.items():
 n=len(m['pins']);simple=name in ['R','C','L','D','LED','F','SJ','SW'];np=math.ceil(n/2);h=max(3.81,np*1.905+1.27);half[name]=h;xy={};pg=[]
 for i,(pn,(label,typ)) in enumerate(m['pins'].items()):
  side=0 if i<np else 1;row=i if side==0 else i-np
  x=(-5.08 if side==0 else 5.08) if simple else (-15.24 if side==0 else 15.24)
  y=0 if simple else grid((np-1)*1.905-row*3.81)
  if n==1:x=-5.08;y=0
  xy[pn]=(x,y,side)
  pg.append(f'(pin {typ} line (at {x} {y} {0 if side==0 else 180}) (length {4.445 if name=="C" else 2.54}) (name {q(label)} {f()}) (number {q(pn)} {f()}))')
 shape=box(-12.7,h,25.4,-2*h)
 if simple:
  half[name]=2.54;shape=box(-2.54,1.016,5.08,-2.032)
  if name=='C':shape=poly([(-.635,-2.032),(-.635,2.032)])+poly([(.635,-2.032),(.635,2.032)])
  if name in ['D','LED']:shape=poly([(2.54,-1.5),(2.54,1.5),(-2.54,0),(2.54,-1.5)])+poly([(-2.54,-1.5),(-2.54,1.5)])
  if name in ['SW','SJ']:shape=poly([(-2.54,0),(2.54,1.5)])
 if name=='TP':shape='(circle (center -2.54 0) (radius 1.016) (stroke (width 0.254) (type default)) (fill (type none)))'
 coord[name]=xy
 lib.append(f'''(symbol "Power:{name}" (pin_names (offset 0.508){' hide' if simple else ''}) {'(pin_numbers hide)' if simple else ''} (in_bom yes) (on_board yes)
(property "Reference" "U" (at 0 {h+2.54} 0) {f()}) (property "Value" "{name}" (at 0 {-h-2.54} 0) {f()})
(symbol "{name}_0_1" {shape}) (symbol "{name}_1_1" {''.join(pg)}))''')
# Power flags only identify supplies supplied through external connectors/fuses.
lib.append('(symbol "Power:PWR_FLAG" (power) (pin_names hide) (pin_numbers hide) (in_bom no) (on_board no) (property "Reference" "#FLG" (at 0 0 0) (effects (font (size 1 1)) hide)) (property "Value" "PWR_FLAG" (at 0 2 0) (effects (font (size 1 1)))) (symbol "PWR_FLAG_1_1" (pin power_out line (at 0 0 90) (length 0) (name "pwr" (effects (font (size 1 1)))) (number "1" (effects (font (size 1 1)))))))')
libstr=''.join(lib)
(BASE/'Power.kicad_sym').write_text('(kicad_symbol_lib (version 20241209) (generator "kicad_symbol_editor") '+libstr.replace('Power:','')+')\n')
(BASE/'sym-lib-table').write_text('(sym_lib_table (lib (name "Power") (type "KiCad") (uri "${KIPRJMOD}/Power.kicad_sym") (options "") (descr "Power Board Rev A")))\n')
root=uid('root');sections=list(dict.fromkeys(p['section'] for p in parts));paths={s:'/'.join(['',root,uid('sheet/'+s)]) for s in sections}
for s in sections:
 group=[p for p in parts if p['section']==s];items=[]
 title=s[3:].replace('_',' ').upper()
 items.append(f'(text {q("TresVizo Power Board — Rev A / "+title)} (at 290 16 0) {f(2.54)} (uuid "{uid(s+"title")}"))')
 items.append(f'(text {q("PROTOTIPO — J5 FPC candidato DNP hasta cotejar el cable; ensayos de banco pendientes")} (at 290 25 0) {f(1.524)} (uuid "{uid(s+"warning")}"))')
 for i,p in enumerate(group):
  x=grid(48+(i%6)*90);y=grid(64+(i//6)*58);name=p['model'];ref=p['reference'];h=half[name]
  props=f'(property "Reference" {q(ref)} (at {x} {y-h-3.81} 0) {f(1.27)}) (property "Value" {q(p["value"])} (at {x} {y+h+3.81} 0) {f(1.016)})'
  for k,v in [('Footprint',p['footprint']),('Datasheet',p['datasheet']),('MPN',p['mpn']),('Design_Note',p['reason'])]:props+=f'(property {q(k)} {q(v)} (at {x} {y} 0) (effects (font (size 1 1)) hide))'
  items.append(f'(symbol (lib_id "Power:{name}") (at {x} {y} 0) (unit 1) (in_bom {"no" if name in ["TP","SJ"] else "yes"}) (on_board yes) (dnp {"yes" if p["dnp"] else "no"}) (uuid "{uid(ref)}") {props} '+''.join(f'(pin {q(pn)} (uuid "{uid(ref+pn)}"))' for pn in p['pins'])+f'(instances (project "power-board" (path "{paths[s]}" (reference {q(ref)}) (unit 1)))))')
  for pn,net in p['pins'].items():
   px,py,side=coord[name][pn];ax=round(x+px,4);ay=round(y-py,4);ex=round(ax+(-2.54 if side==0 else 2.54),4)
   if net is None:items.append(f'(no_connect (at {ax} {ay}) (uuid "{uid(ref+pn+"nc")}"))');continue
   items.append(f'(wire (pts (xy {ax} {ay}) (xy {ex} {ay})) (stroke (width 0) (type default)) (uuid "{uid(ref+pn+"wire")}"))')
   # Global labels truly connect the seven sheets.
   ang=0 if side==0 else 180
   items.append(f'(global_label {q(net)} (shape bidirectional) (at {ex} {ay} {ang}) (effects (font (size 0.889 0.889)) (justify {"right" if side==0 else "left"})) (uuid "{uid(ref+pn+"label")}") (property "Intersheetrefs" "${{INTERSHEET_REFS}}" (at {ex} {ay} {ang}) (effects (font (size 1 1)) hide)))')
 text=f'(kicad_sch (version 20250114) (generator "eeschema") (uuid "{uid(s)}") (paper "A2") (title_block (title {q(title)}) (date "2026-09-20") (rev "A-PROTOTYPE")) (lib_symbols {libstr}) {"".join(items)})'
 (BASE/(s+'.kicad_sch')).write_text(text+'\n')
items=[]
descriptions={
 '01_usb_power':'USB-C / detección CC / bloqueo inverso\\nTUSB320 + TPS22950',
 '02_battery_charger':'LiPo 1S / NTC / protección / power-path\\nBQ24074 + BQ29700',
 '03_power_control':'Botón / HOLD / ventana de arranque / UVLO\\nLTC2954-1 + supervisores',
 '04_5v_outputs':'Boost 4.992 V / alimentación externa\\nTPS61023',
 '05_usb_native':'USB nativo / ESD / VBUS sensing / FPC DNP\\nTS3USB31E + TPS3808',
 '06_gauge':'Voltaje y SOC / aislamiento de I2C\\nMAX17048 + TMUX1511',
 '07_interfaces':'Conectores / señales / LEDs / testpoints\\nESP32 y GNSS externos',
}
for i,s in enumerate(sections):
 x=grid(20+(i%3)*90);y=grid(50+(i//3)*35)
 items.append(f'''(sheet (at {x} {y}) (size 76.2 22.86) (stroke (width 0.254) (type default)) (fill (color 0 0 0 0)) (uuid "{uid('sheet/'+s)}")
(property "Sheetname" {q(s)} (at {x} {y-1.27} 0) (effects (font (size 1.27 1.27)) (justify left bottom)))
(property "Sheetfile" {q(s+'.kicad_sch')} (at {x} {y+24.13} 0) (effects (font (size 1 1)) (justify left top)))
(instances (project "power-board" (path "/{root}" (page "{i+2}")))))''')
 description=descriptions[s].replace('\\n','\n')
 items.append(f'(text {q(description)} (at {x+38.1} {y+11.43} 0) {f(1.27)} (uuid "{uid(s+"description")}"))')
for i,net in enumerate(['USB_VBUS','USB_FUSED','CELL_P','CELL_N','PROT_BAT','GND','PACK_P','TINY_3V3']):
 x=grid(30+(i%4)*36);y=grid(170+(i//4)*17);ref='#FLG'+str(i+1)
 items.append(f'(symbol (lib_id "Power:PWR_FLAG") (at {x} {y} 0) (unit 1) (in_bom no) (on_board no) (dnp no) (uuid "{uid(ref)}") (property "Reference" {q(ref)} (at {x} {y} 0) (effects (font (size 1 1)) hide)) (property "Value" "PWR_FLAG" (at {x} {y-3} 0) {f()}) (instances (project "power-board" (path "/{root}" (reference {q(ref)}) (unit 1)))))')
 items.append(f'(global_label {q(net)} (shape input) (at {x} {y} 0) (effects (font (size 1 1)) (justify right)) (uuid "{uid(ref+"label")}") (property "Intersheetrefs" "${{INTERSHEET_REFS}}" (at {x} {y} 0) (effects (font (size 1 1)) hide)))')
items.append(f'(text "TresVizo — Power Board Rev A\\nUSB nativo / LiPo 1S / módulos externos" (at 148 20 0) {f(2.54)} (uuid "{uid("main-title")}"))')
items.append(f'(text "Fuentes externas: USB-C, batería y referencia 3V3 de Tiny. Flags tras fusibles representan continuidad de potencia.\\nJ5: huella candidata NO APROBADA para el cable de la unidad. No es liberación de fabricación." (at 148 35 0) {f(1.016)} (uuid "{uid("main-note")}"))')
(BASE/'power-board.kicad_sch').write_text(f'(kicad_sch (version 20250114) (generator "eeschema") (uuid "{root}") (paper "A4") (title_block (title "Power Board Rev A") (date "2026-09-20") (rev "A-PROTOTYPE")) (lib_symbols {libstr}) {"".join(items)} (sheet_instances (path "/" (page "1"))))\n')
# Never erase layout settings on regeneration.
project=BASE/'power-board.kicad_pro'
if not project.exists():project.write_text(json.dumps({'meta':{'filename':project.name,'version':1}},indent=2)+'\n')
(BASE/'.gitignore').write_text('*.kicad_prl\n~*.lck\n*-backups/\n')
print('Wrote',len(sections)+1,'hierarchical schematic sheets')
