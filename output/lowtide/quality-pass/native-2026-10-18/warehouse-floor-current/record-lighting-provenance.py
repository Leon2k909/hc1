"""Preserve v3 provenance and record the saved, reviewed native v4 bake."""
import datetime
import hashlib
import json
from pathlib import Path
import shutil

ROOT=Path(__file__).resolve().parents[5]
OUT=Path(__file__).resolve().parent
REL=OUT.relative_to(ROOT).as_posix()
SOURCE=ROOT/'Sources/Lowtide/lighting'
def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def read(p): return json.loads(p.read_text())

verified=read(OUT/'lighting/verification.json')
assert sha(ROOT/'Assets/scenes/maps/Lowtide/lowtide.scene')==verified['scene_sha256']
assert sha(SOURCE/'warehouse-lighting.json')==verified['source_sha256']
before=read(OUT/'lighting-before/hashes.json')
provenance=SOURCE/'bake-provenance.json'
historical=SOURCE/'bake-provenance-v3.json'
old=read(provenance)
assert old['lightingDataSha256']==before['Sources/Lowtide/lighting/warehouse-lighting.json']
if historical.exists(): assert historical.read_bytes()==provenance.read_bytes()
else: shutil.copyfile(provenance,historical)
textures=[]
for row in verified['compiled_textures']:
    path='Assets/'+row['Target']+'_c'
    assert sha(ROOT/path)==row['Hash']
    textures.append(dict(path=path,bytes=(ROOT/path).stat().st_size,sha256=row['Hash'],
        width=row['Width'],height=row['Height'],depth=row['Depth']))
data=dict(engineVersion='26.10.13a',observedUtc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
    nativeApi='IndirectLightVolume.BakeProbes',status=verified['status'],
    geometrySha256={p:sha(ROOT/p) for p in old['geometrySha256']},
    floorMaterialSha256=read(OUT/'promotion.json')['resources'],
    sceneBeforeLightingSha256=before['Assets/scenes/maps/Lowtide/lowtide.scene'],
    savedSceneSha256=verified['scene_sha256'],lightingDataSha256=verified['source_sha256'],
    textures=textures,volumes=2,probesPerVolume=1200,runtimeIntensity=4,runtimeContrast=.85,
    evidence=REL+'/lighting/verification.json',reviewedViewportCaptures=6,
    previousProvenance=historical.relative_to(ROOT).as_posix(),
    rebakeWhen='Static warehouse geometry, materials, fixtures or daylight changes',
    performanceVerified=False)
provenance.write_text(json.dumps(data,indent=2)+'\n')
print(json.dumps(dict(status=data['status'],retainedTextures=len(textures),historicalProvenance=data['previousProvenance'])))
