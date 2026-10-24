"""Remove only the town wall surfaces buried inside the playable ground.

Exterior retaining faces and every collision primitive are retained. All lengths
are plan inches. Two inches of overlap below the floor prevent grazing gaps.
"""
import numpy as np


def ground_volumes(overlap=2):
    # Boundary faces exposed to the hillside are preserved in visible_pieces.
    # Subtract right up to them so no thin buried strips remain on other faces.
    west, south, north = -2380, -1466, 1800
    bounds = [((1, 0, 0), west), ((-1, 0, 0), 0)]
    return (
        bounds + [((0, 1, 0), south), ((0, -1, 0), 1000), ((0, 0, -1), 48+overlap)],
        bounds + [((0, 1, 0), -1000), ((0, -1, 0), -north), ((0, 0, -1), overlap)],
        # The spawn road rises 48 inches over its 200-inch ramp.
        bounds + [((-1, 0, 0), 1850), ((0, 1, 0), -1200),
                  ((0, -1, 0), 1000), ((0, .24, -1), -240+overlap)],
    )


def split_polygon(points, axis, offset):
    """Return the portions inside and outside dot(axis,p)>=offset."""
    points = [np.asarray(p, float) for p in points]
    values = [float(np.dot(axis, p)-offset) for p in points]
    if all(v >= -1e-7 for v in values):
        return points, []
    if all(v <= 1e-7 for v in values):
        return [], points
    inside, outside = [], []
    for i, a in enumerate(points):
        b, va, vb = points[(i+1) % len(points)], values[i], values[(i+1) % len(points)]
        (inside if va >= 0 else outside).append(a)
        if (va < 0) != (vb < 0):
            crossing = a + (b-a) * va/(va-vb)
            inside.append(crossing)
            outside.append(crossing)
    return inside, outside


def polygon_area(points):
    if len(points) < 3:
        return 0.
    return sum(np.linalg.norm(np.cross(points[k]-points[0], points[k+1]-points[0]))*.5
               for k in range(1, len(points)-1))


def visible_pieces(points):
    original = [np.asarray(p, float) for p in points]
    # The outward boundary itself is exposed to the hillside. Horizontal and
    # perpendicular faces may still be removed right up to that boundary.
    if np.allclose([p[0] for p in original], -2380) or np.allclose([p[1] for p in original], -1466):
        return [original]
    normal = np.cross(original[1]-original[0], original[2]-original[0])
    if np.allclose([p[1] for p in original], 1800) and normal[1] > 0:
        return [original]  # exposed north-row foundation, facing away from town
    # This boundary faces the flat garden, not the rising road on its other
    # side. Subtracting the ramp here leaves a triangular hole above the grass.
    garden_ramp_face = np.allclose([p[0] for p in original], -1850, rtol=0, atol=1e-7) and normal[0] > 0
    def floor_at(p):
        e, n, _ = p
        if e <= -1850 and n < -1000 and not garden_ramp_face:
            return float(np.clip(.24*n+240, -48, 0))
        return -48 if n < -1000 else 0
    if normal[2] > 0 and all(abs(p[2]-floor_at(p)) < 1e-7 for p in original):
        return [original]  # the blocked gate's visible stone threshold
    # A face wholly under the floor needs no seam overlap of its own.
    overlap = 0 if all(p[2] <= floor_at(p)+1e-7 for p in original) else 2
    pieces = [original]
    for volume_index, planes in enumerate(ground_volumes(overlap)):
        if volume_index == 2 and garden_ramp_face:
            continue
        remaining = []
        for polygon in pieces:
            inside = polygon
            for axis, offset in planes:
                if not inside:
                    break
                inside, outside = split_polygon(inside, axis, offset)
                if polygon_area(outside) > .001:
                    remaining.append(outside)
        pieces = remaining
    if abs(sum(polygon_area(p) for p in pieces)-polygon_area(original)) < .001:
        return [original]
    return pieces


def trim_model(model, first_faces):
    for paint in ('rubble', 'ashlar', 'ashlar_grey'):
        start = first_faces.get(paint, 0)
        originals = model.polygons[paint][start:]
        retained = model.polygons[paint][:start]
        uv_attributes = {key: model.polygon_uvs.pop(key) for key in list(model.polygon_uvs)
                         if key[0] == paint and key[1] >= start}
        normal_attributes = {key: model.polygon_normals.pop(key) for key in list(model.polygon_normals)
                             if key[0] == paint and key[1] >= start}
        for index, (points, normal) in enumerate(originals, start):
            pieces = visible_pieces(points)
            old_key = (paint, index)
            uv = uv_attributes.get(old_key)
            normals = normal_attributes.get(old_key)
            unchanged = len(pieces) == 1 and len(pieces[0]) == len(points) and np.allclose(pieces[0], points)
            if not unchanged and (uv is not None or normals is not None):
                raise ValueError('Buried wall cleanup encountered authored UVs or smooth normals')
            for piece in pieces:
                new_key = (paint, len(retained))
                if uv is not None:
                    model.polygon_uvs[new_key] = uv
                if normals is not None:
                    model.polygon_normals[new_key] = normals
                retained.append((piece, normal))
        model.polygons[paint] = retained
