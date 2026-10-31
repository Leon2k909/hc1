"""Second art pass: manufactured joints, connected mounts and unique wear atlases."""
import os
for key in ('OPENBLAS_NUM_THREADS','OMP_NUM_THREADS','MKL_NUM_THREADS','NUMEXPR_NUM_THREADS'):os.environ[key]='1'
import psutil
process=psutil.Process();process.nice(psutil.IDLE_PRIORITY_CLASS);process.cpu_affinity(process.cpu_affinity()[-2:])
from pathlib import Path
import hashlib,importlib.util,json,math,re,shutil,sys
import numpy as np
import scipy.ndimage as ndi
from scipy.interpolate import PchipInterpolator
from PIL import Image,ImageDraw,ImageFont

HERE=Path(__file__).parent;ROOT=HERE.parents[2]
spec=importlib.util.spec_from_file_location('pump_proposal',HERE/'build.py')
B=importlib.util.module_from_spec(spec);spec.loader.exec_module(B)
K=B.K;O=B.O;S=B.S;face=B.face;UP=B.UP;X=B.X;FRONT=B.FRONT
ARCHIVE=B.OUT/'revision-01'
ORIGINAL_CANDIDATE=B.candidate;ORIGINAL_MATERIALS=B.materials
NEW_DETAILS=[]
CURVATURE={}

def archive():
    if (ARCHIVE/'archive.json').exists():return
    ARCHIVE.mkdir(parents=True,exist_ok=True)
    copies={}
    for directory in (B.DEST,B.MD):
        for path in directory.iterdir():
            if path.is_file() and path.suffix in ('.obj','.mtl','.vmdl','.vmat','.png'):
                relative=path.relative_to(ROOT);target=ARCHIVE/relative
                target.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(path,target)
                copies[relative.as_posix()]=B.sha(path)
    for name in ('before-main.png','after-main.png','before-rear.png','after-rear.png','render-report.json','review.json','verification.json'):
        path=B.OUT/name
        if path.exists():shutil.copy2(path,ARCHIVE/name)
    (ARCHIVE/'archive.json').write_text(json.dumps({'files':copies,'originalMapUnchanged':True},indent=2)+'\n')

def remove(m,predicate):
    result=K.Model()
    for paint,polys in m.polygons.items():
        for i,(points,normal) in enumerate(polys):
            if predicate(paint,np.array(points)):continue
            result.polygon(paint,points,normal,uv=m.polygon_uvs.get((paint,i)),normals=m.polygon_normals.get((paint,i)))
    result.boxes=list(m.boxes);result.hulls=list(m.hulls)
    return result

def contained(points,lo,hi):return np.all(points.min(axis=0)>=lo) and np.all(points.max(axis=0)<=hi)

def fastener(m,p,n=UP,r=.5,hexagonal=False):
    p=np.asarray(p,float);n=np.asarray(n,float)
    B.ring(m,p+n*.08,n,r*.58,r*1.38,.16,'ps_fastener',16)
    B.turned(m,p+n*.16,n,[(r*.84,0),(r,.09),(r,.48),(r*.84,.59)],'ps_fastener',6 if hexagonal else 16)
    if hexagonal:
        B.turned(m,p+n*.75,n,[(r*.51,0),(r*.51,.17)],'ps_fastener',12)
        B.ring(m,p+n*.86,n,r*.45,r*.56,.08,'ps_edge',12)
    else:
        a=np.array((1.,0.,0.))
        if abs(a@n)>.8:a=np.array((0.,1.,0.))
        b=K.normalise(np.cross(n,a));a=np.cross(b,n)
        m.oriented_box(p+n*.756,np.array((a,b,n)),(r*1.15,.11,.025),'ps_dark')

