"""Isolated chair revision: actual mesh and engine PBR maps; never edits the installed chair."""
from pathlib import Path
import sys, math, json, hashlib, shutil
import numpy as np
from PIL import Image
from scipy.ndimage import gaussian_filter
from scipy.spatial import Delaunay

ROOT=Path(r'C:/sbox-projects/hc1/forked-shooter-main')
sys.path.insert(0,str(ROOT/'Tools'))
import map_kit as K
import collider_operators as O
from belltower_furniture import beam

WORK=Path(__file__).resolve().parent
STAGE=WORK/'candidate'
RESOURCE='models/props/collider/chair-realism-v2'
MATERIAL='materials/collider/chair-realism-v2'
DEST=STAGE/'Assets'/RESOURCE
MD=STAGE/'Assets'/MATERIAL
DEST.mkdir(parents=True,exist_ok=True);MD.mkdir(parents=True,exist_ok=True)
UP=np.array((0.,0.,1.))
TILES=dict(cloth=6.,welt=6.,thread=2.,polymer=6.,paint=8.,alloy=8.,rubber=4.,steel=5.)
for paint,tile in TILES.items(): O.TILES[paint]=tile

def normalise(v):
    length=np.linalg.norm(v)
    return v/length if length>1e-10 else UP.copy()

def soft(m,centre,size,paint,deform=None,power=.40,around=96,vertical=52):
    centre=np.array(centre,float);half=np.array(size,float)/2
    def sample(t,p):
        c=abs(math.cos(p))**power
        pt=half*np.array((c*O.signed_power(math.cos(t),power),c*O.signed_power(math.sin(t),power),O.signed_power(math.sin(p),power)))
        return pt if deform is None else deform(pt)
    def sn(t,p):
        h=.00005
        return normalise(np.cross(sample(t+h,p)-sample(t-h,p),sample(t,p+h)-sample(t,p-h)))
    rings=[]
    for j in range(1,vertical):
        p=-math.pi/2+math.pi*j/vertical
        rings.append([(sample(i*math.tau/around,p),sn(i*math.tau/around,p)) for i in range(around)])
    def emit(items):
        ps=[centre+p for p,n in items];ns=[n for p,n in items]
        n=normalise(sum(ns));axes=[i for i in range(3) if i!=int(np.argmax(np.abs(n)))]
        uv=[(p[axes[0]]/TILES[paint],p[axes[1]]/TILES[paint]) for p in ps]
        m.polygon(paint,ps,n,uv=uv,normals=ns)
    for a,b in zip(rings,rings[1:]):
        for i in range(around):
            j=(i+1)%around
            emit([a[i],a[j],b[j],b[i]])
    for sign,ring in ((-1,rings[0]),(1,rings[-1])):
        pt=sample(0,sign*math.pi/2)
        n=normalise(sum(sn(i*math.tau/around,sign*(math.pi/2-.00001)) for i in range(around)))
        for i in range(around):emit([(pt,n),ring[i],ring[(i+1)%around]])

def tailored_cushion(m,centre,size,deform,seat=False):
    """Two joined superellipsoid patches, with actual mesh rows at the stitched joins.

    Broad cloth panels get even sampling instead of polar topology, so narrow
    seam recesses and small compression folds survive in the exported mesh.
    """
    centre=np.array(centre,float);half=np.array(size,float)/2
    axes=(0,1) if seat else (0,2);depth=2 if seat else 1
    hx,hz=half[list(axes)];points=[]
    for z in np.arange(-hz+.12,hz,.34):
        limit=hx*max(0,1-abs(z/hz)**5)**.2
        xs=list(np.arange(-limit+.06,limit,.34))
        if not seat:
            factor=.93+.065*math.exp(-((z+3)/8)**2)
            xs += [(sign*6.65+offset)/factor for sign in (-1,1) for offset in (-.24,-.12,0,.12,.24)]
        for x in xs:
            if abs(x)<limit-.00001:points.append((x,z))
    for r in (.45,.75,.90,.96,.985,.996,.9995,1.):
        for i in range(256):
            t=i*math.tau/256
            points.append((hx*r*O.signed_power(math.cos(t),.4),hz*r*O.signed_power(math.sin(t),.4)))
    coords=np.unique(np.round(points,8),axis=0)
    triangles=Delaunay(coords).simplices
    for sign in (-1,1):
        positions=[];normals=[];uvs=[]
        for x,z in coords:
            p=np.zeros(3);p[axes[0]]=x;p[axes[1]]=z
            remaining=max(0,1-abs(x/hx)**5-abs(z/hz)**5)
            # The paired patches must meet at exactly zero depth. Rounding a
            # contour coordinate before a fifth root otherwise opens a tiny slit.
            p[depth]=0 if remaining<1e-6 else sign*half[depth]*remaining**.2
            n=np.sign(p)*np.abs(p/half)**4/half
            h=.00005
            jac=np.column_stack([(deform(p+np.eye(3)[i]*h)-deform(p-np.eye(3)[i]*h))/(2*h) for i in range(3)])
            n=normalise(np.linalg.solve(jac.T,n))
            positions.append(centre+deform(p.copy()));normals.append(n)
            # Carry UV distance around the rounded rim instead of projecting
            # the shoulder into a line on the broad panel's plane.
            distance=half[depth]-p[depth]
            u=x+np.sign(x)*distance*abs(x/hx)**4
            v=z+np.sign(z)*distance*abs(z/hz)**4
            uvs.append((u/6,v/6))
        for tri in triangles:
            ps=[positions[i] for i in tri];ns=[normals[i] for i in tri]
            quantized=np.round(ps,3)
            if np.linalg.norm(np.cross(quantized[1]-quantized[0],quantized[2]-quantized[0]))<=2e-10:
                continue
            m.polygon('cloth',ps,normalise(sum(ns)),uv=[uvs[i] for i in tri],normals=ns)

