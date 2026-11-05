"""Review-only rebuild of T2's two-beam hitch, jack stub and concrete pad."""
from pathlib import Path
import sys,json,hashlib,collections,re,math,shutil
import numpy as np
from PIL import Image
sys.dont_write_bytecode=True
ROOT=Path(__file__).absolute().parents[3];sys.path.insert(0,str(ROOT/'Tools'))
import map_kit as K
import riverdale_parts as G
import riverside_parts as P
import riverside_map as R
OUT=ROOT/'output/riverside/trailer-hitch-v1';STAGE=OUT/'stage'
RES='models/props/riverside/trailer_hitch_v1';MAT='materials/riverside/trailer_hitch_v1'
MODEL=STAGE/'Assets'/RES;MATERIAL=STAGE/'Assets'/MAT
for p in (OUT,MODEL,MATERIAL):p.mkdir(parents=True,exist_ok=True)
rng=np.random.default_rng(42012);size=1024
def noise(n):return np.asarray(Image.fromarray(rng.integers(0,256,(n,n),dtype='uint8')).resize((size,size),Image.Resampling.BICUBIC),float)/255
coarse=noise(48);fine=noise(380);cloud=noise(12)
rust=(fine>.75)&(coarse>.62)&(cloud>.58)
color=np.zeros((size,size,3))+[45,50,44];color+=(coarse[...,None]-.5)*8+(fine[...,None]-.5)*5
color[rust]=np.stack((69+fine[rust]*12,48+fine[rust]*8,32+fine[rust]*6),axis=-1)
Image.fromarray(color.clip(0,255).astype('uint8')).save(MATERIAL/'frame_color.png')
Image.fromarray(((.65+.2*coarse+.09*rust)*255).clip(0,255).astype('uint8')).save(MATERIAL/'frame_rough.png')
dy,dx=np.gradient(coarse+rust*.06);normal=np.dstack((-dx*.65,-dy*.65,np.ones_like(dx)));normal/=np.linalg.norm(normal,axis=2)[...,None]
Image.fromarray(((normal*.5+.5)*255).clip(0,255).astype('uint8')).save(MATERIAL/'frame_normal.png')
for name in ('zinc_color.png','zinc_rough.png','zinc_normal.png'):
    shutil.copyfile(ROOT/'Assets/materials/riverside/tv_aerial_v1'/name,MATERIAL/name)
