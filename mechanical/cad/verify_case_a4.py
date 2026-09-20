"""Reabre CAD y exportaciones A4; verifica cambios y consistencia de entrega."""
from pathlib import Path
import json
import zipfile
import xml.etree.ElementTree as ET
import FreeCAD as App
import Part
import Mesh
HERE=Path(__file__).resolve().parent
OUT=HERE.parent/'exports'/'review-a4'
report={'revision':'A4','documents':[],'stl':[]}
for suffix in ('','-INTERIOR','-EXPLODED'):
    path=HERE/f'TresVizo-case-A4{suffix}.FCStd'
    doc=App.openDocument(str(path))
    objs=[o for o in doc.Objects if o.TypeId=='Part::Feature' and not o.Shape.isNull()]
    assert all(o.Shape.isValid() and len(o.Shape.Solids)==1 for o in objs),suffix
    assert not {'Frame','UpperRetainer','NutShim','GNSSPlate','SDPlate','USBPlate','ESPPlate'} & {o.Name for o in doc.Objects}
    with zipfile.ZipFile(path) as z:
        assert z.testzip() is None
        root=ET.fromstring(z.read('GuiDocument.xml'))
        providers=root.find('ViewProviderData')
        assert {p.attrib['name'] for p in providers}=={o.Name for o in doc.Objects}
        missing={p.attrib['file'] for p in root.iter() if 'file' in p.attrib}-set(z.namelist())
        assert not missing,missing
    report['documents'].append({'file':path.name,'valid_solids':len(objs),'mtime':path.stat().st_mtime})
    if suffix=='':
        assert len(doc.Plastic.Group)==7
        report['printed_parts']=[o.Name for o in doc.Plastic.Group]
        assert doc.Base.Shape.isValid() and len(doc.Base.Shape.Solids)==1
        for o in doc.Plastic.Group:
            m=Mesh.Mesh(str(OUT/(o.Name+'-ORIENTED-REVIEW.stl')))
            assert m.isSolid() and not m.hasNonManifolds(),o.Name
            error=abs(m.Volume-o.Shape.Volume)/o.Shape.Volume
            assert error<.01,(o.Name,error)
            report['stl'].append({'name':o.Name,'closed':m.isSolid(),'nonmanifold':m.hasNonManifolds(),'volume_relative_error':error})
step=Part.read(str(OUT/'TresVizo-case-A4-with-RESERVES.step'))
assert step.isValid() and len(step.Solids)==42
report['step']={'valid':True,'solids':len(step.Solids)}
checks=json.loads((OUT/'cad-checks.json').read_text())
assert not any(checks[k] for k in ('collisions','coax_collisions','extraction_collisions'))
report['cad_checks_pass']=True
(OUT/'reopen-checks.json').write_text(json.dumps(report,indent=2,ensure_ascii=False)+'\n')
print(json.dumps(report,ensure_ascii=False))
