"""Stage the two nudged casks (belltower_barrels_v3.NUDGED) on each side, on top of the published v3 casks.

Each one's v3 cask is taken out of its barrels-v3 import and the canonical record by matching its faces against the
generator's cask at the old centre, and the cask for the new centre goes into the same import. Its ten-sided wood hull
moves by the same offset, vertex for vertex; every other line of every file is kept byte for byte. Only staged files
are written; Sources/Belltower/editor/import-barrels-v3-nudge.cs.txt publishes them through the editor.
"""
import argparse
from collections import Counter, defaultdict
import hashlib
import json
from pathlib import Path
import re
import shutil
import numpy as np

import map_kit as K
import belltower_barrels_v2 as V2
import belltower_barrels_v3 as V3
import belltower_furniture as F
import belltower_stage_barrels_v3 as S

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT/'output/belltower/barrels-v3'
MODELS = ROOT/'Assets/models/maps/belltower'
PAINTS = set(V3.MATERIALS) | {F.DARK}
SIDES = {'west': 1, 'east': -1}


def cask(centre, side):
    """ The v3 cask built at a west centre, drawn where it stands on this side. """
    model = K.Model()
    V3.build(model, tuple(centre), 0., 13., 36.)
    return model.mirrored() if side == 'east' else model


def triangles(model):
    out = defaultdict(list)
    for paint, items in model.polygons.items():
        for points, _ in items:
            for k in range(1, len(points) - 1):
                out[paint].append(np.asarray((points[0], points[k], points[k+1]), float))
    return out


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--revision', default='r2')
    args = parser.parse_args()
    assert re.fullmatch('[a-z0-9-]+', args.revision)
    stage = OUT/args.revision/'stage'
    assert not stage.exists(), stage
    stage.mkdir(parents=True)
    work = OUT/args.revision/'work'; work.mkdir(parents=True, exist_ok=True)
    manifest = {'revision': 'belltower-coopered-casks-v3-nudge', 'files': {}, 'models': {}, 'source_sha256': {},
                'protected_sha256': {}, 'scene_unchanged': True, 'only_nudged_casks_changed': True}
    for side, sign in SIDES.items():
        record = {'moves': [], 'files': []}
        rows, templates, added = [], [], []
        for old, new in V3.NUDGED.items():
            rows.append({'centre': np.array(old) * (sign, 1), 'r': 13., 'h': 36.})
            templates.append(triangles(cask(old, side)))
            added.append(cask(new, side))
            record['moves'].append({'old': (np.array(old) * (sign, 1)).tolist(), 'new': (np.array(new) * (sign, 1)).tolist()})
        whole = S.expected(templates, [True] * len(rows))

        # The import each cask is drawn in, and the canonical record.
        imports = sorted(MODELS.glob(f'barrels-v3/{side}_*.obj'))
        located = {}
        for path in imports + [MODELS/f'belltower_{side}.obj']:
            faces = S.find_faces(path, rows, templates, PAINTS)
            if faces:
                located[path] = faces
        canonical = MODELS/f'belltower_{side}.obj'
        assert S.tally(located.pop(canonical), len(rows)) == whole, ('canonical', side)
        found = [Counter() for _ in rows]; owner = {}
        for path, faces in located.items():
            for k, c in enumerate(S.tally(faces, len(rows))):
                if c:
                    assert c == whole[k] and k not in owner, ('a cask split across imports', side, k)
                    owner[k] = path
                found[k] += c
        assert found == whole, ('imports', side)

        canonical_faces = S.find_faces(canonical, rows, templates, PAINTS)
        everything = work/f'{side}_added.obj'
        K.write_obj(everything, S.merge(added), f'belltower_{side}')
        row = S.rewrite(canonical, stage/canonical.relative_to(ROOT), set(canonical_faces), everything)
        record['files'].append({'path': canonical.relative_to(ROOT).as_posix(), **row})
        for path in sorted(set(owner.values())):
            mine = [k for k, p in owner.items() if p == path]
            addition = work/f'{side}_{path.stem}_added.obj'
            K.write_obj(addition, S.merge([added[k] for k in mine]), f'belltower_{side}')
            row = S.rewrite(path, stage/path.relative_to(ROOT), set(located[path]), addition)
            assert row['removed_triangles'] - row['added_triangles'] + sum(1 for l in path.open('rb') if l.startswith(b'f ')) <= S.CHUNK + 6000
            record['files'].append({'path': path.relative_to(ROOT).as_posix(), **row})
            # The import's material list needs every paint the new casks use.
            mtl = path.with_suffix('.mtl'); names = set(re.findall(r'(?m)^newmtl (\S+)', mtl.read_text()))
            assert all(p in names for m in (added[k] for k in mine) for p in m.polygons), ('mtl', path)

        # The hulls move with their casks, vertex for vertex.
        hull_path = MODELS/f'belltower_{side}_hulls_wood.obj'
        lines = hull_path.read_bytes().splitlines(keepends=True); changed = set()
        for item in V2.read_hulls(hull_path):
            for move in record['moves']:
                old, new = np.array(move['old']), np.array(move['new'])
                if np.linalg.norm(np.asarray(item['centre']) - old) > .01 or abs(item['height'] - 36) > .001:
                    continue
                delta = new - old
                for number, point in zip(item['lines'], item['obj']):
                    moved = point + np.array((-delta[0], 0, delta[1]))
                    ending = b'\r\n' if lines[number].endswith(b'\r\n') else b'\n'
                    lines[number] = ('v ' + ' '.join(f'{v:.3f}' for v in moved)).encode() + ending
                    changed.add(number)
        assert len(changed) == 40, (side, len(changed))
        target = stage/hull_path.relative_to(ROOT); target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(b''.join(lines))
        before = hull_path.read_bytes().splitlines(keepends=True)
        assert all(a == b for i, (a, b) in enumerate(zip(before, lines)) if i not in changed) and len(before) == len(lines)
        record['hull_vertices_moved'] = len(changed)
        record['all_other_hull_bytes_exact'] = True
        manifest['models'][side] = record
        manifest['protected_sha256'][f'Assets/models/maps/belltower/belltower_{side}.vmdl'] = sha(MODELS/f'belltower_{side}.vmdl')

    for p in sorted((stage/'Assets').rglob('*')):
        if not p.is_file():
            continue
        relative = p.relative_to(stage).as_posix(); installed = ROOT/relative
        before = sha(installed)
        backup = stage.parent/'before'/relative
        backup.parent.mkdir(parents=True, exist_ok=True); shutil.copyfile(installed, backup)
        manifest['files'][relative] = {'source': p.relative_to(ROOT).as_posix(), 'before': before, 'after': sha(p),
                                       'backup': backup.relative_to(ROOT).as_posix()}
    for path in ('Tools/belltower_barrels_v3.py', 'Tools/belltower_stage_barrels_v3.py',
                 'Tools/belltower_stage_barrels_v3_nudge.py', 'Tools/belltower_furniture.py', 'Tools/map_kit.py'):
        manifest['source_sha256'][path] = sha(ROOT/path)
    scene = 'Assets/scenes/maps/Belltower/belltower.scene'
    manifest['protected_sha256'][scene] = sha(ROOT/scene)
    (stage.parent/'manifest.json').write_text(json.dumps(manifest, indent=2) + '\n')
    print(json.dumps({'files': sorted(manifest['files']),
                      **{side: [(f['path'].split('/')[-1], f['removed_triangles'], f['added_triangles']) for f in m['files']]
                         for side, m in manifest['models'].items()}}, indent=1))


def sha(path):
    return S.sha(path)


if __name__ == '__main__':
    main()
