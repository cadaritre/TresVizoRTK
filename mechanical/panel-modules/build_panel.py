"""Propuesta mecánica independiente, mm; ejecutar con Python de FreeCAD.

No escribe el maestro A5. Las envolventes electrónicas son referencias,
no modelos de fabricación ni prueba del componente físico comprado.
"""
import FreeCAD as App
import Part, MeshPart
import json, hashlib, math, argparse
from pathlib import Path

ROOT = Path(__file__).resolve().parent
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--output-dir', type=Path, default=ROOT.parent / 'integration-review' / 'generated')
args = parser.parse_args()
OUT = args.output_dir.resolve()
OUT.mkdir(parents=True, exist_ok=True)
(OUT / 'stl').mkdir(exist_ok=True)
P = json.loads((ROOT / 'parameters.json').read_text())
SOURCE = ROOT.parent / 'A5' / 'TresVizo-A5.FCStd'
initial_hash = hashlib.sha256(SOURCE.read_bytes()).hexdigest()
original = App.openDocument(str(SOURCE))
doc = App.newDocument('PanelModulos')
V = App.Vector
objects = {}
colors = {}
printed = []
references = []
context = []

def box(x,y,z,dx,dy,dz):
    return Part.makeBox(dx,dy,dz,V(x,y,z))

def cyl_y(x,z,y,r,h):
    return Part.makeCylinder(r,h,V(x,y,z),V(0,1,0))

def rounded_xz(w,h,r,x,z,y,depth):
    s = box(x-w/2+r,y,z-h/2,w-2*r,depth,h)
    s = s.fuse(box(x-w/2,y,z-h/2+r,w,depth,h-2*r))
    for xx in (x-w/2+r,x+w/2-r):
        for zz in (z-h/2+r,z+h/2-r):
            s=s.fuse(cyl_y(xx,zz,y,r,depth))
    return s.removeSplitter()

def rounded_xy(w,h,r,x,y,z,depth):
    s=box(x-w/2+r,y-h/2,z,w-2*r,h,depth)
    s=s.fuse(box(x-w/2,y-h/2+r,z,w,h-2*r,depth))
    for xx in (x-w/2+r,x+w/2-r):
        for yy in (y-h/2+r,y+h/2-r):
            s=s.fuse(Part.makeCylinder(r,depth,V(xx,yy,z)))
    return s.removeSplitter()

def outer_radius(z):
    return 37.1+(z-100)/88 if z>=100 else 36.5545454545+(z-88)/22

def cone_envelope(offset=0):
    a=Part.makeCone(outer_radius(88)+offset,outer_radius(100)+offset,12,V(0,0,88))
    b=Part.makeCone(outer_radius(100)+offset,outer_radius(143)+offset,43,V(0,0,100))
    return a.fuse(b).removeSplitter()

outer=cone_envelope()
inner=cone_envelope(-2.15)

def add(name,label,shape,color,kind='printed',note=''):
    shape=shape.removeSplitter()
    if shape.isNull() or not shape.isValid():
        raise RuntimeError('Geometría inválida: '+name)
    o=doc.addObject('PartDesign::Feature',name)
    o.Label=label; o.Shape=shape
    o.addProperty('App::PropertyString','Estado','Documentación')
    o.Estado=note or ('Propuesta para primera impresión de ajuste' if kind=='printed' else 'Envolvente de referencia')
    if o.ViewObject:
        o.ViewObject.ShapeColor=tuple(c/255 for c in color)
    objects[name]=o;colors[name]=color
    if kind=='printed': printed.append(name)
    elif kind=='reference': references.append(name)
    else: context.append(name)
    return o

clip=rounded_xz(P['panel_width'],53,5,0,115.5,20,22)
panel=outer.cut(inner).common(clip)
for z in (96,139):
    panel=panel.cut(cyl_y(0,z,25,1.7,18))
    # Conservar los M3x8 ISO7380 del A5 vigente y sus planos de apoyo.
    # No apoyar una cabeza boton en un avellanado conico.
    y=P['panel_head_seat_y'][str(z)]
    panel=panel.cut(cyl_y(0,z,y,P['panel_head_clearance_diameter']/2,5))

uz=P['usb_z']; uy=outer_radius(uz)-P['usb_recess']
board_y=uy-24.003
board_z=uz-P['usb_connector_height_assumed']/2-P['usb_board_thickness_assumed']
rail_z=board_z-3.5
panel=panel.cut(rounded_xz(P['usb_slot_width'],P['usb_slot_height'],1.6,0,uz,29,13))
# Rebaje para sobremolde compacto del cable; boca 1.2 mm dentro de la curva.
panel=panel.cut(rounded_xz(14,6.5,2,0,uz,uy,5))

