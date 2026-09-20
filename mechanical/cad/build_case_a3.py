"""A3: base, tapa y calce impresos; solo tornilleria comercial de metal.

Conserva A2, incluido el paso coaxial. Roscas representadas sin helices.
"""
import copy
import json
import math
import xml.etree.ElementTree as ET
from pathlib import Path
import FreeCAD as App
import Part
import MeshPart
import build_case_a2 as a2

a1=a2.a1
a0=a1.a0
V=App.Vector
HERE=Path(__file__).resolve().parent
OUT=HERE.parent/'exports'/'review-a3'
C=json.loads((HERE/'case-a3.json').read_text())


def styles(doc, original, aliases=None):
    """Conserva materiales nativos sin reutilizar geometria ni abrir la GUI."""
    assets=original[0].copy()
    if 'GuiDocument.xml' not in assets: return {},set()
    root=ET.fromstring(assets['GuiDocument.xml'])
    providers=root.find('ViewProviderData')
    templates={p.attrib['name']:p for p in providers}
    for p in list(providers): providers.remove(p)
    for o in doc.Objects:
        p=copy.deepcopy(templates[(aliases or {}).get(o.Name,o.Name)])
        p.attrib['name']=o.Name
        visibility=p.find(".//Property[@name='Visibility']/Bool")
        if visibility is not None:
            visibility.attrib['value']='true' if not hasattr(o,'VisibleEnMontaje') or o.VisibleEnMontaje else 'false'
        providers.append(p)
    providers.attrib['Count']=str(len(doc.Objects))
    assets['GuiDocument.xml']=ET.tostring(root,encoding='utf-8',xml_declaration=True)
    return assets,{o.Name for o in doc.Objects}


