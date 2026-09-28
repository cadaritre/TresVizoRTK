"""Abre el Meridian3 en FreeCAD con colores de presentacion.

Se ejecuta dentro de la interfaz de FreeCAD (las propiedades de color solo
existen con la interfaz cargada):

  FreeCAD view_meridian3.py

El tubo queda semitransparente; las referencias (ref_*: carrier, Tiny,
Tiny-Adapter, latiguillo) en color. Las referencias NO se imprimen.
"""
from pathlib import Path

import FreeCAD as App

ROOT = Path(__file__).resolve().parent
doc = App.openDocument(str(ROOT / 'generated' / 'Meridian3.FCStd'))

BLANCO = (0.94, 0.94, 0.94)
GRIS = (0.35, 0.37, 0.40)
AZUL = (0.0, 0.54, 0.99)          # azul de marca #008AFC
VISTA = {
    '01_threaded_base': (BLANCO, 0), '02_logo_tube': (BLANCO, 60), '03_antenna_cap': (BLANCO, 40),
    '04_sled': (AZUL, 0), '05_usb_panel_cover': (GRIS, 0),
    'ref_carrier_um980': ((0.16, 0.55, 0.24), 0), 'ref_sma_carrier': ((0.8, 0.63, 0.12), 0),
    'ref_clavija_inferior': ((0.86, 0.47, 0.12), 0), 'ref_clavija_superior': ((0.86, 0.47, 0.12), 0),
    'ref_cable': ((0.1, 0.1, 0.1), 0), 'ref_tiny': ((0.12, 0.35, 0.78), 0),
    'ref_tiny_adapter': ((0.0, 0.54, 0.99), 0),
}

for obj in doc.Objects:
    vista = getattr(obj, 'ViewObject', None)
    if vista is None:
        continue
    color, transparencia = next((v for k, v in VISTA.items() if obj.Name.endswith(k)), (GRIS, 0))
    try:
        vista.DisplayMode = 'Shaded'
        vista.ShapeColor = color
        vista.Transparency = transparencia
    except Exception as error:
        print(f'{obj.Name}: no se pudo ajustar la vista ({error})')

try:
    import FreeCADGui as Gui
    Gui.activeDocument().activeView().viewAxonometric()
    Gui.SendMsgToActiveView('ViewFit')
except Exception:
    pass
print('Meridian3: tubo semitransparente, trineo en azul, referencias en color')