def material(name,color,rough,metal=0):
    c=f'"{MAT}/{color}"' if isinstance(color,str) else '"['+' '.join(map(str,(*color,0)))+']"'
    n=f'{MAT}/{name}_normal.png' if name in ('frame','zinc') else 'materials/default/default_normal.tga'
    r=f'"{MAT}/{name}_rough.png"' if name in ('frame','zinc') else f'"[{rough} {rough} {rough} 0]"'
    (MATERIAL/f'{name}.vmat').write_text(f'''Layer0
{{
 shader "shaders/complex.shader"
 F_SPECULAR 1
 TextureColor {c}
 TextureNormal "{n}"
 TextureRoughness {r}
 g_flRoughnessScaleFactor "1"
 g_flMetalness "{metal}"
 g_vColorTint "[1 1 1 1]"
}}
''')
material('frame','frame_color.png',.7,.28)
material('zinc','zinc_color.png',.55,.76)
material('steel',(.22,.24,.21),.48,.8)
material('rubber',(.022,.027,.020),.84)
material('brass',(.35,.25,.09),.43,.78)
X=np.array((1.,0,0));Y=np.array((0.,1,0));Z=np.array((0.,0,1.))
def unit(x):return np.asarray(x,float)/np.linalg.norm(x)
def make(lod):
    m=K.Model();sides=(16,10,6)[lod]
    def box(c,s,paint='frame',b=0,axes=(X,Y,Z)):
        if b and lod<2:G.bevel_box(m,np.asarray(c),axes,s,paint,b)
        else:m.oriented_box(np.asarray(c),axes,s,paint)
    def axis(c,profile,paint='zinc',along=Z,n=None):G.lathe_axis(m,np.asarray(c),along,profile,paint,sides=n or sides)
    def bar(a,b,r,paint='zinc'):
        a=np.asarray(a);b=np.asarray(b);length=float(np.linalg.norm(b-a))
        axis(a,[(0,0),(r,0),(r,length),(0,length)],paint,(b-a)/length)
    def tube(pts,r,paint='rubber',closed=False):G.tube(m,[np.asarray(p,float) for p in pts],r,paint,sides=(8,6,4)[lod],bend_radius=.55,closed=closed)
    def beam(a,b,size,paint='frame',bevel=.12):
        a=np.asarray(a,float);b=np.asarray(b,float);u=unit(b-a);v=unit(np.cross(Z,u));w=np.cross(u,v)
        box((a+b)/2,(np.linalg.norm(b-a),*size),paint,bevel,(u,v,w))
    def bolt(c,along=Z,r=.34):
        axis(c,[(0,0),(r*1.35,0),(r*1.35,.08),(r,.08),(r,.36),(0,.36)],'steel',along,n=6 if lod<2 else 4)
    # Original attachment points and cross section, now rounded closed steel rails with a cross brace.
    for sy in (-1,1):
        beam((0,sy*30,18),(-46,0,14),(3,4))
        if lod<2:
            for x in (-3,-8):
                y=sy*(30+x*30/46);bolt((x,y,20+x*4/46+.02))
    beam((-18,-18.1,16.43),(-18,18.1,16.43),(2,2.7))
    # Folded mounting plate follows the rails' pitch. The parked jack's foot rests on the ground.
    plate=[np.array((x,y,20+x*4/46+.12)) for x,y in [(-24,-15),(-40,-4),(-40,4),(-24,15)]]
    G.card(m,'frame',plate,Z)
    G.card(m,'frame',[p-Z*.25 for p in plate],-Z)
    for i,p in enumerate(plate):G.card(m,'frame',[p,plate[(i+1)%4],plate[(i+1)%4]-Z*.25,p-Z*.25],unit(np.cross(plate[(i+1)%4]-p,-Z)))
    for x,y in [(-25,-12),(-25,12),(-38,-3),(-38,3)]:bolt((x,y,20+x*4/46+.13))
    box((-31,0,.42),(8,6,.68),'zinc',.23)
    axis((-31,0,.75),[(0,0),(1.1,0),(1.1,12.0),(0,12.0)],'zinc')
    axis((-31,0,7.5),[(0,0),(1.65,0),(1.65,17.8),(1.85,17.8),(1.85,18.5),(0,18.5)],'frame')
    axis((-31,0,7.3),[(0,0),(1.76,0),(1.76,.55),(0,.55)],'rubber')
    box((-31,0,26.0),(4.2,3.8,1.7),'zinc',.55)
    bar((-31,0,26.8),(-31,0,28.3),.34,'steel')
    beam((-31,0,28.3),(-31,5.2,28.3),(.65,.6),'zinc',.12)
    axis((-31,5.2,28.1),[(0,0),(.58,0),(.58,3.0),(0,3.0)],'rubber')
    if lod<2:
        axis((-31,0,12),[(0,0),(1.74,0),(1.74,.35),(0,.35)],'zinc')
        bar((-31,-2.4,12.17),(-31,2.6,12.17),.18,'steel')
        G.torus(m,np.array((-31.,2.85,12.17)),X,.52,.1,'steel',seg=10,sides=4)
    # Pressed coupler shell: shallow closed nose, flared rear and turned-out side flanges.
    stations=[(-54,.55,.5,13.3),(-53,1.9,2,13.3),(-50,3,3.4,13.4),(-46,3.2,3.5,13.7),(-41,4.8,3.2,14.2),(-36.5,7.2,2.2,14.5)]
    segments=(16,10,6)[lod]
    rings=[];shell_normals=[]
    for j,(x,w,h,bz) in enumerate(stations):
        a=np.array(stations[max(0,j-1)]);b=np.array(stations[min(len(stations)-1,j+1)])
        dw,dh,db=(b-a)[1:]/(b[0]-a[0])
        angles=np.linspace(0,math.pi,segments+1)
        rings.append([np.array((x,w*math.cos(t),bz+h*math.sin(t))) for t in angles])
        shell_normals.append([unit((-w*db*math.sin(t)-w*dh*math.sin(t)**2-h*dw*math.cos(t)**2,h*math.cos(t),w*math.sin(t))) for t in angles])
    for j in range(len(rings)-1):
        for k in range(segments):
            pts=[rings[j][k],rings[j+1][k],rings[j+1][k+1],rings[j][k+1]]
            normals=[shell_normals[j][k],shell_normals[j+1][k],shell_normals[j+1][k+1],shell_normals[j][k+1]]
            G.card(m,'zinc',pts,sum(normals),both=True,normals=normals)
        for sy,index in ((1,0),(-1,-1)):
            a,b=rings[j][index],rings[j+1][index]
            G.card(m,'zinc',[a,b,b+Y*sy*.55,a+Y*sy*.55],Z,both=True)
    G.card(m,'zinc',rings[0],-X,both=True)
    # Inner ball-seat cup opens downward; its dark cavity is visible from below.
    axis((-50,0,13.30),[(2.05,0),(1.95,.6),(1.4,1.5),(.05,2.0)],'steel')
    for x,y,z in [(-38.5,-5.1,16.1),(-38.5,5.1,16.1),(-43.5,0,17.4)]:bolt((x,y,z),r=.30)
    # Positive latch pivot, two formed side arms and a folding handle with safety retaining pin.
    bar((-44,-1.45,17.45),(-44,1.45,17.45),.27,'steel')
    for sy in (-1,1):beam((-44,sy*.75,17.5),(-48.2,sy*.75,20),(.22,.75),'zinc',.10)
    box((-49.2,0,20.08),(4.5,2.3,.4),'zinc',.16)
    tube([(-50.5,-.95,20.25),(-51.6,-.95,21),(-51.6,.95,21),(-50.5,.95,20.25)],.16,'steel')
    if lod<2:
        bar((-47.9,-1.8,19.0),(-47.9,1.8,19.0),.13,'steel')
        G.torus(m,np.array((-47.9,-2.15,19.0)),X,.45,.09,'steel',seg=10,sides=4)
        for sy in (-1,1):
            for x in (-44.0,-48.3):
                bar((x,sy*2.8,14.7),(x,sy*3.2,14.7),.20,'steel')
    # Chains are alternating, interlocked oval links, hanging under gravity rather than rigid bars.
    def chain_link(center,u,v):
        u=unit(u);v=unit(v);n=unit(np.cross(u,v));segs=(10,7)[lod];ns=(5,4)[lod];rad=.14
        rings=[];normals=[]
        for t in np.linspace(0,2*math.pi,segs,endpoint=False):
            c=center+u*.74*math.cos(t)+v*.39*math.sin(t)
            radial=unit(u*(math.cos(t)/.74)+v*(math.sin(t)/.39))
            dirs=[radial*math.cos(p)+n*math.sin(p) for p in np.linspace(0,2*math.pi,ns,endpoint=False)]
            rings.append([c+d*rad for d in dirs]);normals.append(dirs)
        for j in range(segs):
            j1=(j+1)%segs
            for k in range(ns):
                k1=(k+1)%ns
                pts=[rings[j][k],rings[j][k1],rings[j1][k1],rings[j1][k]]
                norms=[normals[j][k],normals[j][k1],normals[j1][k1],normals[j1][k]]
                G.card(m,'steel',pts,sum(norms),normals=norms)
    for sy in (-1,1):
        def path(t):return np.array((-39-13*t,sy*(5.7-2.4*t),14.4-5.1*math.sin(math.pi*t)-3.4*t))
        if lod<2:
            # Equal arc spacing prevents stretched gaps between links at the bottom of each chain.
            dense=np.array([path(t) for t in np.linspace(0,1,301)]);arc=np.r_[0,np.cumsum(np.linalg.norm(np.diff(dense,axis=0),axis=1))]
            count=20
            for i,s in enumerate(np.linspace(0,arc[-1],count)):
                t=float(np.interp(s,arc,np.linspace(0,1,301)));u=unit(path(min(1,t+.01))-path(max(0,t-.01)))
                v=unit(np.cross(u,Z));v=np.cross(u,v) if i%2 else v
                chain_link(path(t),u,v)
        else:tube([path(t) for t in np.linspace(0,1,9)],.22,'steel')
        G.torus(m,np.array((-39.,sy*5.7,14.7)),X,.52,.16,'steel',seg=(12,8,6)[lod],sides=4)
    # Seven-pin lead hangs from the frame; a capped connector and strain relief end the cable.
    a,b,c,d=[np.array(p,float) for p in [(-36,7.6,14),(-42,13,1),(-52,11,3),(-51,5.3,10.8)]]
    loop=[(1-t)**3*a+3*(1-t)**2*t*b+3*(1-t)*t*t*c+t**3*d for t in np.linspace(0,1,(14,10,6)[lod])]
    tube([(-4,27.4,18.3),(-20,16.9,16.6),(-34,7.8,15),*loop],.23)
    axis((-51,5.3,10.7),[(0,0),(.46,0),(.57,.6),(.72,.8),(.72,2.4),(.78,2.4),(.78,2.8),(0,2.8)],'rubber',X)
    if lod<2:
        for i in range(6):
            t=i*math.pi/3
            bar((-48.19,5.3+.43*math.cos(t),10.7+.43*math.sin(t)),(-48.08,5.3+.43*math.cos(t),10.7+.43*math.sin(t)),.075,'brass')
        bar((-48.19,5.3,10.7),(-48.08,5.3,10.7),.075,'brass')
        for x,y,z in [(-12,22.1,17.45),(-25,13.7,16.1)]:
            G.torus(m,np.array((x,y,z)),X,.37,.07,'steel',seg=10,sides=4)
    m.material_overrides={p:f'{MAT}/{p}.vmat' for p in m.polygons};m.tile_overrides={p:18 for p in m.polygons}
    return m
