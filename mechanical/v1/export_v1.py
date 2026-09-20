"""STEP completo y STL por pieza, orientados en mm y verificados al releer."""
from pathlib import Path
import FreeCAD as A, Part, MeshPart, Mesh, json, hashlib, shutil
ROOT=Path(__file__).resolve().parent;O=ROOT/'generated';V=A.Vector
D=A.openDocument(str(O/'TresVizo-V1.FCStd'));I=json.loads((O/'model-index.json').read_text())
S={o.Name:o.Shape for o in D.Objects if hasattr(o,'Shape') and not hasattr(o,'Group')}
for sub in ['stl','step']: (O/sub).mkdir(exist_ok=True)
exclude=I['routes']+I.get('tools',[])+['A5_IMUTarget','A5_CoaxRouteReserve','TinyUSBPlugReserve']
Part.export([D.getObject(n) for n in S if n not in exclude],str(O/'TresVizo-V1-assembly.step'))
Part.export([D.getObject(n) for n in I['printed']],str(O/'TresVizo-V1-print-parts.step'))
settings=[('A5_MainShell','01-cuerpo',(1,0,0),0),('A5_Chassis','02-chasis-base',(1,0,0),0),('A5_BatteryIMUCarrier','03-cuna-bateria-imu-power',(1,0,0),0),('A5_AntennaCap','04-tapa-antena',(1,0,0),180),('ModulePanel','05-panel-usb-boton',(1,0,0),0),('A5_IMUNutBar','06-prensa-imu',(1,0,0),180),('ButtonCap','07-actuador-boton',(1,0,0),90),('ButtonCartridge','08-cartucho-boton',(1,0,0),90),('StatusLens','09-difusor-estado',(1,0,0),90),('ChargeLens','10-difusor-carga',(1,0,0),90)]
R=[]
for n,filename,axis,angle in settings:
 s=S[n].copy();s.exportStep(str(O/'step'/(filename+'.step')))
 s.rotate(V(),V(*axis),angle);b=s.BoundBox;s.translate(V(-(b.XMin+b.XMax)/2,-(b.YMin+b.YMax)/2,-b.ZMin))
 mesh=MeshPart.meshFromShape(Shape=s,LinearDeflection=.06,AngularDeflection=.18,Relative=False)
 path=O/'stl'/(filename+'.stl');mesh.write(str(path));back=Mesh.Mesh(str(path))
 item={'object':n,'file':str(path.relative_to(ROOT)),'closed':back.isSolid(),'facets':back.CountFacets,'z_min_mm':back.BoundBox.ZMin,'size_mm':[back.BoundBox.XLength,back.BoundBox.YLength,back.BoundBox.ZLength]};R.append(item)
 if not item['closed'] or abs(item['z_min_mm'])>.001:raise ValueError(item)
 print(filename,'closed',item['facets'],flush=True)
# Plantilla ya orientada, heredada del mismo datum A5.
jig=ROOT.parent/'A5/print/07-plantilla-centrado.stl';dest=O/'stl/11-plantilla-centrado-imu.stl';shutil.copy2(jig,dest)
m=Mesh.Mesh(str(dest));R.append({'object':'IMUAlignmentJig','file':str(dest.relative_to(ROOT)),'closed':m.isSolid(),'facets':m.CountFacets,'source_sha256':hashlib.sha256(jig.read_bytes()).hexdigest()})
step=Part.Shape();step.read(str(O/'TresVizo-V1-assembly.step'))
result={'meshes':R,'assembly_step_valid':step.isValid(),'assembly_step_solids':len(step.Solids),'expected_assembly_solids':len(S)-len(exclude),'all_pass':all(x['closed'] for x in R) and step.isValid() and len(step.Solids)==len(S)-len(exclude)}
(O/'exports.json').write_text(json.dumps(result,indent=2));print('EXPORTS',result['all_pass'],flush=True)
