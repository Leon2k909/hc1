from pathlib import Path
import sys,json,hashlib,collections
ROOT=Path('C:/sbox-projects/hc1/forked-shooter-main');sys.path.insert(0,str(ROOT/'Tools'));sys.path.insert(0,str(ROOT/'Sources/CerroBlanco/gallery-vase-v1'))
from build import keys
import map_kit as K,cerroblanco_parts as C
out=ROOT/'output/cerroblanco/gallery-vase-v1';p=json.loads((out/'installed/plan.json').read_text());public=Path(p['public_obj'])
assert hashlib.sha256(public.read_bytes()).hexdigest()==p['installed_sha256']
a=collections.Counter(keys(out/'installed/before.obj'));b=collections.Counter(keys(public));assert sum((a-b).values())==34 and sum((b-a).values())==6240
old=K.Model();old.box((685,-315,0),(715,-285,40),{'default':C.WHITE,'-z':None},C.STONE)
new=K.Model();C.display_plinth(new,700,-300,w=30,thing='vase');assert old.hulls==new.hulls
assert len(old.boxes)==len(new.boxes) and str(old.boxes)==str(new.boxes)
assert new.triangle_count()==old.triangle_count()+6240
assert hashlib.sha256(public.with_suffix('.vmdl').read_bytes()).hexdigest()==p['model_sha256']
report={'installed':True,'old_triangles_removed':34,'new_triangles':6240,'generator_matches':True,'collision_unchanged':True,'approved_bin_retained':True}
(out/'installed/verification.json').write_text(json.dumps(report,indent=2));print(report)
