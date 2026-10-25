"""Stage Belltower's coopered casks (v3, belltower_barrels_v3) in place of all 23 barrels on each side.

The barrels are found by their collision hulls (ten-sided, 20 vertices, standing on z 0, 36 high or the cellar's 40),
which stay exactly as they are, so cover doesn't change. Each old cask is taken out of every import it's drawn in by
matching its faces against the generator's own template at that hull's centre: Detail.barrel's 48-sided tube for 21 of
them, belltower_barrels_v2's casks for the clock frontage's pair (whose import node goes). Nothing else is touched:
every other line of every file is kept byte for byte, and a face is only taken out if all its corners are the
template's.

The new casks go into a few bounded imports of their own (barrels-v3/<side>_<n>.obj), and are appended to the
canonical record (belltower_<side>.obj) the way belltower_map would now write them. Only staged files are written;
Sources/Belltower/editor/import-barrels-v3.cs.txt publishes them through the editor.
"""
import argparse
from collections import Counter, defaultdict
import hashlib
import json
from pathlib import Path
import re
import shutil
import numpy as np
from scipy.spatial import cKDTree

import map_kit as K
import belltower_detail as D
import belltower_barrels_v2 as V2
import belltower_barrels_v3 as V3
from belltower_safe_imports import span

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT/'output/belltower/barrels-v3'
MODELS = ROOT/'Assets/models/maps/belltower'
OLD_PAINTS = {'planks_dark', 'planks', 'iron_black'}
V2_PAINTS = set(V2.MATERIALS)
CHUNK = 45000          # triangles in each new import, well under the compiler's bounded-import size
TOLERANCE = .003       # OBJ positions are written to 0.001; the hull centres are their decagons' means


