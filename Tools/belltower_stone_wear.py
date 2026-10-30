"""Bounded, material-specific stone wear for Belltower's exposed civic props.

Geometry supplies chipped arrises, eased corners and construction joints. The
existing gameplay collision is retained by the generator wrappers. Shared RNGs,
ornaments, water shaders and scene placements are never modified here.
"""
import math
import zlib
import numpy as np
from scipy.spatial import ConvexHull, HalfspaceIntersection
import map_kit as K
import belltower_furniture as F
import belltower_planters as P
import belltower_stone_chips as Chips

LIMESTONE = 'fountain_limestone'
SCAN = P.STONE
DAMP = 'edge_trough_damp'
WATER = 'fountain_water'
MATERIALS = {LIMESTONE: 'materials/belltower/fountain_limestone.vmat',
             SCAN: 'materials/belltower/planters-v1/cut_stone.vmat',
             DAMP: 'materials/belltower/well-v1/well_damp_stone.vmat',
             WATER: 'materials/belltower/fountain_water.vmat'}
TROUGHS = (((-1500., -88., 0.), (-1410., -58., 30.)),
           ((-2290., 330., 0.), (-2260., 430., 30.)))
TOMBS = ((-560., -700.), (-290., -770.))
FOUNTAIN_RINGS = ((96., 114., 3., 26.), (95., 115., 0., 5.), (94., 114., 26., 30.))
FOUNTAIN_TIERS = ((35, 0, 24), (32, 24, 29), (27, 29, 62), (31, 62, 67),
                  (27, 67, 109), (30, 109, 113), (33, 113, 119), (31, 119, 123))


def rng_at(values, salt=0):
    return np.random.default_rng((zlib.crc32(np.round(values, 3).tobytes())+salt) & 0xffffffff)


def configure(model):
    model.material_overrides.update(MATERIALS)
    model.tile_overrides.update({LIMESTONE: 48, SCAN: P.TILE, DAMP: P.TILE, WATER: 96})


def stone(model, footprint, z0, z1, paint, rng, cap=False, bevel=None):
    """Closed convex cut stone; sparse corner loss stays inside its source bounds."""
    poly = np.asarray(footprint, float)
    area = sum(p[0]*poly[(i+1) % len(poly),1]-p[1]*poly[(i+1) % len(poly),0] for i,p in enumerate(poly))
    if area < 0: poly = poly[::-1]
    origin = poly.mean(axis=0); poly = poly-origin
    half = (z1-z0)/2
    assert half > .05
    planes = []; edges = []
    amount = (.25, .52) if cap else (.16, .37)
    if bevel is not None: amount = bevel
    for i, a in enumerate(poly):
        delta = poly[(i+1) % len(poly)]-a
        n = K.normalise((delta[1], -delta[0])); distance = np.dot(n, a)
        assert distance > 0
        edges.append(n); planes.append((*n, 0, -distance))
        for sign in (-1, 1):
            cut = min(rng.uniform(*amount), half*.4)
            planes.append((*n, sign, -(distance+half-cut)))
    planes.extend(((0, 0, 1, -half), (0, 0, -1, -half)))
    for i, vertex in enumerate(poly):
        n = K.normalise(edges[i-1]+edges[i]); distance = np.dot(n, vertex)
        planes.append((*n, 0, -(distance-rng.uniform(.12, .28))))
        if rng.random() < (.5 if cap else .22):
            planes.append((*n, 1, -(distance+half-min(rng.uniform(.5, .95), half*.6))))
    vertices = HalfspaceIntersection(np.asarray(planes), np.zeros(3)).intersections
    hull = ConvexHull(vertices)
    centre = np.array((*origin, (z0+z1)/2))
    triangles = []
    for tri, equation in zip(hull.simplices, hull.equations):
        if np.dot(np.cross(vertices[tri[1]]-vertices[tri[0]], vertices[tri[2]]-vertices[tri[0]]), equation[:3]) < 0:
            tri = tri[::-1]
        triangles.append(tri)
    if cap:
        vertices, triangles = Chips.chipped_mesh(vertices, triangles, Chips.edge_chips(poly, half, rng))
    projections = {}
    for tri in triangles:
        p = vertices[tri]
        cross = np.cross(p[1]-p[0], p[2]-p[0])
        if np.linalg.norm(cross) < 1e-8: continue
        normal = K.normalise(cross)
        dominant = int(np.argmax(np.abs(normal)))
        u, v = (1, 2) if dominant == 0 else ((0, 2) if dominant == 1 else (0, 1))
        if paint in (SCAN, DAMP):
            span = np.ptp(vertices, axis=0)
            patches = [rect for rect in P.PATCHES if (rect[2]-rect[0])*P.TILE > span[u]+.03
                       and (rect[3]-rect[1])*P.TILE > span[v]+.03]
            # A wall's long dimension can be placed along the long scan patch.
            if not patches:
                u, v = v, u
                patches = [rect for rect in P.PATCHES if (rect[2]-rect[0])*P.TILE > span[u]+.03
                           and (rect[3]-rect[1])*P.TILE > span[v]+.03]
            assert patches, ('Stone face exceeds scan interior', span, u, v)
            key = (u,v)
            if key not in projections: projections[key] = patches[int(rng.integers(len(patches)))]
            rect = projections[key]; middle = (vertices.min(axis=0)+vertices.max(axis=0))/2
            uv = [((rect[0]+rect[2])/2+(q[u]-middle[u])/P.TILE,
                   1-(rect[1]+rect[3])/2+(q[v]-middle[v])/P.TILE) for q in p]
        else:
            uv = [((q+centre)[u]/48+.173, (q+centre)[v]/48+.293) for q in p]
        world = p+centre
        exported = np.round(world, 3)
        if np.linalg.norm(np.cross(exported[1]-exported[0], exported[2]-exported[0])) < 1e-7: continue
        F.face(model, paint, world, normal, uv)


