"""A restrained charcoal path bollard with shielded warm LED apertures.

Plan coordinates and dimensions are inches. Geometry is independent of the map
so a scoped editor import can replace a fixture without rebuilding the scene.
"""
import math
from pathlib import Path

import numpy as np
from PIL import Image
from scipy.ndimage import gaussian_filter

import riverdale_parts as P

PREFIX = 'materials/veridant/modern-lamp-v1'
MATERIALS = {f'vr_modern_lamp_{name}': f'{PREFIX}/{name}.vmat'
             for name in ('charcoal', 'recess', 'led', 'metal')}
X = np.array((1., 0., 0.))
Y = np.array((0., 1., 0.))
Z = np.array((0., 0., 1.))


def build_into(model, base, height=40., collision=True):
    """Closed eased housing, deeply recessed lens, overhang and service panel."""
    b = np.asarray(base, float)
    assert 18 <= height <= 48
    slot = height - 3.8
    shell = 'vr_modern_lamp_charcoal'
    dark = 'vr_modern_lamp_recess'
    led = 'vr_modern_lamp_led'
    metal = 'vr_modern_lamp_metal'

    def block(c, size, paint=shell, bevel=.08):
        P.bevel_box(model, b + np.asarray(c), (X, Y, Z), size, paint, bevel=bevel)

    # The mounting plate fits within the former lamp's nine-inch base footprint.
    block((0, 0, .28), (8.6, 8.6, .56), bevel=.14)
    block((0, 0, .66), (6.45, 6.45, .24), dark, bevel=.05)
    block((0, 0, (slot + .78) / 2), (6.2, 6.2, slot - .78), bevel=.12)
    # Small inset service door and captive screws on the rear, not random damage.
    block((0, -3.106, 6.3), (4.1, .045, 8.2), dark, bevel=.07)
    block((0, -3.139, 6.3), (3.91, .035, 8.01), bevel=.07)
    for z in (3.2, 9.4):
        P.rod(model, b + (0, -3.165, z), b + (0, -3.20, z), .085,
              metal, sides=8, caps=True)
    # A dark central heat sink keeps the lens behind the weather lip.
    block((0, 0, slot + .95), (4.3, 4.3, 1.9), dark, bevel=.04)
    block((0, 0, height - .78), (6.55, 6.55, 1.56), bevel=.12)
    # Four narrow apertures sit .8 inches behind the cap edge. Their downward
    # slant and dark louvres avoid the exposed glowing cube of the old lantern.
    for k in range(4):
        a = k * math.pi / 2
        out = np.array((math.cos(a), math.sin(a), 0.))
        right = np.cross(Z, out)
        c = b + out * 2.35 + Z * (slot + .82)
        low = c - Z * .38 + out * .12
        high = c + Z * .38
        P.card(model, led, [low - right * 2.16, low + right * 2.16,
                            high + right * 2.16, high - right * 2.16], out)
        for z in (slot + .17, slot + 1.46):
            P.bevel_box(model, b + out * 2.62 + Z * z,
                        (right, out, Z), (4.78, .50, .16), dark, bevel=.035)
    # Base screws are dark stainless, not conspicuous decorative gold bolts.
    for e in (-3.55, 3.55):
        for n in (-3.55, 3.55):
            P.rod(model, b + (e, n, .56), b + (e, n, .63), .13,
                  metal, sides=8, caps=True)
    if collision:
        model.collision_box(b + (-3.10, -3.10, .56),
                            b + (3.10, 3.10, height), 'metal')
    model.material_overrides.update(MATERIALS)
    model.tile_overrides.update({p: 8. for p in MATERIALS})
    return {'height': height, 'width': 6.55, 'base_width': 8.6,
            'light_height': slot + .82, 'light_radius': 280.}


def write_materials(directory):
    out = Path(directory)
    out.mkdir(parents=True, exist_ok=True)
    rng = np.random.default_rng(43129)
    noise = gaussian_filter(rng.normal(size=(512, 512)), .65, mode='wrap')
    noise /= noise.std()
    color = np.clip(np.array((36., 38., 38.))[None, None, :] + noise[..., None] * .65, 0, 255)
    Image.fromarray(color.astype('uint8')).save(out / 'charcoal_color.png')
    Image.fromarray(np.clip(150 + noise * 4, 0, 255).astype('uint8')).save(out / 'charcoal_rough.png')
    Image.new('RGB', (16, 16), (128, 128, 255)).save(out / 'flat_normal.png')
    for name in ('charcoal', 'recess', 'led', 'metal'):
        tint = {'charcoal': (1, 1, 1), 'recess': (.035, .039, .039),
                'led': (.88, .69, .44), 'metal': (.22, .24, .24)}[name]
        color = f'{PREFIX}/charcoal_color.png' if name == 'charcoal' else 'materials/default/default_color.tga'
        rough = f'{PREFIX}/charcoal_rough.png' if name == 'charcoal' else '[0.5 0.5 0.5 0]'
        emission = ('    F_SELF_ILLUM "1"\n    TextureSelfIllumMask "[1 1 1 0]"\n'
                    '    g_flSelfIllumBrightness "1.1"\n    g_flSelfIllumAlbedoFactor "1"\n'
                    '    g_vSelfIllumTint "[1 0.82 0.58 1]"\n') if name == 'led' else ''
        text = ('// Tools/veridant_modern_lamp.py\n"Layer0"\n{\n'
                '    shader "shaders/complex.shader"\n    F_SPECULAR "1"\n' + emission +
                f'    g_flMetalness "{.78 if name == "metal" else .0}"\n'
                '    g_flRoughnessScaleFactor "1"\n'
                f'    TextureColor "{color}"\n    TextureNormal "{PREFIX}/flat_normal.png"\n'
                f'    TextureRoughness "{rough}"\n    TextureAmbientOcclusion "materials/default/default_ao.tga"\n'
                f'    g_vColorTint "[{tint[0]} {tint[1]} {tint[2]} 1]"\n'
                '    g_flModelTintAmount "1"\n}\n')
        (out / f'{name}.vmat').write_text(text)
