"""Abre V2 en FreeCAD con vista sombreada y colores de presentacion.

Se ejecuta dentro de la interfaz de FreeCAD, no en consola: las propiedades de
color viven en el ViewObject y solo existen con la interfaz cargada.

  "C:/Program Files/FreeCAD 1.1/bin/FreeCAD.exe" view_v2.py
"""
from pathlib import Path

import FreeCAD as App

ROOT = Path(__file__).resolve().parent
DOC = ROOT / 'generated' / 'TresVizo-V2.FCStd'

NEGRO = (0.06, 0.06, 0.07)
BLANCO = (0.94, 0.94, 0.94)
GRIS = (0.55, 0.57, 0.60)

# Por fragmento del nombre de la pieza. Todo en blanco: sin contraste entre
# piezas se lee mejor la forma del conjunto.
COLORES = {
    '01_base_rosca': BLANCO,
    '02_tubo_logo': BLANCO,
    '03_tapa_antena': BLANCO,
    '04_trineo_universal': BLANCO,
    '05_tapa_panel': BLANCO,
    '06_tapa_panel_aux': BLANCO,
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
    color = next((c for clave, c in COLORES.items() if clave in obj.Name), GRIS)
    try:
        vista.DisplayMode = 'Shaded'
        vista.ShapeColor = color
        vista.Transparency = 0
        # Sin aristas resaltadas: en sombreado puro se aprecia mejor la forma.
        vista.LineColor = color
        vista.PointColor = color
    except Exception as error:
        print(f'{obj.Name}: no se pudo ajustar la vista ({error})')

doc.save()

if Gui is not None:
    try:
        Gui.activeDocument().activeView().viewAxonometric()
        Gui.SendMsgToActiveView('ViewFit')
    except Exception:
        pass

print('vista aplicada: cuerpo y tapas de panel en negro, '
      'tapaderas inferior y superior en blanco, trineo en gris')
