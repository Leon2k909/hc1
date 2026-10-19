"""Numerical and offline visual checks for the staged mortar relief.

The CPU shader analogue is compared against an independent dense ray oracle.
Rendered planes use unchanged production albedo/normal/AO maps. This does not
compile HLSL or certify the engine's lighting, mip behaviour or runtime cost.
"""
import json
import math
from pathlib import Path

import numpy as np
from PIL import Image

import lowtide_brick_relief as B
import map_kit as K

OUT = K.ROOT / 'output/lowtide/quality-pass/brick-relief'
STAGE = OUT / 'stage'


def sample(texture, uv):
    height, width = texture.shape[:2]
    xy = uv * (width, -height) + (-.5, height-.5)
    base = np.floor(xy).astype(np.int32)
    f = xy - base
    a = texture[base[:, 1] % height, base[:, 0] % width]
    b = texture[base[:, 1] % height, (base[:, 0]+1) % width]
    c = texture[(base[:, 1]+1) % height, base[:, 0] % width]
    d = texture[(base[:, 1]+1) % height, (base[:, 0]+1) % width]
    if texture.ndim == 3: f = f[..., None]
    return (a*(1-f[:, 0]) + b*f[:, 0])*(1-f[:, 1]) + (c*(1-f[:, 0]) + d*f[:, 0])*f[:, 1]


def trace(height, uv, ray, facing):
    steps = int(np.clip(np.ceil(np.linalg.norm(ray*2048)*2), 8, 64))
    layer = 1 / steps
    at = uv.copy()
    depth = np.zeros(len(uv))
    surface = 1 - sample(height, at)
    previous = surface.copy()
    for _ in range(steps):
        running = depth < surface
        if not running.any(): break
        previous[running] = surface[running] - depth[running]
        at[running] -= ray * layer
        depth[running] += layer
        surface[running] = 1 - sample(height, at[running])
    low, high = np.maximum(depth-layer, 0), depth.copy()
    before, after = previous.copy(), surface-depth
    for _ in range(3):
        middle = (low+high)*.5
        offset = 1-sample(height, uv-ray[None, :]*middle[:, None])-middle
        outside = offset > 0
        low[outside], before[outside] = middle[outside], offset[outside]
        high[~outside], after[~outside] = middle[~outside], offset[~outside]
    weight = np.clip(before / np.maximum(before-after, .00001), 0, 1)
    return uv-ray[None, :]*(low+(high-low)*weight)[:, None]


def oracle(height, uv, ray):
    """First sign change in 512 layers, then twelve bisection refinements."""
    lo = np.zeros(len(uv))
    hi = np.ones(len(uv))
    unresolved = np.ones(len(uv), bool)
    for i in range(513):
        d = i / 512
        indices = np.flatnonzero(unresolved)
        surface = 1 - sample(height, uv[indices] - ray*d)
        hit = indices[d >= surface]
        hi[hit] = d
        lo[hit] = max(0, d-1/512)
        unresolved[hit] = False
        if not unresolved.any(): break
    assert not unresolved.any()
    for _ in range(12):
        mid = (lo+hi)*.5
        surface = 1 - sample(height, uv-ray[None, :]*mid[:, None])
        inside = mid >= surface
        hi[inside] = mid[inside]
        lo[~inside] = mid[~inside]
    return uv-ray[None, :]*((lo+hi)*.5)[:, None]


def smoothstep(a, b, value):
    t = np.clip((value-a)/(b-a), 0, 1)
    return t*t*(3-2*t)


def checks(height, manifest):
    rng = np.random.default_rng(180315)
    uv = rng.uniform(-2, 3, (2048, 2))
    tile = np.array(manifest['tile_inches'])
    result = []
    for angle in (0, 30, 60, 75, 80):
        facing = math.cos(math.radians(angle))
        ray = np.array((math.sin(math.radians(angle)), .12)) / tile * (B.DEPTH_MM/25.4) / max(facing, .16)
        traced = trace(height, uv, ray, facing)
        dense = oracle(height, uv, ray)
        error_mm = np.linalg.norm((traced-dense)*tile*25.4, axis=1)
        periodic = trace(height, uv+(2, -3), ray, facing) - (2, -3)
        assert np.allclose(periodic, traced, atol=2e-10)
        # A constant-height plane has an analytic answer for every view angle.
        for value in (0., .25, .5, .8, 1.):
            flat = np.full((4, 4), value)
            actual = trace(flat, uv[:32], ray, facing)
            assert np.allclose(actual, uv[:32]-ray*(1-value), atol=1e-10)
        result.append(dict(angle_degrees=angle, rays=len(uv),
                           p50_position_error_mm=float(np.quantile(error_mm, .5)),
                           p95_position_error_mm=float(np.quantile(error_mm, .95)),
                           p99_position_error_mm=float(np.quantile(error_mm, .99)),
                           maximum_position_error_mm=float(error_mm.max())))
    fades = 1-smoothstep(*B.FADE_INCHES, np.array([0, 143, 144, 256, 511, 512, 1024]))
    assert np.all(fades[:3] == 1) and np.all(fades[-2:] == 0)
    assert np.all(np.diff(fades) <= 0)
    return dict(dense_reference=result, repeated_uvs_agree=True, analytic_planes=25,
                fade_samples=fades.tolist(), dense_oracle_layers=512, bisections=12)


