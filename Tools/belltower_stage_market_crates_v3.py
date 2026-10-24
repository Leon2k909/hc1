"""Stage just the mirrored Market Street crate group and its three cover boxes."""
import argparse
import hashlib
import json
import math
from collections import Counter
from pathlib import Path
import re
import shutil
import numpy as np

import map_kit as K
import belltower_map as B
import belltower_detail as D
import belltower_crates as C
import belltower_market_crates_v3 as M
from belltower_safe_imports import span

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT/'output/belltower/crates-v3-20261021'
STAGE = OUT/'stage'


def sha(path):
    with path.open('rb') as stream: return hashlib.file_digest(stream, 'sha256').hexdigest()


def pos(value):
    return tuple(int(round(float(v)*1000)) for v in value.split())


def keys(model):
    values = Counter()
    for material, polygons in model.polygons.items():
        for points, _ in polygons:
            p = [pos(K.obj_vector(K.to_world(v))) for v in points]
            for k in range(1, len(p)-1): values[(material.encode(), frozenset((p[0], p[k], p[k+1])))] += 1
    return values


def patch(source, wanted, addition=None):
    before = sha(source)
    points = {p for material, face in wanted for p in face}
    sparse = {}; counts = {'v': 0, 'vt': 0, 'vn': 0}; material = None; found = Counter(); drop = set()
    for number, line in enumerate(source.open('rb')):
        if line.startswith(b'v '):
            counts['v'] += 1; p = pos(line[2:].decode())
            if p in points: sparse[counts['v']] = p
        elif line.startswith(b'vt '): counts['vt'] += 1
        elif line.startswith(b'vn '): counts['vn'] += 1
        elif line.startswith(b'usemtl '): material = line.split()[1]
        elif line.startswith(b'f '):
            indices = [int(t.split(b'/')[0]) for t in line.split()[1:]]
            if all(i in sparse for i in indices):
                key = (material, frozenset(sparse[i] for i in indices))
                if key in wanted: found[key] += 1; drop.add(number)
    if not drop:
        return None, found
    assert found <= wanted
    target = STAGE/source.relative_to(ROOT); target.parent.mkdir(parents=True, exist_ok=True)
    tables, tail = [], []
    if addition:
        for line in addition.open('rb'):
            if line.startswith((b'v ', b'vt ', b'vn ')): tables.append(line)
            elif line.startswith(b'usemtl '): tail.append(line)
            elif line.startswith(b'f '):
                tokens = []
                for token in line.split()[1:]:
                    tokens.append('/'.join(str(int(v)+counts[k]) for k, v in zip(counts, token.split(b'/'))))
                tail.append(('f '+' '.join(tokens)+'\n').encode())
    inserted = False; preserved = hashlib.sha256()
    with target.open('wb') as output:
        for number, line in enumerate(source.open('rb')):
            if not inserted and line.startswith(b'usemtl '): output.writelines(tables); inserted = True
            if number not in drop: output.write(line); preserved.update(line)
        output.writelines(tail)
    assert inserted and sha(source) == before
    # Reconstruct the kept stream independently, stripping only our new spans.
    kept = b''.join(line for i, line in enumerate(source.open('rb')) if i not in drop)
    current = target.read_bytes()
    if tables: current = current.replace(b''.join(tables), b'', 1)
    if tail: current = current[:-len(b''.join(tail))]
    assert current == kept
    return {'removed': len(drop), 'added': sum(l.startswith(b'f ') for l in tail),
            'all_other_obj_bytes_exact': True, 'other_obj_bytes_sha256': preserved.hexdigest()}, found


BOX = re.compile(r'\{\s*_class = "PhysicsShapeBox"[^{}]*\}', re.S)


def boxes(text):
    result = []
    for match in BOX.finditer(text):
        node = match.group()
        origin = tuple(map(float, re.search(r'origin = \[ ([^]]+) \]', node).group(1).split(',')))
        result.append((match, origin))
    return result


def patch_vmdl(source, old_collision, new_collision, resource, side):
    text = source.read_bytes().decode('utf-8')
    expected = [K.to_world(c[0]) for c in old_collision.boxes]
    # Let the established exporter calculate the exact mirrored rotation basis.
    temp = STAGE/(side+'-collision.vmdl')
    K.write_vmdl(temp, 'models/maps/belltower/market-crates-v3', side, new_collision)
    replacements = boxes(temp.read_text())
    assert len(replacements) == len(expected) == 3
    matches = []
    for match, origin in boxes(text):
        ids = [i for i, p in enumerate(expected) if np.max(np.abs(p-origin)) < .0002]
        if ids:
            assert len(ids) == 1
            matches.append((match, ids[0]))
    assert len(matches) == 3 and len({i for _, i in matches}) == 3
    updated = text
    for match, index in sorted(matches, key=lambda p: p[0].start(), reverse=True):
        original_node = match.group(); new_node = replacements[index][0].group()
        # Existing surface/tags/dimensions stay exactly as authored. Only the
        # positions and orientations of these three cover boxes may change.
        for field in ('origin', 'angles'):
            value = re.search(field+r' = \[ [^]]+ \]', new_node).group()
            original_node = re.sub(field+r' = \[ [^]]+ \]', lambda m: value, original_node, count=1)
        updated = updated[:match.start()]+original_node+updated[match.end():]
    lo, hi = span(updated, '_class = "RenderMeshList"')
    render = updated[lo:hi]
    a, b = span(render, '_class = "RenderMeshFile"')
    template = render[a:b]
    name = 'market_crates_v3_'+side
    node = re.sub(r'name = "[^"]+"', f'name = "{name}"', template, count=1)
    node = re.sub(r'filename = "[^"]+"', f'filename = "{resource}"', node, count=1)
    end = render.rfind(']')
    new_render = render[:end]+'\n'+node+',\n'+render[end:]
    updated = updated[:lo]+new_render+updated[hi:]
    target = STAGE/source.relative_to(ROOT); target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(updated.encode('utf-8'))
    return {'cover_boxes_moved': 3, 'other_physics_nodes_preserved': True, 'render_import_added': resource}


