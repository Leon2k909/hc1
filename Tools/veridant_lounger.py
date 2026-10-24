"""Veridant's upholstered teak loungers, in the existing plan-coordinate footprint.

The back rises away from its hinge at the seat. Cushions have a closed, smoothly
shaded shell, a gently crowned top and piping; the frame is separately assembled.
Run veridant_stage_soft_loungers.py to publish these eight dedicated assemblies.
"""
import math
from pathlib import Path

import numpy as np
from PIL import Image
from scipy.ndimage import gaussian_filter

import riverdale_parts as P
from veridant_lounger_soft import cushion as soft_cushion, timber

PREFIX = "materials/veridant/lounger-v2"
MATERIALS = {f"vr_lounger_{name}": f"{PREFIX}/{name}.vmat"
             for name in ("cloth", "piping", "teak", "teak_light", "teak_dark", "metal", "feet")}
UP = np.array((0., 0., 1.))


cushion = soft_cushion


def build_into(model, c, facing, z0=0., surface="wood"):
    f = P.unit((facing[0], facing[1], 0.))
    s = np.cross(UP, f)
    b = np.array((c[0], c[1], z0), float)
    model.material_overrides.update(MATERIALS)
    model.tile_overrides.update({paint: 12. for paint in MATERIALS})
    phase=math.sin(c[0]*.037+c[1]*.061+z0*.013)*2.1
    wood_index=0

    def at(x, y, z):
        return b + f * x + s * y + UP * z

    def wood(centre, axes, size, tone="teak", bevel=.18):
        nonlocal wood_index
        paint = "vr_lounger_" + tone
        timber(model,centre,axes,size,paint,bevel,phase+wood_index*1.713)
        wood_index+=1

    axes = (f, s, UP)
    for sign in (-1, 1):
        wood(at(0, sign * 12.1, 6.15), axes, (74, 1.8, 3.1), "teak_dark", .22)
        for x in (-32.0, 32.0):
            wood(at(x, sign * 11.8, 3.0), axes, (2.8, 2.3, 5.6), "teak", .22)
            P.bobox(model, at(x, sign * 11.8, .24), f, (2.7, 2.2, .48), "vr_lounger_feet", bevel=.10)
    for x in (-35., -18., 35.):
        wood(at(x, 0, 6.6), axes, (2.2, 23., 2.2), "teak_dark")
    for i, x in enumerate(np.linspace(-14.5, 32.5, 12)):
        wood(at(x, 0, 7.8), axes, (3.5, 22.8, 1.0), ("teak", "teak_light", "teak")[i % 3], .12)
    theta = .9
    bx = f * math.cos(theta) - UP * math.sin(theta)
    bz = np.cross(bx, s)
    pivot = at(-18.9, 0, 7.9)
    back_axes = (bx, s, bz)
    for sign in (-1, 1):
        wood(pivot - bx * 13.2 + s * sign * 11.4, back_axes, (27., 1.5, 1.45), "teak", .18)
        P.tube(model, [at(-31., sign * 10.6, 7.7), pivot - bx * 19.8 + s * sign * 10.6 - bz * .7],
               .32, "vr_lounger_metal", sides=10)
        P.tube(model, [pivot + s * sign * 11.9, pivot + s * sign * 13.05], .49,
               "vr_lounger_metal", sides=16)
        for x in np.linspace(-33, -25, 6):
            P.bobox(model, at(x, sign * 10.6, 7.35), f, (.34, .82, .58), "vr_lounger_metal", bevel=.09)
    for i, x in enumerate(np.linspace(1.1, 25.5, 7)):
        wood(pivot - bx * x, back_axes, (2.95, 22.8, .95), "teak_light" if i % 3 == 1 else "teak", .12)
    soft_cushion(model, at(8.3, .10*math.sin(phase), 9.88), axes, 51.8, 23.8, .7+phase)
    soft_cushion(model, pivot - bx * 13.1 + bz * 2.2+s*.12*math.sin(phase+.9), back_axes, 25.9, 23.8, 2.1+phase)
    # Original gameplay footprint: this visual refresh does not move cover/clips.
    model.oriented_box(b + UP * 8, axes, (76, 26, 16), {}, surface)
    return model


