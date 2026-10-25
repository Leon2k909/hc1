"""Fountain bell: continuous cast profile, hollow shell and dedicated bronze.

Plan inches; the original position, yoke and surrounding masonry are retained.
No collision or scene objects are added. Material output can be staged elsewhere.
"""
import math
from pathlib import Path

import numpy as np
from PIL import Image, ImageFilter

import map_kit as K
import belltower_detail as D

BRONZE = "bell_bronze_v2"
INNER = "bell_inner_v2"
RESOURCE = "materials/belltower/bell-v2"
MATERIALS = {name: f"{RESOURCE}/{name}.vmat" for name in (BRONZE, INNER)}


def materials(folder=None):
    folder = Path(folder) if folder else K.ASSETS / RESOURCE
    folder.mkdir(parents=True, exist_ok=True)
    rng = np.random.default_rng(210926)
    size = 1024
    y, x = np.mgrid[:size, :size] / size
    raw = rng.integers(0, 256, (size, size), dtype=np.uint8)
    blur = np.asarray(Image.fromarray(raw).filter(ImageFilter.GaussianBlur(6)), float)
    broad = (blur - blur.mean()) / max(blur.std(), .01)
    fine = (raw.astype(float) - 127.5) / 127.5
    cast = .6*np.sin(2*math.pi*(x*17 + y*4)) + .35*np.sin(2*math.pi*(x*39-y*9))
    # Quiet bronze oxidation; no large high-contrast checkerboard patches.
    patina = np.clip(.045 + .025*broad + .015*np.sin(2*math.pi*(x*3+y)), 0, .12)
    colour = np.array((136., 104., 65.))[None, None, :] + (broad*2.0 + fine*1.1 + cast*.7)[..., None]
    colour = colour*(1-patina[..., None]) + np.array((64., 76., 66.))*patina[..., None]
    rough = np.clip(144 + broad*3 + fine*2 + patina*65, 132, 164)
    # Cast microstructure in tangent space, subtle enough to retain broad highlights.
    normal = np.stack((128 + fine*1.4, 128 + cast*.6, np.full_like(x, 255)), axis=-1)
    for name, data in (("bronze_color", colour), ("bronze_normal", normal), ("bronze_rough", rough)):
        if data.ndim == 2:
            data = np.repeat(data[..., None], 3, axis=2)
        Image.fromarray(np.clip(data, 0, 255).astype(np.uint8)).save(folder / f"{name}.png")
    for paint, tint, exponent in ((BRONZE, "1.0 1.0 1.0 1.0", "1"), (INNER, ".62 .65 .66 1.0", ".8")):
        text = ('// Tools/belltower_bell.py: dedicated fountain bell only\n"Layer0"\n{\n'
                '    shader "shaders/complex.shader"\n    F_SPECULAR "1"\n'
                f'    g_flRoughnessScaleFactor "{exponent}"\n    g_flMetalness "1.0"\n'
                f'    TextureColor "{RESOURCE}/bronze_color.png"\n'
                f'    TextureNormal "{RESOURCE}/bronze_normal.png"\n'
                f'    TextureRoughness "{RESOURCE}/bronze_rough.png"\n'
                '    TextureAmbientOcclusion "materials/default/default_ao.tga"\n'
                f'    g_vColorTint "[{tint}]"\n    g_flModelTintAmount "1.0"\n}}\n')
        K.write_text(folder / f"{paint}.vmat", text)


def smooth_profile(knots, subdivisions=3):
    """Monotone cubic interpolation avoids a cone made of broad flat strips."""
    z, r = np.asarray(knots, float).T
    delta = np.diff(r) / np.diff(z)
    slopes = np.zeros(len(z))
    slopes[0], slopes[-1] = delta[0], delta[-1]
    for i in range(1, len(z)-1):
        if delta[i-1]*delta[i] > 0:
            slopes[i] = 2/(1/delta[i-1] + 1/delta[i])
    result = []
    for i in range(len(z)-1):
        dz = z[i+1]-z[i]
        for t in np.linspace(0, 1, subdivisions, endpoint=False):
            radius = ((2*t**3-3*t*t+1)*r[i] + (t**3-2*t*t+t)*dz*slopes[i]
                      + (-2*t**3+3*t*t)*r[i+1] + (t**3-t*t)*dz*slopes[i+1])
            result.append((radius, z[i]+t*dz))
    result.append((r[-1], z[-1]))
    return result