print('Textures ready',flush=True)
counts=[]
for lod in range(3):
    counts.append(K.write_obj(MODEL/f'hitch_lod{lod}.obj',make(lod),f'hitch_lod{lod}'));print('LOD',lod,counts[-1],flush=True)
K.write_vmdl(MODEL/'hitch.vmdl',RES,'hitch_lod0',make(0))
text=(MODEL/'hitch.vmdl').read_text();a=text.index('\t\t\t{\n\t\t\t\t_class = "RenderMeshList"');b=text.index('\n\t\t\t},',a)+len('\n\t\t\t},')
files='\n'.join(f'{{ _class = "RenderMeshFile" name = "lod{i}" filename = "{RES}/hitch_lod{i}.obj" import_scale = 1 align_origin_x_type = "None" align_origin_y_type = "None" align_origin_z_type = "None" import_filter = {{ exclude_by_default = false exception_list = [] }} }},' for i in range(3))
groups='\n'.join(f'{{ _class = "LODGroup" switch_threshold = {d} meshes = ["lod{i}"] }},' for i,d in enumerate((0,10,28)))
(MODEL/'hitch.vmdl').write_text(text[:a]+f'{{ _class = "RenderMeshList" children = [{files}] }},\n{{ _class = "LODGroupList" children = [{groups}] }},'+text[b:])
if '--geometry-only' in sys.argv:
    m=json.loads((OUT/'manifest.json').read_text());m['triangles']=counts
    m['files']={p.relative_to(STAGE).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for d in (MODEL,MATERIAL) for p in d.iterdir() if p.is_file()}
    (OUT/'manifest.json').write_text(json.dumps(m,indent=2));print(json.dumps({'triangles':counts,'geometry_updated':True}));sys.exit()
