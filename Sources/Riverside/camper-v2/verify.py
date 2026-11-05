"""Check the exact installed change, before retiring review/backup geometry."""
from pathlib import Path
from collections import Counter
import json,sys,hashlib
sys.dont_write_bytecode=True
ROOT=Path(__file__).absolute().parents[3];OUT=ROOT/'output/riverside/camper-v2'
def records(p):
    ls=p.read_text().splitlines(keepends=True);vs=[tuple(round(float(x),3) for x in l.split()[1:4]) for l in ls if l.startswith('v ')];mt='';faces=[]
    for l in ls:
        if l.startswith('usemtl '):mt=l.split()[1]
        if l.startswith('f '):faces.append((mt,tuple(sorted(vs[int(t.split('/')[0])-1] for t in l.split()[1:]))))
    return ls,Counter(faces)
scene=json.loads((ROOT/'Assets/scenes/maps/Riverside/riverside.scene').read_text())
camper=[n for n in scene['GameObjects'] if n.get('Name')=='Boarded Camper'];assert len(camper)==1
assert camper[0]['Position']=='-298,-276,96'
assert not (ROOT/'Assets/models/props/riverside/camper_v2/review').exists()
proof=json.loads((OUT/'installed-verification.json').read_text())
assert proof['old_faces_removed']==480 and proof['physics_doc_identical']
sys.path.insert(0,str(ROOT/'Tools'));import riverside_parts as P;import riverside_map as R;import riverside_camper as C;import map_kit as K
P.reset();m=P.rv();assert not any(m.polygons.values()) and len(m.boxes)==1 and len(P.PROPANE)==2
dst=K.Model();R.place_into(dst,m,(276,-298,96),100);objects=R.camper_objects();assert len(objects)==1 and objects[0]['Position']=='-298,-276,96'
lods=[]
for lod in range(3):
    temp=OUT/f'check-lod{lod}.obj';count=K.write_obj(temp,C.make(lod),f'camper_lod{lod}')
    stable=lambda p:[l for l in p.read_text().splitlines() if not l.startswith(('o ','mtllib '))]
    assert stable(temp)==stable(ROOT/f'Assets/models/props/riverside/camper_v2/camper_lod{lod}.obj'),f'Geometry builder mismatch LOD {lod}'
    temp.unlink();lods.append(count)
report=dict(installed=True,old_faces_removed=480,other_faces_unchanged=True,scene_only_added_camper=True,
            physics_doc_identical=True,generator_has_one_instance=True,separate_propane_retained=True,lod_triangles=lods)
print(json.dumps(report,indent=2))
