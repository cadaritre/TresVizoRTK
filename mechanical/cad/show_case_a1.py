"""Abre A1 y una seccion ampliada del cartucho, sin modificar A0."""
from pathlib import Path
import FreeCAD as App
import FreeCADGui as Gui
import Part

HERE=Path(__file__).resolve().parent
OUT=HERE.parent/'exports'/'review-a1'
path=str(HERE/'TresVizo-case-A1.FCStd')
doc=next((d for d in App.listDocuments().values() if d.FileName==path),None)
if doc is None: doc=App.openDocument(path)
App.setActiveDocument(doc.Name)
Gui.activateWorkbench('PartWorkbench')
for o in doc.Objects:
    if hasattr(o,'ColorRGB'):
        o.ViewObject.ShapeColor=tuple(float(x) for x in o.ColorRGB.split(','))
        o.ViewObject.LineColor=(0.17,0.20,0.22)
        o.ViewObject.DisplayMode='Flat Lines'
        o.ViewObject.LineWidth=1.0
        o.ViewObject.Visibility=o.VisibleEnMontaje
        o.ViewObject.Deviation=0.1
Gui.Selection.clearSelection()
view=Gui.activeDocument().activeView()
view.setCameraType('Orthographic')
camera=App.Rotation(App.Vector(-1,0.4,0),App.Vector(0,0,1),App.Vector(0.4,1,0.25),'ZYX')
view.setCameraOrientation(camera.Q)
view.fitAll()
doc.recompute()
doc.save()

review=App.newDocument('TresVizoMount_A1')
review.Label='TresVizo A1 | CORTE del cartucho - no fabricar el corte'
cut=Part.makeBox(100,100,60,App.Vector(-50,0,-1))
for o in doc.Objects:
    if not hasattr(o,'ColorRGB') or o.Name in ('MainShell','ServiceCover','OpenShoulder','AntennaSupport'):
        continue
    if o.Name not in ('Base','Frame') and o not in doc.Metal.Group and o not in doc.Hardware.Group:
        continue
    s=o.Shape.copy()
    if o.Name=='Frame': s=s.common(Part.makeBox(80,80,7,App.Vector(-40,-40,21)))
    s=s.cut(cut)
    if s.isNull() or s.Volume<0.001: continue
    n=review.addObject('PartDesign::Feature',o.Name)
    n.Label=o.Label
    n.Shape=s
    n.ViewObject.ShapeColor=tuple(float(x) for x in o.ColorRGB.split(','))
    n.ViewObject.LineColor=(0.17,0.20,0.22)
    n.ViewObject.DisplayMode='Flat Lines'
review.recompute()
rv=Gui.activeDocument().activeView()
rv.setCameraType('Orthographic')
rv.setCameraOrientation(camera.Q)
rv.fitAll()
review.saveAs(str(HERE/'TresVizo-case-A1-MOUNT-SECTION.FCStd'))
App.setActiveDocument(doc.Name)
Gui.activeDocument().activeView().fitAll()
Gui.updateGui()
print('A1 y corte del cartucho abiertos. La antena es una reserva, el montaje no esta ensayado.')