def build():
    OUT.mkdir(parents=True,exist_ok=True)
    source_path=HERE/'TresVizo-case-A2.FCStd'
    original=a1.presentation(source_path)
    source=App.openDocument(str(source_path))
    doc=App.newDocument('TresVizoCase_A3')
    doc.Label='TresVizo A3 | montaje impreso + tornilleria comercial'
    plastic=doc.addObject('App::DocumentObjectGroup','Plastic')
    plastic.Label='01 Piezas impresas - prototipo'
    hardware=doc.addObject('App::DocumentObjectGroup','Hardware')
    hardware.Label='02 Solo tornillos, tuercas y arandelas comerciales'
    refs=doc.addObject('App::DocumentObjectGroup','References')
    refs.Label='03 Reservas electronicas - NO imprimir'
    items=[]

    def add(group,name,label,shape,color,status,url='',visible=True):
        o=a0.add(doc,group,name,label,shape,color,status,url,visible)
        items.append(o)
        return o

    excluded={'Base','Frame','LowerLoadPlate','HexKeyPlate','UpperRetainer','NutShim','PoleNut'}
    excluded.update(f'{end}Spacer{i}' for end in ('Lower','Upper') for i in range(1,5))
    for old in source.Objects:
        if not hasattr(old,'ColorRGB') or old.Name in excluded: continue
        group=refs if old in source.References.Group else hardware if old in source.Hardware.Group else plastic
        add(group,old.Name,old.Label,old.Shape.copy(),tuple(float(v) for v in old.ColorRGB.split(',')),
            old.Estado,old.Fuente,old.VisibleEnMontaje)

    bolt_xy=[(C['mount_bolt_radius']*math.cos(math.radians(a)),
              C['mount_bolt_radius']*math.sin(math.radians(a))) for a in (45,135,225,315)]
    r=C['stud_clearance_diameter']/2
    # Z=0 es el apoyo del jalon. Suelo de 4 mm bajo la tuerca; hexagono
    # integral hasta la tapa. No hay placas ni separadores metalicos.
    base=a0.fused([a0.envelope(0,11.6),a0.cyl(28.85,11.3,z=10.5)])
    base=base.cut(a0.cyl(r,25,z=-1))
    base=base.cut(a1.hexagon(C['hex_pocket_af'],20,C['nut_z']))
    base=base.cut(a0.cyl(C['retainer_radius']+0.2,6,z=C['retainer_z']))
    for x,y in bolt_xy:
        base=base.cut(a0.cyl(2.25,25,x,y,-1))
        base=base.cut(Part.makeCone(4.5,2.25,2.25,V(x,y,0),V(0,0,1)))
    # Se conservan los cuatro tornillos horizontales que unen cuerpo/base.
    for angle in (0,90,180,270):
        base=base.cut(a0.radial_bore(angle,15,1.7,23.5,12))
        base=base.cut(a1.oriented(a1.hexagon(5.8,2.8,0),angle,25.8))
        slot=a0.box(2.8,6.8,9,25.8,-3.4,15)
        slot.rotate(V(),V(0,0,1),angle)
        base=base.cut(slot)
    add(plastic,'Base','IMPRIMIR base A3 / hexagono integral AF24.25',base,(0.19,0.23,0.25),
        'Suelo 4 mm. Captura hexagonal y apoyo del jalon integrales. Rigidez y tolerancias requieren probeta.')

    cap=a0.ring(C['retainer_radius'],r,C['retainer_z'],C['retainer_top']-C['retainer_z'])
    for x,y in bolt_xy: cap=cap.cut(a0.cyl(2.25,7,x,y,17))
    add(plastic,'UpperRetainer','IMPRIMIR tapa de retencion / 3.3 mm',cap,(0.86,0.55,0.22),
        'Retiene tuerca contra salida axial; 4 M4 pasantes sujetan base, tapa y bastidor.')
    nut=a1.hexagon(C['nut_af_max'],C['nut_height_max'],C['nut_z'])
    nut=nut.cut(a0.cyl(15.875/2,C['nut_height_max']+2,z=C['nut_z']-1))
    add(hardware,'PoleNut','COMPRAR tuerca hexagonal 5-8-11 UNC',nut,(0.88,0.68,0.25),
        'Tuerca comercial, NO imprimir. Geometria nominal simplificada sin helice; AF y altura segun HN58.',C['nut_source'])
    shim_z=C['nut_z']+C['nut_height_max']
    add(plastic,'NutShim','IMPRIMIR calce de tuerca / nominal 0.5 mm',
        a0.ring(12,r,shim_z,C['retainer_z']-shim_z),(0.86,0.55,0.22),
        'Calce plano impreso. Espesor = 14.7 menos altura real de tuerca; no usar calce metalico a medida.')

    frame=source.Frame.Shape.copy()
    # Alojamiento adicional para la punta; no invade bateria o ruta coaxial.
    frame=frame.fuse(a0.cyl(11,C['stud_cavity_roof']-24.8,z=24.8))
    frame=frame.cut(a0.cyl(r,C['stud_cavity_depth']+1,z=-1)).removeSplitter()
    add(plastic,'Frame','IMPRIMIR bastidor A3 / alivio cerrado del esparrago',frame,(0.25,0.36,0.39),
        'Cavidad axial libre hasta Z26.5 y techo Z28. Conserva canal coaxial A2. No define longitud universal del jalon.')

    sheet=doc.addObject('Spreadsheet::Sheet','Dimensions')
    sheet.Label='A3 / cotas informativas; editar JSON y regenerar'
    rows=[['DATO','VALOR','ESTADO'],['Montaje','5/8-11 UNC','Rosca comercial estandar'],
          ['Estructura','Impresion 3D','Solo tornilleria comprada'],['Suelo bajo tuerca',4,'mm'],
          ['Hexagono',24.25,'mm entre caras; probar ajuste'],['Tuerca AF max',23.8252,'HN58'],
          ['Tapa retencion',3.3,'mm'],['Profundidad axial libre',26.5,'mm desde apoyo'],
          ['Pernos verticales','4 x M4 x 30 avellanados','Con arandelas y tuercas'],
          ['Tornillos horizontales','4 x M3 x 8','Retienen cuerpo/base'],
          ['Antena / cable','Conserva A2','Conectores y sellado pendientes'],
          ['Encendido','Pulsador exterior pendiente','Reserva biestable no integra boton'],
          ['Validacion','Solo geometria CAD','Sin ensayo mecanico']]
    for i,row in enumerate(rows,1):
        for j,val in enumerate(row): sheet.set(chr(65+j)+str(i),str(val))
    for column,width in [('A',235),('B',245),('C',330)]: sheet.setColumnWidth(column,width)
    sheet.setStyle('A1:C1','bold','add')
    doc.recompute()

    wire,start,_=a2.route(); coax=a2.tube(wire,start,2.5)
    audit={'revision':'A3','parts':[],'collisions':[],'coax_collisions':[],
           'meshes':[],'assembly_checks':{},'commercial_hardware':[o.Name for o in hardware.Group],
           'custom_metal_parts':[], 'stud_cavity_depth_mm':C['stud_cavity_depth']}
    for o in items:
        audit['parts'].append({'name':o.Name,'valid':o.Shape.isValid(),'solids':len(o.Shape.Solids)})
        assert o.Shape.isValid() and len(o.Shape.Solids)==1, o.Name
        volume=o.Shape.common(coax).Volume
        if volume>0.02: audit['coax_collisions'].append({'part':o.Name,'volume':volume})
    for i,o in enumerate(items):
        for p in items[i+1:]:
            if not o.Shape.BoundBox.intersect(p.Shape.BoundBox): continue
            volume=o.Shape.common(p.Shape).Volume
            if volume>0.02: audit['collisions'].append({'a':o.Name,'b':p.Name,'volume':volume})
    insertion=[]
    for k in range(49):
        n=nut.copy(); n.translate(V(0,0,k*0.5))
        if n.common(base).Volume>0.02: insertion.append(k*0.5)
    audit['assembly_checks']['main_nut_vertical_insertion_collisions']=insertion
    rotated=nut.copy(); rotated.rotate(V(),V(0,0,1),30)
    raised=nut.copy(); raised.translate(V(0,0,1))
    lowered=nut.copy(); lowered.translate(V(0,0,-1))
    retention={'rotation_30deg_block_volume_mm3':rotated.common(base).Volume,
               'upward_1mm_block_volume_mm3':raised.common(cap).Volume,
               'downward_1mm_block_volume_mm3':lowered.common(base).Volume}
    audit['assembly_checks']['retention_geometric_checks']=retention
    assert all(v>0.02 for v in retention.values()),retention
    radial=[]
    for i in range(1,5):
        for k in range(25):
            n=doc.getObject('RadialNut'+str(i)).Shape.copy(); n.translate(V(0,0,k*0.5))
            if n.common(base).Volume>0.02: radial.append([i,k*0.5])
    audit['assembly_checks']['radial_nut_insertion_collisions']=radial
    stud=[]
    for length in (19,20,25):
        gauge=a0.cyl(15.875/2,length)
        collisions=[o.Name for o in items if o.Shape.common(gauge).Volume>0.02]
        stud.append({'length_mm':length,'collisions':collisions,'roof_clearance_mm':C['stud_cavity_depth']-length})
    audit['assembly_checks']['stud_nominal_envelope']=stud
    (OUT/'cad-checks.json').write_text(json.dumps(audit,indent=2,ensure_ascii=False)+'\n')
    assert not audit['collisions'] and not audit['coax_collisions'], audit
    assert not insertion and not radial and all(not c['collisions'] for c in stud),audit
    for o in plastic.Group:
        mesh=MeshPart.meshFromShape(Shape=o.Shape,LinearDeflection=0.1,AngularDeflection=0.16,Relative=False)
        audit['meshes'].append({'name':o.Name,'closed':mesh.isSolid()})
        assert mesh.isSolid(),o.Name
        mesh.write(str(OUT/(o.Name+'-PROTOTYPE.stl')))
        Part.export([o],str(OUT/(o.Name+'.step')))
    Part.export(items,str(OUT/'TresVizo-case-A3-with-RESERVES.step'))
    (OUT/'cad-checks.json').write_text(json.dumps(audit,indent=2,ensure_ascii=False)+'\n')
    aliases={'UpperRetainer':'AntennaSupport','NutShim':'AntennaSupport'}
    a1.save_preserving_presentation(doc,HERE/'TresVizo-case-A3.FCStd',styles(doc,original,aliases))

    section=App.newDocument('TresVizoMount_A3')
    section.Label='TresVizo A3 | CORTE de base impresa - no fabricar corte'
    cut=a0.box(100,100,160,-50,0,-1)
    for o in items:
        if o.Name not in ('Base','Frame','UpperRetainer','NutShim') and o not in hardware.Group: continue
        shape=o.Shape.copy()
        if o.Name=='Frame': shape=shape.common(a0.box(80,80,9,-40,-40,21))
        shape=shape.cut(cut)
        if shape.isNull() or shape.Volume<0.001: continue
        s=section.addObject('PartDesign::Feature',o.Name); s.Label=o.Label; s.Shape=shape
    section.recompute()
    a1.save_preserving_presentation(section,HERE/'TresVizo-case-A3-MOUNT-SECTION.FCStd',styles(section,original,aliases))
    print(json.dumps({'solids':len(items),'printable_parts':len(plastic.Group),'custom_metal_parts':0,
                      'collisions':audit['collisions'],'coax_collisions':audit['coax_collisions'],
                      'assembly_checks':audit['assembly_checks']}))


if __name__=='__main__': build()
