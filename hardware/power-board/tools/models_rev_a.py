"""Modelos 3D locales; envolventes máximas donde KiCad no suministra modelo."""
from pathlib import Path
import json,shutil,re
import FreeCAD as A,Part
B=Path(__file__).resolve().parents[1]/'rev-a';root=B/'lib/3dmodels';root.mkdir(parents=True,exist_ok=True)
missing={
 'Package_DFN_QFN.3dshapes/VQFN-16-1EP_3x3mm_P0.5mm_EP1.68x1.68mm.step':(3.1,3.1,1.0),
 'Package_DFN_QFN.3dshapes/TDFN-8-1EP_2x2mm_P0.5mm_EP0.8x1.2mm.step':(2.1,2.1,.8),
 'Package_DFN_QFN.3dshapes/Texas_X2QFN-12_1.6x1.6mm_P0.4mm.step':(1.7,1.7,.5),
 'Power.3dshapes/CSD13202Q2.step':(2.1,2.1,.8),
 'Power.3dshapes/TPS22950_YBH.step':(.76,1.16,.45),
}
for name,(w,h,t) in missing.items():
 out=root/name;out.parent.mkdir(parents=True,exist_ok=True);shape=Part.makeBox(w,h,t,A.Vector(-w/2,-h/2,0));shape.exportStep(str(out))
# PH horizontal connector: conservative housing envelope and documented mating clearance in JSON.
name='Connector_JST.3dshapes/JST_PH_S2B-PH-SM4-TB_1x02-1MP_P2.00mm_Horizontal.step';out=root/name;out.parent.mkdir(parents=True,exist_ok=True)
Part.makeBox(9.8,7.6,3.4,A.Vector(-4.9,-4.85,0)).exportStep(str(out));missing[name]=(9.8,7.6,3.4)
# HRO model provided in KiCad's openair-max demo; align XY center to standard footprint.
u=Part.read('/Volumes/KiCad/demos/openair-max/Libraries/HRO_TYPE-C-31-M-12.step');u.translate(A.Vector(-4.475,-3.95,0));out=root/'Connector_USB.3dshapes/USB_C_Receptacle_HRO_TYPE-C-31-M-12.step';out.parent.mkdir(parents=True,exist_ok=True);u.exportStep(str(out))
shutil.copy2('/Volumes/KiCad/demos/openair-max/LICENSE.txt',root/'USB_HRO_MODEL_LICENSE.txt')
for f in (B/'lib').glob('*.pretty/*.kicad_mod'):
 s=f.read_text().replace('${KICAD10_3DMODEL_DIR}','${KIPRJMOD}/lib/3dmodels')
 if f.parent.name=='Power.pretty':
  model='${KIPRJMOD}/lib/3dmodels/Power.3dshapes/'+f.stem+'.step'
  pos=s.rfind(')');s=s[:pos]+f'(model "{model}" (offset (xyz 0 0 0)) (scale (xyz 1 1 1)) (rotate (xyz 0 0 0)))\n'+s[pos:]
 f.write_text(s)
(root/'MODEL_SOURCES.md').write_text('Modelos estándar: KiCad 10.0.6 / kicad-packages3D, licencia CC-BY-SA 4.0 con excepción de uso en placas.\nhttps://www.kicad.org/libraries/license/\n\nUSB HRO: archivo del demo oficial openair-max, licencia adjunta; traslación de (-4.475, -3.95, 0) mm para el footprint estándar. Verificar posición final con el conector adquirido.\n\nEnvolventes conservadoras, sin geometría de contactos, para: '+', '.join(missing)+'\nNo son modelos del fabricante; sirven para reservar volumen. La altura y posición real de cables y FPC siguen requiriendo verificación física.\n')
print('Local 3D models ready; conservative envelopes:',len(missing))
