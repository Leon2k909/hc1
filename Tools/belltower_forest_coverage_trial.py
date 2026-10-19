"""Stage a forest alpha-mip experiment; preserve accepted assets and source pixels."""
import hashlib
import json
import math
import os
from pathlib import Path

import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'output/belltower/quality/forest-coverage-v1'
SHADER = 'shaders/belltower_forest_coverage_trial.shader'
MATERIAL = 'materials/belltower/forest/trials/forest_coverage_v1.vmat'
RECTS = ((.006, .004, .553, .532), (.557, .004, .998, .532),
         (.006, .546, .553, .987), (.557, .546, .998, .987))
PARAMETER = '    float g_flCanopyMipCompensation < Default( 1 ); Range( 0, 1 ); UiGroup( "Canopy coverage,22/10" ); >;\n'
OPACITY = '''        float canopyAlpha = plant.a * fade;
        // The engine subsequently multiplies alpha by (1 + .25 * mip).
        // Cancel only the requested share of that boost. Strength one takes
        // the untouched accepted path; mip zero is unchanged at every strength.
        [branch] if( g_flCanopyMipCompensation < 1.0 )
        {
            float2 texels = m.TextureCoords.xy * float2( TextureDimensions2DS( g_tPlants, 0 ) );
            float2 texelDx = ddx( texels );
            float2 texelDy = ddy( texels );
            float mip = max( 0.0, .5 * log2( max( max( dot( texelDx, texelDx ), dot( texelDy, texelDy ) ), .00000001 ) ) );
            float fullCorrection = 1.0 + .25 * mip;
            float requestedCorrection = 1.0 + .25 * mip * saturate( g_flCanopyMipCompensation );
            canopyAlpha *= requestedCorrection / fullCorrection;
        }
        m.Opacity = canopyAlpha;
'''


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def engine_root():
    value = os.environ.get('FACEPUNCH_ENGINE')
    if not value:
        import winreg
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, 'Environment') as key:
            value = winreg.QueryValueEx(key, 'FACEPUNCH_ENGINE')[0]
    return Path(value)


