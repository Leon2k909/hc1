"""Locally authored cut camouflage cloth over a sagging, framed logistics net."""
import math
import numpy as np
from PIL import Image, ImageDraw
from scipy.ndimage import gaussian_filter
import map_kit as K
import forestbase_materials as M

def materials():
    size=1024; rng=np.random.default_rng(4051)
    field=gaussian_filter(rng.normal(size=(size,size)),42,mode='wrap')
    field/=field.std()
    palette=np.array(((39,47,32),(64,70,44),(92,91,62),(115,107,78)),float)
    color=palette[np.digitize(field,(-.65,.15,.9))]
    color*=1+rng.normal(0,.018,(size,size,1))
    alpha=Image.new('L',(size,size),0); draw=ImageDraw.Draw(alpha)
    # Continuous knotted mesh supports the larger cut textile panels.
    for k in range(-size,size*2,64):
        draw.line((k,0,k+size,size),fill=255,width=3)
        draw.line((k,size,k+size,0),fill=255,width=3)
    for row in range(-1,17):
        for col in range(-1,17):
            x=col*64+(row%2)*32; y=row*64
            x+=int(rng.integers(-8,9)); y+=int(rng.integers(-8,9))
            points=[]
            for angle in np.linspace(0,math.tau,24,endpoint=False):
                radius=1+.22*math.sin(angle*3+rng.uniform(-.2,.2))
                points.append((x+math.cos(angle)*26*radius,y+math.sin(angle)*24*radius))
            draw.polygon(points,fill=255)
            # Staggered curved incisions leave strips connected to the net.
            if (row+col)%3:
                draw.arc((x-18,y-17,x+18,y+17),25,295,fill=0,width=4)
    yy,xx=np.mgrid[:size,:size]
    weave=.002*np.sin(xx*math.pi/2)+.002*np.sin(yy*math.pi/2)
    M.save('camonet',color,.5+weave,.88,alpha=np.asarray(alpha))

def build(m):
    if m.__class__.__name__=='CollisionOnlyModel': return
    m.material_overrides['camonet']='materials/forestbase/camonet.vmat'
    m.tile_overrides['camonet']=96
    def roof(u,v):
        ridge=42*math.sin(math.pi*u)
        sag=12*math.sin(math.pi*v)*(.3+.7*math.sin(math.pi*u))
        folds=2.4*math.sin(u*math.pi*14+v*2)*math.sin(math.pi*v)
        return np.array((-395+745*u,-25+410*v,125+ridge-sag+folds))
    def normal(u,v):
        return K.normalise(np.cross(roof(u+.0001,v)-roof(u-.0001,v),roof(u,v+.0001)-roof(u,v-.0001)))
    for j in range(12):
        for i in range(24):
            uv=((i/24,j/12),((i+1)/24,j/12),((i+1)/24,(j+1)/12),(i/24,(j+1)/12))
            m.polygon('camonet',[roof(u,v) for u,v in uv],
                      normals=[normal(u,v) for u,v in uv],uv=[(u*745/96,v*410/96) for u,v in uv])
    # The existing six solid posts and their collision remain in map.py.
    # Light tubular arches and bindings are purely visual roof fittings.
    for v in (0,1):
        for i in range(12):
            a,b=roof(i/12,v),roof((i+1)/12,v)
            m.beam(a-np.array((0,0,2)),b-np.array((0,0,2)),(2.5,2.5),'steel')
        post_n=360*v
        m.beam((-15,post_n,126),roof(380/745,(post_n+25)/410)-np.array((0,0,2)),(2.5,2.5),'steel')
    for u in (0,.5,1):
        for j in range(12):
            m.beam(roof(u,j/12)-np.array((0,0,2)),roof(u,(j+1)/12)-np.array((0,0,2)),(1.4,1.4),'steel')
    for u in (0,1):
        for j in range(24):
            a,b=roof(u,j/24),roof(u,(j+1)/24)
            da=16+5*math.sin(j*2.1);db=16+5*math.sin((j+1)*2.1)
            m.polygon('camonet',[a,b,b-np.array((0,0,db)),a-np.array((0,0,da))],
                      uv=[(j*410/24/96,0),((j+1)*410/24/96,0),((j+1)*410/24/96,db/96),(j*410/24/96,da/96)])

if __name__=='__main__': materials()
