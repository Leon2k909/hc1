"""Carved limestone lion masks and lilies for Belltower's existing fountain.

Coordinates are local inches: horizontal, outward depth, up. The local face
frame is left handed, so emit() checks winding against transformed normals.
The lion is one implicit solid, with carved sockets and connected mane locks.
No collision, water geometry, scene data or material resources are authored here.
"""
from functools import lru_cache
import hashlib
import inspect
import math
from pathlib import Path
import numpy as np
from scipy.ndimage import map_coordinates
from skimage.measure import marching_cubes

import map_kit as K

STONE = "fountain_limestone"
BRONZE = "fountain_bronze"
LION_BAKE_VERSION = "connected-solid-v2"


def bezier(points, count=20):
    p = np.asarray(points, float)
    t = np.linspace(0, 1, count)[:, None]
    return (1-t)**3*p[0] + 3*(1-t)**2*t*p[1] + 3*(1-t)*t*t*p[2] + t**3*p[3]


class Carving:
    def __init__(self, lo, hi, spacing):
        self.lo = np.asarray(lo, float)
        self.spacing = spacing
        self.axes = [np.arange(a, b+spacing, spacing, dtype=np.float32) for a, b in zip(lo, hi)]
        self.field = np.full(tuple(len(a) for a in self.axes), 1000, np.float32)

    def stamp(self, lo, hi, distance, blend=0., subtract=False):
        cuts = tuple(slice(max(0, math.floor((a-o)/self.spacing)),
                           min(len(axis), math.ceil((b-o)/self.spacing)+1))
                     for a, b, o, axis in zip(lo, hi, self.lo, self.axes))
        if any(s.start >= s.stop for s in cuts):
            return
        x, d, z = np.meshgrid(*(axis[s] for axis, s in zip(self.axes, cuts)), indexing='ij', sparse=True)
        value = distance(x, d, z)
        old = self.field[cuts]
        if subtract:
            old = -old
        if blend:
            h = np.clip(.5 + .5*(value-old)/blend, 0, 1)
            result = value*(1-h) + old*h - blend*h*(1-h)
        else:
            result = np.minimum(old, value)
        self.field[cuts] = -result if subtract else result

    def ellipsoid(self, centre, radii, blend=.45, subtract=False, tilt=0.):
        centre, radii = np.asarray(centre), np.asarray(radii)
        # The extra band ensures the local blend has no clipped influence.
        extent = np.full(3, radii.max()+blend+1) if tilt else radii+blend+1

        def distance(x, d, z):
            x, d, z = x-centre[0], d-centre[1], z-centre[2]
            if tilt:
                x, z = x*math.cos(tilt)+z*math.sin(tilt), -x*math.sin(tilt)+z*math.cos(tilt)
            q = (x/radii[0], d/radii[1], z/radii[2])
            k0 = np.sqrt(sum(v*v for v in q))
            k1 = np.sqrt(sum((v/r)**2 for v, r in zip(q, radii)))
            return k0*(k0-1)/np.maximum(k1, 1e-8)

        self.stamp(centre-extent, centre+extent, distance, blend, subtract)

    def stroke(self, controls, start_radius, end_radius, depth_scale=1.5, blend=.3, subtract=False):
        points = bezier(controls, 20)
        for i, (a, b) in enumerate(zip(points[:-1], points[1:])):
            ta, tb = i/(len(points)-1), (i+1)/(len(points)-1)
            ra, rb = start_radius*(1-ta)+end_radius*ta, start_radius*(1-tb)+end_radius*tb
            scale = np.array((1., depth_scale, 1.))
            delta = (b-a)*scale
            denominator = np.dot(delta, delta)
            extent = max(ra, rb)+blend+.6

            def distance(x, d, z):
                q = ((x-a[0])*scale[0], (d-a[1])*scale[1], (z-a[2])*scale[2])
                t = np.clip(sum(q[j]*delta[j] for j in range(3))/denominator, 0, 1)
                return np.sqrt(sum((q[j]-t*delta[j])**2 for j in range(3))) - (ra*(1-t)+rb*t)

            self.stamp(np.minimum(a, b)-extent, np.maximum(a, b)+extent, distance, blend, subtract)

    def mesh(self):
        x, d, z = np.meshgrid(*self.axes, indexing='ij', sparse=True)
        # Sub-millimetre carving variation; the tiling stone normal supplies pores.
        self.field += .018*np.sin(x*4.3+z*1.8)*np.sin(d*3.1-z*2.4)
        vertices, faces, _, _ = marching_cubes(self.field, 0, spacing=(self.spacing,)*3,
                                              allow_degenerate=False)
        coordinates = (vertices/self.spacing).T
        gradient = np.gradient(self.field, self.spacing)
        normals = np.column_stack([map_coordinates(g, coordinates, order=1, mode='nearest') for g in gradient])
        normals /= np.maximum(np.linalg.norm(normals, axis=1)[:, None], 1e-9)
        vertices += self.lo
        face_normals = np.cross(vertices[faces[:, 1]]-vertices[faces[:, 0]], vertices[faces[:, 2]]-vertices[faces[:, 0]])
        flip = np.sum(face_normals*normals[faces].sum(axis=1), axis=1) < 0
        faces[flip] = faces[flip][:, [0, 2, 1]]
        return vertices, faces, normals

    def surface_channel(self, controls, radius=.21):
        """Cut a shallow chisel channel that follows the sculpt's actual front."""
        points = bezier(controls, 30)
        depth_axis = self.axes[1]
        previous = None
        for x, z in points:
            coords = np.vstack((np.full(len(depth_axis), (x-self.lo[0])/self.spacing),
                                np.arange(len(depth_axis)), np.full(len(depth_axis), (z-self.lo[2])/self.spacing)))
            values = map_coordinates(self.field, coords, order=1, mode='nearest')
            inside = np.flatnonzero(values < 0)
            if not len(inside):
                previous = None; continue
            at = inside[-1]
            if at+1 >= len(values): continue
            t = -values[at]/max(1e-8, values[at+1]-values[at])
            depth = float(depth_axis[at]+t*self.spacing)+radius*.35
            p = np.array((x, depth, z))
            self.ellipsoid(p, (radius, radius*.95, radius), .04, subtract=True)
            if previous is not None:
                self.stroke([previous, previous+(p-previous)/3, previous+2*(p-previous)/3, p],
                            radius, radius, depth_scale=1., blend=.025, subtract=True)
            previous = p


