"""Audit all published pins and stage exact old-face cuts; no map regeneration."""
from pathlib import Path
import hashlib,json,math,sys
import numpy as np
ROOT=Path(sys.argv[1]).resolve();sys.dont_write_bytecode=True
sys.path.insert(0,str(ROOT/'Tools'))
import map_kit as K
import riverside_parts as P
import riverside_map as M
OUT=ROOT/'output/asset-improvement-20261030/riverside-pole-insulator/installed';OUT.mkdir(parents=True,exist_ok=True)
P.reset();owner=K.Model();captured=[];old_wire=P.wire
def record_wire(m,a,b,*args,**kwargs):
    captured.append((list(a),list(b)))
    return old_wire(m,a,b,*args,**kwargs)
P.wire=record_wire
M.dressing(owner)
P.wire=old_wire
items=P.PIN_INSULATORS
assert len(items)==48 and sum(item[3] for item in items)==36,(len(items),sum(item[3] for item in items))
placements=[]
for i,(_,base,yaw,wired) in enumerate(items):
    contact=np.array(base)+np.array((0,0,5));attached=[]
    for a,b in captured:
        for end,other in ((a,b),(b,a)):
            if np.linalg.norm(contact-np.array(end))<.0001:attached.append(np.array(other)-np.array(end))
    assert bool(attached)==wired
    if wired:assert abs(math.sin(math.radians(yaw-math.degrees(math.atan2(attached[0][1],attached[0][0])))))<1e-9
    placements.append(dict(index=i,base=K.to_world(base).tolist(),wire_contact=K.to_world(contact).tolist(),plan_yaw=yaw,wired=wired,spans=len(attached)))
path=ROOT/'Assets/models/maps/riverside/riverside_dressing.obj';original=path.read_bytes();points=[];mat=None;kept=[];counts=[0]*48
for line in original.decode().splitlines(keepends=True):
    p=line.split();hit=None
    if p and p[0]=='v':points.append(np.array((float(p[3]),float(p[1]),float(p[2]))))
    if p and p[0]=='usemtl':mat=p[1]
    if p and p[0]=='f' and mat=='rs_glass':
        verts=np.array([points[int(t.split('/')[0])-1] for t in p[1:]])
        for i,e in enumerate(placements):
            v=verts-np.array(e['base'])
            if abs(v[:,0]).max()<1.41 and abs(v[:,1]).max()<1.41 and v[:,2].min()>-.01 and v[:,2].max()<5.01:
                assert hit is None;hit=i
    if hit is None:kept.append(line)
    else:counts[hit]+=1
assert counts==[16]*48,counts
stage=OUT/'dressing-without-old-insulators.obj';stage.write_bytes(''.join(kept).encode())
backup=OUT/'before-install';backup.mkdir(exist_ok=True)
for p in (path,path.with_suffix('.vmdl'),ROOT/'Assets/scenes/maps/Riverside/riverside.scene'):
    q=backup/p.name
    if q.exists():assert q.read_bytes()==p.read_bytes(),'Existing installation baseline differs'
    else:q.write_bytes(p.read_bytes())
plan=dict(source=str(path.relative_to(ROOT)).replace('\\','/'),before_sha256=hashlib.sha256(original).hexdigest(),after_sha256=hashlib.sha256(stage.read_bytes()).hexdigest(),model_sha256=hashlib.sha256(path.with_suffix('.vmdl').read_bytes()).hexdigest(),removed_triangles=sum(counts),placements=placements,wire_spans=captured,group=K.game_object(M.ids,'Pole Insulators','pole_insulators',children=M.pole_insulator_objects()))
(OUT/'plan.json').write_text(json.dumps(plan,indent=2))
print(json.dumps(dict(insulators=48,wired=36,unwired=12,old_faces_removed=sum(counts),wire_spans=len(captured)),indent=2))
