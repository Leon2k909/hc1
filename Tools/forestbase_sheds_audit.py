"""Independent checks of serialized hall geometry; no editor or engine access."""
import collections
import hashlib
import json
import math
import re
from pathlib import Path

import numpy as np
import forestbase_structure_audit as A

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'output/forestbase'
BEFORE = OUT / 'sheds-before/Assets/models/maps/forestbase'
STAGE = OUT / 'sheds-stage'
MODELS = ROOT / 'Assets/models/maps/forestbase'
HALLS = {'motor': (-1060, -555, 720, 390), 'workshop': (1100, 520, 660, 560)}


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def hull_elements(path):
    """Recover disconnected HullPerElement geometry, independent of file ordering."""
    vertices, faces = [], []
    for line in path.read_text().splitlines():
        s = line.split()
        if s and s[0] == 'v':
            vertices.append(tuple(map(float, s[1:4])))
        elif s and s[0] == 'f':
            faces.append(tuple(int(i)-1 for i in s[1:]))
    parents = list(range(len(vertices)))
    def find(i):
        while i != parents[i]:
            parents[i] = parents[parents[i]]
            i = parents[i]
        return i
    for face in faces:
        for i in face[1:]:
            parents[find(i)] = find(face[0])
    groups = collections.defaultdict(list)
    for face in faces:
        groups[find(face[0])].append(tuple(sorted(vertices[i] for i in face)))
    return collections.Counter(tuple(sorted(v)) for v in groups.values())


def ray_height(box, e, n):
    # World coordinates (north, -east, up); intersect a segment above the props.
    start, end = (n, -e, 350), (n, -e, 165)
    a, b = A.local(start, box), A.local(end, box)
    lo, hi = 0., 1.
    for x, y, half in zip(a, b, box['half']):
        d = y-x
        if abs(d) < 1e-12:
            if abs(x) > half:
                return None
        else:
            t0, t1 = sorted(((-half-x)/d, (half-x)/d))
            lo, hi = max(lo, t0), min(hi, t1)
            if lo > hi:
                return None
    return 350-185*lo


def mesh(path):
    stats = A.mesh_audit(path)
    verts, uv, faces, normals = [], [], [], []
    for line in path.read_text().splitlines():
        s = line.split()
        if not s:
            continue
        if s[0] == 'v':
            verts.append(tuple(map(float, s[1:4])))
        elif s[0] == 'vt':
            uv.append(tuple(map(float, s[1:3])))
        elif s[0] == 'vn':
            normals.append(tuple(map(float, s[1:4])))
        elif s[0] == 'f':
            face = [tuple(map(int, t.split('/'))) for t in s[1:]]
            assert all(0 < t[1] <= len(uv) and 0 < t[2] <= len(normals) for t in face)
            faces.extend((face[0][0]-1, face[i][0]-1, face[i+1][0]-1) for i in range(1, len(face)-1))
    v, f = np.array(verts), np.array(faces)
    area2 = np.linalg.norm(np.cross(v[f[:, 1]]-v[f[:, 0]], v[f[:, 2]]-v[f[:, 0]]), axis=1)
    assert np.isfinite(uv).all() and np.min(area2) > 1e-8, 'Invalid UV or zero-area face'
    stats['minimumDoubleTriangleArea'] = float(np.min(area2))
    return stats