def path_tube(m,path,radius,paint,sides=8,closed=False):
    # Continuous swept tube, no overlapping cylinders at each curve segment.
    path=np.array(path);count=len(path);rings=[]
    for i,p in enumerate(path):
        tangent=normalise(path[(i+1)%count]-path[(i-1)%count]) if closed else normalise(path[min(i+1,count-1)]-path[max(i-1,0)])
        u=normalise(np.cross(tangent,UP if abs(tangent[2])<.85 else (0,1,0)))
        v=np.cross(tangent,u)
        rings.append([(p+radius*(u*math.cos(a*math.tau/sides)+v*math.sin(a*math.tau/sides)),u*math.cos(a*math.tau/sides)+v*math.sin(a*math.tau/sides)) for a in range(sides)])
    for i in range(count if closed else count-1):
        j=(i+1)%count
        for a in range(sides):
            b=(a+1)%sides;items=[rings[i][a],rings[i][b],rings[j][b],rings[j][a]]
            ps=[x for x,n in items];ns=[n for x,n in items]
            m.polygon(paint,ps,normalise(sum(ns)),normals=ns)
    if not closed:
        for i,sgn in ((0,-1),(count-1,1)):
            ps=[x for x,n in rings[i]]
            m.polygon(paint,ps,sgn*normalise(path[min(i+1,count-1)]-path[max(i-1,0)]))

def stitch(m,path,normal):
    # Actual, individually separated small thread loops along the seam.
    for i in range(0,len(path)-1,2):
        a=np.array(path[i]);b=np.array(path[min(i+1,len(path)-1)])
        mid=(a+b)/2+normal*.016
        path_tube(m,[a,mid,b],.012,'thread',5)

def seat_shape(p):
    x,y,z=p
    up=max(0,z/1.9)
    compression=.43*math.exp(-(x/7.2)**2-((y+1)/7.5)**2)
    edge=math.exp(-((abs(x)-9.2)/1.4)**2)
    folds=.065*edge*math.sin(y*2.5+.3*x)*math.exp(-((y+1)/8)**2)
    p[2]-=compression*up+y*.025
    p[2]+=folds*up
    return p

def back_shape(p):
    x,y,z=p
    front=max(0,y/1.6)
    # Slight shoulder taper and a relaxed lumbar roll in the foam.
    p[0]*=.93+.065*math.exp(-((z+3)/8)**2)
    p[1]+=.95*math.exp(-((z+6)/4.4)**2)*front-.115*z
    seams=sum(math.exp(-((p[0]-sx)/.15)**2) for sx in (-6.65,6.65))
    p[1]-=.080*seams*front*math.exp(-(z/13)**8)
    lower_fold=.055*math.sin(p[0]*2.4)*math.exp(-((z+10.8)/1.4)**2)
    p[1]+=lower_fold*front
    return p

