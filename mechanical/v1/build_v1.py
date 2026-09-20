"""V1 de taller: geometria derivada parametrica de A5 + panel; mm."""
from pathlib import Path
import FreeCAD as App
import Part, MeshPart, Mesh
import json, math, hashlib, argparse
ROOT=Path(__file__).resolve().parent
parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('--output-dir',type=Path,default=ROOT/'generated')
OUT=parser.parse_args().output_dir.resolve(); OUT.mkdir(parents=True,exist_ok=True)
BASELINE=ROOT.parents[1]/'.cache/mechanical-v1/baseline'
P=json.loads((ROOT/'parameters.json').read_text(encoding='utf-8'))
V=App.Vector
base=App.openDocument(str(BASELINE/'TresVizo-panel-modules.FCStd'))
doc=App.newDocument('TresVizoV1')
S={o.Name:o.Shape.copy() for o in base.Objects if hasattr(o,'Shape')}
labels={o.Name:o.Label for o in base.Objects if hasattr(o,'Shape')}
colors={o['name']:o['color'] for o in json.loads((BASELINE/'render-meshes.json').read_text())}
original={n:s.copy() for n,s in S.items()}
printed=['A5_MainShell','A5_Chassis','A5_BatteryIMUCarrier','A5_AntennaCap','A5_IMUNutBar','ModulePanel','ButtonCap','ButtonCartridge','StatusLens','ChargeLens']
removed=[]; functional_contacts=[]
def box(x,y,z,dx,dy,dz):return Part.makeBox(dx,dy,dz,V(x,y,z))
def cyl(r,h,xyz,axis=(0,0,1)):return Part.makeCylinder(r,h,V(*xyz),V(*axis))
def move(s,delta):
 s=s.copy();s.translate(V(*delta));return s
def clean(s):
 s=s.removeSplitter()
 if len(s.Solids)>1 and any(t.Volume<0.05 for t in s.Solids):
  s=Part.makeCompound([t for t in s.Solids if t.Volume>=0.05]).removeSplitter()
 return s
def add(n,label,s,color=(100,140,150),kind='print'):
 S[n]=clean(s);labels[n]=label;colors[n]=color
 if kind=='print': printed.append(n)
def discard(n):
 if n in S: del S[n];removed.append(n)
def screw(n,xyz,axis,length=8):
 a=V(*axis);start=V(*xyz)
 s=Part.makeCylinder(1.5,length,start,a).fuse(Part.makeCylinder(P['M3_HEAD_D']/2,P['M3_HEAD_H'],start,-a))
 add(n,'M3 x '+str(length)+' ISO 7380',s,(150,156,163),'hardware')
def hexprism(af,h,xyz):
 r=af/math.sqrt(3);x,y,z=xyz
 pts=[V(x+r*math.cos(i*math.pi/3),y+r*math.sin(i*math.pi/3),z) for i in range(6)]
 return Part.Face(Part.makePolygon(pts+[pts[0]])).extrude(V(0,0,h))
def radial_slot(r0,r1,width,z,h,angle):
 s=box(r0,-width/2,z,r1-r0,width,h).fuse(cyl(width/2,h,(r0,0,z))).fuse(cyl(width/2,h,(r1,0,z)))
 s.rotate(V(),V(0,0,1),angle);return s

def tube(points,r):
 parts=[]
 for a,b in zip(points,points[1:]):
  aa,bb=V(*a),V(*b);d=bb-aa;parts.append(Part.makeCylinder(r,d.Length,aa,d))
 for a in points[1:-1]:parts.append(Part.makeSphere(r,V(*a)))
 return clean(parts[0].multiFuse(parts[1:]))

# Paso axial: alivio solo interior; esquinas perifericas, sin tocar datum IMU.
passcore=cyl(P['CORE_PASS_RADIUS'],180,(0,0,12))
S['A5_MainShell']=clean(S['A5_MainShell'].cut(cyl(P['SHELL_PASS_RADIUS'],P['SHELL_RELIEF_TOP']-11.9,(0,0,11.9))))
S['A5_BatteryIMUCarrier']=clean(S['A5_BatteryIMUCarrier'].common(passcore))
S['A5_Chassis']=clean(S['A5_Chassis'].cut(box(-50,-50,12,100,100,180).cut(passcore)))