def cast_body(m):
    centre=np.array((22.,7.,39.));sides=72
    def radius(a):return 17.5+1.1*math.cos(a-.55)+.65*math.sin(2*a-.6)
    def section(x,scale,a):
        r=radius(a)*scale+.022*math.sin(a*13+x*.7)*math.sin(a*5-x*.4)
        return centre+np.array((x,r*math.cos(a),r*math.sin(a)))
    def shell(profile,paint):
        spline=PchipInterpolator([a for a,b in profile],[b for a,b in profile])
        xs=np.linspace(profile[0][0],profile[-1][0],21)
        def pt(x,a):return section(x,float(spline(x)),a)
        def normal(x,a):
            h=.0001
            return K.normalise(np.cross(pt(x,a+h)-pt(x,a-h),pt(x+h,a)-pt(x-h,a)))
        for xa,xb in zip(xs,xs[1:]):
            for i in range(sides):
                a=i*math.tau/sides;b=(i+1)*math.tau/sides
                points=[pt(xa,a),pt(xa,b),pt(xb,b),pt(xb,a)]
                ns=[normal(xa,a),normal(xa,b),normal(xb,b),normal(xb,a)]
                face(m,paint,points,sum(ns),normals=ns)
        for sign,x in ((-1,xs[0]),(1,xs[-1])):
            face(m,paint,[pt(x,i*math.tau/sides) for i in range(sides)],X*sign)
    shell([(-7,.68),(-6.5,.80),(-4.5,.94),(-1.5,1.0),(2.5,1.0),(4.05,.96)],'ps_pump')
    shell([(4.24,.96),(4.8,.985),(5.6,.975),(6.8,.89),(8.,.80)],'ps_pump')
    # Separate compressed gasket: a real casing split, not a drawn-on dark line.
    for i in range(sides):
        a=i*math.tau/sides;b=(i+1)*math.tau/sides
        pts=[section(4.055,.96,a),section(4.055,.96,b),section(4.235,.96,b),section(4.235,.96,a)]
        face(m,'ps_gasket',pts,sum(p-centre-X*(p[0]-centre[0]) for p in pts))
    for a in np.linspace(0,math.tau,8,endpoint=False):
        fastener(m,centre+X*8.1+np.array((0,13.2*math.cos(a),13.2*math.sin(a))),X,.53,True)
    # Rounded casting webs join the suction boss, with tapered outer ends.
    for a in np.radians((22.5,142.5,262.5)):
        radial=np.array((0,math.cos(a),math.sin(a)));tangent=np.cross(X,radial)
        for r,width,depth in ((8.3,1.7,1.5),(10.6,1.45,1.15),(12.8,1.0,.7)):
            B.block(m,centre+X*(8.0+depth*.24)+radial*r,(depth,2.9,width),'ps_pump',.35,.18,np.array((X,radial,tangent)))
    # Fill/drain plugs and lifting eye give the casting a serviceable construction.
    B.turned(m,(13.8,7,39),-X,[(3.5,0),(3.5,.6),(2.8,.9)],'ps_fastener',12)
    B.turned(m,(22,7,56),UP,[(1.3,0),(1.3,1.0),(1.,1.4)],'ps_fastener',6)

