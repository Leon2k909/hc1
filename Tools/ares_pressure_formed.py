"""Pressed-sheet pressure doors based on Sources/Ares/pressure-doors-v3/concept-v1.png.

Real recessed channels and service pulls, rolled edges, cast clamps and a recessed
wheel. Render geometry only; the original sealed collision envelope is retained.
Local -Y is the room-facing direction. Dimensions are inches.
"""
import math
import numpy as np
from scipy.spatial import Delaunay
import map_kit as K
import riverdale_parts as P
from boxyard_map import Frame

PREFIX='materials/ares/pressure-doors-v3'
NAMES=('body','panel','cassette','frame','steel','rubber','accent','dark','kick','labels','display','glass','red','green','hazard')
MATERIALS={f'ar_pd_{n}':f'{PREFIX}/{n}.vmat' for n in NAMES}
X=np.array((1.,0.,0.));Y=np.array((0.,1.,0.));Z=np.array((0.,0.,1.));AXES=(X,Y,Z)


def area(p):
    p=np.asarray(p);return .5*float(np.sum(p[:,0]*np.roll(p[:,1],-1)-p[:,1]*np.roll(p[:,0],-1)))


def clean(p):
    out=[]
    for v in p:
        if not out or np.linalg.norm(np.array(v)-out[-1])>1e-7:out.append(np.asarray(v,float))
    if np.linalg.norm(out[0]-out[-1])<1e-7:out.pop()
    return np.asarray(out if area(out)>0 else out[::-1])


def rect(x0,x1,z0,z1,c=1.,rounding=.4):
    c=min(c,(x1-x0)*.24,(z1-z0)*.24)
    p=[(x0+c,z0),(x1-c,z0),(x1,z0+c),(x1,z1-c),
       (x1-c,z1),(x0+c,z1),(x0,z1-c),(x0,z0+c)]
    if rounding:
        p=[(v[0],v[2]) for v in P._bend_points([(x,0,z) for x,z in p],rounding,closed=True,max_step=15.)]
    return clean(p)


def rounded(x0,x1,z0,z1,r=1.,step=2.5):
    r=min(r,(x1-x0)*.5,(z1-z0)*.5);p=[]
    for cx,cz,a in ((x1-r,z0+r,-math.pi/2),(x1-r,z1-r,0),
                    (x0+r,z1-r,math.pi/2),(x0+r,z0+r,math.pi)):
        for angle in np.linspace(a,a+math.pi/2,9):p.append((cx+r*math.cos(angle),cz+r*math.sin(angle)))
    return densify(clean(p),step)


def densify(p,step=4.):
    p=clean(p);out=[]
    for a,b in zip(p,np.roll(p,-1,axis=0)):
        for f in np.linspace(0,1,max(1,math.ceil(np.linalg.norm(b-a)/step)),endpoint=False):out.append(a+(b-a)*f)
    return clean(out)


def outnormals(p):
    p=clean(p);e=np.roll(p,-1,axis=0)-p;e/=np.linalg.norm(e,axis=1)[:,None]
    n=np.c_[e[:,1],-e[:,0]];v=n+np.roll(n,1,axis=0);v/=np.linalg.norm(v,axis=1)[:,None]
    return v,n


def inset(p,d):
    p=clean(p);v,n=outnormals(p)
    return p-v*(d/np.sum(v*n,axis=1))[:,None]


def inside(points,p):
    q=np.asarray(points);hit=np.zeros(len(q),bool)
    for a,b in zip(p,np.roll(p,-1,axis=0)):
        if abs(a[1]-b[1])<1e-12:continue
        hit^=((a[1]>q[:,1])!=(b[1]>q[:,1]))&(q[:,0]<(b[0]-a[0])*(q[:,1]-a[1])/(b[1]-a[1])+a[0])
    return hit


