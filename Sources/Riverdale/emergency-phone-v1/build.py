"""Private emergency-phone proposal; published Riverdale sources are read-only."""
import os
for name in ('OPENBLAS_NUM_THREADS','OMP_NUM_THREADS','MKL_NUM_THREADS'):os.environ[name]='1'
import psutil
p=psutil.Process();p.nice(psutil.IDLE_PRIORITY_CLASS);p.cpu_affinity(p.cpu_affinity()[-2:])
from pathlib import Path
from collections import Counter,defaultdict
import hashlib,json,math,re,sys
import numpy as np
from scipy.ndimage import gaussian_filter
from PIL import Image,ImageDraw,ImageFont
ROOT=Path(__file__).resolve().parents[3];sys.path.insert(0,str(ROOT/'Tools'))
import map_kit as K,riverdale_hall as H,riverdale_map as R,collider_operators as O,ares_materials as AM
from belltower_furniture import face
HERE=Path(__file__).parent;OUT=ROOT/'output/riverdale-emergency-phone-review-20261031'
RESOURCE='models/props/riverdale/emergency-phone-v1';MAT='materials/riverdale/emergency-phone-v1'
STAGE=OUT/'stage/Assets';DEST=STAGE/RESOURCE;MD=STAGE/MAT
X=np.array((1.,0.,0.));UP=np.array((0.,0.,1.));FRONT=np.array((0.,-1.,0.));AXES=np.array((X,UP,FRONT))
ORIGIN=np.array((1000.,340.,45.));BASIS=np.array(((0.,-1.,0.),(1.,0.,0.),(0.,0.,1.)))
LO=np.array((-5.,-6.2,-3.7));HI=np.array((5.,.5,18.2))
PAINTS={'ep_yellow':((185,135,30),.53,0.),'ep_black':((30,32,31),.56,0.),
        'ep_metal':((153,155,151),.37,.88),'ep_dark':((17,20,21),.68,0.),'ep_red':((134,10,5),.25,0.)}
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
def block(m,c,size,paint='ep_yellow',r=.16,b=.04):O.round_block(m,np.asarray(c),size,paint,r,b,axes=AXES,segments=12)
def cylinder(m,c,axis,profile,paint='ep_metal',sides=32):O.turned(m,np.asarray(c),np.asarray(axis),profile,paint,sides)
def screw(m,x,z,y=-3.84):
    cylinder(m,(x,y,z),FRONT,[(.17,0),(.17,.045),(.125,.11)],sides=24)
    block(m,(x,y-.12,z),(.16,.028,.012),'ep_dark',.009,.003)
def card(m,c,w,h,index):
    x,y,z=c;row,col=divmod(index,4);u0,u1=(col+.015)/4,(col+.985)/4;v0,v1=1-(row+.985)/4,1-(row+.015)/4
    face(m,'ep_print',[(x-w/2,y,z-h/2),(x+w/2,y,z-h/2),(x+w/2,y,z+h/2),(x-w/2,y,z+h/2)],FRONT,
         uv=[(u0,v0),(u1,v0),(u1,v1),(u0,v1)])