m=K.Model()
tailored_cushion(m,(0,0,21.3),(22,21,3.8),seat_shape,True)
tailored_cushion(m,(0,-9.4,36.5),(21.8,3.2,26),back_shape)
soft(m,(0,-11.35,36.5),(20.9,1.15,25.8),'polymer',lambda p:p+np.array((0,-.115*p[2],0)),power=.28,around=64,vertical=32)
soft(m,(0,-.2,19.4),(21.1,19.4,1.25),'polymer',power=.30,around=64,vertical=24)

# Seat perimeter welt and a close, visible lockstitch.
path=[];threadpath=[]
for i in range(240):
    t=i*math.tau/240;p=.20;c=math.cos(p)**.4
    pt=seat_shape(np.array((11*c*O.signed_power(math.cos(t),.4),10.5*c*O.signed_power(math.sin(t),.4),1.9*O.signed_power(math.sin(p),.4))))
    path.append(pt+np.array((0,0,21.3)))
    threadpath.append(pt*np.array((.985,.985,1))+np.array((0,0,21.39)))
path_tube(m,path,.055,'welt',8,True)
stitch(m,threadpath+[threadpath[0]],UP)

# Back perimeter follows the actual bent foam, with twin fitted-panel seams.
bp=[];bt=[]
for i in range(240):
    t=i*math.tau/240
    x=10.9*.973*O.signed_power(math.cos(t),.4)
    z=13*.973*O.signed_power(math.sin(t),.4)
    y=1.6*max(0.,1-(abs(x)/10.9)**5-(abs(z)/13)**5)**.2
    p=back_shape(np.array((x,y+.01,z)))+np.array((0,-9.4,36.5))
    bp.append(p);bt.append(p+np.array((-.10*np.sign(x),.025,-.10*np.sign(z))))
path_tube(m,bp,.050,'welt',8,True)
stitch(m,bt+[bt[0]],np.array((0,1,0)))
for sx in (-6.65,6.65):
    p=[]
    for z in np.linspace(-10.9,11.3,146):
        x=sx/(.93+.065*math.exp(-((z+3)/8)**2))
        y=1.6*max(0.,1-(abs(x)/10.9)**5-(abs(z)/13)**5)**.2
        q=back_shape(np.array((x,y,z)))+np.array((0,-9.4,36.5))
        p.append(q+np.array((0,.035,0)))
    # Stitching sits beside the recessed panel join rather than floating above it.
    stitch(m,[q+np.array((.105,0,0)) for q in p],np.array((0,1,0)))

# Articulated under-seat carrier, fasteners, locking lever and ribbed tension wheel.
O.round_block(m,(0,-1,17.3),(11.8,11,2.7),'paint',1.5,.25,segments=6)
beam(m,(0,-6.5,17.9),(0,-11,30),(3.2,1.5),'paint',.25)
O.turned(m,(0,5,16.8),(0,1,0),[(1.1,0),(1.37,.18),(1.37,2),(1.1,2.28)],'polymer',48)
for i in range(24):
    a=i*math.tau/24
    O.tube(m,(1.34*math.cos(a),5.3,16.8+1.34*math.sin(a)),(1.34*math.cos(a),6.85,16.8+1.34*math.sin(a)),.065,'polymer',6)
beam(m,(-4,1,17.7),(-9,3.3,17.4),(.45,.35),'paint',.07)
soft(m,(-9.3,3.4,17.4),(1.6,3,.65),'polymer',around=40,vertical=18)
for x in (-4.4,4.4):
    for y in (-4.5,2.5):O.button(m,(x,y,15.92),(0,0,-1),.26,'steel',12)
O.turned(m,(0,0,5.7),UP,[(1.14,0),(1.14,12.8)],'steel',48)
O.turned(m,(0,0,4.1),UP,[(1.8,0),(1.8,6.8),(1.65,7)],'polymer',48)
for z in (5.0,7.6,10.65):
    O.turned(m,(0,0,z),UP,[(1.81,0),(1.82,.09),(1.81,.18)],'polymer',48)
O.turned(m,(0,0,3.6),UP,[(2.5,0),(2.7,.5),(2.1,2.5)],'alloy',48)

for sign in (-1,1):
    beam(m,(sign*10,-.5,18.9),(sign*13.6,-.3,26.6),(1.3,1.1),'alloy',.22)
    O.round_block(m,(sign*13.6,-.3,27.4),(1.5,2.2,4.2),'polymer',.45,.15,segments=6)
    soft(m,(sign*13.6,.2,30.2),(3.3,11.5,1.65),'polymer',power=.42,around=64,vertical=28)
    # Injection-molded parting line and adjustment ratchet below each arm pad.
    O.button(m,(sign*14.45,-.1,27.9),(sign,0,0),.32,'paint',24)
    O.button(m,(sign*14.56,-.1,27.9),(sign,0,0),.12,'steel',6)
    for z in (26.3,26.8,27.3,27.8):
        O.round_block(m,(sign*13.6,.84,z),(.62,.13,.11),'paint',.04,.02,segments=2)

