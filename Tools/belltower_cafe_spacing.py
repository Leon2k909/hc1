"""Spread only the blue eastern cafe into three complete seating groups.

The red western cafe remains as authored. Existing geometry, UVs and furniture
orientations are retained; three groups translate and the fourth is removed.
"""
from collections import Counter
import math
import numpy as np
import map_kit as K
import belltower_detail as D

OLD_WEST = ((-600, -330), (-520, -250), (-600, -170), (-520, -90))
NEW_EAST = ((565, -340), (520, -200), (565, -60), None)


def original_groups(paint_map):
    result = []
    for k, centre in enumerate(OLD_WEST):
        model = K.Model(); rng = np.random.default_rng(70+k)
        top = D.bistro_table(model, centre)
        model.cylinder(centre, 13.8, 0, top, {}, sides=8, surface='metal')
        D.parasol(model, centre, 84, 104, 52, turn=rng.uniform(0, math.pi/4), pole_from=top)
        for angle in (.5, 2.6, 4.7):
            angle += rng.uniform(-.25, .25)
            e, n = centre[0]+24*math.cos(angle), centre[1]+24*math.sin(angle)
            D.bistro_chair(model, (e, n), math.degrees(angle)+180+rng.uniform(-12, 12))
        result.append(model.mirrored(paint_map))
    return result


def delta(k):
    target = NEW_EAST[k]
    return None if target is None else np.array((target[0]+OLD_WEST[k][0], target[1]-OLD_WEST[k][1], 0.))


def quantized(p):
    return tuple(int(round(float(v)*1000)) for v in p)


def apply_east(model, paint_map):
    """Keep the asymmetric spacing on a full map regeneration."""
    lookup = {}; expected = Counter(); hulls = {}
    for k, group in enumerate(original_groups(paint_map)):
        for paint, polygons in group.polygons.items():
            for points, _ in polygons:
                key = (paint, frozenset(quantized(p) for p in points))
                assert key not in lookup or lookup[key] == k
                lookup[key] = k; expected[key] += 1
        for points, surface in group.hulls:
            hulls[(surface, frozenset(quantized(p) for p in points))] = k
    found = Counter()
    for paint in {p for p, _ in lookup}:
        updated = []; new_uv = {}; new_normals = {}
        for i, (points, normal) in enumerate(model.polygons[paint]):
            key = (paint, frozenset(quantized(p) for p in points))
            k = lookup.get(key)
            if k is not None:
                found[key] += 1
                shift = delta(k)
                if shift is None: continue
                points = [p+shift for p in points]
            index = len(updated)
            if (paint, i) in model.polygon_uvs: new_uv[(paint, index)] = model.polygon_uvs[(paint, i)]
            if (paint, i) in model.polygon_normals: new_normals[(paint, index)] = model.polygon_normals[(paint, i)]
            updated.append((points, normal))
        model.polygons[paint] = updated
        model.polygon_uvs = {key: value for key, value in model.polygon_uvs.items() if key[0] != paint}
        model.polygon_uvs.update(new_uv)
        model.polygon_normals = {key: value for key, value in model.polygon_normals.items() if key[0] != paint}
        model.polygon_normals.update(new_normals)
    assert found == expected, 'Expected exactly the original four blue cafe groups.'
    updated = []; found_hulls = set()
    for points, surface in model.hulls:
        key = (surface, frozenset(quantized(p) for p in points))
        if key in hulls:
            found_hulls.add(key); shift = delta(hulls[key])
            if shift is None: continue
            points = [np.asarray(p)+shift for p in points]
        updated.append((points, surface))
    assert found_hulls == set(hulls)
    model.hulls = updated


def clearances():
    points = [np.array(p) for p in NEW_EAST if p is not None]
    gaps = [float(np.linalg.norm(a-b)-104) for i, a in enumerate(points) for b in points[i+1:]]
    assert min(gaps) > 40
    assert min(650-p[0]-52 for p in points) >= 30
    return {'tables_before': 4, 'tables_after': 3, 'chairs_before': 12, 'chairs_after': 9,
            'minimum_canopy_gap_inches': min(gaps), 'minimum_canopy_wall_gap_inches': float(min(650-p[0]-52 for p in points)),
            'table_centres_plan_inches': [list(p) for p in NEW_EAST if p is not None]}