def handset(m):
    profile=[(1.20,.40,.35,-4.75),(1.32,.75,.60,-4.85),(1.60,1.02,.77,-4.93),
             (2.05,1.10,.82,-4.96),(2.55,1.00,.75,-4.88),(3.05,.78,.62,-4.68),
             (3.55,.59,.52,-4.48),(4.5,.54,.50,-4.43),(6.5,.52,.50,-4.53),
             (8.5,.54,.50,-4.43),(9.45,.59,.52,-4.48),(9.95,.78,.62,-4.68),
             (10.45,1.,.75,-4.88),(10.95,1.10,.82,-4.96),(11.40,1.02,.77,-4.93),
             (11.68,.75,.60,-4.85),(11.80,.40,.35,-4.75)]
    # A continuous moulded receiver; interpolate its profile with shape-preserving splines.
    from scipy.interpolate import PchipInterpolator
    knots=np.array(profile);zs=np.linspace(knots[0,0],knots[-1,0],70)
    curves=[PchipInterpolator(knots[:,0],knots[:,i]) for i in (1,2,3)]
    def sample(z,a):return np.array((-2.15+curves[0](z)*math.cos(a),curves[2](z)+curves[1](z)*math.sin(a),z))
    rings=[];normals=[];count=48
    for z in zs:
        ring=[];ns=[]
        for i in range(count):
            a=i*math.tau/count;pos=sample(z,a);t=(sample(z,a+.001)-sample(z,a-.001))/.002
            lo=max(zs[0],z-.001);hi=min(zs[-1],z+.001);dz=(sample(hi,a)-sample(lo,a))/(hi-lo)
            ring.append(pos);ns.append(K.normalise(np.cross(t,dz)))
        rings.append(ring);normals.append(ns)
    for j in range(len(zs)-1):
        for i in range(count):
            k=(i+1)%count;points=[rings[j][i],rings[j][k],rings[j+1][k],rings[j+1][i]]
            ns=[normals[j][i],normals[j][k],normals[j+1][k],normals[j+1][i]]
            face(m,'ep_black',points,K.normalise(sum(ns)),normals=ns)
    face(m,'ep_black',rings[0],-UP);face(m,'ep_black',rings[-1],UP)
    # Fine mould parting line follows the receiver's side, rather than a painted flat stripe.
    for sign in (-1,1):
        points=[sample(z,0 if sign>0 else math.pi) for z in zs]
        for a,b in zip(points,points[1:]):O.tube(m,a,b,.012,'ep_dark',6)
    for z in (2.0,11.0):
        cylinder(m,(-2.15,-5.76,z),FRONT,[(.54,0),(.57,.045),(.51,.095)],'ep_dark',48)
        for dx,dz in [(0,0)]+[(.28*math.cos(a),.28*math.sin(a)) for a in np.linspace(0,math.tau,8,endpoint=False)]:
            cylinder(m,(-2.15+dx,-5.87,z+dz),FRONT,[(.052,0),(.045,.017)],'ep_black',12)
    # Cradle arms are separate from the receiver, with a visible shadow gap.
    for z in (2.8,10.2):
        block(m,(-2.15,-3.83,z),(2.1,.60,.72),'ep_dark',.18,.06)
        for x in (-3.10,-1.20):block(m,(x,-4.25,z),(.24,.55,.50),'ep_black',.1,.035)
def cable(m):
    c=np.array([(-2.15,-4.8,1.2),(-2.8,-5.4,-4.1),(3.8,-2.8,-4.1),(2.8,-1.8,-.05)])
    def bez(t):return (1-t)**3*c[0]+3*(1-t)**2*t*c[1]+3*(1-t)*t*t*c[2]+t**3*c[3]
    points=[]
    for t in np.linspace(0,1,520):
        lo=max(0,t-.001);hi=min(1,t+.001);tangent=K.normalise(bez(hi)-bez(lo))
        u=K.normalise(np.cross(tangent,(0,1,0)));v=np.cross(tangent,u)
        radius=.225*min(1,t*20,(1-t)*20);a=math.tau*24*t
        points.append(bez(t)+radius*(u*math.cos(a)+v*math.sin(a)))
    # Continuous sweep, no segmented open ends or angular cord bends.
    rings=[]
    for i,p in enumerate(points):
        tangent=K.normalise(points[min(i+1,len(points)-1)]-points[max(0,i-1)])
        u=K.normalise(np.cross(tangent,(0,1,0)));v=np.cross(tangent,u)
        rings.append([(p+.064*(u*math.cos(a)+v*math.sin(a)),u*math.cos(a)+v*math.sin(a)) for a in np.linspace(0,math.tau,8,endpoint=False)])
    for ra,rb in zip(rings,rings[1:]):
        for i in range(8):
            j=(i+1)%8;q=[ra[i],ra[j],rb[j],rb[i]]
            face(m,'ep_black',[p for p,n in q],K.normalise(sum(n for p,n in q)),normals=[n for p,n in q])
    face(m,'ep_black',[p for p,n in rings[0]],points[0]-points[1]);face(m,'ep_black',[p for p,n in rings[-1]],points[-1]-points[-2])
    for c in ((-2.15,-4.8,1.2),(2.8,-1.8,0)):
        cylinder(m,c,-UP,[(.29,0),(.29,.12),(.21,.25),(.17,.5)],'ep_black',24)
        for z in (.10,.19,.28):cylinder(m,np.asarray(c)-UP*z,-UP,[(.23,0),(.23,.045)],'ep_dark',20)
