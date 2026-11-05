"""Fit the approved Lowtide ladder design to Riverside's guard tower; review only."""
from pathlib import Path
import sys,inspect,json,hashlib,collections,re,math
import numpy as np
sys.dont_write_bytecode=True
ROOT=Path(__file__).absolute().parents[3];sys.path.insert(0,str(ROOT/'Tools'))
import map_kit as K
import riverdale_parts as G
import riverside_parts as P
import riverside_map as R
import lowtide_quay_ladders as APPROVED
OUT=ROOT/'output/riverside/tower-ladder-v1';STAGE=OUT/'stage'
RES='models/props/riverside/tower_ladder_v1';MODEL=STAGE/'Assets'/RES
MODEL.mkdir(parents=True,exist_ok=True)
Z=np.array((0.,0.,1.));deck=520.
def make(lod):
    src=inspect.getsource(APPROVED.model)
    edits={
        'def model(n=-1450.):':'def model(n=0.):',
        'for n in (-8,8):':'for n in (-9,9):',
        'path=[P(234,n,-132),P(234,n,15)]':'path=[P(234,n,0),P(234,n,570)]',
        'np.linspace(math.pi,0,17)':'np.linspace(math.pi,0,'+str((17,11,7)[lod])+')',
        'P(237+3*math.cos(angle),n,15+3*math.sin(angle))':'P(240+6*math.cos(angle),n,570+6*math.sin(angle))',
        'P(240,n,1.0)':'P(246,n,521.0)',
        'box(240,n,.6,3.0,5.5,1.2':'box(246,n,520.6,3.0,5.5,1.2',
        'P(240,n+offset,1.21),P(240,n+offset,1.5)':'P(246,n+offset,521.21),P(246,n+offset,521.5)',
        'for z in (-15,-66,-116):':'for z in (96,228,360,492):',
        'box(239.65,n,z':'box(246.8,n,z',
        'P(239.3,n,z)':'P(246.45,n,z)',
        'bolt(239.2,n,z+dz)':'bolt(246.35,n,z+dz)',
        'P(234,n,-132),P(234,n,-130.7)':'P(234,n,0),P(234,n,1.3)',
        'range(-120,0,12)':'range(12,520,12)',
        'P(234,-8,z),P(234,8,z)':'P(234,-9,z),P(234,9,z)',
        '2.9,14.1,.32':'2.9,16.1,.32',
        '.17,13.9,.22':'.17,15.9,.22',
        'np.linspace(-6,6,9)':'np.linspace(-7,7,'+str((9,5,0)[lod])+')',
        '(-7.4,7.4)':'(-8.4,8.4)',
        'points=[np.asarray(p,float) for p in points];rings=[];norms=[]':'sides=max(4,int(round(sides*'+str((1,.67,.42)[lod])+')));points=[np.asarray(p,float) for p in points];rings=[];norms=[]',
    }
    for a,b in edits.items():assert src.count(a)==1,a;src=src.replace(a,b)
    env=dict(APPROVED.__dict__);exec(compile(src,'approved-ladder-fitted','exec'),env);prototype=env['model']()
    q=np.array(((0,1,0),(1,0,20/deck),(0,0,1.)),float);nq=np.linalg.inv(q).T
    m=K.Model()
    for paint,polys in prototype.polygons.items():
        for i,(pts,normal) in enumerate(polys):
            points=[q@p-np.array((0.,234.,0.)) for p in pts]
            norm=nq@normal;ns=prototype.polygon_normals.get((paint,i));ns=[nq@n for n in ns] if ns is not None else None
            G.card(m,paint,points,norm,uv=prototype.polygon_uvs.get((paint,i)),normals=ns)
    m.material_overrides.update(prototype.material_overrides);m.tile_overrides.update(prototype.tile_overrides)
    # Mount the reused wall standoffs on cross-struts fixed between the tower's rear timber legs.
    X=np.array((1.,0,0));Y=np.array((0.,1,0))
    for z in (96,228,360,492):
        half=70-24*z/610;y=14.65+20*z/deck
        G.bevel_box(m,np.array((0,y,z)),(X,Y,Z),(half*2,3,3),'paint',.14 if lod<2 else 0)
        for side in (-1,1):
            G.bevel_box(m,np.array((side*half,y-.2,z)),(X,Y,Z),(4.8,.7,7.5),'paint',.10 if lod<2 else 0)
            for dz in (-2.3,2.3):
                G.lathe_axis(m,np.array((side*half,y-.59,z+dz)),-Y,[(0,0),(.5,0),(.5,.4),(0,.4)],'hardware',sides=6 if lod<2 else 4)
    return m