def render(height, manifest, angle, candidate, name):
    width, height_pixels = 1200, 800
    tile = np.array(manifest['tile_inches'])
    # Perspective-independent camera/plane projection. Each pair has identical
    # camera, framing, light and maps; only the UV intersection changes.
    azimuth = math.radians(angle)
    view = np.array((math.sin(azimuth), -math.cos(azimuth), .10))
    view /= np.linalg.norm(view)
    forward = -view
    right = np.cross(forward, (0, 0, 1)); right /= np.linalg.norm(right)
    up = np.cross(right, forward)
    visible_width = 13 if angle < 70 else 7
    x = (np.arange(width)+.5-width/2)/width*visible_width
    y = (height_pixels/2-np.arange(height_pixels)-.5)/width*visible_width
    origins = right*x[None, :, None] + up*y[:, None, None] + view*90
    travel = origins[..., 1] / view[1]
    plane = origins - view*travel[..., None]
    uv = np.column_stack((plane[..., 0].ravel()/tile[0]+.37, plane[..., 2].ravel()/tile[1]+.51))
    if candidate:
        ray = np.array((view[0], view[2])) / tile * (B.DEPTH_MM/25.4) / max(-view[1], .16)
        uv = trace(height, uv, ray, -view[1])
    folder = K.ASSETS / 'materials/lowtide'
    def texture(suffix):
        if candidate and suffix in ('normal', 'ao'):
            return np.asarray(Image.open(STAGE/B.PREFIX/f'lt_brick_{suffix}.png'), np.float32)/255
        return np.asarray(Image.open(folder/f'lt_brick_v2_{suffix}.png'), np.float32)/255
    albedo = sample(texture('color'), uv)
    albedo = np.where(albedo <= .04045, albedo/12.92, ((albedo+.055)/1.055)**2.4)
    normal = sample(texture('normal'), uv)*2-1
    normal /= np.linalg.norm(normal, axis=1, keepdims=True)
    # Tangent U=east, tangent V=up, geometric normal facing the camera's side.
    normal = np.column_stack((normal[:, 0], -normal[:, 2], normal[:, 1]))
    ao = sample(texture('ao'), uv)
    sun = np.array((-.52, -.62, .59)); sun /= np.linalg.norm(sun)
    diffuse = np.maximum(normal @ sun, 0)
    hdr = albedo * (.34*ao[:, None]*np.array((.83, .91, 1.)) + diffuse[:, None]*2.1)
    rgb = np.clip((hdr*(2.51*hdr+.03))/(hdr*(2.43*hdr+.59)+.14), 0, 1)
    rgb = np.where(rgb <= .0031308, rgb*12.92, 1.055*rgb**(1/2.4)-.055)
    path = OUT / f'{name}-{"candidate" if candidate else "before"}.png'
    Image.fromarray(np.rint(np.clip(rgb, 0, 1).reshape(height_pixels, width, 3)*255).astype(np.uint8)).save(path)
    print(f'Rendered {path.name}', flush=True)


def main():
    manifest = json.loads((STAGE/'manifest.json').read_text())
    height = np.asarray(Image.open(STAGE/B.PREFIX/'lt_brick_height.png'), float)/255
    report = checks(height, manifest)
    for angle, name in ((30, 'front'), (60, 'oblique'), (75, 'grazing')):
        for candidate in (False, True):
            render(height, manifest, angle, candidate, name)
    report.update(native_compile='not_run', native_visual_review='not_run',
                  preview='CPU analogue of the staged POM shader on a plane; not an engine capture',
                  limitations=['No engine mip filtering, world-space weathering, GI or measured gameplay cost'],
                  protected_files_unchanged=all(B.sha(K.ROOT/p) == h for p, h in manifest['protected'].items()))
    assert report['protected_files_unchanged']
    (OUT/'offline-verification.json').write_text(json.dumps(report, indent=2)+'\n')
    print(json.dumps(report, indent=2))


if __name__ == '__main__':
    main()
