"""Materializa el borrador eléctrico D0; no produce archivos de fabricación."""
from pathlib import Path
from uuid import uuid5, NAMESPACE_URL
import json
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'kicad'
def uid(s): return str(uuid5(NAMESPACE_URL, 'tresvizo-power-d0/'+s))
def q(s): return json.dumps(str(s),ensure_ascii=False)
def fx(size=1.27): return f'(effects (font (size {size} {size})))'
libs={}; items=[]; components=[]
def symbol(name,pins):
    # pins: number, name, electrical type. All coordinate values are mm.
    n=(len(pins)+1)//2; h=max(5.08,(n+1)*2.54)
    p=[]; coords={}
    for i,(num,label,typ) in enumerate(pins):
        side=0 if i<n else 1; row=i if side==0 else i-n
        x=-15.24 if side==0 else 15.24; y=(n-1)*2.54-row*5.08
        coords[str(num)]=(x,y,side)
        p.append(f'(pin {typ} line (at {x} {y} {0 if side==0 else 180}) (length 2.54) (name {q(label)} {fx(1.016)}) (number {q(num)} {fx(1.016)}))')
    libs[name]=f'''(symbol "PowerDraft:{name}" (pin_names (offset 1.016)) (in_bom yes) (on_board yes)
(property "Reference" "U" (at 0 {h+2.54} 0) {fx()})
(property "Value" "{name}" (at 0 {-h-2.54} 0) {fx()})
(symbol "{name}_0_1" (rectangle (start -12.7 {h}) (end 12.7 {-h}) (stroke (width 0.254) (type default)) (fill (type background))))
(symbol "{name}_1_1" {''.join(p)}))'''
    return coords,h
models={}
def define(name, pins): models[name]=symbol(name,pins)
def note(text,x,y,size=1.27): items.append(f'(text {q(text)} (at {x} {y} 0) {fx(size)} (uuid "{uid(text+str(x)+str(y))}"))')
def label(net,x,y,side,key):
    # place global labels at wire ends, local labels intentionally shared on this single sheet
    angle=0
    items.append(f'(label {q(net)} (at {x} {y} {angle}) (effects (font (size 1.016 1.016)) (justify {"right" if side==0 else "left"} bottom)) (uuid "{uid(key+"label")}"))')
def add(ref,name,x,y,nets,value=None,footprint='',datasheet=''):
    x=round(round(x/1.27)*1.27,4); y=round(round(y/1.27)*1.27,4)
    coords,h=models[name]; value=value or name; key=uid(ref)
    items.append(f'''(symbol (lib_id "PowerDraft:{name}") (at {x} {y} 0) (unit 1) (in_bom yes) (on_board yes) (dnp no) (uuid "{key}")
(property "Reference" "{ref}" (at {x} {y-h-4} 0) {fx()})
(property "Value" {q(value)} (at {x} {y+h+3} 0) {fx(1.016)})
(property "Footprint" {q(footprint)} (at {x} {y} 0) (effects (font (size 1.27 1.27)) hide))
(property "Datasheet" {q(datasheet)} (at {x} {y} 0) (effects (font (size 1.27 1.27)) hide))
{''.join(f'(pin {q(p)} (uuid "{uid(ref+"pin"+p)}"))' for p in coords)}
(instances (project "power-board" (path "/{uid('root')}" (reference "{ref}") (unit 1)))))''')
    for pin,(px,py,side) in coords.items():
        net=nets.get(pin); ax=round(x+px,4); ay=round(y-py,4); ex=round(ax+(-5.08 if side==0 else 5.08),4)
        if net is None:
            items.append(f'(no_connect (at {ax} {ay}) (uuid "{uid(ref+pin+"nc")}"))')
        else:
            items.append(f'(wire (pts (xy {ax} {ay}) (xy {ex} {ay})) (stroke (width 0) (type default)) (uuid "{uid(ref+pin+"wire")}"))')
            label(net,ex,ay,side,ref+pin)
    components.append(dict(reference=ref,value=value,footprint=footprint,datasheet=datasheet,pins=nets))