counts=[]
for lod in range(3):counts.append(K.write_obj(MODEL/f'ladder_lod{lod}.obj',make(lod),f'ladder_lod{lod}'));print('LOD',lod,counts[-1],flush=True)
K.write_vmdl(MODEL/'ladder.vmdl',RES,'ladder_lod0',make(0))
t=(MODEL/'ladder.vmdl').read_text();a=t.index('\t\t\t{\n\t\t\t\t_class = "RenderMeshList"');b=t.index('\n\t\t\t},',a)+len('\n\t\t\t},')
files='\n'.join(f'{{ _class = "RenderMeshFile" name = "lod{i}" filename = "{RES}/ladder_lod{i}.obj" import_scale = 1 align_origin_x_type = "None" align_origin_y_type = "None" align_origin_z_type = "None" import_filter = {{ exclude_by_default = false exception_list = [] }} }},' for i in range(3))
groups='\n'.join(f'{{ _class = "LODGroup" switch_threshold = {d} meshes = ["lod{i}"] }},' for i,d in enumerate((0,25,65)))
(MODEL/'ladder.vmdl').write_text(t[:a]+f'{{ _class = "RenderMeshList" children = [{files}] }},\n{{ _class = "LODGroupList" children = [{groups}] }},'+t[b:])
# Capture the original ladder with its actual world-space rod orientation and phase.
old=K.Model();orig=P.rod;captured=[]
def capture(m,a,b,r,paint,*args,**kwargs):
    orig(m,a,b,r,paint,*args,**kwargs)
    if paint=='rs_wood':orig(old,a,b,r,paint,*args,**kwargs);captured.append((r,paint))
P.rod=capture
try:P.guard_tower(K.Model(),R.TOWER[0],R.TOWER[1],aim=R.SEARCH_TARGET)
finally:P.rod=orig
assert len(captured)==45 and sum(r==1.2 for r,p in captured)==2
R.configure(old);K.write_obj(OUT/'legacy_absolute.obj',old,'old_ladder')
f=G.unit((*R.TOWER[1],0));side=np.cross(Z,f);origin=np.array(R.TOWER[0],float)-f*88
yaw=math.degrees(math.atan2(-side[1],-side[0]));angle=math.radians(yaw)
rot=np.array(((math.cos(angle),-math.sin(angle),0),(math.sin(angle),math.cos(angle),0),(0,0,1.)))
local=K.Model()
for paint,polys in old.polygons.items():
    for i,(pts,normal) in enumerate(polys):
        ns=old.polygon_normals.get((paint,i));G.card(local,paint,[rot.T@(p-origin) for p in pts],rot.T@normal,uv=old.polygon_uvs.get((paint,i)),normals=[rot.T@n for n in ns] if ns is not None else None)
R.configure(local);K.write_model(MODEL,RES,'legacy_ladder',local)
def records(p):
    lines=p.read_text().splitlines(keepends=True);vs=[tuple(round(float(x),3) for x in l.split()[1:4]) for l in lines if l.startswith('v ')];mat='';r=[]
    for i,l in enumerate(lines):
        if l.startswith('usemtl '):mat=l.split()[1]
        if l.startswith('f '):r.append((i,(mat,tuple(sorted(vs[int(t.split('/')[0])-1] for t in l.split()[1:])))))
    return lines,r
_,oldfaces=records(OUT/'legacy_absolute.obj');wanted=collections.Counter(k for _,k in oldfaces)
vmdl=ROOT/'Assets/models/maps/riverside/riverside_dressing.vmdl';vt=vmdl.read_text();source=None
for resource in re.findall(r'filename\s*=\s*"([^"]+\.obj)"',vt):
    p=ROOT/'Assets'/resource
    if not p.exists():continue
    lines,faces=records(p)
    if not wanted-collections.Counter(k for _,k in faces):source=p;break
assert source,'Original guard-tower ladder no longer matches the current dressing mesh.'
cut=set()
for i,k in faces:
    if wanted[k]:cut.add(i);wanted[k]-=1
assert len(cut)==450 and not +wanted
(MODEL/'dressing_without_ladder.obj').write_text(''.join(l for i,l in enumerate(lines) if i not in cut).replace('mtllib '+source.with_suffix('.mtl').name,'mtllib dressing_without_ladder.mtl'))
(MODEL/'dressing_without_ladder.mtl').write_bytes(source.with_suffix('.mtl').read_bytes())
(MODEL/'dressing_without_ladder.vmdl').write_text(vt.replace(source.relative_to(ROOT/'Assets').as_posix(),RES+'/dressing_without_ladder.obj'))
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
protected=[source,vmdl,ROOT/'Assets/scenes/maps/Riverside/riverside.scene']
external={str((ROOT/'Assets'/s).relative_to(ROOT)).replace('\\','/'):sha(ROOT/'Assets'/s) for s in set(make(2).material_overrides.values())}
m=dict(preview_only=True,reused_approved_design='Tools/lowtide_quay_ladders.py',reused_recipe_sha=sha(ROOT/'Tools/lowtide_quay_ladders.py'),triangles=counts,position=K.to_world(origin).tolist(),plan_position=origin.tolist(),yaw=yaw,removed_old_triangles=450,
       resource=RES+'/ladder.vmdl',background=RES+'/dressing_without_ladder.vmdl',protected={p.relative_to(ROOT).as_posix():sha(p) for p in protected},external_files=external,
       files={p.relative_to(STAGE).as_posix():sha(p) for p in MODEL.iterdir() if p.is_file()})
(OUT/'manifest.json').write_text(json.dumps(m,indent=2));print(json.dumps({k:v for k,v in m.items() if k!='files'},indent=2))
