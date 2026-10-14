"""Stage physical paving relief without changing the installed Lowtide material.

The generated granite colour image and existing UV layout remain unchanged.
Derived height, normals and joint AO describe a shallow nine-millimetre surface.
Run this staging command only; the editor imports and previews the candidate.
"""
import argparse
import hashlib
import json
from pathlib import Path

import numpy as np
from PIL import Image
from scipy import ndimage

import lowtide_paving as P
import map_kit as K
import terrain_textures as T

DEPTH_MM = 9.0
RESOURCE = "materials/lowtide/paving_relief/lt_setts"
SHADER = "shaders/hc1_lowtide_paving_relief.shader"


def surface_maps(rgb, scale, region):
    """Return numerical PBR maps at the source image's exact pixel registration."""
    atlas = 1 << int(np.ceil(np.log2(rgb.shape[0])))
    # A repeat spans 64/scale inches, but occupies only region.zw of the atlas.
    # Consequently every original source pixel has this physical footprint.
    mm_pixel = P.TILE_UNITS * 25.4 / (np.asarray(scale) * np.asarray(region[2:]) * atlas)
    luminance = rgb @ np.array([.2126, .7152, .0722], dtype=np.float32)
    smooth = ndimage.gaussian_filter(luminance, 2.5, mode="wrap")
    tops = ndimage.binary_closing(smooth > .355, iterations=2, border_value=1)
    tops = ndimage.binary_fill_holes(tops)
    inside = ndimage.distance_transform_edt(tops, sampling=mm_pixel[::-1])
    outside = ndimage.distance_transform_edt(~tops, sampling=mm_pixel[::-1])
    crest = T.smoothstep(-1.2, 4.5, inside - outside)
    grain = luminance - ndimage.gaussian_filter(luminance, 1.4, mode="wrap")
    # Wear rounds the arris, while the interior stays flat: colour differences
    # between adjacent granites must not become inflated or sunken stone tops.
    height_mm = np.clip(.35 + crest * 8.4 + grain * crest * .45, 0, DEPTH_MM)
    dx = (np.roll(height_mm, -1, 1) - np.roll(height_mm, 1, 1)) / (2 * mm_pixel[0])
    dy = (np.roll(height_mm, -1, 0) - np.roll(height_mm, 1, 0)) / (2 * mm_pixel[1])
    normal = np.stack([-dx, dy, np.ones_like(height_mm)], axis=-1)
    normal /= np.linalg.norm(normal, axis=-1, keepdims=True)
    ao = .65 + .35 * np.sqrt(crest)
    maps = {
        "normal": np.rint((normal + 1) * 127.5).clip(0, 255).astype(np.uint8),
        "height": np.rint(height_mm / DEPTH_MM * 255).clip(0, 255).astype(np.uint8),
        "ao": np.rint(ao * 255).clip(0, 255).astype(np.uint8),
    }
    report = dict(depth_mm=DEPTH_MM, millimetres_per_pixel=mm_pixel.tolist(),
        crest_fraction=float(np.mean(crest > .95)), joint_fraction=float(np.mean(crest < .1)),
        normal_length_range=[float(np.linalg.norm(normal, axis=-1).min()),
                             float(np.linalg.norm(normal, axis=-1).max())],
        height_mm_range=[float(height_mm.min()), float(height_mm.max())])
    assert np.isfinite(normal).all() and np.isfinite(height_mm).all()
    assert .55 < report["crest_fraction"] < .93, report
    assert .025 < report["joint_fraction"] < .25, report
    return maps, report


def material_text(scale, region):
    values = " ".join(f"{n:.8f}" for n in region)
    return f'''// Tools/lowtide_paving_relief.py: candidate; generated albedo is unchanged.
"Layer0"
{{
    shader "{SHADER}"
    TextureColor "{P.RESOURCE}_color.png"
    TextureNormal "{RESOURCE}_normal.png"
    TextureRoughness "{P.RESOURCE}_rough.png"
    TextureMetalness "[0 0 0 0]"
    TextureAmbientOcclusion "{RESOURCE}_ao.png"
    TextureHeight "{RESOURCE}_height.png"
    g_vPavingScale "[{scale[0]:.8f} {scale[1]:.8f}]"
    g_vPavingRegion "[{values}]"
    g_flReliefDepth "{DEPTH_MM / 25.4:.8f}"
    g_vReliefFade "[300 850]"
}}
'''


def write_candidate(directory):
    directory = Path(directory).resolve()
    if directory == K.ASSETS.resolve() or K.ASSETS.resolve() in directory.parents:
        raise ValueError("Stage outside Assets; import through the running editor")
    rgb = P.read_surface()
    scale, region = P.layout(rgb)
    maps, report = surface_maps(rgb, scale, region)
    atlas = 1 << int(np.ceil(np.log2(rgb.shape[0])))
    for suffix, array in maps.items():
        repeats = (int(np.ceil(atlas / array.shape[0])), int(np.ceil(atlas / array.shape[1])))
        if array.ndim == 3:
            repeats += (1,)
        packed = np.tile(array, repeats)[:atlas, :atlas]
        path = directory / f"{RESOURCE}_{suffix}.png"
        path.parent.mkdir(parents=True, exist_ok=True)
        Image.fromarray(packed).save(path, optimize=True)
    (directory / f"{RESOURCE}_relief.vmat").write_text(material_text(scale, region), encoding="utf-8")
    report.update(scale=list(scale), region=list(region), atlas=atlas,
        source_sha256=hashlib.sha256(P.SOURCE.read_bytes()).hexdigest(),
        colour_sha256=hashlib.sha256((K.ASSETS / f"{P.RESOURCE}_color.png").read_bytes()).hexdigest(),
        status="candidate staged; no installed asset or scene changed")
    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--stage", type=Path, required=True)
    args = parser.parse_args()
    result = write_candidate(args.stage)
    (args.stage / "surface-report.json").write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2))
