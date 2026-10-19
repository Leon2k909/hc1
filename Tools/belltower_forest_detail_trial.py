"""Stage a mean-matched forest detail response using the original RGBA atlas.

Only an unreferenced shader/material pair is written under quality output.
The rational response is smooth within the existing modulation limits; its
per-cell coefficients match the accepted response's visible base-level mean.
Box-mip analysis is a source-space proxy, never native BC7 or FPS evidence.
"""
import argparse
import ast
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys

import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'output/belltower/quality/forest-detail-v1'
ATLAS = ROOT / 'Sources/Belltower/generated/forest-trees-v1.png'
ACCEPTED_SHADER = ROOT / 'Assets/shaders/belltower_forest.shader'
ACCEPTED_MATERIAL = ROOT / 'Assets/materials/belltower/forest/forest_trees.vmat'
TRIAL_SHADER = 'shaders/belltower_forest_detail_trial.shader'
TRIAL_MATERIAL = 'materials/belltower/forest/trials/forest_detail_v1.vmat'
CHROMA_STRENGTH = .8


def sha(path):
    with Path(path).open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def srgb_to_linear(rgb):
    return np.where(rgb <= .04045, rgb / 12.92, ((rgb + .055) / 1.055) ** 2.4)


def old_response(luma):
    return .35 + .65 * np.clip(luma / .08, .25, 2)


def response(luma, knee):
    signal = luma * luma
    return .5125 + 1.1375 * signal / (signal + knee)


def source_chroma(rgb, luma, alpha):
    # Generated semi-transparent fringes can contain unreliable RGB. Colour
    # detail comes from opaque interiors; soft edges retain the terrain tint.
    confidence = np.clip((alpha - .65) / .30, 0, 1)
    confidence = confidence * confidence * (3 - 2 * confidence)
    ratio = np.clip(rgb / np.maximum(luma[:, None], .005), .2, 3)
    return ratio, confidence


def rectangle(field, rect):
    h, w = field.shape[:2]
    u0, v0, u1, v1 = rect
    return field[int(v0 * h):int(v1 * h), int(u0 * w):int(u1 * w)]


def regions():
    source = ast.parse((ROOT / 'Tools/belltower_quality_forest.py').read_text(encoding='utf-8'))
    return next(ast.literal_eval(node.value) for node in source.body if isinstance(node, ast.Assign)
                and any(isinstance(target, ast.Name) and target.id == 'RECTS' for target in node.targets))


def visible(field, rect):
    cell = rectangle(field, rect)
    mask = cell[:, :, 1] >= .35
    return cell[:, :, 0][mask], cell[:, :, 1][mask]


