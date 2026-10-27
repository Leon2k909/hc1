"""Authored native tree and grounded planting for the grand-stair planter."""
import math
from pathlib import Path
import numpy as np
from PIL import Image
from scipy.ndimage import gaussian_filter
import riverdale_parts as P

UP = np.array((0., 0., 1.))
RESOURCE = 'materials/veridant/courtyard-olive-v2'
NAMES = ('twig', 'soil', 'mulch', 'herb', 'herb_back')
MATERIALS = {f'vr_courtyard_olive_{name}': f'{RESOURCE}/{name}.vmat' for name in NAMES}


def register(model):
    model.material_overrides.update(MATERIALS)
    model.tile_overrides.update({paint: 16. for paint in MATERIALS})


def tube(model, path, radii, paint, sides=9, phase=0., gnarl=0.):
    """Transported elliptical sections, tapered through natural branch forks."""
    path = np.asarray(path); rings = []; ns = []; travelled = [0.]
    for a, b in zip(path, path[1:]): travelled.append(travelled[-1] + np.linalg.norm(b-a))
    tangent = P.unit(path[1]-path[0]); u, _ = P.perp(tangent)
    for j, (p, r) in enumerate(zip(path, radii)):
        tangent = P.unit(path[min(j+1, len(path)-1)]-path[max(j-1, 0)])
        u = P.unit(u - tangent*np.dot(u, tangent)); w = np.cross(tangent, u)
        dirs = []; vertices = []
        for i in range(sides):
            a = i*math.tau/sides
            radial = u*math.cos(a)+w*math.sin(a)
            modulation = 1+gnarl*(.64*math.sin(a*3+phase+j*.16)+.36*math.sin(a*5-phase+j*.11))
            vertices.append(p+radial*r*modulation)
            dirs.append(radial)
        rings.append(vertices); ns.append(dirs)
    for j in range(len(path)-1):
        for i in range(sides):
            k = (i+1) % sides
            uv = [(i/sides, travelled[j]/20), ((i+1)/sides, travelled[j]/20),
                  ((i+1)/sides, travelled[j+1]/20), (i/sides, travelled[j+1]/20)]
            P.card(model, paint, [rings[j][i], rings[j][k], rings[j+1][k], rings[j+1][i]],
                   ns[j][i]+ns[j][k], normals=[ns[j][i], ns[j][k], ns[j+1][k], ns[j+1][i]], uv=uv)
    P.card(model, paint, rings[-1], path[-1]-path[-2])


def curve(a, b, bend, samples):
    return np.asarray([a+(b-a)*t+bend*math.sin(math.pi*t) for t in np.linspace(0, 1, samples)])


def leaf(model, base, direction, normal, length, width, phase, herb=False):
    """Lanceolate outline, raised midrib and curled tip, with smooth normals."""
    a = P.unit(direction); side = P.unit(np.cross(normal, a)); n = np.cross(a, side)
    points = [np.asarray(base)]; uv = [(.5, 1.)]
    rows = (.22, .59, .83)
    for t in rows:
        half = width*.5*math.sin(math.pi*t)**.73
        for s in (-1, 0, 1):
            p = (base+a*(t*length)+side*(s*half*(1+.035*math.sin(phase+t*8+s)))
                 +n*(length*(.028*math.sin(math.pi*t)*(1-abs(s))-.048*abs(s)*math.sin(math.pi*t)+.065*t*t)))
            points.append(p); uv.append(((s+1)/2, 1-t))
    tip = len(points); points.append(base+a*length+n*length*.065); uv.append((.5, 0.))
    faces = [(0, 1, 2), (0, 2, 3), (1, 4, 5, 2), (2, 5, 6, 3),
             (4, 7, 8, 5), (5, 8, 9, 6), (7, tip, 8), (8, tip, 9)]
    normals = np.zeros((len(points), 3))
    for f in faces:
        for j in range(1, len(f)-1):
            ids = [f[0], f[j], f[j+1]]
            x, y, z = (points[i] for i in ids)
            normals[ids] += np.cross(y-x, z-x)
    normals /= np.linalg.norm(normals, axis=1)[:, None]
    top = 'herb' if herb else ('leaf_light' if math.sin(phase*1.31) > .57 else 'leaf')
    back = 'herb_back' if herb else 'leaf_back'
    # Mesh winding follows the constructed surface; opposite side has real
    # reversed normals, so neither side inherits a dark card-plane normal.
    for f in faces:
        P.card(model, 'vr_courtyard_olive_'+top, [points[i] for i in f], n,
               normals=[normals[i] for i in f], uv=[uv[i] for i in f])
        rev = f[::-1]
        P.card(model, 'vr_courtyard_olive_'+back, [points[i] for i in rev], -n,
               normals=[-normals[i] for i in rev], uv=[uv[i] for i in rev])