def coupling_cover(m):
    radius=8.1;cx=(1.5,4.5,7.5,10.5);ta,tb=math.radians(-12),math.radians(192)
    def p(x,a,r=radius):return np.array((x,7+r*math.cos(a),40+r*math.sin(a)))
    for x in cx:
        for row in range(6):
            a0=ta+(tb-ta)*row/6;a1=ta+(tb-ta)*(row+1)/6;ac=(a0+a1)/2
            inner=[];outer=[]
            # Include each exact rectangular-cell corner. Uniform circle angles
            # alone cut those corners off, leaving unintended diamond gaps.
            half_height=radius*(a1-a0)/2
            angles=sorted(set([k*math.tau/24 for k in range(24)]+
                              [math.atan2(sy*half_height,sx*1.5)%math.tau for sx in (-1,1) for sy in (-1,1)]))
            for q in angles:
                u=math.cos(q);v=math.sin(q)
                scale=min(1.5/max(abs(u),1e-8),radius*(a1-a0)/2/max(abs(v),1e-8))
                inner.append((x+.67*u,ac+.67*v/radius))
                outer.append((x+scale*u,ac+scale*v/radius))
            for k in range(len(angles)):
                j=(k+1)%len(angles)
                for r,sign in ((radius,1),(radius-.085,-1)):
                    coords=[inner[k],inner[j],outer[j],outer[k]]
                    points=[p(xx,aa,r) for xx,aa in coords]
                    ns=[np.array((0,math.cos(aa),math.sin(aa)))*sign for xx,aa in coords]
                    face(m,'ps_guard',points,sum(ns),normals=ns)
                points=[p(*inner[k]),p(*inner[j]),p(*inner[j],radius-.085),p(*inner[k],radius-.085)]
                toward=np.array((x-inner[k][0],0,0))+np.array((0,-math.sin(ac),math.cos(ac)))*(ac-inner[k][1])*radius
                face(m,'ps_guard',points,toward)
    for x in (0.,12.):
        for k in range(36):
            a=ta+(tb-ta)*k/36;b=ta+(tb-ta)*(k+1)/36
            face(m,'ps_guard',[p(x,a),p(x,b),p(x,b,radius-.085),p(x,a,radius-.085)],X*(-1 if x==0 else 1))
    for a in (ta,tb):
        pts=[p(0,a),p(12,a),p(12,a,radius-.085),p(0,a,radius-.085)]
        face(m,'ps_guard',pts,np.cross(pts[1]-pts[0],pts[2]-pts[0]))
        for x in (1.5,10.5):
            at=p(x,a)
            B.block(m,(x,at[1],at[2]-1.2),(3.7,2.0,2.7),'ps_guard',.25,.08)
            B.tube(m,(x,at[1],16.2),(x,at[1],at[2]-2),.5,'ps_edge',10)
            B.block(m,(x,at[1],16.3),(3.4,3.1,.7),'ps_edge',.25,.08)
    B.block(m,(6.,7.,48.31),(10,4.6,.24),'ps_guard',.35,.06)
    B.label(m,3,(6.,7.,48.44),8.8,3.4,X,np.array((0,1,0)))

def rounded_mount(m,x,yz):
    yz=np.array(yz,float);centre=yz.mean(axis=0)
    orientation=np.sign(sum(np.cross(yz[(i+1)%len(yz)]-yz[i],yz[(i+2)%len(yz)]-yz[(i+1)%len(yz)]) for i in range(len(yz))))
    rings=[]
    for dx,inset in ((-2.8,.34),(-2.46,0),(2.46,0),(2.8,.34)):
        vertices=[p+K.normalise(centre-p)*inset for p in yz];outline=[]
        for i,b in enumerate(vertices):
            a=vertices[i-1];c=vertices[(i+1)%len(vertices)]
            u=K.normalise(a-b);v=K.normalise(c-b);angle=math.acos(np.clip(u@v,-1,1))
            radius=min(.64,math.tan(angle/2)*min(np.linalg.norm(a-b),np.linalg.norm(c-b))*.32)
            distance=radius/math.tan(angle/2);o=b+K.normalise(u+v)*radius/math.sin(angle/2)
            start=b+u*distance;end=b+v*distance
            t0=math.atan2(*(start-o)[::-1]);t1=math.atan2(*(end-o)[::-1])
            if orientation>0:
                while t1<t0:t1+=math.tau
            else:
                while t1>t0:t1-=math.tau
            for t in np.linspace(t0,t1,5):
                p=o+radius*np.array((math.cos(t),math.sin(t)));outline.append(np.array((x+dx,*p)))
        rings.append(outline)
    for a,b in zip(rings,rings[1:]):
        for i in range(len(a)):
            j=(i+1)%len(a);points=[a[i],a[j],b[j],b[i]]
            face(m,'ps_motor',points,np.cross(points[1]-points[0],points[2]-points[0]))
    for sign,points in ((-1,rings[0]),(1,rings[-1])):face(m,'ps_motor',points,X*sign)

