from pathlib import Path
from collections import Counter
import sys,json,hashlib
import numpy as np
ROOT=Path(__file__).resolve().parents[3];HERE=Path(__file__).resolve().parent
OUT=ROOT/'output/riverside/searchlight-v1';STAGE=OUT/'stage';OUT.mkdir(parents=True,exist_ok=True)
sys.path.insert(0,str(ROOT/'Tools'))
import map_kit as K,riverdale_parts as P,riverside_map as R,riverdale_splice as S
import searchlight,paint,layout
modeldir=STAGE/'Assets/models/maps/riverside/searchlight-v1';modeldir.mkdir(parents=True,exist_ok=True)
paint.build(STAGE/'Assets/materials/riverside/searchlight-v1')
sl,head,axis=layout.placement();old=K.Model();layout.original(old,sl,head,axis);R.configure(old)
K.write_obj(OUT/'original-lamp.obj',old,'riverside_dressing');_,faces=S.read_obj(OUT/'original-lamp.obj')
_,published=S.read_obj(ROOT/'Assets/models/maps/riverside/riverside_dressing.obj')
assert not Counter(faces)-Counter(published),'Original lamp does not match the published geometry'
preview=K.Model();layout.original(preview,np.array((0,0,-6)),np.zeros(3),P.v(1,0,0));R.configure(preview)
K.write_obj(modeldir/'before.obj',preview,'riverside_dressing');K.write_vmdl(modeldir/'before.vmdl','models/maps/riverside/searchlight-v1','before',preview)
new=searchlight.model();R.configure(new)
triangles=K.write_obj(modeldir/'searchlight.obj',new,'riverside_dressing');K.write_vmdl(modeldir/'searchlight.vmdl','models/maps/riverside/searchlight-v1','searchlight',new)
assert not new.boxes and not new.hulls
points=np.array([p for items in new.polygons.values() for ps,n in items for p in ps])
plan=dict(standalone_triangles=triangles,original_triangles=len(faces),bounds=[points.min(0).tolist(),points.max(0).tolist()],
 files={p.relative_to(STAGE).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in STAGE.rglob('*') if p.is_file()})
(OUT/'preview-plan.json').write_text(json.dumps(plan,indent=2));print(json.dumps({k:v for k,v in plan.items() if k!='files'},indent=2))
for name in ('native.py','import_preview.cs.txt','compile.py','capture.cs.txt'):
    text=(ROOT/'Sources/Riverside/pole-transformer-v1'/name).read_text().replace('pole-transformer-v1','searchlight-v1').replace('transformer.vmdl','searchlight.vmdl')
    if name=='compile.py':text=text.replace("('before','transformer')","('before','searchlight')")
    if name=='capture.cs.txt':
        text=text.replace('"before","transformer"','"before","searchlight"').replace('Transformer comparison','Searchlight comparison')
        text=text.replace('W(54,-82,43)','W(60,-82,36)').replace('W(0,-1,4)','W(0,0,-1)').replace('FieldOfView=31','FieldOfView=29')
    (HERE/name).write_text(text)