def box_stone(model, lo, hi, paint=LIMESTONE, cap=False, salt=0, bevel=None):
    lo, hi = np.asarray(lo, float), np.asarray(hi, float)
    footprint = [(lo[0], lo[1]), (hi[0], lo[1]), (hi[0], hi[1]), (lo[0], hi[1])]
    stone(model, footprint, lo[2], hi[2], paint, rng_at(np.r_[lo, hi], salt), cap, bevel)


def rectangle_ring(model, outer_lo, outer_hi, inner_lo, inner_hi, z0, z1, paint):
    x0, y0 = outer_lo; x1, y1 = outer_hi
    a0, b0 = inner_lo; a1, b1 = inner_hi
    model.box((x0, y0, z0), (x1, b0, z1), paint)
    model.box((x0, b1, z0), (x1, y1, z1), paint)
    model.box((x0, b0, z0), (a0, b1, z1), paint)
    model.box((a1, b0, z0), (x1, b1, z1), paint)


def rectangle_course(model, lo, hi, inner_lo, inner_hi, z0, z1, rng, paint, cap=False, stagger=0):
    """Mitred corners, irregular joint spacing and complete inner wall surfaces."""
    x0, y0 = lo; x1, y1 = hi; a0, b0 = inner_lo; a1, b1 = inner_hi
    sides = [([(x0,y0),(x1,y0)],[(a0,b0),(a1,b0)]),
             ([(x1,y0),(x1,y1)],[(a1,b0),(a1,b1)]),
             ([(x1,y1),(x0,y1)],[(a1,b1),(a0,b1)]),
             ([(x0,y1),(x0,y0)],[(a0,b1),(a0,b0)])]
    for side, (outer, inner) in enumerate(sides):
        outer, inner = np.asarray(outer), np.asarray(inner)
        count = max(1, math.ceil(np.linalg.norm(outer[1]-outer[0])/18))
        weights = rng.uniform(.86,1.14,count)
        ends = np.r_[0, np.cumsum(weights)/weights.sum()]
        if count > 2 and stagger: ends[1:-1] += stagger/count
        ends = np.sort(np.clip(ends, 0, 1))
        for i, (a,b) in enumerate(zip(ends, ends[1:])):
            gap = .045/max(1., np.linalg.norm(outer[1]-outer[0]))
            a += gap if i else .001; b -= gap if i<count-1 else .001
            at = lambda points,t: points[0]*(1-t)+points[1]*t
            footprint = [at(outer,a), at(outer,b), at(inner,b), at(inner,a)]
            stone(model, footprint, z0+rng.uniform(0,.05), z1-rng.uniform(.015,.10), paint, rng, cap)