def spoke(angle):
    along=np.array((math.cos(angle),math.sin(angle),0));across=np.array((-along[1],along[0],0))
    rings=[]
    for t in np.linspace(0,1,26):
        radius=1.8+12.3*t
        width=1.55*(1-t)+.72*t
        height=.76*(1-t)+.52*t
        z=5.12-1.02*t+.13*math.sin(math.pi*t)
        ring=[]
        for j in range(12):
            a=j*math.tau/12
            side=width*O.signed_power(math.cos(a),.40)
            up=height*O.signed_power(math.sin(a),.40)
            ring.append(along*radius+across*side+UP*(z+up))
        rings.append(ring)
    rns=[]
    for i,ring in enumerate(rings):
        row=[]
        for j in range(12):
            dt=rings[min(i+1,len(rings)-1)][j]-rings[max(i-1,0)][j]
            around=ring[(j+1)%12]-ring[(j-1)%12]
            row.append(normalise(np.cross(around,dt)))
        rns.append(row)
    for i,(ra,rb) in enumerate(zip(rings,rings[1:])):
        for j in range(12):
            k=(j+1)%12;pts=[ra[j],ra[k],rb[k],rb[j]]
            n=normalise(np.cross(pts[1]-pts[0],pts[2]-pts[0]))
            m.polygon('alloy',pts,n,normals=[rns[i][j],rns[i][k],rns[i+1][k],rns[i+1][j]])
    for ra,s in ((rings[0],-1),(rings[-1],1)):m.polygon('alloy',ra,s*along)
    return along,across

for i in range(5):
    a=i*math.tau/5+.26;along,axle=spoke(a)
    tip=along*14.1+UP*4.2
    O.turned(m,tip-UP*.6,UP,[(.50,0),(.50,.95)],'steel',32)
    wheelc=along*14.55+UP*1.5
    beam(m,tip,wheelc+UP*.55,(.9,.7),'paint',.12)
    for sign in (-1,1):
        c=wheelc+axle*sign*.63
        O.turned(m,c-axle*.43,axle,[(1.20,0),(1.47,.14),(1.50,.28),(1.50,.58),(1.47,.72),(1.20,.86)],'rubber',48)
        O.turned(m,c+axle*sign*.435,axle*sign,[(1.15,0),(1.21,.055),(1.13,.13),(.44,.16)],'polymer',48)
        O.button(m,c+axle*sign*.625,axle*sign,.35,'steel',16)
        O.button(m,c+axle*sign*.755,axle*sign,.14,'paint',6)

# Export in precisely the orientation of the saved after.obj.
m=O.transform(m,(0,0,0),np.diag((-1.,-1.,1.)))
for paint,polygons in m.polygons.items():
    for index,(points,normal) in enumerate(polygons):
        geometric=np.cross(points[1]-points[0],points[2]-points[0])
        if np.dot(geometric,normal)<0:
            polygons[index]=(points[::-1],normal)
            if (paint,index) in m.polygon_uvs:m.polygon_uvs[(paint,index)].reverse()
            if (paint,index) in m.polygon_normals:m.polygon_normals[(paint,index)].reverse()
m.box((-22,-23,0),(22,23,52),None,'metal')
for paint in m.polygons:
    m.material_overrides[paint]=f'{MATERIAL}/{paint}.vmat'
    m.tile_overrides[paint]=TILES[paint]
tris=K.write_obj(DEST/'after.obj',m,'after')
K.write_vmdl(DEST/'after.vmdl',RESOURCE,'after',m)

