"""Abre V2.2 en FreeCAD con colores de presentacion.

Se ejecuta dentro de la interfaz de FreeCAD, no en consola: las propiedades de
color viven en el ViewObject y solo existen con la interfaz cargada.

  FreeCAD view_v2_2.py

El tubo queda semitransparente para que se vean por dentro el respaldo, los
toalleros, la pantalla, el boton y la plataforma del IMU. Las bandas de TPU van
en gris oscuro. Los objetos ref_* son componentes comprados: se ven para
entender el montaje, no se imprimen.
"""
from pathlib import Path

import FreeCAD as App

ROOT = Path(__file__).resolve().parent
DOC = ROOT / 'generated' / 'TresVizo-V2.2.FCStd'

BLANCO = (0.94, 0.94, 0.94)
GRIS = (0.35, 0.37, 0.40)
AZUL = (0.0, 0.54, 0.99)        # azul de marca #008AFC: la plataforma nueva

VISTA = {
    '01_threaded_base': (BLANCO, 0),
    '02_logo_tube': (BLANCO, 60),
    '03_antenna_cap': (BLANCO, 35),
    '04_imu_platform': (AZUL, 0),
    '05_panel_cover': (GRIS, 0),
    '06_bumper_bottom': ((0.20, 0.22, 0.25), 0),
    '07_bumper_top': ((0.20, 0.22, 0.25), 0),
    'ref_imu_pcb': ((0.10, 0.28, 0.62), 0),
    'ref_imu_chip': ((0.05, 0.05, 0.05), 0),
    'ref_sma': ((0.80, 0.64, 0.15), 0),
    'ref_antenna': ((0.15, 0.15, 0.15), 50),
    'ref_oled': ((0.04, 0.40, 0.30), 0),
    'ref_button': ((0.83, 0.40, 0.10), 0),
    'ref_battery': ((0.55, 0.30, 0.68), 30),
    'ref_um980': ((0.15, 0.62, 0.35), 30),
    'ref_thing_plus': ((0.75, 0.22, 0.17), 30),
    'ref_nut_keepers': ((0.55, 0.57, 0.60), 0),
    'ref_nut': ((0.80, 0.64, 0.25), 0),
    'ref_jst': ((0.93, 0.93, 0.88), 0),
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

print('V2.2: tubo y tapa semitransparentes, plataforma del IMU en azul, panel en gris, '
      'bandas de TPU en gris oscuro; los ref_* son componentes comprados')
