"""Stage just Belltower's armrests, retaining every other mesh face and physics file."""
from pathlib import Path
from collections import Counter
import argparse
import hashlib
import importlib.util
import json
import re
import shutil
import numpy as np
import belltower_map as B
import belltower_furniture as F
import belltower_detail as D
import belltower_compact_obj as C
import map_kit as K

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'output/belltower/bench-arms-v2'


def sha(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def placements():
    result = [((-190, -820), -90, 50, 0)]
    result += [((e, -965), 0, 80, 0) for e in (-1640, -1340, -820, -420)]
    result += [((-500, -1160), 0, 60, B.GARDEN_Z)]
    result += [(centre, yaw, 70, 0) for yaw, centre in ((90, (-150, 130)), (45, (-110, 240)), (135, (-110, 20)))]
    return result


def key(paint, corners):
    return paint, frozenset(row[0][2:].strip() for row in corners)


def rows(path):
    data = C.tables(path)
    counts = {k: len(v)-1 for k,v in data.items()}
    paint = None
    result = []
    for line in path.open('rb'):
        if line.startswith(b'usemtl '): paint = line.split()[1]
        elif line.startswith(b'f '):
            corners = [tuple(data[k][i] for k,i in zip(C.KINDS, indices)) for indices in C.face_tokens(line, counts)]
            result.append((key(paint, corners), corners))
    return result


def geometry(model):
    result = Counter()
    for paint, polygons in model.polygons.items():
        for points, _ in polygons:
            v = [K.obj_vector(K.to_world(p)).encode() for p in points]
            for i in range(1, len(v)-1):
                result[(paint.encode(), frozenset((v[0],v[i],v[i+1])))] += 1
    return result


def patch(source, replacements, stage, backup):
    before = sha(source)
    data = C.tables(source)
    counts = {kind: len(values)-1 for kind, values in data.items()}
    found = Counter(); changed = {}; material = None; faces = 0; saw_faces = False
    append = {k: [] for k in C.KINDS}; caches = {k: {} for k in C.KINDS}
    for number, line in enumerate(source.open('rb')):
        if line.startswith(b'usemtl '): material = line.split()[1]; saw_faces = True
        elif line.startswith((b'v ',b'vt ',b'vn ')):
            assert not saw_faces, 'Table entries after faces require a different indexing patch'
        elif line.startswith(b'f '):
            faces += 1
            if material not in (b'iron_black', b'furniture_wood_dark'): continue
            corners = [tuple(data[k][i] for k,i in zip(C.KINDS, indices)) for indices in C.face_tokens(line, counts)]
            signature = key(material, corners)
            if signature not in replacements: continue
            indices = []
            for corner in replacements[signature]:
                token = []
                for kind, value in zip(C.KINDS, corner):
                    if value not in caches[kind]:
                        append[kind].append(value)
                        caches[kind][value] = counts[kind]+len(append[kind])
                    token.append(str(caches[kind][value]).encode())
                indices.append(b'/'.join(token))
            changed[number] = b'f '+b' '.join(indices)+b'\n'
            found[signature] += 1
    if not changed: return None, found
    target = stage / source.relative_to(ROOT)
    target.parent.mkdir(parents=True, exist_ok=True)
    inserted = False
    with source.open('rb') as original, target.open('wb') as updated:
        for number, line in enumerate(original):
            if not inserted and line.startswith(b'usemtl '):
                for kind in C.KINDS: updated.writelines(append[kind])
                inserted = True
            updated.write(changed.get(number, line))
    assert inserted and sha(source) == before, 'Input changed during staging'
    saved = backup / source.relative_to(ROOT)
    saved.parent.mkdir(parents=True, exist_ok=True)
    assert not saved.exists()
    shutil.copyfile(source, saved)
    assert sha(saved) == before
    return {'before': before, 'after': sha(target), 'source': target.relative_to(ROOT).as_posix(),
            'backup': saved.relative_to(ROOT).as_posix(), 'arm_triangles_replaced': len(changed),
            'triangles_before': faces, 'triangles_after': faces,
            'all_unrelated_source_bytes_preserved': True}, found


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--revision', type=int, default=1)
    args = parser.parse_args()
    stage, backup = OUT/f'stage-r{args.revision}', OUT/f'before-r{args.revision}'
    assert not stage.exists(), 'Use a fresh revision; earlier evidence is retained'
    stage.mkdir(parents=True)
    original_source = OUT/'before/Tools/belltower_furniture.py'
    spec = importlib.util.spec_from_file_location('bench_arm_previous_furniture', original_source)
    previous = importlib.util.module_from_spec(spec); spec.loader.exec_module(previous)
    old, new, old_full, new_full = [K.Model() for _ in range(4)]
    for centre, yaw, length, z in placements():
        p = B.Place((*centre,z), yaw); half = length/2
        previous.bench(old_full,p,length); F.bench(new_full,p,length)
        for side in (-1,1):
            old_x, new_x = side*(half-6), side*(half-1.1)
            F.bench_arm(old,p,old_x,140+int(old_x))
            F.bench_arm(new,p,new_x,140+int(old_x))
    a,b,c,d = map(geometry,(old_full,new_full,old,new))
    assert a-b == c-d and b-a == d-c, 'A bench part other than its arms changed'
    assert not old.boxes and not new.boxes and not old.props and not new.props
    result = {'revision':'bench-arm-placement-v2', 'stage_revision':args.revision,
              'benches':18, 'armrests':36, 'old_arm_centre_inset_inches':6,
              'new_arm_centre_inset_inches':1.1, 'outward_shift_inches':4.9,
              'grip_outer_edges_flush_with_slat_ends':True,
              'all_seats_backs_legs_braces_and_bolts_exact':True,
              'collision_unchanged':True, 'new_scene_objects':0,
              'scene_sha256':sha(ROOT/'Assets/scenes/maps/Belltower/belltower.scene'),
              'files':{}, 'models':{}, 'source_sha256':{}, 'vmdl_guards':{}}
    for p in ('Tools/belltower_furniture.py','Tools/belltower_stage_bench_arms.py','Tools/map_kit.py'):
        result['source_sha256'][p] = sha(ROOT/p)
    for side in ('west','east'):
        aa, bb = (old,new) if side == 'west' else (old.mirrored(),new.mirrored())
        for label, model in (('old',aa),('new',bb)):
            model.tile_overrides.update(D.TILES)
            K.write_obj(stage/f'{side}-{label}.obj',model,f'belltower_{side}')
        old_rows, new_rows = rows(stage/f'{side}-old.obj'), rows(stage/f'{side}-new.obj')
        assert len(old_rows) == len(new_rows) and len(dict(old_rows)) == len(old_rows)
        replacements = {old_row[0]:new_row[1] for old_row,new_row in zip(old_rows,new_rows)}
        wanted = Counter(old_row[0] for old_row in old_rows)
        canonical = ROOT/f'Assets/models/maps/belltower/belltower_{side}.obj'
        row, found = patch(canonical,replacements,stage,backup)
        assert found == wanted, ('Canonical arm mismatch',side,sum(found.values()),sum(wanted.values()))
        result['files'][canonical.relative_to(ROOT).as_posix()] = row
        vmdl = canonical.with_suffix('.vmdl')
        result['vmdl_guards'][vmdl.relative_to(ROOT).as_posix()] = sha(vmdl)
        resources = re.findall(r'filename\s*=\s*"([^"]+\.obj)"',vmdl.read_text())
        found_parts = Counter(); parts = []
        for resource in resources:
            if not re.search(r'_(?:iron_black|furniture_wood_dark)\.obj$',resource): continue
            source = ROOT/'Assets'/resource
            row, found = patch(source,replacements,stage,backup)
            found_parts.update(found)
            if row:
                assert row['triangles_after'] <= 100000
                result['files'][source.relative_to(ROOT).as_posix()] = row
                parts.append(resource)
        assert found_parts == wanted, ('Referenced arm mismatch',side,sum(found_parts.values()),sum(wanted.values()))
        result['models'][side] = {'arm_triangles_replaced':len(old_rows),'changed_bounded_imports':parts,
                                  'same_triangle_count':True,'model_description_and_physics_unchanged':True}
    for group in ('source_sha256','vmdl_guards'):
        assert all(sha(ROOT/p)==h for p,h in result[group].items()), 'Shared input changed'
    assert all(sha(ROOT/p)==row['before'] for p,row in result['files'].items()), 'Shared mesh changed'
    (stage/'manifest.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps({'stage':str(stage.relative_to(ROOT)), 'benches':18,'armrests':36,
                      'files':len(result['files']),'models':result['models']}))


if __name__ == '__main__': main()