old=K.Model()
for sy in (-1,1):old.beam(np.array((0.,sy*30,18)),np.array((-46.,0,14)),(3,4),'rs_rust')
P.cylinder(old,(-44,0),1.6,0,18,'rs_rust',6)
P.obox(old,np.array((-44.,0,1)),(1,0),(8,8,2),'rs_concrete')
R.configure(old);K.write_model(MODEL,RES,'legacy_hitch',old)
origin=np.array((-1030.,1050.,0.))
absolute=P.place(old,origin,0);R.configure(absolute);K.write_obj(OUT/'legacy_absolute.obj',absolute,'old_hitch')
def records(p):
    lines=p.read_text().splitlines(keepends=True);vs=[tuple(round(float(x),3) for x in l.split()[1:4]) for l in lines if l.startswith('v ')];mat='';r=[]
    for i,l in enumerate(lines):
        if l.startswith('usemtl '):mat=l.split()[1]
        if l.startswith('f '):r.append((i,(mat,tuple(sorted(vs[int(t.split('/')[0])-1] for t in l.split()[1:])))))
    return lines,r
_,oldfaces=records(OUT/'legacy_absolute.obj');wanted=collections.Counter(k for _,k in oldfaces)
vmdl=ROOT/'Assets/models/maps/riverside/riverside_low.vmdl';vt=vmdl.read_text();source=None
for resource in re.findall(r'filename\s*=\s*"([^"]+\.obj)"',vt):
    p=ROOT/'Assets'/resource
    if not p.exists():continue
    lines,faces=records(p)
    if not wanted-collections.Counter(k for _,k in faces):source=p;break
assert source,'Original T2 hitch no longer matches current public lowland mesh.'
cut=set()
for i,k in faces:
    if wanted[k]:cut.add(i);wanted[k]-=1
assert len(cut)==len(oldfaces) and not +wanted
(MODEL/'low_without_hitch.obj').write_text(''.join(l for i,l in enumerate(lines) if i not in cut).replace('mtllib '+source.with_suffix('.mtl').name,'mtllib low_without_hitch.mtl'))
(MODEL/'low_without_hitch.mtl').write_bytes(source.with_suffix('.mtl').read_bytes())
(MODEL/'low_without_hitch.vmdl').write_text(vt.replace(source.relative_to(ROOT/'Assets').as_posix(),RES+'/low_without_hitch.obj'))
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
protected=[source,vmdl,ROOT/'Assets/scenes/maps/Riverside/riverside.scene']
m=dict(preview_only=True,triangles=counts,position=K.to_world(origin).tolist(),plan_position=origin.tolist(),removed_old_triangles=len(cut),resource=RES+'/hitch.vmdl',background=RES+'/low_without_hitch.vmdl',
       protected={p.relative_to(ROOT).as_posix():sha(p) for p in protected},files={p.relative_to(STAGE).as_posix():sha(p) for d in (MODEL,MATERIAL) for p in d.iterdir() if p.is_file()})
(OUT/'manifest.json').write_text(json.dumps(m,indent=2));print(json.dumps({k:v for k,v in m.items() if k!='files'},indent=2))