# Dos cierres de cuerpo opuestos. El collar/base conserva asiento circunferencial.
for i in [2,4]:
 discard('A5_RadialBolt'+str(i));discard('A5_RadialNut'+str(i))
# USB: dos fijaciones diagonales, cuatro apoyos existentes (sin flexionar PCB).
for i in [2,3]: discard('USBScrew'+str(i))
# Cartucho: una lengueta cautiva a la izquierda y un M3x8 a la derecha.
back=28.8; bz=110
for n in ['ButtonScrew1','ButtonScrew2']:discard(n)
panel=S['ModulePanel'];cart=S['ButtonCartridge']
# Ampliar poste derecho, conservar la pared exterior curva mediante recorte original.
outer=Part.makeCone(36.5545454545,37.1,12,V(0,0,88)).fuse(Part.makeCone(37.1,37.1+43/88,43,V(0,0,100)))
boss=cyl(3.25,6.9,(9,back,110),(0,1,0)).common(outer)
panel=panel.fuse(boss).cut(cyl(P['M3_PILOT']/2,6.2,(9,back-.01,110),(0,1,0)))
panel=panel.cut(cyl(6.7,1.7,(0,33.2,110),(0,1,0)))
cart=cart.cut(cyl(P['M3_CLEARANCE']/2,4,(9,back-3,110),(0,1,0)))
# Lengueta izquierda entra en un bolsillo abierto en Y, cierre posterior por el M3.
tab=box(-12.1,27.8,105,2.8,4.5,2.0)
panel=panel.fuse(box(-12.4,28.8,104.5,3.6,5.5,3.2)).cut(box(-12.25,27.5,104.85,3.1,5.3,2.3))
cart=cart.fuse(tab)
S['ModulePanel']=clean(panel);S['ButtonCartridge']=clean(cart)
screw('ButtonM3',(9,back-2.5,110),(0,1,0))
functional_contacts.append(['ModulePanel','ButtonM3'])
# Despeje local para cabeza M3 y su acceso; no alcanza el asiento IMU.
S['A5_Chassis']=clean(S['A5_Chassis'].cut(cyl(3.2,6,(9,23.8,110),(0,1,0))))

# Inserto invertido: barril al ras de Z0, brida sobre asiento Z9.525.
p=P['insert']; h=p['barrel_h']; t=p['flange_t']; radial=p['mount_radius_nominal']
insert=cyl(p['barrel_d']/2,h,(0,0,0)).fuse(cyl(p['flange_d']/2,t,(0,0,h)))
insert=insert.cut(cyl(p['thread_major']/2,h+t+2,(0,0,-1)))
# Rellenar solo la antigua cavidad central para crear asiento y alojamientos nuevos.
ch=S['A5_Chassis'].fuse(cyl(20.7,11.95,(0,0,0)))
ch=ch.cut(cyl(p['barrel_d']/2+P['INSERT_5_8_CLEARANCE'],h+.02,(0,0,-.01)))
ch=ch.cut(cyl(p['flange_d']/2+P['INSERT_5_8_CLEARANCE'],20,(0,0,h)))
ch=ch.cut(cyl(8.6,p['overtravel_top']+1,(0,0,-1)))
for i,angle in enumerate([0,120,240],1):
 x=radial*math.cos(math.radians(angle));y=radial*math.sin(math.radians(angle))
 insert=insert.cut(cyl(p['mount_hole_d']/2,t+1,(x,y,h-.5)))
 # Slots radiales absorben el circulo de taladros sin falsear una cota no publicada.
 ch=ch.cut(radial_slot(p['slot_radius_min'],p['slot_radius_max'],P['M3_CLEARANCE'],3.5,10,angle))
 # Cavidad cautiva alargada, accesible desde la cara inferior; tapa de 2.125 mm.
 trap=box(p['slot_radius_min']-3.3,-2.9,0,p['slot_radius_max']-p['slot_radius_min']+6.6,5.8,7.4)
 trap.rotate(V(),V(0,0,1),angle);ch=ch.cut(trap)
 screw('InsertBolt'+str(i),(x,y,h+t),(0,0,-1))
 nut=hexprism(5.5,2.4,(x,y,5)).cut(cyl(1.5,2.6,(x,y,4.9)))
 # Hex orientado con el bolsillo radial.
 nut.rotate(V(x,y,0),V(0,0,1),angle)
 add('InsertNut'+str(i),'Tuerca cautiva M3 - inserto '+str(i),nut,(145,153,161),'hardware')
