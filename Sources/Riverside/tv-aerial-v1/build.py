"""Review-only T2 rooftop Yagi aerial. Never edits public map inputs."""
from pathlib import Path
import sys,json,hashlib,collections,re
import numpy as np
from PIL import Image
sys.dont_write_bytecode=True
ROOT=Path(__file__).absolute().parents[3];sys.path.insert(0,str(ROOT/'Tools'))
import map_kit as K
import riverdale_parts as G
import riverside_parts as P
import riverside_map as R
OUT=ROOT/'output/riverside/tv-aerial-v1';STAGE=OUT/'stage'
RES='models/props/riverside/tv_aerial_v1';MAT='materials/riverside/tv_aerial_v1'
MODEL=STAGE/'Assets'/RES;MATERIAL=STAGE/'Assets'/MAT
for p in (OUT,MODEL,MATERIAL):p.mkdir(parents=True,exist_ok=True)
rng=np.random.default_rng(81812);size=1024
def noise(n):return np.asarray(Image.fromarray(rng.integers(0,256,(n,n),dtype='uint8')).resize((size,size),Image.Resampling.BICUBIC),float)/255
coarse=noise(64);fine=noise(420);cloud=noise(11)
# Zinc's mottled crystalline finish, restrained oxidation and a shallow surface normal.
grain=coarse*.6+fine*.4
color=np.zeros((size,size,3))+[153,160,155]
color+=(grain[...,None]-.5)*30+(cloud[...,None]-.5)*9
Image.fromarray(color.clip(0,255).astype('uint8')).save(MATERIAL/'zinc_color.png')
Image.fromarray(((.42+.20*grain+.07*cloud)*255).clip(0,255).astype('uint8')).save(MATERIAL/'zinc_rough.png')
dy,dx=np.gradient(coarse)
normal=np.dstack((-dx*.7,-dy*.7,np.ones_like(dx)));normal/=np.linalg.norm(normal,axis=2)[...,None]
Image.fromarray(((normal*.5+.5)*255).clip(0,255).astype('uint8')).save(MATERIAL/'zinc_normal.png')
def material(name,color,rough,metal=0):
    c=f'"{MAT}/{color}"' if isinstance(color,str) else '"['+' '.join(map(str,(*color,0)))+']"'
    n=f'{MAT}/zinc_normal.png' if name=='zinc' else 'materials/default/default_normal.tga'
    r=f'"{MAT}/zinc_rough.png"' if name=='zinc' else f'"[{rough} {rough} {rough} 0]"'
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
material('zinc','zinc_color.png',.55,.78)
material('aluminium',(.46,.49,.46),.43,.85)
material('insulator',(.38,.34,.23),.78)
material('rubber',(.029,.035,.031),.83)
material('fastener',(.22,.24,.22),.38,.85)
X=np.array((1.,0,0));Y=np.array((0.,1,0));Z=np.array((0.,0,1.))
def make(lod):
    m=K.Model();sides=(14,10,6)[lod]
    def box(c,s,paint='zinc',b=0,axes=(X,Y,Z)):
        if b and lod<2:G.bevel_box(m,np.asarray(c),axes,s,paint,b)
        else:m.oriented_box(np.asarray(c),axes,s,paint)
    def axis(c,profile,paint='zinc',along=Z,n=None):G.lathe_axis(m,np.asarray(c),along,profile,paint,sides=n or sides)
    def bar(a,b,r,paint='aluminium'):
        a=np.asarray(a);b=np.asarray(b);length=float(np.linalg.norm(b-a))
        axis(a,[(0,0),(r,0),(r,length),(0,length)],paint,(b-a)/length)
    def tube(pts,r,paint='rubber',closed=False):G.tube(m,[np.asarray(p,float) for p in pts],r,paint,sides=(8,6,4)[lod],bend_radius=.9,closed=closed)
    # Sloping flashing lies on this trailer's pitched metal roof, 1.5 in below the old mast root.
    ry=np.array((0.,1.,1/11));ry/=np.linalg.norm(ry);rz=np.cross(X,ry)
    box((0,0,-1.40),(7.2,7.2,.18),'zinc',.07,(X,ry,rz))
    axis((0,0,-1.5),[(1.55,0),(1.55,.25),(1.1,.8),(.88,1.75),(.82,2.05)],'rubber')
    axis((0,0,-1.4),[(0,0),(.8,0),(.8,71.4),(0,71.4)],'zinc')
    axis((0,0,70),[(0,0),(.83,0),(.83,.30),(0,.30)],'rubber')
    if lod<2:
        for x in (-2.65,2.65):
            for y in (-2.65,2.65):
                axis((x,y,-1.24+y/11),[(0,0),(.22,0),(.22,.18),(0,.18)],'fastener',rz,n=6)
    # Two clamped standoffs support a square-section boom rather than bars welded onto a pole.
    box((0,0,65.9),(3.6,2.6,.35),'zinc',.06)
    box((0,0,67.25),(43,1.15,1.15),'aluminium',.09)
    for x in (-21.5,21.5):box((x,0,67.25),(.18,1.22,1.22),'rubber',.06)
    if lod<2:
        for y in (-.95,.95):
            tube([(-1.35,y,66.05),(-1.35,y,64.3),(0,y,63.65),(1.35,y,64.3),(1.35,y,66.05)],.11,'fastener')
            for x in (-1.35,1.35):axis((x,y,66.07),[(0,0),(.23,0),(.23,.25),(0,.25)],'fastener',n=6)
    # Reflector, driven folded dipole and five progressively shorter directors all share one plane.
    for x,width in [(-19,42),(-3,34),(4,31),(10,28),(16,25),(21,22)]:
        box((x,0,68.05),(1.1,2.15,.5),'insulator',.10)
        bar((x,-width/2,68.55),(x,width/2,68.55),.23)
        if lod==0:
            for end in (-1,1):
                axis((x,end*width/2-.16,68.55),[(0,0),(.26,0),(.26,.32),(0,.32)],'rubber',Y)
    # Folded dipole has a feed gap and a weatherproof balun, with a real coax connection.
    box((-11,0,68.1),(3.5,2.4,1.45),'rubber',.24)
    tube([(-12.1,-1.25,68.8),(-12.1,-18,68.8),(-9.8,-18,68.8),(-9.8,18,68.8),(-12.1,18,68.8),(-12.1,1.25,68.8)],.23,'aluminium')
    axis((-10.9,0,67.4),[(0,0),(.34,0),(.34,.8),(0,.8)],'fastener',-Z,n=6 if lod<2 else 4)
    tube([(-10.9,0,66.6),(-10.9,0,63.6),(-7,-1.1,62.8),(-1,-1.4,64),(.72,-.52,62),(.72,-.52,54),(.72,-.52,24),(.72,-.52,4),(2,-1.4,.3),(3.5,-3,-1.5)],.15)
    for z in ((12,31,50,61) if lod<2 else (20,50)):
        G.torus(m,np.array((0.,0.,z)),Z,.91,.08,'rubber',seg=(14,10,6)[lod],sides=4)
    if lod==0:
        for x in (-19,-3,4,10,16,21):
            axis((x,0,68.77),[(0,0),(.13,0),(.13,.13),(0,.13)],'fastener',n=6)
    m.material_overrides={p:f'{MAT}/{p}.vmat' for p in m.polygons};m.tile_overrides={p:12 for p in m.polygons}
    return m
