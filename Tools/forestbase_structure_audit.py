"""Offline checks of exported bridge boxes, independent of the map builder.

This is a sampled geometry audit, not an engine/controller/navmesh test.
"""
import hashlib
import json
import math
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'output/forestbase'
MODELS = ROOT / 'Assets/models/maps/forestbase'
CHUNKS = ('barracks', 'command', 'links')
ROUTES = (
    ('west-link', (-530, 850), (-125, 920)),
    ('east-link', (655, 920), (1070, 920)),
    ('elbow', (1070, 920), (1070, 1020)),
    ('landing', (1070, 1020), (1265, 1040)),
    ('stair-landing', (1265, 1040), (1485, 1040)),
)


def rotation(angles):
    p, y, r = (math.radians(v) / 2 for v in angles)
    sp, cp, sy, cy, sr, cr = math.sin(p), math.cos(p), math.sin(y), math.cos(y), math.sin(r), math.cos(r)
    x, y, z, w = (sr*cp*cy-cr*sp*sy, cr*sp*cy+sr*cp*sy,
                  cr*cp*sy-sr*sp*cy, cr*cp*cy+sr*sp*sy)
    return ((1-2*(y*y+z*z), 2*(x*y-z*w), 2*(x*z+y*w)),
            (2*(x*y+z*w), 1-2*(x*x+z*z), 2*(y*z-x*w)),
            (2*(x*z-y*w), 2*(y*z+x*w), 1-2*(x*x+y*y)))


def read_boxes(folder):
    boxes = []
    for chunk in CHUNKS:
        text = (folder / f'{chunk}.vmdl').read_text()
        for i, match in enumerate(re.finditer(r'_class = "PhysicsShapeBox"([^}]+)}', text)):
            def vector(key):
                return tuple(float(v) for v in re.search(key+r' = \[([^]]+)]', match[1])[1].split(','))
            boxes.append(dict(chunk=chunk, index=i, origin=vector('origin'),
                              half=tuple(v/2 for v in vector('dimensions')),
                              rotation=rotation(vector('angles')), serialized=match[0]))
    return boxes


def local(point, box):
    return tuple(sum(row[i]*(point[j]-box['origin'][j])
                     for j, row in enumerate(box['rotation'])) for i in range(3))


def segment_box_distance(start, end, box):
    a, b = local(start, box), local(end, box)
    d = tuple(v-u for u, v in zip(a, b))
    cuts = [0., 1.]
    for i in range(3):
        if abs(d[i]) > 1e-10:
            cuts += [t for s in (-1, 1) if 0 < (t := (s*box['half'][i]-a[i])/d[i]) < 1]
    cuts.sort()
    def distance(t):
        return sum(max(abs(a[i]+d[i]*t)-box['half'][i], 0)**2 for i in range(3))
    best = float('inf')
    for lo, hi in zip(cuts, cuts[1:]):
        midpoint = (lo+hi)/2
        aa = bb = 0.
        for i in range(3):
            v = a[i]+d[i]*midpoint
            if abs(v) > box['half'][i]:
                offset = a[i]-math.copysign(box['half'][i], v)
                aa += d[i]**2
                bb += offset*d[i]
        t = max(lo, min(hi, -bb/aa)) if aa else lo
        best = min(best, distance(lo), distance(hi), distance(t))
    return math.sqrt(best)


def covered(point, boxes):
    return any(all(abs(v) <= h+.002 for v, h in zip(local(point, b), b['half'])) for b in boxes)


def audit_routes(boxes):
    reports = []
    for name, start, end in ROUTES:
        count = math.ceil(math.dist(start, end)/4)
        blocked, center_gaps, perimeter_gaps = [], [], []
        for k in range(count+1):
            e, n = (a+(b-a)*k/count for a, b in zip(start, end))
            # World axes are (north, -east, up). A 72-inch capsule has its
            # sphere centers 24 and 48 inches above the walking surface.
            hits = [f"{b['chunk']}:{b['index']}" for b in boxes
                    if segment_box_distance((n, -e, 264), (n, -e, 288), b) < 23.95]
            if hits:
                blocked.append(dict(plan=[e, n], boxes=hits))
            if not covered((n, -e, 239.5), boxes):
                center_gaps.append([e, n])
            missing = []
            for ring in range(16):
                angle = ring*math.tau/16
                foot = (n+24*math.sin(angle), -e-24*math.cos(angle), 239.5)
                if not covered(foot, boxes):
                    missing.append(ring)
            if missing:
                perimeter_gaps.append(dict(plan=[e, n], ringSamples=missing))
        reports.append(dict(route=name, samples=count+1, blocked=blocked,
                            unsupportedCenters=center_gaps, partialFootprintSupport=perimeter_gaps))
    return reports


