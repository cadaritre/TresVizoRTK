"""A4: siete piezas estructurales, sin varillas ni adaptadores individuales.

Modelo de revision, unidades mm. Conserva los documentos A0-A3.
"""
import json
import math
from datetime import datetime
from pathlib import Path
import xml.etree.ElementTree as ET
import FreeCAD as App
import Part
import MeshPart
import build_case_a3 as a3
from case_branding import engrave_shell

a2, a1, a0 = a3.a2, a3.a1, a3.a0
V=App.Vector
Z=V(0,0,1)
Y=V(0,1,0)
HERE=Path(__file__).resolve().parent
OUT=HERE.parent/'exports'/'review-a4'
C=json.loads((HERE/'case-a4.json').read_text())
box,cyl,ring,fused=a0.box,a0.cyl,a0.ring,a0.fused


def moved(s, delta):
    r=s.copy(); r.translate(V(*delta)); return r


def slot_y(x1,z1,x2,z2,r,y0,length):
    # Capsula en XZ, extruida en Y.
    length_xz=math.hypot(x2-x1,z2-z1)
    ends=[cyl(r,length,x,y0,z,Y) for x,z in ((x1,z1),(x2,z2))]
    if length_xz>1e-7:
        dx=(x2-x1)/length_xz; dz=(z2-z1)/length_xz
        pts=[V(x1-r*dz,y0,z1+r*dx), V(x2-r*dz,y0,z2+r*dx),
             V(x2+r*dz,y0,z2-r*dx), V(x1+r*dz,y0,z1-r*dx)]
        ends.append(Part.Face(Part.makePolygon(pts+[pts[0]])).extrude(V(0,length,0)))
    return fused(ends)


def radial_slot(r1,r2,angle,r,z0,h):
    a=math.radians(angle)
    p1=(r1*math.cos(a),r1*math.sin(a))
    p2=(r2*math.cos(a),r2*math.sin(a))
    s=slot_y(p1[0],p1[1],p2[0],p2[1],r,0,h)
    s.rotate(V(),V(1,0,0),90)
    s.translate(V(0,0,z0+h))
    return s


def hex_y(af,h,x,y,z):
    s=a1.hexagon(af,h,0)
    s.rotate(V(),V(1,0,0),-90)
    s.translate(V(x,y,z)); return s


def camera_settings(name):
    center=V(0,0,107); height=255
    if 'INTERIOR' in name: center=V(0,0,84); height=200
    if 'EXPLODED' in name: center=V(45,0,110); height=285
    rotation=App.Rotation(V(-1,.4,0),V(0,0,1),V(.4,1,.25),'ZYX')
    eye=rotation.multVec(V(0,0,1))
    position=center+eye*300
    axis=rotation.Axis
    return ('OrthographicCamera {\n position %g %g %g\n orientation %g %g %g %g\n'
            ' nearDistance 1\n farDistance 1000\n aspectRatio 1\n focalDistance 300\n height %g\n}'
            % (position.x,position.y,position.z,axis.x,axis.y,axis.z,rotation.Angle,height))


def make_style(doc, original, aliases, visibility=None):
    # Proveedores nuevos: no heredar extensiones, mapas o materiales binarios
    # de objetos A3 con una topologia distinta. Formato minimo de FreeCAD/BIM
    # OfflineRenderingUtils.buildGuiDocumentFromGuiData.
    root=ET.Element('Document',SchemaVersion='1')
    vp=ET.SubElement(root,'ViewProviderData',Count=str(len(doc.Objects)))
    for o in doc.Objects:
        p=ET.SubElement(vp,'ViewProvider',name=o.Name,expanded='0')
        props=ET.SubElement(p,'Properties',Count='1')
        prop=ET.SubElement(props,'Property',name='Visibility',type='App::PropertyBool')
        show=(visibility or {}).get(o.Name,getattr(o,'VisibleEnMontaje',True))
        ET.SubElement(prop,'Bool',value='true' if show else 'false')
        if hasattr(o,'ColorRGB'):
            color=[round(float(c)*255) for c in o.ColorRGB.split(',')]
            prop=ET.SubElement(props,'Property',name='ShapeColor',type='App::PropertyColor')
            ET.SubElement(prop,'PropertyColor',value=str((color[0]<<24)|(color[1]<<16)|(color[2]<<8)))
            props.attrib['Count']='2'
    ET.SubElement(root,'Camera',settings=camera_settings(doc.Name))
    assets={'GuiDocument.xml':ET.tostring(root,encoding='utf-8',xml_declaration=True)}
    return assets,{o.Name for o in doc.Objects}


