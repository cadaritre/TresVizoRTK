"""Abre V2.2 en FreeCAD con los colores de impresion.

Se ejecuta dentro de la interfaz de FreeCAD, no en consola: las propiedades de
color viven en el ViewObject y solo existen con la interfaz cargada.

  FreeCAD view_v2_2.py

Cuerpo en negro mate y bandas de TPU en el azul marino del logotipo, como se
van a imprimir. Con VER_DENTRO = True el tubo y la tapa quedan
semitransparentes y se ven el respaldo, los toalleros, la pantalla, el boton
y la plataforma del IMU. Los objetos ref_* son componentes comprados: se ven
para entender el montaje, no se imprimen.
"""
from pathlib import Path

import FreeCAD as App

ROOT = Path(__file__).resolve().parent
DOC = ROOT / 'generated' / 'TresVizo-V2.2.FCStd'

VER_DENTRO = False

# Negro mate sin llegar a 0: con negro puro se pierde el sombreado y la pieza se
# ve como una silueta.
NEGRO_MATE = (0.07, 0.07, 0.08)
AZUL_MARINO = (0.08, 0.28, 0.50)   # #144880, azul marino del logotipo de TresVizo
GRIS = (0.35, 0.37, 0.40)

# Clave: (color, transparencia en %, mate). Las claves mas largas van antes que
# las que contienen: 'ref_nut_keepers' antes que 'ref_nut'.
VISTA = {
    '01_threaded_base': (NEGRO_MATE, 0, True),
    '02_logo_tube': (NEGRO_MATE, 60 if VER_DENTRO else 0, True),
    '03_antenna_cap': (NEGRO_MATE, 35 if VER_DENTRO else 0, True),
    '04_imu_platform': (NEGRO_MATE, 0, True),
    '05_panel_cover': (NEGRO_MATE, 0, True),
    '06_bumper_bottom': (AZUL_MARINO, 0, True),
    '07_bumper_top': (AZUL_MARINO, 0, True),
    'ref_imu_pcb': ((0.10, 0.28, 0.62), 0, False),
    'ref_imu_chip': ((0.05, 0.05, 0.05), 0, False),
    'ref_sma': ((0.80, 0.64, 0.15), 0, False),
    'ref_antenna': ((0.15, 0.15, 0.15), 50, False),
    'ref_oled': ((0.04, 0.40, 0.30), 0, False),
    'ref_button': ((0.83, 0.40, 0.10), 0, False),
    'ref_battery': ((0.55, 0.30, 0.68), 30, False),
    'ref_um980': ((0.15, 0.62, 0.35), 30, False),
    'ref_thing_plus': ((0.75, 0.22, 0.17), 30, False),
    'ref_nut_keepers': ((0.55, 0.57, 0.60), 0, False),
    'ref_nut': ((0.80, 0.64, 0.25), 0, False),
    'ref_jst': ((0.93, 0.93, 0.88), 0, False),
}


def acabado_mate(vista, color, transparencia):
    """Sin brillo especular: el plastico impreso no refleja como el material
    por defecto de FreeCAD."""
    materiales = []
    for material in vista.ShapeAppearance:
        material.DiffuseColor = color
        material.AmbientColor = tuple(c * 0.5 for c in color)
        material.SpecularColor = (0.0, 0.0, 0.0)
        material.Shininess = 0.0
        material.Transparency = transparencia / 100.0
        materiales.append(material)
    vista.ShapeAppearance = materiales


doc = App.openDocument(str(DOC))

try:
    import FreeCADGui as Gui
except ImportError:
    Gui = None

for obj in doc.Objects:
    vista = getattr(obj, 'ViewObject', None)
    if vista is None:
        continue
    color, transparencia, mate = next((v for clave, v in VISTA.items() if clave in obj.Name),
                                      (GRIS, 0, False))
    try:
        vista.DisplayMode = 'Shaded'
        vista.ShapeColor = color
        vista.Transparency = transparencia
        vista.LineColor = color
        vista.PointColor = color
        if mate:
            acabado_mate(vista, color, transparencia)
    except Exception as error:
        print(f'{obj.Name}: no se pudo ajustar la vista ({error})')

if Gui is not None:
    try:
        Gui.activeDocument().activeView().viewAxonometric()
        Gui.SendMsgToActiveView('ViewFit')
    except Exception:
        pass

print('V2.2: cuerpo en negro mate y bandas de TPU en azul marino'
      + ('; tubo y tapa semitransparentes' if VER_DENTRO else '')
      + '. Los ref_* son componentes comprados.')
