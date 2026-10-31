"""A private full-object replacement proposal for Collider's lower-hall pump skid."""
import os
for key in ('OPENBLAS_NUM_THREADS','OMP_NUM_THREADS','MKL_NUM_THREADS','NUMEXPR_NUM_THREADS'):
    os.environ[key]='1'
import psutil
proc=psutil.Process();proc.nice(psutil.IDLE_PRIORITY_CLASS);proc.cpu_affinity(proc.cpu_affinity()[-2:])
from pathlib import Path
from collections import Counter
import argparse,hashlib,json,math,re,sys
import numpy as np
from PIL import Image,ImageDraw,ImageFont
import scipy.ndimage as ndi

ROOT=Path(__file__).resolve().parents[3];sys.path.insert(0,str(ROOT/'Tools'))
import map_kit as K
import collider_map as M
import collider_machinery as H
import collider_operators as O
import collider_services as S
import boxyard_map as B
from belltower_furniture import face
OUT=ROOT/'output/asset-improvement-20261030/pump-skid'
RESOURCE='models/props/collider/pump-skid-trial-v1'
MAT='materials/collider/pump-skid-trial-v1'
DEST=ROOT/'Assets'/RESOURCE;MD=ROOT/'Assets'/MAT
ORIGIN=np.array((-850.,-350.,0.))
UP=np.array((0.,0.,1.));X=np.array((1.,0.,0.));FRONT=np.array((0.,-1.,0.));AXES=np.eye(3)
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()

def signature(p,points):
    return p,tuple(sorted(tuple(round(float(v),3) for v in point) for point in points))

def baseline():
    raw=K.Model();H.instrument_cart(raw,*ORIGIN,106,58,74,0)
    # The published packed detail still contains the earlier equipment case here.
    # Extract its actual isolated geometry; do not manufacture a pump-shaped before.
    before=K.Model();vs=[];uv=[];ns=[];paint='';count=0
    lo=ORIGIN+(-58,-39,-.1);hi=ORIGIN+(60,39,80)
    source=ROOT/'Assets/models/maps/collider/collider_detail.obj'
    with source.open() as stream:
        for line in stream:
            if line.startswith('v '):
                a,z,n=map(float,line.split()[1:]);vs.append(np.array((-a,n,z)))
            elif line.startswith('vt '):uv.append(tuple(map(float,line.split()[1:])))
            elif line.startswith('vn '):
                a,z,n=map(float,line.split()[1:]);ns.append(np.array((-a,n,z)))
            elif line.startswith('usemtl '):paint=line[7:].strip()
            elif line.startswith('f '):
                ids=[[int(v)-1 for v in token.split('/')] for token in line.split()[1:]]
                points=np.array([vs[v] for v,t,n in ids])
                if np.all(points.min(axis=0)>=lo) and np.all(points.max(axis=0)<=hi):
                    count+=1
                    before.polygon(paint,[p-ORIGIN for p in points],uv=[uv[t] for v,t,n in ids],normals=[ns[n] for v,t,n in ids])
    assert count==2420,('Unexpected saved equipment case selection',count)
    assert set(before.polygons)=={'co_amber','co_case','co_rubber','co_signs','co_silver','co_trim'}
    for centre,axes,size,surface in raw.boxes:before.boxes.append((centre-ORIGIN,axes,size,surface))
    M.configure(before)
    return before,{'source':source.relative_to(ROOT).as_posix(),'sourceSHA256':sha(source),
                   'planOrigin':ORIGIN.tolist(),'exactMatchedTriangles':count,
                   'copiedSavedGeometryUVsNormals':True,'sourcePlacementDimensions':[106,58,74],
                   'savedAssetType':'equipment case','proposedAssetType':'industrial pump skid',
                   'selectionEnvelopePlan':[lo.tolist(),hi.tolist()]}

def block(m,p,size,paint='ps_frame',radius=.45,bevel=.12,axes=AXES):
    O.round_block(m,np.asarray(p,float),size,paint,radius,bevel,axes=axes,segments=3)

def turned(m,p,axis,profile,paint='ps_metal',sides=32):
    O.turned(m,p,axis,profile,paint,sides)

def tube(m,a,b,r,paint='ps_metal',sides=12):O.tube(m,a,b,r,paint,sides)

