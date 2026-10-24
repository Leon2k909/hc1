"""Shed-only worn timber: rounded arrises, restrained bow and local edge loss.

The board faces keep the existing photographed grain. Wear is in the silhouette,
not another damage texture, and never adds gameplay collision.
"""
import math
import numpy as np
import belltower_furniture as F


def board(model, centre, axes, size, paint=F.WOOD, seed=0, trim=False):
    centre, axes, size = np.asarray(centre, float), np.asarray(axes, float), np.asarray(size, float)
    grain = int(np.argmax(size))
    width, depth = sorted((i for i in range(3) if i != grain), key=lambda i: -size[i])
    length, half_w, half_d = size[grain], size[width]/2, size[depth]/2
    rng = np.random.default_rng(seed & 0xffffffff)
    phase = rng.uniform(0, math.tau, 4)
    # Two isolated losses on the arris; the remaining board is sound timber.
    chips = [(rng.uniform(.09, .32), int(rng.integers(2 if trim else 4))),
             (rng.uniform(.61, .87), int(rng.integers(2 if trim else 4)))]
    stations = sorted(set([0., .025, .17, .43, .73, .975, 1.] +
                         [max(0., min(1., t+d)) for t, _ in chips for d in (-.035, 0., .035)]))
    rings, cross_normals = [], []
    for t in stations:
        # Preserve the footprint and the recess behind the corner trims.
        bend = (.26 if trim else .055)*math.sin(math.pi*t)*math.sin(math.pi*t+phase[0])
        taper = (.055 if trim else .025)*(1+.65*math.sin(t*5+phase[1]))
        hw = max(half_w*.55, half_w-abs(bend)-taper)
        hd = half_d-(.015 if trim else .008)*(1+math.sin(t*6+phase[2]))
        depth_bow = (.045 if trim else .025)*math.sin(math.pi*t)**2
        points, normals = [], []
        for corner, (sx, sy, start) in enumerate(((1,1,0),(-1,1,90),(-1,-1,180),(1,-1,270))):
            loss = sum(max(0., 1-abs(t-at)/.035)*(.28 if trim else .065)
                       for at, k in chips if k == corner)
            rx = min(hw*.65, (.42 if trim else .085)*(1+.20*math.sin(t*7+phase[corner]))+loss)
            ry = min(hd*.75, (.24 if trim else .07)+loss*.35)
            for step in range(3):
                angle = math.radians(start+step*45)
                cs, sn = math.cos(angle), math.sin(angle)
                q = np.zeros(3)
                q[width] = sx*(hw-rx)+rx*cs+bend
                q[depth] = sy*(hd-ry)+ry*sn-depth_bow
                # Small, unequal end losses avoid the perfectly square sawn base.
                end_loss = (.12 if trim else .07)*(1+.7*math.sin(corner*1.7+phase[0]))
                q[grain] = (t-.5)*length + end_loss*(1-t)**10 - .045*t**10
                points.append(q)
                n = np.zeros(3); n[width] = cs/max(rx, .001); n[depth] = sn/max(ry, .001)
                normals.append(n/np.linalg.norm(n))
        rings.append(points); cross_normals.append(normals)
    u0, u1 = F.STRIPS[seed % len(F.STRIPS)]
    v0 = (seed*.61803398875) % 1

    def emit(points, normal, normals=None, end=False):
        # Project narrow returns across their thickness: using board width on
        # an edge collapses every UV to one column and smears the timber grain.
        cross = width if end or abs(normal[depth]) >= abs(normal[width]) else depth
        uv = [(u0+(q[cross]/size[cross]+.5)*(u1-u0),
               (q[depth] if end else q[grain])/F.TILE+v0) for q in points]
        F.face(model, paint, [centre+q@axes for q in points], normal@axes, uv,
               [n@axes for n in normals] if normals is not None else None)

    for row in range(len(rings)-1):
        for k in range(12):
            j = (k+1) % 12
            points = [rings[row][k], rings[row][j], rings[row+1][j], rings[row+1][k]]
            normals = [cross_normals[row][k], cross_normals[row][j], cross_normals[row+1][j], cross_normals[row+1][k]]
            emit(points, sum(normals), normals)
    for row, sign in ((0,-1),(-1,1)):
        n = np.zeros(3); n[grain] = sign
        emit(rings[row], n, end=True)
