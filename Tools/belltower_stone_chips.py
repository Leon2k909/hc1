"""Localized chips with supporting vertices on each original convex stone face."""
from collections import Counter
import numpy as np
from scipy.spatial import ConvexHull, Delaunay

CHIP_STATS = Counter()


def chipped_mesh(vertices, triangles, chips):
    vertices = np.asarray(vertices, float)
    triangles = np.asarray(triangles, int)
    if not chips: return vertices, triangles
    original_vertices,original_triangles = vertices.copy(),triangles.copy()
    CHIP_STATS['attempted'] += 1
    # Recover the original planar facets, rather than stretching their triangles.
    planes = {}
    for equation in ConvexHull(vertices).equations:
        normal,distance = equation[:3],-equation[3]
        planes[tuple(np.round(np.r_[normal,distance],5))] = (normal,distance)
    normals = np.asarray([n for n,d in planes.values()])
    distances = np.asarray([d for n,d in planes.values()])
    shared = list(vertices)
    # Every face incident to an original edge receives the same chip/support
    # vertices. This keeps the boundary closed when the dent crosses a bevel.
    edges = sorted({tuple(sorted((f[i],f[(i+1)%3]))) for f in triangles for i in range(3)})
    for centre,direction,radius,depth in chips:
        centre = np.asarray(centre,float)
        for a,b in edges:
            p = vertices[a]; delta = vertices[b]-p; square = np.dot(delta,delta)
            if square < 1e-12: continue
            t = np.dot(centre-p,delta)/square
            nearest = p+delta*t
            off = np.linalg.norm(nearest-centre)
            if off > radius*1.35: continue
            margin = np.sqrt(max(0,(radius*1.35)**2-off**2)/square)
            for position in (t,t-margin,t+margin):
                if 1e-6 < position < 1-1e-6: shared.append(p+delta*position)
    shared = np.unique(np.round(shared,8),axis=0)
    points = []; faces = []; index = {}
    def vertex(point):
        key = tuple(np.round(point,8))
        if key not in index:
            index[key] = len(points); points.append(np.asarray(point))
        return index[key]
    for normal,distance in planes.values():
        basis = np.eye(3)[np.argmin(np.abs(normal))]
        u = np.cross(normal,basis); u /= np.linalg.norm(u); v = np.cross(normal,u)
        origin = normal*distance
        local = list(shared[np.abs(shared@normal-distance) < 2e-6])
        for centre,direction,radius,depth in chips:
            centre = np.asarray(centre,float)
            if abs(np.dot(centre,normal)-distance) > radius: continue
            projected = centre+normal*(distance-np.dot(centre,normal))
            samples = [projected]
            for scale,count in ((.6,5),(1.35,10)):
                samples.extend(projected+radius*scale*(np.cos(angle)*u+np.sin(angle)*v)
                               for angle in np.linspace(0,2*np.pi,count,endpoint=False))
            for sample in samples:
                if np.all(normals@sample <= distances+2e-7): local.append(sample)
        local = np.unique(np.round(local,8),axis=0)
        projected = np.column_stack(((local-origin)@u,(local-origin)@v))
        triangulation = Delaunay(projected)
        ids = [vertex(p) for p in local]
        for tri in triangulation.simplices:
            if np.dot(np.cross(local[tri[1]]-local[tri[0]],local[tri[2]]-local[tri[0]]),normal) < 0:
                tri = tri[::-1]
            faces.append(tuple(ids[i] for i in tri))
    original = np.asarray(points)
    # Qhull may omit a collinear boundary point from one incident face. Split
    # those edges explicitly before deformation so both sides stay connected.
    edge_points = {}
    for a,b in {tuple(sorted((f[i],f[(i+1)%3]))) for f in faces for i in range(3)}:
        delta = original[b]-original[a]; square = np.dot(delta,delta)
        if square < 1e-14: continue
        ts = (original-original[a])@delta/square
        nearest = original[a]+ts[:,None]*delta
        on_edge = np.flatnonzero((ts > 1e-6) & (ts < 1-1e-6)
                                 & (np.linalg.norm(original-nearest,axis=1) < 2e-7))
        if len(on_edge): edge_points[(a,b)] = sorted(on_edge,key=lambda i:ts[i])
    conforming = []
    for face in faces:
        boundary = []
        for i,a in enumerate(face):
            b = face[(i+1)%3]; key = tuple(sorted((a,b)))
            middle = edge_points.get(key,[])
            boundary.extend([a]+(list(middle) if a < b else list(reversed(middle))))
        if len(boundary) == 3:
            conforming.append(face)
        else:
            centre = len(points); points.append(original[list(face)].mean(axis=0))
            conforming.extend((centre,a,boundary[(i+1)%len(boundary)]) for i,a in enumerate(boundary))
    original = np.asarray(points); displaced = original.copy(); faces = np.asarray(conforming)
    raw_edge_counts = Counter(tuple(sorted((f[i],f[(i+1)%3]))) for f in faces for i in range(3))
    for centre,direction,radius,depth in chips:
        distance = np.linalg.norm(original-np.asarray(centre),axis=1)/radius
        weight = np.maximum(0,1-distance**2)**1.15
        direction = np.asarray(direction,float); direction /= np.linalg.norm(direction)
        displaced += weight[:,None]*min(depth,radius*.30)*direction
    reference = np.cross(original[faces[:,1]]-original[faces[:,0]],original[faces[:,2]]-original[faces[:,0]])
    area = np.einsum('ij,ij->i',reference,reference)
    for _ in range(18):
        after = np.cross(displaced[faces[:,1]]-displaced[faces[:,0]],displaced[faces[:,2]]-displaced[faces[:,0]])
        unsafe = np.einsum('ij,ij->i',reference,after) < area*.25-1e-14
        if not np.any(unsafe): break
        local = np.unique(faces[unsafe]); displaced[local] = (displaced[local]+original[local])/2
    if np.any(unsafe):
        CHIP_STATS['orientation_fallback'] += 1
        return original_vertices,original_triangles
    positions,remap = np.unique(np.round(displaced,3),axis=0,return_inverse=True)
    faces = remap[faces]
    faces = faces[(faces[:,0]!=faces[:,1]) & (faces[:,1]!=faces[:,2]) & (faces[:,2]!=faces[:,0])]
    edge_counts = Counter(tuple(sorted((f[i],f[(i+1)%3]))) for f in faces for i in range(3))
    if not all(count == 2 for count in edge_counts.values()):
        # A precision-collapsed detail uses the original closed, beveled stone.
        # Decorative wear must never break a whole-map export.
        CHIP_STATS['precision_fallback'] += 1
        return original_vertices,original_triangles
    CHIP_STATS['applied'] += 1
    return positions,faces


def edge_chips(footprint,top,rng,cap=True):
    """A few small losses, with enough undamaged edge left to read as cut stone."""
    chips = []; poly = np.asarray(footprint,float)
    order = rng.permutation(len(poly))
    for i in order:
        a = poly[i]; delta = poly[(i+1)%len(poly)]-a; length = np.linalg.norm(delta)
        if length < 8 or rng.random() > (.8 if cap else .12): continue
        inward = np.array((-delta[1],delta[0]))/length
        position = a+rng.uniform(.24,.76)*delta+inward*.12
        radius = rng.uniform(1.0,1.55)
        chips.append(((*position,top-.20),(*inward,-.85),radius,rng.uniform(.55,.9)))
        if len(chips) >= 2: break
    return chips
