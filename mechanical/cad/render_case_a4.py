"""Lamina de las geometrías A4 reales; sin interfaz de FreeCAD."""
from pathlib import Path
import FreeCAD as App
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from cad_raster import draw
HERE=Path(__file__).resolve().parent
OUT=HERE.parent/'exports'/'review-a4'
doc=App.openDocument(str(HERE/'TresVizo-case-A4.FCStd'))
colors={o.Name:np.array([float(v) for v in o.ColorRGB.split(',')]) for o in doc.Objects if hasattr(o,'ColorRGB')}
fig=plt.figure(figsize=(16,10),dpi=150,facecolor='#f3f1e9')
fig.text(.045,.955,'TRESVIZO / A4',fontsize=25,weight='bold',color='#183936')
fig.text(.045,.915,'7 piezas impresas · base de una pieza · símbolo 3 + hexágono grabado',fontsize=15,color='#354944')
axes=[fig.add_axes((.03,.25,.29,.6)),fig.add_axes((.345,.25,.31,.6)),fig.add_axes((.685,.25,.285,.6))]
closed=[(o.Name,o.Shape) for o in doc.Plastic.Group if o.Name in ('MainShell','ServiceCover','Base','AntennaCap')]+[('HA901Reserve',doc.HA901Reserve.Shape)]
interior=[(o.Name,o.Shape) for o in doc.Plastic.Group if o.Name in ('Base','ElectronicsTray','BatteryCradle','IMUSeat')]
components=[(o.Name,o.Shape) for o in doc.References.Group if o.Name not in ('HA901Reserve',)]
draw(axes[0],closed,colors,elev=14,azim=62)
draw(axes[1],interior,colors,elev=20,azim=62)
draw(axes[2],interior+components,colors,elev=18,azim=120)
for x,title,caption in [(.045,'EXTERIOR CON SÍMBOLO TRESVIZO','3 + hexágono, sin VIZO: alto 36 mm.\nGrabado 0.6 mm integrado bajo el portillo.'),(.36,'ESTRUCTURA NUEVA','Espina de 4 mm y cuna amplia.\nSe eliminan varillas y adaptadores sueltos.'),(.70,'RESERVAS DE COMPONENTES','Coaxial azul fuera de batería e IMU.\nLas reservas no son réplicas de las placas.')]:
 fig.text(x,.86,title,fontsize=12,weight='bold',color='#183936')
 fig.text(x,.23,caption,fontsize=10,color='#354944',linespacing=1.6)
fig.text(.045,.13,'7 piezas: cuerpo · base · tapa superior · bandeja electrónica · cuna batería/SD · soporte IMU · portillo',fontsize=11,color='#183936')
fig.text(.045,.08,'REVISIÓN MECÁNICA: faltan planos IMU/antena/inserto, encendido/carga y ensayos de impresión/montaje.',fontsize=10,color='#80502d')
fig.savefig(OUT/'a4-overview.png',facecolor=fig.get_facecolor())
fig.savefig(OUT/'a4-overview.pdf',facecolor=fig.get_facecolor())
print(OUT/'a4-overview.png')
