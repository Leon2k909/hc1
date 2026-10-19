"""CPU geometry review for the window candidate when Blender cannot start.

Renders the exact exported OBJ, original albedo textures and geometric normals.
Directional shadows are rasterized from the same triangles. This is deliberately
labelled an offline construction preview: no engine glass, weathering or GI.
"""
import json
import math
from pathlib import Path

import numpy as np
from PIL import Image

import map_kit as K
import railhead_preview as PV
from lowtide_window_preview import OUT, ROOT

SUN = K.normalise((-.5, -.6, 1.))
VIEWS = {
    'oblique': dict(eye=(3., -7., 3.4), target=(0., 0., 2.75), scale=3.75, size=(1100, 1100)),
    'head': dict(eye=(1.8, -5., 4.1), target=(0., -.05, 3.35), scale=1.9, size=(1280, 900)),
    'joint': dict(eye=(1.5, -3., 2.9), target=(.17, -.08, 2.63), scale=.75, size=(1000, 1000)),
}


def unit(v):
    return v / np.maximum(np.linalg.norm(v, axis=-1, keepdims=True), 1e-12)


def read_obj(path):
    verts, uvs, norms, triangles, materials = [], [], [], [], []
    active = None
    for line in path.read_text().splitlines():
        f = line.split()
        if not f: continue
        if f[0] in ('v', 'vn'):
            x, y, z = map(float, f[1:])
            value = np.array((-x, z, y))
            (verts if f[0] == 'v' else norms).append(value)
        elif f[0] == 'vt': uvs.append(tuple(map(float, f[1:])))
        elif f[0] == 'usemtl': active = f[1]
        elif f[0] == 'f':
            refs = [tuple(int(v) - 1 for v in point.split('/')) for point in f[1:]]
            triangles.append([np.r_[verts[v], uvs[t], norms[n]] for v, t, n in refs])
            materials.append(active)
    return np.asarray(triangles), materials


def number_array(value, default):
    try: return np.array([float(v) for v in value.strip('[]').split()])
    except (ValueError, AttributeError): return np.array(default)


def materials():
    result = {}
    for paint, info in json.loads((OUT / 'materials.json').read_text()).items():
        p = info['inputs']
        if paint == 'rw_window_dark':
            result[paint] = dict(texture=np.array([[[.022, .041, .052]]], np.float32),
                                 scale=np.ones(2), rough=.28)
            continue
        color = p.get('TextureColor', '[.2 .2 .2]')
        file = ROOT / 'Assets' / color
        if file.exists():
            tex = np.asarray(Image.open(file).convert('RGB'), dtype=np.float32) / 255
            tex = np.where(tex <= .04045, tex / 12.92, ((tex + .055) / 1.055) ** 2.4)
        else:
            tex = number_array(color, [.2, .2, .2])[:3][None, None, :]
        tint = number_array(p.get('g_flTintColor'), [1, 1, 1])[:3]
        scale = number_array(p.get('g_vBrickScale'), [1, 1])[:2]
        if 'g_vEnamelTint' in p:
            tint = number_array(p['g_vEnamelTint'], [1, 1, 1])[:3] / .285
            scale = np.repeat(float(p['g_flEnamelScale']), 2)
        rough = float(number_array(p.get('TextureRoughness'), [.58])[0])
        result[paint] = dict(texture=(tex * tint).astype(np.float32), scale=scale, rough=rough)
    return result


def shadow_map(triangles):
    points = triangles[..., :3]
    right = K.normalise(np.cross(SUN, (0, 0, 1)))
    up = np.cross(SUN, right)
    flat = points.reshape(-1, 3)
    projected = np.column_stack((flat @ right, flat @ up))
    minimum = projected.min(axis=0) - 2
    span = projected.max(axis=0) - minimum + 2
    size = 2048
    screen = ((projected - minimum) / span * (size - 1)).reshape(-1, 3, 2)
    depth = np.full((size, size), -1e8, np.float32)
    dummy = np.zeros((size, size, 3), np.float32)
    PV.rasterise(dummy, depth, screen, points @ SUN, np.zeros((len(points), 3)))
    return depth, right, up, minimum, span


def sample_texture(texture, uv):
    height, width = texture.shape[:2]
    xy = np.column_stack((uv[:, 0] * width - .5, (1 - uv[:, 1]) * height - .5))
    base = np.floor(xy).astype(int)
    f = xy - base
    a = texture[base[:, 1] % height, base[:, 0] % width]
    b = texture[base[:, 1] % height, (base[:, 0] + 1) % width]
    c = texture[(base[:, 1] + 1) % height, base[:, 0] % width]
    d = texture[(base[:, 1] + 1) % height, (base[:, 0] + 1) % width]
    return (a * (1-f[:, 0, None]) + b * f[:, 0, None]) * (1-f[:, 1, None]) + \
           (c * (1-f[:, 0, None]) + d * f[:, 0, None]) * f[:, 1, None]