TREE_MODEL = 'models/sbox_props/trees/oak/tree_oak_small_a.vmdl'
TREE_PACKAGE = 'facepunch.tree_oak_small_a#288917'
TREE_SCALE = .45
TREE_YAW = 24.


def build_tree(model, base=(272., 239., 42.), h=180., seed=11):
    # The tree is a native scene model so all five authored LODs and its
    # foliage shader remain intact. The generator adds it in scene_object().
    return {'native_model': TREE_MODEL, 'native_lods': 5, 'scale': TREE_SCALE,
            'high_detail_triangles': 6092}


def scene_object(ids):
    import map_kit as K
    key = 'courtyard-authored-tree'
    return K.game_object(ids, 'Courtyard planter tree', key,
        K.to_world((272., 239., 42.)), K.yaw_rotation(TREE_YAW),
        scale=K.vec((TREE_SCALE, TREE_SCALE, TREE_SCALE)),
        components=[K.component(ids, 'Sandbox.ModelRenderer', key+'/renderer',
            Model=TREE_MODEL, Tint='1,1,1,1')])


def build_planting(model, bounds=(220., 316., 202., 276.), z=42., seed=12):
    register(model); rng = np.random.default_rng(seed); a, b, c, d = bounds
    soil = 'vr_courtyard_olive_soil'; mulch = 'vr_courtyard_olive_mulch'
    def height(e, n):
        return z+.10+.38*math.exp(-((e-272)**2+(n-239)**2)/380)+.06*math.sin(e*.42)*math.cos(n*.49)
    for e0, e1 in zip(np.linspace(a+6.05, b-6.05, 19)[:-1], np.linspace(a+6.05, b-6.05, 19)[1:]):
        for n0, n1 in zip(np.linspace(c+6.05, d-6.05, 15)[:-1], np.linspace(c+6.05, d-6.05, 15)[1:]):
            points = [np.array((e, n, height(e, n))) for e, n in ((e0, n0), (e1, n0), (e1, n1), (e0, n1))]
            P.card(model, soil, points, UP, uv=[((p[0]-a)/20, (p[1]-c)/20) for p in points])
    for i in range(75):
        e, n = rng.uniform(a+7.5, b-7.5), rng.uniform(c+7.5, d-7.5)
        if np.linalg.norm(np.array((e-272, n-239))) < 6: continue
        angle = rng.uniform(0, math.tau); u = np.array((math.cos(angle), math.sin(angle), 0.))
        w = np.cross(UP, u); base = np.array((e, n, height(e, n)+.025))
        length = rng.uniform(.45, 1.25); width = rng.uniform(.12, .35)
        points = [base-u*length*.5-w*width*.3, base+u*length*.4-w*width*.5,
                  base+u*length*.5+w*width*.2, base-u*length*.4+w*width*.5]
        P.card(model, mulch, points, UP)
    # Three restrained rosemary clumps leave the tree's trunk and roots visible.
    herbs = 0
    for group, (e, n, size) in enumerate(((239., 223., 1.), (295., 220., .85), (295., 258., 1.05))):
        foot = np.array((e, n, height(e, n)-.25))
        for stem in range(15):
            angle = rng.uniform(0, math.tau); radial = np.array((math.cos(angle), math.sin(angle), 0.))
            start = foot+radial*rng.uniform(0, 2.4)
            axis = P.unit(radial*rng.uniform(.35, .85)+UP*rng.uniform(.6, 1.2))
            length = rng.uniform(7., 13.)*size; tip = start+axis*length
            tube(model, [start, start+axis*length*.5, tip], (.07, .045, .014),
                 'vr_courtyard_olive_twig', 5)
            cross = P.unit(np.cross(axis, UP))
            for j, f in enumerate(np.linspace(.23, .98, 8)):
                root = start+axis*length*f
                for sign in (-1, 1):
                    direction = P.unit(axis*.3+cross*sign*.8+UP*.1)
                    size_leaf = rng.uniform(.9, 1.6)
                    leaf(model, root, direction, UP, size_leaf, size_leaf*.16, stem*.7+j, herb=True)
                    herbs += 1
    return {'herb_leaves': herbs, 'herb_clumps': 3, 'soil_bounds': [a+6.05, b-6.05, c+6.05, d-6.05]}


