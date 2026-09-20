"""Prepara A4 con logo en una carpeta de salida, sin reemplazar la entrega.

Uso con el Python de FreeCAD: apply_case_a4_branding.py DIRECTORIO
Solo cambia MainShell; valida que todo el volumen retirado sea piel exterior.
"""
from pathlib import Path
from datetime import datetime
import json
import sys
import shutil
import hashlib
import FreeCAD as App
import Part
import MeshPart
import build_case_a4 as a4
from case_branding import engrave_shell

HERE=Path(__file__).resolve().parent
OUT=Path(sys.argv[1]).resolve()
OUT.mkdir(parents=True,exist_ok=True)
cad=OUT/'cad'; cad.mkdir(exist_ok=True)
exports=OUT/'review-a4'; exports.mkdir(exist_ok=True)
config=a4.C['branding']
doc=App.openDocument(str(HERE/'TresVizo-case-A4.FCStd'))
before=doc.MainShell.Shape.copy()
after,cutter=engrave_shell(before,config)
removed=before.cut(after)
added=after.cut(before).Volume
inner=a4.a0.envelope(40,80,-config['depth_mm']-.001)
assert added<.0001
assert removed.common(inner).Volume<.0001
assert len(removed.Solids)==6, len(removed.Solids)  # hexagono + 3 + cuatro trazos
assert removed.BoundBox.ZMax<doc.ServiceCover.Shape.BoundBox.ZMin-8
report={'modified_at':datetime.now().isoformat(timespec='seconds'),
        'config':config,'valid':after.isValid(),'solids':len(after.Solids),
        'removed_regions':len(removed.Solids),'added_volume_mm3':added,
        'removed_volume_mm3':removed.Volume,
        'remaining_nominal_wall_mm':a4.a0.C['wall']-config['depth_mm'],
        'interior_geometry_unchanged':True,
        'source_sha256':hashlib.sha256((HERE/'TresVizo-case-A4.FCStd').read_bytes()).hexdigest()}
for suffix in ('','-EXPLODED'):
    d=doc if not suffix else App.openDocument(str(HERE/f'TresVizo-case-A4{suffix}.FCStd'))
    s=after.copy()
    if suffix:s.translate(App.Vector(100,0,0))
    d.MainShell.Shape=a4.standalone_shape(s)
    d.MainShell.Label='A4 01 / cuerpo con simbolo 3 + hexagono grabado'
    for prop in ('Estado','Fuente'):
        if prop not in d.MainShell.PropertiesList:
            d.MainShell.addProperty('App::PropertyString',prop,'Documentacion')
    d.MainShell.Estado='Logo original sin VIZO, 36 mm de alto y grabado radial de 0.6 mm. Una sola pieza impresa.'
    d.MainShell.Fuente=config['source']
    d.recompute()
    a4.a1.save_preserving_presentation(d,cad/f'TresVizo-case-A4{suffix}.FCStd',a4.make_style(d,None,{}))
shutil.copy2(HERE/'TresVizo-case-A4-INTERIOR.FCStd',cad/'TresVizo-case-A4-INTERIOR.FCStd')
s=after.copy();b=s.BoundBox;s.translate(App.Vector(-b.XMin,-b.YMin,-b.ZMin))
mesh=MeshPart.meshFromShape(Shape=s,LinearDeflection=.05,AngularDeflection=.12,Relative=False)
assert mesh.isSolid() and not mesh.hasNonManifolds()
report['stl_closed']=mesh.isSolid()
report['stl_volume_relative_error']=abs(mesh.Volume-after.Volume)/after.Volume
assert report['stl_volume_relative_error']<.01
mesh.write(str(exports/'MainShell-ORIENTED-REVIEW.stl'))
Part.export([doc.MainShell],str(exports/'MainShell.step'))
physical=[o for o in doc.Objects if o.TypeId=='Part::Feature' and o.Name!='CoaxRouteReserve']
Part.export(physical,str(exports/'TresVizo-case-A4-with-RESERVES.step'))
assert len(physical)==42
for p in cad.glob('*.FCStd'):
    loaded=App.openDocument(str(p))
    assert all(o.Shape.isValid() for o in loaded.Objects if o.TypeId=='Part::Feature')
    App.closeDocument(loaded.Name)
(exports/'branding-checks.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
print(json.dumps(report,ensure_ascii=False),flush=True)