def flat(m,profile,y,paint,holes=(),uv=None):
    """Triangulate a face with real holes; prove every boundary and its area."""
    profile=clean(profile)
    if not holes:
        P.card(m,'ar_pd_'+paint,[(x,y,z) for x,z in profile],-Y,
               uv=[uv(x,z) for x,z in profile] if uv else None);return
    contours=[densify(profile)]+[clean(h) for h in holes]
    points=np.vstack(contours);tri=Delaunay(points).simplices
    edges={tuple(sorted((int(a),int(b)))) for t in tri for a,b in zip(t,np.roll(t,-1))}
    offset=0
    for contour in contours:
        for i in range(len(contour)):
            assert tuple(sorted((offset+i,offset+(i+1)%len(contour)))) in edges,'Recess boundary needs denser sampling'
        offset+=len(contour)
    centre=points[tri].mean(axis=1);keep=inside(centre,profile)
    for hole in contours[1:]:keep&=~inside(centre,hole)
    triangles=points[tri[keep]]
    covered=sum(abs(area(t)) for t in triangles)
    target=abs(area(profile))-sum(abs(area(h)) for h in holes)
    assert abs(covered-target)<max(1e-5,target*1e-8),(covered,target)
    for triangle in triangles:
        P.card(m,'ar_pd_'+paint,[(x,y,z) for x,z in triangle],-Y,
               uv=[uv(x,z) for x,z in triangle] if uv else None)


def band(m,a,b,y0,y1,paint):
    assert len(a)==len(b)
    for i in range(len(a)):
        j=(i+1)%len(a)
        P.card(m,'ar_pd_'+paint,[(a[i,0],y0,a[i,1]),(a[j,0],y0,a[j,1]),
                               (b[j,0],y1,b[j,1]),(b[i,0],y1,b[i,1])],-Y)


def slab(m,profile,back,front,paint,bevel=.18,holes=(),uv=None,facepaint=None):
    """Solid sides and a circular rolled front edge, with analytical normals."""
    p=clean(profile);normals,_=outnormals(p);n3=np.c_[normals[:,0],np.zeros(len(p)),normals[:,1]]
    if uv is None:
        lo=p.min(axis=0);span=p.max(axis=0)-lo
        uv=lambda x,z:((x-lo[0])/span[0],(z-lo[1])/span[1])
    # Sparse loss of coating follows the actual rolled edge. Splitting existing
    # bevel faces avoids floating decals and keeps the wear off untouched faces.
    seed=abs(round(float(np.sum(p*np.array((23.,71.))))*100))+round(abs(front)*1000)
    rng=np.random.default_rng(seed)
    cuts=[]
    for i in range(len(p)):
        length=float(np.linalg.norm(p[(i+1)%len(p)]-p[i]));spans=[]
        if paint in ('body','panel','frame','dark','accent') and bevel>.13:
            for _ in range(rng.poisson(length/16.)):
                start=float(rng.uniform(.015,.97));end=min(.995,start+rng.uniform(.09,.65)/length)
                spans.append((start,end))
        cuts.append(spans)
    for i in range(len(p)):
        j=(i+1)%len(p)
        P.card(m,'ar_pd_'+paint,[(p[i,0],back,p[i,1]),(p[j,0],back,p[j,1]),
                (p[j,0],front+bevel,p[j,1]),(p[i,0],front+bevel,p[i,1])],(n3[i]+n3[j])*.5,
                normals=[n3[i],n3[j],n3[j],n3[i]])
    angles=np.linspace(0,math.pi/2,5)
    layers=[(inset(p,bevel*(1-math.cos(a))),front+bevel*(1-math.sin(a)),
             n3*math.cos(a)-Y*math.sin(a)) for a in angles]
    for level,((a,ya,na),(b,yb,nb)) in enumerate(zip(layers,layers[1:])):
        for i in range(len(p)):
            j=(i+1)%len(p);spans=cuts[i] if level>0 else []
            split=sorted({0.,1.,*(value for pair in spans for value in pair)})
            for u,v in zip(split,split[1:]):
                aa=a[i]*(1-u)+a[j]*u;ab=a[i]*(1-v)+a[j]*v
                ba=b[i]*(1-u)+b[j]*u;bb=b[i]*(1-v)+b[j]*v
                nn=[na[i]*(1-u)+na[j]*u,na[i]*(1-v)+na[j]*v,
                    nb[i]*(1-v)+nb[j]*v,nb[i]*(1-u)+nb[j]*u]
                nn=[n/np.linalg.norm(n) for n in nn]
                exposed=any(start<=(u+v)/2<=end for start,end in spans)
                finish='steel' if exposed else paint
                pts=[(aa[0],ya,aa[1]),(ab[0],ya,ab[1]),(bb[0],yb,bb[1]),(ba[0],yb,ba[1])]
                P.card(m,'ar_pd_'+finish,pts,np.mean(nn,axis=0),normals=nn,uv=[uv(x,z) for x,y,z in pts])
    flat(m,layers[-1][0],front,facepaint or paint,holes,uv)
    P.card(m,'ar_pd_'+paint,[(x,back,z) for x,z in p],Y)