# Dos largueros y cuatro apoyos: patrón Eagle oficial del módulo Adafruit 5871.
cradle=box(-10.5,board_y,rail_z,21,2.2,2)
holes=[]
for x in (-7.62,7.62):
    cradle=cradle.fuse(box(x-2.35,board_y,rail_z,4.7,22,2))
    for y in (board_y+2.54,board_y+20.32):
        cradle=cradle.fuse(Part.makeCylinder(2.7,3.5,V(x,y,rail_z)))
        holes.append((x,y))
cradle=cradle.common(outer)
for x,y in holes:
    cradle=cradle.cut(Part.makeCylinder(.85,5,V(x,y,rail_z-.1)))
panel=panel.fuse(cradle)
# Bolsillo de placa: no hacer descansar FR4 ni cobre contra la cara curva.
panel=panel.cut(rounded_xy(20.72,23.26,2.54,0,board_y+11.43,board_z,1.85))
# Holgura para cabezas M2 reales; las dos delanteras rozaban la pared curva.
for x,y in holes:
    panel=panel.cut(Part.makeCylinder(P['m2_head_diameter']/2+.2,P['m2_head_height']+.2,V(x,y,board_z+P['usb_board_thickness_assumed'])))

bz=P['button_z']
for x in (-9,9):
    # El poste debe solapar la pared; no se trunca contra la cara interior.
    post=cyl_y(x,bz,P['button_back_y'],2.5,10).common(outer)
    post=post.cut(cyl_y(x,bz,P['button_back_y']-.1,.85,6.3))
    panel=panel.fuse(post)
panel=panel.cut(cyl_y(0,bz,29,P['button_bore_diameter']/2,12))

# Alojamiento de dos LEDs / guía óptica. No hay placas electrónicas propias.
for x in (-P['led_x'],P['led_x']):
    z=P['led_z']
    cup=cyl_y(x,z,26,3.7,11).common(outer)
    cup=cup.cut(cyl_y(x,z,25,2.65,9.15))
    panel=panel.fuse(cup)
    panel=panel.cut(cyl_y(x,z,25,1.6,15))
    # Rebaje de apoyo para la pestaña de la guía/difusor.
    panel=panel.cut(cyl_y(x,z,33.65,2.9,.8))
    # Pared abierta hasta el rebaje: difusor se inserta desde atrás.
    panel=panel.cut(cyl_y(x,z,25,2.9,9.45))

add('ModulePanel','Panel curvo · USB / luces / botón',panel,(45,55,66),note='Sustituye ServiceCover sólo en esta propuesta. Soportes integrados, M3 en Z96 y Z139.')

# Actuador con cara curva y pestaña cautiva; entrada desde la cara posterior.
cap=cyl_y(0,bz,P['button_cap_back_y'],P['button_face_diameter']/2,6).common(outer)
flange=cyl_y(0,bz,P['button_cap_back_y'],6.5,4).common(inner)
cap=cap.fuse(flange)
add('ButtonCap','Botón al ras · actuador cautivo',cap,(213,224,226))

# Cartucho independiente para micro-switch: respaldo, paredes y topes de carrera.
back=P['button_back_y']; body=P['button_body_assumed']; gap=.15
bridge=rounded_xz(24,13,2,0,bz,back-2.5,2.5)
for x in (-9,9): bridge=bridge.cut(cyl_y(x,bz,back-3,1.1,4))
socket=box(-body/2-1.6,back,bz-body/2-1.6,body+3.2,P['button_stop_y']-back,body+3.2)
socket=socket.cut(box(-body/2-gap,back-.1,bz-body/2-gap,body+2*gap,6,body+2*gap))
# Canales para las cuatro patas laterales; confirmar ubicación en AU-101 físico.
for x in (-body/2-2,body/2-.2):
    for zz in (-2.2,2.2):
        socket=socket.cut(box(x,back-.1,bz+zz-.6,2.2,3.4,1.2))
bridge=bridge.fuse(socket)
add('ButtonCartridge','Cartucho desmontable · micro-switch 6 mm nominal',bridge,(81,100,118),note='AU-101 sin cotas publicadas: cuerpo 6 mm y altura 5 mm son supuestos ajustables, no cotas certificadas.')

switchbody=box(-body/2,back,bz-body/2,body,P['button_body_depth_assumed'],body)
add('TactileBody','Steren AU-101 · volumen provisional',switchbody,(29,31,33),'reference')
stem=cyl_y(0,bz,back+P['button_body_depth_assumed'],1.6,P['button_total_depth_assumed']-P['button_body_depth_assumed'])
add('TactileStem','Vástago micro-switch · provisional',stem,(170,174,178),'reference')

