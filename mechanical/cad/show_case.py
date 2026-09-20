"""Abre el FCStd A0 en FreeCAD y guarda vistas de revision del CAD real."""
from pathlib import Path
import FreeCAD as App
import FreeCADGui as Gui
import Part

HERE = Path(__file__).resolve().parent
OUT = HERE.parent / 'exports' / 'review-a0'
path = str(HERE / 'TresVizo-case-A0.FCStd')
doc = next((d for d in App.listDocuments().values() if d.FileName == path), None)
if doc is None:
    doc = App.openDocument(path)
App.setActiveDocument(doc.Name)
Gui.activateWorkbench('PartWorkbench')
for o in doc.Objects:
    if hasattr(o, 'ColorRGB'):
        o.ViewObject.ShapeColor = tuple(float(x) for x in o.ColorRGB.split(','))
        o.ViewObject.LineColor = (0.17,0.20,0.22)
        o.ViewObject.DisplayMode = 'Flat Lines'
        o.ViewObject.LineWidth = 1.0
        o.ViewObject.Visibility = o.VisibleEnMontaje
        o.ViewObject.Deviation = 0.1
Gui.Selection.clearSelection()
view = Gui.activeDocument().activeView()
view.setCameraType('Orthographic')
# Camara desde el frente +Y, elevada: Z de camara mira hacia observador.
camera = App.Rotation(App.Vector(-1,0.45,0), App.Vector(0,0,1), App.Vector(0.45,1,0.35), 'ZXY')
view.setCameraOrientation(camera.Q)
view.fitAll()
Gui.updateGui()
view.saveImage(str(OUT/'case-assembled.png'),1400,1600,'White')
doc.recompute()
doc.save()

# Documento separado: corte ilustrativo. Nunca exportar estas piezas cortadas.
review = App.newDocument('TresVizoCase_Interior_A0')
review.Label = 'TresVizo | interior A0 - reservas pendientes'
cut = Part.makeBox(100,100,220,App.Vector(-50,0,-1))
for o in doc.Objects:
    if not hasattr(o, 'ColorRGB') or o.Name == 'PoleAxis':
        continue
    if o.Name == 'ServiceCover':
        continue
    target = review.addObject('PartDesign::Feature',o.Name)
    target.Label = o.Label
    target.Shape = o.Shape.cut(cut) if o.Name in ['MainShell','Radome','Base'] else o.Shape
    target.ViewObject.ShapeColor = tuple(float(x) for x in o.ColorRGB.split(','))
    target.ViewObject.LineColor = (0.17,0.2,0.22)
    target.ViewObject.DisplayMode = 'Flat Lines'
    target.ViewObject.LineWidth = 1.0
review.recompute()
iview = Gui.activeDocument().activeView()
iview.setCameraType('Orthographic')
iview.setCameraOrientation(camera.Q)
iview.fitAll()
Gui.updateGui()
iview.saveImage(str(OUT/'case-interior-RESERVES.png'),1400,1600,'White')
review.saveAs(str(HERE/'TresVizo-case-A0-INTERIOR.FCStd'))
App.setActiveDocument(doc.Name)
Gui.activeDocument().activeView().fitAll()
Gui.updateGui()
print('Carcasa A0 y corte interior abiertos. Las reservas NO confirman montaje real.')
