"""Stage registered mortar-height data and a private Lowtide brick shader.

All live resources are read only. The height field reproduces the existing
brick normal-map bake, which is checked pixel for pixel before any output.
Only numerical height/normal/AO data, candidate materials and shader text are
emitted; no colour image is changed. Native compilation/review remains pending.
"""
import argparse
import hashlib
import json
from pathlib import Path
import re
import uuid

import numpy as np
from PIL import Image
from scipy import ndimage, signal

import map_kit as K
import lowtide_brick as B
import terrain_textures as T

# Four-millimetre pointing plus fine grain, contained in a five-millimetre range.
DEPTH_MM = 5.0
FADE_INCHES = (144, 512)
PREFIX = 'materials/lowtide/brick_relief'
SHADER = 'shaders/hc1_lowtide_brick_relief.shader'
INCLUDE = 'shaders/common/lowtide_brick_relief.hlsl'
SOURCE = K.ROOT / 'Sources/Lowtide/brick/lowtide_brick_relief.hlsl'


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def joint_distances(rgb, mm_pixel):
    """Fit 24 beds and six head joints per course, independent of mineral flecks.

    Broad, bounded centre-line deviations follow the photographed construction.
    Dark/light inclusions within each brick cannot become deep cavities.
    """
    h, w = rgb.shape[:2]
    chroma = (rgb[..., 0]-rgb[..., 1]) / np.maximum(rgb[..., 0], .05)
    mortar = 1-T.smoothstep(.1, .25, chroma)
    profile = ndimage.gaussian_filter1d(mortar.mean(axis=1), 1.8, mode='wrap')
    peaks, _ = signal.find_peaks(np.tile(profile, 3), distance=h/34, prominence=.12, width=(2, 30))
    beds = peaks[(peaks >= h) & (peaks < h*2)]-h
    assert len(beds) == 24, ('Unexpected course count', beds.tolist())
    y, x = np.mgrid[:h, :w]
    distance = np.full((h, w), np.inf, np.float32)
    curves = []
    for bed in beds:
        offsets = np.arange(-12, 13)
        weight = np.maximum(mortar[(bed+offsets) % h]-.35, 0)**3
        shift = (weight*offsets[:, None]).sum(axis=0)/np.maximum(weight.sum(axis=0), 1e-6)
        curve = bed + np.clip(ndimage.gaussian_filter1d(shift, 12, mode='wrap'), -4, 4)
        curves.append(curve)
        d = np.abs((y-curve[None, :]+h*.5) % h-h*.5)*mm_pixel[1]
        distance = np.minimum(distance, d)
    records = []
    for index, (a, b) in enumerate(zip(beds, np.r_[beds[1:], beds[0]+h])):
        middle = np.arange(round(a+(b-a)*.3), round(a+(b-a)*.7)) % h
        profile = ndimage.gaussian_filter1d(mortar[middle].mean(axis=0), 3, mode='wrap')
        peaks, _ = signal.find_peaks(np.tile(profile, 3), distance=w/11.4, prominence=.15, width=(2, 45))
        heads = peaks[(peaks >= w) & (peaks < w*2)]-w
        assert len(heads) == 6, ('Unexpected head-joint count', int(a), heads.tolist())
        yi = np.arange(int(a)-8, int(b)+9)
        low = curves[index]
        high = curves[(index+1) % len(curves)] + (h if index == len(curves)-1 else 0)
        band = (yi[:, None] >= low[None, :]) & (yi[:, None] <= high[None, :])
        section = distance[yi % h].copy()
        for head in heads:
            offsets = np.arange(-14, 15)
            weight = np.maximum(mortar[np.ix_(yi % h, (head+offsets) % w)]-.35, 0)**3
            shift = (weight*offsets[None, :]).sum(axis=1)/np.maximum(weight.sum(axis=1), 1e-6)
            curve = head + np.clip(ndimage.gaussian_filter1d(shift, 6, mode='nearest'), -5, 5)
            d = np.abs((x[0][None, :]-curve[:, None]+w*.5) % w-w*.5)*mm_pixel[0]
            section = np.minimum(section, np.where(band, d, np.inf))
        distance[yi % h] = section
        records.append(dict(bed=int(a), next_bed=int(b), heads=heads.tolist()))
    return distance, records