def candidate():
    m=K.Model()
    # Backplate, rounded die-cast shell, compressed gasket and separate opening front cover.
    block(m,(0,-.16,7),(9.45,14.25,.30),'ep_metal',.48,.06)
    block(m,(0,-1.64,7),(9.,13.8,2.95),'ep_yellow',.58,.14)
    block(m,(0,-3.18,7),(8.84,13.65,.14),'ep_dark',.56,.035)
    block(m,(0,-3.42,7),(8.92,13.7,.40),'ep_yellow',.56,.10)
    # External hinge leaves and hinge pin communicate a manufacturable sealed enclosure.
    for z in (3.0,10.8):
        for x in (4.35,):
            cylinder(m,(x,-2.85,z-.75),UP,[(.24,0),(.24,1.5)],'ep_metal',28)
            block(m,(4.13,-3.38,z),(.58,1.2,.12),'ep_yellow',.10,.025)
    for x in (-3.85,3.85):
        for z in (.75,13.25):screw(m,x,z,-3.64)
    # A raised stainless keypad bezel with recessed membrane, display and individual sealed keys.
    block(m,(1.65,-3.68,6.7),(3.65,6.65,.22),'ep_metal',.23,.055)
    block(m,(1.65,-3.83,6.7),(3.32,6.31,.13),'ep_dark',.16,.035)
    block(m,(1.65,-3.94,8.65),(2.92,1.20,.10),'ep_black',.11,.025)
    card(m,(1.65,-4.005,8.65),2.70,.93,14)
    for row in range(4):
        for col in range(3):
            x=.72+col*.93;z=7.30-row*.92
            block(m,(x,-3.96,z),(.77,.72,.13),'ep_black',.09,.025)
            block(m,(x,-4.075,z),(.66,.61,.14),'ep_metal',.10,.035)
            card(m,(x,-4.152,z),.54,.49,row*3+col)
    for x in (.13,3.17):
        for z in (3.72,9.68):screw(m,x,z,-3.83)
    card(m,(.2,-3.635,12.05),6.6,1.12,12)
    card(m,(1.5,-3.635,1.65),4.25,1.10,13)
    card(m,(1.75,-3.635,10.45),3.25,.60,15)
    handset(m);cable(m)
    # Modest red lens, retaining ring, visible lens flutes and a protective metal cage.
    cylinder(m,(0,-1.75,13.9),UP,[(1.40,0),(1.40,.25),(1.15,.40)],'ep_black',48)
    cylinder(m,(0,-1.75,14.3),UP,[(1.09,0),(1.09,1.55),(1.02,1.80),(.78,2.05),(.38,2.20)],'ep_red',64)
    for a in np.linspace(0,math.tau,32,endpoint=False):
        xy=np.array((1.096*math.cos(a),1.096*math.sin(a),0));O.tube(m,(0,-1.75,14.5)+xy,(0,-1.75,15.8)+xy,.017,'ep_red',6)
    for z,r in ((14.45,1.33),(16.1,1.20)):
        # A ring made by a closed sweep of short smooth cylinders.
        pts=[np.array((r*math.cos(a),-1.75+r*math.sin(a),z)) for a in np.linspace(0,math.tau,49)]
        for a,b in zip(pts,pts[1:]):O.tube(m,a,b,.055,'ep_metal',8)
    for a in np.linspace(0,math.tau,4,endpoint=False):
        O.tube(m,(1.33*math.cos(a),-1.75+1.33*math.sin(a),14.45),(1.20*math.cos(a),-1.75+1.20*math.sin(a),16.1),.075,'ep_metal',12)
    # Close-fitting collision: shell, receiver grip/end caps and beacon; cord remains nonblocking.
    points=[(x,-d,z) for d in (.1,3.62) for x,z in O.outline(8.9,13.7,.55,segments=2)]
    # The outline's second coordinate is vertical about the housing centre.
    m.hull([(x,y,z+7) for x,y,z in points],'metal')
    m.collision_box((-2.75,-5.10,3.0),(-1.55,-3.95,10.0),'plastic')
    for z in (2.,11.):m.hull([(-2.15+1.06*math.cos(a),-4.96+.78*math.sin(a),z+zz) for zz in (-.60,.60) for a in np.linspace(0,math.tau,8,endpoint=False)],'plastic')
    m.hull([(1.1*math.cos(a),-1.75+1.1*math.sin(a),z) for z in (14.3,16.3) for a in np.linspace(0,math.tau,8,endpoint=False)],'plastic')
    assign_uv(m)
    for paint in m.polygons:m.material_overrides[paint]=f'{MAT}/{paint}.vmat';m.tile_overrides[paint]=12.
    return m