def render(triangles, paints, mats, shadows, spec):
    # Work in inches throughout, matching the source mesh and its UV density.
    eye, target = np.asarray(spec['eye']) / .0254, np.asarray(spec['target']) / .0254
    forward = K.normalise(target - eye)
    right = K.normalise(np.cross(forward, (0, 0, 1)))
    up = np.cross(right, forward)
    width, height = spec['size']
    pixels = height / (spec['scale'] / .0254)
    projected = triangles[..., :3] - eye
    screen = np.stack((width / 2 + (projected @ right) * pixels,
                       height / 2 - (projected @ up) * pixels), axis=-1)
    nearness = -projected @ forward
    image = np.full((height, width, 3), .08, np.float32)
    depth = np.full((height, width), -1e8, np.float32)
    shadow, sr, su, minimum, span = shadows
    half = K.normalise(SUN - forward)
    for index, (tri, xy, near, paint) in enumerate(zip(triangles, screen, nearness, paints)):
        geometric = np.cross(tri[1, :3] - tri[0, :3], tri[2, :3] - tri[0, :3])
        if np.dot(geometric, -forward) <= 0: continue
        lo = np.maximum(np.floor(xy.min(axis=0)).astype(int), 0)
        hi = np.minimum(np.ceil(xy.max(axis=0)).astype(int), (width-1, height-1))
        x0, y0 = lo; x1, y1 = hi
        if x1 < x0 or y1 < y0: continue
        (ax, ay), (bx, by), (cx, cy) = xy
        area = (bx-ax)*(cy-ay) - (by-ay)*(cx-ax)
        if abs(area) < 1e-9: continue
        x = np.arange(x0, x1+1) + .5
        y = (np.arange(y0, y1+1) + .5)[:, None]
        a = ((bx-x)*(cy-y) - (by-y)*(cx-x)) / area
        b = ((cx-x)*(ay-y) - (cy-y)*(ax-x)) / area
        c = 1-a-b
        z = a*near[0] + b*near[1] + c*near[2]
        region = depth[y0:y1+1, x0:x1+1]
        visible = (a >= -1e-7) & (b >= -1e-7) & (c >= -1e-7) & (z > region)
        if not visible.any(): continue
        weights = np.stack((a[visible], b[visible], c[visible]), axis=-1)
        attrs = weights @ tri
        pos, uv, normal = attrs[:, :3], attrs[:, 3:5], unit(attrs[:, 5:])
        m = mats[paint]
        mapped = uv*m['scale']
        if 'region' in m:
            # Atlas shaders apply their transform after the OBJ import V flip.
            incoming = np.column_stack((uv[:, 0], 1-uv[:, 1]))
            region_uv = m['region']
            mapped = region_uv[:2]+np.mod(incoming*m['scale'], 1)*region_uv[2:]
            mapped[:, 1] = 1-mapped[:, 1]
        base = sample_texture(m['texture'], mapped)
        sh_uv = (np.column_stack((pos @ sr, pos @ su)) - minimum) / span * (shadow.shape[0]-1)
        sh_pixel = np.rint(sh_uv).astype(int)
        light = np.zeros(len(pos), np.float32)
        # Evaluate the receiver plane at each shadow-map sample. A constant
        # bias alone leaves diagonal self-shadow bands on broad oblique boards.
        geometric = K.normalise(geometric)
        denominator = np.dot(geometric, SUN)
        denominator = math.copysign(max(abs(denominator), .10), denominator)
        gradient = np.array((np.dot(geometric, sr), np.dot(geometric, su)))/denominator
        for dx, dy in ((0, 0), (1, 0), (-1, 0), (0, 1), (0, -1)):
            sx = np.clip(sh_pixel[:, 0]+dx, 0, shadow.shape[1]-1)
            sy = np.clip(sh_pixel[:, 1]+dy, 0, shadow.shape[0]-1)
            delta = (np.column_stack((sx, sy))-sh_uv)/(shadow.shape[0]-1)*span
            receiver = pos @ SUN-delta @ gradient
            light += (receiver >= shadow[sy, sx] - .035) / 5
        diffuse = np.maximum(normal @ SUN, 0) * light
        sky = .26 + .16 * np.clip(normal[:, 2], -1, 1)
        lit = base * (sky[:, None] * np.array((.82, .90, 1.)) + diffuse[:, None] * 2.4)
        exponent = max(8, 2 / max(m['rough'], .1)**4 - 2)
        specular = np.maximum(normal @ half, 0)**exponent * light * .1
        image[y0:y1+1, x0:x1+1][visible] = lit + specular[:, None]
        region[visible] = z[visible]
    hdr = image * 1.12
    rgb = np.clip((hdr*(2.51*hdr+.03))/(hdr*(2.43*hdr+.59)+.14), 0, 1)
    rgb = np.where(rgb <= .0031308, rgb*12.92, 1.055*rgb**(1/2.4)-.055)
    return Image.fromarray(np.rint(np.clip(rgb, 0, 1)*255).astype(np.uint8))


def main():
    mats = materials()
    for label in ('before', 'candidate'):
        triangles, paints = read_obj(OUT / f'{label}.obj')
        shadows = shadow_map(triangles)
        for name, spec in VIEWS.items():
            render(triangles, paints, mats, shadows, spec).save(OUT / f'cpu-{name}-{label}.png')
            print(f'Rendered {label} {name}', flush=True)
    (OUT / 'cpu-provenance.json').write_text(json.dumps(dict(
        kind='Offline CPU geometry rendering', native_engine_capture=False, image_generation=False,
        source='Exact before/candidate OBJ files; current production albedo textures read only',
        lighting='Matched directional shadow maps, approximate diffuse/specular response',
        limitations=['Engine glass and room parallax are represented by neutral panes',
                     'No engine normal maps, weathering, GI, or performance validation'],
        views=VIEWS), indent=2) + '\n')


if __name__ == '__main__':
    main()