# Pin mappings checked against the manufacturer tables cited on each component.
define('BQ24074RGT',[(str(i),n,t) for i,n,t in [(1,'TS','input'),(2,'BAT','power_out'),(3,'BAT','passive'),(4,'CE_N','input'),(5,'EN2','input'),(6,'EN1','input'),(7,'PGOOD_N','open_collector'),(8,'VSS','power_in'),(9,'CHG_N','open_collector'),(10,'OUT','power_out'),(11,'OUT','passive'),(12,'ILIM','input'),(13,'IN','power_in'),(14,'TMR','passive'),(15,'ITERM','passive'),(16,'ISET','passive'),(17,'EP','power_in')]])
define('TPS61023',[(str(i),n,t) for i,n,t in [(1,'FB','input'),(2,'EN','input'),(3,'VIN','power_in'),(4,'GND','power_in'),(5,'SW','passive'),(6,'VOUT','power_out')]])
define('LTC2954ITS8-1',[(str(i),n,t) for i,n,t in [(1,'VIN','power_in'),(2,'PB_N','input'),(3,'ONT','passive'),(4,'GND','power_in'),(5,'INT_N','open_collector'),(6,'EN','open_collector'),(7,'PDT','passive'),(8,'KILL','input')]])
define('MAX17048G',[(str(i),n,t) for i,n,t in [(1,'CTG','power_in'),(2,'CELL','input'),(3,'VDD','power_in'),(4,'GND','power_in'),(5,'ALRT_N','open_collector'),(6,'QSTRT','input'),(7,'SCL','input'),(8,'SDA','bidirectional'),(9,'EP','power_in')]])
define('TS3USB31E',[(str(i),n,t) for i,n,t in [(1,'OE','input'),(2,'HSD+','bidirectional'),(3,'D+','bidirectional'),(4,'GND','power_in'),(5,'D-','bidirectional'),(6,'HSD-','bidirectional'),(7,'NC','no_connect'),(8,'VCC','power_in')]])
define('USBLC6-2SC6',[(str(i),n,'passive') for i,n in [(1,'IO1'),(2,'GND'),(3,'IO2'),(4,'IO2'),(5,'VBUS'),(6,'IO1')]])
# Simple two-terminal symbols use compact conventional shapes.
for name in ['R','C','L','SW']:
    define(name,[('1','~','passive'),('2','~','passive')])
    coords={'1':(-5.08,0,0),'2':(5.08,0,1)}; models[name]=(coords,2.54)
    shape='(rectangle (start -2.54 1.016) (end 2.54 -1.016) (stroke (width 0.254) (type default)) (fill (type none)))'
    if name=='C': shape=''.join(f'(polyline (pts (xy {x} -2.032) (xy {x} 2.032)) (stroke (width 0.254) (type default)) (fill (type none)))' for x in [-.635,.635])
    if name=='SW': shape='(polyline (pts (xy -2.54 0) (xy 2.54 2.032)) (stroke (width 0.254) (type default)) (fill (type none)))'
    length=4.445 if name=='C' else 2.54
    libs[name]=f'''(symbol "PowerDraft:{name}" (pin_names hide) (pin_numbers hide) (in_bom yes) (on_board yes)
(property "Reference" "{name}" (at 0 3.81 0) {fx()}) (property "Value" "{name}" (at 0 -3.81 0) {fx()})
(symbol "{name}_0_1" {shape}) (symbol "{name}_1_1"
(pin passive line (at -5.08 0 0) (length {length}) (name "~" {fx()}) (number "1" {fx()}))
(pin passive line (at 5.08 0 180) (length {length}) (name "~" {fx()}) (number "2" {fx()}))))'''
def passive(ref,value,a,b,x,y):
    typ=ref[0] if ref[0]!='S' else 'SW'
    fp=''  # No fijar encapsulado antes de verificar MPN y DC bias.
    add(ref,typ,x,y,{'1':a,'2':b},value,fp)
note('TresVizo Power Board D0 — BORRADOR ELÉCTRICO EN DESARROLLO',285,13,2.54)
note('Componentes y redes reales; interfaces pendientes indicadas. No fabricar ni conectar batería con este borrador.',285,21,1.524)
note('1. CARGADOR + POWER-PATH',98,33,1.778)
add('U1','BQ24074RGT',95,75,{str(k):v for k,v in {1:'BAT_NTC',2:'PACK_PROTECTED',3:'PACK_PROTECTED',4:'CHARGE_DISABLE',5:'USB_EN2',6:'USB_EN1',7:'USB_PGOOD_N',8:'GND',9:'CHG_N',10:'SYSTEM_POWER',11:'SYSTEM_POWER',12:'CHG_ILIM',13:'USB_INPUT_PROTECTED',14:None,15:None,16:'CHG_ISET',17:'GND'}.items()},datasheet='https://www.ti.com/lit/ds/symlink/bq24074.pdf')
for row,data in enumerate([('C1','1u 16V X7R','USB_INPUT_PROTECTED','GND'),('C2','10u 10V X7R','PACK_PROTECTED','GND'),('C3','22u 10V X7R','SYSTEM_POWER','GND'),('R1','1.78k 1%','CHG_ISET','GND'),('R2','3.32k 1%','CHG_ILIM','GND'),('R3','100k','USB_EN1','GND'),('R4','100k','USB_EN2','GND'),('R5','47k','SYSTEM_POWER','CHARGE_DISABLE')]):
    passive(*data,95 if row<4 else 210,140+(row%4)*17.78)
