"""Move only the three misplaced market barrels and their mirrored counterparts.

Vertex translations preserve all face indices, UVs, normals and materials.
The matching three wood collision hulls move by exactly the same offsets.
Only staged files are written; the native editor publishes checked resources.
"""
import argparse
import ast
from collections import Counter
import hashlib
import json
from pathlib import Path
import re
import shutil
import numpy as np
from scipy.spatial import cKDTree
import belltower_detail as D
import map_kit as K

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT/'output/belltower/market-barrel-placement-v1'
PAINTS = {'planks', 'planks_dark', 'iron_black'}


def sha(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def plan(obj):
    x, z, n = obj
    return np.array((-x, n, z))


def to_obj(p):
    return np.array((-p[0], p[2], p[1]))


def collisions(path, side, expected_centres=None):
    lines = path.read_bytes().splitlines(keepends=True)
    vertices = [None]+[np.array(tuple(map(float, line.split()[1:4]))) for line in lines if line.startswith(b'v ')]
    parent = list(range(len(vertices)))

    def find(i):
        while parent[i] != i:
            parent[i] = parent[parent[i]]; i = parent[i]
        return i

    for line in lines:
        if line.startswith(b'f '):
            face = list(map(int, line.split()[1:]))
            for i in face[1:]: parent[find(i)] = find(face[0])
    groups = {}
    for i in range(1, len(vertices)): groups.setdefault(find(i), []).append(i)
    selected = []
    expected = np.array((-1810 if side == 'west' else 1810, 1300))
    for group in groups.values():
        points = np.array([plan(vertices[i]) for i in group])
        centre = points.mean(axis=0)
        location_matches = np.linalg.norm(centre[:2]-expected) < 29 if expected_centres is None else np.linalg.norm(expected_centres-centre[:2], axis=1).min() < .01
        if len(group) == 20 and location_matches and np.allclose([points[:, 2].min(), points[:, 2].max()], [0, 36]):
            selected.append({'indices': group, 'centre': centre[:2]})
    selected.sort(key=lambda g: min(g['indices']))
    assert len(selected) == 3, ('Expected exactly three market barrel hulls', side, len(selected))
    return lines, vertices, selected


def stage_file(path, translations, stage, hull_indices=None):
    before = sha(path)
    selected_vertices = {}; vertex_lines = {}; material = None; found = Counter(); per_barrel = [Counter() for _ in translations]
    geometry = Counter(); vertex_number = 0
    centres = np.array([old for old, new in translations])
    lower, upper = centres.min(axis=0)-13.04, centres.max(axis=0)+13.04
    template = K.Model(); D.barrel(template, (0, 0), 0, 13, 36)
    expected_counts = Counter({paint: sum(len(p)-2 for p, _ in polys) for paint, polys in template.polygons.items()})
    expected_points = np.array([p for polys in template.polygons.values() for poly, _ in polys for p in poly])
    tree = cKDTree(expected_points)
    for number, line in enumerate(path.open('rb')):
        if line.startswith(b'v '):
            vertex_number += 1
            ox, z, n = map(float, line.split()[1:4]); e = -ox
            if hull_indices is not None:
                candidates = [i for i, ids in enumerate(hull_indices) if vertex_number in ids]
            elif -.001 <= z <= 36.001 and lower[0] <= e <= upper[0] and lower[1] <= n <= upper[1]:
                candidates = [i for i, centre in enumerate(centres) if (centre[0]-e)**2+(centre[1]-n)**2 <= 13.04**2]
            else:
                candidates = []
            if candidates:
                assert len(candidates) == 1
                p = np.array((e, n, z))
                selected_vertices[vertex_number] = (candidates[0], p)
                vertex_lines[vertex_number] = number
        elif line.startswith(b'usemtl '): material = line.split()[1].decode()
        elif line.startswith(b'f ') and hull_indices is None:
            if not selected_vertices: continue
            ids = [int(t.split(b'/')[0]) for t in line.split()[1:]]
            chosen = [selected_vertices[i][0] for i in ids if i in selected_vertices]
            if chosen:
                # Reject a shared ground/furniture vertex or a partly selected face.
                assert len(chosen) == len(ids) and len(set(chosen)) == 1 and material in PAINTS, ('Shared vertex', path, number)
                group = chosen[0]
                assert len(ids) == 3
                relative = np.array([selected_vertices[i][1] for i in ids])-np.r_[centres[group], 0]
                assert tree.query(relative)[0].max() < .0021, ('The selected geometry is not the barrel template', path, number)
                found[material] += 1; per_barrel[group][material] += 1
                geometry[(material, frozenset(tuple(np.round(selected_vertices[i][1], 3)) for i in ids))] += 1
    if not selected_vertices: return None, Counter()
    if hull_indices is None:
        present = [row for row in per_barrel if row]
        for row in present: assert all(row[p] == expected_counts[p] for p in row), ('Partial barrel material', path, row, expected_counts)
    target = stage/path.relative_to(ROOT); backup = stage/'before'/path.relative_to(ROOT)
    target.parent.mkdir(parents=True, exist_ok=True); backup.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(path, backup)
    replacement = {}
    for index, (group, p) in selected_vertices.items():
        old, new = translations[group]
        p[:2] += new-old
        q = to_obj(p)
        replacement[vertex_lines[index]] = ('v '+' '.join(f'{x:.3f}' for x in q)+'\n').encode()
    unchanged = hashlib.sha256()
    with target.open('wb') as output:
        for number, line in enumerate(path.open('rb')):
            if number in replacement: output.write(replacement[number])
            else: output.write(line); unchanged.update(line)
    assert sha(path) == before and sha(backup) == before
    # Independently prove all bytes other than selected position rows stayed intact.
    original = path.read_bytes().splitlines(keepends=True); changed = target.read_bytes().splitlines(keepends=True)
    assert len(original) == len(changed)
    assert all(a == b for i, (a, b) in enumerate(zip(original, changed)) if i not in replacement)
    return {'before': before, 'after': sha(target), 'source': target.relative_to(ROOT).as_posix(),
            'backup': backup.relative_to(ROOT).as_posix(), 'moved_position_rows': len(replacement),
            'barrel_triangles': sum(found.values()), 'unchanged_rows_sha256': unchanged.hexdigest(),
            'faces_uvs_normals_materials_exact': True}, geometry


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--revision', default='r1'); parser.add_argument('--from-revision'); args = parser.parse_args()
    assert re.fullmatch('[a-z0-9-]+', args.revision)
    stage = OUT/args.revision; assert not (stage/'manifest.json').exists()
    stage.mkdir(parents=True, exist_ok=True)
    tree = ast.parse((ROOT/'Tools/belltower_map.py').read_text())
    value = next(n.value for n in tree.body if isinstance(n, ast.Assign) and any(isinstance(t, ast.Name) and t.id == 'MARKET_STORAGE_BARRELS' for t in n.targets))
    targets = np.array(ast.literal_eval(value), float)
    assert targets.shape == (3, 2)
    # The side-wall window bay has no entrance. Keep the stock beyond the front
    # corner, outside the plinth, and below the bay before the side door begins.
    assert (targets[:, 0]+13.025 < -1852.5).all() and (targets[:, 0]-13.025 > -1950).all()
    assert (targets[:, 1]-13.025 > 1450).all() and (targets[:, 1]+13.025 < 1566).all()
    minimum_gap = min(np.linalg.norm(a-b)-26.05 for i, a in enumerate(targets) for b in targets[i+1:])
    assert minimum_gap > 4
    report = {'revision': 'market-barrel-placement-v1', 'files': {}, 'source_sha256': {}, 'protected_sha256': {},
              'models': {}, 'barrel_surface_gap_inches': minimum_gap, 'other_barrel_groups_unchanged': True,
              'random_draws_preserved': True, 'scene_unchanged': True, 'vmdl_descriptions_unchanged': True}
    for p in ['Tools/belltower_map.py', 'Tools/belltower_stage_market_barrels.py', 'Tools/belltower_detail.py', 'Tools/map_kit.py']:
        report['source_sha256'][p] = sha(ROOT/p)
    for side in ['west', 'east']:
        vmdl = ROOT/f'Assets/models/maps/belltower/belltower_{side}.vmdl'
        report['protected_sha256'][vmdl.relative_to(ROOT).as_posix()] = sha(vmdl)
        resources = re.findall(r'filename\s*=\s*"([^"]+\.obj)"', vmdl.read_text())
        hull = ROOT/'Assets'/next(p for p in resources if p.endswith(f'belltower_{side}_hulls_wood.obj'))
        expected_centres = None
        if args.from_revision:
            assert re.fullmatch('[a-z0-9-]+', args.from_revision)
            previous = json.loads((OUT/args.from_revision/'manifest.json').read_text())
            expected_centres = np.array([p['new'] for p in previous['models'][side]['translations']])
        _, _, groups = collisions(hull, side, expected_centres)
        mirrored_targets = targets*np.array((1 if side == 'west' else -1, 1))
        translations = [(group['centre'], target) for group, target in zip(groups, mirrored_targets)]
        row, _ = stage_file(hull, translations, stage, [set(g['indices']) for g in groups])
        report['files'][hull.relative_to(ROOT).as_posix()] = row
        canonical = ROOT/f'Assets/models/maps/belltower/belltower_{side}.obj'
        row, wanted = stage_file(canonical, translations, stage)
        assert row and row['barrel_triangles'] == 5610
        report['files'][canonical.relative_to(ROOT).as_posix()] = row
        found = Counter(); imports = []
        for resource in resources:
            if not any(resource.endswith('_'+p+'.obj') for p in PAINTS): continue
            path = ROOT/'Assets'/resource
            row, matched = stage_file(path, translations, stage)
            if row:
                report['files'][path.relative_to(ROOT).as_posix()] = row
                found.update(matched); imports.append(resource)
        assert found == wanted, ('Canonical/bounded barrel geometry differs', side)
        report['models'][side] = {'barrels_moved': 3, 'translations': [{'old': old.tolist(), 'new': new.tolist()} for old, new in translations],
                                 'bounded_imports': imports, 'unchanged_triangle_count': True}
    scene = ROOT/'Assets/scenes/maps/Belltower/belltower.scene'
    report['protected_sha256'][scene.relative_to(ROOT).as_posix()] = sha(scene)
    for group in ['source_sha256', 'protected_sha256']:
        assert all(sha(ROOT/p) == h for p, h in report[group].items())
    assert all(sha(ROOT/p) == row['before'] for p, row in report['files'].items())
    (stage/'manifest.json').write_text(json.dumps(report, indent=2)+'\n')
    print(json.dumps({'files': len(report['files']), 'barrels_moved': 6, 'minimum_barrel_gap_inches': minimum_gap,
                      'other_props_uvs_materials_and_vmdl_unchanged': True, 'collision_moves_with_barrels': True}))


if __name__ == '__main__': main()
