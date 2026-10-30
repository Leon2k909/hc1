"""Trim duplicate accelerator-shell faces against the laboratory shell.

The structure owns the playable concrete walls. The accelerator back wall owns
its two external corner returns. Only render polygons are trimmed; collision,
material bindings and the original UV interpolation remain unchanged.
"""
import numpy as np
import map_kit as K
from collider_craft import clip


def cut_regions(points):
    points = np.asarray(points)
    lo, hi = points.min(0), points.max(0)
    regions = []
    if hi[0]-lo[0] < .001:
        if abs(abs(lo[0])-1900.) < .001:
            regions.append((1, 674., 980., 2, 0., 900.))
        if abs(abs(lo[0])-1920.) < .001:
            regions.append((1, 1880., 1900., 2, 0., 1040.))
    if hi[1]-lo[1] < .001 and abs(lo[1]-1900.) < .001:
        regions.append((0, -1920., 1920., 2, 0., 1040.))
    if hi[2]-lo[2] < .001 and (abs(lo[2]) < .001 or abs(lo[2]-1040.) < .001):
        for e0, e1 in ((-1920., -1900.), (1900., 1920.)):
            if abs(lo[2]) < .001:
                regions.append((0, e0, e1, 1, 674., 1004.))
            regions.append((0, e0, e1, 1, 1880., 1900.))
    return regions


def area(poly):
    if len(poly) < 3:
        return 0.
    return sum(np.linalg.norm(np.cross(poly[i][:3]-poly[0][:3],
        poly[i+1][:3]-poly[0][:3]))*.5 for i in range(1, len(poly)-1))


def trim(poly):
    """Subtract owned coplanar regions, interpolating any trailing attributes."""
    pieces = [poly]
    changed = False
    for axis, low, high, other, bottom, top in cut_regions([p[:3] for p in poly]):
        next_pieces = []
        for polygon in pieces:
            bounds = np.asarray(polygon)
            if (bounds[:,axis].max() <= low or bounds[:,axis].min() >= high or
                    bounds[:,other].max() <= bottom or bounds[:,other].min() >= top):
                next_pieces.append(polygon)
                continue
            inside, outside = polygon, []
            for a, value, positive in ((axis,low,True), (axis,high,False),
                    (other,bottom,True), (other,top,False)):
                fragment = clip(inside, a, value, not positive)
                if fragment and area(fragment) > 1e-7:
                    outside.append(fragment)
                inside = clip(inside, a, value, positive)
                if not inside:
                    break
            if inside and area(inside) > 1e-7:
                changed = True
                next_pieces.extend(outside)
            else:
                next_pieces.append(polygon)
        pieces = next_pieces
    return pieces, changed


def refine_machine(model):
    replacement = K.Model()
    for paint, polygons in model.polygons.items():
        for index, (points, normal) in enumerate(polygons):
            uv = model.polygon_uvs.get((paint,index))
            normals = model.polygon_normals.get((paint,index))
            if paint == 'co_concrete':
                rows = [np.asarray(p) if uv is None else np.concatenate((p,t))
                    for p,t in zip(points, uv if uv is not None else [None]*len(points))]
                pieces, changed = trim(rows)
                if changed:
                    assert normals is None, 'Only flat concrete shell faces may be trimmed'
                    for polygon in pieces:
                        replacement.polygon(paint, [v[:3] for v in polygon], normal,
                            uv=None if uv is None else [v[3:] for v in polygon])
                    continue
            replacement.polygon(paint, points, normal, uv=uv, normals=normals)
    model.polygons = replacement.polygons
    model.polygon_uvs = replacement.polygon_uvs
    model.polygon_normals = replacement.polygon_normals

