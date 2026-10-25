"""Stage only the blue cafe's translated render faces and four table colliders."""
from collections import Counter
import hashlib
import json
from pathlib import Path
import re
import shutil
import numpy as np
import map_kit as K
import belltower_map as B
import belltower_cafe_spacing as S

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT/'output/belltower/cafe-spacing-v1'
STAGE = OUT/'stage'


def sha(path):
    with path.open('rb') as stream: return hashlib.file_digest(stream, 'sha256').hexdigest()


def q(value):
    return tuple(int(round(float(v)*1000)) for v in value.split())


def geometry(groups):
    lookup = {}; wanted = Counter(); positions = set()
    for k, group in enumerate(groups):
        for paint, polygons in group.polygons.items():
            for points, _ in polygons:
                values = [q(K.obj_vector(K.to_world(p))) for p in points]
                for i in range(1, len(values)-1):
                    key = (paint.encode(), frozenset((values[0], values[i], values[i+1])))
                    assert key not in lookup or lookup[key] == k
                    lookup[key] = k; wanted[key] += 1; positions.update(key[1])
    return lookup, wanted, positions


def patch_render(source, lookup, positions):
    sparse = {}; count = 0; material = None; changes = {}; appended = []; cache = {}; found = Counter()
    paints = {p for p, _ in lookup}
    shifts = [None if S.delta(k) is None else q(K.obj_vector(K.to_world(S.delta(k)))) for k in range(4)]
    for number, line in enumerate(source.open('rb')):
        if line.startswith(b'v '):
            count += 1; value = q(line[2:].decode())
            if value in positions: sparse[count] = value
        elif line.startswith(b'usemtl '): material = line.split()[1]
        elif line.startswith(b'f ') and material in paints:
            tokens = line.split()[1:]; ids = [int(t.split(b'/')[0]) for t in tokens]
            if not all(i in sparse for i in ids): continue
            key = (material, frozenset(sparse[i] for i in ids))
            if key not in lookup: continue
            found[key] += 1; k = lookup[key]
            if shifts[k] is None:
                changes[number] = None; continue
            for index in ids:
                if (index, k) not in cache:
                    value = tuple(a+b for a, b in zip(sparse[index], shifts[k]))
                    cache[(index, k)] = len(appended)
                    appended.append(('v '+' '.join(f'{v/1000:.3f}' for v in value)+'\n').encode())
            changes[number] = (ids, tokens, k)
    if not changes: return None, found
    target = STAGE/source.relative_to(ROOT); target.parent.mkdir(parents=True, exist_ok=True)
    inserted = False; unaffected = hashlib.sha256()
    with target.open('wb') as stream:
        for number, line in enumerate(source.open('rb')):
            if not inserted and line.startswith(b'usemtl '): stream.writelines(appended); inserted = True
            if number not in changes:
                stream.write(line); unaffected.update(line)
            elif changes[number] is not None:
                ids, tokens, k = changes[number]
                moved = [str(count+cache[(index, k)]+1).encode()+b'/'+token.partition(b'/')[2]
                         for index, token in zip(ids, tokens)]
                stream.write(b'f '+b' '.join(moved)+b'\n')
    assert inserted
    # Read back the published byte sequence, skipping only the appended position
    # block and the explicitly affected face lines.
    inserted = False
    with target.open('rb') as check:
        for number, line in enumerate(source.open('rb')):
            if not inserted and line.startswith(b'usemtl '):
                assert [next(check) for _ in appended] == appended; inserted = True
            if number not in changes: assert next(check) == line
            elif changes[number] is not None: assert next(check).startswith(b'f ')
        assert next(check, None) is None
    return {'changed_faces': len(changes), 'removed_faces': sum(v is None for v in changes.values()),
            'unchanged_source_bytes_sha256': unaffected.hexdigest(), 'uvs_normals_materials_retained': True}, found