def trough(model, lo, hi, surface=None):
    configure(model)
    lo, hi = np.asarray(lo,float), np.asarray(hi,float)
    model.box(lo, hi, None, surface)
    rng = rng_at(np.r_[lo,hi], 731)
    # The old cover box remains. Its narrow bowl cannot fit the player's capsule.
    inner_lo, inner_hi = lo[:2]+4.8, hi[:2]-4.8
    rectangle_ring(model, lo[:2]+.55, hi[:2]-.55, inner_lo-.4, inner_hi+.4,
                   lo[2]+.15, hi[2]-3.8, DAMP)
    for course, (bottom,top) in enumerate(((.2,12.85),(13.0,26.1))):
        rectangle_course(model, lo[:2]+.08, hi[:2]-.08, inner_lo, inner_hi,
                         lo[2]+bottom, lo[2]+top, rng, SCAN, stagger=.14 if course else 0)
    rectangle_course(model, lo[:2], hi[:2], inner_lo-.4, inner_hi+.4,
                     hi[2]-3.75, hi[2], rng, SCAN, cap=True)
    model.box((*inner_lo,lo[2]+1.2), (*inner_hi,lo[2]+5.0), DAMP)
    water_z = hi[2]-2.7
    F.face(model, WATER, [(*inner_lo,water_z),(inner_hi[0],inner_lo[1],water_z),
                         (*inner_hi,water_z),(inner_lo[0],inner_hi[1],water_z)], (0,0,1))


def polygon_ring(model, centre, inner, outer, z0, z1, paint, count=3, cap=True):
    """Jointed octagonal stone ring with closed blocks and eased exposed edges."""
    centre = np.asarray(centre,float)
    rng = rng_at(np.r_[centre,inner,outer,z0,z1], 918)
    points = lambda r,k: centre+r*np.array((math.cos(math.pi/8+k*math.pi/4), math.sin(math.pi/8+k*math.pi/4)))
    # A recessed backing is visible through the small masonry joints.
    for k in range(8):
        o0,o1,i0,i1 = points(outer-.5,k),points(outer-.5,k+1),points(inner+.5,k),points(inner+.5,k+1)
        footprint = [o0,o1,i1,i0]
        stone(model, footprint, z0+.12, z1-.5, paint, rng, False, bevel=(.05,.08))
        weights = rng.uniform(.86,1.14,count); ends = np.r_[0,np.cumsum(weights)/sum(weights)]
        for j,(a,b) in enumerate(zip(ends,ends[1:])):
            a += .0012; b -= .0012
            at = lambda r,t: points(r,k)*(1-t)+points(r,k+1)*t
            footprint = [at(outer,a),at(outer,b),at(inner,b),at(inner,a)]
            stone(model,footprint,z0,z1-rng.uniform(.015,.08),paint,rng,cap)


def fountain_rings(model, centre, ring, surface=None):
    configure(model)
    # Ask the established ring helper to author the exact original collision.
    for inner, outer, low, high in FOUNTAIN_RINGS:
        collision = K.Model()
        ring(collision, centre, inner, outer, low, high, 8,
             {'outside':LIMESTONE,'inside':LIMESTONE,'top':LIMESTONE}, surface)
        model.boxes.extend(collision.boxes); model.hulls.extend(collision.hulls)
        polygon_ring(model,centre,inner,outer,low,high,LIMESTONE,
                     count=1 if high-low>10 else 3, cap=high-low<10)


def fountain_block(model, centre, half, low, high, paint=LIMESTONE, surface=None):
    configure(model)
    lo,hi = (centre[0]-half,centre[1]-half,low),(centre[0]+half,centre[1]+half,high)
    model.box(lo,hi,None,surface)
    box_stone(model,lo,hi,paint,cap=high-low<8,bevel=(.22,.45) if high-low<8 else (.16,.32))


def market_steps(model, centre, surface=None):
    configure(model)
    from belltower_market_steps import build
    build(model,centre,surface)
    box_stone(model,(centre[0]-18,centre[1]-18,200),(centre[0]+18,centre[1]+18,212),cap=True)


def tomb(model, centre, surface=None):
    configure(model)
    e,n = centre
    model.box((e-22,n-42,0),(e+22,n+42,30),None,surface)
    # Staggered cut-stone courses support a single projecting cover slab.
    rng = rng_at(np.array((e,n,30)), 864)
    rectangle_ring(model,(e-21.5,n-41.5),(e+21.5,n+41.5),
                   (e-14,n-34),(e+14,n+34),.03,29.8,DAMP)
    for bottom, top, stagger in ((.03,9.86,0), (10.02,19.84,.14), (20.0,29.9,-.1)):
        rectangle_course(model,(e-22,n-42),(e+22,n+42),
                         (e-14,n-34),(e+14,n+34),bottom,top,rng,SCAN,stagger=stagger)
    box_stone(model,(e-25,n-45,30),(e+25,n+45,34),cap=True,bevel=(.32,.64))