def motor_mounts(m):
    for x in (-30.,-10.):
        for cy,sign in ((-6.,1),(20.,-1)):
            # Inclined cast webs penetrate the cylindrical housing: no floating stator.
            yz=[(-11,17.7),(-3,17.7),(-1,31),(-5,34)]
            if sign<0:yz=[(14-y,z) for y,z in yz]
            rounded_mount(m,x,yz)
            B.block(m,(x,cy,17.1),(13,11,1.5),'ps_motor',.7,.22)
            for dx in (-4.6,4.6):fastener(m,(x+dx,cy,17.92),UP,.57,True)
            # Visible shim pack under the machined mounting foot.
            for z in (16.0,16.15,16.30):B.block(m,(x,cy,z),(13.6,11.4,.10),'ps_edge',.25,.035)

def controller(m):
    c=np.array((-28.,-16.,60.));w,d,h=19.,10.,25.
    for x in (-w/2,w/2):B.block(m,c+(x,0,0),(.18,d,h),'ps_sheet',.08,.025)
    for z in (-h/2,h/2):B.block(m,c+(0,0,z),(w,d,.18),'ps_sheet',.08,.025)
    B.block(m,c+(0,d/2,0),(w,.18,h),'ps_sheet',.08,.025)
    B.block(m,c+(0,-d/2-.08,0),(18.5,.25,24.5),'ps_gasket',.25,.05)
    B.block(m,c+(0,-d/2-.32,0),(18.2,.22,24.2),'ps_sheet',.23,.06)
    B.block(m,(-28,-21.58,64.8),(15.5,.35,7.3),'ps_dark',.4,.09)
    B.plate(m,'ps_screen',(-28,-21.77,64.8),14.2,6.0)
    for i,x in enumerate((-32.5,-23.5)):
        if i:B.turned(m,(x,-21.5,54.8),FRONT,[(1.52,0),(1.52,.12)],'ps_guard',32)
        B.turned(m,(x,-21.65,54.8),FRONT,[(1.03,0),(1.03,.42),(.79,.65)],'ps_fastener',24)
        B.turned(m,(x,-22.3,54.8),FRONT,[(.77 if i==0 else 1.02,0),(.77 if i==0 else 1.02,.65),(.67 if i==0 else .94,.86)],'ps_green' if i==0 else 'ps_red',24)
    for z in (53.,67.):
        for dz in (-1.15,0,1.15):B.turned(m,(-37.4,-21.1,z+dz),UP,[(.3,0),(.3,.95)],'ps_fastener',16)
    B.turned(m,(-20,-21.5,59),FRONT,[(.61,0),(.61,.18),(.48,.27)],'ps_metal',24)
    B.plate(m,'ps_dark',(-20,-21.79,59),.1,.66)
    B.label(m,0,(-28,-21.46,49.9),15.5,1.6)
    for x in (-35.7,-20.3):
        for z in (48.8,71.2):fastener(m,(x,-21.45,z),FRONT,.24)
    for x in (-35.,-21.):
        B.block(m,(x,-14,32),(2.8,.25,31),'ps_edge',.15,.05)
        B.block(m,(x+1.2,-15.2,32),(.25,2.8,31),'ps_edge',.15,.05)
        B.block(m,(x,-14,16.5),(6,6,1.1),'ps_frame',.35,.1)
        fastener(m,(x,-15.6,17.1),UP,.48,True)
    for x in (-31.,-25.):
        B.turned(m,(x,-16,47.4),-UP,[(.85,0),(.85,.6),(.62,.95)],'ps_fastener',6)
    S.pipe_run(m,[(-31,-16,47),(-31,-16,34),(-24,-4,34),(-21,3,52),(-21,3,55.5)],.65,'ps_rubber',16,4.)
    a=np.array((-24.,-4.,34.));b=np.array((-21.,3.,52.));v=b-a;length=np.linalg.norm(v);direction=v/length
    for t in np.arange(4.0,length-3.,1.4):B.ring(m,a+direction*t,direction,.65,.79,.18,'ps_rubber',12)
    B.turned(m,(-21,3,55.5),-UP,[(.83,0),(.83,.8),(.65,1.1)],'ps_fastener',6)
    # Stamped certification plate riveted to the clean upper cover.
    B.block(m,(-28,-15.7,72.67),(13,5,.12),'ps_fastener',.18,.025)
    B.label(m,1,(-28,-15.7,72.75),12.3,4.4,X,np.array((0,1,0)))

