"""Abre V2.1 en FreeCAD con colores de presentacion.

Se ejecuta dentro de la interfaz de FreeCAD, no en consola: las propiedades de
color viven en el ViewObject y solo existen con la interfaz cargada.

  FreeCAD view_v2_1.py

El tubo queda semitransparente para que se vea el trineo nuevo por dentro; en
el arbol se le puede quitar la transparencia.
"""
from pathlib import Path

import FreeCAD as App

ROOT = Path(__file__).resolve().parent
DOC = ROOT / 'generated' / 'TresVizo-V2.1.FCStd'

BLANCO = (0.94, 0.94, 0.94)
GRIS = (0.35, 0.37, 0.40)
AZUL = (0.0, 0.54, 0.99)        # azul de marca #008AFC: el trineo nuevo

VISTA = {
    '01_threaded_base': (BLANCO, 0),
    '02_logo_tube': (BLANCO, 55),
    '03_antenna_cap': (BLANCO, 0),
    '04_universal_sled': (AZUL, 0),
    '05_panel_cover': (GRIS, 0),
    '06_aux_panel_cover': (GRIS, 0),
}

doc = App.openDocument(str(DOC))

try:
    import FreeCADGui as Gui
except ImportError:
    Gui = None

for obj in doc.Objects:
    vista = getattr(obj, 'ViewObject', None)
    if vista is None:
        continue
    color, transparencia = next((v for clave, v in VISTA.items() if clave in obj.Name),
                                (GRIS, 0))
    try:
        vista.DisplayMode = 'Shaded'
        vista.ShapeColor = color
        vista.Transparency = transparencia
        vista.LineColor = color
        vista.PointColor = color
    except Exception as error:
        print(f'{obj.Name}: no se pudo ajustar la vista ({error})')

if Gui is not None:
    try:
        Gui.activeDocument().activeView().viewAxonometric()
        Gui.SendMsgToActiveView('ViewFit')
    except Exception:
        pass

print('V2.1: tubo semitransparente, trineo en azul, paneles en gris')