def surface():
    source_rgb, clay = B.read_surface()
    scale, region = B.layout(clay, source_rgb)
    atlas = 1 << int(np.ceil(np.log2(max(clay.shape))))
    left, top, width, height = (round(value * atlas) for value in region)
    # Resample only the numerical material mask using the original bake's exact
    # crop. Production colour pixels are read directly and are never rewritten.
    numeric_mask = Image.fromarray(clay[top:top+height, left:left+width])
    clay = np.asarray(numeric_mask.resize((B.TEXTURE_SIZE, B.TEXTURE_SIZE), Image.Resampling.BILINEAR), np.float32)
    clay = ndimage.minimum_filter(ndimage.maximum_filter(clay, size=3, mode='wrap'), size=3, mode='wrap')
    smooth = ndimage.gaussian_filter(clay, 2.2, mode='wrap')
    rgb = np.asarray(Image.open(B.COLOUR).convert('RGB'), np.float32) / 255
    luminance = rgb @ np.array([.2126, .7152, .0722], np.float32)
    detail = luminance - ndimage.gaussian_filter(luminance, 3.5, mode='wrap')
    millimetres = smooth * 7.0 + detail * smooth * 3.0
    mm_u, mm_v = B.TILE_UNITS * 25.4 / np.asarray(scale)
    dx = (np.roll(millimetres, -1, 1) - np.roll(millimetres, 1, 1)) * (B.TEXTURE_SIZE / mm_u) * .5
    dy = (np.roll(millimetres, -1, 0) - np.roll(millimetres, 1, 0)) * (B.TEXTURE_SIZE / mm_v) * .5
    normal = np.stack([-dx, dy, np.ones_like(millimetres)], axis=-1)
    normal /= np.linalg.norm(normal, axis=-1, keepdims=True)
    encoded = np.rint((normal+1)*127.5).clip(0, 255).astype(np.uint8)
    installed = np.asarray(Image.open(B.DIRECTORY / 'lt_brick_v2_normal.png').convert('RGB'))
    mismatch = np.any(encoded != installed, axis=-1)
    assert not mismatch.any(), f'Height reconstruction differs from {int(mismatch.sum())} installed normal pixels'
    # Fit the actual structural joints before deriving height. The raw colour
    # mask proved unsuitable for relief: mortar flecks became isolated ridges.
    mm_pixel = np.array((mm_u, mm_v)) / B.TEXTURE_SIZE
    distance, joints = joint_distances(rgb, mm_pixel)
    crest = T.smoothstep(1.75, 4.25, distance)
    millimetres = .2 + crest*3.8 + detail*crest*.25
    dx = (np.roll(millimetres, -1, 1)-np.roll(millimetres, 1, 1)) / (2*mm_pixel[0])
    dy = (np.roll(millimetres, -1, 0)-np.roll(millimetres, 1, 0)) / (2*mm_pixel[1])
    refined_normal = np.stack([-dx, dy, np.ones_like(millimetres)], axis=-1)
    refined_normal /= np.linalg.norm(refined_normal, axis=-1, keepdims=True)
    ao = .74 + .26*np.sqrt(crest)
    assert np.isfinite(millimetres).all() and millimetres.min() >= 0 and millimetres.max() <= DEPTH_MM
    output = np.rint(millimetres / DEPTH_MM * 255).astype(np.uint8)
    maps = {'height': output, 'normal': np.rint((refined_normal+1)*127.5).clip(0, 255).astype(np.uint8),
            'ao': np.rint(ao*255).clip(0, 255).astype(np.uint8)}
    report = dict(revision='fitted-mortar-v4', size=list(output.shape[::-1]), depth_encoding_mm=DEPTH_MM,
                  physical_height_mm=[float(millimetres.min()), float(millimetres.max())],
                  tile_inches=(np.array((mm_u, mm_v))/25.4).tolist(), scale=list(scale),
                  registration_baseline_matching_pixels=int(mismatch.size), registration_baseline_mismatching_pixels=int(mismatch.sum()),
                  candidate_normal_recomputed_from_refined_height=True,
                  joint_depth_mm=3.8, arris_distance_from_joint_mm=[1.75, 4.25], structural_joints=joints,
                  submillimetre_detail_preserved=True, colour_pixels_modified=False,
                  maximum_height_quantisation_error_mm=float(np.max(np.abs(output.astype(float)/255*DEPTH_MM-millimetres))))
    return maps, report


def shader_text():
    baseline = (K.ASSETS / 'shaders/hc1_brick.shader').read_text()
    declaration = '    float4 g_vBrickScale < Default4( 1, 1, 0, 0 ); UiGroup( "Brick" ); >;'
    start = '''        float2 worldUv = input.vTextureCoords.xy;
        // Preserve UV derivatives across repeats: the wrapping sampler handles the tile boundary and mipmaps.
        input.vTextureCoords.xy *= g_vBrickScale.xy;
        Material material = Material::From( input );'''
    assert baseline.count(declaration) == baseline.count(start) == 1
    output = baseline.replace(declaration, f'    #include "common/lowtide_brick_relief.hlsl"\n{declaration}')
    output = output.replace(start, '        Material material = ReadReliefBrick( input, g_vBrickScale.xy );')
    output = output.replace('Lowtide masonry: seamless scanned clay, recessed mortar and physical brick scale',
                            'Lowtide brick candidate: registered mortar relief; original weathering retained')
    # The entire existing weathering/shading tail remains byte-identical after
    # newline normalization. Granite and arch materials keep their live shader.
    marker = '        // CommonInputs defaults metalness and transmission to one.'
    assert baseline.split(marker, 1)[1] == output.split(marker, 1)[1]
    return output


