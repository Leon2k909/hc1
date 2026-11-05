"""Stage exact cuts for the four published sodium heads, retaining all shared geometry."""
from pathlib import Path
import hashlib,json,math,sys
import numpy as np
ROOT=Path(sys.argv[1]).resolve();sys.dont_write_bytecode=True
sys.path.insert(0,str(ROOT/'Tools'))
import map_kit as K
import riverside_parts as P
import riverside_map as M
OUT=ROOT/'output/asset-improvement-20261030/riverside-street-lamp/installed';OUT.mkdir(parents=True,exist_ok=True)
P.reset();owner=K.Model()
for k,c in enumerate(M.POLES_WEST):
    if k in (2,4):P.pole(owner,c,430,facing=(1,.1),arms=2,lamp=('sodium',(1,.15)),seed=k)
for k,c in enumerate(M.POLES_EAST):
    if k<2:P.pole(owner,c,400,facing=(-1,0),arms=1,lamp=('sodium',(-1,-.3)),seed=10+k)
assert len(P.STREET_LIGHTS)==4
placements=[]
for _,position,yaw in P.STREET_LIGHTS:
    heading=(math.cos(math.radians(yaw)),math.sin(math.radians(yaw)));engine_yaw=K.plan_yaw(heading);a=math.radians(engine_yaw)
    placements.append(dict(position=K.to_world(position).tolist(),yaw=engine_yaw,axes=np.array(((math.cos(a),-math.sin(a),0),(math.sin(a),math.cos(a),0),(0,0,1))).tolist()))
path=ROOT/'Assets/models/maps/riverside/riverside_dressing.obj';original=path.read_bytes();points=[];mat=None;kept=[];counts=[0]*4
for line in original.decode().splitlines(keepends=True):
    p=line.split();hit=None
    if p and p[0]=='v':points.append(np.array((float(p[3]),float(p[1]),float(p[2]))))
    if p and p[0]=='usemtl':mat=p[1]
    if p and p[0]=='f' and mat in ('rs_alu','rs_lamp_sodium'):
        verts=np.array([points[int(t.split('/')[0])-1] for t in p[1:]])
        for i,e in enumerate(placements):
            v=(verts-np.array(e['position']))@np.array(e['axes'])
            if abs(v[:,0]).max()<11.01 and abs(v[:,1]).max()<5.01 and v[:,2].min()>-1.61 and v[:,2].max()<3.51:
                assert hit is None;hit=i
    if hit is None:kept.append(line)
    else:counts[hit]+=1
assert counts==[14]*4,counts
stage=OUT/'dressing-without-old-heads.obj';stage.write_bytes(''.join(kept).encode())
backup=OUT/'before-install';backup.mkdir(exist_ok=True)
for p in (path,path.with_suffix('.vmdl'),ROOT/'Assets/scenes/maps/Riverside/riverside.scene'):
    q=backup/p.name
    if q.exists():assert q.read_bytes()==p.read_bytes(),'Existing baseline differs'
    else:q.write_bytes(p.read_bytes())
plan=dict(source=str(path.relative_to(ROOT)).replace('\\','/'),before_sha256=hashlib.sha256(original).hexdigest(),after_sha256=hashlib.sha256(stage.read_bytes()).hexdigest(),model_sha256=hashlib.sha256(path.with_suffix('.vmdl').read_bytes()).hexdigest(),removed_triangles=56,placements=placements,group=K.game_object(M.ids,'Streetlight Heads','street_lights',children=M.street_light_objects()))
(OUT/'plan.json').write_text(json.dumps(plan,indent=2));print(dict(instances=4,old_faces_removed=sum(counts),placements=placements))