# Original, physically scaled, seamless PBR texture synthesis.
n=2048;rng=np.random.default_rng(210113)
y,x=np.mgrid[:n,:n].astype(np.float32)/n
noise=rng.normal(0,1,(n,n)).astype(np.float32)
broad=gaussian_filter(noise,32,mode='wrap');broad/=broad.std()
def save(paint,color,height,rough,metal):
    c=np.broadcast_to(np.clip(color,0,255),(n,n,3)).astype(np.uint8)
    Image.fromarray(c).save(MD/f'{paint}_color.png')
    h=np.broadcast_to(height,(n,n))
    dx=(np.roll(h,-1,1)-np.roll(h,1,1))*(n/TILES[paint])/2
    dy=(np.roll(h,-1,0)-np.roll(h,1,0))*(n/TILES[paint])/2
    norm=np.stack((-dx,-dy,np.ones_like(dx)),axis=-1);norm/=np.linalg.norm(norm,axis=-1,keepdims=True)
    Image.fromarray(np.round((norm*.5+.5)*255).astype(np.uint8)).save(MD/f'{paint}_normal.png')
    Image.fromarray(np.broadcast_to(np.clip(np.asarray(rough)*255,0,255),(n,n)).astype(np.uint8)).save(MD/f'{paint}_rough.png')
    path=f'{MATERIAL}/{paint}'
    (MD/f'{paint}.vmat').write_text(O.vmat(paint,path+'_color.png',path+'_normal.png',path+'_rough.png',metal))

# Interlaced yarn bundles with random fibre/yarn colour, no broad artificial grunge.
threads=160
tx=x*threads;ty=y*threads
sx=np.sin(math.tau*tx);sy=np.sin(math.tau*ty)
over=((np.floor(tx)+np.floor(ty))%2)==0
warp=np.sqrt(np.maximum(0,1-(2*(tx%1)-1)**2))
weft=np.sqrt(np.maximum(0,1-(2*(ty%1)-1)**2))
weave=np.where(over,.78*warp+.22*weft,.22*warp+.78*weft)
fiber=.45*np.sin(math.tau*(tx*4+ty*.12))+.45*np.sin(math.tau*(ty*4+tx*.1))
yarnx=rng.normal(0,1,threads)[np.minimum(np.floor(tx).astype(int),threads-1)]
yarny=rng.normal(0,1,threads)[np.minimum(np.floor(ty).astype(int),threads-1)]
variation=.16*(weave-.7)+.018*(yarnx+yarny)+.008*noise+.006*broad
color=np.array((64.,69.,75.))[None,None,:]*(1+variation[...,None])
height=.0030*(weave-.65)+.00015*fiber+.00006*noise
save('cloth',color,height,np.clip(.86+.035*(1-weave)+.012*noise,.78,.96),0)
save('welt',np.array((34.,38.,43.))[None,None,:]*(1+.035*noise[...,None]),height*.55,.83,0)
save('thread',np.array((89.,94.,99.))[None,None,:]*(1+.04*noise[...,None]),.0005*noise,.86,0)
pebble=gaussian_filter(noise,1.4,mode='wrap');pebble/=pebble.std()
save('polymer',np.array((34.,38.,42.))[None,None,:]*(1+.025*pebble[...,None]),.0011*pebble,np.clip(.58+.025*pebble,.48,.7),0)
save('paint',np.array((38.,42.,46.))[None,None,:]*(1+.018*noise[...,None]),.00045*pebble,.47+.015*pebble,0)
brush=gaussian_filter(noise,(.7,18),mode='wrap');brush/=brush.std()
save('alloy',np.array((169.,174.,178.))[None,None,:]*(1+.002*brush[...,None]),.000008*brush,.27+.007*brush,.94)
save('steel',np.array((187.,191.,195.))[None,None,:]*(1+.002*brush[...,None]),.000005*brush,.20+.006*brush,.98)
save('rubber',np.array((24.,26.,28.))[None,None,:]*(1+.035*pebble[...,None]),.0008*pebble,.76+.025*pebble,0)

baseline=WORK/'baseline'
for folder in ('models/props/collider/chair-trial-v1','materials/collider/chair-trial-v1'):
    shutil.copytree(baseline/folder,STAGE/'Assets'/folder,dirs_exist_ok=True)
report={'status':'isolated-review-candidate','installed':False,'resource':RESOURCE+'/after.vmdl','triangles':tris,'materials':sorted(m.polygons),'renderer':'actual OBJ and PBR texture maps','nativeEngineValidated':False,'baselineResource':'models/props/collider/chair-trial-v1/after.vmdl','notes':['Tailored anthracite textile with interlaced yarn maps','Sculpted lumbar and seat compression; subtle edge folds','Inset panel seams with individual lockstitches and continuous welts','Curved cast spokes, distinct rubber tyres, molded wheel hubs and fixings','Ribbed tilt tension control, arm adjustments and gas-lift collars']}
(STAGE/'candidate.json').write_text(json.dumps(report,indent=2))
print(json.dumps(report))
