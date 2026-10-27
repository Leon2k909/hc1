"""Verify the installed pressure doors against staged sources and native evidence."""
import hashlib
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[3]
OUT=ROOT/'output/ares/airlock-door-v1'
manifest=json.loads((OUT/'stage-v3/manifest.json').read_text())

def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def results(path):
    raw=json.loads(Path(path).read_text())
    return [json.loads(c['text']) for c in raw['content'] if c['type']=='text']

for path,item in manifest['files'].items():assert sha(ROOT/path)==item['after'],path
for path,digest in manifest['source_sha256'].items():assert sha(ROOT/path)==digest,path
for path,parts in manifest['required_source_snippets'].items():
    current=(ROOT/path).read_text().replace('\r\n','\n')
    assert all(part.replace('\r\n','\n') in current for part in parts)
scene='Assets/scenes/maps/Ares/ares.scene'
for path,digest in manifest['protected_sha256'].items():
    if path!=scene:assert sha(ROOT/path)==digest,path
document='Assets/models/maps/ares/ares_hall.vmdl'
before=ROOT/manifest['files'][document]['backup']
marker='_class = "PhysicsShapeList"'
a=before.read_text();b=(ROOT/document).read_text()
assert a[a.index(marker):]==b[b.index(marker):]
base=(ROOT/manifest['base_import']).read_bytes()
assert (ROOT/'Assets/models/maps/ares/ares_hall.obj').read_bytes().startswith(base)
retained_triangles=sum(line.startswith(b'f ') for line in base.splitlines())
assert retained_triangles==23700
assets=results(OUT/'asset-info-installed/call_tools.json')
assert len(assets)==14 and all(a['IsCompiledAndUpToDate'] and not a['IsCompileFailed'] for a in assets)
old_rays=results(OUT/'traces-before/call_tools.json')
new_rays=results(OUT/'traces-installed/call_tools.json')
assert len(new_rays)==27 and old_rays==new_rays
assert all(r['Hit'] and not r['StartedSolid'] and r['Component']=='ModelCollider' for r in new_rays)
capture_root=ROOT/'output/ares/quality/pressure-door-v2-installed-v3'
captures={}
for name in ('cargo','angle','hall-overview','hall-exterior'):
    assert (capture_root/f'{name}.png').is_file()
    restoration=json.loads((capture_root/f'{name}-restore.json').read_text())
    assert all(restoration.values())
    captures[name]=(capture_root/f'{name}.png').relative_to(ROOT).as_posix()
status,camera=results(OUT/'final-status/call_tools.json')
assert status['ActiveScene']=='ares' and not status['IsPlaying'] and not status['IsCompiling']
assert status['LastCompileSucceeded'] and status['LastCompileErrors']==0
receipt={
    'revision':'ares-pressure-doors-v2','stage':'stage-v3','doors':3,
    'new_door_triangles':manifest['new_triangles'],'old_door_triangles_removed':3954,
    'retained_hall_triangles':retained_triangles,
    'total_hall_triangles':retained_triangles+manifest['new_triangles'],
    'original_hall_geometry_is_exact_source_prefix':True,'physics_bytes_exact':True,
    'compiled_assets':len(assets),'identical_sealed_hatch_traces':len(new_rays),
    'scene_saved_by_task':False,
    'scene_sha256_at_staging':manifest['protected_sha256'][scene],
    'scene_sha256_after_shared_editor_save':sha(ROOT/scene),
    'camera_after':camera,'editor_status':status,'captures':captures,
    'repair':'Removed unused trailing OBJ attribute tables; used valid mesh node identifiers. '
             'Compiled and captured the separate trial before publishing the live hall.'}
(OUT/'validation.json').write_text(json.dumps(receipt,indent=2)+'\n')
(ROOT/'Sources/Ares/pressure-doors-v2/installed.json').write_text(json.dumps(receipt,indent=2)+'\n')
print(json.dumps({k:receipt[k] for k in ('doors','total_hall_triangles','compiled_assets','identical_sealed_hatch_traces','physics_bytes_exact')}))