def write_materials(out):
    """Seamless outdoor upholstery and teak textures; no external texture fetches."""
    out = Path(out)
    out.mkdir(parents=True, exist_ok=True)
    rng = np.random.default_rng(94721)
    n = 1024
    y, x = np.mgrid[:n, :n].astype(float)

    def smooth(sigma):
        a = gaussian_filter(rng.normal(size=(n, n)), sigma, mode="wrap")
        return a / max(a.std(), 1e-8)

    def maps(name, colour, height, roughness, tile):
        Image.fromarray(np.clip(colour, 0, 255).astype(np.uint8)).save(out / f"{name}_color.png")
        dx = (np.roll(height, -1, 1) - np.roll(height, 1, 1)) / (2 * tile / n)
        dy = (np.roll(height, -1, 0) - np.roll(height, 1, 0)) / (2 * tile / n)
        normal = np.stack((-dx, dy, np.ones_like(dx)), axis=-1)
        normal /= np.linalg.norm(normal, axis=-1)[..., None]
        Image.fromarray(np.clip((normal * .5 + .5) * 255, 0, 255).astype(np.uint8)).save(out / f"{name}_normal.png")
        Image.fromarray(np.clip(roughness * 255, 0, 255).astype(np.uint8)).save(out / f"{name}_rough.png")

    wx, wy = np.cos(x * 2 * math.pi * 256 / n), np.cos(y * 2 * math.pi * 256 / n)
    weave = .55 * (wx + wy) + .20 * wx * wy
    mottling = .006 * smooth(48) + .005 * smooth(7)
    lum = 1 + mottling + .018 * weave + rng.normal(0, .003, (n, n))
    maps("cloth", lum[..., None] * np.array((211., 205., 192.)), .0040 * weave,
         np.clip(.89 + .025 * weave + .012 * smooth(3), .78, .97), 12.)
    long = smooth((55, 3))
    fine = smooth((19, .7))
    grain = np.sin(x * math.pi / 7 + .8 * smooth((95, 14)))
    lum = 1 + .085 * long + .025 * fine + .028 * grain + .018 * smooth(35)
    maps("teak", lum[..., None] * np.array((127., 101., 76.)), .008 * long + .003 * fine,
         np.clip(.77 + .045 * long + .025 * fine, .58, .92), 8.)
    Image.new("RGB", (16, 16), (128, 128, 255)).save(out / "flat_normal.png")
    Image.new("L", (16, 16), 128).save(out / "flat_rough.png")

    for name in ("cloth", "piping", "teak", "teak_light", "teak_dark", "metal", "feet"):
        tex = "cloth" if name in ("cloth", "piping") else "teak" if name.startswith("teak") else None
        tint = {"piping": (.86, .85, .82), "teak_light": (1.06, 1.04, 1.01), "teak_dark": (.76, .73, .69),
                "metal": (.24, .25, .26), "feet": (.065, .059, .052)}.get(name, (1., 1., 1.))
        if tex:
            textures = (f'{PREFIX}/{tex}_color.png', f'{PREFIX}/{tex}_normal.png', f'{PREFIX}/{tex}_rough.png')
        else:
            textures = ('materials/default/default_color.tga', f'{PREFIX}/flat_normal.png', f'{PREFIX}/flat_rough.png')
        rough = '1' if tex else '0.6' if name == 'metal' else '0.25'
        metal = '.85' if name == 'metal' else '0'
        text = ('// Tools/veridant_lounger.py\n"Layer0"\n{\n'
                '    shader "shaders/complex.shader"\n    F_SPECULAR "1"\n'
                f'    g_flRoughnessScaleFactor "{rough}"\n    g_flMetalness "{metal}"\n'
                f'    TextureColor "{textures[0]}"\n    TextureNormal "{textures[1]}"\n'
                f'    TextureRoughness "{textures[2]}"\n'
                '    TextureAmbientOcclusion "materials/default/default_ao.tga"\n'
                f'    g_vColorTint "[{tint[0]} {tint[1]} {tint[2]} 1]"\n'
                '    g_flModelTintAmount "1.0"\n}\n')
        (out / f"{name}.vmat").write_text(text, encoding="utf-8")

