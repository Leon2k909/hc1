"""Closed, gently graded mainland for the photographic Veridant horizon.

The grid contains every coastline bend and play-boundary coordinate. Each cell
therefore clips against a single straight coast segment; there are no open
angular cuts, folded quads, or grass textures projected down a vertical cliff.
"""
import math
import numpy as np
from riverdale_parts import card, unit, v, UP
GROUND_RADIUS = 60000.0


def coast_data():
    from veridant_backdrop import COAST
    coast = np.array(COAST, dtype=float)
    # Match the actual outer face of the retained 40-inch-thick sea wall.
    coast[np.isclose(np.abs(coast[:, 1]), 2600), 0] = -1790
    north = np.unique(np.r_[coast[:, 1], np.arange(-8000, 8001, 400)])
    east = np.interp(north, coast[:, 1], coast[:, 0])
    fade = np.clip((np.abs(north) - 2600) / 600, 0, 1)
    fade = fade * fade * (3 - 2 * fade)
    east += fade * (40 * np.sin(north / 650) + 15 * np.sin(north / 230))
    return np.c_[east, north]


def clip_polygon(points, distance):
    out = []
    for a, b in zip(points[-1:] + points[:-1], points):
        da, db = distance(a), distance(b)
        if (da >= 0) != (db >= 0):
            out.append(a + (b - a) * (da / (da - db)))
        if db >= 0:
            out.append(b)
    result = []
    for point in out:
        if not result or np.linalg.norm(point - result[-1]) > 1e-6:
            result.append(point)
    if len(result) > 1 and np.linalg.norm(result[0] - result[-1]) < 1e-6:
        result.pop()
    return result


