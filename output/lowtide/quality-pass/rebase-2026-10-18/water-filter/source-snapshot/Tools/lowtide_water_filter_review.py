"""Numerical and visual review of staged planar-reflection mip filtering.

Renders an explicitly synthetic canal fixture, with the existing brick colour
image read unchanged. This is not a Lowtide screenshot or a native GPU test.
It isolates the filtering from capture lifecycle, scene light, waves and optics.
"""
import argparse
import json
import math
from pathlib import Path
import re

import numpy as np
from PIL import Image, ImageDraw

import lowtide_water_filter as W

WIDTH, HEIGHT = 1280, 720
BRICK = W.ROOT/'Assets/materials/lowtide/lt_brick_v2_color.png'
CASES = {
    'canal': dict(eye=(-7., 0., 4.7), target=(28., 0., .3), fov=55.),
    'bank': dict(eye=(2., 4.8, 2.1), target=(18., -.2, .2), fov=60.),
    'reverse': dict(eye=(45., -4.7, 1.6), target=(20., 0., .05), fov=65.),
}
WAVES = [((1, .22), .93, .110, .3, -.24), ((.82, -.57), .67, .075, 1.8, -.32),
         ((.44, .90), .43, .055, 3.1, -.43), ((.97, -.24), .28, .040, 4.6, -.61),
         ((.68, .73), .17, .028, 2.3, -.83), ((.92, .39), .11, .018, 5.7, -1.13),
         ((.53, -.85), .073, .012, .9, -1.42), ((.98, -.17), .049, .008, 4.1, -1.77)]


def unit(v):
    return v/np.maximum(np.linalg.norm(v, axis=-1, keepdims=True), 1e-12)


def smooth(a, b, v):
    t = np.clip((v-a)/(b-a), 0, 1)
    return t*t*(3-2*t)


def bilinear(image, uv, wrap=False):
    h, w = image.shape[:2]
    xy = uv*np.array((w, h))-.5
    index = np.floor(xy).astype(int); weight = xy-index
    x, y = index[..., 0], index[..., 1]
    if wrap:
        x0, x1, y0, y1 = x%w, (x+1)%w, y%h, (y+1)%h
    else:
        x0, x1 = np.clip(x, 0, w-1), np.clip(x+1, 0, w-1)
        y0, y1 = np.clip(y, 0, h-1), np.clip(y+1, 0, h-1)
    a = image[y0, x0]*(1-weight[..., 0, None])+image[y0, x1]*weight[..., 0, None]
    b = image[y1, x0]*(1-weight[..., 0, None])+image[y1, x1]*weight[..., 0, None]
    return a*(1-weight[..., 1, None])+b*weight[..., 1, None]


def mips(image):
    # Mirrors the installed downsample_cs.shader Box path, including odd tails.
    result = [image.astype(np.float32)]
    while min(result[-1].shape[:2]) > 1 and len(result) < W.MAX_MIPS:
        source = result[-1]; h, w = source.shape[0]//2, source.shape[1]//2
        source = source[:h*2, :w*2]
        result.append((source[::2, ::2]+source[1::2, ::2]+source[::2, 1::2]+source[1::2, 1::2])*.25)
    return result


def mip_lod(rough, footprint, dimensions, projection, count, strength=W.FILTER_STRENGTH):
    cone = rough*rough*max(np.asarray(dimensions)*np.abs(projection))*strength
    return np.clip(np.log2(np.maximum(np.maximum(footprint, cone), 1)), 0, max(count-1, 0))


def sample(chain, uv, lod):
    level = np.floor(lod).astype(int); weight = lod-level
    out = np.zeros((*uv.shape[:-1], 3), np.float32)
    for i in np.unique(level):
        select = level == i
        a = bilinear(chain[i], uv[select]); b = bilinear(chain[min(i+1, len(chain)-1)], uv[select])
        out[select] = a*(1-weight[select, None])+b*weight[select, None]
    return out


