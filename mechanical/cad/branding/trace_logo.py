"""Extrae contornos CAD del simbolo original publicado en tresvizo.com.

No genera una imagen nueva: conserva el hexagono, el 3 y sus cuatro trazos.
La imagen original queda intacta para poder auditar la conversion a vector.
"""
from pathlib import Path
import json
import hashlib
import numpy as np
from PIL import Image
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

HERE=Path(__file__).resolve().parent

def rdp(points, tolerance):
    a,b=points[0],points[-1]
    ab=b-a
    if np.linalg.norm(ab)<1e-9:
        distances=np.linalg.norm(points-a,axis=1)
    else:
        t=np.clip((points-a)@ab/(ab@ab),0,1)
        distances=np.linalg.norm(points-(a+t[:,None]*ab),axis=1)
    i=int(np.argmax(distances))
    if distances[i]<=tolerance:return points[[0,-1]]
    return np.vstack((rdp(points[:i+1],tolerance)[:-1],rdp(points[i:],tolerance)))

source=HERE/'tresvizo-logo-source.png'
alpha=np.asarray(Image.open(source).convert('RGBA'))[:,:387,3]
fig,ax=plt.subplots()
contours=ax.contour(np.pad(alpha,1),levels=[127.5]).allsegs[0]
loops=[]
for raw in contours:
    p=rdp(raw-1,.65)
    if not np.allclose(p[0],p[-1]):p=np.vstack((p,p[0]))
    area=.5*np.sum(p[:-1,0]*p[1:,1]-p[1:,0]*p[:-1,1])
    if abs(area)>8:loops.append({'signed_area_px2':round(float(area),3),'points':p.round(4).tolist()})
plt.close(fig)
assert len(loops)==7, len(loops)
data={'source_page':'https://tresvizo.com/',
      'source_asset':'https://static.wixstatic.com/media/b699f8_1af60a19f2b94883a9c59e91a1d10241~mv2.png',
      'source_sha256':hashlib.sha256(source.read_bytes()).hexdigest(),
      'crop_x_px':[0,387],'raster_size_px':[990,444],
      'simplification_tolerance_px':.65,'loops':loops}
(HERE/'tresvizo-symbol.json').write_text(json.dumps(data,indent=2)+'\n')
path=' '.join('M '+' L '.join(f'{x:g},{y:g}' for x,y in q['points'])+' Z' for q in loops)
(HERE/'tresvizo-symbol.svg').write_text(
    '<svg xmlns="http://www.w3.org/2000/svg" viewBox="-1 -1 388 446">\n'
    '<title>TresVizo: simbolo 3 y hexagono, sin VIZO</title>\n'
    f'<path fill="#164b7e" fill-rule="evenodd" d="{path}"/>\n</svg>\n')
print([(len(q['points']),q['signed_area_px2']) for q in loops])