note('Icharge nominal 500mA; ILIM nominal 467mA en modo externo.\nTMR/ITERM abiertos: valores internos. TS: NTC externo 10k.\nCE alto por defecto: habilitar sólo con política/protección terminadas.',155,219)
note('2. BOOST 5V / CARGAS EXTERNAS',345,33,1.778)
add('U2','TPS61023',355,65,{'1':'BOOST_FB','2':'BOOST_ENABLE_SAFE','3':'SYSTEM_POWER','4':'GND','5':'BOOST_SW','6':'SYSTEM_5V'},datasheet='https://www.ti.com/lit/ds/symlink/tps61023.pdf')
for row,data in enumerate([('L1','1uH Isat/DCR TBD','SYSTEM_POWER','BOOST_SW'),('C4','10u 10V X7R','SYSTEM_POWER','GND'),('C5','22u 10V X7R','SYSTEM_5V','GND'),('C6','22u 10V X7R','SYSTEM_5V','GND'),('R6','732k 0.1%','SYSTEM_5V','BOOST_FB'),('R7','100k 0.1%','BOOST_FB','GND'),('R8','100k','BOOST_ENABLE_SAFE','GND')]):
    passive(*data,335 if row<4 else 475,110+(row%4)*17.78)
note('Vout nominal = 0.6*(1+732/100) = 4.992V.\nNo conectar EN directo a HOLD: falta compuerta UVLO + latch.\n5V → Tiny / carrier UM980. Salida GNSS secuenciada pendiente.\nUSB_VBUS y SYSTEM_5V son redes distintas.',405,196)
note('3. PULSADOR / APAGADO INDEPENDIENTE',100,243,1.778)
add('U3','LTC2954ITS8-1',95,277,{'1':'SYSTEM_POWER','2':'BUTTON_N','3':'LATCH_ONT','4':'GND','5':'POWER_REQUEST_RAW_N','6':'LATCH_ENABLE','7':'LATCH_PDT','8':'KILL_SAFE'},datasheet='https://www.analog.com/media/en/technical-documentation/data-sheets/2954fb.pdf')
for row,data in enumerate([('C7','100n 10V','SYSTEM_POWER','GND'),('C8','47n 10V','LATCH_ONT','GND'),('C9','1u 10V timing','LATCH_PDT','GND'),('C10','390n 10V timing','LATCH_PDT','GND'),('R9','100k','SYSTEM_POWER','LATCH_ENABLE'),('R10','100k','KILL_SAFE','GND'),('SW1','Pulsador NO','BUTTON_N','GND')]):
    passive(*data,75 if row<4 else 195,321+(row%4)*17.78)
note('PDT 1.39uF ≈ 8.97s nominal; tolerancias/ensayo pendientes.\nONT 47nF ≈ 333ms nominal. Falta asistencia de arranque,\nPROGRAM_MODE y lógica KILL/UVLO. EN no puenteado.',150,399)
note('4. FUEL GAUGE EN PACK PROTEGIDO',355,241,1.778)
add('U4','MAX17048G',355,282,{'1':'GND','2':'PACK_PROTECTED','3':'PACK_PROTECTED','4':'GND','5':'GAUGE_ALERT_RAW_N','6':'GND','7':'GAUGE_SCL_RAW','8':'GAUGE_SDA_RAW','9':'GND'},datasheet='https://www.analog.com/media/en/technical-documentation/data-sheets/MAX17048-MAX17049.pdf')
passive('C11','100n 10V','PACK_PROTECTED','GND',355,333)
note('SDA/SCL/ALERT internos: falta aislamiento hacia Tiny.\nEl gauge no protege la batería. CELL conectado a PACK.\nNo unir RAW a pines de la Tiny sin cerrar dominios OFF.',387,359)
# Separate USB sheet as standalone readable schematic, with unique references but same root project.
def finish(path,title):
    text=f'''(kicad_sch (version 20250114) (generator "eeschema") (uuid "{uid('root')}") (paper "A2")
(title_block (title {q(title)}) (date "2026-09-20") (rev "D0 — NO FABRICAR"))
(lib_symbols {''.join(libs.values())}) {''.join(items)} (sheet_instances (path "/" (page "1"))))'''
    path.write_text(text)