def standalone_shape(shape):
    """Conserva el BREP exacto; descarta nombres topologicos de otro documento."""
    result=Part.Shape()
    result.importBrepFromString(shape.exportBrepToString(),False)
    assert result.isValid() and len(result.Solids)==len(shape.Solids)
    assert abs(result.Volume-shape.Volume)<.001
    return result


def build():
    OUT.mkdir(parents=True,exist_ok=True)
    source_path=HERE/'TresVizo-case-A3.FCStd'
    style=a1.presentation(source_path)
    source=App.openDocument(str(source_path))
    doc=App.newDocument('TresVizoCase_A4')
    doc.Label='TresVizo A4 | 7 piezas - base y bandejas integradas'
    plastic=doc.addObject('App::DocumentObjectGroup','Plastic'); plastic.Label='01 IMPRIMIR - 7 piezas A4 / revision'
    hw=doc.addObject('App::DocumentObjectGroup','Hardware'); hw.Label='02 COMPRAR - tornilleria / referencia de inserto'
    refs=doc.addObject('App::DocumentObjectGroup','References'); refs.Label='03 RESERVAS - pendientes de planos reales'
    items=[]; aliases={}
    def add(group,name,label,shape,color,status,template,visible=True,url=''):
        o=doc.addObject('Part::Feature',name); o.Label=label
        try:
            refined=shape.copy().removeSplitter()
            if refined.isValid() and len(refined.Solids)==len(shape.Solids) and abs(refined.Volume-shape.Volume)<.001:
                shape=refined
        except Part.OCCError: pass  # Refino cosmetico; se valida el solido sin refinar.
        o.Shape=standalone_shape(shape)
        for prop,value in [('Estado',status),('Fuente',url),('ColorRGB',','.join(str(v) for v in color))]:
            o.addProperty('App::PropertyString',prop,'Documentacion'); setattr(o,prop,value)
        o.addProperty('App::PropertyBool','VisibleEnMontaje','Presentacion'); o.VisibleEnMontaje=visible
        group.addObject(o)
        items.append(o); aliases[name]=template; return o
    dark=(.19,.23,.25); teal=(.25,.36,.39); amber=(.86,.55,.22)
    # Se conserva la silueta y portillo. Se agregan alojamientos accesibles
    # para tuercas comerciales en el collar superior y el portillo.
    shell=source.MainShell.Shape.copy()
    for angle in (45,135,225,315):
        lug=box(3.2,7.4,6.0,30.25,-3.7,144.2)
        lug.rotate(V(),Z,angle)
        shell=shell.fuse(lug)
        pocket=a1.oriented(a1.hexagon(5.8,2.8,0),angle,30.4)
        pocket.translate(V(0,0,132.2))
        shell=shell.cut(pocket)
        access=box(2.8,6.8,5,30.4,-3.4,147.2)
        access.rotate(V(),Z,angle)
        shell=shell.cut(access).cut(a0.radial_bore(angle,147.2,1.7,29,12))
    for z in (96,139):
        shell=shell.fuse(box(8,2.8 if z==96 else 3.5,7,-4,31.2,z-3.5))
        shell=shell.cut(hex_y(5.8,2.8,0,31.1,z))
        shell=shell.cut(cyl(1.7,12,0,30,z,Y))
    shell,_=engrave_shell(shell,C['branding'])
    add(plastic,'MainShell','A4 01 / cuerpo con simbolo 3 + hexagono grabado',shell,
        (.79,.81,.79),'Logo original sin VIZO: 36 mm alto, grabado radial 0.6 mm bajo portillo. Collar con tuercas M3. Sin grado IP.', 'MainShell',url=C['branding']['source'])
    add(plastic,'ServiceCover','A4 07 / portillo de servicio',source.ServiceCover.Shape.copy(),dark,
        'Portillo desmontable. No equivale a un pulsador exterior ni resuelve la carga.','ServiceCover')

    # Base unica: asiento de brida interior, sin cartucho/tapa/calce.
    # Se representa el barril apuntando hacia arriba, con el apoyo a Z=4.
    # El vaciado central queda abierto: no se inventa una profundidad universal.
    base=fused([a0.envelope(0,11.6),ring(28.85,24,10.5,11.3)])
    base=base.cut(cyl(9.45,7,z=-1))
    base=base.cut(cyl(C['flange_diameter']/2+.3,24,z=4))
    base=base.cut(cyl(24,15,z=9.3))
    for angle in C['base_slot_angles']:
        base=base.cut(radial_slot(*C['base_slot_center_radii'],angle,1.7,-1,7))
        base=base.cut(radial_slot(*C['base_slot_center_radii'],angle,3.25,-.1,2.3))
    for angle in (0,90,180,270):
        base=base.cut(a0.radial_bore(angle,15,1.7,23.5,12))
        base=base.cut(a1.oriented(a1.hexagon(5.8,2.8,0),angle,25.8))
        s=box(2.8,6.8,9,25.8,-3.4,15); s.rotate(V(),Z,angle); base=base.cut(s)
    for x in (-18,18):
        base=base.fuse(cyl(4.6,24,x,10.5,4))
        base=base.cut(cyl(1.7,32,x,10.5,-1))
        base=base.cut(cyl(3.25,2.4,x,10.5,-.1))
    base=base.cut(cyl(C['flange_diameter']/2+.3,5.3,z=4))
    add(plastic,'Base','A4 02 / BASE UNICA - asiento de brida y apoyos',base,dark,
        'Una sola pieza. 3 ranuras radiales de diseno R12..15.5 a 120 grados: confirmar patron del inserto antes de fabricar. Sin tapa/calce/cartucho.','Base')
    flange=fused([ring(C['flange_diameter']/2,15.875/2,4,C['flange_thickness']),
                   ring(C['barrel_diameter']/2,15.875/2,4+C['flange_thickness'],C['barrel_height_catalog'])])
    add(hw,'FlangedInsert','PENDIENTE plano / inserto con brida 5-8-11 UNC',flange,(.88,.68,.25),
        'ENVOLVENTE de 90611A121; sin agujeros ficticios ni helice. Faltan patron/interpretacion del alto y entrega Mexico. No imprimir.','PoleNut',False,C['insert_source'])
    # Reusar solo los cuatro tornillos radiales y sus tuercas comerciales.
    for old in source.Hardware.Group:
        if old.Name.startswith(('RadialNut','RadialBolt')):
            add(hw,old.Name,old.Label,old.Shape.copy(),(.6,.65,.68),old.Estado,old.Name)

    # Bandeja plana con espina de 4 mm, dos bordes anchos y apoyos integrados.
    # La espalda Y=5.3 se apoya en cama; todos los salientes crecen hacia +Y.
    tray=fused([box(52,4,88,-26,5.3,28),
                box(8,4,22,-26,5.3,116),box(8,4,22,18,5.3,116),
                box(52,4,4,-26,5.3,134),box(22,4,27,-11,5.3,138)])
    for x in (-26,22): tray=tray.fuse(box(4,5.6,73,x,9.3,35))
    for x in (-18,18):
        tray=tray.fuse(box(9,8.5,4,x-4.5,5.3,28))
        tray=tray.cut(cyl(1.7,14,x,10.5,27))
        tray=tray.cut(cyl(4,4.8,x,10.5,32))
    for x in (-13.5,13.5):
        tray=tray.fuse(box(10,3.2,63,x-5,9.3,44))
    for sign in (-1,1):
        for z in C['gnss_slot_z_rows']:
            tray=tray.cut(slot_y(sign*10,z,sign*15,z,1.2,4.5,10))
    # Ventana central deja espacio a soldaduras y evita una placa maciza.
    tray=tray.cut(box(14,12,45,-7,4.5,55))
    # USB: la plataforma y sus cuatro apoyos pertenecen a ESTA pieza.
    usb=fused([box(20.4,19.2,2.6,-10.2,9.3,124.4)]+[
        cyl(2.1,2,x,y,127) for x in (-7,7) for y in (12.5,26.5)])
    # Dos nervios anchos conectan plataforma al marco, sin varillas largas.
    usb=usb.fuse(box(52,4,3,-26,9.3,124.4))
    for x in (-7,7):
        for y in (12.5,26.5): usb=usb.cut(cyl(1.1,6,x,y,124))
    tray=tray.fuse(usb)
    # ESP sin taladros: apoyo de borde, topes y dos lenguetas impresas.
    tray=tray.fuse(box(18,3.2,2,-9,9.3,139))
    tray=tray.fuse(box(18,3.2,2,-9,9.3,160.5))
    for x in (-11,9.3): tray=tray.fuse(box(1.7,6.1,24.3,x,9.3,138.6))
    tray=tray.fuse(box(18,6.1,1.5,-9,9.3,137.5))
    for x in (-5,3):
        tray=tray.fuse(box(2,1.5,7,x,10.8,158))
        tray=tray.fuse(box(2,3.6,1.3,x,12.2,163.3))
    # Biestable: cuna integrada frente a la bandeja, fuera del IMU.
    tray=tray.fuse(box(20.6,18.7,2,-10.3,9.3,107.3))
    for x in (-10.8,9.3): tray=tray.fuse(box(1.5,12,15,x,16,108))
    # Uniones entre modulos y referencia IMU: agujeros FIJOS, sin ranuras.
    for x in (-22,22):
        tray=tray.cut(cyl(1.7,14,x,4,113,Y))
        tray=tray.cut(cyl(1.7,14,24.5 if x>0 else -24.5,4,33,Y))
        tray=tray.cut(cyl(1.7,12,x,4,130,Y))
        tray=tray.cut(hex_y(5.8,2.6,x,5.2,130))
    # Fijacion del IMU por orejas a Z114, separada de tornillos de cuna Z113.
    for x in (-22,22):
        tray=tray.cut(cyl(1.7,14,x,4,120,Y))
        tray=tray.cut(hex_y(5.8,2.6,x,5.2,120))
    wire,start,_=a2.route(); coax=a2.tube(wire,start,2.5); channel=a2.tube(wire,start,4)
    tray=tray.cut(slot_y(0,27,0,33,5,4,13))
    for x in (-24.5,24.5): tray=tray.cut(cyl(3.1,7,x,9.3,33,Y))
    add(plastic,'ElectronicsTray','A4 04 / BANDEJA 4 mm - GNSS + USB + ESP + biestable',tray,teal,
        'Una pieza, espalda plana. Ranuras GNSS dan X=10..15 por lado y filas Z49/53/97/101; no es compatibilidad universal. USB centros oficiales 14x14; pasos 2.2 provisionales.','Frame')

    # Cuna abierta superior: se imprime de pie sobre una base amplia.
    # Soporte SD por el reverso integrado; no agrega placa ni separadores.
    cradle=fused([box(56,4,76,-28,-12,35),box(60,17,3,-30,-12,35),
                  box(2.5,14,72,-30.5,-9,38),box(2.5,14,72,28,-9,38)])
    cradle=cradle.common(cyl(30.3,90,z=28))
    for x in (-10,10): cradle=cradle.fuse(box(6,6,59,x-3,-18,35))
    for x in (-10,10):
        for lo,hi in C['sd_slot_z_center_ranges']:
            cradle=cradle.cut(slot_y(x,lo,x,hi,1.2,-19,13))
    for x in (-22,22):
        for z in (33,113):
            xx=x if z==113 else (24.5 if x>0 else -24.5)
            yy=-12 if z==113 else -10
            cradle=cradle.fuse(box(9,5-yy,7,xx-4.5,yy,z-3.5))
            cradle=cradle.cut(cyl(1.7,20,xx,-13,z,Y))
            cradle=cradle.cut(hex_y(5.8,2.7,xx,yy-.1,z))
    # Pasos de cincha opcional de 6 mm; la retencion frontal la da bandeja.
    for z in (44,99):
        for x in (-24,24): cradle=cradle.cut(box(2.4,6,6,x-1.2,-13,z))
    cradle=cradle.common(cyl(30.3,110,z=20))
    add(plastic,'BatteryCradle','A4 05 / CUNA BATERIA + soporte microSD integrado',cradle,teal,
        'Espalda 4 mm, laterales cortos 2.5 nominales y base amplia. Sin placa SD separada. Cargar bateria antes de unir bandejas; holguras/retencion requieren pack real.','Frame')

    # IMU: asiento pequeno, plano y desmontable, con posicion impuesta por
    # dos llaves diferentes. El patron REAL del breakout queda pendiente.
    imu=fused([box(35,31.7,4,-17.5,-16,119),box(52,6.4,4,-26,9.3,119),
               box(8,6.4,12,-26,9.3,111),box(8,6.4,12,18,9.3,111)])
    for x in (-22,22):
        imu=imu.cut(cyl(1.7,9,x,8,120,Y))
        imu=imu.cut(cyl(3.1,9,x,8,113,Y))
    # Dos llaves de distinta longitud entran en muescas abiertas del marco.
    # Separadas de los tornillos de cuna y de fijacion IMU.
    for x,zheight in ((-18.3,3.0),(17.0,4.0)):
        key=box(1.3,4, zheight,x,5.3,119)
        imu=imu.fuse(key)
        tray_cut=box(1.6,4.5,zheight+.3,x-.15,5.1,118.85)
        doc.ElectronicsTray.Shape=doc.ElectronicsTray.Shape.cut(tray_cut)
    add(plastic,'IMUSeat','A4 06 / asiento IMU fijo - sin patron ficticio',imu,amber,
        'Referencia rigida con llaves y dos pasos M3 fijos. Plano del breakout pendiente: NO es soporte del sensor liberado para imprimir.','IMUPlate')
    # Hombro y apoyo de antena fusionados; desaparecen plataforma y 4 postes.
    cap=fused([source.OpenShoulder.Shape.copy(),ring(24.5,8,165,3)])
    cap=cap.cut(cyl(8,30,z=142))
    add(plastic,'AntennaCap','A4 03 / TAPA UNICA + asiento antena + paso coaxial',cap,dark,
        'Una pieza; Ø16 central fijo de diseno para pasar conector, canal coaxial lateral. No es un montaje SMA de panel certificado. Tres agujeros HA901 pendientes de plano.','OpenShoulder')

    # Tornillos de bandejas: geometria simplificada, NO roscas fabricables.
    for i,x in enumerate((-18,18),1):
        bolt=fused([cyl(2.85,1.9,x,10.5,.3),cyl(1.45,35,x,10.5,2.2)])
        add(hw,'TrayBolt'+str(i),'M3 x 35 / base-bandeja '+str(i),bolt,(.4,.43,.46),
            'Cabeza baja en rebaje inferior. Envolvente, verificar cabeza comercial.','RadialBolt1')
        washer=moved(ring(3.5,1.6,32,.5),(x,10.5,0))
        nut=moved(a1.hexagon(5.5,2.4,32.5).cut(cyl(1.5,4,z=32)),(x,10.5,0))
        add(hw,'TrayWasher'+str(i),'Arandela M3 / base-bandeja',washer,(.7,.73,.76),'OD7 ID3.2 x0.5 de referencia.','TieWasher1')
        add(hw,'TrayNut'+str(i),'Tuerca M3 / base-bandeja',nut,(.7,.73,.76),'Tuerca comercial de referencia.','RadialNut1')
        for j,z in enumerate((33,113),1):
            xx=(24.5 if x>0 else -24.5) if z==33 else (22 if x>0 else -22)
            yy=-10 if z==33 else -12
            length=20 if z==33 else 25
            bolt=fused([cyl(1.45,length,xx,9.3-length,z,Y),cyl(2.85,1.7,xx,9.3,z,Y)])
            nut=hex_y(5.5,2.4,xx,yy,z).cut(cyl(1.5,4,xx,yy-.5,z,Y))
            add(hw,f'ModuleBolt{i}{j}',f'M3 x {length} / union bandejas {i}-{j}',bolt,(.4,.43,.46),
                'Cabeza delantera; tuerca cautiva accesible por detras antes de meter bateria.','RadialBolt1')
            add(hw,f'ModuleNut{i}{j}','Tuerca M3 / union bandejas',nut,(.7,.73,.76),'Tuerca cautiva, sin adhesivo.','RadialNut1')
        x=22 if x>0 else -22
        bolt=fused([cyl(1.45,12,x,3.7,120,Y),cyl(2.85,1.7,x,15.7,120,Y)])
        nut=hex_y(5.5,2.4,x,5.4,120).cut(cyl(1.5,4,x,5,120,Y))
        add(hw,'IMUBolt'+str(i),'M3 x 12 / soporte IMU fijo',bolt,(.4,.43,.46),
            'Fija soporte impreso; NO sustituye los tornillos del breakout.','RadialBolt1')
        add(hw,'IMUNut'+str(i),'Tuerca M3 / soporte IMU fijo',nut,(.7,.73,.76),'Tuerca cautiva; llaves limitan movimiento.','RadialNut1')

    # Referencias nuevas que explicitan el empaquetado; nunca STL imprimible.
    reference_specs=[
        ('BatteryReserve','RESERVA bateria 56 x 12 x 69',box(56,12,69,-28,-7.5,38),'Bateria final pendiente; desplazada 1.5 mm hacia -Y.'),
        ('GNSSReserve','RESERVA carrier UM980 / 36 x 12 x 64',source.GNSSReserve.Shape.copy(),'Carrier y salientes: reserva conservada; centros comerciales sin confirmar.'),
        ('SDReference','RESERVA microSD / familia 24 x 7 x 42',source.SDReference.Shape.copy(),'Ranuras permiten 4 mm en Z; familia y diametro mecanico por confirmar.'),
        ('IMUReserve','RESERVA BMI088 / plano real pendiente',box(28,24,8,-14,-15,123),'No representa agujeros ni centro del chip. Contacto nominal con plano rigido.'),
        ('USBReference','USB 18 x 18 / altura reservada 5',box(18,18,5,-9,10.5,129),'Patron 14x14 oficial, espesor/salientes/fijacion final pendientes.'),
        ('ESPReference','ESP32 Tiny 18 x 23.5 x 2.45',box(18,2.45,23.5,-9,12.5,139),'Retencion por borde provisional; comprobar pads y FPC, sin usar contactos como agujeros.'),
        ('LatchReserve','RESERVA biestable / SIN pulsador exterior',box(18,12,14,-9,16,109.3),'Pines/retencion y circuito de encendido pendientes.'),
        ('HA901Reserve','RESERVA antena externa HA901 / Ø46 x 46',source.HA901Reserve.Shape.copy(),'Etiqueta identificada; no replica, sin patron ni APC calibrado.')]
    for name,label,shape,status in reference_specs:
        old=source.getObject(name)
        color=tuple(float(x) for x in old.ColorRGB.split(','))
        add(refs,name,label,shape,color,status,name,name=='HA901Reserve')
    # Espacio coaxial se puede mostrar desde arbol; no es pieza a fabricar.
    add(refs,'CoaxRouteReserve','AZUL / recorrido coaxial Ø5, radio minimo 10',coax,(.06,.5,.93),
        'Reserva de paso, conectores y cable final pendientes. Visible en documento interior.','USBReference',False)
    plastic.addProperty('App::PropertyString','Revision','Documentacion'); plastic.Revision='A4'
    plastic.addProperty('App::PropertyString','FechaGeneracion','Documentacion'); plastic.FechaGeneracion=datetime.now().isoformat(timespec='seconds')
    plastic.addProperty('App::PropertyString','Pendientes','Documentacion')
    plastic.Pendientes='IMU/antena: plano real. Inserto: patron. Encendido/carga, tolerancias, montaje y ensayo fisico.'
    doc.recompute()

    checks={'revision':'A4','generated_at':datetime.now().isoformat(timespec='seconds'),
            'printed_part_count':len(plastic.Group),'custom_metal_parts':0,'parts':[],
            'collisions':[],'coax_collisions':[],'extraction_collisions':[],
            'limits':C['notes'],'meshes':[]}
    physical=[o for o in items if o.Name!='CoaxRouteReserve']
    for o in physical:
        s=o.Shape
        checks['parts'].append({'name':o.Name,'valid':s.isValid(),'solids':len(s.Solids),'volume_mm3':round(s.Volume,3)})
        if not s.isValid() or len(s.Solids)!=1:
            print('INVALID',o.Name,s.isValid(),[(v.Volume,str(v.BoundBox)) for v in s.Solids],flush=True)
        assert s.isValid() and len(s.Solids)==1,o.Name
        if s.common(coax).Volume>.02: checks['coax_collisions'].append({'part':o.Name,'mm3':s.common(coax).Volume})
    for i,o in enumerate(physical):
        for p in physical[i+1:]:
            if not o.Shape.BoundBox.intersect(p.Shape.BoundBox): continue
            volume=o.Shape.common(p.Shape).Volume
            if volume>.02: checks['collisions'].append({'a':o.Name,'b':p.Name,'mm3':round(volume,4)})
    # El conjunto de bandejas sale por arriba despues de retirar tapa/antena.
    moving=[doc.getObject(n) for n in ('ElectronicsTray','BatteryCradle','IMUSeat','BatteryReserve','GNSSReserve','SDReference','IMUReserve','USBReference','ESPReference','LatchReserve')]
    moving += [o for o in hw.Group if o.Name.startswith(('Module','IMUBolt','IMUNut'))]
    for dz in range(0,181,5):
        for o in moving:
            s=moved(o.Shape,(0,0,dz))
            if s.BoundBox.intersect(doc.MainShell.Shape.BoundBox):
                volume=s.common(doc.MainShell.Shape).Volume
                if volume>.02: checks['extraction_collisions'].append({'part':o.Name,'lift_mm':dz,'mm3':round(volume,4)})
    (OUT/'cad-checks.json').write_text(json.dumps(checks,indent=2,ensure_ascii=False)+'\n')
    a1.save_preserving_presentation(doc,HERE/'TresVizo-case-A4.FCStd',make_style(doc,style,aliases))
    if checks['collisions'] or checks['coax_collisions'] or checks['extraction_collisions']:
        print(json.dumps({k:checks[k] for k in ('collisions','coax_collisions','extraction_collisions')},ensure_ascii=False))
        raise RuntimeError('Resolver colisiones A4 antes de exportar')
    orientations={'ElectronicsTray':('X',90),'IMUSeat':('X',180),'AntennaCap':('X',180)}
    for o in plastic.Group:
        s=o.Shape.copy()
        if o.Name in orientations: s.rotate(V(),V(1,0,0),orientations[o.Name][1])
        bb=s.BoundBox; s.translate(V(-bb.XMin,-bb.YMin,-bb.ZMin))
        mesh=MeshPart.meshFromShape(Shape=s,LinearDeflection=.1,AngularDeflection=.16,Relative=False)
        checks['meshes'].append({'name':o.Name,'closed':mesh.isSolid(),'print_bounds_mm':[round(v,2) for v in (s.BoundBox.XLength,s.BoundBox.YLength,s.BoundBox.ZLength)]})
        assert mesh.isSolid(),o.Name
        mesh.write(str(OUT/(o.Name+'-ORIENTED-REVIEW.stl')))
        Part.export([o],str(OUT/(o.Name+'.step')))
    Part.export(physical,str(OUT/'TresVizo-case-A4-with-RESERVES.step'))
    (OUT/'cad-checks.json').write_text(json.dumps(checks,indent=2,ensure_ascii=False)+'\n')
    # Documentos de revision independientes; ninguna vista modifica el A3.
    for suffix,hidden,exploded in [('INTERIOR',{'MainShell','ServiceCover','AntennaCap','HA901Reserve','FlangedInsert'},False),
                                    ('EXPLODED',set(),True)]:
        rev=App.newDocument('TresVizo_A4_'+suffix)
        rev.Label='TresVizo A4 | '+('INTERIOR - bandejas integradas' if not exploded else 'DESPIECE - 7 piezas impresas')
        names={}
        for o in items:
            if o.Name in hidden: continue
            if exploded and o not in plastic.Group: continue
            n=rev.addObject('Part::Feature',o.Name); n.Label=o.Label
            s=o.Shape.copy()
            if exploded:
                delta={'MainShell':(100,0,0),'Base':(0,0,-25),'ServiceCover':(100,30,0),
                       'ElectronicsTray':(0,40,0),'BatteryCradle':(0,-40,0),
                       'IMUSeat':(0,0,25),'AntennaCap':(0,0,40)}[o.Name]
                s.translate(V(*delta))
            n.Shape=standalone_shape(s); names[n.Name]=aliases[o.Name]
            for prop in ('ColorRGB','Estado','Fuente'):
                n.addProperty('App::PropertyString',prop,'Documentacion')
                setattr(n,prop,getattr(o,prop))
        rev.recompute()
        a1.save_preserving_presentation(rev,HERE/('TresVizo-case-A4-'+suffix+'.FCStd'),make_style(rev,style,names,{o.Name:True for o in rev.Objects}))
    print(json.dumps({'file':doc.FileName,'printed_parts':len(plastic.Group),'solid_count':len(physical),'collisions':0,'coax_collisions':0,'extraction_collisions':0}))


if __name__=='__main__': build()
