"""Lamina de revision desde los solidos reales de A1, sin depender de la GUI."""
import json
from pathlib import Path
import FreeCAD as App
import Part
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

HERE=Path(__file__).resolve().parent
OUT=HERE.parent/'exports'/'review-a1'
doc=App.openDocument(str(HERE/'TresVizo-case-A1.FCStd'))
section=App.openDocument(str(HERE/'TresVizo-case-A1-MOUNT-SECTION.FCStd'))
objects=[o for o in doc.Objects if hasattr(o,'ColorRGB')]
colors={o.Name:np.array([float(c) for c in o.ColorRGB.split(',')]) for o in objects}


def draw(ax, entries, limits, elev=18, azim=65):
    polygons=[]; shades=[]
    light=np.array([0.2,0.7,1.0]); light/=np.linalg.norm(light)
    for name,shape in entries:
        verts,faces=shape.tessellate(0.18)
        v=np.array([[p.x,p.y,p.z] for p in verts])
        tri=v[np.asarray(faces)]
        normal=np.cross(tri[:,1]-tri[:,0],tri[:,2]-tri[:,0])
        normal/=np.maximum(np.linalg.norm(normal,axis=1,keepdims=True),1e-12)
        intensity=0.55+0.45*np.maximum(normal@light,0)
        col=np.clip(colors[name]*intensity[:,None],0,1)
        polygons.extend(tri); shades.extend(col)
    # Z-buffer ortografico: evita ordenar por profundidad media triangulos
    # largos de los canales, lo que produciria falsas transparencias.
    el,az=np.radians([elev,azim])
    eye=np.array([np.cos(el)*np.cos(az),np.cos(el)*np.sin(az),np.sin(el)])
    right=np.array([-np.sin(az),np.cos(az),0])
    up=np.cross(eye,right)
    tri=np.asarray(polygons)@np.stack([right,up,eye],axis=1)
    pos=ax.get_position()
    width,height=int(pos.width*2200),int(pos.height*1375)
    low=tri[:,:,:2].min(axis=(0,1)); high=tri[:,:,:2].max(axis=(0,1))
    scale=min((width-40)/(high[0]-low[0]),(height-40)/(high[1]-low[1]))
    center=(low+high)/2
    tri[:,:,0]=(tri[:,:,0]-center[0])*scale+width/2
    tri[:,:,1]=-(tri[:,:,1]-center[1])*scale+height/2
    depth=np.full((height,width),-np.inf)
    rgba=np.zeros((height,width,4),dtype=np.uint8)
    for t,color in zip(tri,shades):
        xmin=max(0,int(np.floor(t[:,0].min()))); xmax=min(width-1,int(np.ceil(t[:,0].max())))
        ymin=max(0,int(np.floor(t[:,1].min()))); ymax=min(height-1,int(np.ceil(t[:,1].max())))
        if xmin>xmax or ymin>ymax: continue
        x0,y0,z0=t[0]; x1,y1,z1=t[1]; x2,y2,z2=t[2]
        denominator=(y1-y2)*(x0-x2)+(x2-x1)*(y0-y2)
        if abs(denominator)<1e-9: continue
        ys,xs=np.mgrid[ymin:ymax+1,xmin:xmax+1]
        xs=xs+.5; ys=ys+.5
        a=((y1-y2)*(xs-x2)+(x2-x1)*(ys-y2))/denominator
        b=((y2-y0)*(xs-x2)+(x0-x2)*(ys-y2))/denominator
        c=1-a-b
        z=a*z0+b*z1+c*z2
        old=depth[ymin:ymax+1,xmin:xmax+1]
        mask=(a>=-1e-7)&(b>=-1e-7)&(c>=-1e-7)&(z>old)
        old[mask]=z[mask]
        pixels=rgba[ymin:ymax+1,xmin:xmax+1]
        pixels[mask,:3]=(np.asarray(color)*255).astype(np.uint8)
        pixels[mask,3]=255
    ax.imshow(rgba,interpolation='bilinear')
    ax.set_axis_off()


fig=plt.figure(figsize=(16,10),facecolor='#f3f5f5')
fig.text(.045,.94,'TresVizoRTK  /  carcasa A1',fontsize=27,weight='bold',color='#20363c')
fig.text(.045,.905,'Antena sin segunda cubierta · montaje metálico reemplazable',fontsize=14,color='#59696e')
left=fig.add_axes([.015,.18,.40,.67],facecolor='#f3f5f5')
exterior={'MainShell','ServiceCover','OpenShoulder','Base','HA901Reserve'}
draw(left,[(o.Name,o.Shape) for o in objects if o.Name in exterior or o.Name.startswith('RadialBolt')],
     [(-39,39),(-39,39),(-2,218)],elev=13,azim=66)
fig.text(.065,.16,'Ø máximo 74 mm · altura reservada 214 mm',fontsize=11,color='#20363c')
fig.text(.065,.125,'Negro superior: reserva HA-901A Ø46 × 46.\nSus agujeros y dimensiones finales siguen pendientes.',fontsize=10,color='#59696e',linespacing=1.5)

ax=fig.add_axes([.44,.50,.51,.31],facecolor='#f3f5f5')
draw(ax,[(o.Name,o.Shape) for o in section.Objects if hasattr(o,'Shape') and not o.Shape.isNull()],
     [(-35,35),(-35,3),(-1,32)],elev=25,azim=74)
fig.text(.46,.86,'CORTE DEL MONTAJE',fontsize=13,weight='bold',color='#20363c')
fig.text(.46,.46,'Dorado: tuerca hembra 5/8″-11 + calce de ajuste',fontsize=12,weight='bold',color='#9c6c15')
fig.text(.46,.413,'1   Placa inferior: recibe el apoyo del jalón.',fontsize=13,color='#20363c')
fig.text(.46,.367,'2   Placa con hueco hexagonal: impide girar a la tuerca.',fontsize=13,color='#20363c')
fig.text(.46,.321,'3   Placa superior: impide que la tuerca salga hacia arriba.',fontsize=13,color='#20363c')
fig.text(.46,.275,'4   Cuatro M4 pasantes unen placas y bastidor.',fontsize=13,color='#20363c')
fig.text(.46,.21,'Las tres placas son de metal de 3 mm.\nRoscas y tornillería se muestran simplificadas.',fontsize=11,color='#59696e',linespacing=1.5)
fig.text(.045,.055,'REVISIÓN DE DISEÑO · Sin ensayo de carga, estanqueidad o RF. Confirmar rosca y espiga del jalón antes de fabricar.',
         fontsize=11,color='#805137')
fig.savefig(str(OUT/'case-a1-review.png'),dpi=130,facecolor=fig.get_facecolor())
plt.close(fig)

# Verifica que los archivos guardados se pueden abrir y el STEP conserva los solidos.
step=Part.Shape(); step.read(str(OUT/'TresVizo-case-A1-with-RESERVES.step'))
check={'native_solids':len(objects),'native_valid':all(o.Shape.isValid() for o in objects),
       'step_solids':len(step.Solids),'step_valid':step.isValid(),
       'section_objects':len(section.Objects)}
assert check['native_solids']==check['step_solids']==52 and check['native_valid'] and check['step_valid']
(OUT/'reopen-checks.json').write_text(json.dumps(check,indent=2)+'\n')
print(json.dumps(check))