def material_text(name):
    baseline = (B.DIRECTORY / f'{name}.vmat').read_text()
    needle = '    shader "shaders/hc1_brick.shader"'
    assert baseline.count(needle) == 1 and baseline.rstrip().endswith('}')
    output = baseline.replace(needle, f'    shader "{SHADER}"')
    output = output.replace('"materials/lowtide/lt_brick_v2_normal.png"', f'"{PREFIX}/lt_brick_normal.png"')
    output = output.replace('"materials/lowtide/lt_brick_v2_ao.png"', f'"{PREFIX}/lt_brick_ao.png"')
    index = output.rfind('}')
    addition = (f'    TextureHeight "{PREFIX}/lt_brick_height.png"\n'
                f'    g_flMortarDepth "{DEPTH_MM/25.4:.8f}"\n'
                f'    g_vMortarFade "[{FADE_INCHES[0]} {FADE_INCHES[1]}]"\n')
    return '// Offline mortar-relief candidate; production textures and weathering retained.\n' + output[:index] + addition + output[index:]


def metadata(root, relative):
    path = root / relative
    sidecar = path.with_name(path.name + '.meta')
    identifier = uuid.uuid5(uuid.NAMESPACE_URL, relative)
    sidecar.write_text(json.dumps({'guid': str(identifier)}, indent=2) + '\n')


def stage(root):
    root = Path(root).resolve()
    assert not root.is_relative_to(K.ASSETS.resolve()), 'Stage outside live Assets'
    root.mkdir(parents=True, exist_ok=True)
    protected = {}
    for folder in ('Assets/models/maps/lowtide', 'Assets/materials/lowtide', 'Assets/scenes/maps/Lowtide'):
        for path in (K.ROOT / folder).rglob('*'):
            if path.is_file() and not path.name.endswith('_c'):
                protected[path.relative_to(K.ROOT).as_posix()] = sha(path)
    for path in (K.ASSETS/'shaders/hc1_brick.shader', K.ASSETS/'shaders/common/lowtide_shed_wear.hlsl', B.SOURCE):
        protected[path.relative_to(K.ROOT).as_posix()] = sha(path)
    maps, report = surface()
    files = {
        SHADER: shader_text().encode(),
        INCLUDE: SOURCE.read_bytes(),
        f'{PREFIX}/lt_brick_relief.vmat': material_text('lt_brick').encode(),
        f'{PREFIX}/lt_brick_soot_relief.vmat': material_text('lt_brick_soot').encode(),
    }
    for relative, data in files.items():
        path = root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
    for suffix, pixels in maps.items():
        Image.fromarray(pixels).save(root / PREFIX / f'lt_brick_{suffix}.png', optimize=True)
    for relative in list(files) + [f'{PREFIX}/lt_brick_{suffix}.png' for suffix in maps]:
        metadata(root, relative)
    # Colour, roughness and every architectural weathering input are preserved.
    pattern = r'^\s*(\w+)\s+"([^"\r\n]*)"'
    for name in ('lt_brick', 'lt_brick_soot'):
        original = dict(re.findall(pattern, (B.DIRECTORY/f'{name}.vmat').read_text(), re.M))
        candidate = dict(re.findall(pattern, (root/PREFIX/f'{name}_relief.vmat').read_text(), re.M))
        assert all(candidate[key] == value for key, value in original.items() if key not in ('shader', 'TextureNormal', 'TextureAmbientOcclusion'))
    assert all(sha(K.ROOT / path) == digest for path, digest in protected.items())
    report.update(status='offline_candidate_native_compile_and_review_pending',
                  production_changed=False, fade_inches=list(FADE_INCHES),
                  step_range=[8, 64], binary_refinements=3, subpixel_fade=True, mirrored_uv_basis=True,
                  protected=protected, generator_sha256=sha(Path(__file__)),
                  changes={p.relative_to(root).as_posix(): {'before': None, 'after': sha(p)}
                           for p in sorted(root.rglob('*')) if p.is_file() and p.name != 'manifest.json'})
    (root/'manifest.json').write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps({k: v for k, v in report.items() if k not in ('protected', 'changes', 'structural_joints')}, indent=2))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--stage', type=Path, required=True)
    stage(parser.parse_args().stage)