def ring(m,p,axis,inner,outer,depth,paint='ps_metal',sides=32):
    B.lathe(m,p,axis,[(inner,-depth/2),(outer,-depth/2),(outer,depth/2),
                     (inner,depth/2),(inner,-depth/2)],paint,sides=sides)

def screw(m,p,normal=UP,r=.5,hexagonal=False):
    p=np.asarray(p,float);n=np.asarray(normal,float)
    turned(m,p,n,[(r*1.35,0),(r*1.35,.15)],'ps_metal',16)
    turned(m,p+n*.15,n,[(r*.9,0),(r,.10),(r,.55),(r*.86,.65)],'ps_metal',6 if hexagonal else 12)
    if not hexagonal:
        a=np.array((1.,0.,0.))
        if abs(n@a)>.8:a=np.array((0.,1.,0.))
        b=K.normalise(np.cross(n,a));a=np.cross(b,n)
        m.oriented_box(p+n*.805,np.array((a,b,n)),(r*1.15,.12,.025),'ps_dark')

def plate(m,paint,p,w,h,right=X,up=UP,uv=None):
    p=np.asarray(p,float);right=np.asarray(right,float);up=np.asarray(up,float)
    face(m,paint,[p-right*w/2-up*h/2,p+right*w/2-up*h/2,p+right*w/2+up*h/2,p-right*w/2+up*h/2],
         np.cross(right,up),uv=uv or [(0,0),(1,0),(1,1),(0,1)])

def label(m,index,p,w,h,right=X,up=UP):
    v0=1-(index+1)/4;v1=1-index/4
    plate(m,'ps_label',p,w,h,right,up,[(0,v0),(1,v0),(1,v1),(0,v1)])

def flange(m,p,axis,inner,outer,depth=2.0):
    p=np.asarray(p,float);n=np.asarray(axis,float)
    ring(m,p,n,inner,outer,depth,'ps_pump',40)
    ring(m,p+n*(depth/2+.1),n,inner,outer*.81,.25,'ps_gasket',40)
    a=K.normalise(np.cross(n,UP if abs(n[2])<.9 else X));b=np.cross(n,a)
    for angle in np.linspace(0,math.tau,8,endpoint=False):
        screw(m,p+n*(depth/2+.26)+(a*math.cos(angle)+b*math.sin(angle))*(outer-1.25),n,.48,True)

def volute(m):
    centre=np.array((22.,7.,39.));profiles=[(-7,.76),(-5,.94),(-2,1.),(5,1.),(8,.80)]
    def point(t,a):
        offset,scale=t;r=(17.+1.2*(1+math.cos(a-.7)))*scale
        return centre+np.array((offset,r*math.cos(a),r*math.sin(a)))
    for left,right in zip(profiles,profiles[1:]):
        for i in range(48):
            a=i*math.tau/48;b=(i+1)*math.tau/48
            points=[point(left,a),point(left,b),point(right,b),point(right,a)]
            normals=[]
            for t,angle in ((left,a),(left,b),(right,b),(right,a)):
                radial=K.normalise(np.array((0,math.cos(angle),math.sin(angle))))
                slope=(right[1]-left[1])*(17+1.2*(1+math.cos(angle-.7)))/(right[0]-left[0])
                normals.append(K.normalise(radial-X*slope))
            face(m,'ps_pump',points,sum(normals),normals=normals)
    for sign,t in ((-1,profiles[0]),(1,profiles[-1])):
        face(m,'ps_pump',[point(t,i*math.tau/48) for i in range(48)],X*sign)
    for a in np.linspace(0,math.tau,8,endpoint=False):
        screw(m,centre+X*8.15+np.array((0,math.cos(a)*13.2,math.sin(a)*13.2)),X,.53,True)
    for a in np.radians((22.5,142.5,262.5)):
        radial=np.array((0,math.cos(a),math.sin(a)));tangent=np.cross(X,radial)
        block(m,centre+X*8.2+radial*11.1,(1.25,6.0,1.35),'ps_pump',.45,.20,np.array((X,radial,tangent)))

