"""Install only the two proven-equivalent OBJ files with the editor closed."""
from pathlib import Path
import datetime
import hashlib
import json
import os
import shutil
import subprocess

ROOT = Path(__file__).resolve().parents[3]
OUT = Path(__file__).resolve().parent
STAGE = OUT / 'compiler-repair-deduplicated'
REPORT = json.loads((STAGE / 'compaction-report.json').read_text())


def sha(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


running = subprocess.run(['rtk', 'proxy', 'tasklist', '/FI', 'IMAGENAME eq sbox-dev.exe', '/FO', 'CSV', '/NH'],
    text=True, capture_output=True, check=True)
assert '"sbox-dev.exe"' not in running.stdout.lower(), 'Editor must be closed'
guard_paths = [ROOT / 'Assets/scenes/maps/Belltower/belltower.scene']
for side in ('east', 'west'):
    base = ROOT / 'Assets/models/maps/belltower'
    guard_paths += [p for p in base.glob(f'belltower_{side}*') if p.suffix != '.obj' or '_hulls_' in p.stem]
guards = {p.relative_to(ROOT).as_posix(): sha(p) for p in guard_paths if p.is_file()}
for row in REPORT['models'].values():
    source = (ROOT / row['source']).resolve()
    staged = (ROOT / row['staged']).resolve()
    assert source.is_relative_to(ROOT / 'Assets/models/maps/belltower')
    assert staged.is_relative_to(STAGE)
    assert row['all_face_material_position_uv_normal_bytes_identical']
    assert sha(source) == row['before_sha256'], f'Shared source changed: {source}'
    assert sha(staged) == row['after_sha256']
    backup = OUT / 'compiler-repair-before' / row['source']
    assert not backup.exists(), 'Preserve the first pre-repair snapshot'
for row in REPORT['models'].values():
    source = ROOT / row['source']
    backup = OUT / 'compiler-repair-before' / row['source']
    backup.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, backup)
    temporary = source.with_suffix('.obj.compiler-repair-tmp')
    assert not temporary.exists()
    shutil.copyfile(ROOT / row['staged'], temporary)
    os.replace(temporary, source)
    assert sha(source) == row['after_sha256']
assert all(sha(ROOT / relative) == digest for relative, digest in guards.items())
result = {'published_utc': datetime.datetime.now(datetime.timezone.utc).isoformat(),
    'models': REPORT['models'], 'unchanged_guard_sha256': guards,
    'scene_vmdl_material_collision_and_import_identity_preserved': True,
    'native_compile_verified': False, 'startup_verified': False}
(OUT / 'compiler-repair-publication.json').write_text(json.dumps(result, indent=2) + '\n')
print(json.dumps({'published_models': list(REPORT['models']), 'unchanged_guard_files': len(guards)}))
