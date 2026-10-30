"""Authored branching shrubs for the retaining-wall strip, seed 812 only.

Plan coordinates are inches. This asset is decoration; it adds no collision,
lights, scene objects, callbacks or shader animation.
"""
import math
import json
from pathlib import Path

import numpy as np
from PIL import Image
from scipy.ndimage import gaussian_filter

import riverdale_parts as P

UP = np.array((0., 0., 1.))
SOURCE = Path(__file__).resolve().parents[1]/'Sources/Veridant/planter-shrub-v1/beech-source.json'
RESOURCE = 'materials/veridant/shrub-volume-v1'
NAMES = ('leaf', 'leaf_light', 'leaf_back', 'stem', 'wood', 'flower', 'calyx', 'soil', 'edging')
MATERIALS = {f'vr_wall_herb_{n}': f'{RESOURCE}/{n}.vmat' for n in NAMES}
MATERIALS['vr_wall_herb_leaf'] = 'models/sbox_props/shrubs/beech/beech_shrub.vmat'


def shrub(model, foot, height, seed):
    """Use the installed shrub's authored branching, leaf UVs and bent surfaces.

    The legacy call's kind is rosemary; this close border now uses the same
    broadleaf planting palette as the reviewed garden planter. Uniform scaling
    preserves leaf proportions. Each crown is rotated and varied as a whole.
    """
    record = json.loads(SOURCE.read_text())
    assert record['Material'] == MATERIALS['vr_wall_herb_leaf']
    rng = np.random.default_rng(seed)
    angle = rng.uniform(0., math.tau); c, s = math.cos(angle), math.sin(angle)
    rotation = np.array(((c,-s,0.),(s,c,0.),(0.,0.,1.)))
    vertices = np.array([v['Position'] for v in record['Vertices']])
    source_top = vertices[:,2].max()
    source_root = .85
    scale = (height+.40)/(source_top-source_root)
    vertices = (vertices@rotation.T)*scale
    normals = np.array([v['Normal'] for v in record['Vertices']])@rotation.T
    vertices = np.column_stack((-vertices[:,1],vertices[:,0],vertices[:,2]))
    normals = np.column_stack((-normals[:,1],normals[:,0],normals[:,2]))
    vertices += np.array(foot)+np.array((0.,0.,-.40-source_root*scale))
    uv = np.array([(v['UV'][0],1-v['UV'][1]) for v in record['Vertices']])
    for ids in np.array(record['Indices']).reshape(-1,3):
        model.polygon('vr_wall_herb_leaf',vertices[ids],normals=normals[ids],uv=uv[ids])
    return {'root_clumps':1,'leaf_pairs':0,'shoots':0,'flowers':0}


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
    for plant, n in enumerate(np.linspace(74., 140.5, 10)):
        foot = (746.4+rng.uniform(-.85, .85), n+rng.uniform(-.50, .50), z+.12)
        height = h*rng.uniform(.72, .88)
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
