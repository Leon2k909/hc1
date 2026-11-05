from pathlib import Path
from collections import Counter
import json,sys,hashlib
ROOT=Path(__file__).resolve().parents[3];HERE=Path(__file__).resolve().parent
OUT=ROOT/'output/riverside/pole-transformer-v1';STAGE=OUT/'stage';OUT.mkdir(parents=True,exist_ok=True)
sys.path.insert(0,str(ROOT/'Tools'))
import map_kit as K,riverdale_parts as RP,riverside_map as R,riverdale_splice as S
import transformer,paint,layout
modeldir=STAGE/'Assets/models/maps/riverside/pole-transformer-v1';modeldir.mkdir(parents=True,exist_ok=True)
paint.build(STAGE/'Assets/materials/riverside/pole-transformer-v1')
old=K.Model();RP.cylinder(old,(0,0),9,-16,16,'rs_steel',12,top='rs_steel',bottom='rs_steel');R.configure(old)
K.write_obj(modeldir/'before.obj',old,'riverside_dressing');K.write_vmdl(modeldir/'before.vmdl','models/maps/riverside/pole-transformer-v1','before',old)
# Bind the before image to an actual published can, retaining its original UVs and normals.
first=layout.placements()[0]['centre'];sample=K.Model()
RP.cylinder(sample,first,9,first[2]-16,first[2]+16,'rs_steel',12,top='rs_steel',bottom='rs_steel');R.configure(sample)
K.write_obj(OUT/'first_original.obj',sample,'riverside_dressing');_,faces=S.read_obj(OUT/'first_original.obj')
_,published=S.read_obj(ROOT/'Assets/models/maps/riverside/riverside_dressing.obj')
assert not Counter(faces)-Counter(published),'Original transformer differs from published can'
translated=[]
for mat,corners in faces:
    transformed=[]
    for p,uv,n in corners:
        x,z,y=map(float,p.split());p=f'{x+first[0]:.3f} {z-first[2]:.3f} {y-first[1]:.3f}'
        transformed.append((p,uv,n))
    translated.append((mat,tuple(transformed)))
S.write_obj(modeldir/'before.obj',['mtllib before.mtl\n','o before\n'],translated)
new=transformer.model();triangles=K.write_obj(modeldir/'transformer.obj',new,'riverside_dressing');K.write_vmdl(modeldir/'transformer.vmdl','models/maps/riverside/pole-transformer-v1','transformer',new)
assert not new.boxes and not new.hulls
points=[p for faces in new.polygons.values() for ps,n in faces for p in ps]
import numpy as np
points=np.array(points)
manifest=dict(standalone_triangles=triangles,bounds=[points.min(axis=0).tolist(),points.max(axis=0).tolist()],
              files={p.relative_to(STAGE).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in STAGE.rglob('*') if p.is_file()})
(OUT/'preview-plan.json').write_text(json.dumps(manifest,indent=2));print(json.dumps({k:v for k,v in manifest.items() if k!='files'},indent=2))
helper=(ROOT/'Sources/Spillway/service-cabinet-v1/native.py').read_text().replace('output/spillway/service-cabinet-v1','output/riverside/pole-transformer-v1')
(HERE/'native.py').write_text(helper)
script=(ROOT/'Sources/Spillway/service-cabinet-v1/import_preview.cs.txt').read_text().replace('output/spillway/service-cabinet-v1','output/riverside/pole-transformer-v1').replace('install-plan.json','preview-plan.json').replace('Assets/materials/spillway/service-cabinet-v1/','Assets/materials/riverside/pole-transformer-v1/').replace('Assets/models/maps/spillway/service-cabinet-v1/','Assets/models/maps/riverside/pole-transformer-v1/')
(HERE/'import_preview.cs.txt').write_text(script)