def main():
    global STAGE
    parser = argparse.ArgumentParser()
    parser.add_argument('--stage', default='stage')
    args = parser.parse_args()
    assert re.fullmatch(r'[a-z0-9-]+', args.stage)
    STAGE = OUT/args.stage
    assert not (STAGE/'manifest.json').exists(), 'Keep staged evidence.'
    STAGE.mkdir(parents=True, exist_ok=True)
    old, new, old_collision, new_collision = [K.Model() for _ in range(4)]
    placements = []
    for index, (origin, x, size) in enumerate(M.OLD_ROWS):
        yaw = math.degrees(math.atan2(x[1], x[0]))
        original = B.Place(origin, yaw)
        destination, angle = M.location(index, yaw)
        replacement = B.Place(destination, angle)
        C.build(old, original, size); M.build(new, replacement, size)
        h = size/2
        original.box(old_collision, (-h, -h, 0), (h, h, size), None, B.WOOD)
        replacement.box(new_collision, (-h, -h, 0), (h, h, size), None, B.WOOD)
        placements.append({'old': list(origin), 'new': list(destination), 'size': size, 'yaw': angle})
        # Storage lies in the gap beside the stall (ending at e=-1540), before
        # the alley (beginning at e=-1400), clear of the facade at n=1100.
        vertices = np.array([replacement.at((a, b, c)) for a in (-h, h) for b in (-h, h) for c in (0, size)])
        assert vertices[:, 0].min() > -1540 and vertices[:, 0].max() < -1400
        assert vertices[:, 1].min() > 1103 and vertices[:, 1].max() < 1200
        # Conservative nearest distance to the lamp's 6-inch collision base.
        lo, hi = vertices[:, :2].min(axis=0), vertices[:, :2].max(axis=0)
        delta = np.maximum(np.maximum(lo-(-1450., 1122.), (-1450., 1122.)-hi), 0.)
        assert np.linalg.norm(delta) > 10.
    D.configure(old); D.configure(new)
    report = {'revision': 'market-crates-v3', 'crates': 6, 'placements_west': placements,
              'reason': 'Move the pictured Market Street stack and its mirrored copy out of the alley approach, into stall-side storage.',
              'scene_unchanged': True, 'other_crates_unchanged': True, 'files': {}, 'models': {},
              'protected_sha256': {}, 'source_sha256': {}}
    for p in ['Tools/belltower_crates.py', 'Tools/belltower_furniture.py', 'Tools/map_kit.py',
              'Tools/belltower_market_crates_v3.py', 'Tools/belltower_stage_market_crates_v3.py']:
        report['source_sha256'][p] = sha(ROOT/p)
    report['protected_sha256']['Assets/scenes/maps/Belltower/belltower.scene'] = sha(ROOT/'Assets/scenes/maps/Belltower/belltower.scene')
    for side in ('west', 'east'):
        previous, candidate = (old, new) if side == 'west' else (old.mirrored(), new.mirrored())
        before_collision, after_collision = (old_collision, new_collision) if side == 'west' else (old_collision.mirrored(), new_collision.mirrored())
        relative = Path(f'Assets/models/maps/belltower/market-crates-v3/{side}.obj')
        piece = STAGE/relative; piece.parent.mkdir(parents=True, exist_ok=True)
        K.write_obj(piece, candidate, f'belltower_{side}')
        wanted = keys(previous)
        canonical = ROOT/f'Assets/models/maps/belltower/belltower_{side}.obj'
        preservation, found = patch(canonical, wanted, piece)
        assert found == wanted, ('Canonical crate geometry differs', side, sum(found.values()), sum(wanted.values()))
        vmdl = canonical.with_suffix('.vmdl')
        refs = re.findall(r'filename\s*=\s*"([^"]+\.obj)"', vmdl.read_text())
        found_all = Counter(); changed = []
        for path in refs:
            if not any(t in path for t in ('furniture_wood', 'garden_endgrain', 'iron_black')): continue
            source = ROOT/'Assets'/path
            result, found = patch(source, wanted)
            if result:
                found_all += found; changed.append({'resource': path, **result})
        assert found_all == wanted, ('Bounded imports differ', side, sum(found_all.values()), sum(wanted.values()))
        physics = patch_vmdl(vmdl, before_collision, after_collision, relative.relative_to('Assets').as_posix(), side)
        report['models'][side] = {'preservation': preservation, 'changed_imports': changed, **physics}
    for p in (STAGE/'Assets').rglob('*'):
        if not p.is_file(): continue
        relative = p.relative_to(STAGE); actual = ROOT/relative
        before = sha(actual) if actual.exists() else None
        backup = OUT/('before' if args.stage == 'stage' else 'before-'+args.stage)/relative
        if before:
            backup.parent.mkdir(parents=True, exist_ok=True); shutil.copyfile(actual, backup)
            assert sha(backup) == before
        report['files'][relative.as_posix()] = {'source': p.relative_to(ROOT).as_posix(), 'before': before,
            'after': sha(p), 'backup': backup.relative_to(ROOT).as_posix() if before else None}
    (STAGE/'manifest.json').write_text(json.dumps(report, indent=2)+'\n')
    print(json.dumps({'crates': 6, 'files': len(report['files']), 'models': report['models']}))


if __name__ == '__main__': main()
