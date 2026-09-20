"""Proyeccion ortografica de mallas CAD con z-buffer, sin GUI."""
import numpy as np

def draw(ax, entries, colors, limits=None, elev=18, azim=65):
    polygons=[]; shades=[]
    light=np.array([0.2,0.7,1.0]); light/=np.linalg.norm(light)
    for name,shape in entries:
        verts,faces=shape.tessellate(0.18)
        v=np.array([[p.x,p.y,p.z] for p in verts])
        tri=v[np.asarray(faces)]
        normal=np.cross(tri[:,1]-tri[:,0],tri[:,2]-tri[:,0])
        normal/=np.maximum(np.linalg.norm(normal,axis=1,keepdims=True),1e-12)
        intensity=0.55+0.45*np.maximum(normal@light,0)
        col=np.clip(colors[name]*intensity[:,None],0,1)
        polygons.extend(tri); shades.extend(col)
    # Z-buffer ortografico: evita ordenar por profundidad media triangulos
    # largos de los canales, lo que produciria falsas transparencias.
    el,az=np.radians([elev,azim])
    eye=np.array([np.cos(el)*np.cos(az),np.cos(el)*np.sin(az),np.sin(el)])
    right=np.array([-np.sin(az),np.cos(az),0])
    up=np.cross(eye,right)
    tri=np.asarray(polygons)@np.stack([right,up,eye],axis=1)
    pos=ax.get_position()
    width,height=int(pos.width*2200),int(pos.height*1375)
    low=tri[:,:,:2].min(axis=(0,1)); high=tri[:,:,:2].max(axis=(0,1))
    scale=min((width-40)/(high[0]-low[0]),(height-40)/(high[1]-low[1]))
    center=(low+high)/2
    tri[:,:,0]=(tri[:,:,0]-center[0])*scale+width/2
    tri[:,:,1]=-(tri[:,:,1]-center[1])*scale+height/2
    depth=np.full((height,width),-np.inf)
    rgba=np.zeros((height,width,4),dtype=np.uint8)
    for t,color in zip(tri,shades):
        xmin=max(0,int(np.floor(t[:,0].min()))); xmax=min(width-1,int(np.ceil(t[:,0].max())))
        ymin=max(0,int(np.floor(t[:,1].min()))); ymax=min(height-1,int(np.ceil(t[:,1].max())))
        if xmin>xmax or ymin>ymax: continue
        x0,y0,z0=t[0]; x1,y1,z1=t[1]; x2,y2,z2=t[2]
        denominator=(y1-y2)*(x0-x2)+(x2-x1)*(y0-y2)
        if abs(denominator)<1e-9: continue
        ys,xs=np.mgrid[ymin:ymax+1,xmin:xmax+1]
        xs=xs+.5; ys=ys+.5
        a=((y1-y2)*(xs-x2)+(x2-x1)*(ys-y2))/denominator
        b=((y2-y0)*(xs-x2)+(x0-x2)*(ys-y2))/denominator
        c=1-a-b
        z=a*z0+b*z1+c*z2
        old=depth[ymin:ymax+1,xmin:xmax+1]
        mask=(a>=-1e-7)&(b>=-1e-7)&(c>=-1e-7)&(z>old)
        old[mask]=z[mask]
        pixels=rgba[ymin:ymax+1,xmin:xmax+1]
        pixels[mask,:3]=(np.asarray(color)*255).astype(np.uint8)
        pixels[mask,3]=255
    ax.imshow(rgba,interpolation='bilinear')
    ax.set_axis_off()

