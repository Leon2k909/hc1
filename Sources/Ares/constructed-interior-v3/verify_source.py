"""Check the pending generator against the reviewed reactor and support geometry."""
from pathlib import Path
from collections import Counter
import json,sys,hashlib,importlib.util
ROOT=Path(__file__).resolve().parents[3];OUT=ROOT/'output/ares/constructed-interior-v3'
sys.path.insert(0,str(ROOT/'Tools'));sys.path.insert(0,str(OUT/'install-stage/Tools'))
import map_kit as K,riverdale_splice as S
# Existing shared Tools modules adjust sys.path while loading. Bind the staged
# modules explicitly so this check cannot accidentally test an installed v1.
def staged(name):
    spec=importlib.util.spec_from_file_location(name,OUT/'install-stage/Tools'/f'{name}.py')
    module=importlib.util.module_from_spec(spec);sys.modules[name]=module;spec.loader.exec_module(module);return module
I=staged('ares_interior');C=staged('ares_constructed');A=staged('ares_map')
core,glass=K.Model(),K.Model();A.reactor(core,glass);A.configure(core)
K.write_obj(OUT/'source-reactor.obj',core,'ares_reactor')
_,generated=S.read_obj(OUT/'source-reactor.obj');_,review=S.read_obj(OUT/'stage/Assets/models/maps/ares/constructed-v3/reactor.obj')
have,want=Counter(generated),Counter(review)
diff=dict(source_only=sum((have-want).values()),review_only=sum((want-have).values()))
supports=K.Model();C.support_collision(supports)
assert len(supports.boxes)==28 and len(core.boxes)==4
assert len(core.hulls)==4 # original plinth, core, upper hood, plus the new skirt
# New risers at gallery player height remain inside the original solid core.
for paint,polys in core.polygons.items():
    if paint not in (C.STEEL,C.DARK):continue
    for points,normal in polys:
        if all(222<=p[2]<=272 for p in points):
            assert max((p[0]**2+p[1]**2)**.5 for p in points)<170.1,(paint,points)
report=dict(reactor_face_delta=diff,pump_collision_boxes=len(core.boxes),reactor_hulls=len(core.hulls),support_boxes=len(supports.boxes),gallery_risers_inside_original_collision=True)
(OUT/'source-verification.json').write_text(json.dumps(report,indent=2));print(json.dumps(report,indent=2))
assert not any(diff.values()),'Staged generator differs from reviewed reactor'
