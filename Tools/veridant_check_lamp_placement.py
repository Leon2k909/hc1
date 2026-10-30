"""Check staged or installed lantern geometry, floor support and clear routes."""
import argparse
import copy
import itertools
import json
from pathlib import Path
import re

import numpy as np
from scipy.optimize import linprog
from scipy.spatial import ConvexHull
from scipy.spatial.transform import Rotation

import map_kit as K
import veridant_parts as P
from belltower_safe_imports import span
from veridant_lamp_placement import MOVES
from veridant_stage_lamp_placement import ROOT, OUT, sha, key, walk, hull_components


def vector(text, name):
    match = re.search(r'\b' + name + r'\s*=\s*\[([^\]]+)\]', text)
    assert match, name
    return np.asarray([float(v) for v in match[1].split(',')])


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--stage', required=True)
    parser.add_argument('--installed', action='store_true')
    args = parser.parse_args()
    stage = OUT / args.stage
    manifest = json.loads((stage / 'manifest.json').read_text())
    def active(relative):
        staged = stage / relative
        return staged if staged.exists() and not args.installed else ROOT / relative

    for relative, item in manifest['files'].items():
        assert sha(active(relative)) == item['after'], relative
        assert sha(ROOT / item['backup']) == item['before'], relative
    for relative, digest in manifest['protected_sha256'].items():
        assert sha(ROOT / relative) == digest, relative
    scene = json.loads(active('Assets/scenes/maps/Veridant/veridant.scene').read_text())
    scene_key = 'Assets/scenes/maps/Veridant/veridant.scene'
    before = json.loads((ROOT / manifest['files'][scene_key]['backup']).read_text())
    expected = copy.deepcopy(before)
    expected_nodes = {n['Name']: n for n in walk(expected) if n.get('Name') in MOVES}
    for name, move in MOVES.items():
        expected_nodes[name]['Position'] = K.vec(K.to_world(np.asarray(move['new']) + (0, 0, move['height'] - 8)))
    assert scene == expected, 'Scene changes must be limited to eight light positions.'
    namespace = dict(vars(P))
    exec((stage / 'original-lantern.py.txt').read_text(), namespace)
    original = namespace['lantern_post']
    for name, move in MOVES.items():
        old, new = K.Model(), K.Model()
        original(old, name, move['old'], move['height'], light=False)
        P.lantern_post(new, name, move['new'], move['height'], light=False)
        delta = np.asarray(move['new']) - np.asarray(move['old'])
        assert old.triangle_count() == new.triangle_count()
        assert old.polygons.keys() == new.polygons.keys()
        for paint, rows in old.polygons.items():
            assert len(rows) == len(new.polygons[paint])
            for (points, normal), (moved, moved_normal) in zip(rows, new.polygons[paint]):
                assert np.allclose(np.asarray(points) + delta, moved)
                assert np.allclose(normal, moved_normal)
    candidates = []
    self_hulls = {}
    fixture_samples = {}
    for name, move in MOVES.items():
        unit = K.Model()
        P.lantern_post(unit, name, move['new'], move['height'], light=False)
        self_hulls[name] = [frozenset(key(K.to_world(p)) for p in pts) for pts, s in unit.hulls]
        fixture_samples[name] = [np.asarray([K.to_world(p) for p in pts]) for pts, s in unit.hulls]
    target_bounds = {n: (np.vstack(pts).min(0), np.vstack(pts).max(0))
                     for n, pts in fixture_samples.items()}

    def nearby(lo, hi):
        return any(np.all(np.minimum(hi, b) - np.maximum(lo, a) >= -.1)
                   for a, b in target_bounds.values())

    def add(label, points):
        points = np.asarray(points)
        lo, hi = points.min(0), points.max(0)
        if nearby(lo, hi):
            hull = ConvexHull(points)
            candidates.append((label, points, lo, hi, hull.equations))

    docs = []
    for node in walk(scene):
        if node.get('Name') in ('Ground', 'Buildings', 'Dressing', 'Glass'):
            assert node.get('Position') in (None, '0,0,0')
            assert node.get('Scale') in (None, '1,1,1')
            assert node.get('Rotation') in (None, '0,0,0,1')
            collider = next(c for c in node['Components'] if c.get('__type') == 'Sandbox.ModelCollider')
            path = collider['Model']['Path']
            docs.append('Assets/' + path)
    assert len(docs) == 4
    count_boxes, count_hulls = 0, 0
    for relative in docs:
        text = (ROOT / relative).read_text()
        if '_class = "PhysicsShapeList"' not in text:
            continue
        a, b = span(text, '_class = "PhysicsShapeList"')
        physics = text[a:b]
        for index, match in enumerate(re.finditer('_class = "PhysicsShapeBox"', physics)):
            a, b = span(physics[physics.rfind('{', 0, match.start()):], '_class = "PhysicsShapeBox"')
            # span() starts from the nearest preceding brace; this slice starts
            # at that brace, so nested text cannot select an earlier box.
            offset = physics.rfind('{', 0, match.start())
            block = physics[offset:][a:b]
            origin, angles, size = (vector(block, n) for n in ('origin', 'angles', 'dimensions'))
            pitch, yaw, roll = angles
            turn = Rotation.from_euler('ZYX', (yaw, pitch, roll), degrees=True)
            points = turn.apply(np.asarray(list(itertools.product((-1, 1), repeat=3))) * size / 2) + origin
            add(f'{relative}:box:{index}', points)
            count_boxes += 1
        for path in re.findall(r'filename\s*=\s*"([^"]+\.obj)"', physics):
            source = active('Assets/' + path)
            lines, points, line_ids, components = hull_components(source)
            # Hull OBJ axes are (world Y, world Z, world X).
            points = points[:, (2, 0, 1)]
            for index, ids in enumerate(components):
                add(f'{path}:hull:{index}', points[ids])
            count_hulls += len(components)
    report = []
    failures = []
    lights = {n['Name']: n for n in walk(scene) if n.get('Name') in MOVES}
    for name, move in MOVES.items():
        base = K.to_world(np.asarray(move['new']))
        foot_point = base - (0, 0, .05)
        support = [label for label, pts, lo, hi, eq in candidates
                   if np.all(foot_point >= lo - .001) and np.all(foot_point <= hi + .001)
                   and np.all(eq[:, :3] @ foot_point + eq[:, 3] <= .001)]
        assert support, ('No physical floor beneath lantern', name)
        collisions = []
        for fixture in fixture_samples[name]:
            flo, fhi = fixture.min(0), fixture.max(0)
            feq = ConvexHull(fixture).equations
            for label, pts, lo, hi, eq in candidates:
                if any(frozenset(key(p) for p in pts) == signature for signature in self_hulls[name]):
                    continue
                if np.any(np.minimum(fhi, hi) - np.maximum(flo, lo) <= .001):
                    continue
                both = np.vstack((feq, eq))
                result = linprog(np.zeros(3), A_ub=both[:, :3], b_ub=-both[:, 3] - .001,
                                 bounds=((None, None),) * 3, method='highs')
                if result.success:
                    collisions.append(label)
        if collisions:
            failures.append({'name': name, 'collisions': sorted(set(collisions))})
        expected = K.to_world(np.asarray(move['new']) + (0, 0, move['height'] - 8))
        assert np.allclose(np.asarray(lights[name]['Position'].split(','), float), expected)
        report.append({'name': name, 'base': move['new'], 'physical_floor_support': True,
                       'intersections': sorted(set(collisions)), 'point_light_aligned': True})
    result = {'revision': manifest['revision'], 'installed': args.installed,
              'original_design_retained': True, 'lamps_audited': 32, 'lamps_moved': len(MOVES),
              'lantern_shape_exact_translations': True, 'triangle_count_unchanged': True,
              'scene_only_eight_position_changes': True,
              'physics_boxes_examined': count_boxes, 'physics_hulls_examined': count_hulls,
              'nearby_solids_examined': len(candidates), 'placements': report, 'failures': failures,
              'native_visual_check': 'Pending: the s&box editor is closed.'}
    (OUT / ('validation-installed.json' if args.installed else 'validation-staged.json')).write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps(result, indent=2))
    assert not failures, 'Resolve geometry intersections before publishing.'


if __name__ == '__main__':
    main()
