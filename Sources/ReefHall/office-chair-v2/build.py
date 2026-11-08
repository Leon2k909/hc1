"""Reef Hall office chair v2: office-chair-v1 made more realistic, as a standalone model (not placed in the map).

What v1 got wrong in its native capture (output/reefhall/office-chair-v1/runtime-review/chair-after.png):
- two thin rods floated behind the backrest; a task chair hangs its back on one curved spine from the tilt unit
- a flat slab of a back and a square seat; real cushions have a lumbar S-curve and a waterfall front edge
- boxy arms; real ones are a tapered upright with a soft, rounded pad
- flat-colour plastic and a coarse tiled pad; here the approved Collider chair's woven cloth, welt piping and grained
  polymer/steel/rubber maps (materials/collider/chair-realism-v2, at its own tile sizes)
v1 is kept as it was. Model space: origin on the floor under the gas lift, facing +X.
Run from the project root: python Sources/ReefHall/office-chair-v2/build.py
"""
from pathlib import Path
import sys, math, json
import numpy as np
ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / 'Tools'))
import map_kit as K
import riverdale_parts as G
import railhead_dress_detail as D

RES = 'models/maps/reefhall/office-chair-v2'
SHARED = 'materials/collider/chair-realism-v2'
TILES = dict(cloth=6., welt=6., polymer=6., alloy=8., rubber=4., steel=5.)
m = K.Model()
X = np.array((0., -1., 0.)); Y = np.array((1., 0., 0.)); Z = np.array((0., 0., 1.))  # X: sideways, Y: forward


def P(x, y, z): return X * x + Y * y + Z * z
def box(c, size, paint, bevel=.12): G.bevel_box(m, P(*c), (X, Y, Z), size, paint, bevel=bevel)
def cyl(c, axis, prof, paint, sides=24): G.lathe_axis(m, P(*c), axis, prof, paint, sides=sides)


def outline(w, d, r, steps=8):
    pts = []
    for cx, cy, a0 in ((w/2-r, d/2-r, 0), (-w/2+r, d/2-r, math.pi/2), (-w/2+r, -d/2+r, math.pi), (w/2-r, -d/2+r, 3*math.pi/2)):
        for a in np.linspace(a0, a0 + math.pi/2, steps + 1): pts.append((cx + r*math.cos(a), cy + r*math.sin(a)))
    return pts


def loft(rings, paint):
    n = len(rings[0]); vertices = [p for ring in rings for p in ring]; centres = [np.mean(r, axis=0) for r in rings]; tri = []
    for j in range(len(rings) - 1):
        for k in range(n):
            a = j*n+k; b = j*n+(k+1) % n; c = (j+1)*n+(k+1) % n; d = (j+1)*n+k
            hint = (vertices[a]+vertices[b]+vertices[c]+vertices[d])/4 - (centres[j]+centres[j+1])/2
            tri.extend(((a, b, c, hint), (a, c, d, hint)))
    for j, normal in ((0, centres[0]-centres[1]), (len(rings)-1, centres[-1]-centres[-2])):
        idx = len(vertices); vertices.append(centres[j])
        for k in range(n): tri.append((idx, j*n+k, j*n+(k+1) % n, normal))
    accum = [np.zeros(3) for _ in vertices]; faces = []
    for a, b, c, hint in tri:
        normal = K.normalise(np.cross(vertices[b]-vertices[a], vertices[c]-vertices[a]))
        if np.dot(normal, hint) < 0: normal = -normal
        for i in (a, b, c): accum[i] += normal
        faces.append((a, b, c, normal))
    for a, b, c, normal in faces:
        D._face(m, paint, [vertices[i] for i in (a, b, c)], normal, normals=[K.normalise(accum[i]) for i in (a, b, c)])