def candidate():
    B.volute=cast_body;B.screw=fastener
    m=ORIGINAL_CANDIDATE()
    def old_parts(p,pts):
        if p=='ps_warning':return True
        if contained(pts,(-42,-29,44.3),(-14,-10,74)):return True
        if p=='ps_edge' and contained(pts,(-38,-18,17),(-34,-14,47)):return True
        if p in ('ps_rubber','ps_metal') and contained(pts,(-30,-12,58),(-19,1,63)):return True
        if p in ('ps_motor','ps_fastener','ps_dark'):
            for x in (-30,-10):
                for y in (-6,20):
                    if contained(pts,(x-6.1,y-5.6,16.8),(x+6.1,y+5.6,27.1)):return True
        if p in ('ps_edge','ps_fastener','ps_dark'):
            for x in (-47.,47.):
                if contained(pts,(x-4,20,18),(x+4,28,21)):return True
        return False
    m=remove(m,old_parts);coupling_cover(m);motor_mounts(m);controller(m)
    for x in (-47.,47.):
        B.block(m,(x,24,16.6),(7,7,1.3),'ps_edge',.5,.18)
        B.tube(m,(x,24,16.6),(x,24,18),1.35,'ps_frame',16)
        for xx in (x-2,x+2):fastener(m,(xx,24,17.3),UP,.4,True)
    # Hose collars, folded reinforcement and joints sit on actual surfaces.
    for z in (29,41):
        B.block(m,(-35,-14.3,z),(4,.18,1.5),'ps_fastener',.2,.04)
    for x in (-47.,47.):
        for i in range(15):
            a=i*math.tau/15
            B.turned(m,(x+1.45*math.cos(a),24+1.45*math.sin(a),17.3),UP,[(.16,0),(.22,.11),(.1,.21)],'ps_weld',8)
    for paint in m.polygons:
        m.material_overrides[paint]=f'{B.MAT}/{paint}.vmat';m.tile_overrides[paint]=12.
    assign_atlas_uvs(m)
    bake_curvature(m)
    return m

# Each coated part receives six unique orthographic charts. Wear uses the actual
# object coordinates, so scratches, bolt stains and chipped rims stay in place.
LO=np.array((-53.,-29.,0.));HI=np.array((53.,29.,74.))
ATLAS_PAINTS={'ps_pump','ps_motor','ps_frame','ps_sheet','ps_guard','ps_tray'}
CHARTS=[(0,1,2),(0,1,2),(1,0,2),(1,0,2),(2,0,1),(2,0,1)]

def assign_atlas_uvs(m):
    for paint in ATLAS_PAINTS:
        for i,(points,n) in enumerate(m.polygons.get(paint,[])):
            axis=int(np.argmax(abs(n)));chart=axis*2+(1 if n[axis]<0 else 0)
            _,u,v=CHARTS[chart];col=chart%3;row=chart//3
            coords=[]
            for p in points:
                uu=.014+.972*(p[u]-LO[u])/(HI[u]-LO[u])
                vv=.014+.972*(p[v]-LO[v])/(HI[v]-LO[v])
                coords.append(((col+uu)/3,1-(row+1-vv)/2))
            m.polygon_uvs[(paint,i)]=coords

