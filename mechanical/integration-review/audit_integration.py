"""Auditoria reproducible de A5 y panel regenerado; no escribe fuentes.

Ejecutar con Python/FreeCAD despues de panel-modules/build_panel.py.
Las reservas parametrizadas son estudios, no componentes ni montaje liberados.
"""
from pathlib import Path
import hashlib
import itertools
import json
import FreeCAD as App
import Part
import Mesh

ROOT = Path(__file__).resolve().parent
MECH = ROOT.parent
OUT = ROOT / 'generated'
P = json.loads((ROOT / 'review_parameters.json').read_text())
EPS = P['collision_threshold_mm3']
V = App.Vector


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def box(s):
    b = s.BoundBox
    return [round(x, 5) for x in (b.XMin,b.YMin,b.ZMin,b.XMax,b.YMax,b.ZMax)]


def leaf_shapes(doc):
    return {o.Name: o.Shape for o in doc.Objects
            if not hasattr(o, 'Group') and hasattr(o, 'Shape') and not o.Shape.isNull()}


def hits(shape, obstacles):
    result = []
    for name, other in obstacles.items():
        if not shape.BoundBox.intersect(other.BoundBox):
            continue
        common = shape.common(other)
        if common.Volume > EPS:
            result.append({'against': name, 'volume_mm3': round(common.Volume, 5),
                           'box': box(common)})
    return result


def pairs(objects):
    result = []
    for (name, shape), (other, target) in itertools.combinations(objects.items(), 2):
        result.extend(dict(part=name, **h) for h in hits(shape, {other: target}))
    return result


def distances(shape, obstacles, limit=3):
    result = []
    for name, target in obstacles.items():
        d = shape.distToShape(target)[0]
        if d < limit:
            result.append({'against': name, 'distance_mm': round(d, 5)})
    return sorted(result, key=lambda r: r['distance_mm'])


def moved(shape, delta):
    s = shape.copy()
    s.translate(V(*delta))
    return s


def sweep_samples(moving, obstacles, axis, offsets):
    result = []
    for offset in offsets:
        delta = tuple(offset*x for x in axis)
        failures = []
        for name, shape in moving.items():
            failures.extend(dict(part=name, **h) for h in hits(moved(shape, delta), obstacles))
        result.append({'offset_mm': offset, 'intersections': failures})
    return result


source = MECH / 'A5' / 'TresVizo-A5.FCStd'
source_hash = sha(source)
a5 = App.openDocument(str(source))
doc = App.openDocument(str(OUT / 'TresVizo-panel-modules.FCStd'))
old = leaf_shapes(a5)
all_shapes = leaf_shapes(doc)
active = {n:s for n,s in all_shapes.items() if n != 'A5_IMUTarget'}
report = {
    'scope': 'Solidos nominales y reservas explicitamente declaradas; no ensayo fisico ni analisis estructural',
    'freecad_version': App.Version(),
    'source_sha256_before': source_hash,
    'generator_sha256': sha(MECH/'panel-modules/build_panel.py'),
    'panel_parameters_sha256': sha(MECH/'panel-modules/parameters.json'),
    'review_parameters_sha256': sha(ROOT/'review_parameters.json'),
    'objects': [{'name':n, 'valid':s.isValid(), 'solids':len(s.Solids),
                 'volume_mm3':round(s.Volume,5), 'box':box(s)} for n,s in all_shapes.items()],
    'all_pair_intersections': pairs(active),
}
print('Solidos e intersecciones terminados', flush=True)
report['m2_head_intersections']=[]
for name in [n for n in active if n.startswith(('USBScrew','ButtonScrew'))]:
    s=active[name];b=s.BoundBox
    if name.startswith('USB'):
        mask=Part.makeBox(8,8,2,V((b.XMin+b.XMax)/2-4,(b.YMin+b.YMax)/2-4,b.ZMax-2))
    else:
        mask=Part.makeBox(8,2,8,V((b.XMin+b.XMax)/2-4,b.YMin,(b.ZMin+b.ZMax)/2-4))
    report['m2_head_intersections'].append({'name':name,'intersections':hits(s.common(mask),{'ModulePanel':active['ModulePanel']})})

# Comparacion de fuentes; propiedades de forma se calculan, no dependen del render.
changes = []
for name in ['MainShell','Chassis','AntennaCap','BatteryIMUCarrier','IMUNutBar','IMUReserve','IMUTarget','ESPReference','GNSSReserve','SDReference','BatteryReserve','FlangedInsert','CoaxRouteReserve']:
    before, after = old[name], all_shapes['A5_'+name]
    changes.append({'name':name, 'removed_mm3':round(before.cut(after).Volume,5),
                    'added_mm3':round(after.cut(before).Volume,5),
                    'box_before':box(before),'box_after':box(after)})
report['a5_changes'] = changes
report['preserved_front_logo_mm3'] = old['MainShell'].common(Part.makeBox(50,20,40,V(-25,20,40))).cut(
    all_shapes['A5_MainShell']).Volume

