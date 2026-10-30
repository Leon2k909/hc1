"""Move only the eight original lanterns, their hulls and matching point lights.

This stages sparse OBJ edits from the *active* VMDL imports. Existing vertex
indices and all unrelated bytes are preserved. It never runs the map generator.
"""
import copy
import argparse
import hashlib
import inspect
import json
from pathlib import Path
import re
import shutil

import numpy as np
import map_kit as K
import veridant_parts as P
import veridant_materials as VM
from belltower_safe_imports import span
import railhead_stage_extinguisher as Patch
from veridant_lamp_placement import MOVES

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'output/veridant/lamp-placement-v1'


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def key(point):
    return tuple(round(float(x), 3) + 0. for x in point)


def walk(value):
    if isinstance(value, dict):
        yield value
        for child in value.values():
            yield from walk(child)
    elif isinstance(value, list):
        for child in value:
            yield from walk(child)


def lamps():
    data = json.loads((ROOT / 'Assets/scenes/maps/Veridant/veridant.scene').read_text())
    return {node['Name']: node for node in walk(data)
            if node.get('Name') and any(c.get('__type') == 'Sandbox.PointLight'
                                      for c in node.get('Components', []))}


def hull_components(path):
    lines = Path(path).read_bytes().splitlines(keepends=True)
    vertices, line_indices, parent = [], [], []

    def find(x):
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    for number, line in enumerate(lines):
        if line.startswith(b'v '):
            vertices.append(tuple(map(float, line.split()[1:4])))
            line_indices.append(number)
            parent.append(len(parent))
        elif line.startswith(b'f '):
            ids = [int(p.split(b'/')[0]) - 1 for p in line.split()[1:]]
            for i in ids[1:]:
                a, b = find(ids[0]), find(i)
                parent[a] = b
    groups = {}
    for i in range(len(vertices)):
        groups.setdefault(find(i), []).append(i)
    return lines, np.asarray(vertices), line_indices, list(groups.values())