def calibration():
    with Image.open(ATLAS) as image:
        assert image.mode == 'RGBA'
        dimensions = list(image.size)
        source = np.asarray(image, dtype=np.float64) / 255
    linear = srgb_to_linear(source[:, :, :3])
    luma = linear @ np.array([.2126, .7152, .0722])
    field = np.stack((luma, source[:, :, 3]), axis=2)
    colours = np.concatenate((linear, source[:, :, 3:4]), axis=2)
    rects = regions()
    knees, cells, chroma_means = [], [], []
    for index, rect in enumerate(rects):
        values, weights = visible(field, rect)
        target = float(np.average(old_response(values), weights=weights))
        low, high = 1e-10, 1.0
        for _ in range(60):
            mid = (low + high) / 2
            if np.average(response(values, mid), weights=weights) > target:
                low = mid
            else:
                high = mid
        knee = float(np.float32((low + high) / 2))
        knees.append(knee)
        candidate = response(values, knee)
        current = old_response(values)
        colour_cell = rectangle(colours, rect)
        rgb = colour_cell[:, :, :3][colour_cell[:, :, 3] >= .35]
        chroma, confidence = source_chroma(rgb, values, weights)
        colour_weights = candidate * confidence * weights
        assert colour_weights.sum() > 0
        mean_chroma = np.average(chroma, weights=colour_weights, axis=0)
        mean_chroma = mean_chroma.astype(np.float32)
        chroma_means.append(mean_chroma.tolist())
        rgb_response = candidate[:, None] * (1 + CHROMA_STRENGTH * confidence[:, None] * (chroma / mean_chroma - 1))
        cells.append(dict(variant=index, used_by_current_geometry=index != 2, knee=knee,
                          current_mean=target, candidate_mean=float(np.average(candidate, weights=weights)),
                          candidate_rgb_mean=np.average(rgb_response, weights=weights, axis=0).tolist(),
                          current_clipped_fraction=float(np.mean((values <= .02) | (values >= .16))),
                          highlight_std_before=float(np.std(current[values >= .16])),
                          highlight_std_after=float(np.std(candidate[values >= .16])),
                          shadow_std_before=float(np.std(current[values <= .02])),
                          shadow_std_after=float(np.std(candidate[values <= .02]))))
    mips = []
    for level in range(8):
        rows = []
        for index, rect in enumerate(rects):
            values, weights = visible(field, rect)
            before = float(np.average(old_response(values), weights=weights))
            after = float(np.average(response(values, knees[index]), weights=weights))
            colour_cell = rectangle(colours, rect)
            rgb = colour_cell[:, :, :3][colour_cell[:, :, 3] >= .35]
            chroma, confidence = source_chroma(rgb, values, weights)
            chroma = chroma / np.asarray(chroma_means[index])
            rgb_response = response(values, knees[index])[:, None] * (1 + CHROMA_STRENGTH * confidence[:, None] * (chroma - 1))
            rgb_mean = np.average(rgb_response, weights=weights, axis=0)
            rows.append(dict(variant=index, current_mean=before, candidate_mean=after,
                             relative_mean_drift=after / before - 1,
                             relative_rgb_mean_drift=(rgb_mean / before - 1).tolist()))
        h, w = field.shape[:2]
        mips.append(dict(level=level, dimensions=[w, h], variants=rows))
        h2, w2 = h // 2 * 2, w // 2 * 2
        if min(h2, w2) < 4:
            break
        field = field[:h2, :w2].reshape(h2 // 2, 2, w2 // 2, 2, 2).mean(axis=(1, 3))
        colours = colours[:h2, :w2].reshape(h2 // 2, 2, w2 // 2, 2, 4).mean(axis=(1, 3))
    return dict(atlas_dimensions=dimensions, rectangles=rects, coefficients=knees, cells=cells,
                chroma_means=chroma_means, chroma_strength=CHROMA_STRENGTH,
                mip_proxy=mips, mip_scope='Uncompressed linear box-mip source analysis, not native BC7 or rendering.',
                quadrant_split=[(rects[0][2] + rects[1][0]) / 2, (rects[0][3] + rects[2][1]) / 2])


def preview_colour():
    # One actual nearby forest position supplies the diagnostic's constant
    # canopy colour. Lighting, fog, spatial variation and BC7 remain native QA.
    crowns = np.load(ROOT / 'output/belltower/quality/parcel-v4-forest/crowns.npy', mmap_mode='r')
    e, n = crowns[:, 0], crowns[:, 1]
    reach = np.maximum.reduce((-2380 - e, e - 2380, -1466 - n, n - 1800, np.zeros(len(e))))
    indices = np.flatnonzero((reach > 3500) & (reach < 5000))
    index = int(indices[len(indices) // 2])
    plan = np.asarray(crowns[index, :2])
    uv = (plan - [-8380., 7800.]) * [1 / 16760., -1 / 15266.]
    with Image.open(ROOT / 'Assets/materials/belltower/vista/vista_b_color.jpg') as image:
        x, y = np.rint(uv * np.array(image.size)).astype(int)
        sample = np.asarray(image.crop((x - 16, y - 16, x + 17, y + 17)).convert('RGB'), dtype=float) / 255
    return dict(source='Assets/materials/belltower/vista/vista_b_color.jpg', forest_position=plan.tolist(),
                linear_rgb=srgb_to_linear(sample).mean(axis=(0, 1)).tolist(),
                scope='Unlit albedo diagnostic only; constant colour sampled near a real forest card.')


def stage():
    OUT.mkdir(parents=True, exist_ok=True)
    assert sha(ATLAS) == sha(ROOT / 'Assets/materials/belltower/forest/forest-trees-v1.png'), 'Calibration atlas differs from the live texture input'
    assert 'g_flAlphaTestReference "0.35"' in ACCEPTED_MATERIAL.read_text(), 'Review calibration after an alpha-cutoff change'
    data = calibration()
    shader = ACCEPTED_SHADER.read_text(encoding='utf-8')
    needle = '        float leafDetail = clamp( dot( plant.rgb, float3( .2126, .7152, .0722 ) ) / .08, .25, 2.0 );'
    assert shader.count(needle) == 1
    default = ', '.join(f'{value:.10g}' for value in data['coefficients'])
    parameters = ('    float4 g_vCanopyDetailKnee < Default4( ' + default + ' ); UiGroup( "Canopy detail,21/10" ); >;\n'
                  '    float g_flCanopyDetailBlend < Default( 1 ); Range( 0, 1 ); UiGroup( "Canopy detail,21/20" ); >;\n')
    for index, mean in enumerate(data['chroma_means']):
        values = ', '.join(f'{value:.10g}' for value in mean) + ', 1'
        parameters += f'    float4 g_vCanopyChromaMean{index} < Default4( {values} ); UiGroup( "Canopy detail,21/{30 + index}" ); >;\n'
    parameters += '    float g_flCanopyChromaDetail < Default( .8 ); Range( 0, 1 ); UiGroup( "Canopy detail,21/40" ); >;\n'
    marker = '    float g_flCanopyBrightness '
    assert shader.count(marker) == 1
    shader = shader.replace(marker, parameters + marker)
    x, y = data['quadrant_split']
    replacement = f'''        float sourceLuma = dot( plant.rgb, float3( .2126, .7152, .0722 ) );
        float oldDetail = clamp( sourceLuma / .08, .25, 2.0 );
        // The UV windows remain within their original source-image cells.
        // Match each cell's mean, retaining variation inside the old limits.
        float rightCell = step( {x:.8g}, i.vTextureCoords.x );
        float bottomCell = step( {y:.8g}, i.vTextureCoords.y );
        float knee = lerp( lerp( g_vCanopyDetailKnee.x, g_vCanopyDetailKnee.y, rightCell ),
                           lerp( g_vCanopyDetailKnee.z, g_vCanopyDetailKnee.w, rightCell ), bottomCell );
        float signal = sourceLuma * sourceLuma;
        float smoothDetail = .25 + 1.75 * signal / ( signal + max( knee, 0.000001 ) );
        float3 sourceChroma = clamp( plant.rgb / max( sourceLuma, .005 ), .2, 3.0 );
        float3 meanChroma = lerp( lerp( g_vCanopyChromaMean0.xyz, g_vCanopyChromaMean1.xyz, rightCell ),
                                 lerp( g_vCanopyChromaMean2.xyz, g_vCanopyChromaMean3.xyz, rightCell ), bottomCell );
        float chromaConfidence = smoothstep( .65, .95, plant.a ) * saturate( g_flCanopyChromaDetail );
        float3 chroma = lerp( float3( 1, 1, 1 ), sourceChroma / max( meanChroma, .01 ), chromaConfidence );
        float oldResponse = lerp( 1.0, oldDetail, .65 );
        float3 smoothResponse = lerp( 1.0, smoothDetail, .65 ) * chroma;
        // Return toward the accepted tint as the existing distant cards fade.
        float3 canopyDetail = lerp( float3( oldResponse, oldResponse, oldResponse ), smoothResponse, saturate( g_flCanopyDetailBlend ) * fade );'''
    shader = shader.replace(needle, replacement)
    old_albedo = '        m.Albedo = saturate( canopy * lerp( 1.0, leafDetail, .65 ) * g_flCanopyBrightness );'
    new_albedo = '        m.Albedo = saturate( canopy * canopyDetail * g_flCanopyBrightness );'
    assert shader.count(old_albedo) == 1
    shader = shader.replace(old_albedo, new_albedo)
    shader = shader.replace('Belltower distant woodland with the original generated RGBA atlas',
                            'Belltower mean-matched canopy detail trial; original RGBA atlas')
    restored = shader.replace(parameters, '').replace(replacement, needle).replace(new_albedo, old_albedo)
    restored = restored.replace('Belltower mean-matched canopy detail trial; original RGBA atlas',
                                'Belltower distant woodland with the original generated RGBA atlas')
    assert restored == ACCEPTED_SHADER.read_text(encoding='utf-8'), 'Shader edits extend beyond albedo response and its parameters'
    material = ACCEPTED_MATERIAL.read_text(encoding='utf-8')
    assert material.count('shader "shaders/belltower_forest.shader"') == 1
    material = material.replace('shader "shaders/belltower_forest.shader"', f'shader "{TRIAL_SHADER}"')
    material = material.replace('\n}', '\n    g_vCanopyDetailKnee "[' + ' '.join(f'{value:.10g}' for value in data['coefficients']) +
                                ']"\n    g_flCanopyDetailBlend "1"\n}')
    colour_parameters = ''
    for index, mean in enumerate(data['chroma_means']):
        colour_parameters += f'    g_vCanopyChromaMean{index} "[' + ' '.join(f'{value:.10g}' for value in mean) + ' 1]"\n'
    colour_parameters += f'    g_flCanopyChromaDetail "{CHROMA_STRENGTH}"\n'
    material = material.replace('\n}', '\n' + colour_parameters + '}')
    files = []
    for relative, value in ((TRIAL_SHADER, shader), (TRIAL_MATERIAL, material)):
        path = OUT / 'Assets' / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(value, encoding='utf-8', newline='\n')
        live = ROOT / 'Assets' / relative
        assert not live.exists() or sha(live) == sha(path), 'Different trial resource already exists'
        files.append(dict(path=relative, source=path.relative_to(ROOT).as_posix(), sha256=sha(path)))
    dependencies = [Path(__file__), ATLAS, ACCEPTED_SHADER, ACCEPTED_MATERIAL,
                    ROOT / 'Tools/belltower_quality_forest.py', ROOT / 'Sources/Belltower/landscape/forest.json',
                    ROOT / 'Assets/scenes/maps/Belltower/belltower.scene',
                    ROOT / 'output/belltower/quality/parcel-v4-forest/crowns.npy']
    dependencies += [ROOT / 'Assets' / path for path in re.findall(r'"(materials/[^"\n]+\.(?:png|jpg))"', ACCEPTED_MATERIAL.read_text())]
    dependencies = sorted(set(dependencies))
    data['preview_colour'] = preview_colour()
    data['scope'] = 'Source response calibration and shader staging; native compile, visuals and performance unverified.'
    (OUT / 'calibration.json').write_text(json.dumps(data, indent=2) + '\n', encoding='utf-8')
    manifest = dict(revision='forest-detail-v1', files=files,
                    source_sha256={path.relative_to(ROOT).as_posix(): sha(path) for path in dependencies},
                    calibration_sha256=sha(OUT / 'calibration.json'),
                    material_overrides={'materials/belltower/forest/forest_trees.vmat': TRIAL_MATERIAL},
                    texture_inputs_changed=False, geometry_changed=False, scene_changed=False,
                    lighting_alpha_normals_and_fog_unchanged=True,
                    colour_detail_fades_with_existing_card_fade=True, native_verified=False)
    (OUT / 'manifest.json').write_text(json.dumps(manifest, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(dict(files=len(files), coefficients=data['coefficients'], textures_changed=False, geometry_changed=False)))


def render():
    blender = shutil.which('blender')
    if not blender:
        choices = sorted((Path(os.environ.get('ProgramFiles', 'C:/Program Files')) / 'Blender Foundation').glob('*/blender.exe'))
        assert choices, 'Blender is not installed'
        blender = str(choices[-1])
    with (OUT / 'render.log').open('w', encoding='utf-8') as log:
        command = [blender, '--background', '--factory-startup', '--threads', '2', '--python-exit-code', '1',
                   '--python', str(ROOT / 'Tools/belltower_forest_detail_preview.py')]
        process = subprocess.Popen(command, cwd=ROOT, stdout=log, stderr=subprocess.STDOUT,
                                   creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0)
        print('Forest detail renderer PID', process.pid, flush=True)
        try:
            code = process.wait()
        finally:
            if process.poll() is None:
                process.terminate()
                process.wait(timeout=10)
        print('Forest detail renderer exit', code, flush=True)
        if code:
            raise SystemExit(code)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--render-only', action='store_true')
    args = parser.parse_args()
    render() if args.render_only else stage()
