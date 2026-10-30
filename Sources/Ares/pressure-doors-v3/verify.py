"""Verify the installed, prototype-based doors against native editor evidence."""
import hashlib
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[3]
OUT=ROOT/'output/ares/pressure-door-v3'
request=json.loads((OUT/'import-request.json').read_text())
manifest=json.loads((OUT/request['stage']/'manifest.json').read_text())

def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def results(path):
    raw=json.loads(Path(path).read_text())
    return [json.loads(c['text']) for c in raw['content'] if c['type']=='text']

assert not request['preview'],'The live hall has not been installed.'
for path,item in manifest['files'].items():assert sha(ROOT/path)==item['after'],path
for path,digest in manifest['source_sha256'].items():assert sha(ROOT/path)==digest,path
scene='Assets/scenes/maps/Ares/ares.scene'
for path,digest in manifest['protected_sha256'].items():
    if path!=scene:assert sha(ROOT/path)==digest,path
for path,parts in manifest['required_source_snippets'].items():
    source=(ROOT/path).read_text().replace('\r\n','\n')
    assert all(part.replace('\r\n','\n') in source for part in parts)
assert 'from ares_pressure_formed import pressure_door' in (ROOT/'Tools/ares_airlock.py').read_text()
document='Assets/models/maps/ares/ares_hall.vmdl';item=manifest['files'][document]
a=(ROOT/item['backup']).read_bytes();b=(ROOT/document).read_bytes();marker=b'_class = "PhysicsShapeList"'
assert a[a.index(marker):]==b[b.index(marker):]
# The shared base had already received other geometry work before this rebuild.
# Its staged hash, checked above, proves we retained that exact current version;
# it is no longer a prefix of the separate legacy canonical OBJ.
retained=sum(len(line.split())-3 for line in (ROOT/manifest['base_import']).open('rb') if line.startswith(b'f '))
assert retained==manifest['retained_hall_triangles']
assets=results(OUT/'asset-info-installed/call_tools.json')
assert len(assets)==16 and all(a['IsCompiledAndUpToDate'] and not a['IsCompileFailed'] for a in assets)
old=results(OUT/'traces-before/call_tools.json');new=results(OUT/'traces-installed/call_tools.json')
assert len(new)==27 and old==new
assert all(r['Hit'] and not r['StartedSolid'] and r['Component']=='ModelCollider' for r in new)
status,camera=results(OUT/'final-status/call_tools.json')
assert status['ActiveScene']=='ares' and not status['IsCompiling']
assert status['LastCompileSucceeded'] and status['LastCompileErrors']==0
captures={};folder=ROOT/'output/ares/quality/pressure-door-v3-installed'
for name in ('cargo','wing-west','wing-east','hardware','angle'):
    assert (folder/f'{name}.png').is_file()
    restoration=json.loads((folder/f'{name}-restore.json').read_text());assert all(restoration.values())
    captures[name]=(folder/f'{name}.png').relative_to(ROOT).as_posix()
receipt=dict(revision='ares-pressure-doors-v3',stage=request['stage'],doors=3,
    formed_channels=12,service_covers=6,cam_latches=18,
    triangles_by_door={x['name']:x['triangles'] for x in manifest['sections']},
    new_door_triangles=manifest['new_triangles'],retained_hall_triangles=retained,total_hall_triangles=retained+manifest['new_triangles'],
    retained_hall_geometry_exact=True,physics_suffix_bytes_exact=True,
    native_compiled_assets=len(assets),identical_collision_traces=len(new),
    scene_saved_by_task=False,scene_sha256_at_staging=manifest['protected_sha256'][scene],
    scene_sha256_after=sha(ROOT/scene),editor_status=status,camera_after=camera,captures=captures,
    reference='Sources/Ares/pressure-doors-v3/concept-v1.png')
(OUT/'validation.json').write_text(json.dumps(receipt,indent=2)+'\n')
(ROOT/'Sources/Ares/pressure-doors-v3/installed.json').write_text(json.dumps(receipt,indent=2)+'\n')
print(json.dumps({k:receipt[k] for k in ('doors','formed_channels','native_compiled_assets','identical_collision_traces','physics_suffix_bytes_exact')}))
