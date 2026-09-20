"""Reconstruye documentos A4 desde sus BREP sin modificar la geometria.

Uso: python repair_case_a4.py DIRECTORIO_DE_SALIDA
La salida se valida antes de sustituir los documentos de entrega.
"""
import json
import sys
from datetime import datetime
from pathlib import Path
import FreeCAD as App
import build_case_a4 as a4

HERE=Path(__file__).resolve().parent


def repair(out):
    out.mkdir(parents=True,exist_ok=True)
    report=[]
    palette={}
    for suffix in ('','-INTERIOR','-EXPLODED'):
        source=App.openDocument(str(HERE/f'TresVizo-case-A4{suffix}.FCStd'))
        doc=App.newDocument('TresVizo_A4_CLEAN'+suffix.replace('-','_'))
        doc.Label=source.Label
        comparisons=[]
        for old in source.Objects:
            if old.TypeId=='App::DocumentObjectGroup':
                new=doc.addObject(old.TypeId,old.Name)
            else:
                new=doc.addObject('Part::Feature',old.Name)
                new.Shape=a4.standalone_shape(old.Shape)
                comparisons.append({'object':old.Name,
                    'volume_difference_mm3':abs(new.Shape.Volume-old.Shape.Volume),
                    'faces_before':len(old.Shape.Faces),'faces_after':len(new.Shape.Faces),
                    'valid':new.Shape.isValid(),'solids':len(new.Shape.Solids)})
                assert len(new.Shape.Faces)==len(old.Shape.Faces),old.Name
            new.Label=old.Label
            for prop in ('Estado','Fuente','ColorRGB','Revision','FechaGeneracion','Pendientes','VisibleEnMontaje'):
                if prop not in old.PropertiesList: continue
                new.addProperty(old.getTypeIdOfProperty(prop),prop,'Documentacion')
                setattr(new,prop,getattr(old,prop))
            if hasattr(new,'ColorRGB'): palette[new.Name]=new.ColorRGB
            elif new.TypeId=='Part::Feature':
                new.addProperty('App::PropertyString','ColorRGB','Documentacion')
                new.ColorRGB=palette[new.Name]
            if suffix and new.TypeId=='Part::Feature':
                if 'VisibleEnMontaje' not in new.PropertiesList:
                    new.addProperty('App::PropertyBool','VisibleEnMontaje','Presentacion')
                new.VisibleEnMontaje=True
        for old in source.Objects:
            if old.TypeId=='App::DocumentObjectGroup':
                doc.getObject(old.Name).Group=[doc.getObject(o.Name) for o in old.Group]
        doc.recompute()
        target=out/f'TresVizo-case-A4{suffix}.FCStd'
        a4.a1.save_preserving_presentation(doc,target,a4.make_style(doc,None,{}))
        report.append({'file':target.name,'objects':len(doc.Objects),'shapes':comparisons})
        App.closeDocument(doc.Name)
        App.closeDocument(source.Name)
    (out/'repair-checks.json').write_text(json.dumps({
        'repaired_at':datetime.now().isoformat(timespec='seconds'),
        'change':'Part::Feature con BREP independiente y proveedores visuales nuevos',
        'documents':report},ensure_ascii=False,indent=2)+'\n')
    print(json.dumps({'output':str(out),'documents':len(report)},ensure_ascii=False))


if __name__=='__main__': repair(Path(sys.argv[1]).resolve())