def bake_curvature(m):
    """Project real convex/concave mesh seams into the same six texture charts."""
    from collections import defaultdict
    for paint in ATLAS_PAINTS:
        edges=defaultdict(list)
        for i,(points,normal) in enumerate(m.polygons.get(paint,[])):
            coords=m.polygon_uvs[(paint,i)];centre=np.mean(points,axis=0)
            for j,a in enumerate(points):
                k=(j+1)%len(points);b=points[k]
                key=tuple(sorted((tuple(np.round(a,3)),tuple(np.round(b,3)))))
                edges[key].append((normal,centre,coords[j],coords[k]))
        convex=Image.new('L',(2046,1364));concave=Image.new('L',convex.size)
        draw_a=ImageDraw.Draw(convex);draw_b=ImageDraw.Draw(concave)
        for records in edges.values():
            if len(records)==2:
                a,b=records;angle=math.acos(float(np.clip(a[0]@b[0],-1,1)))
                if angle<math.radians(19):continue
                intensity=int(min(1.,angle/(math.pi/2))*255)
                drawer=draw_a if a[0]@(b[1]-a[1])<=0 else draw_b
            elif len(records)==1:
                intensity=80;drawer=draw_a
            else:continue
            for n,c,a,b in records:
                drawer.line((a[0]*2046,(1-a[1])*1364,b[0]*2046,(1-b[1])*1364),fill=intensity,width=2)
        wear=np.asarray(convex,dtype=np.float32)/255;dirt=np.asarray(concave,dtype=np.float32)/255
        CURVATURE[paint]=(ndi.gaussian_filter(wear,.75),ndi.gaussian_filter(dirt,2.0))
        convex.save(B.OUT/('curvature-'+paint+'.png'))

