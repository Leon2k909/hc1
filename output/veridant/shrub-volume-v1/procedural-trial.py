"""Solid leaf geometry for the retaining-wall rosemary strip, seed 812 only.

Plan coordinates are inches. This asset is decoration; it adds no collision,
lights, scene objects, callbacks or shader animation.
"""
import math
from pathlib import Path

import numpy as np
from PIL import Image
from scipy.ndimage import gaussian_filter

import riverdale_parts as P

UP = np.array((0., 0., 1.))
RESOURCE = 'materials/veridant/shrub-volume-v1'
NAMES = ('leaf', 'leaf_light', 'leaf_back', 'stem', 'wood', 'flower', 'calyx', 'soil', 'edging')
MATERIALS = {f'vr_wall_herb_{n}': f'{RESOURCE}/{n}.vmat' for n in NAMES}


def blade(model, base, direction, normal, length, width, tone):
    """A pointed, folded needle with separate shaded upper and lower surfaces."""
    axis = P.unit(direction)
    across = P.unit(np.cross(normal, axis))
    normal = np.cross(axis, across)
    base = np.asarray(base)
    middle = base + axis*length*.44
    points = [base, middle-across*width*.5+normal*length*.012,
              middle+normal*length*.052,
              middle+across*width*.5+normal*length*.012,
              base+axis*length+normal*length*.09]
    coords = ((.5, 0.), (0., .44), (.5, .44), (1., .44), (.5, 1.))
    faces = ((0, 1, 2), (0, 2, 3), (1, 4, 2), (2, 4, 3))
    normals = np.zeros((5, 3))
    for face in faces:
        a, b, c = (points[i] for i in face)
        normals[list(face)] += np.cross(b-a, c-a)
    normals /= np.linalg.norm(normals, axis=1)[:, None]
    for face in faces:
        P.card(model, tone, [points[i] for i in face], normal,
               normals=[normals[i] for i in face], uv=[coords[i] for i in face])
        reverse = face[::-1]
        P.card(model, 'vr_wall_herb_leaf_back', [points[i] for i in reverse], -normal,
               normals=[-normals[i] for i in reverse], uv=[coords[i] for i in reverse])


def tube(model, path, radii, paint, sides=5):
    """Tapered wood with radial normals; no overlapping constant-radius rods."""
    rings = []
    normals = []
    for i, (point, radius) in enumerate(zip(path, radii)):
        tangent = P.unit(path[min(i+1, len(path)-1)]-path[max(0, i-1)])
        u, v = P.perp(tangent)
        ns = [u*math.cos(j*math.tau/sides)+v*math.sin(j*math.tau/sides) for j in range(sides)]
        rings.append([point+n*radius for n in ns]); normals.append(ns)
    for i in range(len(path)-1):
        for j in range(sides):
            k = (j+1) % sides
            P.card(model, paint, (rings[i][j], rings[i][k], rings[i+1][k], rings[i+1][j]),
                   normals[i][j]+normals[i][k],
                   normals=(normals[i][j], normals[i][k], normals[i+1][k], normals[i+1][j]))


