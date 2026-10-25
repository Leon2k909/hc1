"""Rooted, branching wall ivy with individual curved leaves; visual geometry only.

One generated RGBA atlas supplies four leaf variations. The existing woody scan
supplies the stems. No scene objects, collision or wall geometry are created.
"""
import math
import zlib
import numpy as np

LEAF = 'ivy_leaf3d'
STEM = 'ivy_stem3d'
MATERIALS = {
    LEAF: 'materials/belltower/ivy-3d-v1/leaves.vmat',
    STEM: 'materials/belltower/wood_planks_dark.vmat',
}
ATLAS = 'materials/belltower/ivy-3d-v1/leaves.png'


def unit(v):
    v = np.asarray(v, float)
    return v / max(np.linalg.norm(v), 1e-12)


def build(model, points, outward, hanging=False):
    """Use the old upright patch's four corners as its clearance envelope.

    Coordinates are rounded to the installed OBJ precision so the source hook
    and a targeted patch of the installed model produce exactly the same ivy.
    """
    collision_before = (len(model.boxes), len(model.hulls), len(model.props))
    points = np.round(np.asarray(points, float), 3)
    outward = unit(outward)
    up = np.array((0., 0., 1.))
    right = unit(np.cross(up, outward))
    centre = points.mean(axis=0)
    width = np.ptp(points @ right)
    lo, hi = points[:, 2].min(), points[:, 2].max()
    height = hi - lo
    base = centre.copy(); base[2] = hi if hanging else lo
    direction = -1 if hanging else 1
    key = ','.join(f'{v:.3f}' for v in (abs(centre[0]), centre[1], lo, hi, width, int(hanging)))
    rng = np.random.default_rng(zlib.crc32(key.encode()))
    model.material_overrides.update(MATERIALS)
    model.tile_overrides.update({LEAF: 12, STEM: 24})
    stats = {'leaves': 0, 'stem_segments': 0, 'width': float(width), 'height': float(height)}

    def world(q):
        x, y, depth = q
        return base + right*x + up*(direction*y) + outward*depth

    def tube(a, b, radius, sides=4):
        a, b = world(a), world(b)
        along = unit(b-a)
        u = unit(np.cross(along, outward if abs(np.dot(along, outward)) < .9 else up))
        v = np.cross(along, u)
        length = np.linalg.norm(b-a)
        if length < .04:
            return
        rim = [u*math.cos(k*math.tau/sides)+v*math.sin(k*math.tau/sides) for k in range(sides)]
        for k in range(sides):
            p, q = rim[k], rim[(k+1) % sides]
            model.polygon(STEM, [a+radius*p, a+radius*q, b+radius*.9*q, b+radius*.9*p],
                normal=p+q, normals=[p,q,q,p],
                uv=[(k/sides,0),((k+1)/sides,0),((k+1)/sides,length/24),(k/sides,length/24)])
        stats['stem_segments'] += 1

    def leaf(root, size, angle, young=False):
        # A nine-vertex blade with a raised midrib, curled tip and asymmetric
        # twist. The geometry, rather than painted lighting, bends its normals.
        root = np.asarray(root, float)
        tilt = rng.uniform(-.18, .62)
        long = unit(up*math.cos(angle)+right*math.sin(angle)+outward*tilt)
        across = unit(np.cross(long, outward))
        normal = unit(np.cross(across, long))
        length, span = size, size*rng.uniform(.85, 1.08)
        curl, twist = rng.uniform(-.07,.075), rng.uniform(-.045,.045)
        anchor = world(root) + outward*rng.uniform(.3, 1.4)
        def point(u, v):
            bend = .065*(1-4*u*u)*math.sin(math.pi*v) + curl*v*v + twist*u*v
            return anchor + across*(u*span) + long*((v-.05)*length) + normal*(length*bend)
        def vertex(u, v):
            du = point(u+1e-4,v)-point(u-1e-4,v)
            dv = point(u,v+1e-4)-point(u,v-1e-4)
            return point(u,v), unit(np.cross(du,dv))
        vertices = {(i,j): vertex(-.5+i*.5,j*.5) for j in range(3) for i in range(3)}
        # Keep every blade inside the old patch's horizontal/vertical clearance.
        local = [q-base for q,n in vertices.values()]
        if any(abs(np.dot(q,right)) > width*.495 or not .15 <= direction*q[2] <= height-.15 for q in local):
            return
        minimum = min(np.dot(q,outward) for q in local)
        offset = outward*max(0., .18-minimum)
        cell = int(rng.choice([0,1,2,3], p=[.37,.35,.06,.22])) if not young else 1
        column, row = cell % 2, cell // 2
        def uv(i,j):
            return ((column+i*.5)*.5, (1-row*.5)-.5+j*.25)
        for j in range(2):
            for i in range(2):
                ids = [(i,j),(i+1,j),(i+1,j+1),(i,j+1)]
                values = [vertices[k] for k in ids]
                model.polygon(LEAF, [q+offset for q,n in values],
                    normal=sum(n for q,n in values), normals=[n for q,n in values], uv=[uv(*k) for k in ids])
        # Connect the visible petiole to its branch, including the blade's lift.
        petiole = point(0,.055)+offset
        delta = petiole-base
        end = (np.dot(delta,right), direction*delta[2], np.dot(delta,outward))
        tube(root, end, .045, 4)
        stats['leaves'] += 1

    count = 3 if width < 75 else 4
    for main in range(count):
        lateral = (main-(count-1)/2) / max(1,(count-1)/2)
        reach = height*rng.uniform(.79, .985)
        phase = rng.uniform(0,math.tau)
        def stem(t):
            return np.array((lateral*width*(.075+.27*t**.8) + math.sin(t*9+phase)*width*.035*math.sin(math.pi*t),
                t*reach, .18+.3*math.sin(t*7+phase)**2+(1.3*t if hanging else .15*t)))
        steps = max(7, int(reach/7))
        for j in range(steps):
            t0,t1 = j/steps,(j+1)/steps
            tube(stem(t0),stem(t1),.19*(1-t0)+.055,5)
        branches = max(6, int(reach/8))
        for j in range(branches):
            t = .09+.84*(j+.3)/branches
            a = stem(t)
            side = (-1 if (j+main)%2 else 1)
            available = width*.47-side*a[0]
            length = min(available, width*rng.uniform(.17,.30))
            if length < 3:
                continue
            rise = min(reach*.96-a[1], rng.uniform(4,10))
            length = max(3,length)
            depth = rng.uniform(1.2,3.0)
            def branch(s):
                return a+np.array((side*length*s,rise*s+1.5*math.sin(math.pi*s),depth*math.sin(math.pi*s*.72)))
            for k in range(3):
                tube(branch(k/3),branch((k+1)/3),.085*(1-k/3)+.035)
            leaves = max(3, int(length/2.6))
            for k in range(leaves):
                s = (k+.5)/leaves
                origin = branch(s)
                angle = side*rng.uniform(.4,1.35) + (-.5 if k%2 else .3)
                if rng.random() < .13:
                    angle += side*.9
                if hanging:
                    angle = math.pi-angle
                leaf(origin, rng.uniform(3.25,5.05)*(.7 if s>.88 else 1), angle, young=s>.88)
        # Sparse terminal growth leaves the youngest shoots visible.
        for t in (.84,.91,.965):
            origin = stem(t)
            leaf(origin, rng.uniform(2.4,3.6), rng.uniform(-.6,.6)+(math.pi if hanging else 0), True)
    assert collision_before == (len(model.boxes), len(model.hulls), len(model.props))
    return stats
