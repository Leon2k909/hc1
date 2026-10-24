"""Six worn Market Street crates, stored beside their stalls rather than the alley.

This replaces just the mirrored group formerly anchored at (-1370,1180).
All other shipping crates continue to use belltower_crates unchanged.
"""
import math
import types
import numpy as np
import belltower_crates as C
import belltower_furniture as F

OLD_ANCHOR = (-1370., 1180.)
NEW_ANCHOR = (-1514., 1127.)
OLD_ROWS = (
    ((-1370.4945685272105, 1182.8048374969237, 0.), (0.9554463835580711, 0.29516471358514945, 0.), 36.),
    ((-1324.4612177370714, 1186.640174289331, 0.), (0.9646300873454686, 0.2636072733971383, 0.), 44.),
    ((-1278.8040906382168, 1192.6091816622286, 0.), (0.9788555904703233, 0.2045525189407227, 0.), 40.),
)


def location(index, yaw, z=0., support_height=44.):
    # Leave the street lamp at (-1450,1122) clear. Two on the ground and one
    # supported on the larger crate form a compact store beside the stall.
    e, n = NEW_ANCHOR if index == 0 else (-1476., 1174.)
    return (e, n, z+(support_height if index == 2 else 0.)), (yaw-10.)*.35


def board(model, centre, axes, size, seed, paint=F.WOOD, cup=.045):
    """Chamfered plank with shallow bow, uneven edges and a small corner loss."""
    rng = np.random.default_rng(seed)
    centre, axes = np.asarray(centre, float), np.asarray(axes, float)
    length, width, thick = map(float, size)
    half, depth = width/2, thick/2
    bevel = min(rng.uniform(.17, .32), thick*.31, width*.15)
    cup = max(cup, rng.uniform(.07, .13))
    profile = np.array(((-half+bevel, -depth), (half-bevel, -depth),
        (half, -depth+bevel), (half, depth-bevel), (half-bevel, depth),
        (0, depth-cup), (-half+bevel, depth), (-half, depth-bevel), (-half, -depth+bevel)))
    end_cut = rng.uniform(.15, .31)
    bow = rng.uniform(-.15, .15)
    twist = rng.uniform(-.055, .055)
    chip_at = int(rng.integers(1, 7))
    chip_side = int(rng.choice((-1, 1)))
    chip_depth = rng.uniform(.14, .36)
    xs = np.r_[-length/2, np.linspace(-length/2+end_cut, length/2-end_cut, 7), length/2]
    sections = []
    for k, x in enumerate(xs):
        t = (x+length/2)/length
        q = profile.copy()
        if k in (0, len(xs)-1):
            q[:, 0] *= 1-min(.09, end_cut/half)
            q[:, 1] *= 1-min(.25, end_cut/depth)
        # A localized notch has a sloping return, not a black crack decal.
        bite = chip_depth*max(0., 1-abs(k-chip_at)/1.25)
        edge = q[:, 0]*chip_side > half-bevel-.01
        q[edge, 0] -= chip_side*bite
        q[edge & (q[:, 1] > 0), 1] -= bite*.45
        q[:, 0] += rng.uniform(-.045, .045)*math.sin(math.pi*t)
        q[:, 1] += bow*math.sin(math.pi*t)+twist*(2*t-1)*q[:, 0]/half
        sections.append(np.column_stack((np.full(len(q), x), q)))
    u0, u1 = F.STRIPS[seed % len(F.STRIPS)]
    v0 = (seed*.61803398875) % 1
    def world(q): return centre+q@axes
    for a, b in zip(sections, sections[1:]):
        for i in range(len(profile)):
            if i in (0, 1, len(profile)-1): continue
            j = (i+1) % len(profile)
            local = [a[i], b[i], b[j], a[j]]
            points = [world(q) for q in local]
            edge = profile[j]-profile[i]
            outward = edge[1]*axes[1]-edge[0]*axes[2]
            # Split curved strips explicitly; triangle fans cannot leave the bow.
            for ids in ((0, 1, 2), (0, 2, 3)):
                p = [points[k] for k in ids]
                uv = [(u0+(local[k][1]/width+.5)*(u1-u0), local[k][0]/F.TILE+v0) for k in ids]
                normal = np.cross(p[1]-p[0], p[2]-p[0])
                if np.dot(normal, outward) < 0: normal = -normal
                F.face(model, paint, p, normal, uv)
    for section, sign in ((sections[0], -1), (sections[-1], 1)):
        # A hub below the cup lies inside the profile's visibility kernel, so
        # the closed end triangles do not cross the shallow front concavity.
        centre_q = np.array((section[0, 0], 0., -depth*.35))
        for i in range(len(profile)):
            j = (i+1) % len(profile)
            local = [centre_q, section[i], section[j]]
            F.face(model, C.END, [world(q) for q in local], axes[0]*sign,
                   [(q[1]/12+.5, q[2]/12+.5) for q in local])


def nail(model, point, normal, radius=.12):
    point, normal = np.asarray(point, float), np.asarray(normal, float)
    seed = int(round(np.dot(point, (47, 79, 31)))) & 0xffffffff
    rng = np.random.default_rng(seed)
    tangent = np.cross(normal, (0, 0, 1) if abs(normal[2]) < .9 else (0, 1, 0))
    tangent /= np.linalg.norm(tangent)
    bitangent = np.cross(normal, tangent)
    C.nail(model, point+tangent*rng.uniform(-.13, .13)+bitangent*rng.uniform(-.11, .11),
           normal.copy(), radius*rng.uniform(.86, 1.08))


def build(model, p, size):
    # A private globals table substitutes the two detail primitives without
    # monkey-patching the shared furniture/crate modules used by other work.
    implementation = types.FunctionType(C.build.__code__, {**C.build.__globals__, 'board': board, 'nail': nail})
    implementation(model, p, size)


def stack(model, rng, Place, surface, builder=build):
    """Keep all original layout RNG draws, so later props never move."""
    count = int(rng.integers(2, 4))
    tops = []
    for k in range(count):
        size = float(rng.choice((36., 40., 44.)))
        rng.uniform(-4, 4)  # Former row jitter; retain its RNG draw.
        yaw = 10.+rng.uniform(-8, 8)
        at, angle = location(k, yaw, support_height=tops[1][1] if k == 2 else 0.)
        p = Place(at, angle)
        half = size/2
        p.box(model, (-half, -half, 0), (half, half, size), None, surface)
        builder(model, p, size)
        tops.append((at, size))
    if rng.random() < .6:
        at, top = tops[0]
        yaw = 10.+rng.uniform(-20, 20)
        p = Place((at[0], at[1], top), (yaw-10.)*.35)
        p.box(model, (-16, -16, 0), (16, 16, 32), None, surface)
        builder(model, p, 32.)