def shrub(model, foot, height, seed):
    rng = np.random.default_rng(seed)
    stats = {'root_clumps': 1, 'leaf_pairs': 0, 'shoots': 0, 'flowers': 0}
    foot = np.array(foot, float)
    # Three old, woody forks form a connected base underneath the green shoots.
    forks = []
    for fork in range(3):
        angle = fork*math.tau/3+rng.uniform(-.25, .25)
        radial = np.array((math.cos(angle), math.sin(angle), 0.))
        fork_end = foot+radial*rng.uniform(1.8, 2.6)+UP*rng.uniform(2.1, 3.0)
        tube(model, [foot-UP*.33, foot+radial*.8+UP*.8, fork_end],
             (.31, .22, .12), 'vr_wall_herb_wood', 7)
        forks.append(fork_end)
    for stem in range(24):
        angle = stem*2.399963+rng.uniform(-.25, .25)
        radial = np.array((math.cos(angle), math.sin(angle), 0.))
        side = np.cross(UP, radial)
        # Outer shoots arch outward; central shoots remain taller.
        outer = (stem % 4)/3
        reach = rng.uniform(2.2, 4.8)+outer*1.35
        rise = height*rng.uniform(.69, 1.)*(1-.22*outer)
        root = forks[stem % 3]
        delta = radial*reach+UP*(rise-root[2]+foot[2])
        bend = side*rng.uniform(-.8, .8)+radial*.55
        def point(t):
            return root+delta*t+bend*math.sin(math.pi*t)
        path = [point(float(t)) for t in np.linspace(0., 1., 5)]
        tube(model, path, (.092, .074, .052, .029, .009), 'vr_wall_herb_stem')
        stats['shoots'] += 1
        for node, t in enumerate(np.linspace(.10, .97, 10)):
            axis = P.unit(delta+bend*math.pi*math.cos(math.pi*t))
            tangent = P.unit(np.cross(axis, UP))
            cross = np.cross(axis, tangent)
            # Opposite leaf pairs rotate around the stem as they ascend.
            phase = angle+node*.83
            lateral = tangent*math.cos(phase)+cross*math.sin(phase)
            for sign in (-1, 1):
                direction = P.unit(axis*rng.uniform(.32, .61)+lateral*sign)
                normal = P.unit(UP*.68+radial*.40+lateral*sign*.28)
                length = rng.uniform(.73, 1.24)*(1-.28*t)
                paint = 'vr_wall_herb_leaf_light' if (stem+node) % 7 == 0 else 'vr_wall_herb_leaf'
                blade(model, point(t), direction, normal, length, length*rng.uniform(.105, .145), paint)
            stats['leaf_pairs'] += 1
        # Restrained pale blue flowerlets grow at upper leaf axils, not a carpet.
        if stem % 5 == 0:
            for j, t in enumerate((.71, .82, .91)):
                normal = P.unit(radial+UP*.35)
                centre = point(t)+radial*.20
                u, v = P.perp(normal)
                P.rod(model, point(t), centre, .035, 'vr_wall_herb_calyx', 5)
                for petal in range(4):
                    a = petal*math.tau/4+j*.43
                    direction = u*math.cos(a)+v*math.sin(a)
                    points = (centre, centre+direction*.13+u*.07+normal*.07,
                              centre+direction*.25+normal*.14,
                              centre+direction*.13-u*.07+normal*.07)
                    P.card(model, 'vr_wall_herb_flower', points, normal, both=True)
                stats['flowers'] += 1
    return stats


def build_into(model, lo=(740., 34.), hi=(753., 148.), z=0., seed=812,
               kind='rosemary', h=25., count=10, section=None):
    assert tuple(lo) == (740., 34.) and tuple(hi) == (753., 148.)
    assert seed == 812 and kind == 'rosemary' and h == 25. and count == 10
    assert section in (None, 0, 1)
    model.material_overrides.update(MATERIALS)
    model.tile_overrides.update({p: 8. for p in MATERIALS})
    stats = {'root_clumps': 0, 'leaf_pairs': 0, 'shoots': 0, 'flowers': 0}
    # The original planting occupied N=65..150, with no actual soil. Keep the
    # replacement in that envelope and expose a shallow, physically defined bed.
    if section in (None, 0):
        e0, e1, n0, n1 = 739.2, 754.2, 65.3, 149.5
        for e0i, e1i in zip(np.linspace(e0+.35, e1-.35, 7)[:-1], np.linspace(e0+.35, e1-.35, 7)[1:]):
            for n0i, n1i in zip(np.linspace(n0+.35, n1-.35, 25)[:-1], np.linspace(n0+.35, n1-.35, 25)[1:]):
                pts = [np.array((e, n, z+.23+.055*math.sin(e*1.71+n*1.17)))
                       for e, n in ((e0i, n0i), (e1i, n0i), (e1i, n1i), (e0i, n1i))]
                P.card(model, 'vr_wall_herb_soil', pts, UP,
                       uv=[((p[0]-e0)/9, (p[1]-n0)/9) for p in pts])
        for a, b, c, d in ((e0, e0+.34, n0, n1), (e1-.34, e1, n0, n1),
                            (e0+.34, e1-.34, n0, n0+.34), (e0+.34, e1-.34, n1-.34, n1)):
            P.bevel_box(model, np.array(((a+b)/2, (c+d)/2, z+.28)),
                        (np.array((1.,0.,0.)), np.array((0.,1.,0.)), UP),
                        (b-a, d-c, .8), 'vr_wall_herb_edging', bevel=.075)
    rng = np.random.default_rng(seed)
    for plant, n in enumerate(np.linspace(71., 144., 10)):
        foot = (746.4+rng.uniform(-.85, .85), n+rng.uniform(-.50, .50), z+.12)
        height = h*rng.uniform(.77, 1.)
        if section is not None and plant//5 != section:
            continue
        result = shrub(model, foot, height, seed*100+plant)
        for key in stats: stats[key] += result[key]
    return stats