def write_materials(folder):
    folder = Path(folder); folder.mkdir(parents=True, exist_ok=True)
    rng = np.random.default_rng(38119); n = 1024
    def noise(sigma):
        a = gaussian_filter(rng.normal(size=(n, n)), sigma, mode='wrap')
        return a/max(a.std(), 1e-8)
    def save_maps(name, rgb, height, rough, span=(1., 1.)):
        Image.fromarray(np.clip(rgb, 0, 255).astype('uint8')).save(folder/f'{name}_color.png')
        dy = (np.roll(height, -1, 0)-np.roll(height, 1, 0))/(2*span[1]/n)
        dx = (np.roll(height, -1, 1)-np.roll(height, 1, 1))/(2*span[0]/n)
        normal = np.stack((-dx, dy, np.ones_like(dx)), axis=-1)
        normal /= np.linalg.norm(normal, axis=-1)[..., None]
        Image.fromarray(np.clip((normal*.5+.5)*255, 0, 255).astype('uint8')).save(folder/f'{name}_normal.png')
        Image.fromarray(np.clip(rough*255, 0, 255).astype('uint8')).save(folder/f'{name}_rough.png')
    v, u = np.mgrid[:n, :n].astype(float); v /= n-1; u = u/(n-1)*2-1
    mid = np.exp(-(u/.035)**2); vein = np.zeros_like(u)
    for j in np.arange(.08, .95, .065): vein += np.exp(-((v-j-.36*np.abs(u))/.0055)**2)
    fine = noise(1.4); broad = noise(26)
    lum = .97+.045*np.sin(v*math.pi)+.014*fine+.025*vein+.022*mid+.015*broad
    height = .00065*mid+.00013*vein+.000035*fine
    save_maps('leaf', lum[..., None]*np.array((75., 94., 49.)), height, .51+.025*fine)
    save_maps('leaf_back', lum[..., None]*np.array((120., 132., 101.)), height*.6, .76+.02*fine)
    # Irregular, interlocking grey bark plates rather than black painted slashes.
    long = noise((48., 7.)); grain = noise((9., 1.3)); patch = noise(36.)
    fissure = np.clip((np.abs(long)-.70)*.8, 0, .65)
    h = .024*long+.009*grain-.10*fissure
    colour = ((1+.11*patch+.035*grain-.30*fissure)[..., None]*np.array((108., 106., 91.)))
    save_maps('bark', colour, h, .86+.035*grain, (26., 20.))
    clod = noise(3.); large = noise(24.); grit = noise(.6)
    save_maps('soil', (1+.12*large+.075*clod+.04*grit)[..., None]*np.array((65., 49., 33.)),
              .035*clod+.006*grit, .92+.02*clod, (20., 20.))
    for name in NAMES:
        foliage = name in ('leaf', 'leaf_light', 'leaf_back', 'herb', 'herb_back')
        family = ('leaf_back' if name in ('leaf_back', 'herb_back') else 'leaf') if foliage else ('soil' if name in ('soil', 'mulch') else 'bark')
        tint = {'leaf_light': (1.08, 1.10, .99), 'herb': (.70, .88, .83),
                'herb_back': (.85, .95, .90), 'twig': (.70, .66, .53), 'mulch': (1.24, 1.12, .94)}.get(name, (1, 1, 1))
        shader = 'foliage' if foliage else 'complex'
        feature = ('    F_ALPHA_TEST "0"\n    F_FOLIAGE_ANIMATION "0"\n    F_TRANSMISSIVE "1"\n'
                   '    g_flTransmissionScale "0.32"\n    g_flWrapStrength "0.12"\n'
                   '    g_flAmbientBoost "0"\n    g_flRimStrength "0"\n'
                   '    g_flNormalVariation "0"\n    g_flGrassNormalUp "0"\n'
                   '    TextureTransmissiveColor "[0.42 0.55 0.24 0]"\n') if foliage else '    F_SPECULAR "1"\n'
        text = ('// Tools/veridant_courtyard_olive.py\n"Layer0"\n{\n'
                f'    shader "shaders/{shader}.shader"\n'+feature+
                '    g_flRoughnessScaleFactor "1"\n    g_flMetalness "0"\n'
                f'    TextureColor "{RESOURCE}/{family}_color.png"\n'
                f'    TextureNormal "{RESOURCE}/{family}_normal.png"\n'
                f'    TextureRoughness "{RESOURCE}/{family}_rough.png"\n'
                '    TextureAmbientOcclusion "materials/default/default_ao.tga"\n'
                f'    g_vColorTint "[{tint[0]} {tint[1]} {tint[2]} 1]"\n    g_flModelTintAmount "1"\n}}\n')
        (folder/f'{name}.vmat').write_text(text)
