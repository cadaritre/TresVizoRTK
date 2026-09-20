"""Revision A1 sobre el estudio A0 conservado. Todas las cotas en mm.

FreeCAD debe importarse antes de Part en el Python incluido en macOS.
El archivo de origen A0 no se modifica. No modela helices de las roscas.
"""
import json
import math
from pathlib import Path
import xml.etree.ElementTree as ET
import zipfile
import FreeCAD as App
import Part
import MeshPart
import build_case as a0

HERE = Path(__file__).resolve().parent
OUT = HERE.parent / 'exports' / 'review-a1'
C = json.loads((HERE / 'case-a1.json').read_text())
V, Z = App.Vector, App.Vector(0, 0, 1)
box, cyl, fused, ring, revolve = a0.box, a0.cyl, a0.fused, a0.ring, a0.revolve


def presentation(path):
    """Conserva estilos guardados por FreeCAD GUI al regenerar sin interfaz."""
    if not path.exists(): return {}, set()
    with zipfile.ZipFile(path) as archive:
        if 'GuiDocument.xml' not in archive.namelist(): return {}, set()
        xml=archive.read('GuiDocument.xml')
        root=ET.fromstring(xml)
        names={e.attrib['name'] for e in root.findall('.//ViewProvider')}
        files={'GuiDocument.xml'} | {e.attrib['file'] for e in root.iter() if 'file' in e.attrib}
        assets={n:archive.read(n) for n in files if n in archive.namelist()}
    return assets,names


def save_preserving_presentation(doc,path,previous):
    assets,names=previous
    doc.saveAs(str(path))
    # Sólo reutilizar vista si coinciden todos los objetos. No copiar BREP,
    # Document.xml, miniaturas viejas ni información topológica.
    if not App.GuiUp and assets and names=={o.Name for o in doc.Objects}:
        with zipfile.ZipFile(path) as archive:
            files={n:archive.read(n) for n in archive.namelist()}
        files.update(assets)
        temporary=path.with_suffix('.FCStd.tmp')
        with zipfile.ZipFile(temporary,'w',zipfile.ZIP_DEFLATED) as archive:
            for name,data in files.items(): archive.writestr(name,data)
        temporary.replace(path)


def hexagon(af, h, z):
    r = af / math.sqrt(3)
    pts = [V(r*math.cos(math.radians(30+i*60)),
             r*math.sin(math.radians(30+i*60)), z) for i in range(6)]
    return Part.Face(Part.makePolygon(pts + [pts[0]])).extrude(V(0, 0, h))


def oriented(shape, angle, start):
    s = shape.copy()
    s.rotate(V(), V(0, 1, 0), 90)
    s.translate(V(start, 0, 15))
    s.rotate(V(), Z, angle)
    return s