def camera(case, width, height):
    eye, target = np.asarray(case['eye']), np.asarray(case['target'])
    forward = unit(target-eye); right = unit(np.cross(forward, (0, 0, 1))); up = np.cross(right, forward)
    yy, xx = np.mgrid[0:height, 0:width]
    tangent = math.tan(math.radians(case['fov'])/2)
    sy = (1-2*(yy+.5)/height)*tangent
    sx = (2*(xx+.5)/width-1)*tangent*width/height
    ray = unit(forward+sx[..., None]*right+sy[..., None]*up)
    return eye, ray, right, up, (height/width/tangent, 1/tangent)


def environment(eye, rays, brick, reflected=False):
    """Analytic walls, window openings and a shallow bed for a reflection fixture."""
    flat = rays.reshape(-1, 3)
    z = np.clip(flat[:, 2], 0, 1)
    color = np.array((.49, .55, .60))*(1-z[:, None])+np.array((.12, .27, .48))*z[:, None]
    near = np.full(len(flat), np.inf)
    planes = [(1, -5.5, 'wall'), (1, 5.5, 'wall'), (0, 130., 'end'), (2, .17, 'bank')]
    if not reflected: planes.append((2, -.36, 'bed'))
    for axis, level, kind in planes:
        divisor = flat[:, axis]
        t = (level-eye[axis])/np.where(np.abs(divisor) > 1e-8, divisor, 1e-8)
        p = eye+flat*t[:, None]
        active = (t > .001) & (t < near)
        if kind in ('wall', 'end'):
            active &= (p[:, 2] >= 0) & (p[:, 2] <= 27) & (p[:, 0] >= -14) & (p[:, 0] <= 130)
            if kind == 'end': active &= np.abs(p[:, 1]) <= 5.5
        elif kind == 'bank':
            active &= (np.abs(p[:, 1]) >= 3.25) & (np.abs(p[:, 1]) <= 5.5) & (p[:, 0] >= -14) & (p[:, 0] <= 130)
        else:
            active &= (np.abs(p[:, 1]) <= 3.25) & (p[:, 0] >= -14) & (p[:, 0] <= 130)
        if not active.any(): continue
        point = p[active]
        if kind in ('wall', 'end'):
            horizontal = point[:, 0] if kind == 'wall' else point[:, 1]
            uv = np.stack((horizontal/1.24, -point[:, 2]/.93), -1)
            paint = bilinear(brick, uv, True)*(.85 if level < 0 else 1.3)
            x = (horizontal+.2)%3.7-1.85
            y = (point[:, 2]-1.7)%3.9
            window = (np.abs(x) < .61) & (y < 1.65)
            window |= (x*x+(y-1.65)**2 < .61**2) & (y >= 1.65)
            window &= point[:, 2] > 1.7
            frame = window & ((np.abs(x) > .55) | (y < .06) | (np.abs(x) < .025) | (np.abs(y-.8) < .025))
            paint[window] = (.019, .035, .031); paint[frame] = (.13, .17, .12)
            paint[(point[:, 2]%3.9) < .13] *= .42
            paint[np.abs((horizontal+.9)%7.4-3.7) < .035] = (.025, .030, .029)
            paint[point[:, 2] < 1.1] = (.22, .23, .20)
        elif kind == 'bank':
            paint = np.tile((.10, .095, .075), (len(point), 1))
        else:
            variation = .92+.08*np.sin(point[:, 0]*8.7+np.sin(point[:, 1]*3.2))
            paint = np.array((.085, .072, .048))*variation[:, None]
        color[active] = paint; near[active] = t[active]
    return color.reshape(rays.shape), near.reshape(rays.shape[:-1])


def material_roughness():
    text = (W.ROOT/W.MATERIAL).read_text()
    values = re.findall(r'g_flWaterRoughness\s+"([0-9.]+)"', text)
    assert len(values) == 1, 'Expected one explicit live water roughness'
    return float(values[0])