# Montaje/extraccion, con cierres removidos y arnes desconectado.
panel_names = [n for n in active if not n.startswith('A5_') and not n.startswith('Tiny')]
panel = {n:active[n] for n in panel_names}
panel_obstacles = {n:s for n,s in active.items() if n not in panel and not n.startswith('A5_PanelBolt')}
report['panel_extraction_positive_y'] = sweep_samples(panel,panel_obstacles,(0,1,0),list(range(0,41,2)))
shell_obstacles = {n:s for n,s in active.items() if n.startswith('A5_') and
    n not in ['A5_MainShell','A5_AntennaCap','A5_HA901Reserve','A5_IMUTarget'] and
    not n.startswith(('A5_RadialBolt','A5_CapClosure','A5_Panel','A5_AntennaBolt'))}
report['shell_removal_positive_z'] = sweep_samples({'A5_MainShell':active['A5_MainShell']},shell_obstacles,(0,0,1),list(range(0,165,4)))
report['shell_removal_negative_z'] = sweep_samples({'A5_MainShell':active['A5_MainShell']},shell_obstacles,(0,0,-1),[0,2,4,8,12,20])
report['shell_on_bare_chassis_positive_z'] = sweep_samples({'A5_MainShell':active['A5_MainShell']},{'A5_Chassis':active['A5_Chassis']},(0,0,1),[0,4,8,12,20,40,80,120,160])
carrier_names = ['A5_BatteryIMUCarrier','A5_BatteryReserve','A5_IMUReserve','A5_IMUNutBar',
                 'A5_IMUPcbBolt1','A5_IMUPcbBolt2','A5_IMUPcbNut1','A5_IMUPcbNut2']
carrier = {n:active[n] for n in carrier_names}
carrier_obs = {n:s for n,s in active.items() if n not in carrier and n.startswith('A5_') and
               n not in ['A5_MainShell','A5_SDReference','A5_AntennaCap','A5_HA901Reserve','A5_IMUTarget','A5_CoaxRouteReserve'] and
               not n.startswith(('A5_ModuleBolt','A5_ModuleNut','A5_CapClosure','A5_Panel','A5_AntennaBolt'))}
report['carrier_removal_negative_y'] = sweep_samples(carrier,carrier_obs,(0,-1,0),list(range(0,25,2)))
report['motion_limits'] = 'Muestreo discreto, no barrido continuo. Arnes desconectado, SD fuera para sacar cuna, coaxial libre; ver listas de obstaculos en script.'
print('Movimientos terminados', flush=True)

# Reserva externa de sobremolde: prueba pared/panel, no acoplamiento electrico USB.
uy = 37.1+(132-100)/88-1.2
def rounded_plug(w,h,r):
    z=132; y=uy
    s=Part.makeBox(w-2*r,25,h,V(-w/2+r,y,z-h/2))
    s=s.fuse(Part.makeBox(w,25,h-2*r,V(-w/2,y,z-h/2+r)))
    for x in (-w/2+r,w/2-r):
        for zz in (z-h/2+r,z+h/2-r):
            s=s.fuse(Part.makeCylinder(r,25,V(x,y,zz),V(0,1,0)))
    return s.removeSplitter()
port_obstacles = {n:active[n] for n in ['ModulePanel','A5_MainShell']}
report['external_usb_plugs'] = [
    {'envelope_mm':[w,h,25], 'basis':'ESTIMADO; sobremolde sin cable comercial elegido',
     'intersections':hits(rounded_plug(w,h,1.5),port_obstacles),
     'clearances':distances(rounded_plug(w,h,1.5),port_obstacles)} for w,h in [(13,5.5),(16,8)]
]
report['button_motion'] = sweep_samples({'ButtonCap':active['ButtonCap']},
    {n:active[n] for n in ['ModulePanel','ButtonCartridge','A5_Chassis','A5_MainShell']},(0,-1,0),[i*.05 for i in range(9)])

# Herramienta axial estrecha; panel extraido para USB, cuna extraida para IMU.
tool_checks=[]
for name in ['USBScrew1','USBScrew2','USBScrew3','USBScrew4']:
    b=active[name].BoundBox
    tool=Part.makeCylinder(1.5,35,V((b.XMin+b.XMax)/2,(b.YMin+b.YMax)/2,b.ZMax))
    tool_checks.append({'screw':name,'context':'panel fuera del case, llave recta diametro 3 mm',
                        'intersections':hits(tool,{n:s for n,s in panel.items() if n!=name})})
for i in (1,2):
    name='A5_IMUPcbBolt'+str(i); b=active[name].BoundBox
    tool=Part.makeCylinder(1.5,30,V((b.XMin+b.XMax)/2,(b.YMin+b.YMax)/2,b.ZMax))
    tool_checks.append({'screw':name,'context':'cuna fuera del case, llave recta diametro 3 mm',
                       'intersections':hits(tool,{n:s for n,s in carrier.items() if n!=name})})