# Seat: crowned cushion whose front rolls down over a waterfall edge; welt piping round its crown.
def seat_ring(z, w, d, r, droop):
    return [P(x, y, z - droop * max(0., (y + d/2 - 0.6*d) / (0.4*d))**2) for x, y in outline(w, d, r)]
seat = [(15.6, 16.4, 15.0, 2.2, 0.), (16.2, 17.6, 16.4, 2.8, .6), (17.3, 18.2, 17.0, 3.0, 1.3), (18.4, 17.8, 16.6, 2.9, 1.6),
        (18.9, 16.6, 15.4, 2.4, 1.5)]
loft([seat_ring(z, w, d, r, dr) for z, w, d, r, dr in seat], 'cloth')
welt = seat_ring(18.45, 17.9, 16.7, 2.9, 1.6); G.tube(m, welt + [welt[0]], .10, 'welt', sides=8)
box((0, 0, 15.1), (15.6, 14.6, 1.0), 'polymer', .35)  # moulded seat pan under the cushion


# Back: S-curved (lumbar forward, shoulders back, wraps at the sides), padded front, polymer shell behind.
def back_y(x, z): return -8.6 + 1.3*(x/8.6)**2 + .9*math.exp(-((z-24.)/3.8)**2) - .05*(z-27.)
def back_ring(depth, w, h, r, z0=29.):
    return [P(x, back_y(x, z0+z) + depth, z0+z) for x, z in outline(w, h, r)]
loft([back_ring(d, w, h, r) for d, w, h, r in ((-1.9, 16.2, 17.6, 2.4), (-1.6, 17.4, 18.8, 2.9), (-1.1, 17.4, 18.8, 2.9))], 'polymer')
loft([back_ring(d, w, h, r) for d, w, h, r in ((-1.0, 16.8, 18.2, 2.6), (-.4, 17.4, 18.6, 2.9), (.55, 17.0, 18.2, 2.8), (.85, 15.8, 17.0, 2.4))], 'cloth')
bw = back_ring(-.15, 17.45, 18.7, 2.9); G.tube(m, bw + [bw[0]], .10, 'welt', sides=8)
# Horizontal lumbar seam: a sunken welt across the pad.
G.tube(m, [P(x, back_y(x, 24.3) + 1.0 - .02*abs(x)/8, 24.3) for x in np.linspace(-7.6, 7.6, 13)], .07, 'welt', sides=6)

# One curved spine carries the back from the tilt unit, bolted to the shell through a flared plate.
spine = [P(0, -2.0, 14.0), P(0, -6.5, 14.2), P(0, -9.9, 16.6), P(0, -11.2, 21.0), P(0, back_y(0, 25.) - 2.25, 25.)]
G.tube(m, spine, .62, 'polymer', sides=14, bend_radius=1.4)
box((0, back_y(0, 27.) - 2.05, 27.), (4.2, .45, 6.4), 'polymer', .2)
for dx in (-1.4, 1.4):
    for dz in (25.2, 28.8):
        cyl((dx, back_y(dx, dz) - 2.3, dz), -Y, [(0, 0), (.22, 0), (.22, .12), (0, .12)], 'steel', 12)

# Arms: forged bracket under the seat, tapered upright, soft rounded pad with a separate cover seam.
for s in (-1, 1):
    G.tube(m, [P(s*4.5, -1.0, 14.6), P(s*8.4, -1.0, 14.6), P(s*9.4, -1.0, 15.6)], .45, 'alloy', sides=12, bend_radius=.7)
    loft([[P(s*9.6 + x, y - .6, z) for x, y in outline(w, d, r, 5)] for z, w, d, r in
          ((15.3, 1.4, 2.6, .5), (19.5, 1.15, 2.1, .45), (23.6, 1.0, 1.9, .4))], 'polymer')
    loft([[P(s*9.9 + x, y - .2, z) for x, y in outline(w, d, r, 6)] for z, w, d, r in
          ((23.6, 2.3, 9.4, 1.0), (24.2, 3.0, 10.4, 1.4), (25.1, 3.1, 10.4, 1.5), (25.6, 2.5, 9.6, 1.2))], 'rubber')
    box((s*10.6, -.6, 21.8), (.08, .55, 1.6), 'steel', .02)  # height-release button