def main():
    A.CHUNKS = tuple(HALLS)
    old, new = A.read_boxes(BEFORE), A.read_boxes(STAGE)
    report = {'scope': 'Offline exported OBB, convex-element and mesh audit. No engine/controller, navigation, bullet or performance verification.', 'halls': {}}
    for name, (e, n, w, d) in HALLS.items():
        previous = [b for b in old if b['chunk'] == name]
        current = [b for b in new if b['chunk'] == name]
        assert len(current) == len(previous)+2
        removed = [b for b in previous if name == 'workshop' and
                   math.dist(b['origin'], (n-d/2, -e, 86)) < .001 and b['half'] == (4, 4, 86)]
        assert len(removed) == (1 if name == 'workshop' else 0)
        retained = [b for b in previous if b not in removed]
        appended = 3 if name == 'workshop' else 2
        assert [b['serialized'] for b in current[:-appended]] == [b['serialized'] for b in retained]
        if name == 'workshop':
            lintel = current[-3]
            assert math.dist(lintel['origin'], (n-d/2, -e, 162)) < .001
            assert lintel['half'] == (w/4, 5, 8)
            assert A.segment_box_distance((n-d/2, -e, 24), (n-d/2, -e, 48), lintel) > 24
        hulls = {}
        for material in ('metal', 'rubber'):
            file = f'{name}_hulls_{material}.obj'
            a, b = hull_elements(BEFORE/file), hull_elements(STAGE/file)
            assert not a-b, 'Existing hull modified or removed'
            added = sum((b-a).values())
            assert added == (2 if name == 'workshop' and material == 'metal' else 0)
            hulls[material] = dict(before=sum(a.values()), after=sum(b.values()), additions=added)
        samples, old_hits, errors = [], 0, []
        for de in np.linspace(-w*.35, w*.35, 9):
            for dn in np.linspace(-d*.4, d*.4, 7):
                old_hits += any(ray_height(b, e+de, n+dn) is not None for b in previous)
                hits = [h for b in current[-2:] if (h := ray_height(b, e+de, n+dn)) is not None]
                assert hits, 'Roof ray misses new physical slab'
                expected = 205-25*abs(dn)/(d/2)
                errors.append(abs(max(hits)-expected))
                samples.append([float(e+de), float(n+dn), float(max(hits))])
        assert max(errors) < .002
        # The new roof does not intrude into a standing 72-inch capsule at floor level.
        ground_clearance = min(A.segment_box_distance((n+dn, -(e+de), 24), (n+dn, -(e+de), 48), box)-24
                               for box in current[-2:] for de in (-w*.35, 0, w*.35) for dn in (-d*.4, 0, d*.4))
        assert ground_clearance > 90
        doorway = None
        if name == 'workshop':
            def obstruction_count(boxes):
                return sum(any(A.segment_box_distance((n-d/2+offset, -e, 24),
                                                      (n-d/2+offset, -e, 48), box) < 23.95
                               for box in boxes) for offset in range(-64, 65, 4))
            doorway = dict(samples=33, capsuleRadius=24, capsuleHeight=72,
                           beforeBlocked=obstruction_count(previous), afterBlocked=obstruction_count(current))
            assert doorway['beforeBlocked'] > 0 and doorway['afterBlocked'] == 0
        report['halls'][name] = dict(boxesBefore=len(previous), boxesAfter=len(current), retainedBoxesPreserved=True,
                                   removedGarageCenterPosts=len(removed), newLintels=1 if name == 'workshop' else 0,
                                   doorwayBoxSamples=doorway,
                                   hulls=hulls, roofSamples=len(samples), oldExplicitBoxRoofHits=int(old_hits),
                                   roofMaximumHeightError=max(errors), newRoofMinimumCapsuleClearance=ground_clearance,
                                   mesh=mesh(STAGE/f'{name}.obj'), samples=samples)
    hashes = json.loads((OUT/'sheds-before/model-hashes.json').read_text())
    report['unrelatedModelsUnchanged'] = {n: sha(MODELS/f'{n}.vmdl') == v for n, v in hashes.items() if n not in HALLS}
    report['sceneUnchanged'] = sha(ROOT/'Assets/scenes/maps/ForestBase/forestbase.scene') == sha(OUT/'sheds-before/Assets/scenes/maps/ForestBase/forestbase.scene')
    assert report['sceneUnchanged'] and all(report['unrelatedModelsUnchanged'].values())
    report['limitations'] = ['New solid roofs, workshop gables and the removal of the garage center post with a new lintel change physics. Native traversal, navigation, roof access and spawn visibility must be checked again.',
                             'Motor side panels were visual-only and are now removed; existing posts and their physical boxes remain.',
                             'Roof ray fixtures cover explicit boxes. They do not reproduce native import or collider fallback behavior.']
    report['sourceHashes'] = {str(p.relative_to(ROOT)): sha(p) for p in (ROOT/'Tools/forestbase_sheds.py', ROOT/'Tools/forestbase_map.py', ROOT/'Tools/forestbase_sheds_audit.py')}
    (STAGE/'geometry-audit.json').write_text(json.dumps(report, indent=2)+'\n')
    print(json.dumps({n: {k: v for k, v in r.items() if k not in ('samples',)} for n, r in report['halls'].items()}))


if __name__ == '__main__':
    main()
