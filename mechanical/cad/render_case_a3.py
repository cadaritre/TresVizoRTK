"""Corte y despiece desde CAD A3, sin modificar documentos de la GUI."""
import json
import zipfile
import xml.etree.ElementTree as ET
from pathlib import Path
import FreeCAD as App
import Part
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import build_case_a3 as a3
from cad_raster import draw

HERE=Path(__file__).resolve().parent
OUT=HERE.parent/'exports'/'review-a3'
doc=App.openDocument(str(HERE/'TresVizo-case-A3.FCStd'))
section=App.openDocument(str(HERE/'TresVizo-case-A3-MOUNT-SECTION.FCStd'))
objects=[o for o in doc.Objects if o.isDerivedFrom('Part::Feature')]
colors={o.Name:np.array([float(v) for v in o.ColorRGB.split(',')]) for o in objects}
colors['PoleExample']=np.array([.10,.46,.80])

fig=plt.figure(figsize=(16,10),facecolor='#f3f5f5')
fig.text(.04,.943,'TresVizoRTK A3  /  base imprimible',fontsize=28,weight='bold',color='#20363c')
fig.text(.04,.904,'Base, retención y calce impresos · sólo tornillería comercial de metal',fontsize=15,color='#59696e')

left=fig.add_axes([.015,.32,.485,.51])
entries=[(o.Name,o.Shape) for o in section.Objects if o.isDerivedFrom('Part::Feature')]
# Ejemplo geométrico, separado de los archivos de fabricación.
pole=a3.a0.cyl(14,13,z=-13).fuse(a3.a0.cyl(15.875/2,19))
pole=pole.cut(a3.a0.box(80,80,70,-40,0,-20))
entries.append(('PoleExample',pole))
draw(left,entries,colors,elev=24,azim=64)
fig.text(.045,.853,'CORTE ENSAMBLADO',fontsize=14,weight='bold',color='#20363c')
fig.text(.045,.305,'Dorado: tuerca comercial 5/8″-11 UNC.',fontsize=13,color='#97691d',weight='bold')
fig.text(.045,.262,'Hexágono integral: impide girar a la tuerca.\nTapa y cuatro M4: impiden que salga del alojamiento.',fontsize=12,color='#20363c',linespacing=1.5)
fig.text(.045,.195,'Azul: ejemplo de espárrago de 19 mm, sin filetes.\nApoya sobre Z=0; la punta no toca el techo.',fontsize=11,color='#59696e',linespacing=1.5)

right=fig.add_axes([.53,.30,.43,.54])
exploded=[]
for name,dz in [('Base',0),('PoleNut',25),('NutShim',32),('UpperRetainer',37),('Frame',42)]:
    shape=doc.getObject(name).Shape.copy()
    if name=='Frame': shape=shape.common(a3.a0.box(80,80,9,-40,-40,21))
    shape.translate(App.Vector(0,0,dz)); exploded.append((name,shape))
draw(right,exploded,colors,elev=27,azim=65)
fig.text(.55,.853,'DESPIECE DEL ALOJAMIENTO',fontsize=14,weight='bold',color='#20363c')
fig.text(.55,.273,'De abajo hacia arriba:',fontsize=12,weight='bold',color='#20363c')
fig.text(.55,.222,'Base impresa → tuerca → calce impreso\n→ tapa impresa → piso del bastidor.',fontsize=12,color='#20363c',linespacing=1.5)
fig.text(.55,.166,'Profundidad libre para la punta: 26.5 mm.\nLos cuatro M3 horizontales unen cuerpo y base.',fontsize=11,color='#59696e',linespacing=1.5)

fig.text(.04,.10,'No requiere placas, casquillos ni calces metálicos a medida.',fontsize=16,weight='bold',color='#20363c')
fig.text(.04,.047,'PROTOTIPO · Geometría sin choques; resistencia, ajuste impreso y par de apriete pendientes de ensayo.',fontsize=11,color='#805137')
fig.savefig(str(OUT/'printed-mount-a3.png'),dpi=135,facecolor=fig.get_facecolor())
plt.close(fig)

step=Part.Shape(); step.read(str(OUT/'TresVizo-case-A3-with-RESERVES.step'))
missing={}
for name in ('TresVizo-case-A3.FCStd','TresVizo-case-A3-MOUNT-SECTION.FCStd'):
    with zipfile.ZipFile(HERE/name) as archive:
        xml=ET.fromstring(archive.read('GuiDocument.xml'))
        missing[name]=[e.attrib['file'] for e in xml.iter() if 'file' in e.attrib and e.attrib['file'] not in archive.namelist()]
check={'native_solids':len(objects),'native_valid':all(o.Shape.isValid() for o in objects),
       'step_solids':len(step.Solids),'step_valid':step.isValid(),
       'custom_metal_group_present':doc.getObject('Metal') is not None,
       'missing_native_presentation_assets':missing}
assert check['native_solids']==check['step_solids']==42 and check['native_valid'] and check['step_valid']
assert not check['custom_metal_group_present'] and not any(missing.values())
(OUT/'reopen-checks.json').write_text(json.dumps(check,indent=2)+'\n')
print(json.dumps(check))
