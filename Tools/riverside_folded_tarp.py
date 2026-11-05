"""Approved folded rooftop tarp; reuse original dimensions and roof pitch."""
import math
import numpy as np
import map_kit as K
import riverdale_parts as G
MAT='materials/riverside/folded-tarp-v1'
Z=np.array((0.,0.,1.))
def roof(y):return 1-5.5*abs(y)/62.5

def sheet(x,y,level=3,curl=True):
    z=roof(y)+.14+level*.52
    z+=.45*math.sin(x*.20+y*.045)+.30*math.sin(y*.24-x*.06)
    z+=1.25*math.exp(-((x-y*.25+3)/3.2)**2)-.50*math.exp(-((x+y*.14-18)/2.4)**2)+.65*math.exp(-((y+x*.12+12)/3.0)**2)
    z+=.13*math.sin((x+y)*.62)*math.exp(-min(40-abs(x),40-abs(y))/6)
    if curl and x+y>70:
        d=(x+y-70)/math.sqrt(2);a=d/3.5;shift=(3.5*math.sin(a)-d)/math.sqrt(2);x+=shift;y+=shift;z+=3.5*(1-math.cos(a))
    return np.array((x,y,z))

def normal(x,y,level=3,curl=True):
    a=sheet(x+.01,y,level,curl)-sheet(x-.01,y,level,curl);b=sheet(x,y+.01,level,curl)-sheet(x,y-.01,level,curl);n=np.cross(a,b);return n/np.linalg.norm(n)

def model(lod=0):
    m=K.Model();size=(64,40,24)[lod];steps=np.linspace(-40,40,size+1)
    # Upper and lower fabric faces follow the shallow pitched roof and physical fold radii.
    for bottom in (False,True):
        for i in range(size):
            for j in range(size):
                coords=[(steps[i],steps[j]),(steps[i+1],steps[j]),(steps[i+1],steps[j+1]),(steps[i],steps[j+1])]
                pts=[sheet(x,y) for x,y in coords];ns=[normal(x,y) for x,y in coords]
                if bottom:pts=[q-n*.06 for q,n in zip(pts,ns)]
                if bottom:pts.reverse();coords.reverse();ns=[-n for n in ns[::-1]]
                m.polygon('underside' if bottom else 'cloth',pts,normals=ns,uv=[(x/12.8,y/12.8) for x,y in coords])
    # The lower folded sheet becomes visible below the peeled-back corner.
    base=np.linspace(-40,40,9)
    for i in range(8):
        for j in range(8):
            xy=[(base[i],base[j]),(base[i+1],base[j]),(base[i+1],base[j+1]),(base[i],base[j+1])]
            pts=[sheet(x,y,0,False) for x,y in xy];ns=[normal(x,y,0,False) for x,y in xy];m.polygon('cloth',pts,normals=ns,uv=[(x/12.8,y/12.8) for x,y in xy])
    # Successive soft folded edges, rather than solid vertical box walls.
    for level in range(4):
        inset=(.3,.0,.45,.0)[level]
        for axis in (0,1):
            for sg in (-1,1):
                path=[]
                for t in steps:
                    x,y=(sg*(40-inset),t) if axis==0 else (t,sg*(40-inset));path.append(sheet(x,y,level,level==3))
                for k in range(len(path)-1):
                    a,b=path[k:k+2];pts=[a-Z*.055,b-Z*.055,b+Z*.055,a+Z*.055];towards=np.array((sg,0,0) if axis==0 else (0,sg,0));G.card(m,'hem',pts,towards,uv=[(k/5,0),((k+1)/5,0),((k+1)/5,1),(k/5,1)])
                if level==3:G._sweep(m,path,.10,'hem',sides=6 if lod<2 else 4,caps=True)
    if lod<2:
        # Reinforced folded hems with quiet double stitch lines.
        for axis in (0,1):
            for sg in (-1,1):
                for t in np.arange(-37,38,2 if lod==0 else 4):
                    x,y=(sg*39,t) if axis==0 else (t,sg*39);q=sheet(x,y)+normal(x,y)*.035;direction=np.array((0.,.30,0)) if axis==0 else np.array((.30,0,0));G._sweep(m,[q-direction,q+direction],.025,'thread',sides=4)
    # Metal eyelets have an open annular lip and a recessed dark interior.
    for x,y in [(-36,-36),(0,-36),(36,-36),(-36,0),(36,0),(-36,36),(0,36),(36,36)]:
        q=sheet(x,y);n=normal(x,y);G.lathe_axis(m,q+n*.03,n,[(.29,0.),(.50,0.),(.53,.05),(.48,.12),(.29,.12),(.29,0.)],'steel',sides=(16,12,8)[lod]);G.lathe_axis(m,q-n*.005,n,[(0.,0.),(.28,0.),(.28,.015),(0.,.015)],'dark',sides=12)
    m.material_overrides={p:MAT+'/'+p+'.vmat' for p in m.polygons};m.tile_overrides={p:12.8 for p in m.polygons}
    return m

def append_to(target,position):
    m=model(0);offset=np.asarray(position,float)
    for paint,faces in m.polygons.items():
        alias='rf_tarp_'+paint
        target.material_overrides[alias]=m.material_overrides[paint]
        target.tile_overrides[alias]=m.tile_overrides[paint]
        for i,(points,normal) in enumerate(faces):
            target.polygon(alias,[p+offset for p in points],normal,uv=m.polygon_uvs.get((paint,i)),normals=m.polygon_normals.get((paint,i)))