def sha(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def plan(p):
    """ OBJ ( -e, z, n ) to plan ( e, n, z ). """
    return np.array((-p[0], p[2], p[1]))


def casks(side):
    """ The side's barrels from its wood hulls: plan centre, radius, height and which template drew it. """
    sign = 1 if side == 'west' else -1
    rows = []
    v2 = {tuple(np.round(np.asarray(row['new'], float) * (sign, 1), 3)): row for row in V2.placements()}
    for item in V2.read_hulls(MODELS/f'belltower_{side}_hulls_wood.obj'):
        if len(item['indices']) != 20 or abs(item['z0']) > .01 or round(item['height'], 2) not in (36., 40.):
            continue
        centre = np.round(np.asarray(item['centre']), 3)
        h = round(item['height'])
        r = {36: 13., 40: 15.}[h]
        assert abs(np.ptp(item['obj'][:, 0]) / 2 - r) < .01 or abs(np.ptp(item['obj'][:, 2]) / 2 - r) < .01
        match = next((row for key, row in v2.items() if np.linalg.norm(np.asarray(key) - centre) < .01), None)
        rows.append({'centre': centre, 'west': centre * (sign, 1), 'r': r, 'h': float(h),
                     'kind': 'v2' if match else 'old', 'v2': match})
    assert len(rows) == 23 and sum(r['kind'] == 'v2' for r in rows) == 2, (side, len(rows))
    return sorted(rows, key=lambda r: (r['west'][1], r['west'][0]))


def template(row, side):
    """ The old cask's polygons as {paint: [triangle corners in plan]}, where they're drawn on this side. """
    model = K.Model()
    if row['kind'] == 'v2':
        V2.build(model, tuple(row['v2']['new']), 0., 13., 36., seed=row['v2']['seed'])
    else:
        D.barrel(model, tuple(row['west']), 0., row['r'], row['h'])
    if side == 'east':
        model = model.mirrored()
    triangles = defaultdict(list)
    for paint, items in model.polygons.items():
        for points, _ in items:
            for k in range(1, len(points) - 1):
                triangles[paint].append(np.asarray((points[0], points[k], points[k+1]), float))
    return triangles


def find_faces(path, rows, templates, paints):
    """ Every face of the file that's one of the old casks', as {line number: (cask index, paint)}. """
    centres = np.array([r['centre'] for r in rows])
    reach = np.array([r['r'] + .6 for r in rows])
    lo, hi = centres.min(axis=0) - 16, centres.max(axis=0) + 16
    trees = [{paint: cKDTree(np.concatenate(tris)) for paint, tris in t.items()} for t in templates]
    near = {}; vertex = 0; paint = None; faces = {}
    for number, line in enumerate(path.open('rb')):
        if line.startswith(b'v '):
            vertex += 1
            ox, oz, on = map(float, line.split()[1:4])
            e, n = -ox, on
            if -.5 <= oz <= 41 and lo[0] <= e <= hi[0] and lo[1] <= n <= hi[1]:
                d = np.hypot(centres[:, 0] - e, centres[:, 1] - n)
                # Some casks stand into their neighbours, so a corner can be in reach of more than one.
                owners = frozenset(int(k) for k in np.flatnonzero(d <= reach) if oz <= rows[k]['h'] + .6)
                if owners:
                    near[vertex] = (owners, np.array((e, n, oz)))
        elif line.startswith(b'usemtl '):
            paint = line.split()[1].decode()
        elif line.startswith(b'f ') and near and paint in paints:
            ids = [int(t.split(b'/')[0]) for t in line.split()[1:]]
            if not all(i in near for i in ids):
                continue
            owners = frozenset.intersection(*(near[i][0] for i in ids))
            corners = np.array([near[i][1] for i in ids])
            matches = [k for k in sorted(owners)
                       if paint in trees[k] and trees[k][paint].query(corners)[0].max() < TOLERANCE]
            assert len(matches) <= 1, (path, number)
            if matches:
                faces[number] = (matches[0], paint)
    return faces


def expected(templates, kinds):
    return [Counter({p: len(t) for p, t in tri.items()}) if kind else Counter() for tri, kind in zip(templates, kinds)]


def tally(faces, count):
    found = [Counter() for _ in range(count)]
    for k, paint in faces.values():
        found[k][paint] += 1
    return found


def rewrite(source, target, drop, addition=None):
    """ The file without the dropped face lines, plus the addition's tables before its first usemtl and its faces at
    the end, renumbered after the file's own. Every kept line is the source's byte for byte. """
    counts = {b'v': 0, b'vt': 0, b'vn': 0}
    for line in source.open('rb'):
        key = line.split(b' ', 1)[0]
        if key in counts:
            counts[key] += 1
    tables, faces = [], []
    if addition is not None:
        for line in addition.open('rb'):
            if line.startswith((b'v ', b'vt ', b'vn ')):
                tables.append(line)
            elif line.startswith(b'usemtl '):
                faces.append(line)
            elif line.startswith(b'f '):
                tokens = [b'/'.join(str(int(v) + counts[k]).encode() for k, v in zip((b'v', b'vt', b'vn'), t.split(b'/')))
                          for t in line.split()[1:]]
                faces.append(b'f ' + b' '.join(tokens) + b'\n')
    target.parent.mkdir(parents=True, exist_ok=True)
    lines = source.read_bytes().splitlines(keepends=True)
    kept = [line for number, line in enumerate(lines) if number not in drop]
    at = next((i for i, line in enumerate(kept) if line.startswith(b'usemtl ')), len(kept))
    staged = kept[:at] + tables + kept[at:] + faces
    target.write_bytes(b''.join(staged))
    # The kept lines, in order, are the source's byte for byte with only the dropped faces gone.
    assert all(lines[n].startswith(b'f ') for n in drop) and len(kept) == len(lines) - len(drop)
    assert target.read_bytes() == b''.join(staged)
    return {'removed_triangles': len(drop), 'added_triangles': sum(f.startswith(b'f ') for f in faces),
            'kept_lines_sha256': hashlib.sha256(b''.join(kept)).hexdigest(), 'unrelated_lines_exact': True}


def chunks(models):
    """ Group whole casks into imports of at most CHUNK triangles. """
    groups, current, size = [], [], 0
    for model in models:
        count = model.triangle_count()
        if current and size + count > CHUNK:
            groups.append(current); current, size = [], 0
        current.append(model); size += count
    groups.append(current)
    return groups


def merge(models):
    out = K.Model()
    for m in models:
        out.material_overrides.update(m.material_overrides); out.tile_overrides.update(m.tile_overrides)
        out.grain_paints |= m.grain_paints
        for paint, items in m.polygons.items():
            for index, item in enumerate(items):
                target = len(out.polygons[paint])
                if (paint, index) in m.polygon_uvs:
                    out.polygon_uvs[(paint, target)] = m.polygon_uvs[(paint, index)]
                if (paint, index) in m.polygon_normals:
                    out.polygon_normals[(paint, target)] = m.polygon_normals[(paint, index)]
                out.polygons[paint].append(item)
    return out


def node(template_node, name, filename):
    text = re.sub(r'name = "[^"]+"', f'name = "{name}"', template_node, count=1)
    return re.sub(r'filename = "[^"]+"', f'filename = "{filename}"', text, count=1)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--revision', default='r1')
    args = parser.parse_args()
    assert re.fullmatch('[a-z0-9-]+', args.revision)
    stage = OUT/args.revision/'stage'
    assert not stage.exists(), stage
    stage.mkdir(parents=True)
    work = OUT/args.revision/'work'; work.mkdir(parents=True, exist_ok=True)
    manifest = {'revision': 'belltower-coopered-casks-v3', 'files': {}, 'models': {}, 'source_sha256': {},
                'protected_sha256': {}, 'scene_unchanged': True, 'collision_unchanged': True,
                'only_barrel_faces_removed': True}

    for side in ('west', 'east'):
        rows = casks(side)
        templates = [template(row, side) for row in rows]
        vmdl = MODELS/f'belltower_{side}.vmdl'
        text = vmdl.read_bytes().decode()
        resources = re.findall(r'filename\s*=\s*"([^"]+\.obj)"', text)
        v2_import = f'models/maps/belltower/barrels-v2/{side}.obj'
        assert v2_import in resources

        # The old casks in the canonical record, then in what the model actually imports.
        canonical = MODELS/f'belltower_{side}.obj'
        canonical_faces = find_faces(canonical, rows, templates, OLD_PAINTS | V2_PAINTS)
        whole = expected(templates, [True] * len(rows))
        assert tally(canonical_faces, len(rows)) == whole, ('canonical', side)
        imported, imported_faces = Counter(), {}
        for resource in resources:
            if 'hulls' in resource or resource == v2_import:
                continue
            path = ROOT/'Assets'/resource
            faces = find_faces(path, rows, templates, OLD_PAINTS | V2_PAINTS)
            if faces:
                imported_faces[path] = faces
        found = [Counter() for _ in rows]
        for faces in imported_faces.values():
            for k, c in enumerate(tally(faces, len(rows))):
                found[k] += c
        v2_faces = find_faces(ROOT/'Assets'/v2_import, rows, templates, V2_PAINTS)
        for k, c in enumerate(tally(v2_faces, len(rows))):
            found[k] += c
        assert found == whole, ('imports', side, [(k, dict(a - b), dict(b - a)) for k, (a, b) in enumerate(zip(found, whole)) if a != b])

        # The new casks, built on the west side and mirrored as the map mirrors the whole west half.
        models = []
        for row in rows:
            m = K.Model()
            V3.build(m, tuple(row['west']), 0., row['r'], row['h'])
            models.append(m.mirrored() if side == 'east' else m)
        groups = chunks(models)
        new_imports = []
        for n, group in enumerate(groups):
            path = stage/f'Assets/models/maps/belltower/barrels-v3/{side}_{n}.obj'
            path.parent.mkdir(parents=True, exist_ok=True)
            triangles = K.write_obj(path, merge(group), f'belltower_{side}')
            assert triangles <= CHUNK
            new_imports.append((f'models/maps/belltower/barrels-v3/{side}_{n}.obj', triangles))
        everything = work/f'{side}_all.obj'
        K.write_obj(everything, merge(models), f'belltower_{side}')

        record = {'casks': [{'centre': r['centre'].tolist(), 'radius': r['r'], 'height': r['h'], 'was': r['kind'],
                             'old_triangles': sum(whole[k].values()), 'new_triangles': models[k].triangle_count()}
                            for k, r in enumerate(rows)],
                  'canonical': rewrite(canonical, stage/canonical.relative_to(ROOT), set(canonical_faces), everything),
                  'bounded': [], 'new_imports': [{'filename': f, 'triangles': t} for f, t in new_imports],
                  'retired_import': v2_import}
        for path, faces in imported_faces.items():
            row = rewrite(path, stage/path.relative_to(ROOT), set(faces))
            record['bounded'].append({'path': path.relative_to(ROOT).as_posix(), **row})

        # The model: the v2 pair's node becomes the new imports' nodes, and the new paints get their materials.
        lo, hi = span(text, '_class = "RenderMeshList"'); render = text[lo:hi]
        old = re.search(r'\{\s*_class = "RenderMeshFile"\s*name = "clock_barrels_v2_' + side + r'".*?\n\},?\n', render, re.S)
        assert old, side
        block = old.group(0)
        trailing = ',' if block.rstrip().endswith('},') else ''
        body = block.rstrip().rstrip(',')
        replacement = ',\n'.join(node(body, f'barrels_v3_{side}_{n}', f) for n, (f, _) in enumerate(new_imports))
        updated_render = render.replace(block, replacement + trailing + '\n', 1)
        updated = text[:lo] + updated_render + text[hi:]
        existing = set(re.findall(r'from = "([^"]+)"', updated))
        remaps = ''.join(f'\t\t\t\t\t\t\t{{ from = "{paint}.vmat" to = "{path}" }},\n'
                         for paint, path in sorted(V3.MATERIALS.items()) if paint + '.vmat' not in existing)
        anchor = re.search(r'(?m)^.*\{ from = "[^"]+" to = "[^"]+" \}.*$', updated).group(0)
        updated = updated.replace(anchor, remaps + anchor, 1)
        assert updated.replace(remaps, '', 1).replace(updated_render, render, 1) == text
        assert 'barrels-v2' not in updated and updated.count('models/maps/belltower/barrels-v3/') == len(new_imports)
        (stage/vmdl.relative_to(ROOT)).parent.mkdir(parents=True, exist_ok=True)
        (stage/vmdl.relative_to(ROOT)).write_bytes(updated.encode())
        record['remaps_added'] = sorted(p for p in V3.MATERIALS if p + '.vmat' not in existing)
        manifest['models'][side] = record
        manifest['protected_sha256'][f'Assets/models/maps/belltower/belltower_{side}_hulls_wood.obj'] = \
            sha(MODELS/f'belltower_{side}_hulls_wood.obj')

    V3.write_materials(stage)
    for p in sorted((stage/'Assets').rglob('*')):
        if not p.is_file():
            continue
        relative = p.relative_to(stage).as_posix(); installed = ROOT/relative
        before = sha(installed) if installed.exists() else None
        backup = stage.parent/'before'/relative
        if before:
            backup.parent.mkdir(parents=True, exist_ok=True); shutil.copyfile(installed, backup)
        manifest['files'][relative] = {'source': p.relative_to(ROOT).as_posix(), 'before': before, 'after': sha(p),
                                       'backup': backup.relative_to(ROOT).as_posix() if before else None}
    for path in ('Tools/belltower_barrels_v3.py', 'Tools/belltower_stage_barrels_v3.py', 'Tools/belltower_barrels_v2.py',
                 'Tools/belltower_detail.py', 'Tools/belltower_furniture.py', 'Tools/map_kit.py'):
        manifest['source_sha256'][path] = sha(ROOT/path)
    scene = 'Assets/scenes/maps/Belltower/belltower.scene'
    manifest['protected_sha256'][scene] = sha(ROOT/scene)
    for path in V3.MATERIALS.values():
        if (ROOT/'Assets'/path).exists():
            manifest['protected_sha256']['Assets/' + path] = sha(ROOT/'Assets'/path)
    (stage.parent/'manifest.json').write_text(json.dumps(manifest, indent=2) + '\n')
    summary = {side: {'old_triangles': sum(c['old_triangles'] for c in m['casks']),
                      'new_triangles': sum(c['new_triangles'] for c in m['casks']),
                      'bounded_files_changed': len(m['bounded']), 'new_imports': len(m['new_imports']),
                      'remaps_added': m['remaps_added']} for side, m in manifest['models'].items()}
    print(json.dumps({'files': len(manifest['files']), **summary}, indent=1))


if __name__ == '__main__':
    main()