report['tool_checks']=tool_checks

# Inserto: no inventar agujeros, paso helicoidal ni tornillos sin plano.
insert, chassis = active['A5_FlangedInsert'],active['A5_Chassis']
report['pole'] = {'required':P['pole'], 'insert_box':box(insert),
    'cylinders':[{'radius':f.Surface.Radius,'center':list(f.Surface.Center),'axis':list(f.Surface.Axis),'box':box(f)}
                 for f in insert.Faces if isinstance(f.Surface,Part.Cylinder)],
    'axial_lift':sweep_samples({'insert':insert},{'chassis':chassis},(0,0,1),[0,.3,1,2,5]),
    'rotation':[]}
for angle in [0,30,60,90]:
    s=insert.copy();s.rotate(V(),V(0,0,1),angle)
    report['pole']['rotation'].append({'angle_deg':angle,'intersections':hits(s,{'chassis':chassis})})
report['battery_clearances']=distances(active['A5_BatteryReserve'],
    {n:s for n,s in active.items() if n!='A5_BatteryReserve'},15)

# Envolventes de modulos ausentes y corredores de estudio, visibles como reservas.
study_shapes={}
studies=[]
for name,entry in P['power_module_studies'].items():
    b=entry['box'];s=Part.makeBox(*b[3:],V(*b[:3]));study_shapes[name]=s
    studies.append({'name':name,**entry,'intersections':hits(s,active),'clearances':distances(s,active)})
report['power_module_studies']=studies
report['power_module_pair_intersections']=pairs({n:s for n,s in study_shapes.items() if n in ['PowerBoostEnvelope','SoftSwitchEnvelope']})
wiring=[]
for name,entry in P['wiring_corridors'].items():
    pieces=[]
    for aa,bb in zip(entry['points'],entry['points'][1:]):
        a,b=V(*aa),V(*bb); delta=b-a
        pieces.append(Part.makeCylinder(entry['radius'],delta.Length,a,delta))
    s=Part.makeCompound(pieces);study_shapes[name]=s
    wiring.append({'name':name,**entry,'intersections':hits(s,active),
                   'module_intersections':hits(s,{n:study_shapes[n] for n in ['PowerBoostEnvelope','SoftSwitchEnvelope']})})
report['wiring_corridors']=wiring
print('Reservas y accesos terminados', flush=True)

# Guardar estudio completo sin alterar las fuentes ni presentar reservas como montaje.
review=App.newDocument('IntegrationReview')
for name,shape in all_shapes.items():
    o=review.addObject('Part::Feature',name);o.Shape=shape.copy();o.Label=doc.getObject(name).Label
    o.addProperty('App::PropertyString','Estado');o.Estado='Revision: consultar docs/INTEGRATION_REVIEW.md'
for name,shape in study_shapes.items():
    o=review.addObject('Part::Feature',name);o.Shape=shape
    o.Label='ESTIMADO / '+name
    o.addProperty('App::PropertyString','Estado');o.Estado=P['status']
review.recompute();review.saveAs(str(OUT/'TresVizo-integration-review.FCStd'))

# Reabrir/exportaciones: el numero de solidos se informa, no se adivina.
exports=[]
for folder in [MECH/'panel-modules',OUT]:
    for path in sorted(folder.glob('*.step')):
        s=Part.Shape();s.read(str(path))
        exports.append({'path':str(path.relative_to(MECH)), 'valid':s.isValid(),
                        'solids':len(s.Solids),'volume_mm3':round(s.Volume,5)})
    for path in sorted((folder/'stl').glob('*.stl')):
        m=Mesh.Mesh(str(path));exports.append({'path':str(path.relative_to(MECH)),
            'closed':m.isSolid(),'facets':m.CountFacets})
for path in sorted((MECH/'A5/print').glob('*.stl')):
    m=Mesh.Mesh(str(path));exports.append({'path':str(path.relative_to(MECH)), 'closed':m.isSolid(),'facets':m.CountFacets})
report['exports']=exports
report['source_sha256_after']=sha(source)
report['master_preserved']=source_hash==report['source_sha256_after']
report['scope_ready_for_complete_receiver_print']=False
report['remaining_blockers']=['Montaje/conectores de power y Tiny-Adapter','Retencion/engagement del inserto',
    'Medidas de componentes recibidos, cableado completo y conectores','Prueba fisica electrica, termica y mecanica']
(OUT/'integration-audit.json').write_text(json.dumps(report,indent=2,ensure_ascii=False)+'\n')
print(json.dumps({'objects':len(all_shapes),'pairs':len(report['all_pair_intersections']),
                  'master_preserved':report['master_preserved'],'report':str(OUT/'integration-audit.json')},indent=2))
for d in [review,doc,a5]:App.closeDocument(d.Name)
