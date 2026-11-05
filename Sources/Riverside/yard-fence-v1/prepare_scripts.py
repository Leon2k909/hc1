from pathlib import Path
ROOT=Path(__file__).absolute().parents[3];HERE=Path(__file__).absolute().parent
template=(ROOT/'Sources/Riverside/store-timber-steps-v1/build.py').read_text();a=template.index('counts=[')
s='''from pathlib import Path
import sys,json,hashlib,re,collections,ast
import numpy as np
sys.dont_write_bytecode=True
ROOT=Path(__file__).absolute().parents[3];sys.path.insert(0,str(ROOT/'Tools'));sys.path.insert(0,str(Path(__file__).absolute().parent))
import map_kit as K,riverdale_parts as G,riverside_parts as P,riverside_map as R
from geometry import make
OUT=ROOT/'output/riverside/yard-fence-v1';STAGE=OUT/'stage';RES='models/props/riverside/yard_fence_v1';MODEL=STAGE/'Assets'/RES;MODEL.mkdir(parents=True,exist_ok=True)
origin=np.array((-1400.,960.,0.))
'''+template[a:]
for a,b in [('store_without_steps','dressing_without_fence'),('steps_lod','fence_lod'),('steps.vmdl','fence.vmdl'),('legacy_steps','legacy_fence'),('riverside_store.vmdl','riverside_dressing.vmdl')]:s=s.replace(a,b)
a=s.index('old=K.Model();');b=s.index('tree=ast.parse(',a)
s=s[:a]+'''old=K.Model();P.plank_fence(old,[(-1400,960),(-1400,1460)],seed=1);R.configure(old);K.write_obj(OUT/'legacy_absolute.obj',old,'old_fence')
local=K.Model();P.plank_fence(local,[(0,0),(500,0)],seed=1);local.boxes.clear();local.hulls.clear();R.configure(local);K.write_model(MODEL,RES,'legacy_fence',local)
'''+s[b:]
s=s.replace('assert len(cut)==36 and not +want','assert len(cut)>500 and not +want').replace('yaw=0,removed_old_triangles=36','yaw=90,removed_old_triangles=len(cut)')
(HERE/'build.py').write_text(s)
for name in ('review.py','verify.py','import.cs.txt'):
 s=(ROOT/'Sources/Riverside/store-timber-steps-v1'/name).read_text()
 for a,b in [('store-timber-steps-v1','yard-fence-v1'),('store_timber_steps_v1','yard_fence_v1'),('legacy_steps','legacy_fence'),('steps.vmdl','fence.vmdl'),('steps_lod','fence_lod')]:s=s.replace(a,b)
 (HERE/name).write_text(s)
s=(ROOT/'Sources/Riverside/store-timber-steps-v1/context.cs.txt').read_text()
for a,b in [('store-timber-steps-v1','yard-fence-v1'),('store_timber_steps_v1/steps.vmdl','yard_fence_v1/fence.vmdl'),('store_timber_steps_v1/legacy_steps.vmdl','yard_fence_v1/legacy_fence.vmdl'),('store_timber_steps_v1/store_without_steps.vmdl','yard_fence_v1/dressing_without_fence.vmdl'),('riverside_store.vmdl','riverside_dressing.vmdl'),('Local(-90,-100,64),Local(15,0,12),52f','Local(-300,-250,64),Local(0,-250,30),80f'),('StepMaterials','FenceMaterials')]:s=s.replace(a,b)
s=s.replace('("entrance",Local(-300,-250,64),Local(0,-250,30),80f,true),','("whole",Local(-300,-250,64),Local(0,-250,30),80f,true),\n    ("detail",Local(-100,-235,64),Local(0,-250,34),62f,true),')
(HERE/'context.cs.txt').write_text(s)
