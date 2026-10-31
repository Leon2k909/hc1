"""The capture flag kit's pack_real_scale, with each island's size taken from weights on its faces."""
import math

import bmesh
import numpy as np


def pack_weighted(mesh, weight_of, res=2048, pad_px=4):
    bm = bmesh.new()
    bm.from_mesh(mesh)
    layer = bm.loops.layers.uv.active
    facts = bm.loops.layers.float_color["facts"]
    bm.faces.ensure_lookup_table()
    bm.normal_update()
    seen = set()
    islands = []
    for seed in bm.faces:
        if seed.index in seen:
            continue
        seen.add(seed.index)
        stack, faces = [seed], []
        while stack:
            f = stack.pop()
            faces.append(f)
            for l in f.loops:
                a, b = l[layer].uv, l.link_loop_next[layer].uv
                for other in l.link_loops:
                    g = other.face
                    if g.index in seen:
                        continue
                    c, d = other[layer].uv, other.link_loop_next[layer].uv
                    if ((a - d).length < 1e-5 and (b - c).length < 1e-5) or ((a - c).length < 1e-5 and (b - d).length < 1e-5):
                        seen.add(g.index)
                        stack.append(g)
        islands.append(faces)

    rects = []
    for n, faces in enumerate(islands):
        area3 = sum(f.calc_area() * weight_of(f, facts) ** 2 for f in faces)
        pts = np.array([tuple(l[layer].uv) for f in faces for l in f.loops])
        tris = np.array([[tuple(l[layer].uv) for l in f.loops] for f in faces])
        areauv = 0.5 * np.abs((tris[:, 1, 0] - tris[:, 0, 0]) * (tris[:, 2, 1] - tris[:, 0, 1]) - (tris[:, 2, 0] - tris[:, 0, 0]) * (tris[:, 1, 1] - tris[:, 0, 1])).sum()
        scale = math.sqrt(area3 / max(areauv, 1e-12))
        centre = pts.mean(0)
        inches = (pts - centre) * scale
        best = None
        for deg in np.linspace(0, 90, 19):
            r = math.radians(deg)
            rot = np.array(((math.cos(r), -math.sin(r)), (math.sin(r), math.cos(r))))
            q = inches @ rot.T
            w, h = np.ptp(q, axis=0)
            if best is None or w * h < best[0]:
                best = (w * h, rot, w, h)
        _, rot, w, h = best
        q = inches @ rot.T
        low = q.min(0)
        if h > w:
            rot = np.array(((0.0, 1.0), (-1.0, 0.0))) @ rot
            q = inches @ rot.T
            low = q.min(0)
            w, h = h, w
        rects.append((w, h, n, centre, scale, rot, low))

    def attempt(px_per_in):
        pad = pad_px / px_per_in
        limit = res / px_per_in
        x = y = pad
        row = 0.0
        places = {}
        for w, h, n, *_ in sorted(rects, key=lambda r: (-round(r[1], 1), -r[0])):
            if x + w + pad > limit:
                x = pad
                y += row + pad
                row = 0.0
            if y + h + pad > limit:
                return None
            places[n] = (x, y)
            x += w + pad
            row = max(row, h)
        return places

    lo, hi = 2.0, 200.0
    places = None
    for _ in range(30):
        mid = (lo + hi) / 2
        got = attempt(mid)
        if got:
            places, lo = got, mid
        else:
            hi = mid
    density = lo
    for w, h, n, centre, scale, rot, low in rects:
        px, py = places[n]
        for f in islands[n]:
            for l in f.loops:
                q = (np.array(tuple(l[layer].uv)) - centre) * scale @ rot.T - low
                l[layer].uv = ((q[0] + px) * density / res, (q[1] + py) * density / res)
    bm.to_mesh(mesh)
    bm.free()
    print("islands", len(rects), "px/in at weight 1: %.1f" % density, flush=True)
    return density
