"""Normaliza STEP e interfaz. Ejecutar con Python de FreeCAD, después de export_rev_a.py."""
from pathlib import Path
import json, re, sys
import FreeCAD as App, Part
B=Path(__file__).resolve().parents[1];ROOT=B.parent.parent;R=B/'rev-a';M=B/'manufacturing/rev-a'
board=Part.read(str(M/'board-only-kicad.step'))
raw=Part.read(str(M/'power-board-kicad.step'))
assert board.isValid() and len(board.Solids)==1 and raw.isValid()
bb=board.BoundBox
assert abs(bb.XMin+22.5)<1e-5 and abs(bb.YMin+20)<1e-5 and abs(bb.XLength-45)<1e-5 and abs(bb.YLength-40)<1e-5
# KiCad omite cobre/máscara en board-only. Conservamos XY y todos sus taladros;
# el sólido mecánico reserva el espesor nominal completo, sin reducir holguras.
shift=(1.6-bb.ZLength)/2
mat=App.Matrix();mat.A33=1.6/bb.ZLength
nominal=board.copy();nominal.translate(App.Vector(0,0,-bb.ZMin));nominal=nominal.transformGeometry(mat)
components=[];matched=0
for solid in raw.Solids:
    q=solid.BoundBox
    if abs(q.XLength-45)<1e-5 and abs(q.YLength-40)<1e-5 and abs(q.ZLength-bb.ZLength)<1e-5:
        matched+=1;continue
    solid.translate(App.Vector(0,0,shift-bb.ZMin));components.append(solid)
assert matched==1 and nominal.isValid()
final=Part.makeCompound([nominal]+components);assert final.isValid()
final.exportStep(str(B/'manufacturing/power-board.step'))
placement=json.loads((R/'placement.json').read_text());parts=json.loads((R/'circuit.json').read_text())['components'];p={c['reference']:c for c in parts}
def box_for(ref,extra_height=0):
    c=p[ref];a,b,cx,d=placement['courtyards'][ref]
    text=(R/'lib'/(c['footprint'].split(':')[0]+'.pretty')/(c['footprint'].split(':')[1]+'.kicad_mod')).read_text()
    model=re.search(r'\(model\s+"([^"]+)"',text)
    path=model[1].replace('${KIPRJMOD}',str(R)) if model else None
    h=Part.read(path).BoundBox.ZMax if path and Path(path).is_file() else .8
    h=max(.5,h)+extra_height
    return dict(name=ref,position_mm=[round(a-22.5,4),round(20-d,4),1.6],size_mm=[round(cx-a,4),round(d-b,4),round(h,4)],rotation_xyzw=[0,0,0,1])
entries=[]
names={'J1':'USB_C','J2':'BATTERY','J3':'BATTERY_NTC','J4':'GNSS_POWER','J5':'ESP_NATIVE_FPC_CANDIDATE_DNP','J6':'ESP_AUX_SIGNALS'}
directions={'J1':[0,-1,0],'J2':[1,0,0],'J3':[1,0,0],'J4':[-1,0,0],'J5':[0,1,0],'J6':[0,1,0]}
for ref,name in names.items():
    e=box_for(ref);e.update(name=name,reference=ref,mpn=p[ref]['mpn'],footprint=p[ref]['footprint'],insertion_direction=directions[ref],mating_center_mm=None,geometry_basis='Courtyard como envolvente XY; altura modelo local. Centro de acople nominal, revisar con cable comprado.')
    x,y,z=e['position_mm'];w,l,h=e['size_mm'];v=e['insertion_direction']
    e['mating_center_mm']=[x+w/2-v[0]*w/2,y+l/2-v[1]*l/2,z+h/2]
    if ref=='J5':e.update(dnp=True,contact_count=8,pitch_mm=.5,pinout=p[ref]['pins'],physical_mapping_confirmed=False,cable_contact_orientation=None)
    entries.append(e)
features=[]
for ref in ['SW1','LED1','LED2','LED3','LED4']:
    e=box_for(ref);x,y,z=e['position_mm'];w,l,h=e['size_mm'];e['reference']=ref
    e['name']='POWER_BUTTON' if ref=='SW1' else p[ref]['value'].replace(' ','_')
    if ref=='SW1':e.update(press_direction=[0,0,-1],actuation_center_mm=[x+w/2,y+l/2,z+h])
    else:e.update(emission_direction=[0,0,1],optical_center_mm=[x+w/2,y+l/2,z+h])
    features.append(e)
