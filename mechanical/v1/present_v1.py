"""Ejecutar en consola GUI FreeCAD 1.0.2; guarda apariencia nativa y vistas."""
from pathlib import Path
import FreeCAD as App, FreeCADGui as Gui, json
ROOT=Path(__file__).resolve().parent;OUT=ROOT/'generated'
I=json.loads((OUT/'model-index.json').read_text());filename=str(OUT/'TresVizo-V1.FCStd')
doc=next((d for d in App.listDocuments().values() if d.FileName==filename),None)
if doc is None:doc=App.openDocument(filename)
App.setActiveDocument(doc.Name);Gui.activeDocument().activeView()
doc.Label='TresVizo V1 - prototipo completo'
labels={'A5_MainShell':'01 Cuerpo exterior','A5_Chassis':'02 Chasis y base del jalon','A5_BatteryIMUCarrier':'03 Cuna bateria + IMU + bandejas power','A5_AntennaCap':'04 Tapa de antena','ModulePanel':'05 Panel USB-C, luces y boton','A5_IMUNutBar':'06 Prensa de tuercas BMI088','ButtonCap':'07 Actuador del boton','ButtonCartridge':'08 Cartucho del pulsador','StatusLens':'09 Difusor de estado - translucido','ChargeLens':'10 Difusor de carga - translucido','PowerBoost':'PowerBoost 1000C - sin USB-A','SoftPower':'SparkFun Soft Power Switch Mk2','A5_BatteryReserve':'Bateria - reserva 56 x 12 x 69 mm','A5_GNSSReserve':'UM980 - reserva de montaje','A5_ESPReference':'ESP32-S3 Tiny','A5_SDReference':'Modulo microSD','A5_IMUReserve':'BMI088 - PCB fija sobre datum','TinyAdapterPosition':'Waveshare Tiny Adapter','A5_HA901Reserve':'Antena HA-901A centrada','TactileBody':'Pulsador AU-101 - reserva nominal','TactileStem':'Vastago del pulsador','USBModule':'Adafruit 5871 - placa USB-C','RGBLed':'LED RGB de estado'}
for o in doc.Objects:
 if not hasattr(o,'Shape') or hasattr(o,'Group'):continue
 if o.Name in labels:o.Label=labels[o.Name]
 o.ViewObject.ShapeColor=tuple(c/255 for c in I['colors'].get(o.Name,[100,140,150]))
 o.ViewObject.LineColor=(.13,.16,.19);o.ViewObject.DisplayMode='Flat Lines';o.ViewObject.LineWidth=1
 o.ViewObject.Visibility=o.Name not in I['routes']+I.get('tools',[])+['A5_IMUTarget','A5_CoaxRouteReserve','TinyUSBPlugReserve']
 for prop in ['Subdivision','Deviation']:
  if prop=='Deviation' and hasattr(o.ViewObject,prop):setattr(o.ViewObject,prop,.15)
doc.PrintParts.Label='01 Para imprimir - 10 piezas + plantilla'
doc.Fasteners.Label='02 Tornilleria para comprar - 19 tornillos / 13 tuercas'
doc.Components.Label='03 Componentes - no imprimir'
doc.A5_HA901Reserve.ViewObject.ShapeColor=(.82,.84,.83)
doc.PrintParts.Group=[doc.getObject(n) for n in labels if n in I['printed']]+[doc.PrintTools]
# Subcarpetas con recuentos de compra, sin duplicar solidos.
sets=[('M3x8','M3 x 8 - 10 piezas',[n for n in I['hardware'] if ('Bolt' in n and not any(t in n for t in ['Module','Antenna','IMUPcb'])) or n=='ButtonM3']),('M3x20','M3 x 20 - 2 piezas',[n for n in I['hardware'] if 'ModuleBolt' in n]),('M25x8','M2.5 x 8 - antena - 3 piezas',[n for n in I['hardware'] if 'AntennaBolt' in n]),('M25x12','M2.5 x 12 - IMU - 2 piezas',[n for n in I['hardware'] if 'IMUPcbBolt' in n]),('M2x5','M2 x 5 - USB - 2 piezas',[n for n in I['hardware'] if 'USBScrew' in n]),('M3Nuts','Tuercas M3 - 11 piezas',[n for n in I['hardware'] if 'Nut' in n and 'IMUPcb' not in n]),('M25Nuts','Tuercas M2.5 - 2 piezas',[n for n in I['hardware'] if 'IMUPcbNut' in n]),('PoleInsert','Inserto McMaster 90611A121 - 1 pieza',['A5_FlangedInsert'])]
for name,label,names in sets:
 g=doc.getObject(name) or doc.addObject('App::DocumentObjectGroup',name);g.Label=label;doc.Fasteners.addObject(g)
 for n in names:doc.Fasteners.removeObject(doc.getObject(n));g.addObject(doc.getObject(n))
Gui.activateWorkbench('PartWorkbench');Gui.Selection.clearSelection();doc.recompute()
view=Gui.activeDocument().activeView()
front_rotation=App.Rotation(App.Vector(-2,1,0),App.Vector(0,0,1),App.Vector(1,2,.8),'ZXY')
view.setCameraOrientation(front_rotation.Q);view.fitAll()
# Vistas del mismo CAD; solo alternar visibilidad, nunca mover las piezas.
view.saveImage(str(OUT/'v1-assembled.png'),1200,1400,'White')
hide=['A5_MainShell','A5_AntennaCap','A5_HA901Reserve']+[n for n in I['hardware'] if n.startswith(('A5_AntennaBolt','A5_CapClosure'))]
for n in hide:doc.getObject(n).ViewObject.Visibility=False
view.setCameraOrientation(App.Rotation(App.Vector(2,-1,0),App.Vector(0,0,1),App.Vector(-1,-2,.6),'ZXY').Q);view.fitAll();view.saveImage(str(OUT/'v1-interior.png'),1200,1400,'White')
for n in hide:doc.getObject(n).ViewObject.Visibility=True
view.setCameraOrientation(front_rotation.Q);view.fitAll();doc.recompute();doc.save()
Gui.activeDocument().activeView().redraw()
print('V1 ABIERTA EN FREECAD',App.Version()[:3],len([o for o in doc.Objects if hasattr(o,'Shape') and not hasattr(o,'Group')]))