def build(model, *, radius, brush):
    from veridant_backdrop import PLAY_RECT, SEA_Z
    centre = np.array([75.0, -100.0])
    coast = coast_data()
    ce = lambda n: float(np.interp(n, coast[:, 1], coast[:, 0]))
    distance = lambda p: float(p[0] - ce(p[1]))
    x0, x1, y0, y1 = PLAY_RECT
    # Continue the continent beyond the picture. Elevated views must not see
    # the sea plane through low portions of an inland photographic skyline.
    reach = GROUND_RADIUS + 80
    edge_count = 144
    normals = np.array([(math.cos(a), math.sin(a)) for a in
                        (np.arange(edge_count) + .5) * 2 * math.pi / edge_count])
    apothem = reach * math.cos(math.pi / edge_count)

    def smooth(t):
        t = float(np.clip(t, 0, 1))
        return t * t * (3 - 2 * t)

    def height(point):
        d_rect = math.hypot(max(x0 - point[0], 0, point[0] - x1),
                            max(y0 - point[1], 0, point[1] - y1))
        e, n = point
        ridges = (85*math.sin(e/900+n/600) + 65*math.sin(e/450-n/1250)
                  + 30*math.cos(n/300)*math.sin(e/400)) * smooth(d_rect/500)
        base = max(15,min(1100,100+.075*d_rect)+ridges)
        shore_top = (90+25*math.sin(n/750))*smooth((abs(n)-2600)/4000)
        shore_width = 500+2000*smooth(d_rect/7000)
        value = shore_top+(base-shore_top)*smooth((distance(point)-60)/shore_width)
        return value*smooth(d_rect/450)

    def surface_normal(point):
        e, n = point
        return unit(v(height(np.array([e-10,n]))-height(np.array([e+10,n])),
                      height(np.array([e,n-10]))-height(np.array([e,n+10])),20))

    def axis(c, lo, hi, fine_lo, fine_hi, extras):
        coarse = np.arange(math.floor((c-reach)/4000)*4000,
                           math.ceil((c+reach)/4000)*4000+1,4000)
        return np.unique(np.r_[coarse,np.arange(-14400,14401,800),np.arange(-4800,4801,400),
                               np.arange(fine_lo,fine_hi+1,200),lo,hi,extras])

    east = axis(centre[0], x0, x1, -2400, 2800, [])
    north = axis(centre[1], y0, y1, -2200, 2200,
                 coast[(coast[:, 1] > centre[1] - reach) & (coast[:, 1] < centre[1] + reach), 1])
    def sampled_height(point):
        # Match the exported planar triangles, rather than the analytic surface,
        # so every cutout is seated in the mesh even on a coarse rolling cell.
        ei = np.clip(np.searchsorted(east,point[0])-1,0,len(east)-2)
        ni = np.clip(np.searchsorted(north,point[1])-1,0,len(north)-2)
        e0,e1 = east[ei:ei+2]; n0,n1 = north[ni:ni+2]
        u,t = (point-np.array([e0,n0]))/np.array([e1-e0,n1-n0])
        z00,z10,z11,z01 = [height(np.array(p)) for p in ((e0,n0),(e1,n0),(e1,n1),(e0,n1))]
        return z00+(z10-z00)*u+(z11-z10)*t if u>=t else z00+(z11-z01)*u+(z01-z00)*t
    coast_lengths = np.r_[0, np.cumsum(np.linalg.norm(np.diff(coast, axis=0), axis=1))]
    coast_s = lambda n: float(np.interp(n, coast[:, 1], coast_lengths))

    def wall(a, b, toward, outer=False):
        lower_a, lower_b = a.copy(), b.copy()
        lower_a[2] = lower_b[2] = SEA_Z - 40
        along = unit(b[:2] - a[:2])
        coords = [((float(np.dot(p[:2], along)) if outer else coast_s(p[1])) / 256, p[2] / 256)
                  for p in (a, lower_a, lower_b, b)]
        card(model, 'vr_cliff_far', [a, lower_a, lower_b, b], toward, uv=coords)

    for e0, e1 in zip(east[:-1], east[1:]):
        for n0, n1 in zip(north[:-1], north[1:]):
            mid = np.array([(e0 + e1) / 2, (n0 + n1) / 2])
            if x0 < mid[0] < x1 and y0 < mid[1] < y1:
                continue
            closest = np.array([np.clip(centre[0], e0, e1), np.clip(centre[1], n0, n1)])
            if np.linalg.norm(closest - centre) > reach:
                continue
            square = [np.array(p, float) for p in ((e0,n0), (e1,n0), (e1,n1), (e0,n1))]
            elevations = [height(p) for p in square]
            # Clip planar triangles before interpolating heights. Sampling a
            # curved height after clipping bends skinny coastal fans vertically.
            for indices in ((0,1,2), (0,2,3)):
                original = [square[k] for k in indices]
                original_z = np.array([elevations[k] for k in indices])
                matrix = np.column_stack((original[1]-original[0], original[2]-original[0]))
                inverse = np.linalg.inv(matrix)
                points = clip_polygon(original, distance)
                if len(points) < 3:
                    continue
                if any(np.linalg.norm(p - centre) > apothem for p in points):
                    for normal in normals:
                        points = clip_polygon(points, lambda p: apothem - np.dot(p - centre, normal))
                        if len(points) < 3:
                            break
                if len(points) < 3:
                    continue
                top = []
                for point in points:
                    weights = inverse @ (point-original[0])
                    z = original_z[0] + weights[0]*(original_z[1]-original_z[0]) + weights[1]*(original_z[2]-original_z[0])
                    top.append(v(point[0], point[1], z))
                card(model, 'vr_inland_scrub', top, UP,
                     uv=[(p[0]/256,p[1]/256) for p in top], normals=[surface_normal(p[:2]) for p in top])
                for a, b in zip(top, top[1:] + top[:1]):
                    midpoint = (a + b) / 2
                    if abs(distance(a)) < .01 and abs(distance(b)) < .01:
                        if abs(midpoint[1]) <= 2600.001:
                            continue
                        wall(a, b, v(-1, 0, 0))
                    elif min(max(abs(np.dot(p[:2] - centre, normal) - apothem) for p in (a,b))
                             for normal in normals) < .01:
                        wall(a, b, unit(v(*(midpoint[:2] - centre), 0)), outer=True)
    # A small fixed set of crossed shrub cards breaks the near slope's silhouette.
    # These are geometry in the existing model, with no entities or collision.
    rng = np.random.default_rng(241024)
    count = 0
    for _ in range(2400):
        point = np.array([rng.uniform(-4500,5500),rng.uniform(-5200,4800)])
        d_rect = math.hypot(max(x0-point[0],0,point[0]-x1),max(y0-point[1],0,point[1]-y1))
        if not 180 < d_rect < 2500 or distance(point) < 220:
            continue
        h = rng.uniform(35,95)
        left,top,right,bottom = brush['rectangles'][int(rng.integers(len(brush['rectangles'])))]
        width = h*(right-left)/(bottom-top)
        at = v(*point,sampled_height(point)-8)
        texture_width,texture_height = brush['size']
        uv=[(left/texture_width,1-bottom/texture_height),(right/texture_width,1-bottom/texture_height),
            (right/texture_width,1-top/texture_height),(left/texture_width,1-top/texture_height)]
        for angle in (rng.uniform(0,math.pi),rng.uniform(0,math.pi)+math.pi/2):
            side=v(math.cos(angle),math.sin(angle),0)*width*.5
            model.polygon('vr_inland_brush',[at-side,at+side,at+side+UP*h,at-side+UP*h],
                          normal=unit(np.cross(side,UP)),uv=uv)
        count += 1
        if count == 180:
            break
    for paint in ('vr_inland_scrub','vr_cliff_far','vr_inland_brush'):
        model.material_overrides[paint] = f'materials/veridant/{paint}.vmat'
        model.tile_overrides[paint] = 256.0