def shell(model, centre):
    outer = smooth_profile([
        (141,13), (141.25,13.18), (141.65,13.26), (142.1,13.22),
        (142.7,13.02), (143.7,12.63), (145.3,11.85), (147.2,10.96),
        (149.5,10.12), (152.7,9.24), (156.5,8.36), (160.2,7.67),
        (163.8,7.13), (166.2,6.76), (168.4,6.22), (170.2,5.34),
        (171.5,4.22), (172.5,2.92), (173.2,1.55), (173.5,.35)])
    inner = smooth_profile([(141,11.62), (142.4,11.42), (144.2,10.65),
        (147.2,9.35), (151,8.14), (156,6.98), (161,6.03),
        (166,4.98), (169,3.01), (170,.3)])
    profile = outer + list(reversed(inner))
    count, sides = len(profile), 128
    e, n = centre
    for j in range(count):
        jj = (j+1) % count
        paint = INNER if j >= len(outer) else BRONZE
        def vertex(i, k):
            radius, z = profile[i]
            azimuth = 2*math.pi*k/sides
            dr = profile[(i+1)%count][0]-profile[(i-1)%count][0]
            dz = profile[(i+1)%count][1]-profile[(i-1)%count][1]
            normal = K.normalise((math.cos(azimuth)*dz, math.sin(azimuth)*dz, -dr))
            return (np.array((e+radius*math.cos(azimuth), n+radius*math.sin(azimuth), z)),
                    normal, (k/sides, (z-136)/40))
        for k in range(sides):
            entries = [vertex(j,k), vertex(j,k+1), vertex(jj,k+1), vertex(jj,k)]
            pts, normals, uv = map(list, zip(*entries))
            D.outward(model, paint, pts, sum(normals), normals=normals, uv=uv)


def ring(model, centre, u, v, a, b, thickness, paint=BRONZE, segments=96):
    """A continuous oval casting with per-vertex normals, not joined pentagonal rods."""
    c, u, v = map(lambda q: np.asarray(q, float), (centre, u, v))
    cross = np.cross(u, v)
    def vertex(i, j):
        t, p = 2*math.pi*i/segments, 2*math.pi*j/12
        radial = K.normalise(math.cos(t)*u/a + math.sin(t)*v/b)
        normal = math.cos(p)*radial + math.sin(p)*cross
        point = c + a*math.cos(t)*u + b*math.sin(t)*v + thickness*normal
        return point, normal, (i/segments, j/12)
    for i in range(segments):
        for j in range(12):
            entries = [vertex(i,j),vertex(i+1,j),vertex(i+1,j+1),vertex(i,j+1)]
            pts, normals, uv = map(list, zip(*entries))
            D.outward(model, paint, pts, sum(normals), normals=normals, uv=uv)


def build(model, centre):
    model.material_overrides.update(MATERIALS)
    model.tile_overrides.update({BRONZE: 32, INNER: 32})
    model.material_overrides["iron_black"] = "materials/buildings/iron_black.vmat"
    e, n = centre
    shell(model, centre)
    # Restrained cast beads integrated with the curved waist and shoulder.
    ring(model, (e,n,146.7), (1,0,0), (0,1,0), 11.18,11.18,.16)
    ring(model, (e,n,165.8), (1,0,0), (0,1,0), 6.83,6.83,.14)
    for offset in (-2.6,2.6):
        ring(model, (e+offset,n,177), (1,0,0), (0,0,1), 2.55,3.65,.78, segments=64)
    D.rod(model,(e,n,179.5),(e,n,190),1.18,"iron_black",sides=32)
    D.rod(model,(e,n,138.9),(e,n,168),.62,"iron_black",sides=24)
    D.ball(model,(e,n,139.4),1.85,INNER,rings=12,segments=32)


def legacy(model, centre):
    """Exact previous render geometry, for surgical face matching only."""
    e, n = centre
    D.lathe(model,centre,141,[(13,0),(13,2),(11.5,3),(9,9),(7.5,22),(6.5,28),(3,32),(1.6,33)],
            "fountain_bronze",sides=32,caps=(False,True))
    D.lathe(model,centre,141,[(11.7,0),(10.5,3),(8,9)],"fountain_bronze",sides=32)
    for z,r in ((143,12),(148,10),(165,7.5)):
        D.hoop(model,(e,n,z),(1,0,0),(0,1,0),r,.5,"fountain_bronze",segments=32)
    D.rod(model,(e,n,139),(e,n,169),.8,"iron_black")
    D.ball(model,(e,n,139),2.1,"fountain_bronze")
    for offset in (-3,3):
        D.hoop(model,(e+offset,n,179),(1,0,0),(0,0,1),4.5,.8,"fountain_bronze",segments=16)
    D.rod(model,(e,n,180),(e,n,190),1.5,"iron_black")