S['A5_FlangedInsert']=clean(insert); labels['A5_FlangedInsert']='McMaster 90611A121 - 5/8-11 hembra'
S['A5_Chassis']=clean(ch)

# Bandejas universales abiertas: dos bandas por modulo, placas aislantes y topes.
carrier=S['A5_BatteryIMUCarrier']
for key,name,label in [('powerboost','PowerBoost','Adafruit PowerBoost 1000C - sin USB-A'),('soft_switch','SoftPower','SparkFun Soft Power Switch Mk2')]:
 e=P[key];x,y,z,w,depth,height=e['box']; py=e['tray_plate_y']; clearance=P['POWER_MODULE_CLEARANCE']
 env=box(x,y,z,w,depth,height)
 cavity=box(x-clearance,y-clearance,z-clearance,w+2*clearance,depth+2*clearance,height+2*clearance)
 carrier=carrier.cut(cavity)
 ax,ay,az,aw,ad,ah=e['alternative_box']
 carrier=carrier.cut(box(ax-clearance,ay-clearance,az-clearance,aw+2*clearance,ad+2*clearance,ah+2*clearance))
 plate=box(x-2.6,py,z-2.4,w+5.2,2.4,height+4.8)
 bottom=box(x-1.1,y-.4,z-2.4,w+2.2,py+2.4-y+.4,2.0)
 tray=plate.fuse(bottom).common(cyl(P['CORE_PASS_RADIUS'],180,(0,0,0)))
 # Dos parejas de ranuras para brida de 2.5 mm, fuera de la bolsa.
 for zz in e['strap_z']:
  for xx in (x-0.7,x+w-2.1):
   tray=tray.cut(box(xx,py-.1,zz,2.8,2.7,1.4))
 carrier=carrier.fuse(tray)
 add(name,label,env,(34,123,105),'component')
S['A5_BatteryIMUCarrier']=clean(carrier)

# Retenciones adaptables: apoyos de borde y pasos de brida, sin taladrar PCBs.
ch=S['A5_Chassis']
for z in [45,102]:
 ch=ch.fuse(box(-18,9.0,z,36,3.5,2.4))
 for x in [-11,8]:ch=ch.cut(box(x,8.8,z-.15,3.0,4.0,1.3))
# Tiny Adapter: base abierta integrada al chasis y dos labios laterales.
adapter_support=box(-10.4,16.3,142,20.8,1.3,16.5)
for x in [-10.4,9.4]:adapter_support=adapter_support.fuse(box(x,16.3,142,1.0,7.1,16.5))
adapter_support=adapter_support.fuse(box(-10.4,16.3,142,5.4,7.1,1)).fuse(box(5.0,16.3,142,5.4,7.1,1))
# Puentes hasta espina, a los lados de Tiny para no abrazar la placa.
for x in [-10.4,9.4]: adapter_support=adapter_support.fuse(box(x,8.8,147,1,8.8,3))
for x in [-8,5]:adapter_support=adapter_support.cut(box(x,16.1,153,3,1.7,1.4))
ch=ch.fuse(adapter_support)
# Tiny sale hacia arriba: retirar solo el labio superior, conservar guias y
# tope inferior; una brida de 2.5 mm por dos ranuras reemplaza ese labio.
ch=ch.cut(box(-9.3,12.2,162.8,18.6,3.9,1.0))
for x in [-8,5]:ch=ch.cut(box(x,8.0,155,3,4.6,1.4))
S['A5_Chassis']=clean(ch)
S['A5_SDReference']=move(S['A5_SDReference'],(0,0,3))
# microSD: bridas a traves de su soporte existente, puntas alejadas de bateria.
car=S['A5_BatteryIMUCarrier']
for z in [53,85]:
 car=car.fuse(box(-12.9,-17.6,z,25.8,2.8,2.4))
 for x in [-9,6]:car=car.cut(box(x,-17.8,z+.4,3,3.2,1.4))
