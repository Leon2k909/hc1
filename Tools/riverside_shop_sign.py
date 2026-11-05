"""Approved formed Lucky Stop sign; local coordinates retain original roof contacts."""
import math
import numpy as np
import map_kit as K
import riverdale_parts as G
MAT='materials/riverside/shop-sign-v1'
X=np.array((1.,0,0));Y=np.array((0.,-1,0));Z=np.array((0.,0,1.))
def p(x,d,z):return X*x+Y*d+Z*z
def model(lod=0):
    m=K.Model();sides=(20,12,8)[lod]
    def box(c,sz,paint,b=.10):G.bevel_box(m,p(*c),(X,Y,Z),sz,paint,bevel=b if lod<2 else min(b,.035))
    def cyl(c,axis,length,r,paint,segments=None):G.lathe_axis(m,p(*c),axis,[(0,0),(r,0),(r,length),(0,length)],paint,sides=segments or sides)
    def bolt(c,axis=Z,r=.30):
        cyl(c,axis,.07,r*1.55,'steel');cyl(tuple(np.asarray(c)+np.array((0,0,.075))),axis,.22,r,'steel',6)
    def bar(a,b,width,paint):
        a=p(*a);b=p(*b);axis=b-a;length=np.linalg.norm(axis);axis/=length
        other=np.cross(axis,X if abs(np.dot(axis,X))<.9 else Y);other/=np.linalg.norm(other);third=np.cross(axis,other)
        G.bevel_box(m,(a+b)/2,(axis,other,third),(length,width,width),paint,bevel=.10 if lod<2 else .035)
    # Cabinet volume and main image match the original 168 x 8 x 48 inch sign.
    box((0,0,50),(168,8,48),'paint',.65)
    box((0,4.05,50),(162,.15,42),'rubber',.22)
    box((0,4.15,50),(160,.18,40),{'default':'inside','+y':'face'},.075)
    for z in (28.6,71.4):box((0,4.30,z),(164,.80,1.20),'paint',.15)
    for x in (-81.6,81.6):box((x,4.30,50),(1.2,.80,42.8),'paint',.15)
    # Folded rear service cover, hinge leaves, electrical junction and conduit.
    box((0,-4.09,50),(164,.18,44),'paint',.20)
    box((48,-4.25,50),(23,.16,31),'rubber',.15)
    box((48,-4.40,50),(22.4,.18,30.4),'paint',.12)
    if lod<2:
        for z in (41.,59.):
            box((59.5,-4.59,z),(1.1,.18,2.2),'steel',.08);cyl((60,-4.63,z-.9),Z,1.8,.18,'steel')
    box((-59,-5.8,44),(11,3.0,10),'paint',.22)
    box((-59,-7.36,44),(9.8,.14,8.8),'paint',.12)
    if lod<2:G.tube(m,[p(-64,-2,1.5),p(-64,-2,31),p(-59,-5.9,35),p(-59,-5.9,39)],.34,'steel',sides=sides)
    # Two square posts and rear diagonal braces retain the original roof contact points.
    for x in (-64.,64.):
        box((x,0,15),(2.2,2.2,30),'paint',.14)
        box((x,0,.55),(8,8,1.1),'steel',.14)
        bar((x,0,26),(x,-36,4),1.8,'paint')
        box((x,-36,3.65),(7,7,.70),'steel',.12)
        if lod<2:
            for dx in (-2.6,2.6):
                for d in (-2.6,2.6):bolt((x+dx,d,1.12),r=.28);bolt((x+dx,-36+d,4.02),r=.28)
    # Curved gooseneck arms and open reflector shades replace the old lamp boxes.
    for x in (-56.,0.,56.):
        box((x,0,74.3),(5.5,4,.6),'steel',.12)
        path=[p(x,0,74.5),p(x,0,79),p(x,1.2,82),p(x,4.3,84),p(x,8.0,84.4),p(x,11.3,83),p(x,13.6,80.1),p(x,14,79.6)]
        if lod==2:path=path[::2]+[path[-1]]
        G.tube(m,path,.44,'paint',sides=sides)
        profile=[(0,0),(.75,0),(1.0,.5),(1.45,1.1),(3.6,3.0),(3.9,3.25),(3.9,3.50),(3.60,3.50),(3.55,3.20),(1.10,.80),(0,.80)]
        G.lathe_axis(m,p(x,14,79.7),-Z,profile,['paint']*5+['steel']*2+['inside']*3,sides=sides)
        G.lathe_axis(m,p(x,14,76.55),-Z,[(0,0),(.58,0),(.73,.40),(.60,.77),(0,.92)],'bulb',sides=sides)
    if lod<2:
        for z in (28.6,71.4):
            for x in (-78.,-52.,-26.,0.,26.,52.,78.):
                cyl((x,4.72,z),Y,.07,.16,'steel')
                if lod==0:box((x,4.80,z),(.17,.018,.025),'rubber',.003)
        for x in (-72.,0.,72.):cyl((x,3.9,26.75),Y,.12,.29,'rubber')
    if lod==0:
        for x,z,w in [(-67.,28.8,.42),(36.,71.25,.67),(80.9,53.,.22)]:box((x,4.72,z),(w,.018,.10),'rust',.009)
    for paint,polys in m.polygons.items():
        for index,(pts,normal) in enumerate(polys):
            uv=[]
            for q in pts:
                x,d,z=q[0],-q[1],q[2]
                if paint=='face':u=(x+79.925)/159.85;v=(z-30.075)/39.85
                elif abs(normal[2])>.7:u=(x+84)/168;v=(d+40)/58
                elif abs(normal[0])>.7:u=(d+40)/58;v=z/85
                else:u=(x+84)/168;v=(z-26)/48
                uv.append((float(u),float(v)))
            m.polygon_uvs[(paint,index)]=uv
    m.material_overrides={paint:MAT+'/'+paint+'.vmat' for paint in m.polygons};m.material_overrides['face']=MAT+'/face_toned.vmat';m.tile_overrides={paint:64 for paint in m.polygons}
    return m

def append_to(target,position):
    m=model(0);offset=np.asarray(position,float)
    for paint,faces in m.polygons.items():
        alias='shopsignv1_'+paint
        target.material_overrides[alias]=m.material_overrides[paint]
        target.tile_overrides[alias]=m.tile_overrides[paint]
        for i,(points,normal) in enumerate(faces):
            target.polygon(alias,[p+offset for p in points],normal,uv=m.polygon_uvs.get((paint,i)),normals=m.polygon_normals.get((paint,i)))
    target.oriented_box(offset+np.array((0.,0.,50.)),(X,np.array((0.,1.,0.)),Z),(168,8,48),{'default':None},'metal')
