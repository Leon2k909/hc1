"""Prepare an atomic native transaction from the visually checked interior stage."""
from pathlib import Path
import json,hashlib,sys,ast,importlib.util,re
import numpy as np
import native
ROOT=native.ROOT;OUT=native.OUT
sys.path.insert(0,str(ROOT/'Tools'))
import ares_map as original
import map_kit as K
import ares_interior as interior

manifest=json.loads((OUT/'manifest.json').read_text())
stage=OUT/'install-stage'
changes=[]
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def add(relative):
    src=ROOT/relative;candidate=stage/relative;before=OUT/'before'/relative
    assert candidate.exists(),relative
    expected=sha(before) if before.exists() else None
    current=sha(src) if src.exists() else None
    assert current==expected,f'Input changed since preview: {relative}'
    changes.append(dict(relative=relative,before=expected,after=sha(candidate)))
for model in manifest['models']:
    # Derive the live document from the exact preview document, changing only
    # its primary OBJ path. Byte writes preserve the complete physics suffix.
    document=(OUT/'stage/Assets'/model['preview']).read_bytes().decode('utf-8')
    primary=re.search(r'filename\s*=\s*"([^"]+)"',document).group(1)
    assert primary.startswith('models/maps/ares/interior-v1/')
    document=document.replace(primary,model['primary'][7:],1)
    (stage/model['document']).write_bytes(document.encode('utf-8'))
    add(model['primary']);add(str(Path(model['primary']).with_suffix('.mtl')).replace('\\','/'));add(model['document'])
add('Tools/ares_map.py')
assert sha(ROOT/'Assets/scenes/maps/Ares/ares.scene')==manifest['scene_sha256'],'Scene changed since snapshot'

# Check the generator's solid shapes independently of the published ModelDoc.
# These source edits must not silently alter the next generated collision mesh.
spec=importlib.util.spec_from_file_location('ares_interior_staged_map',stage/'Tools/ares_map.py')
revised=importlib.util.module_from_spec(spec);spec.loader.exec_module(revised)
def collisions(module):
    hall=K.Model();glass=K.Model();core=K.Model()
    for name in ('floors','hall_walls','galleries','ring_and_bridges','hall_stairs'):
        getattr(module,name)(hall)
    for name in ('window_wall','control_rooms','wings','concourse'):
        getattr(module,name)(hall,glass)
    module.reactor(core,glass)
    def rounded(value):
        if isinstance(value,(tuple,list)):return [rounded(x) for x in value]
        if isinstance(value,np.ndarray):return np.round(value,8).tolist()
        if isinstance(value,(np.floating,float)):return round(float(value),8)
        return value
    return rounded([hall.boxes,hall.hulls,core.boxes,core.hulls,glass.boxes,glass.hulls])
reuse='--reuse-collision-proof' in sys.argv and (OUT/'source-collision-verification.json').exists()
if reuse:
    previous=json.loads((OUT/'install-plan.json').read_text())
    row=next(x for x in previous if x['relative']=='Tools/ares_map.py')
    assert row['after']==sha(stage/'Tools/ares_map.py'),'Generator changed since collision check'
    # The rebuilt architecture is render-only, and the build independently
    # checks that all four pump collision boxes remain identical.
    assert manifest['collision_unchanged'] and manifest['pump_collision_boxes_unchanged']
else:
    assert collisions(original)==collisions(revised),'Generator collision changed'
architecture=K.Model();interior.append_hall(architecture)
assert not architecture.boxes and not architecture.hulls,'Architecture introduced collision'
(OUT/'source-collision-verification.json').write_text(json.dumps(dict(Identical=True,Scope='Hall, wings, concourse, doors, stairs, glazing, reactor and pumps; source-generated boxes and hulls'),indent=2)+'\n')
(OUT/'install-plan.json').write_text(json.dumps(changes,indent=2)+'\n')
print(json.dumps(dict(Ready=True,Applied=False,Files=len(changes),GeneratedCollisionIdentical=True),indent=2))