S['A5_BatteryIMUCarrier']=clean(car)
# Recuperar los dos alojamientos de plantilla que la fusion A5 habia rellenado;
# no cambia la cara de asiento, los dos tornillos ni el datum del sensor.
for x in [-15.5,15.5]:
 S['A5_BatteryIMUCarrier']=S['A5_BatteryIMUCarrier'].cut(cyl(1.45,3.5,(x,-13.5,120.5)))
# Paso del puente de plantilla; adelgazar localmente respaldo power a 1.9 mm.
S['A5_BatteryIMUCarrier']=clean(S['A5_BatteryIMUCarrier'].cut(box(-17.5,-15.7,123,35,.6,22)))

# Rutas continuas de cableado con salida lateral por encima del pack.
routes={
 'BatteryToPower': {'r':1.8,'points':[[-15,0,108.8],[-15,0,110],[-15,-20,110],[-16,-22,110],[-13.4,-22,106]]},
 'RearPowerBus': {'r':1.6,'points':[[-16,-22,28],[-17,-22,50],[-17,-22,112],[-17,-22,134],[-19,-17,138],[-20,17,138],[-15,13.5,143.5],[-11,13.5,143.5]]},
 'PowerToGNSS': {'r':1.7,'points':[[-17,-22,100],[-17,-22,118.5],[-20,-17,118.5],[-20,20,118.5],[-20,20,98]]},
 'UartAndImu': {'r':1.5,'points':[[20,20,58],[20,20,128],[20,16,134],[0,15,134],[-20,15,134],[-20,-15,134],[-20,-12,129],[-12,-12,129]]},
 'UsbHarness': {'r':2.0,'points':[[-12.3,20,132.5],[-13,24,135.5],[0,25.5,135.5],[0,24.9,138]]},
 'ChargeLight': {'r':1.0,'points':[[-12.6,-22,138],[-15,-19,148],[-15,24.5,148],[13,24.5,148],[13,24.5,121],[4,23.5,121],[4,30,121]]},
}
# Conservar el corredor curvado R10 de A5; se alimenta con el cuerpo colocado,
# antes de cerrar panel/tapa, y se retira antes de deslizar el cuerpo.
S['A5_CoaxRouteReserve']=original['A5_CoaxRouteReserve'].copy()
S['A5_BatteryIMUCarrier']=clean(S['A5_BatteryIMUCarrier'].cut(S['A5_CoaxRouteReserve'].makeOffsetShape(.3,.01)))
labels['A5_CoaxRouteReserve']='Coaxial flexible - instalar despues del cuerpo / R10'
route_names=[]
for n,e in routes.items():
 add(n,n+' - corredor de cable',tube(e['points'],e['r']),(218,152,56),'route');route_names.append(n)
# Ventana de salida de bateria en espalda, lejos de asiento IMU.
S['A5_BatteryIMUCarrier']=clean(S['A5_BatteryIMUCarrier'].cut(tube(routes['BatteryToPower']['points'],2.2)))

