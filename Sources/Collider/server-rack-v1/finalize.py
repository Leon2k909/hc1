"""Verify accepted native repair; synchronize only matching primary staged inputs."""
from pathlib import Path
from datetime import datetime, timezone
import hashlib
import json
import re
import shutil

ROOT=Path(__file__).resolve().parents[3]
OUT=ROOT/'output/collider-server-rack-20261027'
STAGE=OUT/'stage-v1'


def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()


def read(path):return json.loads(path.read_text())


def tool_json(path):
    result=read(path)
    assert not result.get('isError'),result
    return json.loads(next(c['text'] for c in result['content'] if c['type']=='text'))


manifest=read(STAGE/'manifest.json')
imported=read(OUT/'native-import.json')
compile_result=tool_json(OUT/'compile-v1/asset_compile.json')
assert compile_result['Success']
assert imported['OtherPhysicsPreserved'] and imported['SceneSourcePreserved'] and imported['EditorStatePreserved']
clearance=read(OUT/'clearance-after.json')
assert clearance['Checked']==40 and clearance['Failed']==0
assert all(clearance[k] for k in ('OldRackVolumeClear','NewRackCollisionPresent','NewRackOnFloor','ModelValid'))
nav=read(OUT/'native-validation.json')
assert nav['Checked']==68 and not nav['Failed'] and not nav['MissingModels'] and not nav['MissingMaterials']
stairs=read(OUT/'stair-validation.json')
assert stairs['Passed'] and len(stairs['Stairs'])==4
capture=read(OUT/'after/capture-report.json')
assert all(capture[k] for k in ('NativeEngineCapture','FullTextureCapture','SceneDirtyStatePreserved','GamePreserved','SelectedDocumentPreserved'))
geometry=read(OUT/'geometry-check.json')
assert geometry['Triangles']==manifest['addedTriangles'] and geometry['BadWinding']==0 and geometry['AllFinite']
for rel,value in manifest['protected'].items():
    assert sha(ROOT/'Assets'/rel)==value,rel
for rel,value in manifest['source'].items():
    assert sha(ROOT/rel)==value,rel
map_source=(ROOT/'Tools/collider_map.py').read_text()
assert 'for e,n in ((-430,80),SR.POSITION):' in map_source and 'SR.build(m,e,n)' in map_source
synced=[]
for entry in manifest['files']:
    relative=entry['relative']; installed=ROOT/'Assets'/relative
    assert sha(installed)==entry['after']
    assert capture['AssetSourcesSHA256'][relative]==entry['after']
    target=ROOT/'output/collider/stage/assets'/relative
    assert target.exists() and sha(target) in (entry['before'],entry['after']), 'Different primary build revision: '+relative
    if sha(target)==entry['before']:
        backup=OUT/'primary-before'/relative
        backup.parent.mkdir(parents=True,exist_ok=True)
        if not backup.exists():shutil.copy2(target,backup)
        assert sha(backup)==entry['before']
        incoming=target.with_name(target.name+'.rack-incoming')
        try:
            shutil.copy2(installed,incoming)
            assert sha(incoming)==entry['after']
            assert sha(target)==entry['before']
            incoming.replace(target)
        finally:incoming.unlink(missing_ok=True)
    assert sha(target)==entry['after']
    synced.append(relative)
record={'Revision':manifest['revision'],'CheckedAt':datetime.now(timezone.utc).isoformat(),
    'Installed':{e['relative']:e['after'] for e in manifest['files']},'Position':manifest['newRackPosition'],
    'Size':manifest['newSize'],'PrimaryStageSynced':synced,'OtherPhysicsPreserved':True,
    'SceneSHA256':manifest['protected']['scenes/maps/Collider/collider.scene'],
    'NativeCompileSucceeded':True,'StairWidthChecksPassed':40,'StairRoutesPassed':4,'MapPositionsPassed':68,
    'SourceSHA256':{p:sha(ROOT/p) for p in ('Tools/collider_server_rack.py','Sources/Collider/server-rack-v1/stage.py')},
    'Screenshots':{p.name:sha(p) for p in (OUT/'after').glob('*.png')},
    'EditorStatePreserved':True,'FullMatchPerformanceTested':False}
(ROOT/'Sources/Collider/server-rack-v1/installed.json').write_text(json.dumps(record,indent=2)+'\n')
(OUT/'published.json').write_text(json.dumps(record,indent=2)+'\n')
print(json.dumps({'Published':True,'Synced':len(synced),'StairWidth':40,'StairRoutes':4,'MapPositions':68}))