def sculpt_lion_mesh():
    c = Carving((-14, -3.8, -16), (14, 13, 16), .22)
    # Connected backing and broad facial masses. All locks blend into this stone.
    c.ellipsoid((0, -.15, -.4), (11.2, 2.75, 12.9), .65)
    locks = [
        ([(.8, 1.8, 8.6), (2.6, 1.6, 12.5), (7.1, .8, 12.8), (6.2, .03, 10.5)], 1.15, .07),
        ([(4.7, 1.8, 7.6), (8.9, 1.4, 11.9), (10.5, .55, 9.6), (9.4, .03, 7.9)], 1.35, .07),
        ([(6.2, 1.9, 5.8), (11.5, 1.3, 7.0), (9.2, .55, 3.2), (10.2, .02, 1.9)], 1.4, .08),
        ([(7.4, 1.7, 2.2), (11.7, 1.6, .5), (9.5, .65, -4.4), (10.2, .02, -5.5)], 1.35, .06),
        ([(7.0, 1.9, -2.5), (10.3, 1.65, -5.2), (7.3, .8, -9.1), (8.1, .02, -10.2)], 1.35, .07),
        ([(5.0, 2.0, -5.0), (7.4, 1.95, -7), (4.1, .7, -11.7), (5.0, .02, -12.4)], 1.35, .06),
        ([(3.0, 2.0, -7.0), (4.0, 1.8, -9.7), (1.3, .6, -12.6), (1.9, .02, -13.2)], 1.15, .06),
        ([(6.0, 2.6, 6.4), (9.5, 2.7, 4.8), (7.4, 2.3, .3), (8.2, .2, -1.8)], 1.05, .07),
        ([(6.3, 2.7, -.2), (8.2, 2.6, -2.8), (5.5, 2.2, -5), (6.3, .2, -7.4)], 1.05, .06),
    ]
    for sign in (-1, 1):
        for number, (controls, r0, r1) in enumerate(locks):
            points = [(sign*x + (.16*math.sin(number*2.1) if sign < 0 else 0), d, z) for x, d, z in controls]
            c.stroke(points, r0, r1, depth_scale=1.15, blend=.6)
    c.stroke([(1.0, 2.4, 8.7), (.4, 2.1, 11.1), (-3.4, 1.0, 12.3), (-4.8, .05, 11.6)], 1.2, .06, blend=.5)
    c.ellipsoid((0, 3.15, .5), (6.55, 3.75, 7.6), 1.2)
    c.ellipsoid((0, 4.0, 5.3), (4.7, 2.65, 4.0), 1.)
    for sign in (-1, 1):
        c.ellipsoid((sign*4.7, 4.25, -1.6), (2.65, 2.15, 4.25), .8)
        c.ellipsoid((sign*6.0, 2.9, 7.1), (2.25, 1.75, 2.5), .75, tilt=sign*.18)
        c.ellipsoid((sign*3.15, 6.1, 3.55), (2.9, 1.15, 1.1), .55, tilt=-sign*.23)
    c.ellipsoid((0, 6.1, .05), (2.1, 2.6, 4.0), 1.0)
    for sign in (-1, 1):
        c.ellipsoid((sign*2.05, 7.0, -3.7), (2.65, 2.35, 2.05), .45)
    c.ellipsoid((0, 5.3, -6.7), (3.7, 2.45, 2.3), .75)
    c.ellipsoid((0, 8.8, -1.8), (2.15, 1.55, 1.5), .4)
    # Recessed eyes, ear bowls, nostrils and the mouth are cuts in solid stone.
    for sign in (-1, 1):
        c.ellipsoid((sign*3.35, 6.5, 1.9), (1.65, 1.65, 1.0), .18, subtract=True, tilt=sign*.12)
        c.ellipsoid((sign*6.0, 4.15, 7.25), (1.2, .95, 1.45), .2, subtract=True, tilt=sign*.18)
        c.ellipsoid((sign*1.3, 10.03, -2.1), (.55, .70, .40), .12, subtract=True)
        c.ellipsoid((sign*3.35, 5.05, 1.94), (.70, .8, .48), .28)
        c.stroke([(sign*1.2, 6.75, 2.3), (sign*2.4, 7., 3.4), (sign*4.5, 6.8, 3.3), (sign*5.5, 5.7, 2.4)], .42, .12, blend=.3)
    c.ellipsoid((0, 7.8, -5.0), (1.5, 3.6, 1.28), .12, subtract=True)
    c.stroke([(0, 9.08, -2.8), (0, 9.3, -3.4), (0, 9.24, -3.8), (0, 8.8, -4.2)], .12, .2, blend=.05, subtract=True)
    # Shallow curling channels divide connected mane locks, without tube-shaped gaps.
    for sign in (-1, 1):
        for controls in [
            [(7.5, 3.75, 7), (10.2, 3.25, 6.3), (9.7, 3.45, 3.5), (9.2, 2.6, 1.7)],
            [(8.7, 3.4, 1.1), (10.2, 3.5, -1.2), (8.1, 3.45, -4.1), (8.1, 2.4, -5.7)],
            [(6.5, 3.7, -3.9), (8.0, 3.7, -6), (5.4, 3.1, -8.9), (5.4, 1.9, -10.7)],
            [(4.0, 3.6, -7.5), (4.9, 3.35, -9), (2.5, 2.8, -11.2), (2.5, 1.6, -12.4)],
        ]:
            c.stroke([(sign*x, d, z) for x, d, z in controls], .20, .12,
                     depth_scale=.85, blend=.06, subtract=True)
        for controls in [
            [(3.5, 9.3), (5.0, 11.0), (7.2, 11.2), (7.2, 9.8)],
            [(7.0, 6.4), (10.0, 6.9), (9.1, 4.2), (9.7, 2.8)],
            [(8.0, 1.9), (10.3, .6), (9.1, -2.7), (9.5, -4.3)],
            [(7.1, -3.3), (9.2, -5.0), (7.1, -7.9), (7.5, -9.3)],
            [(5.7, -6.3), (6.4, -7.8), (4.1, -10.3), (4.7, -11.3)],
            [(3.0, -8.1), (3.7, -9.5), (2.0, -11.4), (2.3, -12.1)],
        ]:
            c.surface_channel([(sign*x, z) for x, z in controls], .22)
        # Shorter chisel accents in the brow and whisker pads.
        c.surface_channel([(sign*.7, 3.1), (sign*1.0, 5.0), (sign*1.5, 6.7), (sign*2.0, 7.5)], .12)
        c.surface_channel([(sign*2.6, -3.0), (sign*3.3, -2.8), (sign*3.9, -3.5), (sign*4.1, -4.3)], .10)
    return c.mesh()