def mesh_audit(file):
    vertices, normals, triangles, materials = [], [], 0, set()
    for line in file.read_text().splitlines():
        fields = line.split()
        if not fields:
            continue
        if fields[0] in ('v', 'vn'):
            vector = tuple(map(float, fields[1:4]))
            assert len(vector) == 3 and all(math.isfinite(v) for v in vector), line
            (vertices if fields[0] == 'v' else normals).append(vector)
        elif fields[0] == 'f':
            assert len(fields) >= 4
            assert all(0 < int(v.split('/')[0]) <= len(vertices) for v in fields[1:])
            triangles += len(fields)-3
        elif fields[0] == 'usemtl':
            materials.add(fields[1])
    assert vertices and normals and triangles
    assert all(abs(math.sqrt(sum(v*v for v in normal))-1) < .005 for normal in normals)
    return dict(vertices=len(vertices), normals=len(normals), triangles=triangles, materials=sorted(materials))


def sha(file):
    return hashlib.sha256(file.read_bytes()).hexdigest()


def main():
    # Analytic fixtures cover separation, overlap, tangency and a rotated box.
    box = dict(origin=(0, 0, 0), half=(1, 2, 3), rotation=rotation((0, 0, 0)))
    assert segment_box_distance((5, 0, -10), (5, 0, 10), box) == 4
    assert segment_box_distance((0, 0, -10), (0, 0, 10), box) == 0
    box['rotation'] = rotation((0, 90, 0))
    assert abs(segment_box_distance((5, 0, -10), (5, 0, 10), box)-3) < 1e-8
    before = read_boxes(OUT/'structures-before')
    after = read_boxes(MODELS)
    snapshot = OUT/'rail-truss-before'
    old_links = re.findall(r'_class = "PhysicsShapeBox"[^}]+}', (snapshot/'links.vmdl').read_text())
    new_links = [b['serialized'] for b in after if b['chunk'] == 'links']
    unchanged = old_links == new_links
    hashes = json.loads((snapshot/'model-hashes.json').read_text())
    other_models = {c: sha(MODELS/f'{c}.vmdl') == digest for c, digest in hashes.items() if c != 'links'}
    current = audit_routes(after)
    report = dict(scope='Offline sampled exported-box and OBJ checks; no native engine, navmesh, bullets or performance claim.',
                  capsule=dict(radius=24, height=72, feet=240, stepMaximum=4, collisionTolerance=.05),
                  allOtherModelSourcesUnchanged=other_models, railTrussPhysicsUnchanged=unchanged,
                  beforeJunctionRepair=audit_routes(before), current=current,
                  mesh=mesh_audit(MODELS/'links.obj'),
                  sourceHashes={str(p.relative_to(ROOT)): sha(p) for p in
                                (ROOT/'Tools/forestbase_structures.py', MODELS/'links.obj', MODELS/'links.vmdl')},
                  limitations=['Four circular perimeter support samples near diagonal bridge abutments are outside the deck union; center support is checked separately.',
                               'Historical native navigation/spawn tests predate the earlier bridge junction collision repair. Fresh native verification remains required.'])
    (OUT/'structural-route-audit.json').write_text(json.dumps(report, indent=2)+'\n')
    assert unchanged and all(other_models.values()), 'Unexpected physics or unrelated model source change'
    assert all(not r['blocked'] and not r['unsupportedCenters'] for r in current), 'Blocked or unsupported center route'
    print(json.dumps(dict(samples=sum(r['samples'] for r in current), blocked=0, unsupportedCenters=0,
                          partialFootprintSamples=sum(len(r['partialFootprintSupport']) for r in current),
                          physicsUnchanged=unchanged, mesh=report['mesh'])))


if __name__ == '__main__':
    main()
