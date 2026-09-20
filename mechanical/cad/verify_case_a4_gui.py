"""Ejecutar dentro de FreeCAD GUI: restaura, guarda y reabre cada vista A4.

Valida proveedores visuales, colores, visibilidad y restauracion en la GUI.
La inspeccion de las ventanas 3D se realiza ademas desde la interfaz.
"""
from pathlib import Path
from datetime import datetime
import json
import hashlib
import os
import FreeCAD as App
import FreeCADGui as Gui
from PySide import QtCore

cad=Path(os.environ.get('TRESVIZO_CAD_DIR',Path(__file__).resolve().parent))
out=Path(os.environ.get('TRESVIZO_GUI_REPORT_DIR',cad.parent/'exports/review-a4'))
out.mkdir(parents=True,exist_ok=True)
roundtrip=out/'gui-roundtrip'
roundtrip.mkdir(exist_ok=True)
reports=[]
Gui.activateWorkbench('PartWorkbench')
for suffix in ('','-EXPLODED','-INTERIOR'):
    path=cad/f'TresVizo-case-A4{suffix}.FCStd'
    doc=next((d for d in App.listDocuments().values() if d.FileName==str(path)),None)
    if doc is None:
        doc=App.openDocument(str(path))
    App.setActiveDocument(doc.Name)
    objects=[o for o in doc.Objects if o.TypeId=='Part::Feature']
    for obj in objects:
        assert obj.Shape.isValid() and len(obj.Shape.Solids)==1,obj.Name
        assert obj.ViewObject is not None,obj.Name
        color=tuple(float(c) for c in obj.ColorRGB.split(','))
        assert max(abs(a-b) for a,b in zip(color,obj.ViewObject.ShapeColor))<.005,obj.Name
        expected=getattr(obj,'VisibleEnMontaje',True)
        assert obj.ViewObject.Visibility==expected,obj.Name
    doc.recompute()
    Gui.activeDocument().activeView().fitAll()
    Gui.updateGui()
    # Guardar una copia evita modificar el documento de entrega durante la prueba.
    copy_path=roundtrip/path.name
    doc.saveAs(str(copy_path))
    App.closeDocument(doc.Name)
    doc=App.openDocument(str(copy_path))
    App.setActiveDocument(doc.Name)
    Gui.activeDocument().activeView().fitAll()
    Gui.updateGui()
    valid=[o for o in doc.Objects if o.TypeId=='Part::Feature']
    assert len(valid)==len(objects),suffix
    assert all(o.Shape.isValid() and o.ViewObject is not None for o in valid),suffix
    reports.append({'file':path.name,'restored_view_providers':len(valid),
        'roundtrip_copy_saved_with_FreeCAD_GUI':True,'roundtrip_copy_reopened_with_FreeCAD_GUI':True,
        'source_sha256':hashlib.sha256(path.read_bytes()).hexdigest(),
        'copy_sha256':hashlib.sha256(copy_path.read_bytes()).hexdigest()})
    App.closeDocument(doc.Name)
    doc=App.openDocument(str(path))
    Gui.activeDocument().activeView().fitAll()
(out/'gui-checks.json').write_text(json.dumps({
    'tested_at':datetime.now().isoformat(timespec='seconds'),
    'version':App.Version(),'qt_version':QtCore.qVersion(),
    'executable_home':App.getHomePath(),'pid':os.getpid(),
    'scope':'Restauracion, guardado y reapertura; no certifica estabilidad prolongada.',
    'documents':reports},ensure_ascii=False,indent=2)+'\n')
App.Console.PrintMessage('A4: tres documentos guardados y reabiertos en FreeCAD GUI.\n')