def atlas(name,base,rough):
    import ares_materials as AM
    width,height=2046,1364;cw=ch=682
    colour=np.zeros((height,width,3),np.uint8);rr=np.zeros((height,width),np.uint8)
    metal=np.zeros((height,width),np.uint8);normal=np.full((height,width,3),(128,128,255),np.uint8)
    for chart,(axis,u,v) in enumerate(CHARTS):
        rng=np.random.default_rng(310700+chart*31+sum(map(ord,name)))
        yy,xx=np.mgrid[:ch,:cw];uu=(xx/(cw-1)-.014)/.972;vv=((1-yy/(ch-1))-.014)/.972
        p=[np.full_like(uu,(LO[a]+HI[a])*.5) for a in range(3)]
        p[u]=LO[u]+uu*(HI[u]-LO[u]);p[v]=LO[v]+vv*(HI[v]-LO[v])
        x,y,z=p
        # Coordinates missing from a chart are the dominant face's natural plane.
        if axis==0:p[0]=np.full_like(uu,30. if chart==0 else -37.)
        if axis==1:p[1]=np.full_like(uu,-23. if chart==3 else 24.)
        if axis==2:p[2]=np.full_like(uu,72.5 if chart==4 else 17.)
        x,y,z=p
        fine=rng.normal(0,1,uu.shape);grain=ndi.gaussian_filter(fine,.60);grain/=grain.std()
        patch=ndi.gaussian_filter(fine,13);patch/=patch.std()
        chips=np.zeros_like(uu);dirt=np.zeros_like(uu);rust=np.zeros_like(uu)
        if name=='ps_pump':
            r=np.hypot(y-7,z-39)
            if axis==0:
                edge=np.minimum(abs(r-14.6),abs(r-7.5))
                chips=np.clip((.42-edge+.21*grain)*2.0,0,1)*np.clip(.65+.45*patch,0,1)
                for a in np.linspace(0,math.tau,8,endpoint=False):
                    by=7+13.2*math.cos(a);bz=39+13.2*math.sin(a)
                    d=np.hypot(y-by,z-bz)
                    dirt+=.38*np.exp(-((d-.83)/.7)**2)
                    rust+=.26*np.exp(-((d-1.)/.37)**2)*np.clip(.6+.5*patch,0,1)
                    rust+=.12*np.exp(-((y-by)/.36)**2)*np.exp(-(bz-z)/3.2)*(z<bz)*(z>bz-7)
            else:
                edge=np.minimum(abs(x-26.2),abs(x-30.0))
                chips=np.clip((.32-edge+.18*grain)*2,0,1)*np.clip(.4+.5*patch,0,1)
                dirt+=.16*np.exp(-((x-26.15)/.5)**2)
            dirt+=.25*np.exp(-(z-17)/3.5)*(z>16)
        elif name=='ps_motor':
            edge=np.minimum(abs(x+37),abs(x+4))
            chips=np.clip((.4-edge+.16*grain)*2,0,1)*np.clip(.7+.4*patch,0,1)
            dirt+=.26*np.exp(-((z-24)/4)**2)+.17*np.exp(-((x+37)/1.8)**2)
            rust+=.10*np.exp(-((z-19)/1.8)**2)*np.clip(patch+.3,0,1)
        elif name in ('ps_frame','ps_tray'):
            edge=np.minimum.reduce((abs(abs(x)-49),abs(abs(y)-23),abs(z-12),abs(z-5)))
            chips=np.clip((.36-edge+.25*grain)*2,0,1)*np.clip(.65+.6*patch,0,1)
            dirt+=.26*np.exp(-((z-16)/2.8)**2)+.10*np.clip(patch-.2,0,1)
            rust+=.22*np.exp(-((z-5)/2)**2)*np.clip(patch+.2,0,1)
            if name=='ps_tray' and axis==2:
                for cx,cy,r0 in ((-2,-14,3.5),(32,-9,2.8),(-37,16,1.9)):
                    d=np.hypot((x-cx),(y-cy)*1.4);dirt+=.38*np.exp(-(d/r0)**4)
        elif name=='ps_sheet':
            edge=np.minimum.reduce((abs(x+37.5),abs(x+18.5),abs(z-47.5),abs(z-72.5)))
            chips=np.clip((.23-edge+.11*grain)*2,0,1)*np.clip(.45+.6*patch,0,1)
            dirt+=.14*np.exp(-((z-48)/2.0)**2)
            for sx,sz in ((-35.7,48.8),(-20.3,48.8),(-35.7,71.2),(-20.3,71.2)):
                dirt+=.18*np.exp(-((x-sx)**2+(z-sz)**2)/.7)
        elif name=='ps_guard':
            edge=np.minimum(abs(x),abs(x-12.))
            chips=np.clip((.55-edge+.26*grain)*2,0,1)*np.clip(.65+.5*patch,0,1)
            dirt+=.13*np.clip(patch+.2,0,1)
        row,col=divmod(chart,3);sl=np.s_[row*ch:(row+1)*ch,col*cw:(col+1)*cw]
        edge_wear,cavity=CURVATURE[name]
        chips=np.clip(chips+edge_wear[sl]*1.8*np.clip(.5+.52*patch+.13*grain,0,1),0,1)
        dirt+=cavity[sl]*.55
        # Fine abrasion, much weaker than edge coating loss.
        scratches=Image.new('L',(cw,ch));draw=ImageDraw.Draw(scratches)
        for _ in range(180):
            a,b=rng.uniform(0,cw),rng.uniform(0,ch)
            draw.line((a,b,a+rng.uniform(2,15),b+rng.uniform(-1.5,1.5)),fill=int(rng.uniform(8,75)),width=1)
        sc=np.asarray(scratches)/255.;chips=np.clip(chips+sc*.65,0,1);dirt=np.clip(dirt,0,.65);rust=np.clip(rust,0,.40)
        c=np.array(base)[None,None,:]*(1+.012*patch[...,None]+.007*grain[...,None])
        c=c*(1-chips[...,None])+np.array((105,108,99))*chips[...,None]
        c*=1-dirt[...,None];c=c*(1-rust[...,None])+np.array((94,54,28))*rust[...,None]
        roughness=np.clip(rough+.025*patch+.018*grain+.23*dirt+.18*rust-.21*chips,.24,.95)
        met=np.clip(.88*chips*(1-rust*2),0,.9)
        bump=grain*(.0014 if name in ('ps_pump','ps_motor') else .00025)-chips*.007-sc*.0015
        bump-=rust*.0015
        nm=AM.normals(bump,(cw/(HI[u]-LO[u]),ch/(HI[v]-LO[v])))
        colour[sl]=np.clip(c,0,255).astype('uint8');rr[sl]=np.uint8(roughness*255)
        metal[sl]=np.uint8(met*255);normal[sl]=np.clip((nm*.5+.5)*255,0,255).astype('uint8')
    stem='atlas_'+name
    for suffix,array in (('color',colour),('rough',rr),('metal',metal),('normal',normal)):
        Image.fromarray(array).save(B.MD/(stem+'_'+suffix+'.png'))
    path=f'{B.MAT}/{stem}'
    text=O.vmat(name,path+'_color.png',path+'_normal.png',path+'_rough.png')
    text=text.replace('    g_flMetalness "0.0"',f'    F_METALNESS_TEXTURE "1"\n    TextureMetalness "{path}_metal.png"')
    (B.MD/(name+'.vmat')).write_text(text)

