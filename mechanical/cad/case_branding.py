"""Grabado del simbolo TresVizo sobre la envolvente exterior, unidades mm."""
import json
from pathlib import Path
import FreeCAD as App
import Part
import build_case as a0

HERE=Path(__file__).resolve().parent

def engrave_shell(shell, config):
    data=json.loads((HERE/'branding/tresvizo-symbol.json').read_text())
    height=config['height_mm']
    depth=config['depth_mm']
    center=config['center_z_mm']
    assert 0<depth<1 and 20<=height<=40
    scale=height/444
    faces=[]
    for loop in data['loops']:
        # Desde +Y (frente del portillo), la derecha de pantalla es -X.
        points=[App.Vector(-(u-192.5)*scale,20,center+(221.5-v)*scale)
                for u,v in loop['points']]
        faces.append((loop['signed_area_px2'],Part.Face(Part.makePolygon(points))))
    outer=max(faces,key=lambda f:f[0])
    hexagon=outer[1]
    for area,face in faces:
        if area<0:hexagon=hexagon.cut(face)
    islands=[hexagon]+[face for area,face in faces if area>0 and face is not outer[1]]
    prisms=Part.makeCompound([f.extrude(App.Vector(0,25,0)) for f in islands])
    z0,z1=center-height/2-1,center+height/2+1
    skin=a0.envelope(z0,z1,1).cut(a0.envelope(z0,z1,-depth))
    cutter=prisms.common(skin)
    result=shell.cut(cutter).removeSplitter()
    assert result.isValid() and len(result.Solids)==1
    assert shell.Volume-result.Volume>50
    return result, cutter
