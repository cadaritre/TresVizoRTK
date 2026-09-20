"""Vistas ortográficas de los triángulos exportados por FreeCAD, sin geometría inventada."""
import json, math, copy, struct, zipfile, argparse
import xml.etree.ElementTree as ET
from pathlib import Path
import numpy as np
from PIL import Image, ImageDraw, ImageFont

SOURCE_ROOT=Path(__file__).resolve().parent
parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('--input-dir',type=Path,default=SOURCE_ROOT.parent/'integration-review'/'generated')
ROOT=parser.parse_args().input_dir.resolve()
M={m['name']:m for m in json.loads((ROOT/'render-meshes.json').read_text())}
S=2
W,H=1800,1120
im=Image.new('RGB',(W*S,H*S),'#f1f3f5')
draw=ImageDraw.Draw(im)
font_path='/System/Library/Fonts/Supplemental/Arial.ttf'
bold_path='/System/Library/Fonts/Supplemental/Arial Bold.ttf'

def text(x,y,t,size=22,fill='#26394a',bold=False):
    f=ImageFont.truetype(bold_path if bold else font_path,size*S)
    draw.text((x*S,y*S),t,font=f,fill=fill)

def render(names,rect,view,translations=None):
    x0,y0,w,h=rect
    view=np.array(view,dtype=float);view/=np.linalg.norm(view)
    right=np.cross(view,[0,0,1]);right/=np.linalg.norm(right)
    up=np.cross(right,view)
    rot=np.array([right,up,view]).T
    vv=[];ff=[];cc=[];k=0
    for name in names:
        m=M[name]; v=np.array(m['vertices'])
        if translations and name in translations: v+=np.array(translations[name])
        vv.extend(v); ff.extend(np.array(m['faces'])+k)
        col=m['color']
        if name in ['A5_MainShell','A5_Chassis','A5_AntennaCap']: col=[158,169,178]
        if name=='A5_HA901Reserve': col=[52,62,70]
        cc.extend([col]*len(m['faces']));k+=len(v)
    v=np.array(vv);f=np.array(ff);c=np.array(cc);a=v@rot
    lo=a[:,:2].min(axis=0);hi=a[:,:2].max(axis=0)
    scale=min(w/(hi[0]-lo[0]),h/(hi[1]-lo[1]))*.91
    middle=(hi+lo)/2
    coords=np.column_stack(((a[:,0]-middle[0])*scale+x0+w/2,-(a[:,1]-middle[1])*scale+y0+h/2))*S
    triangles=v[f]
    normal=np.cross(triangles[:,1]-triangles[:,0],triangles[:,2]-triangles[:,0])
    lengths=np.linalg.norm(normal,axis=1);normal/=np.maximum(lengths[:,None],1e-12)
    light=view*.8+up*.6-right*.35;light/=np.linalg.norm(light)
    shade=.48+.50*np.clip(normal@light,0,1)
    shaded=np.minimum(c*shade[:,None]+7,255).astype(int)
    depth=a[f,2].mean(axis=1)
    order=np.argsort(depth)
    for i in order:
        if normal[i]@view<-.01: continue
        draw.polygon([tuple(q) for q in coords[f[i]]],fill=tuple(shaded[i]))
    def project(v):
        q=np.array(v)@rot
        return ((q[0]-middle[0])*scale+x0+w/2,-(q[1]-middle[1])*scale+y0+h/2)
    return project

text(60,35,'TRESVIZO  /  PANEL CON MÓDULOS COMERCIALES',33,bold=True)
text(60,86,'Propuesta mecánica A5 · septiembre 2026 · cotas en mm',21,fill='#607383')
for x,w in [(40,480),(540,470),(1030,730)]:
    draw.rounded_rectangle((x*S,140*S,(x+w)*S,940*S),radius=22*S,fill='#ffffff')
text(65,163,'01  INTEGRADO EN LA CARCASA',20,bold=True)
text(565,163,'02  CARA EXTERIOR',20,bold=True)
text(1055,163,'03  MONTAJE POSTERIOR',20,bold=True)

panel=[n for n in M if not n.startswith('A5_') and n not in ['TinyAdapterPosition','TinyUSBPlugReserve']]
render(['A5_MainShell','A5_Chassis','A5_AntennaCap','A5_HA901Reserve']+panel,(75,220,420,620),(.12,1,.13))
front=render(panel,(595,260,340,555),(0,1,0))
back=render(panel,(1080,265,620,565),(-.7,-1,.45))

def callout(project,point,end,label,ylabel=None):
    a=project(point);b=end
    draw.line((a[0]*S,a[1]*S,b[0]*S,b[1]*S),fill='#728997',width=2*S)
    draw.ellipse(((a[0]-3)*S,(a[1]-3)*S,(a[0]+3)*S,(a[1]+3)*S),fill='#24a49e')
    text(b[0],b[1] if ylabel is None else ylabel,label,18)