def build():
    OUT.mkdir(parents=True, exist_ok=True)
    target=HERE/'TresVizo-case-A1.FCStd'
    section_target=HERE/'TresVizo-case-A1-MOUNT-SECTION.FCStd'
    previous=presentation(target)
    previous_section=presentation(section_target)
    source = App.openDocument(str(HERE / 'TresVizo-case-A0.FCStd'))
    doc = App.newDocument('TresVizoCase_A1')
    doc.Label = 'TresVizo A1 | HA-901A externa + jalon 5-8'
    plastic = doc.addObject('App::DocumentObjectGroup', 'Plastic')
    plastic.Label = '01 Plasticos de prototipo'
    metal = doc.addObject('App::DocumentObjectGroup', 'Metal')
    metal.Label = '02 Placas METALICAS a fabricar'
    hardware = doc.addObject('App::DocumentObjectGroup', 'Hardware')
    hardware.Label = '03 Herrajes comerciales / geometria simplificada'
    references = doc.addObject('App::DocumentObjectGroup', 'References')
    references.Label = '04 Reservas electronicas NO son piezas fabricables'
    items = []

    def add(group, name, label, shape, color, status, source_url='', visible=True):
        o = a0.add(doc, group, name, label, shape, color, status, source_url, visible)
        items.append(o)
        return o

    replacements = {'Radome', 'Base', 'Frame', 'AntennaPlate', 'AntennaReserve'}
    ref_names = {o.Name for o in source.References.Group}
    for old in source.Objects:
        if not hasattr(old, 'ColorRGB') or old.Name in replacements or old.Name == 'PoleAxis':
            continue
        color = tuple(float(n) for n in old.ColorRGB.split(','))
        is_ref = old.Name in ref_names
        add(references if is_ref else plastic, old.Name, old.Label, old.Shape.copy(),
            color, 'HEREDADO A0: '+old.Estado, old.Fuente, not is_ref)

    bolts = [(C['mount_bolt_radius']*math.cos(math.radians(a)),
              C['mount_bolt_radius']*math.sin(math.radians(a))) for a in (45, 135, 225, 315)]

    # Cupula A0 sustituida por hombro abierto. Todo el cilindro de la antena
    # queda encima; la reserva no reproduce detalles ni orificios comerciales.
    shoulder = revolve([(37,144.4),(36,151),(30,158),(24.5,164),(24.5,167),
                        (23.3,167),(23.3,163),(28,156),(33.8,150.5),(33.8,144.4)])
    for a in (45,135,225,315):
        shoulder = shoulder.cut(a0.radial_bore(a,147.2,1.7,27,15))
    add(plastic,'OpenShoulder','Hombro abierto - sin segundo radomo',shoulder,
        (0.19,0.23,0.25),'DISENO A1; cierre inferior heredado A0, sellado pendiente')

    antenna_support = source.AntennaPlate.Shape.copy()
    antenna_support = antenna_support.fuse(cyl(22.8,3,z=165).cut(cyl(7,5,z=164)))
    for x in (-14,14):
        for y in (-14,14):
            antenna_support = antenna_support.fuse(cyl(2,14.4,x,y,150.6))
    add(plastic,'AntennaSupport','Puente HA-901A - patron de 3 agujeros PENDIENTE',
        antenna_support,(0.86,0.55,0.22),
        'Soporte inferior y paso coaxial de diseno. NO perforar patron ficticio ni cargar el conector SMA.')
    add(references,'HA901Reserve','HA-901A / RESERVA 46 x 46, no medida certificada',
        cyl(C['antenna_reserve_diameter']/2,C['antenna_reserve_height'],z=C['antenna_base_z']),
        (0.12,0.13,0.15),'Modelo de foto identificado; dimensiones/patron/IP/APC por confirmar',
        'Captura del propietario 2026-09-19; etiqueta HA-901A', True)

    # Base reforzada: cartucho interno; espiga exterior encaja en el cuerpo A0.
    base = fused([a0.envelope(0,11.6), cyl(28.85,11.3,z=10.5)])
    base = base.cut(cyl(8.5,25,z=-1))
    base = base.cut(cyl(C['plate_radius']+0.2,6.1,z=-0.1))
    base = base.cut(hexagon(C['plastic_pocket_af'],12.0,5.9))
    base = base.cut(cyl(C['plate_radius']+0.2,4.3,z=C['upper_plate_z']))
    # Asientos originales de bastidor, conservan la cota Z=22 del conjunto A0.
    for x,y in a0.C['frame_post_xy']:
        base = base.fuse(cyl(3.2,0.8,x,y,21.0))
        base = base.cut(cyl(1.7,24,x,y,-0.5))
    for x,y in bolts:
        base = base.cut(cyl(3.2,24,x,y,-1))
    # Tuercas radiales M3 deslizables desde arriba; retienen cuerpo y base.
    for a in (0,90,180,270):
        base = base.cut(a0.radial_bore(a,15,1.7,23.5,12))
        base = base.cut(oriented(hexagon(5.8,2.8,0),a,25.8))
        # Paso de insercion >= ancho ENTRE VERTICES de la tuerca orientada.
        slot = box(2.8,6.8,9,25.8,-3.4,15)
        slot.rotate(V(),Z,a)
        base = base.cut(slot)
    add(plastic,'Base','Base A1 - captura axial y hexagonal del cartucho',base,
        (0.19,0.23,0.25),'Prototipo. 4 tuercas radiales M3 cautivas; cargas y tolerancias sin ensayar.')

    frame = source.Frame.Shape.copy()
    for x,y in bolts:
        frame = frame.cut(cyl(2.25,5,x,y,21))
    add(plastic,'Frame','Bastidor A1 - 4 pasos M4 al cartucho',frame,
        (0.25,0.36,0.39),'Hereda pendientes A0; fijacion inferior ahora con pernos pasantes M4.')

    plate_color=(0.68,0.74,0.77)
    low = ring(C['plate_radius'],8.5,0,3)
    key = cyl(C['plate_radius'],3,z=3).cut(hexagon(C['key_pocket_af'],5,2))
    upper = ring(C['plate_radius'],8.5,C['upper_plate_z'],3)
    for x,y in bolts:
        for which in ('low','key','upper'):
            shape = {'low':low,'key':key,'upper':upper}[which].cut(cyl(2.25,25,x,y,-1))
            if which=='low':
                shape = shape.cut(Part.makeCone(4.5,2.25,2.25,V(x,y,0),Z))
                low=shape
            elif which=='key': key=shape
            else: upper=shape
    add(metal,'LowerLoadPlate','Acero 3 mm / placa inferior de apoyo',low,plate_color,
        'FABRICAR EN METAL; 4 avellanados 90 grados, mayor diametro 9.0. No imprimir para servicio.')
    add(metal,'HexKeyPlate','Acero 3 mm / llave hexagonal AF 24.15',key,(0.42,0.48,0.53),
        'FABRICAR EN METAL; perfil hexagonal bloquea giro. Desbarbar y ensayar ajuste con tuerca comprada.')
    add(metal,'UpperRetainer','Acero 3 mm / placa superior de retencion',upper,plate_color,
        'FABRICAR EN METAL; retiene extraccion axial. Calces requeridos segun altura real de la tuerca.')
    nut = hexagon(C['nut_af_max'],C['nut_height_max'],C['nut_z']).cut(cyl(15.875/2,18,z=2))
    add(hardware,'PoleNut','COMPRAR tuerca hexagonal 5-8-11 UNC-2B',nut,(0.88,0.68,0.25),
        'HN58 / equivalencia dimensional. Taladro CAD nominal simplificado, no diametro de broca ni rosca fabricable.',C['nut_source'])
    shim_z=C['nut_z']+C['nut_height_max']
    add(metal,'NutShim','Calce de ajuste - espesor seleccionado al montar',ring(12,8.5,shim_z,C['upper_plate_z']-shim_z),
        (0.82,0.58,0.22),'Espesor CAD 0.5014 para tuerca de altura maxima. Rango teorico 0.5014 a 1.111 mm; medir antes de elegir.')

    for i,(x,y) in enumerate(bolts,1):
        for label,z,h in [('Lower',6,11.7),('Upper',20.7,1.3)]:
            spacer=ring(3,2.15,z,h)
            spacer.translate(V(x,y,0))
            add(metal,f'{label}Spacer{i}',f'Casquillo metalico {label} {i} / largo {h}',spacer,
                plate_color,'OD 6 / ID 4.3. Longitud de diseno; ajustar tolerancias para repartir precarga con tuerca.')
        screw=fused([Part.makeCone(4.3,2,2.3,V(x,y,0),Z),cyl(2,27.7,x,y,2.3)])
        add(hardware,f'TieBolt{i}',f'REF tornillo avellanado M4 x 30 / {i}',screw,(0.37,0.4,0.43),
            'Envolvente simplificada; longitud total 30. Elegir cabeza compatible con avellanado y verificar norma/proveedor.')
        washer=ring(4.5,2.15,25,0.8); washer.translate(V(x,y,0))
        add(hardware,f'TieWasher{i}',f'REF arandela M4 / {i}',washer,plate_color,'Envolvente de diseno OD 9 / ID 4.3 / espesor 0.8.')
        mn=hexagon(7,3.2,25.8).cut(cyl(2.1,5,z=25)); mn.translate(V(x,y,0))
        add(hardware,f'TieNut{i}',f'REF tuerca M4 / {i}',mn,plate_color,'Rosca simplificada; verificar herraje y seguro contra aflojamiento.')
    for i,a in enumerate((0,90,180,270),1):
        rn=hexagon(5.5,2.4,0).cut(cyl(1.55,4,z=-0.5))
        add(hardware,f'RadialNut{i}',f'REF tuerca cautiva M3 radial / {i}',oriented(rn,a,26),
            plate_color,'Se coloca por ranura superior ANTES de cerrar base.')
        rs=fused([cyl(1.45,8,z=0),cyl(2.75,1.7,z=8)])
        add(hardware,f'RadialBolt{i}',f'REF tornillo radial M3 x 8 / {i}',oriented(rs,a,24.5),
            (0.37,0.4,0.43),'Retencion de cuerpo/base; cabeza y longitud deben verificarse con herraje comprado.')

    sheet=doc.addObject('Spreadsheet::Sheet','Dimensions')
    sheet.Label='A1 / cotas informativas, editar JSON y regenerar'
    rows=[['DATO','VALOR','ESTADO'],['Rosca propuesta','5/8-11 UNC-2B','Confirmar jalon'],
          ['Tuerca AF max',C['nut_af_max'],'HN58'],['Altura tuerca max',C['nut_height_max'],'HN58'],
          ['Hexagono placa',C['key_pocket_af'],'Diseno, verificar corte'],
          ['Altura conjunto / reserva',214,'Antena real pendiente plano'],
          ['Base de reserva antena Z',168,'No es APC ni ARP calibrado'],
          ['Antena','HA-901A','Patron 3 agujeros sin documentar'],
          ['Placas','Acero, 3 mm','No imprimir en plastico'],
          ['Validacion','Solo geometria CAD','Sin ensayo de carga, sellado o RF']]
    for i,row in enumerate(rows,1):
        for j,val in enumerate(row): sheet.set(chr(65+j)+str(i),str(val))
    for column,width in [('A',220),('B',230),('C',310)]: sheet.setColumnWidth(column,width)
    sheet.setStyle('A1:C1','bold','add')
    doc.recompute()
    audit={'revision':C['revision'],'scope':'Geometria simplificada A1, no valida roscas, precarga, cargas, hardware real, RF o sellado.',
           'parts':[],'collisions':[],'meshes':[]}
    for o in items:
        s=o.Shape
        row={'name':o.Name,'valid':s.isValid(),'solids':len(s.Solids),'volume_mm3':round(s.Volume,4)}
        audit['parts'].append(row)
        if not row['valid'] or row['solids']!=1 or s.Volume<=0: raise RuntimeError(str(row))
    for i,o in enumerate(items):
        for p in items[i+1:]:
            if not o.Shape.BoundBox.intersect(p.Shape.BoundBox): continue
            vol=o.Shape.common(p.Shape).Volume
            if vol>0.02: audit['collisions'].append({'a':o.Name,'b':p.Name,'volume_mm3':round(vol,4)})
    insertion=[]
    for i in range(1,5):
        for k in range(25):
            shape=doc.getObject('RadialNut'+str(i)).Shape.copy()
            shape.translate(V(0,0,k*0.5))
            volume=shape.common(doc.Base.Shape).Volume
            if volume>0.02: insertion.append({'nut':i,'lift':k*0.5,'volume':volume})
    audit['radial_nut_insertion_collisions_sampled_0_5mm']=insertion
    (OUT/'cad-checks.json').write_text(json.dumps(audit,indent=2,ensure_ascii=False)+'\n')
    if audit['collisions'] or insertion: raise RuntimeError('Colisiones A1: '+str(audit))
    for group in (plastic,metal):
        for o in group.Group:
            Part.export([o],str(OUT/(o.Name+('.step' if group==plastic else '-METAL.step'))))
            if group==plastic:
                mesh=MeshPart.meshFromShape(Shape=o.Shape,LinearDeflection=0.1,AngularDeflection=0.16,Relative=False)
                audit['meshes'].append({'name':o.Name,'closed':mesh.isSolid(),'facets':mesh.CountFacets})
                if not mesh.isSolid(): raise RuntimeError('Malla abierta: '+o.Name)
                mesh.write(str(OUT/(o.Name+'-PROTOTYPE.stl')))
    Part.export(items,str(OUT/'TresVizo-case-A1-with-RESERVES.step'))
    (OUT/'cad-checks.json').write_text(json.dumps(audit,indent=2,ensure_ascii=False)+'\n')
    doc.recompute()
    save_preserving_presentation(doc,target,previous)
    # Seccion separada reproducible tambien sin GUI. Nunca se exporta a STL.
    section=App.newDocument('TresVizoMount_A1')
    section.Label='TresVizo A1 | CORTE del cartucho - no fabricar el corte'
    cut=box(100,100,60,-50,0,-1)
    for o in items:
        if o.Name not in ('Base','Frame') and o not in metal.Group and o not in hardware.Group: continue
        shape=o.Shape.copy()
        if o.Name=='Frame': shape=shape.common(box(80,80,7,-40,-40,21))
        shape=shape.cut(cut)
        if shape.isNull() or shape.Volume<0.001: continue
        n=section.addObject('PartDesign::Feature',o.Name)
        n.Label=o.Label
        n.Shape=shape
    section.recompute()
    save_preserving_presentation(section,section_target,previous_section)
    print(json.dumps({'document':doc.FileName,'solids':len(items),'collisions':audit['collisions']},ensure_ascii=False))
    return doc


if __name__=='__main__':
    build()
