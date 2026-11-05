"""Verify the saved replacements, retention of the original, and matched visual evidence."""
from pathlib import Path
import hashlib,json,shutil,sys,tempfile
import numpy as np
from PIL import Image
ROOT=Path(__file__).resolve().parents[3];HERE=Path(__file__).parent
OUT=Path(tempfile.gettempdir())/'belltower-wall-lantern-v2';stage=OUT/'install-stage'
def sha(p):
    with open(p,'rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()
m=json.loads((stage/'manifest.json').read_text())
assert all(sha(ROOT/p)==r['after'] for p,r in m['files'].items())
assert all(sha(ROOT/p)==h for p,h in m['protected'].items())
assert all(sha(ROOT/p)==h for p,h in m['retained_original_files'].items())
assert not m['deleted']
assert all(json.loads((OUT/f'installed-compile-{Path(p).stem}.json').read_text())['Success'] for p in m['compile_models'])
assert json.loads((OUT/'compile-retained-original.json').read_text())['Success']
# Generator placements, mirrored rotations, fixture clearances and original geometry survive regeneration.
sys.path.insert(0,str(ROOT/'Tools'));import map_kit as K,belltower_map as B,belltower_wall_lanterns as L
class Discard(K.Model):
    def polygon(self,*args,**kwargs):pass
model=Discard();rng=np.random.default_rng(2024);B._shops[0]=0
B.west_houses(model,rng);B.bakery(model,[],rng);B.inn(model,[],rng)
poses=[('west',tuple(p['position']),p['yaw']) for p in model.props if p.get('kind')=='wall_lantern']
poses += [('east',tuple(p['position']),p['yaw']) for p in model.mirrored(B.EAST_PAINTS).props if p.get('kind')=='wall_lantern']
key=lambda p:(p[0],*(round(float(v),5) for v in p[1]),round(float(p[2]),5))
assert sorted(map(key,poses))==sorted(map(key,m['placements']))
old=K.Model();assert B._legacy_wall_lantern(old,K.Wall('n',(-100,100),(-12,0),(-100,100),'+e'),0,0)
assert old.triangle_count()==960
sys.path.insert(0,str(ROOT/'Sources/Belltower/terracotta-pot-v2'));import native
native.OUT=OUT;live=native.script(HERE/'verify-installed.cs.txt','verify-installed')
status=native.call('compile_status');assert not status['IsBuilding'] and all(c['Success'] and c['Errors']==0 for c in status['Compilers'])
before=json.loads((OUT/'review/before-final-camera.json').read_text())['Capture']
after=json.loads((OUT/'installed/after-installed-camera.json').read_text())['Capture']
for key in ('Position','Angles','FieldOfView','FovAxis','Width','Height','TemporaryMatchedInspectionLight','RequestedExposure'):
    assert before[key]==after[key],key
restored=json.loads((OUT/'installed/after-installed-restore.json').read_text())
assert all(v for k,v in restored.items() if k!='Candidate')
b=np.asarray(Image.open(OUT/'review/before-final.png').convert('RGB')).astype(int)
a=np.asarray(Image.open(OUT/'installed/after-installed.png').convert('RGB')).astype(int)
diff=np.max(np.abs(b-a),axis=2)>5;outside=np.ones(diff.shape,bool);outside[190:930,330:850]=False
fraction=float(diff[outside].mean());assert fraction<.005,fraction
evidence=ROOT/'output/belltower/wall-lantern-v2';evidence.mkdir(parents=True,exist_ok=True)
for p in (OUT/'installed').glob('after-installed*'):shutil.copy2(p,evidence/p.name)
receipt=json.loads((stage/'installed.json').read_text());receipt.update(live)
receipt.update({'OriginalTriangles':960,'OriginalAsset':L.ORIGINAL,'FilesDeleted':0,'VerifiedSourceMeshes':len(m['files']),'CompiledMapDefinitions':len(m['compile_models']),'RegeneratedPlacementsVerified':24,'MatchedBeforeAndSavedAfter':True,'OutsideFixtureChangedFraction':fraction,'Restoration':restored})
(HERE/'installed.json').write_text(json.dumps(receipt,indent=2)+'\n');print(json.dumps(receipt,indent=2))
