"""Esquema funcional sin escala para revisar la arquitectura propuesta."""
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle, FancyBboxPatch, Polygon

HERE=Path(__file__).resolve().parent
BG='#f3f5f5'; INK='#20363c'; GREEN='#527d78'; GOLD='#ca983e'; BLUE='#327cbb'
fig=plt.figure(figsize=(16,10),facecolor=BG)
fig.text(.045,.947,'Menos piezas, montaje accesible',fontsize=28,weight='bold',color=INK)
fig.text(.045,.903,'Propuesta de arquitectura A4 · conservar el exterior y reconstruir el interior',fontsize=15,color='#59696e')

def canvas(rect,xlim,ylim):
    ax=fig.add_axes(rect); ax.set_xlim(*xlim); ax.set_ylim(*ylim); ax.set_aspect('equal'); ax.axis('off'); return ax

fig.text(.055,.844,'BASE: UNA PIEZA IMPRESA',fontsize=15,weight='bold',color=INK)
ax=canvas([.03,.53,.47,.27],(-37,37),(-18,20))
# Corte conceptual: asiento integrado y brida interior. NO son cotas de producto.
left=[(-31,0),(-7,0),(-7,8),(-19,8),(-19,15),(-28,15),(-28,10),(-31,10)]
ax.add_patch(Polygon(left,closed=True,color=GREEN))
ax.add_patch(Polygon([(-x,y) for x,y in left],closed=True,color=GREEN))
for side in (-1,1):
    ax.add_patch(Rectangle((side*4 if side>0 else -6.6,0),2.6,8,color=GOLD))
    ax.add_patch(Rectangle((4 if side>0 else -18,8),14,2.3,color=GOLD))
    x=side*13
    ax.add_patch(Rectangle((x-.65,2),1.3,9.5,color='#4c555c'))
    ax.add_patch(Rectangle((x-2.1,10.3),4.2,1.5,color='#4c555c'))
    ax.add_patch(Rectangle((x-2,3),4,2,color='#a6afb3'))
ax.add_patch(Rectangle((-4,0),8,13,color=BLUE))
ax.add_patch(Rectangle((-15,-11),30,11,color=BLUE))
ax.annotate('Inserto con brida\ncomprado terminado',xy=(17,9),xytext=(20,22),fontsize=11,color=INK,
            arrowprops={'arrowstyle':'-','color':INK},ha='center')
ax.text(0,-16,'JALÓN',ha='center',fontsize=11,color=BLUE,weight='bold')
fig.text(.055,.512,'La brida apoya sobre la propia base.',fontsize=13,color=INK,weight='bold')
fig.text(.055,.465,'Tres tornillos retienen el inserto y limitan su giro.\nEl cuerpo se atornilla a esta misma base.',fontsize=12,color=INK,linespacing=1.5)
fig.text(.055,.412,'Se eliminan el cartucho, la tapa y el calce separados.',fontsize=11,color='#59696e')

fig.text(.545,.844,'INTERIOR: BANDEJAS IMPRESAS ACOSTADAS',fontsize=15,weight='bold',color=INK)
ax=canvas([.54,.42,.43,.38],(0,115),(0,90))
ax.add_patch(FancyBboxPatch((7,7),45,77,boxstyle='round,pad=0,rounding_size=4',facecolor=GREEN,edgecolor=INK,lw=1.5))
for x in (10,45): ax.add_patch(Rectangle((x,12),4,67,color='#355f5b'))
for y in (18,36,54,72):
    for x in (17,37):
        ax.add_patch(FancyBboxPatch((x,y),4,8,boxstyle='round,pad=0,rounding_size=2',facecolor=BG,edgecolor='none'))
for x,y,w,h in [(23,17,12,19),(23,44,12,13),(23,66,12,11)]:
    ax.add_patch(Rectangle((x,y),w,h,facecolor=BLUE,edgecolor='#21496b',lw=1))
ax.text(29.5,0,'ELECTRÓNICA',ha='center',fontsize=10,color=INK,weight='bold')
ax.add_patch(FancyBboxPatch((67,15),39,63,boxstyle='round,pad=0,rounding_size=4',facecolor=GREEN,edgecolor=INK,lw=1.5))
ax.add_patch(Rectangle((71,20),31,53,facecolor='#a4adb1',edgecolor='#727f84',lw=2))
ax.add_patch(Rectangle((70,17),33,4,facecolor='#355f5b'))
ax.add_patch(Rectangle((70,73),33,3,facecolor='#355f5b'))
ax.text(86,0,'BATERÍA',ha='center',fontsize=10,color=INK,weight='bold')
fig.text(.545,.389,'Espinas anchas y nervios cortos.',fontsize=13,color=INK,weight='bold')
fig.text(.545,.342,'Apoyos integrados + ranuras cortas para las placas.\nLas dos bandejas forman un módulo extraíble.',fontsize=12,color=INK,linespacing=1.5)

fig.text(.055,.319,'REFERENCIAS FIJAS',fontsize=14,weight='bold',color=INK)
fig.text(.055,.272,'IMU: asiento rígido, topes y patrón real.\nSMA: recorte del conector o paso protegido de cable.',fontsize=12,color=INK,linespacing=1.5)

fig.text(.055,.185,'Objetivo: 7 piezas impresas principales',fontsize=17,weight='bold',color=INK)
fig.text(.055,.143,'Base · cuerpo · tapa de antena · bandeja electrónica · cuna de batería · soporte IMU · portillo',fontsize=12,color='#59696e')
fig.text(.055,.084,'ESQUEMA FUNCIONAL SIN ESCALA · No representa distribución final de placas ni patrones comerciales de tornillos.',fontsize=10,color='#805137')
fig.text(.055,.052,'Pendiente: CAD reconstruido, componentes finales, laminado, montaje y ensayos. A3 conserva la arquitectura anterior.',fontsize=10,color='#805137')
fig.savefig(HERE/'redesign-concept.png',dpi=140,facecolor=BG)
fig.savefig(HERE/'redesign-concept.svg',facecolor=BG)
plt.close(fig)
