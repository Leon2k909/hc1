"""Audit published lamp boxes and stage exact face cuts; never regenerate the map."""
from pathlib import Path
from collections import defaultdict
import hashlib,json,math,re,sys
import numpy as np
ROOT=Path(sys.argv[1]).resolve();sys.dont_write_bytecode=True
sys.path.insert(0,str(ROOT/'Tools'))
import map_kit as K
import riverside_map as M
import riverside_parts as P
OUT=ROOT/'output/asset-improvement-20261030/riverside-porch-light/installed'
OUT.mkdir(parents=True,exist_ok=True)
expected=[]
def record(name,c,yaw,L,W,side,seed,ground,lift=0):
    _,info=P.trailer(L,W,'rs_siding_white',seed=seed,door_side=side,lit_share=.8 if name=='office' else .6,boarded_share=0 if name=='office' else .15,door_lit=True if name=='office' else None)
    p=info['porch_light']-np.array((0,side*14,-6))+np.array((0,0,lift))
    pos=K.to_world(P.local_to_world(p,(c[0],c[1],ground),yaw))
    facing=np.array(P.local_to_world((0,side,0),(0,0,0),yaw))
    expected.append(dict(name=name,position=pos.tolist(),yaw=K.plan_yaw(facing),size=[5,4,6]))
for group,ground in ((M.LOW_TRAILERS,0),(M.TERRACE_TRAILERS,M.HIGH),(M.LEVEE_TRAILERS,M.HIGH)):
    for name,c,yaw,L,W,tint,side,seed,extra in group:record(name,c,yaw,L,W,side,seed,ground,M.RAISED if extra=='ladder' else 0)
name,c,yaw,L,W=M.OFFICE;record(name,c,yaw,L,W,1,51,M.HIGH)
expected.append(dict(name='Lucky Stop',position=K.to_world((M.STORE_DOOR[1]+20,M.STORE[2]-3,M.STORE_FLOOR+96)).tolist(),yaw=180,size=[8,6,5]))
assert len(expected)==26
public=[]
for name in ('riverside_low','riverside_terrace','riverside_levee','riverside_pad','riverside_store'):
    path=ROOT/'Assets/models/maps/riverside'/(name+'.vmdl')
    public.append(dict(path=str(path.relative_to(ROOT)),sha256=hashlib.sha256(path.read_bytes()).hexdigest(),physics_sha256=hashlib.sha256(path.read_text()[path.read_text().index('_class = "PhysicsShapeList"'):].encode()).hexdigest()))
sources={}
for row in public:
    path=ROOT/row['path'];text=path.read_text();render=text.split('_class = "PhysicsShapeList"')[0]
    for rel in re.findall(r'filename\s*=\s*"([^"]+\.obj)"',render):sources[rel]=True
    # Keep the canonical merged source free of retired boxes too, even where a private render import is active.
    sources.setdefault(str(path.with_suffix('.obj').relative_to(ROOT/'Assets')).replace('\\','/'),False)
placements={};cuts=[]
for relative,active in sources.items():
    path=ROOT/'Assets'/relative
    if not path.exists():continue
    original=path.read_bytes();lines=original.decode().splitlines(keepends=True)
    points=[];mat=None;kept=[];faces=[]
    for line in lines:
        p=line.split()
        if p and p[0]=='v':points.append((float(p[3]),float(p[1]),float(p[2])))
        if p and p[0]=='usemtl':mat=p[1]
        if p and p[0]=='f' and mat=='rs_porch_light':faces.append([points[int(t.split('/')[0])-1] for t in p[1:]])
        elif p and p[0]=='usemtl' and mat=='rs_porch_light':continue
        else:kept.append(line)
    if not faces:continue
    # Weld coincident exported vertices to find the individual twelve-triangle boxes.
    clusters=[]
    for face in faces:
        coords={tuple(round(v,5) for v in p) for p in face}
        touching=[i for i,(vs,fs) in enumerate(clusters) if vs&coords]
        fs=[face]
        for i in reversed(touching):
            vs,old=clusters.pop(i);coords|=vs;fs+=old
        clusters.append((coords,fs))
    for vs,fs in clusters:
        assert len(fs)==12,(relative,len(fs))
        v=np.array(list(vs));centre=(v.min(0)+v.max(0))/2
        matches=[(i,e) for i,e in enumerate(expected) if np.linalg.norm(centre-np.array(e['position']))<.003]
        assert len(matches)==1,(relative,centre,matches)
        i,e=matches[0]
        if active:
            assert i not in placements,('Duplicate active box',i,relative)
            placements[i]=dict(e,source=relative)
    target=OUT/'stage'/relative;target.parent.mkdir(parents=True,exist_ok=True)
    target.write_bytes(''.join(kept).encode())
    backup=OUT/'before-install'/relative;backup.parent.mkdir(parents=True,exist_ok=True)
    if backup.exists():assert backup.read_bytes()==original,'Existing backup differs'
    else:backup.write_bytes(original)
    cuts.append(dict(path='Assets/'+relative,before_sha256=hashlib.sha256(original).hexdigest(),after_sha256=hashlib.sha256(target.read_bytes()).hexdigest(),removed_faces=len(faces),active=active,fixtures=len(clusters)))
assert len(placements)==26,(len(placements),sorted(placements))
objects=[]
for i,e in sorted(placements.items()):
    key=f'porch_light/{i}';w,d,h=e['size']
    obj=K.game_object(M.ids,'Porch Light '+e['name'],key,e['position'],K.yaw_rotation(e['yaw']),scale=(d/4,w/5,h/6),components=[K.component(M.ids,'Sandbox.ModelRenderer',key+'/renderer',BodyGroups=18446744073709551615,Model='models/props/riverside/porch_light_v2/porch_light.vmdl',RenderType='On',Tint='1,1,1,1')])
    obj['Position']=','.join(f'{v:.6f}' for v in e['position']);objects.append(obj)
scene=ROOT/'Assets/scenes/maps/Riverside/riverside.scene'
(OUT/'before-install/riverside.scene').write_bytes(scene.read_bytes())
manifest=dict(placements=[e for _,e in sorted(placements.items())],cuts=cuts,public_models=public,scene_sha256=hashlib.sha256(scene.read_bytes()).hexdigest(),group=K.game_object(M.ids,'Porch Lights','porch_lights',children=objects))
(OUT/'plan.json').write_text(json.dumps(manifest,indent=2))
print(json.dumps(dict(fixtures=len(placements),active_old_faces=sum(c['removed_faces'] for c in cuts if c['active']),cuts=cuts),indent=2))