def candidate():
    m=K.Model()
    # Grounded isolation feet, genuine folded channels and a shallow open drip tray.
    for x in (-43.,43.):
        for y in (-22.,22.):
            block(m,(x,y,1.7),(8.6,8.6,3.4),'ps_rubber',1.1,.4)
            block(m,(x,y,3.8),(9,9,.9),'ps_metal',.8,.15)
            screw(m,(x,y,4.25),UP,.8,True)
    for y in (-22.,22.):
        for z in (5.,12.):block(m,(0,y,z),(102,9,1.8),'ps_frame',.5,.18)
        block(m,(0,y+(-3.6 if y<0 else 3.6),8.5),(102,1.6,6.4),'ps_frame',.4,.16)
    for x in (-42.,0.,42.):block(m,(x,0,13.5),(7,49,2.2),'ps_frame',.6,.22)
    block(m,(0,0,15.2),(98,47,1.5),'ps_tray',.9,.25)
    for y in (-23.1,23.1):block(m,(0,y,17.1),(98,.9,4.1),'ps_tray',.2,.12)
    for x in (-48.6,48.6):block(m,(x,0,17.1),(.9,47,4.1),'ps_tray',.2,.12)
    # Rolled rear protection / carrying rail with curved, joined corners.
    S.pipe_run(m,[(-47,24,18),(-47,24,71),(47,24,71),(47,24,18)],1.35,'ps_frame',16,5)
    for x in (-47.,47.):
        block(m,(x,24,19),(7,7,1.3),'ps_edge',.5,.18)
        for xx in (x-2,x+2):screw(m,(xx,24,19.7),UP,.4,True)
    # Finned motor, bearing bells, mounting lugs and an open fan guard on the rear.
    turned(m,(-37,7,40),X,[(12.4,0),(14,2),(14,31),(12.7,33)],'ps_motor',48)
    for a in np.linspace(0,math.tau,24,endpoint=False):
        radial=np.array((0,math.cos(a),math.sin(a)));tangent=np.cross(X,radial)
        block(m,np.array((-20.5,7,40))+radial*15.3,(28.8,2.6,.62),'ps_motor',.18,.07,
              np.array((X,radial,tangent)))
    for x in (-37.,-4.):
        turned(m,(x,7,40),X,[(13,0),(14.7,.6),(14.7,2.1),(12.5,4)],'ps_motor',48)
        for a in np.linspace(0,math.tau,4,endpoint=False):
            screw(m,(x+4.02,7+11.4*math.cos(a),40+11.4*math.sin(a)),X,.6,True)
    for x in (-30.,-10.):
        for y in (-6.,20.):
            block(m,(x,y,22),(9,9,10),'ps_motor',1.2,.4)
            block(m,(x,y,17.7),(12,11,1.6),'ps_motor',.8,.22)
            screw(m,(x,y,18.55),UP,.68,True)
    ring(m,(-42.5,7,40),X,12.1,15.,7,'ps_motor',48)
    turned(m,(-39.1,7,40),-X,[(11.9,0),(11.9,.25)],'ps_dark',48)
    # Real pitched fan blades sit behind the open wire grille.
    for blade in range(5):
        def point(r,t):
            a=blade*math.tau/5+.57*t-.022*r
            return np.array((-43.4+(t-.5)*.85,7+r*math.cos(a),40+r*math.sin(a)))
        def normal(r,t):
            return K.normalise(np.cross(point(r+.001,t)-point(r-.001,t),point(r,t+.001)-point(r,t-.001)))
        for r0,r1 in zip((2.1,5.,8.),(5.,8.,10.7)):
            for t0,t1 in zip(np.linspace(0,1,5)[:-1],np.linspace(0,1,5)[1:]):
                points=[point(r0,t0),point(r1,t0),point(r1,t1),point(r0,t1)]
                normals=[normal(r0,t0),normal(r1,t0),normal(r1,t1),normal(r0,t1)]
                face(m,'ps_edge',points,sum(normals),normals=normals)
                face(m,'ps_edge',[p+X*.16 for p in points],-sum(normals),normals=[-n for n in normals])
    turned(m,(-44.1,7,40),-X,[(2.4,0),(2.2,.6),(1.6,.85)],'ps_metal',24)
    for offset in np.arange(-10.8,11.,1.5):
        half=math.sqrt(11.8**2-offset**2)
        tube(m,(-46.05,7-half,40+offset),(-46.05,7+half,40+offset),.16,'ps_edge',8)
    for offset in (-8.,-4.,0.,4.,8.):
        half=math.sqrt(11.8**2-offset**2)
        tube(m,(-46.2,7+offset,40-half),(-46.2,7+offset,40+half),.13,'ps_edge',8)
    ring(m,(-46.15,7,40),X,11.75,12.5,.75,'ps_metal',48)
    tube(m,(-.5,7,40),(14,7,40),3.8,'ps_metal',32)
    for x in (3,9):ring(m,(x,7,40),X,3.85,5.7,3.,'ps_gasket',32)
    # Perforated coupling guard: individual ribs leave real air gaps.
    for x in np.arange(1.0,12.,1.4):
        B.lathe(m,(x,7,40),X,[(6.2,0),(6.8,0),(6.8,.4),(6.2,.4),(6.2,0)],'ps_warning',sides=24)
    volute(m)
    for y in (-6.,20.):
        block(m,(22,y,17.05),(18,12,2.2),'ps_pump',1.2,.3)
        rings=[]
        for z,w,d in ((17.45,13.5,9.0),(18.25,13.5,9.0),(27.25,9.,7.0),(29.25,8.,6.6)):
            rings.append([np.array((22+p[0],y+p[1],z)) for p in O.outline(w,d,1.1,3)])
        for lower,upper in zip(rings,rings[1:]):
            for i in range(len(lower)):
                j=(i+1)%len(lower)
                points=[lower[i],lower[j],upper[j],upper[i]]
                face(m,'ps_pump',points,np.cross(points[1]-points[0],points[2]-points[0]))
        for sign,cap_points in ((-1,rings[0]),(1,rings[-1])):face(m,'ps_pump',cap_points,UP*sign)
        for x in (14.8,29.2):screw(m,(x,y,18.2),UP,.62,True)
    # Deep open suction socket, gasketed bolt flange and a bent discharge port.
    ring(m,(39,7,39),X,6.1,7.5,17,'ps_pump',48)
    flange(m,(45,7,39),X,6.1,10.3,2.8)
    ring(m,(48.15,7,39),X,6.1,7.8,1.2,'ps_metal',48)
    turned(m,(32,7,39),X,[(6.0,0),(6.0,.2)],'ps_dark',40)
    S.pipe_run(m,[(22,7,47),(22,7,65),(22,-20,65)],3.6,'ps_pump',24,6.0)
    m.polygons['ps_pump'].pop()  # Open outlet, rather than a painted cap in its mouth.
    flange(m,(22,-21.0,65),FRONT,3.05,7.5,2.)
    ring(m,(22,-23.0,65),FRONT,3.05,4.0,2.0,'ps_metal',40)
    ring(m,(22,-18,65),FRONT,3.05,3.15,10.,'ps_dark',32)
    turned(m,(22,-14,65),FRONT,[(2.95,0),(2.95,.2)],'ps_dark',32)
    # Pressure take-off, precision gauge, rolled bezel and a physical needle.
    S.pipe_run(m,[(22,-12,65),(2,-12,65),(2,-19,65)],.75,'ps_metal',12,2.3)
    turned(m,(2,-19,65),FRONT,[(5.7,0),(6.5,.8),(6.5,3.0),(6.15,3.5)],'ps_metal',48)
    ring(m,(2,-22.65,65),FRONT,5.5,6.35,.55,'ps_edge',48)
    plate(m,'ps_dial',(2,-23.0,65),10.8,10.8)
    # Dial corners sit behind a bezel; the circular face is actually clipped.
    dial_polys=m.polygons['ps_dial'];dial_polys.clear();m.polygon_uvs={k:v for k,v in m.polygon_uvs.items() if k[0]!='ps_dial'}
    pts=[];uv=[]
    for a in np.linspace(0,math.tau,64,endpoint=False):
        pts.append(np.array((2+5.4*math.cos(a),-23.,65+5.4*math.sin(a))))
        uv.append((.5+.5*math.cos(a),.5+.5*math.sin(a)))
    face(m,'ps_dial',pts,FRONT,uv=uv)
    p=np.array((2.,-23.12,65.));a=np.array((-.72,0,.69));side=np.cross(FRONT,a)
    face(m,'ps_dark',[p-side*.19-a*.9,p+side*.19-a*.9,p+a*4.15],FRONT)
    turned(m,p+FRONT*.03,FRONT,[(.45,0),(.45,.15)],'ps_metal',20)
    # Gasketed front controller with service seam, switches and legible ID plate.
    block(m,(-28,-17,59),(24,12,27),'ps_motor',1.3,.45)
    block(m,(-28,-23.15,59),(22.5,.6,25.5),'ps_gasket',1.,.12)
    block(m,(-28,-23.55,59),(21.6,.5,24.6),'ps_pump',.9,.13)
    block(m,(-28,-23.9,64),(17,.5,8),'ps_dark',.7,.12)
    plate(m,'ps_screen',(-28,-24.17,64),15.7,6.9)
    for x in (-36.,-20.):
        for z in (48.7,69.3):screw(m,(x,-23.85,z),FRONT,.38)
    for i,x in enumerate((-33.,-23.)):
        turned(m,(x,-23.95,53),FRONT,[(2.2,0),(2.2,.5)],'ps_dark',24)
        turned(m,(x,-24.5,53),FRONT,[(1.6,0),(1.6,.8),(1.25,1.0)],'ps_green' if i==0 else 'ps_red',24)
    label(m,0,(-28,-23.86,46.2),18.6,1.7)
    tube(m,(-36,-16,18),(-36,-16,46),1.1,'ps_edge',12)
    block(m,(-21,7,59),(13,14,7),'ps_motor',.8,.22)
    for x in (-25.,-17.):screw(m,(x,3.5,62.6),UP,.36)
    S.pipe_run(m,[(-28,-11,60),(-28,-5,60),(-27,0,61),(-21,0,61)],.85,'ps_rubber',12,3.)
    ring(m,(-28,-7,60),np.array((0,1,0)),.86,1.25,.65,'ps_metal',16)
    # Rear service plate, cable saddle and low drain valve make the rear worth viewing too.
    block(m,(-18,22.8,25),(28,1,9),'ps_edge',.5,.12)
    label(m,1,(-18,23.32,25),25,6.5,-X,UP)
    for x in (-30.,-6.):screw(m,(x,23.36,25),-FRONT,.4)
    S.pipe_run(m,[(24,18,25),(36,18,25),(36,18,20)],1.0,'ps_metal',12,2.)
    turned(m,(36,18,19),UP,[(2.1,0),(2.1,2.2),(1.4,3)],'ps_metal',16)
    block(m,(36,18,23.3),(7,1.2,1.1),'ps_red',.5,.15)
    # Sparse physical edge nicks expose metal; weld seams remain attached to joints.
    rng=np.random.default_rng(3010307)
    for x0,x1 in ((-46,-35),(-9,6),(29,44)):
        for x in np.linspace(x0,x1,5):
            w=float(rng.uniform(.35,1.1))
            plate(m,'ps_metal',(x,-26.515,11.8),w,.12,uv=[(0,0),(1,0),(1,1),(0,1)])
    for x in (-42.,42.):
        for y in (-22.,22.):
            for i in range(5):
                turned(m,(x-2.2+i*.45,y,14.7),UP,[(.3,0),(.38,.08),(.22,.2)],'ps_weld',8)
    block(m,(0,-26.50,8.4),(28,.2,3.7),'ps_edge',.3,.04)
    label(m,2,(0,-26.62,8.4),26,3.2)
    for x in (-13.3,13.3):screw(m,(x,-26.64,8.4),FRONT,.24)
    # Local traces of fluid on the tray, rather than cloudy noise over every surface.
    for cx,cy,r0 in ((-2.,-14.,3.0),(32.,-9.,2.1),(-37.,16.,1.4)):
        points=[]
        for i in range(28):
            a=i*math.tau/28;r=r0*(1+.10*math.sin(a*5)+.07*math.cos(a*9+.7))
            points.append((cx+r*math.cos(a),cy+r*.62*math.sin(a),15.974))
        for i in range(len(points)):
            face(m,'ps_oil',[(cx,cy,15.974),points[i],points[(i+1)%len(points)]],UP)
    for p in m.polygons:
        m.material_overrides[p]=f'{MAT}/{p}.vmat';m.tile_overrides[p]=12.
    m.box((-53,-29,3),(53,29,74),None,'plastic')
    return m

