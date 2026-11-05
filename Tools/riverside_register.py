"""Approved Lucky Stop register. No collision, matching the original decoration."""
import math
import numpy as np
import map_kit as K
import riverdale_parts as G
MAT="materials/riverside/register-v1"
keys=[('7', 'ivory'), ('8', 'ivory'), ('9', 'ivory'), ('DEPT 1', 'teal'), ('DEPT 2', 'teal'), ('FEED', 'grey'), ('4', 'ivory'), ('5', 'ivory'), ('6', 'ivory'), ('DEPT 3', 'teal'), ('DEPT 4', 'teal'), ('VOID', 'red'), ('1', 'ivory'), ('2', 'ivory'), ('3', 'ivory'), ('SUB', 'grey'), ('TOTAL', 'amber'), ('CLEAR', 'grey'), ('0', 'ivory'), ('00', 'ivory'), ('.', 'ivory'), ('CASH', 'amber'), ('CARD', 'teal'), ('NO SALE', 'grey')]
X=np.array((1.,0,0));Y=np.array((0.,-1,0));Z=np.array((0.,0,1.))
def p(x,d,z):return X*x+Y*d+Z*z
angle=math.atan(.38);B=Y*math.cos(angle)-Z*math.sin(angle);N=Y*math.sin(angle)+Z*math.cos(angle)
def model(lod=0):
    m=K.Model();sides=(16,10,8)[lod]
    def box(c,sz,paint,b=.09,axes=(X,Y,Z)):G.bevel_box(m,p(*c),axes,sz,paint,bevel=b if lod<2 else .001)
    def cyl(c,axis,length,r,paint):G.lathe_axis(m,p(*c),axis,[(0,0),(r,0),(r,length),(0,length)],paint,sides=sides)
    def panel(c,right,up,w,h,paint):
        c=np.asarray(c);right=np.asarray(right)*w/2;up=np.asarray(up)*h/2
        m.polygon(paint,[c-right-up,c+right-up,c+right+up,c-right+up],np.cross(right,up),uv=[(0,0),(1,0),(1,1),(0,1)])
    # Heavy cash drawer, separate seam and folded metal front.
    box((0,0,1.9),(16,12,3),'black',.18)
    box((0,6.035,1.95),(15.35,.16,2.28),'drawer',.11)
    box((0,6.145,2.28),(10.1,.08,.31),'black',.035)
    box((0,6.26,2.12),(9.4,.20,.18),'steel',.035)
    cyl((5.9,6.15,1.67),Y,.10,.28,'steel')
    box((5.9,6.265,1.67),(.046,.012,.24),'black',.006)
    for x in (-6.6,6.6):
        for depth in (-4.6,4.6):cyl((x,depth,0),Z,.46,.47,'black')
    # Sloped electronic-register housing. Plane rises toward the printer and display at the back.
    pts=[p(-7.5,5.4,3.45),p(7.5,5.4,3.45),p(7.5,-5.4,3.45),p(-7.5,-5.4,3.45),
         p(-7.5,5.4,4.3),p(7.5,5.4,4.3),p(7.5,-5.4,8.4),p(-7.5,-5.4,8.4)]
    for face,normal in [([0,1,5,4],Y),([2,3,7,6],-Y),([1,2,6,5],X),([3,0,4,7],-X),([4,5,6,7],N),([3,2,1,0],-Z)]:m.polygon('housing',[pts[i] for i in face],normal)
    box((0,0,6.35),(15.05,11.52,.26),'housing',.10,axes=(X,B,N))
    box((.45,.8,6.42-.38*.8),(13.6,7.65,.36),'black',.16,axes=(X,B,N))
    # Twenty-four real key caps on a sloped deck. Their legends share one material/texture.
    for i,(label,color) in enumerate(keys):
        col=i%6;row=i//6;x=-5.14+col*2.22;depth=-1.72+row*1.73
        z=6.42-.38*depth
        center=p(x,depth,z)+N*.25
        start=len(m.polygons['keys'])
        G.bevel_box(m,center,(X,B,N),(1.88,1.37,.36),{'default':'black','+z':'keys'},bevel=.09 if lod<2 else .001)
        for index in range(start,len(m.polygons['keys'])):
            points,normal=m.polygons['keys'][index]
            uv=[]
            for q in points:
                delta=q-center
                u=np.clip(np.dot(delta,X)/1.88+.5,0,1);v=np.clip(np.dot(delta,B)/1.37+.5,0,1)
                # Atlas rows are counted down from the top; OBJ V runs upward.
                uv.append(((i%8+u)/8,1-(i//8+v)/8))
            m.polygon_uvs[('keys',index)]=uv
    # Back display: a recessed VFD lens, not an illuminated billboard.
    box((2,-4.75,9.42),(9.6,1.28,2.9),'housing',.17)
    box((2,-4.02,9.47),(8.68,.16,1.99),'black',.09)
    panel(p(2,-3.922,9.47),X,Z,8.30,1.65,'display')
    # Printer module and narrow receipt slot to the left of the display.
    box((-5.38,-3.78,8.77),(3.25,3.0,2.31),'housing',.17)
    box((-5.38,-2.20,9.1),(2.8,.20,.23),'black',.045)
    # Folded thermal paper; dual-sided geometry, slight curl, quiet printed detail.
    if lod<2:
        paper=[(-2.05,9.19),(-1.9,10.25),(-1.8,11.3),(-1.3,11.65),(-.8,11.6)]
        for k in range(len(paper)-1):
            d0,z0=paper[k];d1,z1=paper[k+1]
            q=[p(-6.65,d0,z0),p(-4.1,d0,z0),p(-4.1,d1,z1),p(-6.65,d1,z1)]
            uv=[(0,k/(len(paper)-1)),(1,k/(len(paper)-1)),(1,(k+1)/(len(paper)-1)),(0,(k+1)/(len(paper)-1))]
            m.polygon('receipt',q,uv=uv,both_sides=True)
    # Serial/badge strip on the housing face; actual intake slots down its right side.
    panel(p(-.5,5.423,3.93),X,Z,4.8,.36,'badge')
    if lod<2:
        for depth in np.linspace(-3.7,1.2,9):
            box((7.515,float(depth),4.55),(.025,.19,.8),'black',.012)
        for x in (-7.1,7.1):
            for depth in (-4.9,4.9):cyl((x,depth,3.6),Z,.05,.12,'steel')
    if lod==0:
        for x in (-7.55,7.55):
            for depth in (-4.8,4.7):
                box((x,depth,2.4),(.035,.08,.24),'steel',.009)
    # Stable local projection for housing wear. Key legends/paper/display retain custom UVs.
    for paint,polys in m.polygons.items():
        for index,(points,normal) in enumerate(polys):
            if (paint,index) in m.polygon_uvs:continue
            if abs(normal[2])>.6:uv=[((q[0]+8)/16,(-q[1]+6)/12) for q in points]
            elif abs(normal[0])>.7:uv=[((-q[1]+6)/12,q[2]/12) for q in points]
            else:uv=[((q[0]+8)/16,q[2]/12) for q in points]
            m.polygon_uvs[(paint,index)]=uv
    m.material_overrides={paint:f'{MAT}/{paint}.vmat' for paint in m.polygons}
    m.tile_overrides={paint:12 for paint in m.polygons}
    return m

def append_to(target,position):
    m=model(0)
    offset=np.asarray(position,float)
    for paint,faces in m.polygons.items():
        alias="regv1_"+paint
        target.material_overrides[alias]=m.material_overrides[paint]
        target.tile_overrides[alias]=m.tile_overrides[paint]
        for i,(points,normal) in enumerate(faces):
            target.polygon(alias,[p+offset for p in points],normal,uv=m.polygon_uvs.get((paint,i)),normals=m.polygon_normals.get((paint,i)))
