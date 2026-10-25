"""Belltower fountain water v3: nozzle-sized jets and fine impact spray.

No collision, scene objects or texture pixels are created. Droplets carry their
phase and launch direction in UVs for bounded, GPU-only ballistic motion.
"""
import math
import numpy as np
import map_kit as K
import belltower_furniture as F
import belltower_detail as D

WATER = 'fountain_water'
JET = 'fountain_jet'
RESOURCE = 'materials/belltower'
SURFACE_SHADER = 'shaders/belltower_fountain_surface_v3.shader'
STREAM_SHADER = 'shaders/belltower_fountain_stream_v3.shader'


def material_definitions(centre=(0., 130.)):
    world = K.to_world((*centre, 21.5))
    origin = ' '.join(f'{v:.4f}' for v in world)
    return {
        WATER: ('"Layer0"\n{\n'
            f'    shader "{SURFACE_SHADER}"\n'
            f'    TextureNormalA "{RESOURCE}/fountain_water_normal.png"\n'
            f'    TextureNormalB "{RESOURCE}/fountain_water_normal.png"\n'
            f'    g_vBasinCentre "[{origin}]"\n'
            '    g_vWaterColor "[0.035 0.085 0.073]"\n'
            '    g_flAbsorptionDistance "95"\n'
            '    g_flWaterRoughness "0.085"\n}\n'),
        JET: ('"Layer0"\n{\n'
            f'    shader "{STREAM_SHADER}"\n'
            f'    TextureNormalA "{RESOURCE}/fountain_jet_normal.png"\n'
            f'    g_vBasinCentre "[{origin}]"\n'
            '    g_flFlowSpeed "1.0"\n}\n')}


def pool(model, centre):
    model.tile_overrides[WATER] = 96
    model.material_overrides[WATER] = f'{RESOURCE}/{WATER}.vmat'
    model.cylinder(centre, 96, 20, 21.5, {'top': WATER}, sides=8, turn=math.pi/8)


def spout(model, P, along, out, seed=0):
    up = np.array((0., 0., 1.))
    model.tile_overrides[JET] = 96
    model.material_overrides[JET] = f'{RESOURCE}/{JET}.vmat'
    # A horizontal jet exits the existing 1.1-inch bore. A 20.5-inch fall takes
    # 0.326 seconds under gravity, placing its impact at the existing 45-inch
    # offset. Conservation of volume narrows the stream as it accelerates.
    rings = []
    segments, sides = 56, 12
    for t in np.linspace(0, 1, segments+1):
        point = P(0, 10.12+34.88*t, 42-20.5*t*t)
        tangent = K.normalise(out*34.88-up*41*t)
        v = K.normalise(np.cross(tangent, along))
        speed = np.linalg.norm(out*34.88-up*41*t)
        radius = .455*math.sqrt(34.88/speed)
        ring = []
        for j in range(sides+1):
            angle = j*math.tau/sides
            normal = along*math.cos(angle)+v*math.sin(angle)
            ring.append((point+normal*radius, normal, (j/sides, t*5.6)))
        rings.append(ring)
    for a, b in zip(rings, rings[1:]):
        for j in range(sides):
            vertices = (a[j], a[j+1], b[j+1], b[j])
            F.face(model, JET, [x[0] for x in vertices], sum(x[1] for x in vertices),
                   [x[2] for x in vertices], [x[1] for x in vertices])
    impact = P(0, 45, 21.5)
    rng = np.random.default_rng(913+seed)
    def droplet(identity, radius, elongation):
        sphere=K.Model(); D.ball(sphere,(0,0,0),1,JET,rings=6,segments=10)
        scale=np.array((radius*.82,radius*.82,radius*elongation))
        for points,normal in sphere.polygons[JET]:
            vertices=[impact+np.asarray(p)*scale for p in points]
            normals=[K.normalise(np.asarray(p)/scale) for p in points]
            # Stable identity with a curved silhouette, rather than an
            # octahedron that becomes a visible diamond in close views.
            uv=[(2+identity+.5+.35*p[0],.5+.35*p[2]) for p in points]
            F.face(model, JET, vertices, sum(normals), uv, normals)

    for j in range(32):
        droplet(seed*32+j, rng.uniform(.045, .11), rng.uniform(1.1, 1.8))
    # A few larger beads emerge from the falling end of the coherent jet.
    for j in range(8):
        droplet(128+seed*8+j, rng.uniform(.11, .20), rng.uniform(1.4, 2.0))
    # Transient, narrow crown fingers. Negative U marks these water sheets; the
    # shader animates each burst independently. Both windings retain back culling
    # on the coherent jet, avoiding its former double-blended opaque shell.
    for j in range(8):
        identity = seed*8+j
        angle = j*math.tau/8+rng.uniform(-.2, .2)
        radial = along*math.cos(angle)+out*math.sin(angle)
        across = K.normalise(np.cross(up, radial))
        height = rng.uniform(.85, 1.65)
        reach = rng.uniform(2.0, 3.7)
        rows = []
        for t in np.linspace(0, 1, 6):
            p = impact+radial*(.3+reach*t)+up*(.02+height*math.sin(math.pi*t))
            width = (.055+.12*math.sin(math.pi*t))*(1-.7*t)
            tangent = radial*reach+up*(height*math.pi*math.cos(math.pi*t))
            normal = K.normalise(np.cross(across, tangent))
            rows.append([(p+across*width*s, normal, (-(2+identity+u), t)) for s, u in ((-1,.2),(1,.8))])
        for a, b in zip(rows, rows[1:]):
            values = (a[0],a[1],b[1],b[0])
            for side in (-1,1):
                F.face(model,JET,[p for p,n,uv in values],sum(n for p,n,uv in values)*side,
                       [uv for p,n,uv in values],[n*side for p,n,uv in values])


def build(model, centre=(0., 130.)):
    pool(model, centre)
    e, n = centre
    for k in range(4):
        angle = k*math.pi/2
        out = np.array((math.cos(angle), math.sin(angle), 0.))
        along = np.array((-out[1], out[0], 0.))
        origin = np.array((e, n, 0.))+27*out
        def P(x, d, z):
            return origin+along*x+out*d+np.array((0., 0., z))
        spout(model, P, along, out, k)
