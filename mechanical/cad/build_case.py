"""Construye el estudio mecanico A0 con FreeCAD. Unidades: milimetros.

Ejecutar desde la consola de FreeCAD o con el Python incluido en FreeCAD.
El JSON contiene cotas de diseno y reservas; no certifica placas comerciales.
"""
import json
import math
from pathlib import Path
import FreeCAD as App
import Part
import MeshPart

HERE = Path(__file__).resolve().parent
OUT = HERE.parent / 'exports' / 'review-a0'
C = json.loads((HERE / 'case-a0.json').read_text())
H = C['height']
S = C['seam_z']
if abs(C['outer_profile_rz'][-1][1] - H) > 1e-8:
    raise ValueError('height debe coincidir con la ultima Z del perfil exterior')
V = App.Vector
Z = V(0, 0, 1)
NAME = 'TresVizoCase_A0'


def box(dx, dy, dz, x, y, z):
    return Part.makeBox(dx, dy, dz, V(x, y, z))


def cyl(r, h, x=0, y=0, z=0, axis=Z):
    return Part.makeCylinder(r, h, V(x, y, z), axis)


def fused(shapes):
    result = shapes[0]
    for shape in shapes[1:]:
        result = result.fuse(shape)
    return result.removeSplitter()


def radius_at(z):
    for (r0, z0), (r1, z1) in zip(C['outer_profile_rz'], C['outer_profile_rz'][1:]):
        if z0 <= z <= z1:
            return r0 + (r1-r0)*(z-z0)/(z1-z0)
    raise ValueError(z)


def profile(z0, z1, offset=0):
    return [(radius_at(z0)+offset, z0)] + [
        (r+offset, z) for r, z in C['outer_profile_rz'] if z0 < z < z1
    ] + [(radius_at(z1)+offset, z1)]


def revolve(points, angle=360):
    pts = [V(r, 0, z) for r, z in points]
    return Part.Face(Part.makePolygon(pts+[pts[0]])).revolve(V(), Z, angle)


def envelope(z0, z1, offset=0):
    return revolve([(0, z0)] + profile(z0, z1, offset) + [(0, z1)])


def ring(ro, ri, z, height):
    return cyl(ro, height, z=z).cut(cyl(ri, height+2, z=z-1))


def radial_bore(angle, z, radius=1.7, start=25, length=18):
    a = math.radians(angle)
    return cyl(radius, length, start*math.cos(a), start*math.sin(a), z,
               V(math.cos(a), math.sin(a), 0))


def rounded_front(width, height, corner, z, y0=20, depth=25):
    # Perfil redondeado en XZ extruido hacia +Y.
    w, h, r = width, height, corner
    return fused([box(w-2*r, depth, h, -w/2+r, y0, z),
                  box(w, depth, h-2*r, -w/2, y0, z+r)] + [
        cyl(r, depth, x, y0, zz, V(0, 1, 0))
        for x in (-w/2+r, w/2-r) for zz in (z+r, z+h-r)
    ])


def flutes(shape, z0, z1, angles, width=2.5, depth=0.55):
    # Canales exteriores poco profundos; no atraviesan la pared nominal.
    pts = profile(z0, z1, -depth) + list(reversed(profile(z0, z1, 2)))
    wedge = revolve(pts, width)
    for a in angles:
        cut = wedge.copy()
        cut.rotate(V(), Z, a-width/2)
        shape = shape.cut(cut)
    return shape.removeSplitter()


