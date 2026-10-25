from pathlib import Path
import datetime
import hashlib
import json
import os
import shutil
import subprocess

ROOT = Path(__file__).resolve().parents[3]
OUT = Path(__file__).resolve().parent
STAGE = OUT / 'compiler-safe-imports-stage'
manifest = json.loads((STAGE / 'manifest.json').read_text())


def sha(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


running = subprocess.run(['rtk', 'proxy', 'tasklist', '/FI', 'IMAGENAME eq sbox-dev.exe', '/FO', 'CSV', '/NH'], capture_output=True, text=True, check=True)
assert '"sbox-dev.exe"' not in running.stdout.lower()
scene = ROOT / 'Assets/scenes/maps/Belltower/belltower.scene'
scene_hash = sha(scene)
new_files = {}
for model in manifest['models'].values():
    assert model['all_renderable_triangles_and_attributes_exact']
    assert model['vmdl_original_prefix_suffix_and_physics_exact']
    for relative, digest in model['input_guards'].items():
        assert sha(ROOT / relative) == digest, relative
    for item in model['parts']:
        new_files[item['asset']] = item['sha256']
    new_files[model['mtl']] = model['mtl_sha256']
    assert sha(STAGE / model['vmdl']) == model['vmdl_after_sha256']
for relative, digest in new_files.items():
    target = (ROOT / relative).resolve()
    assert target.is_relative_to(ROOT / 'Assets/models/maps/belltower/compiler-safe')
    assert not target.exists(), 'Do not replace another source revision'
    assert sha(STAGE / relative) == digest
for relative, digest in new_files.items():
    target = ROOT / relative
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(STAGE / relative, target)
for model in manifest['models'].values():
    relative = model['vmdl']
    target = ROOT / relative
    backup = OUT / 'compiler-safe-imports-before' / relative
    assert not backup.exists()
    backup.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(target, backup)
    temporary = target.with_suffix('.vmdl.bounded-import-tmp')
    assert not temporary.exists()
    shutil.copyfile(STAGE / relative, temporary)
    os.replace(temporary, target)
    assert sha(target) == model['vmdl_after_sha256']
assert sha(scene) == scene_hash
result = {'published_utc': datetime.datetime.now(datetime.timezone.utc).isoformat(),
    'scene_sha256': scene_hash, 'new_import_files': new_files,
    'vmdl_sha256': {m['vmdl']: m['vmdl_after_sha256'] for m in manifest['models'].values()},
    'all_renderable_triangles_and_attributes_exact': True, 'physics_and_scene_bytes_preserved': True,
    'native_startup_verified': False, 'native_model_compilation_verified': False}
(OUT / 'safe-import-publication.json').write_text(json.dumps(result, indent=2) + '\n')
print(json.dumps({'published_import_files': len(new_files), 'vmdl_resources_preserved': 2, 'scene_preserved': True}))