def patch_collision(source, groups):
    points_by_group = {}
    for k, group in enumerate(groups):
        assert len(group.hulls) == 1
        for p in group.hulls[0][0]:
            value = q(K.obj_vector(K.to_world(p)))
            assert value not in points_by_group
            points_by_group[value] = k
    lines = source.read_bytes().splitlines(keepends=True)
    vertices = {}; groups_by_id = {}; seen = Counter(); count = 0
    for i, line in enumerate(lines):
        if line.startswith(b'v '):
            count += 1; value = q(line[2:].decode()); vertices[count] = value
            if value in points_by_group:
                groups_by_id[count] = points_by_group[value]; seen[points_by_group[value]] += 1
    assert seen == Counter({k: 16 for k in range(4)}), seen
    shifts = [None if S.delta(k) is None else q(K.obj_vector(K.to_world(S.delta(k)))) for k in range(4)]
    remap = {}; new_vertices = {}; count = 0; old_index = 0; out = []; faces_removed = 0
    unaffected_before = Counter(); unaffected_after = Counter()
    for line in lines:
        if line.startswith(b'v '):
            old_index += 1; k = groups_by_id.get(old_index)
            if k is not None and shifts[k] is None: continue
            count += 1; remap[old_index] = count; value = vertices[old_index]
            if k is not None:
                value = tuple(a+b for a, b in zip(value, shifts[k]))
                line = ('v '+' '.join(f'{v/1000:.3f}' for v in value)+'\n').encode()
            new_vertices[count] = value; out.append(line)
        elif line.startswith(b'f '):
            ids = [int(v) for v in line.split()[1:]]
            affected = {groups_by_id[i] for i in ids if i in groups_by_id}
            if affected:
                assert len(affected) == 1 and all(i in groups_by_id for i in ids)
                if shifts[next(iter(affected))] is None: faces_removed += 1; continue
            else:
                unaffected_before[frozenset(vertices[i] for i in ids)] += 1
                unaffected_after[frozenset(new_vertices[remap[i]] for i in ids)] += 1
            out.append(('f '+' '.join(str(remap[i]) for i in ids)+'\n').encode())
        else: out.append(line)
    assert unaffected_before == unaffected_after and faces_removed > 0
    target = STAGE/source.relative_to(ROOT); target.parent.mkdir(parents=True, exist_ok=True); target.write_bytes(b''.join(out))
    return {'moved_table_colliders': 3, 'removed_table_colliders': 1, 'unrelated_collision_faces_exact': True}


def main():
    assert not (STAGE/'manifest.json').exists(), 'Preserve the staged revision.'
    groups = S.original_groups(B.EAST_PAINTS)
    lookup, wanted, positions = geometry(groups)
    canonical = ROOT/'Assets/models/maps/belltower/belltower_east.obj'
    vmdl = canonical.with_suffix('.vmdl'); text = vmdl.read_text()
    protected = [vmdl, canonical.with_suffix('.mtl'), ROOT/'Assets/scenes/maps/Belltower/belltower.scene',
                 ROOT/'Assets/models/maps/belltower/belltower_west.obj', ROOT/'Assets/models/maps/belltower/belltower_west.vmdl']
    protected_hashes = {p.relative_to(ROOT).as_posix(): sha(p) for p in protected}
    files = {}; reports = {}
    row, found = patch_render(canonical, lookup, positions)
    assert found == wanted, ('Canonical cafe differs', sum(found.values()), sum(wanted.values()))
    reports[canonical.relative_to(ROOT).as_posix()] = row
    found_parts = Counter()
    suffixes = tuple('_'+paint.decode()+'.obj' for paint in {p for p, _ in wanted})
    for resource in re.findall(r'filename\s*=\s*"([^"]+\.obj)"', text):
        if not resource.endswith(suffixes): continue
        source = ROOT/'Assets'/resource
        row, found = patch_render(source, lookup, positions); found_parts.update(found)
        if row: reports[source.relative_to(ROOT).as_posix()] = row
    assert found_parts == wanted, ('Referenced cafe differs', sum(found_parts.values()), sum(wanted.values()))
    collision = ROOT/'Assets/models/maps/belltower/belltower_east_hulls_metal.obj'
    collision_report = patch_collision(collision, groups)
    for path in (STAGE/'Assets').rglob('*'):
        if not path.is_file(): continue
        rel = path.relative_to(STAGE); source = ROOT/rel
        backup = OUT/'before'/rel; backup.parent.mkdir(parents=True, exist_ok=True)
        if backup.exists(): assert sha(backup) == sha(source), 'Pinned input changed.'
        else: shutil.copyfile(source, backup)
        files[rel.as_posix()] = {'before': sha(source), 'after': sha(path), 'source': path.relative_to(ROOT).as_posix(),
                               'backup': backup.relative_to(ROOT).as_posix()}
    assert all(sha(ROOT/p) == digest for p, digest in protected_hashes.items())
    manifest = {'revision': 'cafe-spacing-v1', 'scope': 'blue eastern cafe only', 'clearances': S.clearances(),
                'files': files, 'render_reports': reports, 'collision': collision_report,
                'source_sha256': {p: sha(ROOT/p) for p in ['Tools/belltower_cafe_spacing.py',
                    'Tools/belltower_stage_cafe_spacing.py', 'Tools/belltower_map.py', 'Tools/belltower_detail.py', 'Tools/map_kit.py']},
                'protected_sha256': protected_hashes, 'scene_unchanged': True, 'red_cafe_unchanged': True}
    STAGE.mkdir(parents=True, exist_ok=True); (STAGE/'manifest.json').write_text(json.dumps(manifest, indent=2)+'\n')
    print(json.dumps({'files': len(files), 'clearances': manifest['clearances'], 'collision': collision_report}))


if __name__ == '__main__': main()
