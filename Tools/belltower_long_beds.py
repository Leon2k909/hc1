"""Low, worn limestone flower beds beside Belltower's gazebos.

The caller retains the original 120 x 36 x 14 collision. Individual masonry
courses, mitred coping and recessed soil supply the visible construction.
"""
import math
import numpy as np
from scipy.spatial import ConvexHull

import belltower_planters as P
import belltower_furniture as F
from map_kit import normalise

CENTRES = ((-650., -1160.), (-350., -1160.))
STONE = P.STONE
SOIL = P.SOIL


def soil_height(x, y):
    return 11.35 + .24 * math.sin(x * .17) * math.cos(y * .21) + .12 * math.cos(x * .41 + y * .19)


def build(model, centre, z=-48., seed=0):
    model.material_overrides.update({STONE: f'{P.RESOURCE}/cut_stone.vmat', SOIL: f'{P.RESOURCE}/compost.vmat'})
    model.tile_overrides.update({STONE: P.TILE, SOIL: 64.})
    centre = np.array((*centre, z), float)
    rng = np.random.default_rng(int(seed) + 86513)
    start = model.triangle_count()
    model.box(centre + (-55.8, -13.8, .12), centre + (55.8, 13.8, 10.8), SOIL)
    # Stagger the joints between courses. Each corner is mitred through its
    # thickness, so no two blocks occupy the same corner volume.
    for course, (out_x, out_y, in_x, in_y, low, high) in enumerate((
        (59.1, 17.2, 55.5, 13.4, .18, 6.15),
        (59.5, 17.6, 55.5, 13.4, 6.33, 11.90),
        (60., 18., 55., 13., 12.05, 14.),
    )):
        for side in range(4):
            angle = side * math.pi / 2
            along = np.array((math.cos(angle), math.sin(angle), 0.))
            outward = np.array((-math.sin(angle), math.cos(angle), 0.))
            axes = np.array((along, outward, (0., 0., 1.)))
            half = out_x if side % 2 == 0 else out_y
            inner_half = in_x if side % 2 == 0 else in_y
            outer = out_y if side % 2 == 0 else out_x
            inner = in_y if side % 2 == 0 else in_x
            count = 6 if side % 2 == 0 else 2
            cuts = np.linspace(-half, half, count + 1)
            if course == 1 and count == 6:
                cuts = np.concatenate(([-half], np.arange(-half + 10, half - 5, 20), [half]))
            cuts[1:-1] += rng.uniform(-.55, .55, len(cuts) - 2)
            for i, (a, b) in enumerate(zip(cuts, cuts[1:])):
                a_inner = -inner_half if i == 0 else a
                b_inner = inner_half if i == len(cuts) - 2 else b
                gap = .10
                footprint = [(a + gap, outer), (b - gap, outer),
                    (b_inner - gap, inner), (a_inner + gap, inner)]
                footprint.reverse()
                footprint = np.asarray(footprint)
                offset = footprint.mean(axis=0)
                top = high - rng.uniform(0., .055)
                block_centre = centre + offset[0] * along + offset[1] * outward + (0., 0., (low + top) / 2)
                P.chipped_stone(model, block_centre, axes,
                    footprint - offset, top - low, rng, coping=course == 2)
    # Uneven soil sits below the coping rather than covering its whole top.
    xs, ys = np.linspace(-55.6, 55.6, 25), np.linspace(-13.5, 13.5, 7)
    def at(x, y):
        return centre + (x, y, soil_height(x, y))
    def normal(x, y):
        step = .01
        dx = (soil_height(x + step, y) - soil_height(x - step, y)) / (2 * step)
        dy = (soil_height(x, y + step) - soil_height(x, y - step)) / (2 * step)
        return normalise((-dx, -dy, 1.))
    for x0, x1 in zip(xs, xs[1:]):
        for y0, y1 in zip(ys, ys[1:]):
            for xy in (((x0, y0), (x1, y0), (x1, y1)), ((x0, y0), (x1, y1), (x0, y1))):
                F.face(model, SOIL, [at(x, y) for x, y in xy], (0., 0., 1.),
                    [(x / 64 + .273, y / 64 + .419) for x, y in xy], [normal(x, y) for x, y in xy])
    for i in range(20):
        x, y = rng.uniform(-54, 54), rng.uniform(-12, 12)
        radius = rng.uniform(.18, .42)
        points = rng.normal(size=(9, 3))
        points /= np.linalg.norm(points, axis=1, keepdims=True)
        points *= (radius, radius * .8, radius * .45)
        hull = ConvexHull(points)
        origin = at(x, y) + (0., 0., radius * .1)
        for triangle, equation in zip(hull.simplices, hull.equations):
            F.face(model, SOIL, [origin + p for p in points[triangle]], equation[:3])
    return model.triangle_count() - start
