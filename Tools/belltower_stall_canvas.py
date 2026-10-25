"""Soft, tensioned market-stall canvas. Existing cloth materials and collision stay with the caller."""
import math
import zlib
import numpy as np

import building_textures as BT
import belltower_furniture as F


def build(model, p, w, d, paint):
    """Keep the four post attachment heights; let the spans and valance drape."""
    seed = zlib.crc32(np.round(p.o, 3).tobytes())
    phase = (seed % 997) / 997 * math.tau
    tile = BT.tile_units(paint)
    x0, x1, y0, y1 = -w-8, w+8, -d-8, d+14
    nx, ny = 24, 12
    xs = np.unique(np.r_[np.linspace(x0, x1, nx+1), -w, w])
    ys = np.unique(np.r_[np.linspace(y0, y1, ny+1), -d, d])

    def cloth(x, y):
        t = (y+d)/(2*d)
        clipped = np.clip(t, 0, 1)
        span = max(0., 1-(x/w)**2)
        # A hanging span, with a small belly and folds radiating from each pin.
        z = 106.2-14*t - span*(3.6+1.4*clipped)
        z -= 1.1*math.sin(math.pi*clipped)*max(0., 1-(x/(w+8))**4)
        for sx in (-1, 1):
            for sy in (-1, 1):
                r = math.hypot(x-sx*w, y-sy*d)
                z += .65*math.sin(r*.34)*math.exp(-r/20)
        # The small overhang folds down outside the supported corners.
        z -= .7*(max(0., abs(x)-w)/8)**2
        return np.array((x, y, z))

    def roof_normal(x, y):
        step = .02
        dx = cloth(x+step, y)-cloth(x-step, y)
        dy = cloth(x, y+step)-cloth(x, y-step)
        n = np.cross(dx, dy)
        return n/np.linalg.norm(n)

    def transform_normal(n):
        return p.x*n[0]+p.y*n[1]+p.z*n[2]

    def emit(points, normals, uv):
        world = [p.at(q) for q in points]
        wn = [transform_normal(n) for n in normals]
        F.face(model, paint, world, sum(wn), uv, wn)
        F.face(model, paint, world, -sum(wn), uv, [-n for n in wn])

    # UVs stay in the cloth's undeformed coordinates, continuous across every
    # cell. The existing eight-inch stripes follow the surface rather than
    # being reprojected separately onto each little face.
    uv_shift = (seed % 1024)/1024
    for a, b in zip(xs, xs[1:]):
        for c, e in zip(ys, ys[1:]):
            pairs = ((a, c), (b, c), (b, e), (a, e))
            emit([cloth(x, y) for x, y in pairs], [roof_normal(x, y) for x, y in pairs],
                 [((x-x0)/tile+uv_shift, (y-y0)/tile) for x, y in pairs])

    def flap(x, v):
        top = cloth(x, y1)
        blend = math.sin(math.pi*(x-x0)/(x1-x0))
        length = 10 + .85*math.sin(x*.095+phase)*blend
        # Small, irregular folds and a curled hem; no repeated deep scallops.
        billow = (.65*math.sin(x*.12+phase)+.35*math.sin(x*.21))*v*blend
        return top + np.array((0, .8*math.sin(v*math.pi/2)+billow,
                              -length*v+.35*math.sin(math.pi*v)))

    def flap_normal(x, v):
        dx = flap(x+.02, v)-flap(x-.02, v)
        dv = flap(x, v+.002)-flap(x, v-.002)
        n = np.cross(dx, dv)
        return n/np.linalg.norm(n)

    for a, b in zip(xs, xs[1:]):
        for c, e in zip((0., .25, .7, .9), (.25, .7, .9, 1.)):
            pairs = ((a, c), (b, c), (b, e), (a, e))
            emit([flap(x, v) for x, v in pairs], [flap_normal(x, v) for x, v in pairs],
                 [((x-x0)/tile+uv_shift, (y1-y0+10*v)/tile) for x, v in pairs])