def lion_signature():
    return hashlib.sha256((LION_BAKE_VERSION+''.join(inspect.getsource(f) for f in (bezier, Carving, sculpt_lion_mesh))).encode()).hexdigest()


def lion_cache_path():
    return Path(__file__).resolve().parents[1]/'Sources/Belltower/props/fountain-ornaments-v2'/('lion-'+lion_signature()[:12]+'.npz')


@lru_cache(maxsize=1)
def lion_mesh():
    path = lion_cache_path()
    if not path.exists():
        raise RuntimeError('Bake the changed lion sculpt with Tools/belltower_bake_fountain_lion.py before generating the fountain.')
    with np.load(path, allow_pickle=False) as cached:
        assert str(cached['signature']) == lion_signature()
        return cached['vertices'].copy(), cached['faces'].copy(), cached['normals'].copy()


def vertex_normals(vertices, faces):
    normals = np.zeros_like(vertices)
    n = np.cross(vertices[faces[:, 1]]-vertices[faces[:, 0]], vertices[faces[:, 2]]-vertices[faces[:, 0]])
    for k in range(3):
        np.add.at(normals, faces[:, k], n)
    return normals/np.maximum(np.linalg.norm(normals, axis=1)[:, None], 1e-9)


def petal(controls, width, crown, rings=26, around=12, vein=False):
    """Closed, rounded leaf with its back embedded in the supporting stone."""
    points = bezier(controls, rings)
    vertices = []
    for i, centre in enumerate(points):
        t = i/(rings-1)
        tangent = points[min(i+1, rings-1)]-points[max(i-1, 0)]
        tangent /= np.linalg.norm(tangent)
        across = np.array((-tangent[1], tangent[0]))
        radius = width*math.sin(math.pi*t)**.8 + .015
        for j in range(around):
            a = 2*math.pi*j/around
            p = centre+across*(radius*math.cos(a))
            front = max(0., math.sin(a))
            depth = -.10 + (crown*math.sin(math.pi*t)**.35)*front**.75 + min(0., math.sin(a))*.26
            if vein:
                depth -= .13*math.exp(-(math.cos(a)/.16)**2)*front*math.sin(math.pi*t)
            vertices.append((p[0], depth, p[1]))
    faces = []
    for i in range(rings-1):
        for j in range(around):
            a, b = i*around+j, i*around+(j+1) % around
            c, d = b+around, a+around
            faces.extend(((a, b, c), (a, c, d)))
    for j in range(1, around-1):
        faces.append((0, j+1, j))
        last = (rings-1)*around
        faces.append((last, last+j, last+j+1))
    vertices, faces = np.asarray(vertices), np.asarray(faces, np.int32)
    # This construction's outward side is +depth. Correct the full closed mesh.
    volume = np.sum(vertices[faces[:, 0]]*np.cross(vertices[faces[:, 1]], vertices[faces[:, 2]]))/6
    if volume < 0:
        faces = faces[:, [0, 2, 1]]
    return vertices, faces, vertex_normals(vertices, faces)