# Pasos locales de arnes en espina y en el borde de la bandeja, lejos del IMU.
for n in ['RearPowerBus','PowerToGNSS','UartAndImu','UsbHarness','ChargeLight']:
    e=routes[n]; tool=tube(e['points'],e['r']+(.35 if n=='PowerToGNSS' else .3))
    S['A5_Chassis']=clean(S['A5_Chassis'].cut(tool))
    if n in ['ChargeLight','PowerToGNSS']:
        S['A5_BatteryIMUCarrier']=clean(S['A5_BatteryIMUCarrier'].cut(tool))
# Entrada del inserto por -Y a Z+16, seguida de descenso vertical; la base
# conserva entero el asiento inferior y los dos cierres laterales X opuestos.
S['A5_Chassis']=clean(S['A5_Chassis'].cut(box(-9.55,-41,15.7,19.1,41,12)))
# Acceso de llave al tornillo frontal del inserto, antes de montar la electronica.
angle=math.radians(120)
S['A5_Chassis']=clean(S['A5_Chassis'].cut(cyl(1.7,41,(radial*math.cos(angle),radial*math.sin(angle),13.56))))
# Geometria embebida y tres carpetas; referencias dentro de componentes.
gp=doc.addObject('App::DocumentObjectGroup','PrintParts');gp.Label='01 Para imprimir'
gh=doc.addObject('App::DocumentObjectGroup','Fasteners');gh.Label='02 Tornilleria para comprar'
gc=doc.addObject('App::DocumentObjectGroup','Components');gc.Label='03 Componentes'
gr=doc.addObject('App::DocumentObjectGroup','References');gr.Label='Referencias y cableado - no imprimir';gc.addObject(gr)
objects={}
hardware=[]
for n,s in S.items():
 if not s.isValid() or not s.Solids: raise ValueError('Invalido '+n)
 if n in printed and len(s.Solids)!=1: raise ValueError('Pieza impresa desconectada: '+n)
 o=doc.addObject('Part::Feature',n);o.Label=labels[n];o.Shape=s;objects[n]=o
 if n in printed:gp.addObject(o)
 elif any(t in n for t in ['Bolt','Nut','Screw','ButtonM3','FlangedInsert']):gh.addObject(o);hardware.append(n)
 elif n in route_names+['A5_IMUTarget','A5_CoaxRouteReserve','TinyUSBPlugReserve']:gr.addObject(o)
 else:gc.addObject(o)
 o.addProperty('App::PropertyString','Fabricacion','V1');o.Fabricacion='Imprimir' if n in printed else 'Comercial / referencia'
 if o.ViewObject:
  o.ViewObject.ShapeColor=tuple(c/255 for c in colors.get(n,[100,140,150]));o.ViewObject.Visibility=n not in route_names+['A5_IMUTarget','TinyUSBPlugReserve']
tools_group=doc.addObject('App::DocumentObjectGroup','PrintTools');tools_group.Label='Plantilla reutilizable - fuera del montaje';gp.addObject(tools_group)
source_doc=App.openDocument(str(ROOT.parent/'sources/a5/TresVizo-A5.FCStd'))
gauge=doc.addObject('Part::Feature','IMUAlignmentGauge');gauge.Label='11 Plantilla de centrado BMI088';gauge.Shape=source_doc.IMUAlignmentGauge.Shape.copy();tools_group.addObject(gauge)
if gauge.ViewObject:gauge.ViewObject.Visibility=False
doc.recompute();doc.saveAs(str(OUT/'TresVizo-V1.FCStd'))
meta={'printed':printed,'hardware':hardware,'routes':route_names,'removed':removed,'functional_contacts':functional_contacts,'objects':[{'name':n,'solids':len(s.Solids),'valid':s.isValid(),'volume':s.Volume,'bbox':[getattr(s.BoundBox,k) for k in ['XMin','YMin','ZMin','XMax','YMax','ZMax']]} for n,s in S.items()], 'colors':colors}
meta['tools']=['IMUAlignmentGauge']
(OUT/'model-index.json').write_text(json.dumps(meta,indent=2,ensure_ascii=False),encoding='utf-8')
print('BUILT',len(S),'printed',len(printed),flush=True)
App.closeDocument(doc.Name);App.closeDocument(base.Name)