def write_materials(directory):
    out = Path(directory); out.mkdir(parents=True, exist_ok=True)
    rng = np.random.default_rng(812372); n = 512
    def noise(sigma):
        a = gaussian_filter(rng.normal(size=(n,n)), sigma, mode='wrap')
        return a/max(a.std(), 1e-8)
    fine = noise(1.1); patch = noise(24.)
    y, x = np.mgrid[:n, :n].astype(float); x = x/(n-1)*2-1; y /= n-1
    midrib = np.exp(-(x/.055)**2)
    leaf_colour = (1+.027*fine+.040*patch+.05*midrib)[...,None]*np.array((94., 118., 76.))
    Image.fromarray(np.clip(leaf_colour, 0, 255).astype('uint8')).save(out/'leaf_color.png')
    Image.fromarray(np.clip((.61+.025*fine)*255,0,255).astype('uint8')).save(out/'leaf_rough.png')
    Image.new('RGB',(16,16),(128,128,255)).save(out/'flat_normal.png')
    soil = noise(2.); grit = noise(.6)
    rgb = (1+.09*patch+.08*soil+.045*grit)[...,None]*np.array((55., 43., 29.))
    Image.fromarray(np.clip(rgb,0,255).astype('uint8')).save(out/'soil_color.png')
    field = .025*soil+.004*grit
    dy = (np.roll(field,-1,0)-np.roll(field,1,0))/(18/n)
    dx = (np.roll(field,-1,1)-np.roll(field,1,1))/(18/n)
    normal = np.stack((-dx,dy,np.ones_like(dx)),axis=-1)
    normal /= np.linalg.norm(normal,axis=-1)[...,None]
    Image.fromarray(np.clip((normal*.5+.5)*255,0,255).astype('uint8')).save(out/'soil_normal.png')
    colours = {'leaf': (1,1,1), 'leaf_light': (1.10,1.09,.95),
               'leaf_back': (1.28,1.20,1.13), 'stem': (.29,.34,.17),
               'wood': (.24,.20,.14), 'flower': (.47,.45,.64),
               'calyx': (.26,.31,.18), 'soil': (1,1,1), 'edging': (.13,.14,.12)}
    for name in NAMES:
        foliage = name.startswith('leaf')
        colour = f'{RESOURCE}/leaf_color.png' if foliage else f'{RESOURCE}/soil_color.png' if name=='soil' else 'materials/default/default_color.tga'
        normal = f'{RESOURCE}/soil_normal.png' if name=='soil' else f'{RESOURCE}/flat_normal.png'
        rough = f'{RESOURCE}/leaf_rough.png' if foliage else '[0.93 0.93 0.93 0]' if name=='soil' else '[0.76 0.76 0.76 0]'
        tint = colours[name]
        text = ('// Tools/veridant_wall_rosemary.py\n"Layer0"\n{\n'
                '    shader "shaders/complex.shader"\n    F_SPECULAR "1"\n'
                '    g_flMetalness "0"\n    g_flRoughnessScaleFactor "1"\n'
                f'    TextureColor "{colour}"\n    TextureNormal "{normal}"\n'
                f'    TextureRoughness "{rough}"\n'
                '    TextureAmbientOcclusion "materials/default/default_ao.tga"\n'
                f'    g_vColorTint "[{tint[0]} {tint[1]} {tint[2]} 1]"\n    g_flModelTintAmount "1"\n}}\n')
        (out/f'{name}.vmat').write_text(text)