def materials():
    import ares_materials as AM
    MD.mkdir(parents=True,exist_ok=True);n=1024;rng=np.random.default_rng(3010307)
    y,x=np.mgrid[:n,:n]/n;noise=rng.normal(0,1,(n,n))
    grain=ndi.gaussian_filter(noise,.7,mode='wrap');grain/=grain.std()
    broad=ndi.gaussian_filter(noise,26,mode='wrap');broad/=broad.std()
    mid=ndi.gaussian_filter(noise,3,mode='wrap');mid/=mid.std()
    for name,base,rough,metal in (
        ('ps_pump',(67,101,94),.54,0.),('ps_motor',(65,78,82),.58,0.),
        ('ps_frame',(55,69,69),.60,0.),('ps_tray',(62,66,62),.61,.20),
        ('ps_edge',(91,98,96),.47,.75),('ps_metal',(137,141,134),.35,.9),
        ('ps_dark',(23,28,28),.69,0.),('ps_gasket',(32,35,32),.78,0.),
        ('ps_rubber',(37,39,35),.80,0.),('ps_warning',(179,139,53),.57,0.),
        ('ps_weld',(92,97,88),.52,.8),('ps_red',(142,37,25),.49,0.),('ps_green',(44,103,63),.46,0.),
        ('ps_oil',(43,46,38),.24,0.)):
        paint=metal<.5 and name not in ('ps_dark','ps_rubber','ps_gasket')
        colour=np.array(base)[None,None,:]*(1+.006*grain[...,None]+.009*broad[...,None]+.004*mid[...,None])
        roughness=np.clip(rough+.018*grain+.025*broad,.23,.94)
        cast=name in ('ps_pump','ps_motor')
        height=grain*(.00023 if cast else .000055)+mid*(.00007 if cast else .00002)
        if paint:
            pits=(grain>2.35)&(broad>.6);colour[pits]*=.83;roughness[pits]+=.07;height[pits]-=.0007
        if metal>.5:
            brush=ndi.gaussian_filter(noise,(.4,35),mode='wrap');brush/=brush.std()
            colour*=1+.010*brush[...,None];height+=brush*.000045;roughness+=brush*.028
        Image.fromarray(np.clip(colour,0,255).astype('uint8')).save(MD/(name+'_color.png'))
        AM.BX.save_grey(MD/(name+'_rough.png'),np.clip(roughness,.20,.95))
        AM.BX.save_normal(MD/(name+'_normal.png'),AM.normals(height,(n/12,n/12)))
        path=f'{MAT}/{name}'
        (MD/(name+'.vmat')).write_text(O.vmat(name,path+'_color.png',path+'_normal.png',path+'_rough.png',metal))
    dial=Image.new('RGB',(1024,1024),(219,216,191));d=ImageDraw.Draw(dial)
    for i in range(81):
        a=math.radians(135+270*i/80);r0=372 if i%10==0 else 407
        d.line((512+math.cos(a)*r0,512+math.sin(a)*r0,512+math.cos(a)*454,512+math.sin(a)*454),fill=(40,47,40),width=8 if i%10==0 else 3)
    for i in range(9):
        a=math.radians(135+270*i/8)
        d.text((512+math.cos(a)*320,512+math.sin(a)*320),str(i),font=ImageFont.truetype('C:/Windows/Fonts/arial.ttf',60),anchor='mm',fill=(43,50,45))
    for text,z,size in (('bar',610,50),('CP-07',693,30),('CLASS 1.6',739,25)):
        d.text((512,z),text,font=ImageFont.truetype('C:/Windows/Fonts/arial.ttf',size),anchor='mm',fill=(63,69,58))
    dial.save(MD/'dial_color.png');(MD/'ps_dial.vmat').write_text(O.vmat('ps_dial',f'{MAT}/dial_color.png',rough='[0.29 0.29 0.29 0]'))
    atlas=Image.new('RGB',(2048,1024),(190,190,167));d=ImageDraw.Draw(atlas)
    rows=[('COLLIDER SERVICES / CP-07','PUMP CONTROL  |  ISOLATE BEFORE SERVICE'),
          ('ELECTRIC DRIVE  /  37 kW','3~ 400 V   50 Hz     SERIAL 07-0426'),
          ('PROCESS PUMP / CP-07','INSPECT MOUNTS AND CONNECTIONS BEFORE USE'),
          ('SERVICE CONNECTION','DRAIN AND DEPRESSURISE BEFORE DISCONNECTING')]
    for i,(title,subtitle) in enumerate(rows):
        cy=i*256+128;d.rectangle((18,cy-109,2030,cy+109),outline=(67,75,64),width=4)
        d.text((1024,cy-33),title,font=ImageFont.truetype('C:/Windows/Fonts/arialbd.ttf',77),anchor='mm',fill=(32,45,39))
        d.text((1024,cy+52),subtitle,font=ImageFont.truetype('C:/Windows/Fonts/arial.ttf',42),anchor='mm',fill=(56,66,56))
    atlas.save(MD/'labels_color.png');(MD/'ps_label.vmat').write_text(O.vmat('ps_label',f'{MAT}/labels_color.png',rough='[0.65 0.65 0.65 0]'))
    screen=Image.new('RGB',(1024,512),(27,44,37));d=ImageDraw.Draw(screen)
    d.rounded_rectangle((10,10,1014,502),25,outline=(79,102,77),width=4)
    for text,position,size in (('LOCAL / RUN',(55,42),51),('047.2 Hz',(55,127),105),('PRESSURE   3.1 bar',(55,285),61),('DRIVE OK     FLOW OK',(55,400),44)):
        d.text(position,text,font=ImageFont.truetype('C:/Windows/Fonts/consola.ttf',size),fill=(159,187,136))
    screen.save(MD/'screen_color.png');(MD/'ps_screen.vmat').write_text(O.vmat('ps_screen',f'{MAT}/screen_color.png',rough='[0.27 0.27 0.27 0]'))