def recess(m,profile,front,depth,paint='panel',radius=.28):
    """A concave stamped channel with a rolled lip, side wall and filleted floor."""
    p=clean(profile);r=min(radius,depth*.40)
    cross=[(r*math.sin(a),r*(1-math.cos(a))) for a in np.linspace(0,math.pi/2,4)]
    cross+=[(r,depth-r)]
    cross += [(r+r*(1-math.cos(a)),depth-r+r*math.sin(a)) for a in np.linspace(0,math.pi/2,4)[1:]]
    layers=[np.c_[q[:,0],np.full(len(p),front+d),q[:,1]] for off,d in cross for q in [inset(p,off)]]
    ns=[]
    for k,row in enumerate(layers):
        tangent=np.roll(row,-1,axis=0)-np.roll(row,1,axis=0)
        depthdir=layers[min(k+1,len(layers)-1)]-layers[max(k-1,0)]
        n=np.cross(tangent,depthdir);n/=np.linalg.norm(n,axis=1)[:,None]
        if k in (0,len(layers)-1):n[:]=-Y
        ns.append(n)
    for k,(a,b) in enumerate(zip(layers,layers[1:])):
        for i in range(len(p)):
            j=(i+1)%len(p);nn=[ns[k][i],ns[k][j],ns[k+1][j],ns[k+1][i]]
            P.card(m,'ar_pd_'+paint,[a[i],a[j],b[j],b[i]],np.mean(nn,axis=0),normals=nn)
    flat(m,inset(p,cross[-1][0]),front+depth,paint)


def box(m,c,size,paint,bevel=.12):P.bevel_box(m,c,AXES,size,'ar_pd_'+paint,bevel=bevel)


def turned(m,x,z,back,profile,paint='steel',sides=32,close=True):
    P.lathe_axis(m,(x,back,z),-Y,profile,'ar_pd_'+paint,sides=sides,cap='ar_pd_'+paint if close else None)


def bolt(m,x,z,back,r=.65):
    turned(m,x,z,back,[(r*1.35,0),(r*1.35,.09),(r*1.12,.14),(r*1.12,.32),(r*.95,.45)],sides=24)
    turned(m,x,z,back-.452,[(r*.48,0),(r*.48,.015)],'dark',sides=6)


