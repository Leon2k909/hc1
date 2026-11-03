"""Ridged, eroded valley terrain for Spillway's visual backdrop only."""
import math
import numpy as np
from scipy.ndimage import map_coordinates
import riverdale_parts as P
import spillway_waterfalls as WATERFALLS


def terrain(model, rng):
    # Dense near slopes and irregular peaks replace the smooth concentric hills.
    angles = np.linspace(0, 2 * math.pi, 576, endpoint=False)
    radii = np.concatenate((np.linspace(3600, 24000, 52), np.geomspace(24750, 85000, 40)))
    rr, aa = np.meshgrid(radii, angles, indexing="ij")
    e, n = rr * np.sin(aa), rr * np.cos(aa)
    def noise(scale, seed):
        field = np.random.default_rng(seed).random((160, 160))
        return map_coordinates(field, [(n / scale + 64).ravel(), (e / scale + 64).ravel()], order=3, mode="wrap").reshape(e.shape)
    broad = noise(5700, 811)
    mid = noise(1900, 812)
    fine = noise(520, 813)
    micro = noise(160, 814)
    inner = np.clip((rr - 3600) / 6000, 0, 1)
    h = 80 + inner * (420 + broad * 900)
    # Several overlapping massifs, with distinct saddles and an open river valley.
    peaks = [(15000, 19000, 7400, 11500, 14000), (27000, 31000, 10300, 16000, 13500),
             (44000, 17000, 12100, 17000, 14500), (-21000, 25000, 7300, 13000, 17500),
             (-39000, 16000, 9100, 18000, 15500), (5000, 48000, 9000, 21000, 13000),
             (23000, -20000, 7000, 14000, 14000), (-21000, -23000, 7600, 16000, 14500),
             (2000, -44000, 9000, 21000, 14000)]
    massif = np.zeros_like(e)
    for x, y, height, sx, sy in peaks:
        dx = (e - x + (mid - .5) * 2000) / sx
        dy = (n - y + (broad - .5) * 2400) / sy
        peak = height * np.exp(-(dx * dx + dy * dy) * 1.5)
        massif = np.maximum(massif, peak)
    # Ridge networks carve valleys; variation remains strongest on high slopes.
    ridge = 1 - np.abs(mid * 2 - 1)
    gullies = np.abs(noise(900, 815) * 2 - 1)
    detail = (ridge - .48) * 1050 - gullies * 350 + (fine - .5) * 240 + (micro - .5) * 70
    h += (massif + detail * np.clip(massif / 2800, 0, 1)) * inner
    # The dam's abutments stay embedded in the valley; no terrain crosses the play space.
    h = np.maximum(50, h)
    h = WATERFALLS.carve_basin(e, n, h)
    dr = np.gradient(h, radii, axis=0)
    da = (np.roll(h, -1, axis=1) - np.roll(h, 1, axis=1)) / (2 * (angles[1] - angles[0]))
    de = dr * np.sin(aa) + da * np.cos(aa) / rr
    dn = dr * np.cos(aa) - da * np.sin(aa) / rr
    normals = np.stack((-de, -dn, np.ones_like(h)), axis=-1)
    normals /= np.linalg.norm(normals, axis=-1, keepdims=True)
    points = np.stack((e, n, h), axis=-1)
    for i in range(len(radii) - 1):
        for j in range(len(angles)):
            j1 = (j + 1) % len(angles)
            ids = ((i, j), (i, j1), (i + 1, j1), (i + 1, j))
            paint = "rv_forest" if (h[i, j] < 2300 and radii[i] < 23000) else "rv_rock"
            for tri in ((0, 1, 2), (0, 2, 3)):
                ps = [points[ids[k]] for k in tri]
                ns = [normals[ids[k]] for k in tri]
                normal = P.unit(np.cross(ps[1] - ps[0], ps[2] - ps[0]))
                if normal[2] < 0:
                    ps = ps[::-1]; ns = ns[::-1]; normal = -normal
                P.card(model, paint, ps, normal, normals=ns)
    close_shoreline(model, points[0], normals[0])
    return radii, angles, h


def close_shoreline(model, rim_points, rim_normals):
    """Connect the visual terrain's open 3600-inch rim to a submerged bank.

    Leave the accepted terrain and forest positions intact. The lower edge is
    below the -245 river plane, outside the playable enclosure, and render-only.
    """
    rim_points=np.asarray(rim_points,float)
    rim_normals=np.asarray(rim_normals,float)
    radius=np.linalg.norm(rim_points[:,:2],axis=1)
    radial=rim_points[:,:2]/radius[:,None]
    angle=np.arctan2(radial[:,0],radial[:,1])
    inner=3180+55*np.sin(angle*7)+30*np.sin(angle*13+.8)
    rings=[]; normals=[]
    for t in np.linspace(0,1,7):
        r=inner+(radius-inner)*t
        z=-560+(rim_points[:,2]+560)*(2*t-t*t)
        slope=2*(rim_points[:,2]+560)*(1-t)/(radius-inner)
        normal=np.column_stack((-radial*slope[:,None],np.ones(len(radius))))
        normal/=np.linalg.norm(normal,axis=1)[:,None]
        rings.append(np.column_stack((radial*r[:,None],z)))
        normals.append(normal)
    # Exact seam positions and normals, including the existing waterfall carve.
    rings[-1]=rim_points.copy(); normals[-1]=rim_normals.copy()
    for i in range(len(rings)-1):
        for j in range(len(radius)):
            j1=(j+1)%len(radius)
            points=[rings[i][j],rings[i][j1],rings[i+1][j1],rings[i+1][j]]
            ns=[normals[i][j],normals[i][j1],normals[i+1][j1],normals[i+1][j]]
            P.card(model,"rv_forest",points,(0,0,1),normals=ns)