@lru_cache(maxsize=1)
def lily_mesh():
    meshes = [petal([(0, -.9), (-.3, 4.5), (.3, 9.5), (0, 13)], 2.65, 2.10, vein=True)]
    for sign in (-1, 1):
        meshes.append(petal([(sign*.7, -.1), (sign*.3, 8.2), (sign*10.2, 10.2), (sign*6.3, 3.9)], 1.85, 1.8, vein=True))
        meshes.append(petal([(sign*.4, -1), (sign*.1, -4.7), (sign*2.8, -5.9), (sign*3.9, -4.4)], .92, 1.5, rings=22))
    meshes.append(petal([(0, -1.1), (.05, -3.1), (0, -4.7), (0, -6.1)], .92, 1.55, rings=22))
    # A gently arched binding band, with rounded ends and a convex front.
    band = petal([(-3.4, -.7), (-1.4, -.4), (1.4, -.4), (3.4, -.7)], .68, 2.05, rings=24)
    band[0][:, 1] += .65
    meshes.append(band)
    vertices, faces, normals = [], [], []
    offset = 0
    for v, f, n in meshes:
        vertices.extend(v); faces.extend(f+offset); normals.extend(n); offset += len(v)
    return np.asarray(vertices), np.asarray(faces), np.asarray(normals)


