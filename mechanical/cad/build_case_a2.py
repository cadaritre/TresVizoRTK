"""A2: entrada bajo antena y recorrido reservado de coaxial. Conserva A1."""
import math
import json
import copy
import xml.etree.ElementTree as ET
from pathlib import Path
import FreeCAD as App
import Part
import MeshPart
import build_case_a1 as a1

HERE=Path(__file__).resolve().parent
OUT=HERE.parent/'exports'/'review-a2'
V=App.Vector
Z=V(0,0,1)


def arc(center,start,end):
    a=start-center; b=end-center
    middle=a+b; middle.normalize(); middle.multiply(a.Length)
    return Part.Arc(start,center+middle,end).toShape()


def sbend(start,direction,side,offset,radius):
    c=1-offset/(2*radius)
    s=math.sqrt(1-c*c)
    midpoint=start+side*(radius*(1-c))+direction*(radius*s)
    end=start+side*offset+direction*(2*radius*s)
    return [arc(start+side*radius,start,midpoint),
            arc(end-side*radius,midpoint,end)],end


def route():
    start=V(0,0,167.9)
    p=V(0,0,160)
    edges=[Part.makeLine(start,p)]
    more,p=sbend(p,V(0,0,-1),V(1,0,0),17,10); edges+=more
    more,p=sbend(p,V(0,0,-1),V(0,-1,0),23,12); edges+=more
    q=V(17,-23,44); edges.append(Part.makeLine(p,q)); p=q
    q=p+V(0,12,-12); edges.append(arc(p+V(0,12,0),p,q)); p=q
    more,p=sbend(p,V(0,1,0),V(-1,0,0),17,10); edges+=more
    # Termina ANTES de la reserva de carrier, en su zona inferior de conexion.
    # No representa la geometria ni el genero del conector SMA comercial.
    q=p+V(0,math.sqrt(12**2-4**2),8)
    edges.append(arc(p+V(0,0,12),p,q))
    return Part.Wire(edges),start,q


def tube(wire,start,radius):
    circle=Part.Wire([Part.makeCircle(radius,start,V(0,0,-1))])
    return wire.makePipeShell([circle],True,False)