def add(doc, group, name, label, shape, color, status, source='', visible=True):
    obj = doc.addObject('PartDesign::Feature', name)
    obj.Label = label
    obj.Shape = shape.removeSplitter()
    obj.addProperty('App::PropertyString', 'Estado', 'Documentacion')
    obj.Estado = status
    obj.addProperty('App::PropertyString', 'Fuente', 'Documentacion')
    obj.Fuente = source
    obj.addProperty('App::PropertyString', 'ColorRGB', 'Presentacion')
    obj.ColorRGB = ','.join(str(v) for v in color)
    obj.addProperty('App::PropertyBool', 'VisibleEnMontaje', 'Presentacion')
    obj.VisibleEnMontaje = visible
    group.addObject(obj)
    if App.GuiUp:
        obj.ViewObject.ShapeColor = color
        obj.ViewObject.LineColor = (0.16, 0.19, 0.22)
        obj.ViewObject.DisplayMode = 'Flat Lines'
        obj.ViewObject.Visibility = visible
    return obj


def build():
    # No cerrar ni reemplazar otros documentos abiertos.
    doc = App.newDocument(NAME)
    doc.Label = 'TresVizo | carcasa A0 - revision mecanica'
    ext = doc.addObject('App::DocumentObjectGroup', 'Exterior')
    ext.Label = '01 - Carcasa / piezas de prototipo'
    ins = doc.addObject('App::DocumentObjectGroup', 'Interior')
    ins.Label = '02 - Bastidor y adaptadores pendientes'
    refs = doc.addObject('App::DocumentObjectGroup', 'References')
    refs.Label = '03 - Componentes / reservas NO validadas'
    datums = doc.addObject('App::DocumentObjectGroup', 'Datums')
    datums.Label = '04 - Referencias mecanicas'
    params = doc.addObject('Spreadsheet::Sheet', 'Dimensions')
    params.Label = 'Cotas A0 / cambiar JSON y regenerar'
    rows = [
        ['COTA / RESERVA', 'mm', 'ESTADO'],
        ['Altura exterior', C['height'], 'Eleccion de diseno A0'],
        ['Diametro maximo', max(r for r,z in C['outer_profile_rz'])*2, 'Eleccion de diseno A0'],
        ['Pared cuerpo radial', C['wall'], 'Canales restan 0.55 mm localmente'],
        ['Pared tapa radial', C['radome_wall'], 'Sin validacion RF'],
        ['Union tapa Z', C['seam_z'], 'Holgura axial 0.4 / radial 0.35'],
        ['ESP32 ancho', 18, 'Plano Waveshare'], ['ESP32 largo', 23.5, 'Plano Waveshare'],
        ['USB ancho/largo', 18, 'Plano Waveshare'], ['USB entre centros', 14, 'Diametro de agujeros no acotado'],
        ['SD ancho', 24, 'Referencia de familia; unidad pendiente'],
        ['SD largo', 42, 'Referencia de familia; unidad pendiente'],
        ['SD patron X/Z', '20 / 38', 'Referencia de familia; verificar'],
        ['Bateria reserva X/Y/Z', '56 / 12 / 69', 'Hipotesis 955565, no bateria seleccionada'],
        ['Carrier UM980 reserva X/Y/Z', '36 / 12 / 64', 'NO son medidas de la carrier'],
        ['Carrier BDLX declarada', '32 / 52 / 11', 'Ficha BDLX, sin plano de agujeros ni alcance de salientes'],
        ['BMI088 reserva X/Y/Z', '28 / 24 / 8', 'NO son medidas del breakout'],
        ['Antena reserva diametro/alto', '46 / 46', 'NO identifica el modelo de antena'],
        ['Origen instrumento', '0,0,0', 'Centro de cara inferior; NO APC/ARP calibrado'],
        ['Frente', '+Y', 'Marca triangular en tapa de servicio'],
        ['Sensor IMU / APC', 'PENDIENTES', 'No usar centro de reserva como origen del sensor']
    ]
    for i, row in enumerate(rows, 1):
        for j, val in enumerate(row):
            params.set(chr(65+j)+str(i), str(val))
    params.setColumnWidth('A', 245)
    params.setColumnWidth('B', 145)
    params.setColumnWidth('C', 370)
    params.setStyle('A1:C1', 'bold', 'add')

    # Cuerpo hueco, collar superior y zocalo independiente.
    body = envelope(12, S).cut(envelope(11.9, S, -C['wall']))
    collar = ring(33.45, 30.65, S-0.5, 6.5)
    # Hombro une el collar con la pared; no introduce disco que cierre el cuerpo.
    body = fused([body, collar, ring(radius_at(S-0.8), 30.65, S-1.2, 1.2)])
    body = flutes(body, 32, S-4, [32,58,122,148,212,238,302,328])
    base = envelope(0, 11.6).cut(cyl(26.5, 9, z=4))
    base = fused([base, ring(28.85, 26.5, 10.5, 7.5)])
    # Zona central maciza, a mecanizar tras elegir inserto metalico del jalon.
    for a in [0, 90, 180, 270]:
        body = body.cut(radial_bore(a, 15, 1.7, 26, 10))
        base = base.cut(radial_bore(a, 15, 1.7, 24, 10))

    cap = envelope(S+0.4, H).cut(envelope(S+0.4, H-2.6, -C['radome_wall']))
    # Alojamiento inferior de espiga, 0.35 mm radial.
    cap = cap.cut(cyl(33.8, 6.4, z=S+0.3))
    cap = flutes(cap, S+9, H-9, [32,58,122,148,212,238,302,328], depth=0.45)
    for a in [45, 135, 225, 315]:
        cap = cap.cut(radial_bore(a, S+3.2, 1.7, 27, 15))
        body = body.cut(radial_bore(a, S+3.2, 1.7, 27, 15))

    # Portillo frontal desmontable. La abertura amplia admite mano/herramienta
    # para el adaptador de desarrollo; el conector de carga no esta definido.
    covermask = rounded_front(28, 53, 5, 89, 22, 22)
    recessmask = rounded_front(28.6, 53.6, 5.3, 88.7, 22, 22)
    outer = envelope(88, 143, 0.6)
    cover = outer.cut(envelope(88, 143, -1.55)).common(covermask)
    body = body.cut(envelope(88, 143, 2).cut(envelope(88, 143, -1.9)).common(recessmask))
    body = body.cut(rounded_front(22, 29, 3, 108, 20, 25))
    for zz in [96, 139]:
        drill = cyl(1.6, 20, 0, 24, zz, V(0, 1, 0))
        body = body.cut(drill)
        cover = cover.cut(drill)
    # Flecha de frente: bajorrelieve, sin boton de medicion ni LEDs inventados.
    tri = Part.Face(Part.makePolygon([V(-4,32,103),V(4,32,103),V(0,32,108),V(-4,32,103)])).extrude(V(0,12,0))
    cover = cover.cut(tri.common(envelope(100, 109, 2).cut(envelope(100, 109, 0.05))))
    bodyobj = add(doc, ext, 'MainShell', 'Cuerpo - pared 2.8 mm', body, (0.79,0.81,0.79), 'DISENO A0; cierre y sellado pendientes')
    capobj = add(doc, ext, 'Radome', 'Tapa antena - pared 2.4 mm', cap, (0.91,0.92,0.88), 'DISENO A0; no validado electromagneticamente')
    baseobj = add(doc, ext, 'Base', 'Base - interfaz jalon pendiente', base, (0.19,0.23,0.25), 'SIN ROSCA; alojamiento metalico pendiente')
    coverobj = add(doc, ext, 'ServiceCover', 'Portillo USB / frente +Y', cover, (0.16,0.21,0.22), 'DISENO A0; retirar para acceso USB; carga pendiente')

    # Bastidor extraible vertical; postes fuera de la reserva de bateria.
    posts = C['frame_post_xy']
    framepieces = [cyl(28.5, 3, z=22)]
    framepieces += [cyl(2.5, 123, x,y,25) for x,y in posts]
    framepieces += [ring(28.5, 21, 114, 3), ring(28.5, 23.8, 145, 3)]
    # Puentes para atornillar las plataformas, con cuatro puntos de fijacion.
    framepieces += [box(50,5,3,-25,y-2.5,zz) for y in (-12,12) for zz in (114,145)]
    # Apoyo inferior de bateria con dos ranuras para cincha, separado de celda.
    framepieces += [box(57,21,3,-28.5,-10.5,35)]
    frame = fused(framepieces)
    for xx in [-20,20]:
        frame = frame.cut(box(2.2,12,5,xx-1.1,-6,34))
    for zz in [114,145]:
        for x,y in posts:
            frame = frame.cut(cyl(1.3,7,x,y,zz-3))
    # Taladros base para fijar bastidor desde el fondo: holgura M3; tuercas pendientes.
    for x,y in posts:
        frame = frame.cut(cyl(1.7,7,x,y,21))
        base = base.fuse(cyl(3.2,18.8,x,y,3))
        base = base.cut(cyl(1.7,5,x,y,-0.5))
        base = base.cut(cyl(1.7,23,x,y,-0.5))
    for xx in [-23,23]:
        for zz in [47,103]:
            frame = frame.cut(cyl(1.4,10,xx,6,zz,V(0,1,0)))
        for zz in [51,89]:
            frame = frame.cut(cyl(1.4,10,xx,-16,zz,V(0,1,0)))
    baseobj.Shape = base.removeSplitter()
    frameobj = add(doc, ins, 'Frame', 'Bastidor extraible / bateria / puentes', frame, (0.25,0.36,0.39), 'DISENO A0; fijaciones y rigidez por validar')

    # Plataforma IMU: rigida, centrada, reemplazable. NO perforar patron ficticio.
    imuplate = box(51,30,2.8,-25.5,-15,117)
    for x,y in posts:
        imuplate = imuplate.cut(cyl(2.75,4,x,y,116.5))
    imuobj = add(doc, ins, 'IMUPlate', 'Plataforma IMU - patron del breakout pendiente', imuplate, (0.86,0.55,0.22), 'ADAPTADOR EN BLANCO; agregar separadores/patron despues del plano real')
    antplate = cyl(28.5,2.6,z=148)
    # Solo paso coaxial de diseno; NO se interpreta como rosca o montaje SMA.
    antplate = antplate.cut(cyl(6,5,z=147))
    for x,y in posts:
        antplate = antplate.cut(cyl(1.7,4,x,y,148))
    antobj = add(doc, ins, 'AntennaPlate', 'Plataforma antena - paso coaxial 12 mm', antplate, (0.86,0.55,0.22), 'PATRON ANTENA PENDIENTE; no es masa RF certificada')

    # Placa frontal de desarrollo y carrier: blanks reemplazables, sin sujecion
    # comercial inventada. Montar carrier requiere patron de agujeros real.
    carrierplate = box(51,2.2,70,-25.5,7,40)
    for xx in [-23,23]:
        for zz in [47,103]:
            carrierplate = carrierplate.cut(cyl(1.4,4,xx,6,zz,V(0,1,0)))
    carrierobj = add(doc, ins, 'GNSSPlate', 'Adaptador carrier UM980 - EN BLANCO', carrierplate, (0.57,0.63,0.64), 'PENDIENTE patron de la carrier; agujeros laterales pertenecen al bastidor')
    # Adaptador SD basado en familia 42 x 24 / patron 38 x 20. La equivalencia
    # con la unidad recibida no se ha confirmado; no presentarlo como definitiva.
    sdplate = box(51,2.2,46,-25.5,-9.2,47)
    for xx in [-10,10]:
        for zz in [51,89]:
            sdplate = sdplate.fuse(cyl(2.2,8.8,xx,-18,zz,V(0,1,0)))
            sdplate = sdplate.cut(cyl(1.1,13,xx,-19,zz,V(0,1,0)))
    for xx in [-23,23]:
        for zz in [51,89]:
            sdplate = sdplate.cut(cyl(1.4,4,xx,-10,zz,V(0,1,0)))
    sdobj = add(doc, ins, 'SDPlate', 'Adaptador microSD - patron de familia 20 x 38', sdplate, (0.57,0.63,0.64), 'PROVISIONAL; comprobar patron con placa real antes de imprimir', 'https://fluxworkshop.com/products/bfaa100021-micro-sd-blue')
    espplate = box(22,2.2,27.5,-11,-17,120.5)
    espobj = add(doc, ins, 'ESPPlate', 'Cuna ESP32 - fijacion final pendiente', espplate, (0.57,0.63,0.64), 'Placa sin agujeros de montaje; retencion y soldaduras pendientes')
    # Soporte USB con patron oficial 14 x 14. Diametro de paso propuesto M2,
    # condicionado al diametro real de la placa, que el plano no especifica.
    usbplate = box(22,22,2.4,-11,6.5,130)
    usbpieces = [usbplate]
    for x in [-7,7]:
        for y in [10.5,24.5]:
            usbpieces.append(cyl(2,1.6,x,y,132.4))
    usbshape = fused(usbpieces)
    for x in [-7,7]:
        for y in [10.5,24.5]:
            usbshape = usbshape.cut(cyl(1.1,6,x,y,129))
    usbobj = add(doc, ins, 'USBPlate', 'Soporte USB - centros 14 x 14', usbshape, (0.57,0.63,0.64), 'CENTROS OFICIALES; taladro 2.2 de diseno pendiente verificar placa y fijacion al bastidor', 'Waveshare ESP32-S3-Tiny / Dimensions')

    # Envolventes de espacio: piezas separadas, no exportadas como fabricables.
    known = 'https://docs.waveshare.com/ESP32-S3-Tiny'
    refobjects = []
    def ref(name,label,shape,color,status,source=''):
        o = add(doc, refs, name,label,shape,color,status,source,False)
        refobjects.append(o)
        return o
    ref('BatteryReserve','RESERVA bateria - 56 x 12 x 69',box(*C['battery_reserve_xyz'],*C['battery_reserve_origin']),(0.45,0.47,0.51),'ESPACIO PROPUESTO; bateria 955565 sin seleccionar')
    ref('GNSSReserve','RESERVA carrier UM980 y salientes',box(*C['gnss_reserve_xyz'],*C['gnss_reserve_origin']),(0.17,0.47,0.30),'Ficha BDLX declara 32 x 52 x 11; esta reserva es 36 x 12 x 64. Agujeros y alcance SMA/USB pendientes','https://www.bdlxgnss.com/?list_22/101.html=')
    ref('IMUReserve','RESERVA BMI088 - NO es su medida',box(*C['imu_reserve_xyz'],*C['imu_reserve_origin']),(0.16,0.47,0.76),'PENDIENTE contorno, agujeros, sensor y ejes reales')
    ref('AntennaReserve','RESERVA Helix - diametro 46 / alto 46',cyl(C['antenna_reserve_diameter']/2,C['antenna_reserve_height'],z=C['antenna_reserve_z']),(0.34,0.35,0.37),'PENDIENTE modelo y dimensiones. NO asumir HA-901A')
    # Placa de referencia ESP: espesor total plano 2.45, sin headers ni cables.
    ref('ESPReference','ESP32-S3-Tiny - envolvente del plano',box(18,2.45,23.5,-9,-20.95,122),(0.11,0.39,0.68),'CONTORNO OFICIAL; no incluye cables o headers soldados',known)
    ref('USBReference','USB Waveshare - reserva altura 5',box(18,18,5,-9,8.5,134),(0.11,0.39,0.68),'18 x 18 y centros 14 x 14 oficiales; altura 5 es reserva de diseno',known)
    ref('SDReference','microSD - referencia familia 24 x 7 x 42',box(24,7,42,-12,-25,49),(0.11,0.39,0.68),'FAMILIA SIMILAR; comprobar revision antes de fijar soportes','https://fluxworkshop.com/products/bfaa100021-micro-sd-blue')
    ref('LatchReserve','RESERVA interruptor con pines - 18 x 12 x 14',box(18,12,14,-9,-24,29),(0.16,0.48,0.26),'ESPACIO PROPUESTO; pines, retencion y modelo por confirmar')
    axis = add(doc, datums, 'PoleAxis', 'Eje mecanico jalon/antena - Z', Part.makeLine(V(0,0,-10),V(0,0,H+11)), (0.9,0.2,0.15),'NO es centro de fase ni origen IMU', visible=False)
    doc.recompute()

    # Validacion CAD, no prueba de montaje ni validacion de hardware real.
    parts = [bodyobj,capobj,baseobj,coverobj,frameobj,imuobj,antobj,carrierobj,sdobj,espobj,usbobj]
    audit = {'revision': C['revision'], 'units':'mm', 'parts':[], 'collisions':[],
             'scope':'Solidos CAD y reservas A0. No valida componentes recibidos, sujetadores, cableado, sellado, RF ni resistencia.'}
    OUT.mkdir(parents=True, exist_ok=True)
    for obj in parts+refobjects:
        s = obj.Shape
        data = {'name':obj.Name,'valid':s.isValid(),'solids':len(s.Solids),'volume_mm3':round(s.Volume,3)}
        audit['parts'].append(data)
        if not data['valid'] or data['solids'] != 1:
            raise RuntimeError('Geometria invalida o desconectada: '+str(data))
    for i,a in enumerate(parts+refobjects):
        for b in (parts+refobjects)[i+1:]:
            volume = a.Shape.common(b.Shape).Volume
            if volume > 0.02:
                audit['collisions'].append({'a':a.Name,'b':b.Name,'volume_mm3':round(volume,3)})
    # Comprueba la insercion axial del bastidor/placas por el extremo superior.
    moving = [frameobj,imuobj,antobj,carrierobj,sdobj,espobj,usbobj]+refobjects
    insertion = []
    for delta in range(0,211,10):
        for o in moving:
            s = o.Shape.copy()
            s.translate(V(0,0,delta))
            volume = s.common(bodyobj.Shape).Volume
            if volume > 0.02:
                insertion.append({'part':o.Name,'lift_mm':delta,'volume_mm3':round(volume,3)})
    audit['axial_extraction_collisions_sampled_10mm'] = insertion
    if audit['collisions'] or insertion:
        (OUT/'cad-checks.json').write_text(json.dumps(audit,indent=2,ensure_ascii=False)+'\n')
        raise RuntimeError('Colisiones CAD pendientes; ver cad-checks.json')
    # STL solo para piezas de prueba. Orientacion de impresion sin optimizar.
    for obj in parts:
        mesh = MeshPart.meshFromShape(Shape=obj.Shape,LinearDeflection=0.08,AngularDeflection=0.15,Relative=False)
        audit.setdefault('meshes',[]).append({'name':obj.Name,'closed':mesh.isSolid(),'facets':mesh.CountFacets})
        mesh.write(str(OUT/(obj.Name+'-PROTOTYPE.stl')))
        Part.export([obj],str(OUT/(obj.Name+'.step')))
    Part.export(parts,str(OUT/'TresVizo-case-A0-structure.step'))
    Part.export(parts+refobjects,str(OUT/'TresVizo-case-A0-with-RESERVES.step'))
    (OUT/'cad-checks.json').write_text(json.dumps(audit,indent=2,ensure_ascii=False)+'\n')
    doc.recompute()
    doc.saveAs(str(HERE/'TresVizo-case-A0.FCStd'))
    print(json.dumps({'document':doc.FileName,'parts':len(parts),'collisions':audit['collisions'],'extraction_collisions':insertion},ensure_ascii=False))
    return doc


if __name__ == '__main__':
    build()