def protected():
    paths=[ROOT/'Assets/models/maps/collider'/f'collider_{name}{ext}'
           for name in ('structure','detail','machine','glass') for ext in ('.obj','.mtl','.vmdl')]
    paths+=[ROOT/'Assets/scenes/maps/Collider/collider.scene',ROOT/'Tools/collider_map.py',ROOT/'Tools/collider_machinery.py']
    for kind in ('models/props','materials'):
        paths.extend(p for p in (ROOT/'Assets'/kind/'collider').rglob('*')
                     if p.is_file() and 'trial-v1' in p.as_posix() and 'pump-skid-trial-v1' not in p.as_posix()
                     and p.suffix in ('.obj','.mtl','.vmdl','.vmat','.png'))
    return {p.relative_to(ROOT).as_posix():sha(p) for p in sorted(set(paths))}

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--refine',action='store_true');parser.add_argument('--geometry-only',action='store_true');args=parser.parse_args()
    if DEST.exists():
        assert args.refine,'Existing proposal needs explicit refinement'
        old=json.loads((OUT/'manifest.json').read_text())
        for path,h in old['protectedSourceSHA256'].items():assert sha(ROOT/path)==h,path
    guards=protected();before,provenance=baseline();after=candidate()
    for path in before.material_overrides.values():
        material=ROOT/'Assets'/path;guards['Assets/'+path]=sha(material)
        for tex in re.findall(r'Texture\w+\s+"([^"]+)"',material.read_text()):
            p=ROOT/'Assets'/tex
            if not tex.startswith('[') and p.is_file():guards['Assets/'+tex]=sha(p)
    OUT.mkdir(parents=True,exist_ok=True);DEST.mkdir(parents=True,exist_ok=True)
    if not args.geometry_only:materials()
    variants={}
    for name,model in (('before',before),('after',after)):
        K.write_obj(DEST/(name+'.obj'),model,name);K.write_vmdl(DEST/(name+'.vmdl'),RESOURCE,name,model)
        variants[name]={'triangles':model.triangle_count(),'meshSHA256':sha(DEST/(name+'.obj'))}
    for path,h in guards.items():assert sha(ROOT/path)==h,path
    result={'status':'candidate-only-not-installed','userApproved':False,'installedInMap':False,'editorUsed':False,
            'engineCompilation':'pending','baseline':provenance,'models':variants,'protectedSourceSHA256':guards,
            'originalRetained':True,'collisionBoxUnchanged':True,'fullObjectRebuilt':True,
            'newDetails':['finned motor and open rear fan guard','cast volute and deep open suction socket',
                          'gasketed eight-bolt flanges and bent outlet','working-scale dial with physical needle',
                          'sealed controller, labels and routed cable','isolation feet, channel frame and open drip tray',
                          'cast paint grain, physical coating nicks, brushed metal and localized grime'],
            'workload':{'priority':'idle','cpuAffinity':proc.cpu_affinity(),'BLASThreads':1}}
    for path in (OUT/'manifest.json',Path(__file__).parent/'candidate.json'):
        path.write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps({k:v for k,v in result.items() if k!='protectedSourceSHA256'}))

if __name__=='__main__':main()