def assign_uv(m):
    for paint in PAINTS:
        for i,(pts,n) in enumerate(m.polygons[paint]):
            axis=int(np.argmax(abs(n)));chart=axis*2+int(n[axis]<0);u,v=[j for j in range(3) if j!=axis]
            m.polygon_uvs[(paint,i)]=[((chart%3+.025+.95*(p[u]-LO[u])/(HI[u]-LO[u]))/3,1-(chart//3+.025+.95*(p[v]-LO[v])/(HI[v]-LO[v]))/2) for p in pts]
def baseline():
    a=K.Model();b=K.Model();H.wall_phone(a,b,H.Face((1000,0),(-1,0)),H.Face((1000,0),(-1,0)).s_of(1000,340),52)
    expected=Counter()
    def key(p,pts):return p,tuple(sorted(tuple(np.round(q,3)) for q in pts))
    for model in (a,b):
        for paint,polys in model.polygons.items():
            for pts,n in polys:
                for i in range(1,len(pts)-1):expected[key(paint,[pts[0],pts[i],pts[i+1]])]+=1
    model=K.Model();orig=[]
    for filename in ('riverdale_hall_detail','riverdale_hall_dress','riverdale_hall_fine'):
        path=ROOT/f'Assets/models/maps/riverdale/{filename}.obj';vs=[];ts=[];ns=[];paint=''
        for line in path.read_text().splitlines():
            if line.startswith('v '):
                x,z,n=map(float,line.split()[1:]);vs.append(np.array((-x,n,z)))
            elif line.startswith('vt '):ts.append(tuple(map(float,line.split()[1:])))
            elif line.startswith('vn '):
                x,z,n=map(float,line.split()[1:]);ns.append(np.array((-x,n,z)))
            elif line.startswith('usemtl '):paint=line[7:]
            elif line.startswith('f '):
                ids=[[int(v)-1 for v in t.split('/')] for t in line.split()[1:]];pts=[vs[v] for v,t,n in ids];k=key(paint,pts)
                if expected[k]:
                    expected[k]-=1;model.polygon(paint,[(q-ORIGIN)@BASIS.T for q in pts],uv=[ts[t] for v,t,n in ids],normals=[ns[n]@BASIS.T for v,t,n in ids]);orig.append(filename)
    assert not +expected,('Saved phone does not match expected triangles',sum((+expected).values()))
    assert model.triangle_count()==126
    R.configure(model);return model,dict(Counter(orig))
def materials(m):
    n=2048;rng=np.random.default_rng(71031)
    for paint,(base,rough,metal) in PAINTS.items():
        edges=defaultdict(list)
        for i,(pts,normal) in enumerate(m.polygons[paint]):
            uv=m.polygon_uvs[(paint,i)]
            for j,p in enumerate(pts):
                k=(j+1)%len(pts);key=tuple(sorted((tuple(np.round(p,4)),tuple(np.round(pts[k],4)))))
                edges[key].append((normal,uv[j],uv[k]))
        wear=Image.new('L',(n,n));draw=ImageDraw.Draw(wear)
        for records in edges.values():
            if len(records)==2 and records[0][0]@records[1][0]>.94:continue
            for normal,a,b in records:draw.line((a[0]*n,(1-a[1])*n,b[0]*n,(1-b[1])*n),fill=210,width=2)
        edge=gaussian_filter(np.asarray(wear,dtype=np.float32)/255,.9)
        noise=rng.normal(0,1,(n,n)).astype('float32');fine=gaussian_filter(noise,.6);fine/=fine.std();mid=gaussian_filter(noise,5);mid/=mid.std()
        chips=np.clip(edge*1.9*np.clip(mid*.6+fine*.2+.15,0,1),0,.85) if paint=='ep_yellow' else np.zeros_like(edge)
        scuffs=Image.new('L',(n,n));d=ImageDraw.Draw(scuffs)
        for _ in range(150 if paint=='ep_yellow' else 400):
            x,y=rng.uniform(0,n,2);d.line((x,y,x+rng.uniform(1,15),y+rng.uniform(-2,2)),fill=int(rng.uniform(10,40)),width=1)
        sc=np.asarray(scuffs,dtype=np.float32)/255
        c=np.array(base,dtype=float)[None,None,:]*(1+.009*fine[...,None]+.007*mid[...,None])
        c=c*(1-chips[...,None])+np.array((104,101,89))*chips[...,None];c*=1-.10*sc[...,None]
        rr=np.clip(rough+.018*fine+.018*mid-.12*chips+.12*sc,.19,.93)
        mm=np.clip(metal+.8*chips,0,.94)
        bump=fine*(.00011 if paint=='ep_yellow' else .000035)-chips*.0014-sc*.0003
        normals=np.empty((n,n,3),np.uint8)
        for chart in range(6):
            axis=chart//2;u,v=[j for j in range(3) if j!=axis];row,col=divmod(chart,3)
            y0,y1=row*n//2,(row+1)*n//2;x0,x1=col*n//3,(col+1)*n//3;sl=np.s_[y0:y1,x0:x1]
            normal=AM.normals(bump[sl],((x1-x0)/(HI[u]-LO[u]),(y1-y0)/(HI[v]-LO[v])))
            normals[sl]=np.clip((normal*.5+.5)*255,0,255).astype('uint8')
        for suffix,array in (('color',np.uint8(np.clip(c,0,255))),('rough',np.uint8(rr*255)),('metal',np.uint8(mm*255)),('normal',normals)):
            Image.fromarray(array).save(MD/f'{paint}_{suffix}.png')
        stem=f'{MAT}/{paint}';text=O.vmat(paint,stem+'_color.png',stem+'_normal.png',stem+'_rough.png')
        text=text.replace('    g_flMetalness "0.0"',f'    F_METALNESS_TEXTURE "1"\n    TextureMetalness "{stem}_metal.png"')
        if paint=='ep_red':text=text.replace('    F_SPECULAR "1"','    F_SPECULAR "1"\n    F_SELF_ILLUM "1"\n    g_vSelfIllumTint "[0.50 0.018 0.007 1]"\n    g_flSelfIllumScale "0.7"')
        (MD/f'{paint}.vmat').write_text(text)
    labels=Image.new('RGB',(2048,2048),(142,146,143));d=ImageDraw.Draw(labels)
    glyphs=['1','2','3','4','5','6','7','8','9','*','0','#']
    for i,g in enumerate(glyphs):
        row,col=divmod(i,4);x,y=col*512,row*512
        d.text((x+256,y+230),g,font=ImageFont.truetype('C:/Windows/Fonts/arialbd.ttf',240),anchor='mm',fill=(18,23,23))
        if i<9:d.text((x+256,y+420),['','ABC','DEF','GHI','JKL','MNO','PQRS','TUV','WXYZ'][i],font=ImageFont.truetype('C:/Windows/Fonts/arial.ttf',65),anchor='mm',fill=(35,40,38))
    for i,bg,fg,title,sub in [(12,(34,39,37),(218,211,172),'EMERGENCY','PLANT TELEPHONE'),
            (13,(190,178,130),(30,36,31),'LIFT HANDSET','DIAL 222 - CONTROL'),(14,(26,40,32),(123,157,119),'LINE READY','SECURE PLANT NETWORK'),
            (15,(184,169,119),(39,43,36),'RIVERDALE','COMMUNICATIONS / U1-07')]:
        row,col=divmod(i,4);x,y=col*512,row*512;d.rectangle((x,y,x+512,y+512),fill=bg)
        d.text((x+256,y+190),title,font=ImageFont.truetype('C:/Windows/Fonts/arialbd.ttf',57),anchor='mm',fill=fg)
        d.text((x+256,y+340),sub,font=ImageFont.truetype('C:/Windows/Fonts/arial.ttf',33),anchor='mm',fill=fg)
    labels.save(MD/'ep_print_color.png');(MD/'ep_print.vmat').write_text(O.vmat('ep_print',f'{MAT}/ep_print_color.png',rough='[0.52 0.52 0.52 0]'))
def main():
    DEST.mkdir(parents=True,exist_ok=True);MD.mkdir(parents=True,exist_ok=True)
    guards={p.relative_to(ROOT).as_posix():sha(p) for folder in ('Assets/models/maps/riverdale','Assets/materials/riverdale') for p in (ROOT/folder).rglob('*') if p.is_file() and p.suffix in ('.obj','.mtl','.vmdl','.png','.vmat')}
    scene=ROOT/'Assets/scenes/maps/Riverdale/riverdale.scene';guards[scene.relative_to(ROOT).as_posix()]=sha(scene)
    before,counts=baseline();print('Actual saved original extracted:',counts,flush=True)
    after=candidate();print('New geometry:',after.triangle_count(),'triangles',flush=True)
    materials(after);print('PBR materials generated',flush=True)
    for name,model in [('before',before),('after',after)]:K.write_model(DEST,RESOURCE,name,model)
    for path,h in guards.items():assert sha(ROOT/path)==h,path
    report=dict(status='proposal-not-installed',userApproved=False,installedInMap=False,originalRetained=True,
        resource=RESOURCE,materials=MAT,originalTriangles=126,proposedTriangles=after.triangle_count(),originalSourceParts=counts,
        selectedOriginalPlan=ORIGIN.tolist(),protectedSourceSHA256=guards,
        models={name:dict(sha256=sha(DEST/f'{name}.obj'),boxes=len(model.boxes),hulls=len(model.hulls)) for name,model in [('before',before),('after',after)]},
        proposedCollision='Close-fitting shell and receiver/beacon bodies; flexible cord has no blocking box',nativeChecks='pending')
    (HERE/'candidate.json').write_text(json.dumps(report,indent=2)+'\n');(OUT/'candidate.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps({k:v for k,v in report.items() if k!='protectedSourceSHA256'}))
if __name__=='__main__':main()
