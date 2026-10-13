"""Photographic deck boards for Lowtide's sack pallets; keeps the original skid bounds."""
import io
from pathlib import Path
import zlib

import numpy as np
from PIL import Image
from scipy import ndimage

import map_kit as K

SOURCE = Path(__file__).with_name("lowtide_pallets_source.png")
OUT = K.ASSETS / "materials/lowtide/pallets"
RESOURCE = "materials/lowtide/pallets"
TOP = "lt_pallet_wood"
SIDE = "lt_pallet_side"


def write_materials():
    OUT.mkdir(parents=True, exist_ok=True)
    with Image.open(SOURCE) as image:
        rgb = np.asarray(image.convert("RGB").resize((2048, 2048), Image.Resampling.LANCZOS), np.float32) / 255
    luminance = rgb @ np.array((.2126, .7152, .0722), np.float32)
    grain = ndimage.gaussian_filter(luminance, .7, mode="wrap") - ndimage.gaussian_filter(luminance, 6, mode="wrap")
    pores = np.clip((.40 - luminance) * 2, 0, .65)
    rough = np.clip(.80 + pores * .18 - grain * .12, .69, .95)
    height = grain * .10 - pores * .012
    dy, dx = np.gradient(ndimage.gaussian_filter(height, .7, mode="wrap"))
    normal = np.dstack((-dx * 4, dy * 4, np.ones_like(dx)))
    normal /= np.linalg.norm(normal, axis=2, keepdims=True)
    for channel, data in (("color", rgb * 255), ("normal", (normal * .5 + .5) * 255), ("rough", rough * 255)):
        stream = io.BytesIO()
        Image.fromarray(np.clip(np.rint(data), 0, 255).astype(np.uint8)).save(stream, format="PNG", optimize=True)
        path, payload = OUT / f"wood_{channel}.png", stream.getvalue()
        if not path.exists() or path.read_bytes() != payload:
            path.write_bytes(payload)
    for paint, tint in ((TOP, 1), (SIDE, .86)):
        text = f'''// Tools/lowtide_pallets.py; generated weathered timber
"Layer0"
{{
    shader "shaders/complex.shader"
    F_SPECULAR "1"
    g_flMetalness "0"
    g_flRoughnessScaleFactor "1"
    g_vColorTint "[{tint} {tint} {tint} 1]"
    g_flModelTintAmount "1"
    TextureColor "{RESOURCE}/wood_color.png"
    TextureNormal "{RESOURCE}/wood_normal.png"
    TextureRoughness "{RESOURCE}/wood_rough.png"
    TextureAmbientOcclusion "materials/default/default_ao.tga"
}}
'''
        K.write_text(OUT / f"{paint}.vmat", text)


def configure(model):
    for paint in (TOP, SIDE):
        if paint in model.polygons:
            model.material_overrides[paint] = f"{RESOURCE}/{paint}.vmat"
            model.tile_overrides[paint] = 64


def face_uv(paint, points, normal, lo, size):
    points, normal, lo, size = (np.asarray(value, float) for value in (points, normal, lo, size))
    seed = zlib.crc32(",".join(f"{value:.3f}" for value in lo).encode())
    if abs(normal[2]) > .5:
        u = (points[:, 0] - lo[0]) / size[0]
        v = (points[:, 1] - lo[1]) / 32 + .125
    else:
        along = 1 if abs(normal[0]) > .5 else 0
        u = (points[:, along] - lo[along]) / size[along]
        # Crop the shallow side from one board so it has no fake horizontal plank joint.
        v = (points[:, 2] - lo[2]) / 32 + (seed % 4) * .25 + .03
    if seed & 1:
        u = 1 - u
    return np.column_stack((u * .90 + .05, v))


def build(model, lo, size):
    lo, size = np.asarray(lo, float), np.asarray(size, float)
    starts = {paint: len(model.polygons[paint]) for paint in (TOP, SIDE)}
    model.box(lo, lo + size, {"default": SIDE, "+z": TOP}, "wood")
    for paint, start in starts.items():
        for i in range(start, len(model.polygons[paint])):
            points, normal = model.polygons[paint][i]
            model.polygon_uvs[(paint, i)] = face_uv(paint, points, normal, lo, size).tolist()


if __name__ == "__main__":
    write_materials()
    print("Lowtide pallet timber and surface maps saved")
