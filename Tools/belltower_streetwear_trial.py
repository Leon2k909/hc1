"""Stage a non-destructive Belltower cobblestone variation trial.

The current 2-metre cobblestone scan and parallax relief are kept intact. A
cheap, continuous world-position field gently darkens broad worn areas so the
same scan does not make an entire street look uniformly clean. The new shader
and material have separate names, allowing native baseline/candidate captures
without replacing accepted resources or changing gameplay geometry.

    python Tools/belltower_streetwear_trial.py [--install]

Without --install, write a standalone candidate and a synthetic flat-material
comparison to output/belltower/quality/streetwear-v1. --install copies only new
resources into Assets so the editor can compile and compare them.
"""
import argparse
import hashlib
import json
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont

import belltower_quality_materials as Materials

ROOT = Path(__file__).resolve().parents[1]
STAGE = ROOT / "output/belltower/quality/streetwear-v1"
ACCEPTED_SHADER = ROOT / "Assets/shaders/belltower_relief.shader"
ACCEPTED_MATERIAL = ROOT / "Assets/materials/belltower/street_cobbles.vmat"
STONE_IMAGE = ROOT / "Assets/materials/stone/cobble_stones_tight_basecolor.png"
TRIAL_SHADER = "shaders/belltower_streetwear_trial.shader"
TRIAL_MATERIAL = "materials/belltower/trials/street_cobbles_aaa.vmat"
STRENGTH = .22
SMALL_SCALE = 230.0
LARGE_SCALE = 690.0

SHADER_INPUTS = """    // Two terrain-scale masks add subtle non-periodic variation across the
    // entire town, independently of the repeating photographed stone UVs.
    float g_flStreetWearStrength < Default( 0 ); Range( 0, .35 ); UiGroup( "Street wear,30/10" ); >;
    float2 g_vStreetWearScale < Default2( 230, 690 ); UiGroup( "Street wear,30/20" ); >;

    float StreetHash( float2 p )
    {
        float3 v = frac( float3( p.x, p.y, p.x ) * .1031 );
        v += dot( v, v.yzx + 33.33 );
        return frac( ( v.x + v.y ) * v.z );
    }

    float StreetNoise( float2 point )
    {
        float2 cell = floor( point );
        float2 blend = frac( point );
        blend = blend * blend * ( 3.0 - 2.0 * blend );
        float low = lerp( StreetHash( cell ), StreetHash( cell + float2( 1, 0 ) ), blend.x );
        float high = lerp( StreetHash( cell + float2( 0, 1 ) ), StreetHash( cell + float2( 1, 1 ) ), blend.x );
        return lerp( low, high, blend.y );
    }
"""

STREET_WEAR = """        // Patina follows world position, not the 2-metre scan tile; no abrupt
        // boundaries appear at mesh edges or between the mirrored town halves.
        [branch] if ( g_flStreetWearStrength > .001 )
        {
            float2 world = m.WorldPosition.xy;
            float coarse = StreetNoise( ( world + float2( 127, -301 ) ) / max( g_vStreetWearScale.y, 1 ) );
            float fine = StreetNoise( ( world + float2( -421, 187 ) ) / max( g_vStreetWearScale.x, 1 ) );
            float patina = smoothstep( .25, .73, coarse * .62 + fine * .38 );
            m.Albedo *= 1.0 - g_flStreetWearStrength * patina;
        }
"""


def sha(data):
    if isinstance(data, Path):
        data = data.read_bytes()
    if isinstance(data, str):
        data = data.encode("utf-8")
    return hashlib.sha256(data).hexdigest()


def shader_text():
    source = ACCEPTED_SHADER.read_text(encoding="utf-8")
    assert source.count('    // White is the stone\'s crest') == 1
    assert source.count('        m.Albedo = color.rgb * g_flTintColor * i.vVertexColor.rgb;') == 1
    # The separate shader gets a new identity without modifying the original.
    source = source.replace('Description = "Belltower scanned stone: shallow parallax relief at physical scale";',
                            'Description = "Belltower scanned street stone: world-space dry patina trial";')
    source = source.replace('    // White is the stone\'s crest', SHADER_INPUTS + '\n    // White is the stone\'s crest')
    source = source.replace('        m.Albedo = color.rgb * g_flTintColor * i.vVertexColor.rgb;',
                            '        m.Albedo = color.rgb * g_flTintColor * i.vVertexColor.rgb;\n' + STREET_WEAR)
    assert source.count('    float StreetNoise(') == 1
    assert source.count('float patina = smoothstep(') == 1
    return source


def material_text():
    source = Materials.material_text("street_cobbles")
    assert source is not None
    assert source.count('shader "shaders/belltower_relief.shader"') == 1
    source = source.replace('shader "shaders/belltower_relief.shader"', f'shader "{TRIAL_SHADER}"')
    source = source.replace('\n}', f'\n    g_flStreetWearStrength "{STRENGTH}"\n'
                            f'    g_vStreetWearScale "[{SMALL_SCALE:g} {LARGE_SCALE:g}]"\n}}')
    return source