def translate_hulls(source, destination, old_models, subset):
    lines, vertices, line_indices, groups = hull_components(source)
    signatures = {}
    for ids in groups:
        signature = frozenset(key(vertices[i]) for i in ids)
        assert signature not in signatures, 'Duplicate hull components need review.'
        signatures[signature] = ids
    modified, receipt = set(), []
    for name, move in subset.items():
        delta = K.to_world(np.asarray(move['new']) - np.asarray(move['old']))[[1, 2, 0]]
        for points, surface in old_models[name].hulls:
            assert surface == 'metal'
            signature = frozenset(key(K.to_world(p)[[1, 2, 0]]) for p in points)
            assert signature in signatures, ('Old collision hull not found', name)
            ids = signatures[signature]
            assert not modified.intersection(ids)
            modified.update(ids)
            for i in ids:
                new = vertices[i] + delta
                lines[line_indices[i]] = ('v ' + ' '.join(f'{x:.3f}' for x in new) + '\n').encode()
            receipt.append({'name': name, 'vertices': len(ids), 'delta_obj': delta.tolist()})
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_bytes(b''.join(lines))
    new_lines, new_vertices, new_line_ids, new_groups = hull_components(destination)
    assert len(new_groups) == len(groups)
    original_lines = source.read_bytes().splitlines(keepends=True)
    changed_lines = {line_indices[i] for i in modified}
    assert all(a == b for i, (a, b) in enumerate(zip(original_lines, new_lines)) if i not in changed_lines)
    assert len(original_lines) == len(new_lines)
    return {'hulls_moved': len(receipt), 'vertices_moved': len(modified),
            'other_collision_bytes_exact': True, 'components': receipt}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--stage', required=True)
    args = parser.parse_args()
    assert re.fullmatch('stage-[a-z0-9-]+', args.stage)
    OUT.mkdir(parents=True, exist_ok=True)
    stage = OUT / args.stage
    assert not stage.exists(), 'Preserve earlier stages.'
    stage.mkdir()
    # Capture the unmodified original design. The layout hook is inserted only
    # after this stage, so this function must still use its input base directly.
    old_source = inspect.getsource(P.lantern_post)
    assert 'placed_base' not in old_source
    (stage / 'original-lantern.py.txt').write_text(old_source)
    old_models = {}
    light_rows = lamps()
    all_lamps = json.loads((ROOT / 'output/veridant/lantern-roof-v1/manifest.json').read_text())['lamps']
    audit = []
    for fixture in all_lamps:
        name = fixture['name']
        node = light_rows[name]
        position = np.array(tuple(map(float, node['Position'].split(','))))
        expected = K.to_world(np.asarray(fixture['base']) + (0, 0, fixture['h'] - 8))
        assert np.allclose(position, expected), ('Scene/source position changed', name)
        move = MOVES.get(name)
        if move:
            assert tuple(fixture['base']) == move['old'] and fixture['h'] == move['height']
        audit.append({**fixture, 'moved': move is not None,
                      'new_base': list(move['new']) if move else fixture['base'],
                      'reason': move['reason'] if move else 'Retained: already at a boundary, planting margin or gate pier.'})
    assert len(audit) == 32 and sum(r['moved'] for r in audit) == len(MOVES)
    files, protected, geometry = {}, {}, {}

    def record(relative):
        relative = Path(relative)
        source, target = ROOT / relative, stage / relative
        backup = stage / 'before' / relative
        backup.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, backup)
        files[relative.as_posix()] = {'before': sha(source), 'after': sha(target),
            'source': target.relative_to(ROOT).as_posix(), 'backup': backup.relative_to(ROOT).as_posix()}

    for name, move in MOVES.items():
        old = K.Model()
        P.lantern_post(old, name, move['old'], move['height'], light=False)
        assert len(old.hulls) == 2 and not old.boxes
        old_models[name] = old
    for model_name in sorted({m['model'] for m in MOVES.values()}):
        subset = {n: m for n, m in MOVES.items() if m['model'] == model_name}
        doc = Path(f'Assets/models/maps/veridant/{model_name}.vmdl')
        text = (ROOT / doc).read_text()
        a, b = span(text, '_class = "RenderMeshList"')
        imports = re.findall(r'filename\s*=\s*"([^"]+\.obj)"', text[a:b])
        bases = [p for p in imports if p.endswith('-base.obj')]
        assert len(bases) == 1, ('Inspect active base imports', model_name, imports)
        base = Path('Assets') / bases[0]
        protected[doc.as_posix()] = sha(ROOT / doc)
        for p in imports:
            if p != bases[0]:
                protected['Assets/' + p] = sha(ROOT / 'Assets' / p)
        old, new = K.Model(), K.Model()
        for name, move in subset.items():
            P.lantern_post(old, name, move['old'], move['height'], light=False)
            P.lantern_post(new, name, move['new'], move['height'], light=False)
        assert old.triangle_count() == new.triangle_count()
        new.tile_overrides.update({p: VM.TILES.get(p, 64.) for p in new.polygons})
        fragment = stage / f'fragments/{model_name}.obj'
        fragment.parent.mkdir(exist_ok=True)
        K.write_obj(fragment, new, model_name)
        lookup, polygons = Patch.lookup_polygons(old)
        detail, found = Patch.replace_obj(ROOT / base, stage / base,
                                         stage / f'proof/{model_name}-retained.obj', lookup, fragment)
        Patch.coverage(found, lookup, polygons)
        assert detail['removed_triangles'] == old.triangle_count()
        record(base)
        hull = Path(f'Assets/models/maps/veridant/{model_name}_hulls_metal.obj')
        hull_detail = translate_hulls(ROOT / hull, stage / hull, old_models, subset)
        assert hull_detail['hulls_moved'] == 2 * len(subset)
        record(hull)
        geometry[model_name] = {**detail, **hull_detail, 'lamps': len(subset),
                                'added_triangles': new.triangle_count(), 'base_import': base.as_posix()}
    relative = Path('Assets/scenes/maps/Veridant/veridant.scene')
    before_text = (ROOT / relative).read_text()
    before_json = json.loads(before_text)
    expected = copy.deepcopy(before_json)
    expected_nodes = {node['Name']: node for node in walk(expected) if node.get('Name') in MOVES}
    after_text, scene_moves = before_text, []
    for name, move in MOVES.items():
        node = light_rows[name]
        old_position = node['Position']
        new_position = K.vec(K.to_world(np.asarray(move['new']) + (0, 0, move['height'] - 8)))
        pattern = (r'("__guid":\s*"' + re.escape(node['__guid']) +
                   r'"(?:(?!"__guid").)*?"Position":\s*")' + re.escape(old_position) + r'(")')
        after_text, count = re.subn(pattern, lambda m: m[1] + new_position + m[2], after_text, flags=re.S)
        assert count == 1, ('Unique point light not found', name)
        expected_nodes[name]['Position'] = new_position
        scene_moves.append({'name': name, 'id': node['__guid'], 'before': old_position,
                            'after': new_position})
    assert json.loads(after_text) == expected, 'An unrelated scene property changed.'
    (stage / relative).parent.mkdir(parents=True, exist_ok=True)
    (stage / relative).write_text(after_text)
    record(relative)
    for p in ('Assets/models/maps/veridant/veridant_buildings.obj',
              'Assets/models/maps/veridant/veridant_dress.obj',
              'Assets/materials/veridant/vr_steel.vmat', 'Assets/materials/veridant/vr_lamp.vmat'):
        protected[p] = sha(ROOT / p)
    manifest = {'revision': 'veridant-lamp-placement-v1', 'files': files,
                'protected_sha256': protected, 'audit': audit, 'geometry': geometry,
                'scene_moves': scene_moves, 'original_design_retained': True,
                'unchanged_lanterns': 32 - len(MOVES), 'lamps_moved': len(MOVES),
                'new_fixture_unused': True, 'source_hook_pending': True}
    for p, item in files.items():
        assert sha(ROOT / p) == item['before'] and sha(ROOT / item['source']) == item['after']
    for p, digest in protected.items():
        assert sha(ROOT / p) == digest
    (stage / 'manifest.json').write_text(json.dumps(manifest, indent=2) + '\n')
    print(json.dumps({'lamps_audited': len(audit), 'lamps_moved': len(MOVES),
                      'files_staged': len(files), 'old_design_retained': True,
                      'geometry': geometry}, indent=2))


if __name__ == '__main__':
    main()