def build():
    OUT.mkdir(parents=True,exist_ok=True)
    source_path=HERE/'TresVizo-case-A1.FCStd'
    source_style=a1.presentation(source_path)
    doc=App.openDocument(str(source_path))
    doc.Label='TresVizo A2 | paso y recorrido coaxial'
    wire,start,end=route()
    reserve=tube(wire,start,2.5)
    channel=tube(wire,start,4.0)
    # Entrada recta superior Ø16. Ranura abierta para acomodar el cable en
    # la plataforma inferior sin enhebrarlo por un agujero pequeno.
    support=doc.AntennaSupport.Shape.cut(a1.cyl(8,26,z=145))
    support=support.cut(a1.box(31,8,5,0,-4,147))
    support=support.cut(channel).removeSplitter()
    doc.AntennaSupport.Shape=support
    doc.AntennaSupport.Label='Soporte antena A2 / entrada 16 y salida lateral 8'
    doc.AntennaSupport.Estado='Entrada Ø16 de diseno y ranura lateral 8. Verificar conector real; patron de tres agujeros aun pendiente.'
    doc.Frame.Shape=doc.Frame.Shape.cut(channel).removeSplitter()
    doc.Frame.Label='Bastidor A2 / escotadura lateral coaxial 8'
    doc.Frame.Estado='Canal Ø8 en el anillo junto a IMU. No atraviesa plataforma ni reserva de IMU.'
    doc.recompute()
    solids=[o for o in doc.Objects if hasattr(o,'ColorRGB')]
    gauge=a1.cyl(7.95,22,z=147)
    checks={'revision':'A2','units':'mm','entry_diameter':16,'channel_diameter':8,
            'coax_reserve_diameter':5,'minimum_centerline_bend_radius':10,
            'centerline_length':round(wire.Length,3),'end_position':list(end),
            'entry_gauge_15_9mm_collision_mm3':round(doc.AntennaSupport.Shape.common(gauge).Volume,6),
            'coax_collisions':[],'parts':[],'collisions':[],
            'limits':'Reserva de ruta. No certifica conectores, cable comprado, sellado, sujecion ni conexion SMA.'}
    for o in solids:
        s=o.Shape
        checks['parts'].append({'name':o.Name,'valid':s.isValid(),'solids':len(s.Solids)})
        if not s.isValid() or len(s.Solids)!=1: raise RuntimeError('Pieza invalida: '+o.Name)
        volume=s.common(reserve).Volume
        if volume>0.02: checks['coax_collisions'].append({'part':o.Name,'volume_mm3':round(volume,4)})
    for i,o in enumerate(solids):
        for p in solids[i+1:]:
            if not o.Shape.BoundBox.intersect(p.Shape.BoundBox): continue
            volume=o.Shape.common(p.Shape).Volume
            if volume>0.02: checks['collisions'].append({'a':o.Name,'b':p.Name,'volume':volume})
    checks['route_valid']=reserve.isValid() and len(reserve.Solids)==1
    (OUT/'cad-checks.json').write_text(json.dumps(checks,indent=2,ensure_ascii=False)+'\n')
    if checks['coax_collisions'] or checks['collisions'] or not checks['route_valid'] or checks['entry_gauge_15_9mm_collision_mm3']>0.001:
        raise RuntimeError(str(checks['coax_collisions'])+' '+str(checks['collisions']))
    # El conjunto principal mantiene exactamente sus nombres de objeto para
    # conservar presentacion GUI de A1. La ruta vive en un archivo de revision.
    doc.Dimensions.set('A12','Entrada coaxial / canal'); doc.Dimensions.set('B12','16 / 8 mm')
    doc.Dimensions.set('C12','Cotas de diseno; conector real pendiente')
    doc.Dimensions.set('A13','Reserva cable / radio minimo'); doc.Dimensions.set('B13','5 / 10 mm')
    doc.Dimensions.set('C13','Ruta por costado, fuera de IMU y bateria')
    doc.recompute()
    a1.save_preserving_presentation(doc,HERE/'TresVizo-case-A2.FCStd',source_style)
    for o in doc.Plastic.Group:
        mesh=MeshPart.meshFromShape(Shape=o.Shape,LinearDeflection=0.1,AngularDeflection=0.16,Relative=False)
        if not mesh.isSolid(): raise RuntimeError('Malla abierta: '+o.Name)
        mesh.write(str(OUT/(o.Name+'-PROTOTYPE.stl')))
        Part.export([o],str(OUT/(o.Name+'.step')))
    Part.export(solids,str(OUT/'TresVizo-case-A2-with-RESERVES.step'))
    review=App.newDocument('TresVizoCable_A2')
    review.Label='TresVizo A2 | recorrido coaxial - vista sin carcasa'
    group=review.addObject('App::DocumentObjectGroup','Review')
    selected={'AntennaSupport','Frame','IMUPlate','IMUReserve','GNSSReserve',
              'BatteryReserve','SDReference','ESPReference','USBReference','LatchReserve'}
    for o in solids:
        if o.Name in selected:
            a1.a0.add(review,group,o.Name,o.Label,o.Shape,tuple(float(c) for c in o.ColorRGB.split(',')),o.Estado)
    a1.a0.add(review,group,'CoaxRouteReserve','AZUL / espacio de cable Ø5 / NO es cable certificado',
              reserve,(0.06,0.5,0.93),'Radio minimo 10. Genero y volumen de conectores SMA pendientes.')
    review.recompute()
    # Reutiliza estilos nativos de los objetos conservados; el cable toma el
    # material azul de USBReference. No requiere abrir la GUI que falla en Mac.
    assets=source_style[0].copy()
    if 'GuiDocument.xml' in assets:
        xml=ET.fromstring(assets['GuiDocument.xml'])
        providers=xml.find('ViewProviderData')
        originals={p.attrib['name']:p for p in providers}
        for p in list(providers): providers.remove(p)
        for o in review.Objects:
            key='References' if o.Name=='Review' else 'USBReference' if o.Name=='CoaxRouteReserve' else o.Name
            p=copy.deepcopy(originals[key]);p.attrib['name']=o.Name
            visible=p.find(".//Property[@name='Visibility']/Bool")
            if visible is not None: visible.attrib['value']='true'
            providers.append(p)
        providers.attrib['Count']=str(len(review.Objects))
        assets['GuiDocument.xml']=ET.tostring(xml,encoding='utf-8',xml_declaration=True)
        style=(assets,{o.Name for o in review.Objects})
    else: style=({},set())
    a1.save_preserving_presentation(review,HERE/'TresVizo-case-A2-CABLE-ROUTE.FCStd',style)
    # Exportacion separada sin confundirse con piezas fabricables.
    Part.export([review.CoaxRouteReserve],str(OUT/'CoaxRoute-RESERVE-NOT-FOR-PRINT.step'))
    print(json.dumps({k:checks[k] for k in ('centerline_length','end_position','coax_collisions','route_valid')}))
    return doc


if __name__=='__main__': build()
