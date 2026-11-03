from pathlib import Path
import json,sys,hashlib
import numpy as np
ROOT=Path(__file__).resolve().parents[3];sys.path.insert(0,str(ROOT/'Tools'))
import map_kit as K
HERE=Path(__file__).parent;OUT=ROOT/'output/collider-tool-cabinet-accepted-20261031'
shapes=json.loads((HERE/'candidate.json').read_text())['collisionShapes'];hulls=[]
for shape in shapes:
    if shape['kind']!='hull' or shape['surface']!='rubber':continue
    points=np.asarray(shape['points']);chosen=sorted(set(np.argmin(points,axis=0).tolist()+np.argmax(points,axis=0).tolist()))
    while len(chosen)<32:
        distances=np.min(np.linalg.norm(points[:,None]-points[chosen][None,:],axis=2),axis=1)
        chosen.append(int(np.argmax(distances)))
    shape['points']=points[chosen].tolist();hulls.append((shape['points'],'rubber'))
assert len(hulls)==4
if not (OUT/'before/accepted-physics.json').exists():(OUT/'before/accepted-physics.json').write_text(json.dumps(shapes,indent=2)+'\n')
(HERE/'accepted-physics.json').write_text(json.dumps(shapes,indent=2)+'\n')
relative='Assets/models/props/collider/tool-cabinet-trial-v1/installed_hulls_rubber.obj'
stage=OUT/'stage'/relative;stage.parent.mkdir(parents=True,exist_ok=True);K.write_hulls_obj(stage,[points for points,surface in hulls])
p=ROOT/'Assets/models/maps/collider/collider_detail.vmdl';s=p.read_text();assert s.count('models/props/collider/tool-cabinet-trial-v1/after_hulls_rubber.obj')==1
s=s.replace('models/props/collider/tool-cabinet-trial-v1/after_hulls_rubber.obj','models/props/collider/tool-cabinet-trial-v1/installed_hulls_rubber.obj')
target=OUT/'stage/Assets/models/maps/collider/collider_detail.vmdl';target.write_text(s,newline='\n')
receipt=dict(source=relative,verticesPerTyreHull=32,visibleMeshUnchanged=True,originalPointsRetainedInBackup=True,
             previousModelSHA256=hashlib.sha256(p.read_bytes()).hexdigest())
(OUT/'hull-fix.json').write_text(json.dumps(receipt,indent=2)+'\n')
