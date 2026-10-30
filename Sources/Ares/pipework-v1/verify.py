"""Check the installed pipe assets, narrow document patch and native QA receipts."""
import hashlib
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[3]
OUT=ROOT/'output/ares/pipework-v1'
STAGE=OUT/'stage-v5'
manifest=json.loads((STAGE/'manifest.json').read_text())

def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def results(path):
    raw=json.loads(Path(path).read_text())
    return [json.loads(c['text']) for c in raw['content'] if c['type']=='text']

for path,item in manifest['files'].items():assert sha(ROOT/path)==item['after'],path
for path,value in manifest['source_sha256'].items():assert sha(ROOT/path)==value,path
for path,parts in manifest['required_source_snippets'].items():
    text=(ROOT/path).read_text().replace('\r\n','\n')
    assert all(part.replace('\r\n','\n') in text for part in parts),path
scene='Assets/scenes/maps/Ares/ares.scene'
for path,value in manifest['protected_sha256'].items():
    if path!=scene:assert sha(ROOT/path)==value,path

doc=(ROOT/manifest['document']).read_bytes().decode()
backups=list(STAGE.glob('native-before-hall-*.vmdl'));assert len(backups)==1
before=backups[0].read_bytes().decode();restored=doc
for paint,resource in manifest['materials'].items():
    entry=f'{{ from = "{paint}.vmat" to = "{resource}" }},'
    assert restored.count(entry)==1
    restored=restored.replace('\r\n'+entry,'',1)
assert restored==before,'The live ModelDoc changed beyond the five pipe material aliases.'
marker='_class = "PhysicsShapeList"'
assert doc[doc.index(marker):]==before[before.index(marker):]
retained=(OUT/'stage-v3/proof/retained.obj').read_bytes()
active=(ROOT/manifest['active_base']).read_bytes()
assert active.startswith(retained)
assert sha(OUT/'stage-v3/proof/retained.obj')==manifest['retained_bytes_sha256']
old_faces=sum(line.startswith(b'f ') for line in retained.splitlines())
new_faces=sum(line.startswith(b'f ') for line in active.splitlines())
assert old_faces==21460 and new_faces==317588
assert new_faces-old_faces==manifest['new_triangles']==296128
old=results(OUT/'traces-before/call_tools.json');new=results(OUT/'traces-after/call_tools.json')
assert len(new)==16 and old==new
assets=results(OUT/'info-installed/call_tools.json')
assert len(assets)==7 and all(a['IsCompiledAndUpToDate'] and not a['IsCompileFailed'] for a in assets)
captures={}
folder=ROOT/'output/ares/quality/pipework-v1-installed'
for name in ('cargo-close','cargo-angle','wing-angle'):
    assert (folder/f'{name}.png').is_file()
    restoration=json.loads((folder/f'{name}-restore.json').read_text())
    assert all(restoration.values())
    camera=json.loads((folder/f'{name}-camera.json').read_text())['Capture']
    assert camera['TrialModels']==0
    captures[name]=(folder/f'{name}.png').relative_to(ROOT).as_posix()
before_view=json.loads((ROOT/'output/ares/quality/pipework-v1-before-current/cargo-angle-camera.json').read_text())['Capture']
after_view=json.loads((folder/'cargo-angle-camera.json').read_text())['Capture']
assert all(before_view[k]==after_view[k] for k in ('Position','Angles','FieldOfView','Width','Height','RequestedExposure','SourceSceneSha256'))
status,camera=results(OUT/'status-final/call_tools.json')
assert status['ActiveScene']=='ares' and not status['IsPlaying'] and not status['IsCompiling']
assert status['LastCompileSucceeded'] and status['LastCompileErrors']==0
receipt={'revision':'ares-pipework-v1','stage':'stage-v5','runs':len(manifest['runs']),
    'flange_pairs':sum(r['joints'] for r in manifest['runs']),
    'wall_hangers':sum(r['supports'] for r in manifest['runs']),
    'new_pipe_triangles':296128,'removed_original_pipe_triangles':2240,
    'unrelated_base_triangles_preserved':21460,'compiled_assets':len(assets),
    'matching_collision_rays':16,'physics_bytes_exact':True,
    'hall_document_only_adds_five_pipe_material_aliases':True,
    'retained_obj_bytes_exact':True,'scene_saved_by_task':False,
    'scene_sha256_at_start':manifest['protected_sha256'][scene],
    'scene_sha256_at_finish':sha(ROOT/scene),'captures':captures,
    'editor_status':status,'camera_at_finish':camera}
(OUT/'validation.json').write_text(json.dumps(receipt,indent=2)+'\n')
(ROOT/'Sources/Ares/pipework-v1/installed.json').write_text(json.dumps(receipt,indent=2)+'\n')
print(json.dumps({k:receipt[k] for k in ('runs','flange_pairs','wall_hangers','compiled_assets','matching_collision_rays','physics_bytes_exact')}))
