"""Stage only the four gazebo flower-bed visuals, preserving bounded imports."""
from pathlib import Path
from collections import Counter
import hashlib
import importlib.util
import json
import shutil
import sys
import numpy as np

import belltower_map as B
import belltower_long_beds as L
import belltower_detail as D
import belltower_compact_obj as C
import map_kit as K

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'output/belltower/long-bed'
STAGE = OUT / 'stage'


def sha(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def keys(model):
    result = Counter()
    for paint, polygons in model.polygons.items():
        for points, _ in polygons:
            values = [K.obj_vector(K.to_world(p)) for p in points]
            for i in range(1, len(values) - 1):
                result[(paint, frozenset((values[0], values[i], values[i + 1])))] += 1
    return result


def patch(source, old, addition, name):
    before = sha(source)
    data = C.tables(source)
    offsets = {kind: len(values) - 1 for kind, values in data.items()}
    wanted = keys(old)
    found = Counter()
    removed = []
    material = None
    for number, line in enumerate(source.open('rb')):
        if line.startswith(b'usemtl '):
            material = line.split()[1].decode()
        elif line.startswith(b'f '):
            key = (material, frozenset(data[b'v'][int(t.split(b'/')[0])][2:].strip().decode() for t in line.split()[1:]))
            if key in wanted:
                found[key] += 1
                removed.append(number)
    assert found == wanted, (source, sum(found.values()), sum(wanted.values()))
    piece = STAGE / 'pieces' / (name + '.obj')
    piece.parent.mkdir(parents=True, exist_ok=True)
    K.write_obj(piece, addition, 'belltower_' + ('east' if 'east' in name else 'west'))
    raw = piece.read_bytes().splitlines(keepends=True)
    tables = [line for line in raw if line.startswith((b'v ', b'vt ', b'vn '))]
    tail = []
    for line in raw:
        if line.startswith(b'usemtl '):
            tail.append(line)
        elif line.startswith(b'f '):
            tokens = []
            for row in C.face_tokens(line, {k: 10**9 for k in C.KINDS}):
                tokens.append(b'/'.join(str(i + offsets[k]).encode() for k, i in zip(C.KINDS, row)))
            tail.append(b'f ' + b' '.join(tokens) + b'\n')
    relative = source.relative_to(ROOT)
    target = STAGE / relative
    target.parent.mkdir(parents=True, exist_ok=True)
    dropped = set(removed)
    inserted = False
    with source.open('rb') as original, target.open('wb') as updated:
        for number, line in enumerate(original):
            if not inserted and line.startswith(b'usemtl '):
                updated.writelines(tables)
                inserted = True
            if number not in dropped:
                updated.write(line)
        assert inserted
        updated.writelines(tail)
    assert sha(source) == before
    backup = OUT / 'before' / relative
    backup.parent.mkdir(parents=True, exist_ok=True)
    assert not backup.exists()
    shutil.copyfile(source, backup)
    return {'before': before, 'after': sha(target), 'removed_faces': len(removed),
        'added_faces': addition.triangle_count(), 'all_non_bed_source_bytes_preserved': True,
        'source': target.relative_to(ROOT).as_posix(), 'backup': backup.relative_to(ROOT).as_posix()}


def subset(model, paint):
    result = K.Model()
    if model.polygons.get(paint):
        result.polygons[paint] = model.polygons[paint]
    result.polygon_uvs = {k: v for k, v in model.polygon_uvs.items() if k[0] == paint}
    result.polygon_normals = {k: v for k, v in model.polygon_normals.items() if k[0] == paint}
    result.tile_overrides = model.tile_overrides.copy()
    result.material_overrides = model.material_overrides.copy()
    return result


def normal(value):
    if isinstance(value, np.ndarray): return normal(value.tolist())
    if isinstance(value, np.generic): return value.item()
    if isinstance(value, dict): return [[repr(k), normal(v)] for k, v in sorted(value.items(), key=lambda x: repr(x[0]))]
    if isinstance(value, (tuple, list)): return [normal(v) for v in value]
    return value


def main():
    assert not (STAGE / 'manifest.json').exists()
    old, new = K.Model(), K.Model()
    for e, n in L.CENTRES:
        old.box((e - 60, n - 18, B.GARDEN_Z), (e + 60, n + 18, B.GARDEN_Z + 14),
            {'+z': 'soil', 'default': 'ashlar_grey'}, B.STONE)
        L.build(new, (e, n), B.GARDEN_Z, seed=abs(e))
    assert not new.boxes and not new.hulls and not new.props
    for paint, polygons in new.polygons.items():
        for points, normal_vector in polygons:
            rounded = np.array([list(map(float, K.obj_vector(K.to_world(p)).split())) for p in points])
            expected = K.to_world(normal_vector)[[1, 2, 0]]
            for i in range(1, len(points) - 1):
                cross = np.cross(rounded[i] - rounded[0], rounded[i + 1] - rounded[0])
                assert np.dot(cross, expected) > 0, (paint, 'degenerate export triangle')
    # The current shared garden source differs only in these bed meshes and the
    # sixteen plants they support. All collision, other props and RNG are exact.
    spec = importlib.util.spec_from_file_location('long_bed_previous_map', OUT / 'before/Tools/belltower_map.py')
    previous = importlib.util.module_from_spec(spec); spec.loader.exec_module(previous)
    a, b = K.Model(), K.Model()
    previous.gardens(a, np.random.default_rng(2024)); B.gardens(b, np.random.default_rng(2024))
    assert normal(a.boxes) == normal(b.boxes) and normal(a.hulls) == normal(b.hulls)
    assert len(a.props) == len(b.props)
    changed = 0
    for x, y in zip(a.props, b.props):
        if normal(x) == normal(y): continue
        changed += 1
        assert x['path'] == y['path'] == D.BUSH and x['yaw'] == y['yaw']
        assert x['position'][:2] == y['position'][:2] and x['scale'][:2] == y['scale'][:2]
        assert abs(x['position'][2] + x['scale'][2] * D.BUSH_TOP_Z - y['position'][2] - y['scale'][2] * D.BUSH_TOP_Z) < 1e-8
    assert changed == 16
    manifest = {'revision': 'worn-gazebo-flower-beds-v1', 'beds': 4,
        'original_cover_collision_exact': True, 'new_colliders': 0, 'new_scene_objects': 0,
        'changed_plants_per_half': 16, 'all_other_garden_props_exact': True,
        'source_sha256': {p: sha(ROOT / p) for p in ['Tools/belltower_map.py', 'Tools/belltower_long_beds.py', 'Tools/belltower_planters.py']},
        'files': {}, 'vmdl_guards': {}, 'models': {}}
    imports = json.loads((ROOT / 'output/belltower/bush-grounding/compiler-safe-imports-stage/manifest.json').read_text())
    for side in ('west', 'east'):
        original, replacement = (old, new) if side == 'west' else (old.mirrored(), new.mirrored())
        source = ROOT / f'Assets/models/maps/belltower/belltower_{side}.obj'
        manifest['files'][source.relative_to(ROOT).as_posix()] = patch(source, original, replacement, side + '-canonical')
        manifest['vmdl_guards'][source.with_suffix('.vmdl').relative_to(ROOT).as_posix()] = sha(source.with_suffix('.vmdl'))
        counts = {}
        for paint in ('ashlar_grey', 'soil', L.STONE, L.SOIL):
            rows = [p for p in imports['models'][side]['parts'] if p['material'] == paint]
            assert len(rows) == 1
            source = ROOT / rows[0]['asset']
            row = patch(source, subset(original, paint), subset(replacement, paint), side + '-' + paint)
            # Compact only the small bounded import, preserving its resolved
            # material/position/UV/normal data exactly.
            staged = ROOT / row['source']
            compact = staged.with_suffix('.compact.obj')
            proof = C.compact(staged, compact, deduplicate=True)
            compact.replace(staged)
            row['after'] = sha(staged); row['import_compaction'] = proof
            manifest['files'][source.relative_to(ROOT).as_posix()] = row
            counts[paint] = {'removed': row['removed_faces'], 'added': row['added_faces']}
        manifest['models'][side] = {'changes': counts, 'new_visual_triangles': replacement.triangle_count()}
    STAGE.mkdir(parents=True, exist_ok=True)
    (STAGE / 'manifest.json').write_text(json.dumps(manifest, indent=2) + '\n')
    print(json.dumps({'beds': 4, 'files': len(manifest['files']), 'new_triangles_per_half': new.triangle_count(), 'collision_preserved': True, 'plants_to_ground': 32}))


if __name__ == '__main__': main()
