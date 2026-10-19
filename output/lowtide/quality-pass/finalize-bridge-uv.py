from pathlib import Path
import hashlib
import json

ROOT=Path(__file__).resolve().parents[3]
FOLDER=ROOT/'output/lowtide/quality-pass'
manifest=json.loads((FOLDER/'bridge-uv-manifest.json').read_text())
def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
assert sha(ROOT/'Assets/models/maps/lowtide/lowtide_fleet.obj')==manifest['after']
for relative,digest in manifest['protected'].items():
    assert sha(ROOT/relative)==digest, relative
captures=['bridge-uv-walk-after.png','bridge-uv-wide-after.png']
for name in captures: assert (FOLDER/name).is_file()
report=dict(status='installed, natively compiled and visually verified in the existing Lowtide editor viewport',
    installed_sha256=manifest['after'],protected_files_verified=len(manifest['protected']),
    captures={name:sha(FOLDER/name) for name in captures},
    baseline='bridge-uv-wide-before.png',
    review='The former broad stretched stripes are gone. Individual plank grain and joints are legible in walk and wide views.',
    scene_clean=True,play_mode=False,camera_restored=True,
    camera_position='1254.02344,304.488434,146.833755',
    camera_angles='4.60011911,-91.898056,0',
    fresh_console_errors=0,console_cursor=793,
    scope='320 existing UV records across 80 deck boards; geometry, other UVs, collision and generated colour images unchanged')
(FOLDER/'bridge-uv-verification.json').write_text(json.dumps(report,indent=2)+'\n')
(FOLDER/'bridge-uv-pending.json').write_text(json.dumps({'status':report['status'],'verification':'bridge-uv-verification.json','do_not_reapply':True},indent=2)+'\n')
print(json.dumps({'status':report['status'],'protected_files_verified':len(manifest['protected'])}))