def water_inputs(case, brick, time=0, base_rough=None, width=WIDTH, height=HEIGHT):
    if base_rough is None: base_rough = material_roughness()
    eye, rays, right, up, projection = camera(case, width, height)
    opaque, depth = environment(eye, rays, brick)
    distance = -eye[2]/np.minimum(rays[..., 2], -.00001)
    plane = eye+rays*np.minimum(distance, 1e5)[..., None]
    active = (rays[..., 2] < -.001) & (distance < depth) & (np.abs(plane[..., 1]) < 3.25) & (plane[..., 0] > -14) & (plane[..., 0] < 130)
    position = plane[..., :2]/.0254-np.array((-2.1, .65))*time
    dy, dx = np.gradient(position, axis=(0, 1))
    slope = np.zeros_like(position); variance = np.zeros(active.shape)
    for direction, wavelength, strength, phase, speed in WAVES:
        direction = unit(np.asarray(direction, float))
        vector = direction*(2*math.pi/(48*wavelength))
        footprint = np.maximum(np.abs(dx@vector), np.abs(dy@vector))
        resolved = 1-smooth(.65, 2.4, footprint)
        angle = position@vector+phase+time*speed
        slope += direction*(strength*np.cos(angle)*resolved)[..., None]
        variance += .5*strength*strength*(1-resolved*resolved)
    normal = unit(np.concatenate((slope*.8, np.ones((*active.shape, 1))), -1))
    rough = np.sqrt(base_rough*base_rough+variance*.8*.8)
    view = unit(eye-plane)
    incoming = -view
    reflected = incoming-2*np.sum(incoming*normal, axis=-1, keepdims=True)*normal
    flat_reflected = incoming.copy(); flat_reflected[..., 2] *= -1
    delta = reflected-flat_reflected; delta[..., 2] *= -1
    yy, xx = np.mgrid[0:height, 0:width]
    uv = np.stack(((xx+.5)/width, (yy+.5)/height), -1)
    uv += np.stack((delta@right*height/width, -delta@up), -1)*.014
    uv = np.clip(uv, 0, 1)
    capture_eye, capture_rays, _, _, _ = camera(case, width//2, height//2)
    capture_eye = capture_eye.copy(); capture_eye[2] *= -1
    capture_rays[..., 2] *= -1
    capture, _ = environment(capture_eye, capture_rays, brick, True)
    chain = mips(capture)
    uvdy, uvdx = np.gradient(uv, axis=(0, 1))
    dimensions = np.array((capture.shape[1], capture.shape[0]))
    footprint = np.maximum(np.linalg.norm(uvdx*dimensions, axis=-1), np.linalg.norm(uvdy*dimensions, axis=-1))
    lod = mip_lod(rough, footprint, dimensions, projection, len(chain))
    facing = np.clip(np.abs(np.sum(view*normal, axis=-1)), 0, 1)
    fresnel = .02037+(1-.02037)*(1-facing)**5
    path = .36/np.maximum(view[..., 2], .01)
    transmission = np.exp(-path/(18*.0254))
    return dict(opaque=opaque, active=active, uv=uv, chain=chain, lod=lod, fresnel=fresnel,
                transmission=transmission, normal=normal, view=view, rough=rough)


def compose(inputs, candidate):
    active = inputs['active']
    reflected = sample(inputs['chain'], inputs['uv'][active], inputs['lod'][active]) if candidate else bilinear(inputs['chain'][0], inputs['uv'][active])
    fresnel = inputs['fresnel'][active]
    transmission = inputs['transmission'][active]
    opacity = 1-(1-fresnel)*transmission
    image = inputs['opaque'].copy()
    image[active] = reflected*fresnel[:, None]+np.array((.014, .022, .018))*(1-transmission[:, None])*.7+image[active]*(1-opacity[:, None])
    return image


def display(linear, label):
    hdr = linear*.95
    rgb = np.clip((hdr*(2.51*hdr+.03))/(hdr*(2.43*hdr+.59)+.14), 0, 1)
    rgb = np.where(rgb <= .0031308, rgb*12.92, 1.055*rgb**(1/2.4)-.055)
    image = Image.fromarray(np.rint(rgb*255).astype(np.uint8))
    draw = ImageDraw.Draw(image)
    draw.rectangle((0, image.height-29, image.width, image.height), fill=(22, 25, 27))
    draw.text((12, image.height-21), 'OFFLINE REFLECTION TEST SCENE | '+label+' | synthetic canal; matched waves and optics; not an engine capture', fill=(225, 225, 218))
    return image


def verify(manifest):
    if 'project_root' in manifest:
        assert Path(manifest['project_root']).resolve() == W.ROOT, 'Candidate belongs to another checkout'
    assert all(W.sha(W.ROOT/p) == h for p, h in manifest['sources'].items())
    assert all(W.sha(W.ROOT/p) == h for p, h in manifest['protected'].items())
    assert all(W.sha(Path(p)) == h for p, h in manifest['api']['external_sources'].items())
    assert all(W.sha(W.OUT/'stage'/p) == h for p, h in manifest['staged_files'].items())
    assert W.code() == (W.OUT/'stage'/W.CODE).read_text()
    assert W.shader() == (W.OUT/'stage'/W.SHADER).read_text()
    assert (W.ROOT/W.BASE_SHADER).read_text().count('g_tWaterReflection.SampleLevel( WaterReflectionSampler, saturate( uv ), 0 ).rgb') == 1
    code = W.code()
    assert code.index('commands.DrawReflection(') < code.index('commands.GenerateMipMaps(') < code.index('commands.Attributes.Set( "LowtideReflection"') < code.index('commands.DrawModel(') < code.index('commands.ReleaseRenderTarget(')
    dimensions = [(w, h) for w in (1, 2, 3, 16, 255, 256, 640, 960, 1280) for h in (1, 2, 7, 144, 360, 539, 720, 4096)]
    for width, height in dimensions:
        dims = W.mip_dimensions(width, height)
        assert 1 <= len(dims) <= 7 and all(w >= 1 and h >= 1 for w, h in dims)
        assert sum(w*h for w, h in dims[1:]) <= width*height/3
    constants = [(0, 0, 0), (.02, .3, 1), (8, 32, 256), (4096, 16384, 65504)]
    for color in constants:
        chain = mips(np.tile(color, (64, 128, 1)))
        assert all(np.allclose(level, color, rtol=2e-7, atol=1e-8) for level in chain)
    rng = np.random.default_rng(5621)
    image = rng.random((256, 256, 3), dtype=np.float32)*12
    chain = mips(image)
    baseline = image.mean(axis=(0, 1), dtype=np.float64)
    error = max(float(np.max(np.abs(level.mean(axis=(0, 1), dtype=np.float64)-baseline))) for level in chain)
    assert error < 2e-6
    variances = [float(level.var(dtype=np.float64)) for level in chain]
    assert all(a >= b for a, b in zip(variances, variances[1:]))
    uv = rng.uniform(-.1, 1.1, (5000, 2))
    assert np.array_equal(sample(chain, uv, np.zeros(len(uv))), bilinear(chain[0], uv).astype(np.float32))
    count = 0; resolution_errors = []
    for fov in (35, 55, 75, 100):
        projection = np.array((1/(16/9*math.tan(math.radians(fov)/2)), 1/math.tan(math.radians(fov)/2)))
        rough = np.linspace(0, .5, 1201)
        for width in (256, 640, 960, 1280):
            height = round(width*9/16); dims = (width, height)
            levels = len(W.mip_dimensions(*dims))
            lod = mip_lod(rough, .5, dims, projection, levels)
            assert np.all(np.diff(lod) >= 0) and np.isfinite(lod).all()
            assert lod.min() >= 0 and lod.max() <= levels-1
            scope = (lod > 0) & (lod < levels-1)
            actual = 2**lod[scope]/max(np.asarray(dims)*projection)
            resolution_errors.append(float(np.max(np.abs(actual-rough[scope]**2*W.FILTER_STRENGTH))))
            count += len(rough)
    assert max(resolution_errors) < 1e-12
    assert np.all(mip_lod(np.linspace(0, 1, 200), 1000, (256, 1), (1, 1), 1) == 0)
    # Turning roughness filtering off still honours minification of distorted UVs.
    footprints = np.geomspace(.125, 1024, 301)
    derivative_only = mip_lod(.5, footprints, (960, 540), (1, 1), 7, strength=0)
    assert np.allclose(derivative_only, np.clip(np.log2(np.maximum(footprints, 1)), 0, 6))
    return dict(status='offline_filter_math_and_scope_passed', manifest_sha256=W.sha(W.OUT/'manifest.json'),
                reviewer_sha256=W.sha(Path(__file__)), protected_live_files=len(manifest['protected']),
                target_size_cases=len(dimensions), constant_hdr_cases=len(constants),
                hdr_max_mean_error=error, source_variances=variances, zero_lod_samples=len(uv),
                roughness_projection_cases=count, resolution_scale_error=max(resolution_errors),
                single_mip_fallback_cases=200, derivative_only_cases=len(footprints),
                roughness_filter_scale=W.FILTER_STRENGTH, stage_files=len(manifest['staged_files']),
                live_assets_and_code_unchanged=True, native_shader_compiled=False,
                limitation='Source ordering and CPU mathematics are not proof of native GPU barriers, lifetime, rendering, sandbox acceptance or FPS')


def main(preview=True):
    manifest = json.loads((W.OUT/'manifest.json').read_text())
    report = verify(manifest)
    W.write(W.OUT/'verification.json', json.dumps(report, indent=2)+'\n')
    print(json.dumps(report, indent=2), flush=True)
    if not preview: return
    directory = W.OUT/'preview'; directory.mkdir(parents=True, exist_ok=True)
    rgb = np.asarray(Image.open(BRICK).convert('RGB'), np.float32)/255
    brick = np.where(rgb <= .04045, rgb/12.92, ((rgb+.055)/1.055)**2.4)
    metrics = {}
    for name, case in CASES.items():
        inputs = water_inputs(case, brick)
        active = inputs['active']
        assert active.any() and np.isfinite(inputs['lod']).all()
        for candidate in (False, True):
            label = 'candidate' if candidate else 'before'
            frame = compose(inputs, candidate)
            display(frame, 'FILTERED' if candidate else 'SHARP LEVEL ZERO').save(directory/f'{name}-{label}.png')
            print(f'Rendered {name} {label}', flush=True)
        metrics[name] = dict(water_pixels=int(active.sum()), lod_range=[float(inputs['lod'][active].min()), float(inputs['lod'][active].max())],
                             roughness_range=[float(inputs['rough'][active].min()), float(inputs['rough'][active].max())])
    provenance = dict(kind='Synthetic CPU reflection fixture', native_engine_capture=False, actual_lowtide_scene=False,
                      manifest_sha256=W.sha(W.OUT/'manifest.json'), renderer_sha256=W.sha(Path(__file__)),
                      source_brick_pixels_unchanged=True, source_image={BRICK.relative_to(W.ROOT).as_posix():W.sha(BRICK)},
                      cases=CASES, resolution=[WIDTH, HEIGHT], metrics=metrics,
                      reflected_image='Analytic walls/windows/sky rendered from the mirrored fixture camera, with real source brick pixels',
                      filter='Native linear Box mip arithmetic plus shader LOD equation, using the actual half-resolution capture layout',
                      roughness_filter_scale=W.FILTER_STRENGTH,
                      base_roughness=material_roughness(),
                      material_input={W.MATERIAL:W.sha(W.ROOT/W.MATERIAL)},
                      wave_model='Fixed analytic fixture ripples; does not reproduce the current ocean normal maps or shoreline shader',
                      unchanged_between_versions=['camera and reflected fixture', 'wave normals and filtered variance', 'Fresnel and absorption', 'lighting and exposure'],
                      limitations=['Synthetic fixture geometry and approximate optics; no map appearance acceptance',
                                   'No native shaders, sandbox hotload, GPU barriers, real lighting, temporal AA or performance tests'],
                      files={p.name:W.sha(p) for p in sorted(directory.glob('*.png'))})
    W.write(directory/'provenance.json', json.dumps(provenance, indent=2)+'\n')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--verify-only', action='store_true')
    parser.add_argument('--output', type=Path, default=W.OUT)
    args = parser.parse_args()
    W.OUT = args.output.resolve()
    assert W.OUT.is_relative_to(W.ROOT/'output/lowtide/quality-pass')
    main(not args.verify_only)
