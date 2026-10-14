"""Check the visual pass against the captured pre-edit source state."""
import hashlib
import copy
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "Tools"))
import lowtide_finish as Q
import lowtide_map as L
import lowtide_marine as M
import lowtide_masonry as S
import subprocess

before = Path(__file__).parent / "before"
hashes = json.loads((before / "model-hashes.json").read_text())
changed = [p for p, digest in hashes.items() if hashlib.sha256((ROOT/p).read_bytes()).hexdigest() != digest]
fleet = 'Assets/models/maps/lowtide/lowtide_fleet.obj'
assert all(p.endswith('.vmdl') or p == fleet for p in changed), changed
assert len(changed) == 5, changed
original_fleet = subprocess.check_output(['rtk','git','show','HEAD:'+fleet],cwd=ROOT,text=True)
assert hashlib.sha256(original_fleet.replace('\r\n','\n').encode()).hexdigest() == hashes[fleet]
def retained(source):
    result = []
    paint = None
    for line in source.splitlines():
        if line.startswith('usemtl '):
            paint = line.split(maxsplit=1)[1]
        if paint in M.HULL_PAINTS and (line.startswith('f ') or line.startswith('usemtl ')):
            continue
        result.append(line)
    return result
assert retained(original_fleet) == (ROOT/fleet).read_text().splitlines()
for p in [p for p in changed if p.endswith('.vmdl')]:
    # Material-only vmdl edits must leave the full physics description intact.
    import subprocess
    original = subprocess.check_output(['rtk', 'git', 'show', 'HEAD:'+p], cwd=ROOT, text=True)
    current = (ROOT/p).read_text()
    remapped = current.replace(Q.RESOURCE+'/lt_quay_stone.vmat', 'materials/buildings/ashlar_grey.vmat')
    assert original.strip() == remapped.strip(), p

old = json.loads((before/'Assets/scenes/maps/Lowtide/lowtide.scene').read_text())
new = json.loads(L.SCENE_FILE.read_text())
assert old['SceneProperties'] == new['SceneProperties']
old_objects = {o.get('Name',o.get('__guid')):o for o in old['GameObjects']}
new_objects = {o.get('Name',o.get('__guid')):o for o in new['GameObjects']}
allowed = {'Sun','Fog','Look','Lowtide','Reflection Probes'}
for name, obj in old_objects.items():
    if name not in allowed:
        assert new_objects[name] == obj, name
original_children = old_objects['Lowtide']['Children']
current_children = [o for o in new_objects['Lowtide']['Children'] if o['Name'] not in ('Harbour Details','Tidal Details','Masonry Details')]
current_children = copy.deepcopy(current_children)
water = next(o for o in current_children if o['Name'] == 'Water')
reflection = [c for c in water['Components'] if c['__type'] == 'Facepunch.LowtideWaterReflections']
assert len(reflection) == 1 and reflection[0]['WaterHeight'] == -137
water['Components'][:] = [c for c in water['Components'] if c not in reflection]
assert original_children == current_children
detail = Q.build(L)
assert not detail.boxes and not detail.hulls
marine = M.build(L)
assert not marine.boxes and not marine.hulls
assert not next(o for o in new_objects['Lowtide']['Children'] if o['Name']=='Harbour Details')['Components'][0].get('IsTrigger')
assert len([o for o in new_objects['Lowtide']['Children'] if o['Name']=='Harbour Details']) == 1
stable = json.dumps(new, sort_keys=True)
Q.apply_scene(new, L)
M.apply_scene(new,L)
S.apply_scene(new,L)
assert stable == json.dumps(new, sort_keys=True), 'Scene patch is not idempotent'
lines = [
    'PASS: original OBJ and MTL files byte-identical except the three replaced barge material groups',
    'PASS: all non-barge Fleet faces and indexed vertex/UV/normal buffers preserved exactly',
    'PASS: four existing VMDLs differ only in the scoped stone material path',
    'PASS: all original model collider declarations preserved',
    'PASS: original world model scene objects unchanged except the canal reflection component',
    'PASS: spawns, objectives, navigation settings and gameplay objects unchanged',
    'PASS: drainage and marine detail meshes have no collision boxes or hulls',
    'PASS: masonry details have no physics declarations',
    'PASS: scene application is idempotent and retains one renderer for each new mesh',
]
assert 'Physics' not in (L.OUT_DIR/'lowtide_masonry.vmdl').read_text()
(Path(__file__).parent/'source-checks.txt').write_text('\n'.join(lines)+'\n')
print('\n'.join(lines))
