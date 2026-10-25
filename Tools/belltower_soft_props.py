"""Small physical bends in old timber and folded paper; no texture changes."""
import numpy as np
import belltower_furniture as F


def clip(vertices, axis, edge, sign):
    result = []
    for a, b in zip(vertices, vertices[1:] + vertices[:1]):
        da, db = (a[0][axis]-edge)*sign, (b[0][axis]-edge)*sign
        if da >= -1e-9:
            result.append(a)
        if (da < 0) != (db < 0):
            t = da/(da-db)
            result.append((a[0]+t*(b[0]-a[0]), a[1]+t*(b[1]-a[1])))
    return result


def emit(model, paint, points, normal, uv, centre, axes, warp, divisions):
    """Split long faces before bending, retaining UVs and the closed edge grid."""
    centre, axes = np.asarray(centre), np.asarray(axes)
    vertices = [((np.asarray(p)-centre) @ axes.T, np.asarray(t)) for p, t in zip(points, uv)]
    cells = [vertices]
    for axis, edges in divisions:
        sliced = []
        for polygon in cells:
            for low, high in zip(edges, edges[1:]):
                piece = clip(clip(polygon, axis, low, 1), axis, high, -1)
                if len(piece) >= 3:
                    sliced.append(piece)
        cells = sliced
    local_normal = np.asarray(normal) @ axes.T
    for polygon in cells:
        positions, coords, normals = [], [], []
        for p, texture in polygon:
            delta = .001
            jacobian = np.column_stack([(warp(p+np.eye(3)[i]*delta)-warp(p-np.eye(3)[i]*delta))/(2*delta)
                                        for i in range(3)])
            n = np.linalg.solve(jacobian.T, local_normal) @ axes
            normals.append(n/np.linalg.norm(n))
            positions.append(centre + warp(p) @ axes)
            coords.append(tuple(texture))
        for i in range(1, len(positions)-1):
            ids = (0, i, i+1)
            rounded = np.round([positions[j] for j in ids], 3)
            if np.linalg.norm(np.cross(rounded[1]-rounded[0], rounded[2]-rounded[0])) < 1e-8:
                continue
            F.face(model, paint, [positions[j] for j in ids], normal,
                   [coords[j] for j in ids], [normals[j] for j in ids])


def shelf_drop(x, half):
    return -.10 * max(0., 1-(x/half)**2)


def timber(size):
    half = size[0]/2
    def warp(p):
        q = p.copy()
        q[2] += shelf_drop(p[0], half)
        return q
    return warp, [(0, np.linspace(-half-.001, half+.001, max(3, round(size[0]/9)+1)))]


def packet(size, phase):
    w, d, h = size
    def warp(p):
        x, y, z = p
        a, b, c = 2*x/w, 2*y/d, 2*z/h
        # The tied parcel remains within its previous stack height. The paper
        # creases inward, and the underside stays flat on its supporting shelf.
        weight = np.clip((c+1)/2, 0, 1)
        crease = np.sin(2.2*a+phase) * (.3+.7*weight)
        return p + (0., -.09*crease*(1-b*b*.25),
                    -.16*max(0., 1-a*a)*(.7+.3*max(0., 1-b*b))*weight)
    return warp, [(0, np.linspace(-w/2-.01, w/2+.01, 5)),
                  (1, np.linspace(-d/2-.4, d/2+.4, 4))]


def ticket(width, height):
    def warp(p):
        q = p.copy()
        # Upper middle stays in its metal clip; the free corners curl gently.
        q[1] += .12*(2*p[0]/width)**2 * np.clip(.5-p[2]/height, 0, 1)
        return q
    return warp, [(0, np.linspace(-width/2-.01, width/2+.01, 5))]