def label_uv(tile,s,t):return ((tile%4+.025+.95*s)/4,1-(tile//4+.025+.95*(1-t))/4)
def cassette_uv(tile,s,t):return ((tile%2+.008+.984*s)/2,1-(tile//2+.012+.976*(1-t))/4)


def label(m,x0,x1,z0,z1,y,tile):
    P.card(m,'ar_pd_labels',[(x0,y,z0),(x1,y,z0),(x1,y,z1),(x0,y,z1)],-Y,
           uv=[label_uv(tile,s,t) for s,t in ((0,0),(1,0),(1,1),(0,1))])


def leaf_profile(width,height,side):
    half=width/2
    return clean([(-side*x,z) for x,z in [(-half+15,11),(-.70,11),(-.70,height-7),
                 (-half+15,height-7),(-half+7,height-15),(-half+7,19)]])


def cassette_layout(width,height,side):
    p=leaf_profile(width,height,side);lo,hi=p[:,0].min()+5.5,p[:,0].max()-5.5
    low,high=height*.49,height-18;w=hi-lo;h=high-low
    fractions=(.48,.74) if side<0 else (.26,.52)
    grooves=[rounded(lo+w*f-2.35,lo+w*f+2.35,low+7,high-7,2.35) for f in fractions]
    hx=lo+w*.205 if side<0 else hi-w*.205
    return dict(lo=float(lo),hi=float(hi),low=low,high=high,w=float(w),h=h,
                hx=float(hx),hz=low+h*.32,hw=w*.315,hh=h*.42,grooves=grooves)


def service_cover(m,l,side):
    x,z,w,h=l['hx'],l['hz'],l['hw'],l['hh'];profile=rect(x-w/2,x+w/2,z-h/2,z+h/2,1.7,.55)
    slab(m,inset(profile,-.35),-6.42,-6.78,'rubber',.10)
    px=x+side*w*.28;pz=z-h*.06
    pull=rounded(px-1.35,px+1.35,pz-4.6,pz+4.6,1.,step=1.)
    slab(m,profile,-6.72,-7.12,'panel',.18,holes=[pull])
    recess(m,pull,-7.12,.95,'dark',.24)
    # A real recessed grip bar spans the dark pocket, with metal end bearings.
    box(m,(px,-6.77,pz),(1.0,.64,5.5),'frame',.18)
    for dz in (-3.5,3.5):bolt(m,px,pz+dz,-6.92,.22)
    for dx in (-w/2+2.,w/2-2.):
        for dz in (-h/2+2.,h/2-2.):bolt(m,x+dx,z+dz,-7.13,.43)


def seal_loop(m,profile,y,r=.40):
    p=clean(profile);norm,_=outnormals(p)
    rings=[];ns=[]
    for i,(x,z) in enumerate(p):
        n=np.array((norm[i,0],0,norm[i,1]));angles=np.linspace(0,math.tau,9)[:-1]
        nn=[n*math.cos(a)-Y*math.sin(a) for a in angles]
        rings.append([np.array((x,y,z))+r*v for v in nn]);ns.append(nn)
    for i in range(len(p)):
        j=(i+1)%len(p)
        for k in range(8):
            q=(k+1)%8;nn=[ns[i][k],ns[i][q],ns[j][q],ns[j][k]]
            P.card(m,'ar_pd_rubber',[rings[i][k],rings[i][q],rings[j][q],rings[j][k]],np.mean(nn,axis=0),normals=nn)


def casing(m,width,height,border):
    half=width/2;outer=rect(-half-border,half+border,0,height+border,15,.85)
    # The smallest radius must exceed every inward offset. Otherwise the tiny
    # corner arcs turn inside out and overlap when the deep throat is lofted.
    opening=rect(-half+1,half-1,6,height+2,12,4.2)
    a=inset(opening,-.9)
    slab(m,outer,-.18,-7.9,'frame',.65,holes=[densify(a,2.)])
    # A monotonic machined throat, with a separately seated, continuous seal.
    # Each lip occupies its own depth; no folded faces or overlapping ribbons.
    b=inset(opening,0.);c=inset(opening,1.0);d=inset(opening,3.0)
    band(m,a,b,-7.9,-7.15,'steel');band(m,b,c,-7.15,-6.35,'rubber')
    band(m,c,d,-6.35,-3.2,'steel')
    seat0=inset(opening,-.10);seat1=inset(opening,.80)
    band(m,seat0,seat1,-7.5,-7.5,'rubber')
    seal_loop(m,inset(opening,.35),-7.9,.40)
    flat(m,inset(opening,3.2),-2.9,'rubber')
    for side in (-1,1):
        for zz in (9.,height+border*.52):bolt(m,side*(half+border*.43),zz,-7.93,.8)
    for xx in np.linspace(-half+22,half-22,5 if width>250 else 3):bolt(m,float(xx),height+border*.53,-7.94,.70)


def clamps(m,width,height):
    half=width/2;stations=(43.,height*.52,height-29.)
    for side in (-1,1):
        px=side*(half+3.0);tx=side*(half-16.0)
        for zz in stations:
            # Bolted cast mounting block and a separate fork on the door leaf.
            slab(m,rect(px-6.4,px+6.4,zz-9.3,zz+9.3,1.4,.45),-7.7,-8.55,'dark',.25)
            for dx in (-4.6,4.6):
                for dz in (-7.3,7.3):bolt(m,px+dx,zz+dz,-8.57,.53)
            slab(m,rect(tx-5.3,tx+5.3,zz-8.8,zz+8.8,1.3,.4),-5.6,-6.4,'dark',.22)
            for dz in (-6.9,6.9):
                box(m,(tx,-8.0,zz+dz),(9.5,3.2,3.5),'frame',.30)
                for dx in (-3.4,3.4):bolt(m,tx+dx,zz+dz,-9.62,.43)
            axis=-side*X
            # The horizontal spindle has actual shoulders, sleeves and a socket.
            P.lathe_axis(m,(px,-8.6,zz),axis,[(2.7,0),(2.95,.55),(2.95,3.6),
                (2.45,4.05),(2.45,7.0),(2.35,7.3),(2.35,15.2),
                (3.0,15.7),(3.0,19.),(2.7,20.3)],'ar_pd_steel',sides=32,cap='ar_pd_steel')
            P.lathe_axis(m,(px,-8.6,zz),axis,[(2.55,6.5),(2.8,6.9),(2.8,14.6),
                (2.55,15.)],'ar_pd_dark',sides=40)
            for t in (7.0,14.2):
                P.lathe_axis(m,(px,-8.6,zz),axis,[(2.85,t),(3.1,t+.18),
                    (3.1,t+.56),(2.85,t+.75)],'ar_pd_steel',sides=40)
            bolt(m,px-side*11.,zz,-11.42,.34)
            for dx in (-3.6,3.6):box(m,(tx+dx,-8.5,zz),(2.1,4.7,9.5),'dark',.30)
            box(m,(px+side*2.5,-9.3,zz),(6.8,4.16,10.8),'frame',.35)
            slab(m,rect(px+side*2.5-2.0,px+side*2.5+2.0,zz-3.9,zz+3.9,.35,.25),
                 -11.36,-11.50,'accent',.08)
            for dz in (-3.0,3.0):bolt(m,px+side*2.5,zz+dz,-11.51,.24)
        # The exposed lock rod connects all three stations behind their cast caps.
        P.rod(m,(side*(half+8.6),-8.95,stations[0]),(side*(half+8.6),-8.95,stations[-1]),
              .72,'ar_pd_steel',sides=20,caps=True)
        for zz in (stations[0]+16,stations[-1]-16):
            box(m,(side*(half+8.6),-8.0,zz),(3.7,2.3,3.8),'dark',.32)


def wheel(m,x,z,r):
    # A recessed circular cup in a bolted casting, rather than a floating wheel.
    half=r+3.3;profile=rect(x-half,x+half,z-half,z+half,3.5,.8)
    circle=rounded(x-r-1.65,x+r+1.65,z-r-1.65,z+r+1.65,r+1.65,step=2.)
    slab(m,profile,-5.65,-7.75,'frame',.34,holes=[circle])
    recess(m,circle,-7.75,.95,'dark',.35)
    for dx in (-half+2.3,half-2.3):
        for dz in (-half+2.3,half-2.3):bolt(m,x+dx,z+dz,-7.77,.72)
    turned(m,x,z,-6.85,[(4.1,0),(4.45,.35),(4.45,1.2),(3.5,1.65),(2.4,2.0),(2.4,3.0)],'dark',48)
    turned(m,x,z,-8.5,[(2.7,0),(2.7,.6),(2.4,.9)],'steel',40)
    P.torus(m,(x,-10.25,z),-Y,r,.78,'ar_pd_accent',seg=72,sides=12)
    for k in range(3):
        angle=k*math.tau/3+math.radians(30);left=[];right=[]
        for rr in np.linspace(2.0,r-.35,6):
            a=angle+.18*(1-rr/r);c=np.array((x+rr*math.cos(a),z+rr*math.sin(a)))
            tangent=np.array((-math.sin(a),math.cos(a)));w=.67-.15*rr/r
            left.append(c+tangent*w);right.append(c-tangent*w)
        slab(m,clean(left+right[::-1]),-9.6,-10.28,'steel',.13)
    turned(m,x,z,-10.27,[(2.2,0),(2.3,.25),(2.3,.55),(1.85,.82)],'frame',40)
    bolt(m,x,z,-11.1,.79)
    slab(m,rect(x-12.5,x+12.5,z-half-8.,z-half-2.,.6,.25),-5.65,-6.05,'dark',.12)
    label(m,x-12.1,x+12.1,z-half-7.6,z-half-2.4,-6.07,4)


def gauge(m,x,z):
    p=rect(x-8.8,x+8.8,z-10,z+10,1.7,.55)
    slab(m,p,-5.6,-6.7,'dark',.25)
    for dx in (-6.7,6.7):
        for dz in (-7.9,7.9):bolt(m,x+dx,z+dz,-6.72,.55)
    turned(m,x,z,-6.72,[(6.5,0),(6.8,.3),(6.8,1.6),(6.5,2.1),(6.0,2.1)],'steel',64,False)
    P.torus(m,(x,-8.8,z),-Y,6.02,.12,'ar_pd_dark',seg=64,sides=6)
    pts=[];uv=[]
    for a in np.linspace(0,math.tau,65)[:-1]:
        xx,zz=math.cos(a),math.sin(a);pts.append((x+5.95*xx,-8.64,z+5.95*zz));uv.append(label_uv(8,(xx+1)/2,(zz+1)/2))
    P.card(m,'ar_pd_labels',pts,-Y,uv=uv)
    d=np.array((math.sin(.65),math.cos(.65)));across=np.array((-d[1],d[0]))
    needle=[np.array((x,z))+d*t+across*w for t,w in ((-1.4,-.15),(-1.4,.15),(4.8,.04),(5.1,0))]
    P.card(m,'ar_pd_dark',[(xx,-8.75,zz) for xx,zz in needle],-Y)
    turned(m,x,z,-8.77,[(.42,0),(.4,.14)],'steel',24)
    P.lathe_axis(m,(x,-6.7,z),-Y,[(5.94,2.25),(5.92,2.30),(4.7,2.35),
        (3.0,2.39),(1.0,2.42),(0,2.43)],'ar_pd_glass',sides=64)


def control(m,x,z):
    outer=rect(x-5.8,x+5.8,z-14.4,z+13.5,1.2,.5)
    slab(m,inset(outer,-.35),-5.6,-6.3,'rubber',.12)
    screen=rounded(x-3.3,x+3.3,z+1,z+10.5,.55,step=1.1)
    well=rounded(x-3.1,x+3.1,z-11.8,z-5.8,.45,step=1.1)
    slab(m,outer,-6.25,-9.7,'dark',.28,holes=[screen,well])
    recess(m,screen,-9.7,.45,'rubber',.14)
    P.card(m,'ar_pd_display',[(x-2.9,-9.36,z+1.4),(x+2.9,-9.36,z+1.4),
        (x+2.9,-9.36,z+10.1),(x-2.9,-9.36,z+10.1)],-Y,uv=[(0,0),(1,0),(1,1),(0,1)])
    recess(m,well,-9.7,1.1,'rubber',.20)
    for dx in (-4.2,4.2):
        for dz in (-12.9,12.0):bolt(m,x+dx,z+dz,-9.72,.35)
    for dx,paint in ((-1.9,'dark'),(1.9,'green')):
        turned(m,x+dx,z-2.2,-9.71,[(1.,0),(1.,.25),(.78,.3),(.75,.55)],'steel',28)
        turned(m,x+dx,z-2.2,-10.24,[(.68,0),(.68,.18)],paint,28)
    # Physical orange flip guard, hinge pin and toggle inside the recessed well.
    for dx in (-2.05,2.05):box(m,(x+dx,-10.12,z-8.5),(.78,1.4,6.1),'accent',.18)
    box(m,(x,-10.12,z-11.15),(4.6,1.4,.85),'accent',.18)
    P.rod(m,(x-2.4,-10.1,z-5.8),(x+2.4,-10.1,z-5.8),.38,'ar_pd_steel',sides=20,caps=True)
    P.rod(m,(x,-8.85,z-8.7),(x,-10.2,z-7.45),.28,'ar_pd_steel',sides=20,caps=True)
    box(m,(x,-10.32,z-7.35),(1.2,.8,1.9),'rubber',.25)


def pressure_door(model,centre,facing,width=180,height=180,border=16):
    m=K.Model();half=width/2;unit=0 if width>250 else 1 if centre[0]<0 else 2
    casing(m,width,height,border)
    for side in (-1,1):
        leaf=leaf_profile(width,height,side);lo,hi=leaf[:,0].min(),leaf[:,0].max()
        l=cassette_layout(width,height,side)
        px=l['hx']+side*l['hw']*.28;pz=l['hz']-l['hh']*.06
        pull=rounded(px-1.35,px+1.35,pz-4.6,pz+4.6,1.,step=1.)
        uv=lambda x,z:((x-lo)/(hi-lo),(z-11)/(height-18))
        slab(m,leaf,-3.1,-5.6,'body',.24,holes=l['grooves']+[pull],uv=uv)
        profile=rect(l['lo'],l['hi'],l['low'],l['high'],5.3,.8)
        band(m,inset(profile,-.38),profile,-5.65,-6.02,'rubber')
        tile=unit*2+int(side>0)
        puv=lambda x,z,tile=tile,l=l:cassette_uv(tile,(x-l['lo'])/l['w'],(z-l['low'])/l['h'])
        slab(m,profile,-5.95,-6.63,'panel',.25,holes=l['grooves']+[pull],uv=puv,facepaint='cassette')
        for groove in l['grooves']:recess(m,groove,-6.63,.98,'panel',.29)
        service_cover(m,l,side)
        for xx in (l['lo']+2.4,l['hi']-2.4):
            for zz in (l['low']+2.8,l['high']-2.8):bolt(m,xx,zz,-6.65,.48)
        # Replaceable lower guard with formed corners and six recessed fasteners.
        kick=rect(lo+5.0,hi-5.0,17.0,37.,3.,.65)
        kuv=lambda x,z:((x-(lo+5))/(hi-lo-10),(z-17)/20)
        slab(m,inset(kick,-.28),-5.62,-5.95,'rubber',.10)
        slab(m,kick,-5.92,-7.05,'dark',.27,uv=kuv,facepaint='kick')
        for xx in (lo+8,(lo+hi)/2,hi-8):
            for zz in (20.,34.):bolt(m,xx,zz,-7.07,.50)
        if side<0:
            xx=(lo+hi)/2;slab(m,rect(xx-12.5,xx+12.5,22.6,31.2,.5,.2),-7.08,-7.25,'frame',.08)
            label(m,xx-12.1,xx+12.1,23.,30.8,-7.27,5)
    # An overlapping central weather/pressure strip, with a visible rubber seam.
    box(m,(0,-5.2,(height+4)/2),(1.3,.70,height-15),'rubber',.16)
    box(m,(-.74,-5.63,(height+4)/2),(.35,.45,height-16),'steel',.10)
    clamps(m,width,height)
    wheel(m,-min(half*.45,38),58,10.5 if width>250 else 9.0)
    control(m,max(17,half*.25),62)
    gauge(m,min(half*.62,99),65)
    # A diamond-plate threshold and worn caution strip, kept below existing feet.
    box(m,(0,-9.2,2.6),(width+14,4.8,5.2),'steel',.27)
    P.card(m,'ar_pd_hazard',[(-half+10,-11.62,.7),(half-10,-11.62,.7),
        (half-10,-11.62,2.45),(-half+10,-11.62,2.45)],-Y,
        uv=[(0,0),((width-20)/12,0),((width-20)/12,1.75/12),(0,1.75/12)])
    for xx in np.arange(-half+12,half-10,9):
        for yy in (-10.35,-8.45):
            c=np.array((xx,yy,5.25));a=np.array((.707,.707,0));b=np.array((-.707,.707,0))
            P.bevel_box(m,c,(a,b,Z),(3.2,.58,.18),'ar_pd_dark',bevel=.10)
    points=np.vstack([pts for rows in m.polygons.values() for pts,n in rows])
    assert np.isfinite(points).all()
    assert points[:,0].min()>=-half-border-1e-6 and points[:,0].max()<=half+border+1e-6
    assert points[:,1].min()>=-12 and points[:,1].max()<=0
    assert points[:,2].min()>=0 and points[:,2].max()<=height+border+1e-6
    assert not m.boxes and not m.hulls
    frame=Frame(centre[0],centre[1],math.degrees(math.atan2(facing[1],facing[0]))+90,centre[2]);axes=np.array((frame.x,frame.y,frame.z))
    model.material_overrides.update(MATERIALS);model.tile_overrides.update({k:24. for k in MATERIALS})
    for paint,rows in m.polygons.items():
        for index,(pts,normal) in enumerate(rows):
            ns=m.polygon_normals.get((paint,index))
            P.card(model,paint,[frame.o+p@axes for p in pts],normal@axes,
                normals=[n@axes for n in ns] if ns is not None else None,uv=m.polygon_uvs.get((paint,index)))
    return dict(type='cargo' if width>250 else 'wing',triangles=m.triangle_count(),
                width=width,height=height,locking_dogs=6,formed_channels=4,service_covers=2,
                private_materials=len(MATERIALS),collision_envelope_exact=True)
