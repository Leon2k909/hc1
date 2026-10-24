"""Remove only exact zero-area planter faces; preserve every other OBJ byte."""
from pathlib import Path
import datetime
import hashlib
import json
import os
import shutil
import subprocess
import numpy as np

ROOT = Path(__file__).resolve().parents[3]
OUT = Path(__file__).resolve().parent
prior = json.loads((OUT / 'compiler-repair-publication.json').read_text())
running = subprocess.run(['rtk', 'proxy', 'tasklist', '/FI', 'IMAGENAME eq sbox-dev.exe', '/FO', 'CSV', '/NH'], capture_output=True, text=True, check=True)
assert '"sbox-dev.exe"' not in running.stdout.lower()


def sha(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


rows = {}
for side in ('east', 'west'):
    source = ROOT / prior['models'][side]['source']
    assert sha(source) == prior['models'][side]['after_sha256']
    target = OUT / 'compiler-repair-nondegenerate' / source.relative_to(ROOT)
    assert not target.exists()
    target.parent.mkdir(parents=True, exist_ok=True)
    vertices = [None]
    material = None
    removed = []
    kept = hashlib.sha256()
    with source.open('rb') as original, target.open('wb') as output:
        for number, line in enumerate(original, 1):
            if line.startswith(b'v '):
                vertices.append(np.array(list(map(float, line.split()[1:]))))
            elif line.startswith(b'usemtl '):
                material = line.split()[1].decode()
            elif line.startswith(b'f '):
                a, b, c = [vertices[int(t.split(b'/')[0])] for t in line.split()[1:]]
                if np.array_equal(np.cross(b - a, c - a), np.zeros(3)):
                    assert material == 'planter_cut_stone'
                    removed.append({'line': number, 'material': material, 'face': line.decode().strip(), 'vertices': [a.tolist(), b.tolist(), c.tolist()]})
                    continue
            output.write(line)
            kept.update(line)
    assert len(removed) == 6
    assert sha(target) == kept.hexdigest()
    rows[side] = {'source': source.relative_to(ROOT).as_posix(), 'before_sha256': sha(source),
        'after_sha256': sha(target), 'removed': removed, 'all_other_obj_bytes_exact': True,
        'all_renderable_triangles_preserved': True, 'staged': target.relative_to(ROOT).as_posix()}
for side, row in rows.items():
    source = ROOT / row['source']
    assert sha(source) == row['before_sha256']
    temporary = source.with_suffix('.obj.zero-area-repair-tmp')
    assert not temporary.exists()
    shutil.copyfile(ROOT / row['staged'], temporary)
    os.replace(temporary, source)
source_generator = ROOT / 'Tools/belltower_planters.py'
generator_backup = OUT / 'compiler-repair-before/Tools/belltower_planters.py'
assert not generator_backup.exists()
generator_backup.parent.mkdir(parents=True, exist_ok=True)
shutil.copy2(source_generator, generator_backup)
result = {'published_utc': datetime.datetime.now(datetime.timezone.utc).isoformat(),
    'models': rows, 'exact_zero_area_faces_removed_total': 12,
    'planter_generator_before_sha256': sha(source_generator), 'native_compile_verified': False}
assert all(sha(ROOT / relative) == digest for relative, digest in prior['unchanged_guard_sha256'].items())
(OUT / 'zero-area-repair-publication.json').write_text(json.dumps(result, indent=2) + '\n')
print(json.dumps({'removed_zero_area_faces': 12, 'all_other_obj_bytes_exact': True}))
