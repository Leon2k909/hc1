"""Stage only the approved T2 door's 16 old faces from the current shared lowland mesh."""
from pathlib import Path
from collections import Counter
import hashlib,json,sys
import numpy as np
ROOT=Path(sys.argv[1]).resolve();sys.dont_write_bytecode=True;sys.path.insert(0,str(ROOT/'Tools'))
import map_kit as K
import riverside_parts as P
import riverside_map as M
OUT=ROOT/'output/riverside/trailer-door-v1/installed';OUT.mkdir(parents=True,exist_ok=True)
def faces(data):
    points=[];mat=None
    for line in data.decode().splitlines(keepends=True):
        p=line.split();key=None
        if p and p[0]=='v':points.append(tuple(round(float(v),4) for v in p[1:]))
        if p and p[0]=='usemtl':mat=p[1]
        if p and p[0]=='f':key=(mat,tuple(sorted(points[int(t.split('/')[0])-1] for t in p[1:])))
        yield line,key
expected=Counter(k for _,k in faces((ROOT/'Assets/models/props/riverside/trailer_door_v1/review/old_door.obj').read_bytes()) if k)
path=ROOT/'Assets/models/maps/riverside/riverside_low.obj';original=path.read_bytes();kept=[];removed=[]
for line,key in faces(original):
    if key and expected[key]>0:removed.append(line);expected[key]-=1
    else:kept.append(line)
assert not sum(expected.values()) and len(removed)==16
stage=OUT/'low-without-old-door.obj';stage.write_bytes(''.join(kept).encode())
backup=OUT/'before-install';backup.mkdir(exist_ok=True)
for p in (path,path.with_suffix('.vmdl'),ROOT/'Assets/scenes/maps/Riverside/riverside.scene'):
    q=backup/p.name
    if q.exists():assert q.read_bytes()==p.read_bytes(),'Installation baseline changed'
    else:q.write_bytes(p.read_bytes())
P.reset();name,origin,yaw,L,W,tint,side,seed,extra=M.LOW_TRAILERS[0]
part,_=M.build_trailer(name,L,W,tint,side,seed,extra);P.carry(K.Model(),part,(*origin,0),yaw)
assert len(P.TRAILER_DOORS)==1
group=K.game_object(M.ids,'Trailer Entry Doors','trailer_doors',children=M.trailer_door_objects())
position=list(map(float,group['Children'][0]['Position'].split(',')));assert np.allclose(position,(995,891.826512653,30),atol=1e-5)
plan=dict(source=str(path.relative_to(ROOT)).replace('\\','/'),before_sha256=hashlib.sha256(original).hexdigest(),after_sha256=hashlib.sha256(stage.read_bytes()).hexdigest(),model_sha256=hashlib.sha256(path.with_suffix('.vmdl').read_bytes()).hexdigest(),removed_triangles=16,group=group)
(OUT/'plan.json').write_text(json.dumps(plan,indent=2));print(json.dumps(dict(doors=1,old_faces_removed=16,position=position),indent=2))
