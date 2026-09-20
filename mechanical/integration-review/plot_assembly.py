"""Secciones del BREP que muestran los bloqueos de paso axial del cuerpo."""
from pathlib import Path
import FreeCAD as App
import Part
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D

ROOT=Path(__file__).resolve().parent
doc=App.openDocument(str(ROOT/'generated/TresVizo-panel-modules.FCStd'))
fig,axes=plt.subplots(1,2,figsize=(12,6),layout='constrained')
fig.suptitle('A5: obstáculos reales durante el paso del cuerpo',fontsize=17,fontweight='bold')
cases=[(8,33,'A5_BatteryIMUCarrier','Subir +8 mm · corte Z33 · cuna'),
       (-2,11,'A5_Chassis','Bajar −2 mm · corte Z11 · base')]
for ax,(dz,z,target,title) in zip(axes,cases):
    shell=doc.getObject('A5_MainShell').Shape.copy()
    shell.translate(App.Vector(0,0,dz))
    obstacle=doc.getObject(target).Shape
    common=shell.common(obstacle)
    plane=Part.makePlane(90,90,App.Vector(-45,-45,z),App.Vector(0,0,1))
    for shape,color,lw in [(shell,'#236eae',1.5),(obstacle,'#d18423',1.5),(common,'#c52632',4)]:
        for edge in shape.section(plane).Edges:
            pts=edge.discretize(Deflection=.04)
            ax.plot([p.x for p in pts],[p.y for p in pts],color=color,linewidth=lw)
    ax.set_title(title,fontsize=12)
    ax.set_aspect('equal');ax.set_xlim(-35,35);ax.set_ylim(-35,35)
    ax.set_xlabel('X (mm)');ax.set_ylabel('Y (mm); FRONT = +Y')
    ax.grid(alpha=.15)
    ax.text(.02,.02,f'Intersección 3D: {common.Volume:.5f} mm³',transform=ax.transAxes,
            fontsize=10,color='#a01a27',bbox={'facecolor':'white','edgecolor':'none','alpha':.95})
fig.legend(handles=[Line2D([0],[0],color='#236eae',label='Cuerpo desplazado'),
                    Line2D([0],[0],color='#d18423',label='Plástico interior'),
                    Line2D([0],[0],color='#c52632',lw=4,label='Intersección')],
           loc='outside lower center',ncol=3,frameon=False)
fig.savefig(ROOT/'generated/assembly-blockers.png',dpi=180)
plt.close(fig);App.closeDocument(doc.Name)