# Tilt unit with tension knob and paddle levers.
box((0, .2, 13.9), (6.0, 8.6, 2.0), 'polymer', .45)
cyl((0, 4.6, 13.5), Y, [(0, 0), (1.25, 0), (1.35, .3), (1.35, 1.9), (1.1, 2.2), (0, 2.2)], 'rubber', 24)
for s in (-1, 1):
    G.tube(m, [P(s*2.8, 1.5, 14.), P(s*6.4, 1.8, 13.6), P(s*8.2, 2.6, 13.4)], .14, 'steel', sides=10, bend_radius=.4)
    box((s*8.6, 2.9, 13.4), (1.6, 2.4, .5), 'polymer', .2)

# Chrome gas lift in a ribbed shroud.
cyl((0, 0, 6.2), Z, [(0, 0), (.66, 0), (.66, 7.0), (0, 7.0)], 'steel', 32)
cyl((0, 0, 3.6), Z, [(0, 0), (1.32, 0), (1.42, .3), (1.18, .7), (1.12, 4.6), (1.0, 4.9), (0, 4.9)], 'polymer', 32)
for z in (5.0, 5.9, 6.8, 7.7): G.torus(m, P(0, 0, z), Z, 1.16, .06, 'polymer', seg=32, sides=6)

# Polished alloy five-star base: tapered, crowned spokes on a hub, swivel casters with hooded twin wheels.
cyl((0, 0, 2.6), Z, [(0, 0), (2.4, 0), (2.55, .5), (2.3, 1.6), (1.5, 2.1), (0, 2.1)], 'alloy', 40)
for k in range(5):
    angle = math.tau*k/5 + .2; dx, dy = math.cos(angle), math.sin(angle)
    d = P(dx, dy, 0); side = np.cross(Z, d)
    rings = []
    for t, w, h, z in ((1.8, 1.9, 1.4, 4.0), (5.5, 1.5, 1.05, 3.4), (9.2, 1.15, .85, 2.75), (10.2, 1.0, .8, 2.65)):
        centre = d*t + Z*z
        rings.append([centre + side*(w/2*math.cos(a)) + Z*(h/2*math.sin(a)*(1.25 if math.sin(a) > 0 else .8))
                      for a in np.linspace(0, math.tau, 18, endpoint=False)])
    loft(rings, 'alloy')
    tip = d*9.9
    G.lathe_axis(m, tip + Z*1.85, Z, [(0, 0), (.3, 0), (.3, .9), (0, .9)], 'steel', sides=16)
    yaw = angle + .43 + .18*math.sin(k*3.); ax = np.array((math.cos(yaw), math.sin(yaw), 0)); out = np.cross(Z, ax)
    centre = tip + out*.5 + Z*1.35
    G.bevel_box(m, centre + Z*1.0, (ax, out, Z), (1.9, 1.5, .7), 'polymer', bevel=.22)
    for s in (-1, 1):
        q = centre + ax*s*.6
        G.lathe_axis(m, q, ax*s, [(0, 0), (1.12, 0), (1.34, .12), (1.36, .5), (1.2, .64), (0, .64)], 'rubber', sides=28)
        G.lathe_axis(m, q + ax*s*.65, ax*s, [(0, 0), (.55, 0), (.55, .06), (0, .06)], 'polymer', sides=24)

m.material_overrides = {p: f'{SHARED}/{p}.vmat' for p in TILES}
m.tile_overrides = dict(TILES)
count = K.write_model(ROOT / 'Assets' / RES, RES, 'office_chair', m)
print(json.dumps(dict(triangles=count, resource=RES + '/office_chair.vmdl')))