counts=[]
for lod in range(3):counts.append(K.write_obj(MODEL/f'aerial_lod{lod}.obj',make(lod),f'aerial_lod{lod}'))
K.write_vmdl(MODEL/'aerial.vmdl',RES,'aerial_lod0',make(0))
text=(MODEL/'aerial.vmdl').read_text();a=text.index('\t\t\t{\n\t\t\t\t_class = "RenderMeshList"');b=text.index('\n\t\t\t},',a)+len('\n\t\t\t},')
files='\n'.join(f'{{ _class = "RenderMeshFile" name = "lod{i}" filename = "{RES}/aerial_lod{i}.obj" import_scale = 1 align_origin_x_type = "None" align_origin_y_type = "None" align_origin_z_type = "None" import_filter = {{ exclude_by_default = false exception_list = [] }} }},' for i in range(3))
groups='\n'.join(f'{{ _class = "LODGroup" switch_threshold = {d} meshes = ["lod{i}"] }},' for i,d in enumerate((0,12,32)))
(MODEL/'aerial.vmdl').write_text(text[:a]+f'{{ _class = "RenderMeshList" children = [{files}] }},\n{{ _class = "LODGroupList" children = [{groups}] }},'+text[b:])
if '--geometry-only' in sys.argv:
    manifest=json.loads((OUT/'manifest.json').read_text());manifest['triangles']=counts
    manifest['files']={p.relative_to(STAGE).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for d in (MODEL,MATERIAL) for p in d.iterdir() if p.is_file()}
    (OUT/'manifest.json').write_text(json.dumps(manifest,indent=2));print(json.dumps({'triangles':counts,'geometry_updated':True}));sys.exit()
old=K.Model();base=np.zeros(3)
P.rod(old,base,base+Z*70,.8,'rs_steel',6)
for k in range(5):
    zz=50+k*4;length=30-k*4
    P.rod(old,base+Z*zz-Y*length/2,base+Z*zz+Y*length/2,.4,'rs_steel',4)
R.configure(old);K.write_model(MODEL,RES,'legacy_aerial',old)
origin=np.array((-794.7722080465406,1033.5,123.))
absolute=P.place(old,origin,0);R.configure(absolute);K.write_obj(OUT/'legacy_absolute.obj',absolute,'old_aerial')
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
assert source,'Original T2 aerial no longer matches the public mesh.'
cut=set()
for i,k in faces:
    if wanted[k]:cut.add(i);wanted[k]-=1
assert len(cut)==len(oldfaces) and not +wanted
(MODEL/'low_without_aerial.obj').write_text(''.join(l for i,l in enumerate(lines) if i not in cut).replace('mtllib '+source.with_suffix('.mtl').name,'mtllib low_without_aerial.mtl'))
(MODEL/'low_without_aerial.mtl').write_bytes(source.with_suffix('.mtl').read_bytes())
(MODEL/'low_without_aerial.vmdl').write_text(vt.replace(source.relative_to(ROOT/'Assets').as_posix(),RES+'/low_without_aerial.obj'))
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
protected=[source,vmdl,ROOT/'Assets/scenes/maps/Riverside/riverside.scene']
m=dict(preview_only=True,triangles=counts,position=K.to_world(origin).tolist(),plan_position=origin.tolist(),removed_old_triangles=len(cut),resource=RES+'/aerial.vmdl',background=RES+'/low_without_aerial.vmdl',
       protected={p.relative_to(ROOT).as_posix():sha(p) for p in protected},files={p.relative_to(STAGE).as_posix():sha(p) for d in (MODEL,MATERIAL) for p in d.iterdir() if p.is_file()})
(OUT/'manifest.json').write_text(json.dumps(m,indent=2));print(json.dumps({k:v for k,v in m.items() if k!='files'},indent=2))