def noise(point):
    """Vectorised mirror of the candidate's hash and smooth interpolation."""
    cell = np.floor(point)
    blend = point - cell
    blend = blend * blend * (3 - 2 * blend)

    def hashed(p):
        v = np.mod(np.stack((p[..., 0], p[..., 1], p[..., 0]), axis=-1) * .1031, 1.0)
        v += np.sum(v * (v[..., [1, 2, 0]] + 33.33), axis=-1)[..., None]
        return np.mod((v[..., 0] + v[..., 1]) * v[..., 2], 1.0)

    d10 = np.array((1, 0))
    d01 = np.array((0, 1))
    a = hashed(cell) * (1 - blend[..., 0]) + hashed(cell + d10) * blend[..., 0]
    b = hashed(cell + d01) * (1 - blend[..., 0]) + hashed(cell + d10 + d01) * blend[..., 0]
    return a * (1 - blend[..., 1]) + b * blend[..., 1]


def variation(world):
    coarse = noise((world + [127, -301]) / LARGE_SCALE)
    fine = noise((world + [-421, 187]) / SMALL_SCALE)
    t = np.clip((coarse * .62 + fine * .38 - .25) / (.73 - .25), 0, 1)
    return t * t * (3 - 2 * t)


def flat_preview(destination):
    """Flat synthetic stone: shows only the material idea, not a native render."""
    width, height = 880, 540
    x = np.linspace(-950, 950, width, dtype=np.float64)
    y = np.linspace(-580, 580, height, dtype=np.float64)
    east, north = np.meshgrid(x, y)
    world = np.stack((north, -east), axis=-1)
    with Image.open(STONE_IMAGE) as src:
        base = np.asarray(src.convert("RGB"), dtype=np.uint8)
    h, w = base.shape[:2]
    # Existing generator: one base UV tile per 256 inches, multiplied by
    # g_vStoneUvScale 3.2512. This is a plan-view approximation only.
    uu = np.mod(east / 256 * 3.2512, 1.0)
    vv = np.mod(north / 256 * 3.2512, 1.0)
    pixels = base[np.floor(vv * h).astype(np.int32) % h, np.floor(uu * w).astype(np.int32) % w]
    tint = np.array((.92, .93, .92), dtype=np.float32)
    original = np.clip(pixels.astype(np.float32) * tint, 0, 255).astype(np.uint8)
    field = variation(world)
    # Approximate the native linear-albedo multiplier as gamma-compressed sRGB.
    target = np.clip(original * np.power(1 - STRENGTH * field[..., None], 1 / 2.2), 0, 255).astype(np.uint8)
    canvas = Image.new("RGB", (width * 2 + 40, height + 80), "#1d2428")
    canvas.paste(Image.fromarray(original), (10, 50))
    canvas.paste(Image.fromarray(target), (width + 30, 50))
    draw = ImageDraw.Draw(canvas)
    font = ImageFont.truetype("C:/Windows/Fonts/arial.ttf", 18) if Path("C:/Windows/Fonts/arial.ttf").exists() else ImageFont.load_default()
    draw.text((16, 13), "Existing repeated cobbles", font=font, fill="#eeeeee")
    draw.text((width + 36, 13), "Trial: larger-scale dry patina", font=font, fill="#eeeeee")
    draw.text((12, height + 57), "Offline shader approximation | real-time engine review required", font=font, fill="#ffffff")
    canvas.save(destination)
    return {'wear_min': float(field.min()), 'wear_mean': float(field.mean()), 'wear_max': float(field.max()),
            'max_linear_darkening': STRENGTH, 'res': [width, height]}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--install', action='store_true', help='Install new trial resources; never overwrite existing assets')
    args = parser.parse_args()
    STAGE.mkdir(parents=True, exist_ok=True)
    shader, material = shader_text(), material_text()
    stage_files = [(TRIAL_SHADER, STAGE / Path(TRIAL_SHADER).name, shader),
                   (TRIAL_MATERIAL, STAGE / Path(TRIAL_MATERIAL).name, material)]
    manifest = []
    for relative, path, value in stage_files:
        path.write_text(value, encoding='utf-8', newline='\n')
        target = ROOT / 'Assets' / relative
        installed = None
        if args.install:
            target.parent.mkdir(parents=True, exist_ok=True)
            if target.exists() and sha(target) != sha(value):
                raise RuntimeError('Different trial resource already installed: ' + relative)
            if not target.exists():
                target.write_text(value, encoding='utf-8', newline='\n')
            installed = sha(target)
        manifest.append({'resource': relative, 'staged': str(path.relative_to(ROOT)).replace('\\','/'),
                         'sha256': sha(value), 'installed_sha256': installed})
    stats = flat_preview(STAGE / 'streetwear-comparison.png')
    report = {'revision': 'streetwear-v1', 'state': 'staged for native comparison',
              'original': {str(p.relative_to(ROOT)).replace('\\','/'): sha(p) for p in (ACCEPTED_SHADER, ACCEPTED_MATERIAL, STONE_IMAGE)},
              'trial': manifest, 'strength': STRENGTH, 'scales_in_inches': [SMALL_SCALE, LARGE_SCALE],
              'preview': stats, 'changes_to_live_model_or_collision': False,
              'note': 'New unreferenced trial resources only; native rendering, quality and perf unverified.'}
    (STAGE / 'manifest.json').write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
    print(json.dumps({'stage': str(STAGE.relative_to(ROOT)), 'trial_assets_installed': args.install,
                      'preview': stats, 'resources': [x['resource'] for x in manifest]}))


if __name__ == '__main__':
    main()