def reserve(name,pos,size):return dict(name=name,position_mm=pos,size_mm=size,rotation_xyzw=[0,0,0,1],basis='Reserva de diseño para acceso, no medición de cable ni tolerancia garantizada')
keepouts=[reserve('USB_PLUG_AND_INSERTION',[-6,19.5,-.5],[12,20,7]),reserve('BATTERY_PLUG_AND_CABLE',[-35,-16,1.2],[14,11,6]),reserve('NTC_PLUG_AND_CABLE',[-31,-2,1.2],[10,7,5]),reserve('GNSS_PLUG_AND_CABLE',[21,-12,1.2],[14,11,6]),reserve('AUX_PLUG_AND_CABLE',[-12,-33,1.2],[20,14,6]),reserve('FPC_CABLE_CANDIDATE',[8,-32,1.3],[13,14,5]),reserve('BUTTON_ACCESS',[11.5,13.5,3.1],[6,6,6]),reserve('STATUS_OPTICAL_PATH',[5.5,12,2.1],[5,8,7]),reserve('CHARGE_OPTICAL_PATH',[-17.5,16,2.1],[4,4,7])]
env=[reserve('BOTTOM_COMPONENT_CLEARANCE',[-22.5,-20,-1.8],[45,40,1.8]),reserve('TOP_COMPONENT_CLEARANCE',[-22.5,-20,1.6],[45,40,4.1])]
data=dict(schema_version=1,name='POWER & INTERFACE PCB',status='Rev A — PCB ruteado; referencia digital disponible; integración física pendiente',units='mm',coordinates=dict(xy_origin='board_geometric_center',z_origin='board_bottom',axes='right_handed',kicad_transform='X=x-22.5; Y=20-y; Z=0 cara inferior nominal; USB sale hacia +Y'),board=dict(width_mm=45,length_mm=40,thickness_mm=1.6,outline_xy_mm=[[-22.5,-20],[22.5,-20],[22.5,20],[-22.5,20]]),mounting_holes=[dict(name='H'+str(i+1),center_xy_mm=[x-22.5,20-y],diameter_mm=2.2) for i,(x,y) in enumerate(placement['holes'])],connectors=entries,external_features=features,component_envelopes=env,keepouts=keepouts,step=dict(path='hardware/power-board/manufacturing/power-board.step',local_frame_confirmed=True,kicad_component_z_translation_mm=shift-bb.ZMin,board_nominal_envelope_mm=1.6,includes_unpopulated_fpc_candidate=True),completeness=dict(mounting_holes_reviewed=True,component_envelopes_reviewed=True,access_and_cables_reviewed=False),notes=['Sólo la nueva placa. Otro responsable define placement global y holguras del case.','Dirección de inserción apunta desde el cable hacia el receptáculo. Coordenadas de centros de acople aproximadas a partir de envolventes.','STEP incluye J5 candidato para reservar su volumen; BOM lo excluye del montaje.','Modelos de encapsulados pequeños y PH incluyen envolventes conservadoras, no todos son CAD de fabricante; ver MODEL_SOURCES.md.','Espesor nominal incluye cobre/máscaras; STEP original KiCad conserva su marco dieléctrico, usar el STEP normalizado indicado.','No se ha efectuado fit check de esta placa en la carcasa ni medido cables reales.'])
(ROOT/'mechanical/integration/power_board_interface.json').write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n')
sys.path.insert(0,str(ROOT))
from mechanical.integration.power_board_reference import build_geometry
model=build_geometry();assert model['mode']=='STEP' and all(s.isValid() for _,s in model['solids']+model['keepouts'])
q=final.BoundBox
report=dict(status='VALID_LOCAL_STEP',solids=len(final.Solids),bounding_box_mm=[q.XMin,q.YMin,q.ZMin,q.XMax,q.YMax,q.ZMax],nominal_board_mm=[45,40,1.6],kicad_body_thickness_mm=bb.ZLength,component_z_translation_mm=shift-bb.ZMin,keepouts=len(model['keepouts']),missing=model['missing'],case_fit='NOT_TESTED')
(R/'review/mechanical-checks.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