def alpha_proxy(atlas):
    image = Image.open(atlas).getchannel('A').convert('F')
    levels = []
    for level in range(9):
        alpha = np.asarray(image) / 255
        variants = []
        for variant, (u0, v0, u1, v1) in enumerate(RECTS):
            cell = alpha[math.floor(v0 * image.height):math.ceil(v1 * image.height),
                         math.floor(u0 * image.width):math.ceil(u1 * image.width)]
            variants.append(dict(variant=variant, alpha_mean=float(cell.mean()),
                                 coverage={str(strength): float((cell * (1 + .25 * level * strength) >= .35).mean())
                                           for strength in (0, .5, 1)}))
        levels.append(dict(level=level, dimensions=image.size, variants=variants))
        image = image.resize((max(1, image.width // 2), max(1, image.height // 2)), Image.Resampling.BOX)
    return dict(scope='Source linear-alpha box-mip proxy, not native BC7, MSAA or rasterization.', levels=levels)


def main():
    engine = engine_root()
    references = ['core/shaders/vr_common.fxc', 'core/shaders/common/shadingmodel.hlsl']
    common = (engine / references[0]).read_text(encoding='utf-8')
    compact = ''.join(common.split())
    assert 'floatflCompensatedOpacity=flOpacity*(1.0+flMipLevel*0.25);' in compact
    assert 'clip(flCompensatedOpacity-flAlphaTestReference);' in compact
    accepted = ROOT / 'Assets/shaders/belltower_forest.shader'
    original = accepted.read_text(encoding='utf-8')
    description = 'Belltower distant woodland with the original generated RGBA atlas'
    trial_description = 'Belltower forest mip-coverage comparison; original atlas and accepted lighting'
    shader = original.replace(description, trial_description)
    marker = '    float g_flCanopyBrightness'
    assert shader.count(marker) == 1 and shader.count('        m.Opacity = plant.a * fade;\n') == 1
    shader = shader.replace(marker, PARAMETER + marker)
    shader = shader.replace('        m.Opacity = plant.a * fade;\n', OPACITY)
    restored = shader.replace(trial_description, description).replace(PARAMETER, '').replace(OPACITY, '        m.Opacity = plant.a * fade;\n')
    assert restored == original, 'The trial changes more than its explicit coverage controls'
    assert shader.count('.Sample(') == original.count('.Sample(')
    assert shader.count('.SampleLevel(') == original.count('.SampleLevel(')
    material_path = ROOT / 'Assets/materials/belltower/forest/forest_trees.vmat'
    original_material = material_path.read_text(encoding='utf-8')
    assert original_material.count('shaders/belltower_forest.shader') == 1
    material = original_material.replace('shaders/belltower_forest.shader', SHADER)
    material = material.rsplit('}', 1)[0] + '    g_flCanopyMipCompensation "1"\n}\n'
    assert material.replace('    g_flCanopyMipCompensation "1"\n', '').replace(SHADER, 'shaders/belltower_forest.shader').rstrip() == original_material.rstrip()
    for relative, content in ((SHADER, shader), (MATERIAL, material)):
        path = OUT / 'Assets' / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding='utf-8')
    inputs = [accepted, material_path, ROOT / 'Sources/Belltower/generated/forest-trees-v1.png',
              ROOT / 'Assets/materials/belltower/forest/forest-trees-v1.png',
              ROOT / 'Assets/scenes/maps/Belltower/belltower.scene',
              ROOT / 'Sources/Belltower/landscape/forest.json', ROOT / 'Tools/belltower_quality_forest.py', Path(__file__)]
    inputs += sorted((ROOT / 'Assets/materials/belltower/vista').glob('vista_[bcd]_color.jpg'))
    inputs += sorted((ROOT / 'Assets/materials/belltower/vista').glob('vista_[bcd]_normal.jpg'))
    manifest = dict(revision='forest-coverage-v1', files=[dict(path=p, source=(OUT / 'Assets' / p).relative_to(ROOT).as_posix(),
                    sha256=sha(OUT / 'Assets' / p)) for p in (SHADER, MATERIAL)],
                    source_sha256={p.relative_to(ROOT).as_posix(): sha(p) for p in inputs},
                    engine_source_sha256={p: sha(engine / p) for p in references},
                    material_overrides={'materials/belltower/forest/forest_trees.vmat': MATERIAL},
                    comparison_strengths=[1, .5, 0], accepted_response_strength=1,
                    geometry_changed=False, texture_inputs_changed=False, scene_changed=False, native_verified=False)
    (OUT / 'manifest.json').write_text(json.dumps(manifest, indent=2) + '\n', encoding='utf-8')
    analysis = alpha_proxy(ROOT / 'Sources/Belltower/generated/forest-trees-v1.png')
    (OUT / 'alpha-mip-proxy.json').write_text(json.dumps(analysis, indent=2) + '\n', encoding='utf-8')
    # Exercise the cancellation equation across continuous mip levels, not only
    # the few levels represented by the image proxy. This is not a GPU test.
    mip = np.linspace(0, 16, 65536, dtype=np.float32)
    engine_boost = 1 + .25 * mip
    for strength in (0, .5, 1):
        requested = 1 + .25 * mip * strength
        scale = requested / engine_boost
        assert np.isfinite(scale).all() and np.all((scale > 0) & (scale <= 1))
        assert np.max(np.abs(scale * engine_boost - requested)) < 1e-6
        if strength == 1:
            assert np.array_equal(scale, np.ones_like(scale))
        assert scale[0] == 1
    checks = dict(passed=True, manifest_sha256=sha(OUT / 'manifest.json'),
                  checker_sha256=sha(Path(__file__)), accepted_shader_roundtrip_exact=True, accepted_material_properties_preserved=True,
                  strength_one_uses_accepted_path=True, mip_zero_unchanged=True,
                  extra_texture_samples=0, source_pixels_changed=False,
                  scope='Source and arithmetic checks only; native shader compilation and appearance are unverified.',
                  native_verified=False)
    (OUT / 'checks.json').write_text(json.dumps(checks, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(dict(staged_assets=2, manifest_sha256=checks['manifest_sha256'], source_checks_passed=True,
                          native_verified=False, accepted_assets_written=False)))


if __name__ == '__main__':
    main()