for name,x,col in [('StatusLens',-P['led_x'],(57,197,193)),('ChargeLens',P['led_x'],(242,173,65))]:
    lens=cyl_y(x,P['led_z'],34.15,1.48,5).common(outer)
    lens=lens.fuse(cyl_y(x,P['led_z'],33.7,2.75,.45))
    add(name,'Difusor '+('estado' if x<0 else 'carga')+' · cara al ras',lens,col,note='Resina translúcida / PMMA; probar brillo y retener con silicona neutra. Sin estanqueidad certificada.')

led=cyl_y(-P['led_x'],P['led_z'],25.25,2.5,5.95)
led=led.fuse(Part.makeSphere(2.5,V(-P['led_x'],31.2,P['led_z'])).common(box(-7,31.2,118,6,3,6)))
add('RGBLed','LED Steren Ø5 × 8.45 · cuerpo sin patas',led,(78,149,143),'reference')

# Geometría de referencia tomada del contorno y taladros oficiales; componentes simplificados.
pcb=rounded_xy(20.32,22.86,2.54,0,board_y+11.43,board_z,P['usb_board_thickness_assumed'])
for x,y in holes: pcb=pcb.cut(Part.makeCylinder(1.25,3,V(x,y,board_z-.1)))
add('USBModule','Adafruit 5871 · placa comercial',pcb,(14,97,87),'reference',note='Contorno y agujeros: Eagle oficial. Espesor 1.6 mm provisional.')
usb=rounded_xz(8.94,3.3,1.5,0,uz,uy-7.35,7.35)
usb=usb.cut(rounded_xz(7.2,2.2,1,0,uz,uy-1,1.5))
add('USBReceptacle','USB-C · envolvente y boca',usb,(185,194,204),'reference',note='Anchura/profundidad del footprint CUSB31. Altura 3.3 mm provisional.')
add('USBPortInterior','Interior USB-C · visualización',rounded_xz(7,2,0.9,0,uz,uy-.8,.1),(23,29,34),'reference')
add('USBContactTongue','Lengüeta USB-C · visualización',box(-3,uy-.7,uz-.2,6,.4,.4),(112,127,130),'reference')
add('USBChip','TS3USB30 · reserva de componentes',box(-2,board_y+8,board_z+1.6,4,4,1.2),(33,37,40),'reference')
for i,(x,y) in enumerate(holes):
    screw=Part.makeCylinder(P['m2_shank_diameter']/2,5,V(x,y,board_z+1.6),V(0,0,-1))
    screw=screw.fuse(Part.makeCylinder(P['m2_head_diameter']/2,P['m2_head_height'],V(x,y,board_z+1.6)))
    add('USBScrew'+str(i+1),'M2 × 5 · montaje USB',screw,(145,155,165),'reference')
for i,x in enumerate((-9,9)):
    screw=cyl_y(x,bz,back-2.5,P['m2_shank_diameter']/2,8).fuse(cyl_y(x,bz,back-2.5-P['m2_head_height'],P['m2_head_diameter']/2,P['m2_head_height']))
    add('ButtonScrew'+str(i+1),'M2 × 8 · cartucho botón',screw,(145,155,165),'reference')

# Ensamble de referencia: se omiten grupos compuestos para no duplicar sus sólidos.
excluded={'Plastic','Hardware','References','AssemblyTools','ServiceCover','USBReference','LatchReserve','IMUAlignmentGauge'}
for src in original.Objects:
    if src.Name in excluded or not hasattr(src,'Shape') or src.Shape.isNull(): continue
    shape=src.Shape.copy()
    if src.Name=='MainShell':
        portal=rounded_xz(P['shell_opening_width'],P['shell_opening_top']-P['shell_opening_bottom'],3,0,(P['shell_opening_top']+P['shell_opening_bottom'])/2,20,24)
        shape=shape.cut(portal)
    if src.Name=='Chassis':
        # Despejes locales de repisa/rampas contra el panel actual.
        # Se conserva la espina, base, asiento IMU y ejes de fijacion.
        for cut in P['chassis_clearance_boxes']:
            shape=shape.cut(box(*cut))
    color=(109,123,139) if src.Name in ('MainShell','AntennaCap','Base') else (133,142,151)
    if src.Name=='IMUSeat': color=(232,159,59)
    if 'Reserve' in src.Name or 'Reference' in src.Name: color=(107,158,170)
    add('A5_'+src.Name,src.Label+(' · modificación propuesta' if src.Name in ('MainShell','Chassis') else ' · A5'),shape,color,'context',note='Copia embebida de A5; maestro conservado.')

