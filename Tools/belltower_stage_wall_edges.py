"""Stage worn town-wall edges without rebuilding unrelated town geometry."""
from pathlib import Path
from collections import Counter
import hashlib
import importlib.util
import itertools
import argparse
import json
import re
import shutil
import numpy as np
import belltower_map as B
import belltower_detail as D
import belltower_wall_edges as W
import belltower_wall_cleanup as Cleanup
import belltower_compact_obj as C
from belltower_safe_imports import span
import map_kit as K

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'output/belltower/wall-edges'
STAGE = OUT / 'stage'


def sha(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def geometry(model):
    result = Counter()
    for paint, polygons in model.polygons.items():
        for points, _ in polygons:
            values = [K.obj_vector(K.to_world(p)).encode() for p in points]
            for i in range(1, len(values)-1):
                result[(paint.encode(), frozenset((values[0], values[i], values[i+1])))] += 1
    return result


def polygon_options(model):
    """Accept either legacy diagonal, proving the exact polygon boundary."""
    lookup, polygons = {}, []
    for paint, faces in model.polygons.items():
        for points, _ in faces:
            vertices = [K.obj_vector(K.to_world(p)).encode() for p in points]
            index = len(polygons)
            polygons.append((paint.encode(), vertices))
            for tri in itertools.combinations(vertices, 3):
                key = (paint.encode(), frozenset(tri))
                assert key not in lookup, ('Ambiguous target polygon', key)
                lookup[key] = index
    return lookup, polygons


def check_coverage(found, lookup, polygons):
    groups = [Counter() for _ in polygons]
    counts = Counter()
    for key, count in found.items():
        assert count == 1
        index = lookup[key]
        vertices = list(key[1])
        assert len(vertices) == 3
        for a, b in itertools.combinations(vertices, 2):
            groups[index][frozenset((a, b))] += 1
        counts[index] += 1
    for index, (paint, vertices) in enumerate(polygons):
        perimeter = Counter(frozenset((a, vertices[(i+1) % len(vertices)])) for i, a in enumerate(vertices))
        assert counts[index] == len(vertices)-2, ('Missing target polygon', index, paint, vertices, counts[index])
        assert all(count <= 2 for count in groups[index].values())
        assert Counter({edge: count for edge, count in groups[index].items() if count == 1}) == perimeter


def record(path, staged):
    relative = path.relative_to(ROOT)
    old = sha(path) if path.exists() else None
    backup = OUT / 'before' / relative
    if old is not None:
        backup.parent.mkdir(parents=True, exist_ok=True)
        if backup.exists():
            assert sha(backup) == old, ('Pinned input changed', path)
        else:
            shutil.copyfile(path, backup)
        assert sha(backup) == old
    return {'before': old, 'after': sha(staged), 'source': staged.relative_to(ROOT).as_posix(),
            'backup': backup.relative_to(ROOT).as_posix() if old is not None else None}


def patch(path, wanted, addition=None):
    before = sha(path)
    tables = C.tables(path)
    offsets = {kind: len(values)-1 for kind, values in tables.items()}
    found = Counter(); removed = set(); paint = None
    for number, line in enumerate(path.open('rb')):
        if line.startswith(b'usemtl '):
            paint = line.split()[1]
        elif line.startswith(b'f ') and paint in (b'rubble', b'ashlar_grey'):
            key = (paint, frozenset(tables[b'v'][int(t.split(b'/')[0])][2:].strip() for t in line.split()[1:]))
            if key in wanted:
                removed.add(number); found[key] += 1
    if not removed:
        return None, found
    extra_tables, extra_faces = [], []
    if addition is not None:
        for line in addition.open('rb'):
            if line.startswith((b'v ', b'vt ', b'vn ')):
                extra_tables.append(line)
            elif line.startswith(b'usemtl '):
                extra_faces.append(line)
            elif line.startswith(b'f '):
                tokens = [b'/'.join(str(i+offsets[k]).encode() for k, i in zip(C.KINDS, row))
                          for row in C.face_tokens(line, {k: 10**9 for k in C.KINDS})]
                extra_faces.append(b'f '+b' '.join(tokens)+b'\n')
    staged = STAGE / path.relative_to(ROOT)
    staged.parent.mkdir(parents=True, exist_ok=True)
    inserted = False
    with path.open('rb') as source, staged.open('wb') as target:
        for number, line in enumerate(source):
            if not inserted and line.startswith(b'usemtl '):
                target.writelines(extra_tables); inserted = True
            if number not in removed:
                target.write(line)
        assert inserted
        target.writelines(extra_faces)
    assert sha(path) == before
    row = record(path, staged)
    row.update(removed_triangles=len(removed), appended_triangles=len([s for s in extra_faces if s.startswith(b'f ')]),
               unrelated_source_bytes_preserved=True)
    return row, found


def plain(value):
    if isinstance(value, np.ndarray): return plain(value.tolist())
    if isinstance(value, np.generic): return value.item()
    if isinstance(value, (tuple, list)): return [plain(x) for x in value]
    return value


def main():
    global OUT, STAGE
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out', type=Path, default=OUT)
    args = parser.parse_args()
    OUT = args.out.resolve(); STAGE = OUT/'stage'
    OUT.mkdir(parents=True, exist_ok=True)
    assert not (STAGE / 'manifest.json').exists()
    spec = importlib.util.spec_from_file_location('previous_wall_edges_map', ROOT / 'output/belltower/wall-edges/before/Tools/belltower_map.py')
    previous = importlib.util.module_from_spec(spec); spec.loader.exec_module(previous)
    before_full, after_full = K.Model(), K.Model()
    previous.town_walls(before_full); B.town_walls(after_full)
    assert plain(before_full.boxes) == plain(after_full.boxes)
    assert plain(before_full.hulls) == plain(after_full.hulls)
    assert plain(before_full.props) == plain(after_full.props)
    old, new = K.Model(), K.Model()
    W.targets(old, B.STONE, worn=False); W.targets(new, B.STONE)
    Cleanup.trim_model(old, {}); Cleanup.trim_model(new, {})
    full_a, full_b, target_a, target_b = map(geometry, (before_full, after_full, old, new))
    assert full_a-full_b == target_a-target_b
    assert full_b-full_a == target_b-target_a
    assert plain(old.boxes) == plain(new.boxes)
    assert not new.props and not new.hulls
    exported_triangles = 0
    for paint, polygons in new.polygons.items():
        for points, expected in polygons:
            p = np.asarray([list(map(float, K.obj_vector(K.to_world(q)).split())) for q in points])
            n = K.to_world(expected)[[1, 2, 0]]
            for i in range(1, len(p)-1):
                cross = np.cross(p[i]-p[0], p[i+1]-p[0])
                assert np.dot(cross, n) > 1e-8, (paint, 'degenerate or reversed triangle')
                exported_triangles += 1
    assert exported_triangles < 100000
    report = {'revision': 'worn-town-wall-edges-v1', 'files': {}, 'source_sha256': {}, 'protected_sha256': {},
              'original_collision_exact': True, 'all_other_town_wall_geometry_exact': True,
              'new_scene_objects': 0, 'new_materials': 0, 'new_texture_pixels': False,
              'gate_towers': 4, 'merlons_per_half': len(old.boxes)-2,
              'new_triangles_per_half': new.triangle_count(), 'models': {},
              'scene_sha256': sha(ROOT/'Assets/scenes/maps/Belltower/belltower.scene')}
    for relative in ('Tools/belltower_map.py', 'Tools/belltower_wall_edges.py', 'Tools/belltower_stage_wall_edges.py',
                     'Tools/belltower_wall_cleanup.py', 'Tools/map_kit.py'):
        report['source_sha256'][relative] = sha(ROOT/relative)
    for relative in ('Assets/materials/belltower/rubble.vmat', 'Assets/materials/belltower/ashlar_grey.vmat'):
        report['protected_sha256'][relative] = sha(ROOT/relative)
    for side in ('west', 'east'):
        replacement = new if side == 'west' else new.mirrored()
        lookup, polygons = polygon_options(old if side == 'west' else old.mirrored())
        wanted = lookup.keys()
        replacement.tile_overrides.update(D.TILES)
        relative = Path(f'Assets/models/maps/belltower/wall-edges-v1/{side}.obj')
        piece = STAGE / relative
        piece.parent.mkdir(parents=True, exist_ok=True)
        K.write_obj(piece, replacement, f'belltower_{side}')
        for suffix in ('.obj', '.mtl'):
            staged = piece.with_suffix(suffix)
            target = ROOT / relative.with_suffix(suffix)
            report['files'][target.relative_to(ROOT).as_posix()] = record(target, staged)
        canonical = ROOT / f'Assets/models/maps/belltower/belltower_{side}.obj'
        row, found = patch(canonical, wanted, piece)
        check_coverage(found, lookup, polygons)
        canonical_found = found
        report['files'][canonical.relative_to(ROOT).as_posix()] = row
        vmdl = canonical.with_suffix('.vmdl')
        text = vmdl.read_text()
        a, b = span(text, '_class = "RenderMeshList"')
        render = text[a:b]
        x, y = span(render, '_class = "RenderMeshFile"')
        node = re.sub(r'name = "[^"]+"', f'name = "wall_edges_{side}"', render[x:y], count=1)
        node = re.sub(r'filename = "[^"]+"', f'filename = "{relative.relative_to("Assets").as_posix()}"', node, count=1)
        imports = re.findall(r'filename\s*=\s*"([^"]+\.obj)"', render)
        all_found = Counter(); changed_parts = 0
        for resource in imports:
            if not re.search(r'_(?:rubble|ashlar_grey)\.obj$', resource): continue
            path = ROOT / 'Assets' / resource
            row, found = patch(path, wanted)
            all_found.update(found)
            if row:
                changed_parts += 1
                report['files'][path.relative_to(ROOT).as_posix()] = row
        assert all_found == canonical_found, ('Bounded target mismatch', side, sum(all_found.values()), sum(canonical_found.values()))
        end = render.rfind(']')
        updated = text[:a] + render[:end].rstrip() + ',\n\t\t\t\t\t' + node + '\n\t\t\t\t' + render[end:] + text[b:]
        # Physics and every preceding render import stay byte-for-byte intact.
        p0, p1 = span(text, '_class = "PhysicsShapeList"')
        q0, q1 = span(updated, '_class = "PhysicsShapeList"')
        assert text[p0:p1] == updated[q0:q1]
        assert re.findall(r'filename\s*=\s*"([^"]+\.obj)"', updated[a:])[:len(imports)] == imports
        staged_vmdl = STAGE / vmdl.relative_to(ROOT)
        staged_vmdl.write_text(updated)
        report['files'][vmdl.relative_to(ROOT).as_posix()] = record(vmdl, staged_vmdl)
        report['models'][side] = {'removed_triangles': sum(canonical_found.values()), 'new_triangles': replacement.triangle_count(),
                                  'bounded_parts_with_old_faces_removed': changed_parts,
                                  'new_bounded_import_triangles': replacement.triangle_count(), 'physics_byte_identical': True,
                                  'all_prior_render_imports_preserved': True, 'original_polygon_boundaries_exact': True}
    (STAGE/'manifest.json').write_text(json.dumps(report, indent=2)+'\n')
    print(json.dumps({k:v for k,v in report.items() if k not in ('files','source_sha256','protected_sha256')}))


if __name__ == '__main__': main()