def materials():
    ORIGINAL_MATERIALS()
    # Aged blue steel, warm guard coating and pale folded controller sheet stay distinct.
    for name,base,rough in (
        ('ps_pump',(51,78,85),.64),('ps_motor',(53,65,71),.60),('ps_frame',(48,58,59),.64),
        ('ps_sheet',(138,142,129),.53),('ps_guard',(169,124,37),.58),('ps_tray',(74,77,71),.58)):
        atlas(name,base,rough)
    import ares_materials as AM
    n=1024;rng=np.random.default_rng(7103);noise=rng.normal(0,1,(n,n));grain=ndi.gaussian_filter(noise,.65);grain/=grain.std()
    c=np.array((92,98,94))[None,None,:]*(1+.02*grain[...,None])
    Image.fromarray(np.clip(c,0,255).astype('uint8')).save(B.MD/'fastener_color.png')
    AM.BX.save_grey(B.MD/'fastener_rough.png',np.clip(.43+.04*grain,.25,.7))
    AM.BX.save_normal(B.MD/'fastener_normal.png',AM.normals(grain*.0003,(n/12,n/12)))
    (B.MD/'ps_fastener.vmat').write_text(O.vmat('ps_fastener',f'{B.MAT}/fastener_color.png',f'{B.MAT}/fastener_normal.png',f'{B.MAT}/fastener_rough.png',.82))
    # Finish labels with tiny abrasions, faded ink and a proper caution panel.
    path=B.MD/'labels_color.png';im=Image.open(path).convert('RGB');d=ImageDraw.Draw(im)
    d.rectangle((0,768,2047,1023),fill=(178,137,42))
    d.text((1024,838),'CAUTION / ROTATING COUPLING',font=ImageFont.truetype('C:/Windows/Fonts/arialbd.ttf',63),anchor='mm',fill=(31,35,29))
    d.text((1024,937),'ISOLATE DRIVE BEFORE REMOVING GUARD',font=ImageFont.truetype('C:/Windows/Fonts/arial.ttf',45),anchor='mm',fill=(43,44,31))
    for _ in range(500):
        x=int(rng.uniform(0,2048));y=int(rng.uniform(0,1024));d.line((x,y,x+int(rng.uniform(1,9)),y),fill=(177,174,149),width=1)
    im.save(path)

def main():
    archive();B.candidate=candidate;B.materials=materials
    sys.argv=[sys.argv[0],'--refine']+(['--geometry-only'] if '--geometry-only' in sys.argv else [])
    B.main()
    data=json.loads((B.OUT/'manifest.json').read_text());data.update(realismRevision=2,
        previousProposalArchive='output/asset-improvement-20261030/pump-skid/revision-01',
        previousPumpMeshSHA256='0bc0ceac2f1b6d1af505d20963ee052fc918a5de1bf5f372cf7901ab4df7571e',
        newDetails=['curved split cast housing with separate compressed gasket',
                    'formed perforated coupling shield with real holes',
                    'inclined connected motor mounts and shim packs',
                    'folded controller shell, hinges, cam lock and correctly sized switches',
                    'corrugated cable conduit and routed gland connections',
                    'unique position-based wear atlases with exposed-metal masks',
                    'bolt halos, localized oxidation, recessed dirt and fine cast texture'])
    for path in (B.OUT/'manifest.json',HERE/'candidate.json'):path.write_text(json.dumps(data,indent=2)+'\n')

if __name__=='__main__':main()
