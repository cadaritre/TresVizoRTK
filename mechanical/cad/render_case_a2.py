"""Muestra el paso real y la ruta reservada del coaxial A2."""
import json
from pathlib import Path
import FreeCAD as App
import Part
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from cad_raster import draw

HERE=Path(__file__).resolve().parent
OUT=HERE.parent/'exports'/'review-a2'
review=App.openDocument(str(HERE/'TresVizo-case-A2-CABLE-ROUTE.FCStd'))
doc=App.openDocument(str(HERE/'TresVizo-case-A2.FCStd'))
objects=[o for o in review.Objects if hasattr(o,'ColorRGB')]
colors={o.Name:np.array([float(c) for c in o.ColorRGB.split(',')]) for o in objects}
fig=plt.figure(figsize=(16,10),facecolor='#f3f5f5')
fig.text(.04,.945,'TresVizoRTK A2  /  paso del coaxial',fontsize=26,weight='bold',color='#20363c')
fig.text(.04,.905,'Entrada bajo la antena → salida lateral → costado del bastidor → zona inferior del UM980',fontsize=12,color='#59696e')
ax=fig.add_axes([.015,.115,.42,.745])
draw(ax,[(o.Name,o.Shape) for o in objects],colors,elev=13,azim=-50)
fig.text(.055,.078,'Azul: reserva de recorrido Ø5 mm.\nAntena y carcasa ocultas para mostrar el paso.',fontsize=10,color='#365b77',linespacing=1.5)

upper=Part.makeBox(90,90,33,App.Vector(-45,-45,143))
ax=fig.add_axes([.49,.515,.46,.31])
draw(ax,[(o.Name,o.Shape.common(upper)) for o in objects if o.Name in ('AntennaSupport','CoaxRouteReserve')],
     colors,elev=48,azim=-48)
fig.text(.49,.85,'ENTRADA Ø16 BAJO LA ANTENA',fontsize=15,weight='bold',color='#20363c')
fig.text(.49,.485,'El agujero atraviesa el asiento superior.\nLa plataforma inferior tiene una ranura lateral de 8 mm.',fontsize=12,color='#20363c',linespacing=1.5)

middle=Part.makeBox(90,90,25,App.Vector(-45,-45,106))
ax=fig.add_axes([.49,.16,.46,.25])
draw(ax,[(o.Name,o.Shape.common(middle)) for o in objects if o.Name in ('Frame','IMUPlate','IMUReserve','CoaxRouteReserve')],
     colors,elev=40,azim=-48)
fig.text(.49,.425,'PASO POR EL COSTADO DE LA IMU',fontsize=14,weight='bold',color='#20363c')
fig.text(.49,.13,'Escotadura de 8 mm en el anillo del bastidor.\nEl recorrido no atraviesa la placa ni la reserva de la IMU.',fontsize=11,color='#20363c',linespacing=1.5)
fig.text(.04,.025,'CAD de revisión · Cable y conectores finales pendientes de identificar; diámetro de entrada y sellado por comprobar.',fontsize=10,color='#805137')
fig.savefig(str(OUT/'coax-route-a2.png'),dpi=135,facecolor=fig.get_facecolor())
plt.close(fig)
solids=[o for o in doc.Objects if hasattr(o,'ColorRGB')]
step=Part.Shape();step.read(str(OUT/'TresVizo-case-A2-with-RESERVES.step'))
check={'native_solids':len(solids),'step_solids':len(step.Solids),
       'native_valid':all(o.Shape.isValid() for o in solids),'step_valid':step.isValid()}
assert check['native_solids']==check['step_solids']==52 and check['native_valid'] and check['step_valid']
(OUT/'reopen-checks.json').write_text(json.dumps(check,indent=2)+'\n')
print(json.dumps(check))