def emit(model, P, mesh, z_offset=0., scale=1., paint=STONE):
    vertices, faces, normals = mesh
    origin = np.asarray(P(0, 0, 0))
    matrix = np.column_stack([np.asarray(P(*p))-origin for p in ((1, 0, 0), (0, 1, 0), (0, 0, 1))])
    assert abs(abs(np.linalg.det(matrix))-1) < 1e-6
    points = vertices*scale
    points[:, 2] += z_offset
    transformed = points @ matrix.T + origin
    transformed_normals = normals @ np.linalg.inv(matrix)
    for face in faces:
        ids = face.copy()
        v = transformed[ids]
        n = transformed_normals[ids]
        if np.dot(np.cross(v[1]-v[0], v[2]-v[0]), n.sum(axis=0)) < 0:
            ids = ids[[0, 2, 1]]; v = transformed[ids]; n = transformed_normals[ids]
        uv = [(points[i, 0]/48+.17, points[i, 2]/48+.29) for i in ids]
        model.polygon(paint, v, normals=n, uv=uv)
    model.material_overrides[paint] = f"materials/belltower/{paint}.vmat"
    model.tile_overrides[paint] = 48


def lion(model, P):
    emit(model, P, lion_mesh(), z_offset=47.)
    # Closed bronze outlet with an actual dark bore. Its tip meets the unchanged
    # water spline at P(0,10,42); the small rear cap is deep inside the mouth.
    around = 32
    vertices, faces = [], []
    profile = [(7.4, .78), (9.45, .78), (9.60, .94), (10.0, .94),
               (10.12, .80), (10.12, .55), (7.3, .55)]
    for depth, r in profile:
        for j in range(around):
            a = 2*math.pi*j/around
            vertices.append((r*math.cos(a), depth, 42+r*math.sin(a)))
    for i in range(len(profile)-1):
        for j in range(around):
            a = i*around+j; b = i*around+(j+1) % around
            faces.extend(((a, b, b+around), (a, b+around, a+around)))
    v, f = np.asarray(vertices), np.asarray(faces)
    # Orient the outer barrel towards its radius and inner barrel into its bore.
    for i, face in enumerate(f):
        centre = v[face].mean(axis=0)
        radial = np.array((centre[0], 0, centre[2]-42))
        desired = radial if i//(around*2) < 4 else -radial
        if abs(np.cross(v[face[1]]-v[face[0]], v[face[2]]-v[face[0]])[1]) > .01:
            desired = np.array((0, 1., 0))
        if np.dot(np.cross(v[face[1]]-v[face[0]], v[face[2]]-v[face[0]]), desired) < 0:
            f[i] = face[[0, 2, 1]]
    emit(model, P, (v, f, vertex_normals(v, f)), paint=BRONZE)


def lily(model, P, z, scale):
    emit(model, P, lily_mesh(), z_offset=z, scale=scale)


def build(model, centre=(0., 130.)):
    """All 4 masks and 12 lilies in their existing fountain locations."""
    e, n = centre

    def face_frame(angle, radius):
        out = np.array((math.cos(angle), math.sin(angle), 0.))
        along = np.array((-out[1], out[0], 0.))
        origin = np.array((e, n, 0.))+radius*out
        return lambda x, d, z: origin+along*x+out*d+np.array((0., 0., z))

    for k in range(8):
        lily(model, face_frame(k*math.pi/4+math.pi/4, 114*math.cos(math.pi/8)), 13, .65)
    for k in range(4):
        P = face_frame(k*math.pi/2, 27)
        lily(model, P, 83, 1.25)
        lion(model, P)
