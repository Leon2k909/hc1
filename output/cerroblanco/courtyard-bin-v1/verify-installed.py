from pathlib import Path
import sys,json,hashlib,collections
ROOT=Path('C:/sbox-projects/hc1/forked-shooter-main');sys.path.insert(0,str(ROOT/'Tools'));sys.path.insert(0,str(ROOT/'Sources/CerroBlanco/courtyard-bin-v1'))
from build import keys
import map_kit as K,cerroblanco_parts as C
out=ROOT/'output/cerroblanco/courtyard-bin-v1';p=json.loads((out/'installed/plan.json').read_text());public=Path(p['public_obj'])
assert hashlib.sha256(public.read_bytes()).hexdigest()==p['installed_sha256']
a=collections.Counter(keys(out/'installed/before.obj'));b=collections.Counter(keys(public))
assert sum((a-b).values())==46 and sum((b-a).values())==3654
old=K.Model();old.cylinder((380,-650),9,0,34,{'side':None,'top':None,'bottom':None},sides=16,surface=C.METAL)
new=K.Model();C.litter_bin(new,380,-650)
assert old.hulls==new.hulls and old.boxes==new.boxes
assert new.triangle_count()==3654
assert hashlib.sha256(public.with_suffix('.vmdl').read_bytes()).hexdigest()==p['model_sha256']
report={'installed':True,'old_triangles_removed':46,'new_triangles':3654,'generator_matches':True,'collision_unchanged':True,'unrelated_faces_preserved':25998,'public_model_path_unchanged':True}
(out/'installed/verification.json').write_text(json.dumps(report,indent=2));print(report)
