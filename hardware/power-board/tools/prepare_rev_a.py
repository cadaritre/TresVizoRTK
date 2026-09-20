"""Bibliotecas autocontenidas; huellas personalizadas según land patterns TI."""
from pathlib import Path
import json, shutil, re
B=Path(__file__).resolve().parents[1]/'rev-a';D=json.loads((B/'circuit.json').read_text())
SRC=Path('/Volumes/KiCad/KiCad/KiCad.app/Contents/SharedSupport/footprints')
libs=set()
for p in D['components']:
 lib,name=p['footprint'].split(':');libs.add(lib);dest=B/'lib'/(lib+'.pretty');dest.mkdir(parents=True,exist_ok=True)
 if lib!='Power':shutil.copy2(SRC/(lib+'.pretty')/(name+'.kicad_mod'),dest/(name+'.kicad_mod'))
usb=B/'lib/Connector_USB.pretty/USB_C_Receptacle_HRO_TYPE-C-31-M-12.kicad_mod'
u=usb.read_text()
def clip_silk(m):
 t=m.group(0)
 if '(layer "F.SilkS")' in t and any(v in t for v in ['(start -4.7 2)','(start 4.7 2)','(start -4.7 3.9)']):return ''
 return t
usb.write_text(re.sub(r'\n\t\(fp_line\n.*?\n\t\)',clip_silk,u,flags=re.S))
def custom(name,w,h,pads,desc):
 s=f'(footprint "{name}" (version 20240108) (generator "pcbnew") (layer "F.Cu") (descr "{desc}") (attr smd)\n'
 s+=f'(property "Reference" "REF**" (at 0 {-h/2-1} 0) (layer "F.SilkS") (effects (font (size 0.6 0.6) (thickness 0.12))))\n'
 s+=f'(property "Value" "{name}" (at 0 {h/2+1} 0) (layer "F.Fab") (effects (font (size 0.6 0.6) (thickness 0.12))))\n'
 for layer,margin in [('F.Fab',0),('F.CrtYd',.25)]:s+=f'(fp_rect (start {-w/2-margin} {-h/2-margin}) (end {w/2+margin} {h/2+margin}) (stroke (width 0.05) (type default)) (fill none) (layer "{layer}"))\n'
 s+=f'(fp_circle (center {-w/2-.13} {-h/2-.13}) (end {-w/2-.06} {-h/2-.13}) (stroke (width .1) (type default)) (fill none) (layer "F.SilkS"))\n'
 for num,x,y,pw,ph,shape in pads:s+=f'(pad "{num}" smd {shape} (at {x} {y}) (size {pw} {ph}) (layers "F.Cu" "F.Paste" "F.Mask") '+('(roundrect_rratio 0.15)' if shape=='roundrect' else '')+')\n'
 (B/'lib/Power.pretty'/(name+'.kicad_mod')).write_text(s+')\n')
custom('TPS22950_YBH',.706,1.106,[(r+str(c+1),-.2+c*.4,-.4+i*.4,.2,.2,'circle') for i,r in enumerate('ABC') for c in range(2)],'TI YBH0006 DSBGA, pitch 0.4, land diameter 0.20 mm; TPS22950 datasheet')
custom('CSD13202Q2',2,2,[(1,-.975,-.65,.45,.3,'roundrect'),(2,-.975,0,.45,.3,'roundrect'),(3,-.975,.65,.45,.3,'roundrect'),(4,.975,.65,.45,.3,'roundrect'),(5,.975,0,.45,.3,'roundrect'),(6,.975,-.65,.45,.3,'roundrect'),(7,.095,.65,.75,.3,'roundrect'),(8,0,-.325,1,.95,'roundrect')],'TI DQK0006A SON2x2 land pattern; exposed contacts 7 SOURCE and 8 DRAIN')
(B/'fp-lib-table').write_text('(fp_lib_table\n'+''.join(f'(lib (name "{n}") (type "KiCad") (uri "${{KIPRJMOD}}/lib/{n}.pretty") (options "") (descr "Local KiCad 10 footprints / manufacturer patterns"))\n' for n in sorted(libs))+')\n')
(B/'lib/README.md').write_text('Huellas estándar de KiCad 10.0.6, bibliotecas KiCad bajo CC-BY-SA 4.0 con excepción de uso en placas. https://www.kicad.org/libraries/license/\n\nPower.pretty contiene land patterns transcritos de los datasheets TI CSD13202Q2 y TPS22950. Verificación física/ensamble pendiente.\n')
print('Local libraries ready:',len(libs))
