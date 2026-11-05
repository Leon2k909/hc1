"""Stage a narrow cut against the current published pad; never regenerate the map."""
from pathlib import Path
import hashlib,json,sys
import numpy as np
ROOT=Path(sys.argv[1]).resolve()
sys.dont_write_bytecode=True
sys.path.insert(0,str(ROOT/'Tools'))
import map_kit as K
import riverside_parts as P
import riverside_map as M
OUT=ROOT/'output/asset-improvement-20261030/riverside-speed-sign/installed'
OUT.mkdir(parents=True,exist_ok=True)
path=ROOT/'Assets/models/maps/riverside/riverside_pad.obj'
original=path.read_bytes();lines=original.decode().splitlines(keepends=True)
base=np.array((-30,85,96));f=np.array((-1,-.4,0));f/=np.linalg.norm(f)
axes=np.array((f,np.cross((0,0,1),f),(0,0,1))).T
points=[];material=None;kept=[];removed=[]
for line in lines:
    p=line.split();cut=False
    if p and p[0]=='v':points.append(np.array((float(p[3]),float(p[1]),float(p[2]))))
    if p and p[0]=='usemtl':material=p[1]
    if p and p[0]=='f' and material in ('rs_signs','rs_steel'):
        v=(np.array([points[int(t.split('/')[0])-1] for t in p[1:]])-base)@axes
        cut=(abs(v[:,0]).max()<2.2 and abs(v[:,1]).max()<15.1 and v[:,2].min()>-.01 and v[:,2].max()<110.01)
    (removed if cut else kept).append(line)
assert len(removed)==16,len(removed)
P.reset();m=K.Model();P.speed_sign(m,(-85,-30,96),(.4,-1))
assert len(P.SPEED_SIGNS)==1 and not m.polygons and len(m.boxes)==1
group=K.game_object(M.ids,'Speed-Limit Signs','speed_signs',children=M.speed_sign_objects())
target=OUT/'pad-without-old-sign.obj';target.write_bytes(''.join(kept).encode())
backup=OUT/'before-install';backup.mkdir(exist_ok=True)
for p in (path,path.with_suffix('.vmdl'),ROOT/'Assets/scenes/maps/Riverside/riverside.scene'):
    q=backup/p.name
    if q.exists():assert q.read_bytes()==p.read_bytes(),str(q)+' already exists with another baseline'
    else:q.write_bytes(p.read_bytes())
manifest=dict(source=str(path.relative_to(ROOT)),before_sha256=hashlib.sha256(original).hexdigest(),after_sha256=hashlib.sha256(target.read_bytes()).hexdigest(),removed_triangles=16,model_sha256=hashlib.sha256(path.with_suffix('.vmdl').read_bytes()).hexdigest(),group=group)
(OUT/'plan.json').write_text(json.dumps(manifest,indent=2));print(dict(removed_triangles=16,instances=1,original_post_collision_boxes=len(m.boxes)))