finish(OUT/'power-board.kicad_sch','Power Board — núcleo de alimentación')
items=[]
note('TresVizo Power Board D0 — USB NATIVO / Tiny externa',290,20,2.54)
note('Borrador parcial: falta detector VBUS, política USB y conector FPC físico. CP2102N no incluido.',290,29,1.524)
add('U5','TS3USB31E',310,100,{'1':'USB_DISCONNECT','2':'TINY_USB_P','3':'HOST_USB_P','4':'GND','5':'HOST_USB_N','6':'TINY_USB_N','7':None,'8':'TINY_3V3_REF'},datasheet='https://www.ti.com/lit/ds/symlink/ts3usb31e.pdf')
add('D1','USBLC6-2SC6',110,100,{'1':'HOST_USB_P','2':'GND','3':'HOST_USB_N','4':'HOST_USB_N','5':'USB_VBUS','6':'HOST_USB_P'},datasheet='https://www.st.com/resource/en/datasheet/usblc6-2.pdf')
passive('R11','47k','TINY_3V3_REF','USB_DISCONNECT',310,152)
passive('C12','100n 10V','TINY_3V3_REF','GND',310,179)
passive('R12','5.1k 1%','USB_CC1','GND',110,152)
passive('R13','5.1k 1%','USB_CC2','GND',110,179)
note('Receptáculo USB-C USB2 (huella pendiente):\nA6/B6 → HOST_USB_P; A7/B7 → HOST_USB_N\nA4/A9/B4/B9 → USB_VBUS\nA1/A12/B1/B12 → GND\nA5 → USB_CC1; B5 → USB_CC2\nSBU abiertos; shield/ESD de VBUS y CC por cerrar.',112,245)
note('D± del switch al host; HSD± a Tiny.\nVCC desde 3V3 de Tiny (auxiliar, no FPC supuesto).\nOE alto desconecta. Ioff especificado en D± al faltar VCC.\nLa lógica pendiente sólo bajará OE con VBUS válido\ny Tiny power-good. Nunca habilitar desde firmware solo.',345,245)
note('INTERFAZ FPC — SÓLO NOMBRES DE RED, SIN NÚMEROS INVENTADOS\nTINY_USB_P / TINY_USB_N / SYSTEM_5V / GND / TINY_BOOT / TINY_RUN\nNo hay footprint ni pads FPC asignados.\nUSB_VBUS sensing se toma del receptáculo, nunca de SYSTEM_5V.',290,310,1.524)
note('ENTRADA POTENCIA PENDIENTE\nUSB_VBUS → protección → USB_INPUT_PROTECTED (hoja alimentación).\nLas redes no están puenteadas en D0. Rd sólo permite attach;\nno implica autorización de 500mA, 1.5A ni 3A.\nFaltan corriente total, suspend y arranque sin batería.',290,367)
items=[item.replace('(project "power-board"', '(project "usb-native"') for item in items]
finish(OUT/'usb-native.kicad_sch','Power Board — USB nativo, interfaces parciales')
(OUT/'power-board.kicad_pro').write_text(json.dumps({'meta':{'filename':'power-board.kicad_pro','version':1}},indent=2)+'\n')
(OUT/'usb-native.kicad_pro').write_text(json.dumps({'meta':{'filename':'usb-native.kicad_pro','version':1}},indent=2)+'\n')
(ROOT/'draft-netlist.json').write_text(json.dumps({'revision':'D0','status':'partial_not_for_fabrication','components':components},indent=2)+'\n')
# A real PCB document containing ONLY a provisional outline, no placement claim.
(OUT/'power-board.kicad_pcb').write_text('''(kicad_pcb (version 20241229) (generator "pcbnew")
(general (thickness 1.6)) (paper "A4")
(layers (0 "F.Cu" signal) (2 "In1.Cu" power) (4 "In2.Cu" power) (31 "B.Cu" signal) (44 "Edge.Cuts" user) (49 "F.Fab" user))
(setup (pad_to_mask_clearance 0))
(gr_rect (start -17.5 -15) (end 17.5 15) (stroke (width 0.05) (type default)) (fill none) (layer "Edge.Cuts"))
(gr_text "D0 35x30 - OUTLINE ONLY" (at 0 0) (layer "F.Fab") (effects (font (size 1 1) (thickness 0.15)))))\n''')
(OUT/'PowerDraft.kicad_sym').write_text('(kicad_symbol_lib (version 20241209) (generator "kicad_symbol_editor") '+''.join(libs.values()).replace('PowerDraft:','')+')\n')
(OUT/'sym-lib-table').write_text('(sym_lib_table (lib (name "PowerDraft") (type "KiCad") (uri "${KIPRJMOD}/PowerDraft.kicad_sym") (options "") (descr "Símbolos D0; mapeo de fabricante, huellas pendientes")))\n')
print(f'{len(components)} componentes; esquemas y contorno provisional escritos en {OUT}')
