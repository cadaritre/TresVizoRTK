"""Abre la opcion del domo en FreeCAD con colores de presentacion.

Se ejecuta dentro de la interfaz de FreeCAD:

  FreeCAD view_dome.py

El domo queda semitransparente para que se vea la antena dentro.
"""
from pathlib import Path

import FreeCAD as App

ROOT = Path(__file__).resolve().parent
DOC = ROOT / 'generated' / 'TresVizo-DomeOption.FCStd'

BLANCO = (0.94, 0.94, 0.94)
GRIS = (0.35, 0.37, 0.40)
OSCURO = (0.15, 0.16, 0.18)
AZUL = (0.0, 0.54, 0.99)
DOMO = (0.88, 0.93, 0.99)

VISTA = {
    'V21_01': (BLANCO, 0),
    'V21_02': (BLANCO, 0),
    'V21_04': (AZUL, 0),
    'V21_05': (GRIS, 0),
    'V21_06': (GRIS, 0),
    '07_tapa_plato': (BLANCO, 0),
    '08_domo': (DOMO, 60),
    'Antena': (OSCURO, 0),
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

print('Opcion domo: domo semitransparente, antena en gris oscuro')