# Leyendas cortas fuera de la silueta; las caras coloreadas pertenecen al CAD.
text(587,217,'Tapa curva: 28 × 53',20,fill='#516a79')
text(568,842,'USB-C encastrado 1.2 mm',19)
text(568,870,'Botón y dos ventanas al ras',19)
text(1060,842,'4 fijaciones M2 para USB',19)
text(1060,870,'Cartucho de botón desmontable',19)
text(65,862,'Mismos anclajes M3 de la tapa',19)
text(65,890,'Ajustes de carcasa y repisa incluidos',18,fill='#607383')

text(60,975,'3 PIEZAS ESTRUCTURALES + 2 DIFUSORES',22,bold=True)
text(60,1018,'Panel con soportes · actuador cautivo · cartucho para micro-switch Steren AU-101.',21)
text(60,1060,'Panel actualizado al A5 simplificado. Integración completa pendiente: ver INTEGRATION_REVIEW.md antes de imprimir.',18,fill='#607383')
im.resize((W,H),Image.Resampling.LANCZOS).save(ROOT/'panel-preview.png')

# Segunda vista: despiece de los mismos sólidos, para entender el montaje.
im=Image.new('RGB',(1600*S,1080*S),'#f1f3f5');draw=ImageDraw.Draw(im)
text(55,35,'PANEL / DESPIECE DE MONTAJE',32,bold=True)
text(55,85,'Cada pieza se desmonta desde el interior. Electrónica comercial representada por envolventes.',21,fill='#607383')
translations={}
for n in ['USBModule','USBReceptacle','USBPortInterior','USBContactTongue','USBChip']+[n for n in M if n.startswith('USBScrew')]: translations[n]=[0,0,17]
for n in ['ButtonCartridge','TactileBody','TactileStem']+[n for n in M if n.startswith('ButtonScrew')]: translations[n]=[0,-17,0]
translations['ButtonCap']=[0,9,0]
for n in ['StatusLens','ChargeLens']: translations[n]=[0,9,0]
translations['RGBLed']=[0,-9,0]
render(panel,(250,145,1100,760),(-.65,-1,.28),translations)
text(60,950,'USB: M2 × 5  ·  Cartucho: M2 × 8  ·  Panel: anclajes M3 existentes',23,bold=True)
text(60,998,'AU-101: alojamiento nominal de 6 mm ajustable en parameters.json; confirmar cuerpo, altura y carrera con la pieza comprada.',19)
im.resize((1600,1080),Image.Resampling.LANCZOS).save(ROOT/'panel-exploded.png')

# Propiedades de presentación de FreeCAD. Se usa la estructura del documento A5
# como plantilla; no se altera su geometría ni su archivo.
source=SOURCE_ROOT.parent/'A5'/'TresVizo-A5.FCStd'
with zipfile.ZipFile(source) as z:
    original_gui=ET.fromstring(z.read('GuiDocument.xml'))
    template=original_gui.find(".//ViewProvider[@name='MainShell']")
    material=z.read(template.find(".//Property[@name='ShapeAppearance']/MaterialList").get('file'))
gui=ET.Element('Document',SchemaVersion='1',HasExpansion='1')
ET.SubElement(gui,'Expand',count='0')
data=ET.SubElement(gui,'ViewProviderData',Count=str(len(M)))
extra={}
for i,(name,m) in enumerate(M.items()):
    vp=copy.deepcopy(template);vp.set('name',name);vp.set('treeRank',str(i));data.append(vp)
    props=vp.find('Properties')
    col=m['color'];packed=(col[0]<<24)|(col[1]<<16)|(col[2]<<8)
    for prop in props:
        if prop.get('name')=='Visibility':prop[0].set('value','false' if name.startswith('A5_') or name.startswith('Tiny') else 'true')
        if prop.get('name')=='DisplayMode':prop[0].set('value','1')
        if prop.get('name') in ('LineColorArray','PointColorArray'):
            fname=prop.get('name')+'_'+name;prop[0].set('file',fname)
            extra[fname]=struct.pack('<II',1,0x28333d00)
        if prop.get('name')=='ShapeAppearance':
            fname='ShapeAppearance_'+name;prop[0].set('file',fname)
            a=bytearray(material);a[8:12]=struct.pack('<I',packed);extra[fname]=bytes(a)
ET.SubElement(gui,'Camera',settings='OrthographicCamera {\n viewportMapping ADJUST_CAMERA\n position 0 170 115.5\n orientation 1 0 0 1.57079632679\n nearDistance 1\n farDistance 500\n aspectRatio 1\n focalDistance 134\n height 68\n}\n')
path=ROOT/'TresVizo-panel-modules.FCStd'
with zipfile.ZipFile(path) as z: contents={n:z.read(n) for n in z.namelist() if n!='GuiDocument.xml'}
contents['GuiDocument.xml']=ET.tostring(gui,encoding='utf-8',xml_declaration=True)
contents.update(extra)
tmp=path.with_suffix('.tmp')
with zipfile.ZipFile(tmp,'w',zipfile.ZIP_DEFLATED) as z:
    for n,v in contents.items(): z.writestr(n,v)
tmp.replace(path)
print('panel-preview.png, panel-exploded.png y presentación FCStd guardados')