# Tiny-Adapter original: reubicación de su reserva, sin inventar pinout FPC.
adapter=box(-9,18,143,18,5,18)
add('TinyAdapterPosition','Tiny-Adapter original · nueva reserva vertical',adapter,(87,127,183),'reference',note='Posición propuesta; retención interior y FPC/cable se terminan al integrar módulos reales.')
plug=box(-4.5,18,133.8,9,5,9.2)
add('TinyUSBPlugReserve','Reserva enchufe USB-C interno',plug,(80,86,94),'reference',note='Enchufe compacto de 9.2 mm: reserva de diseño, sin producto cerrado.')

doc.recompute()

def bbox(s):
    b=s.BoundBox
    return [round(v,4) for v in (b.XMin,b.YMin,b.ZMin,b.XMax,b.YMax,b.ZMax)]

# Comprobación de invasión sólida de piezas nuevas contra A5.
checks=[]
targets=[n for n in context if n not in ('A5_IMUTarget',)]
newparts=printed+references
for n in newparts:
    s=objects[n].Shape
    for t in targets:
        q=objects[t].Shape
        if not s.BoundBox.intersect(q.BoundBox): continue
        common=s.common(q)
        if common.Volume>0.001:
            checks.append({'part':n,'against':t,'volume_mm3':round(common.Volume,5),'box':bbox(common)})

# Holguras funcionales y estados de movimiento que importan para el panel.
cap_pressed=cap.copy();cap_pressed.translate(V(0,-(P['button_cap_back_y']-P['button_stop_y']),0))
checks_internal={
 'cap_against_panel_rest_mm3':cap.common(panel).Volume,
 'cap_against_panel_pressed_mm3':cap_pressed.common(panel).Volume,
 'cap_against_cartridge_pressed_mm3':cap_pressed.common(bridge).Volume,
 'cartridge_against_panel_mm3':bridge.common(panel).Volume,
 'usb_board_against_panel_mm3':pcb.common(panel).Volume,
 'usb_connector_against_panel_mm3':usb.common(panel).Volume,
 'button_initial_gap_mm':P['button_cap_back_y']-(back+P['button_total_depth_assumed']),
 'button_hard_stop_travel_mm':P['button_cap_back_y']-P['button_stop_y'],
}
report={'source_sha256_before':initial_hash,'source_sha256_after':hashlib.sha256(SOURCE.read_bytes()).hexdigest(),
 'objects':[{'name':n,'valid':o.Shape.isValid(),'solids':len(o.Shape.Solids),'box':bbox(o.Shape)} for n,o in objects.items()],
 'a5_intersections':checks,'functional_checks':checks_internal,
 'notes':['Sin prueba física. No incluye rutas de arnés ni cargador y biestable montados.','Taladros piloto y dimensiones del AU-101 requieren cupón de ajuste.','Plantilla temporal de alineación IMU se retira antes de instalar panel.']}
(OUT/'fit-report.json').write_text(json.dumps(report,indent=2)+'\n')

# Todos los objetos y caras quedan embebidos; sin enlaces al archivo A5 original.
doc.saveAs(str(OUT/'TresVizo-panel-modules.FCStd'))
Part.export([objects[n] for n in printed+references],str(OUT/'panel-assembly.step'))
Part.export([objects['ModulePanel'],objects['A5_MainShell'],objects['A5_Chassis']],str(OUT/'case-integration.step'))
for n in printed+['A5_MainShell','A5_Chassis']:
    mesh=MeshPart.meshFromShape(Shape=objects[n].Shape,LinearDeflection=.06,AngularDeflection=.12,Relative=False)
    mesh.write(str(OUT/'stl'/(n+'.stl')))

# Cupón antes de imprimir tapa: cavidades nominales 6.2 / 6.4 / 6.6 de izquierda a derecha.
coupon=box(0,0,0,38,15,4)
for x,size in [(6,6.2),(19,6.4),(32,6.6)]:
    coupon=coupon.cut(box(x-size/2,4-size/2,1,size,size,4))
for x,r in [(6,.85),(19,1.1),(32,1.6)]:
    coupon=coupon.cut(Part.makeCylinder(r,5,V(x,11,-.1)))
assert coupon.isValid() and len(coupon.Solids)==1
MeshPart.meshFromShape(Shape=coupon,LinearDeflection=.04,AngularDeflection=.1,Relative=False).write(str(OUT/'stl'/'fit-coupon.stl'))

meshes=[]
for n,o in objects.items():
    vv,ff=o.Shape.tessellate(.16)
    meshes.append({'name':n,'color':colors[n],'vertices':[list(v) for v in vv],'faces':ff})
(OUT/'render-meshes.json').write_text(json.dumps(meshes,separators=(',',':')))
print(json.dumps({'objects':len(objects),'printed':printed,'a5_intersections':checks,'functional_checks':checks_internal,'master_preserved':report['source_sha256_before']==report['source_sha256_after']},indent=2))
App.closeDocument(doc.Name);App.closeDocument(original.Name)
